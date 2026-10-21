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
from neuroconv.tools import configure_and_write_nwbfile
from neuroconv import ConverterPipe

from turner_lab_to_nwb.asap_m1_mptp.session_plan import plan_sessions
from turner_lab_to_nwb.asap_m1_mptp.interfaces import (
    M1MPTPElectrodesInterface,
    M1MPTPSpikeTimesInterface,
    M1MPTPManipulandumInterface,
    M1MPTPLFPInterface,
    M1MPTPEMGInterface,
    M1MPTPTrialsInterface,
    M1MPTPAntidromicStimulationInterface,
)


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

    Parameters
    ----------
    session_plan : dict
        One session from session_plan.plan_sessions: its trials as (MATLAB file, trial index) pairs,
        its units, its electrode locations, notes, and the primary unit row used for session-level
        metadata (Animal, MPTP, DateCollected, ...). Also "subject_metadata_file", the monkey's YAML.
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
    # Extract session-level info
    primary_unit = session_plan["primary_unit"]
    session_info = {key: primary_unit[key] for key in ("Animal", "MPTP", "DateCollected", "A_P", "M_L", "Depth")}
    joint = {"V": "elbow", "L": "wrist"}[session_info["Animal"]]
    trial_sources = session_plan["trial_sources"]

    # Create interfaces
    # Electrodes interface must be first to set up electrode table
    electrodes_interface = M1MPTPElectrodesInterface(
        electrode_locations=session_plan["electrode_locations"],
        verbose=verbose,
    )
    spike_interface = M1MPTPSpikeTimesInterface(
        units=session_plan["units"],
        trial_sources=trial_sources,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    # Specialized interfaces for different analog data types
    manipulandum_interface = M1MPTPManipulandumInterface(
        trial_sources=trial_sources,
        joint=joint,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    lfp_interface = M1MPTPLFPInterface(
        trial_sources=trial_sources,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    emg_interface = M1MPTPEMGInterface(
        trial_sources=trial_sources,
        inter_trial_time_interval=inter_trial_time_interval,
        muscle_names=muscle_names,
        verbose=verbose,
    )
    trials_interface = M1MPTPTrialsInterface(
        trial_sources=trial_sources,
        trial_files=session_plan["trial_files"],
        joint=joint,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    antidromic_interface = M1MPTPAntidromicStimulationInterface(
        units=session_plan["units"],
        animal=session_info["Animal"],
        antidromic_exploration_offset=4000.0,  # Place antidromic data 4000s after trial start
        verbose=verbose,
    )

    # Load base metadata from YAML file
    metadata_file = Path(__file__).parent / "metadata.yaml"
    general_metadata = load_dict_from_file(metadata_file)

    # Load subject-specific metadata override if provided
    subject_metadata_file = session_plan.get("subject_metadata_file")
    if subject_metadata_file:
        subject_override = load_dict_from_file(Path(subject_metadata_file))
        general_metadata = dict_deep_update(general_metadata, subject_override)
        # Remove fields marked with __REMOVE__ (used to clear inherited values)
        for section in general_metadata.values():
            if isinstance(section, dict):
                keys_to_remove = [k for k, v in section.items() if v == "__REMOVE__"]
                for k in keys_to_remove:
                    del section[k]

    # Update metadata with session-specific information
    cell_types = [unit["metadata"]["Antidrom"] for unit in session_plan["units"]]
    general_metadata["NWBFile"]["session_id"] = session_id
    general_metadata["NWBFile"][
        "session_description"
    ] += f" MPTP condition: {session_info['MPTP']}. Cell types: {', '.join(cell_types)}."
    subject_name_map = {"V": "Venus", "L": "Leu"}
    general_metadata["Subject"]["subject_id"] = subject_name_map.get(session_info["Animal"], session_info["Animal"])

    # Add session-specific MPTP status to pharmacology field
    mptp_condition = session_info["MPTP"]
    if mptp_condition == "Pre":
        general_metadata["NWBFile"]["pharmacology"] += (
            "\n\nSession-specific information: This recording was obtained BEFORE MPTP administration (baseline control condition)."
        )
    elif mptp_condition == "Post":
        general_metadata["NWBFile"]["pharmacology"] += (
            "\n\nSession-specific information: This recording was obtained AFTER MPTP administration (parkinsonian condition)."
        )

    data_interfaces = {
        "electrodes": electrodes_interface,
        "spike": spike_interface,
        "manipulandum": manipulandum_interface,
        "lfp": lfp_interface,
        "emg": emg_interface,
        "trials": trials_interface,
        "antidromic": antidromic_interface
    }
    converter = ConverterPipe(data_interfaces=data_interfaces)

    # Get base metadata from interface and merge with YAML
    # Note: dict_deep_update(a, b) updates a with b, so put converter_metadata first
    # so that general_metadata (with our session-specific values) takes precedence
    converter_metadata = converter.get_metadata()
    metadata = dict_deep_update(converter_metadata, general_metadata)

    # Set session_start_time using actual recording date at midnight with Pittsburgh timezone
    pittsburgh_tz = ZoneInfo("America/New_York")  # Turner Lab - University of Pittsburgh
    if session_info["DateCollected"] == "NaT" or pd.isna(session_info["DateCollected"]):
        # Use Jan 1st of appropriate year as default: 1999 for Pre, 2000 for Post
        default_year = 1999 if session_info["MPTP"] == "Pre" else 2000
        session_start_time = datetime(default_year, 1, 1, 0, 0, 0, tzinfo=pittsburgh_tz)
    else:
        recording_date = datetime.strptime(session_info["DateCollected"], "%d-%b-%Y")
        session_start_time = datetime(
            recording_date.year,
            recording_date.month,
            recording_date.day,
            0,
            0,
            0,
            tzinfo=pittsburgh_tz,
        )
    metadata["NWBFile"]["session_start_time"] = session_start_time

    # Create NWB file - spike interface will add electrode table and units
    nwbfile = converter.create_nwbfile(metadata=metadata)

    # Add temporal data limitation documentation
    notes_parts = []

    # Annotate missing analog data at the top if applicable
    if getattr(manipulandum_interface, "analog_data_missing", False):
        notes_parts.append(
            "MISSING ANALOG DATA: This session has no manipulandum angle, velocity, or torque data "
            "due to an A/D converter malfunction that corrupted the analog recording channel. "
            "The malfunction produced a completely flat signal. Spike times, trial events, and "
            "antidromic stimulation data (if any) are unaffected."
        )

    if trials_interface.target_amplitude_mismatch_files:
        notes_parts.append(
            "TARGET AMPLITUDE NOT AVAILABLE: target_amplitude_degrees is NaN for the trials of "
            f"{', '.join(trials_interface.target_amplitude_mismatch_files)}. The target list in the source file "
            "does not line up with the recorded trials: the target sizes it gives disagree with the measured "
            "movement amplitudes (derived_movement_amplitude), so they are left out. The movement amplitudes "
            "and all other trial values are unaffected."
        )

    # Session-specific notes from planning (merged files, duplicated units)
    notes_parts.extend(session_plan["notes"])

    notes_parts.append(
        "TEMPORAL DATA STRUCTURE: This dataset was converted from trialized MATLAB files "
        "where all timestamps were relative to individual trial starts. Inter-trial intervals "
        "were NOT recorded in the source data."
    )
    notes_parts.append(
        "SESSION TIMING: Recording dates are accurate from experimental logs, but precise "
        "session start times within each day are not available. session_start_time is set to "
        "midnight (Pittsburgh timezone) for every session, including sessions recorded on the same "
        "date."
    )
    notes_parts.append(
        "ARTIFICIAL GAPS: Trials are separated by fixed 3-second gaps for temporal organization. "
        "These gaps are placeholders and should NOT be interpreted as actual behavioral timing."
    )
    notes_parts.append(
        "DATA VALIDITY ANNOTATIONS:\n"
        "1. invalid_times table: Lists all inter-trial gaps (tagged 'artificial_inter_trial_gap'). "
        "Use this to exclude gap periods from continuous data analysis (LFP, EMG, kinematics).\n"
        "2. Units obs_intervals: Each unit has observation intervals specifying when it was recorded. "
        "Spikes only occurred during these intervals; gaps represent 'not observable', not 'silent'."
    )
    notes_parts.append(
        "ANALOG vs TRIAL TIMING: Analog data (manipulandum, EMG, LFP) end a few milliseconds before "
        "the trial stop_time (5 to 6 ms in monkey V, 15 to 24 ms in monkey L, whose analog data are "
        "sampled every 10 ms) because the analog recorder stopped slightly before the behavioral "
        "software marked the trial as ended. Some spikes can occur in this gap. Trial boundaries "
        "(start_time, stop_time, obs_intervals, invalid_times) use the authoritative Events.end "
        "timestamp, not analog data length."
    )

    nwbfile.notes = "\n\n".join(notes_parts)

    configure_and_write_nwbfile(nwbfile=nwbfile, nwbfile_path=nwbfile_path)

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
            "subject_metadata_file": None,  # Uses default metadata.yaml
            "emg_muscle_columns": [
                "emg_muscle_1", "emg_muscle_2", "emg_muscle_3",
                "emg_muscle_4", "emg_muscle_5", "emg_muscle_6",
            ],
        },
        "L": {
            "table_path": assets_folder_path / "metadata_table" / "leu_table.csv",
            "data_path": Path("/home/heberto/data/turner/leu_data/"),
            "subject_metadata_file": conversion_folder_path / "metadata_leu.yaml",
            "emg_muscle_columns": [],  # Leu has no EMG
        },
    }

    # Select which monkeys to convert (change to ["V"] or ["L"] for single monkey)
    monkeys_to_convert = ["V", "L"]

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
            session_plan["subject_metadata_file"] = config["subject_metadata_file"]

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
            subject_name_map = {"V": "Venus", "L": "Leu"}
            subject_name = subject_name_map.get(primary_unit["Animal"], primary_unit["Animal"])
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
