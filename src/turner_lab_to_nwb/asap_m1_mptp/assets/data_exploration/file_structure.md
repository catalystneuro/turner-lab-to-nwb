# Primary Motor Cortex in Parkinsonian Macaques: Turner-Delong Dataset

## Dataset Contents

**Data location**: `/home/heberto/data/turner/Ven_All/`

**Total files**: 360 MATLAB files (`.mat`) + 1 metadata table (`VenTable.mat`)

**File naming verification**:
- **Standard format**: `v####.#.mat` (e.g., v1401.1.mat, v1102.2.mat) - 356 files
- **Secondary recordings**: `v####b.#.mat` (e.g., v1501b.1.mat, v3607b.2.mat) - 4 files  
- **Metadata table**: `VenTable.mat` - 1 file

**Recording sessions**: 359 total sessions documented in metadata (matches 360 files minus VenTable.mat)

## Overview

Files in this directory contain single-unit neuronal data collected from monkey subjects during performance of a single-dimension joint flexion/extension task.

The subject's arm was held in padded manipulandum with elbow or wrist joint aligned with a torque motor. Flexion/extension of the elbow or wrist joint moved a cursor and captured targets presented on a vertically-mounted display by of the contralateral arm. Targets consisted of 2 possible peripheral target locations positioned to left and right of a center start position target.

For monkey Ven, each trial is composed of a start position hold period of pseudo-random duration followed by appearance of a peripheral target to the left or right of the start position (direction chosen at random). Food reward was delivered at the end of a trial if the animal captured the displayed peripheral target with the cursor and then held the cursor within the target for a required target hold period.

Each data file contains data collected during stable recording from one (or occasionally two) single-units. The number of trials collected varies between files depending on stable unit isolation. The target to capture was indicated by the spatial location of the target.

The files from monkey Ven contain data from only one trial type:
- A 2-choice reaction time task in which flexion and extension targets are presented in random order.

Single units were tested for antidromic activation from the putamen (STRI), cerebral peduncle (PED), VL thalamus (THAL) or subthalamic nucleus (STN) via macroelectrodes were implanted chronically at those locations. See Meta-data below for details.

Recording sessions were performed before and after the induction of hemi-parkinsonism by intra-carotid infusion of MPTP.

## Variables

### Events
The primary events for each trial are stored in the `Events` structure. All times are in milliseconds relative to the beginning of each trial.

- `Events.home_cue_on` = time of start position appearance
- `Events.target_cue_on` = time of peripheral target appearance at end of start position hold period
- `Events.targ_dir` = direction of target (1==flexion, 2==extension)
- `Events.home_leave` = time of cursor exit from start position after appearance of peripheral target
- `Events.reward` = time of reward delivery at the end of the peripheral target hold period

Temporally-unpredictable proprioceptive perturbations were applied to the joint using a torque motor aligned with the axis of rotation of the involved joint. Perturbations were applied on randomly-selected subsets of trials.
- `Events.tq_flex` = time of onset of a torque perturbation that produced joint flexion
- `Events.tq_ext` = time of onset of a torque perturbation that produced joint extension

#### Reading Events Data
```python
from pymatreader import read_mat
import numpy as np

mat_file = read_mat("/home/heberto/data/turner/Ven_All/v1401.1.mat")
events = mat_file["Events"]

# Get trial timing events
home_cue_times = events["home_cue_on"]  # Start position appearance
target_cue_times = events["targ_cue_on"]  # Target appearance (note: targ_cue_on not target_cue_on)
target_directions = events["targ_dir"]  # 1=flexion, 2=extension
movement_starts = events["home_leave"]  # Movement onset
reward_times = events["reward"]  # Reward delivery

# Check for perturbation trials (not all trials have perturbations)
if "tq_flex" in events:
    flexion_perturbations = events["tq_flex"]
if "tq_ext" in events:
    extension_perturbations = events["tq_ext"]

print(f"Total trials: {len(target_directions)}")
print(f"Flexion trials: {sum(np.array(target_directions) == 1)}")
print(f"Extension trials: {sum(np.array(target_directions) == 2)}")
```

### Analog
`Analog` is an array of structures containing segments of analog data for each trial. Analog data were digitized at 500 Hz and interpolated to 1kHz (monkey Ven) or 200 Hz (monkey Leu). For trial number 'n':

- `Analog(n).x` = manipulandum angle
- `Analog(n).torq` = commands sent to torque controller (fs=1kHz)
- `Analog(n).emg` = EMG signals from 5 or 6 arm muscles via chronically-implanted EMG electrodes. Before A/D conversion, EMG signals were preprocessed (rectified and low-pass filtered)
- `Analog(n).vel` = angular velocity of manipulandum movement calculated from Analog.x
- `Analog(n).lfp` = low-pass filtered signal from microelectrode (10k gain, 1-100 Hz)

#### Reading Analog Data
```python
mat_file = read_mat("/home/heberto/data/turner/Ven_All/v1401.1.mat")
analog_data = mat_file["Analog"]

# Analog data structure: analog_data[signal_type][trial_index]
# Access data for specific trial (e.g., trial 0)
trial_idx = 0

# Extract analog signals for this trial
position = analog_data["x"][trial_idx]  # Joint angle (degrees or radians)
velocity = analog_data["vel"][trial_idx]  # Angular velocity
torque_cmd = analog_data["torq"][trial_idx]  # Torque motor commands

print(f"Position shape: {position.shape}")
print(f"Velocity shape: {velocity.shape}")
print(f"Torque shape: {torque_cmd.shape}")

# EMG and LFP may not be present in all files
if "emg" in analog_data:
    emg_signals = analog_data["emg"][trial_idx]  # Shape: (time_points, n_muscles)
    print(f"EMG shape: {emg_signals.shape}")

if "lfp" in analog_data:
    lfp_signal = analog_data["lfp"][trial_idx]  # Local field potential
    print(f"LFP shape: {lfp_signal.shape}")

print(f"Position data length: {len(position)} samples")
print(f"Sampling rate: 1kHz (monkey Ven) or 200Hz (monkey Leu)")
```

### Movement (Mvt)
`Mvt` contains trial-by-trial measures of motor performance extracted from analysis of `Analog.x` and `Analog.vel` signals. All times in milliseconds from beginning of the trial:

- `Mvt.onset_t` = time of onset of target capture movement
- `Mvt.end_t` = time of movement end
- `Mvt.pkvel` = peak velocity during target capture movement
- `Mvt.pkvel_t` = time of velocity peak
- `Mvt.end_posn` = angular position of joint at end of capture movement
- `Mvt.mvt_amp` = amplitude of target capture movement

#### Reading Movement Data
```python
mat_file = read_mat("/home/heberto/data/turner/Ven_All/v1401.1.mat")
movement_data = mat_file["Mvt"]

# Extract movement parameters for all trials
movement_onsets = movement_data["onset_t"]  # Movement start times (ms)
movement_ends = movement_data["end_t"]  # Movement end times (ms)
peak_velocities = movement_data["pkvel"]  # Peak velocity values
peak_vel_times = movement_data["pkvel_t"]  # Time of peak velocity (ms)
end_positions = movement_data["end_posn"]  # Final joint positions
movement_amplitudes = movement_data["mvt_amp"]  # Movement amplitudes

# Calculate movement durations
movement_durations = movement_ends - movement_onsets  # Duration in ms

print(f"Average movement duration: {np.mean(movement_durations):.1f} ms")
print(f"Average peak velocity: {np.mean(peak_velocities):.2f}")
print(f"Average movement amplitude: {np.mean(movement_amplitudes):.2f}")
```

### Unit Timestamps
`unit_ts` contains the times of single unit spikes in milliseconds relative to the beginning of a trial (trials x spike times). The matrix is padded by NaNs. Spike sorting was performed on-line during each recording session.

#### Reading Spike Data
```python
import numpy as np

mat_file = read_mat("/home/heberto/data/turner/Ven_All/v1401.1.mat")
spike_times = mat_file["unit_ts"]  # Shape: (n_trials, max_spikes_per_trial)

print(f"Spike data shape: {spike_times.shape}")
print(f"Number of trials: {spike_times.shape[0]}")

# Get spikes for a specific trial (e.g., trial 0)
trial_idx = 0
trial_spikes = spike_times[trial_idx, :]
# Remove NaN padding
valid_spikes = trial_spikes[~np.isnan(trial_spikes)]

print(f"Trial {trial_idx} has {len(valid_spikes)} spikes")
print(f"First few spike times: {valid_spikes[:5]} ms")

# Calculate firing rate for each trial
trial_firing_rates = []
for trial in range(spike_times.shape[0]):
    trial_spikes = spike_times[trial, :]
    valid_spikes = trial_spikes[~np.isnan(trial_spikes)]
    # Assume trial duration of ~2000ms (adjust based on actual trial length)
    firing_rate = len(valid_spikes) / 2.0  # spikes per second
    trial_firing_rates.append(firing_rate)

print(f"Average firing rate: {np.mean(trial_firing_rates):.1f} Hz")
```

### Stimulation Data

**Purpose**: Antidromic identification recordings for cell type classification

The stimulation data (`StrStim`, `PedStim`, `ThalStim`, `STNStim`) contains **antidromic identification recordings** - electrical stimulation applied to specific brain regions to identify neuron types by their axonal projections. This technique involves electrically stimulating target regions where neurons project their axons. If a recorded neuron has an axon terminating in the stimulated region, the electrical pulse travels backward (antidromically) up the axon to the cell body, causing it to fire with a characteristic short, fixed latency.

**Cell Types Identified**:
- **Pyramidal Tract Neurons (PTNs)**: Identified by antidromic activation from cerebral peduncle (`PedStim`)  
- **Corticostriatal Neurons (CSNs)**: Identified by antidromic activation from posterolateral striatum (`StrStim`)

**Data Structure**: 50-msec duration sweeps of raw single-unit data (fs=20 kHz) centered on stimulation times:

- `StrStim.TraceName` = description of test performed for each sweep. 'coll_n' = collision test. 'ff_n' = frequency following test. On occasion, sweeps were collected to document orthodromic activation from striatum or thalamus 'thal'
- `StrStim.Curr` = current delivered obtained by amplifying voltage drop across a resistor. (Calibration tbd)
- `StrStim.Unit` = raw single-unit signal
- `StrStim.Time` = timebase relative to time of shock delivery

**Usage Across Papers**: All three papers use this technique for cell classification. The stimulation data represents methodological validation rather than main experimental data, enabling cell-type specific analyses reported in all studies.

**Availability**: Stim data were collected for only a subset of recording sessions. Stim data were rarely collected if no effect of stimulation was observed on-line. If responses were evoked from >1 stimulation location, then >1 Stim data record is present. i.e., a few data files contain `StrStim` and `PedStim` variables.

#### Reading Stimulation Data
```python
mat_file = read_mat("/home/heberto/data/turner/Ven_All/v1401.1.mat")

# Check which stimulation data is available
stim_types = ["StrStim", "PedStim", "ThalStim", "STNStim"]
available_stim = [s for s in stim_types if s in mat_file.keys()]
print(f"Available stimulation data: {available_stim}")

# Example: Reading striatum stimulation data (if present)
if "StrStim" in mat_file:
    stim_data = mat_file["StrStim"]
    
    # Get stimulation parameters
    trace_names = stim_data["TraceName"]  # Test type descriptions
    currents = stim_data["Curr"]  # Stimulation currents
    unit_responses = stim_data["Unit"]  # Raw unit data (20kHz, 50ms sweeps)
    timebase = stim_data["Time"]  # Time relative to shock
    
    print(f"Number of stimulation sweeps: {len(trace_names)}")
    print(f"Sweep duration: 50ms at 20kHz = {unit_responses.shape[1]} samples")
    print(f"Current range: {np.min(currents):.1f} to {np.max(currents):.1f}")
    
    # Check test types
    unique_tests = np.unique(trace_names)
    print(f"Test types performed: {unique_tests}")
```

### File Information Structure

`file_info` contains session-level metadata and data acquisition parameters stored within each MATLAB file:

- `file_info.fname` = base filename (e.g., "v1401")
- `file_info.epoch` = experimental epoch identifier
- `file_info.unit_n` = unit number (1 or 2)
- `file_info.trial_n` = number of trials in this session
- `file_info.unit_fs` = spike data sampling rate (Hz)
- `file_info.analog_fs` = analog data sampling rate (Hz)

#### Reading File Information
```python
mat_file = read_mat("/home/heberto/data/turner/Ven_All/v1401.1.mat")
file_info = mat_file["file_info"]

print(f"Filename: {file_info['fname']}")
print(f"Experimental epoch: {file_info['epoch']}")
print(f"Unit number: {file_info['unit_n']}")
print(f"Number of trials: {file_info['trial_n']}")
print(f"Spike sampling rate: {file_info['unit_fs']} Hz")
print(f"Analog sampling rate: {file_info['analog_fs']} Hz")
```

**Important Note**: The `file_info.epoch` field consistently shows "pre-MPTP" across all tested files, including those that metadata indicates are Post-MPTP sessions. **Use the metadata table (`ven_table.csv`) MPTP column for accurate experimental condition classification**, not the file_info.epoch field.

**Sampling Rate Verification**: All tested files show consistent 1000Hz sampling rates for both spike and analog data, confirming the documentation's stated 1kHz rate for monkey Ven.

## Meta-data

Meta-data for each single unit studied is stored in the matlab table `AllTab` in `VenTable.mat`. Each row of the table contains information about an individual single-unit. If two single-units were isolated during a single recording session, then two adjacent rows are devoted to units 1 and 2.

#### Reading Meta-data

**Note**: The original `VenTable.mat` file contains a MATLAB table structure that cannot be read with standard Python libraries (`pymatreader` and `scipy.io` both fail). The file was converted to CSV format using MATLAB:

```matlab
% Convert MATLAB table to CSV
T = load("VenTable.mat");
myTable = T.AllTab;
writetable(myTable, "ven_table.csv");
```

**Reading the CSV metadata table**:

```python
import pandas as pd
import numpy as np

# Load the converted metadata table
metadata_df = pd.read_csv("/home/heberto/development/turner-lab-to-nwb/src/turner_lab_to_nwb/asap_m1_mptp/assets/metadata_table/ven_table.csv")

print(f"Total recording sessions: {len(metadata_df)}")
print(f"Available columns: {list(metadata_df.columns)}")

# Access specific metadata fields
filenames = metadata_df["FName1"]  # Primary filename for each unit
secondary_files = metadata_df["FName2"]  # Secondary filename (if recorded twice)
mptp_condition = metadata_df["MPTP"]  # Pre or Post MPTP treatment
depths = metadata_df["Depth"]  # Recording depth (mm below chamber zero)
antidromic_results = metadata_df["Antidrom"]  # Antidromic test results
latencies = metadata_df["Latency"]  # Antidromic latencies (ms)
thresholds = metadata_df["Threshold"]  # Current thresholds (μA)

# Spatial coordinates relative to chamber center
anterior_posterior = metadata_df["A_P"]  # A-P position (positive = anterior)
medial_lateral = metadata_df["M_L"]  # M-L position (positive = lateral)

# Data availability flags
emg_available = metadata_df["emg_collected"]  # Boolean: EMG data present
lfp_available = metadata_df["lfp_collected"]  # Boolean: LFP data present
stim_data_flags = metadata_df["StimData"]  # Stimulation data availability

# Trial counts for different sessions
ntrials_session1 = metadata_df["ntrials1_1"]  # Trials in primary session
ntrials_session2 = metadata_df["ntrials2_1"]  # Trials in secondary session (if any)

# Find units with specific characteristics
ptn_units = metadata_df[metadata_df['Antidrom'].str.contains('PED', na=False)]
csn_units = metadata_df[metadata_df['Antidrom'].str.contains('STRI', na=False)]

print(f"Pyramidal tract neurons (PTNs): {len(ptn_units)}")
print(f"Corticostriatal neurons (CSNs): {len(csn_units)}")

# Filter by experimental condition
pre_mptp_units = metadata_df[metadata_df['MPTP'] == 'Pre']
post_mptp_units = metadata_df[metadata_df['MPTP'] == 'Post']

print(f"Pre-MPTP sessions: {len(pre_mptp_units)}")
print(f"Post-MPTP sessions: {len(post_mptp_units)}")
```

### Metadata Table Columns

The CSV metadata table contains **24 columns** with comprehensive information about each recording session:

#### Basic Session Information
- **`Animal`**: Subject identifier (always "V" for monkey Ven)
- **`MPTP`**: Experimental condition - `Pre` (before MPTP) or `Post` (after MPTP treatment)
- **`DateCollected`**: Recording date (format: DD-MMM-YYYY)
- **`FName1`**: Primary data filename (e.g., "v1401" for v1401.1.mat)
- **`FName2`**: Secondary filename if unit was recorded in multiple sessions (often with 'b' suffix)

#### Recording Location & Depth
- **`Depth`**: Electrode depth in mm below chamber reference point (consistent zero across all recordings)
- **`A_P`**: Anterior-Posterior position relative to chamber center (mm, positive = anterior)
- **`M_L`**: Medial-Lateral position relative to chamber center (mm, positive = lateral)
- **`UnitNum1`**, **`UnitNum2`**: Unit number identifiers (1 or 2) for each isolated neuron

#### Antidromic Identification Results
- **`Antidrom`**: Cell type classification based on antidromic stimulation:
  - `PED`: Pyramidal tract neuron (activated from cerebral peduncle)
  - `STRI`: Corticostriatal neuron (activated from striatum/putamen)
  - `THAL`: Thalamic-projecting neuron (activated from VL thalamus)
  - `NR`: No response to stimulation
  - `NT`: Not tested
  - `PED/STRI`: Dual activation (rare cases)
- **`Latency`**: Antidromic response latency in milliseconds
- **`Threshold`**: Current threshold for antidromic activation in microamps
- **`LAT2`**, **`Thresh2`**: Secondary stimulation site parameters (if dual activation present)

#### Sensory Response Properties
- **`SENSORY`**: Body region responsive to somatosensory testing:
  - `hand`, `wrist`, `elbow`, `forearm`, `shoulder`: Joint/limb regions
  - `NR`: No response, `NT`: Not tested
- **`SENS_DETAIL`**: Detailed description of sensory responses (e.g., "finger ext", "active grip", "wrist flex")

#### Data Availability & Trial Counts
- **`ntrials1_1`**, **`ntrials1_2`**: Number of trials in primary recording session
- **`ntrials2_1`**, **`ntrials2_2`**: Number of trials in secondary session (if applicable)
- **`emg_collected`**: Boolean flag (1/0) indicating EMG data presence
- **`lfp_collected`**: Boolean flag (1/0) indicating LFP data presence
- **`StimData`**: Stimulation data availability:
  - `Ped`: Peduncle stimulation sweeps present
  - `Str`: Striatum stimulation sweeps present
  - `Ped/Str`: Both types present
  - Empty: No stimulation data

### Data File Naming Convention

**Format**: `v[Site][Session][Unit]` (e.g., v1401.1)
- **`v`**: Monkey Ven identifier
- **`14`**: Recording site #14 (penetration location in chamber)
- **`01`**: Session #1 at this site/depth
- **`.1`**: Data from unit #1 (some files have .2 for second unit)

**Secondary files** (e.g., v1401b.1): Same unit recorded again, typically with 'b' suffix indicating second recording session.

