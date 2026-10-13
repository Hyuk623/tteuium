# Top view -> 3D -> rendered side view: execution report (2026-10-12)

Executes `handoff/CLAUDE_CODE_CLI_PROMPT_TOP_TO_3D_2026-10-12.md`. Implementer: Claude Code. Korean summary:
`TOP_TO_3D_EXECUTION_2026-10-12_KO.md`. Outputs: `build/topview_20261012_01/`.

## 0. Read / missing
Read: CONVENTIONS.md, LOG tail, `docs/정의집_토마토_2026-10-11.md`, LABEL_CLASS_SCHEMA, DETECTOR_POLICY (+10-12 status),
MTG_CONVENTION (A1.5, 8.3/8.4 on hold, 12.3, A3-A5), skeleton spec sections 2/6.4/6.9, `tomato3d/synth/{labels_json,
sideview,scene,structure,leaflet_surface,compound_leaf}.py`, `tomato3d/state/potscale.py`, `tools/leaflet_segmenter.py`,
the recon/twoview/fuse3d stubs, O-mature manifest + scene_0000 graph/index, R_contract camera geometry.
**Missing:** claude.ai doc `상면3D_흐름검토_2026-10-12` (not on disk; the prompt was used). `P1_EXECUTION` /
`P1_SIDESHOOT_EXECUTION` were skimmed via LOG only.

## 1. Where the code lives and why
New package **`tomato3d/topview/`** (calibration, measure2d, geometry + `topview_config.json`) and
**`tomato3d/synth/pairs.py`** (T2). The prompt asked to fill `twoview`/`recon`/`fuse3d`; they do not fit:
`twoview` (skeleton 6.9) takes a top AND a side image on the board and states it is "not a full 3D reconstruction";
`recon` carves a visual hull from many board poses; `fuse3d` lifts masks onto that reconstruction. A single
board-less top photo has none of those inputs. They remain stubs.

**Spec tension to note:** skeleton 6.9 warns that 3D from few views "would be a learned prior, and measurements
taken off that prior are not traceable to observation". This flow is exactly that, so every inferred value carries
an `inferred_*` status and `optical_readiness = conditional_completion` is the ceiling (as the prompt says).

## 2. Per task

| task | state | what exists |
|---|---|---|
| T0 calibration intake | **done; result `unavailable`** | `tomato3d/topview/calibration.py`; template + README `build/leaf_bend_template/`; output `t0_calibration.json` |
| T1 real top -> 2-D | **done** (px only; mm `unavailable`) | `tomato3d/topview/measure2d.py`; end-to-end run `real_IMG_8419/` |
| T2 paired dataset | **code done, gated closed** | `tomato3d/synth/pairs.py`; refusal verified; 1-scene smoke `t2_smoke_uncalibrated/` (`not_for_training: true`) |
| T3 geometry model | **learned model blocked (needs T2)**; analytic baseline done + scored | `tomato3d/topview/geometry.py`; `t3_baseline_eval_synthetic.json/.csv`; real `real_IMG_8419/geometry_baseline.json` |
| T4 side render + agreement | **blocked** | no 3D estimate to render (T3 learned model); real side direction labels absent (R.5 waits for the 52 human labels); `tomato_side_nonboard` has 0 images |
| T5 P1 package | **blocked** | needs T3; a baseline-only package would present inferred tilt without a sign prior |

### T0 - calibration
- `data/records/leaf_bend/leaf_bend_records.csv` is **absent** -> `BENT_FRACTION unavailable`, theta `unavailable`,
  **T2 gate closed**. Template columns: record_id, plant_id, capture_datetime, photo_file, photo_sha256, axis, rank,
  bend_type (flat/bent/intermediate/unknown), theta_deg (A1.5), alpha_deg (12.3, `;`-separated), curl_note, observer,
  note. Angles only; the README tells the recorder to log EVERY judgeable compound (a fraction from hand-picked
  examples is biased).
- `records/compound_bend_types_20261010` (7 typed examples, no theta) is **not counted**: illustrative picks.
- Definition choice to confirm: `BENT_FRACTION = n_bent / (n_flat + n_bent + n_intermediate)`, intermediate reported
  separately (8.4 on hold).
- **Generator audit (O-mature)** - conflicts with measured facts, independent of bending:
  - leaflet true L/W: generator p10/p50/p90 **0.89 / 1.19 / 1.51**, only 16 % inside the measured 1.4-1.7. Cause:
    library contours are top-view masks (already foreshortened) and `leaflet_width_scale` 1.2-1.5 (`user_assumed`,
    tuned in pilot 1 together with `leaflet_roll_deg` 10-60) widens them. The pair was tuned to match the TOP
    PROJECTION, so the 3D truth is wrong while the projection looks right.
  - compounds per plant 6-8 vs real 4-5 (`user_stated`).
  - `rachis_droop_deg` 10-70 `user_assumed`: one continuous droop, no flat/bent mixture, so BENT_FRACTION has nowhere
    to enter until the generator gets a bend-type mixture.
  - blade curl on hold (MTG 8.3); the generator's roll is not a curl measurement.

### T1 - real top -> measured 2-D
Detector v4 boxes (leaflet classes, `measure_min_confidence` 0.25 = F1-best on the 4 real reference photos,
`derived_provisional`) -> SAM 2.1 tiny box prompt on one embedding, best of 3 masks, clipped to its box (leak share
reported) -> area_px, min-area-rect length/width, second-moment axis angle (mod 180, tip not resolved), centroid.
`vis_frac = unavailable` on real photos. mm only through `potscale` rim records; none exist -> **all mm
`unavailable`**, px values only (no image-wide scale).
End-to-end photo: `IMG_8419.jpg` (original 3024 px, the v4 **test** split, never trained on; downloaded from the
Roboflow project). 34 leaflets (leaf 23, terminal 8, leaf2 3), 0 empty masks, ~3 min on CPU. Two detections near
the bottom-left belong to a **neighbouring plant**: per-plant attribution needs the rim record (pot boundary); not
solved here. The `date_data/` photos are multi-pot TRAYS (not the v4 domain) and were not used.

### T2 - paired dataset
Per scene: top views (look-at cameras) + 4 side views (R.1 side geometry, `R_contract.json`), each one raster pass of
`parts.npz` with per-part instances (`labels_json.instance_plan`): visible ids, organ, depth, valid, packed amodal per
instance; `truth.json` with per-leaflet one-sided mesh area, midrib length, chord elevation, mean normal tilt,
bend/roll/twist, compound direction (board frame), rank, rachis length; `dataset.json` header with calibration
sha + gate state, geometry sha, generator config sha, seeds, parameter hashes. **Refuses** with the gate closed
(tested). The smoke run used a declared `provisional_smoke` top geometry (elevation 85+-3, 270 mm) - the real
board-less top framing (camera height / zoom, plant ~0.66 of frame) is unmeasured; in the smoke the plant fills ~1/3.
Not yet built: generating NEW scenes with calibrated parameters (needs the generator bend-type mixture + T0 values).

### T3 - baseline (no learned model)
Pure-pitch aspect prior: `e = acos(r_proj / r_true)`, `r_true` in 1.4-1.7; true length/area = projected / cos e;
sign `unavailable`; ratio > 1.7 flagged. Scored on 753 leaflet-views of the 30 O-mature top views against mesh truth
(median rel. error / median |rel. error|):

| vis_frac | n | area, amodal mask, no correction | area, amodal, prior | area, VISIBLE, prior | length, visible, prior |
|---|---|---|---|---|---|
| >= 0.9 | 174 | -0.169 / 0.169 | -0.008 / 0.161 | -0.037 / 0.171 | +0.038 / 0.106 |
| 0.5-0.9 | 266 | -0.175 / 0.175 | -0.023 / 0.166 | -0.376 / 0.376 | -0.077 / 0.122 |
| < 0.5 | 313 | -0.171 / 0.171 | -0.030 / 0.198 | -0.849 / 0.849 | -0.442 / 0.442 |

Readings: (1) the prior removes the ~17 % projection bias on average but leaves ~16 % per-leaflet scatter;
(2) **occlusion dominates** what a real photo gives (visible mask): -38 % and -85 % area in the occluded bins -
amodal completion is the job of the learned model; (3) **the synthetic check cannot validate the prior for real
plants**: with the generator's own L/W (oracle) the error is -16 %, i.e. the prior "works" here only because the
generator's too-wide leaflets and its roll cancel in projection (T0 audit). Real photo IMG_8419: projected ratio
p10/p50/p90 1.11/1.33/2.44; **9 of 34 leaflets above 1.7** (roll, curl or occlusion-cut masks).

## 3. Section 4 items
- O-mature realism failure: affects T3 evaluation relevance (wrong leaflet aspect, too many compounds) - numbers
  describe the generator, not real plants. Would also poison T2 training -> gate.
- `camera_pose_gate_passed = false` on all 180 O-mature views; reprojection **2.66-9.47 px** (the prompt said
  3.6-9.5; top views 2.66-5.13). Effect: none on label/truth correctness (masks and truth are computed in the same
  given pose); only the viewpoint distribution is borrowed from imperfect real poses. T2 uses synthetic look-at
  cameras (exact by construction), so T2 is unaffected.

## 4. Open items for the user
1. Fill `data/records/leaf_bend/leaf_bend_records.csv` (template `build/leaf_bend_template/`) - opens T2.
2. Confirm the BENT_FRACTION definition (intermediate in the denominator).
3. Decide how to fix the generator leaflet shape (L/W 1.19 vs 1.4-1.7): measure flattened leaflets (the destructive
   capture protocol exists) and re-derive width_scale/roll, or keep the projection-tuned pair.
4. Rim points for real top photos (`data/records/pots/`) - without them no mm and no per-plant attribution.
5. Real board-less top framing (camera height / zoom) for the T2 top cameras.
6. Real side direction labels (R.5) for T4.

## 5. Tests
New `tests/test_topview.py` (13 tests). Full `tests/`: **456 passed, 1 skipped** (571 s).

## Addendum 2026-10-12 (real-link session)
- Rim-plane bias SIGN: this report never stated a direction, but the T1 outputs in build/topview_20261012_01 did ("underestimates") - wrong; leaves above the rim are OVERestimated (d / (d - h cos tilt)). Corrected in code and noted in build/topview_20261012_01/CORRECTION_2026-10-12.md.
- Open items 4 (rim points) and 5 (top framing) are answered: the user clicked all 13 top rims; per-photo pose 193-278 mm / tilt 1-32 deg (approximate). See handoff/TOPVIEW_REAL_LINK_EXECUTION_2026-10-12.md.
