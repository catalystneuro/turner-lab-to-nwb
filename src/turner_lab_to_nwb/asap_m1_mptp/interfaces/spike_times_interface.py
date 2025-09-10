from pathlib import Path
from typing import Optional

import numpy as np
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
                'Animal': first_unit['Animal'],
                'MPTP': first_unit['MPTP'],
                'DateCollected': first_unit['DateCollected'],
                'A_P': first_unit['A_P'],
                'M_L': first_unit['M_L'],
                'Depth': first_unit['Depth']
            }

    def get_metadata(self) -> DeepDict:
        """Get metadata for the NWB file."""
        metadata = super().get_metadata()

        metadata["NWBFile"][
            "session_description"
        ] = f"Turner Lab MPTP motor cortex recording session from {self.base_file_path.stem}"
        metadata["NWBFile"]["session_id"] = self.base_file_path.stem
        metadata["NWBFile"]["session_start_time"] = "1900-01-01T00:00:00"

        # Subject information
        metadata["Subject"] = {
            "subject_id": "unknown",
            "species": "Macaca mulatta",  # Macaque monkey
            "sex": "U",  # Unknown
            "description": "MPTP-treated parkinsonian macaque monkey",
        }

        return metadata

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

        # Create electrode table first (before adding units)
        device = nwbfile.create_device(
            name="DeviceMicroelectrodeSystem",
            description="Turner Lab microelectrode recording system: Glass-coated PtIr microelectrode "
                        "mounted in hydraulic microdrive (MO-95, Narishige Intl., Tokyo) within "
                        "cylindrical stainless steel recording chamber (35° coronal angle). "
                        "Signal amplified ×10⁴, bandpass filtered 0.3-10kHz. "
                        "Sampling: 20kHz for unit discrimination, 1kHz for analog/behavioral signals. "
                        "Chamber-relative coordinate system with sub-millimeter precision."
        )
        
        electrode_group = nwbfile.create_electrode_group(
            name="ElectrodeGroupM1Chamber", 
            description="Primary motor cortex (M1) electrode group within chamber-relative coordinate system. "
                        "Layer 5 pyramidal neurons targeted in arm representation area. "
                        "Chamber surgically positioned over left M1 using stereotactic atlas coordinates. "
                        "Daily electrode positions defined relative to chamber center/reference point. "
                        "Functional verification via microstimulation (≤40μA, 10 pulses at 300Hz). "
                        "Antidromic identification from cerebral peduncle (PTNs) and posterolateral striatum (CSNs).",
            location="Primary motor cortex (M1), arm area, Layer 5 - chamber coordinates",
            device=device
        )
        
        # Add custom columns for electrode insertion positions (chamber-relative coordinates)
        nwbfile.add_electrode_column(name="insertion_position_ap_mm", description="Electrode insertion position: Anterior-Posterior coordinate relative to chamber center (mm, positive = anterior)")
        nwbfile.add_electrode_column(name="insertion_position_ml_mm", description="Electrode insertion position: Medial-Lateral coordinate relative to chamber center (mm, positive = lateral)")
        nwbfile.add_electrode_column(name="insertion_position_depth_mm", description="Electrode insertion position: depth below chamber reference point (mm, positive = deeper)")
        
        # Add electrode with insertion positions as custom columns
        nwbfile.add_electrode(
            x=0.0,  # Use neutral coordinates for standard x,y,z
            y=0.0,
            z=0.0,
            imp=float('nan'),  # Electrode impedance not recorded
            location="Primary motor cortex (M1), arm area, Layer 5",
            filtering="0.3-10kHz bandpass for spikes, 1-100Hz for LFP when available",
            group=electrode_group,
            insertion_position_ap_mm=self.session_info['A_P'],
            insertion_position_ml_mm=self.session_info['M_L'],
            insertion_position_depth_mm=self.session_info['Depth']
        )

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
            nwbfile.add_unit_column("cell_type", "Cell type classification (PTN/CSN/NR/NT)")
            nwbfile.add_unit_column("unit_number", "Original unit number from recording")

        # Process each unit
        for unit_file_path, unit_meta in zip(unit_files, unit_metadata_list):
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
                n_trials, max_spikes_per_trial = spike_times_matrix.shape
            elif spike_times_matrix.ndim == 2:
                # 2D format: trials x max_spikes_per_trial (standard format)
                n_trials, max_spikes_per_trial = spike_times_matrix.shape
            else:
                raise ValueError(f"Unexpected unit_ts array dimensions: {spike_times_matrix.ndim}. Expected 1D or 2D array.")

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

            # Get cell type from metadata
            cell_type = unit_meta.get("Antidrom", "unknown")
            unit_number = unit_meta.get("UnitNum1", 0)

            # Add unit to NWB file - link to electrode index 0
            nwbfile.add_unit(
                spike_times=all_spike_times,
                electrodes=[0],  # Link to electrode index 0
                cell_type=cell_type,
                unit_number=unit_number,
            )

            if self.verbose:
                print(f"Added unit {unit_number} with {len(all_spike_times)} spikes, cell_type: {cell_type}")
