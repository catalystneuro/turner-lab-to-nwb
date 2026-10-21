"""Group the source MATLAB files into NWB sessions.

The lab sometimes recorded one neuron across two files on the same day, and the metadata table
links them through FName2/UnitNum2. Files linked this way become one session, named after the
first file. The session's trials are the first file's trials followed by each later file's trials,
leaving out trials that repeat a trial of an earlier file.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from pymatreader import read_mat

# A "b" file whose trials all repeat its first file also stores a unit of the first file a second
# time, with identical spikes, under its own table row. The copy is dropped; its stimulation sweeps
# go to the unit that is kept, and where the kept row only says "not tested", the copy's tested
# antidromic label is used.
DUPLICATE_UNITS = {
    "v4527b.2": "v4527.2",
    "v5812.2": "v5811.2",
}
ANTIDROMIC_LABEL_COLUMNS = ("Antidrom", "StimData", "Latency", "Threshold", "LAT2", "Thresh2")


def get_trial_keys(events: dict) -> list[tuple]:
    """
    One key per trial built from every per-trial Events field, to find trials shared by two files.

    The stimulation fields are left out: some files store a copy of a trial with stimulation times
    that the other copy lacks (v4401b), or without the stim field at all (v5101b, v5203b).
    """
    n_trials = len(np.atleast_1d(events["end"]))
    fields = [
        np.atleast_1d(np.asarray(events[name], dtype=float))
        for name in sorted(events)
        if name not in ("stim", "stim_site") and np.size(events[name]) == n_trials
    ]
    return [
        tuple("nan" if np.isnan(field[trial_index]) else float(field[trial_index]) for field in fields)
        for trial_index in range(n_trials)
    ]


def _unit_label(fname: str, unit_number) -> str:
    return f"{fname}.{int(unit_number)}"


def _linked_label(row: dict) -> str | None:
    fname2 = row.get("FName2")
    if pd.isna(fname2) or fname2 == "" or pd.isna(row.get("UnitNum2")):
        return None
    return _unit_label(fname2, row["UnitNum2"])


def plan_sessions(metadata_df: pd.DataFrame, data_path: Path) -> list[dict]:
    """
    Build one plan per session from the metadata table.

    Each plan holds the session's trials as (file, trial index) pairs in session order, the units
    with the (file, trial index, session trial index) of every trial they were recorded in, the
    electrode locations, and notes for the NWB file.
    """
    rows = [row.to_dict() for _, row in metadata_df.iterrows()]

    # Join files that share a neuron
    parent = {}

    def find(fname):
        parent.setdefault(fname, fname)
        while parent[fname] != fname:
            fname = parent[fname]
        return fname

    for row in rows:
        find(row["FName1"])
        linked = _linked_label(row)
        if linked is not None:
            parent[find(linked.split(".")[0])] = find(row["FName1"])

    groups = {}
    for fname in list(parent):
        groups.setdefault(find(fname), set()).add(fname)

    plans = []
    for fnames in sorted(groups.values(), key=min):
        fnames = sorted(fnames)
        group_rows = [row for row in rows if row["FName1"] in fnames]
        notes = []

        # Unit files referenced per file, and the location of each file (its first unit's row; a
        # continuation file without a row of its own takes the row that links to it)
        unit_numbers = {}
        file_location_row = {}
        for row in sorted(group_rows, key=lambda row: (row["FName1"], row["UnitNum1"])):
            unit_numbers.setdefault(row["FName1"], set()).add(int(row["UnitNum1"]))
            file_location_row.setdefault(row["FName1"], row)
        for row in group_rows:
            linked = _linked_label(row)
            if linked is not None:
                linked_fname, linked_unit = linked.split(".")
                unit_numbers.setdefault(linked_fname, set()).add(int(linked_unit))
                file_location_row.setdefault(linked_fname, row)

        # Session trials: each file's trials in order, skipping trials that repeat an earlier file
        trial_sources = []
        trial_files = []
        session_trial_of_key = {}
        session_trials_of_file = {}
        for fname in fnames:
            events_file = data_path / f"{fname}.{min(unit_numbers[fname])}.mat"
            trial_keys = get_trial_keys(read_mat(str(events_file))["Events"])
            new_trial_of_key = {}
            session_trials = []
            for file_trial, key in enumerate(trial_keys):
                if key in session_trial_of_key:
                    session_trials.append(session_trial_of_key[key])
                    continue
                new_trial_of_key.setdefault(key, len(trial_sources))
                session_trials.append(len(trial_sources))
                trial_sources.append((events_file, file_trial))
                trial_files.append(fname)
            session_trial_of_key.update(new_trial_of_key)
            session_trials_of_file[fname] = session_trials

        # Duplicated units: keep one copy, take the tested label, and keep the copy's sweeps
        kept_rows = [
            dict(row) for row in group_rows if _unit_label(row["FName1"], row["UnitNum1"]) not in DUPLICATE_UNITS
        ]
        extra_antidromic_labels = {}
        for row in group_rows:
            label = _unit_label(row["FName1"], row["UnitNum1"])
            kept_label = DUPLICATE_UNITS.get(label)
            if kept_label is None:
                continue
            kept = next(r for r in kept_rows if _unit_label(r["FName1"], r["UnitNum1"]) == kept_label)
            extra_antidromic_labels.setdefault(kept_label, []).append(label)
            if kept["Antidrom"] == "NT" and row["Antidrom"] != "NT":
                for column in ANTIDROMIC_LABEL_COLUMNS:
                    kept[column] = row[column]
                notes.append(
                    f"DUPLICATED UNIT: unit {kept_label} is stored a second time as {label}, in a file whose "
                    f"trials all repeat {kept['FName1']}, with identical spikes. The copy is not a separate unit. "
                    f"The metadata table lists {kept_label} as not tested for antidromic activation and {label} "
                    f"as {row['Antidrom']}; the tested label and its antidromic values are used, and the "
                    f"stimulation sweeps of {label} are included."
                )
            elif kept["Antidrom"] != row["Antidrom"]:
                notes.append(
                    f"DUPLICATED UNIT: unit {kept_label} is stored a second time as {label}, in a file whose "
                    f"trials all repeat {kept['FName1']}, with identical spikes. The copy is not a separate unit. "
                    f"The metadata table labels the two copies differently ({kept['Antidrom']} for {kept_label}, "
                    f"{row['Antidrom']} for {label}); the label of {kept_label} is used, and the stimulation "
                    f"sweeps of both copies are included."
                )

        # Electrodes: one per distinct file location
        electrode_locations = []
        electrode_of_file = {}
        for fname in fnames:
            location_row = file_location_row[fname]
            location = (location_row["A_P"], location_row["M_L"], location_row["Depth"])
            for electrode_index, existing in enumerate(electrode_locations):
                if (existing["A_P"], existing["M_L"], existing["Depth"]) == location:
                    electrode_of_file[fname] = electrode_index
                    break
            else:
                electrode_of_file[fname] = len(electrode_locations)
                electrode_locations.append(location_row)

        # Units: every trial the unit was recorded in, mapped onto the session trials
        units = []
        for row in kept_rows:
            label = _unit_label(row["FName1"], row["UnitNum1"])
            recorded_labels = [label] + ([_linked_label(row)] if _linked_label(row) else [])
            spike_sources = []
            covered_trials = set()
            contributing_labels = []
            for recorded_label in recorded_labels:
                fname = recorded_label.split(".")[0]
                new_trials = [
                    (data_path / f"{recorded_label}.mat", file_trial, session_trial)
                    for file_trial, session_trial in enumerate(session_trials_of_file[fname])
                    if session_trial not in covered_trials
                ]
                if new_trials:
                    contributing_labels.append(recorded_label)
                    spike_sources.extend(new_trials)
                    covered_trials.update(session_trial for _, _, session_trial in new_trials)
            units.append(
                {
                    "name": "+".join(contributing_labels),
                    "metadata": row,
                    "spike_sources": spike_sources,
                    "antidromic_files": [
                        data_path / f"{source_label}.mat"
                        for source_label in [label] + extra_antidromic_labels.get(label, [])
                    ],
                    "electrode_indices": sorted(
                        {electrode_of_file[source_label.split(".")[0]] for source_label in contributing_labels}
                    ),
                }
            )

        contributing_files = list(dict.fromkeys(trial_files))
        if len(fnames) > 1:
            notes.insert(
                0,
                f"MERGED FILES: this session combines the source files {', '.join(fnames)}, recorded on the "
                "same day and linked in the lab's metadata table because at least one neuron was recorded "
                f"across them. Trials come from {', '.join(contributing_files)} in that order, separated like all "
                "trials by the artificial inter-trial gap; the trials column source_file names each trial's file, "
                "and the gap between two files is tagged file_boundary in invalid_times. Trials that repeat a "
                "trial of an earlier file were left out. Each unit is observed (obs_intervals) only during the "
                "trials of the files it was recorded in, which its unit_name lists.",
            )

        first_file_rows = [row for row in kept_rows if row["FName1"] == fnames[0]]
        complete_rows = [row for row in first_file_rows if not pd.isna([row["A_P"], row["M_L"], row["Depth"]]).any()]
        primary_unit = complete_rows[0] if complete_rows else first_file_rows[0]

        plans.append(
            {
                "fname": fnames[0],
                "primary_unit": primary_unit,
                "units": units,
                "electrode_locations": electrode_locations,
                "trial_sources": trial_sources,
                "trial_files": trial_files,
                "notes": notes,
            }
        )

    return plans
