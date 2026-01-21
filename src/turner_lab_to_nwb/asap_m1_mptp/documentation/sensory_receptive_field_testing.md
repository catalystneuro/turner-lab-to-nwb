# Sensory Receptive Field Testing in the Turner Lab Dataset

## Overview

During single-unit recordings from primary motor cortex (M1), researchers performed qualitative sensory testing to characterize each neuron's receptive field properties. This testing assessed whether neurons responded to somatosensory stimulation of the arm, helping localize recording sites within the arm-related motor cortex and providing additional physiological characterization beyond antidromic identification.

## Scientific Context

### Why Test Sensory Responses in Motor Cortex?

Primary motor cortex neurons receive substantial proprioceptive and tactile input, creating a sensorimotor integration zone. Testing sensory responses serves several purposes:

1. **Anatomical Localization**: M1 arm representation can be identified by neurons responding to arm manipulation. Sensory responses to specific body regions (hand, elbow, shoulder) confirm the electrode is in the appropriate somatotopic zone of motor cortex.

2. **Standard Electrophysiological Practice**: Characterizing receptive fields is routine during extracellular recordings. It provides a qualitative "fingerprint" of each neuron beyond spike waveform and firing rate.

3. **Relevance to Parkinsonism**: The muscle stretch paper specifically examined how MPTP affects cortical processing of proprioceptive input. Knowing each neuron's sensory responsiveness contextualizes these findings.

### How Was Sensory Testing Performed?

From the methods section of "Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons" (Pasquereau & Turner, 2011):

> "A cortical region was targeted for data collection if neurons responded to active and/or passive movement of the arm and microstimulation at low currents evoked contraction of forelimb muscles (<40 μA, 10 biphasic pulses at 300 Hz)"

**Important distinction - Two separate electrode systems were used:**

1. **Recording electrode** (glass-coated tungsten microelectrode): Advanced through cortex via the chronic recording chamber to record single-unit activity. This is the same electrode that captures the spike times stored in the NWB Units table.

2. **Stimulating electrodes** (for antidromic identification): Separate electrodes chronically implanted in the cerebral peduncle (for PTN identification) and posterolateral putamen (for CSN identification). These deliver electrical pulses to activate axons antidromically.

The sensory characterization was performed through **manual sensorimotor examination** while recording from the cortical electrode:

1. **Neuron Isolation**: While advancing the recording microelectrode through cortex, researchers isolated single units based on spike waveform
2. **Sensorimotor Mapping**: For each isolated neuron, the experimenter manually manipulated the monkey's arm (passive movement) and observed the animal's active movements while listening to the audio monitor of neural activity
3. **Qualitative Assessment**: The experimenter noted which body regions and which types of manipulation (flexion, extension, touch, etc.) caused the neuron to fire
4. **Documentation**: Responses were recorded in free-text format in the metadata table

The microstimulation mentioned in the quote (40 μA pulses) was used separately to verify the recording site was in motor cortex by evoking muscle contractions - this confirmed the electrode was in the arm representation of M1.

This is standard qualitative receptive field mapping used in primate neurophysiology.

### Types of Sensory Stimulation

Researchers applied manual somatosensory stimulation during recording, including:

- **Proprioceptive**: Joint manipulation (flexion, extension, pronation, supination)
- **Tactile**: Light touch, pressure, tapping, probing of skin
- **Active**: Responses during voluntary movement or grip by the animal

## Data Encoding

The receptive field characterization is stored in two metadata columns that translate to NWB unit table columns:

### `receptive_field_location` (source: SENSORY column)

**Purpose**: Records the body region(s) comprising the neuron's receptive field.

**Values observed in the dataset**:

| Category | Values | Count |
|----------|--------|-------|
| Single joint/region | `hand`, `wrist`, `elbow`, `forearm`, `shoulder`, `finger` | 140 |
| Multiple regions | `hand / wrist`, `elbow / forearm`, `wrist / elbow / hand`, etc. | 51 |
| No response | `no_response` (testing performed, no response detected) | 101 |
| Not tested | `not_tested` (receptive field testing not performed) | 67 |

**Interpretation**:
- Body regions are listed in order of responsiveness (primary region first)
- Multiple regions separated by ` / ` indicate neurons with broad receptive fields
- Anatomically, most neurons responded to distal arm regions (hand, wrist, fingers) consistent with the arm-related M1 recording target

### `receptive_field_stimulus` (source: SENS_DETAIL column)

**Purpose**: Describes the specific sensory stimulus or manipulation that activated this neuron.

**Categories of stimuli**:

| Type | Examples | Description |
|------|----------|-------------|
| **Extension** | `ext`, `finger ext`, `wrist ext`, `elbow ext` | Neuron fires during joint/digit extension |
| **Flexion** | `flex`, `finger flex`, `wrist flex`, `elbow flex` | Neuron fires during joint/digit flexion |
| **Rotation** | `pron`, `sup`, `forearm pron`, `forearm sup` | Neuron fires during forearm pronation/supination |
| **Tactile** | `light touch`, `palm probe`, `cut stim`, `finger tap` | Neuron fires to cutaneous stimulation |
| **Active movement** | `active`, `active grip`, `active hand` | Neuron fires during voluntary movement |
| **Combined** | `finger ext & elbow ext`, `wrist / finger flex` | Multi-joint or combined responses |
| **Special notations** | `nearby fire w/ finger ext`, `selective finger ext` | Notes about response specificity |
| **No response** | `NR` | Testing performed, no response detected |
| **Not tested** | `NT` | Receptive field testing not performed |

**Abbreviations used**:
- `ext` = extension
- `flex` = flexion
- `pron` = pronation
- `sup` = supination
- `abd` = abduction
- `cut` = cutaneous (skin stimulation)
- `wk` = weak (response)

## Distribution in Dataset

```
Receptive Field Location Distribution (n=359 units):
- Hand-related (hand, finger, wrist): 125 units (35%)
- Proximal arm (elbow, forearm, shoulder): 36 units (10%)
- Multiple regions: 51 units (14%)
- No response: 101 units (28%)
- Not tested: 67 units (19%)
```

The predominance of hand/wrist responses reflects the recording target in arm-related M1, where distal representations are prominent.

## Relationship to Other Unit Properties

### Cell Type (Antidromic Classification)

Both pyramidal tract neurons (PTNs) and corticostriatal neurons (CSNs) can show sensory responses. The sensory characterization is independent of but complementary to the antidromic cell-type identification:

- **PTNs**: Direct output neurons to spinal cord; sensory responses indicate closed-loop sensorimotor properties
- **CSNs**: Project to striatum; sensory responses indicate cortical processing before basal ganglia relay

### MPTP Condition

Sensory testing was performed during recording sessions both pre- and post-MPTP. The muscle stretch paper specifically analyzed how proprioceptive responses change with parkinsonism, finding enhanced and temporally altered cortical stretch responses after MPTP.

## NWB Storage

In converted NWB files, receptive field properties are stored in the Units table:

```python
# Access receptive field properties
units_df = nwbfile.units.to_dataframe()

# Receptive field location (normalized to lowercase, or 'no_response'/'not_tested')
rf_locations = units_df['receptive_field_location']

# Stimulus type that activated the neuron (verbatim from source, or 'NR'/'NT')
rf_stimuli = units_df['receptive_field_stimulus']

# Filter units by receptive field properties
hand_responsive = units_df[units_df['receptive_field_location'].str.contains('hand', na=False)]
extension_responsive = units_df[units_df['receptive_field_stimulus'].str.contains('ext', na=False)]
```

## Limitations

1. **Qualitative Assessment**: Sensory testing was performed manually without quantitative measurement of stimulus parameters or response magnitudes.

2. **Incomplete Testing**: 19% of units were not tested (`NT`), typically when recording time was limited or the primary focus was on other characterization.

3. **Observer Variability**: Descriptions were recorded by experimenters in free text, leading to terminology variation (e.g., `ext` vs `extension`, `finger ext` vs `selective finger ext`).

4. **Not Standardized Across Sessions**: Testing protocols may have varied across the multi-year recording period.

## References

The sensory characterization methodology is described in the Turner lab papers:

- Pasquereau & Turner (2011) - Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons
- Pasquereau & Turner (2013) - Primary motor cortex of the parkinsonian monkey: altered neuronal responses to muscle stretch
- Pasquereau, DeLong & Turner (2016) - Primary motor cortex of the parkinsonian monkey: altered encoding of active movement
