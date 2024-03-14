import os
import warnings
from pathlib import Path

from neuroconv.utils import FolderPathType, FilePathType
from tqdm import tqdm

from turner_lab_to_nwb.asap_tdt.asap_tdt_convert_session import session_to_nwb
from turner_lab_to_nwb.asap_tdt.utils import load_session_metadata

warnings.filterwarnings("ignore", "Could not identify sev files for channels")
warnings.filterwarnings(
    "ignore",
    r"Complex objects \(like classes\) are not supported\. They are imported on a best effort base but your mileage will vary\.",
)


def convert_sessions(
    folder_path: FolderPathType,
    data_list_file_path: FilePathType,
    output_folder_path: FolderPathType,
    gpi_only: bool = False,
    overwrite: bool = False,
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
    gpi_only : bool, default: False
        Whether to convert only the GPI sessions, default is False.
    overwrite : bool, default: False
        Whether to overwrite the NWB files if they already exist, default is False.
    verbose: bool, default: True
        Controls verbosity, default is True.
    """

    folder_path = Path(folder_path)
    tdt_tank_file_paths = list(folder_path.rglob("*.Tbk"))

    # The mapping of the target identifiers to more descriptive names, e.g. 1: "Left", 3: "Right"
    target_name_mapping = {1: "Left", 3: "Right"}

    sessions_metadata = load_session_metadata(data_list_file_path)
    # filter the sessions based on the target
    sessions_metadata = sessions_metadata[sessions_metadata["Target"].str.contains("GP") == gpi_only]
    # filter out NaN values
    sessions_metadata = sessions_metadata[sessions_metadata["Target"] != "NaN"]
    progress_bar = tqdm(
        enumerate(tdt_tank_file_paths),
        desc=f"Converting {len(tdt_tank_file_paths)} sessions",
        position=0,
        total=len(tdt_tank_file_paths),
    )

    for tank_file_ind, tdt_tank_file_path in progress_bar:
        tdt_tank_file_name = tdt_tank_file_path.stem

        subject_id = "Isis" if "I" in tdt_tank_file_name.split("_") else "Gaia"
        session_id = tdt_tank_file_path.stem.replace("Gaia_", "")

        session_metadata = sessions_metadata[sessions_metadata["Filename"] == session_id]
        if session_metadata.empty:
            print(f"Session {session_id} of subject {subject_id} is skipped because of empty metadata ...")
            continue

        nwbfile_name = f"{subject_id}_{session_id}.nwb"
        if stub_test:
            nwbfile_name = f"stub_{subject_id}_{session_id}.nwb"
        nwbfile_path = Path(output_folder_path) / nwbfile_name
        if nwbfile_path.exists() and not overwrite:
            print(f"Session {session_id} of subject {subject_id} is skipped because the NWB file already exists ...")
            continue

        # find the files
        events_file_paths = list(tdt_tank_file_path.parent.glob(f"{session_id}.mat"))
        if not events_file_paths:
            raise FileNotFoundError(f"No events file found for session {session_id} of subject {subject_id}.")
        events_file_path = str(events_file_paths[0])

        flt_file_paths = list(tdt_tank_file_path.parent.glob(f"{session_id}_Chans*.flt.mat"))
        if not flt_file_paths:
            flt_file_paths = list(tdt_tank_file_path.parent.glob(f"{session_id}.flt.mat"))
            if not flt_file_paths:
                print(f"No flt file found for session {session_id} of subject {subject_id}.")
                flt_file_paths = None

        plexon_file_paths = list(tdt_tank_file_path.parent.glob(f"{session_id}_Chans*.plx"))
        if not plexon_file_paths:
            plexon_file_paths = list(tdt_tank_file_path.parent.glob(f"{session_id}.plx"))
            if not plexon_file_paths:
                print(f"No plexon file found for session {session_id} of subject {subject_id}.")
                plexon_file_paths = None

        progress_bar.set_description(f"\nConverting session {session_id} of subject {subject_id}")

        session_to_nwb(
            nwbfile_path=str(nwbfile_path),
            tdt_tank_file_path=str(tdt_tank_file_path),
            subject_id=subject_id,
            session_id=session_id,
            session_metadata=session_metadata,
            events_file_path=events_file_path,
            gpi_only=gpi_only,
            flt_file_path=flt_file_paths,
            plexon_file_path=plexon_file_paths,
            target_name_mapping=target_name_mapping,
            stub_test=stub_test,
            verbose=verbose,
        )


if __name__ == "__main__":
    # Parameters for conversion
    # The root folder containing the sessions
    folder_path = Path("/Volumes/LaCie/CN_GCP/Turner/Previous_PD_Project_Sample/pre_MPTP/Isis")

    # The path to the electrode metadata file (.xlsx)
    data_list_file_path = Path("/Users/weian/data/Data_list/DataList.xlsx")

    # The output folder for the NWB files
    output_folder_path = Path("/Volumes/LaCie/CN_GCP/Turner/nwbfiles_public")
    os.makedirs(output_folder_path, exist_ok=True)

    convert_sessions(
        folder_path=folder_path,
        output_folder_path=output_folder_path,
        data_list_file_path=data_list_file_path,
        gpi_only=True,
        stub_test=True,
        verbose=False,
    )
