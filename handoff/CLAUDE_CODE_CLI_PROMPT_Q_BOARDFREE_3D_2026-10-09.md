# Prompt Q — Board-free 3D reconstruction pilot (dwt_101 first)

Paste to Claude Code. English file, per repo convention. One cell of work per step; declare before
running; report-only until a gate is explicitly declared.

## Standing decisions (user, 2026-10-09)
- "보드에 집착하지 말고" — stop requiring ChArUco board poses. The dwt_1XX board-less captures are the
  main line going forward.
- "dwt_01~04 버려도 됨" — the 2026-09-20 board sessions are DROPPABLE. Do not build anything new that
  depends on them; a board-vs-boardless comparison is OPTIONAL (Q.5) and never blocks.
- In-flight cells (N/O/P) and the C6 contract are untouched by this prompt. Any future move of the gate's
  real reference set to board-less photos is a DECLARED gate redefinition (see DETECTOR_POLICY_2026-10-09),
  not something this pilot does silently.

## Data (already on disk)
- `data/raw/dwt_101 .. dwt_113/dwt_1XX_gen_20261005/` — 9 HEIC per plant:
  top (elev≈90°), level_000/090/180/270 (elev≈0°), side_000/090/180/270 (elev≈25°); azimuths are
  capture-order approximations (`azimuth_basis=capture_order_assumed`).
- `generator_capture.csv` per plant: per-photo azimuth/elevation, `scale_reference=ruler_cm`,
  `ruler_plane` (top: pot_rim; others: beside_pot_vertical), pot_height_cm, soil heights, phenotype notes.
- `build/roboflow_upload_20261009/dwt_1XX_<view>.jpg` — 3024x3024 JPEG q92, EXIF-transposed, converted
  from the HEIC (new-format HDR HEIC needs pillow-heif; plain ImageMagick on this machine fails).
  Use these JPEGs as pipeline input; record their sha256 in the run manifest.

## Q.0 — Contract (declare before running)
`build/boardfree_20261009_01/Q_contract.json`: input shas, method + version pins, the four Q.3 checks with
thresholds declared as REPORT-ONLY, and the namespace rule: every output lives under `boardfree_` names;
nothing feeds C6 or the existing board pipeline.

## Q.1 — Pose + dense geometry, one plant (dwt_101)
- Primary: DUSt3R or MASt3R (pin repo + commit + weights sha) on the 9 views, on Kaggle T4 if local has no
  GPU (reuse the tomato-offload kernel pattern; dataset under dolgfish as `tomato-boardfree-pilot`).
- Output: per-view poses (R,t), confidence maps, fused point cloud (relative scale), pairwise match counts.
- Fallback if DUSt3R-class fails: init from the recorded approximate geometry (azimuth 0/90/180/270,
  elev 0/25/90, camera distance free) and refine with feature matches; report which path ran.
- Do NOT claim metric size yet; Q.1 output is in arbitrary scale.

## Q.2 — Absolute scale, two independent sources
- (a) Ruler: detect the cm ruler in each view where visible (the I.4b ruler-tick module in tomato3d/ is
  reusable; its tick-period logic is the measured reference — read its constants, do not re-derive).
- (b) Pot: fit the pot rim circle/cylinder in the cloud; compare against the recorded pot dimensions in
  generator_capture.csv.
- Report scale from (a) and (b) separately and their % disagreement. If they disagree > 5%, STOP and
  report; do not average silently. (The Sep point-cloud scale withdrawal is the cautionary precedent.)

## Q.3 — Self-validation without the board (all report-only this round)
1. Recorded-geometry residuals: angle between recovered azimuth/elevation pairs and the recorded
   approximate values; report per-view (expect noise; capture order was hand-held).
2. Leave-one-out: reconstruct from 8 views, project into the held-out 9th, report plant-silhouette IoU
   (SAM mask on the held-out view as reference; GT-box prompt convention).
3. Ruler consistency: scale estimated per ruler-visible view; report spread (p95-p5)/median.
4. Repeat determinism: run Q.1 twice with fixed seeds; report pose delta.
Declare numeric thresholds in Q_contract.json BEFORE running, as report-only candidates for a future gate.

## Q.4 — Hook into the existing organ pipeline (diagnostic)
With Q.1 poses + Q.2 scale: run the existing silhouette-hull + leaflet-cluster steps (tomato3d/ modules,
read/import only) on dwt_101. Output `boardfree_hull_dwt_101` + a render for eye inspection. Label every
artifact 진단용/표시용. The frozen detector was trained on 1x board photos; these are 2x board-less, so
detector output here is diagnostic only — note domain shift in the report. (This is exactly the gap the
upcoming tomato_top_nonboard series is meant to close; do not retrain anything in this prompt.)

## Q.5 — OPTIONAL, never blocking
If and only if Q.1–Q.4 finish cleanly and cheaply: run the same path on one board session plant with the
board masked out, compare poses against board poses. Skippable without note; dwt_01~04 are droppable per
the standing decision.

## Do not
- Do not touch N/O/P cells, C6 rows, the frozen detector, or the C6 real reference set.
- Do not average disagreeing scale sources; do not promote any Q.3 number to a gate in this prompt.
- Do not write into tomato3d/ or tests/ (Claude Code column: read/import only for tools/ counterparts
  per CONVENTIONS); all outputs under build/boardfree_20261009_01/.
- Do not re-derive ruler width; use the measured module constant (3.11 cm family, I.4b).
- LOG one line per completed step, append-only.
