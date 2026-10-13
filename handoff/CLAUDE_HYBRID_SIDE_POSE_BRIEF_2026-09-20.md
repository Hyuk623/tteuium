# Brief: hybrid ChArUco + leaflet-landmark side poses — Claude Code, 2026-09-20

Documentation-first brief (per `AGENTS.md`) for
`handoff/CLAUDE_HYBRID_CHARUCO_LEAFLET_RECONSTRUCTION_2026-09-20.md`. Written before implementation;
outcomes appended afterwards. No training, inference, model download or PPFD in this work.

## 1. Request

Add an opt-in diagnostic branch that estimates a **side** camera pose from reconstructed, reviewed
leaflet landmarks (`leaflet_landmark_pnp`) when the ChArUco board gives no pose, keeping the
ChArUco-only baseline intact and comparable. CONVENTIONS 3.1 stays the rule for the baseline; the
hybrid source is separately identified, never merged into it.

## 2. Inspected state (verified today)

- `build/new_captures_20260920/dwt_01|dwt_02`: 18 photos each; 6 and 8 ChArUco poses solved; **0 pass
  the 1 px gate**; all 16 side views unposed. Captures remain `validated_metric=false`.
- **Neither session has any leaflet labels**: both `edit_session/seed.backup.json` contain 0 leaflets,
  and no editor run exists under either session. There are therefore **no reviewed same-session
  correspondences**, so the handoff's condition for a real side-view trial is not met.
- Reusable pieces: `Cam`/`triangulate` in the editor, `tools/leaf_light/reconstruction.py::triangulate`
  and `project`, `tools/rebuild_leaf_edit_session.py` (point depths, extents, surface attachment with a
  depth-hash freshness contract), `tools/editor_point_review.py` (+ scene with toggles),
  `tools/serve_leaf_edit_session.py` (`--patches` pass-through pattern), `sheet_to_board_mm`.
- Importer F2 (focal truncation to 0.01 mm) is implemented by Codex; **F1 stays open** and is not
  addressed or claimed here.
- Older photos1 labels belong to a different capture session and are not transferable as biology; they
  may still exercise software on their own inputs.

## 3. Intended changes

1. **`tools/side_pose_candidate.py`** (new)
   - `freeze_reference(result_dir)`: versioned snapshot of triangulated reference points (board mm),
     their source observations/poses, calibration and depth-CSV hashes. Frozen before any side solve.
   - `solve_side_pose(...)`: matches reference XYZ to manually confirmed side-image pixels by
     (leaflet, `point_id`); deterministic fit/held-out partition recorded with its seed; robust
     `solvePnPRansac` + `solvePnPRefineLM` on inliers only; degeneracy checks (coverage, planarity,
     collinearity, cheirality) and alternative solutions via `solvePnPGeneric`; fit/inlier/outlier and
     held-out residuals; explicit statuses for insufficient points, degenerate geometry, no solution,
     behind camera, and validation unavailable. Distortion handled once, on raw original pixels.
   - Acceptance policy is data, not code: `min_fit_points`, `min_holdout_points`,
     `max_fit_error_px`, `max_holdout_error_px`, recorded in every candidate. A null entry stays
     inactive (never a silent default) and then inclusion requires an explicit override.
   - `readiness(result_dir)`: lists exactly which leaflets/points/images still block a trial.
2. **Rebuild integration**: `--side-poses` attaches candidates; freshness by reference/calibration/
   observation hashes; included candidates produce a **separate** `hybrid_point_depths.csv` plus
   `side_pose_candidates.json`; `editor_point_depths.csv` (baseline) is never overwritten; report
   counts by status/inclusion/freshness.
3. **Viewer**: per-photo pose-source badge (measured ChArUco / inferred landmark diagnostic /
   unavailable / stale) and a hybrid-points toggle in the existing 3D scene, with baseline retained.
4. **Server**: `--side-poses` pass-through so the existing browser rebuild button uses it.
5. **Editor**: direction-pair navigation suggestions (01/03 with 21/11 … 28/18) labelled as capture
   labels, not measured alignment.

## 4. Execution restrictions

No SfM, no nominal-angle poses, no averaging of poses, no scale from bboxes, no overwriting of any
ChArUco pose, no gate loosening, no tuning on held-out data. Writes stay under `build/`; originals,
growth JSONs, `config/`, `docs/` untouched. Hybrid output is diagnostic: `validated_metric=false`,
`suitable_for_ppfd=false`.

## 5. Validation plan

Deterministic synthetic tests: exact pose recovery with known cameras/landmarks including distortion;
wrong matches become outliers; insufficient/degenerate/collinear/behind-camera/missing-calibration all
produce explicit states; held-out points provably do not influence the fit (perturbing a held-out
observation leaves the pose unchanged); partition and seed persist; staleness after editing reference
points/calibration; baseline unchanged with hybrid off; provenance survives save/load; the server
rebuild route carries the option. A real trial is **not** attempted: with no labels there are no
reviewed correspondences, and the readiness report will name what is missing.

## 6. Outcomes (completion report, 2026-09-20)

### 6.1 What was implemented

- **`tools/side_pose_candidate.py`** (new): `freeze_reference`, `partition`, `geometry_checks`,
  `solve_side_pose`, `readiness`, `write_candidate`, CLI `freeze | solve | readiness`.
  Algorithm as documented in the candidate itself: `cv2.solvePnPRansac(SOLVEPNP_SQPNP)` then
  `cv2.solvePnPRefineLM` **on fit inliers only**, cheirality check, `solvePnPGeneric` alternatives,
  distortion applied once to raw original pixels. `DEFAULT_POLICY` (recorded in every candidate):
  `min_fit_points 6, min_holdout_points 2, max_fit_error_px 2.0, max_holdout_error_px 2.0,
  ransac_reprojection_px 4.0, ransac_iterations 5000, ransac_confidence 0.999, min_extent_mm 5.0,
  min_planarity_ratio 0.02, min_collinearity_ratio 0.02, holdout_seed 20260920`. The PnP minimum of
  4 points is kept separate from these acceptance requirements. Near-planar landmarks are a
  **non-fatal** `geometry_warnings` entry (two-fold PnP ambiguity); no extent and near-collinear are
  fatal. A null threshold stays inactive: `quality_status=unavailable`, and inclusion then needs an
  explicit override that is recorded as one.
- **`tools/rebuild_leaf_edit_session.py`**: `--side-poses` attaches candidates
  (`load_side_poses`, `hybrid_capture`, `hybrid_depths`). Freshness is decided from the reference
  depth-CSV hash, the calibration hash, capture membership, and the rule that a **measured ChArUco
  pose is never replaced**. Included candidates produce `hybrid_point_depths.csv` (with
  `baseline_*_board_mm`, `shift_from_baseline_mm`, `pose_source_for_this_observation`,
  `uses_inferred_camera`, `branch=hybrid`, `validated_metric=False`, `suitable_for_ppfd=False`) and
  `hybrid_capture.json` (`contains_inferred_poses=true`). `capture.json` and
  `editor_point_depths.csv` are untouched. The report adds `side_pose_status`,
  `side_pose_candidates`, `side_poses_used_in_hybrid`, `side_pose_by_status`,
  `side_pose_by_inclusion`, `side_pose_stale`, `hybrid`, `hybrid_note`.
- **Viewer** (`tools/editor_point_review.py`, `tools/editor_point_scene.html`): a per-photo pose-source
  badge (measured ChArUco / inferred landmark diagnostic / stale candidate / not eligible /
  unavailable, with candidate id, residuals and stale reasons), a statement that detected board IDs
  belong to the photograph and never to an inferred camera, and a hybrid-points toggle in the 3D
  scene drawing hybrid points as diamonds with a dashed link to their baseline position (purple = a
  point the baseline could not place). The toggle is off by default and disabled when nothing is
  attached.
- **Server** (`tools/serve_leaf_edit_session.py`): `--side-poses` pass-through, so the existing browser
  rebuild button produces the hybrid branch; the job summary reports the side-pose and hybrid counts.
- **Editor** (`tools/leaf_point_annotator.html`): a per-pane partner button offering the capture-label
  partner (21 with 11 ... 28 with 18, then 01/03), opened in the *other* pane, with tooltip and toast
  stating it is a file-label convention and not a measured alignment.

### 6.2 Validation

`tools/tests/test_hybrid_side_pose.py` (12 tests) and `tools/tests/leaf_annotator_pairs.test.cjs`
(3 tests). Full suite: **199 passed, 1 skipped**. Covered: exact recovery of a known camera through
distortion (centre error < 1e-4 mm, fit/held-out RMS < 1e-4 px); distortion proven to be applied
(zeroed coefficients move residuals past a pixel) and not applied twice; swapped matches become
outliers without moving the camera; insufficient, degenerate, collinear, no-extent, unmatched,
out-of-image and duplicate cases each produce their own explicit state; near-planar is solved but
reported as ambiguous; an inactive threshold never becomes a silent pass; perturbing held-out
observations leaves `rvec/tvec` and `fit_rms_px` identical while the held-out residual rises and
inclusion is withdrawn; the partition is seeded and reproducible; a flipped refinement is rejected as
`points_behind_camera`; hybrid adds one point that the baseline left `fewer_than_two_solved_views`
and reproduces its known XYZ to 1e-6 mm while baseline-supported points shift by < 1e-9 mm;
`editor_point_depths.csv` and `capture.json` stay hash-identical to a run without the option; stale
reference or calibration and an existing measured pose are refused; the browser route carries the
option end to end.

**15 mutation runs, all caught**: measured pose replaceable; stale reference ignored; calibration
change ignored; ineligible candidate used; hybrid overwriting the baseline table; inferred frame
labelled as a measured board pose; refinement on outliers; held-out folded into the fit; cheirality
check removed; distortion ignored; null threshold passing silently; degenerate geometry solved
anyway; inferred pose labelled as measured in the viewer; stale candidate shown as usable; server
dropping the option.

### 6.3 Real data: no trial, and exactly what blocks it

Command run today:
`python -m tools.side_pose_candidate readiness --result build/new_captures_20260920/dwt_01 --out build/side_pose_readiness_20260920/dwt_01`
(and the same for `dwt_02`), writing `build/side_pose_readiness_20260920/<plant>/readiness.json`.

| | dwt_01 | dwt_02 |
|---|---|---|
| reference points available | 0 | 0 |
| needed per side image | 8 (6 fit + 2 held out) | 8 |
| leaflets with labels | none | none |
| images with a solved pose | 01, 03, 24, 25, 26, 28 | 01, 03, 21, 24, 25, 26, 27, 28 |
| images without a pose | 12 | 10 |

Neither session has any leaflet label, so there are no reviewed same-session correspondences, no
frozen reference, and **no side-view trial was attempted**. Required next actions per plant: label
leaflets in the posed images listed above; mark the same physical point IDs (tip, visible attachment,
distinctive lobe apex, vein junction) in at least two posed images per point; rebuild to triangulate
them; freeze a reference; then mark at least 8 of those exact point IDs in one side image. Pose
quality is unchanged: zero images pass the 1 px gate, so any future candidate would rest on reference
points that themselves failed that gate.

### 6.4 Run commands

```
python -m tools.side_pose_candidate readiness --result <RESULT> --out <OUT>
python -m tools.side_pose_candidate freeze    --result <RESULT> --out build/side_reference_<date>
python -m tools.side_pose_candidate solve --reference build/side_reference_<date> \
       --observations <side_observations.json> --out build/side_candidates_<date>
python -m tools.rebuild_leaf_edit_session --session <SESSION> --backup <BACKUP> \
       --context <ANNOTATIONS> --out <OUT> --side-poses build/side_candidates_<date>
python -m tools.serve_leaf_edit_session --session <SESSION> --context <ANNOTATIONS> \
       --runs build/editor_runs --side-poses build/side_candidates_<date>
```

`<side_observations.json>`: `{"image_file": ..., "observations": [{"viewer_leaflet_id", "point_id",
"x_px", "y_px"}]}` in original pixels. Artifacts per run: `reference.json`,
`reference_points.csv`, `<candidate_id>.json`, `<candidate_id>_points.csv`,
`side_pose_candidates.json`, `hybrid_point_depths.csv`, `hybrid_capture.json`,
`labels/index.html`.

### 6.5 Limits and what is still open

Nothing here is a measurement. An inferred camera inherits the frozen landmarks' uncertainty, the
reference itself comes from poses that fail the 1 px gate, and every hybrid row carries
`validated_metric=false` and `suitable_for_ppfd=false`. Extra reconstructed points are coverage, not
accuracy; the baseline cannot project into an unposed side view, so no baseline side-image residual
exists to compare against. Joint optimisation of all cameras, pose averaging and SfM remain out of
scope. Importer **F1** (an explicit contract overriding contradictory calibration evidence) is
untouched and still open. The three-route fusion and JSON-guided reconstruction handoffs written by
Codex today are not part of this work.
