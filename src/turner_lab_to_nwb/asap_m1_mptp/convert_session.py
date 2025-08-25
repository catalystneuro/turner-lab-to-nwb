import argparse
from pathlib import Path

from neuroconv.utils import load_dict_from_file, dict_deep_update
from neuroconv.tools import configure_and_write_nwbfile
from neuroconv import ConverterPipe

from turner_lab_to_nwb.asap_m1_mptp.interfaces import M1MPTPSpikeTimesInterface, M1MPTPAnalogKinematicsInterface


def convert_session_to_nwb(matlab_file_path: str, nwbfile_path: str, cell_type: str = "unknown", inter_trial_time_interval: float = 3.0):
    """
    Convert a single Turner Lab MATLAB session to NWB format.
    
    Parameters
    ----------
    matlab_file_path : str
        Path to the MATLAB .mat file
    nwbfile_path : str
        Path where to save the NWB file
    cell_type : str, optional
        Cell type classification ("PTN", "CSN", or "unknown"), by default "unknown"
    inter_trial_time_interval : float, optional
        Time interval between trials in seconds, by default 3.0
    """
    # Create interfaces
    spike_interface = M1MPTPSpikeTimesInterface(file_path=matlab_file_path, inter_trial_time_interval=inter_trial_time_interval, verbose=True)
    analog_interface = M1MPTPAnalogKinematicsInterface(file_path=matlab_file_path, inter_trial_time_interval=inter_trial_time_interval, verbose=True)
    
    # Load metadata from YAML file
    metadata_file = Path(__file__).parent / "metadata.yaml"
    general_metadata = load_dict_from_file(metadata_file)

    data_interfaces = {"spike": spike_interface, "analog": analog_interface}
    converter = ConverterPipe(data_interfaces=data_interfaces)

    # Get base metadata from interface and merge with YAML
    converter_metadata = converter.get_metadata()
    metadata = dict_deep_update(general_metadata, converter_metadata)

    # Create NWB file with spike data first
    nwbfile = converter.create_nwbfile(metadata=metadata)
    
    configure_and_write_nwbfile(nwbfile=nwbfile, nwbfile_path=nwbfile_path)
    
    print(f"Successfully converted {matlab_file_path} to {nwbfile_path}")


if __name__ == "__main__":
    # Fixed inter-trial time interval
    INTER_TRIAL_TIME_INTERVAL = 3.0  # seconds
    
    parser = argparse.ArgumentParser(description="Convert Turner Lab M1 MPTP session to NWB")
    parser.add_argument("matlab_file", help="Path to the MATLAB .mat file")
    parser.add_argument("output_nwb", help="Path for output NWB file")
    parser.add_argument("--cell-type", choices=["PTN", "CSN", "unknown"], 
                       default="unknown", help="Cell type classification")
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not Path(args.matlab_file).exists():
        raise FileNotFoundError(f"MATLAB file not found: {args.matlab_file}")
    
    # Create output directory if needed
    Path(args.output_nwb).parent.mkdir(parents=True, exist_ok=True)
    
    # Convert session
    convert_session_to_nwb(args.matlab_file, args.output_nwb, args.cell_type, INTER_TRIAL_TIME_INTERVAL)