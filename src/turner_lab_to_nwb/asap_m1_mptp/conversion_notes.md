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

### Visual Overview
![Experimental Protocol](./assets/figures/active_paper_figure_1_diagram.png)

**Figure Analysis**: This experimental protocol diagram shows the visuomotor step-tracking task structure. The monkey begins by maintaining cursor position at a center hold target (top panel). After a variable hold period (~2.5s), a peripheral target appears requiring either flexion (FLX) or extension (EXT) elbow movement. The monkey must move the cursor from center to the target (movement phase), then maintain position at the target (target hold, 0.75-1.5s) to receive liquid reward. The paradigm tests elbow joint motor control through a simple center-out reaching task with two possible directions corresponding to anatomical flexion/extension movements.

### What Constitutes a Trial

Each trial in the Turner Lab dataset represents **one complete behavioral episode** of the flexion/extension motor task:

**Trial Definition**: A single reach from center position to a peripheral target, encompassing the complete sequence from initial cue presentation through reward delivery.

**What Changes Between Trials**:
- **Target direction**: Randomized flexion (1) or extension (2) movement
- **Hold period duration**: Pseudo-random center position hold time before target appearance
- **Torque perturbations**: Random subset of trials include unexpected torque pulses
- **Motor performance**: Natural variability in movement kinematics, reaction times, peak velocities

**What Remains Constant Within Session**:
- Task paradigm and experimental setup
- Electrode placement and recorded units
- Sampling rates and recording parameters
- Subject and experimental condition (Pre/Post MPTP)

### Trial Temporal Structure

Each trial follows a stereotyped sequence:

1. **Center Hold Period** (variable duration)
   - Monkey maintains cursor at start position
   - Baseline neural activity recorded

2. **Target Presentation** 
   - Peripheral target appears (left/right → flexion/extension)
   - Cue-related neural responses

3. **Movement Execution**
   - Cursor leaves center position
   - Reaching movement to target
   - Peak motor cortex activity

4. **Target Hold & Reward**
   - Cursor held within target zone
   - Reward delivery upon successful completion

**Trial Duration**: Variable (~2-4 seconds typical), depending on hold periods and movement speed

### Data Storage Structure in MATLAB Files

**Trial-indexed data organization**:

```python
# Example from v1401.1.mat with 20 trials
mat_file = read_mat("v1401.1.mat")

# Event timing (trial x event)
events = mat_file["Events"]
events["home_cue_on"]    # [20] array - start cue times for each trial
events["targ_cue_on"]    # [20] array - target cue times for each trial  
events["targ_dir"]       # [20] array - target direction per trial (1 or 2)
events["home_leave"]     # [20] array - movement onset times per trial
events["reward"]         # [20] array - reward delivery times per trial

# Spike data (trial x spike_times)
spike_times = mat_file["unit_ts"]  # Shape: (20, 29) - 20 trials, up to 29 spikes
# Each row = one trial's spike times, NaN-padded

# Analog data (signal_type -> trial array)
analog = mat_file["Analog"]
analog["x"]    # List of 20 arrays - position data per trial
analog["vel"]  # List of 20 arrays - velocity data per trial  
analog["emg"]  # List of 20 arrays - EMG data per trial (when present)

# Movement parameters (extracted per trial)
movement = mat_file["Mvt"]
movement["onset_t"]   # [20] array - movement onset per trial
movement["pkvel"]     # [20] array - peak velocity per trial
movement["mvt_amp"]   # [20] array - movement amplitude per trial
```

### Trial Variability and Randomization

**Randomized Elements**:
- **Target direction**: 1 (flexion) or 2 (extension) chosen randomly
- **Hold duration**: Variable center hold period before target appearance
- **Perturbation timing**: Random subset of trials include torque perturbations

**Example trial sequence** from metadata analysis:
```python
# Sample from v1401.1.mat
target_directions = [1, 2, 2, 1, 2, 1, 1, 2, 1, 2, ...]  # Random sequence
# Roughly equal numbers of flexion (1) and extension (2) trials
```

**Trial Independence**: Each trial represents an independent behavioral measurement, allowing statistical analysis of:
- Movement kinematics across conditions
- Neural firing patterns by target direction  
- Reaction time variability
- Motor learning or adaptation effects

### Neural Data Trial Structure

**Spike timing within trials**:
- All spike times referenced to trial start (t=0)
- Typical trial events occur at predictable relative times:
  - Home cue: ~2-4 seconds into trial
  - Target cue: Variable (after hold period)
  - Movement: ~300-500ms after target cue
  - Reward: ~1-2 seconds after movement

**Cross-trial analysis enabled**:
- Peri-event time histograms aligned to task events
- Population vector analysis across movement directions
- Trial-averaged firing rates by condition
- Movement parameter correlations with neural activity

This trial-based organization preserves the experimental structure essential for understanding motor cortex function during voluntary reaching movements.

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

              DATA ANALYSIS FOCUS BY STUDY

Paper 1: Movement Phase        Paper 2: Perturbation Trials    Paper 3: Hold/Rest Periods
• Target → Movement phase      • tq_flex/tq_ext responses     • Center hold baseline
• Kinematic encoding          • Stretch-evoked activity      • Inter-trial intervals  
• Direction-specific activity • LLSR timing analysis         • Spontaneous firing
• Movement parameter decoding • Proprioceptive processing    • Cell-type comparisons
```

## Data Organization for Multi-Study Support

**Single experimental paradigm, multiple analytical perspectives**:

- **Events structure**: Supports timing analysis for all three studies
- **Spike data**: Same neural recordings provide movement encoding, stretch responses, and spontaneous activity
- **Analog signals**: Joint kinematics support both voluntary movement and perturbation analyses
- **Perturbation identification**: Trials with torque perturbations identified by non-NaN values in `tq_flex`/`tq_ext`
- **Cell type metadata**: Antidromic identification enables cell-type specific analyses across all studies