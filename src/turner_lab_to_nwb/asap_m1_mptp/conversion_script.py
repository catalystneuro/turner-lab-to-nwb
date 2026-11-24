# import argparse
import warnings
from pathlib import Path
import pandas as pd
from zoneinfo import ZoneInfo
from datetime import datetime
from tqdm import tqdm

# Suppress pymatreader warning about MATLAB string variables - we handle this
# via custom extraction in assets/matlab_utilities/extract_matlab_strings.py
warnings.filterwarnings(
    "ignore",
    message="pymatreader cannot import Matlab string variables",
    category=UserWarning,
)

from neuroconv.utils import load_dict_from_file, dict_deep_update

from turner_lab_to_nwb.asap_m1_mptp.nwbconverter import M1MPTPNWBConverter
from turner_lab_to_nwb.asap_m1_mptp.session_plan import plan_sessions

METADATA_PATH = Path(__file__).parent / "metadata.yaml"
PITTSBURGH_TIMEZONE = ZoneInfo("America/New_York")


def get_session_start_time(primary_unit: dict) -> datetime:
    """Midnight of the recording day in Pittsburgh; the source has no time of day."""
    if primary_unit["DateCollected"] == "NaT" or pd.isna(primary_unit["DateCollected"]):
        # Jan 1st of the year of the condition: 1999 before MPTP, 2000 after
        return datetime(1999 if primary_unit["MPTP"] == "Pre" else 2000, 1, 1, tzinfo=PITTSBURGH_TIMEZONE)
    recording_date = datetime.strptime(primary_unit["DateCollected"], "%d-%b-%Y")
    return datetime(recording_date.year, recording_date.month, recording_date.day, tzinfo=PITTSBURGH_TIMEZONE)


def convert_session_to_nwbfile(
    session_plan: dict,
    nwbfile_path: str | Path,
    session_id: str,
    inter_trial_time_interval: float = 3.0,
    muscle_names: list | None = None,
    verbose: bool = False,
):
    """
    Convert a single Turner Lab session to NWB format.

    Every text written comes from metadata.yaml: the shared sections, with the section of the session's monkey
    (Monkeys) merged over them and the session's own values (Session) filled in.

    Parameters
    ----------
    session_plan : dict
        One session from session_plan.plan_sessions: its trials as (MATLAB file, trial index) pairs, its units, its
        electrode locations, notes, and the primary unit row used for session-level metadata (Animal, MPTP,
        DateCollected, ...)
    nwbfile_path : str
        Path where to save the NWB file
    session_id : str
        Unique identifier for this session
    inter_trial_time_interval : float, optional
        Time interval between trials in seconds, by default 3.0
    muscle_names : list, optional
        List of muscle names for EMG channels, by default None
    verbose : bool, optional
        Whether to print verbose output, by default False
    """
    primary_unit = session_plan["primary_unit"]
    dataset_metadata = load_dict_from_file(METADATA_PATH)
    monkey_metadata = dataset_metadata.pop("Monkeys")[primary_unit["Animal"]]
    session_text = dataset_metadata.pop("Session")
    joint = monkey_metadata.pop("joint")

    converter = M1MPTPNWBConverter(
        session_plan=session_plan,
        joint=joint,
        muscle_names=muscle_names,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )

    # Note: dict_deep_update(a, b) updates a with b, so the converter's defaults come first
    metadata = dict_deep_update(converter.get_metadata(), dataset_metadata)
    metadata = dict_deep_update(metadata, monkey_metadata)

    cell_types = [unit["metadata"]["Antidrom"] for unit in session_plan["units"]]
    metadata["NWBFile"]["session_id"] = session_id
    metadata["NWBFile"]["session_description"] += session_text["session_description_suffix"].format(
        mptp=primary_unit["MPTP"], cell_types=", ".join(cell_types)
    )
    metadata["NWBFile"]["pharmacology"] += session_text["pharmacology_suffix"].get(primary_unit["MPTP"], "")
    metadata["NWBFile"]["session_start_time"] = get_session_start_time(primary_unit)

    notes = session_text["notes"]
    notes_parts = []
    if converter.data_interface_objects["manipulandum"].analog_data_missing:
        notes_parts.append(notes["missing_analog_data"])
    target_amplitude_mismatch_files = converter.data_interface_objects["trials"].target_amplitude_mismatch_files
    if target_amplitude_mismatch_files:
        notes_parts.append(notes["target_amplitude_not_available"].format(files=", ".join(target_amplitude_mismatch_files)))
    # Session-specific notes from planning (merged files, duplicated units)
    notes_parts.extend(session_plan["notes"])
    notes_parts.extend(notes["always"])
    metadata["NWBFile"]["notes"] = "\n\n".join(notes_parts)

    converter.run_conversion(nwbfile_path=nwbfile_path, metadata=metadata, overwrite=True)

    if verbose:
        print(f"Successfully converted {session_plan['fname']} to {nwbfile_path}")


if __name__ == "__main__":
    # Configuration
    root_folder_path = Path(__file__).parent.parent.parent.parent
    output_folder = root_folder_path / "nwbfiles"
    inter_trial_time_interval = 3.0  # seconds
    stub_test = False  # Set to True to convert only 5 sessions for testing
    verbose = False  # Set to True to print progress information

    conversion_folder_path = root_folder_path / "src" / "turner_lab_to_nwb" / "asap_m1_mptp"
    assets_folder_path = conversion_folder_path / "assets"

    # Per-monkey configuration
    monkey_configs = {
        "V": {
            "table_path": assets_folder_path / "metadata_table" / "ven_table.csv",
            "data_path": Path("/home/heberto/data/turner/ven_data/"),
            "emg_muscle_columns": [
                "emg_muscle_1", "emg_muscle_2", "emg_muscle_3",
                "emg_muscle_4", "emg_muscle_5", "emg_muscle_6",
            ],
        },
        "L": {
            "table_path": assets_folder_path / "metadata_table" / "leu_table.csv",
            "data_path": Path("/home/heberto/data/turner/leu_data/"),
            "emg_muscle_columns": [],  # Leu has no EMG
        },
    }

    # Select which monkeys to convert (change to ["V"] or ["L"] for single monkey)
    monkeys_to_convert = ["V", "L"]

    monkeys_metadata = load_dict_from_file(METADATA_PATH)["Monkeys"]
    subject_names = {monkey: monkeys_metadata[monkey]["Subject"]["subject_id"] for monkey in monkeys_metadata}

    # Create output directory if needed
    output_folder.mkdir(parents=True, exist_ok=True)

    for monkey_id in monkeys_to_convert:
        config = monkey_configs[monkey_id]
        print(f"\n--- Converting Monkey {monkey_id} ---")

        metadata_df = pd.read_csv(config["table_path"])

        # One session per group of files linked by a neuron recorded across them (see session_plan.py)
        sessions_to_convert = plan_sessions(metadata_df, config["data_path"])

        if stub_test:
            sessions_to_convert = sessions_to_convert[:5]

        if verbose:
            print(f"Converting {len(sessions_to_convert)} sessions...")

        for session_plan in tqdm(sessions_to_convert, desc=f"Monkey {monkey_id}"):
            fname = session_plan["fname"]
            primary_unit = session_plan["primary_unit"]

            # Construct session ID
            if primary_unit["DateCollected"] == "NaT" or pd.isna(primary_unit["DateCollected"]):
                formatted_date = "NA"
                print(f"Warning: {fname} has missing date, using NA in session_id")
            else:
                date_obj = datetime.strptime(primary_unit["DateCollected"], "%d-%b-%Y")
                formatted_date = date_obj.strftime("%Y%m%d")

            depth_um = int(primary_unit["Depth"] * 1000)
            depth_str = f"{depth_um}um"
            mptp_condition = f"{primary_unit['MPTP']}MPTP"
            subject_name = subject_names[primary_unit["Animal"]]
            session_id = f"{subject_name}++{fname}++{mptp_condition}++Depth{depth_str}++{formatted_date}"

            nwbfile_path = output_folder / f"{session_id}.nwb"

            # Extract EMG muscle names from metadata (Leu has no EMG columns)
            muscle_names = None
            if config["emg_muscle_columns"]:
                muscle_names = [
                    primary_unit[col] if pd.notna(primary_unit.get(col)) else None
                    for col in config["emg_muscle_columns"]
                ]
                while muscle_names and muscle_names[-1] is None:
                    muscle_names.pop()
                if not muscle_names:
                    muscle_names = None

            convert_session_to_nwbfile(
                session_plan,
                nwbfile_path,
                session_id,
                inter_trial_time_interval,
                muscle_names=muscle_names,
                verbose=verbose,
            )

        print(f"Monkey {monkey_id}: {len(sessions_to_convert)} sessions converted")

    print(f"\nConversion complete! Files saved to {output_folder}")
