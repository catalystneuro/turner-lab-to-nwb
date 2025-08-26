# Timing Structure Analysis Summary

**Generated**: 2025-08-25 20:13:51

**Files analyzed**: 359
**Total trials**: 9949

## Analysis Summary

**Successfully analyzed**: 359 files
**Failed to analyze**: 1 files: VenTable.mat

## Event Timing Summary

| Event | Min (ms) | Max (ms) | Mean (ms) | Std (ms) | Total Events |
|-------|----------|----------|-----------|----------|--------------|
| Home Cue | 1272 | 11420 | 2453 | 756 | 9827 |
| Target Cue | 4042 | 20586 | 6563 | 1288 | 9770 |
| Movement Onset | 4330 | 21362 | 6993 | 1291 | 9263 |
| Reward Delivery | 5305 | 22331 | 7950 | 1319 | 9181 |

## Movement Parameters

### Timing Parameters

| Parameter | Min (ms) | Max (ms) | Mean (ms) | Std (ms) | Values |
|-----------|----------|----------|-----------|----------|---------|
| Movement Onset Time | 4334 | 21103 | 6898 | 1273 | 8910 |
| Movement End Time | 4697 | 21563 | 7286 | 1276 | 8895 |
| Peak Velocity Time | 4518 | 21386 | 7089 | 1272 | 8895 |

### Kinematic Parameters

| Parameter | Min | Max | Mean | Std | Values |
|-----------|-----|-----|------|-----|---------|
| Peak Velocity | 20.2 | 254.8 | 101.9 | 37.5 | 8895 |
| Movement Amplitude | -37.9 | 30.4 | -3.4 | 19.7 | 8895 |
| End Position | -28.8 | 30.1 | -1.3 | 19.5 | 8895 |

## Analog Data Duration

- **Minimum duration**: 1548ms (1.5s)
- **Maximum duration**: 23068ms (23.1s)
- **Mean duration**: 8748ms (8.7s)
- **Standard deviation**: 1382ms (1.4s)
- **Total trials**: 9949

## Spike Data Formats

- **2D format**: 357 files
- **1D format**: 2 files

## Data-Derived Trial Timeline

```
Trial Start (0ms)
    |
    ├── Home Cue (1272-11420ms): Visual cue for center hold position
    |
    ├── Target Cue (4042-20586ms): Peripheral target presentation
    |
    ├── Movement Onset (4330-21362ms): Subject leaves home position
    |
    ├── Reward Delivery (5305-22331ms): Liquid reward for successful trial
    |
    ├── Movement Parameters (Mvt structure):
    |   ├── Movement Onset Time (4334-21103ms)
    |   ├── Movement End Time (4697-21563ms)
    |   ├── Peak Velocity Time (4518-21386ms)
    |   ├── Peak Velocity (pkvel): Maximum velocity value (scalar)
    |   ├── Movement Amplitude (mvt_amp): Total movement distance (scalar)
    |   └── End Position (end_posn): Final joint angle (scalar)
    |
    ├── Analog Data Streams (0-23068ms, 1kHz sampling):
    |   ├── Position (x): Elbow joint angle throughout trial
    |   ├── Velocity (vel): Angular velocity (derived from position)
    |   ├── Torque (torq): Motor torque commands
    |   ├── EMG (emg): Muscle activity (5-6 channels, when collected)
    |   └── LFP (lfp): Local field potentials (when collected)
    |
    ├── Spike Times (unit_ts, 0-23068ms):
    |   ├── 2D format: Multiple spikes per trial (trials × max_spikes)
    |   └── 1D format: Single spike per trial (some sessions)
    |
    └── Analog Recording End (1548-23068ms): Full neural/behavioral data
```

## Key Timing Statistics

- **Home cue to target**: ~4110ms
- **Target to movement**: ~430ms
- **Movement to reward**: ~957ms
- **Analog recording duration**: 1.5-23.1s per trial
- **Data beyond reward**: ~799ms average
