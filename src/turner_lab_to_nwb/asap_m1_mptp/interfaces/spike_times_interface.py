from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import FilePath
from pynwb import NWBFile
from pymatreader import read_mat

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict


class M1MPTPSpikeTimesInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP spike time data."""

    keywords = ("extracellular electrophysiology", "spike times", "single unit", "MPTP", "motor cortex")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP single unit spike timing data from MATLAB files"

    def __init__(
        self,
        file_path: FilePath,
        session_metadata: dict,
        inter_trial_time_interval: float = 3.0,
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPSpikeTimesInterface.

        Parameters
        ----------
        file_path : FilePath
            Path to the first Turner Lab .mat file (will check for additional units automatically)
        session_metadata : dict
            Metadata for all units in this session (each unit contains session-level info)
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.base_file_path = Path(file_path)
        self.session_metadata = session_metadata
        self.inter_trial_time_interval = inter_trial_time_interval

        # Extract session-level info from first unit (all units have same session info)
        if self.session_metadata:
            first_unit = self.session_metadata[0]
            self.session_info = {
                "Animal": first_unit["Animal"],
                "MPTP": first_unit["MPTP"],
                "DateCollected": first_unit["DateCollected"],
                "A_P": first_unit["A_P"],
                "M_L": first_unit["M_L"],
                "Depth": first_unit["Depth"],
            }


    def add_to_nwbfile(
        self, nwbfile: NWBFile, metadata: Optional[dict] = None, trial_start_times: Optional[np.ndarray] = None
    ) -> None:
        """
        Add spike times to the NWB file as a Units table. Automatically detects and loads
        multiple units from the same session.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict, optional
            Metadata dictionary
        trial_start_times : np.ndarray, optional
            Array of trial start times in seconds. If provided, spike times will be
            adjusted to global timeline. If None, assumes trials are concatenated
            with inter-trial intervals.
        """
        if metadata is None:
            metadata = self.get_metadata()

        # Electrode table should already be created by electrodes interface

        # Discover all unit files for this session
        base_name = self.base_file_path.stem.split(".")[0]  # e.g., "v5811" from "v5811.1.mat"
        base_dir = self.base_file_path.parent

        unit_files = []
        unit_metadata_list = []

        # Check for .1.mat and .2.mat files
        for unit_num in [1, 2]:
            unit_file_path = base_dir / f"{base_name}.{unit_num}.mat"
            if unit_file_path.exists():
                # Find metadata for this unit
                unit_meta = None
                for unit_info in self.session_metadata:
                    if unit_info["UnitNum1"] == unit_num:
                        unit_meta = unit_info
                        break

                if unit_meta:
                    unit_files.append(unit_file_path)
                    unit_metadata_list.append(unit_meta)

        if self.verbose:
            print(f"Found {len(unit_files)} unit files for session {base_name}")

        # Initialize units table if needed
        if nwbfile.units is None:
            nwbfile.add_unit_column(
                "neuron_projection_type",
                "Neuron classification based on projection target identified through antidromic stimulation: "
                "pyramidal_tract_neuron, corticostriatal_neuron, no_response, not_tested, "
                "pyramidal_tract_and_corticostriatal_neuron, pyramidal_tract_and_thalamic_neuron, "
                "thalamic_projection_neuron",
            )
            nwbfile.add_unit_column(
                "antidromic_stimulation_sites",
                "Anatomical sites where antidromic stimulation was performed during recording session: "
                "cerebral_peduncle, posterolateral_striatum, cerebral_peduncle_and_posterolateral_striatum, "
                "or empty string if no stimulation was attempted",
            )
            nwbfile.add_unit_column(
                "antidromic_latency_ms",
                "Antidromic response latency in milliseconds for primary stimulation site",
            )
            nwbfile.add_unit_column(
                "antidromic_threshold",
                "Stimulation threshold for antidromic response at primary stimulation site",
            )
            nwbfile.add_unit_column(
                "antidromic_latency_2_ms",
                "Antidromic response latency in milliseconds for secondary stimulation site (if applicable)",
            )
            nwbfile.add_unit_column(
                "antidromic_threshold_2",
                "Stimulation threshold for antidromic response at secondary stimulation site (if applicable)",
            )
            nwbfile.add_unit_column(
                "sensory_region",
                "General body region where sensory responsiveness was observed: "
                "hand, wrist, elbow, forearm, shoulder, finger, mixed regions (e.g., hand/wrist), "
                "no_response, not_tested",
            )
            nwbfile.add_unit_column(
                "sensory_detail",
                "Detailed description of the sensory stimulus or manipulation that elicited response: "
                "proprioceptive manipulations, tactile stimulations, active movements, or descriptive combinations",
            )
            nwbfile.add_unit_column(
                "unit_name",
                "Unit identifier from source MATLAB filename (1 or 2 for multi-unit sessions)",
            )
            nwbfile.add_unit_column(
                "related_session_id",
                "Session ID of related recording session where this same neuron was recorded again. "
                "Value is 'none' if the unit was not re-recorded in another session, or the full session_id "
                "(format: {Animal}{FName}++{MPTP}++Depth{depth}um++{date}) of the continuation session if it exists. "
                "This links neurons that were recorded across multiple sessions at the same electrode location.",
            )

        # Process each unit
        for unit_file_path, unit_meta in zip(unit_files, unit_metadata_list):
            # Extract unit number from filename (e.g., "v1001.1.mat" -> 1)
            from pathlib import Path
            unit_num = int(Path(unit_file_path).stem.split('.')[1])

            # Load MATLAB data for this unit
            mat_data = read_mat(str(unit_file_path))

            # Validate required data fields
            if "unit_ts" not in mat_data:
                raise ValueError(f"Missing 'unit_ts' field in MATLAB file: {unit_file_path}")

            # Load spike times matrix - handle both 1D and 2D formats
            spike_times_matrix = mat_data["unit_ts"]

            if spike_times_matrix.ndim == 1:
                # 1D format: one value per trial (or two values per trial for different conditions)
                # Convert to 2D format for consistent processing
                if self.verbose:
                    print(f"Converting 1D unit_ts array (shape {spike_times_matrix.shape}) to 2D format")
                spike_times_matrix = spike_times_matrix.reshape(-1, 1)  # Each row is a trial with 1 spike max
                n_trials, _ = spike_times_matrix.shape
            elif spike_times_matrix.ndim == 2:
                # 2D format: trials x max_spikes_per_trial (standard format)
                n_trials, _ = spike_times_matrix.shape
            else:
                raise ValueError(
                    f"Unexpected unit_ts array dimensions: {spike_times_matrix.ndim}. Expected 1D or 2D array."
                )

            # Generate trial start times if not provided (should be same for all units in session)
            if trial_start_times is None:
                # Use analog-based trial durations (same approach as trials_interface.py)
                analog_data = mat_data["Analog"]

                # Get actual trial durations from analog data
                trial_durations = []
                for trial_index in range(n_trials):
                    trial_analog = analog_data["x"][trial_index]
                    duration_s = len(trial_analog) / 1000.0  # 1kHz sampling, convert to seconds
                    trial_durations.append(duration_s)

                # Create trial start times with inter-trial intervals
                trial_start_times = []
                current_time = 0.0

                for trial_index in range(n_trials):
                    trial_start_times.append(current_time)
                    current_time += trial_durations[trial_index] + self.inter_trial_time_interval

                trial_start_times = np.array(trial_start_times)

            # Convert trial-based spike times to continuous timeline
            all_spike_times = []

            for trial_idx in range(n_trials):
                trial_spikes = spike_times_matrix[trial_idx, :]

                # Remove NaN values (padding)
                valid_spikes = trial_spikes[~np.isnan(trial_spikes)]

                if len(valid_spikes) > 0:
                    # Convert from milliseconds to seconds and add trial start time offset
                    global_spike_times = (valid_spikes / 1000.0) + trial_start_times[trial_idx]
                    all_spike_times.extend(global_spike_times)

            # Sort all spike times
            all_spike_times = np.array(sorted(all_spike_times))

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
                "THAL": "thalamic_projection_neuron"
            }
            neuron_projection_type = neuron_type_mapping.get(cell_type, "unknown")
            
            # Map stimulation sites to full anatomical names
            stim_data = unit_meta.get("StimData", "")
            stimulation_sites_mapping = {
                "Ped": "cerebral_peduncle",
                "Str": "posterolateral_striatum",
                "Ped/Str": "cerebral_peduncle_and_posterolateral_striatum"
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
            
            # Get sensory receptive field properties from metadata
            sensory_region_raw = unit_meta.get("SENSORY", "")
            sensory_detail_raw = unit_meta.get("SENS_DETAIL", "")
            
            # Normalize sensory region values for consistency
            if sensory_region_raw == "NR":
                sensory_region = "no_response"
            elif sensory_region_raw == "NT":
                sensory_region = "not_tested"
            elif pd.isna(sensory_region_raw) or sensory_region_raw == "":
                sensory_region = "not_tested"
            else:
                sensory_region = sensory_region_raw.lower()  # Standardize case
            
            # Normalize sensory detail values
            if sensory_detail_raw in ["NR", "NT"] or pd.isna(sensory_detail_raw) or sensory_detail_raw == "":
                sensory_detail = sensory_detail_raw if sensory_detail_raw in ["NR", "NT"] else ""
            else:
                sensory_detail = sensory_detail_raw  # Keep verbatim for richness

            # Determine related_session_id for cross-referenced recordings
            # If FName2 and UnitNum2 are present, this unit continues in another session
            fname2 = unit_meta.get("FName2", "")
            unitnum2 = unit_meta.get("UnitNum2", float("nan"))

            if pd.notna(fname2) and fname2 != "" and pd.notna(unitnum2):
                # This unit has a cross-reference to another session
                # Construct the related session_id using the same format as current session
                from datetime import datetime

                # Get metadata for constructing session_id
                animal = unit_meta.get("Animal", "V")
                mptp_condition = unit_meta.get("MPTP", "Pre")
                date_str = unit_meta.get("DateCollected", "")
                depth_mm = unit_meta.get("Depth", 0.0)

                # Format date from "29-Jul-1999" to "19990729"
                if date_str and date_str != "NaT" and not pd.isna(date_str):
                    try:
                        date_obj = datetime.strptime(date_str, "%d-%b-%Y")
                        formatted_date = date_obj.strftime("%Y%m%d")
                    except:
                        formatted_date = "NA"
                else:
                    formatted_date = "NA"

                # Convert depth to micrometers
                depth_um = int(depth_mm * 1000) if pd.notna(depth_mm) else 0

                # Extract filename code from FName2 (everything after 'v' prefix)
                fname2_code = fname2[1:] if fname2.startswith('v') else fname2

                # Construct related session_id
                mptp_str = f"{mptp_condition}MPTP"
                related_session_id = f"{animal}{fname2_code}++{mptp_str}++Depth{depth_um}um++{formatted_date}"
            else:
                # No cross-reference for this unit
                related_session_id = "none"

            # Add unit to NWB file - link to electrode index 0
            nwbfile.add_unit(
                spike_times=all_spike_times,
                electrodes=[0],  # Link to electrode index 0
                neuron_projection_type=neuron_projection_type,
                antidromic_stimulation_sites=antidromic_stimulation_sites,
                antidromic_latency_ms=antidromic_latency,
                antidromic_threshold=antidromic_threshold,
                antidromic_latency_2_ms=antidromic_latency_2,
                antidromic_threshold_2=antidromic_threshold_2,
                sensory_region=sensory_region,
                sensory_detail=sensory_detail,
                unit_name=unit_num,
                related_session_id=related_session_id,
            )

            if self.verbose:
                print(f"Added unit with {len(all_spike_times)} spikes")
