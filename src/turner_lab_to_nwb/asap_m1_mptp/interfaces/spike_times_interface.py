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
            Metadata for all units in this session
        inter_trial_time_interval : float, optional
            Time interval between trials in seconds, by default 3.0
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.base_file_path = Path(file_path)
        self.session_metadata = session_metadata
        self.inter_trial_time_interval = inter_trial_time_interval

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
            nwbfile.add_unit_column("file_origin", "Source MATLAB file")

        # Process each unit
        for unit_file_path, unit_meta in zip(unit_files, unit_metadata_list):
            # Load MATLAB data for this unit
            mat_data = read_mat(str(unit_file_path))

            # Validate required data fields
            if "unit_ts" not in mat_data:
                raise ValueError(f"Missing 'unit_ts' field in MATLAB file: {unit_file_path}")

            # Load spike times matrix (trials x max_spikes_per_trial)
            spike_times_matrix = mat_data["unit_ts"]
            n_trials, max_spikes_per_trial = spike_times_matrix.shape

            # Generate trial start times if not provided (should be same for all units in session)
            if trial_start_times is None:
                trial_start_times = np.arange(n_trials) * self.inter_trial_time_interval

            # Convert trial-based spike times to continuous timeline
            all_spike_times = []

            for trial_idx in range(n_trials):
                trial_spikes = spike_times_matrix[trial_idx, :]

                # Remove NaN values (padding)
                valid_spikes = trial_spikes[~np.isnan(trial_spikes)]

                if len(valid_spikes) > 0:
                    # Add trial start time offset
                    global_spike_times = valid_spikes + trial_start_times[trial_idx]
                    all_spike_times.extend(global_spike_times)

            # Sort all spike times
            all_spike_times = np.array(sorted(all_spike_times))

            # Get cell type from metadata
            cell_type = unit_meta.get("Antidrom", "unknown")
            unit_number = unit_meta.get("UnitNum1", 0)

            # Add unit to NWB file
            nwbfile.add_unit(
                spike_times=all_spike_times,
                cell_type=cell_type,
                unit_number=unit_number,
                file_origin=str(unit_file_path.name),
            )

            if self.verbose:
                print(f"Added unit {unit_number} with {len(all_spike_times)} spikes, cell_type: {cell_type}")
