"""Read the trials of a session from the source files they come from.

A session's trials are given as (file path, trial index in that file) pairs in session order. Most
sessions take every trial of one file; sessions merged from several files take trials from each.
"""

from pathlib import Path

import numpy as np
from pymatreader import read_mat


def read_trial_source_files(trial_sources: list[tuple[Path, int]]) -> dict[Path, dict]:
    """Read every file that contributes trials to the session, once."""
    return {file_path: read_mat(str(file_path)) for file_path in dict.fromkeys(path for path, _ in trial_sources)}


def get_trial_timeline(
    mat_data_by_file: dict[Path, dict], trial_sources: list[tuple[Path, int]], inter_trial_time_interval: float
) -> tuple[np.ndarray, np.ndarray]:
    """
    Start times and durations of the session's trials, in seconds.

    The source files carry no time between trials, so trials are placed back to back, each lasting
    Events['end'] and separated by the inter-trial gap. Trials, spikes and analog streams all use this
    timeline.
    """
    trial_durations = (
        np.array([np.atleast_1d(mat_data_by_file[path]["Events"]["end"])[trial] for path, trial in trial_sources])
        / 1000.0
    )
    trial_start_times = np.concatenate([[0.0], np.cumsum(trial_durations[:-1] + inter_trial_time_interval)])
    return trial_start_times, trial_durations


def gather_trial_fields(
    mat_data_by_file: dict[Path, dict], trial_sources: list[tuple[Path, int]], struct_name: str
) -> dict | None:
    """
    Per-trial fields of a MATLAB struct (Events or Mvt) over the session's trials.

    A field missing from a file, or not stored per trial in it, is NaN for that file's trials.
    Returns None when no file has the struct.
    """
    structs = {path: mat_data.get(struct_name) for path, mat_data in mat_data_by_file.items()}
    if not any(isinstance(struct, dict) for struct in structs.values()):
        return None
    n_trials_by_file = {
        path: len(np.atleast_1d(mat_data["Events"]["end"])) for path, mat_data in mat_data_by_file.items()
    }
    field_names = dict.fromkeys(
        name for struct in structs.values() if isinstance(struct, dict) for name in struct if name != "stim_site"
    )
    gathered = {}
    for name in field_names:
        values = []
        for path, trial in trial_sources:
            struct = structs[path]
            is_per_trial = (
                isinstance(struct, dict) and name in struct and np.size(struct[name]) == n_trials_by_file[path]
            )
            values.append(np.atleast_1d(struct[name])[trial] if is_per_trial else np.nan)
        gathered[name] = np.array(values, dtype=float)
    return gathered
