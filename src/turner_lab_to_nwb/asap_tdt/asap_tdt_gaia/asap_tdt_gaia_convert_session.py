"""Primary script to run to convert an entire session for of data using the NWBConverter."""
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from dateutil.tz import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update, FilePathType

from turner_lab_to_nwb.asap_tdt.asap_tdt_gaia.asap_tdt_gaianwbconverter import AsapTdtGaiaNWBConverter


def session_to_nwb(
    nwbfile_path: FilePathType,
    tdt_tank_file_path: FilePathType,
    session_metadata: pd.DataFrame,
    events_file_path: FilePathType,
    flt_file_path: Optional[FilePathType] = None,
    plexon_file_path: Optional[FilePathType] = None,
    target_name_mapping: Optional[dict] = None,
    stub_test: bool = False,
):
    """
    Convert a session of data to NWB.

    Parameters
    ----------
    nwbfile_path : FilePathType
        The path that points to the NWB file to be created.
    tdt_tank_file_path : FilePathType
        The path that points to a TDT Tank file (.Tbk).
    data_list_file_path : FilePathType
        The path that points to the electrode metadata file (.xlsx).
    session_id : str
        The unique identifier for the session.
    events_file_path : FilePathType
        The path that points to the .mat file containing the events, units data and optionally include the stimulation data.
    location : Optional[str], optional
        The location of the probe, when specified allows to filter the channels by location. By default None.
    flt_file_path : FilePathType, optional
        The path to the high-pass filtered data.
    plexon_file_path : FilePathType, optional
        The path to Plexon file (.plx) containing the spike sorted data.
    target_name_mapping : Optional[dict], optional
        A dictionary mapping the target identifiers to more descriptive names, e.g. 1: "Left", 3: "Right".
    stub_test : bool, optional
        Whether to run the conversion in stub test mode, by default False.
    """
    ecephys_file_path = Path(tdt_tank_file_path)

    source_data = dict()
    conversion_options = dict()

    channel_metadata = session_metadata.to_dict(orient="list")

    # Add Recording
    source_data.update(
        dict(
            Recording=dict(
                file_path=str(ecephys_file_path),
                channel_metadata=channel_metadata,
                gain=1.0,
            ),
        ),
    )
    conversion_options.update(dict(Recording=dict(stub_test=stub_test)))

    # Add Sorting (uncurated spike times from Plexon Offline Sorter v3)
    conversion_options_sorting = dict(
        stub_test=stub_test,
        write_as="processing",
        units_description="The units were sorted using the Plexon Offline Sorter v3.",
    )

    # Add Processed Recording (high-pass filtered data)
    if flt_file_path:
        source_data.update(
            dict(ProcessedRecording=dict(file_path=str(flt_file_path), channel_metadata=channel_metadata))
        )
        conversion_options.update(dict(ProcessedRecording=dict(stub_test=stub_test, write_as="processed")))

    # Add Sorting (uncurated spike times from Plexon Offline Sorter v3)
    if plexon_file_path:
        source_data.update(dict(PlexonSorting=dict(file_path=str(plexon_file_path), channel_metadata=channel_metadata)))
        conversion_options.update(dict(PlexonSorting=conversion_options_sorting))

    # Add Sorting (curated spike times from Plexon Offline Sorter v3, only include single units)
    location = None if "VL" in channel_metadata["Target"] else "GPi"
    source_data.update(dict(CuratedSorting=dict(file_path=str(events_file_path), location=location)))
    conversion_options.update(
        dict(
            CuratedSorting=dict(
                stub_test=stub_test,
                units_description="The curated single-units from the Plexon Offline Sorter v3, selected based on the quality of spike sorting.",
            )
        )
    )

    # Add Events
    source_data.update(dict(Events=dict(file_path=str(events_file_path))))
    if target_name_mapping:
        conversion_options.update(dict(Events=dict(target_name_mapping=target_name_mapping)))

    converter = AsapTdtGaiaNWBConverter(source_data=source_data, verbose=False)

    metadata = converter.get_metadata()
    # For data provenance we can add the time zone information to the conversion if missing
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("US/Pacific")
    session_id = channel_metadata["Filename"][0]
    metadata["NWBFile"].update(
        session_id=str(session_id).replace("_", "-"),
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
    )

    # Update default metadata with the editable in the corresponding yaml file
    general_metadata = "public_metadata.yaml" if location == "GPi" else "embargo_metadata.yaml"
    editable_metadata_path = Path(__file__).parent.parent / "metadata" / general_metadata
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Load subject metadata from the yaml file
    subject_metadata_path = Path(__file__).parent / "metadata" / "subject_metadata.yaml"
    subject_metadata = load_dict_from_file(subject_metadata_path)
    pharmacology = subject_metadata["Subject"].pop("pharmacology")
    metadata["NWBFile"].update(pharmacology=pharmacology)
    metadata["Subject"].update(**subject_metadata["Subject"])
    date_of_birth = metadata["Subject"]["date_of_birth"]
    date_of_birth_dt = datetime.strptime(date_of_birth, "%Y-%m-%d")
    metadata["Subject"].update(date_of_birth=date_of_birth_dt.replace(tzinfo=tzinfo))

    # Load ecephys metadata
    ecephys_metadata = load_dict_from_file(Path(__file__).parent.parent / "metadata" / "ecephys_metadata.yaml")
    metadata = dict_deep_update(metadata, ecephys_metadata)

    # Run conversion
    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":
    # Parameters for conversion
    # The root folder containing the sessions
    folder_path = Path("/Volumes/t7-ssd/Turner/Previous_PD_Project_sample")

    # The date string that identifies the session
    date_string = "160624"
    # The identifier of the session to be converted
    session_id = f"I_{date_string}_2"

    # The identifier of the subject
    subject_id = "Gaia"

    # The path to a single TDT Tank file (.Tbk)
    tank_file_path = folder_path / f"I_{date_string}" / f"{subject_id}_{session_id}.Tbk"

    # The path to the electrode metadata file (.xlsx)
    data_list_file_path = Path("/Volumes/t7-ssd/Turner/Previous_PD_Project_sample/Isis_DataList_temp.xlsx")

    # The plexon file with the spike sorted data from VL
    vl_plexon_file_path = folder_path / f"I_{date_string}" / f"{session_id}_Chans_1_16.plx"
    # The plexon file with the spike sorted data from GPi, optional
    # When stimulation site is GPi, the plexon file is empty and this should be set to None
    gpi_plexon_file_path = None
    # gpi_plexon_file_path = folder_path / f"I_{date_string}" / f"{session_id}_Chans_17_32.plx"

    # The path to the high-pass filtered data from VL
    vl_flt_file_path = folder_path / f"I_{date_string}" / f"{session_id}_Chans_1_16.flt.mat"
    # The path to the high-pass filtered data from GPi, optional
    # gpi_flt_file_path = folder_path / f"I_{date_string}" / f"{session_id}_Chans_24_24.flt.mat"
    gpi_flt_file_path = None

    # The path to the .mat file containing the events, units data and optionally include the stimulation data
    events_file_path = folder_path / f"I_{date_string}" / f"{session_id}.mat"
    # The mapping of the target identifiers to more descriptive names, e.g. 1: "Left", 3: "Right"
    target_name_mapping = {1: "Left", 3: "Right"}

    # The path to the NWB file to be created
    nwbfile_path = Path(f"/Volumes/t7-ssd/nwbfiles/stub_{subject_id}_{session_id}.nwb")

    # For testing purposes, set stub_test to True to convert only a stub of the session
    stub_test = False

    session_to_nwb(
        nwbfile_path=nwbfile_path,
        tdt_tank_file_path=tank_file_path,
        gpi_flt_file_path=gpi_flt_file_path,
        vl_flt_file_path=vl_flt_file_path,
        data_list_file_path=data_list_file_path,
        vl_plexon_file_path=vl_plexon_file_path,
        gpi_plexon_file_path=gpi_plexon_file_path,
        session_id=session_id,
        subject_id=subject_id,
        events_file_path=events_file_path,
        target_name_mapping=target_name_mapping,
        stub_test=stub_test,
    )