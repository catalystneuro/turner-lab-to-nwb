from pathlib import Path
from typing import Optional

import numpy as np
from pynwb import NWBFile, TimeSeries
from pynwb.behavior import SpatialSeries
from pynwb.device import Device

from neuroconv.basedatainterface import BaseDataInterface

from .trial_sources import get_trial_timeline, read_trial_source_files


class M1MPTPManipulandumInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP manipulandum control and feedback signals."""

    keywords = ("behavior", "manipulandum", "motor task", "angle", "velocity", "torque")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP manipulandum angle, velocity, and torque signals"

    def __init__(
        self,
        trial_sources: list[tuple[Path, int]],
        inter_trial_time_interval: float = 3.0,
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPManipulandumInterface.

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
        self._mat_data_by_file = read_trial_source_files(trial_sources)
        has_analog = [isinstance(mat_data.get("Analog"), dict) for mat_data in self._mat_data_by_file.values()]
        if any(has_analog) and not all(has_analog):
            raise ValueError(f"Only some source files of this session have analog data: {list(self._mat_data_by_file)}")
        # In 14 monkey L sessions an A/D converter malfunction left the analog channels flat, stored as NaN
        self.analog_data_missing = not any(has_analog)

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add manipulandum data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict
            Metadata with the device in "Devices" ("TorqueMotor") and the series names and descriptions in
            "Behavior" ("Manipulandum" and "ProcessingModule")
        """
        if self.analog_data_missing:
            if self.verbose:
                print("No analog data found in file (Analog is missing or NaN), skipping manipulandum interface")
            return
        mat_data_by_file = self._mat_data_by_file
        analog_data_by_file = {path: mat_data["Analog"] for path, mat_data in mat_data_by_file.items()}
        first_file = self.trial_sources[0][0]
        analog_data = analog_data_by_file[first_file]
        analog_sampling_rate = mat_data_by_file[first_file]["file_info"]["analog_fs"]

        if "TorqueMotor" not in nwbfile.devices:
            nwbfile.add_device(Device(**metadata["Devices"]["TorqueMotor"]))
        series_metadata = metadata["Behavior"]["Manipulandum"]

        # Expected manipulandum signals
        manipulandum_signals = ["x", "vel", "torq"]
        
        if self.verbose:
            print(f"Processing manipulandum signals: {manipulandum_signals}")

        # Place each trial's samples from that trial's start time, on the same timeline as the
        # trials table and the spike times
        trial_start_times, _ = get_trial_timeline(mat_data_by_file, self.trial_sources, self.inter_trial_time_interval)

        # Process each signal
        for signal_name in manipulandum_signals:
            if signal_name not in analog_data:
                if self.verbose:
                    print(f"Signal '{signal_name}' not found in data, skipping...")
                continue

            n_trials = len(self.trial_sources)

            trial_data_list = []
            timestamps = []
            for trial_index, (path, file_trial) in enumerate(self.trial_sources):
                trial_data = analog_data_by_file[path][signal_name][file_trial]
                n_samples = trial_data.shape[0]
                trial_timestamps = trial_start_times[trial_index] + np.arange(n_samples) / analog_sampling_rate
                trial_data_list.append(trial_data)
                timestamps.extend(trial_timestamps)

            continuous_data = np.concatenate(trial_data_list, axis=0)
            timestamps = np.array(timestamps)

            # Add appropriate data series based on signal type
            if signal_name == "x":
                # Joint angle data - raw manipulandum angle sensor data
                angle_series = SpatialSeries(
                    name=series_metadata["angle"]["name"],
                    data=continuous_data.reshape(-1, 1),  # Make 2D
                    timestamps=timestamps,
                    unit="degrees",
                    description=series_metadata["angle"]["description"],
                    reference_frame=series_metadata["angle"]["reference_frame"],
                )

                nwbfile.add_acquisition(angle_series)

            elif signal_name == "vel":
                # Velocity data
                velocity_series = TimeSeries(
                    name=series_metadata["velocity"]["name"],
                    data=continuous_data,
                    timestamps=timestamps,
                    unit="degrees/s",
                    description=series_metadata["velocity"]["description"],
                )

                # Add to behavior processing module
                module_metadata = metadata["Behavior"]["ProcessingModule"]
                if module_metadata["name"] not in nwbfile.processing:
                    behavior_module = nwbfile.create_processing_module(**module_metadata)
                else:
                    behavior_module = nwbfile.processing[module_metadata["name"]]

                behavior_module.add(velocity_series)

            elif signal_name == "torq":
                # Commands sent to the torque controller, which show something different in each monkey
                torque_series = TimeSeries(
                    name=series_metadata["torque"]["name"],
                    data=continuous_data,
                    timestamps=timestamps,
                    unit="arbitrary",
                    description=series_metadata["torque"]["description"],
                )

                nwbfile.add_acquisition(torque_series)

            if self.verbose:
                print(f"Added {signal_name}: {len(continuous_data)} samples across {n_trials} trials")