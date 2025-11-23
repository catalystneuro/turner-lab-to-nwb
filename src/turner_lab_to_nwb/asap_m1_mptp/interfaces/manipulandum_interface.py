from pathlib import Path
from typing import Optional

import numpy as np
from pydantic import FilePath
from pynwb import NWBFile, TimeSeries
from pynwb.behavior import SpatialSeries, CompassDirection
from pymatreader import read_mat

from neuroconv.basedatainterface import BaseDataInterface


class M1MPTPManipulandumInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP manipulandum control and feedback signals."""

    keywords = ("behavior", "manipulandum", "motor task", "angle", "velocity", "torque")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP manipulandum angle, velocity, and torque signals"

    def __init__(self, file_path: FilePath, inter_trial_time_interval: float = 3.0, verbose: bool = False):
        """
        Initialize the M1MPTPManipulandumInterface.

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
        Add manipulandum data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict, optional
            Metadata dictionary
        """
        # Load MATLAB data
        mat_data = read_mat(str(self.file_path))
        analog_data = mat_data["Analog"]
        file_info = mat_data["file_info"]
        analog_sampling_rate = file_info["analog_fs"]

        # Expected manipulandum signals
        manipulandum_signals = ["x", "vel", "torq"]
        
        if self.verbose:
            print(f"Processing manipulandum signals: {manipulandum_signals}")

        # Process each signal
        for signal_name in manipulandum_signals:
            if signal_name not in analog_data:
                if self.verbose:
                    print(f"Signal '{signal_name}' not found in data, skipping...")
                continue

            signal_data_list = analog_data[signal_name]
            n_trials = len(signal_data_list)

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

            # Add appropriate data series based on signal type
            if signal_name == "x":
                # Elbow joint angle data - raw manipulandum angle sensor data
                angle_series = SpatialSeries(
                    name="SpatialSeriesElbowAngle",
                    data=continuous_data.reshape(-1, 1),  # Make 2D
                    timestamps=timestamps,
                    unit="degrees",
                    description="Raw manipulandum angle from sensor during visuomotor flexion/extension task",
                    reference_frame="Anatomical flexion/extension axis, 0 degrees = neutral position, positive = extension",
                )

                # Wrap in CompassDirection for angular data
                compass_direction = CompassDirection(name="CompassDirectionElbowAngle", spatial_series=angle_series)
                nwbfile.add_acquisition(compass_direction)

            elif signal_name == "vel":
                # Velocity data
                velocity_series = TimeSeries(
                    name="TimeSeriesElbowVelocity",
                    data=continuous_data,
                    timestamps=timestamps,
                    unit="degrees/s",
                    description="Elbow joint velocity during visuomotor task",
                )

                # Add to behavior processing module
                if "behavior" not in nwbfile.processing:
                    behavior_module = nwbfile.create_processing_module("behavior", "Behavioral data")
                else:
                    behavior_module = nwbfile.processing["behavior"]

                behavior_module.add(velocity_series)

            elif signal_name == "torq":
                # Torque data - raw commands sent to torque controller
                torque_series = TimeSeries(
                    name="TimeSeriesElbowTorque",
                    data=continuous_data,
                    timestamps=timestamps,
                    unit="arbitrary",
                    description="Commands sent to torque controller during visuomotor task",
                )

                nwbfile.add_acquisition(torque_series)

            if self.verbose:
                print(f"Added {signal_name}: {len(continuous_data)} samples across {n_trials} trials")