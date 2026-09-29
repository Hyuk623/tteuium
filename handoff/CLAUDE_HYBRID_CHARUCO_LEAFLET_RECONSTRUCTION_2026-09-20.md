# Claude Code handoff: hybrid ChArUco and leaflet-landmark reconstruction

## Request and authorization

The user requests an implementation handoff for a hybrid model: use ChArUco-based reconstruction as the reference and reconstructed physical leaflet landmarks to support side views whose board pose is unavailable. Integrate this into the existing program.

This handoff is the user's explicitly requested diagnostic extension of the ChArUco-only pose-source rule in CONVENTIONS.md section 3.1. Preserve that rule for the baseline; allow a separately identified `leaflet_landmark_pnp` source in the opt-in hybrid branch. This is not authorization for unrestricted SfM, nominal-angle poses, a new application, deep-learning training/inference, or PPFD simulation. The present Codex task writes this handoff only; it does not execute reconstruction.

Claude should inspect current files first, document concrete implementation choices, implement the integrated diagnostic path, and run focused non-learning validation. Attempt one real side-view trial only if reviewed, same-session correspondences are already sufficient. Otherwise deliver the working labeling/readiness flow with explicit missing-data reasons; never invent observations to demonstrate success.

## Read first and reuse

- AGENTS.md and CONVENTIONS.md; latest handoff/LOG.md and TODO.md.
- CLAUDE_CAPTURE_LABELING_DECISIONS_2026-09-20.md.
- CODEX_TOP_OBLIQUE_SIDE_PROPOSAL_REVIEW_2026-09-20.md.
- LEAFLET_BBOX_XYZ_IMPLEMENTATION_2026-09-19.md.
- LEAFLET_SURFACE_REVIEW_INTEGRATION_2026-09-20.md.
- CODEX_IMPORTER_FIX_REVIEW_2026-09-20.md, including its later F2 implementation addendum.
- tools/leaf_point_annotator.html; tools/serve_leaf_edit_session.py; tools/rebuild_leaf_edit_session.py; tools/leaflet_extent.py; existing triangulation, surface-generation and result-viewer functions and their tests.

The user requests changes within this existing application. Respect concurrent edits and ownership; preserve prior work and use new build output directories. Do not edit human config or design documents merely to make a trial pass.

## Latest verified starting point

The prepared captures are under build/new_captures_20260920/dwt_01/ and dwt_02/, with edit_session/ beneath each. Each contains 18 images. ChArUco poses are solved for 6 and 8 images respectively; zero pass the unchanged 1 px gate. All 16 side images lack a solved pose. Trial intrinsics remain unvalidated. At the last reviewed handoff neither new session had leaflet landmark labels. Check current saved state before assuming that is still true.

Older photos1 trial labels and partial surfaces belong to another capture session. They can exercise software on their own inputs but cannot be transferred as biological correspondences to dwt_01/dwt_02.

Manual growth JSONs are count/parent-identity references, not coordinates: dwt_01 lists 8/9/9 leaflets across three compound leaves; dwt_02 lists 7/7/5. Preserve these records. Date separation is user-managed and one-lens capture is a user-stated condition.

Focal-length comparison now truncates both values to two decimal places in mm; raw EXIF remains unchanged. Do not undo this user-confirmed rule. Importer F1 (explicit contract overriding contradictory calibration evidence) remains separately open; do not claim it resolved by this hybrid work.

## Architecture and coordinate contracts

Maintain two comparable branches:

1. **Baseline:** current measured ChArUco camera poses and original observations, with existing diagnostic flags and quality gates.
2. **Hybrid:** the same fixed reference poses plus separately stored side-camera candidates estimated from reconstructed, reviewed physical landmarks.

Use existing board-frame millimetres and the project's world-to-camera convention. Reuse sheet_to_board_mm; never introduce another sheet/board conversion. Keep original-image pixel observations and current distortion handling; never use crop-display coordinates or undistort twice.

Do not average camera poses or assume hybrid output is better. A successful hybrid calculation is not independent measurement of depth, scale, or camera calibration.

## End-to-end implementation

### A. Organ-centered observations

Selecting a leaflet shows its linked top, oblique and side images, bboxes, physical point IDs and visibility/identity states. Offer 21/11, 22/12, ..., 28/18 as navigation pairs with top 01/03 when available. These are direction-label suggestions only, never measured geometric alignments.

Retain manual bbox editing, linking/splitting, deletion, undo, original-pixel storage and history. Keep flower/bud labels separate. Use reviewed same-leaflet and same-physical-point correspondences; do not use bbox corners, arbitrary contour indices or inferred midrib points as observations. Preserve invisible points as unobserved.

### B. Frozen ChArUco reference landmarks

Triangulate initial points from at least two appropriate top/oblique observations with available measured ChArUco poses. Preserve the original residual, ray-angle, identity and pose-quality assessments. Failed quality gates remain visible; explicit diagnostic use is not a quality pass.

Freeze a versioned snapshot of reference points, source observations, reference poses and calibration before solving a side camera. Keep this reference separate from later hybrid-refined points. Report insufficient observations, inadequate baseline, ambiguous identity or inconsistent geometry rather than constructing seed coordinates.

### C. Side-camera pose candidate

For one side image, gather correspondences between frozen reference XYZ and manually confirmed pixel observations. Use calibrated 3D-to-2D PnP with a documented robust fit and refinement method supported by the installed OpenCV version.

Document the algorithm's point requirements separately from experimental acceptance requirements. Inspect spatial coverage, near-collinearity/planarity, positive camera depth, alternative solutions and sensitivity to reference-point uncertainty. Do not treat a low fit residual or a minimal mathematical point count as adequate validation.

Partition physical point IDs into fit and held-out sets before fitting. Save the partition and any sampling seed. Held-out points cannot select a model, tune settings, or participate in refinement while still being described as independent validation. Their reference XYZ themselves remain uncertain, so this is an internal consistency check, not proof of metric truth.

Record fit/inlier/outlier/held-out residuals and explicit validation availability. If no suitable hold-out exists, show a candidate with validation unavailable and exclude it from the default hybrid reconstruction. Do not silently turn an inactive/null threshold into a default. Claude must document the diagnostic acceptance policy before a real trial, without loosening existing gates or tuning on held-out results.

Never overwrite a failed or existing ChArUco pose. Never use nominal angles, copy an oblique pose, or obtain scale from a bbox. Initially leave measured ChArUco poses fixed; joint optimization of all cameras is outside this first implementation.

### D. Diagnostic integration and partial surfaces

Allow an explicitly selected diagnostic side-pose candidate to contribute only under the documented inclusion policy. Preserve a visible diagnostic override, if offered, distinct from an automatic quality pass. A side view with no eligible pose remains available for visual identity review only.

Recompute supported point positions from selected observations, retaining baseline coordinates and provenance. One new side image alone cannot supply depth for a previously unseen feature; another suitably posed observation is required. New points using inferred cameras inherit their uncertainty and source type.

Reuse existing partial-surface generation and image overlays. Distinguish observed landmarks, interpolated patches and unknown regions. Bbox cuboids remain spatial guides only, never leaf surfaces or PPFD occluders. Do not claim recovered curvature or whole-plant completeness from sparse interpolated points.

### E. Dependency and freshness handling

Use an acyclic first-version dependency chain:

original observations + calibration + ChArUco poses -> frozen reference landmarks -> side-pose candidate -> hybrid points -> partial surfaces.

Do not feed refined hybrid points back into their own side-pose solver. Editing reference coordinates, relevant identities/point observations, fit/validation partitions or calibration marks dependent candidates and outputs stale. Preserve previous versions and excluded observations. Require explicit recalculation through existing rebuild controls. Do not delete points merely because they fall outside a diagnostic bbox cuboid.

## Persistence and UI

Reuse current schemas where possible and add backward-compatible fields. Configuration/provenance belong in JSON and per-observation/result tables in CSV. Design exact filenames and fields after reading current consumers.

Each side-pose candidate must record:

- plant/session/image identity; source `leaflet_landmark_pnp`; immutable candidate ID/version;
- camera rotation/translation with units and frame convention;
- calibration/reference/observation hashes and source image/leaflet/point IDs;
- algorithm, settings, fit/held-out partition, inlier/outlier IDs;
- fit and validation residuals, degeneracy/stability checks and unavailable reasons;
- calculation status, quality status, diagnostic inclusion state and freshness separately;
- `validated_metric=false` and `suitable_for_ppfd=false` for current data.

Display measured ChArUco pose, inferred leaflet pose, unavailable pose, stale candidate and failed/unset quality checks distinctly. Keep baseline/hybrid toggles in the existing result viewer and link each 3D point or surface back to source photos and overlays. Report actual detected board IDs, never attribute board detections to a landmark-derived camera.

Wire settings through the existing browser -> server -> rebuild -> viewer route, not just a standalone CLI. Preserve browser edits and storage origin; do not restart a live editor without protecting unsaved work.

## Comparison and validation

Run meaningful synthetic/deterministic tests without model inference:

- Known calibrated cameras and fixed XYZ landmarks recover the side pose with correct frames/units and raw-pixel distortion handling.
- Wrong matches, insufficient points, degenerate distributions, ambiguous solutions and missing calibration produce explicit failure/unavailable states.
- Held-out observations are never used for fitting or refinement; reference hashes and source lineage survive save/load.
- Linking/splitting or editing relevant points invalidates dependent poses/points/surfaces, preserves original observations and supports undo.
- Baseline ChArUco results are unchanged when hybrid mode is off; legacy sessions still load.
- Failed/inactive gates and diagnostic provenance remain visible in exports and UI; inferred cameras never silently become ChArUco or metric-validated cameras.
- Exercise the actual server rebuild route and stale-result path.

For a qualified one-side-image trial, compare the baseline and hybrid on the same observations and frozen settings. Report held-out reprojection errors where both branches support comparison, missing predictions, newly supported points/areas, failures and manual effort. Additional reconstructed points alone are coverage, not evidence of increased accuracy. If the baseline cannot project into that side view, state that no direct baseline side-image residual exists.

Do not claim measured shape/PPFD accuracy without independent physical validation. Current failed calibration/pose quality remains unchanged by this integration.

## Deliverables and completion report

Deliver the integrated selection/labeling/readiness flow, optional diagnostic side-pose solver, baseline/hybrid reconstruction and overlays, provenance/freshness handling, focused tests and an English completion handoff with exact run commands and artifact paths.

Distinguish implemented functionality from real-data results. If suitable reference points are missing, list exactly which images/leaflets/physical features need review rather than manufacturing a result. Report any failed trial honestly. No deep-learning training/inference, model downloads or PPFD runs are part of this handoff.
