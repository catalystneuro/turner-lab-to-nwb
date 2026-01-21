# Electrodes Used in Turner Lab MPTP Experiments

This document describes the different electrode systems used in the Turner lab experiments, clarifying their distinct purposes and specifications.

## Overview

The experiments utilized four distinct electrode systems:

1. **Recording electrode** - For capturing single-unit neural activity in M1
2. **Antidromic stimulating electrodes** - For cell-type identification (PTN vs CSN)
3. **Intracortical microstimulation (ICMS)** - For verifying motor cortex location
4. **EMG electrodes** - For recording muscle activity

## 1. Recording Electrode

**Purpose**: Capture extracellular single-unit activity from primary motor cortex (M1) neurons. This electrode records the spike times stored in the NWB Units table.

### Specifications

| Property | Value |
|----------|-------|
| **Type** | Glass-coated tungsten microelectrode |
| **Access** | Chronic recording chamber implanted over M1 |
| **Orientation** | 35 degrees in coronal plane (orthogonal to cortical surface) |
| **Target** | Layer 5, arm-related region of primary motor cortex |
| **Hemisphere** | Right (contralateral to MPTP injection) |

### Procedure

From "Primary motor cortex of the parkinsonian monkey: altered encoding of active movement" (Pasquereau, DeLong & Turner, 2016):

> "A cylindrical stainless steel chamber was implanted with stereotaxic guidance over a burr hole allowing access to the arm-related regions of the left M1 and the putamen. The chamber was oriented parallel to the coronal plane at an angle of 35 degrees so that electrode penetrations were orthogonal to the cortical surface."

The recording electrode is advanced through the chronic chamber on each recording session. Neurons are isolated based on spike waveform, and spike sorting is performed offline to isolate single-unit activity.

### Data Captured

- Spike times (stored in NWB Units table)
- Spike waveforms
- Continuous neural signal during recording

## 2. Antidromic Stimulating Electrodes

**Purpose**: Identify neuron cell types by antidromically activating their axons at known projection targets.

### Two Separate Stimulating Sites

#### Cerebral Peduncle Electrode (for PTN identification)

| Property | Value |
|----------|-------|
| **Target structure** | Cerebral peduncle |
| **Purpose** | Identify Pyramidal Tract Neurons (PTNs) |
| **Current range** | 100-400 microAmps |
| **Pulse duration** | 0.2 ms biphasic |
| **Expected latency** | 0.6-2.5 ms |

PTNs are layer 5b pyramidal neurons projecting to the spinal cord via the corticospinal tract. The short latency (0.6-2.5 ms) indicates large, fast-conducting axons.

#### Putamen Electrode (for CSN identification)

| Property | Value |
|----------|-------|
| **Target structure** | Posterolateral putamen |
| **Purpose** | Identify Corticostriatal Neurons (CSNs) |
| **Current range** | 100-600 microAmps |
| **Pulse duration** | 0.2 ms biphasic |
| **Expected latency** | 2.0-20 ms |

CSNs are intratelencephalic-type layer 5 neurons projecting to the striatum. The longer latency (2.0-20 ms) indicates smaller, slower-conducting axons compared to PTNs.

### Antidromic Identification Criteria

From "Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons" (Pasquereau & Turner, 2011):

All neurons classified as PTN or CSN met three standard criteria:

1. **Fixed latency**: Consistent response latency across stimulations
2. **High-frequency following**: Ability to follow stimulation at >200 Hz
3. **Collision test**: Spontaneous spikes occurring within the critical window blocked the antidromic response

### Data Captured

- Antidromic latency (stored in `antidromic_latency_ms` column)
- Stimulation threshold (stored in `antidromic_threshold` column)
- Stimulation site (stored in `antidromic_stimulation_sites` column: "PED" or "STRI")

## 3. Intracortical Microstimulation (ICMS)

**Purpose**: Verify that the recording electrode is positioned in arm-related motor cortex by evoking muscle contractions.

### Specifications

| Property | Value |
|----------|-------|
| **Electrode used** | Same recording electrode (glass-coated tungsten) |
| **Current** | <40 microAmps |
| **Pulse pattern** | 10 biphasic pulses at 300 Hz |
| **Expected response** | Contraction of forelimb muscles |

### Procedure

From "Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons" (Pasquereau & Turner, 2011):

> "A cortical region was targeted for data collection if neurons responded to active and/or passive movement of the arm and microstimulation at low currents evoked contraction of forelimb muscles (<40 microAmps, 10 biphasic pulses at 300 Hz)"

This microstimulation is used to confirm the recording site is in motor cortex (not sensory cortex or other areas) by verifying that electrical stimulation produces movement. This is separate from the antidromic stimulation used for cell-type identification.

### Data Captured

This verification procedure is not explicitly stored in the dataset - it was used to guide electrode placement during experiments.

## 4. EMG Electrodes

**Purpose**: Record electromyographic (EMG) activity from arm muscles to monitor behavioral state and measure stretch reflex responses.

### Electrode Type

Chronically implanted intramuscular EMG electrodes (pairs of multi-stranded stainless steel wires).

### Subject-Specific Muscle Configurations

#### Monkey V (Ven)

| Muscle | Function |
|--------|----------|
| Posterior deltoid | Shoulder extension/external rotation |
| Trapezius | Scapular elevation/retraction |
| Triceps longus | Elbow extension |
| Triceps lateralis | Elbow extension |
| Brachioradialis | Elbow flexion |

#### Monkey L (Lau)

| Muscle | Function |
|--------|----------|
| Flexor carpi ulnaris | Wrist flexion |
| Flexor carpi radialis | Wrist flexion |
| Biceps longus | Elbow flexion |
| Brachioradialis | Elbow flexion |
| Triceps lateralis | Elbow extension |

### Signal Processing

| Property | Value |
|----------|-------|
| **Processing** | Rectified and low-pass filtered |
| **Sampling** | Same rate as kinematic data |
| **Availability** | Check `emg_collected` metadata flag |

### Experimental Uses

1. **Resting state verification** (Pyramidal Tract Neurons study): EMG monitored to confirm absence of movement during spontaneous activity recordings

2. **Stretch reflex measurement** (Muscle Stretch study): EMG used to quantify behavioral long-latency stretch reflex (LLSR) responses, allowing comparison between neural and behavioral measures

3. **Movement monitoring** (Active Movement study): EMG recorded during task performance

### Data Location in MATLAB Files

- **Location**: `Analog.emg[trial_idx]` (when present)
- **Shape**: (time_points, n_muscles)
- **Note**: Not all sessions include EMG data

## Summary Table

| Electrode System | Location | Purpose | Data in NWB |
|------------------|----------|---------|-------------|
| **Recording** | M1 cortex (advanced each session) | Capture spike times | Units table (spike_times, waveform_mean) |
| **Antidromic - Peduncle** | Cerebral peduncle (chronic) | Identify PTNs | antidromic_latency_ms, antidromic_threshold |
| **Antidromic - Putamen** | Posterolateral putamen (chronic) | Identify CSNs | antidromic_latency_ms, antidromic_threshold |
| **ICMS** | Same as recording electrode | Verify motor cortex location | Not stored |
| **EMG** | Arm muscles (chronic implants) | Record muscle activity | acquisition (EMG time series) |

## Data Location in Turner Dataset

This section describes where data from each electrode system is stored in the original MATLAB files and metadata table.

### Recording Electrode Data

**Spike times** are stored in each session's MATLAB file:

| Variable | Description | Format |
|----------|-------------|--------|
| `unit_ts` | Spike times per trial | Matrix (n_trials x max_spikes), NaN-padded, times in ms |

**Local field potential** (LFP) from the recording electrode:

| Variable | Description | Format |
|----------|-------------|--------|
| `Analog.lfp[trial_idx]` | Low-pass filtered microelectrode signal | 10k gain, 1-100 Hz bandpass |
| `lfp_collected` | Availability flag | Metadata table column (1/0) |

**Recording location** is documented in the metadata table (`ven_table.csv`):

| Column | Description |
|--------|-------------|
| `Depth` | Electrode depth in mm below chamber reference |
| `A_P` | Anterior-posterior position relative to chamber center (mm) |
| `M_L` | Medial-lateral position relative to chamber center (mm) |

### Antidromic Stimulation Data

**Raw stimulation sweeps** are stored in session MATLAB files (when available):

| Variable | Content | Sampling |
|----------|---------|----------|
| `PedStim` | Cerebral peduncle stimulation data | 20 kHz, 50 ms sweeps |
| `StrStim` | Striatum (putamen) stimulation data | 20 kHz, 50 ms sweeps |
| `ThalStim` | Thalamus stimulation data (rare) | 20 kHz, 50 ms sweeps |
| `STNStim` | Subthalamic nucleus stimulation data (rare) | 20 kHz, 50 ms sweeps |

**Stimulation sweep structure** (e.g., `StrStim`):

| Field | Description |
|-------|-------------|
| `.TraceName` | Test type: `coll_n` (collision), `ff_n` (frequency following) |
| `.Curr` | Stimulation current delivered |
| `.Unit` | Raw single-unit signal during stimulation |
| `.Time` | Timebase relative to shock delivery |

**Cell type classification results** are in the metadata table:

| Column | Description |
|--------|-------------|
| `Antidrom` | Classification result: `PED`, `STRI`, `THAL`, `NR`, `NT`, or combinations |
| `Latency` | Primary antidromic latency (ms) |
| `Threshold` | Primary stimulation threshold (microAmps) |
| `LAT2` | Secondary site latency (if dual activation) |
| `Thresh2` | Secondary site threshold (if dual activation) |
| `StimData` | Availability flag: `Ped`, `Str`, `Ped/Str`, or empty |

**Note**: Stimulation sweep data (`PedStim`, `StrStim`, etc.) were collected only for a subset of sessions. Sweeps were rarely saved if no antidromic response was observed online.

### ICMS Data

Intracortical microstimulation was used as a **verification procedure** during experiments and is **not explicitly stored** in the dataset. The procedure confirmed recording sites were in arm-related motor cortex before data collection began.

### EMG Data

**EMG signals** are stored in session MATLAB files:

| Variable | Description | Format |
|----------|-------------|--------|
| `Analog.emg[trial_idx]` | EMG from arm muscles | (time_points, n_muscles), rectified & low-pass filtered |

**Availability** is indicated in the metadata table:

| Column | Description |
|--------|-------------|
| `emg_collected` | Boolean flag (1/0) indicating EMG data presence |

**Note**: Not all sessions include EMG data. The number of muscles varies by subject (5 muscles for Monkey V, 5 for Monkey L).

### Quick Reference: Finding Data by Electrode Type

```
Recording Electrode:
├── Spike times:      MATLAB file → unit_ts
├── LFP signal:       MATLAB file → Analog.lfp (if lfp_collected=1)
└── Location:         Metadata → Depth, A_P, M_L

Antidromic Stimulation:
├── Raw sweeps:       MATLAB file → PedStim, StrStim (if StimData not empty)
├── Classification:   Metadata → Antidrom column
├── Latency:          Metadata → Latency, LAT2 columns
└── Threshold:        Metadata → Threshold, Thresh2 columns

EMG Electrodes:
├── Signals:          MATLAB file → Analog.emg (if emg_collected=1)
└── Availability:     Metadata → emg_collected column

ICMS:
└── Not stored (verification procedure only)
```

## References

Electrode specifications and procedures are described in:

- Pasquereau B, Turner RS (2011) Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons. *Cerebral Cortex* 21:1362-1378.

- Pasquereau B, Turner RS (2013) Primary motor cortex of the parkinsonian monkey: altered neuronal responses to muscle stretch. *Frontiers in Systems Neuroscience* 7:98.

- Pasquereau B, DeLong MR, Turner RS (2016) Primary motor cortex of the parkinsonian monkey: altered encoding of active movement. *Brain* 139:127-143.
