#!/usr/bin/env python3
"""
Analyze timing structure of MATLAB files and generate markdown summary.
"""

import numpy as np
from pymatreader import read_mat
from pathlib import Path
import sys
from datetime import datetime

def analyze_single_file(file_path):
    """Analyze timing elements in a single MATLAB file"""
    mat_data = read_mat(str(file_path))
    events = mat_data["Events"]
    movement_data = mat_data["Mvt"]
    analog = mat_data["Analog"]
    unit_ts = mat_data["unit_ts"]
    
    n_trials = len(events["targ_dir"])
    
    # Collect timing data
    timing_data = {
        'filename': file_path.name,
        'n_trials': n_trials,
        'events': {},
        'movement': {},
        'perturbations': {},
        'analog_durations': [],
        'spike_info': {}
    }
    
    # Event timing analysis
    event_fields = ["home_cue_on", "targ_cue_on", "home_leave", "reward"]
    for field in event_fields:
        if field in events:
            times = np.array(events[field])
            timing_data['events'][field] = {
                'min': times.min(),
                'max': times.max(),
                'mean': times.mean(),
                'std': times.std()
            }
    
    # Movement parameter timing
    mvt_time_fields = ["onset_t", "end_t", "pkvel_t"]
    mvt_scalar_fields = ["pkvel", "mvt_amp", "end_posn"]
    
    for field in mvt_time_fields:
        if field in movement_data:
            times = np.array(movement_data[field])
            valid_times = times[~np.isnan(times)]
            if len(valid_times) > 0:
                timing_data['movement'][field] = {
                    'min': valid_times.min(),
                    'max': valid_times.max(),
                    'mean': valid_times.mean(),
                    'std': valid_times.std(),
                    'n_valid': len(valid_times)
                }
    
    for field in mvt_scalar_fields:
        if field in movement_data:
            values = np.array(movement_data[field])
            valid_values = values[~np.isnan(values)]
            if len(valid_values) > 0:
                timing_data['movement'][field] = {
                    'min': valid_values.min(),
                    'max': valid_values.max(),
                    'mean': valid_values.mean(),
                    'std': valid_values.std(),
                    'n_valid': len(valid_values)
                }
    
    # Perturbation timing
    perturbation_fields = ["tq_flex", "tq_ext"]
    for field in perturbation_fields:
        if field in events:
            times = np.array(events[field])
            valid_times = times[~np.isnan(times)]
            if len(valid_times) > 0:
                timing_data['perturbations'][field] = {
                    'min': valid_times.min(),
                    'max': valid_times.max(),
                    'mean': valid_times.mean(),
                    'std': valid_times.std(),
                    'n_trials': len(valid_times),
                    'pct_trials': len(valid_times) / n_trials * 100
                }
    
    # Analog data durations
    for trial_idx in range(n_trials):
        trial_duration = len(analog["x"][trial_idx])
        timing_data['analog_durations'].append(trial_duration)
    
    timing_data['analog_durations'] = np.array(timing_data['analog_durations'])
    
    # Spike timing
    timing_data['spike_info']['shape'] = unit_ts.shape
    timing_data['spike_info']['format'] = '2D' if unit_ts.ndim == 2 else '1D'
    
    if unit_ts.ndim == 2:
        all_spikes = []
        for trial_idx in range(min(n_trials, 10)):
            trial_spikes = unit_ts[trial_idx, :]
            valid_spikes = trial_spikes[~np.isnan(trial_spikes)]
            all_spikes.extend(valid_spikes)
        
        if all_spikes:
            all_spikes = np.array(all_spikes)
            timing_data['spike_info']['min'] = all_spikes.min()
            timing_data['spike_info']['max'] = all_spikes.max()
            timing_data['spike_info']['n_spikes'] = len(all_spikes)
    
    elif unit_ts.ndim == 1:
        valid_spikes = unit_ts[~np.isnan(unit_ts)]
        if len(valid_spikes) > 0:
            timing_data['spike_info']['min'] = valid_spikes.min()
            timing_data['spike_info']['max'] = valid_spikes.max()
            timing_data['spike_info']['n_spikes'] = len(valid_spikes)
    
    return timing_data

def compile_across_files(file_data_list):
    """Compile timing data across multiple files"""
    compiled = {
        'files_analyzed': [data['filename'] for data in file_data_list],
        'total_trials': sum(data['n_trials'] for data in file_data_list),
        'events_compiled': {},
        'movement_compiled': {},
        'perturbations_compiled': {},
        'analog_compiled': {},
        'spike_compiled': {}
    }
    
    # Compile event data
    event_fields = ["home_cue_on", "targ_cue_on", "home_leave", "reward"]
    event_names = {
        "home_cue_on": "Home Cue",
        "targ_cue_on": "Target Cue", 
        "home_leave": "Movement Onset",
        "reward": "Reward Delivery"
    }
    
    for field in event_fields:
        all_values = []
        for data in file_data_list:
            if field in data['events']:
                # Collect individual event times, not just min/max
                mat_data = read_mat(f"/home/heberto/data/turner/Ven_All/{data['filename']}")
                times = np.array(mat_data["Events"][field])
                # Filter out NaN values
                valid_times = times[~np.isnan(times)]
                all_values.extend(valid_times)
        
        if all_values:
            all_values = np.array(all_values)
            compiled['events_compiled'][field] = {
                'name': event_names[field],
                'min': all_values.min(),
                'max': all_values.max(),
                'mean': all_values.mean(),
                'std': all_values.std(),
                'n_events': len(all_values)
            }
    
    # Compile movement data
    mvt_fields = ["onset_t", "end_t", "pkvel_t", "pkvel", "mvt_amp", "end_posn"]
    mvt_names = {
        "onset_t": "Movement Onset Time",
        "end_t": "Movement End Time",
        "pkvel_t": "Peak Velocity Time",
        "pkvel": "Peak Velocity",
        "mvt_amp": "Movement Amplitude", 
        "end_posn": "End Position"
    }
    
    for field in mvt_fields:
        all_values = []
        for data in file_data_list:
            if field in data['movement']:
                mat_data = read_mat(f"/home/heberto/data/turner/Ven_All/{data['filename']}")
                values = np.array(mat_data["Mvt"][field])
                valid_values = values[~np.isnan(values)]
                all_values.extend(valid_values)
        
        if all_values:
            all_values = np.array(all_values)
            compiled['movement_compiled'][field] = {
                'name': mvt_names[field],
                'min': all_values.min(),
                'max': all_values.max(),
                'mean': all_values.mean(),
                'std': all_values.std(),
                'n_values': len(all_values)
            }
    
    # Compile analog durations
    all_durations = []
    for data in file_data_list:
        all_durations.extend(data['analog_durations'])
    
    compiled['analog_compiled'] = {
        'min': np.min(all_durations),
        'max': np.max(all_durations),
        'mean': np.mean(all_durations),
        'std': np.std(all_durations),
        'n_trials': len(all_durations)
    }
    
    # Compile spike data
    spike_formats = {}
    for data in file_data_list:
        format_type = data['spike_info']['format']
        if format_type not in spike_formats:
            spike_formats[format_type] = []
        spike_formats[format_type].append(data['filename'])
    
    compiled['spike_compiled'] = spike_formats
    
    return compiled

def generate_markdown_summary(compiled_data, output_file, failed_files=None):
    """Generate markdown summary of timing analysis"""
    
    with open(output_file, 'w') as f:
        # Header
        f.write("# Timing Structure Analysis Summary\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Files analyzed**: {len(compiled_data['files_analyzed'])}\n")
        f.write(f"**Total trials**: {compiled_data['total_trials']}\n\n")
        
        # Files analyzed - just summary, no full list
        f.write("## Analysis Summary\n\n")
        f.write(f"**Successfully analyzed**: {len(compiled_data['files_analyzed'])} files\n")
        if failed_files:
            f.write(f"**Failed to analyze**: {len(failed_files)} files: {', '.join(failed_files)}\n")
        f.write("\n")
        
        # Event timing summary
        f.write("## Event Timing Summary\n\n")
        f.write("| Event | Min (ms) | Max (ms) | Mean (ms) | Std (ms) | Total Events |\n")
        f.write("|-------|----------|----------|-----------|----------|--------------|\n")
        
        for field, data in compiled_data['events_compiled'].items():
            f.write(f"| {data['name']} | {data['min']:.0f} | {data['max']:.0f} | {data['mean']:.0f} | {data['std']:.0f} | {data['n_events']} |\n")
        
        f.write("\n")
        
        # Movement parameters
        f.write("## Movement Parameters\n\n")
        f.write("### Timing Parameters\n\n")
        f.write("| Parameter | Min (ms) | Max (ms) | Mean (ms) | Std (ms) | Values |\n")
        f.write("|-----------|----------|----------|-----------|----------|---------|\n")
        
        timing_fields = ["onset_t", "end_t", "pkvel_t"]
        for field in timing_fields:
            if field in compiled_data['movement_compiled']:
                data = compiled_data['movement_compiled'][field]
                f.write(f"| {data['name']} | {data['min']:.0f} | {data['max']:.0f} | {data['mean']:.0f} | {data['std']:.0f} | {data['n_values']} |\n")
        
        f.write("\n### Kinematic Parameters\n\n")
        f.write("| Parameter | Min | Max | Mean | Std | Values |\n")
        f.write("|-----------|-----|-----|------|-----|---------|\n")
        
        kinematic_fields = ["pkvel", "mvt_amp", "end_posn"]
        for field in kinematic_fields:
            if field in compiled_data['movement_compiled']:
                data = compiled_data['movement_compiled'][field]
                f.write(f"| {data['name']} | {data['min']:.1f} | {data['max']:.1f} | {data['mean']:.1f} | {data['std']:.1f} | {data['n_values']} |\n")
        
        f.write("\n")
        
        # Analog data summary
        f.write("## Analog Data Duration\n\n")
        analog = compiled_data['analog_compiled']
        f.write(f"- **Minimum duration**: {analog['min']}ms ({analog['min']/1000:.1f}s)\n")
        f.write(f"- **Maximum duration**: {analog['max']}ms ({analog['max']/1000:.1f}s)\n")
        f.write(f"- **Mean duration**: {analog['mean']:.0f}ms ({analog['mean']/1000:.1f}s)\n")
        f.write(f"- **Standard deviation**: {analog['std']:.0f}ms ({analog['std']/1000:.1f}s)\n")
        f.write(f"- **Total trials**: {analog['n_trials']}\n\n")
        
        # Spike data summary
        f.write("## Spike Data Formats\n\n")
        for format_type, files in compiled_data['spike_compiled'].items():
            f.write(f"- **{format_type} format**: {len(files)} files\n")
        f.write("\n")
        
        # Trial timeline
        f.write("## Data-Derived Trial Timeline\n\n")
        f.write("```\n")
        f.write("Trial Start (0ms)\n")
        f.write("    |\n")
        
        # Events
        for field in ["home_cue_on", "targ_cue_on", "home_leave", "reward"]:
            if field in compiled_data['events_compiled']:
                data = compiled_data['events_compiled'][field]
                f.write(f"    ├── {data['name']} ({data['min']:.0f}-{data['max']:.0f}ms): ")
                if field == "home_cue_on":
                    f.write("Visual cue for center hold position\n")
                elif field == "targ_cue_on":
                    f.write("Peripheral target presentation\n")
                elif field == "home_leave":
                    f.write("Subject leaves home position\n")
                elif field == "reward":
                    f.write("Liquid reward for successful trial\n")
                f.write("    |\n")
        
        # Movement parameters
        f.write("    ├── Movement Parameters (Mvt structure):\n")
        for field in ["onset_t", "end_t", "pkvel_t"]:
            if field in compiled_data['movement_compiled']:
                data = compiled_data['movement_compiled'][field]
                f.write(f"    |   ├── {data['name']} ({data['min']:.0f}-{data['max']:.0f}ms)\n")
        f.write("    |   ├── Peak Velocity (pkvel): Maximum velocity value (scalar)\n")
        f.write("    |   ├── Movement Amplitude (mvt_amp): Total movement distance (scalar)\n")
        f.write("    |   └── End Position (end_posn): Final joint angle (scalar)\n")
        f.write("    |\n")
        
        # Analog and spike data
        analog = compiled_data['analog_compiled']
        f.write(f"    ├── Analog Data Streams (0-{analog['max']}ms, 1kHz sampling):\n")
        f.write("    |   ├── Position (x): Elbow joint angle throughout trial\n")
        f.write("    |   ├── Velocity (vel): Angular velocity (derived from position)\n")
        f.write("    |   ├── Torque (torq): Motor torque commands\n")
        f.write("    |   ├── EMG (emg): Muscle activity (5-6 channels, when collected)\n")
        f.write("    |   └── LFP (lfp): Local field potentials (when collected)\n")
        f.write("    |\n")
        f.write(f"    ├── Spike Times (unit_ts, 0-{analog['max']}ms):\n")
        f.write("    |   ├── 2D format: Multiple spikes per trial (trials × max_spikes)\n")
        f.write("    |   └── 1D format: Single spike per trial (some sessions)\n")
        f.write("    |\n")
        f.write(f"    └── Analog Recording End ({analog['min']}-{analog['max']}ms): Full neural/behavioral data\n")
        f.write("```\n\n")
        
        # Key statistics
        f.write("## Key Timing Statistics\n\n")
        if "home_cue_on" in compiled_data['events_compiled'] and "targ_cue_on" in compiled_data['events_compiled']:
            home_cue = compiled_data['events_compiled']["home_cue_on"]['mean']
            target_cue = compiled_data['events_compiled']["targ_cue_on"]['mean']
            f.write(f"- **Home cue to target**: ~{target_cue - home_cue:.0f}ms\n")
        
        if "targ_cue_on" in compiled_data['events_compiled'] and "home_leave" in compiled_data['events_compiled']:
            target_cue = compiled_data['events_compiled']["targ_cue_on"]['mean']
            movement = compiled_data['events_compiled']["home_leave"]['mean']
            f.write(f"- **Target to movement**: ~{movement - target_cue:.0f}ms\n")
        
        if "home_leave" in compiled_data['events_compiled'] and "reward" in compiled_data['events_compiled']:
            movement = compiled_data['events_compiled']["home_leave"]['mean']
            reward = compiled_data['events_compiled']["reward"]['mean']
            f.write(f"- **Movement to reward**: ~{reward - movement:.0f}ms\n")
        
        f.write(f"- **Analog recording duration**: {analog['min']/1000:.1f}-{analog['max']/1000:.1f}s per trial\n")
        
        if "reward" in compiled_data['events_compiled']:
            reward_mean = compiled_data['events_compiled']["reward"]['mean']
            data_beyond = analog['mean'] - reward_mean
            f.write(f"- **Data beyond reward**: ~{data_beyond:.0f}ms average\n")

def main():
    # Set up file paths - analyze ALL .mat files
    base_data_path = Path("/home/heberto/data/turner/Ven_All/")
    
    # Find all .mat files in the directory
    all_mat_files = list(base_data_path.glob("*.mat"))
    all_mat_files.sort()  # Sort for consistent ordering
    
    existing_files = all_mat_files
    
    if not existing_files:
        print("No MATLAB files found for analysis")
        return
    
    print(f"Found {len(existing_files)} MATLAB files")
    print(f"Analyzing all files...")
    
    # Analyze each file with error handling
    file_data_list = []
    failed_files = []
    
    for i, file_path in enumerate(existing_files, 1):
        try:
            print(f"  [{i:3d}/{len(existing_files)}] {file_path.name}")
            data = analyze_single_file(file_path)
            file_data_list.append(data)
        except Exception as e:
            print(f"  [{i:3d}/{len(existing_files)}] {file_path.name} - FAILED: {str(e)}")
            failed_files.append(file_path.name)
            continue
    
    if failed_files:
        print(f"\nFailed to analyze {len(failed_files)} files:")
        for filename in failed_files:
            print(f"  - {filename}")
    
    # Compile across files
    compiled_data = compile_across_files(file_data_list)
    
    # Generate markdown summary
    output_file = Path(__file__).parent / "timing_analysis_summary.md"
    generate_markdown_summary(compiled_data, output_file, failed_files)
    
    print(f"\nMarkdown summary generated: {output_file}")
    print(f"Successfully analyzed: {len(file_data_list)} files")
    print(f"Total trials analyzed: {compiled_data['total_trials']}")
    if failed_files:
        print(f"Failed files: {len(failed_files)}")

if __name__ == "__main__":
    main()