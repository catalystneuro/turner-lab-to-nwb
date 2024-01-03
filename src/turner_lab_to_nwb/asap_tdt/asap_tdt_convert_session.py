"""Primary script to run to convert an entire session for of data using the NWBConverter."""
from pathlib import Path
import datetime
from zoneinfo import ZoneInfo

from neuroconv.utils import load_dict_from_file, dict_deep_update, FilePathType

from turner_lab_to_nwb.asap_tdt import AsapTdtNWBConverter


def session_to_nwb(
    nwbfile_path: FilePathType,
    tdt_tank_file_path: FilePathType,
    data_list_file_path: FilePathType,
    VL_plexon_file_path: FilePathType,
    GPi_plexon_file_path: FilePathType,
    stub_test: bool = False,
):
    """
    Parameters
    ----------
    nwbfile_path : FilePathType
        The path that points to the NWB file to be created.
    tdt_tank_file_path : FilePathType
        The path that points to a TDT Tank file (.Tbk).
    data_list_file_path : FilePathType
        The path that points to the electrode metadata file (.xlsx).
    stub_test : bool, optional
        Whether to run the conversion in stub test mode, by default False.
    """
    ecephys_file_path = Path(tdt_tank_file_path)

    source_data = dict()
    conversion_options = dict()

    # Add Recording
    source_data.update(
        dict(Recording=dict(file_path=str(ecephys_file_path), electrode_metadata_file_path=str(data_list_file_path)))
    )
    conversion_options.update(dict(Recording=dict(stub_test=stub_test)))

    # Add Sorting
    source_data.update(
        dict(
            SortingVL=dict(file_path=str(VL_plexon_file_path)),
            SortingGPi=dict(file_path=str(GPi_plexon_file_path)),
        )
    )
    conversion_options.update(
        dict(
            SortingVL=dict(stub_test=stub_test),
            SortingGPi=dict(stub_test=stub_test),
        )
    )

    converter = AsapTdtNWBConverter(source_data=source_data)

    metadata = converter.get_metadata()
    metadata["NWBFile"].update(
        session_id=ecephys_file_path.stem.replace("_", "-"),
        # todo: add session_start_time to metadata
        session_start_time=datetime.datetime.now(tz=ZoneInfo("US/Pacific")),
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
    folder_path = Path("/Volumes/t7-ssd/Turner/Previous_PD_Project_sample/I_160615")

    tank_file_path = folder_path / "Gaia_I_160615_1.Tbk"
    data_list_file_path = Path("/Volumes/t7-ssd/Turner/Previous_PD_Project_sample/Isis_DataList_160615.xlsx")

    VL_plexon_file_path = folder_path / "I_160615_1_Chans_1_1.plx"
    GPi_plexon_file_path = folder_path / "I_160615_1_Chans_17_32.plx"

    nwbfile_path = Path("/Volumes/t7-ssd/nwbfiles/stub_Gaia_I_160615_1.nwb")
    stub_test = True

    session_to_nwb(
        nwbfile_path=nwbfile_path,
        tdt_tank_file_path=tank_file_path,
        data_list_file_path=data_list_file_path,
        VL_plexon_file_path=VL_plexon_file_path,
        GPi_plexon_file_path=GPi_plexon_file_path,
        stub_test=stub_test,
    )
