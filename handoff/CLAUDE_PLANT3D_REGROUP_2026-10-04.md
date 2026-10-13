# Whole-plant 3D rerun with measured-elevation grouping (dwt_t1-t3)

Claude Code, 2026-10-04. User chose "whole-plant 3D rerun" over continuing ViewFusion, because the measured hull already explains held-out image 13 better than generated views (envelope IoU 0.57 vs 0.49, `build/mapping_validation_20261004_02/comparison_note.md`). Root: `build/plant3d_regroup_20261004_01/`.

## Kaggle check (before the rerun)

Kernel `dolgfish/tomato-viewfusion-trial-04` (v8) and `dolgfish/tomato-color-cues-infer` (v2) are COMPLETE. Dataset `tomato-viewfusion-trial-04-inputs` holds `*_execution_package_07` (r04). Re-downloaded v8 output: both candidate bundles and all 80 PNGs are hash-identical to `build/multiview_completion_20261004_04/kaggle_out_v8`.

## What ran

- `make_configs.py` copies each plant's existing pipeline config (T3: `plants_pose_AB1.json`, the A+B1 pose session) and adds `view_grouping` = `build/p1_r03_program_update_20261004_01/view_grouping.json` unchanged (board centre (95,-57,0), top if elevation > 70 deg). Source hashes are in `configs_manifest.json`.
- `tools.plant_pipeline` S0-S8 per plant into `run2_<plant>/`. All three reach S8; S2/S5/S6 wait for optional human work as before.
- The first attempt (`dwt_t*/`, kept) failed in S3. Cause: `tools/plant_structure.py:655` (sha256 4ea79500...) hashes `info` with numpy int64 inside, which raises `TypeError: Object of type int64 is not JSON serializable` on every real run with a view grouping. `tools/` is Codex-owned and was not changed: a briefly applied one-line fix was reverted to the identical original (hash rechecked; 11 focused tests passed with the fix). The rerun goes through `run_pipeline.py` + `s3_safe.py`, which convert numpy scalars to plain Python before the existing `digest` and otherwise call the unchanged module.

## Results (`comparison.json`, `regions_old_vs_new.csv`)

Measured grouping (elevation): T1 top = 27/28 (83-84 deg), T2 top = 17/18 (89 deg), T3 A+B1 has no top view (all 11 posed photos 30-38 deg). 01/03 are ring views in all three.

| Plant | Before (filename grouping) | After (measured grouping) | Hull |
| --- | --- | --- | --- |
| dwt_t1 | L01-L05, z 75.5-118.5 mm | identical regions, voxels and names | 68.7 cm3, unchanged |
| dwt_t2 | 6 unnamed regions (did not match 4 growth-record leaves) | 5 regions: L01-L04 + growing_leaf; unassigned voxels 8029 -> 5979 | 81.3 cm3, unchanged |
| dwt_t3 (A+B1) | L01-L04 at 72.5/73.5/87.5/102.5 mm | L01-L04 at 72.5/82.5/101.5/105.5 mm; unassigned 2920 -> 2417 | 59.6 cm3, unchanged |

- Hull carving does not use grouping, so hull volume/height/stem are unchanged; only compound-region assignment changes.
- Codex's "12 candidate regions" for T1 (`region_review.json`) counts candidate entries including single-box ones; its diagnostic CSV has the same 5 voxel-bearing regions as this run. No conflict.
- Names are still a height-order proposal. T2 and T3 regions changed and need a look in `run2_<plant>/<plant>/hierarchy/viewer.html` before any name is confirmed (bind names to the new `region_assignment_hash` in `comparison.json`).

## S8 traits still use filename groups

`traits.json` is identical before/after: `tools/plant_traits.py:45 view_group(code)` assigns top/side from the photo number, and the means at lines 130-135 use that group. `view_geometry` is recorded per row but not used. For this dataset S8 "top leaf area" therefore averages 01/03 (ring views). The elevation-based values computed on 10-03 are in `build/dwt_test_fill_20261003/traits_by_elevation.csv` (T1 ring 11.77 cm2 / top 10.03 cm2; T2 13.99 / 17.50; T3 13.35 / 16.11). These are model-only, uncalibrated diagnostics.

## Not done

No region names confirmed, no calibration, no new inference/training, no change to `tools/`, `config/` or earlier outputs. `validated_metric=false`, `suitable_for_ppfd=false` as before.
