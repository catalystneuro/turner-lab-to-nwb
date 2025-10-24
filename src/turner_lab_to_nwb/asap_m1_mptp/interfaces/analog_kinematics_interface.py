from pathlib import Path
from typing import Optional

import numpy as np
from pydantic import FilePath
from pynwb import NWBFile, TimeSeries
from pynwb.behavior import SpatialSeries, CompassDirection
from pymatreader import read_mat

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict


class M1MPTPAnalogKinematicsInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP analog kinematics data."""

    keywords = ("behavior", "kinematics", "analog signals", "elbow angle", "velocity", "torque")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP analog kinematics data from MATLAB files"

    def __init__(self, file_path: FilePath, inter_trial_time_interval: float = 3.0, verbose: bool = False):
        """
        Initialize the M1MPTPAnalogKinematicsInterface.

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

        metadata["NWBFile"]["session_description"] = f"Turner Lab MPTP analog kinematics from {self.file_path.stem}"
        metadata["NWBFile"]["session_id"] = self.file_path.stem

        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add analog kinematics data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict, optional
            Metadata dictionary
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        """
        if metadata is None:
            metadata = self.get_metadata()

        # Load MATLAB data
        mat_data = read_mat(str(self.file_path))

        # Check for analog data - must be present
        if "Analog" not in mat_data:
            raise ValueError(f"No 'Analog' field found in MATLAB file: {self.file_path}")

        analog_data = mat_data["Analog"]

        # Get available analog signals
        available_signals = list(analog_data.keys())
        if self.verbose:
            print(f"Available analog signals: {available_signals}")

        # Step 1: Create dictionary of concatenated signals with proper timing
        concatenated_signals = {}

        # Get sampling rate from file_info - must be present
        if "file_info" not in mat_data:
            raise ValueError(f"No 'file_info' field found in MATLAB file: {self.file_path}")

        file_info = mat_data["file_info"]
        if "analog_fs" not in file_info:
            raise ValueError(f"No 'analog_fs' field found in file_info for file: {self.file_path}")

        analog_sampling_rate = file_info["analog_fs"]
        if self.verbose:
            print(f"Analog sampling rate: {analog_sampling_rate} Hz")

        for signal_name in available_signals:
            signal_data_list = analog_data[signal_name]  # List of trial arrays
            n_trials = len(signal_data_list)

            # Handle variable trial lengths and any dimensionality 
            trial_data_list = []
            timestamps = []

            # Build cumulative timeline matching trials interface (Option 2: analog-based boundaries)
            current_time = 0.0
            
            for trial_index in range(n_trials):
                trial_data = signal_data_list[trial_index]
                trial_start_time = current_time

                # Get trial duration from first dimension (time samples) - works for any dimensionality
                n_samples = trial_data.shape[0]
                trial_duration = n_samples / analog_sampling_rate  # Actual duration in seconds
                trial_timestamps = np.linspace(trial_start_time, trial_start_time + trial_duration, n_samples)
                
                # Always concatenate along trial dimension (axis 0) - preserves all channels/dimensions
                trial_data_list.append(trial_data)
                timestamps.extend(trial_timestamps)
                
                # Update current time for next trial (matching trials interface)
                current_time = trial_start_time + trial_duration + self.inter_trial_time_interval
            
            # Concatenate all trial data along trial dimension (handles 1D, 2D, 3D, etc. automatically)
            continuous_data = np.concatenate(trial_data_list, axis=0) if trial_data_list else np.array([])

            # Store concatenated signal data
            concatenated_signals[signal_name] = {
                "data": continuous_data,
                "timestamps": np.array(timestamps),
                "n_trials": n_trials,
                "sampling_rate": analog_sampling_rate,
            }

            if self.verbose:
                print(f"Concatenated {signal_name}: {len(continuous_data)} samples across {n_trials} trials")

        # Step 2: Write signals to NWB file
        for signal_name, signal_info in concatenated_signals.items():
            continuous_data = signal_info["data"]
            timestamps = signal_info["timestamps"]

            # Handle the expected signals according to documentation: x, vel, torq, emg, lfp
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

                # Add raw sensor data to acquisition
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

                # Add to acquisition (raw control signals)
                nwbfile.add_acquisition(torque_series)

            elif signal_name == "emg":
                # EMG data from chronically-implanted intramuscular electrodes - preprocessed (rectified and low-pass filtered)
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

            elif signal_name == "lfp":
                # LFP data - low-pass filtered signal from microelectrode
                lfp_series = TimeSeries(
                    name="TimeSeriesLFP",
                    data=continuous_data,
                    timestamps=timestamps,
                    unit="volts",
                    description="Local field potential from microelectrode (10k gain, 1-100 Hz)",
                )

                # Add to acquisition
                nwbfile.add_acquisition(lfp_series)

            else:
                # Unexpected signal type - error immediately
                raise ValueError(
                    f"Unexpected analog signal type: '{signal_name}'. " f"Expected exactly: x, vel, torq, emg, lfp"
                )

            if self.verbose:
                n_trials = signal_info["n_trials"]
                print(f"Added {signal_name}: {len(continuous_data)} samples across {n_trials} trials")
