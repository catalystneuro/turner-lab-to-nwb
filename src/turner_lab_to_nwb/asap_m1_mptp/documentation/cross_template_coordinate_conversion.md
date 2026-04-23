# Cross-Template Coordinate Conversion: D99 to NMT v2.0-sym

This document describes how electrode coordinates are converted from D99 atlas space to NMT v2.0-sym (NIMH Macaque Template) space using RheMAP nonlinear warps, and how both coordinate sets are stored in NWB files.

**Related documentation:**
- [anatomical_coordinates.md](anatomical_coordinates.md): Chamber coordinate system, D99 atlas coordinates, NWB storage format
- [Verification report](../../build/coordinate_verification/anatomical_coordinates_verification.md): D99 coordinate validation (298 sessions)

## Why Two Coordinate Spaces?

The Turner Lab dataset stores electrode positions in two macaque brain template spaces:

| Template | Type | Why |
|----------|------|-----|
| **D99** (Saleem & Logothetis) | Single-subject histology-based atlas | Source coordinates: Dr. Turner computed chamber-to-atlas transforms using D99 geometry |
| **NMT v2.0-sym** (NIMH Macaque Template) | Population-averaged MRI template (31 macaques) | Community standard: most widely used template for macaque neuroimaging, recommended for data sharing |

D99 is the native space of the original coordinate transformation. NMT v2.0-sym is included because it is the de facto community standard for cross-study comparisons, and most published macaque fMRI and electrophysiology datasets are registered to NMT.

## The Coordinate Pipeline

The full pipeline from raw data to NWB storage has three stages:

```
Stage 1: Chamber coordinates (source data)
    A_P, M_L, Depth in chamber-relative frame
    Computed by: experimenters during recording
    Available for: all sessions

        |
        v  (geometric transformation by Dr. Robert Turner)

Stage 2: D99 atlas coordinates (ACx convention)
    A_P_acx, M_L_acx, Depth_acx
    Transform: AP offset (-8.2 mm) + 35-degree coronal rotation
    Available for: both monkeys (V and L)

        |
        v  (RheMAP nonlinear warp via ANTsPy)

Stage 3: NMT v2.0-sym atlas coordinates
    Computed by: applying pre-computed composite warp field
    Available for: both monkeys (V and L)
```

## How the Warp Works

### RheMAP

[RheMAP](https://github.com/PRIME-RE/RheMAP) (Sirmpilatze & Klink, 2020) provides pre-computed nonlinear registration warps between all major macaque brain templates. The warps are composite fields (affine + nonlinear combined into a single displacement field) stored as NIfTI volumes (~480 MB each).

For this project, we use the D99-to-NMTv2.0-sym warp from the [Zenodo dataset](https://zenodo.org/records/4748589) (DOI: 10.5281/zenodo.4748589, v1.3).

### The Point Transform Convention (Critical)

ANTs uses **reversed warp direction for points** compared to images:

| Operation | Warp file to use |
|-----------|-----------------|
| Warp an **image** from D99 to NMT | `D99_to_NMTv2.0-sym_CompositeWarp.nii.gz` |
| Warp a **point** from D99 to NMT | `NMTv2.0-sym_to_D99_CompositeWarp.nii.gz` (opposite!) |

This is an ANTs convention, not a RheMAP quirk. The reason: image resampling asks "for each voxel in the target, where does it come from in the source?" while point mapping asks "where does this source point land in the target?" These are inverse operations.

Using the wrong direction silently produces incorrect coordinates. Always verify with a known landmark.

### The RAS/LPS Conversion

ANTs internally operates in LPS+ coordinates (Left-Posterior-Superior). NIfTI files (including both D99 and NMT) use RAS+ (Right-Anterior-Superior). The conversion is:

```
RAS to LPS:  negate x (R -> L), negate y (A -> P), keep z (S = S)
LPS to RAS:  negate x (L -> R), negate y (P -> A), keep z (S = S)
```

Both conversions are the same operation (negate x and y). Forgetting this step shifts coordinates to the wrong hemisphere and anterior/posterior position.

### Step-by-Step Conversion

For a single coordinate in D99 RAS (mm):

```python
import ants
import pandas as pd

# Input: D99 RAS coordinate (mm)
d99_r, d99_a, d99_s = -15.02, -4.2, 15.02  # example electrode position

# 1. RAS to LPS (negate R and A for ANTs)
points = pd.DataFrame({"x": [-d99_r], "y": [-d99_a], "z": [d99_s]})

# 2. Apply warp (REVERSED direction for points)
transformed = ants.apply_transforms_to_points(
    dim=3,
    points=points,
    transformlist=["data/rhemap_warps/NMTv2.0-sym_to_D99_CompositeWarp.nii.gz"],
)

# 3. LPS back to RAS (negate L and P)
nmt_r = -transformed["x"].values[0]
nmt_a = -transformed["y"].values[0]
nmt_s = transformed["z"].values[0]
# Result: NMT v2.0-sym RAS coordinate (mm)
```

## NWB Storage

Both D99 and NMT coordinates are stored using the `ndx-anatomical-localization` NWB extension:

```
nwbfile.lab_meta_data["localization"]
    |
    +-- spaces
    |   +-- D99v2  (origin: AC, units: mm, orientation: RAS)
    |   +-- NMTv2  (origin: ear bar zero, units: mm, orientation: RAS)
    |   +-- MEBRAINS  (origin: AC, units: mm, orientation: RAS)
    |
    +-- anatomical_coordinates_tables
        +-- D99v2AtlasCoordinates
        |   x (R), y (A), z (S), localized_entity,
        |   brain_region, brain_region_id,
        |   brain_region_lookup_method, brain_region_distance_mm,
        |   voxel_label, voxel_label_id
        |
        +-- NMTv2AtlasCoordinates   (same 10 columns as D99)
        |
        +-- MEBRAINSAtlasCoordinates   (same 10 columns as D99)
```

The standard NWB electrode table `x, y, z` fields use NMT v2.0-sym coordinates when available (converted to PIR convention in microns), falling back to D99 coordinates when the warp is unavailable. Both native coordinate sets remain accessible in their respective `AnatomicalCoordinatesTable` entries.

Each table carries **two independent region annotations** per electrode:

- `voxel_label_id` / `voxel_label`: the raw atlas voxel label at that coordinate (no interpolation). For D99 this is whatever the D99 parcellation says; for NMT it is the CHARM level-4 label; for MEBRAINS it is the numeric string form of the Julich Brain Macaque label ID. Special values: `"unlabeled"` (coord in-volume but on label=0), `"outside_volume"` (coord outside the template bounding box).
- `brain_region_id` / `brain_region`: a curated M1-constrained label. If the raw voxel is the atlas's native M1 label (F1_(4) for D99, M1 for CHARM, 4a/4p for MEBRAINS), it is kept. Otherwise the nearest M1 voxel within 5 mm is chosen, with the distance recorded in `brain_region_distance_mm` and the fallback flagged in `brain_region_lookup_method`.

The curation is dataset-specific to dandiset 001636 (all electrodes are ICMS-verified M1 at threshold <30 µA) and is documented in `documentation/nearest_neighbor_region_labeling.md`.

## The Two Templates: Key Differences

### D99 (Saleem & Logothetis, 2012; updated 2021)

- Single-subject histological atlas registered to MRI
- 0.25 mm isotropic, 368 cortical and subcortical regions
- Origin: anterior commissure (AC)
- Orientation: RAS
- Coordinate system: NIfTI world coordinates in mm
- The atlas used in this dataset for the original chamber-to-atlas transformation

### NMT v2.0-sym (Jung et al., 2021)

- Population-averaged MRI template from 31 rhesus macaques (symmetric variant)
- 0.25 mm isotropic
- Origin: defined by the template's NIfTI affine (not at AC; the AC is at approximately R=0, A=19.4, S=15.4 in NMT world coordinates)
- Orientation: RAS
- Comes with CHARM (cortical, 6 hierarchical levels) and SARM (subcortical) parcellations
- Horsley-Clarke aligned

The large offset between coordinate values in D99 vs NMT (approximately +16 mm in A, +14 mm in S) reflects the different origins of the two templates, not an error in the warp. The nonlinear warp also accounts for shape differences between the single D99 subject and the population average.

## Verification Results

### CHARM Cross-Validation

We looked up the warped NMT coordinates in the CHARM atlas (hierarchical cortical parcellation bundled with NMT) at its finest level (level 6):

| D99 Region | CHARM L6 Region | Count | Notes |
|-----------|----------------|------:|-------|
| F1_(4) | M1 | 123 | Direct match |
| F1_(4) | label_0 (boundary) | 36 | Unlabeled boundary voxels at cortical folds |
| F1_(4) | PMdc | 10 | Adjacent premotor region, within registration uncertainty |
| F2_(6DR/6DC) | PMdc | 39 | Direct match (F2 = dorsal premotor) |
| 3a/b | area_3a/b | 22 | Direct match |
| 3a/b | label_0 (boundary) | 20 | Boundary voxels |
| area_1-2 | areas_1-2 | 8 | Direct match |
| outside | label_0 | 9 | Already unlabeled in D99, also unlabeled in NMT |

The "mismatches" are almost entirely boundary voxels (label_0 at cortical fold edges) and adjacent-region assignments within the 1-2 mm registration uncertainty. No anatomically implausible assignments were found.

### Coordinate Smoothness

The D99-to-NMT mapping is smooth and monotonic on all three axes (R, A, S), as confirmed by the scatter comparison plot. There are no discontinuities or outliers, indicating the warp field is well-behaved in the recording region.

### Sanity Check: AC Origin

The D99 anterior commissure (0, 0, 0) maps to NMT (0.13, 19.4, 15.4). The R coordinate is near zero (the AC is on the midline in both templates). The A and S offsets reflect the different template origins and are consistent with the known geometry.

## Verification Scripts

All verification scripts are in `build/coordinate_verification/`:

| Script | Output | Description |
|--------|--------|-------------|
| `nmt_warp_verification.py` | `nmt_horizontal_slice_plot.html`, `d99_vs_nmt_scatter.html` | Batch warp all coordinates, CHARM cross-validation, NMT slice plot, axis scatter comparison |
| `d99_nmt_comparison_slices.py` | `d99_nmt_comparison_slices.html` | Side-by-side D99 (top) vs NMT (bottom) horizontal slices at matched levels |
| `horizontal_slice_plot.py` | `horizontal_slice_plot.html` | Original D99-only horizontal slice plot |
| `anatomical_coordinates_verification.py` | (console output) | D99 coordinate verification across 298 NWB files |

## Data Requirements

### Warp file

Download `warps_final_NMTv2.0-sym.zip` (5.3 GB) from [Zenodo](https://zenodo.org/records/4748589). Extract `NMTv2.0-sym_to_D99_CompositeWarp.nii.gz` to:

```
data/rhemap_warps/NMTv2.0-sym_to_D99_CompositeWarp.nii.gz
```

If this file is absent, the conversion gracefully skips NMT coordinates (D99 coordinates are still stored, standard NWB x/y/z fall back to D99-derived values).

### NMT template (for verification only)

The NMT v2.0-sym template and CHARM atlas are in `data/nmt_v2/`. These are not needed for the NWB conversion itself (only the warp file is needed), but are used by the verification scripts.

### Software dependency

The `antspyx` Python package provides `ants.apply_transforms_to_points`. It is listed in `pyproject.toml` dependencies.

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Single coordinate warp | ~2-3 s | Dominated by loading the 480 MB warp field |
| Batch warp (274 coordinates) | ~3 s | Warp field loaded once, all points transformed together |
| Full NWB conversion (1 session) | ~3 s additional | One coordinate per session |

For bulk conversions, the per-session overhead is ~2-3 seconds (warp field reloaded each session since `ants.apply_transforms_to_points` does not cache). The `batch_convert_d99_to_nmt` function is available for verification and analysis scripts that need to warp many coordinates at once.

## References

- Saleem KS, Logothetis NK (2012). "A Combined MRI and Histology Atlas of the Rhesus Monkey Brain in Stereotaxic Coordinates." Academic Press.
- Saleem KS et al. (2021). "High-resolution mapping and digital atlas of subcortical regions in the macaque monkey based on matched MAP-MRI and histology." NeuroImage, 245, 118759.
- Jung B et al. (2021). "A comprehensive macaque fMRI pipeline and hierarchical atlas." NeuroImage, 235, 117997.
- Sirmpilatze N, Klink PC (2020). "RheMAP: Non-linear warps between common rhesus macaque brain templates." NeuroImage, 226, 117519. Data: DOI 10.5281/zenodo.4748589.
