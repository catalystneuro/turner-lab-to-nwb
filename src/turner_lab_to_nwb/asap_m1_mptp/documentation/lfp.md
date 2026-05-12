# Local Field Potential (LFP) Recordings

## Overview

The Turner Lab M1 MPTP dataset includes local field potential (LFP) recordings from a subset of sessions. LFP was recorded simultaneously with single-unit activity from the same glass-coated platinum-iridium microelectrode used for spike detection.

**Related documentation:**
- [Electrodes in Experiment](electrodes_in_experiment.md) - Recording electrode specifications
- [File Structure](../assets/data_exploration/file_structure.md) - MATLAB data format
- [NWB Conversion Strategy](nwb_conversion.md) - How LFP maps to NWB

## Recording Setup

### Hardware Configuration

| Component | Specification |
|-----------|---------------|
| Electrode | Glass-coated PtIr microelectrode (same as spike recording) |
| Amplifier gain | 10,000x (10k) |
| Bandpass filter | 1-100 Hz |
| Sampling rate | 1 kHz (same as other analog signals) |

### Signal Processing Chain

```
Microelectrode tip in M1 cortex
    │
    ▼
Amplifier (10k gain)
    │
    ▼
Bandpass filter (1-100 Hz)
    │
    ▼
A/D conversion (1 kHz)
    │
    ▼
Stored in MATLAB file (Analog.lfp)
```

The LFP signal represents the low-frequency component of the extracellular potential, capturing summed synaptic activity and population-level neural dynamics in the local cortical region.

## MATLAB Data Structure

### Source Field

```python
Analog['lfp'][trial_idx]  # LFP signal for trial trial_idx
```

### Data Format

- **Structure**: List of 1D arrays, one per trial
- **Units**: Raw 12-bit unsigned A/D counts (centered ~2048). Stored as-is in the NWB file under `unit="a.u."` (see [Why no voltage calibration](#why-no-voltage-calibration) below).
- **Shape**: `(n_samples_per_trial,)` for each trial
- **Sampling**: 1 kHz (matches position, velocity, torque, EMG)

### Example Code

```python
from pymatreader import read_mat

mat_data = read_mat("v0502.1.mat")

# Check if LFP was collected
if "lfp" in mat_data["Analog"]:
    lfp_data = mat_data["Analog"]["lfp"]
    n_trials = len(lfp_data)

    # Access single trial
    trial_0_lfp = lfp_data[0]
    print(f"Trial 0 LFP: {len(trial_0_lfp)} samples")
```

## Data Availability

### Session Statistics

| Metric | Value |
|--------|-------|
| Sessions with LFP | 223 out of 351 (64%) |
| Sessions without LFP | 128 out of 351 (36%) |

### Availability Flag

The metadata table (`ven_table.csv`) includes a boolean flag indicating LFP availability:

```python
import pandas as pd

metadata = pd.read_csv("ven_table.csv")
lfp_sessions = metadata[metadata["lfp_collected"] == 1]
print(f"Sessions with LFP: {len(lfp_sessions)}")
```

## Scientific Context

### Relevance to Parkinson's Disease Research

LFP recordings are particularly valuable for studying beta-band (14-32 Hz) oscillatory activity, which is a hallmark of parkinsonian pathophysiology. The Turner lab papers document enhanced beta rhythmicity in pyramidal tract neurons (PTNs) following MPTP-induced parkinsonism.

From the Pyramidal Tract Neurons paper (Cerebral Cortex 2011):

> Post-MPTP PTNs showed prominent beta peaks in autocorrelograms... Beta rhythmicity correlated with parkinsonian symptom severity.

Key findings related to LFP:
- **PTNs**: Significant increase in 14-32 Hz power spectral density after MPTP
- **CSNs**: No significant change in beta-band power
- **Correlation**: Beta rhythmicity linked to symptom severity

### Analysis Applications

The LFP data enables:
1. **Beta oscillation quantification**: Power spectral analysis of 14-32 Hz activity
2. **Spike-field coherence**: Relationship between single-unit firing and LFP oscillations
3. **Pre/Post MPTP comparison**: Changes in oscillatory dynamics with parkinsonism
4. **Task-related modulation**: LFP changes during movement preparation and execution

## NWB Implementation

**Status**: Implemented (January 2026)

### NWB Structure

The LFP interface (`lfp_interface.py`) writes LFP data to the NWB file as an `ElectricalSeries` in the ecephys processing module.

| Field | Value |
|-------|-------|
| NWB container | `nwbfile.processing['ecephys']['LFP']` |
| Class | `pynwb.TimeSeries` |
| Unit | `a.u.` (arbitrary units) |
| Conversion | 1.0 (default) |
| Offset | 0 (default) |
| Description | Local field potential from microelectrode (10k gain, 1-100 Hz bandpass filtered) |

### Why no voltage calibration

The LFP is stored as a plain `TimeSeries` rather than as an `ElectricalSeries`. `ElectricalSeries` is contractually a volts container per the NWB schema, and storing raw A/D counts there with `conversion=1.0` would make a false physical-unit claim that downstream tools could be tripped up by.

A voltage calibration would require knowing both the LFP amplifier gain (documented as 10000x) and the LFP digitizer's ADC voltage range. The ADC range is **not documented** in the source materials. By parallel reasoning to the antidromic Unit factor (`1.526e-8 V/count = 10 V / 2^16 / 10000`, derived by back-fitting tutorial plots and confirmed with the authors), one could conjecture that the LFP path uses the same 10 V ADC range with a 12-bit digitizer, giving `2.4414e-7 V/count` and an offset of `-5.0e-4 V` to map the 12-bit midpoint (count 2048) to 0 V. The resulting amplitudes (~20 µV RMS, hundreds of µV peak-to-peak) are physiologically plausible. However, this rests on an assumption about the ADC range that we cannot independently verify, so we chose to make no physical-unit claim rather than a provisional one.

This mirrors the EMG approach (also `TimeSeries(unit="a.u.")`) and trades two things: the electrode-table linkage that an `ElectricalSeries` would carry (electrode metadata is still in `nwbfile.electrodes` and can be cross-referenced via the spike data, but is not a direct foreign-key from this signal), and auto-discovery as "LFP" by NWB-aware tools that scan for `ElectricalSeries` inside the LFP processing-module container.

The data values themselves are unchanged: 12-bit unsigned A/D counts centered on the midpoint 2048. Subtract 2048 for zero-baseline analyses.

### Trial Concatenation

LFP data is concatenated across trials with:
- Trial boundaries aligned to the trials table
- 3-second synthetic inter-trial intervals
- Timestamps synchronized with other analog signals

### Access Example

```python
from pynwb import NWBHDF5IO

with NWBHDF5IO("session.nwb", "r") as io:
    nwbfile = io.read()

    # Check if LFP exists (not all sessions have it)
    if "ecephys" in nwbfile.processing and "LFP" in nwbfile.processing["ecephys"].data_interfaces:
        lfp = nwbfile.processing["ecephys"]["LFP"]
        lfp_data = lfp.data[:]
        lfp_timestamps = lfp.timestamps[:]
        print(f"LFP: {len(lfp_data)} samples")
        print(f"Units: {lfp.unit}")  # Will show 'a.u.' (arbitrary units)
```

### Extracting Trial-Aligned LFP

```python
import numpy as np

# Get trial boundaries
trials = nwbfile.trials.to_dataframe()

# Extract LFP for a specific trial
trial_idx = 5
trial_start = trials.iloc[trial_idx]["start_time"]
trial_stop = trials.iloc[trial_idx]["stop_time"]

# Find LFP samples within trial
lfp = nwbfile.processing["ecephys"]["LFP"]
lfp_timestamps = lfp.timestamps[:]
mask = (lfp_timestamps >= trial_start) & (lfp_timestamps < trial_stop)
trial_lfp = lfp.data[mask]
```

## Limitations and Considerations

1. **Single channel**: LFP is recorded from a single microelectrode (no multi-site array)
2. **Not all sessions**: Only 64% of sessions include LFP data
3. **Bandpass filtered**: Raw broadband signal not available (1-100 Hz only)
4. **No voltage calibration**: Data are stored as raw 12-bit A/D counts under `unit="a.u."`. No physical-unit (volts) conversion is applied because the LFP digitizer's ADC range is undocumented. Use for relative amplitude analyses, spectral analysis, normalized measures, and within-dataset comparisons. See [Why no voltage calibration](#why-no-voltage-calibration) above.
5. **Simultaneous with spikes**: LFP and spikes come from the same electrode, which may affect spike-field coherence interpretation

## References

- [Pyramidal Tract Neurons Paper Summary](../assets/papers_summary_and_notes/pyramidal_tract_neurons_summary.md) - Beta oscillation findings
- [Experimental Setup Commonalities](../assets/papers_summary_and_notes/experimental_setup_commonalities.md) - Recording methodology
