from pathlib import Path
from typing import Optional
import numpy as np

from neuroconv.basedatainterface import BaseDataInterface
from pydantic import FilePath
from pynwb import NWBFile
from pymatreader import read_mat


class M1MPTPTrialsInterface(BaseDataInterface):

    def __init__(
        self,
        file_path: FilePath,
        inter_trial_time_interval: float = 3.0,
        verbose: bool = False,
    ):
        super().__init__(verbose=verbose)
        self.file_path = Path(file_path)
        self.inter_trial_time_interval = inter_trial_time_interval

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None):
        mat_data = read_mat(str(self.file_path))

        # STEP 1: Extract all Events data first
        events = mat_data["Events"]
        home_cue_times = np.array(events["home_cue_on"]) / 1000.0
        target_cue_times = np.array(events["targ_cue_on"]) / 1000.0
        target_directions = np.array(events["targ_dir"])
        movement_onsets = np.array(events["home_leave"]) / 1000.0
        reward_times = np.array(events["reward"]) / 1000.0
        n_trials = len(target_directions)

        # STEP 2: Add trial columns for Events data
        nwbfile.add_trial_column("home_cue_time", "time of the start position appearance (seconds)")
        nwbfile.add_trial_column("target_cue_time", "time of the target appearance (seconds)")
        nwbfile.add_trial_column("movement_onset_time", "movement initiation time relative to trial start (seconds)")
        nwbfile.add_trial_column("reward_time", "reward delivery time relative to trial start (seconds)")

        # STEP 3: Process transformed Events variables to a tidy format
        flexion_perturbations = np.array(events.get("tq_flex", [np.nan] * n_trials))
        extension_perturbations = np.array(events.get("tq_ext", [np.nan] * n_trials))

        # Create movement_type array (flexion=1, extension=2 -> "flexion"/"extension")
        movement_type = ["flexion" if direction == 1 else "extension" for direction in target_directions]

        # Create perturbation_type and perturbation_time arrays
        perturbation_type = []
        perturbation_time = []
        
        for i in range(n_trials):
            # Check for flexion perturbation
            if not np.isnan(flexion_perturbations[i]):
                perturbation_type.append("flex")
                perturbation_time.append(flexion_perturbations[i] / 1000.0)
            # Check for extension perturbation
            elif not np.isnan(extension_perturbations[i]):
                perturbation_type.append("ext")
                perturbation_time.append(extension_perturbations[i] / 1000.0)
            # No perturbation
            else:
                perturbation_type.append("none")
                perturbation_time.append(np.nan)

        # Add trial columns for transformed Events variables
        nwbfile.add_trial_column("movement_type", "flexion or extension")
        nwbfile.add_trial_column("perturbation_type", "torque perturbation type (flex/ext/none)")
        nwbfile.add_trial_column("perturbation_time", "perturbation onset time relative to trial start (seconds)")

        # STEP 4: Extract movement Mvt data
        movement_data = mat_data["Mvt"]
        movement_onset_times = np.array(movement_data["onset_t"]) / 1000.0
        movement_end_times = np.array(movement_data["end_t"]) / 1000.0
        peak_velocities = np.array(movement_data["pkvel"])
        peak_velocity_times = np.array(movement_data["pkvel_t"]) / 1000.0
        end_positions = np.array(movement_data["end_posn"])
        movement_amplitudes = np.array(movement_data["mvt_amp"])

        # STEP 5: Add trial columns for movement data
        nwbfile.add_trial_column(
            "extracted_movement_onset_time", "extracted movement onset time relative to trial start (seconds)"
        )
        nwbfile.add_trial_column("movement_end_time", "extracted movement end time relative to trial start (seconds)")
        nwbfile.add_trial_column("peak_velocity", "peak velocity during movement")
        nwbfile.add_trial_column("peak_velocity_time", "time of peak velocity relative to trial start (seconds)")
        nwbfile.add_trial_column("movement_amplitude", "movement amplitude")
        nwbfile.add_trial_column("end_position", "final joint position")

        # STEP 6: Extract analog data for trial timing
        analog_data = mat_data["Analog"]
        trial_durations = []
        for trial_index in range(n_trials):
            trial_analog = analog_data["x"][trial_index]
            duration_s = len(trial_analog) / 1000.0  # Assuming 1kHz sampling, convert to seconds
            trial_durations.append(duration_s)

        # Calculate trial start and stop times based on actual analog data durations
        trial_start_times = []
        trial_stop_times = []
        current_time = 0.0

        for trial_index in range(n_trials):
            trial_start = current_time
            trial_stop = trial_start + trial_durations[trial_index]

            trial_start_times.append(trial_start)
            trial_stop_times.append(trial_stop)

            # Next trial starts after inter-trial interval
            current_time = trial_stop + self.inter_trial_time_interval

        trial_start_times = np.array(trial_start_times)
        trial_stop_times = np.array(trial_stop_times)

        # Add trials to NWB file using processed arrays
        for trial_index in range(n_trials):
            nwbfile.add_trial(
                start_time=trial_start_times[trial_index],
                stop_time=trial_stop_times[trial_index],
                movement_type=movement_type[trial_index],
                home_cue_time=home_cue_times[trial_index],
                target_cue_time=target_cue_times[trial_index],
                movement_onset_time=movement_onsets[trial_index],
                reward_time=reward_times[trial_index],
                perturbation_type=perturbation_type[trial_index],
                perturbation_time=perturbation_time[trial_index],
                extracted_movement_onset_time=movement_onset_times[trial_index],
                movement_end_time=movement_end_times[trial_index],
                peak_velocity=peak_velocities[trial_index],
                peak_velocity_time=peak_velocity_times[trial_index],
                movement_amplitude=movement_amplitudes[trial_index],
                end_position=end_positions[trial_index],
            )

        if self.verbose:
            print(f"Added {n_trials} trials to NWB file")
            print(f"Flexion trials: {sum(target_directions == 1)}")
            print(f"Extension trials: {sum(target_directions == 2)}")
