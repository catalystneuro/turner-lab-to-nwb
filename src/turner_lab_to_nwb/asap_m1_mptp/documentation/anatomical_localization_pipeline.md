# Anatomical localization pipeline

This document is the front door for the electrode-localization side of the conversion. It walks the full path from the author's raw chamber measurements to the region labels that appear in the NWB file and on the dandi-atlas viewer, states what each stage consumes and produces, and explains why the final labels look the way they do based on direct discussion with the data author.

For depth on any specific stage, the deep-dive documents are:

- [`anatomical_coordinates.md`](anatomical_coordinates.md): chamber coordinate system, the 35° tilt geometry, atlas descriptions (D99 / NMT / MEBRAINS), the NWB column schema, and what we deliberately do not store and why.
- [`cross_template_coordinate_conversion.md`](cross_template_coordinate_conversion.md): the D99 -> NMT and D99 -> MEBRAINS warps (RheMAP), ANTs point-vs-image convention, RAS/LPS handling.
- [`nearest_neighbor_region_labeling.md`](nearest_neighbor_region_labeling.md): the strict M1-only nearest-neighbour curation policy, the fallback target per atlas, why unconstrained NN was rejected, the distribution of curated labels across the 447 files.

## The pipeline in one diagram

```
  +------------------+      geometric transform      +------------------+
  |  Chamber coords  |  ─────────────────────────▶   |   D99 coords     |
  |  (A_P, M_L,      |  AP offset + 35° rotation     |  (RAS mm, AC     |
  |   Depth)         |  computed by Dr. Turner       |   origin)        |
  +------------------+                               +------------------+
        source data                                      Layer 1 output
        (authored by experimenter)                    (authored by author,
                                                      from author geometry)
                                                         │
                                                         ├─────────────────────────────┐
                                                         │   RheMAP nonlinear warp     │
                                                         ▼                             ▼
                                                 +------------------+       +----------------------+
                                                 |   NMT v2.0-sym   |       |   MEBRAINS 1.0       |
                                                 |   coordinates    |       |   coordinates        |
                                                 +------------------+       +----------------------+
                                                       Layer 2 output (derived, curator-computed)
                                                         │                             │
                                                         │                             │
                                  ┌──────────────────────┼─────────────────────────────┤
                                  │ voxel lookup         │ voxel lookup                │ voxel lookup
                                  ▼                      ▼                             ▼
                         +------------------+   +------------------+         +----------------------+
                         |  D99 raw label   |   |  CHARM-4 raw     |         |  MEBRAINS raw label  |
                         |  (voxel_label*)  |   |  label           |         |  (voxel_label*)      |
                         +------------------+   +------------------+         +----------------------+
                                                         │
                                     M1-constrained nearest-neighbour (5 mm cap)
                                                         │
                         ┌───────────────────────────────┼───────────────────────────────┐
                         ▼                               ▼                               ▼
                +------------------+          +------------------+            +----------------------+
                |  D99 curated M1  |          |  CHARM curated   |            |  MEBRAINS curated M1 |
                |  (brain_region*) |          |  M1              |            |  (brain_region*)     |
                |  always F1_(4)   |          |  always M1       |            |  always 303 (4p L)   |
                +------------------+          +------------------+            +----------------------+
                                                 Layer 3 output (curator-computed)

                 All six outputs land on each AnatomicalCoordinatesTable as separate columns.
```

## Stage by stage

### Stage 1: Source chamber measurements (authored)

- **Inputs:** `A_P`, `M_L`, `Depth` recorded daily during each recording session in the chamber-relative coordinate frame. Units: mm.
- **Origin:** cylindrical stainless-steel recording chamber center, chamber axis tilted 35° in the coronal plane so that electrode penetrations enter orthogonal to the cortical surface of M1.
- **Where it lives:** metadata tables `assets/metadata_table/ven_table.csv` and `leu_table.csv`.
- **Authority:** source data, authored by the experimenters.

### Stage 2: Author's geometric transform to D99 (authored)

Dr. Robert Turner (data author) converted the chamber-relative coordinates to D99 RAS world coordinates using a rigid geometric transform:

- **AP offset:** constant -8.2 mm shift from chamber center to the anterior commissure, because the chamber AP axis is parallel to the brain's AP axis with no sagittal tilt.
- **35° coronal rotation:** the chamber's Depth and M-L axes are coupled to the atlas R and S axes by a 2D rotation. Going 1 mm deeper moves the electrode tip roughly 0.74 mm ventrally and 0.68 mm medially in atlas space, matching cos(35°) = 0.82 and sin(35°) = 0.57 (small deviations come from cortical curvature).
- **No MRI registration.** The transform is geometric only; no individual imaging of either Venus or Leu was used.

- **Inputs:** chamber `(A_P, M_L, Depth)` and the chamber geometry constants.
- **Outputs:** ACx coordinates `(A_P_acx, M_L_acx, Depth_acx)`, stored alongside the chamber coordinates in the metadata table; then converted to D99 RAS `(R = -M_L_acx, A = A_P_acx, S = Depth_acx)` inside the conversion code.
- **Authority:** authored by Dr. Turner. This is the closest-to-source layer of the localization.

### Stage 3: Warp D99 to NMT v2.0-sym and to MEBRAINS 1.0 (curator-computed)

The D99 coordinate is warped independently into each of the two downstream template spaces using pre-computed nonlinear composite warps from the [RheMAP project](https://zenodo.org/records/4748589) (Sirmpilatze & Klink, 2020). The warps are atlas-to-atlas (D99 volume to NMT volume; D99 volume to MEBRAINS volume), not subject-specific.

- **ANTs point convention:** for point transforms the warp direction is reversed vs. image transforms. To move a point *from* D99 *to* NMT we apply the `NMTv2.0-sym_to_D99_CompositeWarp.nii.gz` warp; the MEBRAINS case is analogous with `MEBRAINS_to_D99_CompositeWarp.nii.gz`.
- **RAS/LPS bracketing:** ANTs operates in LPS; our coordinates are RAS. We negate R and A before the call and negate again on the result.
- **Precompute step:** `scripts/precompute_warped_coordinates.py` runs ANTs once for the full set of unique source D99 coordinates and writes `assets/metadata_table/warped_coordinates.csv`; the conversion code only looks up from this CSV at runtime (~3 s per ANTs call otherwise).
- **Inputs:** a D99 RAS coordinate and the relevant RheMAP warp file.
- **Outputs:** NMT v2.0-sym RAS coordinate (origin: ear bar zero) and MEBRAINS 1.0 RAS coordinate (origin: anterior commissure).
- **Authority:** curator-computed derivation. Adds warp uncertainty on top of the geometric-transform uncertainty already present in Stage 2.

Full ANTs invocation, verification, and sanity checks live in [`cross_template_coordinate_conversion.md`](cross_template_coordinate_conversion.md).

### Stage 4: Raw voxel lookup (curator-computed, honest answer)

For each of the three atlases, index the atlas's parcellation volume at the electrode coordinate and return the label at that voxel with no interpolation. Implemented by `lookup_d99_region`, `lookup_nmt_voxel`, and `lookup_mebrains_region` in `interfaces/electrodes_interface.py`.

- **Inputs:** a coordinate in the atlas's native RAS frame and the atlas's parcellation NIfTI plus label table.
- **Outputs per atlas:** a `(voxel_label, voxel_label_id)` tuple.
  - If the voxel is labeled: the label's full name and abbreviation / numeric ID.
  - If the voxel is in the template but carries label=0: the sentinel `"unlabeled voxel (label=0)"` / `"unlabeled"`.
  - If the coordinate is outside the template bounding box: `"outside template volume"` / `"outside_volume"`.
- **Where it lands in NWB:** the `voxel_label_id` / `voxel_label` columns on each `AnatomicalCoordinatesTable`.

These columns are the honest atlas answer. They are not what the dandi-atlas viewer renders on the map — they are the audit trail beneath the curated label.

### Stage 5: M1-constrained nearest-neighbour curation (curator-computed, best-available M1 label)

For each of the three atlases, independently, curate a label suitable for viewer display. Implemented by `lookup_d99_m1`, `lookup_charm_m1`, and `lookup_mebrains_m1`.

Policy (strict M1-only; full discussion in [`nearest_neighbor_region_labeling.md`](nearest_neighbor_region_labeling.md)):

1. If the raw voxel at the coordinate is the atlas's native M1 label (`F1_(4)` = 359 for D99; `M1` = 79 for CHARM-4; `301` / `303` = 4a / 4p left for MEBRAINS), preserve it. Method = `"exact"`, distance = 0.
2. Otherwise, find the nearest M1 voxel within 5 mm (Euclidean, in the atlas's world-coordinate frame). Use its label. Method = `"nearest_neighbor"`, distance = the real distance in mm.
3. If no M1 voxel is within 5 mm, emit the sentinel `brain_region_id = "outside"`, method = `"no_m1_within_5mm"`, distance = NaN. This does not fire on any electrode in dandiset 001636 (max observed distance is 4.18 mm).

The curated label is the one the dandi-atlas viewer reads.

- **Inputs:** coordinate in the atlas's RAS frame, the atlas's parcellation volume, and the set of M1 voxel indices (pre-built into a KD-tree at module load time).
- **Outputs per atlas:** `(brain_region, brain_region_id, brain_region_lookup_method, brain_region_distance_mm)`.
- **Scope:** this curation is specific to dandiset 001636 because every recording site here is ICMS-verified M1 (see the "Why the data looks this way" section below). It is not a general NWB pattern. On a mixed-target dandiset the policy would need to be revisited.

### Stage 5b: Coordinate curation (piggybacks on Stage 5's D99 NN)

The Stage-5 label curation picks the nearest F1_(4) voxel in D99 space to decide the label. Coordinate curation reuses that same voxel: take its voxel-center world coordinate as the curated D99 position, then run it through the same RheMAP warps from Stage 3 to get curated NMT and curated MEBRAINS positions.

- **Inputs:** raw D99 coord, the cached F1_(4) voxel KD-tree (same one Stage 5 uses), and the precomputed warp table (Stage 3).
- **Outputs:** `(curated_d99_r, curated_d99_a, curated_d99_s)`, `(curated_nmt_r, ...)`, `(curated_mebrains_r, ...)`.
- **Implementation:** `snap_d99_to_f1_voxel` in `interfaces/electrodes_interface.py` returns the curated D99 coord; `lookup_warped_coordinates` reads both raw and curated warps from `assets/metadata_table/warped_coordinates.csv` (regenerated by `scripts/precompute_warped_coordinates.py`).
- **Scope:** dataset-specific; coord curation is only sensible when label curation is. Shares the 5 mm cap with Stage 5 (the snap is only done when the raw coord is within 5 mm of F1; on 001636 that is always true).
- **Why this design (curate at D99, propagate) rather than per-atlas snapping:** the three curated coords all represent the same anatomical point (one F1 voxel, transported through the warp), preserving cross-atlas consistency. Per-atlas snapping would produce three different anatomical points and break the "these rows describe one electrode" contract. See `agent_conversation.md` rounds 7-8 for the full discussion.

### Stage 6: Write to the NWB file

Each `AnatomicalCoordinatesTable` (`D99v2AtlasCoordinates`, `NMTv2AtlasCoordinates`, `MEBRAINSAtlasCoordinates`) carries thirteen columns per row:

| Column | Stage | Meaning |
|---|---|---|
| `x, y, z` | 3 + 5b | **Curated** coordinate in the atlas's RAS frame, mm. For D99: nearest F1_(4) voxel center. For NMT/MEBRAINS: RheMAP warp of the curated D99. Viewer-facing. |
| `x_raw, y_raw, z_raw` | 2 or 3 | **Raw** coordinate in the atlas's RAS frame, mm (author's geometric transform for D99; RheMAP warp of the raw D99 for NMT/MEBRAINS). Honest uncurated position. |
| `localized_entity` | - | Row index into `nwbfile.electrodes` |
| `voxel_label_id` / `voxel_label` | 4 | Raw voxel lookup at the raw coord (honest atlas answer) |
| `brain_region_id` / `brain_region` | 5 | Curated M1 label (viewer-facing) |
| `brain_region_lookup_method` | 5 | `exact` / `nearest_neighbor` / `no_m1_within_5mm` |
| `brain_region_distance_mm` | 5 | 0 / NN distance / NaN |

Two invariants hold, one per curation axis:

- **Label invariant.** When `brain_region_lookup_method == "exact"`, `brain_region_id == voxel_label_id`.
- **Coordinate invariant.** The curated `x, y, z` always represents "the RheMAP warp of the nearest F1_(4) voxel center to the raw D99 coord." For D99 specifically, `(x, y, z) == nearest_F1_voxel_center` regardless of method, and `(x_raw, y_raw, z_raw) == output of author's geometric transform`.

These two curation axes are independent:

- The label uses the raw voxel lookup at the raw coord to decide `exact` vs `nearest_neighbor`.
- The coordinate curation always snaps (on this dataset) because every raw D99 coord is within 5 mm of F1. The snap distance may still be 0 if the raw coord already lies on a voxel center (rare) or small (typical for Venus exact-hit cases, where the raw coord is within one voxel of F1).

The `electrodes.x/y/z` field (standard NWB) is the curated NMT coord in PIR micrometers — this is what the dandi-atlas viewer uses for 3D dot positions on the NMT template.

The `Localization` container also carries three typed `Space` objects from `ndx-anatomical-localization` 0.1.0 (`D99v2Space`, `NMTv2Space`, `MEBRAINSSpace`) with canonical origin / units / orientation baked in.

## Why the data looks this way (conversations with Dr. Turner)

The author-provided D99 coordinates and our downstream atlas-based region labels do not always agree. Sending recording-position visualisations to Dr. Turner early in the integration surfaced three atlas-level reasons for the disagreement, each of which motivates the curation policy we ended up with.

Figures provided by Dr. Turner are stored in `assets/turner_correspondence/`. Full correspondence log is in `email_communication.md` at the repo root (section "Seventh Email" and onward, 2026-03-03).

### Finding 1: NMT and MEBRAINS templates overestimate sulcal gaps

Post-mortem tissue processing shrinks and distorts the cortex. In the NMT v2.0-sym and MEBRAINS templates, the banks of the central sulcus are pulled apart and the fundus is filled with unlabeled (label=0) voxels. In the living brain, those banks nearly touch (<1 mm gap). A Leu electrode that is anatomically inside cortical gray matter in vivo can land in "empty space" in the template — not because the coordinate is wrong, but because the template lost the tissue during processing.

- Figures: `in_vivo_central_sulcus.jpg` (in vivo MRI), `cicerone_central_sulcus.png` (Cicerone neuronavigation).
- Effect in our data: 100% of Leu MEBRAINS coordinates land on `unlabeled` voxels; 35% of Leu NMT coordinates land on `unlabeled`.
- Why curation absorbs it: the nearest labeled M1 voxel is always within 4.18 mm; the curated label pulls the electrode back onto the nearest intact M1 patch.

### Finding 2: D99 is vertically compressed

D99 is built from a single subject and, when overlaid on an in vivo MRI aligned to the anterior commissure, the dorsal part of the in vivo brain extends above D99's top boundary. Recording sites at dorsal/lateral positions can fall outside D99 simply because the D99 template is too short in the dorso-ventral axis.

- Figure: `d99_over_in_vivo_mri.png` (coronal overlay).
- Effect in our data: Leu's 61 D99 "unlabeled" cases and additional non-motor voxel hits are at the posterior-dorsal edge of the template, where D99's coverage is thinnest. Leu's D99 superior range (16.9-23.1 mm) is higher than Venus's (13.2-19.6 mm), explaining the subject-level difference.
- Why curation absorbs it: the same 5 mm NN fallback recovers these sessions because labeled M1 (F1_(4)) is always within range even when the raw voxel at the coordinate is label=0.

### Finding 3: D99 places the F1/premotor boundary too posteriorly

Dr. Turner flagged that modern cytoarchitectonic evidence (Matelli et al., DOI: 10.1016/s0013-4694(98)00022-4; Lemon review, DOI: 10.1146/annurev-neuro-070918-050216) puts the F1/F4 (M1/ventral-premotor) boundary roughly 2 mm anterior to the genu of the central sulcus. D99's boundary is positioned further posterior. Electrodes that are functionally M1 by ICMS therefore sometimes land on voxels labeled as premotor (F2 / F4) in D99's parcellation.

- Figure: `f1_f4_boundary_matelli1991.png` (cortical parcellation map from the Matelli paper).
- Effect in our data: 42 Venus D99 electrodes have raw voxel `F2_(6DR/6DC)` (premotor); 52 Venus NMT electrodes hit CHARM `PM`; 42 Venus MEBRAINS electrodes hit `F4d` left (307). None of these are actually premotor recordings — they're ICMS-verified M1 near the cytoarchitectonic boundary.
- Why the curation's strictness matters: a looser "any motor label" policy would have kept those F2 / PM / F4d labels and shown premotor dots on the map. The strict M1-only curation corrects them to F1_(4) / M1 / 303, matching the ICMS ground truth.

### The ground-truth anchor: ICMS microexcitability

Dr. Turner named ICMS as the strongest single-electrode evidence for M1 identity: **primary motor cortex is microexcitable at <30 µA (10 shocks at 300 Hz), unlike adjacent cortical areas (somatosensory S1, premotor F2 / F4, SMA).** Many recording sites in this dataset evoke movement at <10 µA. This is cytoarchitectonically specific to M1, not to motor cortex in general — premotor regions require 50-200+ µA in resting preparations.

The `icms_threshold_uA` column on the electrodes table carries this per-electrode. Every recording site in dandiset 001636 sits below the <30 µA threshold, which is why we treat any non-M1 raw voxel answer (somatosensory 3a/b, premotor F2, unlabeled) as a warp artifact rather than an alternative anatomical hypothesis.

### What Dr. Turner confirmed could not be improved

Dr. Turner reviewed his Venus chamber-position estimate after seeing the visualisation and reported he could not find obvious ways to improve it. There is intrinsic noise (~1-2 mm) in the original raw location data — the methods used at the time were not perfectly accurate at controlling electrode location, and cross-subject atlas registration adds its own uncertainty. The geometric transform is the best authored-side layer available; subject-native MRI data does not exist for either Venus or Leu.

That leaves ICMS as the authoritative per-electrode identity signal, the geometric transform as the best-available 3D position, and atlas voxel lookups as a third layer whose disagreements are informative about template / warp limitations rather than about recording errors.

## Summary table: authorities per layer

| Layer | What it carries | Authored by | Curator-computed? | Uncertainty source |
|---|---|---|---|---|
| 1 | Chamber `(A_P, M_L, Depth)` | Experimenters | No | Electrode-positioning instrument (~1-2 mm) |
| 2 | D99 `(R, A, S)` | Dr. Turner (geometric transform) | No | Geometric transform: no subject MRI, assumed 35° chamber angle exact |
| 3 | NMT, MEBRAINS `(R, A, S)` | RheMAP atlas-to-atlas warp | Yes | Warp uncertainty layered on top of layer 2 |
| 4 | Raw voxel labels | Atlas parcellation voxel lookup | Yes | Template sulcal-gap artifacts, D99 vertical compression, F1/PM boundary mismatch |
| 5 | Curated M1 labels (`brain_region_id`) | M1-constrained NN fallback (5 mm cap) | Yes | Dataset-specific; scope limited to 001636 |
| 5b | Curated M1 coordinates (`x, y, z`) | Snap raw D99 to nearest F1 voxel center, propagate via RheMAP (5 mm cap) | Yes | Same dataset-specific scope as layer 5; sub-mm residual gap between curated NMT/MEBRAINS and those atlases' own M1 meshes |

ICMS threshold (`icms_threshold_uA` on the electrodes table) sits alongside all of this as the ground-truth authority on whether each recording site is M1.

### How far the curated dot moves from the raw warp output

For each electrode the curated `(x, y, z)` differs from `(x_raw, y_raw, z_raw)` by the distance below (Euclidean mm). This is the amount the viewer dot shifts toward the M1 mesh under curation:

| Atlas | Venus (n=298) median / max | Leu (n=149) median / max |
|---|---|---|
| D99v2 | 0.14 / 2.73 | 2.10 / 3.89 |
| NMTv2 | 0.13 / 2.71 | 1.63 / 3.71 |
| MEBRAINS | 0.13 / 2.71 | 1.83 / 3.88 |

Venus median is tiny (~0.13 mm) because the snap quantises to voxel centers on a 0.25 mm grid; exact-hit electrodes shift at most half a voxel edge. Leu median is larger (~1.6-2.1 mm) because almost all Leu raw D99 voxels miss F1 (raw voxel reads `3a/b` or `unlabeled`), so the snap moves the coord meaningfully toward the F1 mesh. The D99 max (3.89 mm on Leu) is the largest M1-NN distance on the dataset; NMT/MEBRAINS maxima differ slightly because the RheMAP warp is not metric-preserving.

## Residual between curated NMT / MEBRAINS coord and the atlas's own M1 mesh

The curated D99 coord is the center of an F1_(4) voxel, so on the D99 viewer the dot lands exactly on the atlas's own M1 mesh. For NMT and MEBRAINS the curated coord is the **RheMAP warp of that curated D99 point**, not a point directly snapped to the downstream atlas's own M1. So the curated NMT coord lands close to a CHARM M1 voxel but usually not *exactly* on one, and similarly for MEBRAINS / 4a-4p. This section quantifies that residual and explains why it is intentionally left as-is.

### Empirical residual on 447 electrodes

Indexing each curated NMT / MEBRAINS coord against the target atlas's own M1 parcellation:

| Atlas / subject | Residual median (mm) | Residual max (mm) | Lands on atlas's native M1 voxel? |
|---|---|---|---|
| NMT / Venus | 0.194 | 0.675 | 45% direct hit, 37% adjacent unlabeled, 18% neighbouring motor (CHARM PM / SI) |
| NMT / Leu | 0.456 | 0.583 | 0% direct hit (all 149 land on unlabeled adjacent voxels) |
| MEBRAINS / Venus | 0.311 | 0.943 | 45% direct hit, 47% adjacent unlabeled, 8% F4d (307) |
| MEBRAINS / Leu | 0.737 | 0.886 | 0% direct hit (all 149 land on unlabeled adjacent voxels) |

The residual is always sub-millimeter (max 0.94 mm across the whole dataset). On a 0.25 mm NMT voxel grid that is 1-4 voxel widths; on the 0.20 mm MEBRAINS grid it is 1-5 voxel widths. Visually, at typical viewer zoom where the rendered dot is comparable in size to the voxel, the dot overlaps the mesh even when offset by a few voxels.

### Why we leave the residual alone: anatomical context

The residual sits inside every uncertainty floor we already accept:

| Reference size | Magnitude | Residual as fraction |
|---|---|---|
| Cortical layer 5 thickness (where our recordings live) | ~0.4-0.6 mm | 30-200% (residual can straddle one layer) |
| Macaque M1 full cortical thickness | ~2.0-2.5 mm | 10-45% (within the cortical sheet) |
| In-vivo central sulcus fundus gap | <1 mm | comparable |
| Post-mortem sulcal gap in NMT / MEBRAINS | 2-5 mm | residual is smaller than the gap we cannot eliminate anyway |
| Chamber-positioning noise (Dr. Turner, 2026-03-09 correspondence) | 1-2 mm intrinsic | residual is below this noise floor |
| RheMAP atlas-to-atlas registration uncertainty (general) | 1-2 mm typical | residual is below this |
| Label-curation NN distance on this dataset | 0.7-4.2 mm | residual is smaller than the label fallback |
| M1 arm representation extent (A-P) | 5-10 mm | 2-10% |
| Full M1 cortical strip (A-P) | 15-20 mm | 1-5% |
| Macaque whole-brain A-P length | ~75 mm | 0.3-1.2% |

The curation is cosmetic with respect to every source of uncertainty already present in the pipeline. Moving the coord further (by re-snapping it to the downstream atlas's own M1 voxel set) would only eliminate a sub-voxel offset that is anatomically meaningless.

### Why NOT per-atlas re-snapping

An alternative considered and rejected: snap each atlas's raw coord independently to that atlas's own M1 voxel set, producing three curated coords that each sit exactly on their atlas's M1 mesh. Costs of this approach:

1. **Cross-atlas consistency breaks.** The three curated coords would represent three different anatomical points. A user transforming the curated D99 coord through RheMAP to compare with the curated NMT coord would miss by ~0.5 mm because each coord was snapped independently to a different template's M1 boundary.
2. **Composability breaks.** Any downstream analysis that combines curated coords across atlases (e.g. "does the 4a/4p subdivision on MEBRAINS agree with the F1 anterior/posterior position in D99?") gets garbage answers.
3. **Explanation complexity.** Instead of "one snap at D99, propagated through the warp" the story becomes "one snap per atlas, three different M1 targets."

The visual gain of per-atlas snapping is eliminating a 0.2-0.9 mm residual that is already well below every other uncertainty source. The composability cost is real and permanent. We chose cross-atlas consistency.

## Brief glossary and context for reviewers not in the macaque neuroanatomy world

**Sulcus:** a groove/fold on the cortical surface. The central sulcus separates motor (anterior bank) from somatosensory (posterior bank) cortex and runs roughly dorsal-to-ventral on the lateral hemisphere.

**Bank:** one of the two walls of a sulcus. The anterior bank of the central sulcus is M1 (primary motor); the posterior bank is S1 (primary somatosensory).

**Fundus:** the deepest part of a sulcus, where the two banks meet. In the living brain the fundus gap is under 1 mm; in post-mortem templates it widens to 2-5 mm due to tissue shrinkage — the "sulcal gap artifact" that drives our M1 curation.

**Gyrus:** the ridge between two sulci. The precentral gyrus carries M1; the postcentral gyrus carries S1.

**Crown / lip:** the outermost part of a gyrus, where the sulci open at the cortical surface.

**Cortical layers:** six laminar bands stacked from pial (outside) to white matter (inside). Macaque cortex is ~2 mm thick. Layer 5 is ~0.5 mm thick and contains the pyramidal projection neurons we record from.

**Atlas voxel sizes across common templates:**

| Atlas | Species | Voxel edge | Relative to brain A-P length |
|---|---|---|---|
| Allen Mouse CCFv3 (full-res) | Mouse | **10 µm** | ~1/1200 |
| Allen Mouse CCFv3 (common, 25 µm) | Mouse | 25 µm | ~1/480 |
| Gubra mouse LSFM | Mouse | 20 µm | ~1/600 |
| Waxholm rat | Rat | 39 µm | ~1/770 |
| Riken marmoset | Marmoset | 100 µm | ~1/400 |
| **D99 v2 (macaque)** | Macaque | **250 µm** | **~1/300** |
| **NMT v2.0-sym (macaque)** | Macaque | **250 µm** | **~1/300** |
| **MEBRAINS 1.0 (macaque)** | Macaque | **200 µm** | **~1/375** |
| MNI152 (human) | Human | 1 mm | ~1/170 |
| MNI152 / AAL (common) | Human | 2 mm | ~1/85 |

Macaque atlases sit at the 0.20-0.25 mm voxel regime. Sub-mm residuals on these templates translate to 1-4 voxels — within the rendered dot size at typical viewer zoom and well inside the Dr. Turner ~1-2 mm chamber-noise floor we already accepted. On a mouse CCFv3 rendering the same 0.5 mm offset would be 50 voxels and conspicuously wrong; on a human MNI rendering it would be sub-voxel and invisible. The macaque regime is in between, where the offset is visible at voxel-level zoom but anatomically meaningless.

## Current table shape (example rows)

Across all 447 NWB files in dandiset 001636, each `AnatomicalCoordinatesTable` has exactly one row (single recording electrode per session) with the 13 columns documented in Stage 6. The tables below show two representative sessions side by side per atlas: **Venus v0502** hits M1 exactly on all three atlases (raw and curated coords almost identical), and **Leu l10001** requires the nearest-neighbour fallback on all three (curated coord shifts ~1-2 mm from raw toward the M1 mesh).

### `D99v2AtlasCoordinates`

Space: `D99v2Space` (name `D99v2`, origin anterior commissure, RAS, mm).

| Column | Venus v0502 | Leu l10001 |
|---|---|---|
| `x` (curated, R, mm) | -15.000 | -13.000 |
| `y` (curated, A, mm) | -4.250 | -7.750 |
| `z` (curated, S, mm) | 15.000 | 17.750 |
| `x_raw` (R, mm) | -15.023 | -13.006 |
| `y_raw` (A, mm) | -4.200 | -8.700 |
| `z_raw` (S, mm) | 15.024 | 17.449 |
| `localized_entity` | 0 (DynamicTableRegion into `nwbfile.electrodes`) | 0 |
| `brain_region_id` | `F1_(4)` | `F1_(4)` |
| `brain_region` | agranular frontal area F1 (or area 4) | agranular frontal area F1 (or area 4) |
| `brain_region_lookup_method` | `exact` | `nearest_neighbor` |
| `brain_region_distance_mm` | 0.0 | 0.9967 |
| `voxel_label_id` | `F1_(4)` | `3a/b` |
| `voxel_label` | agranular frontal area F1 (or area 4) | somatosensory areas 3a and 3b |

Note: Venus v0502 has `brain_region_lookup_method = "exact"` but the curated coord still differs slightly from the raw (-15.000 vs -15.023). That's because the snap goes to the F1 voxel *center*, and the raw coord sits inside the voxel but not at its center. The shift is always under half a voxel edge (0.125 mm on a 0.25 mm grid).

### `NMTv2AtlasCoordinates`

Space: `NMTv2Space` (name `NMTv2`, origin ear bar zero, RAS, mm).

| Column | Venus v0502 | Leu l10001 |
|---|---|---|
| `x` (curated, R, mm) | -14.707 | -12.794 |
| `y` (curated, A, mm) | 12.418 | 8.266 |
| `z` (curated, S, mm) | 28.929 | 30.667 |
| `x_raw` (R, mm) | -14.730 | -12.630 |
| `y_raw` (A, mm) | 12.364 | 7.619 |
| `z_raw` (S, mm) | 28.954 | 30.269 |
| `localized_entity` | 0 | 0 |
| `brain_region_id` | `M1` | `M1` |
| `brain_region` | primary_motor_cortex | primary_motor_cortex |
| `brain_region_lookup_method` | `exact` | `nearest_neighbor` |
| `brain_region_distance_mm` | 0.0 | 1.1724 |
| `voxel_label_id` | `M1` | `SI` |
| `voxel_label` | primary_motor_cortex | primary_somatosensory_cortex |

### `MEBRAINSAtlasCoordinates`

Space: `MEBRAINSSpace` (name `MEBRAINS`, origin anterior commissure, RAS, mm).

| Column | Venus v0502 | Leu l10001 |
|---|---|---|
| `x` (curated, R, mm) | -15.393 | -13.058 |
| `y` (curated, A, mm) | -6.500 | -10.647 |
| `z` (curated, S, mm) | 14.124 | 16.190 |
| `x_raw` (R, mm) | -15.402 | -12.928 |
| `y_raw` (A, mm) | -6.569 | -11.460 |
| `z_raw` (S, mm) | 14.130 | 15.741 |
| `localized_entity` | 0 | 0 |
| `brain_region_id` | `303` | `303` |
| `brain_region` | 4p left | 4p left |
| `brain_region_lookup_method` | `exact` | `nearest_neighbor` |
| `brain_region_distance_mm` | 0.0 | 1.4707 |
| `voxel_label_id` | `303` | `unlabeled` |
| `voxel_label` | 4p left | unlabeled voxel (label=0) |

### Reading these rows side by side

Venus v0502 and Leu l10001 record the same functional target (arm-representation M1, ICMS-confirmed in the Leu case) but their raw voxel answers differ across atlases:

- Venus lands exactly on each atlas's native M1 label in all three templates. The raw answer and the curated answer agree; `voxel_label_id == brain_region_id`; distance is 0.
- Leu lands on `3a/b` in D99, `SI` in CHARM-4 (NMT), and an `unlabeled` voxel in MEBRAINS. The raw answers are atlas-specific reflections of the same underlying warp artifact (coordinate near the sulcal fundus). The curation pulls all three back to the atlas's native M1 label with the real distance preserved (~1-1.5 mm in each atlas).

The invariant holds in both rows: `method == "exact"` iff `brain_region_id == voxel_label_id`.

### Aggregate distribution across 447 sessions

All 447 sessions emit the same `brain_region_id` per atlas, which is the point of the strict-M1 policy:

| Atlas | `brain_region_id` on all 447 rows |
|---|---|
| D99v2 | `F1_(4)` |
| NMTv2 | `M1` |
| MEBRAINS | `303` (4p left) |

`brain_region_lookup_method` distribution is what varies. Aggregated from the full local manifest:

| Atlas | Subject | exact | nearest_neighbor | no_m1_within_5mm | NN distance median / max (mm) |
|---|---|---:|---:|---:|---:|
| D99v2 | Venus | 182 | 116 | 0 | 0.81 / 2.73 |
| D99v2 | Leu | 2 | 147 | 0 | 2.10 / 3.89 |
| NMTv2 | Venus | 136 | 162 | 0 | 0.80 / 3.25 |
| NMTv2 | Leu | 0 | 149 | 0 | 1.98 / 3.60 |
| MEBRAINS | Venus | 122 | 176 | 0 | 0.70 / 3.43 |
| MEBRAINS | Leu | 0 | 149 | 0 | 2.47 / 4.18 |

The `no_m1_within_5mm` sentinel is never emitted — max observed NN distance across all 894 NN rows is 4.18 mm against a 5 mm cap. The per-session manifest of all 447 rows (30 columns, including raw x/y/z in every atlas) is at `location_manifest.csv` at the repo root.
