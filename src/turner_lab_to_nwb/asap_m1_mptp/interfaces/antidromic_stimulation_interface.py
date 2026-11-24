import re
from pathlib import Path
from typing import Optional

import numpy as np
from pynwb import NWBFile, TimeSeries, register_map
from pynwb.ecephys import ElectricalSeries
from pynwb.file import TimeIntervals
from pynwb.base import TimeSeriesReferenceVectorData, TimeSeriesReference
from pynwb.io.core import VectorDataMap
from pymatreader import read_mat

from neuroconv._temporal_alignment import _TemporalAlignment
from neuroconv.basedatainterface import BaseDataInterface


# Workaround for hdmf >= 6.0: columns added with add_column are built with the
# generic VectorData spec, which drops the compound dtype. Remove once fixed upstream.
@register_map(TimeSeriesReferenceVectorData)
class TimeSeriesReferenceVectorDataMap(VectorDataMap):
    def build(self, *args, **kwargs):
        kwargs.pop("matched_spec", None)
        return super().build(*args, **kwargs)


# Every sweep label (TraceName) in the source files, without its trailing sweep number, mapped to the
# stimulation protocol. Labels that name the stimulation site instead of the test are "unspecified".
STIMULATION_PROTOCOL_BY_LABEL = {
    "coll": "Collision",
    "COLL": "Collision",
    "col": "Collision",
    "coll]": "Collision",
    "ff": "FrequencyFollowing",
    "FF": "FrequencyFollowing",
    "FREQ": "FrequencyFollowing",
    "freqf": "FrequencyFollowing",
    "ortho": "Orthodromic",
    "thalstim": "unspecified",
    "thstin": "unspecified",
    "thal": "unspecified",
    "pedstim": "unspecified",
    "cpstim": "unspecified",
    "ped": "unspecified",
    "putstim": "unspecified",
    "stim": "unspecified",
}

# The stimulation site of each kind of sweep in the source files, as named in the series and the sweeps table
SWEEP_LOCATION_BY_STIM_TYPE = {"PedStim": "Peduncle", "StrStim": "Striatum", "ThalStim": "Thalamus", "STNStim": "STN"}

# The source has no clock time for the sweeps: each series is placed this many seconds after the previous one
SERIES_SPACING = 1000.0


class M1MPTPAntidromicStimulationInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP antidromic stimulation data."""

    keywords = ("antidromic stimulation", "cell type identification", "electrical stimulation")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP antidromic stimulation recordings used for neuron classification"

    def __init__(
        self,
        units: list[dict],
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPAntidromicStimulationInterface.

        Parameters
        ----------
        units : list of dict
            One entry per unit, with "name" and "antidromic_files": (.mat file, recording electrode index)
            pairs for the unit's own file, the file it continues in, and the file of any dropped copy of the unit
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)

        # Collect the stimulation data of every unit, from its own file, the file it continues in and any dropped copy
        self.unit_files_data = []  # List of (unit, file_label, electrode_index, mat_data, available_stim_types)
        for unit in units:
            for unit_file_path, electrode_index in unit["antidromic_files"]:
                mat_data = read_mat(str(unit_file_path))

                # Check which stimulation types are available
                stim_types = ["StrStim", "PedStim", "ThalStim", "STNStim"]
                available_stim_types = [stim_type for stim_type in stim_types if stim_type in mat_data]

                # Only add if this file has stimulation data
                if available_stim_types:
                    file_label = Path(unit_file_path).name.removesuffix(".mat")  # e.g. "v1001.1"
                    self.unit_files_data.append((unit, file_label, electrode_index, mat_data, available_stim_types))
                    if self.verbose:
                        print(f"Found antidromic data for unit {unit['name']} in {file_label}: {available_stim_types}")

        if self.verbose:
            print(f"Total files with antidromic data: {len(self.unit_files_data)}")

        # Collect all sweep data per (file_label, stim_type) combination
        # Data structure: {(file_label, stim_type): {'unit': dict, 'responses': [], 'stimuli': [], 'metadata': [], 'time_data': array}}
        self._collected_data = {}
        self._series_index = {}  # Track global ordering for time offsets (ensures ascending start_times)
        global_stim_counter = 0
        # A file that continues a unit can store copies of sweeps already in an earlier file of the unit
        seen_sweeps = {}  # (unit name, stim_type) -> set of sweep bytes

        for unit, file_label, electrode_index, mat_data, available_stim_types in self.unit_files_data:
            for stim_idx, stim_type in enumerate(available_stim_types):
                key = (file_label, stim_type)
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

                seen = seen_sweeps.setdefault((unit["name"], stim_type), set())
                new_sweep_indices = []
                for sweep_idx in range(n_sweeps):
                    sweep_bytes = unit_data[:, sweep_idx].tobytes() + current_data[:, sweep_idx].tobytes()
                    if sweep_bytes not in seen:
                        seen.add(sweep_bytes)
                        new_sweep_indices.append(sweep_idx)
                if not new_sweep_indices:
                    continue

                self._series_index[key] = global_stim_counter
                global_stim_counter += 1

                # Initialize collection for this key
                self._collected_data[key] = {
                    'unit': unit,
                    'electrode_index': electrode_index,
                    'responses': [],
                    'stimuli': [],
                    'metadata': [],
                    'time_data': time_data,
                    'n_samples_per_sweep': n_samples,
                }

                # Collect each sweep's data and metadata
                for sweep_idx in new_sweep_indices:
                    trace_name = trace_names[sweep_idx]
                    test_type = self._parse_test_type_name(trace_name)

                    self._collected_data[key]['responses'].append(unit_data[:, sweep_idx])
                    self._collected_data[key]['stimuli'].append(current_data[:, sweep_idx])
                    self._collected_data[key]['metadata'].append({
                        'sweep_index': sweep_idx,
                        'trace_name': trace_name,
                        'test_type': test_type,
                    })

        # Alignment by composition (see neuroconv/_temporal_alignment.py), one time-bearing object per series, named
        # like the series. Native times run from 0, each series SERIES_SPACING after the previous one; the converter
        # shifts them all to after the trials.
        self.temporal_alignment = _TemporalAlignment()
        for (file_label, stim_type), data in self._collected_data.items():
            time_seconds = data["time_data"] / 1000.0
            sampling_rate = (data["n_samples_per_sweep"] - 1) / (time_seconds[-1] - time_seconds[0])
            number_of_samples = data["n_samples_per_sweep"] * len(data["metadata"])
            # The first sweep's first sample, time_seconds[0] from its stimulation onset
            start_time = self._series_index[(file_label, stim_type)] * SERIES_SPACING + time_seconds[0]
            self.temporal_alignment._add_time_bearing_object(
                key=f"{file_label}_{SWEEP_LOCATION_BY_STIM_TYPE[stim_type]}",
                get_native_times=lambda start_time=start_time, rate=sampling_rate, n=number_of_samples: (
                    start_time + np.arange(n) / rate
                ),
                default_start_time=start_time,
                get_number_of_samples=lambda n=number_of_samples: n,
            )

    def _parse_test_type_name(self, trace_name: str) -> str:
        """
        Map a sweep label to its stimulation protocol with STIMULATION_PROTOCOL_BY_LABEL.

        Parameters
        ----------
        trace_name : str
            Sweep label in the source file, like 'coll_5', 'FF_2', 'thalstim_0'

        Returns
        -------
        str
            'Collision', 'FrequencyFollowing', 'Orthodromic' or 'unspecified'
        """
        label = re.fullmatch(r"(.+)_\d+", trace_name)
        if label is None or label.group(1) not in STIMULATION_PROTOCOL_BY_LABEL:
            raise ValueError(f"Unknown antidromic sweep label {trace_name!r}")
        return STIMULATION_PROTOCOL_BY_LABEL[label.group(1)]

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
        metadata : dict
            Metadata with the module, table and series text in "AntidromicIdentification" and the monkey's
            stimulation electrodes in "StimulationElectrodes"
        """
        if not self.unit_files_data:
            if self.verbose:
                print("No antidromic stimulation data found in this session")
            return

        antidromic_metadata = metadata["AntidromicIdentification"]
        module_metadata = antidromic_metadata["ProcessingModule"]
        if module_metadata["name"] in nwbfile.processing:
            antidromic_module = nwbfile.processing[module_metadata["name"]]
        else:
            antidromic_module = nwbfile.create_processing_module(**module_metadata)

        # Add stimulation electrodes table (only when antidromic data exists)
        self._add_stimulation_electrodes_table(antidromic_module, metadata=metadata)

        sweeps_metadata = antidromic_metadata["SweepsTable"]
        if sweeps_metadata["name"] not in nwbfile.intervals:
            antidromic_sweeps = TimeIntervals(name=sweeps_metadata["name"], description=sweeps_metadata["description"])
            columns = sweeps_metadata["columns"]
            for name in ("stimulation_onset_time", "unit_name"):
                antidromic_sweeps.add_column(name=name, description=columns[name])
            antidromic_sweeps.add_column(name="unit", description=columns["unit"], table=nwbfile.units)
            for name in ("location", "stimulation_protocol", "source_label", "sweep_number"):
                antidromic_sweeps.add_column(name=name, description=columns[name])
            # TimeSeriesReferenceVectorData columns for response and stimulation
            for name in ("response", "stimulation"):
                antidromic_sweeps.add_column(
                    name=name, description=columns[name], col_cls=TimeSeriesReferenceVectorData
                )
            antidromic_sweeps.add_column(
                name="stimulation_electrode", description=columns["stimulation_electrode"]
            )

            nwbfile.add_time_intervals(antidromic_sweeps)
            if self.verbose:
                print("Created AntidromicSweepsIntervals intervals table with TimeSeriesReferenceVectorData columns")
        else:
            antidromic_sweeps = nwbfile.intervals[sweeps_metadata["name"]]
            if self.verbose:
                print("Adding to existing AntidromicSweepsIntervals table (multi-unit session)")

        # Each stimulation type's row in the StimulationElectrodesTable
        stimulation_electrodes = metadata["StimulationElectrodes"]["electrodes"]
        stim_electrode_index_map = {
            electrode["stim_type"]: row for row, electrode in enumerate(stimulation_electrodes) if electrode["stim_type"]
        }

        # Create consolidated series and intervals
        total_sweeps_added = 0
        series_count = 0
        units_table_row = {unit_name: row for row, unit_name in enumerate(nwbfile.units["unit_name"][:])}

        for (file_label, stim_type), data in self._collected_data.items():
            unit_name = data['unit']['name']
            location = SWEEP_LOCATION_BY_STIM_TYPE[stim_type]
            stim_electrode_index = stim_electrode_index_map[stim_type]

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

            # The first sample of the series, as the converter placed it
            first_sweep_starting_time = self.temporal_alignment[f"{file_label}_{location}"].get_times()[0]

            # Create electrode table region for recording
            response_metadata = antidromic_metadata["ResponseSeries"]
            recording_electrode_region = nwbfile.create_electrode_table_region(
                region=[data['electrode_index']],
                description=response_metadata["electrodes_description"],
            )

            text_fields = dict(
                file_label=file_label,
                location=location,
                location_lower=location.lower(),
                unit_name=unit_name,
                n_sweeps=n_sweeps,
                n_samples_per_sweep=n_samples_per_sweep,
            )
            comments = antidromic_metadata["series_comments"].format(**text_fields)

            # Create consolidated response series.
            # conversion = 10 V / 2**16 / 10000 = 1.526e-8 V/count (range / bits / amp gain).
            # The signed int16 data are already centered at 0, so no offset is needed.
            response_series = ElectricalSeries(
                name=response_metadata["name"].format(**text_fields),
                description=response_metadata["description"].format(**text_fields),
                data=all_responses,
                starting_time=first_sweep_starting_time,
                rate=sampling_rate,
                electrodes=recording_electrode_region,
                conversion=1.526e-08,
                comments=comments,
            )

            # Create consolidated stimulation series
            stimulation_metadata = antidromic_metadata["StimulationSeries"]
            stim_series = TimeSeries(
                name=stimulation_metadata["name"].format(**text_fields),
                description=stimulation_metadata["description"].format(**text_fields),
                data=all_stimuli,
                starting_time=first_sweep_starting_time,
                rate=sampling_rate,
                unit="amperes",
                conversion=1.526e-08,
                comments=comments,
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

                # The sweeps are stored back to back, so each sweep's times follow from its first sample
                interval_start_time = first_sweep_starting_time + index_start / sampling_rate
                interval_stop_time = interval_start_time + duration_seconds
                stimulation_onset_time = interval_start_time - time_seconds[0]  # t=0 for this sweep

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
                    unit_name=unit_name,
                    unit=units_table_row[unit_name],
                    location=location,
                    stimulation_protocol=sweep_metadata['test_type'],
                    source_label=sweep_metadata['trace_name'],
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
                print(f"Added {file_label} {location}: {n_sweeps} sweeps ({test_summary}), "
                      f"{n_samples_per_sweep} samples each at {sampling_rate:.0f}Hz")

        if self.verbose:
            print(f"\nTotal: {total_sweeps_added} sweeps indexed in {series_count} consolidated series")
            print(f"(Previously would have created {total_sweeps_added * 2} separate series)")

    def _add_stimulation_electrodes_table(self, antidromic_module, metadata: dict) -> None:
        """
        Add the table of the monkey's chronically implanted stimulation electrodes, metadata["StimulationElectrodes"],
        to the antidromic_identification processing module. Its rows are in the order of that list.
        """
        from hdmf.common import DynamicTable, VectorData

        table_metadata = metadata["AntidromicIdentification"]["StimulationElectrodesTable"]
        if table_metadata["name"] in antidromic_module.data_interfaces:
            return

        stimulation_electrodes = metadata["StimulationElectrodes"]
        electrodes = stimulation_electrodes["electrodes"]
        columns = {
            "location": [electrode["location"] for electrode in electrodes],
            "device_name": [electrode["name"] for electrode in electrodes],
            "n_contacts": [electrode["n_contacts"] for electrode in electrodes],
            "notes": [electrode["notes"] for electrode in electrodes],
        }
        stim_electrodes_table = DynamicTable(
            name=table_metadata["name"],
            description=table_metadata["description"].format(row_summary=stimulation_electrodes["row_summary"]),
            columns=[
                VectorData(name=name, description=table_metadata["columns"][name], data=data)
                for name, data in columns.items()
            ],
        )
        antidromic_module.add(stim_electrodes_table)
