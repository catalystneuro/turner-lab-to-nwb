# Anatomical Coordinate Localization

This document describes the electrode positioning system used in the Turner Lab M1 MPTP dataset, including how coordinates are extracted from source data, their meaning, and how they are stored in NWB format.

**Related documentation:**
- [Electrodes in Experiment](electrodes_in_experiment.md) - Recording vs stimulation electrodes
- [Sensory Receptive Field Testing](sensory_receptive_field_testing.md) - How recording sites were verified
- [File Structure](../assets/data_exploration/file_structure.md) - Metadata table column definitions

## Overview

The Turner Lab dataset uses a **chamber-relative coordinate system** rather than absolute stereotactic atlas coordinates. This approach provides sub-millimeter precision for daily electrode positioning while acknowledging that these coordinates are specific to each animal's implanted recording chamber.

## Coordinate System Definition

### Reference Frame

| Property | Description |
|----------|-------------|
| **Origin** | Chamber center/reference point |
| **Chamber type** | Cylindrical stainless steel |
| **Chamber orientation** | 35 degrees to coronal plane |
| **Target region** | Left primary motor cortex (M1), arm representation |
| **Hemisphere** | Left (contralateral to task-performing right arm) |

### Coordinate Axes

| Axis | Field Name | Direction Convention | Observed Range |
|------|------------|---------------------|----------------|
| **Anterior-Posterior** | `A_P` | Positive = anterior | -7 to +6 mm |
| **Medial-Lateral** | `M_L` | Positive = lateral | -6 to +2 mm |
| **Depth** | `Depth` | Positive = deeper (ventral) | 8.4 to 27.6 mm |

### Anatomical Context

- **Target cortical area**: Primary motor cortex (M1), Brodmann area 4, arm representation
- **Cortical layer**: Layer 5 (pyramidal neurons - PTNs and CSNs)
- **Anatomical landmark**: Within 3mm of anterior bank of central sulcus
- **Functional verification**: Electrode locations confirmed via intracortical microstimulation (ICMS) at current of 40 microamps or less, 10 pulses at 300Hz

## Data Extraction

### Source Data Location

Coordinates are extracted from the metadata table (`ven_table.csv`, converted from `VenTable.mat`):

```python
# From conversion_script.py
session_info_dict = {
    "session_info": {
        "A_P": primary_unit["A_P"],     # Anterior-Posterior position (mm)
        "M_L": primary_unit["M_L"],     # Medial-Lateral position (mm)
        "Depth": primary_unit["Depth"], # Insertion depth (mm)
    },
    ...
}
```

### File Naming Convention

The MATLAB filename encodes spatial sampling information:

```
Format: v[Site][Session].N.mat
Example: v1401.1.mat

- v     : Monkey identifier (Ven)
- 14    : Recording site index (penetration location 14)
- 01    : Session index (first depth at this site)
- .1    : Unit number within session
```

The site and session indices are extracted in the conversion code:

```python
# From electrodes_interface.py (lines 208-219)
base_name = self.base_file_path.stem.split(".")[0]  # e.g., "v5811"
recording_site_index = int(base_name[1:3])    # Characters 2-3 (site index)
recording_session_index = int(base_name[3:5]) # Characters 4-5 (session index)
```

## NWB Storage Format

### Standard NWB Electrode Coordinates

The standard NWB `x`, `y`, `z` coordinates are set to `NaN` because:
- Only chamber-relative coordinates are available
- No transformation to standard brain atlas coordinates exists
- Preserving chamber-relative precision is more scientifically accurate

```python
nwbfile.add_electrode(
    x=float("nan"),  # Unknown global coordinates
    y=float("nan"),
    z=float("nan"),
    ...
)
```

### Custom NWB Columns

Chamber-relative coordinates are stored in custom electrode table columns:

| Column Name | Description | Recording Electrode | Stimulation Electrode |
|-------------|-------------|--------------------|-----------------------|
| `chamber_grid_ap_mm` | A-P position relative to chamber center (mm) | From metadata | NaN |
| `chamber_grid_ml_mm` | M-L position relative to chamber center (mm) | From metadata | NaN |
| `chamber_insertion_depth_mm` | Depth from chamber reference (mm) | From metadata | NaN |
| `recording_site_index` | Chamber penetration site identifier | From filename | -1 |
| `recording_session_index` | Depth sampling session identifier | From filename | -1 |

### Accessing Coordinates in NWB

```python
import pynwb

# Load NWB file
with pynwb.NWBHDF5IO("session.nwb", "r") as io:
    nwbfile = io.read()

    # Access electrode table
    electrodes = nwbfile.electrodes

    # Get chamber coordinates for recording electrode (index 0)
    ap = electrodes["chamber_grid_ap_mm"][0]
    ml = electrodes["chamber_grid_ml_mm"][0]
    depth = electrodes["chamber_insertion_depth_mm"][0]

    # Get site/session indices
    site_idx = electrodes["recording_site_index"][0]
    session_idx = electrodes["recording_session_index"][0]

    print(f"Position: A-P={ap}mm, M-L={ml}mm, Depth={depth}mm")
    print(f"Site {site_idx}, Session {session_idx}")
```

## Scientific Use Cases

### 1. Within-Subject Spatial Analysis

Compare neural properties across recording locations within the same animal:

```python
# Example: Group neurons by cortical location
import pandas as pd

# Build dataframe from multiple sessions
sessions_data = []
for nwb_file in nwb_files:
    electrodes = nwb_file.electrodes
    sessions_data.append({
        "session_id": nwb_file.session_id,
        "A_P": electrodes["chamber_grid_ap_mm"][0],
        "M_L": electrodes["chamber_grid_ml_mm"][0],
        "Depth": electrodes["chamber_insertion_depth_mm"][0],
    })

df = pd.DataFrame(sessions_data)
# Analyze spatial distribution of neural properties
```

### 2. Depth-Dependent Properties

Examine how neural properties vary with cortical depth:

```python
# Compare superficial vs deep recordings
superficial = df[df["Depth"] < 15.0]  # Shallower recordings
deep = df[df["Depth"] >= 15.0]        # Deeper recordings (likely layer 5)
```

### 3. Cortical Mapping

Reconstruct electrode penetration trajectories:

```python
# Group by recording site to get depth profiles
for site_idx, site_data in df.groupby("recording_site_index"):
    depths = site_data.sort_values("Depth")
    # Analyze properties across cortical layers at this A-P/M-L location
```

## Important Limitations

### Not Standard Atlas Coordinates

These coordinates do NOT directly correspond to:
- Horsley-Clarke stereotaxic coordinates
- MNI Macaque Atlas coordinates
- AC-PC based coordinate systems

They represent positions within a **subject-specific coordinate frame** defined by the implanted recording chamber.

### Cross-Study Comparisons

For cross-study or cross-animal analysis:
- Initial chamber placement used stereotaxic atlas guidance
- Each animal's chamber position is unique
- Transformation to standard atlas would require:
  - Individual MRI/CT imaging
  - Registration to standard template
  - Coordinate transformation matrices

### Stimulation Electrode Coordinates

Stimulation electrodes (cerebral peduncle, putamen, thalamus) have:
- `NaN` for all chamber grid coordinates
- `-1` for site/session indices
- These electrodes were chronically implanted at fixed locations
- Positions verified histologically but not tracked in chamber coordinates

## Standard Macaque Brain Atlases

This section describes popular macaque brain atlases that could theoretically be used for cross-study comparisons, though mapping from chamber-relative coordinates would require additional registration data not available in this dataset.

### Horsley-Clarke Stereotaxic System

The **Horsley-Clarke** coordinate system is the standard reference frame for macaque neurophysiology:

- **Origin**: Ear bar zero (EBZ) - midpoint of the interaural line
- **Axes**:
  - A-P: Anterior-Posterior (positive = anterior)
  - M-L: Medial-Lateral (positive = lateral, from midline)
  - D-V: Dorsal-Ventral (positive = dorsal, from horizontal plane through EBZ)
- **Horizontal plane**: Defined by ear bars and infraorbital ridge

This is the coordinate system used during surgical chamber implantation to position the chamber over M1.

### Popular Macaque Atlases

| Atlas | Type | Resolution | Key Features |
|-------|------|------------|--------------|
| **NMT v2** (NIMH Macaque Template) | Population MRI template | 0.25-0.5 mm | Symmetric and asymmetric versions; Horsley-Clarke aligned; integrated with AFNI |
| **CHARM** (Cortical Hierarchy Atlas of the Rhesus Macaque) | Cortical parcellation | Matched to NMT | Hierarchical parcellation with multiple granularity levels |
| **SARM** (Subcortical Atlas of the Rhesus Macaque) | Subcortical parcellation | Matched to NMT | 6 hierarchical levels; nomenclature from RMBSC4 |
| **MEBRAINS 1.0** | Population T1/T2 template | High-res | 10-subject average; multi-modal; Horsley-Clarke aligned (2024) |
| **D99** | Single-subject MRI | 0.5 mm | Widely used; available on Scalable Brain Atlas |
| **RMBSC4** (Rhesus Monkey Brain in Stereotaxic Coordinates) | Histological atlas | Section-based | Gold standard for stereotaxic coordinates; 4th edition |

### Atlas Resources

**NIMH Macaque Template (NMT v2) and CHARM/SARM:**
- https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/nonhuman/macaque_tempatl/main_toc.html
- Integrated with AFNI's `@animal_warper` for registration

**MEBRAINS:**
- https://www.neuroconnlab.de/mebrains/
- Recent (2024) population-based template

**Scalable Brain Atlas:**
- https://scalablebrainatlas.incf.org/macaque/
- Web-based viewer for multiple macaque atlases

**Brainglobe Atlas API:**
- https://brainglobe.info/documentation/brainglobe-atlasapi/
- Python API for programmatic atlas access
- Note: As of 2025, no macaque atlases are included; only mouse, rat, human, and other species

### Mapping Chamber Coordinates to Standard Atlas

To transform chamber-relative coordinates to standard Horsley-Clarke or atlas coordinates, you would need:

1. **Surgical coordinates**: Chamber center position in stereotaxic frame (A-P, M-L, D-V from EBZ)
2. **Chamber orientation**: Rotation angles (35 degrees coronal in this dataset)
3. **Individual anatomy**: MRI/CT scan for subject-specific registration

**Transformation (conceptual):**

```
Atlas_coords = T_rotation @ Chamber_coords + T_translation

Where:
- T_rotation: 3x3 rotation matrix (35-degree coronal angle)
- T_translation: Chamber center position in stereotaxic space
- Chamber_coords: [A_P, M_L, Depth] from this dataset
```

**Current limitation**: The surgical stereotaxic readings for chamber placement are not available in this dataset, preventing precise atlas registration. The chamber-relative coordinates remain the most accurate representation of recording positions.

### Future Integration Possibilities

If individual MRI data and surgical coordinates become available:

1. **Register individual MRI to NMT v2** using AFNI's `@animal_warper`
2. **Identify chamber position** on individual MRI
3. **Compute transformation matrix** from chamber to NMT space
4. **Apply to all recording coordinates** for atlas-aligned positions
5. **Query brain regions** using CHARM (cortex) or SARM (subcortical)

## Related Files

| File | Description |
|------|-------------|
| [electrodes_interface.py](../../interfaces/electrodes_interface.py) | NWB electrode configuration implementation |
| [conversion_notes.md](../../conversion_notes.md) | Full coordinate system documentation |
| [file_structure.md](../assets/data_exploration/file_structure.md) | MATLAB metadata table structure |

## References

Surgical implantation and coordinate system details from the published papers:

> After training, each monkey was prepared for recording by aseptic surgery under isoflurane inhalation anaesthesia. A cylindrical stainless steel chamber was implanted with stereotaxic guidance over a burr hole allowing access to the arm-related regions of the left M1 and the putamen. The chamber was oriented parallel to the coronal plane at an angle of 35 degrees so that electrode penetrations were orthogonal to the cortical surface.

See [Paper Summaries](../assets/papers_summary_and_notes/) for full methodology details.
