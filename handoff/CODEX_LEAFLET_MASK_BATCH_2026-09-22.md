# Bbox-prompted leaflet mask batch implementation

## Authorization and scope

The user explicitly confirmed implementation and local mask inference after clarification of the stale planning-only sentence. Process dwt_01 and dwt_02: 30 photographs, 577 leaflet annotation observations (292 + 285), not 577 physical leaflets. No training, cloud API, cross-view identity assignment, landmarks, reconstruction or PPFD execution. Every mask requires individual human acceptance. User-facing controls and explanations must be Korean.

## Inspected baseline

Claude's original-pixel COCO exports and mapping reports already cover all 30 photographs. Reuse their verified uncropped stretch transform and preserve original annotation IDs/provenance. Existing tools/leaflet_segmenter.py supplies SAM prompts/crops and verifies the checkpoint; tools/serve_leaf_edit_session.py supplies the local editor, session authentication and serialization lock; tools/sam_mask_tuner.js supplies sensitivity thresholding. The configured SAM 2.1 Hiera Tiny checkpoint SHA-256 was independently checked, with CPU and four threads.

The existing prompted mask conversion selects a dominant connected component. This batch must instead retain the complete raster, including holes and tiny/disconnected regions. Existing acceptProposal creates a mask-derived bbox and requires a physical leaflet target; batch acceptance must store a separate per-source-annotation mask without replacing the human bbox or assigning physical identity.

## Implementation contract

- Add persistent batch orchestration under tools/, attached to the existing local editor. Generated files stay in a new build/leaflet_mask_batch_20260922/ directory; source photos, labels, session seeds, calibration, config and previous results remain read-only.
- Manifest binds plant, session, source annotation, image hash, source bbox, coordinate transform and model configuration. Only class leaflet is eligible. Unknown or failed mappings retain explicit failure records.
- Cache complete crop-resolution candidate logits and model scores, keyed by image, bbox, model/config and explicit prompts. No automatic centre click. Resume reuses unchanged results; include/exclude edits affect only one item. Sensitivity defaults to 20, baseline 50, using the existing threshold formula.
- Keep generation state separate from review state. All accepted masks must reflect an explicit individual user action. Candidate/threshold/polygon changes clear acceptance. Hold/reject/undo are persisted with revision checks and history; original observations never change.
- Integrate Korean review controls into the existing editor, with enlarged source crop, original bbox, mask, candidate switching, include/exclude prompts and direct contour editing. Risk signals order review but never accept masks. Save accepted-only exports with original pixel coordinates and separate original bbox/mask bounds.
- Pilot one middle and one side photo per plant, then all 30. Preserve every one of the 577 observation states, including errors and holds. Report generation and review time and unchanged-acceptance ratio; review metrics stay unavailable until actual user review.

## Validation

Tests cover coordinate restoration, source-label preservation, disconnected pieces/holes, cached threshold changes, candidate switching, accept/hold/reject/undo, optimistic revision conflicts, restart/resume, changed-prompt invalidation, failures, accepted-only export and existing endpoint authentication. Inspect pilot overlays before full execution. Keep actual outcomes below; do not describe drafts as validated segmentation or 3D surfaces.

## Implemented and verified

- Added `tools/leaflet_mask_batch.py`, `tools/leaflet_mask_batch.js`, and `tools/tests/test_leaflet_mask_batch.py`. Extended `tools/leaflet_segmenter.py` with a logits-preserving predictor and `tools/serve_leaf_edit_session.py` with authenticated batch endpoints and the integrated Korean review panel. Existing single-item endpoints and legacy annotation storage remain compatible.
- Full tools suite: **235 passed, 1 skipped** (`build/leaflet_mask_batch_20260922/pytest_full.txt`). After adding the completion audit/CSV command, the focused batch suite passed **12 tests**. JavaScript syntax checked with Node.
- Real pilot: dwt_01 middle 21 / side 11 generated 56 drafts; dwt_02 middle 21 / side 11 generated 35 drafts. Four photos, 91 drafts, no generation failures. Original-coordinate overlays inspected for both plants. Dark/overlapping leaves sometimes have incomplete or mixed masks; this is why every observation stays unreviewed.
- Browser tests on isolated `ui_test_fixture/` copies verified threshold 20 -> 50 -> undo, individual acceptance, hold, candidate change, correction controls and accepted-only export. No actual dwt_01/dwt_02 mask was accepted by the agent. Fixture exports are test artifacts and must be excluded from research/training data.
- Real include/exclude refinement on a fixture copy affected that observation only. The include pixel was inside and the exclude pixel outside the new mask; the other item was byte-identical. At sensitivity 20 the new mask was too narrow to call a complete leaf. Comparing sensitivity 50 without any configured model expanded its area from 5,305 to 41,289 pixels while the stored logits hash remained unchanged. This demonstrates reversible thresholding, not verified segmentation accuracy.
- Real interruption/resume preserved completed items. Process-level write leases also protect review/export, including against a CLI worker. Added bounded atomic-replace retries for transient OneDrive locks. Fixed the existing Windows early-POST rejection reset by consuming only a bounded request body before rejection; Host/Origin/token validation remains mandatory and tests pass.
- Usage, restart commands, files and API contract: `CODEX_LEAFLET_MASK_BATCH_USAGE_2026-09-22.md`.

## Completion status

Full generation and final source/cache audits are in progress. Do not treat this section as a completed human review. Final counts and timings will be appended after the remaining jobs finish.

## Final generation and audit outcome — 2026-09-22

This dated completion entry supersedes the in-progress status above. Implementation and the authorized generation run are complete; individual human review is still pending.

| Plant | Photos | Saved candidate sets | Runtime failures | Empty default masks at sensitivity 20 | Human accepted | Unreviewed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dwt_01 | 14 | 292 | 0 | 2 | 0 | 292 |
| dwt_02 | 16 | 285 | 0 | 3 | 0 | 285 |
| Total | 30 | 577 | 0 | 5 | 0 | 577 |

A ready generation state means the candidate arrays were saved, not that the selected mask is complete or correct. Five default selections are empty at sensitivity 20 and require candidate/threshold review or explicit correction. No empty mask can be accepted. Nonempty masks also require individual human acceptance. The counts are per-photo observations, not distinct physical leaflets.

Final audits account for every observation, show no changed source hashes (38 checked input paths for dwt_01 and 42 for dwt_02, with possible shared paths), and verify all 577 active logits-cache hashes. Both workers have stopped normally. Source photos, human boxes/other classes, prior annotations, calibration and earlier reconstruction outputs remain preserved. Audit snapshots and per-item CSVs are in each plant output directory. Aggregate files: `build/leaflet_mask_batch_20260922/completion_report.json` and `completion_counts.csv`.

Recorded processing wall-time sums are 2,296.13 s (38.27 min) for dwt_01 and 2,678.42 s (44.64 min) for dwt_02. Per-item medians are 5.62 s and 6.18 s respectively. Sums include loading/compression and wall-time interruptions, so they are neither uninterrupted inference benchmarks nor total project elapsed time. Human review/edit times and unchanged-acceptance fraction are unavailable (null), because no real observation was reviewed or accepted by the agent.

The integrated review pages are served locally at http://127.0.0.1:8821/ (dwt_01) and http://127.0.0.1:8822/ (dwt_02). The dwt_01 page was visually verified after the final toolbar/zoom changes; no browser console errors were reported. The action toolbar remains above the image. Use `CODEX_LEAFLET_MASK_BATCH_USAGE_2026-09-22.md` for restart commands and review/export behavior. Test fixture acceptances/exports are excluded.

Next: the user reviews every observation, corrects masks as needed, and exports accepted masks. Claude should review the tooling changes before connecting exports to later identity/landmark/geometry work. This task did not run training, cross-view identity assignment, reconstruction or PPFD, and does not change existing geometry quality gates.
