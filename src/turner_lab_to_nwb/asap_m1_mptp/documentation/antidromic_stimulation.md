# Antidromic Stimulation Protocol

## Overview

Antidromic stimulation is an electrophysiological technique used to identify and classify neurons based on their axonal projection targets. This document explains the method, its application in the Turner lab MPTP studies, and the analysis procedures used to classify pyramidal tract neurons (PTNs) and corticostriatal neurons (CSNs).

**Related documentation:**
- [Electrodes in Experiment](electrodes_in_experiment.md) - Recording vs stimulation electrode systems
- [Stimulation Events](stimulation_events.md) - In-trial stimulation for isolation monitoring
- [NWB Conversion Strategy](nwb_conversion.md) - How antidromic data maps to NWB format

---

## Part 1: Fundamentals of Antidromic Stimulation

### What is Antidromic Conduction?

The term "antidromic" derives from Greek roots meaning "running backwards." It describes the artificial propagation of action potentials in the direction opposite to their normal (orthodromic) flow.

**Normal (orthodromic) conduction:**
```
Cell body (soma) --> Axon --> Synaptic terminal --> Target structure
```

**Antidromic conduction:**
```
Stimulation at target <-- Action potential travels backwards <-- Recorded at soma
```

### The Biophysical Basis

Axons are bidirectional conductors. While synapses transmit signals in only one direction (presynaptic to postsynaptic), the axon membrane itself can propagate action potentials in either direction. When electrical stimulation is delivered at a point along an axon:

1. The stimulus depolarizes the axon membrane locally
2. If depolarization exceeds threshold, an action potential initiates
3. This action potential propagates in both directions from the stimulation point
4. The action potential traveling toward the soma (antidromic) can be recorded at the cell body

### Why Use Antidromic Stimulation?

The fundamental insight is that if you stimulate at a known anatomical location and record a response in a neuron, **that neuron must have an axon projecting to the stimulation site**. This allows definitive classification of neurons by their output targets without anatomical tracing of individual axons.

---

## Part 2: Criteria for Antidromic Identification

A critical challenge is distinguishing true antidromic responses (direct axonal activation) from orthodromic responses (where stimulation activates other neurons that synaptically drive the recorded neuron). Three classical criteria are used:

### Criterion 1: Fixed Latency

**Requirement:** Response latency must show <0.2 ms variation across repeated stimulations.

**Rationale:**
- Antidromic responses have extremely consistent latencies because direct axonal conduction is deterministic
- The same physical distance is traversed each time
- No synaptic delays (which are inherently variable) are involved

**Contrast with synaptic activation:**
- Synaptic transmission has inherent variability (vesicle release probability, receptor binding kinetics)
- Polysynaptic pathways accumulate timing jitter
- Latencies typically vary by >0.5 ms

### Criterion 2: High-Frequency Following

**Requirement:** Neurons must reliably follow stimulation at >200 Hz (typically tested with 2-4 pulses at 200 Hz, i.e., 5 ms inter-pulse interval).

**Rationale:**
- Axonal refractory periods are short (~1-2 ms for large axons)
- No synaptic fatigue occurs with direct axonal activation
- Each stimulus independently triggers a response

**Contrast with synaptic activation:**
- Synaptic vesicle pools deplete rapidly at high frequencies
- Postsynaptic receptor desensitization occurs
- Synaptic transmission typically fails above 50-100 Hz

### Criterion 3: Collision Test

**Requirement:** Spontaneous spikes occurring within a critical time window before stimulation must block the antidromic response.

**Rationale:**
This criterion exploits the fact that action potentials cannot pass through each other when traveling in opposite directions on the same axon:

1. A spontaneous spike occurs and travels down the axon (orthodromic direction)
2. Stimulation is delivered before that spike clears the axon
3. The antidromic spike traveling up collides with the orthodromic spike
4. Both spikes annihilate at the collision point
5. No antidromic response is recorded at the soma

**Critical window calculation:**
```
Critical window = Antidromic latency + Axonal refractory period (~1-2 ms)
```

For a neuron with 2.0 ms antidromic latency, the critical window is approximately 3-4 ms. If a spontaneous spike occurs within this window before stimulation, the antidromic response should be blocked.

**Why this is definitive:** Synaptic activation cannot be blocked by prior activity in the recorded neuron's own axon. Only direct axonal activation exhibits the collision phenomenon.

---

## Part 3: Application in the Turner Lab Studies

### The Scientific Question

The Turner lab investigated how MPTP-induced parkinsonism differentially affects cortical neurons based on their output targets. This required distinguishing two major classes of layer 5 pyramidal neurons in primary motor cortex (M1):

### Pyramidal Tract Neurons (PTNs)

**Anatomical definition:** Large layer 5b pyramidal neurons whose axons descend through the cerebral peduncle to the spinal cord via the corticospinal (pyramidal) tract.

**Functional role:** Primary "output" neurons of motor cortex that send motor commands directly to spinal motor circuits, ultimately controlling muscle activation.

**Antidromic identification parameters:**

| Parameter | Value |
|-----------|-------|
| Stimulation site | Cerebral peduncle (prepontine, arm-responsive portion) |
| Stimulation current | 100-400 uA |
| Pulse duration | 0.2 ms biphasic pulses |
| Antidromic latency | 0.6-2.5 ms |

**Interpretation:** Short latencies (0.6-2.5 ms) indicate large-diameter, fast-conducting axons (~20-50 m/s conduction velocity), consistent with corticospinal neurons.

### Corticostriatal Neurons (CSNs)

**Anatomical definition:** Intratelencephalic-type layer 5 pyramidal neurons projecting to the striatum (specifically, the posterolateral putamen), providing cortical input to basal ganglia circuits.

**Functional role:** Provide excitatory glutamatergic input to the basal ganglia, contributing to the cortico-basal ganglia-thalamocortical loop involved in motor control and action selection.

**Antidromic identification parameters:**

| Parameter | Value |
|-----------|-------|
| Stimulation site | Posterolateral putamen (3 electrodes between planes HC A8-14) |
| Stimulation current | 100-600 uA |
| Pulse duration | 0.2 ms biphasic pulses |
| Antidromic latency | 2.0-20 ms |

**Interpretation:** Longer latencies (2-20 ms) indicate smaller-diameter, slower-conducting axons than PTNs, consistent with intratelencephalic-type pyramidal neurons.

### Electrode Implantation

The Turner lab used chronically implanted "floating" stimulating electrodes:

**Mapping phase:**
- Arm-related areas of putamen and cerebral peduncle identified through sensorimotor examination
- Sites verified by microstimulation effects (movement evoked at low currents)

**Electrode construction:**
- Custom-built electrodes: 2-3 Teflon-coated PtIr microwires (50 um diameter)
- Wires threaded through 30-gauge stainless steel cannula
- Wire tips staggered by 0.5 mm for depth coverage

**Implantation configuration:**
- 3 electrodes in posterolateral putamen (for CSN identification)
- 1 electrode in prepontine cerebral peduncle (for PTN identification)
- Additional electrodes in thalamus (VL) and subthalamic nucleus (STN) in some sessions

---

## Part 4: Testing Protocols

### Frequency Following Test

**Purpose:** Verify that the response follows high-frequency stimulation, which synaptic activation cannot achieve.

**Protocol:**
1. Deliver a train of 2-4 stimulation pulses at 200 Hz (5 ms inter-pulse interval)
2. Record the neural response to each pulse
3. Count the number of evoked responses

**Expected results:**
- **Antidromic:** Neuron responds to each pulse with a spike at the characteristic latency
- **Synaptic:** Responses fail or become inconsistent after the first 1-2 pulses

**Analysis:**
- Calculate following rate = (number of responses) / (number of stimulation pulses)
- Antidromic neurons should show following rates >80-90%
- Verify consistent latency across all pulses in the train

**Data identifier:** `TraceName = 'ff_n'` in MATLAB stimulation sweep structures

### Collision Test

**Purpose:** Definitively prove direct axonal connection by demonstrating that spontaneous spikes block the antidromic response.

**Protocol:**
1. Record a series of stimulation sweeps (50 ms each at 20 kHz)
2. For each sweep, determine whether a spontaneous spike occurred within the critical collision window before stimulation
3. Compare responses in "collision" trials vs "non-collision" trials

**Expected results:**
- **Non-collision trials:** Clear antidromic response at fixed latency
- **Collision trials:** No antidromic response (blocked by collision)

**Analysis approach:**
1. Align all sweeps to stimulation onset
2. Identify sweeps with spontaneous spikes in critical window
3. Overlay or average collision vs non-collision sweeps separately
4. Verify absence of antidromic response in collision trials

**Data identifier:** `TraceName = 'coll_n'` in MATLAB stimulation sweep structures

### Latency Measurement

**Measurement method:** Latency is measured from stimulation onset to the first inflection point (initial upward deflection) of the antidromic spike waveform.

**Why first inflection?** The first inflection represents the moment the action potential arrives at the recording site; the peak occurs later as the spike develops fully.

**Conduction velocity estimation:**
```
Velocity (m/s) = Distance (mm) / Latency (ms)
```

Example for a PTN with 1.5 ms latency and ~60 mm distance from M1 to peduncle:
```
Velocity = 60 mm / 1.5 ms = 40 m/s
```

---

## Part 5: Data Storage and NWB Representation

### MATLAB Source Data

Antidromic stimulation sweeps are stored in structures organized by stimulation site:

| Structure | Stimulation Site | Neuron Type |
|-----------|------------------|-------------|
| `StrStim` | Striatum (putamen) | CSN |
| `PedStim` | Cerebral peduncle | PTN |
| `ThalStim` | Thalamus | Rare |
| `STNStim` | Subthalamic nucleus | Rare |

**Sweep contents:**

| Field | Description |
|-------|-------------|
| `TraceName` | Test type: `'ff_n'` (frequency following), `'coll_n'` (collision) |
| `Curr` | Stimulation current delivered (uA) |
| `Unit` | Raw single-unit signal (50 ms at 20 kHz = 1000 samples) |
| `Time` | Timebase relative to shock delivery (ms) |

### Classification Results in Metadata

The metadata table (`ven_table.csv`) contains classification results:

| Column | Description | Values |
|--------|-------------|--------|
| `Antidrom` | Classification result | `'PED'` (PTN), `'STRI'` (CSN), `'THAL'`, `'NR'` (no response), `'NT'` (not tested), `'PED/STRI'` (dual) |
| `Latency` | Primary antidromic latency | milliseconds |
| `Threshold` | Current threshold for activation | microamperes |
| `LAT2` | Secondary site latency (if dual activation) | milliseconds |
| `Thresh2` | Secondary site threshold | microamperes |

### NWB Storage Locations

In converted NWB files, antidromic data appears in:

**Units table columns:**
- `neuron_projection_type`: Classification (`pyramidal_tract_neuron`, `corticostriatal_neuron`, `not_tested`, `no_response`)
- `antidromic_latency_ms`: Response latency
- `antidromic_threshold_uA`: Stimulation threshold
- `antidromic_stimulation_sites`: Sites tested

**Intervals table:**
- `nwbfile.intervals["AntidromicSweepsIntervals"]`: Sweep-level data including:
  - `stimulation_protocol`: `'FrequencyFollowing'` or `'Collision'`
  - `sweep_number`: Sequential sweep identifier
  - `unit_name`: Associated unit
  - `location`: Stimulation site
  - `stimulation_onset_time`: When stimulation was delivered
  - `response`: Link to response time series
  - `stimulation`: Link to stimulation time series

**Processing module:**
- `nwbfile.processing['antidromic_identification']`: Raw stimulation traces

---

## Part 6: Key Findings Enabled by Antidromic Identification

### Neuron Samples Across Studies

| Study | Year | Journal | PTNs | CSNs | Total |
|-------|------|---------|------|------|-------|
| Spontaneous Activity | 2011 | Cerebral Cortex | 123 | 98 | 221 |
| Muscle Stretch | 2013 | Frontiers Syst Neurosci | 115 | 90 | 205 |
| Active Movement | 2016 | Brain | 153 | 126 | 279 |

### Differential Vulnerability Pattern

Antidromic identification revealed that MPTP-induced parkinsonism **selectively affects PTNs while relatively sparing CSNs**:

**PTN effects (vulnerable):**

| Study | Finding |
|-------|---------|
| Spontaneous Activity | 27% reduction in firing rate; increased burstiness; enhanced beta (14-32 Hz) rhythmicity |
| Muscle Stretch | Degraded directional selectivity; no enhancement of stretch responses |
| Active Movement | 50% reduction in movement-related activity; 37% reduction in kinematic encoding |

**CSN effects (preserved):**

| Study | Finding |
|-------|---------|
| Spontaneous Activity | No change in firing rate or patterns |
| Muscle Stretch | Relatively preserved responses |
| Active Movement | 21% reduction (less severe than PTNs) |

### Implications

Without antidromic identification, these cell-type specific effects would have been masked in a heterogeneous population of "M1 neurons." The technique revealed:

1. **The corticospinal output pathway (PTNs) is preferentially impaired** - directly explaining bradykinesia through reduced motor commands reaching spinal cord

2. **The corticostriatal feedback pathway (CSNs) is relatively spared** - basal ganglia continue to receive cortical input while output from cortex to spinal cord is compromised

3. **Parkinsonism is not general cortical hypofunction** - it selectively affects neurons based on their circuit position

---

## Part 7: Visualization and Analysis Example

### Frequency Following Analysis

A typical frequency following analysis involves:

1. **Load sweep data** from the intervals table
2. **Extract timing information:**
   - Stimulation onset time
   - Known antidromic latency for the unit
3. **Detect stimulation pulses** by finding peaks in the stimulation current trace
4. **Calculate expected response times:**
   ```python
   expected_response_times = stimulation_peak_times + antidromic_latency
   ```
5. **Visualize alignment** of actual responses with expected times
6. **Count successful following** across all pulses in the train

### What to Look For

**Successful frequency following:**
- Action potentials appear at each expected response time
- Latency is consistent across all pulses (fixed latency criterion)
- Following rate >80-90%

**Failed frequency following (suggests synaptic, not antidromic):**
- Responses to later pulses in train are absent or delayed
- Latency varies between pulses
- Following rate <50%

### Collision Test Analysis

1. **Identify collision trials:** Sweeps where spontaneous spikes occurred within the critical window before stimulation
2. **Separate sweeps:** Collision trials vs non-collision trials
3. **Compare responses:**
   - Non-collision: Clear antidromic spike at expected latency
   - Collision: Absent antidromic response
4. **Verify:** Presence of blocking confirms antidromic (not synaptic) activation

---

## References

### Primary Methods Papers

- Turner RS, DeLong MR (2000) Corticostriatal activity in primary motor cortex of the macaque. *J Neurosci* 20:7096-7108. [Original electrode implantation and identification procedures]

- Fuller JH, Schlag JD (1976) Determination of antidromic excitation by the collision test: problems of interpretation. *Brain Res* 112:283-298. [Collision test methodology]

### Turner Lab MPTP Studies

- Pasquereau B, Turner RS (2011) Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons. *Cerebral Cortex* 21:1362-1378.

- Pasquereau B, Turner RS (2013) Primary motor cortex of the parkinsonian monkey: altered neuronal responses to muscle stretch. *Front Syst Neurosci* 7:98.

- Pasquereau B, DeLong MR, Turner RS (2016) Primary motor cortex of the parkinsonian monkey: altered encoding of active movement. *Brain* 139:127-143.
