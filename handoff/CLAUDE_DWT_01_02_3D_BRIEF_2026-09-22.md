# Brief: dwt_01 / dwt_02 Roboflow labels into the existing 3D workflow — Claude Code, 2026-09-22

Documentation-first brief for `handoff/CLAUDE_DWT_01_02_3D_RECONSTRUCTION_2026-09-22.md`. Outcomes are
appended in section 6. `tools/` is Codex's column; the user asked Claude Code to execute this
Codex-written handoff (same arrangement as the 2026-09-21 membership work). No concurrent `tools/`
edits exist (last change: Claude, 2026-09-21 23:10).

## 1. Inspected state (verified today)

- Input package `build/roboflow_dataset_review_20260922/by_plant/`: dwt_01 middle 7 / side 7, dwt_02
  middle 8 / side 8 photos; 196 + 192 + 184 + 204 = 776 annotations. Every leaflet and compound-leaf
  polygon is a rectangle; stems are real polygons. Export photos 640 x 640, version preprocessing
  "auto-orient + Stretch to 640 x 640" (read from the Roboflow version record 2026-09-21).
- Prepared sessions `build/new_captures_20260920/<plant>/edit_session/`: 18 PNG frames 3024 x 3024 made
  from HEIC with orientation applied; frames record `view_code` and `source_path`
  (`...\dwt_01_260920_24.heic`), so an export name maps through the recorded source stem, not an index.
- Seeds hold 0 leaflets. No later disk backup with labels exists for either plant. The browser may hold
  unsaved-to-disk work under `leafPointAnnotator:<session_id>`; `bootstrap.js` and the server's
  `--initial-backup` offer a seed only when the browser has no saved work for that session.
- `rebuild.checked_inputs` requires a backup whose capture equals the prepared capture.
- 2026-09-20 dwt_01 trial: 6 user-confirmed texture-feature pairs (`P002`, `P005`–`P009`) with
  `leaflet_id = null`, marked "not semantic landmark". They are not leaflet points.
- Correction to my 2026-09-21 chat statement "no trained model": the Roboflow version API showed no
  model field, but Codex verified a finished YOLO26n segmentation model on side v1
  (CODEX_SIDE_SEG_BBOX_MODEL_REVIEW). It is not used here (no inference authorized).

## 2. Plan

1. **`tools/roboflow_session_import.py`** (new CLI) per plant:
   - snapshot input hashes (COCO files, export photos, session files, growth JSON);
   - map each export photo to a prepared frame by plant, capture date, view code and the frame's
     recorded source stem; refuse anything else;
   - validate the transform from pixels: the prepared photo stretched to the export size must match the
     export best at the identity orientation among the 8 flips/rotations, with a minimum normalised
     correlation and zero best integer offset (crop/shift check). Constants live at the top of the
     module and are written into the report;
   - convert bbox edges and polygon vertices with separate `sx = W/w`, `sy = H/h` from the actual sizes
     and check the round trip; keep source class name/ID, archive/split/annotation IDs and the transform
     on every record; photos that fail stay in an `unmapped` file, excluded from geometry;
   - write an original-pixel COCO file, overlays on the prepared originals, a mapping report, and a new
     seed backup made by running the editor's own `importDetections` through Node (one implementation of
     the detection schema), plus the read-only growth reference.
2. **Editor**: `parseCocoDetections` keeps per-annotation `provenance` and per-image `extra.transform`.
3. **Reconstruction**: a new `reconstruction-request-1` for each plant against the new seed; the existing
   rebuild, readiness and review outputs. Nothing is triangulated from boxes.
4. **Review page**: the rebuild's review adds an "imported 2D labels only" table per photo so 2D-only
   evidence is visible and not presented as geometry.
5. **Coverage report and review list** per plant: imported labels per photo and class, posed vs unposed
   photos, identities/points available, and the minimal human review needed for real 3D points.

## 3. Restrictions

Only dwt_01 and dwt_02. No training, inference, Roboflow change, upload, PPFD or GroIMP. Source photos,
exports, growth JSON, calibration, config and previous outputs are read-only. The 1 px pose gate and
`validated_metric=false` / `suitable_for_ppfd=false` stay. No SfM, no nominal-angle poses.

## 4. Validation

Synthetic-image tests for the converter (identity accepted; rotated, flipped, cropped and wrong-photo
exports rejected; exact scaling and round trip; provenance kept; unmapped labels retained; plant/date
scope enforced; repeat import adds nothing), the editor provenance test, focused existing suites, and a
visual overlay check on the real photos.

## 6. Outcomes (completion report, 2026-09-22)

### 6.1 Changed / added files

- `tools/roboflow_session_import.py` (new CLI), `tools/annotator_import_coco.cjs` (new; runs the
  editor's own `importDetections`), `tools/tests/test_roboflow_session_import.py` (new, 5 tests).
- `tools/leaf_point_annotator.html`: `parseCocoDetections` keeps annotation `provenance` and image
  `extra.transform` in each detection's `source`.
- `tools/rebuild_leaf_edit_session.py`: `imported_label_summary`; report fields `imported_labels`,
  `imported_labels_by_photo`. `tools/editor_point_review.py`: "가져온 2D 라벨 · 기하 아님" table.
  `tools/tests/test_reconstruction_request.py`: +1 test.

### 6.2 Commands run (per plant `<p>` in dwt_01, dwt_02)

```
python -m tools.roboflow_session_import --plant <p> --package build/roboflow_dataset_review_20260922/by_plant \
    --session build/new_captures_20260920/<p>/edit_session \
    --growth tomato_photos_organized_/260920/<p>/260920/<p>_260920.json --out build/dwt_01_02_3d_20260922/<p>/labels
python -m tools.reconstruction_request write --out build/dwt_01_02_3d_20260922/<p>/request.json --plant <p> \
    --session <p>_20260920 --capture-date 2026-09-20 --growth <growth json> \
    --prepared-session build/new_captures_20260920/<p>/edit_session \
    --annotation-snapshot build/dwt_01_02_3d_20260922/<p>/labels/seed_with_imports.backup.json \
    --annotation-context build/new_captures_20260920/<p>/edit_session/annotations.source.json \
    --output build/dwt_01_02_3d_20260922/<p>/rebuild
python -m tools.rebuild_leaf_edit_session --session <session> --backup <seed_with_imports> --context <context> \
    --out build/dwt_01_02_3d_20260922/<p>/rebuild --request build/dwt_01_02_3d_20260922/<p>/request.json
python -m tools.side_pose_candidate readiness --result build/dwt_01_02_3d_20260922/<p>/rebuild \
    --out build/dwt_01_02_3d_20260922/<p>/side_readiness
```

### 6.3 Results

- 776/776 labels mapped (388 per plant), 0 unmapped, 0 duplicates; 30/30 photos passed the pixel
  check (identity correlation 0.99983–0.99987, orientation margin 0.253–0.767, offset (0,0)); overlays
  inspected visually on dwt_01 view 24 (boxes on leaflets, main-stem polygon on the stem).
- Export coordinates are decimals (e.g. 359.153), so scaling loses ~0.005 export px; my earlier chat
  estimate of "up to ~5 px" loss was wrong.
- Request `ready` with no findings; rebuild: 0 editor observations, 0 modelled leaflets, 0 points,
  0 extents, 0 surfaces. Side readiness: 0/8 reference points. Growth review: every parent
  `fewer_reviewed_leaflets_than_recorded`.
- Coverage table, editor launch command and the minimal review list: `build/dwt_01_02_3d_20260922/README.md`.
- 46 referenced inputs re-hashed unchanged; no output for dwt_03/dwt_04.

### 6.4 Validation

Converter tests 5 passed (identity accepted; rotated, flipped, cropped and wrong-photo exports rejected;
other plant excluded; accounting; provenance; no identity invented; refuses non-empty output; repeat
import adds nothing). Focused suites 70 passed. Full tools suite 224 passed, 1 skipped.

### 6.5 Not done and why

- No cross-view identities, physical points, triangulated XYZ, extents or surfaces: the labels carry
  none of these, and inventing them is prohibited. The README lists the minimal human review
  (4–5 leaflets, tip + base in one posed pair: dwt_01 24–25, dwt_02 27–28 or 25–26).
- No automatic parent/sub-stem linking: a class label is not a relationship.
- The 09-20 dwt_01 texture pairs were not imported (no leaflet identity; not landmarks).
- The seed is offered by the server only to a browser without saved work for the session; the
  original-pixel COCO file is the fallback import.
- The YOLO26n model Codex found on side v1 was not used (no inference authorized).
