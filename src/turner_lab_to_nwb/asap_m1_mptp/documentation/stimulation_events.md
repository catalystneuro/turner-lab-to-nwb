# In-Trial Stimulation Events

## Overview

The December 2025 data update from Robert Turner includes new fields in the Events structure for documenting in-trial antidromic stimulation. This stimulation was used to monitor unit isolation during recording sessions.

**Related documentation:**
- [Electrodes in Experiment](electrodes_in_experiment.md) - Recording vs stimulation electrode systems
- [File Structure](../assets/data_exploration/file_structure.md) - Full Events structure documentation
- [NWB Conversion Strategy](nwb_conversion.md) - How stimulation data maps to NWB

## New Fields in Events Structure

### Old Events Structure (pre-December 2025)
```
('home_cue_on', 'targ_cue_on', 'targ_dir', 'home_leave', 'reward', 'tq_flex', 'tq_ext')
```

### New Events Structure (December 2025)
```
('home_cue_on', 'targ_cue_on', 'targ_dir', 'home_leave', 'reward', 'tq_flex', 'tq_ext', 'end', 'stim_site', 'stim')
```

### Field Descriptions

- **`end`**: Trial end timestamp
- **`stim_site`**: Stimulation site identifier (string, e.g., stimulation target area)
- **`stim`**: Per-trial stimulation time in milliseconds relative to trial start
  - `NaN` when no stimulation was delivered in that trial
  - ~244-245 ms when stimulation was delivered (always early in trial)

## Scientific Context

From Robert's email (November 6, 2025):

> In a subset of recording sessions, we delivered single stimulation pulses early in some subset of trials to activate an otherwise silent neuron and thereby monitor its isolation. The "suspiciously constant spike times" [in v5604b.2.mat] reflect antidromically activated spikes elicited by that stimulation.

This explains the data quality flag we raised earlier about v5604b.2.mat having "suspiciously constant spike times (256 +/- 0.34 ms across 29/40 trials)". These were not placeholder values but real antidromically-evoked spikes.

## Example Data

### File with stimulation (v5604b.2.mat)
```python
Events['stim'] = [nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan,
                  245., 244., 244., 244., 245., 244., 244., 244., 244.,
                  244., 244., 244., 244., 244., 244., 244., 244., 245.,
                  244., 244., 245., 244., 245., 244., 245., 244., 244.,
                  244., 244.]
```

### File without stimulation (v0502.1.mat)
```python
Events['stim'] = [nan, nan, nan, nan, nan, nan, nan, nan, nan, nan,
                  nan, nan, nan, nan, nan, nan, nan, nan, nan, nan]
```

## Relationship to IT Neurons

The stimulation protocol was particularly important for intra-telencephalic (IT) type cortical pyramidal neurons, which have very low tonic firing rates. Some IT neurons rarely spiked spontaneously but could be reliably activated by antidromic stimulation from the striatum. This allowed researchers to confirm unit isolation even for neurons with minimal spontaneous activity.

Reference: DOI: 10.1523/JNEUROSCI.20-18-07096.2000

## NWB Implementation

**Status**: Implemented (January 2026)

### Stimulation Time Column

- Column name: `isolation_monitoring_stim_time`
- Type: float (seconds, relative to session start - aligned with other trial event times)
- Value: NaN for trials without stimulation
- HED annotation: `Experiment-procedure, Somatic-presentation, Time-value/# s`

### Stimulation Site Column

- Column name: `isolation_monitoring_stim_site`
- Type: string
- Values: `'Str'` (striatum), `'Thal'` (thalamus), `'Ped'` (cerebral peduncle), or empty string
- Note: The `stim_site` field in MATLAB uses the newer string type which Python libraries cannot read directly. A custom extraction function was developed to decode the UTF-16-LE encoded strings from the MATLAB `__function_workspace__` binary blob. See `assets/matlab_utilities/matlab_string_extraction.md` for technical details.

**Location in NWB files**:
- `nwbfile.trials['isolation_monitoring_stim_time']`
- `nwbfile.trials['isolation_monitoring_stim_site']`

**Statistics**:
- 171 out of 400 session files contain in-trial stimulation events
- Stimulation typically delivered ~244-245 ms after trial start
- Stimulation sites breakdown:
  - Thalamus (Thal): 117 files
  - Striatum (Str): 51 files
  - Peduncle (Ped): 3 files

This preserves important experimental context about when and where antidromic stimulation pulses were delivered, which is relevant for interpreting spike times in those trials.

## Files Affected

Sessions with stimulation data can be identified by checking:
1. The `StimData` column in the metadata table (indicates stimulation site: Ped, Str, Thal, or combinations)
2. The `stim` field in the Events structure having non-NaN values

## References

- [Pyramidal Tract Neurons Paper Summary](../assets/papers_summary_and_notes/pyramidal_tract_neurons_summary.md) - Antidromic identification methodology
