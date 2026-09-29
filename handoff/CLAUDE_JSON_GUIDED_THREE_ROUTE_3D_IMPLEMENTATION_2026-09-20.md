# Claude Code implementation handoff: JSON-guided three-route hybrid leaflet reconstruction

## 1. Task and scope

Build an integrated diagnostic 3D reconstruction calculator in the existing tomato application. Combine global, vertical and circumferential observation-linking routes; consult the user's growth JSON; reconstruct physical leaflet landmarks using ChArUco poses; optionally recover missing side-camera poses from frozen reconstructed landmarks; generate supported partial leaf surfaces and linked photo overlays.

This is one observation graph and geometry pipeline, not three neural networks or averaged meshes. This file is the consolidated entrypoint for the latest user request. Reuse compatible details from the companion handoffs below; this file adds the JSON/CSV integration contract and incorporates the later route-review corrections. It does not supersede original observations or historical results.

The current Codex task prepares documentation only. Claude's implementation should include deterministic/synthetic tests and a limited same-session diagnostic reconstruction only when sufficiently reviewed observations exist. Do not run deep-learning training/inference, download weights, or run PPFD simulation under this brief. Do not fabricate a trial result when annotations are missing.

The user-requested hybrid extension explicitly permits `leaflet_landmark_pnp` as a separate opt-in diagnostic pose source, extending the old ChArUco-only rule only for the hybrid branch. Preserve a ChArUco-only baseline. This is not authorization for unrestricted SfM, nominal-angle camera poses or replacement of original ChArUco results.

## 2. Read and inspect before editing

Read AGENTS.md, CONVENTIONS.md, latest handoff/LOG.md and TODO.md, and:

- CLAUDE_HYBRID_CHARUCO_LEAFLET_RECONSTRUCTION_2026-09-20.md
- CLAUDE_THREE_ROUTE_LEAFLET_FUSION_2026-09-20.md
- CODEX_THREE_ROUTE_FUSION_REVIEW_2026-09-20.md
- CLAUDE_CAPTURE_LABELING_DECISIONS_2026-09-20.md
- CODEX_IMPORTER_FIX_REVIEW_2026-09-20.md, including later outcome addenda

Inspect existing implementations and consumers before designing adapters:

- tools/leaf_point_annotator.html
- tools/serve_leaf_edit_session.py
- tools/rebuild_leaf_edit_session.py
- tools/leaflet_extent.py
- tools/import_organized_capture.py
- Existing annotation backup/export, triangulation, partial-surface, photo-overlay and 3D-viewer code and tests.

Respect concurrent edits. Make the existing editor -> saved snapshot -> server rebuild -> viewer path work; do not deliver a disconnected calculator or a second application. Preserve legacy sessions, source photos, user annotations, undo history and previous results. Do not modify human config or docs merely to make a run pass. Generated outputs go into fresh build directories.

## 3. Starting state and user decisions

At the latest review, build/new_captures_20260920/dwt_01/ and dwt_02/ each held 18 decoded images and prepared edit_session/ directories. Measured poses existed for 6 and 8 images respectively, none passed the unchanged 1 px criterion, and all 16 side images lacked a solved pose. New-session landmark labeling had not started. Re-read current files before relying on these counts.

Older photos1 labels and partial surfaces belong to another capture session. Do not transfer them as anatomical correspondences to either new plant.

The human will keep dates separated operationally. Use existing plant/session identity checks; do not reopen importer mixed-date selection as required new work. One-lens operation is user-stated, not proof of calibrated crop/focus/processing equivalence.

Focal comparisons now truncate to two decimal places in mm, without rounding; preserve raw EXIF and camera calibration. Do not revert this rule. Importer F1 (explicit camera expectation overriding contradictory calibration evidence) remains a separate known issue and must not be presented as resolved by route fusion.

## 4. Data architecture: JSON references and existing observation tables

Keep three distinct responsibilities:

| Input | Authority | Use |
|---|---|---|
| Human growth JSON | User-recorded biological counts and compound-leaf IDs | Check count discrepancies and parent assignments |
| Annotation/association JSON | Reviewed labels, identities, route associations, histories and provenance | Select and connect observations across images |
| Capture/calibration/settings JSON | Image registry, calibration, pose sources, quality policy and hashes | Define the geometric calculation |

Reuse the existing JSON editor backup rather than duplicating authoritative annotations. Reuse existing CSV point/bbox/contour exports where applicable. Numeric per-observation and per-result tables stay CSV; configuration, associations, provenance and file references stay JSON. Existing JSON snapshots may retain their current coordinate arrays for backward compatibility. Do not create two independently editable copies of the same measurements.

Add a versioned reconstruction-request manifest or extend an equivalent existing manifest. It should reference, rather than overwrite:

- plant_id, session_id and capture date;
- human growth JSON path and content hash;
- immutable annotation snapshot path and hash;
- capture/calibration references and hashes;
- authoritative CSV observation exports, if used by the current adapter;
- route metadata or association graph reference;
- selected baseline/hybrid mode and explicit candidate-pose selection;
- quality-policy reference/version, frozen reference version and output destination.

Resolve relative paths against a documented manifest base, not the process working directory. Check referenced files and identities before calculation; missing, malformed or mismatched input produces an actionable error without repairing human data. A changed hash must trigger explicit refresh/versioning, not silent use of a stale snapshot. No required unknown quantity is represented as zero.

### Human growth records

Current paths:

- tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json
- tomato_photos_organized_/260920/dwt_02/260920/dwt_02_260920.json

Last verified values: dwt_01 compound leaves L01/L02/L03 have 8/9/9 leaflets; unfolding count 0, growth shoots 3, trusses 0. dwt_02 has 7/7/5 leaflets; unfolding count 0, growth shoots 2, trusses 0. Read the files at runtime; never hardcode these counts into the calculator.

Count unique reviewed leaflet identities across the session, grouped by known parent compound leaf. Separate unconfirmed identities, unknown parents and coverage gaps from actual mismatches. Do not count the same leaflet once per photo or per route. Growth shoots are not extra leaflets.

If L01 records eight leaflets and annotations contain nine distinct reviewed IDs, show a count/identity review finding. Seven observed IDs may simply mean incomplete visibility; do not invent the eighth. Do not merge or delete labels automatically to satisfy a count. The growth JSON has no spatial coordinates or spatial ordering: use photographs and measured geometry for position corrections, never JSON array order. Do not edit the human record to make predictions agree.

## 5. Three review routes and identity graph

- Global: all associated photographs with usable observations.
- Vertical: 01 -> 21 -> 11, and corresponding oblique/side pairs 22/12 through 28/18. Top 01 or 03 can connect only where the same physical feature is visible.
- Circumferential: 11 -> 12 -> ... -> 18 -> 11; also support 21 -> 22 -> ... -> 28 -> 21.

Read explicit view metadata. Routes specify review/navigation order, not measured angles or mandatory chronological solve order. Missing views and interrupted tracks remain explicit. A feature absent from top views can still be reconstructed from other suitable posed views.

Scope each physical-point identity by plant/session/leaflet/point, retaining parent-organ identity where required by the existing schema. A point observation additionally includes image identity. Local names such as b1 or i1 may repeat on different leaflets: never join globally on point_id alone.

Association edges reference existing observations and record route membership, association type (organ identity versus physical point), review state, provenance and history. A shared observation reached by several routes is counted once with unchanged weight. Organ-only edges never create point correspondences.

Keep human identity confirmation separate from geometric agreement. Detect contradictory identity cycles; incomplete/unreviewed cycles are unavailable, not automatically conflicting or validated. Do not force a continuous track around all eight directions.

## 6. Photo information and annotation behavior

For each view retain:

- Actual ChArUco detections and corner/marker IDs.
- Leaflet bbox, reviewed visible region, persistent identity and known parent.
- Leaflet visibility: full/partial/unknown, and identity-review state.
- Physical landmark coordinates in original-image pixels, semantic meanings, point visibility, review and source history.

Use bbox for selection/zoom and eligible diagnostic extents. Bbox corners, independent contour vertex indices, screen-relative left/right numbering and inferred midrib centerlines are not physical correspondences. True visible vein junctions, tips, attachment points and distinctive lobe tips may be physical landmarks after review.

A partially occluded leaflet can still have visible, confirmed points. Exclude unobserved points, not all points on a partially visible leaf. Whole-leaf bbox eligibility is a separate rule: partial boxes cannot constrain the unseen whole leaflet.

Preserve flower/bud labels. Split/relink must move relevant bbox, regions, physical points, candidate provenance and per-view metadata together without overwriting destination work. Preserve deletion and undo histories. Crop/zoom affects display only.

## 7. Reconstruction computation

### Baseline

Use the existing triangulation with reviewed physical points observed in at least two suitable ChArUco-posed photos. Keep board-frame millimetres, world-to-camera pose convention and distortion handling consistent. Reuse sheet_to_board_mm. Never take top-image XY and append side-image Z.

Preserve current ray-angle, reprojection and quality flags. An available pose with failed quality may support explicitly marked diagnostics, not a metric pass. Retain the ChArUco-only result unchanged as the comparison baseline.

### Frozen reference and optional side pose

Freeze versioned reference XYZ derived only from original ChArUco observations/poses. Collect confirmed observations of these physical points in one side image. Estimate a calibrated 3D-to-2D pose using a documented robust PnP method and refinement.

Before a real trial, document solver-specific point requirements, spatial distribution/degeneracy checks, positive-depth checks, alternative-solution handling, stability assessment and diagnostic acceptance policy. Keep algorithmic minima separate from sufficient experimental evidence. Do not invent relaxed thresholds to obtain a successful run; null criteria remain inactive.

Partition fit and held-out physical point IDs before fitting. Held-out points must not fit, tune, select or refine the pose while retaining a validation label. No suitable hold-out means validation unavailable, not passed. Reference XYZ are themselves uncertain: held-out reprojection is an internal consistency check, not independent metric truth.

Each side candidate uses the same frozen reference. Do not estimate 12 from an inferred 11 and then 13 from 12. Circumferential links propagate identity suggestions, not pose certainty. Store new candidates with source leaflet_landmark_pnp; never replace or relabel original measured/failed ChArUco records.

### Fusion and partial surfaces

Collect eligible, deduplicated observations using the selected pose registry and existing reconstruction functions. Retain baseline and hybrid XYZ separately, with residuals, excluded observations and reasons. Do not average three route results or increase confidence merely because a link belongs to three routes.

Side-only features need another appropriately posed observation for depth. Missing reference coverage remains unknown. Generate partial leaf surfaces only where observed points and boundary evidence support them; distinguish interpolation from observations. Reproject results onto contributing photos for review.

Bbox cuboids are spatial guides only. Do not use them as leaf meshes or PPFD occluders, and never clamp/delete a point solely because it lies outside a diagnostic cuboid.

## 8. Calculator UI, dependencies and outputs

Reuse the current UI with the following user flow:

Load session + referenced growth JSON -> choose leaflet and route -> review bbox/identity/visible points -> inspect count/association findings -> check baseline/hybrid readiness -> calculate selected eligible geometry -> inspect photo overlays and linked 3D output.

Show pose source, pose availability, computed/failed/unset quality, validation availability, diagnostic inclusion and staleness separately. Display count discrepancies as review guidance, not geometric constraints. Failed or incomplete inputs must remain visible with reasons. Provide an existing or integrated baseline/hybrid toggle, not a separate app.

Use the acyclic chain:

observations + calibration + measured poses -> frozen reference points -> side-pose candidates -> hybrid points -> partial surfaces.

Geometry-relevant edits stale dependent outputs. Navigation-only changes do not. A growth-count-only update refreshes count findings and provenance but does not mathematically change XYZ; resulting annotation/identity corrections do trigger geometric invalidation. Never feed hybrid-refined points back into the solver that produced their own reference camera.

Persist JSON run provenance and CSV point/residual/coverage/findings tables using existing contracts wherever possible. Record source paths/hashes, algorithm/settings, selected observations and pose candidates, fit/hold-out membership, calibration/reference versions, timestamp and exclusions. Preserve previous runs.

Current-data exports retain validated_metric=false and suitable_for_ppfd=false. A code-test pass does not change those scientific flags. Connect changes through editor -> server -> rebuild -> viewer and verify this full route. Protect unsaved browser work and storage origin during any activation.

## 9. Validation and staged delivery

Deliver incrementally:

1. JSON reference loader and growth-count review, route navigation, scoped observation graph.
2. Unique observation collection, baseline rebuild and linked photo/3D review.
3. Optional side-pose candidates, frozen dependencies and explicit diagnostic selection.
4. One qualified same-session trial and comparison, or an exact missing-observation report.

Focused tests must cover:

- Malformed/missing JSON, incorrect identity, relative-path resolution, stale hashes and unchanged human records.
- Unique counts across routes/views; hidden leaflets never created; unknown parent assignments kept explicit.
- Repeated local point IDs on distinct leaflets/sessions never merged.
- Correct vertical/ring routes, wraparound, missing photos and deduplication.
- Visible points on partial leaflets versus ineligible whole-leaf bbox bounds.
- Original-pixel coordinates, backward-compatible backup/load/undo and split/relink provenance.
- Known synthetic pose/point recovery, unit/frame/distortion consistency, wrong matches and degenerate/missing inputs.
- Held-out leakage prevention, non-circular staleness propagation and baseline unchanged when hybrid is disabled.
- Actual server-to-viewer rebuild, failure/stale paths and diagnostic flags.

When accepted observations and poses are identical, route selection alone must produce identical geometry. Compare annotation workflow benefits separately from pose-source benefits. Report additional confirmed coverage, correction time, failures and held-out residuals where comparable. Extra reconstructed points do not demonstrate higher accuracy. If the baseline has no side pose, report that a direct baseline side-image residual is unavailable.

End with an English completion handoff: exact changed files, run commands, tests actually executed, saved artifacts, code/runtime activation state, real-data results versus synthetic results, and unresolved scientific limits. Do not claim full-plant reconstruction, measured curvature, growth prediction or PPFD readiness.

## 10. Document preparation outcome

This consolidated brief was written at the user's request. No source code, annotations, human JSON, camera settings or captures were modified; no reconstruction or model execution was performed during its preparation.
