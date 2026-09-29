# Implementation handoff: global, vertical and circumferential leaflet reconstruction

## Purpose and scope

Integrate three observation-linking routes into the existing ChArUco-based labeling and diagnostic 3D reconstruction application. This is one shared identity/observation graph and one geometry pipeline, not three independently trained neural networks or three meshes averaged together.

This document records the user's corrected routes from the side conversation. Creating this handoff does not execute implementation, reconstruction, inference or training. Re-read current code and main-thread handoffs before implementation to avoid concurrent edits.

Companion: `CLAUDE_HYBRID_CHARUCO_LEAFLET_RECONSTRUCTION_2026-09-20.md`. Retain its frozen-reference, diagnostic pose-source exception, held-out validation and dependency contracts. This document adds the precise navigation and fusion method; it does not replace those safeguards.

## 1. User-confirmed routes

The earlier `01 -> 11 -> 21` example was a typo and is superseded by:

- Route A, global: all available photographs with usable observations and appropriately identified camera poses.
- Route B, vertical: **01 -> 21 -> 11**, meaning top -> oblique -> side at direction 1.
- Route C, circumferential: **11 -> 12 -> 13 -> ... -> 18 -> 11**, meaning adjacent side views around the plant.

For the other direction numbers, suggest oblique/side pairs `22 -> 12` through `28 -> 18`. Attach top 01 or 03 only when the same physical feature is visible; these top photographs are shared anchors, not separate azimuth stations inferred from their filenames. Also support the oblique ring `21 -> 22 -> ... -> 28 -> 21`.

These arrows specify review/navigation order and proposed associations. They do not establish camera angles, valid geometric correspondence, or a required chronological solve order. In particular, two posed oblique views may provide a reference point even if it is absent from the top view.

Use explicit session view metadata; do not infer geometry from filenames. Missing photographs remain missing. Do not rename original files to fit these routes.

## 2. Information extracted from photographs

| Observation | Stored information | Use |
|---|---|---|
| ChArUco detection | Actual detected marker/corner IDs and pixel coordinates | Measured camera pose and board-based scale reference |
| Leaflet bbox | Original-image rectangle and observation ID | Selection, zoom and eligible diagnostic spatial extent |
| Leaflet identity | Persistent leaflet ID and parent compound-leaf ID when known | Link the same organ across routes |
| Visible region | Reviewed mask/outline with provenance | Delimit visible surface evidence; not automatic physical correspondence |
| Physical landmark | Point ID, semantic meaning and original-image pixel coordinates | Triangulate the same physical feature across posed views |
| Visibility/review | Full/partial/unknown; confirmed/unconfirmed | Prevent hidden or uncertain observations from becoming facts |

Bbox corners, independently drawn contour vertex indices, inferred midrib points and screen-relative left/right labels are not physical point correspondences. A leaflet ID alone does not establish which point within it is being matched.

Consult the correct plant/date growth JSON for biological count and parent-identity review. Its counts do not specify spatial coordinates or require all leaflets to be visible in every photograph. New lower leaflets may be introduced from oblique or side views even if absent from the top image.

## 3. Shared observation graph

Keep existing IDs and saved observations. Add backward-compatible route metadata rather than duplicating labels for each route.

A suggested observation key is `(plant_id, session_id, image_id, leaflet_id, point_id)` for points. Bbox/region observations retain their own IDs. Association edges reference existing observations and carry:

- `edge_id`, source and target observation/image IDs;
- `route_types`: global, vertical, circumferential (an edge may serve several routes);
- `association_type`: leaflet_identity or physical_point;
- review status: proposed, confirmed, rejected, conflict or unavailable;
- author/method, revision and correction history;
- geometry assessment with residuals and explicit unavailable reasons, kept separate from human identity confirmation.

Never infer point identity from an organ-only edge. Never merge different point IDs merely because they occur in one bbox. Reaching the same observation by two routes must not double-count it or increase its statistical weight.

A loop such as `11 -> 12 -> 22 -> 21 -> 11` can reveal contradictory identity assignments. Check both leaflet and physical-point identity where their respective edges exist. An incomplete or unreviewed loop is unavailable, not inconsistent; a consistent loop is not proof of geometric accuracy. Geometry residual checks require camera poses and cannot be inferred from graph connectivity alone.

## 4. Existing UI integration

Reuse the current editor, split-view comparison, save/undo controls and rebuild route. Inspect `tools/leaf_point_annotator.html`, `tools/serve_leaf_edit_session.py`, `tools/rebuild_leaf_edit_session.py`, existing geometry helpers and tests before editing.

For a selected leaflet offer:

1. Global: all associated photos.
2. Vertical: top -> oblique -> side, with `01 -> 21 -> 11` as the direction-1 example.
3. Circumferential: previous/next direction within the selected side or oblique ring, including wraparound.

Show the actual photo code, view type, bbox, point IDs, visibility, identity review and pose source/status in each pane. Allow users to skip an occluded photo, resume a track later, introduce a previously hidden leaflet, correct an association or split a mistaken identity. Do not force an uninterrupted track.

Route selection changes the review workspace, not saved coordinates or geometry acceptance. All labels stay in original-image pixels; crop/zoom is display only. Missing/unposed photos may still support manual identity review but cannot supply a triangulation ray.

Preserve flowers/buds, accepted masks, point provenance, deletion history and undo. Link/split must move the correct per-view observations and candidate provenance together without overwriting destination work.

## 5. Geometry and fusion

### A. Baseline and initial reference

Preserve the current ChArUco-only result as a baseline. Use confirmed physical point correspondences with at least two suitable measured-pose observations to create initial points in the existing board frame, in millimetres. Reuse camera intrinsics, distortion handling and `sheet_to_board_mm`.

Retain existing reprojection/ray-angle gates and diagnostic flags. A computed pose is not necessarily a passed-quality pose. No nominal-angle substitution, top-image XY plus side-image Z, or mesh averaging is allowed.

### B. Optional missing-side-pose support

If a side image lacks a ChArUco pose, route B and route C help the user find confirmed 2D observations of already reconstructed physical landmarks. Use the companion handoff's opt-in `leaflet_landmark_pnp` path against a frozen ChArUco-derived reference snapshot.

Do not label these poses as measured ChArUco poses. Establish fit and held-out physical-point sets before fitting, preserve their lineage, and report insufficient/degenerate inputs or unavailable validation. The initial 3D landmark uncertainty propagates to the side pose.

For the first implementation, do not sequentially estimate 11 from 21, then 12 from 11, then 13 from 12. Circumferential links propagate identity suggestions, not camera-pose certainty. Each candidate side pose must use the fixed reference geometry specified by the companion handoff. Missing reference coverage remains explicit.

### C. Integrated point and surface calculation

Gather eligible observations for each physical point from all routes, deduplicate by observation identity, and call the existing triangulation/rebuild pipeline. Routes guide correspondence discovery; they do not contribute three independent XYZ measurements.

Retain baseline XYZ alongside hybrid XYZ and per-view residuals. Keep conflicting associations for review instead of silently selecting a winner. If robust exclusions are used, record excluded observations, method and reasons.

Create supported partial surfaces through existing code. Distinguish observed points from interpolated geometry. Preserve unseen regions as unknown. Bbox-derived cuboids are diagnostic extents only, never PPFD occluders.

## 6. Proposed helper contracts

These are integration seams, not a request for a parallel application. Reuse equivalent existing functions where available and document final names.

- `build_view_routes(session_views) -> route_graph`: consumes explicit image IDs/view types/direction indices; returns vertical paths, circumferential edges and missing-view reasons. No camera pose is invented.
- `review_track_consistency(observations, association_edges) -> findings`: returns identity/point conflicts, incomplete cycles and affected IDs; does not mutate accepted labels.
- `collect_unique_point_observations(point_id, observations, association_edges, pose_registry) -> eligible, excluded`: deduplicates observations and reports review/visibility/pose exclusion reasons with provenance.
- Existing rebuild: consumes a versioned annotation snapshot and the selected baseline/hybrid pose registry; emits point tables, partial-surface references, reprojection overlays and status metadata.

Tables belong in CSV; route definitions, provenance and comparison summaries belong in JSON. Write new generated results only to a fresh `build/` directory. Keep legacy schemas readable.

## 7. Dependency handling

Use the acyclic chain:

observations + calibration + measured poses -> frozen reference XYZ -> optional side-pose candidates -> hybrid points -> partial surfaces.

Changing accepted identity/point associations, relevant coordinates, calibration or reference versions must mark dependent results stale. Navigation-only changes must not invalidate geometry. Never feed refined hybrid points back into their own reference pose solve. Preserve original failed pose records and earlier results.

## 8. Validation and comparison

Implement focused deterministic tests for:

- Correct `01 -> 21 -> 11` order and both eight-direction ring wraparounds.
- Missing views, hidden features and side-only leaflets without fabricated observations.
- Original-pixel coordinates and backward-compatible save/load/undo.
- Same observation reached by several routes counted once.
- Organ-only matches never creating point correspondences.
- Conflicting cycles flagged; incomplete cycles not falsely declared failed or verified.
- Link/split/delete preserving provenance and invalidating dependent geometry.
- Baseline unchanged when route assistance/hybrid mode is disabled.
- Pose unavailable, failed quality, inferred pose and stale output correctly represented through editor -> server -> rebuild -> viewer.

Separate association workflow comparison from pose-source comparison. Route navigation alone cannot improve geometry when accepted observations and poses are identical; test that the resulting reconstruction is identical in that case.

For later real-data evaluation, record which additional confirmed observations each route helps obtain and compare global-only, global+vertical, and global+vertical+circumferential workflows. Keep model/settings fixed and label any observation-set differences. Report manual correction time, confirmed coverage, failures, and held-out reprojection errors where comparable. Do not equate extra reconstructed points with increased accuracy.

## 9. Delivery and restrictions

First deliver the integrated route-navigation and track-review workflow. Then connect existing baseline reconstruction and the separately identified optional diagnostic side-pose path. Re-read current main-thread state before any implementation or real-data trial.

Do not train/run deep learning, download models, alter human growth records, loosen quality gates, overwrite original captures or run PPFD under this document-preparation task. Scientific acceptance thresholds and side-pose policy follow the companion handoff; no unapproved defaults may silently become validation criteria.

Completion must distinguish code delivery, synthetic tests and actual same-session reconstruction. If labeled reference points are insufficient, report exactly what is missing. No claim of whole-plant completion, measured curvature, metric validation or PPFD readiness follows from route fusion alone.

## Document creation outcome

Written as an English side-conversation implementation handoff on 2026-09-20 with the user's corrected vertical route. Only this new document and one append-only log entry were written. Existing source code, shared main-thread handoff, labels, captures and configuration were not changed. No reconstruction or model execution was performed.
