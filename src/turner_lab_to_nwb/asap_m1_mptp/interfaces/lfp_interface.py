from pathlib import Path
from typing import Optional

import numpy as np
from pynwb import NWBFile, TimeSeries

from neuroconv.basedatainterface import BaseDataInterface

from .trial_sources import get_trial_timeline, read_trial_source_files


class M1MPTPLFPInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP local field potential data."""

    keywords = ("electrophysiology", "LFP", "local field potential", "neural")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP local field potential recordings"

    def __init__(
        self, trial_sources: list[tuple[Path, int]], inter_trial_time_interval: float = 3.0, verbose: bool = False
    ):
        """
        Initialize the M1MPTPLFPInterface.

        Parameters
        ----------
        trial_sources : list of (Path, int)
            The session's trials in order, as (Turner Lab .mat file, trial index in that file)
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.trial_sources = trial_sources
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
        mat_data_by_file = read_trial_source_files(self.trial_sources)
        has_signal = [
            isinstance(mat_data.get("Analog"), dict) and "lfp" in mat_data["Analog"]
            for mat_data in mat_data_by_file.values()
        ]
        if not any(has_signal):
            if self.verbose:
                print("No LFP data found in file, skipping LFP interface")
            return
        if not all(has_signal):
            raise ValueError(f"Only some source files of this session have LFP data: {list(mat_data_by_file)}")

        first_file = self.trial_sources[0][0]
        analog_sampling_rate = mat_data_by_file[first_file]["file_info"]["analog_fs"]
        n_trials = len(self.trial_sources)

        if self.verbose:
            print(f"Processing LFP data: {n_trials} trials")

        # Place each trial's samples from that trial's start time, on the same timeline as the
        # trials table and the spike times
        trial_start_times, _ = get_trial_timeline(mat_data_by_file, self.trial_sources, self.inter_trial_time_interval)

        trial_data_list = []
        timestamps = []
        for trial_index, (path, file_trial) in enumerate(self.trial_sources):
            trial_data = mat_data_by_file[path]["Analog"]["lfp"][file_trial]
            n_samples = trial_data.shape[0]
            trial_timestamps = trial_start_times[trial_index] + np.arange(n_samples) / analog_sampling_rate
            trial_data_list.append(trial_data)
            timestamps.extend(trial_timestamps)

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
            "calibration applied: the LFP digitizer's ADC range is undocumented, and the lab confirmed that no "
            "voltage calibration is available. "
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
