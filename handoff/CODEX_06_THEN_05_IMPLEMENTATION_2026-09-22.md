# Implementation brief: Document 06 followed by Document 05

The user explicitly requested implementation of the accepted English plan. This request authorizes this Codex implementation despite the previously recorded Claude-led interval; Claude retains follow-up leadership through 2026-09-26 18:00 Asia/Seoul. Avoid editing files concurrently with Claude.

## Existing behavior and scope

Reuse the existing local editor, cached SAM masks/logits, original-pixel annotations, identity/membership controls, measured camera poses, bbox extent solver and immutable rebuild outputs. Current real batches contain 577 ready leaflet observations (576 unreviewed, one edited), no accepted masks, and 90 compound observations with one generated. Solved poses remain below the 1-pixel quality gate. No new detector training, learned Re-ID, remote inference, model download, PPFD, growth simulation or SfM is included.

Implement cached sensitivity sweeps with independent reviewed references; accepted-mask identity association; strict/diagnostic finite 2 mm voxel evidence fusion; and DBSCAN XYZ/PCA feature sweeps. Keep unknowns and excluded observations explicit. No synthetic ground truth or auto-acceptance of real labels. Partial visibility supplies positive evidence, not negative carving. IDs stay distinct from point correspondences and clustering features. Cluster results are proposals, not physical identities or leaf surfaces.

## Implementation sequence

1. Read-only snapshots/adapters, settings/reference manifests and metric helpers. Add three operations to the current job service: sensitivity_sweep, instance_fusion and instance_clustering.
2. Reuse current mask review and identity editing. Wire snapshot and source-revision staleness into existing UI. Add result layers and source-photo/mask inspection in the same editor.
3. Chunked finite bbox-region fusion with per-view support/contradiction/unknown, provenance, strict gate and diagnostic flags. Use the existing camera projection and extent implementations.
4. DBSCAN on XYZ and XYZ plus local PCA descriptors, fixed experimental parameter grid, independent-reference-only ARI/NMI and explicit ambiguous/noise results.
5. Synthetic and HTTP/UI tests, real six-photo pilot (dwt_01 11/24/25 and dwt_02 11/27/28), source-preservation audit and final English handoff. Real runs with missing reviewed masks/identities/references must report unavailable, not manufacture results.

All edits remain in tools/, tools/tests/, handoff/ and generated build/. Original config/, docs/, tomato3d/, tests/ and human data/records/ remain untouched. No changed image export is imported, so the known importer crop-validation issue is not hidden or bypassed.

## Validation and completion

Cover crop/pixel/unit projection, read-only cached sweeps, matching/merge/split metrics, partial occlusion, route deduplication, identity link/split provenance, missing/failed poses and unbounded extents, synthetic voxel support, clustering/noise/PCA degeneracy, stale snapshots, token/origin checks and current save/undo/export regressions. Exclude UI fixtures from all research evaluations. Record actual code, commands, tests, real blockers and output state after implementation.

## Outcome

In progress.

## User scope override — 2026-09-22

Implement Document 06 ONLY. Document 05 clustering is deferred and must not run or be exposed in the UI. The user also requested a mask brush: paint, erase, adjustable size, explicit save and undo for both compound and leaflet observations. Preserve existing history and use no inference for brush edits. This scope supersedes the earlier sequence above.

## Final outcome

Document 06 only implemented, including the user-requested mask brush. Document 05 deferred. Python 47 and Node 39 tests passed. Six-photo/99-observation cached pilot completed; no independent references or confirmed cross-view identities were fabricated. 723 existing source/state files unchanged. Full details and commands: CLAUDE_DOCUMENT_06_ONLY_COMPLETION_2026-09-22.md.
