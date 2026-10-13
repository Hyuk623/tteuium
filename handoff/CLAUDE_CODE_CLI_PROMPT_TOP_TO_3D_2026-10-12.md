# Claude Code — top view → 3D → rendered side view (2026-10-12)

Implementer: Claude Code. Goal (user decision 2026-10-12): from ONE real top-view photo, estimate the plant's 3D
structure and **render the side view from that 3D** — never generate a side image directly from a top image. The
deliverables are leaf area and tilt; the rendered side view is the validation artifact.

Korean design note (read it, it is the source of these decisions): claude.ai project doc `상면3D_흐름검토_2026-10-12`.

## 0. Read first (list what you read and what is missing)
`CONVENTIONS.md`, last 40 LOG lines, `docs/정의집_토마토_2026-10-11.md`,
`handoff/LABEL_CLASS_SCHEMA_2026-10-12.md`, `handoff/DETECTOR_POLICY_2026-10-09.md` (+ the 2026-10-12 status
update), `handoff/MTG_CONVENTION_2026-10-10.md` (A1/A2/§13/A3/A4), `handoff/P1_EXECUTION_2026-10-11.md`,
`handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md`, `tomato3d/synth/{labels_json,leafarea,sideview,scene,structure}.py`,
`tomato3d/{recon,twoview,fuse3d}/` (all stubs today), the O-mature run's `manifest.jsonl`, one scene's
`plant_graph.json` + `leaflet_index.json`.

## 1. Why this works, and the one thing that must hold
A leaflet's true length/width ratio is narrow (1.4–1.7, measured). A leaflet appearing at ratio 0.5 in a top view
is tilted by a recoverable amount. The synthetic runs already carry, per view: RGB, **depth in mm**, **amodal
masks**, per-organ masks, and the 3D truth (`plant_graph.compounds[].direction_unit`, `rachis_arc_length_mm`;
`leaflet_index[].length_mm`). The same organ carries the SAME id in the top and the ring views, so top↔side pairs
need no manual matching.

**Must hold:** the generator's bending must resemble real Micro-Tom. Today it does not — `BENT_FRACTION` is 0
(unmeasured), the flat/bent θ boundary is on hold, blade curl is undefined, and O-mature draws 6–8 compounds per
plant against a real 4–5. **Calibration (task T0) comes before bulk generation.** Training on uncalibrated
scenes yields software that runs and answers wrongly on real photos.

## 2. Separation that makes the domain gap small
- The **detector** is trained on real photos (Roboflow `tomato_top_nonboard` v4) — texture/colour live there.
- The **geometry model** is trained on synthetic **masks**, not RGB. Mask shape is texture-free, so the
  synthetic↔real gap that R.1 found in backgrounds barely touches it.
Never feed synthetic RGB to the geometry model "for realism"; if you think you need it, report why instead.

## 3. Work orders

**T0 — generator calibration from side close-ups (gate for T2).**
Build the intake that turns side close-up photos into the generator's bending parameters: a human-recorded table
(`data/records/leaf_bend/` — human-owned, read-only to you; ship a template + README under `build/`) of
per-compound type (flat / bent / intermediate), measured θ and α where the A1.5 points are visible, curl note,
plant and rank. From it derive `BENT_FRACTION` and the θ distribution, each `source_kind = measured` with n.
Close-ups carry no scale — take ANGLES only from them, never lengths. If the table is empty, T0 reports
`unavailable` and T2 must not run with invented values.

**T1 — real top view to measured 2-D (independent of T0; start here).**
`tomato3d/state/` (or a new `tomato3d/topview/` if cleaner — say which and why): Roboflow v4 boxes → SAM masks
(reuse `tools/sam_*`, read-only import) → per-pot mm/px from `pot_rim_outer_edge_mm = 60` → per-leaflet projected
area, projected length/width, blade azimuth, `vis_frac`. Boxes alone are not area; state that in the output.
Every value keeps its status; no mm without the rim reference; perspective means per-pot scale, never one global.

**T2 — paired synthetic dataset (needs T0).**
With the calibrated parameters, generate scenes and export, per scene, the top-view and side-view **masks plus
the 3D truth**, no Cycles render (the label export already proved mask re-rasterisation from
`render_job/parts.npz` matches the stored layer exactly: 30 views, 7,864,320 px, 0 differing). Include amodal
masks so occluded organs have a complete target. Record scene count, seeds, parameter hash and the calibration
provenance in the dataset header.

**T3 — geometry model: top mask → 3D.**
Fill `tomato3d/twoview/` / `recon/` / `fuse3d/` rather than inventing new packages (they were scaffolded for
this; if they do not fit, say so). Per leaflet and per compound predict: elevation (see the sign rule below),
true length, true one-sided area, compound `direction_unit`. Train on T2, hold out whole scenes, report error vs
the depth map and the truth, and report it separately for occluded and unoccluded organs.
**Sign rule:** the top projection cannot distinguish an up-tilt from a down-tilt. This flow resolves it with the
generator's bending prior (tomato compounds mostly bend down), so the SIGN is a model prior, not a measurement —
emit it with a status that says so, and never write it into an MTG field that claims `measured`.

**T4 — render the side view from the estimate, and validate.**
From the estimated 3D, render a side view with the existing renderer/rasteriser and derive the camera-relative
direction class per compound (`tomato3d.synth.sideview.camera_relative_to_quadrant` — its quadrant conversion was
exact on 3,247 samples). Compare with the real side photos' direction labels and with
`tomato_side_nonboard` where available. Report agreement per compound, and the unclear-band share on both sides.

**T5 — feed P1.**
Emit the result as a P1 state package: MTG rows + optical surfaces with
`optical_readiness = conditional_completion` (never `supported` — this is an inference, not a reconstruction),
the per-value statuses from T1/T3, and a manifest naming the calibration and model versions.

## 4. Rules
Do not edit `tools/` (shared; import read-only), `config/`, `data/records/`, `docs/`, or Codex-claimed files
(`vtc_*`, `tomato_fsp_*`, `fsp_axes*`). No detector training. No thresholds invented — blade curl and the
flat/bent boundary stay on hold until T0 measures them. Report the O-mature realism failure and the
`camera_pose_gate_passed = false` on all 180 views (reprojection 3.6–9.5 px) and say whether either affects T2/T3;
do not silently use them.

## 5. Deliverables
Per-task done/blocked report `handoff/TOP_TO_3D_EXECUTION_2026-10-12.md` + `_KO.md`, code + tests (full `tests/`
suite passes, report counts), the T0 template, the T2 dataset header, the T4 agreement table, one end-to-end run
on a real top photo under `build/`, flow_map rows + checker rerun, LOG claim first / result last.
