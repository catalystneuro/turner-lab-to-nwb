# Primary Motor Cortex in Parkinsonian Macaques: Turner-Delong Dataset

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

mat_file = read_mat("v1401.1.mat")
events = mat_file["Events"]

# Get trial timing events
home_cue_times = events["home_cue_on"]  # Start position appearance
target_cue_times = events["target_cue_on"]  # Target appearance
target_directions = events["targ_dir"]  # 1=flexion, 2=extension
movement_starts = events["home_leave"]  # Movement onset
reward_times = events["reward"]  # Reward delivery

# Check for perturbation trials (not all trials have perturbations)
if "tq_flex" in events:
    flexion_perturbations = events["tq_flex"]
if "tq_ext" in events:
    extension_perturbations = events["tq_ext"]

print(f"Total trials: {len(target_directions)}")
print(f"Flexion trials: {sum(target_directions == 1)}")
print(f"Extension trials: {sum(target_directions == 2)}")
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
mat_file = read_mat("v1401.1.mat")
analog_data = mat_file["Analog"]

# Access data for specific trial (e.g., trial 0)
trial_idx = 0
if isinstance(analog_data, list):
    trial_data = analog_data[trial_idx]
else:
    # If single trial structure
    trial_data = analog_data

# Extract analog signals for this trial
position = trial_data["x"]  # Joint angle (degrees or radians)
velocity = trial_data["vel"]  # Angular velocity
torque_cmd = trial_data["torq"]  # Torque motor commands

# EMG and LFP may not be present in all files
if "emg" in trial_data:
    emg_signals = trial_data["emg"]  # Shape: (time_points, n_muscles)
    print(f"EMG shape: {emg_signals.shape}")

if "lfp" in trial_data:
    lfp_signal = trial_data["lfp"]  # Local field potential
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
mat_file = read_mat("v1401.1.mat")
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

mat_file = read_mat("v1401.1.mat")
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
`StrStim`, `PedStim` etc. contain 50-msec duration sweeps of raw single-unit data (fs=20 kHz) centered on the times of single shock stimulations of striatum, peduncle, etc.:

- `StrStim.TraceName` = description of test performed for each sweep. 'coll_n' = collision test. 'ff_n' = frequency following test. On occasion, sweeps were collected to document orthodromic activation from striatum or thalamus 'thal'
- `StrStim.Curr` = current delivered obtained by amplifying voltage drop across a resistor. (Calibration tbd)
- `StrStim.Unit` = raw single-unit signal
- `StrStim.Time` = timebase relative to time of shock delivery

Stim data were collected for only a subset of recording sessions. Stim data were rarely collected if no effect of stimulation was observed on-line. If responses were evoked from >1 stimulation location, then >1 Stim data record is present. i.e., a few data files contain `StrStim` and `PedStim` variables.

#### Reading Stimulation Data
```python
mat_file = read_mat("v1401.1.mat")

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

## Meta-data

Meta-data for each single unit studied is stored in the matlab table `AllTab` in `VenTable.mat`. Each row of the table contains information about an individual single-unit. If two single-units were isolated during a single recording session, then two adjacent rows are devoted to units 1 and 2.

#### Reading Meta-data
```python
# Load the metadata table
metadata_file = read_mat("VenTable.mat")
all_table = metadata_file["AllTab"]

print(f"Total number of recorded units: {len(all_table)}")
print(f"Available metadata columns: {list(all_table.keys())}")

# Access specific metadata fields
filenames = all_table["Fname"]  # Primary filename for each unit
depths = all_table["Depth"]  # Recording depth (mm)
antidromic_results = all_table["Antidrom"]  # Antidromic test results
latencies = all_table["Latency"]  # Antidromic latencies (ms)
thresholds = all_table["Threshold"]  # Current thresholds (μA)

# Spatial coordinates relative to chamber center
anterior_posterior = all_table["A_P"]  # A-P position (positive = anterior)
medial_lateral = all_table["M_L"]  # M-L position (positive = lateral)

# Data availability flags
emg_available = all_table["emg_collected"]  # Boolean: EMG data present
lfp_available = all_table["lfp_collected"]  # Boolean: LFP data present
stim_data_flags = all_table["StimData"]  # Stimulation data availability

# Example: Find units with specific characteristics
ptn_units = [i for i, result in enumerate(antidromic_results) 
             if 'PED' in str(result)]  # Pyramidal tract neurons
csn_units = [i for i, result in enumerate(antidromic_results) 
             if 'STRI' in str(result)]  # Corticostriatal neurons

print(f"Pyramidal tract neurons (PTNs): {len(ptn_units)}")
print(f"Corticostriatal neurons (CSNs): {len(csn_units)}")
```

### Data File Naming Convention
- **Character 1**: animal initial
- **Characters 2-3**: incremental count of recording chamber penetration sites. Individual chamber sites were often sampled from on >1 recording day
- **Characters 4-5**: count of recording sessions at different penetration depths
- **Character 6**: (optional) if a second recording session was performed for the same unit at the same depth
- **'.1' or '.2'**: indicates whether a file contains data from unit 1 or unit 2

Most columns are self-explanatory.

### Key Meta-data Fields

- `Fname2`: root name of file if a second recording session was collected from the same single-unit
- `Depth`: distance (mm) of recording location below an arbitrary zero point. Zero point is consistent across all recordings in an animal
- `A_P` and `M_L`: x-y location of penetration relative to chamber center. Positive A_P = anterior. Positive M_L = lateral
- `Antidrom`: result from on-line test for antidromic activation from locations in putamen (STRI), cerebral peduncle (PED), VL thalamus (THAL)
- `Latency`: on-line estimate of antidromic latency (msec)
- `Threshold`: on-line estimate of current threshold (micro-amps)
- `LAT2` and `Thresh2`: stimulation values for second source of activation if present. i.e., if unit was activated from both STRI and PED
- `SENSORY` and `SENS_DETAIL`: categories and detailed results from somatosensory/proprioceptive exam performed typically after recording session
- `emg_collected` and `lfp_collected`: flag to indicate if `Analog` variable in data file contains emg and lfp data
- `StimData`: flags to indicate if data file contains `StriStim`, `PedStim` etc. dataVariables

