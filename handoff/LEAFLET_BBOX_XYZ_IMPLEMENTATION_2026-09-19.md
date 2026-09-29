# Leaflet bbox identity, diagnostic cuboid and XYZ integration — Claude Code, 2026-09-19

Implements `handoff/CLAUDE_CODE_LEAFLET_BBOX_XYZ_HANDOFF_2026-09-19.md` inside the existing
`tools/` application (editor -> saved backup -> `rebuild_leaf_edit_session` -> existing result viewer).
Ownership note: `tools/` is Codex's column in `CONVENTIONS.md` §1; the user explicitly transferred this
task to Claude Code and the handoff authorizes these edits. Codex should re-read the changed files before
its next edit. No `config/`, `docs/`, `tomato3d/` or `tests/` file was changed. No deep learning / SAM ran.

**Implementation is complete and tested; scientific validation is not.** Calibration (RMS ~9.06 px,
0/18 poses pass the 1 px gate) is unchanged, every output keeps `validated_metric=false` and
`suitable_for_ppfd=false`. No full-plant reconstruction, validated dimension or PPFD readiness is claimed.

## Launch (actual prepared session with the final editor)

```
python -m tools.serve_leaf_edit_session --session build/photos1_manual3d_20260919/edit_session07 --context build/photos1_manual3d_20260919/manual_candidates.review09.json --runs build/photos1_manual3d_20260919/editor_runs --initial-backup build/photos1_manual3d_20260919/third_view_review10/third_view_revised.backup.json
```

Open `http://127.0.0.1:8821/`, press the load button. Port 8821 is the default on purpose: browser
storage is per origin and earlier sessions were opened at 8821, so any work saved there is kept and the
explicit revised backup is offered only when that browser has no saved work for session
`photos1_20260919`. Stop any `python -m http.server 8821` first. The server renders the CURRENT
`tools/leaf_point_annotator.html` on every request, so an older copy in a session folder is never served.

Integration result from the same inputs (no leaflet boxes exist yet): `build/photos1_manual3d_20260919/edited_roundtrip08/`.

## Data model (editor backup JSON, all backward compatible)

Per leaflet record (`variants.__all__.leaflets["organ|leaflet"]`):
- `bboxes[image_key]` = `{annotation_id, x_min_px, y_min_px, x_max_px, y_max_px, image_width_px, image_height_px, created_at}`;
  continuous original-pixel edges `[0,W]x[0,H]` (same convention as flower boxes). One box per leaflet per photo.
- `view_status[image_key]` = `{visibility: full|partial|unknown, identity_review: confirmed|unconfirmed}`.
  Missing = `unknown/unconfirmed` (conservative). Independent fields.
- `point_semantic_names[point_id]` (pre-existing field, reused): `distal_tip`, `visible_attachment`,
  `lobe_apex`, `vein_junction`, `other:<text>`, or a legacy value (kept verbatim).
- `observation_history[]`: bbox create/edit/delete/import, visibility and identity-review changes, meaning changes.
- `identity_history[]` (pre-existing) now also stores `moved_observation` (point IDs, bbox, prior view status, meanings).

Flower/bud/truss boxes (`boxes`) are untouched; leaflet boxes are not a `BOX_CLASSES` class.
New CSV: `<prefix>_leaflet_bboxes.csv` (full JS precision, exact round trip). `points.csv`/`contours.csv` columns unchanged.

## Editor changes (`tools/leaf_point_annotator.html`)

- Tool `소엽 · bbox` (key `B`): draw/move/resize the selected leaflet's box; other leaflets' boxes are drawn
  dashed and are never hit-tested, so overlapping leaves stay separate identities. Empty-area drag pans.
  The selected leaflet's saved points are shown read-only in this mode.
- `leafHasView` includes bbox-only photos -> they appear in identity lists, linked-view buttons and leaf list.
- Linked-view buttons open the other pane and zoom to the leaflet box (else its points); pane button `소엽`
  and `두 칸 소엽 확대`. Zoom only changes the screen transform.
- Panel `이 사진의 소엽 관찰`: visibility, identity review, box delete, and "eligible boxes k/n" readiness.
- `moveLeafView` (link/split) moves points, contour, bbox, visibility and meanings together; the moved
  view's identity review resets to `unconfirmed`; destination conflicts (existing observation in that photo,
  different meaning for the same point ID, incompatible boundary counts when both have points) throw
  before any mutation. Source IDs are retained, never renamed.
- Boxes are refused on a photo whose bitmap size differs from its calibrated camera (preview protection).

## Rebuild / geometry

- `tools/leaflet_extent.py` (new helper used only by the rebuild adapter): each eligible box -> half-spaces
  of its viewing region (bbox outline sampled 16 points/side, undistorted with the capture camera model,
  convex hull; outer approximation disclosed and checked via `max_projected_outside_bbox_px`). LP (HiGHS)
  gives the axis-aligned enclosing cuboid; `HalfspaceIntersection` gives the feasible polytope, its volume
  and edges. Statuses: `bounded_feasible_region`, `insufficient_data_no_eligible_view`,
  `unbounded_single_view`, `unbounded_extent`, `incompatible_views_empty_intersection`,
  `degenerate_zero_volume_intersection`, `numerical_failure`. No cuboid is emitted for any non-bounded status.
- Eligibility: solved raw pose + `full` + `confirmed` + original-resolution coordinates. Others stay listed
  with `exclusion_reason`.
- `tools/rebuild_leaf_edit_session.py` new outputs: `leaflet_bbox_observations.csv`, `leaflet_extents.csv`,
  `leaflet_extents.json` (method, calibration hashes, photo hashes, half-spaces, polytope). Depth CSV gains
  plant/session/variant IDs, `point_semantic_name`, per-view visibility/review,
  `all_contributing_views_identity_confirmed`, `estimate_kind`, cuboid relations
  (`inside_bbox_cuboid`, `inside_feasible_region`, distances, `x/y/z_cuboid_local_mm` = board minus
  `cuboid_min_mm`, translation only). Points outside are flagged, never moved/clamped/deleted.
  Point-derived extent is reported separately. `geometry_status`: bbox_only / image_points_without_depth /
  point_depth_available / partial_surface_available; cuboid availability is a separate column.
  Report schema -> `rebuilt-local-leaf-edit-session-2`; `input_files_changed` is now actually measured.
- Surfaces still come only from the existing physical-point requirements; bbox corners and polygon vertices
  are never correspondences.

## Viewer (`tools/editor_point_review.py`, `tools/editor_point_scene.html`)

Leaflet selector: feasible region (cyan), enclosing cuboid (yellow dashed), sparse point extent (magenta),
outside points (red ring); info lists statuses, boxes with visibility/review/exclusion, point IDs, source
photo buttons with pose/gate flags and that photo's actual detected marker IDs. Labeled photos draw saved
leaflet boxes and list them in a per-photo table.

## Server (`tools/serve_leaf_edit_session.py`, `tools/leaf_rebuild_client.js`) — finished and tested

Current-source editor per request; loopback Host check; POST requires same Origin + per-process token;
job status requires token; 16 MiB JSON limit; one running job (409 otherwise); runs must be under `build/`
and outside the session; each run `run_YYYYmmdd_HHMMSS_xxxxxxxx/` holds the posted backup, `job.json`
(backup hash, editor hash, status, error) and `result/`; failures are reported and marked
`REBUILD_FAILED_INCOMPLETE.json`; path traversal returns 404.

## Checks executed

- `python -m pytest tools/tests -q`: 142 passed, 1 skipped (baseline 123 passed, 1 skipped; 19 new).
  New: `leaf_annotator_leaflet.test.cjs` (10 Node tests), `test_leaflet_extent.py` (6),
  `test_rebuild_leaflet_bbox.py` (6), `test_serve_leaf_edit_session.py` (6).
- `python -m pytest tests -q`: 183 passed (core untouched).
- Mutation checks: removing the meaning-conflict guard, preview-resolution guard, bbox move on split,
  relink review reset, bbox-only listing, and the visibility / identity / resolution gates in the rebuild
  each made the new tests fail.
- Real data: `edit_session07` (same capture/review09 inputs as session05; seed leaflets identical, only the
  editor hash differs) + explicit `third_view_revised.backup.json` -> `edited_roundtrip08`: 48 rows,
  0 value differences on every pre-existing column vs `edited_roundtrip06`, 23 points with XYZ in 11 photos,
  identical A1/D1/D2 surfaces, all cuboids `insufficient_data_no_eligible_view` (no boxes exist yet).
- Browser (port 8836, separate storage origin; cleared afterwards): served editor loaded 18 photos and 8
  leaflets from the explicit backup; saved browser work was preserved on reload; a mouse-drawn box stored
  3024-px coordinates enclosing A1's points; rebuild button produced a run; viewer showed box, exclusion,
  marker IDs. Synthetic bounded case visually showed polytope/cuboid/point extent distinctly.
  The assistant box lives only in `editor_runs_browsercheck07/` (`EXAMPLE_PROVENANCE.json`: partial,
  unconfirmed, not a label).
- 246 protected inputs (source photos, config, docs, imported images, trial intrinsics, session05,
  third_view_review10, review09, board_evidence01, roundtrip06, visible_B1_review11_final) hash-identical.

## Limitations / decisions for review

1. Point depths are still triangulated from unconfirmed views (as before) so existing XYZ is not lost; they
   are flagged by `all_contributing_views_identity_confirmed=false`. Excluding them would be a policy change.
2. Leaflet boxes/cuboids only exist after the human draws and confirms them; none were fabricated.
3. Cuboid is exploratory: raw poses fail the gate; distortion handled by sampled outline hull
   (outer approximation, residual reported). Not a surface, thickness or PPFD occluder.
4. `edit_session06`, `edited_roundtrip07` are intermediate copies from before two small UI tweaks; kept,
   superseded by `edit_session07` / `edited_roundtrip08`.
5. Static `index.html` in older session folders still contains the old editor; use the server command.
