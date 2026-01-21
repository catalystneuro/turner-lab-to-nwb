# Electromyography (EMG) Recordings in the Turner Lab Dataset

## Overview

During single-unit recordings from primary motor cortex (M1), researchers simultaneously recorded electromyographic (EMG) activity from forearm and upper arm muscles. EMG recordings provided critical information about the timing and pattern of muscle activation during both voluntary movements and proprioceptive perturbations, enabling direct comparison between cortical neural activity and peripheral motor output.

## Scientific Context

### Why Record EMG in This Study?

Recording EMG alongside cortical single-unit activity serves several important purposes in the Turner lab's parkinsonian motor studies:

1. **Motor Output Reference**: EMG provides a direct measure of the motor commands that reach muscles, allowing researchers to distinguish between cortical dysfunction and downstream motor execution deficits.

2. **Stretch Reflex Assessment**: The long-latency stretch reflex (LLSR) is quantified through EMG responses to torque perturbations. The LLSR is exaggerated in parkinsonism and contributes to rigidity.

3. **Movement Kinematics Correlation**: EMG patterns reveal the muscle activation strategy used to produce movements, complementing kinematic measures (position, velocity) from the manipulandum.

4. **Triphasic Pattern Analysis**: Normal ballistic movements exhibit a characteristic triphasic EMG pattern (agonist-antagonist-agonist). Disruption of this pattern is a hallmark of parkinsonian bradykinesia.

### Muscles Recorded

Different muscle sets were implanted in each subject, tailored to the specific joint used in the task:

**Monkey L (Wrist Task)**:
- Flexor carpi ulnaris (wrist flexor)
- Flexor carpi radialis (wrist flexor)
- Biceps longus (elbow flexor)
- Brachioradialis (elbow flexor/forearm supinator)
- Triceps lateralis (elbow extensor)

**Monkey V (Elbow Task)**:
- Posterior deltoid (shoulder extensor)
- Trapezius (shoulder/scapula)
- Triceps longus (elbow extensor)
- Triceps lateralis (elbow extensor)
- Brachioradialis (elbow flexor/forearm supinator)

### EMG Recording Methods

From the methods sections of the Turner lab papers (Pasquereau & Turner, 2013; Pasquereau, DeLong & Turner, 2016):

> "Pairs of Teflon-insulated multistranded stainless steel wires were implanted into multiple arm muscles... The wires were led subcutaneously to a connector fixed to the skull implant. Accurate placement of electromyographic (EMG) electrodes was verified post-surgically."

**Signal Processing Pipeline**:
1. EMG signals were differentially amplified (gain = 10,000)
2. Band-pass filtered (20 Hz to 5 kHz)
3. Full-wave rectified
4. Low-pass filtered (100 Hz)
5. Digitized at either 200 Hz (Monkey L) or 500 Hz (Monkey V), interpolated to 1 kHz

**Important**: The stored EMG data represents **preprocessed** (rectified and low-pass filtered) muscle activity, not raw EMG waveforms. This processing converts the biphasic EMG signal into an envelope representing muscle activation magnitude.

**Data Format**: The EMG values in the source files appear to be raw A/D converter output (centered around ~2048, consistent with 12-bit digitization). No voltage calibration factor is documented in the source materials, so the data is stored in arbitrary units in the NWB files.

## Data Availability

EMG data was collected during only a subset of recording sessions:

| Condition | Sessions with EMG |
|-----------|-------------------|
| Pre-MPTP | ~20 sessions |
| Post-MPTP | ~8 sessions |

**Critical Limitation**: No usable EMG signal was available in Monkey L after MPTP administration due to electrode degradation.

The `emg_collected` flag in the metadata table indicates which sessions include EMG data.

## Key Findings from EMG Analysis

### Voluntary Movement (Active Movement Paper)

During the visuomotor step-tracking task:

**Normal State**:
- EMG exhibited characteristic triphasic activation pattern
- Agonist muscle (e.g., triceps for extension) showed sharp onset ~100 ms before movement
- Activity ramped up steeply to peak at ~+70 ms after movement onset
- Antagonist muscle (e.g., brachioradialis) showed reciprocal inhibition followed by braking burst

**Post-MPTP**:
- Slower rate of rise in agonist EMG activity
- Later peak activation (delayed relative to movement onset)
- Prolonged, sustained activation (>500 ms after movement onset vs. sharp peak)
- Reduced directional specificity (similar patterns for both movement directions)
- Disrupted triphasic pattern contributing to bradykinesia

### Proprioceptive Perturbations (Muscle Stretch Paper)

During torque perturbation trials:

**EMG Response Components**:
- **M1 (Short-latency)**: 20-45 ms, spinal reflex
- **M2 (Long-latency early)**: 45-75 ms, transcortical component
- **M3 (Long-latency late)**: 75-100 ms, volitional/transcortical

**Post-MPTP Changes**:
- Enhanced long-latency EMG responses (exaggerated LLSR)
- Total duration of EMG responses prolonged
- Latencies of earliest EMG responses unchanged (spinal component intact)
- Enhanced muscle activation contributing to rigidity

## Data Encoding in NWB Files

### Storage Location

EMG data is stored as TimeSeries objects in the NWB file's acquisition group:

```python
# Access EMG data from NWB file
emg_triceps = nwbfile.acquisition['EMGTricepsLongus']
emg_brachioradialis = nwbfile.acquisition['EMGBrachioradialis']

# Get data and timestamps
emg_data = emg_triceps.data[:]
timestamps = emg_triceps.timestamps[:]

print(f"EMG data shape: {emg_data.shape}")
print(f"Duration: {timestamps[-1] - timestamps[0]:.2f} seconds")
```

### Data Structure

Each muscle's EMG is stored as a separate TimeSeries with:
- **Data**: Continuous preprocessed EMG signal (rectified, filtered)
- **Timestamps**: Time points for each sample (accounts for inter-trial intervals)
- **Unit**: Arbitrary units (a.u.) - relative amplitude after preprocessing
- **Description**: Muscle name and recording methodology

### Naming Convention

EMG channels are named using the pattern `EMG{MuscleName}`:
- `EMGTricepsLongus`
- `EMGTricepsLateralis`
- `EMGBrachioradialis`
- `EMGTrapezius`
- `EMGDeltoidPosterior`

When duplicate muscle recordings exist (e.g., two triceps channels), numeric suffixes are added: `EMGTricepsLongus1`, `EMGTricepsLongus2`.

### Example Analysis

```python
import numpy as np
from pynwb import NWBHDF5IO

# Load NWB file
with NWBHDF5IO('session.nwb', 'r') as io:
    nwbfile = io.read()

    # List all EMG channels
    emg_channels = [name for name in nwbfile.acquisition.keys()
                    if name.startswith('EMG')]
    print(f"Available EMG channels: {emg_channels}")

    # Get trial table for alignment
    trials = nwbfile.trials.to_dataframe()

    # Extract EMG around movement onset for first trial
    trial = trials.iloc[0]
    movement_onset = trial['go_cue_time']  # or appropriate column

    # Get EMG data
    emg = nwbfile.acquisition['EMGTricepsLongus']
    timestamps = emg.timestamps[:]

    # Find indices for peri-movement window (-500ms to +500ms)
    window_start = movement_onset - 0.5
    window_end = movement_onset + 0.5
    mask = (timestamps >= window_start) & (timestamps <= window_end)

    peri_movement_emg = emg.data[mask]
    peri_movement_time = timestamps[mask] - movement_onset
```

## Relationship to Neural Activity

### Temporal Alignment

EMG and neural spike data can be aligned to:
- **Target appearance** (go cue): To examine preparatory activity
- **Movement onset**: To compare motor command timing
- **Torque perturbation onset**: To analyze stretch reflex pathways

### Cell Type Correlations

**Pyramidal Tract Neurons (PTNs)**:
- Direct projections to spinal motor neurons
- Activity changes ~50-100 ms before EMG changes during voluntary movement
- PTN hypoactivation post-MPTP correlates with altered EMG patterns

**Corticostriatal Neurons (CSNs)**:
- Indirect influence on motor output via basal ganglia
- Less direct correlation with EMG timing
- Relatively preserved activity post-MPTP despite EMG abnormalities

### Key Dissociation: LLSR vs. Cortical Responses

A critical finding from the muscle stretch study: the exaggerated LLSR (measured via EMG) was **not** accompanied by enhanced M1 cortical responses. This dissociation suggests:

1. The exaggerated LLSR in parkinsonism is primarily mediated by **spinal mechanisms**
2. M1 cortical stretch responses are actually unchanged or reduced
3. Reduced cortical descending inhibition may disinhibit spinal reflexes

## Limitations

1. **Preprocessed Data**: Stored EMG is rectified and filtered; raw waveforms are not available for alternative processing.

2. **Subset of Sessions**: EMG was not recorded in all sessions, limiting statistical power for some analyses.

3. **Post-MPTP Gap**: No post-MPTP EMG from Monkey L due to electrode issues.

4. **Relative Amplitudes**: Units are arbitrary (preprocessed signal), so absolute force cannot be directly inferred.

5. **Limited Muscle Set**: Only 5-6 muscles per subject; some synergists and antagonists were not recorded.

## References

The EMG recording methodology and analysis are described in:

- Pasquereau B, Turner RS (2013) Primary motor cortex of the parkinsonian monkey: altered neuronal responses to muscle stretch. *Frontiers in Systems Neuroscience* 7:98.

- Pasquereau B, DeLong MR, Turner RS (2016) Primary motor cortex of the parkinsonian monkey: altered encoding of active movement. *Brain* 139:127-143.

Background on EMG analysis methods:

- Basmajian JV, De Luca CJ (1985) Muscles Alive: Their Functions Revealed by Electromyography. 5th ed. Williams & Wilkins.

- Turner RS, Grafton ST, Votaw JR, Delong MR, Hoffman JM (1998) Motor subcircuits mediating the control of movement velocity. *Journal of Neurophysiology* 80:2162-2176.
