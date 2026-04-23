# M1-constrained nearest-neighbour region labeling

This document records the policy and reasoning behind the `brain_region_id` / `brain_region_lookup_method` / `brain_region_distance_mm` / `voxel_label_id` columns on the three `AnatomicalCoordinatesTable` entries (D99, NMT, MEBRAINS) in dandiset 001636.

## Problem

Every recording site in the dandiset is primary motor cortex confirmed by intracortical microstimulation at <30 µA (`icms_threshold_uA` column on the electrodes table). But the three atlas voxel lookups disagree with this identity for a large fraction of electrodes:

- Venus M1 exact hits: 61% D99, 46% CHARM-4, 41% MEBRAINS 4a/4p.
- Leu M1 exact hits: 1% D99, 0% CHARM-4, 0% MEBRAINS.

The remainder land on non-motor atlas labels (most often S1) or on unlabeled voxels. Three compounding causes:

1. **Post-mortem sulcal gap.** Template parcellations have unlabeled voxels at the central sulcus fundus where post-mortem tissue shrinkage opens a gap. Electrodes descending through the anterior bank of the central sulcus often land in that gap even though *in vivo* the tissue is present and motor.
2. **Warp artifacts.** NMT and MEBRAINS coordinates are warped from D99 via RheMAP (atlas-to-atlas, no individual MRI). The warp can shift a coordinate across the M1/S1 boundary.
3. **D99 template limitations.** D99 places the F1/F2 (M1/PMd) boundary more posteriorly than modern cytoarchitectonic evidence suggests (Matelli et al.; Lemon review). Arm M1 extends onto the gyral surface anterior to the central sulcus bank.

All three effects produce the same pattern: ICMS-verified M1 electrodes whose raw atlas voxel reads somatosensory, premotor, or unlabeled.

## Policy

Two independent region annotations per electrode on each of the three tables:

1. **`voxel_label_id` / `voxel_label`** — raw atlas voxel answer. No interpolation. Honest reporting of what the atlas physically labels at that coordinate. Special values: `"unlabeled"` when the voxel is inside the template but carries label=0; `"outside_volume"` when the coordinate falls outside the template bounding box.
2. **`brain_region_id` / `brain_region`** — curated M1-constrained label. If the raw voxel is the atlas's native M1 label (F1_(4) for D99, M1 for CHARM-4, 4a or 4p for MEBRAINS), preserve it. Otherwise, find the nearest M1 voxel within a 5 mm cap and use its label. Record the Euclidean distance in `brain_region_distance_mm` and the path taken in `brain_region_lookup_method` (`"exact"`, `"nearest_neighbor"`, or `"no_m1_within_5mm"`).

The curated value is what the dandi-atlas viewer displays. The raw value is for anyone who wants to interrogate the atlas directly or audit the curation.

## Why strict M1-only fallback

Only the atlas's specific M1 label triggers the `"exact"` path. Any other label, including other motor areas (D99 F2/F3/F4/F5/F6/F7 premotor and SMA; CHARM PM and SMA/preSMA; MEBRAINS F6 preSMA), is treated as warp artifact and corrected.

This is stricter than "keep any motor label." The reasoning:

- ICMS at <30 µA is cytoarchitectonically specific to M1, not to motor cortex broadly. Premotor areas (PMd, PMv) and SMA typically require 50-200+ µA to evoke a response in resting preparations.
- In the Matelli/Rizzolatti agranular-frontal-cortex classification, F1 is the only primary motor area; F2-F7 are higher-order motor areas with fundamentally different functional identities (planning, selection, sequencing; projection to brainstem rather than spinal cord).
- A Venus electrode whose raw D99 voxel reads F2 is therefore an M1 recording where the geometric transform crossed the F1/F2 boundary in the atlas, not a premotor recording.

The `voxel_label_id` column preserves the original F2 / PM / preSMA hits so that anyone interested in which electrodes fall near the M1/PM boundary can still query them.

## Fallback targets per atlas

| Atlas | M1 label(s) kept as `"exact"` | Fallback target for NN |
|---|---|---|
| D99 v2 | F1_(4) (label id 359) | nearest F1_(4) voxel |
| NMT v2.0-sym (CHARM level 4) | M1 (index 79) | nearest M1 voxel |
| MEBRAINS 1.0 (Julich Brain) | 4a (301) or 4p (303) | nearest of {4a, 4p} |

MEBRAINS is the only atlas whose native parcellation subdivides M1 (anterior vs posterior area 4). The NN picks whichever subdivision is closer, preserving the A-P position information. CHARM never subdivides M1 (a single label at every level 4-6). D99 does not subdivide F1.

**On this dataset the 4a/4p granularity collapses to a single value.** Every one of the 447 electrodes is closer to 4p (303) than to 4a (301), with a median margin of 2.62 mm (minimum 0.56 mm, maximum 6.30 mm) and 4a often beyond the 5 mm cap entirely (100/447 electrodes have no 4a voxel within reach). The anatomical reason is that 4a sits on the precentral gyrus crown while 4p extends into the anterior bank of the central sulcus; the Turner chamber is tilted 35° coronal and aims electrodes at the arm representation on the sulcal bank, putting every recording site on the 4p side of the 4a/4p boundary. `brain_region_id` on the MEBRAINS table is therefore `"303"` (4p left) for every session in dandiset 001636. The subdivision advantage of MEBRAINS remains real in principle, but only materialises if a future dandiset's electrodes span the crown-vs-bank boundary.

## Cap

5 mm. If the nearest M1 voxel is farther than 5 mm, emit `brain_region_id = "outside"` and `brain_region_lookup_method = "no_m1_within_5mm"` (the `"outside"` sentinel maps to OUTSIDE_ID in the dandi-atlas viewer). This does not fire on this dataset (max observed distance is 4.47 mm in Leu MEBRAINS) but the schema supports it.

The 5 mm cap is a sanity limit, not a tuned parameter. On this dataset any electrode that required >5 mm to reach labeled M1 would be a sign of something wrong upstream (coordinate corruption, mismatched atlas, wrong subject). Smaller caps were considered but would cut into the legitimate sulcal-gap cases; the worst genuine gap on Leu MEBRAINS is 4.18 mm.

## Why unconstrained NN was rejected

An alternative policy ("snap to any labeled region, including non-motor") was tested and rejected. For Leu, 100% of NMT electrodes snapped to somatosensory cortex (CHARM SI) under unconstrained NN, because the S1 bank of the central sulcus is geometrically closer in the template than the M1 bank across the sulcal gap. This is correct geometry but wrong science: the electrodes are ICMS-verified M1. The unconstrained answer would have labeled the entire Leu dataset as sensory recordings on the map, which is misleading.

M1-constrained NN deliberately ignores closer non-motor labels and searches only within the M1 voxel set. It produces an answer that agrees with the ICMS ground truth, at the cost of making the atlas's own voxel labels less visible on the map. The `voxel_label_id` column exists to restore that visibility for anyone who wants it.

## Scope and dataset specificity

This policy is **specific to dandiset 001636** (ICMS-verified motor cortex recordings). It is not a general pattern for NWB conversion. If the same pipeline is applied to a dataset with mixed cortical targets (e.g., M1 + S1 + PMd), the fallback must either be disabled or use a per-electrode-class target derived from some other ground truth. The table-level `method` string on each `AnatomicalCoordinatesTable` documents this scope explicitly, so downstream users know the curated label is a convenience, not atlas authority.

## Distribution on the 447 files (after reupload)

Expected `brain_region_lookup_method` distribution per atlas, computed from the locally converted NWB files:

| | Venus (n=298) | Leu (n=149) |
|---|---|---|
| **D99** exact | 61.1% | 1.3% |
| **D99** nearest_neighbor | 38.9% | 98.7% |
| **D99** no_m1_within_5mm | 0% | 0% |
| **NMT (CHARM M1)** exact | 45.6% | 0.0% |
| **NMT (CHARM M1)** nearest_neighbor | 54.4% | 100.0% |
| **MEBRAINS (4a/4p)** exact | 40.9% | 0.0% |
| **MEBRAINS (4a/4p)** nearest_neighbor | 59.1% | 100.0% |

Median NN distances: Venus 0.4-0.8 mm across atlases; Leu 0.6-2.5 mm across atlases. Max observed: 4.47 mm (Leu MEBRAINS).

## Future work

The dandi-atlas viewer reads only `brain_region_id`, which means the `"outside"` sentinel is overloaded: it could mean the coord is outside the template volume entirely, or in-volume but beyond the 5 mm cap. The NWB schema distinguishes these cases (via `voxel_label_id = "outside_volume"` vs `voxel_label_id = "unlabeled"`), but the viewer cannot. If the sentinel ever starts firing on real data, the options to address this are either (a) use two distinct sentinel strings in `brain_region_id` and extend the viewer's OUTSIDE_ID routing, or (b) surface `brain_region_lookup_method` alongside `brain_region_id` on the viewer side. See the agent conversation at `~/development/work_repos/dandi-atlas/agent_conversation.md` for the discussion trace.

## Schema-change checklist for future updates

Lesson from the 2026-04 reupload coordination with the dandi-atlas viewer side: the `AnatomicalCoordinatesTable` container names (`D99v2AtlasCoordinates`, `NMTv2AtlasCoordinates`, `MEBRAINSAtlasCoordinates`) renamed silently when the ndx-anatomical-localization 0.1.0 release landed, because we renamed them to match the typed-Space canonical names. The viewer had hardcoded HDF5 paths and broke on the refetch. For any future schema change, the summary communicated to downstream consumers must include:

1. **Column list** (names, dtypes, meaning).
2. **Table container names** (HDF5 paths under `general/localization/`).
3. **Space object names** and their typed Python class.
4. **Any renames** with the old->new mapping explicitly written out.

The ndx-anatomical-localization `NMTv2Space` corresponds to the symmetric NMT v2.0 template; the asymmetric variant is a separate `NMTv2AsymmetricSpace` class with `space_name = "NMTv2Asymmetric"`. If a future dandiset uses the asymmetric variant, the current `NMTv2AtlasCoordinates` table name would collide; consider `NMTv2SymAtlasCoordinates` / `NMTv2AsymAtlasCoordinates` at that point to preserve the disambiguation.
