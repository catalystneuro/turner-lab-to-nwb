from pathlib import Path
from typing import Optional

import numpy as np
from pydantic import FilePath
from pynwb import NWBFile
from pynwb.ecephys import ElectricalSeries
from pymatreader import read_mat

from neuroconv.basedatainterface import BaseDataInterface


class M1MPTPLFPInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP local field potential data."""

    keywords = ("electrophysiology", "LFP", "local field potential", "neural")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP local field potential recordings"

    def __init__(self, file_path: FilePath, inter_trial_time_interval: float = 3.0, verbose: bool = False):
        """
        Initialize the M1MPTPLFPInterface.

        Parameters
        ----------
        file_path : FilePath
            Path to the Turner Lab .mat file containing analog data
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.file_path = Path(file_path)
        self.inter_trial_time_interval = inter_trial_time_interval

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add LFP data to the NWB file as an ElectricalSeries linked to the M1 recording electrode.

        The LFP is stored in an ecephys processing module within an LFP container,
        following NWB best practices for processed electrophysiology data.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict, optional
            Metadata dictionary
        """
        # Load MATLAB data
        mat_data = read_mat(str(self.file_path))

        # Check if LFP data exists
        if "Analog" not in mat_data or "lfp" not in mat_data["Analog"]:
            if self.verbose:
                print("No LFP data found in file, skipping LFP interface")
            return

        analog_data = mat_data["Analog"]
        file_info = mat_data["file_info"]
        analog_sampling_rate = file_info["analog_fs"]

        signal_data_list = analog_data["lfp"]
        n_trials = len(signal_data_list)

        if self.verbose:
            print(f"Processing LFP data: {n_trials} trials")

        # Verify electrodes table exists
        if nwbfile.electrodes is None or len(nwbfile.electrodes) == 0:
            raise ValueError(
                "Electrodes table must be populated before adding LFP. "
                "Ensure ElectrodesInterface runs before LFPInterface."
            )

        # Create electrode table region for M1 recording electrode (index 0)
        # This is the same electrode used for spike recording
        recording_electrode_region = nwbfile.create_electrode_table_region(
            region=[0],  # M1 recording electrode
            description="M1 recording electrode - same electrode used for single-unit recordings"
        )

        # Build concatenated timeline
        trial_data_list = []
        timestamps = []
        current_time = 0.0

        for trial_index in range(n_trials):
            trial_data = signal_data_list[trial_index]
            trial_start_time = current_time

            n_samples = trial_data.shape[0]
            trial_duration = n_samples / analog_sampling_rate
            trial_timestamps = np.linspace(trial_start_time, trial_start_time + trial_duration, n_samples)

            trial_data_list.append(trial_data)
            timestamps.extend(trial_timestamps)

            current_time = trial_start_time + trial_duration + self.inter_trial_time_interval

        continuous_data = np.concatenate(trial_data_list, axis=0)
        timestamps = np.array(timestamps)

        # Reshape to 2D for neuroconv compatibility (n_samples, n_channels)
        continuous_data_2d = continuous_data.reshape(-1, 1)

        # Create LFP as ElectricalSeries with electrode linkage
        lfp_series = ElectricalSeries(
            name="LFP",
            data=continuous_data_2d,
            timestamps=timestamps,
            electrodes=recording_electrode_region,
            description="Local field potential from M1 microelectrode. "
            "Recorded simultaneously with single-unit activity during visuomotor task. "
            "Signal processing: 10k gain, 1-100 Hz bandpass filtered.",
            comments="LFP from same electrode as spike recordings. "
            "Trials concatenated with inter-trial gaps.",
        )

        # Get or create ecephys processing module
        if "ecephys" in nwbfile.processing:
            ecephys_module = nwbfile.processing["ecephys"]
        else:
            ecephys_module = nwbfile.create_processing_module(
                name="ecephys",
                description="Processed extracellular electrophysiology data"
            )

        # Add the LFP ElectricalSeries directly to the processing module
        ecephys_module.add(lfp_series)

        if self.verbose:
            print(f"Added LFP: {len(continuous_data)} samples across {n_trials} trials")
            print(f"  Linked to electrode: {nwbfile.electrodes[0].location[0]}")
            print(f"  Stored in: processing/ecephys/LFP")
