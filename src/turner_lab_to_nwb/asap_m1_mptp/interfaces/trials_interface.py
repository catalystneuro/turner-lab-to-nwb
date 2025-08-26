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
        events = mat_data["Events"]
        movement_data = mat_data["Mvt"]

        # Extract event times and convert from milliseconds to seconds
        home_cue_times = np.array(events["home_cue_on"]) / 1000.0
        target_cue_times = np.array(events["targ_cue_on"]) / 1000.0
        target_directions = np.array(events["targ_dir"])
        movement_onsets = np.array(events["home_leave"]) / 1000.0
        reward_times = np.array(events["reward"]) / 1000.0

        # Extract movement parameters and convert from milliseconds to seconds
        movement_onset_times = np.array(movement_data["onset_t"]) / 1000.0
        movement_end_times = np.array(movement_data["end_t"]) / 1000.0
        peak_velocities = np.array(movement_data["pkvel"])
        peak_velocity_times = np.array(movement_data["pkvel_t"]) / 1000.0
        end_positions = np.array(movement_data["end_posn"])
        movement_amplitudes = np.array(movement_data["mvt_amp"])

        n_trials = len(target_directions)

        # Calculate trial start and stop times based on actual analog data durations
        # This approach preserves all recorded data while maintaining inter-trial intervals
        analog_data = mat_data["Analog"]
        
        # Get actual trial durations from analog data (using position signal as reference)
        trial_durations = []
        for trial_index in range(n_trials):
            trial_analog = analog_data["x"][trial_index]
            duration_s = len(trial_analog) / 1000.0  # Assuming 1kHz sampling, convert to seconds
            trial_durations.append(duration_s)
        
        # Create continuous timeline with inter-trial intervals
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
        
        if self.verbose:
            print(f"Trial durations (s): min={min(trial_durations):.1f}, max={max(trial_durations):.1f}, mean={np.mean(trial_durations):.1f}")
            print(f"Total session duration: {trial_stop_times[-1]:.1f}s with {self.inter_trial_time_interval}s inter-trial intervals")

        # Add trial columns with descriptions
        nwbfile.add_trial_column("movement_type", "movement direction (flexion or extension)")
        nwbfile.add_trial_column("home_cue_time", "start position cue onset relative to trial start (seconds)")
        nwbfile.add_trial_column("target_cue_time", "peripheral target cue onset relative to trial start (seconds)")
        nwbfile.add_trial_column("movement_onset_time", "movement initiation time relative to trial start (seconds)")
        nwbfile.add_trial_column("reward_time", "reward delivery time relative to trial start (seconds)")
        nwbfile.add_trial_column("perturbation_type", "torque perturbation type (flex/ext/none)")
        nwbfile.add_trial_column("perturbation_time", "perturbation onset time relative to trial start (seconds)")

        # Add movement parameter columns
        nwbfile.add_trial_column(
            "extracted_movement_onset_time", "extracted movement onset time relative to trial start (seconds)"
        )
        nwbfile.add_trial_column("movement_end_time", "extracted movement end time relative to trial start (seconds)")
        nwbfile.add_trial_column("peak_velocity", "peak velocity during movement")
        nwbfile.add_trial_column("peak_velocity_time", "time of peak velocity relative to trial start (seconds)")
        nwbfile.add_trial_column("movement_amplitude", "movement amplitude")
        nwbfile.add_trial_column("end_position", "final joint position")

        # Handle perturbation data - check if present and extract
        flexion_perturbations = events.get("tq_flex", [None] * n_trials)
        extension_perturbations = events.get("tq_ext", [None] * n_trials)

        # Convert perturbation times to arrays, handling None values
        if flexion_perturbations is not None:
            flexion_perturbations = np.array(flexion_perturbations)
        if extension_perturbations is not None:
            extension_perturbations = np.array(extension_perturbations)

        # Add trials to NWB file
        for trial_index in range(n_trials):
            # Determine perturbation type and time
            perturbation_type = "none"
            perturbation_time = np.nan

            # Check for flexion perturbation
            if (
                flexion_perturbations is not None
                and trial_index < len(flexion_perturbations)
                and not np.isnan(flexion_perturbations[trial_index])
            ):
                perturbation_type = "flex"
                perturbation_time = flexion_perturbations[trial_index] / 1000.0

            # Check for extension perturbation
            elif (
                extension_perturbations is not None
                and trial_index < len(extension_perturbations)
                and not np.isnan(extension_perturbations[trial_index])
            ):
                perturbation_type = "ext"
                perturbation_time = extension_perturbations[trial_index] / 1000.0

            nwbfile.add_trial(
                start_time=trial_start_times[trial_index],
                stop_time=trial_stop_times[trial_index],
                movement_type="flexion" if target_directions[trial_index] == 1 else "extension",
                home_cue_time=home_cue_times[trial_index],
                target_cue_time=target_cue_times[trial_index],
                movement_onset_time=movement_onsets[trial_index],
                reward_time=reward_times[trial_index],
                perturbation_type=perturbation_type,
                perturbation_time=perturbation_time,
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
            if flexion_perturbations is not None or extension_perturbations is not None:
                perturbation_count = sum(
                    1
                    for i in range(n_trials)
                    if (
                        (
                            flexion_perturbations is not None
                            and i < len(flexion_perturbations)
                            and not np.isnan(flexion_perturbations[i])
                        )
                        or (
                            extension_perturbations is not None
                            and i < len(extension_perturbations)
                            and not np.isnan(extension_perturbations[i])
                        )
                    )
                )
                print(f"Trials with perturbations: {perturbation_count}")
