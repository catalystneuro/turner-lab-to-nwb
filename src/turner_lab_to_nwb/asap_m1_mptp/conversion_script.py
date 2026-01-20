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
    matlab_file_path: str,
    nwbfile_path: str,
    session_info_dict: dict,
    session_id: str,
    inter_trial_time_interval: float = 3.0,
    muscle_names: list = None,
    verbose: bool = False,
):
    """
    Convert a single Turner Lab MATLAB session to NWB format.

    Parameters
    ----------
    matlab_file_path : str
        Path to the MATLAB .mat file
    nwbfile_path : str
        Path where to save the NWB file
    session_info_dict : dict
        Structured session metadata containing:
        - 'session_info': Dict with session-level data (Animal, MPTP, DateCollected,
          stereotactic coordinates A_P/M_L, Depth, etc.)
        - 'units': List of unit-specific metadata dicts (UnitNum1, Antidrom, etc.)
    session_id : str
        Unique identifier for this session
    inter_trial_time_interval : float, optional
        Time interval between trials in seconds, by default 3.0
    muscle_names : list, optional
        List of muscle names for EMG channels, by default None
    verbose : bool, optional
        Whether to print verbose output, by default False
    """
    if not matlab_file_path.exists():
        raise FileNotFoundError(f"MATLAB file not found: {matlab_file_path}")

    # Extract session-level info
    session_info = session_info_dict["session_info"]

    # Create interfaces
    # Electrodes interface must be first to set up electrode table
    electrodes_interface = M1MPTPElectrodesInterface(
        file_path=matlab_file_path,
        session_metadata=session_info_dict["units"],
        verbose=verbose,
    )
    spike_interface = M1MPTPSpikeTimesInterface(
        file_path=matlab_file_path,
        session_metadata=session_info_dict["units"],
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    # Specialized interfaces for different analog data types
    manipulandum_interface = M1MPTPManipulandumInterface(
        file_path=matlab_file_path,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    lfp_interface = M1MPTPLFPInterface(
        file_path=matlab_file_path,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    emg_interface = M1MPTPEMGInterface(
        file_path=matlab_file_path,
        inter_trial_time_interval=inter_trial_time_interval,
        muscle_names=muscle_names,
        verbose=verbose,
    )
    trials_interface = M1MPTPTrialsInterface(
        file_path=matlab_file_path,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    antidromic_interface = M1MPTPAntidromicStimulationInterface(
        file_path=matlab_file_path,
        session_metadata=session_info_dict["units"],
        antidromic_exploration_offset=4000.0,  # Place antidromic data 4000s after trial start
        inter_sweep_interval=0.1,  # 100ms between sweeps
        verbose=verbose,
    )

    # Load base metadata from YAML file
    metadata_file = Path(__file__).parent / "metadata.yaml"
    general_metadata = load_dict_from_file(metadata_file)

    # Update metadata with session-specific information
    cell_types = [unit["Antidrom"] for unit in session_info_dict["units"]]
    general_metadata["NWBFile"]["session_id"] = session_id
    general_metadata["NWBFile"][
        "session_description"
    ] += f" MPTP condition: {session_info['MPTP']}. Cell types: {', '.join(cell_types)}."
    general_metadata["Subject"]["subject_id"] = session_info["Animal"]
    general_metadata["Subject"][
        "description"
    ] = f"MPTP-treated parkinsonian macaque monkey. Recording date: {session_info['DateCollected']}. Stereotactic coordinates: A/P={session_info['A_P']}mm, M/L={session_info['M_L']}mm, Depth={session_info['Depth']}mm."

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
    nwbfile.notes = (
        "Temporal data limitation: Recording dates are accurate from experimental logs, "
        "but precise session start times within each day are not available in source data. "
        "session_start_time is set to midnight (Pittsburgh timezone) with 2-hour systematic "
        "offsets for multiple sessions recorded on the same date, ordered by file sequence. "
        "Trial durations and within-trial event times are derived from experimental data. "
        "However, actual inter-trial intervals are not available in source data - trials "
        "are separated by fixed 3-second gaps for temporal organization. The gaps between "
        "trials should not be interpreted as actual behavioral inter-trial timing."
    )

    configure_and_write_nwbfile(nwbfile=nwbfile, nwbfile_path=nwbfile_path)

    if verbose:
        print(f"Successfully converted {matlab_file_path} to {nwbfile_path}")


if __name__ == "__main__":
    # Configuration
    base_data_path = Path("/home/heberto/data/turner/new_turner/")
    root_folder_path = Path(__file__).parent.parent.parent.parent
    output_folder = root_folder_path / "nwbfiles"
    inter_trial_time_interval = 3.0  # seconds
    stub_test = False  # Set to True to convert only 5 sessions for testing
    verbose = False  # Set to True to print progress information

    # Load metadata table
    conversion_folder_path = root_folder_path / "src" / "turner_lab_to_nwb" / "asap_m1_mptp"
    assets_folder_path = conversion_folder_path / "assets"
    metadata_table_path = assets_folder_path / "metadata_table" / "ven_table.csv"
    metadata_df = pd.read_csv(metadata_table_path)

    # EMG muscle column names for extracting channel mapping
    emg_muscle_columns = ["emg_muscle_1", "emg_muscle_2", "emg_muscle_3", "emg_muscle_4", "emg_muscle_5", "emg_muscle_6"]

    # Create output directory if needed
    output_folder.mkdir(parents=True, exist_ok=True)

    # Group metadata by file base (FName1) - each represents one recording session
    # The spike interface will automatically discover all units (.1.mat, .2.mat) per session
    session_groups = metadata_df.groupby(["FName1"])

    # Convert groups to list for easier handling
    sessions_to_convert = [(name, group) for name, group in session_groups]

    # Limit to 5 sessions for testing if stub_test is True
    if stub_test:
        sessions_to_convert = sessions_to_convert[:5]

    if verbose:
        print(f"Converting {len(sessions_to_convert)} sessions...")

    # Convert all sessions
    for (fname,), session_group in tqdm(sessions_to_convert, desc="Converting sessions"):
        # Use first row for session-level info (prioritize rows with complete metadata)
        complete_rows = session_group.dropna(subset=["A_P", "M_L", "Depth"])
        if len(complete_rows) > 0:
            primary_unit = complete_rows.iloc[0]
        else:
            primary_unit = session_group.iloc[0]

        # Create structured session metadata dictionary
        session_info_dict = {
            "session_info": {
                "Animal": primary_unit["Animal"],
                "MPTP": primary_unit["MPTP"],
                "DateCollected": primary_unit["DateCollected"],
                "FName1": fname,
                "A_P": primary_unit["A_P"],
                "M_L": primary_unit["M_L"],
                "Depth": primary_unit["Depth"],
            },
            "units": [row.to_dict() for _, row in session_group.iterrows()],
        }

        # Construct session ID using format: {subject}++{PreMPTP|PostMPTP}++Depth{depth_um}um++{YearMonthDay}
        # Convert date from "06-Apr-1999" to "19990406" format, use "NA" for missing dates
        if primary_unit["DateCollected"] == "NaT" or pd.isna(primary_unit["DateCollected"]):
            formatted_date = "NA"
            print(f"Warning: {fname} has missing date, using NA in session_id")
        else:
            date_obj = datetime.strptime(primary_unit["DateCollected"], "%d-%b-%Y")
            formatted_date = date_obj.strftime("%Y%m%d")

        # Convert depth to micrometers to avoid decimals in session_id
        depth_um = int(primary_unit['Depth'] * 1000)  # Convert mm to μm
        depth_str = f"{depth_um}um"

        # Extract filename code from fname, preserving full code including "b" suffix
        # Example: "v5811" -> "5811", "v0502" -> "0502", "v3607b" -> "3607b"
        filename_code = fname[1:]  # All characters after 'v' prefix
        
        # Create session ID with subject and filename code combined
        mptp_condition = f"{primary_unit['MPTP']}MPTP"
        session_id = f"{primary_unit['Animal']}{filename_code}++{mptp_condition}++Depth{depth_str}++{formatted_date}"

        # Use first unit file as base (interface will discover other units automatically)
        first_unit_num = primary_unit["UnitNum1"]
        matlab_file_path = base_data_path / f"{fname}.{int(first_unit_num)}.mat"

        # Construct output path
        nwbfile_path = output_folder / f"{session_id}.nwb"

        # Extract EMG muscle names from metadata (filter out NaN values)
        muscle_names = [
            primary_unit[col] if pd.notna(primary_unit.get(col)) else None
            for col in emg_muscle_columns
        ]
        # Remove trailing None values
        while muscle_names and muscle_names[-1] is None:
            muscle_names.pop()

        # Convert session
        convert_session_to_nwbfile(
            matlab_file_path,
            nwbfile_path,
            session_info_dict,
            session_id,
            inter_trial_time_interval,
            muscle_names=muscle_names if muscle_names else None,
            verbose=verbose,
        )

    if verbose:
        print(f"Conversion complete! Files saved to {output_folder}")
