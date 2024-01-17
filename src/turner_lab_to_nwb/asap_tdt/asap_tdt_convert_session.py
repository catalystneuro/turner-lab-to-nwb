"""Primary script to run to convert an entire session for of data using the NWBConverter."""
from pathlib import Path
from typing import Optional

from dateutil.tz import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update, FilePathType

from turner_lab_to_nwb.asap_tdt import AsapTdtNWBConverter


def session_to_nwb(
    nwbfile_path: FilePathType,
    tdt_tank_file_path: FilePathType,
    data_list_file_path: FilePathType,
    vl_plexon_file_path: FilePathType,
    session_id: str,
    gpi_plexon_file_path: Optional[FilePathType] = None,
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
    vl_plexon_file_path : FilePathType
        The path to Plexon file (.plx) containing the spike sorted data from VL.
    gpi_plexon_file_path : FilePathType, optional
        The path to Plexon file (.plx) containing the spike sorted data from GPi.
    session_id : str
        The unique identifier for the session.
    stub_test : bool, optional
        Whether to run the conversion in stub test mode, by default False.
    """
    ecephys_file_path = Path(tdt_tank_file_path)

    source_data = dict()
    conversion_options = dict()

    # Add Recording
    source_data.update(
        dict(Recording=dict(file_path=str(ecephys_file_path), data_list_file_path=str(data_list_file_path)))
    )
    conversion_options.update(dict(Recording=dict(stub_test=stub_test)))

    # Add Sorting
    source_data.update(dict(SortingVL=dict(file_path=str(vl_plexon_file_path))))
    conversion_options_sorting = dict(
        stub_test=stub_test,
        write_as="processing",
        units_description="The units were sorted using the Plexon Offline Sorter v3.",
    )
    conversion_options.update(dict(SortingVL=conversion_options_sorting))
    if gpi_plexon_file_path:
        source_data.update(dict(SortingGPi=dict(file_path=str(gpi_plexon_file_path))))
        conversion_options.update(dict(SortingGPi=conversion_options_sorting))

    converter = AsapTdtNWBConverter(source_data=source_data)

    metadata = converter.get_metadata()
    # For data provenance we can add the time zone information to the conversion if missing

    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("US/Pacific")
    metadata["NWBFile"].update(
        session_id=str(session_id).replace("_", "-"),
        session_start_time=session_start_time.replace(tzinfo=tzinfo),
    )

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "asap_tdt_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

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

    # The path to a single TDT Tank file (.Tbk)
    tank_file_path = folder_path / f"I_{date_string}" / f"Gaia_{session_id}.Tbk"

    # The path to the electrode metadata file (.xlsx)
    data_list_file_path = Path("/Volumes/t7-ssd/Turner/Previous_PD_Project_sample/Isis_DataList_temp.xlsx")

    # The plexon file with the spike sorted data from VL
    vl_plexon_file_path = folder_path / f"I_{date_string}" / f"{session_id}_Chans_1_16.plx"
    # The plexon file with the spike sorted data from GPi, optional
    # When stimulation site is GPi, the plexon file is empty and this should be set to None
    # gpi_plexon_file_path = None
    gpi_plexon_file_path = folder_path / f"I_{date_string}" / f"{session_id}_Chans_24_24.plx"

    # The path to the NWB file to be created
    nwbfile_path = Path(f"/Volumes/t7-ssd/nwbfiles/stub_Gaia_{session_id}.nwb")

    # For testing purposes, set stub_test to True to convert only a stub of the session
    stub_test = False

    session_to_nwb(
        nwbfile_path=nwbfile_path,
        tdt_tank_file_path=tank_file_path,
        data_list_file_path=data_list_file_path,
        vl_plexon_file_path=vl_plexon_file_path,
        gpi_plexon_file_path=gpi_plexon_file_path,
        session_id=session_id,
        stub_test=stub_test,
    )
