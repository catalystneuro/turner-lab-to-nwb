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
| **Anterior-Posterior** | `chamber_grid_ap_mm` | Positive = posterior | -7 to 0 mm |
| **Medial-Lateral** | `chamber_grid_ml_mm` | Positive = right | -6 to -2 mm |
| **Depth** | `Depth` | Positive = deeper (ventral) | 8.4 to 27.6 mm |

### Anatomical Context

- **Target cortical area**: Primary motor cortex (M1), Brodmann area 4, arm representation
- **Cortical layer**: Layer 5 (pyramidal neurons - PTNs and CSNs)
- **Anatomical landmark**: Within 3mm of anterior bank of central sulcus
- **Functional verification**: Electrode locations confirmed via intracortical microstimulation (ICMS) at current of 40 microamps or less, 10 pulses at 300Hz

### Chamber Geometry and the 35-Degree Tilt

The recording chamber is tilted 35 degrees from vertical in the coronal plane so that electrode penetrations enter orthogonal to the cortical surface of M1 on the lateral convexity. This tilt couples the chamber's depth and medial-lateral axes in atlas space.

```
    CORONAL VIEW (looking from anterior, left hemisphere)

                           midline
                              |
         dorsal               |
           ^                  |
           |                  |
           |        chamber   |
           |        center    |
           |          :  \    |
           |          :   \   |       cortical
           |          :    \  |       surface
           |          :  35 \ |      .........
           |          :deg   \|  ...          ..
           |          :     ..\               ..
           |          :  ..   | \             .
           |          :..     |  \  electrode .
           |        ..        |   \ track     .
           |     ..           |    \          .
           |   . gray matter  |     \  F1     .
           |  .               |      * tip    .
           | .                |       .       .
           |  .               |               .
           |   ..   white matter   ..........
           |     .................
           |                  |
           +------------------+--------> lateral
                              |
                           midline

    The electrode enters from the lateral surface at 35 degrees
    from vertical. As it advances deeper:
      - it moves ventrally (S decreases)       ~0.74 mm per mm depth
      - it moves medially  (R toward midline)  ~0.68 mm per mm depth
    The AP axis of the chamber is aligned with the brain's
    anterior-posterior axis (no tilt in the sagittal plane):
      - AP_chamber maps 1:1 to the A axis in atlas space
```

This geometry explains several features of the data:

1. **Chamber AP maps perfectly to the atlas Anterior axis** (correlation r = 1.000, slope = 1.0 mm/mm). There is no sagittal tilt.
2. **Chamber Depth couples S and R in atlas space**. Going 1 mm deeper moves the electrode tip ~0.74 mm ventrally and ~0.68 mm medially. This matches the 35-degree angle: cos(35) = 0.82 and sin(35) = 0.57 (the measured slopes differ slightly due to cortical curvature).
3. **Chamber ML couples R and S in atlas space**. Moving 1 mm laterally on the chamber grid shifts the electrode entry point on the cortical surface, coupling both axes.

As a consequence, for the most posterior chamber positions (AP = -1 to 0, i.e., closest to chamber center), the electrode enters through the posterior bank of the central sulcus (somatosensory cortex: areas 1-2, then 3a/b) and as it goes deeper it crosses the fundus of the sulcus into the anterior bank (motor cortex: F1). At more anterior chamber positions (AP = -7 to -5), the electrode enters motor cortex directly.

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

## NWB Storage Format

### Standard NWB Electrode Coordinates

The standard NWB `x`, `y`, `z` coordinates are populated with D99 atlas coordinates converted to the NWB PIR convention (Posterior-Inferior-Right) in microns:
- `x` = `-A_P_acx * 1000` (+posterior, microns). Flipped sign: ACx +anterior becomes NWB +posterior.
- `y` = `-Depth_acx * 1000` (+inferior, microns). ACx Depth_acx is +superior (dorsal), so sign is flipped for NWB +inferior.
- `z` = `-M_L_acx * 1000` (+right, microns). Flipped sign: left hemisphere +lateral becomes NWB +right (negative).

The coordinates in the `AnatomicalCoordinatesTable` are stored in the native D99 RAS orientation (see below). When acx coordinates are not available (e.g., for Monkey L, pending), `x`, `y`, `z` are set to `NaN`.

### D99 Atlas Coordinates (ndx-anatomical-localization)

Atlas coordinates are also stored using the `ndx-anatomical-localization` extension in the **native D99 RAS orientation** (Right-Anterior-Superior), so the values can be used directly for atlas lookups without additional coordinate transforms:

```python
# Accessing D99 atlas coordinates (RAS, mm, origin = anterior commissure)
localization = nwbfile.lab_meta_data["localization"]
coords_table = localization.anatomical_coordinates_tables["D99AtlasCoordinates"]
space = coords_table.space  # D99 Space object with origin, units, orientation="RAS"

r = coords_table["x"][0]  # +right (left hemisphere recordings are negative)
a = coords_table["y"][0]  # +anterior
s = coords_table["z"][0]  # +superior
brain_region = coords_table["brain_region"][0]
```

The `Localization` container includes:
- A `Space` object describing the D99 atlas (origin: anterior commissure, units: mm, orientation: RAS)
- An `AnatomicalCoordinatesTable` linking coordinates to the electrode table with brain region labels

### Custom NWB Columns

Chamber-relative coordinates are stored in custom electrode table columns:

| Column Name | Description | Units |
|-------------|-------------|-------|
| `chamber_grid_ap_mm` | A-P position relative to chamber center | mm (positive = posterior) |
| `chamber_grid_ml_mm` | M-L position relative to chamber center | mm (positive = right) |
| `chamber_insertion_depth_mm` | Depth from chamber reference point | mm (positive = deeper) |

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

    print(f"Position: A-P={ap}mm, M-L={ml}mm, Depth={depth}mm")
```

## Important Limitations

### Chamber Coordinates Are Subject-Specific

The chamber-relative coordinates (`chamber_grid_ap_mm`, `chamber_grid_ml_mm`, `chamber_insertion_depth_mm`) are positions within a subject-specific coordinate frame defined by the implanted recording chamber. They have been transformed to D99 atlas coordinates (see above), but the transformation is geometric, not imaging-based, so cross-subject registration uncertainty of 1-2 mm should be expected.

### D99 Atlas Coordinates Availability

D99 atlas coordinates are currently available for **Monkey V only**. When unavailable (e.g., Monkey L, pending), the standard NWB `x`, `y`, `z` fields are set to `NaN` and the `AnatomicalCoordinatesTable` is omitted. See [Chamber-to-Atlas Transformation](#chamber-to-atlas-transformation-acx-coordinates) for how these coordinates were computed.

### Stimulation Electrodes

Stimulation electrodes (cerebral peduncle, putamen, thalamus) are represented as NWB devices rather than in the electrodes table:
- Chronically implanted at fixed locations during surgery
- Positions verified histologically but not tracked in chamber coordinates
- See `nwbfile.devices` for stimulation electrode descriptions

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
| **D99** | Single-subject MRI | 0.25 mm | AC origin; RAS orientation; used in this dataset (see below) |
| **RMBSC4** (Rhesus Monkey Brain in Stereotaxic Coordinates) | Histological atlas | Section-based | Gold standard for stereotaxic coordinates; 4th edition |

### D99 Atlas Coordinate System

The D99 v2.0 atlas (Saleem et al., 2012; updated Saleem et al., 2021) is the atlas used in this dataset. Its NIfTI file uses:

- **Origin**: Anterior commissure (AC), defined as (0, 0, 0) in world coordinates
- **Orientation**: RAS
  - +X = Right
  - +Y = Anterior
  - +Z = Superior
- **Units**: millimeters
- **Resolution**: 0.25 mm isotropic
- **Alternative origin**: The atlas also supports ear bar zero (EBZ) coordinates from the Saleem and Logothetis printed atlas. AFNI provides on-the-fly conversion between AC and EBZ systems.

The original D99 atlas (Saleem and Logothetis, 2012) was published as a printed stereotaxic atlas with its own axis conventions (A-P, M-L, D-V). The NIfTI distribution uses RAS orientation, as encoded in the affine matrix (positive diagonal, qform/sform code = 5). Whether the authors originally conceived the atlas in RAS or the NIfTI packaging imposed it is not documented. However, since the distributed NIfTI file is in RAS, we store our coordinates in the same convention so they can be used directly for voxel lookups without additional transforms.

All horizontal slices are aligned parallel to the plane passing through the interaural line and infraorbital ridge, and coronal slices are perpendicular to that plane.

**References:**
- Saleem KS, Logothetis NK (2012). "A Combined MRI and Histology Atlas of the Rhesus Monkey Brain in Stereotaxic Coordinates"
- Saleem KS et al. (2021). "High-resolution mapping and digital atlas of subcortical regions in the macaque monkey based on matched MAP-MRI and histology." NeuroImage.
- AFNI D99 documentation: https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/nonhuman/macaque_tempatl/atlas_d99v2.html

### Motor Cortex Parcellation in D99 (Matelli-Rizzolatti F Nomenclature)

The D99 atlas parcels the frontal agranular cortex using the **F nomenclature** introduced by Matelli, Luppino, and Rizzolatti (1985, 1991). This system replaces the coarse Brodmann scheme (areas 4 and 6) with seven architectonically, connectionally, and functionally distinct motor areas designated F1 through F7. The D99 labels encode both systems: for example, `F1_(4)` means "F1 in the Matelli/Rizzolatti scheme, which corresponds to Brodmann area 4." Similarly, `F2_(6DR/6DC)` maps F2 to subdivisions of Brodmann area 6. Where no parenthetical appears (e.g., F3, F6), the area falls within Brodmann area 6 but has no further classical subdivision worth noting.

#### D99 Motor Region Labels

| D99 Index | Abbreviation | Full Name | Classical Equivalent |
|-----------|--------------|-----------|---------------------|
| 359 | F1_(4) | Agranular frontal area F1 | Area 4, primary motor cortex (M1) |
| 451 | F2_(6DR/6DC) | Agranular frontal area F2 | Dorsal premotor cortex (PMd) |
| 369 | F3 | Agranular frontal area F3 | Supplementary motor area (SMA proper) |
| 444 | F4 | Agranular frontal area F4 | Ventral premotor cortex, caudal (PMv caudal) |
| 427 | F5_(6Va/6Vb) | Agranular frontal area F5 | Ventral premotor cortex, rostral (PMv rostral) |
| 401 | F6 | Agranular frontal area F6 | Pre-supplementary motor area (pre-SMA) |
| 424 | F7 | Agranular frontal area F7 | Dorsorostral area 6 (6DR) |

Note: The D99 labels file does not encode a cortical hierarchy for these areas (subcortical structures have category groupings, but cortical areas are stored as flat entries). The hierarchical organization described below comes from the Matelli/Rizzolatti framework.

#### Spatial Layout

The seven F areas tile three strips of the frontal agranular cortex: the lateral convexity (dorsal and ventral surfaces) and the medial wall. Each strip has a caudal subdivision (closer to the central sulcus) and a rostral subdivision (closer to the prefrontal cortex).

```
    LATERAL VIEW (left hemisphere, cortical surface)

              Rostral                                            Caudal
             (anterior)                                        (posterior)
                                                                  :
                  Arcuate                                      Central
                  Sulcus                                       Sulcus
                     :                                            :
                     :                                            :
         DORSAL     .:.............................................:.
         (superior) |            :                :               |
                    |    F7      :       F2       :               |
                    |   (6DR)    :    (PMd)       :       F1      |
                    |            :   6DR/6DC      :      (M1)     |
                    |............:.................:     area 4    |
                    |            :                :               |
                    |   F5a  F5p:       F4        :    <<<<<<     |
                    |  (PMv rostral) (PMv caudal) :  RECORDING    |
         VENTRAL    |   6Va/6Vb :    4C/6V       :    TARGET     |
         (inferior) '.............................................'
                     :                                            :
                     :                                            :


    MEDIAL VIEW (medial wall, looking at the interhemispheric surface)

              Rostral                                            Caudal
             (anterior)                                        (posterior)
                                                                  :
                                                               Central
                                                               Sulcus
                                                                  :
         DORSAL     ..............................................:.
         (superior) |                :                  :         |
                    |      F6        :        F3        :   F1    |
                    |   (pre-SMA)    :   (SMA proper)   :  (M1)  |
                    |                :                  :         |
                    |................:...................:.........|
                    |                :                  :         |
                    |     24c'       :     24c / 24d    :         |
                    |    (CMAr)      :   (CMAd / CMAv) :         |
         VENTRAL    |   cingulate    :    cingulate     :         |
         (inferior) |    sulcus      :     sulcus       :         |
                    '.............................................'
                                                                  :

    LEGEND
       F1  = Primary motor cortex (area 4): Betz cells, direct corticospinal output
       F2  = Dorsal premotor (PMd): sensorimotor transformation for reaching
       F3  = SMA proper: bilateral coordination, movement sequences
       F4  = Ventral premotor caudal (PMv): proximal arm, neck, face, peripersonal space
       F5  = Ventral premotor rostral (PMv): grasping, hand shaping (F5a/F5p subdivisions)
       F6  = Pre-SMA: higher-order planning, initiation timing
       F7  = Dorsorostral premotor: cognitive motor control, supplementary eye field
      24c  = Cingulate motor areas (CMAr, CMAd, CMAv)

    <<<<<< = Recording target in this dataset (F1, arm representation, Layer 5)
```

#### Functional Hierarchy: Two Tiers

The F areas divide into two tiers based on their spinal access and connectivity with F1:

**Caudal (executive) areas**: F1, F2, F3, F4, F5p

- Located closer to the central sulcus
- Have direct corticospinal projections (can drive movement)
- Connect directly with F1 (primary motor cortex)
- Receive input primarily from parietal somatosensory and visuomotor areas
- Role: sensorimotor transformation and movement execution

**Rostral (planning) areas**: F6, F7, F5a

- Located closer to the arcuate sulcus / prefrontal cortex
- Project to brainstem only (no direct spinal cord access)
- Do NOT connect directly with F1
- Receive input from prefrontal and cingulate cortex
- Role: higher-order motor planning, cognitive control, action selection

This caudal-rostral gradient reflects a hierarchy from concrete movement execution (caudal) to abstract motor planning (rostral).

#### Recording Location in This Dataset

All recordings in this dataset target **F1_(4)**, the primary motor cortex, specifically:

- **Cortical area**: F1, arm representation (verified by intracortical microstimulation at 40 uA or less)
- **Cortical layer**: Layer 5, which contains the large projection neurons
- **Cell types**: Two populations are distinguished by antidromic stimulation:
  - **PTNs** (pyramidal tract neurons): F1 Layer 5 cells that send their axons down the cerebral peduncle to the spinal cord. These are the final cortical output for voluntary movement.
  - **CSNs** (corticostriatal neurons): F1 Layer 5 cells that project to the putamen (striatum). These feed the cortico-basal ganglia loop that is disrupted by MPTP-induced dopamine depletion.

Both cell types reside in the same cortical area (F1) and layer (Layer 5), but participate in different motor circuits. The MPTP lesion destroys dopaminergic neurons in the substantia nigra pars compacta (D99 label: SNpc), disrupting basal ganglia processing of the CSN pathway and, through altered thalamic feedback, also affecting PTN activity.

**References:**
- Matelli M, Luppino G, Rizzolatti G (1985). "Patterns of cytochrome oxidase activity in the frontal agranular cortex of the macaque monkey." Behav Brain Res, 18:125-136.
- Matelli M, Luppino G, Rizzolatti G (1991). "Architecture of superior and mesial area 6 and the adjacent cingulate cortex in the macaque monkey." J Comp Neurol, 311:445-462.
- Belmalih A et al. (2007). "A multiarchitectonic approach for the definition of functionally distinct areas and domains in the monkey frontal lobe." J Anat, 211:199-211.

### Atlas Resources

**NIMH Macaque Template (NMT v2) and CHARM/SARM:**
- https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/nonhuman/macaque_tempatl/main_toc.html
- Population template from 31 macaques (symmetric and asymmetric variants) with hierarchical cortical (CHARM) and subcortical (SARM) parcellations at 6 spatial scales
- Integrated with AFNI's `@animal_warper` for registration and `afni_proc.py` for full fMRI pipelines
- Led by Adam Messinger and Daniel Glen at NIMH, Bethesda (Jung et al. 2021, NeuroImage)

**MEBRAINS:**
- https://direct.mit.edu/imag/article/doi/10.1162/imag_a_00077/119045/MEBRAINS-1-0-A-new-population-based-macaque-atlas
- Population template from 10 macaques combining T1, T2 MRI and CT; includes FreeSurfer cortical surfaces
- Integrated into EBRAINS and Scalable Brain Atlas platforms
- Led by Wim Vanduffel at KU Leuven, Belgium (Balan et al. 2024, Imaging Neuroscience)

**Scalable Brain Atlas:**
- https://scalablebrainatlas.incf.org/
- Web-based interactive viewer hosting 20+ atlases across 6 species (mouse, rat, macaque, human, marmoset, ferret)
- Macaque atlases include Calabrese 2015, Paxinos 2000, NeuroMaps 2009, Markov 2014, and F99-registered Caret templates (D99 is not included; it is distributed through AFNI)
- Developed by Rembrandt Bakker at the Donders Institute, Radboud University Nijmegen, funded by INCF

**Brainglobe Atlas API:**
- https://brainglobe.info/documentation/brainglobe-atlasapi/
- Python API for programmatic atlas access
- Note: As of 2025, no macaque atlases are included; only mouse, rat, human, and other species

### Chamber-to-Atlas Transformation (ACx Coordinates)

The atlas coordinates stored in the NWB files were computed by **Dr. Robert Turner** (data author) from the chamber-relative positions using the known chamber placement geometry. The transformation uses two parameters:

1. **AP offset (-8.2 mm)**: The distance from the chamber center to the anterior commissure along the anterior-posterior axis. The chamber center is 8.2 mm posterior to the AC in D99 atlas space. This means `A_P_acx = A_P - 8.2` (a constant shift, because the chamber AP axis is parallel to the atlas A axis with no sagittal tilt).

2. **35-degree coronal tilt rotation**: The chamber is tilted 35 degrees from vertical in the coronal plane. This means the chamber ML and Depth axes do not align with the atlas R and S axes. A 2D rotation by 35 degrees, combined with offsets for the chamber center position in the R-S plane, transforms `(M_L, Depth)` into `(M_L_acx, Depth_acx)`. Unlike the AP offset, this is not a simple constant shift: M_L_acx and Depth_acx both depend on the original M_L and Depth values.

The resulting ACx coordinates (`A_P_acx`, `M_L_acx`, `Depth_acx`) are stored in the metadata table (`ven_table.csv`) alongside the original chamber coordinates. The conversion code reads them directly and converts to D99 RAS:

```
R = -M_L_acx       (left hemisphere +lateral becomes +right negative)
A = A_P_acx         (+anterior in both systems)
S = Depth_acx       (+superior/dorsal in both systems)
```

**Precision and limitations**: This transformation is geometric (rigid rotation + translation), not based on individual MRI registration. The accuracy depends on the precision of the stereotaxic chamber placement and the assumption that the chamber angle was exactly 35 degrees. No individual MRI or CT data were used. The atlas (D99) is from a different animal, so there is an inherent cross-subject registration uncertainty of approximately 1-2 mm, visible in the 16 "outside atlas" sessions (5.4%) that fall on unlabeled voxels at cortical boundaries. See [anatomical_coordinates_verification.md](../../build/coordinate_verification/anatomical_coordinates_verification.md) for the full verification analysis.

**ACx coordinates are currently available for Monkey V only.** Coordinates for Monkey L are pending.

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
