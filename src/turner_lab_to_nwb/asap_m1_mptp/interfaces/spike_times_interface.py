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
                "Classification of layer 5 M1 neurons based on axonal projection target, determined through "
                "antidromic activation (electrical stimulation at target sites evoking backward-traveling spikes). "
                "Values: "
                "| 'pyramidal_tract_neuron': Large layer 5b neurons projecting to spinal cord via corticospinal "
                "tract, identified by cerebral peduncle stimulation (latency 0.6-2.5 ms) "
                "| 'corticostriatal_neuron': Intratelencephalic-type neurons projecting to posterolateral putamen, "
                "identified by striatal stimulation (latency 2.0-20 ms) "
                "| 'no_response': Antidromic stimulation attempted at one or both sites but neuron did not respond "
                "| 'not_tested': Antidromic identification was not performed for this neuron "
                "| 'pyramidal_tract_and_corticostriatal_neuron': Dual-projecting neuron responding to both sites "
                "| 'pyramidal_tract_and_thalamic_neuron': Neuron projecting to both pyramidal tract and thalamus "
                "| 'thalamic_projection_neuron': Neuron projecting to thalamus",
            )
            nwbfile.add_unit_column(
                "antidromic_stimulation_sites",
                "Anatomical sites where antidromic stimulation was delivered via chronically implanted electrodes "
                "to identify neuron projection targets. "
                "Values: "
                "| 'cerebral_peduncle': Stimulation of corticospinal tract fibers to identify pyramidal tract "
                "neurons (100-400 uA, 0.2 ms biphasic pulses) "
                "| 'posterolateral_striatum': Stimulation of putamen to identify corticostriatal neurons "
                "(100-600 uA, 0.2 ms biphasic pulses) "
                "| 'cerebral_peduncle_and_posterolateral_striatum': Both stimulation sites were tested "
                "| '': Empty string indicates antidromic testing was not attempted for this neuron",
            )
            nwbfile.add_unit_column(
                "antidromic_latency_ms",
                "Latency from stimulation to antidromic spike arrival at the recording electrode (in milliseconds) "
                "for the primary stimulation site. Reflects axon conduction velocity: PTNs have shorter latencies "
                "(0.6-2.5 ms) due to large, fast-conducting axons; CSNs have longer latencies (2.0-20 ms) due to "
                "smaller axons. Classification required fixed latency, high-frequency following (>200 Hz), and "
                "collision test confirmation.",
            )
            nwbfile.add_unit_column(
                "antidromic_threshold",
                "Minimum stimulation current (in microamps) required to reliably evoke antidromic activation at "
                "the primary stimulation site. Lower thresholds indicate electrode proximity to the axon or larger "
                "axon diameter. Typical ranges: 100-400 uA for cerebral peduncle, 100-600 uA for striatum.",
            )
            nwbfile.add_unit_column(
                "antidromic_latency_2_ms",
                "Antidromic response latency (in milliseconds) from secondary stimulation site, for neurons with "
                "dual projections (e.g., pyramidal_tract_and_corticostriatal_neuron). NaN if not applicable.",
            )
            nwbfile.add_unit_column(
                "antidromic_threshold_2",
                "Minimum stimulation current (in microamps) for antidromic activation at the secondary stimulation "
                "site. NaN if neuron does not have dual projections or secondary site was not tested.",
            )
            nwbfile.add_unit_column(
                "receptive_field_location",
                "Body region comprising this neuron's somatosensory receptive field, determined through qualitative "
                "sensorimotor examination. The experimenter manually manipulated the monkey's contralateral arm "
                "(passive joint movement, skin contact) while monitoring neural activity on an audio speaker. "
                "Values: "
                "| 'hand': Receptive field on the hand "
                "| 'wrist': Receptive field at the wrist joint "
                "| 'elbow': Receptive field at the elbow joint "
                "| 'forearm': Receptive field on the forearm "
                "| 'shoulder': Receptive field at the shoulder "
                "| 'finger': Receptive field on digit(s) "
                "| Combinations (e.g., 'hand / wrist'): Neuron responds to multiple body regions "
                "| 'no_response': Sensory testing performed but no response detected "
                "| 'not_tested': Sensory mapping not performed (limited recording time)",
            )
            nwbfile.add_unit_column(
                "receptive_field_stimulus",
                "Specific sensory stimulus or manipulation that activated this neuron during qualitative receptive "
                "field mapping (qualitative observer assessment, not quantified). "
                "Values: "
                "| 'ext': Joint extension (proprioceptive) "
                "| 'flex': Joint flexion (proprioceptive) "
                "| 'pron': Forearm pronation (proprioceptive) "
                "| 'sup': Forearm supination (proprioceptive) "
                "| 'light touch': Light tactile stimulation "
                "| 'palm probe': Pressure on palm "
                "| 'finger tap': Tapping on digit(s) "
                "| 'cut stim': Cutaneous (skin) stimulation "
                "| 'active': Firing during voluntary movement "
                "| 'active grip': Firing during voluntary grip "
                "| 'active hand': Firing during voluntary hand movement "
                "| Combinations (e.g., 'finger ext & elbow ext'): Multi-joint responses "
                "| 'NR': No response to any stimulus tested "
                "| 'NT': Sensory testing not performed "
                "| '': Testing data not recorded",
            )
            nwbfile.add_unit_column(
                "unit_name",
                "Unit identifier extracted from source MATLAB filename. When multiple well-isolated single units "
                "were recorded simultaneously during the same electrode penetration, each was saved separately. "
                "Most sessions contain a single unit. "
                "Values: "
                "| 1: First (or only) unit from this session, from file '{session}.1.mat' "
                "| 2: Second unit from this session, from file '{session}.2.mat'",
            )
            nwbfile.add_unit_column(
                "unit_also_in_session_id",
                "Cross-reference to another NWB session containing recordings from this same neuron, identified "
                "by the experimenter based on waveform similarity and recording location during the same electrode "
                "penetration. Empty string if this unit was only recorded in one session. Format matches session_id: "
                "{subject_id}++{fname}++{Pre|Post}MPTP++Depth{um}um++{YYYYMMDD}. This enables tracking individual "
                "neurons across multiple recording sessions or experimental conditions.",
            )
            nwbfile.add_unit_column(
                "is_post_mptp",
                "Boolean indicating parkinsonian state at time of recording. MPTP "
                "(1-methyl-4-phenyl-1,2,3,6-tetrahydropyridine) was administered once via unilateral left internal "
                "carotid artery injection (0.5 mg/kg), inducing selective dopaminergic cell death in the ipsilateral "
                "substantia nigra and producing stable contralateral hemiparkinsonian symptoms. Comparing pre/post "
                "recordings reveals how parkinsonism affects cortical motor encoding, particularly in pyramidal "
                "tract neurons. "
                "Values: "
                "| False: Pre-MPTP baseline recording (healthy motor control) "
                "| True: Post-MPTP recording after parkinsonian symptoms stabilized (bradykinesia, rigidity, "
                "movement initiation deficits)",
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
                # Use Events['end'] for trial durations - MUST match trials_interface.py exactly
                # to ensure obs_intervals align with trial boundaries.
                # Note: Events['end'] is slightly longer than analog data length (~5ms) because
                # analog recording may stop before the official trial end. Some spikes can occur
                # in this gap, so we use Events['end'] to capture all valid spikes.
                events = mat_data["Events"]
                trial_durations = np.array(events.get("end", [])) / 1000.0  # Convert ms to seconds

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

            # Compute observation intervals: when this unit was observable (trial boundaries only)
            # The source data is trialized - we only have data during trials, not inter-trial intervals.
            # This annotation allows downstream analysts to correctly compute firing rates and ISIs.
            # See documentation/how_we_deal_with_trialized_data.md for details.
            obs_intervals = []
            for trial_index in range(n_trials):
                trial_start = trial_start_times[trial_index]
                trial_duration = trial_durations[trial_index]
                obs_intervals.append([trial_start, trial_start + trial_duration])
            obs_intervals = np.array(obs_intervals)

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

            # Determine unit_also_in_session_id for cross-referenced recordings
            # If FName2 and UnitNum2 are present, this unit was also recorded in another session
            fname2 = unit_meta.get("FName2", "")
            unitnum2 = unit_meta.get("UnitNum2", float("nan"))

            if pd.notna(fname2) and fname2 != "" and pd.notna(unitnum2):
                # This unit has a cross-reference to another session
                # Construct session_id using same format as conversion_script.py
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

                # Construct session_id: {Animal}++{fname}++{MPTP}MPTP++Depth{um}um++{YYYYMMDD}
                mptp_str = f"{mptp_condition}MPTP"
                unit_also_in_session_id = f"{animal}++{fname2}++{mptp_str}++Depth{depth_um}um++{formatted_date}"
            else:
                # No cross-reference for this unit
                unit_also_in_session_id = ""

            # Determine MPTP treatment status (boolean)
            mptp_status = unit_meta.get("MPTP", "")
            is_post_mptp = mptp_status == "Post"

            # Add unit to NWB file - link to electrode index 0
            nwbfile.add_unit(
                spike_times=all_spike_times,
                obs_intervals=obs_intervals,  # When unit was observable (trial boundaries only)
                electrodes=[0],  # Link to electrode index 0
                neuron_projection_type=neuron_projection_type,
                antidromic_stimulation_sites=antidromic_stimulation_sites,
                antidromic_latency_ms=antidromic_latency,
                antidromic_threshold=antidromic_threshold,
                antidromic_latency_2_ms=antidromic_latency_2,
                antidromic_threshold_2=antidromic_threshold_2,
                receptive_field_location=receptive_field_location,
                receptive_field_stimulus=receptive_field_stimulus,
                unit_name=unit_num,
                unit_also_in_session_id=unit_also_in_session_id,
                is_post_mptp=is_post_mptp,
            )

            if self.verbose:
                print(f"Added unit with {len(all_spike_times)} spikes")
