from typing import Optional

import numpy as np
from pydantic import FilePath
from pynwb import NWBFile, TimeSeries
from pynwb.ecephys import ElectricalSeries
from pynwb.file import TimeIntervals
from pynwb.base import TimeSeriesReferenceVectorData, TimeSeriesReference
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

        Uses consolidated series approach: one response series and one stimulation series
        per unit/location combination, with TimeSeriesReferenceVectorData in the intervals
        table to reference specific sweep segments within each series.

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
        if "antidromic_identification" in nwbfile.processing:
            antidromic_module = nwbfile.processing["antidromic_identification"]
            if self.verbose:
                print("Adding to existing antidromic_identification module (multi-unit session)")
        else:
            antidromic_module = nwbfile.create_processing_module(
                name="antidromic_identification",
                description="Antidromic stimulation tests for neuron classification. "
                "Contains consolidated electrical stimulation and neural response recordings "
                "(50ms sweeps at 20kHz) from chronically implanted electrodes used to identify "
                "pyramidal tract neurons (PTNs) and corticostriatal neurons (CSNs) via collision "
                "tests and frequency-following tests. Data is organized as one response series "
                "and one stimulation series per unit/location combination, with the intervals "
                "table (AntidromicSweepsIntervals) providing TimeSeriesReference columns to "
                "access individual sweeps within the consolidated series.",
            )

        # Add stimulation electrodes table (only when antidromic data exists)
        self._add_stimulation_electrodes_table(antidromic_module)

        # Get or create intervals table for antidromic sweeps
        if "AntidromicSweepsIntervals" not in nwbfile.intervals:
            antidromic_sweeps = TimeIntervals(
                name="AntidromicSweepsIntervals",
                description="Intervals table for antidromic stimulation sweeps. Each row represents one sweep "
                "with TimeSeriesReference columns linking to specific sample ranges within the consolidated "
                "response and stimulation series. Use the 'response' and 'stimulation' columns to extract "
                "data for individual sweeps. Filter by 'stimulation_protocol', 'location', or 'unit_name' "
                "to select specific sweep types. The 50ms sweeps are centered at t=0 (pulse_time), with "
                "25ms pre-stimulation and 25ms post-stimulation windows.",
            )

            # Add custom columns
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
                description="Sweep index number within the series for this unit/location combination (0-based)",
            )
            # TimeSeriesReferenceVectorData columns for response and stimulation
            antidromic_sweeps.add_column(
                name="response",
                description="Reference to neural voltage response segment for this sweep. Contains (idx_start, count, timeseries) "
                "tuple pointing to the specific sample range within the consolidated response ElectricalSeries. "
                "Access data with: series.data[idx_start:idx_start+count] * series.conversion",
                col_cls=TimeSeriesReferenceVectorData,
            )
            antidromic_sweeps.add_column(
                name="stimulation",
                description="Reference to stimulation current segment for this sweep. Contains (idx_start, count, timeseries) "
                "tuple pointing to the specific sample range within the consolidated stimulation TimeSeries. "
                "Access data with: series.data[idx_start:idx_start+count] * series.conversion",
                col_cls=TimeSeriesReferenceVectorData,
            )
            antidromic_sweeps.add_column(
                name="stimulation_electrode",
                description="Index into StimulationElectrodesTable indicating which electrode delivered the stimulation",
            )

            nwbfile.add_time_intervals(antidromic_sweeps)
            if self.verbose:
                print("Created AntidromicSweepsIntervals intervals table with TimeSeriesReferenceVectorData columns")
        else:
            antidromic_sweeps = nwbfile.intervals["AntidromicSweepsIntervals"]
            if self.verbose:
                print("Adding to existing AntidromicSweepsIntervals table (multi-unit session)")

        # Calculate start time for antidromic data based on actual trial end times
        if len(nwbfile.trials) > 0:
            max_trial_stop_time = max(nwbfile.trials['stop_time'][:])
            buffer_after_trials = 10.0  # seconds
            base_start_time = max_trial_stop_time + buffer_after_trials
            if self.verbose:
                print(f"Antidromic data start time: {base_start_time:.1f}s (last trial ended at {max_trial_stop_time:.1f}s)")
        else:
            base_start_time = self.antidromic_exploration_offset
            if self.verbose:
                print(f"No trials found, using configured offset: {base_start_time:.1f}s")

        # Define electrode mapping
        recording_electrode_index = 0  # M1 recording electrode in nwbfile.electrodes

        location_map = {
            "PedStim": "Peduncle",
            "StrStim": "Striatum",
            "ThalStim": "Thalamus",
            "STNStim": "STN"
        }

        stim_electrode_index_map = {
            "PedStim": 0,   # Peduncle
            "StrStim": 1,   # Putamen (use first of 3 as representative)
            "ThalStim": 4,  # Thalamus
            "STNStim": 0,   # Fallback to peduncle
        }

        # =====================================================================
        # FIRST PASS: Collect all sweep data per (unit_num, stim_type) combination
        # =====================================================================
        # Data structure: {(unit_num, stim_type): {'responses': [], 'stimuli': [], 'metadata': [], 'time_data': array}}
        collected_data = {}
        stim_type_index = {}  # Track stim type ordering for time offsets

        for unit_num, mat_data, available_stim_types in self.unit_files_data:
            for stim_idx, stim_type in enumerate(available_stim_types):
                key = (unit_num, stim_type)
                stim_type_index[key] = stim_idx

                stim_data = mat_data[stim_type]

                # Extract data components
                unit_data = stim_data["Unit"]  # Shape: (n_samples, n_sweeps)
                if "Time" in stim_data:
                    time_data = stim_data["Time"]
                elif "time" in stim_data:
                    time_data = stim_data["time"]
                else:
                    raise ValueError(f"No 'Time' field found in {stim_type} data")
                current_data = stim_data["Curr"]  # Shape: (n_samples, n_sweeps)
                trace_names = stim_data["TraceName"]  # List of test type labels

                n_samples, n_sweeps = unit_data.shape

                # Initialize collection for this key
                collected_data[key] = {
                    'responses': [],
                    'stimuli': [],
                    'metadata': [],
                    'time_data': time_data,
                    'n_samples_per_sweep': n_samples,
                }

                # Collect each sweep's data and metadata
                for sweep_idx in range(n_sweeps):
                    trace_name = trace_names[sweep_idx]
                    test_type = self._parse_test_type_name(trace_name)

                    collected_data[key]['responses'].append(unit_data[:, sweep_idx])
                    collected_data[key]['stimuli'].append(current_data[:, sweep_idx])
                    collected_data[key]['metadata'].append({
                        'sweep_index': sweep_idx,
                        'trace_name': trace_name,
                        'test_type': test_type,
                    })

        # =====================================================================
        # SECOND PASS: Create consolidated series and intervals
        # =====================================================================
        total_sweeps_added = 0
        series_count = 0

        for (unit_num, stim_type), data in collected_data.items():
            location = location_map[stim_type]
            stim_electrode_index = stim_electrode_index_map[stim_type]
            stim_idx = stim_type_index[(unit_num, stim_type)]

            # Concatenate all sweeps into single arrays
            # Note: ElectricalSeries needs 2D data (n_samples, n_channels) for neuroconv compatibility
            all_responses = np.concatenate(data['responses']).reshape(-1, 1)  # Shape: (total_samples, 1)
            all_stimuli = np.concatenate(data['stimuli'])  # Shape: (total_samples,) - TimeSeries can be 1D
            n_samples_per_sweep = data['n_samples_per_sweep']
            n_sweeps = len(data['metadata'])

            # Calculate timing information
            time_data = data['time_data']
            time_seconds = time_data / 1000.0  # Convert ms to seconds
            duration_seconds = time_seconds[-1] - time_seconds[0]
            sampling_rate = (n_samples_per_sweep - 1) / duration_seconds  # Hz

            # Calculate starting time for this unit/stim_type combination
            # Space different stim types 1000s apart, sweeps within by inter_sweep_interval
            stim_type_offset = stim_idx * 1000.0
            series_start_time = base_start_time + stim_type_offset

            # The sweep data starts at time_seconds[0] relative to stimulation onset
            # For rate-based series, we set starting_time to the first sample's absolute time
            first_sweep_starting_time = series_start_time + time_seconds[0]

            # Create electrode table region for recording
            recording_electrode_region = nwbfile.create_electrode_table_region(
                region=[recording_electrode_index],
                description="Recording electrode in M1",
            )

            # Create consolidated response series
            response_series = ElectricalSeries(
                name=f"AntidromicResponseUnit{unit_num}{location}",
                description=f"Consolidated neural responses from M1 to {location.lower()} stimulation for Unit {unit_num}. "
                f"Contains {n_sweeps} concatenated 50ms sweeps at 20kHz. Each sweep is {n_samples_per_sweep} samples. "
                f"Use the AntidromicSweepsIntervals table to access individual sweeps via TimeSeriesReference. "
                f"Data in volts. CALIBRATION UNCERTAIN: conversion factor estimated from typical recording "
                f"system specs (10000x gain, +/-5V ADC). Awaiting confirmation from data authors.",
                data=all_responses,
                starting_time=first_sweep_starting_time,
                rate=sampling_rate,
                electrodes=recording_electrode_region,
                conversion=1.526e-08,  # Estimated: (5V / 32768) / 10000 gain
                comments=f"Concatenated sweeps for Unit {unit_num}, {location} stimulation. "
                f"Sweep boundaries every {n_samples_per_sweep} samples.",
            )

            # Create consolidated stimulation series
            stim_series = TimeSeries(
                name=f"AntidromicStimulationUnit{unit_num}{location}",
                description=f"Consolidated stimulation currents delivered to {location.lower()} for Unit {unit_num}. "
                f"Contains {n_sweeps} concatenated 50ms sweeps at 20kHz. Each sweep is {n_samples_per_sweep} samples. "
                f"Use the AntidromicSweepsIntervals table to access individual sweeps via TimeSeriesReference. "
                f"Data in amperes. CALIBRATION UNCERTAIN: conversion factor estimated.",
                data=all_stimuli,
                starting_time=first_sweep_starting_time,
                rate=sampling_rate,
                unit="amperes",
                conversion=1.526e-08,  # Estimated
                comments=f"Concatenated sweeps for Unit {unit_num}, {location} stimulation. "
                f"Sweep boundaries every {n_samples_per_sweep} samples.",
            )

            # Add series to processing module
            antidromic_module.add(response_series)
            antidromic_module.add(stim_series)
            series_count += 2

            # Add intervals for each sweep within this consolidated series
            for sweep_index, sweep_metadata in enumerate(data['metadata']):
                # Calculate sample indices within the concatenated array
                index_start = sweep_index * n_samples_per_sweep
                count = n_samples_per_sweep

                # Calculate timing for this sweep
                sweep_offset = sweep_index * self.inter_sweep_interval
                sweep_start_time = series_start_time + sweep_offset
                stimulation_onset_time = sweep_start_time  # t=0 for this sweep

                # The actual start_time for the interval (25ms before stim onset)
                interval_start_time = stimulation_onset_time + time_seconds[0]
                interval_stop_time = stimulation_onset_time + time_seconds[-1]

                # Create TimeSeriesReference tuples
                response_ref = TimeSeriesReference(
                    idx_start=index_start,
                    count=count,
                    timeseries=response_series,
                )
                stim_ref = TimeSeriesReference(
                    idx_start=index_start,
                    count=count,
                    timeseries=stim_series,
                )

                antidromic_sweeps.add_interval(
                    start_time=interval_start_time,
                    stop_time=interval_stop_time,
                    stimulation_onset_time=stimulation_onset_time,
                    unit_name=str(unit_num),
                    location=location,
                    stimulation_protocol=sweep_metadata['test_type'],
                    sweep_number=sweep_index,
                    response=response_ref,
                    stimulation=stim_ref,
                    stimulation_electrode=stim_electrode_index,
                )
                total_sweeps_added += 1

            if self.verbose:
                # Count test types for this unit/location
                test_type_counts = {}
                for m in data['metadata']:
                    tt = m['test_type']
                    test_type_counts[tt] = test_type_counts.get(tt, 0) + 1
                test_summary = ", ".join([f"{count} {ttype}" for ttype, count in test_type_counts.items()])
                print(f"Added Unit{unit_num}{location}: {n_sweeps} sweeps ({test_summary}), "
                      f"{n_samples_per_sweep} samples each at {sampling_rate:.0f}Hz")

        if self.verbose:
            print(f"\nTotal: {total_sweeps_added} sweeps indexed in {series_count} consolidated series")
            print(f"(Previously would have created {total_sweeps_added * 2} separate series)")

    def _add_stimulation_electrodes_table(self, antidromic_module) -> None:
        """
        Add stimulation electrodes table to the antidromic_identification processing module.

        This table documents the chronically implanted macroelectrodes used for antidromic
        neuron identification.

        Parameters
        ----------
        antidromic_module : ProcessingModule
            The antidromic_identification processing module
        """
        from hdmf.common import DynamicTable, VectorData

        # Only add the table once (check if it already exists)
        if "StimulationElectrodesTable" in antidromic_module.data_interfaces:
            return

        # Create stimulation electrodes table
        stim_electrodes_table = DynamicTable(
            name="StimulationElectrodesTable",
            description="Chronically implanted macroelectrodes for antidromic neuron identification. "
            "These electrodes were surgically implanted and present for all recording sessions, "
            "though antidromic testing was not performed for every recorded neuron. "
            "Used to classify M1 neurons as PTNs (peduncle), CSNs (putamen), or thalamocortical neurons (thalamus). "
            "Row indices: 0=peduncle, 1-3=putamen (3 electrodes), 4=thalamus.",
            columns=[
                VectorData(
                    name="location",
                    description="Anatomical location of stimulation site",
                    data=[
                        "Cerebral peduncle (pre-pontine)",
                        "Putamen (posterolateral)",
                        "Putamen (posterolateral)",
                        "Putamen (posterolateral)",
                        "Ventrolateral thalamus",
                    ],
                ),
                VectorData(
                    name="device_name",
                    description="Name of the device in nwbfile.devices",
                    data=[
                        "DeviceMicrowirePeduncleStimulation",
                        "DeviceMicrowirePutamenStimulation1",
                        "DeviceMicrowirePutamenStimulation2",
                        "DeviceMicrowirePutamenStimulation3",
                        "DeviceMicrowireThalamicStimulation",
                    ],
                ),
                VectorData(
                    name="notes",
                    description="Additional electrode-specific notes",
                    data=[
                        "Ventral to substantia nigra, arm-responsive pre-pontine region. For PTN identification.",
                        "Electrode 1 of 3, posterolateral putamen for M1 CSN projections. Used as representative electrode reference for all StrStim data.",
                        "Electrode 2 of 3, posterolateral putamen for M1 CSN projections. Physical electrode documented but not distinguished in source data.",
                        "Electrode 3 of 3, posterolateral putamen for M1 CSN projections. Physical electrode documented but not distinguished in source data.",
                        "VL thalamus for thalamocortical projection identification.",
                    ],
                ),
            ],
        )

        antidromic_module.add(stim_electrodes_table)
