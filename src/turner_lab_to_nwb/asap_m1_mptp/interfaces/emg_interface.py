from pathlib import Path
from typing import Optional, List

import numpy as np
from pynwb import NWBFile, TimeSeries

from neuroconv.basedatainterface import BaseDataInterface

from .trial_sources import get_trial_timeline, read_trial_source_files


class M1MPTPEMGInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP electromyography data."""

    keywords = ("electromyography", "EMG", "muscle activity", "behavioral")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP EMG recordings from arm muscles"

    def __init__(
        self,
        trial_sources: list[tuple[Path, int]],
        inter_trial_time_interval: float = 3.0,
        muscle_names: Optional[List[str]] = None,
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPEMGInterface.

        Parameters
        ----------
        trial_sources : list of (Path, int)
            The session's trials in order, as (Turner Lab .mat file, trial index in that file)
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        muscle_names : list of str, optional
            List of muscle names for each EMG channel, in order. If not provided,
            generic channel names will be used.
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.trial_sources = trial_sources
        self.inter_trial_time_interval = inter_trial_time_interval
        self.muscle_names = muscle_names

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add EMG data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict
            Metadata with the muscles and the series descriptions in metadata["Behavior"]["EMG"]
        """
        emg_metadata = metadata["Behavior"]["EMG"]
        muscles = emg_metadata["muscles"]

        # Load MATLAB data
        mat_data_by_file = read_trial_source_files(self.trial_sources)
        has_signal = [
            isinstance(mat_data.get("Analog"), dict) and "emg" in mat_data["Analog"]
            for mat_data in mat_data_by_file.values()
        ]
        if not any(has_signal):
            if self.verbose:
                print("No EMG data found in file, skipping EMG interface")
            return
        if not all(has_signal):
            raise ValueError(f"Only some source files of this session have EMG data: {list(mat_data_by_file)}")

        first_file = self.trial_sources[0][0]
        analog_sampling_rate = mat_data_by_file[first_file]["file_info"]["analog_fs"]
        n_trials = len(self.trial_sources)

        if self.verbose:
            print(f"Processing EMG data: {n_trials} trials")

        # Place each trial's samples from that trial's start time, on the same timeline as the
        # trials table and the spike times
        trial_start_times, _ = get_trial_timeline(mat_data_by_file, self.trial_sources, self.inter_trial_time_interval)

        trial_data_list = []
        timestamps = []
        for trial_index, (path, file_trial) in enumerate(self.trial_sources):
            trial_data = mat_data_by_file[path]["Analog"]["emg"][file_trial]
            n_samples = trial_data.shape[0]
            trial_timestamps = trial_start_times[trial_index] + np.arange(n_samples) / analog_sampling_rate
            trial_data_list.append(trial_data)
            timestamps.extend(trial_timestamps)
        
        continuous_data = np.concatenate(trial_data_list, axis=0)
        timestamps = np.array(timestamps)

        n_channels = continuous_data.shape[1]

        # A muscle recorded on several channels (monkey V's triceps longus) gets numbered series, 1, 2, ...
        base_names = [f"EMG{muscles[muscle_name]['name']}" for muscle_name in self.muscle_names[:n_channels]]
        base_name_counts = {base_name: base_names.count(base_name) for base_name in base_names}
        channel_numbers = {}
        for channel_index in range(n_channels):
            muscle_name = self.muscle_names[channel_index]
            base_name = base_names[channel_index]
            muscle_description = muscles[muscle_name]["description"]
            duplicate_note = ""
            series_name = base_name
            if base_name_counts[base_name] > 1:
                channel_numbers[base_name] = channel_numbers.get(base_name, 0) + 1
                series_name = f"{base_name}{channel_numbers[base_name]}"
                duplicate_note = " " + emg_metadata["duplicate_note"].format(
                    channel=channel_numbers[base_name],
                    n_channels=base_name_counts[base_name],
                    muscle=muscle_description.split(" - ")[0].lower(),
                )
            inferred_compartment_note = emg_metadata["inferred_compartment_notes"].get(series_name)
            inferred_compartment_note = " " + inferred_compartment_note if inferred_compartment_note else ""

            emg_series = TimeSeries(
                name=series_name,
                data=continuous_data[:, channel_index],
                timestamps=timestamps,
                unit="a.u.",
                description=emg_metadata["description"].format(
                    muscle_description=muscle_description,
                    duplicate_note=duplicate_note,
                    inferred_compartment_note=inferred_compartment_note,
                ),
                comments=emg_metadata["comments"],
            )
            nwbfile.add_acquisition(emg_series)

        if self.verbose:
            print(f"Added EMG: {continuous_data.shape[0]} samples x {n_channels} channels across {n_trials} trials")