"""Primary script to run to convert an entire session for of data using the NWBConverter."""
from pathlib import Path
from typing import Union
import datetime
from zoneinfo import ZoneInfo

from neuroconv.utils import load_dict_from_file, dict_deep_update, FolderPathType, FilePathType

from turner_lab_to_nwb.asap_embargo import AsapEmbargoNWBConverter


def session_to_nwb(
    ecephys_folder_path: FolderPathType,
    nwbfile_path: FilePathType,
    stub_test: bool = False,
):
    ecephys_folder_path = Path(ecephys_folder_path)

    source_data = dict()
    conversion_options = dict()

    # Add Recording
    source_data.update(dict(Recording=dict(folder_path=str(ecephys_folder_path))))
    conversion_options.update(dict(Recording=dict(stub_test=stub_test)))

    converter = AsapEmbargoNWBConverter(source_data=source_data)

    metadata = converter.get_metadata()
    metadata["NWBFile"].update(session_id=ecephys_folder_path.stem.replace("_", "-"))

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "asap_embargo_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Run conversion
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options)


if __name__ == "__main__":
    # Parameters for conversion
    data_dir_path = Path("/Users/weian/data/L_230905_125344")
    nwbfile_path = Path("/Volumes/t7-ssd/nwbfiles/L_230905_125344.nwb")
    stub_test = False

    session_to_nwb(
        ecephys_folder_path=data_dir_path,
        nwbfile_path=nwbfile_path,
        stub_test=stub_test,
    )
