# Experimental Setup Commonalities Across MPTP Studies

This document summarizes the common experimental elements and key differences across the three Turner lab papers studying primary motor cortex (M1) in MPTP-treated parkinsonian macaques.

## Publication Series

| Paper | Year | Journal | Focus |
|-------|------|---------|-------|
| Pyramidal Tract Neurons | 2011 | Cerebral Cortex | Spontaneous activity |
| Muscle Stretch | 2013 | Frontiers in Systems Neuroscience | Proprioceptive responses |
| Active Movement | 2016 | Brain | Movement encoding |

## Common Elements

### Animal Subjects

All three studies used the same two animals:

| Subject | Species | Sex | Weight | Notes |
|---------|---------|-----|--------|-------|
| Monkey V | *Macaca mulatta* | Female | 4.8 kg | Rhesus macaque |
| Monkey L | *Macaca mulatta* | Female | 6.0 kg | Rhesus macaque |

### MPTP Treatment Protocol

Identical across all studies:

| Parameter | Value |
|-----------|-------|
| **Neurotoxin** | MPTP-HCl (1-methyl-4-phenyl-1,2,3,6-tetrahydropyridine) |
| **Dose** | 0.5 mg/kg |
| **Route** | Unilateral intracarotid injection |
| **Injection Site** | Left internal carotid artery |
| **Effect** | Selective dopaminergic denervation of right hemisphere |
| **Symptom Profile** | Moderate, stable left-sided hemiparkinsonian symptoms |

### Parkinsonian Symptoms Observed
- Bradykinesia (slowness of movement)
- Hypometria (reduced movement amplitude)
- Rigidity (increased muscle tone)
- Akinesia (difficulty initiating movement)
- Symptoms stable throughout post-MPTP recording periods

### Recording Methods

| Element | Specification |
|---------|---------------|
| **Recording Site** | Primary motor cortex (M1), arm area |
| **Cortical Layer** | Layer 5 (pyramidal cell layer) |
| **Electrode Type** | Glass-coated tungsten microelectrodes |
| **Electrode Access** | Chronic recording chamber implanted over M1 |
| **Signal Processing** | Offline spike sorting to isolate single units |
| **Hemisphere** | Right (contralateral to injection, ipsilateral to symptoms) |

### Neuron Type Identification

#### Antidromic Stimulation Parameters

| Neuron Type | Stimulation Site | Current | Pulse Duration | Latency Range |
|-------------|------------------|---------|----------------|---------------|
| **PTN** | Cerebral peduncle | 100-400 uA | 0.2 ms biphasic | 0.6-2.5 ms |
| **CSN** | Posterolateral putamen | 100-600 uA | 0.2 ms biphasic | 2.0-20 ms |

#### Antidromic Identification Criteria
All neurons met three standard criteria:
1. **Fixed latency**: Consistent response timing across stimulations
2. **High-frequency following**: Ability to follow >200 Hz stimulation
3. **Collision test**: Spontaneous spikes within critical window blocked antidromic response

### Experimental Design
- Pre- and post-MPTP comparison design
- Same neurons types studied before and after MPTP treatment
- Within-subject longitudinal design

## Study-Specific Differences

### Experimental Paradigms

| Study | Paradigm Type | Behavioral State | Key Measurements |
|-------|---------------|------------------|------------------|
| **Pyramidal Tract Neurons** | No task | Quiet rest (awake) | Spontaneous firing rates, burst patterns, oscillations |
| **Muscle Stretch** | Passive perturbation | Relaxed, passive | Stretch-evoked responses, reflex latencies, EMG |
| **Active Movement** | Visuomotor step-tracking | Active motor behavior | Movement-related activity, kinematic encoding |

### Pyramidal Tract Neurons Study (2011)

**Experimental Conditions:**
- Monkey at rest, awake but not performing any task
- EMG monitored to confirm absence of movement
- Minimum 60 seconds of stable recording per neuron

**Analysis Focus:**
- Mean spontaneous firing rates
- Coefficient of variation (CV) of interspike intervals
- Burst analysis (Poisson Surprise method)
- Beta-band (14-32 Hz) oscillatory activity
- Power spectral density analysis

**Neuron Counts:**

| Condition | PTNs | CSNs | Total |
|-----------|------|------|-------|
| Pre-MPTP  | 72   | 55   | 127   |
| Post-MPTP | 51   | 43   | 94    |
| **Total** | **123** | **98** | **221** |

### Muscle Stretch Study (2013)

**Experimental Conditions:**
- Monkey's arm positioned in manipulandum
- Arm relaxed, no active holding
- Torque motor delivered rapid step perturbations
- Perturbations in both flexion and extension directions

**Analysis Focus:**
- Response latencies to perturbation onset
- Response magnitude (peak and integrated)
- Directional selectivity index
- EMG stretch reflex components (M1, M2, M3)
- Comparison of neural vs behavioral (EMG) responses

**Neuron Counts:**

| Condition | PTNs | CSNs | Total |
|-----------|------|------|-------|
| Pre-MPTP  | 68   | 52   | 120   |
| Post-MPTP | 47   | 38   | 85    |
| **Total** | **115** | **90** | **205** |

### Active Movement Study (2016)

**Experimental Conditions:**
- Visuomotor step-tracking task
- Monkey controls cursor by elbow flexion/extension
- Center-out movements to peripheral targets
- Randomized hold periods and movement directions

**Task Sequence:**
1. CENTER HOLD (1-2 seconds variable)
2. GO CUE / TARGET APPEARANCE (flexion or extension)
3. MOVEMENT PHASE
4. TARGET HOLD (variable)
5. REWARD

**Analysis Focus:**
- Generalized Linear Models (GLM) for kinematic encoding
- Movement-related activity (spike density functions)
- Directional tuning during active movement
- Kinematic sensitivity (pseudo-R^2)
- Pre-movement, movement, and post-movement activity

**GLM Model:**
```
E(SC_i) = exp(beta_1*Dir_i + beta_2*Pos_i + beta_3*Speed_i + beta_4*Acc_i + beta_5*RT_i)
```

**Neuron Counts:**

| Condition | PTNs | CSNs | Total |
|-----------|------|------|-------|
| Pre-MPTP  | 93   | 73   | 166   |
| Post-MPTP | 60   | 53   | 113   |
| **Total** | **153** | **126** | **279** |

## Summary of Key Findings Across Studies

### PTN Effects (Consistent Vulnerability)

| Study | PTN Finding |
|-------|-------------|
| Spontaneous Activity | 27% reduction in firing rate, increased burstiness, enhanced beta rhythmicity |
| Muscle Stretch | No enhancement of responses, degraded directional selectivity |
| Active Movement | 50% reduction in movement-related activity, 37% reduction in kinematic encoding |

### CSN Effects (Relative Preservation)

| Study | CSN Finding |
|-------|-------------|
| Spontaneous Activity | No change in firing rate or patterns |
| Muscle Stretch | Relatively preserved responses |
| Active Movement | 21% reduction in movement-related activity (less than PTNs) |

### Consistent Themes Across Studies

1. **PTN Selective Vulnerability**: PTNs show greater dysfunction than CSNs across all paradigms
2. **Hypoactivation**: Reduced activity levels, not hyperactivity
3. **Degraded Selectivity**: Compromised directional tuning and kinematic encoding
4. **Preserved Temporal Structure**: Timing of responses maintained despite amplitude changes
5. **Beta Rhythmicity**: Abnormal oscillatory activity in PTNs

## Relevance for NWB Conversion

### Common Data Streams
- Single-unit spike times (all studies)
- Neuron type classification (PTN vs CSN)
- Pre- vs post-MPTP condition labels
- Subject identifiers (Monkey V, Monkey L)

### Study-Specific Data Streams

| Study | Additional Data |
|-------|-----------------|
| **Pyramidal Tract Neurons** | Extended baseline recordings, no task events |
| **Muscle Stretch** | Perturbation times, EMG data, kinematic data |
| **Active Movement** | Task events (go cue, movement onset), kinematics (position, velocity, acceleration), trial outcomes |

### Trial Structure Differences

| Study | Trial Structure |
|-------|-----------------|
| **Pyramidal Tract Neurons** | Continuous recording epochs, no discrete trials |
| **Muscle Stretch** | Discrete perturbation trials with randomized timing |
| **Active Movement** | Discrete movement trials with defined task phases |

## Methodological Consistency

The three studies demonstrate a systematic, comprehensive approach to understanding MPTP effects on M1:

1. **Same animals** - Allows direct comparison across studies
2. **Same MPTP protocol** - Consistent lesion across studies
3. **Same cell-type identification** - Comparable PTN/CSN classification
4. **Complementary paradigms** - Rest, passive movement, active movement
5. **Same recording methods** - Technical consistency

This methodological consistency makes the dataset particularly valuable for understanding the full scope of cortical dysfunction in parkinsonism, from resting state abnormalities to compromised proprioceptive and motor processing.
