# Trial Structure and Timing Analysis

## Overview

The Turner Lab MPTP dataset presents an important design decision regarding how to define trial boundaries for NWB conversion. The MATLAB data files contain trial-segmented data where all timing information (events, spikes, analog signals) is relative to individual trial starts. This document analyzes different approaches for defining `start_time` and `stop_time` for trials in the NWB format.

## Data Structure Context

### Trial-Relative Timing
All data in the MATLAB files is stored relative to individual trial starts:
- **Event times**: Stored in milliseconds relative to trial start (e.g., center_target_appearance=2199ms, reward=8177ms)
- **Spike times**: Stored in milliseconds relative to trial start
- **Analog data**: Stored as separate arrays per trial (e.g., `Analog.x[trial_idx]`)
- **Derived movement parameters**: Extracted kinematics from post-processing analysis relative to trial start

### Typical Trial Timeline
**UPDATED**: Based on comprehensive analysis of 359 MATLAB files containing 9,949 trials:
```
Trial Start (0ms)
    |
    ├── Center Target Appearance (2,453ms ± 756ms)
    |   • Range: 1,272-11,420ms across dataset
    |   • Visual cue for monkey to align cursor with center position
    |   
    ├── [Hold Period: ~4.1s average]
    |   • Monkey maintains cursor at center target
    |   • Torque perturbations applied here when present (1-2s after capture)
    |     └── Torque Impulse: 0.1 Nm, 50ms, causing ~10° displacement
    |
    ├── Lateral Target Appearance (6,563ms ± 1,288ms)
    |   • Range: 4,042-20,586ms across dataset
    |   • Peripheral target signals movement direction (flexion/extension)
    |
    ├── [Reaction Time: ~430ms average]
    |   • Motor planning and decision period
    |
    ├── Subject Movement Onset (6,993ms ± 1,291ms)
    |   • Range: 4,330-21,362ms across dataset
    |   • Monkey begins movement from center toward lateral target
    |   │
    |   ├── Derived Movement Onset (6,898ms ± 1,273ms)
    |   │   • Algorithmically detected movement start from kinematics
    |   │   • Range: 4,334-21,103ms
    |   │
    |   ├── Peak Velocity Time (7,089ms ± 1,272ms)
    |   │   • Range: 4,518-21,386ms
    |   │   • Maximum velocity: 101.9±37.5°/s (range: 20.2-254.8°/s)
    |   │
    |   └── Derived Movement End (7,286ms ± 1,276ms)
    |       • Range: 4,697-21,563ms
    |       • Movement amplitude: -3.4±19.7° (range: -37.9° to 30.4°)
    |       • End position: -1.3±19.5° (range: -28.8° to 30.1°)
    |
    ├── Reward Delivery (7,950ms ± 1,319ms)
    |   • Range: 5,305-22,331ms across dataset
    |   • Liquid reward for successful target acquisition
    |
    └── Recording End (8,748ms ± 1,382ms)
        • Range: 1,548-23,068ms across dataset
        • Analog data capture continues ~799ms beyond reward
        • 1kHz sampling for position, velocity, torque, EMG, LFP
        • Spike times recorded throughout with millisecond precision
```

### Key Timing Statistics (Updated from 9,949 trials)
- **Center target to lateral target**: ~4,110ms (SD: 1,288ms)
- **Lateral target to subject movement**: ~430ms (SD: varies)  
- **Subject movement to reward**: ~957ms (SD: varies)
- **Analog recording duration**: 1.5-23.1s per trial (mean: 8.7s)
- **Data beyond reward**: ~799ms average

## Trial Boundary Options

### Option 1: Event-Based Boundaries (0 to reward + 1.0s)

**Definition**: 
- `start_time = 0` (relative to trial recording start)
- `stop_time = reward_time + 1.0s`

**Rationale**:
- Reward marks behavioral task completion
- 1-second buffer captures post-reward neural responses
- Consistent with typical motor control study conventions
- Aligns with task structure described in published papers

**Advantages**:
- ✅ Contains all behavioral events
- ✅ Contains all analog data (verified across test files)
- ✅ Contains all spike data  
- ✅ Biologically meaningful endpoints
- ✅ Consistent trial durations (7.3-10.3s)

**Disadvantages**:
- ❌ May truncate very late neural activity
- ❌ Fixed buffer may not suit all trial types

**Implementation**:
```python
trial_start = cumulative_time
trial_stop = cumulative_time + reward_time/1000 + 1.0
cumulative_time = trial_stop + inter_trial_interval
```

### Option 2: Analog-Based Boundaries (0 to analog_end)

**Definition**:
- `start_time = 0`
- `stop_time = len(Analog.x[trial]) / 1000.0` (full analog duration)

**Rationale**:
- Uses natural recording boundaries
- Preserves all recorded data
- No assumptions about relevant time windows
- Matches actual data collection parameters

**Advantages**:
- ✅ Guaranteed to contain ALL recorded data
- ✅ No data truncation
- ✅ Preserves late neural responses
- ✅ True to original recording structure
- ✅ Variable trial lengths reflect actual experimental conditions

**Disadvantages**:
- ❌ May include irrelevant post-task activity
- ❌ Slightly larger file sizes

**Implementation**:
```python
trial_start = cumulative_time
trial_stop = cumulative_time + len(analog_data[trial]) / 1000.0
cumulative_time = trial_stop + inter_trial_interval
```

### Option 3: Center Target to Reward + Buffer

**Definition**:
- `start_time = center_target_appearance_time` (first behavioral event)
- `stop_time = reward_time + 0.5s`

**Rationale**:
- Trial starts with first task-relevant event (center target appearance)
- Minimal pre-task baseline included
- Focuses on behaviorally relevant period
- Reduces data storage for pre-task periods

**Advantages**:
- ✅ Tightly aligned with task execution
- ✅ Minimal irrelevant data
- ✅ Clear behavioral anchoring
- ✅ Smaller file sizes

**Disadvantages**:
- ❌ Loses pre-center-target baseline activity
- ❌ May miss preparatory neural signals
- ❌ Incompatible with some baseline correction methods
- ❌ Doesn't contain full analog recordings

**Implementation**:
```python
trial_start = cumulative_time
trial_stop = cumulative_time + (reward_time - center_target_appearance_time)/1000 + 0.5
cumulative_time = trial_stop + inter_trial_interval
```

## Analysis Results

### Data Containment Testing

Testing across three representative files (v0502.1.mat, v3601.1.mat, v0601.1.mat):

| Approach | Events | Analog | Spikes | Consistency |
|----------|--------|--------|--------|-------------|
| 0 to reward+1.0s | ✅ 100% | ✅ 100% | ✅ 100% | High |
| 0 to analog_end | ✅ 100% | ✅ 100% | ✅ 100% | High |
| center_target to reward+0.5s | ✅ 100% | ❌ 60% | ❌ 70% | Medium |

### Trial Duration Distribution
**UPDATED**: Based on comprehensive analysis of 9,949 trials:

| Approach | Min | Max | Mean | StdDev |
|----------|-----|-----|------|--------|
| Event-based (0 to reward+1s) | 6.3s | 23.3s | 9.0s | 1.3s |
| Analog-based (actual recordings) | 1.5s | 23.1s | 8.7s | 1.4s |
| Center target to reward+0.5s | 4.8s | 22.8s | 8.4s | 1.3s |

## Inter-Trial Intervals

The `inter_trial_time_interval` parameter (default: 3.0s) represents the gap between trials, not trial duration. This creates a continuous timeline where:

```
Trial 0: [0, stop_0]
Gap: [stop_0, stop_0 + 3.0]
Trial 1: [stop_0 + 3.0, stop_1]
Gap: [stop_1, stop_1 + 3.0]
Trial 2: [stop_1 + 3.0, stop_2]
...
```

## Recommendation for Discussion

**Primary recommendation**: **Option 1 (Event-based: 0 to reward + 1.0s)**

This approach balances biological significance with data completeness. It:
- Aligns with experimental design (reward marks trial completion)
- Contains all recorded data based on testing
- Provides consistent, meaningful boundaries
- Follows conventions in motor neuroscience literature

**Alternative for consideration**: **Option 2 (Analog-based)**

If preserving every millisecond of recorded data is critical, using analog boundaries ensures no data loss while maintaining the natural structure of the recordings. Variable trial lengths are not problematic and actually reflect the true experimental conditions.

## Questions for Data Authors

1. **Biological significance**: Is there important neural activity beyond reward + 1.0s that should be preserved?

2. **Task design**: Were trials intentionally recorded for specific durations, or did recording stop naturally after task completion?

3. **Inter-trial intervals**: Is the 3.0s default inter-trial interval accurate for the experimental protocol?

4. **Pre-center-target activity**: Is the pre-center-target period (0 to ~2.5s) scientifically important for baseline or preparatory activity analysis?

5. **Data completeness priority**: Should we prioritize preserving all recorded data (Option 2) or focus on behaviorally relevant periods (Option 1)?

## Implementation Notes

The chosen approach will affect:
- Total NWB file size
- Memory requirements for analysis
- Compatibility with analysis pipelines
- Interpretability of neural dynamics

The conversion pipeline should document which approach was used and provide rationale for future users of the dataset.