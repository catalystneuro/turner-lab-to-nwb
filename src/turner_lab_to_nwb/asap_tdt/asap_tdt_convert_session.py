from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from dateutil import tz
from neuroconv.utils import FilePathType, load_dict_from_file, dict_deep_update
from nwbinspector import inspect_nwbfile
from pymatreader import read_mat

from turner_lab_to_nwb.asap_tdt import ASAPTdtNWBConverter
from turner_lab_to_nwb.asap_tdt.interfaces import (
    ASAPTdtRecordingInterface,
    ASAPTdtEventsInterface,
    ASAPTdtSortingInterface,
    ASAPTdtFilteredRecordingInterface,
    ASAPTdtPlexonSortingInterface,
    ASAPTdtMultiFileFilteredRecordingInterface,
)

from turner_lab_to_nwb.asap_tdt.utils import load_units_dataframe


def session_to_nwb(
    nwbfile_path: FilePathType,
    tdt_tank_file_path: FilePathType,
    subject_id: str,
    session_id: str,
    session_metadata: pd.DataFrame,
    events_file_path: FilePathType,
    gpi_only: bool = False,
    flt_file_path: Optional[FilePathType] = None,
    plexon_file_path: Optional[FilePathType] = None,
    target_name_mapping: Optional[dict] = None,
    stub_test: bool = False,
    verbose: bool = True,
):

    data_interfaces = dict()
    conversion_options = dict()

    channel_metadata = session_metadata.to_dict(orient="list")

    # Temporary until TDT files are fixed that have missing "StoreName" header key error.
    try:
        recording_interface = ASAPTdtRecordingInterface(
            file_path=str(tdt_tank_file_path),
            channel_metadata=channel_metadata,
            gain=1.0,
        )
    except Exception as e:
        print(f"Error in recording interface for session {tdt_tank_file_path}: {e}")
        return []

    data_interfaces.update(Recording=recording_interface)
    conversion_options.update(Recording=dict(stub_test=stub_test))

    events_interface = ASAPTdtEventsInterface(file_path=events_file_path)
    data_interfaces.update(Events=events_interface)
    conversion_options.update(Events=dict(target_name_mapping=target_name_mapping))

    # Check 'units' structure in the events file
    # Sometimes the events file does not contain the 'units' structure, so we need to check if it exists
    events_mat = read_mat(events_file_path)
    has_units = False
    if "units" in events_mat:
        units_df = load_units_dataframe(mat=events_mat)
        # check in advance if the units are empty
        units_df = units_df[units_df["brain_area"].eq("GPi") == gpi_only]
        has_units = not units_df.empty

    # Add Curated Sorting
    if has_units:
        curated_sorting_interface = ASAPTdtSortingInterface(file_path=events_file_path, gpi_only=gpi_only)
        data_interfaces.update(CuratedSorting=curated_sorting_interface)
        conversion_options.update(
            CuratedSorting=dict(
                stub_test=stub_test,
                units_description="The curated single-units from the Plexon Offline Sorter v3, selected based on the quality of spike sorting.",
            )
        )

    # Add Filtered Recording
    if flt_file_path is not None:
        # When there is only one flt file, we can directly subset the channels using the channel metadata
        if len(flt_file_path) == 1:
            processed_recording_source_data = dict(
                file_path=str(flt_file_path[0]),
                channel_metadata=channel_metadata,
                es_key="ElectricalSeriesProcessed",
            )
            processed_recording_interface = ASAPTdtFilteredRecordingInterface(**processed_recording_source_data)
            data_interfaces.update(ProcessedRecording=processed_recording_interface)
            conversion_options.update(ProcessedRecording=dict(stub_test=stub_test, write_as="processed"))

        # For files that contain the "Ch_" string in the name, they contain only one channel per file
        elif "Ch_" in str(flt_file_path[0]):
            # When there are multiple flt files, we need to match the target to the flt file
            channel_ids = session_metadata.groupby("Target")["Chan#"].apply(list).to_dict()
            for target_name, channels in channel_ids.items():
                file_paths = [str(file) for chan in channels for file in flt_file_path if f"Ch_{chan}.flt" in file.stem]
                assert len(file_paths) == len(channels), f"Could not find flt file for channels {channels}."
                channel_metadata_per_target = session_metadata[session_metadata["Target"] == target_name]
                processed_recording_source_data = dict(
                    file_paths=file_paths,
                    channel_metadata=channel_metadata_per_target.to_dict(orient="list"),
                    es_key="ElectricalSeriesProcessed" + target_name,
                )
                processed_recording_interface = ASAPTdtMultiFileFilteredRecordingInterface(
                    **processed_recording_source_data
                )
                interface_name = f"ProcessedRecording{target_name}"
                data_interfaces.update({interface_name: processed_recording_interface})
                conversion_options.update({interface_name: dict(stub_test=stub_test, write_as="processed")})

        # When there are multiple flt files (but they contain more than one channel), we need to match the channel names in the file name to the channel metadata
        else:
            # When there are multiple flt files, we need to match the target to the flt file
            channel_ids = session_metadata.groupby("Target")["Chan#"].apply(list).to_dict()
            # we have to check that both channels are present in the flt file name
            channels_from_flt_name = [file.stem.replace(".flt", "").split("_")[-2:] for file in flt_file_path]
            channel_ranges = [range(int(channels[0]), int(channels[1]) + 1) for channels in channels_from_flt_name]
            # match target to flt file
            for target_name, channels in channel_ids.items():
                flt_file_path_per_target = None
                for ind, channel_range in enumerate(channel_ranges):
                    if all(int(chan) in channel_range for chan in channels):
                        flt_file_path_per_target = flt_file_path[ind]
                        break
                channel_metadata_per_target = session_metadata[session_metadata["Target"] == target_name]
                assert flt_file_path_per_target is not None, f"Could not find flt file for channels {channels}."

                processed_recording_source_data = dict(
                    file_path=str(flt_file_path_per_target),
                    channel_metadata=channel_metadata_per_target.to_dict(orient="list"),
                    es_key="ElectricalSeriesProcessed" + target_name,
                )
                processed_recording_interface = ASAPTdtFilteredRecordingInterface(**processed_recording_source_data)
                interface_name = f"ProcessedRecording{target_name}"
                data_interfaces.update({interface_name: processed_recording_interface})
                conversion_options.update({interface_name: dict(stub_test=stub_test, write_as="processed")})

    # Add Uncurated Sorting
    if plexon_file_path is not None:
        conversion_options_sorting = dict(
            stub_test=stub_test,
            write_as="processing",
            units_description="The units were sorted using the Plexon Offline Sorter v3.",
        )
        if len(plexon_file_path) == 1:
            plexon_sorting_interface = ASAPTdtPlexonSortingInterface(
                file_path=plexon_file_path[0], channel_metadata=channel_metadata
            )
            data_interfaces.update(PlexonSorting=plexon_sorting_interface)
            conversion_options.update(PlexonSorting=conversion_options_sorting)
        else:
            channel_ids = session_metadata.groupby("Target")["Chan#"].apply(list).to_dict()
            channels_from_plx_name = [file.stem.split("_")[-2:] for file in plexon_file_path]
            channel_ranges = [range(int(channels[0]), int(channels[1]) + 1) for channels in channels_from_plx_name]
            # match target to plexon file
            for target_name, channels in channel_ids.items():
                plexon_file_path_per_target = None
                for ind, channel_range in enumerate(channel_ranges):
                    if all(int(chan) in channel_range for chan in channels):
                        plexon_file_path_per_target = plexon_file_path[ind]
                        break
                if plexon_file_path_per_target is None:
                    print(f"Could not find plexon file for channels {channels}.")
                    continue
                channel_metadata_per_target = session_metadata[session_metadata["Target"] == target_name]
                try:
                    plexon_sorting_interface = ASAPTdtPlexonSortingInterface(
                        file_path=plexon_file_path_per_target,
                        channel_metadata=channel_metadata_per_target.to_dict(orient="list"),
                    )
                    interface_name = f"PlexonSorting{target_name}"
                    data_interfaces.update({interface_name: plexon_sorting_interface})
                    conversion_options.update({interface_name: conversion_options_sorting})
                except ValueError as e:
                    # Skip the session if there is no sorting data inside the plexon file
                    print(f"Error in plexon sorting interface for session {plexon_file_path_per_target}: {e}")
                    continue

    # Create the converter
    converter = ASAPTdtNWBConverter(
        data_interfaces=data_interfaces,
        verbose=verbose,
    )

    metadata = converter.get_metadata()
    # For data provenance we can add the time zone information to the conversion if missing
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("US/Pacific")

    # Add tag to the session_id
    tag = "pre_MPTP" if "pre_MPTP" in Path(tdt_tank_file_path).parts else "post_MPTP"
    session_id_with_tag = f"{tag}-{session_id}"
    session_id_with_tag = session_id_with_tag.replace("_", "-")  # e.g. pre-MPTP-I-160818-4
    metadata["NWBFile"].update(
        session_id=session_id_with_tag,
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
    )

    # Update default metadata with the editable in the corresponding yaml file
    general_metadata = f"{tag}_public_metadata.yaml" if gpi_only else f"{tag}_embargo_metadata.yaml"
    editable_metadata_path = Path(__file__).parent / "metadata" / general_metadata
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Load subject metadata from the yaml file
    subject_metadata_path = Path(__file__).parent / "metadata" / "subjects_metadata.yaml"
    subject_metadata = load_dict_from_file(subject_metadata_path)
    subject_metadata = subject_metadata["Subject"][subject_id]

    # Add pharmacology metadata for post_MPTP sessions
    pharmacology = subject_metadata.pop("pharmacology")
    if tag == "post_MPTP":
        metadata["NWBFile"].update(pharmacology=pharmacology)

    metadata["Subject"].update(**subject_metadata)
    date_of_birth = metadata["Subject"]["date_of_birth"]
    date_of_birth_dt = datetime.strptime(date_of_birth, "%Y-%m-%d")
    metadata["Subject"].update(date_of_birth=date_of_birth_dt.replace(tzinfo=tzinfo))

    # Load ecephys metadata
    ecephys_metadata = load_dict_from_file(Path(__file__).parent / "metadata" / "ecephys_metadata.yaml")
    has_sorting = any("Sorting" in data_interface_name for data_interface_name in data_interfaces.keys())
    if not has_sorting:
        # Remove unit metadata when no unit data is present for the session
        ecephys_metadata["Ecephys"].pop("UnitProperties")
    metadata = dict_deep_update(metadata, ecephys_metadata)

    metadata["LabMetaData"] = dict(name="MPTPMetaData", MPTP_status=tag)

    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        overwrite=True,
        conversion_options=conversion_options,
    )

    # Run inspection for nwbfile
    results = list(inspect_nwbfile(nwbfile_path=nwbfile_path))
    return results
