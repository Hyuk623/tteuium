# Prompt R — Synthetic side-view training set with terminal-leaflet direction labels

Paste to Claude Code. Implements the side-view labeling policy appended to DETECTOR_POLICY_2026-10-09
(compound-level boxes + camera-relative 4-way direction; clockwise quadrant derived in post-processing).
PREREQUISITE: the O-mature cell analysis is accepted — use O-or-later generator config only. If O is not
yet accepted when you run this, stop after R.0 and report.

## R.0 — Contract (declare before rendering)
`build/sideprop_20261009_01/R_contract.json`: generator config sha (O-mature or later), seeds, scene
count, camera geometry, bin boundaries and the 10-deg exclusion band, output format. Namespace: all
outputs under `sideprop_`/`synside_`; nothing touches C6, N/O/P rows, or the real-photo Roboflow projects.

## R.1 — Render a synthetic side-view set
Use the existing renderer/Kaggle kernel pattern (package_kaggle.py / tomato-synth-render). Camera
geometry mirrors the real board-less side protocol: elevation ~25 deg (jitter +/-5), azimuths
0/90/180/270 (jitter +/-10), distance matched to the real 2x framing, no board. Declare the scene count
in R.0 (suggest 150 scenes x 4 views = 600 images; adjust to GPU budget).

## R.2 — Auto labels from generator ground truth
Per rendered view, per compound:
- bbox: projection of the compound's meshes (rachis + leaflets) into the view;
- direction: delta = wrap(compound_azimuth - camera_azimuth); quantize into 4 camera-relative bins
  `cl_toward` (|delta|<=45), `cl_right`, `cl_away`, `cl_left` (fix the sign convention in code and
  document it in the contract); EXCLUDE samples within 10 deg of any bin boundary (write them to an
  `excluded_boundary` list, do not silently drop);
- also emit main_stem and growth_shoot boxes, and the GT absolute clockwise quadrant (1-4, plant frame)
  for every compound - this is for testing the converter, not for training.
Export YOLO-format labels + a COCO json, plus a labels_manifest.csv (scene, view, compound id, delta
deg, bin, excluded flag, quadrant GT).

## R.3 — Quadrant converter + test
Implement `camera_relative_to_quadrant(cls, view_azimuth)` and unit-test it against the R.2 quadrant GT:
must be exact on all non-excluded samples. This converter is what production uses on real photos.

## R.4 — Real eval set scaffolding (labels are human work, not yours)
From build/roboflow_upload_20261009/side_views/ (52 real photos, dwt_101-113 x az 0/90/180/270):
write an eval split list (hold out ALL views of 4 plants, stratified) and a one-page labeling guide
(compound boxes; direction classes with examples; `unclear` 5th option) the user can follow in
Roboflow. Do not upload synthetic images to tom_side_seg_bbox or any real-photo project.

## R.5 — Training plan (declared now, run only after real eval labels exist)
Three arms on identical hyperparameters: real-only baseline / synthetic-only / synthetic+real.
Pre-registered decision rule: the synmix arm ships only if it beats real-only on the real held-out
mAP50; otherwise dropped. Per-class accuracy reported separately; if cl_toward/cl_away confusion
dominates, fall back to the declared 3-class merge. Model names carry `_synmix` where applicable;
such models never judge C6.

## Do not
- Use pre-O scenes; mix synthetic into real-photo Roboflow projects; promote any synmix model toward
  the C6 gate; train before the real eval set exists; hardcode API keys. LOG one line per phase.
