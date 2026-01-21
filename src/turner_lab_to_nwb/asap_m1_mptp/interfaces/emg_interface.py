from pathlib import Path
from typing import Optional, List

import numpy as np
from pydantic import FilePath
from pynwb import NWBFile, TimeSeries
from pymatreader import read_mat

from neuroconv.basedatainterface import BaseDataInterface


class M1MPTPEMGInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP electromyography data."""

    keywords = ("electromyography", "EMG", "muscle activity", "behavioral")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP EMG recordings from arm muscles"

    # Map abbreviated muscle names from metadata to full anatomical names
    MUSCLE_NAME_MAP = {
        # Monkey V (elbow task)
        "triceps long.": "TricepsLongus",
        "triceps lat.": "TricepsLateralis",
        "brachioradialis": "Brachioradialis",
        "trapezius": "Trapezius",
        "deltoid post.": "DeltoidPosterior",
        # Monkey L (wrist task)
        "flexor carpi ulnaris": "FlexorCarpiUlnaris",
        "flexor carpi radialis": "FlexorCarpiRadialis",
        "biceps longus": "BicepsLongus",
    }

    # Muscle descriptions including anatomical function
    MUSCLE_DESCRIPTIONS = {
        "triceps long.": "Triceps longus (long head) - elbow extensor",
        "triceps lat.": "Triceps lateralis (lateral head) - elbow extensor",
        "brachioradialis": "Brachioradialis - elbow flexor and forearm supinator/pronator",
        "trapezius": "Trapezius - shoulder and scapula stabilizer",
        "deltoid post.": "Posterior deltoid - shoulder extensor and external rotator",
        "flexor carpi ulnaris": "Flexor carpi ulnaris - wrist flexor and ulnar deviator",
        "flexor carpi radialis": "Flexor carpi radialis - wrist flexor and radial deviator",
        "biceps longus": "Biceps brachii (long head) - elbow flexor and forearm supinator",
    }

    def __init__(
        self,
        file_path: FilePath,
        inter_trial_time_interval: float = 3.0,
        muscle_names: Optional[List[str]] = None,
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPEMGInterface.

        Parameters
        ----------
        file_path : FilePath
            Path to the Turner Lab .mat file containing analog data
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        muscle_names : list of str, optional
            List of muscle names for each EMG channel, in order. If not provided,
            generic channel names will be used.
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.file_path = Path(file_path)
        self.inter_trial_time_interval = inter_trial_time_interval
        self.muscle_names = muscle_names

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

        n_channels = continuous_data.shape[1]

        # Pre-compute all series names to handle duplicates (e.g., "triceps long." appears twice)
        # First pass: count occurrences of each base name
        base_name_counts = {}
        for channel_index in range(n_channels):
            muscle_name = self.muscle_names[channel_index]
            # Use mapping for full anatomical name, fall back to camelCase of original
            full_name = self.MUSCLE_NAME_MAP.get(
                muscle_name,
                "".join(word.capitalize() for word in muscle_name.replace(".", "").split())
            )
            base_name = f"EMG{full_name}"
            base_name_counts[base_name] = base_name_counts.get(base_name, 0) + 1

        # Second pass: assign names with numeric suffixes for duplicates
        base_name_indices = {}
        series_names = []
        for channel_index in range(n_channels):
            muscle_name = self.muscle_names[channel_index]
            # Use mapping for full anatomical name, fall back to camelCase of original
            full_name = self.MUSCLE_NAME_MAP.get(
                muscle_name,
                "".join(word.capitalize() for word in muscle_name.replace(".", "").split())
            )
            base_name = f"EMG{full_name}"

            if base_name_counts[base_name] > 1:
                # Multiple channels with same name: use 1, 2, 3...
                base_name_indices[base_name] = base_name_indices.get(base_name, 0) + 1
                series_names.append(f"{base_name}{base_name_indices[base_name]}")
            else:
                series_names.append(base_name)

        # Create one TimeSeries per EMG channel/muscle
        for channel_index in range(n_channels):
            channel_data = continuous_data[:, channel_index]
            muscle_name = self.muscle_names[channel_index]
            series_name = series_names[channel_index]

            # Get muscle description with anatomical function
            muscle_description = self.MUSCLE_DESCRIPTIONS.get(muscle_name, muscle_name)

            description = (
                f"Preprocessed EMG from {muscle_description}. "
                "Recording: chronically-implanted Teflon-insulated multistranded stainless steel wire electrodes. "
                "Signal processing: differentially amplified (gain=10,000), bandpass filtered (20 Hz - 5 kHz), "
                "full-wave rectified, low-pass filtered (100 Hz), then digitized."
            )

            comments = (
                "Data are uncalibrated A/D converter values (centered ~2048, consistent with 12-bit digitization). "
                "No voltage calibration factor is available. Values represent relative muscle activation magnitude."
            )

            # Create EMG time series for this channel
            emg_series = TimeSeries(
                name=series_name,
                data=channel_data,
                timestamps=timestamps,
                unit="a.u.",
                description=description,
                comments=comments,
            )

            nwbfile.add_acquisition(emg_series)

        if self.verbose:
            print(f"Added EMG: {continuous_data.shape[0]} samples x {n_channels} channels across {n_trials} trials")