# Primary Motor Cortex of the Parkinsonian Monkey: Altered Encoding of Active Movement

**Citation**: Pasquereau B, DeLong MR, Turner RS (2016) Primary motor cortex of the parkinsonian monkey: altered encoding of active movement. *Brain* 139:127-143.

## Overview

This study investigated how MPTP-induced parkinsonism affects the encoding of active movement kinematics in primary motor cortex (M1) neurons, with particular focus on pyramidal tract neurons (PTNs) and corticostriatal neurons (CSNs). Using generalized linear models (GLMs), the authors uniquely dissociated kinematic encoding from movement-independent "residual" activity, enabling direct testing of hypotheses about M1 dysfunction while controlling for secondary effects of bradykinesia.

## Introduction and Context

Primary motor cortex (M1) dysfunction has long been recognized as central to Parkinson's disease motor impairments. As the principal source of corticospinal projections and a key target of basal ganglia-thalamocortical connections, M1 represents a critical site where abnormal basal ganglia activity may be translated into aberrant motor commands, resulting in characteristic parkinsonian symptoms like akinesia, bradykinesia, and hypometria.

### Study Hypotheses

The research tested three competing hypotheses about M1 dysfunction in parkinsonism:

1. **Hypoactivation**: M1 receives reduced excitatory drive, generating deficient motor commands due to excessive basal ganglia inhibition or impaired movement scaling/motivation.

2. **Loss of Functional Specificity**: Degraded selectivity throughout basal ganglia-thalamocortical circuits leads to co-activation of competing motor programs in M1.

3. **Abnormal Timing**: Motor command timing in M1 becomes altered or temporally dispersed.

## Animals and MPTP Treatment

### Subjects
- Two female rhesus macaques (*Macaca mulatta*)
- **Monkey V**: 4.8 kg body weight
- **Monkey L**: 6.0 kg body weight

### MPTP Administration Protocol
- **Method**: Unilateral intracarotid injection
- **Dose**: 0.5 mg/kg MPTP-HCl dissolved in saline
- **Target**: Left internal carotid artery (affecting right hemisphere)
- **Rationale**: Unilateral injection induces stable, moderate parkinsonism suitable for longitudinal behavioral and neurophysiological studies

### Parkinsonian Symptoms Observed
- Moderate contralateral (right-sided) hemiparkinsonian symptoms
- Bradykinesia (slowness of movement)
- Hypometria (reduced movement amplitude)
- Increased movement duration
- Decreased peak velocity
- Symptoms stable throughout post-MPTP recording period

## Neuron Subtypes

The study focused on two distinct classes of layer 5 pyramidal neurons, identified through antidromic stimulation:

### Pyramidal Tract Neurons (PTNs)
- **Location**: Layer 5b of primary motor cortex
- **Projection Target**: Spinal cord via corticospinal tract (pyramidal tract)
- **Function**: Primary efferent pathway conveying motor commands from cortex to segmental motor centers
- **Identification Method**: Antidromic activation from stimulating electrodes in the cerebral peduncle
- **Antidromic Latency**: 0.6-2.5 ms (indicating large, fast-conducting axons)

### Corticostriatal Neurons (CSNs)
- **Location**: Layer 5 of primary motor cortex
- **Projection Target**: Posterolateral striatum (putamen)
- **Function**: Cortical input to basal ganglia circuits; intratelencephalic-type neurons
- **Identification Method**: Antidromic activation from stimulating electrodes in the posterolateral striatum
- **Antidromic Latency**: 2.0-20 ms (smaller, slower-conducting axons than PTNs)

### Antidromic Identification Criteria
Neurons were classified as antidromically activated based on:
1. Fixed latency responses to stimulation
2. Ability to follow high-frequency (>200 Hz) stimulation
3. Collision test: Spontaneous spikes occurring within the antidromic latency window blocked the antidromic response

## Experimental Protocol

### Visuomotor Step-Tracking Task

Monkeys controlled a cursor on a video display by flexing or extending their elbow within a manipulandum (rotating handle coupled to a torque motor). The task sequence:

1. **CENTER HOLD** (variable 1-2 seconds)
   - Monkey maintains cursor position within central target zone
   - Hold period randomized to prevent anticipatory movements

2. **GO CUE / TARGET APPEARANCE**
   - Peripheral target appears (flexion or extension direction)
   - Monkey initiates rapid ballistic movement to capture target

3. **MOVEMENT PHASE**
   - Step-tracking movement toward peripheral target
   - Kinematics recorded: position, velocity, acceleration

4. **TARGET HOLD** (variable duration)
   - Cursor must be maintained within peripheral target zone

5. **REWARD**
   - Liquid reward delivered upon successful target capture and hold

### Kinematic Measurements
- **Joint position**: Degrees of elbow flexion/extension
- **Velocity**: First derivative of position (degrees/second)
- **Acceleration**: Second derivative of position (degrees/second^2)
- **Reaction time**: Time from GO cue to movement onset
- **Movement duration**: Time from movement onset to target acquisition

## Data Collection

### Neuron Sample Sizes

| Condition | PTNs | CSNs | Total |
|-----------|------|------|-------|
| Pre-MPTP  | 93   | 73   | 166   |
| Post-MPTP | 60   | 53   | 113   |
| **Total** | **153** | **126** | **279** |

### Recording Methods
- Single-unit extracellular recordings using glass-coated tungsten microelectrodes
- Electrodes advanced through chronic recording chamber implanted over M1
- Spike sorting performed offline to isolate single-unit activity
- Recording sessions: Multiple sessions per condition spanning weeks-months

## Analysis Methods

### Generalized Linear Model (GLM) for Kinematic Encoding

The GLM decomposed neural activity into kinematic-encoding and movement-independent components:

**Model Formula:**
```
E(SC_i) = exp(beta_1*Dir_i + beta_2*Pos_i + beta_3*Speed_i + beta_4*Acc_i + beta_5*RT_i)
```

Where:
- **SC_i**: Spike count in trial i
- **Dir_i**: Movement direction (flexion vs extension)
- **Pos_i**: Peak position reached
- **Speed_i**: Peak movement speed
- **Acc_i**: Peak acceleration
- **RT_i**: Reaction time

### Key Analysis Variables
- **Kinematic Sensitivity**: Goodness-of-fit of the GLM (pseudo-R^2 values)
- **Residual Activity**: Movement-independent firing rate after accounting for kinematics
- **Directional Tuning**: Preference for flexion vs extension movements
- **Temporal Dynamics**: Peri-movement spike density functions aligned to movement onset

### Statistical Comparisons
- Two-sample comparisons (pre- vs post-MPTP)
- Bootstrap resampling for confidence intervals
- Receiver Operating Characteristic (ROC) analysis for effect sizes

## Key Findings

### Movement Encoding Deficits

#### Kinematic Sensitivity Reduction
- **29% reduction** in kinematic encoding strength after MPTP
- PTNs showed greater encoding deficits than CSNs
- Reduced ability to accurately predict movement parameters from neural activity

#### Movement-Related Activity Changes
- **36% hypoactivation** of movement-related neural activity
- **50% reduction** in PTN movement-related activity specifically
- **43% reduction** in pre-movement responses
- Preserved but reduced CSN movement-related activity

### Cell-Type Specific Effects

| Measure | PTN Effect | CSN Effect |
|---------|------------|------------|
| Kinematic sensitivity | 37% reduction | 18% reduction |
| Movement-related activity | 50% reduction | 21% reduction |
| Pre-movement responses | 53% reduction | 31% reduction |
| Directional tuning | Severely degraded | Moderately preserved |

### Kinematic Parameter Encoding
- Reduced encoding of velocity, acceleration, and direction
- Degraded temporal precision of movement-related responses
- Compromised population-level movement representation
- Speed sensitivity particularly affected

### Temporal Dynamics
- Delayed onset of movement-related activity
- Prolonged movement-related responses
- Reduced peak firing rates around movement onset
- Maintained but weakened post-movement responses

### Support for Hypoactivation Hypothesis
Results most strongly supported the **hypoactivation hypothesis**:
- Consistent reductions in firing rates across task phases
- Deficient kinematic encoding not explained by bradykinesia alone
- Loss of movement-related activity independent of movement slowing

### Evidence Against Alternative Hypotheses
- **Loss of specificity**: Directional tuning was reduced but not eliminated; neurons remained selective
- **Abnormal timing**: Temporal structure of responses preserved; no evidence of temporal dispersion

## Clinical Relevance

### Neural Basis of Parkinsonian Motor Symptoms
- **Bradykinesia**: Reduced PTN activity leads to deficient motor commands reaching spinal cord
- **Hypometria**: Compromised kinematic encoding impairs scaling of movement amplitude
- **Movement Initiation Deficits**: Pre-movement hypoactivation contributes to akinesia

### Therapeutic Implications
- Results suggest that treatments restoring normal M1 activity levels could improve motor function
- Deep brain stimulation effects may partly operate through normalizing cortical activity
- Targeted cortical stimulation may represent a therapeutic avenue

## Significance

This research establishes that parkinsonian pathology significantly impairs the cortical encoding of movement parameters, particularly in pyramidal tract neurons. The findings demonstrate that:

1. **Cortical dysfunction is primary, not secondary**: Encoding deficits persist after controlling for bradykinesia
2. **Cell-type specificity**: PTNs are more vulnerable than CSNs to parkinsonian pathology
3. **Hypoactivation is the dominant mechanism**: Consistent with reduced excitatory drive to M1
4. **Corticospinal pathway is preferentially affected**: Direct motor commands to spinal cord are compromised

These insights complement our understanding of basal ganglia involvement in Parkinson's disease by demonstrating significant cortical contributions to the characteristic motor symptoms.
