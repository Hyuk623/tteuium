# One pipeline: photos -> whole-plant traits (Claude, 2026-10-01)

User request: "combine the separate models into one pipeline", "until my involvement is as small as possible".
User goal (10-01): whole-plant leaf area + PPFD/DLI for 24 plants; non-destructive calibration; no per-leaf review.

## What changed

- `tools/plant_batch.py` (new): `--photos-root <dir>` with one sub-folder per plant (folder name = plant id, optional
  growth.json). Runs `tools.plant_auto` per plant (skip finished, resume interrupted, record failures and continue),
  then summarises every plant's `traits.json` into `<out>/traits/` (traits.csv, TRAITS.md, traits_summary.json).
  `--summary-only` rebuilds the table after the person adds measurements.
- `tools/plant_auto.py`: S0b marker-corner pose rescue right after S0 (`out/pose_session/edit_session` + rescue.json);
  the per-run config gets `pose_session`, so S3+ use the extra poses. S1/S2 still run on the original session.
- `tools/marker_pose_rescue.py`: new `rescue_session(src, dst, plant)`; `rescue()` is a thin wrapper (same outputs).
- `tools/plant_pipeline.py`: new stage **S8 traits** (`tools.plant_traits.plant_traits`) per plant -> `<plant>/traits.json`;
  run-level `traits.csv` / `TRAITS.md`; HUMAN_TASKS.md now has "required" (measurements only) and "optional"
  (leaf-level review) sections when `goal` is `whole_plant` (default; plants json key `goal`).
- `tools/plant_traits.py` (new) + `tools/tests/test_plant_traits.py` (5 tests).
- `measurements/` (new, person-filled): `leaf_area.csv` (plant_id, leaf_area_cm2, method, date) and `light.csv`
  (plant_id or *, ppfd_umol_m2_s, photoperiod_h, date); templates + Korean README. Not `config/`.

## S8 method

Per posed photo: union of all ready, non-rejected leaflet masks (person-accepted, model-accepted and unreviewed);
each mask's pixels get the 20th depth percentile of S3 hull voxels projecting inside it; area = sum (Z/f)^2 per pixel.
Per plant: side-ring mean (proxy), top-photo mean, hull footprint (floor-binned x-y cells), hull cm3 and height,
stem diameter from `stem_thickness.json`, accepted-area share. Summary: k through origin from measured plants,
leave-one-out error when >= 3; DLI = PPFD x h x 3600/1e6; intercepted = DLI x (top-photo leaf area, else footprint).
`validated_metric` is true only once the leave-one-out error exists.

Check (dwt_01, held-out models, no human input) vs human masks on the same photos: 24: 14.81 vs 14.59 cm2,
25: 15.78 vs 15.64, 28: 16.91 vs 23.94 (detector missed overlapping leaves). Model-accepted masks alone gave 54 % of
the area, hence all non-rejected masks are used.

End-to-end check 10-02 (`build/plants_e2e_20261002`, plant_batch on the 18 raw dwt_01 photos, local CPU 1 h 16 min,
default 4-plant models so dwt_01 was in training): poses 6 -> 7, 495 leaflet boxes, 254 masks auto-accepted, S8 side
proxy 16.05 cm2 (5 photos), top 18.05 cm2, hull 104 cm3; same 4 photos vs human masks 16.48 vs 16.85 cm2 (-2 %).

## For Codex

- Rescued poses exist for dwt_01..04 (`pose_session` in tools/plant_pipeline_plants.json); S6 still uses the original
  session because instance_workflow checks prepared hashes against it.
- No XL files touched.
