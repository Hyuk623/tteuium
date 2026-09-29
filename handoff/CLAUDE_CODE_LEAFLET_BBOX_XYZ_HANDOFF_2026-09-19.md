# Claude Code implementation prompt: leaflet identity, bbox and diagnostic XYZ

## Assignment and authority

Implement the following in the EXISTING tomato labeling and diagnostic reconstruction application. The user explicitly transferred this implementation from Codex to Claude Code. This transfer authorizes the necessary edits to the existing `tools/` application and its tests for this task; do not reject it solely because older ownership documentation assigns those files to Codex. Codex has stopped implementation to avoid simultaneous edits.

Work only inside:
`C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

Read `../공통규약.md`, `CONVENTIONS.md`, the latest `handoff/LOG.md` entries and `handoff/TODO.md` first. Keep source photographs, calibration, existing labels, correspondence IDs and historical outputs intact. Do not edit `config/` or `docs/`. Write new generated outputs in a new directory under `build/`. Use Korean for the user interface and English for code/comments/handoff records.

Do not run deep-learning training or inference, including SAM. Do not implement a separate replacement application. Inspect and reuse the current editor, depth adapter and result viewers.

## User's requested workflow

**Per-leaflet 2D bbox → cross-view leaflet identity → possible 3D spatial extent → physical point correspondences → partial leaf surface.**

The user additionally requests that leaf annotations be represented as **XYZ associated with the leaflet's 3D cuboid**. Interpret this as follows:

- Keep original-image observations in `(u, v)` pixels.
- Reconstruct observed physical correspondences into `(x, y, z)` in the existing ChArUco board frame, in millimetres.
- Associate the cuboid, reconstructed points and any supported partial surface with the same `leaflet_id`.
- The cuboid is a spatial reference/extent, not the definition of identity. Do not assign another leaf's point merely because it is inside the cuboid.
- If cuboid-local XYZ is also displayed, label it explicitly and retain board-frame XYZ and the cuboid origin/transform. Do not silently replace metric XYZ with normalized coordinates.
- Unknown depth stays unavailable; a single-photo observation does not receive fabricated XYZ.
- Preserve points outside the diagnostic cuboid and display any discrepancy. Do not clamp, move or delete them to force containment.

## Verified current state

The dataset is **18 photographs of one plant**, not 18 plants.

- Source photos: `C:/Users/sho36/Downloads/Photos-1-001/` (read only).
- Imported full-resolution plant images: `build/photos1_3d_20260919/images/IMG_7910.png` through `IMG_7927.png`, 3024 × 3024.
- Preview images: `build/photo_audit_photos1_20260919/previews/`, 1500 × 1500. Never persist preview coordinates as original pixels.
- User-confirmed board: 7 × 5 squares, 38 mm per square. Read `config/board_spec.json`; do not substitute the older 7 × 7 prose description.
- Trial intrinsics: `build/photo_audit_board_20260919/intrinsics.board_only.trial.json`.
- Calibration RMS is approximately 9.0644 px; 17 raw poses were solved, but **0/18 pass the configured 1 px pose criterion**. IMG_7910 has insufficient corners for the existing pose procedure.
- User authorized exploratory reconstruction despite the poor calibration. Keep its failed/unvalidated flags and existing thresholds. Do not repeatedly block all exploratory work by demanding new photographs.
- Actual detected board evidence: `build/photos1_manual3d_20260919/board_evidence01/capture.board_evidence.json`. It contains photo-specific marker/corner detections and raw measured poses. Do not substitute all possible board IDs for IDs detected in a particular photo.

Latest integrated reconstruction result:
`build/photos1_manual3d_20260919/edited_roundtrip06/`

It contains 23 distinct physical point estimates, 48 image observations across 11 of the 18 photos, three partial/coarse surfaces (A1, D1, D2), and preserved independent 2D regions. Other leaflets have sparse point depths without surfaces. All are unreviewed diagnostic results, not a validated complete plant or PPFD-ready geometry.

Authoritative inputs for reproducing this result:

1. Prepared session: `build/photos1_manual3d_20260919/edit_session05/`
2. Context: `build/photos1_manual3d_20260919/manual_candidates.review09.json`
3. **Explicit revised backup:** `build/photos1_manual3d_20260919/third_view_review10/third_view_revised.backup.json`

Do not replace item 3 with `edit_session05/seed.backup.json`: the seed lacks the newest third-view observations. Do not use the rejected initial candidate backup in `third_view_review10/` as accepted input. Existing assistant-generated annotations are not user-reviewed ground truth.

Result records include `edited_roundtrip06/rebuild_report.json`, `verification.json`, `editor_point_depths.csv`, `labels/`, `preview/` and `index.html`. There is no `edited_roundtrip06/report.json`.

## Existing code to reuse

### Label editor: `tools/leaf_point_annotator.html`

Already implements two side-by-side image panes, zoom/pan, original-image coordinate transforms, boundary/interior correspondence points, contours, undo/history, backup/restore, CSV export, and cross-view identity correction. Flower, bud and truss bboxes already exist.

Inspect these existing entry points before changing anything:

- `currentLeaf`, `leafKey`, `leafHasView`, `selectLeaf`
- `identityEntries`, `moveLeafView`, `inheritLeafProvenance`, `correctIdentity`
- `BOX_CLASSES`, `boxFromDrag`, `validBox`, `moveBox`, `resizeBox`
- `buildBoxExport`, `importBoxRow`, `buildBackup`, `restoreBackup`
- `updateIdentityTools`, `drawBoxes`, `showImage`, pixel/screen transforms
- `window.__leafAnnotator` (existing test/integration API)

At handoff, bbox classes are flower/bud/truss. **Leaflet bbox metadata and cuboid reconstruction are not yet implemented.** Existing leaf view linking is based on points/contours; extend it so bbox-only observations are also first-class observations.

### Session preparation: `tools/prepare_leaf_edit_session.py`

Copies source photos into a prepared local session, retains source hashes, creates the backup seed and local HTML/bootstrap. It protects persisted editor work from automatic replacement. It supports sparse physical points and partial candidates. Independent polygon vertex indices are deliberately not converted into correspondences.

### Reconstruction adapter: `tools/rebuild_leaf_edit_session.py`

`checked_inputs` verifies session/source/camera evidence. `convert` converts explicit editor backups while respecting point deletion, identity changes and sparse IDs. `point_depths` triangulates individual physical points. `rebuild` writes a new result with linked photo labels, depth records and partial surfaces. Integrate bbox extent calculation here rather than creating an unrelated reconstruction path.

### Existing result views

- `tools/editor_point_review.py` and `tools/editor_point_scene.html`: all-photo saved-point gallery and interactive 3D point selection linked to source photos.
- `tools/manual_leaf_preview.py` and `.html`: partial leaf surfaces, source-photo labels, board evidence and depth inspection.
- `tools/visible_leaf_patch.py` and `.html`: supporting physical-landmark interpolation clipped to independently observed image regions. A separate B1 diagnostic example is in `build/photos1_manual3d_20260919/visible_B1_review11_final/`; it is NOT merged into the latest main three-surface result. It retains 107/768 candidate triangles from five points; missing B1/b3 remains missing. Reuse only if appropriate; do not treat interpolation as measured surface curvature.

### Unfinished local rebuild connection — review before use

These files exist from an earlier interrupted implementation but are **not yet tested, launched or accepted as working**:

- `tools/serve_leaf_edit_session.py`
- `tools/leaf_rebuild_client.js`

Their intended function is a localhost editor button that snapshots the current backup, calls the existing rebuild adapter, and opens a newly versioned result. Inspect and finish them if useful. Check input validation, failed jobs, concurrent submissions, origin/token checks, allowed filesystem paths and source preservation.

Known integration issue: the server currently reads the prepared session's `index.html`. That is an older copy of the editor. Updating only `tools/leaf_point_annotator.html` will not update that served copy. Deliver a refreshed/versioned prepared editor using the current source without losing existing seed provenance, explicit revised backup, or browser-persisted labels.

## Required implementation

### 1. Leaflet observation and identity

- Add one bbox per observed leaflet per photo, associated with a stable `leaflet_id` and existing parent organ identity where applicable.
- Allow linking the same leaflet across photos and splitting a wrongly linked photo observation into a new identity.
- Record visibility (`full`, `partial`, `unknown`) independently from identity review (`confirmed`, `unconfirmed`). Choose equivalent explicit enums if the existing schema dictates them.
- Preserve existing leaf IDs; do not silently rename or collapse them during migration.
- Keep flower/bud/truss bboxes distinct and backward compatible.
- Preserve edit/delete/link/split history and original observation metadata.
- A bbox-only observation must appear in identity lists even before a point is marked.
- Link/split must move the intended photo observation and associated annotations consistently, detect destination conflicts, and never overwrite another leaflet in the same image.

### 2. Leaflet-centric editor

- Selecting a leaflet displays all linked photographs, including bbox-only views.
- Let the user open reference/comparison photos side by side and zoom to that leaflet's bbox.
- Use bbox only as a working/zoom region. Overlapping leaves remain separate identities.
- All stored coordinates remain in original-image pixels, through zoom, pan, crop, export, import and backup/restore.
- Add a convenient way to mark point meaning: tip, visible attachment, distinctive lobe apex, vein junction, or another explicit physical feature.
- Keep the same `point_id` for the same physical feature across photos. Never reorder IDs by screen position, contour traversal or camera angle.
- Unobserved points remain absent. Preserve boundary/interior classification and history.

### 3. Bbox-derived diagnostic 3D extent

- Use only known measured camera poses and eligible observations of the same leaflet.
- Estimate the intersection of viewing regions, then its enclosing 3D cuboid in board coordinates. Respect camera distortion in the existing projection model and disclose any approximation.
- A single photo cannot provide a bounded depth interval. Do not insert arbitrary near/far distances, thickness, a fixed plant volume or nominal camera angles to manufacture a result.
- Partially occluded or unknown-completeness boxes must not constrain the whole leaflet's extent as if they were full silhouettes. Unconfirmed identity links must not silently become trusted geometry.
- Explicitly report insufficient data, unbounded extent, incompatible views, invalid poses/input and numerical failure. Do not display a fake zero-sized box.
- Distinguish an enclosing axis-aligned cuboid from the actual feasible viewing-region intersection; the cuboid can include infeasible space.
- This is exploratory only with current calibration. Preserve raw-pose provenance and failed quality flags.
- Do not use the cuboid as a leaf surface, physical thickness or PPFD occluder.

### 4. XYZ, correspondence and surface integration

- Reuse existing triangulation for physical points seen in at least two images with usable measured poses.
- Recompute when correspondence coordinates, observation membership or identity changes. Prevent stale XYZ after edits, deletion, link or split.
- Associate point XYZ with the same leaflet and cuboid. Retain the original `(u, v)` observations and photo IDs.
- Display point-derived extent separately from bbox-derived extent: sparse points do not establish the full leaflet boundary.
- Report points outside a bbox-derived cuboid as discrepancies while preserving them.
- Distinguish `bbox only`, `point depth available` and `partial surface available`; also show cuboid availability independently.
- Generate a partial surface only when the existing evidence requirements are satisfied. Neither bbox corners nor separately traced polygon vertices are physical correspondences.
- Selecting a 3D leaflet/point reveals source photos, saved bboxes, corresponding point IDs, actual detected marker IDs and quality flags.
- Distinguish image observations, triangulated estimates and interpolated geometry in UI and output metadata.

### 5. Save/rebuild/review flow

- Integrate the workflow into existing editor → explicit saved snapshot → rebuild → existing result viewer.
- Preserve all old artifacts; create a new output directory per run.
- Retain plant/session/variant/organ/leaflet/photo/point identifiers end to end.
- Use CSV for observation/calculation tables and JSON for metadata/configuration/backups, consistent with existing contracts.
- Store a reproducible link to the exact backup, source hashes and calibration used.
- Do not silently import an older prepared seed over current browser work.

## Validation required before reporting completion

Add meaningful regression tests under the existing support-tool test suite and run affected existing tests. Cover:

1. Bbox-only identity creation and cross-view selection.
2. Link/split including points, bbox, visibility, semantics and metadata; no destination overwrite.
3. Original pixel-coordinate preservation through zoom/crop, export/import and backup restore.
4. Editing/removing a correspondence changes/recalculates its depth; insufficient observations invalidate it rather than reuse stale XYZ.
5. Known synthetic cameras and boxes: bounded solution, one-view/unbounded case, incompatible views and occlusion exclusion; no arbitrary depth.
6. Unconfirmed identity and unavailable pose handling; diagnostic versus accepted quality flags retained.
7. Points outside the box remain intact and visible.
8. Legacy leaves/contours, sparse point IDs, flowers/buds/trusses and history survive loading and saving.
9. Point/leaf selection in the result shows correct source photo, actual detected marker IDs and appropriate geometry status.
10. Any finished local rebuild server preserves inputs, restricts paths, reports failures and serves the updated editor.

Use synthetic fixtures for algorithm verification and existing data for a diagnostic integration check. Do not fabricate complete/confirmed leaflet boxes on the actual photos merely to make a demonstration pass. If manually added sample annotations are needed, save a separate explicitly unreviewed example backup.

## Required delivery

- Modified existing application and tests, not a separate replacement app.
- A concrete launch command and a fresh prepared session/result path that actually uses the new editor.
- Short Korean usage instructions: choose leaflet → draw/link bbox → set visibility → mark shared physical features → rebuild → inspect XYZ/cuboid/source photos.
- English handoff listing changed files, executed checks, results and remaining limitations; append `handoff/LOG.md`.
- Clearly separate implementation completion from scientific validation. Do not claim full-plant reconstruction, validated dimensions or PPFD readiness.

## Status of the last Codex turn

Codex read conventions, the existing editor bbox/identity code and handoff records. The user then transferred implementation to Claude Code. **No new leaflet-bbox/cuboid feature edits were made in that interrupted turn.** The two untested local rebuild files above predate that turn. This prompt documents the next implementation task; it does not assert that the requested feature is already complete.
