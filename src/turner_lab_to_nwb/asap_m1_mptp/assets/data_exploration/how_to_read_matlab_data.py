from pathlib import Path
from pymatreader import read_mat
import numpy as np

def explore_matlab_data(file_path):
    """
    Comprehensive exploration of Turner-Delong MPTP dataset MATLAB files.
    
    This function reads and analyzes single-unit neuronal data collected from 
    parkinsonian macaque monkeys during flexion/extension motor tasks.
    """
    print(f"\n=== Analyzing file: {file_path.name} ===")
    
    mat_file = read_mat(file_path)
    
    # Filter out MATLAB metadata
    keys_to_avoid = ["__header__", "__version__", "__globals__"]
    all_keys = mat_file.keys()
    filtered_keys = [key for key in all_keys if key not in keys_to_avoid]
    
    print(f"\nData structures found: {filtered_keys}")
    
    # Events structure - trial timing and task parameters
    if "Events" in mat_file:
        print("\n--- EVENTS STRUCTURE ---")
        print("Contains trial timing and task event markers (times in ms from trial start):")
        events = mat_file["Events"]
        for field in events.keys():
            data = events[field]
            if hasattr(data, 'shape'):
                print(f"  {field}: {data.shape} - {get_event_description(field)}")
            else:
                print(f"  {field}: {type(data)} - {get_event_description(field)}")
    
    # Analog data - continuous signals sampled at 500Hz-1kHz
    if "Analog" in mat_file:
        print("\n--- ANALOG STRUCTURE ---")
        print("Array of trial-by-trial continuous data (500Hz-1kHz sampling):")
        analog = mat_file["Analog"]
        print(f"  Number of trials: {len(analog) if isinstance(analog, list) else 'Single trial'}")
        
        if isinstance(analog, list) and len(analog) > 0:
            sample_trial = analog[0] if isinstance(analog[0], dict) else analog
            for field in sample_trial.keys():
                data = sample_trial[field]
                if hasattr(data, 'shape'):
                    print(f"  {field}: {data.shape} - {get_analog_description(field)}")
        elif isinstance(analog, dict):
            for field in analog.keys():
                data = analog[field]
                if hasattr(data, 'shape'):
                    print(f"  {field}: shape varies by trial - {get_analog_description(field)}")
    
    # Movement parameters - extracted kinematic measures
    if "Mvt" in mat_file:
        print("\n--- MOVEMENT STRUCTURE ---")
        print("Trial-by-trial motor performance measures extracted from analog signals:")
        mvt = mat_file["Mvt"]
        for field in mvt.keys():
            data = mvt[field]
            if hasattr(data, 'shape'):
                print(f"  {field}: {data.shape} - {get_movement_description(field)}")
    
    # Unit timestamps - spike timing data
    if "unit_ts" in mat_file:
        print("\n--- SPIKE TIMESTAMPS ---")
        unit_ts = mat_file["unit_ts"]
        print(f"  unit_ts: {unit_ts.shape} - Spike times in ms from trial start")
        print(f"           Matrix padded with NaNs, each row = trial, columns = spike times")
        print(f"           Online spike sorting performed during recording")
        
        # Count non-NaN spikes
        non_nan_spikes = np.sum(~np.isnan(unit_ts))
        total_trials = unit_ts.shape[0]
        print(f"           Total spikes: {non_nan_spikes} across {total_trials} trials")
    
    # Stimulation data - antidromic identification sweeps
    stim_types = ["StrStim", "PedStim", "ThalStim", "STNStim"]
    found_stim = False
    for stim_type in stim_types:
        if stim_type in mat_file:
            if not found_stim:
                print("\n--- STIMULATION DATA ---")
                print("50ms sweeps (20kHz) for antidromic activation testing:")
                found_stim = True
            
            stim_data = mat_file[stim_type]
            location = get_stim_location(stim_type)
            print(f"  {stim_type}: {location} stimulation data")
            
            if isinstance(stim_data, dict):
                for field in stim_data.keys():
                    data = stim_data[field]
                    if hasattr(data, 'shape'):
                        print(f"    {field}: {data.shape} - {get_stim_description(field)}")
    
    if not found_stim:
        print("\n--- STIMULATION DATA ---")
        print("  No stimulation data found in this file")
        print("  (Stim data collected only when antidromic responses observed)")

def get_event_description(field):
    """Return description for Events structure fields"""
    descriptions = {
        'home_cue_on': 'Start position target appearance',
        'target_cue_on': 'Peripheral target appearance (end of hold period)',
        'targ_dir': 'Target direction (1=flexion, 2=extension)',
        'home_leave': 'Cursor exit from start position',
        'reward': 'Reward delivery time',
        'tq_flex': 'Flexion torque perturbation onset',
        'tq_ext': 'Extension torque perturbation onset'
    }
    return descriptions.get(field, 'Event timing marker')

def get_analog_description(field):
    """Return description for Analog structure fields"""
    descriptions = {
        'x': 'Manipulandum angle position',
        'torq': 'Torque motor commands (1kHz)',
        'emg': 'EMG from 5-6 arm muscles (rectified, filtered)',
        'vel': 'Angular velocity (calculated from position)',
        'lfp': 'Local field potential (1-100Hz, 10k gain)'
    }
    return descriptions.get(field, 'Analog signal')

def get_movement_description(field):
    """Return description for Movement structure fields"""
    descriptions = {
        'onset_t': 'Movement onset time',
        'end_t': 'Movement end time',
        'pkvel': 'Peak velocity during movement',
        'pkvel_t': 'Time of velocity peak',
        'end_posn': 'Final joint position',
        'mvt_amp': 'Movement amplitude'
    }
    return descriptions.get(field, 'Movement parameter')

def get_stim_description(field):
    """Return description for stimulation data fields"""
    descriptions = {
        'TraceName': 'Test type (coll_n=collision, ff_n=frequency following)',
        'Curr': 'Stimulation current delivered',
        'Unit': 'Raw single-unit signal (20kHz)',
        'Time': 'Timebase relative to shock delivery'
    }
    return descriptions.get(field, 'Stimulation parameter')

def get_stim_location(stim_type):
    """Return anatomical location for stimulation type"""
    locations = {
        'StrStim': 'Striatum/Putamen',
        'PedStim': 'Cerebral Peduncle', 
        'ThalStim': 'VL Thalamus',
        'STNStim': 'Subthalamic Nucleus'
    }
    return locations.get(stim_type, 'Unknown location')

# Main analysis
if __name__ == "__main__":
    print("=== TURNER-DELONG MPTP DATASET EXPLORATION ===")
    print("Single-unit recordings from parkinsonian macaque M1 during motor tasks")
    print("Data collected before/after MPTP-induced hemi-parkinsonism")
    
    folder_path = Path("/home/heberto/data/turner/Ven_All")
    assert folder_path.exists(), f"Data folder not found: {folder_path}"
    
    # Analyze example file
    file_path = folder_path / "v1401.1.mat"
    assert file_path.exists(), f"Example file not found: {file_path}"
    
    explore_matlab_data(file_path)
    
    # Show file naming convention
    print("\n=== FILE NAMING CONVENTION ===")
    print("Format: [Animal][Site][Session][Unit]")
    print("v1401.1 breakdown:")
    print("  v = Monkey Ven")
    print("  14 = Recording chamber penetration site #14") 
    print("  01 = Session #1 at this penetration depth")
    print("  .1 = Data from unit #1")
    
    print(f"\nTotal .mat files in directory: {len(list(folder_path.glob('*.mat')))}")
    print("Each file contains one recording session from 1-2 isolated units")
    
    print("\n=== EXPERIMENTAL CONTEXT ===")
    print("Task: 2-choice flexion/extension reaction time task")
    print("Setup: Arm in manipulandum, elbow/wrist joint aligned with torque motor")
    print("Targets: Left/right peripheral targets from center start position")
    print("Perturbations: Random torque perturbations on subset of trials")
    print("Recording: Single-unit activity + analog signals (position, EMG, LFP)")
    print("Stimulation: Antidromic testing from putamen, peduncle, thalamus, STN")
