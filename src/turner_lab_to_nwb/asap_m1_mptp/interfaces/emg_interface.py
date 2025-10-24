from pathlib import Path
from typing import Optional

import numpy as np
from pydantic import FilePath
from pynwb import NWBFile, TimeSeries
from pymatreader import read_mat

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict


class M1MPTPEMGInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP electromyography data."""

    keywords = ("electromyography", "EMG", "muscle activity", "behavioral")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP EMG recordings from arm muscles"

    def __init__(self, file_path: FilePath, inter_trial_time_interval: float = 3.0, verbose: bool = False):
        """
        Initialize the M1MPTPEMGInterface.

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

    def get_metadata(self) -> DeepDict:
        """Get metadata for the NWB file."""
        metadata = super().get_metadata()

        metadata["NWBFile"]["session_description"] = f"Turner Lab MPTP EMG data from {self.file_path.stem}"
        metadata["NWBFile"]["session_id"] = self.file_path.stem

        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add EMG data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict, optional
            Metadata dictionary
        """
        # Load MATLAB data
        mat_data = read_mat(str(self.file_path))
        
        # Check if EMG data exists
        if "Analog" not in mat_data or "emg" not in mat_data["Analog"]:
            if self.verbose:
                print("No EMG data found in file, skipping EMG interface")
            return

        analog_data = mat_data["Analog"]
        file_info = mat_data["file_info"]
        analog_sampling_rate = file_info["analog_fs"]

        signal_data_list = analog_data["emg"]
        n_trials = len(signal_data_list)

        if self.verbose:
            print(f"Processing EMG data: {n_trials} trials")

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

        # Create EMG time series
        emg_series = TimeSeries(
            name="TimeSeriesEMG",
            data=continuous_data,
            timestamps=timestamps,
            unit="arbitrary",
            description="EMG signals from chronically-implanted Teflon-insulated multistranded stainless steel wire electrodes. "
                       "Multiple arm muscles recorded: flexor carpi ulnaris, flexor carpi radialis, biceps longus, "
                       "brachioradialis, triceps lateralis (Monkey L); posterior deltoid, trapezius, triceps longus, "
                       "triceps lateralis, brachioradialis (Monkey V). Electrode placement verified post-surgically. "
                       "Data preprocessed (rectified and low-pass filtered).",
        )

        # Add to acquisition
        nwbfile.add_acquisition(emg_series)

        if self.verbose:
            print(f"Added EMG: {len(continuous_data)} samples across {n_trials} trials")