# Current leaf area and 3D surface handoff

Date: 2026-10-03. Recipient: next Codex session.

## Scope and status

Current measured leaves only. Future CompoundLeaf growth forecasting belongs to another session.
Implemented distortion-aware projected area, fixed-camera mesh/plane comparison, and explicit local patches preserving holes, disconnected tissue and folds. Full physical accuracy and curved-model work remain blocked.

Read the parent `공통규약.md`, project `AGENTS.md` / `CONVENTIONS.md`, latest LOG and TODO before changes. Codex owns `tools/` and `tools/tests/`; preserve core/config/human observations and other sessions' work.

## Environment and inputs

- Comparison CLIs use explicit `--study` JSON and fresh `--out` under `build/`. They do not directly read `TOMATO3D_*` environment settings. Use `python -X utf8` on Windows.
- Temperature, humidity, CO2, EC and pH are not inputs to this geometry calculation. Optional measured PPFD (umol/m2/s) and photoperiod (h/day) feed light summaries only.
- Common: plant/session/date identity, source images, calibrated camera matrix (px), distortion coefficients, image dimensions (px), fixed board poses (rotation rad, translation mm), source hashes and review states.
- Area route: saved leaflet masks with original crop coordinates, structure/hull XYZ (mm), capture style and optional explicit elevation-group/movement provenance. Depth retains the existing per-mask 20th percentile and minimum 5 hull points.
- Surface route: confirmed physical point IDs with per-image XY (px), fit and disjoint held-out images, boundary observations, patch identities/reviews, and numerical policies. Explicit charts use `point_ids`, `boundary_point_ids`, `hole_point_ids` plus hashed original-resolution `visible_support` masks. Multiple charts may share one leaflet.
- Optional independent measurements: `measurements/leaf_area.csv` and `measurements/light.csv`, joined by plant/date/session. Calibration must match estimator, camera, integration/grouping policies and capture style.
- Numerical settings control inverse distortion, integration convergence, triangulation quality, ray-plane conditioning and surface support/intersection checks. Full field definitions: `tools/LEAF_AREA_COMPARISON.md`. Synthetic settings are not physical acceptance thresholds.

## Outputs and interpretation

- Legacy/corrected projected area and supported partial area: cm2; original/used/missing pixel counts; measured elevation and camera centre.
- Candidate triangle vertices: board-frame mm; supported one-sided patch/compound area: cm2; unsigned normals and fit/held-out reprojection RMS: px.
- Calibrated whole-plant area is available only with compatible independent measurements. Optional DLI and projected-area light interception are not absorbed photons or photosynthesis.
- Files: `photos.csv`, `groups.csv`, `candidate_surfaces.csv`, `compound_areas.csv`, `patch_inventory.csv`, calibration summaries, source/policy audit JSONs and `viewer.html`.
- Missing is null/unavailable, never invented zero. Do not sum photo areas as tissue, add partial surfaces to calibrated totals, fill leaflet gaps, or promote candidates to optical-ready/physically validated.

## Code and verified results

- Code: `tools/leaf_area_geometry.py`, `leaf_area_compare.py`, `leaf_surface_compare.py`, their HTML viewers, and opt-in extensions to `tools/plant_traits.py`. Legacy default behavior is preserved.
- Results root: `build/leaf_area_implementation_20261003/`.
- `real_compare_04`: T1/T2/T3, 54 photographs, 4048 input/code hashes verified during execution; incomplete photo coverage remains explicit.
- `chart_hole_03`, `chart_disconnected_03`, `chart_fold_03`: synthetic topology/viewer checks only.
- `verification_03.junit.xml`: 111 focused tests passed. `requirement_audit_02.json` records remaining requirements.
- Detailed history: `handoff/CODEX_LEAF_AREA_3D_EXECUTION_2026-10-03.md`.

## Resume condition

The user confirmed that no reviewed curved-fitting contract, confirmed correspondence data or independent leaf-area references exist elsewhere. Existing pilot reviews contain 7 pending points and 0 human confirmations. Do not repeat searches/path requests or manufacture substitutes.

Next substantive work requires Claude's reviewed curved-fit/selection contract and/or actual confirmed observations and independent metric references. Requests are already in `handoff/TODO.md`. Preserve the full objective as incomplete until verified; do not restart completed tests or runs merely to report activity. This handoff does not authorize training, inference, remote jobs, uploads, pushes or native light simulation.

CLI reference: `python -X utf8 -m tools.leaf_area_compare --help` and `python -X utf8 -m tools.leaf_surface_compare --help`.

## First-leaf area normalization (user confirmed)

Use the first supplied labelled leaf's area as dimensionless 1: `relative_area = A_i / A_first`. Preserve absolute areas and the reference label. Normalize separately by plant/session/date/method/scope/view; do not derive first-leaf identity from proposed height-order names. Missing or zero reference means unavailable, with no silent substitute.

Implemented in `tools/relative_leaf_area.py` (CSV CLI) and the surface comparison CSV/report/viewer. Multiple supported patches sharing one leaf identity are summed before normalization. Surface ratios remain explicitly partial. See `tools/LEAF_AREA_COMPARISON.md` for input columns and commands.

Validation: 32 focused normalization/surface tests passed. Synthetic areas 20, 30, 10 produce 1, 1.5, 0.5; the two-chart folded example sums to 8.472135955 cm2 and has reference ratio 1. Results: `build/relative_leaf_area_20261003/`. These examples do not supply missing confirmed real leaf identities, whole-leaf measurements or physical validation.

## Current user decision superseding metric input for the preliminary calculation

Before physical measurement, fix the first labelled leaf to dimensionless 1 and compare other detections against it. Implemented: `tools/detected_leaf_area.py --batch <saved batch> --out <fresh build directory>` counts original-resolution saved mask foreground pixels; `--mode bbox` is an explicit separate box-occupancy alternative. No new inference, calibration or 3D input is needed. `area_px2 / reference_area_px2` is the dimensionless image-space ratio; never write this as cm2 or a missing physical measurement.

Reference: first manifest label per photo. Image annotation IDs are not confirmed cross-view leaf IDs. Preserve per-photo ratios and their reference IDs; do not infer L01 identity or combine views. Cached masks can be unreviewed; retain review, visibility and manual-edit provenance. No silent box fallback or replacement reference. Outputs: `relative_detected_leaf_areas.csv`, `audit.json`. Focused detection/normalization/surface regressions: 40 passed in 6.32 s.

Actual detection-only results: `build/detection_relative_leaf_area_20261003_01/relative_detected_leaf_areas_all.csv`, with per-plant audits in the same parent. T1/T2/T3: 435/489/394 per-photo detection observations across 54 images, all 1318 ratios computed. All 54 per-image first references equal 1. These counts are not unique physical leaves. CSV division/reference checks passed; no new inference or physical-area validation. The follow-on diffusion feasibility/specification deliverable is `handoff/CODEX_MULTIVIEW_DIFFUSION_INTEGRATION_SPEC_2026-10-03.md`.
