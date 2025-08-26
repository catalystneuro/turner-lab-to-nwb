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

    def __init__(self, file_path: FilePath, inter_trial_time_interval: float = 3.0, verbose: bool = False):
        """
        Initialize the M1MPTPSpikeTimesInterface.
        
        Parameters
        ----------
        file_path : FilePath
            Path to the Turner Lab .mat file containing spike data
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
        
        metadata["NWBFile"]["session_description"] = (
            f"Turner Lab MPTP motor cortex recording session from {self.file_path.stem}"
        )
        metadata["NWBFile"]["session_id"] = self.file_path.stem
        metadata["NWBFile"]["session_start_time"] = "1900-01-01T00:00:00"
        
        # Subject information
        metadata["Subject"] = {
            "subject_id": "unknown",
            "species": "Macaca mulatta",  # Macaque monkey
            "sex": "U",  # Unknown
            "description": "MPTP-treated parkinsonian macaque monkey"
        }
        
        return metadata

    def add_to_nwbfile(
        self, 
        nwbfile: NWBFile, 
        metadata: Optional[dict] = None,
        trial_start_times: Optional[np.ndarray] = None,
        cell_type: str = "unknown"
    ) -> None:
        """
        Add spike times to the NWB file as a Units table.
        
        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add data to
        metadata : dict, optional
            Metadata dictionary
        trial_start_times : np.ndarray, optional
            Array of trial start times in seconds. If provided, spike times will be 
            adjusted to global timeline. If None, assumes trials are concatenated
            with 2-second intervals.
        cell_type : str, optional
            Cell type classification ("PTN", "CSN", or "unknown"), by default "unknown"
        """
        if metadata is None:
            metadata = self.get_metadata()

        # Load MATLAB data
        mat_data = read_mat(str(self.file_path))
        
        # Validate required data fields
        if "unit_ts" not in mat_data:
            raise ValueError(f"Missing 'unit_ts' field in MATLAB file: {self.file_path}")

        # Load spike times matrix (trials x max_spikes_per_trial)
        spike_times_matrix = mat_data["unit_ts"]
        n_trials, max_spikes_per_trial = spike_times_matrix.shape
        
        if self.verbose:
            print(f"Loaded spike data: {n_trials} trials, max {max_spikes_per_trial} spikes/trial")

        # Generate trial start times if not provided
        if trial_start_times is None:
            trial_start_times = np.arange(n_trials) * self.inter_trial_time_interval
            if self.verbose:
                print(f"Using default inter-trial interval: {self.inter_trial_time_interval}s")

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

        # Add unit to NWB file
        if nwbfile.units is None:
            nwbfile.add_unit_column("cell_type", "Cell type classification (PTN/CSN/unknown)")
            nwbfile.add_unit_column("file_origin", "Source MATLAB file")

        # Add the single unit
        nwbfile.add_unit(
            spike_times=all_spike_times,
            cell_type=cell_type,
            file_origin=str(self.file_path.name)
        )

        if self.verbose:
            print(f"Added unit with {len(all_spike_times)} spikes, cell_type: {cell_type}")