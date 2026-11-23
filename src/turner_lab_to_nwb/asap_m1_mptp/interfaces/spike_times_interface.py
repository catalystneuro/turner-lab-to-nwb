from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pynwb import NWBFile
from pynwb.misc import Units
from pymatreader import read_mat

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict

from .trial_sources import get_trial_timeline, read_trial_source_files

class M1MPTPSpikeTimesInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP spike time data."""

    keywords = ("extracellular electrophysiology", "spike times", "single unit", "MPTP", "motor cortex")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP single unit spike timing data from MATLAB files"

    def __init__(
        self,
        units: list[dict],
        trial_sources: list[tuple[Path, int]],
        inter_trial_time_interval: float = 3.0,
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPSpikeTimesInterface.

        Parameters
        ----------
        units : list of dict
            One entry per unit, with "name" (source files, e.g. "v2701.1+v2702.2"), "metadata" (the unit's
            row of the metadata table), "spike_sources" ((unit .mat file, trial index in that file, session
            trial index) for every trial the unit was recorded in) and "electrode_indices"
        trial_sources : list of (Path, int)
            The session's trials in order, as (Turner Lab .mat file, trial index in that file)
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.units = units
        self.trial_sources = trial_sources
        self.inter_trial_time_interval = inter_trial_time_interval

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add spike times to the NWB file as a Units table, one row per unit of the session.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict
            Metadata with the units table description and column descriptions in metadata["Units"]
        """

        # Electrode table should already be created by electrodes interface

        # Session timeline: must match trials_interface.py exactly so obs_intervals align with trials
        trial_start_times, trial_durations = get_trial_timeline(
            read_trial_source_files(self.trial_sources), self.trial_sources, self.inter_trial_time_interval
        )

        units_metadata = metadata["Units"]
        if nwbfile.units is None:
            nwbfile.units = Units(name="units", description=units_metadata["description"])
            for name, description in units_metadata["columns"].items():
                nwbfile.add_unit_column(name, description)

        # Process each unit
        unit_mat_data = {}
        for unit in self.units:
            unit_meta = unit["metadata"]

            # Convert trial-based spike times to the session timeline, trial by trial
            all_spike_times = []
            obs_intervals = []
            for unit_file_path, file_trial, session_trial in unit["spike_sources"]:
                if unit_file_path not in unit_mat_data:
                    mat_data = read_mat(str(unit_file_path))
                    if "unit_ts" not in mat_data:
                        raise ValueError(f"Missing 'unit_ts' field in MATLAB file: {unit_file_path}")
                    spike_times_matrix = mat_data["unit_ts"]
                    if spike_times_matrix.ndim == 1:
                        # 1D format: one value per trial; convert to 2D for consistent processing
                        spike_times_matrix = spike_times_matrix.reshape(-1, 1)
                    elif spike_times_matrix.ndim != 2:
                        raise ValueError(
                            f"Unexpected unit_ts array dimensions: {spike_times_matrix.ndim}. Expected 1D or 2D array."
                        )
                    n_file_trials = len(np.atleast_1d(mat_data["Events"]["end"]))
                    if spike_times_matrix.shape[0] != n_file_trials:
                        raise ValueError(
                            f"{unit_file_path} has {spike_times_matrix.shape[0]} rows of unit_ts for {n_file_trials} trials"
                        )
                    unit_mat_data[unit_file_path] = (spike_times_matrix, mat_data["file_info"]["unit_fs"])

                spike_times_matrix, unit_fs = unit_mat_data[unit_file_path]

                # Spike times are stored on the unit sampling clock (unit_fs, 1 kHz in every file)
                if nwbfile.units.resolution is None:
                    nwbfile.units.resolution = 1.0 / unit_fs

                # Remove NaN values (padding), convert ms to s and add the trial start time
                trial_spikes = spike_times_matrix[file_trial, :]
                valid_spikes = trial_spikes[~np.isnan(trial_spikes)]
                all_spike_times.extend(valid_spikes / 1000.0 + trial_start_times[session_trial])

                # Observation interval: the unit was observable during this trial only. The source data
                # is trialized, so this lets analysts compute firing rates and ISIs correctly.
                # See documentation/how_we_deal_with_trialized_data.md for details.
                trial_start = trial_start_times[session_trial]
                obs_intervals.append([trial_start, trial_start + trial_durations[session_trial]])

            all_spike_times = np.array(sorted(all_spike_times))
            obs_intervals = np.array(sorted(obs_intervals))

            # Get cell type from metadata (used to determine neuron_projection_type)
            cell_type = unit_meta.get("Antidrom", "unknown")
            
            # Map antidromic classification to full neuron type names
            neuron_type_mapping = {
                "PED": "pyramidal_tract_neuron",
                "STRI": "corticostriatal_neuron",
                "NR": "no_response",
                "NT": "not_tested",
                "PED/STRI": "pyramidal_tract_and_corticostriatal_neuron",
                "PED/THAL": "pyramidal_tract_and_thalamic_neuron",
                "THAL": "thalamic_projection_neuron",
                "STN": "subthalamic_projection_neuron",
                "STN/STRI": "subthalamic_and_corticostriatal_neuron",
                "STN/THAL": "subthalamic_and_thalamic_neuron",
                "PED/STN": "pyramidal_tract_and_subthalamic_neuron",
            }
            neuron_projection_type = neuron_type_mapping.get(cell_type, "unknown")
            
            # Map stimulation sites to full anatomical names
            stim_data = unit_meta.get("StimData", "")
            stimulation_sites_mapping = {
                "Ped": "cerebral_peduncle",
                "Str": "posterolateral_striatum",
                "Ped/Str": "cerebral_peduncle_and_posterolateral_striatum",
                "STN": "subthalamic_nucleus",
                "Ped/STN": "cerebral_peduncle_and_subthalamic_nucleus",
            }
            if pd.isna(stim_data) or stim_data == "":
                antidromic_stimulation_sites = ""
            else:
                antidromic_stimulation_sites = stimulation_sites_mapping.get(stim_data, "")

            # Get antidromic response properties from metadata
            antidromic_latency = unit_meta.get("Latency", float("nan"))
            antidromic_threshold = unit_meta.get("Threshold", float("nan"))
            antidromic_latency_2 = unit_meta.get("LAT2", float("nan"))
            antidromic_threshold_2 = unit_meta.get("Thresh2", float("nan"))
            
            # Get receptive field properties from metadata
            rf_location_raw = unit_meta.get("SENSORY", "")
            rf_stimulus_raw = unit_meta.get("SENS_DETAIL", "")

            # Normalize receptive field location values for consistency
            if rf_location_raw == "NR":
                receptive_field_location = "no_response"
            elif rf_location_raw == "NT":
                receptive_field_location = "not_tested"
            elif pd.isna(rf_location_raw) or rf_location_raw == "":
                receptive_field_location = "not_tested"
            else:
                receptive_field_location = rf_location_raw.lower()  # Standardize case

            # Normalize receptive field stimulus values
            if rf_stimulus_raw in ["NR", "NT"] or pd.isna(rf_stimulus_raw) or rf_stimulus_raw == "":
                receptive_field_stimulus = rf_stimulus_raw if rf_stimulus_raw in ["NR", "NT"] else ""
            else:
                receptive_field_stimulus = rf_stimulus_raw  # Keep verbatim for richness

            # Determine MPTP treatment status (boolean)
            mptp_status = unit_meta.get("MPTP", "")
            is_post_mptp = mptp_status == "Post"

            # Add unit to NWB file, linked to the electrodes of the files it was recorded in
            nwbfile.add_unit(
                spike_times=all_spike_times,
                obs_intervals=obs_intervals,  # When unit was observable (trial boundaries only)
                electrodes=unit["electrode_indices"],
                neuron_projection_type=neuron_projection_type,
                antidromic_stimulation_sites=antidromic_stimulation_sites,
                antidromic_latency_ms=antidromic_latency,
                antidromic_threshold=antidromic_threshold,
                antidromic_latency_2_ms=antidromic_latency_2,
                antidromic_threshold_2=antidromic_threshold_2,
                receptive_field_location=receptive_field_location,
                receptive_field_stimulus=receptive_field_stimulus,
                unit_name=unit["name"],
                is_post_mptp=is_post_mptp,
            )

            if self.verbose:
                print(f"Added unit with {len(all_spike_times)} spikes")
