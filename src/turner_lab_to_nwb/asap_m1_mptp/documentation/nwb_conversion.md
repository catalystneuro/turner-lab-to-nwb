# NWB Conversion Strategy for Turner Lab ASAP M1 MPTP Dataset

## Overview

This document outlines how each data stream from the Turner-Delong MPTP dataset should be mapped to appropriate NWB (Neurodata Without Borders) data structures. The conversion preserves the scientific integrity of the original data while making it accessible through standardized interfaces.

**Related documentation:**
- [File Structure](../assets/data_exploration/file_structure.md) - Source MATLAB data format
- [Trial Structure](trial_structure.md) - Trial timing and boundaries
- [Anatomical Coordinates](anatomical_coordinates.md) - Electrode positioning
- [Stimulation Events](stimulation_events.md) - In-trial stimulation handling
- [Sensory Receptive Field Testing](sensory_receptive_field_testing.md) - Unit characterization

## Data Stream Mapping to NWB

### 1. Extracellular Electrophysiology

#### **Spike Times** (`unit_ts` -> NWB)
**Source**: `unit_ts` matrix (n_trials, max_spikes_per_trial), NaN-padded
**Target NWB Structure**: `Units` table
```python
# Store in NWB Units table
nwbfile.add_unit_column('spike_times', 'spike times for each unit')
nwbfile.add_unit_column('cell_type', 'cell type classification (PTN/CSN/Unidentified)')
nwbfile.add_unit_column('antidromic_response', 'antidromic identification result')
nwbfile.add_unit_column('recording_location', 'electrode coordinates (A-P, M-L, depth)')

# For each unit:
nwbfile.add_unit(
    spike_times=concatenated_spike_times,  # All trials concatenated with trial offsets
    cell_type='PTN',  # From metadata Antidrom field
    antidromic_response='PED',
    recording_location=[A_P, M_L, depth]
)
```
**Key Considerations**:
- Concatenate trial-based spike times into continuous timeline
- Apply trial start time offsets to maintain temporal relationships
- Store cell type classification from metadata `Antidrom` column
- Include electrode location from metadata A_P, M_L, Depth fields

#### **Antidromic Stimulation Traces** (`StrStim`/`PedStim` -> NWB)
**Purpose**: Cell type identification through antidromic activation
**Source**: Stimulation sweep structures (50ms, 20kHz) for PTN/CSN classification
**Target NWB Structure**: `ProcessingModule` for methodological validation data
```python
# Create processing module for antidromic stimulation identification data
stim_module = ProcessingModule(
    'antidromic_stimulation', 
    'Cell type identification through antidromic activation - PTNs via PedStim, CSNs via StrStim'
)

# Store each stimulation type with identification purpose
for stim_type in ['StrStim', 'PedStim', 'ThalStim', 'STNStim']:
    if stim_type in matlab_data:
        stim_data = matlab_data[stim_type]
        
        # Map stimulation type to cell type
        cell_type_mapping = {
            'PedStim': 'Pyramidal Tract Neurons (PTNs)',
            'StrStim': 'Corticostriatal Neurons (CSNs)', 
            'ThalStim': 'Thalamic response validation',
            'STNStim': 'Subthalamic response validation'
        }
        
        # Create TimeSeries for raw traces
        stim_traces = TimeSeries(
            name=f'{stim_type.lower()}_traces',
            data=stim_data['Unit'],  # Raw unit responses (20kHz, 50ms)
            timestamps=stim_data['Time'],  # Time relative to shock
            unit='volts',
            description=f'{stim_type} antidromic stimulation for {cell_type_mapping.get(stim_type, "identification")}'
        )
        
        # Store stimulation parameters and test protocols
        stim_currents = TimeSeries(
            name=f'{stim_type.lower()}_currents',
            data=stim_data['Curr'],
            unit='microamps',
            description=f'Stimulation currents for {stim_type}'
        )
        
        # Store test protocol information
        test_protocols = DynamicTable(
            name=f'{stim_type.lower()}_protocols',
            description=f'Test protocols used for {stim_type} identification',
            columns=[
                VectorData('trace_name', 'Test type (coll_n=collision, ff_n=frequency following)', data=stim_data['TraceName']),
                VectorData('current', 'Stimulation current (μA)', data=stim_data['Curr'])
            ]
        )
        
        stim_module.add(stim_traces)
        stim_module.add(stim_currents)
        stim_module.add(test_protocols)

nwbfile.add_processing_module(stim_module)
```

### 2. Behavioral Task Events

#### **Trial Structure and Timing** (`Events` → NWB)
**Source**: `Events` structure with trial timing
**Target NWB Structure**: `Trials` table + `TimeIntervals`

**TERMINOLOGY CHOICES:**
- `center_target_appearance_time`: Discrete visual event (not "onset") when monkey aligns cursor
- `lateral_target_appearance_time`: Matches experimental papers; signals movement direction  
- `subject_movement_onset_time`: Purposefully emphasizes subject's behavioral action vs. experimental setup events; distinguishes animal behavior from apparatus/stimuli
- `torque_perturbation_*`: Scientific precision for stimulus parameters (0.1 Nm, 50ms)
- `derived_*`: Movement parameters from kinematic analysis post-processing
- **"onset" vs "appearance"**: "Onset" for events that initiate ongoing states (subject movement); "appearance" for punctual visual stimuli
- Full names: "flexion"/"extension" not abbreviated forms

```python
# Create trials table - UPDATED TERMINOLOGY
nwbfile.add_trial_column('movement_type', 'flexion or extension')
nwbfile.add_trial_column('center_target_appearance_time', 'time when center target appeared for monkey to align cursor and initiate trial (seconds)')
nwbfile.add_trial_column('lateral_target_appearance_time', 'time when lateral target appeared signaling monkey to move from center to flexion/extension position (seconds)')
nwbfile.add_trial_column('subject_movement_onset_time', 'time when monkey began moving from center position toward lateral target (seconds)')
nwbfile.add_trial_column('reward_time', 'reward delivery time relative to trial start (seconds)')
nwbfile.add_trial_column('torque_perturbation_type', 'direction of torque perturbation causing muscle stretch (flexion/extension/none)')
nwbfile.add_trial_column('torque_perturbation_onset_time', 'onset time of unpredictable torque impulse (0.1 Nm, 50ms) applied to manipulandum 1-2s after center target capture (seconds)')

# Derived movement parameters from kinematic analysis
nwbfile.add_trial_column('derived_movement_onset_time', 'onset time of target capture movement derived from kinematic analysis (seconds)')
nwbfile.add_trial_column('derived_movement_end_time', 'end time of target capture movement derived from kinematic analysis (seconds)')
nwbfile.add_trial_column('derived_peak_velocity', 'peak velocity during target capture movement derived from kinematic analysis')
nwbfile.add_trial_column('derived_peak_velocity_time', 'time of peak velocity during target capture movement derived from kinematic analysis (seconds)')
nwbfile.add_trial_column('derived_movement_amplitude', 'amplitude of target capture movement derived from kinematic analysis')
nwbfile.add_trial_column('derived_end_position', 'angular joint position at end of target capture movement (degrees)')
```

### 3. Analog Kinematics

#### **Joint Position and Velocity** (`Analog.x`, `Analog.vel` → NWB)
**Source**: Trial-based analog signals (1kHz sampling)
**Target NWB Structure**: `BehavioralTimeSeries`
```python
from pynwb.behavior import BehavioralTimeSeries

# Concatenate all trials with appropriate timestamps
position_data = []
velocity_data = []
timestamps = []

for trial_idx in range(n_trials):
    trial_start = trial_start_times[trial_idx]
    trial_position = analog_data['x'][trial_idx]
    trial_velocity = analog_data['vel'][trial_idx]
    trial_timestamps = trial_start + np.arange(len(trial_position)) / 1000  # 1kHz → seconds
    
    position_data.extend(trial_position)
    velocity_data.extend(trial_velocity) 
    timestamps.extend(trial_timestamps)

# Create behavioral time series
position_ts = TimeSeries(
    name='elbow_position',
    data=position_data,
    timestamps=timestamps,
    unit='degrees',
    description='Elbow joint angular position during reaching task'
)

velocity_ts = TimeSeries(
    name='elbow_velocity', 
    data=velocity_data,
    timestamps=timestamps,
    unit='degrees/second',
    description='Elbow joint angular velocity'
)

# Store in behavioral module
behavioral_module = BehavioralTimeSeries()
behavioral_module.add_timeseries(position_ts)
behavioral_module.add_timeseries(velocity_ts)
nwbfile.add_acquisition(behavioral_module)
```

#### **Movement Parameters** (`Mvt` → NWB)
**Source**: Extracted movement kinematics per trial
**Target NWB Structure**: Additional trial columns
```python
# Add movement parameter columns to trials table
nwbfile.add_trial_column('movement_onset_time', 'extracted movement onset (ms)')
nwbfile.add_trial_column('movement_end_time', 'extracted movement end (ms)')  
nwbfile.add_trial_column('peak_velocity', 'peak velocity during movement')
nwbfile.add_trial_column('peak_velocity_time', 'time of peak velocity')
nwbfile.add_trial_column('movement_amplitude', 'movement amplitude')
nwbfile.add_trial_column('end_position', 'final joint position')

# Include in trial data (as shown above in trial creation loop)
```

### 4. LFP Signals

#### **Local Field Potentials** (`Analog.lfp` → NWB)
**Source**: Trial-based LFP (1-100Hz, 10k gain)
**Target NWB Structure**: `LFP` in acquisition or processing
```python
from pynwb.ecephys import LFP, ElectricalSeries

# Only process files with LFP data
if 'lfp' in analog_data:
    # Concatenate LFP across trials
    lfp_data = []
    timestamps = []
    
    for trial_idx in range(n_trials):
        trial_start = trial_start_times[trial_idx] 
        trial_lfp = analog_data['lfp'][trial_idx]
        trial_timestamps = trial_start + np.arange(len(trial_lfp)) / 1000
        
        lfp_data.extend(trial_lfp)
        timestamps.extend(trial_timestamps)
    
    # Create electrical series
    lfp_electrical_series = ElectricalSeries(
        name='lfp',
        data=lfp_data,
        timestamps=timestamps,
        electrodes=electrode_table_region,  # Reference to electrode
        unit='volts',
        description='Local field potential (1-100Hz, 10k gain)'
    )
    
    # Create LFP container
    lfp = LFP(electrical_series=lfp_electrical_series)
    nwbfile.add_acquisition(lfp)
```

### 5. EMG Signals

#### **Electromyography** (`Analog.emg` → NWB)
**Source**: Multi-muscle EMG (5-6 muscles, rectified & filtered)
**Target NWB Structure**: Custom `TimeSeries` in acquisition
```python
# Only process files with EMG data  
if 'emg' in analog_data:
    # Get muscle count from first trial
    n_muscles = analog_data['emg'][0].shape[1]
    
    # Concatenate EMG across trials
    emg_data = []
    timestamps = []
    
    for trial_idx in range(n_trials):
        trial_start = trial_start_times[trial_idx]
        trial_emg = analog_data['emg'][trial_idx]  # Shape: (time_points, n_muscles)
        trial_timestamps = trial_start + np.arange(trial_emg.shape[0]) / 1000
        
        emg_data.append(trial_emg)
        timestamps.extend(trial_timestamps)
    
    # Stack EMG data
    emg_array = np.vstack(emg_data)  # Shape: (total_time_points, n_muscles)
    
    # Create TimeSeries for EMG
    emg_timeseries = TimeSeries(
        name='emg',
        data=emg_array,
        timestamps=timestamps,
        unit='volts',
        description=f'EMG from {n_muscles} arm muscles (rectified and low-pass filtered)',
        comments='Muscles recorded from chronically implanted electrodes'
    )
    
    nwbfile.add_acquisition(emg_timeseries)
```

## Metadata Integration

### Subject and Session Information
```python
# Extract from metadata table
subject_info = Subject(
    subject_id='Ven',
    species='Macaca mulatta',
    description='Macaque monkey with MPTP-induced hemiparkinsonism'
)

# Session-level metadata 
nwbfile = NWBFile(
    session_description='Single-unit recording during flexion/extension motor task',
    identifier=filename,  # e.g., 'v1401.1'
    session_start_time=recording_date,
    subject=subject_info,
    experimenter=['Turner', 'DeLong'],
    institution='Emory University',
    lab='Turner Lab'
)

# Add experimental condition
nwbfile.add_session_notes(f'MPTP condition: {mptp_condition}')  # Pre or Post
```

### Electrode and Recording Site Information
```python
# Create electrode table
electrode_group = nwbfile.create_electrode_group(
    name='tetrode',
    description='Single microelectrode',
    location=f'M1, A-P: {metadata_ap}mm, M-L: {metadata_ml}mm',
    device=device
)

nwbfile.add_electrode(
    location=f'M1 depth {depth}mm',
    group=electrode_group,
    x=metadata_ml,
    y=metadata_ap, 
    z=depth
)
```

## Processing Modules and Analysis

### Cell Type Classification
```python
# Add processing module for cell classification
classification_module = ProcessingModule(
    'cell_classification', 
    'Antidromic identification and cell type classification'
)

# Store classification results
cell_types = CategoricalTimeSeries(
    name='cell_types',
    data=[cell_type],  # PTN, CSN, or Unidentified
    timestamps=[0.0],
    description='Cell type based on antidromic stimulation',
    categories=['PTN', 'CSN', 'Unidentified']
)

classification_module.add(cell_types)
nwbfile.add_processing_module(classification_module)
```

## Key Implementation Notes

1. **Time Alignment**: All timestamps converted from milliseconds to seconds for NWB compliance
2. **Trial Concatenation**: Trial-based data concatenated with proper time offsets
3. **Metadata Preservation**: Rich metadata from CSV table integrated throughout NWB structure
4. **Optional Data Handling**: Check availability flags before processing LFP/EMG data
5. **Cell Type Integration**: Antidromic classification results embedded in Units table
6. **Spatial Information**: Electrode coordinates and recording depths preserved
7. **Experimental Context**: MPTP condition and session information clearly documented

This conversion strategy maintains the full scientific value of the original dataset while providing standardized access through NWB interfaces.