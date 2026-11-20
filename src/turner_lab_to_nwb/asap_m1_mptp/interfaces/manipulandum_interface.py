from pathlib import Path
from typing import Literal, Optional

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
        joint: Literal["elbow", "wrist"],
        inter_trial_time_interval: float = 3.0,
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPManipulandumInterface.

        Parameters
        ----------
        trial_sources : list of (Path, int)
            The session's trials in order, as (Turner Lab .mat file, trial index in that file)
        joint : {"elbow", "wrist"}
            Joint moved in the task: elbow for monkey V, wrist for monkey L
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.trial_sources = trial_sources
        self.joint = joint
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
        mat_data_by_file = read_trial_source_files(self.trial_sources)
        analog_data_by_file = {path: mat_data.get("Analog") for path, mat_data in mat_data_by_file.items()}
        has_analog = [isinstance(analog_data, dict) for analog_data in analog_data_by_file.values()]
        if not any(has_analog):
            if self.verbose:
                print("No analog data found in file (Analog is missing or NaN), skipping manipulandum interface")
            self.analog_data_missing = True
            return
        if not all(has_analog):
            raise ValueError(f"Only some source files of this session have analog data: {list(analog_data_by_file)}")
        self.analog_data_missing = False
        first_file = self.trial_sources[0][0]
        analog_data = analog_data_by_file[first_file]
        analog_sampling_rate = mat_data_by_file[first_file]["file_info"]["analog_fs"]

        # Add torque motor device if not already present
        if "TorqueMotor" not in nwbfile.devices:
            nwbfile.add_device(
                Device(
                    name="TorqueMotor",
                    description=(
                        "TQ40W torque motor (Aerotech Inc.) used in the manipulandum system to provide resistance "
                        "and position control during the visuomotor step-tracking task. The monkey's arm was held in "
                        f"a padded manipulandum with the {self.joint} joint aligned with the torque motor axis of "
                        "rotation. See the torque series description for what the recorded command shows. "
                        "Note: Pasquereau and Turner (2013) describe a second use, brief, temporally unpredictable "
                        "torque perturbations (0.1 Nm, 50 ms impulse) on randomly selected trials to evoke stretch "
                        "reflexes."
                    ),
                    manufacturer="Aerotech Inc.",
                )
            )

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
                    name=f"{self.joint.capitalize()}Angle",
                    data=continuous_data.reshape(-1, 1),  # Make 2D
                    timestamps=timestamps,
                    unit="degrees",
                    description="Raw manipulandum angle from sensor during visuomotor flexion/extension task",
                    reference_frame="Anatomical flexion/extension axis, 0 degrees = neutral position, positive = flexion",
                )

                nwbfile.add_acquisition(angle_series)

            elif signal_name == "vel":
                # Velocity data
                velocity_series = TimeSeries(
                    name=f"{self.joint.capitalize()}Velocity",
                    data=continuous_data,
                    timestamps=timestamps,
                    unit="degrees/s",
                    description=f"{self.joint.capitalize()} joint velocity during visuomotor task",
                )

                # Add to behavior processing module
                if "behavior" not in nwbfile.processing:
                    behavior_module = nwbfile.create_processing_module("behavior", "Behavioral data")
                else:
                    behavior_module = nwbfile.processing["behavior"]

                behavior_module.add(velocity_series)

            elif signal_name == "torq":
                # Torque data - raw commands sent to torque controller. What the command shows differs
                # between the monkeys: monkey V (elbow) has perturbation pulses, monkey L (wrist) has none.
                no_newton_metres = (
                    "No conversion to newton-metres is available: the amplifier and controller gains are not in "
                    "these MATLAB files, and the original recordings they were exported from were not provided."
                )
                if self.joint == "elbow":
                    torque_description = (
                        "Command sent to the torque motor controller, in arbitrary units. Perturbations appear as "
                        "50 ms pulses that leave rest about 5 ms after torque_perturbation_onset_time and reach half "
                        "their peak at about 8 ms (sessions v1401, v1402 and v1501 have perturbation times but no "
                        "pulses in the command). The pulse size "
                        "varies: before MPTP each session uses one of three levels (about 46, 91 and 183 units above "
                        "rest); after MPTP it varies from trial to trial and is often followed by a command in the "
                        f"opposite direction. {no_newton_metres} Note: Pasquereau and Turner (2013) describe the "
                        "perturbations as 0.1 Nm, 50 ms torque impulses delivered 1 to 2 s after center target capture."
                    )
                else:
                    torque_description = (
                        "Command sent to the torque motor controller, in arbitrary units. The monkey L source files "
                        "contain no torque perturbation times. The command is NaN in every file before MPTP; after "
                        f"MPTP it is a continuous trace without distinct pulses. {no_newton_metres}"
                    )
                torque_series = TimeSeries(
                    name=f"{self.joint.capitalize()}Torque",
                    data=continuous_data,
                    timestamps=timestamps,
                    unit="arbitrary",
                    description=torque_description,
                )

                nwbfile.add_acquisition(torque_series)

            if self.verbose:
                print(f"Added {signal_name}: {len(continuous_data)} samples across {n_trials} trials")