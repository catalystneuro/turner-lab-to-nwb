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

### Analog
`Analog` is an array of structures containing segments of analog data for each trial. Analog data were digitized at 500 Hz and interpolated to 1kHz (monkey Ven) or 200 Hz (monkey Leu). For trial number 'n':

- `Analog(n).x` = manipulandum angle
- `Analog(n).torq` = commands sent to torque controller (fs=1kHz)
- `Analog(n).emg` = EMG signals from 5 or 6 arm muscles via chronically-implanted EMG electrodes. Before A/D conversion, EMG signals were preprocessed (rectified and low-pass filtered)
- `Analog(n).vel` = angular velocity of manipulandum movement calculated from Analog.x
- `Analog(n).lfp` = low-pass filtered signal from microelectrode (10k gain, 1-100 Hz)

### Movement (Mvt)
`Mvt` contains trial-by-trial measures of motor performance extracted from analysis of `Analog.x` and `Analog.vel` signals. All times in milliseconds from beginning of the trial:

- `Mvt.onset_t` = time of onset of target capture movement
- `Mvt.end_t` = time of movement end
- `Mvt.pkvel` = peak velocity during target capture movement
- `Mvt.pkvel_t` = time of velocity peak
- `Mvt.end_posn` = angular position of joint at end of capture movement
- `Mvt.mvt_amp` = amplitude of target capture movement

### Unit Timestamps
`unit_ts` contains the times of single unit spikes in milliseconds relative to the beginning of a trial (trials x spike times). The matrix is padded by NaNs. Spike sorting was performed on-line during each recording session.

### Stimulation Data
`StrStim`, `PedStim` etc. contain 50-msec duration sweeps of raw single-unit data (fs=20 kHz) centered on the times of single shock stimulations of striatum, peduncle, etc.:

- `StrStim.TraceName` = description of test performed for each sweep. 'coll_n' = collision test. 'ff_n' = frequency following test. On occasion, sweeps were collected to document orthodromic activation from striatum or thalamus 'thal'
- `StrStim.Curr` = current delivered obtained by amplifying voltage drop across a resistor. (Calibration tbd)
- `StrStim.Unit` = raw single-unit signal
- `StrStim.Time` = timebase relative to time of shock delivery

Stim data were collected for only a subset of recording sessions. Stim data were rarely collected if no effect of stimulation was observed on-line. If responses were evoked from >1 stimulation location, then >1 Stim data record is present. i.e., a few data files contain `StrStim` and `PedStim` variables.

## Meta-data

Meta-data for each single unit studied is stored in the matlab table `AllTab` in `VenTable.mat`. Each row of the table contains information about an individual single-unit. If two single-units were isolated during a single recording session, then two adjacent rows are devoted to units 1 and 2.

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
‘Events’ - The primary events for each trial are stored in the 'Events' structure. All times are in milliseconds relative to the beginning of each trial.
Events.home_cue_on = time of start position appearance
Events.target_cue_on = time of peripheral target appearance at end of start position hold period
Events.targ_dir = direction of target (1==flexion, 2==extension)
Events.home_leave = time of cursor exit from start position after appearance of peripheral target
Events.reward = time of reward delivery at the end of the peripheral target hold period

Temporally-unpredictable proprioceptive perturbations were applied to the joint using a torque motor aligned with the axis of rotation of the involved joint. Perturbations were applied on randomly-selected subsets of trials.
Events.tq_flex = time of onset of a torque perturbation that produced joint flexion.
Events.tq_ext = time of onset of a torque perturbation that produced joint extension.


‘Analog’ is an array of structures containing segments of analog data for each trial. Analog data were digitized at 500 Hz and interpolated to 1kHz (monkey Ven) or 200 Hz (monkey Leu). For trial number ‘n’:
Analog(n).x = manipulandum angle
Analog(n).torq = commands sent to torque controller (fs=1kHz)
Analog(n).emg = EMG signals from 5 or 6 arm muscles via chronically-implanted EMG electrodes. Before A/D conversion, EMG signals were preprocessed (rectified and low-pass filtered)
Analog(n).vel = angular velocity of manipulandum movement calculated from Analog.x
Analog(n).lfp = low-pass filtered signal from microelectrode (10k gain, 1-100 Hz).

‘Mvt’ contains trial-by-trial measures of motor performance extracted from analysis of Analog.x and Analog.vel signals. All times milliseconds from beginning of the trial
Mvt.onset_t = time of onset of target capture movement 
Mvt.end_t = time of movement end
Mvt.pkvel = peak velocity during target capture movement
Mvt.pkvel_t = time of velocity peak
Mvt.end_posn = angular position of joint at end of capture movement
Mvt.mvt_amp = amplitude of target capture movement

‘unit_ts’ contains the times of single unit spikes in milliseconds relative to the begining of a trial (trials x spike times). The matrix is padded by NaNs. Spike sorting was performed on-line during each recording session

‘StrStim’, ‘PedStim’ etc. contain 50-msec duration sweeps of raw single-unit data (fs=20 kHz) centered on the times of single shock stimulations of striatum, peduncle, etc. 
StrStim.TraceName = description of test performed for each sweep. ‘coll_n’ = collision test. ‘ff_n’ = frequency following test. On occasion, sweeps were collected to document orthodromic activation from striatum or thalamus ‘thal’
StrStim.Curr = current delivered obtained by amplifying voltage drop across a resistor. (Calibration tbd)
StrStim.Unit = raw single-unit signal
StrStim.Time = timebase relative to time of shock delivery.

Stim data were collected for only a subset of recording sessions. Stim data were rarely collected if no effect of stimulation was observed on-line. If responses were evoked from >1 stimulation location, then >1 Stim data record is present. i.e., a few data files contain ‘StrStim’ and ‘PedStim’ variables.

Meta-data
Meta-data for each single unit studied is stored in the matlab table 'AllTab' in VenTable.mat. Each row of the table contains information about an individual single-unit. If two single-units were isolated during a single recording session, then two adjacent rows are devoted to units 1 and 2.
Data file naming convention:
character 1: animal initial
characters 2-3: incremental count of recording chamber penetration sites. Individual chamber sites were often sampled from on >1 recording day.
characters 4-5: count of recording sessions at different penetration depths
character 6: (optional) if a second recording session was performed for the same unit at the same depth.
‘.1’ or ‘.2’: indicates whether a file contains data from unit 1 or unit 2.

Most columns are self-explanatory.

‘Fname2’: root name of file if a second recording session was collected from the same single-unit.

‘Depth’: distance (mm) of recording location below an arbitrary zero point. Zero point is consistent across all recordings in an animal.

‘A_P’ and ‘M_L’: x-y location of penetration relative to chamber center. Positive A_P = anterior. Positive M_L = lateral

‘Antidrom’: result from on-line test for antidromic activation from locations in putamen (STRI), cerebral peduncle (PED), VL thalamus (THAL)

‘Latency’: on-line estimate of antidromic latency (msec)
‘Threshold’: on-line estimate of current threshold (micro-amps).
‘LAT2’ and ‘Thresh2’: stimulation values for second source of activation if present. i.e., if unit was activated from both STRI and PED

‘SENSORY’ and ‘SENS_DETAIL’: categories and detailed results from somatosensory/proprioceptive exam performed typically after recording session. 

‘emg_collected’ and ‘lfp_collected’: flag to indicate if ‘Analog’ variable in data file contains emg and lfp data.

‘StimData’: flags to indicate if data file contains ‘StriStim’, ‘PedStim’ etc. data.

