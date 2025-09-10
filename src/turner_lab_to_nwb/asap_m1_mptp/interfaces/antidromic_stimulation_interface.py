from typing import Optional

import numpy as np
from pydantic import FilePath
from pynwb import NWBFile
from pynwb.ecephys import ElectricalSeries, DynamicTableRegion
from pymatreader import read_mat

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict


class M1MPTPAntidromicStimulationInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP antidromic stimulation data."""

    keywords = ("antidromic stimulation", "cell type identification", "electrical stimulation")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP antidromic stimulation recordings used for neuron classification"

    def __init__(
        self,
        file_path: FilePath,
        session_metadata: dict,
        antidromic_exploration_offset: float = 4000.0,
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPAntidromicStimulationInterface.

        Parameters
        ----------
        file_path : FilePath
            Path to the Turner Lab .mat file
        session_metadata : dict
            Metadata for all units in this session
        antidromic_exploration_offset : float, optional
            Time offset in seconds to place antidromic stimulation data after behavioral trials
            to avoid timeline overlap, by default 4000.0 seconds
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.source_data = {"file_path": str(file_path)}
        self.antidromic_exploration_offset = antidromic_exploration_offset
        self.session_metadata = session_metadata
        
        # Load MATLAB data
        self.mat_data = read_mat(str(file_path))
        
        # Check which stimulation types are available
        self.available_stim_types = []
        stim_types = ["StrStim", "PedStim", "ThalStim", "STNStim"]
        for stim_type in stim_types:
            if stim_type in self.mat_data:
                self.available_stim_types.append(stim_type)
        
        if self.verbose and self.available_stim_types:
            print(f"Found antidromic stimulation data: {self.available_stim_types}")

    def get_metadata(self) -> DeepDict:
        """Get metadata for the NWB file."""
        return super().get_metadata()

    def _parse_test_types(self, trace_names: list) -> str:
        """
        Parse cryptic test type names into human-readable descriptions.
        
        Parameters
        ----------
        trace_names : list
            List of trace names like ['coll_1', 'ff_2', 'thal']
            
        Returns
        -------
        str
            Human-readable description of test types performed
        """
        if not trace_names:
            return "Test types: unknown"
            
        collision_tests = [name for name in trace_names if name.startswith('coll_')]
        frequency_tests = [name for name in trace_names if name.startswith('ff_')]
        orthodromic_tests = [name for name in trace_names if name in ['thal', 'orthodromic']]
        
        test_descriptions = []
        
        if collision_tests:
            test_descriptions.append(f"collision tests ({len(collision_tests)} sweeps)")
            
        if frequency_tests:
            test_descriptions.append(f"frequency-following tests ({len(frequency_tests)} sweeps)")
            
        if orthodromic_tests:
            test_descriptions.append(f"orthodromic activation tests ({len(orthodromic_tests)} sweeps)")
        
        if test_descriptions:
            return f"Tests performed: {', '.join(test_descriptions)}. " \
                   f"Collision tests verify antidromic spike collision with spontaneous spikes. " \
                   f"Frequency-following tests verify consistent latency at high stimulation rates."
        else:
            return f"Test types: {set(trace_names)}"

    def _validate_timestamps(self, timestamps_list: list) -> bool:
        """
        Validate that timestamps within the interface don't overlap.
        
        This method will be removed once we get data for monkey L to confirm
        the temporal structure is consistent across subjects.
        
        Parameters
        ----------
        timestamps_list : list
            List of timestamp arrays for different stimulation types
            
        Returns
        -------
        bool
            True if no overlaps detected, False otherwise
        """
        if len(timestamps_list) <= 1:
            return True
            
        # Sort all timestamps and check for overlaps
        all_timestamps = []
        for i, timestamps in enumerate(timestamps_list):
            for t in timestamps:
                all_timestamps.append((t, i))
        
        all_timestamps.sort()
        
        # Check for overlaps (timestamps from different series within 0.001s)
        for i in range(len(all_timestamps) - 1):
            t1, series1 = all_timestamps[i]
            t2, series2 = all_timestamps[i + 1]
            
            if series1 != series2 and abs(t2 - t1) < 0.001:  # 1ms tolerance
                if self.verbose:
                    print(f"Warning: Timestamp overlap detected at {t1:.3f}s between series {series1} and {series2}")
                return False
                
        return True

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add antidromic stimulation data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add stimulation data to
        metadata : dict, optional
            Metadata dictionary
        """
        if not self.available_stim_types:
            if self.verbose:
                print("No antidromic stimulation data found in this file")
            return

        # Create processing module for antidromic identification
        antidromic_module = nwbfile.create_processing_module(
            name="antidromic_identification",
            description="Antidromic stimulation tests for neuron classification. "
            "Contains electrical stimulation current and neural response recordings "
            "from chronically implanted electrodes used to identify pyramidal tract neurons (PTNs) "
            "and corticostriatal neurons (CSNs).",
        )

        # Use configured offset for stimulation data placement
        stim_start_time = self.antidromic_exploration_offset
        
        # Define electrode mapping (indices in the electrode table)
        electrode_map = {
            "recording": 0,     # M1 recording electrode
            "PedStim": 1,       # Cerebral peduncle stimulation 
            "StrStim": 2,       # Putamen stimulation (use first of 3)
            "ThalStim": 5,      # VL thalamus stimulation
            "STNStim": 1,       # Use peduncle if STN data exists (fallback)
        }

        # Process each available stimulation type with temporal separation
        all_timestamps = []  # Collect for validation
        
        for stim_index, stim_type in enumerate(self.available_stim_types):
            stim_data = self.mat_data[stim_type]
            
            # Extract data components
            unit_data = stim_data["Unit"]  # Shape: (1000, n_sweeps)
            time_data = stim_data.get("Time", stim_data["time"])  # Shape: (1000,)
            current_data = stim_data["Curr"]  # Shape: (1000, n_sweeps)
            trace_names = stim_data["TraceName"]
            
            # Data dimensions (consistent format)
            n_samples, n_sweeps = unit_data.shape
            
            # Space sweeps 0.1 seconds apart, space stim types 1000 seconds apart
            stim_type_offset = stim_index * 1000.0  # 1000s between different stim types
            sweep_intervals = np.arange(n_sweeps) * 0.1
            
            # Create timestamps - time_data matches samples, replicate for each sweep
            timestamps = []
            for sweep_index in range(n_sweeps):
                sweep_start = stim_start_time + stim_type_offset + sweep_intervals[sweep_index]
                sweep_times = sweep_start + (time_data / 1000.0)  # Convert ms to seconds
                timestamps.extend(sweep_times)
            timestamps = np.array(timestamps)
            
            # Flatten data and reshape for ElectricalSeries (time x channels)
            unit_data_flat = unit_data.flatten().reshape(-1, 1)
            current_data_flat = current_data.flatten().reshape(-1, 1)
            
            # Collect timestamps for validation
            all_timestamps.append(timestamps)
            
            # Get electrode indices
            stim_electrode_index = electrode_map[stim_type]
            recording_electrode_index = electrode_map["recording"]
            
            # Create electrode table regions
            stim_electrode_region = DynamicTableRegion(
                name="electrodes", 
                data=[stim_electrode_index], 
                description=f"Stimulation electrode for {stim_type}",
                table=nwbfile.electrodes
            )
            recording_electrode_region = DynamicTableRegion(
                name="electrodes", 
                data=[recording_electrode_index], 
                description="Recording electrode",
                table=nwbfile.electrodes
            )
            
            # Create stimulation current series
            location_map = {
                "PedStim": "Peduncle", 
                "StrStim": "Striatum", 
                "ThalStim": "Thalamus",
                "STNStim": "STN"
            }
            location = location_map[stim_type]
            
            stim_series = ElectricalSeries(
                name=f"ElectricalSeries{location}Stimulation",
                description=f"Stimulation current delivered to {location.lower()} for antidromic identification",
                data=current_data_flat,
                timestamps=timestamps,
                electrodes=stim_electrode_region,
                conversion=1e-6,  # Convert to microamps (common stimulation unit)
                comments="Stimulation current in microamperes",
            )
            
            # Parse and describe test types
            test_summary = self._parse_test_types(trace_names)
            
            # Create neural response series  
            response_series = ElectricalSeries(
                name=f"ElectricalSeries{location}Response",
                description=f"Neural response recorded from M1 during {location.lower()} stimulation. "
                f"Raw voltage traces (20kHz, 50ms sweeps) for antidromic identification. "
                f"{test_summary}",
                data=unit_data_flat,
                timestamps=timestamps,
                electrodes=recording_electrode_region,
                conversion=1e-6,  # Convert to microvolts (common neural recording unit)
                comments="Neural response voltage in microvolts",
            )
            
            # Add to processing module
            antidromic_module.add(stim_series)
            antidromic_module.add(response_series)
            
            if self.verbose:
                print(f"Added {stim_type} data: {n_sweeps} sweeps, {n_samples} samples each")
                if trace_names:
                    print(f"  {test_summary}")

        # Validate timestamps don't overlap
        if not self._validate_timestamps(all_timestamps):
            if self.verbose:
                print("Warning: Timestamp overlaps detected between stimulation types")
        
        if self.verbose:
            print(f"Antidromic stimulation data placed starting at {stim_start_time:.1f} seconds")
            if len(self.available_stim_types) > 1:
                print(f"Multiple stimulation types separated by 1000s intervals")