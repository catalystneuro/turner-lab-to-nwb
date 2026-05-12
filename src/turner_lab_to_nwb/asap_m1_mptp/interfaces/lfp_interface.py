from pathlib import Path
from typing import Optional

import numpy as np
from pydantic import FilePath
from pynwb import NWBFile, TimeSeries
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
        Add LFP data to the NWB file as a TimeSeries (unit="a.u.") in the ecephys
        processing module. Stored as a plain TimeSeries rather than ElectricalSeries
        because the ADC range needed to calibrate to volts is undocumented.

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
        if "Analog" not in mat_data or not isinstance(mat_data["Analog"], dict) or "lfp" not in mat_data["Analog"]:
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

        # Stored as plain TimeSeries with unit="a.u." rather than ElectricalSeries
        # (which would imply volts). The voltage calibration cannot be confirmed:
        # the LFP digitizer's ADC range is undocumented, and even by parallel
        # reasoning to the antidromic factor it would rest on an unverified
        # assumption about the ADC range. Mirrors the EMG approach. Counts are
        # 12-bit unsigned, centered on the midpoint 2048; subtract 2048 for
        # zero-baseline analyses.
        lfp_series = TimeSeries(
            name="LFP",
            data=continuous_data,
            timestamps=timestamps,
            unit="a.u.",
            description="Local field potential from M1 microelectrode. "
            "Recorded simultaneously with single-unit activity during visuomotor task. "
            "Signal processing: 10k gain, 1-100 Hz bandpass filtered.",
            comments="Raw 12-bit unsigned A/D counts (centered ~2048). No voltage "
            "calibration applied: the LFP digitizer's ADC range is undocumented. "
            "LFP from same electrode as spike recordings (electrode metadata available "
            "in nwbfile.electrodes). Trials concatenated with inter-trial gaps.",
        )

        # Get or create ecephys processing module
        if "ecephys" in nwbfile.processing:
            ecephys_module = nwbfile.processing["ecephys"]
        else:
            ecephys_module = nwbfile.create_processing_module(
                name="ecephys",
                description="Processed extracellular electrophysiology data"
            )

        # Add the LFP TimeSeries directly to the processing module
        ecephys_module.add(lfp_series)

        if self.verbose:
            print(f"Added LFP: {len(continuous_data)} samples across {n_trials} trials")
            print(f"  Stored in: processing/ecephys/LFP")
