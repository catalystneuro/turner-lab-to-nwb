# Timing Structure Analysis Summary

**Generated**: 2025-09-09 15:12:31

**Files analyzed**: 359
**Total trials**: 9949

## Analysis Summary

**Successfully analyzed**: 359 files
**Failed to analyze**: 1 files: VenTable.mat

## Event Timing Summary

| Event | Min (ms) | Max (ms) | Mean (ms) | Std (ms) | Total Events |
|-------|----------|----------|-----------|----------|--------------|
| Center Target Appearance | 1272 | 11420 | 2453 | 756 | 9827 |
| Lateral Target Appearance | 4042 | 20586 | 6563 | 1288 | 9770 |
| Subject Movement Onset | 4330 | 21362 | 6993 | 1291 | 9263 |
| Reward Delivery | 5305 | 22331 | 7950 | 1319 | 9181 |

## Movement Parameters

### Timing Parameters

| Parameter | Min (ms) | Max (ms) | Mean (ms) | Std (ms) | Values |
|-----------|----------|----------|-----------|----------|---------|
| Derived Movement Onset Time | 4334 | 21103 | 6898 | 1273 | 8910 |
| Derived Movement End Time | 4697 | 21563 | 7286 | 1276 | 8895 |
| Derived Peak Velocity Time | 4518 | 21386 | 7089 | 1272 | 8895 |

### Kinematic Parameters

| Parameter | Min | Max | Mean | Std | Values |
|-----------|-----|-----|------|-----|---------|
| Derived Peak Velocity | 20.2 | 254.8 | 101.9 | 37.5 | 8895 |
| Derived Movement Amplitude | -37.9 | 30.4 | -3.4 | 19.7 | 8895 |
| Derived End Position | -28.8 | 30.1 | -1.3 | 19.5 | 8895 |

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
    ├── Center Target Appearance (1272-11420ms): Center target appears for monkey to align cursor
    |
    ├── Lateral Target Appearance (4042-20586ms): Lateral target appears signaling movement direction
    |
    ├── Subject Movement Onset (4330-21362ms): Subject begins movement from center toward lateral target
    |
    ├── Reward Delivery (5305-22331ms): Liquid reward for successful trial
    |
    ├── Derived Movement Parameters (from kinematic analysis):
    |   ├── Derived Movement Onset Time (4334-21103ms)
    |   ├── Derived Movement End Time (4697-21563ms)
    |   ├── Derived Peak Velocity Time (4518-21386ms)
    |   ├── Derived Peak Velocity: Maximum velocity during target capture
    |   ├── Derived Movement Amplitude: Amplitude of target capture movement
    |   └── Derived End Position: Angular joint position at movement end
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

- **Center target to lateral target**: ~4110ms
- **Lateral target to subject movement**: ~430ms
- **Subject movement to reward**: ~957ms
- **Analog recording duration**: 1.5-23.1s per trial
- **Data beyond reward**: ~799ms average
