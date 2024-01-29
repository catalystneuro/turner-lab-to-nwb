import os
from pathlib import Path
from typing import Literal

from neuroconv.tools import LocalPathExpander
from neuroconv.utils import FolderPathType, FilePathType
from tqdm import tqdm
import warnings

warnings.filterwarnings("ignore", "Could not identify sev files for channels")
warnings.filterwarnings(
    "ignore",
    r"Complex objects \(like classes\) are not supported\. They are imported on a best effort base but your mileage will vary\.",
)

from turner_lab_to_nwb.asap_tdt.asap_tdt_convert_session import session_to_nwb
from turner_lab_to_nwb.asap_tdt.utils import load_session_metadata


def convert_sessions(
    folder_path: FolderPathType,
    data_list_file_path: FilePathType,
    output_folder_path: FolderPathType,
    dataset_mode: Literal["embargo", "public"],
    stub_test: bool = False,
    verbose: bool = True,
):
    """
    Convert all sessions from the ASAP TDT dataset.

    Parameters
    ----------
    folder_path : FolderPathType
        The root folder containing the sessions.
    data_list_file_path : FilePathType
        The path to the electrode metadata file (.xlsx).
    output_folder_path : FolderPathType
        The output folder for the NWB files.
    dataset_mode : Literal["embargo", "public"]
        The mode of the dataset, for the public mode only GPi channels are kept.
    verbose: bool, default: True
        Controls verbosity, default is True.
    """

    # Specify source data (note this assumes the files are arranged in the same way as in the example data)
    source_data_spec = {
        "recording": {
            "base_directory": folder_path,
            "file_path": "{subject_id}/{date_string}/Gaia_{session_id}.Tbk",
        }
    }

    # Instantiate LocalPathExpander
    path_expander = LocalPathExpander()

    # Expand paths and extract metadata
    metadata_list = path_expander.expand_paths(source_data_spec)

    assert dataset_mode in [
        "embargo",
        "public",
    ], f"Dataset mode must be one of ['embargo', 'public'], not {dataset_mode}."

    # For public dataset only keep GPi channels
    location = "GPi" if dataset_mode == "public" else None

    progress_bar = tqdm(
        enumerate(metadata_list),
        desc=f"Converting {len(metadata_list)} sessions in {dataset_mode} mode",
        position=0,
        total=len(metadata_list),
    )
    for index, metadata in progress_bar:
        subject_id = metadata["metadata"]["Subject"]["subject_id"]
        session_id = metadata["metadata"]["NWBFile"]["session_id"]

        # Load electrode metadata for the session
        session_metadata = load_session_metadata(file_path=data_list_file_path, session_id=session_id)

        # TODO: remove this once the electrode metadata is available for all sessions
        if session_metadata.empty:
            if verbose:
                print("\nSkipping session {} because no electrode metadata was found.".format(session_id))
            continue
        channel_ids = session_metadata.groupby("Target")["Chan#"].apply(list).to_dict()

        # Skip sessions that do not have the specified location
        if location is not None and location not in channel_ids:
            continue

        vl_plexon_file_path = None
        vl_flt_file_path = None
        gpi_plexon_file_path = None
        gpi_flt_file_path = None

        # In embargo mode keep all channels
        date_string = metadata["metadata"]["extras"]["date_string"]
        session_folder_path = folder_path / subject_id / date_string
        if "VL" in channel_ids and dataset_mode == "embargo":
            vl_channels = "Chans_{}_{}".format(channel_ids["VL"][0], channel_ids["VL"][-1])
            vl_plexon_file_path = session_folder_path / f"{session_id}_{vl_channels}.plx"
            assert vl_plexon_file_path.exists(), f"The file {vl_plexon_file_path} does not exist."

            vl_flt_file_path = session_folder_path / f"{session_id}_{vl_channels}.flt.mat"
            assert vl_flt_file_path.exists(), f"The file {vl_flt_file_path} does not exist."

        if "GPi" in channel_ids:
            gpi_channels = "Chans_{}_{}".format(channel_ids["GPi"][0], channel_ids["GPi"][-1])
            gpi_plexon_file_path = session_folder_path / f"{session_id}_{gpi_channels}.plx"
            assert gpi_plexon_file_path.exists(), f"The file {gpi_plexon_file_path} does not exist."

            gpi_flt_file_path = session_folder_path / f"{session_id}_{gpi_channels}.flt.mat"
            assert gpi_flt_file_path.exists(), f"The file {gpi_flt_file_path} does not exist."

        events_file_path = session_folder_path / f"{session_id}.mat"
        # The mapping of the target identifiers to more descriptive names, e.g. 1: "Left", 3: "Right"
        target_name_mapping = {1: "Left", 3: "Right"}

        nwbfile_name = f"{subject_id}_{session_id}.nwb"
        if stub_test:
            nwbfile_name = f"stub_{subject_id}_{session_id}.nwb"
        nwbfile_path = str(output_folder_path / nwbfile_name)

        progress_bar.set_description(f"\nConverting session {session_id} of subject {subject_id}")
        session_to_nwb(
            tdt_tank_file_path=metadata["source_data"]["recording"]["file_path"],
            nwbfile_path=nwbfile_path,
            data_list_file_path=data_list_file_path,
            location=location,
            vl_plexon_file_path=vl_plexon_file_path,
            gpi_plexon_file_path=gpi_plexon_file_path,
            vl_flt_file_path=vl_flt_file_path,
            gpi_flt_file_path=gpi_flt_file_path,
            session_id=session_id,
            subject_id=subject_id,
            events_file_path=events_file_path,
            target_name_mapping=target_name_mapping,
            stub_test=stub_test,
        )


if __name__ == "__main__":
    # Parameters for conversion
    # The root folder containing the sessions
    folder_path = Path("/Users/weian/data/pre_MPTP")

    # The path to the electrode metadata file (.xlsx)
    data_list_file_path = Path("/Volumes/t7-ssd/Turner/Previous_PD_Project_sample/Isis_DataList_temp.xlsx")

    # For public dataset mode we only keep GPi channels
    # Use dataset_mode="embargo" to keep all channels
    dataset_mode = "embargo"

    # The output folder for the NWB files
    output_folder_path = folder_path / f"nwbfiles_{dataset_mode}"
    os.makedirs(output_folder_path, exist_ok=True)

    convert_sessions(
        folder_path=folder_path,
        output_folder_path=output_folder_path,
        data_list_file_path=data_list_file_path,
        dataset_mode=dataset_mode,
        stub_test=False,
    )
