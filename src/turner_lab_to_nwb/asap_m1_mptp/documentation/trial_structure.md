# Behavioral Task and Trial Structure

## Overview

The Turner lab MPTP dataset contains recordings from macaque monkeys performing a visuomotor step-tracking task. This center-out reaching paradigm requires rapid, ballistic arm movements and provides a controlled framework for studying how parkinsonism affects cortical motor control. Each trial captures the full sequence of neural and muscular activity from target appearance through movement execution and reward delivery.

**Related documentation:**
- [EMG Recordings](emg_recordings.md) - Muscle activity during the task
- [Anatomical Coordinates](anatomical_coordinates.md) - Recording site locations in motor cortex
- [Antidromic Stimulation](antidromic_stimulation.md) - Neuron classification methods
- [Trial Boundary Options](../assets/data_exploration/trial_boundary_options.md) - Technical details on NWB trial boundary definitions

---

## Part 1: The Visuomotor Step-Tracking Task

### Scientific Purpose

The task was designed to elicit rapid, visually-guided arm movements that engage primary motor cortex (M1). Key features include:

1. **Ballistic movements**: Quick, discrete movements that cannot be corrected mid-flight, reflecting the initial motor command
2. **Directional selectivity**: Alternating flexion and extension movements allow assessment of directional tuning in M1 neurons
3. **Consistent kinematics**: Standardized movement amplitude and speed enable comparison across conditions
4. **Longitudinal design**: Same task performed before and after MPTP treatment allows direct comparison

### The Manipulandum

Monkeys controlled a cursor on a video display by rotating their elbow within a manipulandum, a mechanical device that converts arm movement into electronic signals:

- **Movement axis**: Single degree of freedom (elbow flexion/extension)
- **Coupling**: Rotating handle connected to a torque motor
- **Feedback**: Real-time cursor position displayed on screen
- **Perturbations**: Torque motor could deliver controlled mechanical perturbations (used in the muscle stretch study)

### Why This Task?

The step-tracking paradigm is well-established in motor neuroscience for studying cortical motor control because:

- It isolates movement initiation and execution from complex planning
- Movement parameters (direction, amplitude, speed) are experimentally controlled
- Reaction times can be measured precisely
- The same neural circuits are repeatedly engaged across trials
- Compatible with simultaneous single-unit recording

---

## Part 2: Trial Structure

Each trial follows a stereotyped sequence of events. The monkey must complete each phase successfully to receive a liquid reward.

### Phase 1: Inter-trial Interval

**Duration**: Variable (typically 2-3 seconds)

Between trials, the monkey rests. No specific cursor position is required. This period allows the animal to consume the previous reward and provides a baseline period for neural activity.

### Phase 2: Center Hold

**Duration**: 1-2 seconds (randomized)

**Events**:
- Center target appears on screen
- Monkey moves cursor to center target
- Monkey must hold cursor within target zone

**Purpose**:
- Establishes consistent starting position for all movements
- Randomized hold duration prevents anticipatory movements
- Allows assessment of preparatory neural activity

**Neural correlates**:
- Low, sustained firing rates in M1 neurons
- Some neurons show preparatory activity during the hold period
- PTNs and CSNs both active during center hold

### Phase 3: Go Cue / Target Appearance

**Event**: Peripheral target appears (flexion or extension direction)

**Timing**: Occurs at end of center hold period

**Parameters**:
- Target direction pseudorandomized across trials
- Target amplitude: fixed within session (typically 20-25 degrees)
- Visual feedback: immediate cursor-target display

**Neural correlates**:
- Directionally-tuned neurons begin modulating activity
- Pre-movement activity builds before actual movement onset
- PTNs show stronger directional tuning than CSNs

### Phase 4: Reaction Time

**Duration**: Typically 200-400 ms

**Definition**: Time from go cue (target appearance) to movement onset

**Significance**:
- Reflects motor planning and preparation time
- Prolonged in parkinsonism (part of akinesia/bradykinesia)
- Neural activity during this period predicts movement parameters

### Phase 5: Movement Execution

**Duration**: Typically 150-300 ms

**Kinematics measured**:
| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| Peak velocity | Maximum movement speed | 80-120 degrees/second |
| Movement duration | Onset to target acquisition | 150-300 ms |
| Peak acceleration | Maximum rate of velocity change | Variable |
| Movement amplitude | Total angular displacement | 20-25 degrees |

**Neural correlates**:
- Peak firing rates in movement-related neurons
- PTNs show strongest modulation during this phase
- Activity correlates with movement kinematics (velocity, direction)

**Post-MPTP changes**:
- Reduced peak velocity (bradykinesia)
- Prolonged movement duration
- Reduced movement amplitude (hypometria)
- Reduced and delayed neural activity in PTNs

### Phase 6: Target Hold

**Duration**: Variable (typically 0.5-1 second)

**Requirement**: Cursor must remain within peripheral target zone

**Purpose**:
- Ensures movement was completed accurately
- Prevents premature reward delivery
- Provides post-movement neural activity window

### Phase 7: Reward

**Event**: Liquid reward delivered upon successful target hold

**Significance**:
- Marks behavioral completion of trial
- Provides positive reinforcement
- Reward timing can influence neural activity in some circuits

---

## Part 3: Trial Timeline Visualization

```
Trial Start (0 ms)
    |
    |--- [Pre-task baseline: ~2.5 s average] ---
    |
    +-- Center Target Appearance (~2.5 s)
    |     Monkey aligns cursor to center
    |
    |--- [Center Hold: 1-2 s randomized] ---
    |
    +-- Lateral Target Appearance / Go Cue (~6.5 s)
    |     Peripheral target signals movement direction
    |
    |--- [Reaction Time: ~300-500 ms] ---
    |
    +-- Movement Onset (~7.0 s)
    |     |
    |     +-- Peak Velocity (~7.1 s)
    |     |     Maximum movement speed
    |     |
    |     +-- Movement End (~7.3 s)
    |           Target acquired
    |
    |--- [Target Hold: 0.5-1 s] ---
    |
    +-- Reward Delivery (~8.0 s)
    |     Liquid reward for successful completion
    |
    +-- Recording End (~8.7 s)
          Data capture continues briefly post-reward
```

### Timing Statistics

Based on analysis of 9,949 trials across 359 recording sessions:

| Event | Mean Time | Standard Deviation | Range |
|-------|-----------|-------------------|-------|
| Center target on | 2,453 ms | 756 ms | 1,272-11,420 ms |
| Lateral target on | 6,563 ms | 1,288 ms | 4,042-20,586 ms |
| Movement onset | 6,993 ms | 1,291 ms | 4,330-21,362 ms |
| Peak velocity | 7,089 ms | 1,272 ms | 4,518-21,386 ms |
| Movement end | 7,286 ms | 1,276 ms | 4,697-21,563 ms |
| Reward | 7,950 ms | 1,319 ms | 5,305-22,331 ms |

Note: All times are relative to trial start (time 0). The wide ranges reflect variation in center hold duration and occasional atypical trials.

### Aborted and Incomplete Trials

Not all trials in the dataset were completed successfully. The NWB files preserve these trials with missing values (NaN) for events that did not occur.

**Aborted trials**: Trials where the monkey broke fixation or the trial was manually terminated before the go cue. These trials have:
- `lateral_target_appearance_time` = NaN (go cue never presented)
- `cursor_departure_time` = NaN
- `reward_time` = NaN
- All derived kinematic columns = NaN

**Trials with missing kinematic data**: Some completed trials (with reward delivery) lack derived movement parameters. This occurs when the kinematic detection algorithm could not reliably identify movement onset/end, typically because:
- The movement was atypical (very slow, multi-phasic, or corrective)
- Post-MPTP bradykinesia produced velocity profiles that didn't meet detection criteria
- The velocity trace was noisy or ambiguous

For these trials:
- Behavioral events (`lateral_target_appearance_time`, `cursor_departure_time`, `reward_time`) are present
- Derived columns (`derived_movement_onset_time`, `derived_movement_end_time`, `derived_peak_velocity`, etc.) = NaN

**Handling in analysis**: When analyzing trial data, filter for complete trials:

```python
# Get only complete trials with kinematic data
complete_trials = trials_df.dropna(subset=['derived_movement_end_time'])

# Get only successful trials (may lack kinematic data)
successful_trials = trials_df.dropna(subset=['reward_time'])
```

---

## Part 4: Torque Perturbation Trials

A subset of trials included brief mechanical perturbations delivered during the center hold period. These trials were used in the muscle stretch study to examine proprioceptive responses.

### Perturbation Parameters

| Parameter | Value |
|-----------|-------|
| Torque magnitude | 0.1 Nm |
| Duration | 50 ms |
| Resulting displacement | ~10 degrees |
| Direction | Flexion or extension |
| Timing | 1-2 seconds after center target capture |

### Purpose

Torque perturbations activate muscle spindle afferents, triggering stretch reflex responses. By recording M1 neurons during these perturbations, researchers could:

1. Measure cortical responses to proprioceptive input
2. Compare transcortical reflex components across conditions
3. Assess whether parkinsonian rigidity involves cortical hyperexcitability

### Key Finding

Post-MPTP, the long-latency stretch reflex (measured via EMG) was enhanced, but M1 cortical responses were not enhanced. This dissociation suggests the exaggerated stretch reflex in parkinsonism is primarily mediated by spinal mechanisms rather than cortical hyperexcitability.

---

## Part 5: Trial Events in NWB Files

### Trials Table Structure

Each trial is represented as a row in the NWB trials table with the following columns:

| Column | Description | Units |
|--------|-------------|-------|
| `start_time` | Trial start relative to session | seconds |
| `stop_time` | Trial end relative to session | seconds |
| `go_cue_time` | Target appearance (movement cue) | seconds |
| `movement_onset_time` | Subject-reported movement start | seconds |
| `reward_time` | Reward delivery | seconds |
| `target_direction` | Movement direction | "flexion" or "extension" |

### Derived Kinematic Columns

| Column | Description | Units |
|--------|-------------|-------|
| `derived_movement_onset_time` | Algorithmically detected onset | seconds |
| `derived_movement_end_time` | Algorithmically detected end | seconds |
| `peak_velocity_time` | Time of maximum velocity | seconds |
| `peak_velocity` | Maximum velocity magnitude | degrees/second |
| `movement_amplitude` | Total angular displacement | degrees |
| `end_position` | Final position | degrees |

### Perturbation Columns (when present)

| Column | Description | Units |
|--------|-------------|-------|
| `torque_flexion_time` | Flexion perturbation onset | seconds |
| `torque_extension_time` | Extension perturbation onset | seconds |

### Example: Accessing Trial Data

```python
from pynwb import NWBHDF5IO

with NWBHDF5IO('session.nwb', 'r') as io:
    nwbfile = io.read()

    # Get trials as DataFrame
    trials = nwbfile.trials.to_dataframe()

    # Find all extension trials
    extension_trials = trials[trials['target_direction'] == 'extension']

    # Calculate reaction times
    trials['reaction_time'] = trials['movement_onset_time'] - trials['go_cue_time']

    # Get mean reaction time
    print(f"Mean reaction time: {trials['reaction_time'].mean():.3f} seconds")
```

---

## Part 6: Alignment to Neural and Analog Data

### Temporal Alignment

All event times in the trials table are expressed in seconds relative to session start, allowing direct alignment with:

- **Spike times**: `nwbfile.units['spike_times']` are in the same timebase
- **Analog signals**: Position, velocity, EMG timestamps align directly
- **LFP data**: Same session-relative timing

### Extracting Peri-Event Activity

```python
import numpy as np

# Get spike times for a unit
unit_idx = 0
spike_times = nwbfile.units['spike_times'][unit_idx]

# Align to movement onset for first trial
trial = trials.iloc[0]
movement_onset = trial['movement_onset_time']

# Find spikes within window (-500 ms to +500 ms)
window = 0.5  # seconds
mask = (spike_times >= movement_onset - window) & (spike_times <= movement_onset + window)
aligned_spikes = spike_times[mask] - movement_onset  # Now relative to movement onset

print(f"Found {len(aligned_spikes)} spikes in peri-movement window")
```

### Trial-Averaged Analysis

The standard approach for analyzing movement-related neural activity:

1. Select trials by condition (e.g., extension movements only)
2. Align all trials to a common event (e.g., movement onset)
3. Bin spike times to create peri-event time histograms (PETHs)
4. Average across trials to estimate the neuron's response profile

---

## Part 7: Key Findings from the Active Movement Study

### Parkinsonian Motor Deficits

Behavioral analysis of task performance revealed characteristic parkinsonian changes post-MPTP:

| Measure | Pre-MPTP | Post-MPTP | Change |
|---------|----------|-----------|--------|
| Reaction time | ~300 ms | ~400 ms | +33% |
| Peak velocity | ~110 deg/s | ~80 deg/s | -27% |
| Movement duration | ~200 ms | ~300 ms | +50% |

### Neural Encoding Deficits

Using generalized linear models (GLMs), the study quantified how well M1 neurons encoded movement kinematics:

**Pyramidal Tract Neurons (PTNs)**:
- 50% reduction in movement-related activity
- 37% reduction in kinematic encoding strength
- Degraded directional tuning

**Corticostriatal Neurons (CSNs)**:
- 21% reduction in movement-related activity
- 18% reduction in kinematic encoding
- Relatively preserved directional tuning

### Interpretation

The selective impairment of PTNs (the direct cortical output to spinal cord) while CSNs (cortical input to basal ganglia) are relatively preserved suggests that:

1. Parkinsonian motor deficits reflect impaired cortical motor commands, not just basal ganglia dysfunction
2. The corticospinal pathway is preferentially affected
3. Reduced PTN activity directly contributes to bradykinesia through weakened motor commands

---

## References

- Pasquereau B, DeLong MR, Turner RS (2016) Primary motor cortex of the parkinsonian monkey: altered encoding of active movement. *Brain* 139:127-143.

- Pasquereau B, Turner RS (2013) Primary motor cortex of the parkinsonian monkey: altered neuronal responses to muscle stretch. *Frontiers in Systems Neuroscience* 7:98.

- Pasquereau B, Turner RS (2011) Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons. *Cerebral Cortex* 21:1362-1378.
