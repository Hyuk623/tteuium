# Leaflet bbox -> XYZ -> partial surface: review integration — Claude Code, 2026-09-20

Implements `handoff/CLAUDE_LEAFLET_BBOX_XYZ_SURFACE_PROMPT_2026-09-20.md` (user sketch
`C:/Users/sho36/Downloads/제목 없음 17.pdf`). Verified the current code first: most of the chain already
existed, so this turn added the **missing connections** instead of duplicating features. `tools/` is
Codex's column; the user directed this work. No `config/`, `docs/`, `tomato3d/` or `tests/` edits.
No deep-learning training or inference and no PPFD simulation were run in this turn.

## Existing features reused (verified in code, not assumed)

| Brief section | Already implemented | Where |
|---|---|---|
| 2 leaflet bbox + identity, visibility/review, split/relink, delete/undo | yes | `tools/leaf_point_annotator.html` |
| 3 measured-pose coordinate contract, original pixels | yes | annotator + `tools/leaflet_extent.py` |
| 4 bbox viewing-region cuboid with explicit failure states | yes | `tools/leaflet_extent.py`, `rebuild_leaf_edit_session.py` |
| 6 segmentation drafts vs accepted regions, point meanings | yes | annotator, `tools/leaflet_segmenter.py`, `accepted_regions.json` |
| 7 triangulation, quality gates, rebuild from an explicit snapshot | yes | `rebuild_leaf_edit_session.py` |
| 8 leaflet-centric photo/3D review, marker IDs | partly | `tools/editor_point_review.py`, `editor_point_scene.html` |
| 9 GroIMP OBJ with identity/units | yes | `tools/groimp_bridge.py` |

Partial surfaces existed only as a **separate batch artifact** (`tools/sam_supported_leaf_patches.py` ->
`build/photos1_manual3d_20260919/sam_auto_20260920/three_d/`) with its own viewer, disconnected from the
rebuild's leaflet review, with no staleness link to the correspondences it was interpolated from.

## What this turn added

1. **Surface attachment with an explicit staleness contract** — `rebuild_leaf_edit_session.attach_surfaces()`
   and `--patches DIR`. The patch run's `depth_sha256` is compared with the depth CSV this rebuild just wrote:
   - equal -> `current_for_this_point_snapshot`; different -> `stale_from_earlier_point_snapshot`.
   - Stale surfaces stay listed with their provenance but are **not drawn** anywhere.
   - Written to `leaflet_surfaces.json`; per-leaflet `surface_kinds`, `attached_surface_status` and
     `attached_surface_faces` are added to `leaflet_extents.csv/json` and the run summary table.
   - Identities are mapped to this run's `viewer_leaflet_id`; patch records that this run does not know are
     reported with `identity_known_in_this_run=false`, and unavailable identities keep their reason.
   - Failure to produce a cuboid never blocks surfaces or points (evidence states stay independent).
2. **Reprojection onto the source photographs** (`editor_point_review.py`): every posed photo now also shows
   reconstructed points as white crosses and current partial surfaces as a green footprint (fill + contour),
   with a per-photo note and counts. Saved observations keep their existing colours, so observed vs computed
   stays visually distinct. Photos without a solved pose say so instead of drawing anything.
3. **Independent visibility toggles** in the 3D review (`editor_point_scene.html`): 복원된 점 / 보간 부분 면 /
   가능 공간 / 직육면체 / 점 범위. Selecting a leaflet highlights its surface and lists triangle count, source
   photos, landmark point IDs and whether the surface matches the current points.
4. **GroIMP boundary made explicit** (`tools/groimp_bridge.py`): `export.json` now records
   `geometry_kind='leaf_surface_triangles'`, `contains_bbox_cuboid=false`, `validated_metric=false`,
   `suitable_for_ppfd=false`. Cuboids and attached patches are separate files that this exporter cannot read.

## Validation actually executed

- `python -m pytest tools/tests -q`: **158 passed, 1 skipped** (baseline before this turn: 154 passed, 1 skipped).
  New `tools/tests/test_leaflet_surface_attachment.py` (4) covers: attachment + identity mapping + reprojection
  pixels drawn; correspondence edit -> stale + not drawn (checked against a control render); missing
  `depth_sha256` rejected; attachment optional; no cuboid in the surface payload; GroIMP refuses these files.
  New Node case in `leaf_annotator_leaflet.test.cjs`: overlapping boxes in one photo remain separate leaflets,
  editing in the overlap touches only the selected leaflet, deleting one keeps the other.
- Mutation checks (each made the new tests fail): freshness comparison forced to `current`; stale surfaces
  drawn on photos.
- Core `tests/` was **not** re-run this turn (no `tomato3d/` change).
- Real data, current user snapshot (`editor_runs/run_20260920_001200_c0ff5c90/editor.backup.json`, unchanged):
  `build/photos1_manual3d_20260919/integrated_surfaces_final_20260920/` (first pass without the summary
  column: `integrated_surfaces_20260920/`). 89 point observations, depth CSV byte-identical to the source run,
  six attached patches all `current`, `leaf_002` unavailable with its reason, five leaflet boxes,
  **0 cuboids** (all boxes still unknown/unconfirmed — nothing was forced), `input_files_changed=false`,
  `deep_learning_run=false`.
- Browser check of that result (static page on port 8839, closed afterwards; the editor on 8821 was not
  touched and no seed was reloaded): toggles verified by pixel counts (surfaces off -> 0 green while points
  remain; points off -> 0 orange while surfaces remain), leaflet selection shows surface/photo/marker details,
  photo reprojection note and overlay confirmed on IMG_7913.

## What the reprojection immediately shows (review finding, not a fix)

On IMG_7913 most patches land on leaflets, but **one patch reprojects onto the board**, and several sit
beside the leaf edge. With 0/18 poses passing the 1 px gate and legacy correspondences of mixed quality,
this is expected and is exactly the comparison the brief asks for. Treat it as a review queue item:
check identity, landmark correctness and pose before trusting any patch.

## Remaining gaps

1. No cuboid exists on real data yet: every saved box is unknown visibility / unconfirmed identity, and one
   is on unposed IMG_7910. Only the user marking boxes full+confirmed in >=2 posed photos will produce one.
2. Automatic cross-view physical-point matching is still unimplemented (the SIFT trial failed, 1 match at
   68.6 px vs the 2 px gate). `leaf_002` therefore remains unreconstructed.
3. Surfaces are interpolation between existing landmarks clipped to unreviewed masks: not measured curvature,
   area or a complete leaf; not a PPFD occluder.
4. Calibration is unchanged and unvalidated (RMS ~9.06 px, 0/18 poses pass the gate). No dimensional claim.
5. The patch tool remains a separate command; the rebuild attaches an existing run but does not run
   segmentation itself (deliberate: inference stays an explicit, authorized step).
6. The user's sketch step ⑤ ("뒤집힘 룰") is not implemented; its intended meaning (underside/mirrored views)
   needs confirmation.

## Commands

```
# Editor (existing, unchanged): preserves browser work on port 8821
python -m tools.serve_leaf_edit_session --session build/photos1_manual3d_20260919/edit_session07 --context build/photos1_manual3d_20260919/manual_candidates.review09.json --runs build/photos1_manual3d_20260919/editor_runs --initial-backup build/photos1_manual3d_20260919/third_view_review10/third_view_revised.backup.json --segmenter unavailable

# Rebuild a saved snapshot and attach an existing partial-surface run (NEW --patches)
python -m tools.rebuild_leaf_edit_session --session build/photos1_manual3d_20260919/edit_session07 --context build/photos1_manual3d_20260919/manual_candidates.review09.json --backup <run>/editor.backup.json --patches build/photos1_manual3d_20260919/sam_auto_20260920/three_d --out build/photos1_manual3d_20260919/<NEW_DIR>

# Review: <NEW_DIR>/index.html (summary), labels/index.html (photos + 3D + toggles), leaflet_surfaces.json
python -m http.server 8839 --bind 127.0.0.1 --directory build/photos1_manual3d_20260919/integrated_surfaces_final_20260920
```

After editing correspondences, rebuild first, then re-run `tools.sam_supported_leaf_patches` against the new
result; attaching the old patch run will be reported as stale rather than silently reused.
