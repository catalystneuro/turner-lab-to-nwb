# import argparse
from pathlib import Path
import pandas as pd
from zoneinfo import ZoneInfo
from datetime import datetime
from tqdm import tqdm

from neuroconv.utils import load_dict_from_file, dict_deep_update
from neuroconv.tools import configure_and_write_nwbfile
from neuroconv import ConverterPipe

from turner_lab_to_nwb.asap_m1_mptp.interfaces import (
    M1MPTPSpikeTimesInterface,
    M1MPTPAnalogKinematicsInterface,
    M1MPTPTrialsInterface,
)


def convert_session_to_nwbfile(
    matlab_file_path: str,
    nwbfile_path: str,
    session_info_dict: dict,
    inter_trial_time_interval: float = 3.0,
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
    inter_trial_time_interval : float, optional
        Time interval between trials in seconds, by default 3.0
    verbose : bool, optional
        Whether to print verbose output, by default False
    """
    if not matlab_file_path.exists():
        raise FileNotFoundError(f"MATLAB file not found: {matlab_file_path}")

    # Extract session-level info
    session_info = session_info_dict["session_info"]

    # Create interfaces
    spike_interface = M1MPTPSpikeTimesInterface(
        file_path=matlab_file_path,
        session_metadata=session_info_dict["units"],
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    analog_interface = M1MPTPAnalogKinematicsInterface(
        file_path=matlab_file_path,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )
    trials_interface = M1MPTPTrialsInterface(
        file_path=matlab_file_path,
        inter_trial_time_interval=inter_trial_time_interval,
        verbose=verbose,
    )

    # Load base metadata from YAML file
    metadata_file = Path(__file__).parent / "metadata.yaml"
    general_metadata = load_dict_from_file(metadata_file)

    # Update metadata with session-specific information
    cell_types = [unit["Antidrom"] for unit in session_info_dict["units"]]
    general_metadata["NWBFile"][
        "session_description"
    ] += f" MPTP condition: {session_info['MPTP']}. Cell types: {', '.join(cell_types)}."
    general_metadata["Subject"]["subject_id"] = session_info["Animal"]
    general_metadata["Subject"][
        "description"
    ] = f"MPTP-treated parkinsonian macaque monkey. Recording date: {session_info['DateCollected']}. Stereotactic coordinates: A/P={session_info['A_P']}mm, M/L={session_info['M_L']}mm, Depth={session_info['Depth']}mm."

    data_interfaces = {"spike": spike_interface, "analog": analog_interface, "trials": trials_interface}
    converter = ConverterPipe(data_interfaces=data_interfaces)

    # Get base metadata from interface and merge with YAML
    converter_metadata = converter.get_metadata()
    metadata = dict_deep_update(general_metadata, converter_metadata)

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

    configure_and_write_nwbfile(nwbfile=nwbfile, nwbfile_path=nwbfile_path)

    if verbose:
        print(f"Successfully converted {matlab_file_path} to {nwbfile_path}")


if __name__ == "__main__":
    # Configuration
    base_data_path = Path("/home/heberto/data/turner/Ven_All/")
    output_folder = Path("/home/heberto/development/turner-lab-to-nwb/nwbfiles/")
    inter_trial_time_interval = 3.0  # seconds
    stub_test = False  # Set to True to convert only 5 sessions for testing
    verbose = False  # Set to True to print progress information

    # Load metadata table
    metadata_table_path = Path(__file__).parent / "assets" / "metadata_table" / "ven_table.csv"
    metadata_df = pd.read_csv(metadata_table_path)

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

        # Construct session ID using format: {subject}++{PreMPTP|PostMPTP}++Depth{depth}++{YearMonthDay}
        # Convert date from "06-Apr-1999" to "19990406" format, use "NA" for missing dates
        if primary_unit["DateCollected"] == "NaT" or pd.isna(primary_unit["DateCollected"]):
            formatted_date = "NA"
            print(f"Warning: {fname} has missing date, using NA in session_id")
        else:
            date_obj = datetime.strptime(primary_unit["DateCollected"], "%d-%b-%Y")
            formatted_date = date_obj.strftime("%Y%m%d")

        # Format depth to 1 decimal place, replace dot with underscore for filename compatibility
        depth_str = f"{primary_unit['Depth']:.1f}mm".replace(".", "_")

        # Create session ID with your specified format
        mptp_condition = f"{primary_unit['MPTP']}MPTP"
        session_id = f"{primary_unit['Animal']}++{mptp_condition}++Depth{depth_str}++{formatted_date}"

        # Use first unit file as base (interface will discover other units automatically)
        first_unit_num = primary_unit["UnitNum1"]
        matlab_file_path = base_data_path / f"{fname}.{int(first_unit_num)}.mat"

        # Construct output path
        nwbfile_path = output_folder / f"{session_id}.nwb"

        # Convert session
        convert_session_to_nwbfile(
            matlab_file_path, nwbfile_path, session_info_dict, inter_trial_time_interval, verbose=verbose
        )

    if verbose:
        print(f"Conversion complete! Files saved to {output_folder}")
