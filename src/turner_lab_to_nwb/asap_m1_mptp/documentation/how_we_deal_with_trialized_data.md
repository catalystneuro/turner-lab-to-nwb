# Handling Trialized Data in NWB Conversion

This document explains how the Turner Lab MPTP dataset's trialized structure is converted to continuous NWB format and how the artificial inter-trial gaps are annotated for downstream analysis.

## The Problem: Trialized Source Data

The original MATLAB files contain **per-trial data** with all timestamps relative to individual trial starts:

- **Spike times**: `unit_ts` matrix (n_trials x max_spikes), NaN-padded
- **Analog signals**: Per-trial arrays (`Analog.x[trial_idx]`, `Analog.vel[trial_idx]`, etc.)
- **Behavioral events**: Per-trial timestamps (e.g., `Events.targetOn`, `Events.go`)

**Critical limitation**: The source data contains NO information about actual inter-trial intervals. The gaps between trials were not recorded.

## The Solution: Concatenation with Annotated Gaps

The conversion pipeline concatenates trials into a continuous timeline:

1. **Trial 1**: starts at t=0, ends at t=trial_1_duration
2. **Gap 1**: artificial 3-second placeholder (NOT recorded data)
3. **Trial 2**: starts at t=trial_1_duration + 3s, etc.

```
Timeline:
|----Trial 1----|  GAP  |----Trial 2----|  GAP  |----Trial 3----|
                  (3s)                    (3s)
                  NOT                     NOT
                RECORDED                RECORDED
```

The 3-second gap duration is configurable via the `inter_trial_time_interval` parameter (default: 3.0 seconds).

## NWB Annotations for Data Validity

Two complementary NWB mechanisms annotate the artificial gaps:

### 1. `invalid_times` Table (Session-wide)

All inter-trial gaps are recorded in the `invalid_times` table with tags:
- `artificial_inter_trial_gap`: Identifies the gap type
- `not_recorded`: Emphasizes no data was collected during this period

**Use for**: Filtering continuous data (LFP, EMG, kinematics)

```python
# Access invalid times
invalid_times_df = nwbfile.invalid_times.to_dataframe()
print(invalid_times_df)
#    start_time  stop_time                                    tags
# 0        8.45      11.45  [artificial_inter_trial_gap, not_recorded]
# 1       19.72      22.72  [artificial_inter_trial_gap, not_recorded]
# ...
```

### 2. `obs_intervals` Column (Per-unit)

Each unit in the Units table has an `obs_intervals` column specifying when the unit was observable (i.e., during trials only).

**Use for**: Spike train analysis, firing rate calculations, ISI distributions

```python
# Access observation intervals for unit 0
obs_intervals = nwbfile.units.get_unit_obs_intervals(0)
print(obs_intervals)
# [[0.0, 8.45], [11.45, 19.72], [22.72, 30.15], ...]
# Each row is [trial_start, trial_stop]
```

## Why This Matters for Analysis

### Firing Rate Calculations

Without proper handling, firing rates would be underestimated:

```python
# WRONG: Divides by total time including gaps
wrong_rate = len(spike_times) / (session_end - session_start)

# CORRECT: Divides by observed time only
obs_intervals = nwbfile.units.get_unit_obs_intervals(unit_index)
total_observed_time = sum(stop - start for start, stop in obs_intervals)
correct_rate = len(spike_times) / total_observed_time
```

### Inter-Spike Interval (ISI) Analysis

Spikes at trial boundaries should not contribute to ISI:

```python
import numpy as np

def get_within_trial_isis(spike_times, obs_intervals):
    """Compute ISIs only for spikes within the same trial."""
    isis = []
    for start, stop in obs_intervals:
        trial_spikes = spike_times[(spike_times >= start) & (spike_times <= stop)]
        if len(trial_spikes) > 1:
            isis.extend(np.diff(trial_spikes))
    return np.array(isis)
```

### GLM and Regression Models

Models should only include time bins where data was recorded:

```python
# Create time bins, then mask out invalid periods
time_bins = np.arange(0, session_end, bin_size)
valid_mask = np.ones(len(time_bins), dtype=bool)

invalid_times_df = nwbfile.invalid_times.to_dataframe()
for _, row in invalid_times_df.iterrows():
    invalid_mask = (time_bins >= row['start_time']) & (time_bins < row['stop_time'])
    valid_mask[invalid_mask] = False

# Use only valid bins for modeling
X_valid = X[valid_mask]
y_valid = y[valid_mask]
```

### Continuous Signal Analysis (LFP, EMG)

Filter out gap periods before spectral analysis:

```python
def get_valid_signal_segments(timestamps, signal, invalid_times_df):
    """Extract only valid signal segments (within trials)."""
    valid_mask = np.ones(len(timestamps), dtype=bool)

    for _, row in invalid_times_df.iterrows():
        gap_mask = (timestamps >= row['start_time']) & (timestamps < row['stop_time'])
        valid_mask[gap_mask] = False

    return timestamps[valid_mask], signal[valid_mask]
```

## Technical Implementation Details

### Trial Duration: Two Data Sources

The source MATLAB files contain two measures of trial duration that differ by ~5ms:

| Source | Value | Used By |
|--------|-------|---------|
| `Events.end` | Official trial end timestamp from behavioral software | Trials table, spike times, obs_intervals, invalid_times |
| `len(Analog.x) / 1000` | When analog recording stopped | LFP, EMG, manipulandum timestamps |

**Why they differ**: The analog recording system may stop sampling slightly before the behavioral software marks the trial as complete. This creates a ~5ms gap where spikes can still occur but no analog data exists.

**Design decision**: We use `Events.end` for all trial boundary definitions (trials table, `invalid_times`, `obs_intervals`) because:
1. It is the authoritative trial boundary from the experiment
2. Some spikes occur after analog recording stops but before trial end
3. Using analog length would incorrectly exclude valid spikes from `obs_intervals`

The analog interfaces (LFP, EMG, manipulandum) use their actual sample counts for timestamps, which is correct - they only have data for the samples they recorded.

### Where Gaps Are Created

| Interface | File | What It Does |
|-----------|------|--------------|
| `TrialsInterface` | trials_interface.py | Creates trial boundaries (using `Events.end`), adds `invalid_times` |
| `SpikeTimesInterface` | spike_times_interface.py | Concatenates spikes (using `Events.end`), adds `obs_intervals` |
| `LFPInterface` | lfp_interface.py | Concatenates LFP with timestamp gaps (using analog sample count) |
| `EMGInterface` | emg_interface.py | Concatenates EMG with timestamp gaps (using analog sample count) |
| `ManipulandumInterface` | manipulandum_interface.py | Concatenates kinematics with timestamp gaps (using analog sample count) |

### Relationship Between Annotations

The `invalid_times` entries and `obs_intervals` are complementary:
- `invalid_times` gaps + trial intervals = complete session timeline
- `obs_intervals` for each unit = all trial intervals (same for all units in a session)
- Spikes should ONLY occur within `obs_intervals`
- Continuous data timestamps skip over `invalid_times` gaps
- Analog data ends ~5ms before `obs_intervals` end (this is expected)

## Summary

| Aspect | Source Data | NWB Representation |
|--------|-------------|-------------------|
| Trial timing | Per-trial relative timestamps | Continuous absolute timestamps |
| Inter-trial gaps | NOT RECORDED | 3-second artificial placeholders |
| Gap annotation | N/A | `invalid_times` table |
| Unit observability | Implicit (data exists per trial) | Explicit `obs_intervals` column |
| Spike times | Per-trial matrix | Concatenated array with `obs_intervals` |
| Continuous signals | Per-trial arrays | Concatenated with timestamp gaps |

## See Also

- [Trial Structure](trial_structure.md) - Detailed trial timing and event sequences
- [NWB Conversion](nwb_conversion.md) - Overall data stream mapping
- [File Structure](../assets/data_exploration/file_structure.md) - Source MATLAB format
