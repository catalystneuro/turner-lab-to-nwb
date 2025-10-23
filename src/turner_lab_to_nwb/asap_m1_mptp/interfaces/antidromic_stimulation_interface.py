from typing import Optional

from pydantic import FilePath
from pynwb import NWBFile, TimeSeries
from pynwb.ecephys import ElectricalSeries, DynamicTableRegion
from pynwb.file import TimeIntervals
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
        inter_sweep_interval: float = 0.1,
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
        inter_sweep_interval : float, optional
            Time interval in seconds between consecutive sweeps, by default 0.1 seconds
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.source_data = {"file_path": str(file_path)}
        self.antidromic_exploration_offset = antidromic_exploration_offset
        self.inter_sweep_interval = inter_sweep_interval
        self.session_metadata = session_metadata

        # Discover all unit files for this session (handles multi-unit sessions)
        from pathlib import Path
        base_path = Path(file_path)
        base_dir = base_path.parent
        base_name = base_path.stem.split('.')[0]  # e.g., "v1001" from "v1001.1.mat"

        # Collect all unit files and their data
        self.unit_files_data = []  # List of (unit_num, mat_data, available_stim_types)

        # Check for .1.mat and .2.mat files
        for unit_num in [1, 2]:
            unit_file_path = base_dir / f"{base_name}.{unit_num}.mat"
            if unit_file_path.exists():
                # Load MATLAB data
                mat_data = read_mat(str(unit_file_path))

                # Check which stimulation types are available
                available_stim_types = []
                stim_types = ["StrStim", "PedStim", "ThalStim", "STNStim"]
                for stim_type in stim_types:
                    if stim_type in mat_data:
                        available_stim_types.append(stim_type)

                # Only add if this unit has stimulation data
                if available_stim_types:
                    self.unit_files_data.append((unit_num, mat_data, available_stim_types))
                    if self.verbose:
                        print(f"Found antidromic data in Unit {unit_num}: {available_stim_types}")

        if self.verbose:
            print(f"Total units with antidromic data: {len(self.unit_files_data)}")

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

    def _parse_test_type_name(self, trace_name: str) -> str:
        """
        Convert trace name to CamelCase test type.

        Parameters
        ----------
        trace_name : str
            Original trace name like 'coll_5', 'ff_2', 'thal'

        Returns
        -------
        str
            CamelCase test type like 'Collision', 'FrequencyFollowing', 'Orthodromic'
        """
        if trace_name.startswith('coll_'):
            return 'Collision'
        elif trace_name.startswith('ff_'):
            return 'FrequencyFollowing'
        elif trace_name in ['thal', 'orthodromic']:
            return 'Orthodromic'
        else:
            # Unknown test type - use the raw name capitalized
            return trace_name.capitalize()

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add antidromic stimulation data to the NWB file.

        Each sweep is stored as a separate ElectricalSeries pair (response + stimulation).
        Naming convention: ElectricalSeries{TestType}{SweepNumber}{Site}{ResponseOrStimulation}
        Example: ElectricalSeriesCollision05StriatumResponse

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add stimulation data to
        metadata : dict, optional
            Metadata dictionary
        """
        if not self.unit_files_data:
            if self.verbose:
                print("No antidromic stimulation data found in this session")
            return

        # Get or create processing module for antidromic identification
        # For multi-unit sessions, multiple units may add data to the same module
        if "antidromic_identification" in nwbfile.processing:
            antidromic_module = nwbfile.processing["antidromic_identification"]
            if self.verbose:
                print("Adding to existing antidromic_identification module (multi-unit session)")
        else:
            antidromic_module = nwbfile.create_processing_module(
                name="antidromic_identification",
                description="Antidromic stimulation tests for neuron classification. "
                "Each sweep is stored as a separate ElectricalSeries pair (response + stimulation). "
                "Contains electrical stimulation current and neural response recordings (50ms sweeps at 20kHz) "
                "from chronically implanted electrodes used to identify pyramidal tract neurons (PTNs) "
                "and corticostriatal neurons (CSNs) via collision tests and frequency-following tests. "
                "For multi-unit sessions, data from multiple units are stored in the same module with "
                "unit numbers in the series names to distinguish them.",
            )

        # Get or create intervals table for antidromic sweeps
        # For multi-unit sessions, multiple units add to the same table
        if "TimeIntervalsAntidromicProtocol" not in nwbfile.intervals:
            antidromic_sweeps = TimeIntervals(
                name="TimeIntervalsAntidromicProtocol",
                description="Intervals table for antidromic stimulation sweeps. Each row represents one sweep "
                "with links to the corresponding stimulation current and neural response ElectricalSeries. "
                "Includes metadata about test type, stimulation location, and unit number. "
                "The 50ms sweeps are centered at t=0 (pulse_time), with 25ms pre-stimulation and 25ms post-stimulation windows.",
            )

            # Add custom columns in order: start_time, stop_time, stimulation_onset_time,
            # unit_name, location, stimulation_protocol, sweep_number,
            # response, stimulation, response_series_name, stimulation_series_name
            antidromic_sweeps.add_column(
                name="stimulation_onset_time",
                description="Time of electrical stimulation pulse delivery (t=0 in the original MATLAB sweep). "
                "The 50ms sweep extends from stimulation_onset_time-0.025s to stimulation_onset_time+0.025s. "
                "Corresponds to the center point of the sweep where the stimulation current is injected.",
            )
            antidromic_sweeps.add_column(
                name="unit_name",
                description="Unit number (1 or 2) from source filename, matching the unit_name in the units table",
            )
            antidromic_sweeps.add_column(
                name="location",
                description="Anatomical location of stimulation electrode: 'Striatum', 'Peduncle', 'Thalamus', or 'STN'",
            )
            antidromic_sweeps.add_column(
                name="stimulation_protocol",
                description="Antidromic stimulation protocol used: 'Collision' (paired spontaneous and antidromic spikes), "
                "'FrequencyFollowing' (high-frequency train), or 'Orthodromic' (sub-threshold control)",
            )
            antidromic_sweeps.add_column(
                name="sweep_number",
                description="Sweep index number from the original MATLAB data array (0-based)",
            )
            antidromic_sweeps.add_column(
                name="response",
                description="Reference to the ElectricalSeries containing neural voltage response (in volts) for this sweep",
            )
            antidromic_sweeps.add_column(
                name="stimulation",
                description="Reference to the TimeSeries containing stimulation current (in amperes) for this sweep",
            )
            antidromic_sweeps.add_column(
                name="response_series_name",
                description="Name of the ElectricalSeries containing neural voltage response for this sweep",
            )
            antidromic_sweeps.add_column(
                name="stimulation_series_name",
                description="Name of the TimeSeries containing stimulation current for this sweep",
            )

            nwbfile.add_time_intervals(antidromic_sweeps)
            if self.verbose:
                print("Created TimeIntervalsAntidromicProtocol intervals table")
        else:
            antidromic_sweeps = nwbfile.intervals["TimeIntervalsAntidromicProtocol"]
            if self.verbose:
                print("Adding to existing TimeIntervalsAntidromicProtocol table (multi-unit session)")

        # Calculate start time for antidromic data based on actual trial end times
        # Place antidromic data after all behavioral trials with a buffer
        if len(nwbfile.trials) > 0:
            # Find the maximum stop_time from all trials
            max_trial_stop_time = max(nwbfile.trials['stop_time'][:])
            # Add a buffer (e.g., 10 seconds) after the last trial
            buffer_after_trials = 10.0  # seconds
            stim_start_time = max_trial_stop_time + buffer_after_trials
            if self.verbose:
                print(f"Antidromic data start time: {stim_start_time:.1f}s (last trial ended at {max_trial_stop_time:.1f}s)")
        else:
            # Fallback to configured offset if no trials exist
            stim_start_time = self.antidromic_exploration_offset
            if self.verbose:
                print(f"No trials found, using configured offset: {stim_start_time:.1f}s")

        # Define electrode mapping (indices in the electrode table)
        electrode_map = {
            "recording": 0,     # M1 recording electrode
            "PedStim": 1,       # Cerebral peduncle stimulation
            "StrStim": 2,       # Putamen stimulation (use first of 3)
            "ThalStim": 5,      # VL thalamus stimulation
            "STNStim": 1,       # Use peduncle if STN data exists (fallback)
        }

        # Location name mapping
        location_map = {
            "PedStim": "Peduncle",
            "StrStim": "Striatum",
            "ThalStim": "Thalamus",
            "STNStim": "STN"
        }

        # Process each unit file that has stimulation data
        all_timestamps = []  # Collect for validation
        total_sweeps_added = 0

        for unit_num, mat_data, available_stim_types in self.unit_files_data:
            if self.verbose:
                print(f"\nProcessing Unit {unit_num} antidromic data...")

            # Process each available stimulation type for this unit
            for stim_index, stim_type in enumerate(available_stim_types):
                stim_data = mat_data[stim_type]

                # Extract data components
                unit_data = stim_data["Unit"]  # Shape: (n_samples, n_sweeps)
                if "Time" in stim_data:
                    time_data = stim_data["Time"]  # Shape: (n_samples,) - shared timebase
                elif "time" in stim_data:
                    time_data = stim_data["time"]
                else:
                    raise ValueError(f"No 'Time' field found in {stim_type} data")
                current_data = stim_data["Curr"]  # Shape: (n_samples, n_sweeps)
                trace_names = stim_data["TraceName"]  # List of test type labels

                # Data dimensions
                n_samples, n_sweeps = unit_data.shape

                # Get location name for this stimulation type
                location = location_map[stim_type]

                # Get electrode indices
                recording_electrode_index = electrode_map["recording"]

                # Create electrode table region for recording (used by ElectricalSeries response)
                # Note: Stimulation uses TimeSeries (not ElectricalSeries) so doesn't need electrode region
                recording_electrode_region = DynamicTableRegion(
                    name="electrodes",
                    data=[recording_electrode_index],
                    description="Recording electrode in M1",
                    table=nwbfile.electrodes
                )

                # Calculate sampling rate from time data
                # Time data is in milliseconds, convert to seconds
                time_seconds = time_data / 1000.0  # Convert ms to seconds
                n_samples = len(time_seconds)
                duration_seconds = time_seconds[-1] - time_seconds[0]
                sampling_rate = (n_samples - 1) / duration_seconds  # Hz

                if self.verbose:
                    print(f"  Calculated sampling rate: {sampling_rate:.2f} Hz from {n_samples} samples over {duration_seconds*1000:.2f} ms")

                # Process each sweep individually
                for sweep_idx in range(n_sweeps):
                    # Get test type for this sweep
                    trace_name = trace_names[sweep_idx]
                    test_type = self._parse_test_type_name(trace_name)

                    # Use sweep index for unique naming (trace names can have duplicates)
                    # Calculate starting time for this sweep
                    # Space stim types 1000s apart, sweeps within type by inter_sweep_interval
                    stim_type_offset = stim_index * 1000.0
                    sweep_offset = sweep_idx * self.inter_sweep_interval
                    sweep_start_time = stim_start_time + stim_type_offset + sweep_offset

                    # Calculate the actual starting time (accounting for the offset in original time data)
                    # time_seconds[0] is the offset from sweep_start_time (typically -0.025s)
                    starting_time = sweep_start_time + time_seconds[0]

                    # Extract data for this specific sweep
                    response_data = unit_data[:, sweep_idx].reshape(-1, 1)  # (n_samples, 1)
                    stim_current = current_data[:, sweep_idx].reshape(-1, 1)  # (n_samples, 1)

                    # Create unique names for this sweep
                    # Format: ElectricalSeries{Response|Stimulation}Unit{UnitNum}{TestType}{Location}Sweep{SweepIndex:02d}
                    # Location needed because sessions can have multiple stim sites (e.g., both Ped and Str)
                    # Use sweep_idx (not trace name number) because trace names can have duplicates
                    # Unit number from filename is critical for multi-unit sessions
                    series_name_base = f"Unit{unit_num}{test_type}{location}Sweep{sweep_idx:02d}"

                    # Create stimulation current series for this sweep
                    # Use TimeSeries (not ElectricalSeries) because units are amperes, not volts
                    #
                    # CALIBRATION NOTE: The conversion factor is estimated based on:
                    # 1. Metadata "Threshold" values range 1-1000 (likely µA based on typical antidromic stimulation)
                    # 2. Raw ADC int16 range: -16285 to +16628 counts
                    # 3. Assuming 16-bit ADC with ±10V range and gain similar to neural recordings
                    # 4. Estimated conversion: ~6.0e-08 A/count gives 0-1000 µA range (matches metadata)
                    #
                    # HOWEVER, the exact calibration is UNKNOWN (file_structure.md notes "Calibration tbd").
                    # Current conversion (1.526e-08) assumes 10000x gain and ±5V ADC based on:
                    # - LFP recordings documented as "10k gain" in same dataset
                    # - Standard neurophysiology recording system specifications
                    #
                    # TODO: Confirm with Turner lab - see email_communication.md Question 5
                    stim_series = TimeSeries(
                        name=f"TimeSeriesStimulation{series_name_base}",
                        description=f"{test_type} test sweep (index {sweep_idx}): Stimulation current delivered to {location.lower()}. "
                        f"50ms sweep centered on stimulation onset (t=0). "
                        f"Original trace name: '{trace_name}'. "
                        f"Data in amperes. CALIBRATION UNCERTAIN: conversion factor estimated from typical recording "
                        f"system specs (10000x gain, ±5V ADC). Awaiting confirmation from data authors. "
                        f"Time 0 = stimulation pulse delivery.",
                        data=stim_current,
                        starting_time=starting_time,
                        rate=sampling_rate,
                        unit="amperes",
                        conversion=1.526e-08,  # Estimated: (5V / 32768) / 10000 gain ≈ 1.526e-08 V/count
                        comments=f"Stimulation current trace in amperes. Conversion factor estimated pending lab confirmation.",
                    )

                    # Create neural response series for this sweep
                    #
                    # CALIBRATION NOTE: The conversion factor is estimated based on:
                    # 1. Typical extracellular spike amplitudes: 50-500 µV for well-isolated units
                    # 2. Raw ADC int16 range: -17568 to +17264 counts (peak-to-peak ~35k counts)
                    # 3. LFP recordings in same dataset documented as "10k gain"
                    # 4. Assuming same 10000x gain for unit recordings with ±5V ADC
                    # 5. Formula: conversion = (ADC_range / 2^15) / gain = (5V / 32768) / 10000
                    #
                    # This gives spike amplitudes of ~50-270 µV (realistic for extracellular recording).
                    # The exact calibration is UNKNOWN (file_structure.md notes "Calibration tbd").
                    #
                    # TODO: Confirm with Turner lab - see email_communication.md Question 5
                    response_series = ElectricalSeries(
                        name=f"ElectricalSeriesResponse{series_name_base}",
                        description=f"{test_type} test sweep (index {sweep_idx}): Neural response from M1 to {location.lower()} stimulation. "
                        f"50ms sweep at 20kHz centered on stimulation (t=0). "
                        f"Collision tests verify antidromic spike collision with spontaneous spikes. "
                        f"Frequency-following tests verify consistent latency at high stimulation rates. "
                        f"Original trace name: '{trace_name}'. "
                        f"Data in volts. CALIBRATION UNCERTAIN: conversion factor estimated from typical recording "
                        f"system specs (10000x gain, ±5V ADC) and documented 10k gain for LFP. Awaiting confirmation. "
                        f"Time 0 = stimulation pulse delivery.",
                        data=response_data,
                        starting_time=starting_time,
                        rate=sampling_rate,
                        electrodes=recording_electrode_region,
                        conversion=1.526e-08,  # Estimated: (5V / 32768) / 10000 gain ≈ 1.526e-08 V/count
                        comments=f"Neural voltage trace in volts. Conversion factor estimated pending lab confirmation.",
                    )

                    # Add to processing module
                    antidromic_module.add(stim_series)
                    antidromic_module.add(response_series)

                    # Add interval to the antidromic_sweeps table
                    # start_time and stop_time are calculated from starting_time and duration
                    start_time = starting_time
                    duration = (n_samples - 1) / sampling_rate  # Duration in seconds
                    stop_time = starting_time + duration
                    # stimulation_onset_time is the center of the sweep (t=0 in original MATLAB data)
                    stimulation_onset_time = sweep_start_time

                    antidromic_sweeps.add_interval(
                        start_time=start_time,
                        stop_time=stop_time,
                        sweep_number=sweep_idx,
                        stimulation_onset_time=stimulation_onset_time,
                        stimulation_series_name=stim_series.name,
                        response_series_name=response_series.name,
                        stimulation=stim_series,
                        response=response_series,
                        stimulation_protocol=test_type,
                        location=location,
                        unit_name=str(unit_num),  # Convert to string for consistency with units table
                    )

                    total_sweeps_added += 1

                if self.verbose:
                    # Count test types for this stimulation site
                    test_type_counts = {}
                    for tn in trace_names:
                        tt = self._parse_test_type_name(tn)
                        test_type_counts[tt] = test_type_counts.get(tt, 0) + 1

                    test_summary = ", ".join([f"{count} {ttype}" for ttype, count in test_type_counts.items()])
                    print(f"Added {stim_type} ({location}): {n_sweeps} sweeps ({test_summary}), {n_samples} samples each at 20kHz")

        if self.verbose:
            print(f"\nTotal: {total_sweeps_added} sweeps stored as {total_sweeps_added * 2} ElectricalSeries")
            print(f"Antidromic data placement: {stim_start_time:.1f}s - {stim_start_time + stim_type_offset + sweep_offset + 0.05:.1f}s")
            print(f"Inter-sweep interval: {self.inter_sweep_interval}s")