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

### Summary of All Stored Localization Data

| Storage Location | Field | Value | Source | Units/Convention |
|---|---|---|---|---|
| `electrodes` table | `x, y, z` | NMT v2.0-sym coordinates | Derived (RheMAP warp from D99) | micrometers, PIR |
| `electrodes` table | `location` | Curated D99 M1 region full name ("agranular frontal area F1") | Curator (M1-constrained NN; see below) | string |
| `electrodes` table | `chamber_grid_ap_mm` | Chamber A-P position | Dr. Turner (source data) | mm, +posterior |
| `electrodes` table | `chamber_grid_ml_mm` | Chamber M-L position | Dr. Turner (source data) | mm, +right |
| `electrodes` table | `chamber_insertion_depth_mm` | Insertion depth | Dr. Turner (source data) | mm, +deeper |
| `D99v2AtlasCoordinates` | `x, y, z` | D99 RAS coordinates | Dr. Turner (geometric transform) | mm, RAS, origin=AC |
| `D99v2AtlasCoordinates` | `brain_region` | Curated D99 M1 region full name | Curator (M1-constrained NN to F1_(4)) | string |
| `D99v2AtlasCoordinates` | `brain_region_id` | Curated D99 M1 abbreviation | Curator (M1-constrained NN to F1_(4)) | string, always `F1_(4)` on this dataset |
| `D99v2AtlasCoordinates` | `brain_region_lookup_method` | `exact` / `nearest_neighbor` / `no_m1_within_5mm` | Curator | enum string |
| `D99v2AtlasCoordinates` | `brain_region_distance_mm` | Distance from coord to nearest D99 F1 voxel | Curator | mm; 0 for exact, positive for NN, NaN for capped |
| `D99v2AtlasCoordinates` | `voxel_label` | Raw D99 voxel label (e.g. "somatosensory areas 1 and 2") | D99 v2.0 atlas voxel lookup (no interpolation) | string or sentinel |
| `D99v2AtlasCoordinates` | `voxel_label_id` | Raw D99 voxel abbreviation (e.g. `area_1-2`) | D99 v2.0 atlas voxel lookup | string or `unlabeled` / `outside_volume` |
| `NMTv2AtlasCoordinates` | `x, y, z` | NMT v2.0-sym RAS coordinates | Derived (RheMAP nonlinear warp from D99) | mm, RAS, origin=EBZ |
| `NMTv2AtlasCoordinates` | `brain_region` | Curated CHARM M1 region full name (`primary_motor_cortex`) | Curator (M1-constrained NN to CHARM 79) | string |
| `NMTv2AtlasCoordinates` | `brain_region_id` | Curated CHARM M1 abbreviation | Curator | string, always `M1` on this dataset |
| `NMTv2AtlasCoordinates` | `brain_region_lookup_method` | `exact` / `nearest_neighbor` / `no_m1_within_5mm` | Curator | enum string |
| `NMTv2AtlasCoordinates` | `brain_region_distance_mm` | Distance from coord to nearest CHARM M1 voxel | Curator | mm |
| `NMTv2AtlasCoordinates` | `voxel_label` | Raw CHARM level-4 voxel label | CHARM level-4 voxel lookup | string or sentinel |
| `NMTv2AtlasCoordinates` | `voxel_label_id` | Raw CHARM abbreviation (e.g. `M1`, `PM`, `SI`) | CHARM level-4 voxel lookup | string or `unlabeled` / `outside_volume` |
| `MEBRAINSAtlasCoordinates` | `x, y, z` | MEBRAINS 1.0 RAS coordinates | Derived (RheMAP nonlinear warp from D99) | mm, RAS, origin=AC |
| `MEBRAINSAtlasCoordinates` | `brain_region` | Curated MEBRAINS M1 full name (`4a left` or `4p left`) | Curator (M1-constrained NN to 4a/4p) | string |
| `MEBRAINSAtlasCoordinates` | `brain_region_id` | Curated MEBRAINS M1 numeric string ID | Curator | `301` or `303` on this dataset |
| `MEBRAINSAtlasCoordinates` | `brain_region_lookup_method` | `exact` / `nearest_neighbor` / `no_m1_within_5mm` | Curator | enum string |
| `MEBRAINSAtlasCoordinates` | `brain_region_distance_mm` | Distance from coord to nearest MEBRAINS M1 voxel | Curator | mm |
| `MEBRAINSAtlasCoordinates` | `voxel_label` | Raw MEBRAINS voxel label | MEBRAINS voxel lookup | string or sentinel |
| `MEBRAINSAtlasCoordinates` | `voxel_label_id` | Raw MEBRAINS numeric string ID | MEBRAINS voxel lookup | string or `unlabeled` / `outside_volume` |

### Data Provenance

The localization data in each NWB file is produced in three layers. Keeping these layers distinct is important when interpreting the columns:

```
Chamber coords ─→ [geometric transform] ─→ D99 coords ─→ [RheMAP warp] ─→ NMT/MEBRAINS coords
     (source)          (Dr. Turner)           (source)    (precomputed)         (derived)
                                                 │
                               ┌─────────────────┴───────────────────────────────┐
                               ▼                                                 ▼
                     [raw atlas voxel lookup]                     [M1-constrained NN lookup]
                          (curator)                                   (curator)
                               │                                                 │
                               ▼                                                 ▼
                voxel_label / voxel_label_id                brain_region / brain_region_id
              (honest atlas answer, may be                   (curated M1 label, what the
               non-motor, unlabeled, or OOB)                   dandi-atlas viewer displays)
```

**Layer 1: Source coordinates (from Dr. Turner).** Chamber-relative coordinates (`A_P`, `M_L`, `Depth`) are recorded daily during experiments. ACx coordinates (`A_P_acx`, `M_L_acx`, `Depth_acx`) are derived by Dr. Turner using the known chamber placement geometry: a constant AP offset (-8.2 mm from chamber center to anterior commissure) and a 35-degree rotation in the coronal plane. These are stored in the metadata table (`ven_table.csv`) and are the authored localization data for this dataset. No individual MRI was used; accuracy is limited by the geometric approximation.

**Layer 2: Derived coordinates (curator-computed warps).** NMT v2.0-sym and MEBRAINS coordinates are derived by applying pre-computed nonlinear warps from the RheMAP project (Sirmpilatze & Klink, 2020) to the D99 coordinates. These transforms are atlas-to-atlas (D99 volume to NMT volume, D99 volume to MEBRAINS volume), not subject-specific. Their purpose is interoperability: a downstream user can work in whichever template space their pipeline uses. The warp adds its own uncertainty on top of the geometric-transform uncertainty from Layer 1.

**Layer 3: Region annotations (curator-computed lookups).** Each `AnatomicalCoordinatesTable` carries two region-annotation columns that serve different purposes:

- `voxel_label_id` / `voxel_label` are the **raw atlas voxel answer** at the coordinate, with no interpolation. For D99 this is whatever the D99 parcellation says; for NMT it is the CHARM level-4 label; for MEBRAINS it is the numeric string form of the Julich Brain Macaque label ID. When the coordinate falls on an unlabeled voxel (label=0) or outside the template bounding box, these columns carry the sentinel strings `"unlabeled"` / `"outside_volume"`.
- `brain_region_id` / `brain_region` are a **curated M1-constrained label**. If the raw voxel is the atlas's native primary motor cortex label (F1_(4) for D99, M1 for CHARM, 4a or 4p for MEBRAINS), it is preserved and the method column is set to `"exact"`. Otherwise the nearest M1 voxel within 5 mm is chosen, with the Euclidean distance recorded in `brain_region_distance_mm` and the fallback flagged in `brain_region_lookup_method`.

The curation is a dataset-specific convenience for dandiset 001636: every recording site in this dataset is ICMS-verified M1 (threshold <30 µA, stored in `icms_threshold_uA` on the electrodes table), so a non-M1 raw-voxel answer is definitionally a warp artifact rather than a real anatomical answer. The curation is documented in full in [documentation/nearest_neighbor_region_labeling.md](nearest_neighbor_region_labeling.md). The curation should not be used as a substitute for the ICMS evidence, and the policy (fall back to M1 when raw voxel is non-motor) is specific to M1-recording datasets.

### Standard NWB Electrode Coordinates

The standard NWB `x`, `y`, `z` coordinates are populated in the PIR convention (Posterior-Inferior-Right) in microns. Coordinates are derived from **NMT v2.0-sym** (the NIMH Macaque Template, the most widely used community standard) via the RheMAP warp.

The NMT and MEBRAINS warped coordinates are **precomputed** and stored in `assets/metadata_table/warped_coordinates.csv`. The conversion pipeline reads from this CSV at runtime (instant lookup) rather than calling ANTs per session. To regenerate the precomputed coordinates (e.g., after updating source coordinates), run:

```bash
uv run python src/turner_lab_to_nwb/asap_m1_mptp/scripts/precompute_warped_coordinates.py
```

The `AnatomicalCoordinatesTable` entries store coordinates in native RAS orientation for each space (see below).

### D99 Atlas Coordinates (ndx-anatomical-localization)

Atlas coordinates are stored using the `ndx-anatomical-localization` extension in the **native D99 RAS orientation** (Right-Anterior-Superior), so the values can be used directly for atlas lookups without additional coordinate transforms:

```python
# Accessing D99 atlas coordinates (RAS, mm, origin = anterior commissure)
localization = nwbfile.lab_meta_data["localization"]
coords_table = localization.anatomical_coordinates_tables["D99v2AtlasCoordinates"]
space = coords_table.space  # D99 Space object with origin, units, orientation="RAS"

r = coords_table["x"][0]  # +right (left hemisphere recordings are negative)
a = coords_table["y"][0]  # +anterior
s = coords_table["z"][0]  # +superior
brain_region = coords_table["brain_region"][0]
```

### NMT v2.0-sym Atlas Coordinates (ndx-anatomical-localization)

Coordinates are also stored in **NMT v2.0-sym** (NIMH Macaque Template, symmetric variant) space. These are computed by applying a nonlinear composite warp from the RheMAP project (Sirmpilatze & Klink, 2020) to the D99 coordinates. The warped results are precomputed in batch (see `scripts/precompute_warped_coordinates.py`) and looked up at conversion time from `assets/metadata_table/warped_coordinates.csv`.

```python
# Accessing NMT v2.0-sym coordinates (RAS, mm, origin = ear bar zero)
localization = nwbfile.lab_meta_data["localization"]
nmt_table = localization.anatomical_coordinates_tables["NMTv2AtlasCoordinates"]
nmt_space = nmt_table.space  # NMT_v2.0_sym Space object

r_nmt = nmt_table["x"][0]  # +right
a_nmt = nmt_table["y"][0]  # +anterior
s_nmt = nmt_table["z"][0]  # +superior
```

**Note on NMT v2 origin:** The `Space` object for NMT v2 records `origin="ear bar zero"`, reflecting NMT v2's native coordinate system where (0,0,0) corresponds to the intersection of the midsagittal plane and the interaural line. This differs from D99 and MEBRAINS, which both use the anterior commissure (AC) as origin.

The precompute script uses ANTsPy (`ants.apply_transforms_to_points`) with the `NMTv2.0-sym_to_D99_CompositeWarp.nii.gz` warp file (applied in the **reversed direction** for points, per ANTs convention). Coordinates are converted from RAS to LPS before warping and back afterward.

**RheMAP warp file** (needed only for precomputation, not at conversion time): Download `warps_final_NMTv2.0-sym.zip` from [Zenodo (DOI: 10.5281/zenodo.4748589)](https://zenodo.org/records/4748589) and extract `NMTv2.0-sym_to_D99_CompositeWarp.nii.gz` to `data/rhemap_warps/`.

**References:**
- Sirmpilatze N, Klink PC (2020). "RheMAP: Non-linear warps between common rhesus macaque brain templates." NeuroImage, 226, 117519. DOI: 10.5281/zenodo.4748589
- Jung B et al. (2021). "A comprehensive macaque fMRI pipeline and hierarchical atlas." NeuroImage, 235, 117997.

### MEBRAINS 1.0 Atlas Coordinates (ndx-anatomical-localization)

Coordinates are also stored in **MEBRAINS 1.0** (Balan et al. 2024), an independent population-based macaque template built from 10 rhesus monkeys. MEBRAINS provides a cross-validation target: if localization results hold in both NMT v2 and MEBRAINS space, they are template-independent. Like NMT, MEBRAINS coordinates are precomputed in batch and looked up from `warped_coordinates.csv` at conversion time.

```python
# Accessing MEBRAINS 1.0 coordinates (RAS, mm, origin = anterior commissure)
localization = nwbfile.lab_meta_data["localization"]
mebrains_table = localization.anatomical_coordinates_tables["MEBRAINSAtlasCoordinates"]
mebrains_space = mebrains_table.space  # MEBRAINS_1.0 Space object

r_mebrains = mebrains_table["x"][0]  # +right
a_mebrains = mebrains_table["y"][0]  # +anterior
s_mebrains = mebrains_table["z"][0]  # +superior
```

The precompute script uses ANTsPy (`ants.apply_transforms_to_points`) with the `MEBRAINS_to_D99_CompositeWarp.nii.gz` warp file (applied in the **reversed direction** for points, per ANTs convention), following the same RAS-to-LPS conversion as the NMT warp.

MEBRAINS uses the anterior commissure (AC) as its origin with approximate Horsley-Clarke alignment. Because both D99 and MEBRAINS use AC origin, their coordinates are in a similar range (unlike NMT which uses EBZ origin).

MEBRAINS does not have a native whole-brain parcellation comparable to CHARM/SARM. The `brain_region` and `brain_region_id` columns carry the D99-derived label (looked up in D99 native space before warping). The Julich Brain Macaque Maps (partial cortical coverage, registered to the MEBRAINS surface) exist but are not suitable for automated voxel lookup in our pipeline (see [What We Do Not Store](#what-we-do-not-store-and-why)).

**RheMAP warp file** (needed only for precomputation, not at conversion time): Download from the [RheMAP G-NODE repository](https://gin.g-node.org/ChrisKlink/RheMAP) (`warps/final/MEBRAINS_to_D99_CompositeWarp.nii.gz`) and place in `data/rhemap_warps/`.

**References:**
- Balan PF et al. (2024). "MEBRAINS 1.0: A new population-based macaque atlas." Imaging Neuroscience, 2, imag_a_00077. DOI: 10.1162/imag_a_00077
- Sirmpilatze N, Klink PC (2020). RheMAP (as above).

### The Localization Container

The `Localization` container (from the `ndx-anatomical-localization` extension, v0.1.0) holds all atlas-space data. It includes:

- **Three typed `Space` objects** (dedicated classes in the 0.1.0 release; canonical metadata is baked in):
  - `D99v2Space` — name `D99v2`, origin anterior commissure, units mm, orientation RAS.
  - `NMTv2Space` — name `NMTv2`, origin ear bar zero, units mm, orientation RAS.
  - `MEBRAINSSpace` — name `MEBRAINS`, origin anterior commissure, units mm, orientation RAS.

- **Three `AnatomicalCoordinatesTable` entries**, each linking coordinates to the electrode table:
  - `D99v2AtlasCoordinates`: source coordinates from Dr. Turner's geometric transform; region annotations via D99 voxel lookup plus M1-constrained NN.
  - `NMTv2AtlasCoordinates`: coordinates warped from D99 via RheMAP; region annotations via CHARM level-4 voxel lookup plus M1-constrained NN.
  - `MEBRAINSAtlasCoordinates`: coordinates warped from D99 via RheMAP; region annotations via MEBRAINS voxel lookup plus M1-constrained NN.

All three tables carry the same ten columns (`x`, `y`, `z`, `localized_entity`, `brain_region_id`, `brain_region`, `brain_region_lookup_method`, `brain_region_distance_mm`, `voxel_label_id`, `voxel_label`). The `brain_region_*` columns hold the curated M1 label (what the dandi-atlas viewer displays) and the `voxel_label_*` columns hold the raw atlas answer. See [Data Provenance](#data-provenance) for the distinction.

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

D99 atlas coordinates are available for **both monkeys (V and L)**. See [Chamber-to-Atlas Transformation](#chamber-to-atlas-transformation-acx-coordinates) for how these coordinates were computed.

### Stimulation Electrodes

Stimulation electrodes (cerebral peduncle, putamen, thalamus) are represented as NWB devices rather than in the electrodes table:
- Chronically implanted at fixed locations during surgery
- Positions verified histologically but not tracked in chamber coordinates
- See `nwbfile.devices` for stimulation electrode descriptions

## What We Do Not Store (and Why)

This section documents data we deliberately chose not to include in the NWB files, with the technical reasoning behind each decision. These are informed choices, not oversights.

### CHARM/SARM Hierarchical Labels

**Partial use only.** We use CHARM level 4 as the native NMT parcellation for the `NMTv2AtlasCoordinates` table's `voxel_label_id` / `voxel_label` columns and as the target for the M1-constrained NN curation of `brain_region_id` (M1 = CHARM index 79). We do **not** store CHARM labels at levels 2, 3, 5, or 6, and we do not store SARM subcortical labels. The reasoning below is why we do not attempt to offer CHARM as a generic multi-level label set; the M1-constrained use is specifically chosen to avoid the reliability issues and is documented in [nearest_neighbor_region_labeling.md](nearest_neighbor_region_labeling.md).

The community recommendation for NWB annotation is to include CHARM/SARM labels at multiple hierarchy levels (e.g., level 2 for robust coarse labels, level 6 for fine cytoarchitectonic areas). We do not include these labels at arbitrary levels because CHARM voxel lookup at our atlas-to-atlas warped coordinates is unreliable in general, even though it works for our specific M1-only use case.

**Technical analysis.** We tested CHARM voxel lookup at NMT coordinates produced by applying the RheMAP D99-to-NMT warp to our D99 source coordinates. Results:

- 3 out of 5 representative M1 coordinates returned CHARM label 0 (unlabeled), meaning the warped point landed outside the cortical gray matter ribbon in NMT space.
- The nearest CHARM label to one "miss" was 2 mm away (PMdc, caudal dorsal premotor cortex).
- When a coordinate did hit a labeled voxel, CHARM level 6 returned "PMdc" (premotor cortex), not "M1" (primary motor cortex), even though the D99 atlas correctly labels the original coordinate as F1 (M1). The atlas-to-atlas warp shifted the point across an area boundary.

**Why this happens.** Three factors compound:

1. **Cortical ribbon thickness.** CHARM labels exist only on cortical gray matter voxels. The cortical ribbon is ~1.5-2.5 mm thick at 0.25 mm resolution. White matter, CSF, and subcortical structures are unlabeled (0). SARM covers subcortex separately.
2. **Atlas-to-atlas warp misalignment.** The RheMAP warp aligns the D99 volume to the NMT v2 volume globally, optimizing tissue boundary correspondence across the whole brain. It does not guarantee that a point on the cortical surface of D99 maps to the cortical surface of NMT. The cortical folding patterns of D99 (one brain) and NMT v2 (average of 31 brains) differ, so a gray matter voxel in D99 can warp to a white matter or CSF voxel in NMT.
3. **Geometric transform uncertainty.** Our D99 coordinates come from a geometric transform (constant AP offset + 35-degree rotation), not individual MRI registration. This adds ~1-2 mm uncertainty before the atlas warp is even applied.

**What would be needed.** Reliable CHARM lookup requires registering the individual animal's MRI directly to NMT v2 using a subject-specific nonlinear warp (e.g., via AFNI's `@animal_warper`). This produces a warp that respects the animal's specific cortical geometry, keeping cortical points on the cortical surface after transformation. No individual MRI data exists for the animals in this dataset, so subject-specific registration is not possible.

**What downstream users can do.** The NMT v2 coordinates we store are the essential building block. A user who has (or acquires) the animal's MRI could register it to NMT v2, obtain a subject-specific warp, transform our D99 coordinates through that warp, and perform a reliable CHARM lookup at the resulting coordinates.

### Registration Quality Metric

**Not stored as a numeric column.** No individual MRI was used in this dataset, so there is no warp quality metric (e.g., Dice coefficient, Jacobian determinant) to report. The table-level `method` attribute on each `AnatomicalCoordinatesTable` describes the geometric-only approach and its limitations. The `brain_region_lookup_method` and `brain_region_distance_mm` per-row columns function as an anatomically meaningful proxy: electrodes where the curated label came from an `exact` raw-voxel hit are well-registered to the atlas's native M1 territory; electrodes that required `nearest_neighbor` fallback reveal how far the coordinate landed from labeled M1 (warp uncertainty, sulcal-gap artifact, or cytoarchitectonic boundary offset).

Across all 447 sessions, raw atlas voxel lookups (`voxel_label_id`) give the following breakdown (computed from the locally converted NWB files; see `nearest_neighbor_region_labeling.md` for the full analysis):

| Atlas | Venus exact M1 hit | Venus non-motor / unlabeled | Leu exact M1 hit | Leu non-motor / unlabeled |
|-------|-------------------:|---------------------------:|-----------------:|--------------------------:|
| D99 v2.0 (F1_(4)) | 61.1% | 38.9% | 1.3% | 98.7% |
| NMT CHARM-4 (M1) | 45.6% | 54.4% | 0.0% | 100.0% |
| MEBRAINS (4a/4p) | 40.9% | 59.1% | 0.0% | 100.0% |

All non-exact hits within 5 mm of labeled M1 are recovered by the M1-constrained NN fallback (max observed distance: 4.47 mm), so no electrodes hit the `no_m1_within_5mm` sentinel on this dataset. Leu's higher fallback rate reflects more dorsal electrode placement at the central sulcus fundus (D99 S range: 16.9-23.1 mm for Leu vs 13.2-19.6 mm for Venus) and the post-mortem sulcal-gap artifact that affects all three templates at that depth.

### Julich Brain Macaque Maps Labels

**Not stored.** The Julich Brain Macaque Maps (Rapan et al. 2021, 2023; Niu et al. 2020, 2021, 2024) provide multimodal cytoarchitectonic maps registered to the MEBRAINS surface. We store MEBRAINS coordinates for cross-validation purposes, but do not look up Julich labels because: (1) the Julich maps have incomplete cortical coverage (frontal, parietal, visual, and somatosensory cortex as of 2024, with gaps); (2) the maps are surface-based probabilistic labels, not volumetric parcellations suitable for direct voxel lookup; and (3) the same atlas-to-atlas warp limitation applies.

### Subject-Native MRI Coordinates

**Not available.** No individual MRI or CT data exists for the animals in this dataset. All atlas coordinates are derived from the geometric chamber-to-D99 transform computed by Dr. Turner.

## Relationship to NWB Best Practices

The community recommendation for well-annotated NWB files with NHP localization data includes: (1) NMT v2 coordinates as the primary space, (2) CHARM/SARM labels at multiple hierarchy levels, (3) reference space metadata, and (4) registration quality indicators. Here is how our files compare:

| Recommendation | Our Status | Rationale |
|---|---|---|
| NMT v2 coordinates | Stored (`NMTv2AtlasCoordinates`) | Derived from D99 via RheMAP warp |
| CHARM hierarchical labels | Partial (level 4 only, M1-constrained) | Level-4 M1 index used for curated `brain_region_id` and raw `voxel_label_id` on the NMT table; other levels not stored due to atlas-to-atlas warp reliability limits (see above) |
| SARM subcortical labels | N/A | All recordings are cortical (M1) |
| Reference space metadata | Stored (three `Space` objects with origin, units, orientation) | Fully specified |
| Registration quality | Not stored as numeric | No individual MRI; `method` text describes limitations |
| D99 coordinates + labels | Stored (`D99v2AtlasCoordinates`) | Source of truth, closest to original data |
| MEBRAINS coordinates | Stored (`MEBRAINSAtlasCoordinates`) | Cross-validation target |

**Key difference from the ideal.** The community recommendation assumes a lab that has subject MRI and can register directly to NMT v2 using `@animal_warper`. In that workflow, CHARM lookup at the subject-specific warped coordinates is reliable. Our situation is different: we are data curators working with a geometric transform (no individual MRI), so our NMT coordinates come from an atlas-to-atlas warp with insufficient precision for cortical voxel lookup. The D99 labels (looked up at the original D99 coordinates, before any warping) are the most reliable region annotations we can provide.

**What we provide that the ideal does not require.** We store coordinates in three independent template spaces (D99, NMT v2, MEBRAINS), enabling template-independence checks. We also carry the D99 region label through to all three tables, so every coordinate table is self-contained with both coordinates and a region name.

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

| Atlas | Type | Resolution | Key Features | Used in This Dataset |
|-------|------|------------|--------------|---------------------|
| **D99** v2.0 | Single-subject MRI + histology | 0.25 mm | AC origin; RAS orientation; 368 labeled regions | Yes: source coordinates and region labels |
| **NMT v2** (NIMH Macaque Template) | Population MRI template (31 macaques) | 0.25-0.5 mm | EBZ origin; Horsley-Clarke aligned; integrated with AFNI | Yes: derived coordinates via RheMAP warp |
| **CHARM** (Cortical Hierarchy Atlas of the Rhesus Macaque) | Cortical parcellation on NMT v2 | Matched to NMT | 6 hierarchical levels (4 to 134 regions); derived from D99 boundaries | Partial: level 4 used for the NMT table's `voxel_label_id` and as the M1-constrained curation target (M1 = index 79); other levels not stored (see [CHARM/SARM section](#charmsarm-hierarchical-labels)) |
| **SARM** (Subcortical Atlas of the Rhesus Macaque) | Subcortical parcellation on NMT v2 | Matched to NMT | 6 hierarchical levels; nomenclature from RMBSC4 | No: all recordings are cortical |
| **MEBRAINS 1.0** | Population T1/T2 template (10 macaques) | 0.20 mm | AC origin; approximate Horsley-Clarke alignment (2024) | Yes: derived coordinates via RheMAP warp |
| **RMBSC4** (Rhesus Monkey Brain in Stereotaxic Coordinates) | Histological atlas | Section-based | Gold standard for stereotaxic coordinates; 4th edition (Paxinos) | No |

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

**Precision and limitations**: This transformation is geometric (rigid rotation + translation), not based on individual MRI registration. The accuracy depends on the precision of the stereotaxic chamber placement and the assumption that the chamber angle was exactly 35 degrees. No individual MRI or CT data were used. The atlas (D99) is from a different animal, so there is an inherent cross-subject registration uncertainty of approximately 1-2 mm, visible in the 16/298 Venus sessions (5.4%) and 61/149 Leu sessions (40.9%) that fall on unlabeled D99 voxels at cortical boundaries. Leu's higher D99 outside rate reflects more dorsal electrode positions (D99 S: 16.9-23.1 mm vs Venus 13.2-19.6 mm) at the compressed dorsal boundary of the D99 template. See [anatomical_coordinates_verification.md](../../build/coordinate_verification/anatomical_coordinates_verification.md) for the full verification analysis.

**ACx coordinates are available for both monkeys (V and L).**

## Discussion with Data Author on Atlas Accuracy (2026-03-03)

After integrating the D99 atlas coordinates and warping them to NMT v2.0-sym and MEBRAINS spaces, we sent Dr. Turner a visualization showing recording positions in all three coordinate spaces with their respective atlas parcellations, along with a cross-tabulation of D99 region assignments against antidromic classification. The results showed 17 units (5%) falling outside D99 atlas bounds and 17 PTNs assigned to 3a/b rather than F1.

Dr. Turner confirmed these discrepancies are expected and stem from atlas limitations rather than recording errors. He identified three specific issues, providing figures for each (stored in `assets/turner_correspondence/`):

### 1. NMT/MEBRAINS overestimate sulcal gaps

Post-mortem tissue processing causes shrinkage and distortion, so NMT and MEBRAINS templates show large out-of-brain (black) gaps in sulci that do not exist in the living brain. In vivo, the banks of the central sulcus are nearly touching (<1mm gap). This means coordinates that are within cortical gray matter in the live animal can land in "empty space" in the template.
(See: `in_vivo_central_sulcus.jpg`, `cicerone_central_sulcus.png`)

### 2. D99 is vertically compressed

When D99 is overlaid on an in vivo MRI (both aligned to anterior commissure), the dorsal brain extends above D99's boundary. Recording sites at dorsal/lateral positions can fall "outside" D99 simply because the template is too small in the dorso-ventral axis.
(See: `d99_over_in_vivo_mri.png`)

### 3. D99 places the M1/premotor boundary too posteriorly

A substantial amount of arm-related M1 extends onto the gyral surface anterior to the bank of the central sulcus. The D99 template places the F1/F2 boundary too far posteriorly, so units that are functionally in M1 (confirmed by microstimulation at <10-30 uA) get assigned to premotor or 3a/b labels by automated D99 voxel lookup. Dr. Turner cited Matelli et al. (doi: 10.1016/s0013-4694(98)00022-4) and Lemon (doi: 10.1146/annurev-neuro-070918-050216), the latter showing the F1/F4 boundary ~2mm anterior to the genu of the central sulcus.
(See: `f1_f4_boundary_matelli1991.png`)

### Microstimulation as ground truth

Dr. Turner noted that microstimulation data provides the strongest evidence for M1 identity: M1 is microexcitable at currents <30 uA (10 shocks at 300Hz), unlike surrounding cortical areas (S1, premotor). At many recording locations, movement was evoked at <10 uA. This information was subsequently added to the metadata for both monkeys (Venus: 2026-03-09, Leu: 2026-03-05).

### Implications for the dataset

The atlas-based region labels should be treated as approximate. The 17 units in 3a/b are likely M1 neurons near the cytoarchitectonic boundary, and the 17 "outside atlas" units reflect template size and boundary limitations. Dr. Turner reviewed his chamber position estimate for Venus and could not find improvements, acknowledging intrinsic noise (~1-2mm) in the original location data from the electrode positioning methods used at the time. The microstimulation results now included in the metadata provide an independent, functional confirmation of M1 identity that is more reliable than atlas-based assignment for this dataset.

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
