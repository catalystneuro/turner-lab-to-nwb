# Conversion Notes

## Scope of Work
[link](https://docs.google.com/document/d/1QiJqoLkSIVx7yHg-PSUnLraxlkd_eu4RJP-V5XMEvEw/edit?usp=sharing)

(this is private)


### Data Streams to Convert

The conversion pipeline will handle the following data streams:

- **Extracellular electrophysiology**
    - Spike times
    - Waveforms
    - Antidromic stimulation traces

- **Behavioral task events**
    - Trial timing
    - Reach targets
    - Perturbations
    - Rewards

- **Analog kinematics**
    - Elbow joint angle

- **LFP signals**
    - Trial-based (when present)

- **EMG signals**
    - Trial-based (when present)


### Electrode Coordinate System

The Turner lab dataset uses **chamber-relative coordinates** rather than absolute stereotactic atlas coordinates:

#### **Coordinate Reference Frame**
- **Origin**: Chamber center/reference point (surgically positioned over left M1)
- **Chamber specifications**: Cylindrical stainless steel, 35° coronal angle
- **Coordinate system type**: Subject-specific, chamber-relative coordinates

#### **Coordinate Definitions**  
- **A_P**: Anterior-Posterior position relative to chamber center (mm, positive = anterior)
- **M_L**: Medial-Lateral position relative to chamber center (mm, positive = lateral)  
- **Depth**: Electrode depth below chamber reference point (mm, positive = deeper)

#### **Anatomical Context**
- **Target region**: Primary motor cortex (M1), arm representation area
- **Functional verification**: Electrode locations confirmed via microstimulation (≤40μA, 10 pulses at 300Hz)
- **Anatomical landmark**: Within 3mm of anterior bank of central sulcus
- **Layer targeting**: Layer 5 pyramidal neurons (PTNs and CSNs)

#### **Clinical/Scientific Context**
- **Initial targeting**: Chamber surgically positioned using stereotactic atlas coordinates
- **Daily recordings**: Electrode positions defined relative to chamber for precision and reproducibility
- **Cross-study comparisons**: Would require individual transformation to atlas coordinates
- **Coordinate precision**: Sub-millimeter accuracy within chamber reference frame

#### **Atlas Relationship**
These coordinates do NOT directly correspond to standard macaque brain atlas coordinates (Horsley-Clarke, MNI Macaque Atlas, AC/PC-based). They represent positions within a subject-specific coordinate frame defined by the implanted recording chamber. For cross-study analysis, coordinates would need individual transformation based on each animal's anatomy and chamber placement.

### Data Stream Locations in MATLAB Files

#### **Extracellular Electrophysiology**
- **Spike times**: `unit_ts` matrix - **Two data formats encountered:**
  - **Standard format**: Shape (n_trials, max_spikes_per_trial), padded with NaNs
  - **Compact format**: Shape (n_values,) - 1D array with one value per condition/trial
  - The conversion handles both formats automatically
- **Waveforms**: Not stored (online spike sorting performed during recording)
- **Antidromic stimulation traces**: 
  - `StrStim` - Striatum stimulation sweeps (50ms, 20kHz)
  - `PedStim` - Cerebral peduncle stimulation sweeps
  - `ThalStim` - Thalamus stimulation sweeps  
  - `STNStim` - Subthalamic nucleus stimulation sweeps

#### **Behavioral Task Events**
- **Trial timing**: `Events` structure
  - `Events.home_cue_on` - Start position target appearance
  - `Events.targ_cue_on` - Peripheral target appearance
  - `Events.home_leave` - Movement onset (cursor exit from start)
  - `Events.reward` - Reward delivery time
- **Reach targets**: `Events.targ_dir` (1=flexion, 2=extension)
- **Perturbations**: `Events.tq_flex`, `Events.tq_ext` (torque perturbation onsets, when present)

#### **Analog Kinematics**
- **Elbow joint angle**: `Analog.x[trial_idx]` (1kHz sampling for monkey Ven)
- **Angular velocity**: `Analog.vel[trial_idx]` (calculated from position)
- **Torque commands**: `Analog.torq[trial_idx]` (motor control signals)
- **Movement parameters**: `Mvt` structure with extracted measures
  - `Mvt.onset_t`, `Mvt.end_t`, `Mvt.pkvel`, `Mvt.mvt_amp`

#### **LFP Signals**
- **Location**: `Analog.lfp[trial_idx]` (when present)
- **Properties**: 1-100Hz bandpass, 10k gain, trial-based segments
- **Availability**: Check metadata `lfp_collected` flag

#### **EMG Signals**  
- **Location**: `Analog.emg[trial_idx]` (when present)
- **Properties**: 5-6 arm muscles, rectified & low-pass filtered
- **Shape**: (time_points, n_muscles)
- **Availability**: Check metadata `emg_collected` flag

#### **Cell Type Identification**
- **Source**: Metadata table `ven_table.csv`, column `Antidrom`
- **Classifications**:
  - `PED` = Pyramidal tract neurons (PTNs) 
  - `STRI` = Corticostriatal neurons (CSNs)
  - `NR` = No response, `NT` = Not tested

**📖 Complete reading instructions**: [File Structure Documentation](assets/data_exploration/file_structure.md)

### Data Format Variations

#### **Spike Times (`unit_ts`) Format Differences**

During conversion development, we encountered two different `unit_ts` data formats that require special handling:

**Standard 2D Format (Most files):**
- Shape: `(n_trials, max_spikes_per_trial)`
- Example: `(20, 138)` = 20 trials, up to 138 spikes per trial
- Data: Multiple spike times per trial, NaN-padded
- Usage: Typical format allowing multiple spikes per trial

**Compact 1D Format (Some files like v3601.1.mat, v5604b.2.mat):**
- Shape: `(n_values,)`  
- Example: `(20,)` or `(40,)`
- Data: Single representative spike time per trial/condition
- Usage: Simplified format with one spike time per trial, NaN when no spike

**What we observed:**
- v3601.1.mat: 1D array shape `(20,)` with 4 non-NaN values out of 20
- v5604b.2.mat: 1D array shape `(40,)` with 29 non-NaN values out of 40  
- Standard files: 2D array like `(20, 138)` with multiple spikes per trial

**Expected trial counts (verified from metadata table and file_info):**
- v3601.1.mat: `ntrials1_1=10, ntrials1_2=10` (total=20), `file_info.trial_n=20`, Events confirms 20 behavioral trials
- v5604b.2.mat: `ntrials1_1=20, ntrials1_2=20` (total=40), `file_info.trial_n=40`, Events confirms 40 behavioral trials
- Standard files: Same pattern, e.g., v0502.1.mat has 20 behavioral trials but 2D `unit_ts` shape `(20, 138)`

**Key insight**: The 1D `unit_ts` array length **exactly matches** the total number of behavioral trials:
- 1D format: Array length = total behavioral trials (one-to-one mapping)
- 2D format: First dimension = total behavioral trials, second dimension = max spikes per trial

**What we expected:**
- All files to follow the standard 2D format based on initial data exploration

**What needs clarification with data authors:**
1. **Data collection difference**: Why some sessions used 1D vs 2D spike recording format?
2. **Temporal meaning**: In 1D format, does each element represent:
   - Single spike per trial (most likely given one-to-one trial mapping)?
   - Peak/representative firing time within each trial?
   - First spike occurrence in each trial?
3. **Recording methodology**: Was spike detection/sorting different for 1D vs 2D sessions?
4. **Data completeness**: Are we losing spike data by using only one value per trial in 1D format?

**Current assumptions in conversion:**
- 1D format represents one spike time per behavioral trial
- Direct mapping: `unit_ts[i]` corresponds to behavioral trial `i`
- NaN values indicate trials with no recorded spikes
- We reshape 1D to 2D `(n_trials, 1)` for consistent NWB processing

**Current solution**: The conversion automatically detects format and reshapes 1D arrays to 2D `(n_values, 1)` for consistent processing.


## Keywords
**MPTP**: 1-methyl-4-phenyl-1,2,3,6-tetrahydropyridine — A neurotoxin used to induce parkinsonism in primates by selectively destroying dopaminergic neurons in the substantia nigra.

**M1**: Primary Motor Cortex — The cortical area essential for generating voluntary movement, also a target of basal ganglia-thalamocortical projections.

**SNc**: Substantia Nigra pars compacta — Midbrain structure containing dopaminergic neurons; degenerates in Parkinson’s disease (documented with TH immunostaining).

**BG**: Basal Ganglia — A group of subcortical nuclei involved in motor control and strongly implicated in Parkinson’s disease pathophysiology.

**PTN**: Pyramidal Tract-type Neuron — Cortical neurons in layer 5b projecting to the spinal cord (via corticospinal tract). Strongly affected by MPTP; central to conveying motor commands.

**CSN**: Corticostriatal Neuron — Cortical intratelencephalic neurons projecting to the striatum; relatively spared in parkinsonism compared to PTNs.

**GLM**: Generalized Linear Model — Statistical model used to quantify spike-rate encoding of kinematic parameters (direction, position, speed, acceleration).

**SDF**: Spike Density Function — A continuous estimate of neuronal firing rate over time, built by convolving spike trains with a kernel.

**EMG**: Electromyography — Muscle electrical activity recordings, used to assess motor output during movements and reflexes.

**LLSR**: Long-Latency Stretch Reflex — A transcortical reflex response to muscle stretch, exaggerated in Parkinson’s disease and thought to underlie rigidity.

**RT**: Reaction Time — Delay between stimulus and initiation of movement, often prolonged after MPTP.

**MD**: Movement Duration — Time taken to complete a movement, typically lengthened in parkinsonism.

**Velmax / Acc**: Peak Velocity / Acceleration — Kinematic parameters encoded by M1 neurons and affected by MPTP.

**TH**: Tyrosine Hydroxylase — Enzyme marker for dopaminergic neurons, used in histology to confirm MPTP-induced nigral cell loss.

## Trial Structure and Session Organization

### Dataset Organization Analysis

Based on metadata analysis of the Turner Lab dataset:

**Recording Session Structure**:
- **359 MATLAB files** across **85 unique recording dates**
- **Multiple sessions per day**: 1-11 recording sessions on the same date
- **Each session contains 2-40 trials** (mean: ~14 trials per session)

**Evidence from metadata table (`ven_table.csv`)**:
```python
# Analysis shows:
unique_dates = df['DateCollected'].nunique()  # 85 dates
total_files = len(df)  # 359 files
trials_per_session = df['ntrials1_1'].mean()  # ~14 trials average
```

**Same-day recordings represent different sessions because**:
- Different electrode depths and spatial coordinates (A-P, M-L)
- Different units isolated (UnitNum1, UnitNum2)
- Independent trial sequences with complete data streams
- Distinct cell type identification results per session

### Session-Level Organization

Each MATLAB file represents a distinct recording session with:
- **Spatial specificity**: Unique electrode placement (depth, A-P, M-L coordinates)
- **Neural specificity**: 1-2 isolated single units with antidromic identification
- **Temporal specificity**: Complete trial sequence with behavioral and neural data
- **Experimental context**: Pre/Post MPTP condition, recording date, sensory responses

### Same-Day Recording Strategy

Example from metadata analysis:
```
21-Jan-2000 (11 sessions):
- v4507-v4513: Sequential electrode advancement
- Depth progression: 18.45mm → 20.00mm
- Systematic cell type identification across cortical layers
```

This approach enabled systematic exploration of cortical space and identification of different neuron types within single experimental days.

### NWB Conversion Implications

**Conclusion**: **One MATLAB file → One NWB session**

This session-based approach:
1. Preserves scientific integrity of individual recording sessions
2. Maintains spatial and temporal relationships within each session
3. Enables both single-session analysis and cross-session comparisons
4. Properly represents the experimental methodology

**🔗 Detailed NWB conversion strategy**: [NWB Conversion Documentation](assets/data_exploration/nwb_conversion.md)

## Trial Structure Within Recording Sessions

### Trial description in the papers
The description of the trial in the paper is the following:

** active movement paper**
> A trial began when a centre target appeared on the monitor and the monkey aligned the cursor with the target. After holding the cursor at this start-position hold period (2–5 s, uniform random distribution), the target jumped to the left or right (chosen at random), and the animal moved the cursor to capture the lateral target. After a target-hold interval (0.75–1.5 s), the animal received a drop of juice or food, followed by an intertrial interval (1.2–1.7 s).

** Stretch paper ** 
The description in another paper:
> A trial began when a center target appeared and the monkey made the appropriate joint movement to align the cursor with the target. The monkey maintained this position for the duration of a start-position hold period (random duration, 2–5 s), during which the animal could not predict the location of the upcoming lateral target. The target then shifted to the left or right (chosen at random), and the animal moved the cursor to capture the lateral target. The animal received a drop of juice for successful completion of the task.

> On two‑thirds of the trials (selected at random), single flexing or extending torque impulses (0.1 Nm–50 ms duration) were applied to the manipulandum by a DC brushless torque motor (TQ40W, Aerotech Inc., Pittsburgh PA) at an unpredictable time beginning 1–2 s (uniform randomized distribution) after initial capture of the center target. Each square‑wave torque impulse induced an angular displacement of the joint (mean = 10‑deg) causing a sudden stretch of arm extensor or flexor muscles. The animals were not trained to produce a specific response to these unpredictable perturbations, but the animals naturally adopted a strategy that returned the joint to its initial pre‑impulse position.

** Pyramidal tract neurons paper**
> On each behavioral trial, the animal was required to align the cursor with a series of targets displayed on the monitor. A trial began when a center target appeared and the monkey made the appropriate joint movement to align the cursor with the target. The monkey maintained this position for the duration of a start-position hold period (random duration, 2–5 s), during which the animal could not predict the location of the upcoming lateral target. The target then shifted to the left or right (chosen at random), and the animal moved the cursor to capture the lateral target. The animal received a drop of juice or food for successful completion of the task.


### Visual Overview
![Experimental Protocol](./assets/figures/active_paper_figure_1_diagram.png)

**Figure Analysis**: This experimental protocol diagram shows the visuomotor step-tracking task structure. The monkey begins by maintaining cursor position at a center hold target (top panel). After a variable hold period (~2.5s), a peripheral target appears requiring either flexion (FLX) or extension (EXT) elbow movement. The monkey must move the cursor from center to the target (movement phase), then maintain position at the target (target hold, 0.75-1.5s) to receive liquid reward. The paradigm tests elbow joint motor control through a simple center-out reaching task with two possible directions corresponding to anatomical flexion/extension movements.


### Trial Temporal Structure

Based on analysis of 359 MATLAB files containing 9,949 trials, the experimental protocol follows this chronological sequence:

```
Trial Timeline (mean timings from 9,949 trials):

Trial Start (0ms)
    │
    ├── Center Target Appearance (2,453ms ± 756ms)
    │   • Visual cue for monkey to align cursor with center position
    │   • Range: 1.3-11.4s, establishes baseline elbow position
    │   
    ├── [Hold Period: ~4.1s average]
    │   • Monkey maintains cursor at center target
    │   • Torque perturbations applied here when present (1-2s after capture)
    │     └── Torque Impulse: 0.1 Nm, 50ms, causing ~10° displacement
    │
    ├── Lateral Target Appearance (6,563ms ± 1,288ms)
    │   • Peripheral target signals movement direction (flexion/extension)  
    │   • Range: 4.0-20.6s, determines required motor response
    │
    ├── [Reaction Time: ~430ms average]
    │   • Motor planning and decision period
    │
    ├── Subject Movement Onset (6,993ms ± 1,291ms)
    │   • Monkey begins movement from center toward lateral target
    │   • Range: 4.3-21.4s, volitional movement initiation
    │   │
    │   ├── Derived Movement Onset (6,898ms ± 1,273ms)
    │   │   • Algorithmically detected movement start from kinematics
    │   │
    │   ├── Peak Velocity Time (7,089ms ± 1,272ms) 
    │   │   • Maximum velocity: 101.9±37.5°/s (range: 20.2-254.8°/s)
    │   │
    │   └── Derived Movement End (7,286ms ± 1,276ms)
    │       • Movement amplitude: -3.4±19.7° (range: -37.9° to 30.4°)
    │       • End position: -1.3±19.5° (range: -28.8° to 30.1°)
    │
    ├── Reward Delivery (7,950ms ± 1,319ms)
    │   • Liquid reward for successful target acquisition
    │   • Range: 5.3-22.3s, ~957ms after movement onset
    │
    └── Recording End (8,748ms ± 1,382ms)
        • Analog data capture continues ~799ms beyond reward
        • Total duration: 1.5-23.1s per trial (mean: 8.7s)
        • 1kHz sampling for position, velocity, torque, EMG, LFP
        • Spike times recorded throughout with millisecond precision
```

**Key Temporal Features:**
- Variable trial durations accommodate different behavioral states in parkinsonian monkeys
- Extended hold periods ensure stable starting positions for movement analysis  
- Post-reward data collection captures movement completion and return-to-baseline
- High temporal resolution (1ms) enables precise neural-behavioral correlations


## Scientific Papers and Experimental Protocols

The Turner Lab ASAP M1 MPTP dataset supports **three complementary research studies** that examined different aspects of motor cortex dysfunction in MPTP-induced parkinsonism using the same fundamental experimental setup.

### Paper 1: Active Movement Encoding

**Research Hypothesis**: MPTP-induced parkinsonism alters M1 encoding of voluntary movement kinematics through three potential mechanisms: hypoactivation (reduced excitatory drive), loss of functional specificity (degraded selectivity), or abnormal timing (altered temporal dynamics). The study specifically tested whether pyramidal tract neurons (PTNs) and corticostriatal neurons (CSNs) show differential vulnerabilities in movement parameter encoding.

**Data Captured**: Single-unit recordings during visuomotor step-tracking task with focus on movement-related neural activity, kinematic parameter encoding (position, velocity, acceleration, direction), and cell-type specific responses during active reaching movements.

### Paper 2: Muscle Stretch Responses  

**Research Hypothesis**: MPTP-induced parkinsonism alters cortical processing of proprioceptive information through enhanced cortical excitability, degraded spatial selectivity, or temporal dysregulation of stretch reflex pathways. The study examined whether the long-latency stretch reflex (LLSR) mediated through M1 shows abnormal enhancement in parkinsonism.

**Data Captured**: Neural responses to unexpected torque perturbations during the reaching task, with focus on stretch-evoked activity, response latencies, directional selectivity during passive limb manipulation, and proprioceptive feedback processing.

### Paper 3: Pyramidal Tract Neuron Spontaneous Activity

**Research Hypothesis**: MPTP-induced parkinsonism affects resting-state cortical activity in a cell-type specific manner, with pyramidal tract neurons showing differential vulnerability compared to corticostriatal neurons during non-movement periods.

**Data Captured**: Spontaneous firing rates during rest periods, baseline neural activity during inter-trial intervals and center hold phases, with emphasis on cell-type identification and comparison of resting-state activity patterns.

## Data Stream Utilization Across Studies

| Data Stream | Description | Paper 1: Active Movement | Paper 2: Muscle Stretch | Paper 3: Spontaneous Activity |
|-------------|-------------|---------------------------|--------------------------|-------------------------------|
| **Spike Times (`unit_ts`)** | Single-unit action potentials, trial-based timing | Used: Movement-related firing patterns | Used: Stretch-evoked neural responses | Used: Baseline activity during rest |
| **Trial Events (`Events.home_cue_on`)** | Start position target appearance | Used: Trial structure timing | Not used | Not used |
| **Trial Events (`Events.targ_cue_on`)** | Peripheral target appearance | Used: Movement cue timing | Not used | Not used |
| **Trial Events (`Events.targ_dir`)** | Target direction (1=flex, 2=ext) | Used: Direction-specific encoding | Not used | Not used |
| **Trial Events (`Events.home_leave`)** | Movement onset timing | Used: Movement initiation analysis | Not used | Not used |
| **Trial Events (`Events.reward`)** | Reward delivery timing | Used: Task completion timing | Not used | Not used |
| **Perturbation Events (`Events.tq_flex`)** | Flexion torque perturbation onset | Not used | Used: Stretch reflex timing | Not used |
| **Perturbation Events (`Events.tq_ext`)** | Extension torque perturbation onset | Not used | Used: Stretch reflex timing | Not used |
| **Joint Position (`Analog.x`)** | Elbow/wrist angle during movement | Used: Kinematic parameter encoding | Used: Joint position during stretch | Not used |
| **Joint Velocity (`Analog.vel`)** | Angular velocity of movement | Used: Velocity encoding analysis | Used: Velocity during perturbations | Not used |
| **Torque Commands (`Analog.torq`)** | Motor control signals | Used: Movement control analysis | Used: Perturbation force delivery | Not used |
| **EMG Signals (`Analog.emg`)** | Muscle electrical activity | Not used | Used: Stretch reflex responses | Not used |
| **LFP Signals (`Analog.lfp`)** | Local field potential | Not used | Not used | Not used |
| **Movement Parameters (`Mvt.onset_t`, `Mvt.pkvel`, etc.)** | Extracted movement kinematics | Used: Movement parameter decoding | Not used | Not used |
| **Antidromic Stimulation (`StrStim`, `PedStim`)** | Cell type identification traces | Used: PTN vs CSN classification | Used: PTN vs CSN classification | Used: PTN vs CSN classification |
| **Cell Type Metadata (`Antidrom` column)** | PTN/CSN classification results | Used: Cell-type specific analysis | Used: Cell-type specific analysis | Used: Cell-type specific analysis |
| **Spatial Coordinates (`A_P`, `M_L`, `Depth`)** | Electrode recording location | Not used | Not used | Not used |
| **MPTP Condition (`MPTP` column)** | Pre/Post treatment classification | Used: Condition comparison | Used: Condition comparison | Used: Condition comparison |

## Unified Experimental Protocol

All studies used the same **visuomotor step-tracking paradigm**:

```
                    EXPERIMENTAL PROTOCOL
                   Turner Lab MPTP Studies

┌─────────────────────────────────────────────────────────────────┐
│                      TRIAL STRUCTURE                            │
│                                                                 │
│  ┌─────────┐    ┌────────────┐    ┌─────────────┐    ┌───────┐  │
│  │ CENTER  │────│   TARGET   │────│  MOVEMENT   │────│REWARD │  │
│  │  HOLD   │    │PRESENTATION│    │ EXECUTION   │    │       │  │
│  │         │    │            │    │             │    │       │  │
│  │Variable │    │Left/Right  │    │Flexion/     │    │Liquid │  │
│  │duration │    │peripheral  │    │Extension    │    │reward │  │
│  │         │    │target      │    │reaching     │    │       │  │
│  └─────────┘    └────────────┘    └─────────────┘    └───────┘  │
│                                                                 │
│             PERTURBATIONS (random subset of trials)            │
│             ┌─────────────────────────────────────┐            │
│             │ Unexpected torque pulses            │            │
│             │ • Flexion (tq_flex) or Extension   │            │
│             │ • Applied during movement phase     │            │
│             │ • Elicit stretch reflex responses   │            │
│             └─────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```
## DATA ANALYSIS FOCUS BY STUDY

| Paper 1: Movement Phase | Paper 2: Perturbation Trials | Paper 3: Hold/Rest Periods |
|---|---|---|
| Target → Movement phase | tq_flex/tq_ext responses | Center hold baseline |
| Kinematic encoding | Stretch-evoked activity | Inter-trial intervals |
| Direction-specific activity | LLSR timing analysis | Spontaneous firing |
| Movement parameter decoding | Proprioceptive processing | Cell-type comparisons |

## Data Organization for Multi-Study Support

**Single experimental paradigm, multiple analytical perspectives**:

- **Events structure**: Supports timing analysis for all three studies
- **Spike data**: Same neural recordings provide movement encoding, stretch responses, and spontaneous activity
- **Analog signals**: Joint kinematics support both voluntary movement and perturbation analyses
- **Perturbation identification**: Trials with torque perturbations identified by non-NaN values in `tq_flex`/`tq_ext`
- **Cell type metadata**: Antidromic identification enables cell-type specific analyses across all studies