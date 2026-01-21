# Experiment Hypothesis Variables

This document maps the scientific hypotheses from Turner Lab papers to the variables available in the NWB files. Use this to decide which columns to include in the master CSV for session selection.

## Paper 1: Spontaneous Activity (Cerebral Cortex 2011)

**Title**: Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons

### Hypotheses Tested

| Hypothesis | Description | Key Finding |
|------------|-------------|-------------|
| **Cell-type vulnerability** | PTNs and CSNs respond differently to MPTP | PTNs showed 27% reduction in firing rate; CSNs unchanged |
| **Beta oscillations** | Parkinsonism increases pathological beta rhythmicity | PTNs showed increased 14-32 Hz power |
| **Firing pattern changes** | MPTP alters burstiness and regularity | PTNs showed increased burst rate and CV |

### Variables Needed for Replication

| Variable | NWB Location | Why Needed |
|----------|--------------|------------|
| `subject_id` | `nwbfile.subject.subject_id` | Group by animal (V or L) |
| `mptp_status` | `session_id` or `pharmacology` | **Primary comparison**: Pre vs Post MPTP |
| `neuron_projection_type` | `units["neuron_projection_type"]` | **Cell-type comparison**: PTN vs CSN |
| `ptn_count` | Derived from units table | Sample size per session |
| `csn_count` | Derived from units table | Sample size per session |
| `antidromic_latency_ms` | `units["antidromic_latency_ms"]` | Verify neuron classification |

### Derived Analyses (computed from spike times, not stored)
- Spontaneous firing rate (spikes/sec during rest)
- Coefficient of variation (CV) of interspike intervals
- Burst rate and burst proportion
- Beta-band (14-32 Hz) power spectral density

---

## Paper 2: Active Movement (Brain 2016)

**Title**: Primary motor cortex of the parkinsonian monkey: altered encoding of active movement

### Hypotheses Tested

| Hypothesis | Description | Key Finding |
|------------|-------------|-------------|
| **Hypoactivation** | M1 receives reduced excitatory drive | Supported: 36% reduction in movement-related activity |
| **Loss of specificity** | Degraded selectivity causes co-activation | Partial: Directional tuning reduced but not eliminated |
| **Abnormal timing** | Motor command timing becomes dispersed | Not supported: Temporal structure preserved |

### Variables Needed for Replication

| Variable | NWB Location | Why Needed |
|----------|--------------|------------|
| `subject_id` | `nwbfile.subject.subject_id` | Group by animal |
| `mptp_status` | `session_id` or `pharmacology` | **Primary comparison**: Pre vs Post MPTP |
| `neuron_projection_type` | `units["neuron_projection_type"]` | **Cell-type comparison**: PTN vs CSN |
| `total_trials` | `len(nwbfile.trials)` | Ensure sufficient trial count |
| `flexion_trials` | `trials["movement_type"]` | Balance flexion/extension |
| `extension_trials` | `trials["movement_type"]` | Balance flexion/extension |
| `has_perturbation_trials` | `trials["torque_perturbation_type"]` | Exclude perturbation trials for pure active movement |

### Trial-Level Variables (for GLM analysis)
| Variable | NWB Location | Why Needed |
|----------|--------------|------------|
| `derived_peak_velocity` | `trials["derived_peak_velocity"]` | Kinematic encoding analysis |
| `derived_movement_amplitude` | `trials["derived_movement_amplitude"]` | Movement scaling analysis |
| `derived_movement_onset_time` | `trials["derived_movement_onset_time"]` | Align to movement onset |
| `movement_type` | `trials["movement_type"]` | Directional tuning analysis |

---

## Paper 3: Muscle Stretch (Frontiers 2013)

**Title**: Primary motor cortex of the parkinsonian monkey: altered neuronal responses to muscle stretch

### Hypotheses Tested

| Hypothesis | Description | Key Finding |
|------------|-------------|-------------|
| **Enhanced transcortical** | M1 stretch responses are exaggerated | **Not supported**: M1 responses unchanged/reduced |
| **Enhanced spinal** | Spinal reflex gain is increased | Supported: Behavioral LLSR exaggerated, not cortical |
| **Directional encoding** | Stretch direction selectivity preserved | **Not supported**: Directional selectivity degraded |

### Variables Needed for Replication

| Variable | NWB Location | Why Needed |
|----------|--------------|------------|
| `subject_id` | `nwbfile.subject.subject_id` | Group by animal |
| `mptp_status` | `session_id` or `pharmacology` | **Primary comparison**: Pre vs Post MPTP |
| `neuron_projection_type` | `units["neuron_projection_type"]` | **Cell-type comparison**: PTN vs CSN |
| `has_perturbation_trials` | `trials["torque_perturbation_type"]` | **Required**: Must have perturbation trials |
| `has_emg` | `nwbfile.acquisition` | Required for behavioral LLSR measurement |

### Trial-Level Variables (for stretch response analysis)
| Variable | NWB Location | Why Needed |
|----------|--------------|------------|
| `torque_perturbation_type` | `trials["torque_perturbation_type"]` | Direction of stretch (flexion/extension) |
| `torque_perturbation_onset_time` | `trials["torque_perturbation_onset_time"]` | Align neural responses to perturbation |

---

## All Extractable Variables from NWB Files

### Session-Level Metadata

| Variable | NWB Location | Description | Paper Relevance |
|----------|--------------|-------------|-----------------|
| `asset_path` | DANDI API | DANDI asset path | Data access |
| `asset_url` | DANDI API | S3 URL for streaming | Data access |
| `session_id` | `nwbfile.session_id` | Unique session identifier | All papers |
| `subject_id` | `nwbfile.subject.subject_id` | Animal (V or L) | All papers |
| `session_date` | `nwbfile.session_start_time` | Recording date | Longitudinal tracking |
| `session_time` | `nwbfile.session_start_time` | Recording time | Session ordering |
| `mptp_status` | Parsed from `session_id` | Pre-MPTP or Post-MPTP | **All papers (critical)** |
| `related_publications` | `nwbfile.related_publications` | DOI links | Reference |

### Electrode/Recording Location

| Variable | NWB Location | Description | Paper Relevance |
|----------|--------------|-------------|-----------------|
| `chamber_grid_ap_mm` | `electrodes["chamber_grid_ap_mm"]` | Anterior-posterior position | Anatomical consistency |
| `chamber_grid_ml_mm` | `electrodes["chamber_grid_ml_mm"]` | Medial-lateral position | Anatomical consistency |
| `chamber_insertion_depth_mm` | `electrodes["chamber_insertion_depth_mm"]` | Electrode depth | Cortical layer targeting |

### Unit Summary Statistics

| Variable | NWB Location | Description | Paper Relevance |
|----------|--------------|-------------|-----------------|
| `total_units` | `len(nwbfile.units)` | Total units in session | Sample size |
| `ptn_count` | Count of `pyramidal_tract_neuron` | PTN count | **All papers (critical)** |
| `csn_count` | Count of `corticostriatal_neuron` | CSN count | **All papers (critical)** |
| `other_neuron_count` | Remaining units | Unidentified neurons | Data quality |
| `neuron_projection_types` | Unique values | List of all types | Quick filtering |

### Unit-Level Details (Aggregatable)

| Variable | NWB Location | Description | Paper Relevance |
|----------|--------------|-------------|-----------------|
| `min_antidromic_latency_ms` | `min(units["antidromic_latency_ms"])` | Fastest PTN latency | Verify PTN classification |
| `max_antidromic_latency_ms` | `max(units["antidromic_latency_ms"])` | Slowest CSN latency | Verify CSN classification |
| `mean_antidromic_latency_ms` | `mean(units["antidromic_latency_ms"])` | Average latency | Population characterization |
| `receptive_field_locations` | Unique values | Body regions represented | Somatotopic mapping |

### Trial/Behavioral Information

| Variable | NWB Location | Description | Paper Relevance |
|----------|--------------|-------------|-----------------|
| `total_trials` | `len(nwbfile.trials)` | Number of trials | Sample size |
| `flexion_trials` | Count of `movement_type=="flexion"` | Flexion count | Active movement paper |
| `extension_trials` | Count of `movement_type=="extension"` | Extension count | Active movement paper |
| `has_perturbation_trials` | Any `torque_perturbation_type != "none"` | Perturbation present | **Stretch paper (critical)** |
| `perturbation_trial_count` | Count of perturbation trials | Number of stretch trials | Stretch paper |

### Kinematic Summary (from trials table)

| Variable | NWB Location | Description | Paper Relevance |
|----------|--------------|-------------|-----------------|
| `mean_peak_velocity` | `mean(trials["derived_peak_velocity"])` | Average movement speed | Bradykinesia assessment |
| `mean_movement_amplitude` | `mean(trials["derived_movement_amplitude"])` | Average displacement | Hypometria assessment |
| `mean_reaction_time` | Derived from cursor_departure - lateral_target | Response latency | Akinesia assessment |

### Data Availability Flags

| Variable | NWB Location | Description | Paper Relevance |
|----------|--------------|-------------|-----------------|
| `has_emg` | Check acquisition for EMG* keys | EMG data present | **Stretch paper (critical)** |
| `has_lfp` | Check acquisition for LFP key | LFP data present | Beta oscillation analysis |

---

## Recommended Column Sets by Use Case

### Minimal Set (Basic Filtering)
Essential for any analysis:
- `asset_path`, `asset_url`
- `session_id`, `subject_id`, `session_date`
- `mptp_status`
- `total_units`, `ptn_count`, `csn_count`
- `total_trials`

### Spontaneous Activity Analysis
Add to minimal set:
- `neuron_projection_types`
- `has_lfp` (for beta oscillation analysis)

### Active Movement Analysis
Add to minimal set:
- `flexion_trials`, `extension_trials`
- `has_perturbation_trials` (to exclude perturbation sessions)
- `mean_peak_velocity`, `mean_movement_amplitude` (for kinematic characterization)

### Stretch Reflex Analysis
Add to minimal set:
- `has_perturbation_trials` (must be True)
- `perturbation_trial_count`
- `has_emg` (must be True for behavioral LLSR)

### Comprehensive Set (All Variables)
Include everything for maximum flexibility in exploratory analyses.

---

## Notes on Data Quality Filtering

### Recommended Filters
1. **Minimum trial count**: >=20 trials per movement direction
2. **Identified neurons**: Sessions with at least 1 PTN or 1 CSN
3. **Valid coordinates**: Non-null chamber grid coordinates

### Session Exclusion Criteria (from papers)
- Units that could not be held for sufficient duration
- Sessions with excessive movement artifacts during "rest" recordings
- Trials with incomplete behavioral sequences

---

## Cross-Paper Analysis Considerations

All three papers use:
- Same two animals (V and L)
- Same MPTP protocol (0.5 mg/kg unilateral intracarotid)
- Same recording methods (glass-coated tungsten microelectrodes)
- Same antidromic identification criteria
- Same hemisphere (right, contralateral to left injection)

This consistency enables:
- Combining data across paradigms
- Tracking individual neuron types across studies
- Longitudinal analysis of MPTP progression effects
