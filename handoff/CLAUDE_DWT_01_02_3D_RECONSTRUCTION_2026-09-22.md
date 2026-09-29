# Claude Code Handoff: Reconstruct dwt_01 and dwt_02 Only

Date: 2026-09-22
Status: implementation request prepared; Codex has not executed reconstruction for this handoff.

## 1. User request

Use the newly supplied and organized Roboflow annotations to implement and run the existing 3D reconstruction workflow for **dwt_01 and dwt_02 only**. Reuse the current annotation editor, correspondence review, ChArUco geometry, diagnostic hybrid branch, reconstruction calculator and linked result viewer. Do not create another standalone application.

Project root:

`C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

All paths below are relative to this root. Read current repository instructions and the latest handoff LOG/TODO before editing. Do not overwrite concurrent work or existing labels. This task permits local data adaptation, implementation and geometric reconstruction for these two plants. It does not authorize deep-learning training/inference, model-weight downloads, Roboflow Workflow execution, photo uploads, PPFD/GroIMP runs or changes to remote datasets. Do not process dwt_03 or dwt_04.

The practical objective is a traceable, inspectable 3D result for each plant, with source photos and annotations accessible from the result. Its completeness depends on actual correspondence evidence. Report partial results and missing observations honestly; do not fabricate a complete plant to satisfy the request.

## 2. Verified inputs

### A. Grouped human annotations and export images

Base: `build/roboflow_dataset_review_20260922/by_plant/`

| Plant/session | View directory | Images | Annotations |
| --- | --- | ---: | ---: |
| dwt_01 / 260920 | `dwt_01/260920/middle/` | 7 | 196 |
| dwt_01 / 260920 | `dwt_01/260920/side/` | 7 | 192 |
| dwt_02 / 260920 | `dwt_02/260920/middle/` | 8 | 184 |
| dwt_02 / 260920 | `dwt_02/260920/side/` | 8 | 204 |

Each directory contains its images and `_annotations.coco.json`. Total scope: **30 annotated images and 776 per-image annotations**. These annotation counts are not counts of distinct physical organs.

Package metadata: `README.md`, `manifest.json`, `image_provenance.csv`, `annotation_id_map.csv` at the base above. Original archive files are preserved in its parent directory. The grouped copies were verified against the originals: image bytes unchanged, all annotation geometry/class fields unchanged, local COCO IDs remapped to remove split collisions with a reversible provenance map.

The annotations are human labels, not model predictions. Export photos are **640 x 640**, auto-oriented and stretched to that size. No top-view labels are supplied by these two exports. dwt_01 side view 15 and middle view 26 are absent from the exports; other original photos may still exist in the prepared sessions. An unlabeled original photo is not an absent photo, and it must not receive an invented label.

### B. Existing original-resolution sessions and geometry

For each `<plant>` in `dwt_01`, `dwt_02`:

- `build/new_captures_20260920/<plant>/capture.json`
- `build/new_captures_20260920/<plant>/edit_session/`
- That session contains `capture.json`, `intrinsics.json`, `board_spec.snapshot.json`, `annotations.source.json`, `seed.backup.json`, and `session_report.json`.
- `build/reconstruction_requests_20260920/<plant>.json`
- `build/reference_review_20260920/<plant>/` holds historical reference-layer outputs.

Each prepared capture contains 18 photos: top codes 01/03, side 11-18, and oblique 21-28. Export `middle` corresponds to the existing oblique group; validate this using photo content and capture records, not assumed physical camera angles.

The naming differs. Example lookup pair:

- Export: `dwt_01_260920_24.jpg`
- Prepared frame: `dwt_01_20260920_24.png`

Resolve by plant, full capture date, view code, recorded source path and actual image alignment. Do not join on a bare integer, directory order, or class ID.

The inspected prepared sessions use 3024 x 3024 camera intrinsics, trial calibration RMS approximately 9.064 px, and board variant `charuco_7x5_266x190mm` (7 x 5 squares, 38 mm per square). Read these values from the actual referenced files; do not copy stale 7 x 7 defaults from old documents or change config. `physical_print_verified` remains false in the inspected snapshot.

| Plant | Existing solved-pose view codes | Passing the 1 px pose gate |
| --- | --- | ---: |
| dwt_01 | 01, 03, 24, 25, 26, 28 | 0 |
| dwt_02 | 01, 03, 21, 24, 25, 26, 27, 28 | 0 |

No side-ring photo has a solved ChArUco pose in these inspected captures. Solved poses are not passing poses. Preserve the **1 px pose acceptance threshold** and all existing point/ray-quality settings. Diagnostic use must stay explicitly diagnostic, with `validated_metric=false` and `suitable_for_ppfd=false`; do not silently relax a gate or replace the baseline.

### C. Human growth references

- `tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json`: L01/L02/L03 leaflet counts 8/9/9; growth shoots 3; trusses 0.
- `tomato_photos_organized_/260920/dwt_02/260920/dwt_02_260920.json`: L01/L02/L03 leaflet counts 7/7/5; growth shoots 2; trusses 0.

Re-read these files at execution time and preserve them. Counts guide review only. They contain neither geometry nor an image-to-organ assignment and must not force per-photo counts, automatic deletion or hidden-leaf creation.

## 3. Reuse the existing implementation

Inspect these entry points and their current schemas before changing them:

- `tools/leaf_point_annotator.html`: `parseCocoDetections`, `importDetections`, `adoptLeafletDetection`, parent/sub-stem linking, membership proposals, cross-view leaf linking/splitting, point editing and backups.
- `tools/reconstruction_request.py`: reference/hash checks, `review_counts`, route membership, `collect_observations`.
- `tools/rebuild_leaf_edit_session.py`: conversion, existing point depths, extent/surface output, optional hybrid integration, reference refresh.
- `tools/side_pose_candidate.py`: readiness, reference freezing, and diagnostic side-camera candidates.
- `tools/serve_leaf_edit_session.py`, `tools/editor_point_review.py`, `tools/editor_point_scene.html`: existing editor-to-rebuild-to-3D-viewer flow.

Relevant context:

- `handoff/CODEX_ROBOFLOW_DATASET_LINK_REVIEW_2026-09-22.md`
- `handoff/CLAUDE_COMPOUND_LEAF_MEMBERSHIP_BRIEF_2026-09-21.md`
- `handoff/CLAUDE_JSON_REFERENCE_BRIEF_2026-09-20.md`
- `handoff/CLAUDE_HYBRID_SIDE_POSE_BRIEF_2026-09-20.md`
- `handoff/CLAUDE_THREE_ROUTE_LEAFLET_FUSION_2026-09-20.md`
- `handoff/CLAUDE_JSON_GUIDED_THREE_ROUTE_3D_IMPLEMENTATION_2026-09-20.md`

The old membership brief says no real Roboflow export existed. That historical limitation is now superseded by section 2A. Historical prepared sessions had no imported leaflet identities; inspect the latest backups for subsequent work before assuming this is still the entire current state. Never reset a newer human backup to the empty seed.

## 4. Implementation sequence

### Step 1: Preserve and map the annotations

Create a new run directory under `build/dwt_01_02_3d_20260922/<plant>/`. Snapshot the selected inputs and record hashes without altering source photos, original COCO files, calibration, human growth records or prior reconstruction outputs.

Implement/reuse a small adapter for the existing import flow. Preserve source category name and ID, source archive/split/annotation ID, source image size, transformed image size, and coordinate mapping. Use explicit aliases:

| Source class | Existing editor class |
| --- | --- |
| middle `compond_leaf`, side `compound_leaves` | `compoundleaves` |
| `leaflet` | `leaflet` |
| `main_stem` | `main-stem` |
| `sub_stem` | `sub-stem` |
| middle `shoot`, side `growth_shoot` | `growth-shoot` |

The middle and side numeric category IDs are different; map by each file's category dictionary. Their unused category 0 is a project/supercategory entry, not a sixth plant organ.

Validate orientation, crop and source-image equivalence before transforming coordinates. For a verified uncropped stretch of the same oriented photo, bbox edges and polygon vertices use the separate width/height scale factors; 3024/640 equals 4.725 only for the verified 3024-square case. Do not hardcode that factor for every photo. Use the existing pixel-centre versus pixel-edge convention for point observations, and preserve the original data plus explicit transform. Render overlays on the prepared original-resolution photos to verify alignment. A filename match or matching aspect ratio alone is insufficient.

The current importer deliberately rejects wrong dimensions. Add a validated adaptation path rather than disabling that check. If alignment cannot be established for a photo, retain its 2D export labels, report the unresolved mapping, and exclude it from geometry until resolved.

### Step 2: Establish physical organ identities and meaningful points

Import boxes/polygons into the existing two-pane editor. Reuse existing parent/sub-stem and leaflet identity functions. Keep separate IDs for a per-photo detection, a physical leaflet, a parent compound leaf, and a physical point. Scope associations by plant and session; do not associate organs between dwt_01 and dwt_02.

Use visible sub-stem attachment and reviewed alternate views as parent-membership evidence. A compound bbox overlap alone does not prove attachment. Keep occlusion, unknown membership and uncertain identity explicit. Link a shoot's bbox and mask only when evidence identifies the same organ; do not double-count it.

Existing non-learning geometric/appearance proposals may assist review, but they must remain proposals. No deep-learning inference is authorized. Reuse reviewed cross-view IDs and points where available. Otherwise expose the minimal targeted review in the current editor: same leaflet, its visible tip/base, a distinctive lobe tip or vein junction. Keep the same physical `point_id` across views; bbox corners/centres and independently ordered contour vertices are not anatomical correspondences. Unobserved points remain missing.

The export's `image_id` and `annotation_id` are not cross-view physical IDs. Grouping the same plant together does not identify the same leaflet across its photos.

### Step 3: Compute supported 3D geometry

Run the existing reconstruction path independently for each plant. Start with reviewed physical points observed in at least two usable views and the stored camera poses. Deduplicate observations reached through multiple review routes; navigation routes do not provide additional independent evidence.

Known-pose bbox intersections may provide exploratory 3D location ranges for a reviewed same-leaf identity. Use bbox constraints only when their visibility/coverage is adequate; visible-part boxes on occluded leaves must not truncate the full leaf. Unknown whole-leaf visibility is not equivalent to fully visible. No arbitrary single-view depth/thickness or silent finite range when unconstrained. Extents are visualization aids, not leaf surfaces or PPFD occluders, and must not delete points outside the box automatically.

For unposed side views, use the existing diagnostic landmark-PnP branch only if a frozen same-session 3D reference and its required correspondences exist. Its current contract requires at least 8 reference points (6 fit + 2 held out), with the existing spatial/degeneracy checks. Do not use the held-out observations during pose fitting, infer a camera from nominal turntable angles, replace measured ChArUco poses, or average camera poses. Refresh stale references after identity/point edits. No SfM or joint camera optimization is requested.

Create partial leaf surfaces only where reviewed 3D points and actual image boundaries support them. **Every supplied leaflet/compound-leaf segmentation is a rectangle**; those fields cannot supply traced leaf silhouettes. Stem polygons provide 2D visible-region evidence but do not determine 3D stem thickness or hidden connectivity on their own. Where boundary depth or coverage is insufficient, show points/extents and a surface-unavailable reason. Distinguish measured image observations, triangulated estimates and interpolated surface patches.

Do all independent import, identity-review preparation, geometry readiness and supported reconstruction work before asking for missing data. If reviewed identities/points are insufficient, leave a usable populated editor and a precise per-leaf/per-view request for the few missing observations. Do not declare a full plant reconstructed, fabricate correspondences, or discard the valid 2D work to force a result.

### Step 4: Display the result with source evidence

Use the existing viewer with one selectable plant at a time. Show separate states for 2D label only, bbox range, triangulated points, partial surface, unresolved identity and unavailable depth. Selecting a 3D object/point must lead to its actual source photos, original-coordinate bbox/polygon/point observations, point meanings, parent membership, calibration/pose source, residuals and the ChArUco IDs actually detected in that photo.

Do not imply that a diagnostic side pose has detected ChArUco markers it did not observe. Do not paint rectangle-derived regions as observed leaf geometry. Display the quality limitations beside the result; no PPFD suitability or whole-plant completeness claim.

## 5. Deliverables and acceptance checks

Deliver, for dwt_01 and dwt_02 separately:

1. A new prepared session with imported and source-linked human labels, without destroying existing labels or review history.
2. A coordinate/image/class mapping report and refreshable reconstruction request referencing exact input hashes.
3. Existing-format point-depth, extent and partial-surface artifacts for whatever is supported; explicit unavailable reasons for the rest.
4. The existing interactive 3D/source-photo viewer and a compact coverage/quality report (imported observations, confirmed identities, triangulated points, partial surfaces, unposed views and required corrections).
5. An English completion handoff listing exact changed files, commands run, artifact paths, validation and remaining human steps.

Before claiming completion, verify:

- Scope includes only the two allowed plants; no source changes to dwt_03/dwt_04.
- Import preserves all 776 supplied annotations as source records, including unresolved ones; successful geometric use may be a smaller explicitly reported subset.
- Class aliases are correct despite different numeric IDs; repeated import does not duplicate observations.
- Export-to-original coordinates align visually and round-trip within the declared numeric mapping tolerance; orientation/crop mismatches are rejected. This is a transform check, not a claim of biological or calibration accuracy.
- Existing labels survive import; leaf merge/split/reparent updates active candidates/provenance consistently and keeps history; a point edit marks/rebuilds dependent geometry.
- Missing/occluded observations, unposed cameras, impossible bbox intersections and insufficient correspondences remain unavailable instead of being fabricated.
- Synthetic/known-point geometry checks and relevant existing tests pass for changed code. Run focused import/membership/reconstruction/viewer tests; avoid redundant historical mutation loops.
- The original 1 px pose gate, calibration flags and geometry-unit conventions remain intact. Export XYZ in the existing **board frame, millimetres**, using the repository conversion rather than a second coordinate system.

Codex prepared this file and verified the input paths/counts and existing capture state. No reconstruction, inference or training was executed while writing the handoff.
# Mask automation addendum (2026-09-22)

The user has now explicitly authorized program changes and local SAM mask generation for the existing 577 leaflet bbox observations in dwt_01/dwt_02. This narrowly supersedes the earlier no-inference restriction for this mask task only. Training, cross-view association, 3D and PPFD execution remain outside this task. Implementation contract and subsequent results: `CODEX_LEAFLET_MASK_BATCH_2026-09-22.md`. Preserve source boxes; save masks by source annotation ID; every result needs individual human acceptance. User interface is Korean.
