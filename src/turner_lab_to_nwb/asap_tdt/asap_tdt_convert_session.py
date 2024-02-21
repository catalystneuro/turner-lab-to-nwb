from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from dateutil import tz
from neuroconv.utils import FilePathType, load_dict_from_file, dict_deep_update
from pymatreader import read_mat

from turner_lab_to_nwb.asap_tdt import ASAPTdtNWBConverter
from turner_lab_to_nwb.asap_tdt.interfaces import (
    ASAPTdtRecordingInterface,
    ASAPTdtEventsInterface,
    ASAPTdtSortingInterface,
    ASAPTdtFilteredRecordingInterface,
    ASAPTdtPlexonSortingInterface,
)
from turner_lab_to_nwb.asap_tdt.utils import load_units_dataframe


def session_to_nwb(
    nwbfile_path: FilePathType,
    tdt_tank_file_path: FilePathType,
    subject_id: str,
    session_id: str,
    session_metadata: pd.DataFrame,
    events_file_path: FilePathType,
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
        return

    data_interfaces.update(Recording=recording_interface)
    conversion_options.update(Recording=dict(stub_test=stub_test))

    events_interface = ASAPTdtEventsInterface(file_path=events_file_path)
    data_interfaces.update(Events=events_interface)
    conversion_options.update(Events=dict(target_name_mapping=target_name_mapping))

    # Check 'units' structure in the events file

    gpi_only = True if "GP" in session_metadata["Target"].values else False

    # Sometimes the events file does not contain the 'units' structure, so we need to check if it exists
    matin = read_mat(events_file_path)
    has_units = False
    if "units" in matin:
        units_df = load_units_dataframe(mat=matin)
        # check in advance if the units are empty
        units_df = units_df[units_df["brain_area"].str.contains("GP") == gpi_only]
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
        if len(flt_file_path) == 1:
            processed_recording_source_data = dict(
                file_path=str(flt_file_path[0]),
                channel_metadata=channel_metadata,
                es_key="ElectricalSeriesProcessed",
            )
            processed_recording_interface = ASAPTdtFilteredRecordingInterface(**processed_recording_source_data)
            data_interfaces.update(ProcessedRecording=processed_recording_interface)
            conversion_options.update(ProcessedRecording=dict(stub_test=stub_test, write_as="processed"))

        else:
            # When there are multiple flt files, we need to match the target to the flt file
            channel_ids = session_metadata.groupby("Target")["Chan#"].apply(list).to_dict()
            # match target to flt file
            for target_name, channels in channel_ids.items():
                channel_names = "Chans_{}_".format(channel_ids[target_name][0])
                channel_metadata_per_target = session_metadata[session_metadata["Target"] == target_name]
                flt_file_path_per_target = [path for path in flt_file_path if channel_names in path.name]
                if len(flt_file_path_per_target) != 1:
                    raise ValueError(f"Found {len(flt_file_path_per_target)} flt files for target {target_name}.")

                processed_recording_source_data = dict(
                    file_path=str(flt_file_path_per_target[0]),
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
            # match target to plexon file
            for target_name, channels in channel_ids.items():
                channel_names = "Chans_{}_".format(channel_ids[target_name][0])
                channel_metadata_per_target = session_metadata[session_metadata["Target"] == target_name]
                if channel_metadata_per_target["Note"].isin(["no units"]).all():
                    continue
                plexon_file_path_per_target = [path for path in plexon_file_path if channel_names in path.name]
                if len(plexon_file_path_per_target) != 1:
                    print(f"Found {len(plexon_file_path_per_target)} plexon files for target {target_name}.")
                    continue
                plexon_sorting_interface = ASAPTdtPlexonSortingInterface(
                    file_path=plexon_file_path_per_target[0],
                    channel_metadata=channel_metadata_per_target.to_dict(orient="list"),
                )
                interface_name = f"PlexonSorting{target_name}"
                data_interfaces.update({interface_name: plexon_sorting_interface})
                conversion_options.update({interface_name: conversion_options_sorting})

    # Create the converter
    converter = ASAPTdtNWBConverter(
        data_interfaces=data_interfaces,
        verbose=verbose,
    )

    metadata = converter.get_metadata()
    # For data provenance we can add the time zone information to the conversion if missing
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("US/Pacific")
    tag = "pre-MPTP" if "pre_MPTP" in Path(tdt_tank_file_path).parts else "post-MPTP"
    session_id = session_id.replace("_", "-")
    session_id_with_tag = f"{tag}-{session_id}"  # e.g. pre-MPTP-I-160818-4
    metadata["NWBFile"].update(
        session_id=session_id_with_tag,
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
    )

    # Update default metadata with the editable in the corresponding yaml file
    general_metadata = "public_metadata.yaml" if gpi_only else "embargo_metadata.yaml"
    editable_metadata_path = Path(__file__).parent / "metadata" / general_metadata
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Load subject metadata from the yaml file
    subject_metadata_path = Path(__file__).parent / "metadata" / "subjects_metadata.yaml"
    subject_metadata = load_dict_from_file(subject_metadata_path)
    subject_metadata = subject_metadata["Subject"][subject_id]
    pharmacology = subject_metadata.pop("pharmacology")
    metadata["NWBFile"].update(pharmacology=pharmacology)
    metadata["Subject"].update(**subject_metadata)
    date_of_birth = metadata["Subject"]["date_of_birth"]
    date_of_birth_dt = datetime.strptime(date_of_birth, "%Y-%m-%d")
    metadata["Subject"].update(date_of_birth=date_of_birth_dt.replace(tzinfo=tzinfo))

    # Load ecephys metadata
    has_sorting = any("Sorting" in data_interface_name for data_interface_name in data_interfaces.keys())
    if has_sorting:
        ecephys_metadata = load_dict_from_file(Path(__file__).parent / "metadata" / "ecephys_metadata.yaml")
        metadata = dict_deep_update(metadata, ecephys_metadata)

    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        overwrite=True,
        conversion_options=conversion_options,
    )
