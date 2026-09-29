# Automatic draft corrections and backend activation

User request: resolve the two reproduced review findings and enable the disabled automatic segmentation backend.

Scope: transfer view-specific landmark candidates and point provenance when splitting/relinking a leaflet, reconcile assigned draft references, preserve history and undo; detect competing matches in both directions. Add regression coverage before deployment. Reuse the installed SAM checkpoint and runtime, verify availability and perform a bounded smoke check if feasible. Preserve original photos, calibration, saved annotations and session identity. No training, bulk inference or automatic acceptance of proposals. Update this brief with actual validation and activation outcomes.

Reference: CODEX_AUTO_DRAFT_REVIEW_2026-09-20.md. Application edits confined to tools/ and tools/tests/. Existing diagnostic geometry restrictions remain unchanged.

## Implemented and verified

- `moveLeafView` moves per-view landmark candidates and point provenance, retaining other views. Assigned automatic drafts follow the destination identity with an appended identity-move history event. Historical lineage is preserved. Existing target metadata is never silently overwritten. Cached point matches are invalidated.
- `proposePointMatches` counts eligible graph degrees on both source and target sides before changing statuses. Many-to-one and many-to-many alternatives remain ambiguous in either viewing direction.
- SAM automatic generation now uses configurable `points_per_batch` (default 1) to limit transient mask memory on this CPU. The existing 24-by-24 sampling grid and filtering thresholds remain unchanged.
- Node editor suite: 64 passed; subsequently added split-undo/collision regression and reran the automatic-label file: 12 passed (65 distinct Node tests total).
- Python automatic-mask and server suite: 13 passed in 462.95 seconds. Separate automatic-mask run: 6 passed, including batch-setting tests with a stub generator (no model execution in unit tests).
- Actual checkpoint verification and SAM model loading succeeded: SAM 2.1 hiera tiny, torch 2.13.0+cpu. Cold load took 649 seconds on this host.
- Checked live rebuild jobs: none running. Restarted only the identified editor server, preserving port 8821, session, run directory and initial-backup arguments; enabled the existing SAM config. New process ID: 27332. HTTP status confirms backend=sam2, available=true, automatic=true, is_mock=false; served HTML contains both fixes.
- A single original photograph (IMG_7913.png) is being tested through `/api/segment_automatic`; result will be recorded below. No automatic draft is accepted or merged into browser labels by this check.

## Reproduction / deployment

Run `node --test tools/tests/*.test.cjs` and `python -m pytest -q tools/tests/test_automatic_masks.py tools/tests/test_serve_leaf_edit_session.py` from the project root.

Activation scripts and outputs are in `build/auto_draft_review_20260920/`. Keep the existing launch command but replace `--segmenter unavailable` with `--segmenter sam2 --segmenter-config build/photos1_manual3d_20260919/sam_auto_20260920/sam2_config.json`. The default backend remains unavailable for unrelated sessions. No weights downloaded, no training, no PPFD run, no calibration or original annotation edits. Existing damaged identity records are not guessed or automatically migrated.

### Actual runtime note

The restarted server has loaded the real model and instantiated automatic generation with 24 points per side / batch size 1. SAM emits its existing missing optional `sam2._C` extension warning and skips that optional postprocessing step. This is not a model-load failure; do not describe the optional hole/sprinkle postprocessing as verified. The application-level mask area/ring filters still apply. The runtime and vendor files were not modified or reinstalled.

## Final bounded smoke outcome: timeout, not success

The original-photo automatic HTTP request timed out after 1800 seconds, including lazy model initialization. No candidate response was received or accepted; do not claim successful end-to-end automatic detection. The server was still computing. A fresh job check confirmed no running rebuild jobs; the identified editor process is being restarted with the same SAM-enabled arguments to discard this timed-out trial and release resources. Browser storage and original data remain untouched.

Resolved: identity metadata migration, bidirectional ambiguity, and disabled backend configuration. Still unresolved: practical CPU latency of whole-image automatic mask generation. The real model loads, but useful automatic draft throughput has not been validated. A lower-resolution/coarser preview profile with original-pixel coordinate mapping, or GPU execution, needs separate implementation/validation; no such performance change is claimed here. Do not run finish.cjs, whose success precondition is deliberately unsatisfied.
