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
    session_metadata: dict,
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
    session_metadata : dict
        Session-specific metadata from the metadata table
    inter_trial_time_interval : float, optional
        Time interval between trials in seconds, by default 3.0
    verbose : bool, optional
        Whether to print verbose output, by default False
    """
    # Create interfaces
    spike_interface = M1MPTPSpikeTimesInterface(
        file_path=matlab_file_path,
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
    general_metadata['NWBFile']['session_description'] += f" MPTP condition: {session_metadata['MPTP']}. Cell type: {session_metadata['Antidrom']}."
    general_metadata['Subject']['subject_id'] = f"monkey_{session_metadata['Animal']}"
    general_metadata['Subject']['description'] = f"MPTP-treated parkinsonian macaque monkey. Recording date: {session_metadata['DateCollected']}"

    data_interfaces = {"spike": spike_interface, "analog": analog_interface, "trials": trials_interface}
    converter = ConverterPipe(data_interfaces=data_interfaces)

    # Get base metadata from interface and merge with YAML
    converter_metadata = converter.get_metadata()
    metadata = dict_deep_update(general_metadata, converter_metadata)

    # Set placeholder session_start_time with Pittsburgh timezone (Turner Lab - University of Pittsburgh)
    pittsburgh_tz = ZoneInfo("America/New_York")  # Pittsburgh is in Eastern Time
    placeholder_date = datetime(1900, 1, 1, 0, 0, 0, tzinfo=pittsburgh_tz)
    metadata["NWBFile"]["session_start_time"] = placeholder_date

    # Create NWB file with spike data first
    nwbfile = converter.create_nwbfile(metadata=metadata)

    configure_and_write_nwbfile(nwbfile=nwbfile, nwbfile_path=nwbfile_path)

    if verbose:
        print(f"Successfully converted {matlab_file_path} to {nwbfile_path}")


if __name__ == "__main__":
    # Configuration
    base_data_path = Path("/home/heberto/data/turner/Ven_All/")
    output_folder = Path("/home/heberto/development/turner-lab-to-nwb/nwbfiles/")
    inter_trial_time_interval = 3.0  # seconds
    stub_test = True  # Set to True to convert only 5 sessions for testing

    # Load metadata table
    metadata_table_path = Path(__file__).parent / "assets" / "metadata_table" / "ven_table.csv"
    metadata_df = pd.read_csv(metadata_table_path)
    
    # Create output directory if needed
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Get unique filenames (some files have multiple units, we want each unique file)
    unique_filenames = metadata_df['FName1'].unique()
    
    # Limit to 5 files for testing if stub_test is True
    if stub_test:
        unique_filenames = unique_filenames[:5]
    
    print(f"Converting {len(unique_filenames)} sessions...")
    
    # Convert all sessions
    for filename_base in tqdm(unique_filenames, desc="Converting sessions"):
        # Get metadata for this file (take first row if multiple units per file)
        session_metadata_row = metadata_df[metadata_df['FName1'] == filename_base].iloc[0]
        session_metadata = session_metadata_row.to_dict()
        
        # Construct session ID and file paths
        session_id = f"{session_metadata['Animal']}_{session_metadata['MPTP']}_{filename_base}"
        
        # Determine unit number from metadata (UnitNum1 is always present, UnitNum2 may be NaN)
        unit_num = session_metadata['UnitNum1']  # Use first unit for this filename
        
        # Construct MATLAB file path with appropriate unit number
        matlab_file_path = base_data_path / f"{filename_base}.{int(unit_num)}.mat"
        
        if not matlab_file_path.exists():
            raise FileNotFoundError(f"MATLAB file not found: {matlab_file_path}")
        
        # Construct output path
        nwbfile_path = output_folder / f"{session_id}.nwb"
        
        # Convert session
        convert_session_to_nwbfile(
            str(matlab_file_path), 
            str(nwbfile_path), 
            session_metadata, 
            inter_trial_time_interval, 
            verbose=False
        )
    
    print(f"Conversion complete! Files saved to {output_folder}")
