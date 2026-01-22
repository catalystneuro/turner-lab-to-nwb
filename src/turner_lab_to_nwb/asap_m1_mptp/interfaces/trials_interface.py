import json
from pathlib import Path
from typing import Optional
import numpy as np

from hed import load_schema_version
from hed.models import Sidecar
from neuroconv.basedatainterface import BaseDataInterface
from ndx_hed import HedLabMetaData, HedValueVector
from pydantic import FilePath
from pynwb import NWBFile
from pymatreader import read_mat


class M1MPTPTrialsInterface(BaseDataInterface):
    """
    Interface for converting trial structure and behavioral events to NWB format.

    TERMINOLOGY CHOICES:
    - center_target_appearance_time: Emphasizes discrete visual event (not "onset")
    - lateral_target_appearance_time: Matches experimental papers terminology
    - subject_movement_onset_time: Purposefully emphasizes subject's behavioral action
        vs. experimental setup events; distinguishes animal behavior from apparatus/stimuli
    - torque_perturbation_*: Scientific precision for stimulus parameters
    - derived_*: Movement parameters obtained from kinematic analysis post-processing
    - "onset" vs "appearance": "Onset" for events that initiate ongoing states (subject
        movement); "appearance" for punctual visual stimuli
    - Full names: "flexion"/"extension" not "flex"/"ext" for clarity
    """

    def __init__(
        self,
        file_path: FilePath,
        inter_trial_time_interval: float = 3.0,
        hed_sidecar_path: Optional[FilePath] = None,
        verbose: bool = False,
    ):
        super().__init__(verbose=verbose)
        self.file_path = Path(file_path)
        self.inter_trial_time_interval = inter_trial_time_interval

        # Default to assets/trials_hed_sidecar.json if not provided
        if hed_sidecar_path is None:
            self.hed_sidecar_path = Path(__file__).parent.parent / "assets" / "trials_hed_sidecar.json"
        else:
            self.hed_sidecar_path = Path(hed_sidecar_path)

    def _load_and_validate_hed_sidecar(self) -> tuple[dict, str]:
        """
        Load HED sidecar and validate all HED strings using hedtools Sidecar class.

        Returns
        -------
        tuple[dict, str]
            Tuple of (column_definitions, schema_version)
        """
        with open(self.hed_sidecar_path) as f:
            sidecar_data = json.load(f)

        # Extract metadata (schema version) from _metadata key
        metadata = sidecar_data.pop("_metadata", {})
        schema_version = metadata.get("hed_schema_version", "8.4.0")
        schema = load_schema_version(schema_version)

        # Validate entire sidecar using hedtools Sidecar class
        sidecar = Sidecar(str(self.hed_sidecar_path))
        issues = sidecar.validate(schema)
        if issues:
            raise ValueError(f"Invalid HED sidecar: {issues}")

        if self.verbose:
            print(f"Loaded and validated HED sidecar from {self.hed_sidecar_path}")

        return sidecar_data, schema_version

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None):
        # Load and validate HED sidecar (BIDS-compliant flat structure)
        columns, schema_version = self._load_and_validate_hed_sidecar()

        # Add HED schema metadata if not already present
        if "hed_schema" not in nwbfile.lab_meta_data:
            hed_metadata = HedLabMetaData(hed_schema_version=schema_version)
            nwbfile.add_lab_meta_data(hed_metadata)

        mat_data = read_mat(str(self.file_path))

        # STEP 1: Extract all Events data first
        events = mat_data["Events"]
        center_target_appearance_times = np.array(events["home_cue_on"]) / 1000.0
        lateral_target_appearance_times = np.array(events["targ_cue_on"]) / 1000.0
        target_directions = np.array(events["targ_dir"])
        cursor_departure_times = np.array(events["home_leave"]) / 1000.0
        reward_times = np.array(events["reward"]) / 1000.0
        n_trials = len(target_directions)

        # STEP 2: Add trial columns for Events data (using sidecar for HED definitions)
        nwbfile.add_trial_column(
            name="center_target_appearance_time",
            description=columns["center_target_appearance_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["center_target_appearance_time"]["HED"]
        )
        nwbfile.add_trial_column(
            name="lateral_target_appearance_time",
            description=columns["lateral_target_appearance_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["lateral_target_appearance_time"]["HED"]
        )
        nwbfile.add_trial_column(
            name="cursor_departure_time",
            description=columns["cursor_departure_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["cursor_departure_time"]["HED"]
        )
        nwbfile.add_trial_column(
            name="reward_time",
            description=columns["reward_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["reward_time"]["HED"]
        )

        # STEP 3: Extract in-trial stimulation data for isolation monitoring
        # Some sessions delivered single antidromic stimulation pulses early in trials
        # to activate otherwise silent neurons and verify recording isolation
        isolation_stim_times_raw = np.array(events.get("stim", [np.nan] * n_trials))
        isolation_stim_times = isolation_stim_times_raw / 1000.0  # Convert ms to seconds

        # Extract stimulation site from MATLAB string array in __function_workspace__
        # Only extract if there are any non-NaN stim times (i.e., stimulation was delivered)
        has_stim_data = np.any(~np.isnan(isolation_stim_times))
        if has_stim_data:
            from turner_lab_to_nwb.asap_m1_mptp.assets.matlab_utilities import (
                extract_stim_site_from_workspace,
            )
            isolation_stim_sites, extraction_error = extract_stim_site_from_workspace(
                self.file_path, n_trials
            )
            if extraction_error:
                # Fall back to empty strings if extraction fails
                isolation_stim_sites = [""] * n_trials
                if self.verbose:
                    print(f"Warning: Could not extract stim_site: {extraction_error}")
        else:
            # No stimulation in this session
            isolation_stim_sites = [""] * n_trials

        # Add columns for isolation monitoring stimulation
        nwbfile.add_trial_column(
            name="isolation_monitoring_stim_time",
            description=columns["isolation_monitoring_stim_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["isolation_monitoring_stim_time"]["HED"],
        )
        nwbfile.add_trial_column(
            name="isolation_monitoring_stim_site",
            description=columns["isolation_monitoring_stim_site"]["Description"],
        )

        # STEP 4: Process transformed Events variables to a tidy format
        flexion_perturbations = np.array(events.get("tq_flex", [np.nan] * n_trials))
        extension_perturbations = np.array(events.get("tq_ext", [np.nan] * n_trials))

        # Create movement_type array (flexion=1, extension=2 -> "flexion"/"extension")
        movement_type = ["flexion" if direction == 1 else "extension" for direction in target_directions]

        # Create torque_perturbation_type and torque_perturbation_onset_time arrays
        torque_perturbation_type = []
        torque_perturbation_onset_times = []

        for i in range(n_trials):
            # Check for flexion perturbation
            if not np.isnan(flexion_perturbations[i]):
                torque_perturbation_type.append("flexion")
                torque_perturbation_onset_times.append(flexion_perturbations[i] / 1000.0)
            # Check for extension perturbation
            elif not np.isnan(extension_perturbations[i]):
                torque_perturbation_type.append("extension")
                torque_perturbation_onset_times.append(extension_perturbations[i] / 1000.0)
            # No perturbation
            else:
                torque_perturbation_type.append("none")
                torque_perturbation_onset_times.append(np.nan)

        # Add trial columns for transformed Events variables (no HED for categorical labels)
        nwbfile.add_trial_column(
            name="movement_type",
            description="flexion or extension",
        )
        nwbfile.add_trial_column(
            name="torque_perturbation_type",
            description="direction of torque perturbation causing muscle stretch (flexion/extension/none)",
        )
        nwbfile.add_trial_column(
            name="torque_perturbation_onset_time",
            description=columns["torque_perturbation_onset_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["torque_perturbation_onset_time"]["HED"],
        )

        # STEP 5: Extract movement Mvt data
        movement_data = mat_data["Mvt"]
        derived_movement_onset_times = np.array(movement_data["onset_t"]) / 1000.0
        derived_movement_end_times = np.array(movement_data["end_t"]) / 1000.0
        derived_peak_velocities = np.array(movement_data["pkvel"])
        derived_peak_velocity_times = np.array(movement_data["pkvel_t"]) / 1000.0
        derived_end_positions = np.array(movement_data["end_posn"])
        derived_movement_amplitudes = np.array(movement_data["mvt_amp"])

        # STEP 6: Add trial columns for movement data (derived from kinematic analysis)
        nwbfile.add_trial_column(
            name="derived_movement_onset_time",
            description=columns["derived_movement_onset_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["derived_movement_onset_time"]["HED"]
        )
        nwbfile.add_trial_column(
            name="derived_movement_end_time",
            description=columns["derived_movement_end_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["derived_movement_end_time"]["HED"]
        )
        nwbfile.add_trial_column(
            name="derived_peak_velocity",
            description=columns["derived_peak_velocity"]["Description"],
            col_cls=HedValueVector,
            hed=columns["derived_peak_velocity"]["HED"]
        )
        nwbfile.add_trial_column(
            name="derived_peak_velocity_time",
            description=columns["derived_peak_velocity_time"]["Description"],
            col_cls=HedValueVector,
            hed=columns["derived_peak_velocity_time"]["HED"]
        )
        nwbfile.add_trial_column(
            name="derived_movement_amplitude",
            description=columns["derived_movement_amplitude"]["Description"],
            col_cls=HedValueVector,
            hed=columns["derived_movement_amplitude"]["HED"]
        )
        nwbfile.add_trial_column(
            name="derived_end_position",
            description=columns["derived_end_position"]["Description"],
            col_cls=HedValueVector,
            hed=columns["derived_end_position"]["HED"]
        )

        # STEP 7: Extract trial end times from Events['end'] field
        # The 'end' field contains experimental trial end timestamps (in ms)
        # This is more accurate than calculating from analog data length
        trial_end_times_relative = np.array(events.get("end", [])) / 1000.0  # Convert ms to seconds

        # Calculate trial start and stop times
        trial_start_times = []
        trial_stop_times = []
        current_time = 0.0

        for trial_index in range(n_trials):
            trial_start = current_time
            trial_duration = trial_end_times_relative[trial_index]
            trial_stop = trial_start + trial_duration

            trial_start_times.append(trial_start)
            trial_stop_times.append(trial_stop)

            # Next trial starts after inter-trial interval
            current_time = trial_stop + self.inter_trial_time_interval

        trial_start_times = np.array(trial_start_times)
        trial_stop_times = np.array(trial_stop_times)

        # Add trials to NWB file using processed arrays
        # CRITICAL: All event times must be offset by trial start time to align with session timeline
        for trial_index in range(n_trials):
            trial_start = trial_start_times[trial_index]

            # Calculate isolation monitoring stim time (offset by trial start, NaN if no stim)
            isolation_stim_time = isolation_stim_times[trial_index]
            if not np.isnan(isolation_stim_time):
                isolation_stim_time = trial_start + isolation_stim_time

            nwbfile.add_trial(
                start_time=trial_start,
                stop_time=trial_stop_times[trial_index],
                movement_type=movement_type[trial_index],
                center_target_appearance_time=trial_start + center_target_appearance_times[trial_index],
                lateral_target_appearance_time=trial_start + lateral_target_appearance_times[trial_index],
                cursor_departure_time=trial_start + cursor_departure_times[trial_index],
                reward_time=trial_start + reward_times[trial_index],
                torque_perturbation_type=torque_perturbation_type[trial_index],
                torque_perturbation_onset_time=trial_start + torque_perturbation_onset_times[trial_index] if not np.isnan(torque_perturbation_onset_times[trial_index]) else np.nan,
                derived_movement_onset_time=trial_start + derived_movement_onset_times[trial_index],
                derived_movement_end_time=trial_start + derived_movement_end_times[trial_index],
                derived_peak_velocity=derived_peak_velocities[trial_index],
                derived_peak_velocity_time=trial_start + derived_peak_velocity_times[trial_index],
                derived_movement_amplitude=derived_movement_amplitudes[trial_index],
                derived_end_position=derived_end_positions[trial_index],
                isolation_monitoring_stim_time=isolation_stim_time,
                isolation_monitoring_stim_site=isolation_stim_sites[trial_index],
            )

        if self.verbose:
            print(f"Added {n_trials} trials to NWB file")
            print(f"Flexion trials: {sum(target_directions == 1)}")
            print(f"Extension trials: {sum(target_directions == 2)}")
            n_stim_trials = np.sum(~np.isnan(isolation_stim_times))
            print(f"Trials with isolation monitoring stimulation: {n_stim_trials}")
            if n_stim_trials > 0:
                unique_sites = set(s for s in isolation_stim_sites if s)
                print(f"Stimulation sites: {unique_sites}")

        # STEP 8: Add invalid_times for inter-trial gaps
        # These gaps are ARTIFICIAL placeholders - the source data did not record inter-trial intervals.
        # This annotation allows downstream analysts to properly exclude gap periods from analysis.
        # See documentation/how_we_deal_with_trialized_data.md for details.
        if n_trials > 1:
            for trial_index in range(n_trials - 1):
                gap_start = trial_stop_times[trial_index]
                gap_stop = gap_start + self.inter_trial_time_interval
                nwbfile.add_invalid_time_interval(
                    start_time=gap_start,
                    stop_time=gap_stop,
                    tags=["artificial_inter_trial_gap", "not_recorded"],
                )

            if self.verbose:
                print(f"Added {n_trials - 1} invalid_times entries for inter-trial gaps")

        # Validate HED annotations in the trials table using HedNWBValidator
        # Import here to avoid requiring ndx-events as a top-level dependency
        from ndx_hed.utils.hed_nwb_validator import HedNWBValidator

        hed_metadata = nwbfile.lab_meta_data["hed_schema"]
        validator = HedNWBValidator(hed_metadata)
        issues = validator.validate_table(nwbfile.trials)
        if issues:
            raise ValueError(f"HED validation failed for trials table: {issues}")
