# Automatic labeling drafts: Codex review

## Brief before implementation

Review Claude's completed `CLAUDE_AUTO_BBOX_LANDMARK_BRIEF_2026-09-20.md` against the automatic-labeling request. Inspect automatic mask proposals, landmark generation, physical-match acceptance, persistence, and server integration. Verify with deterministic tests only: no learned inference, training, downloads or PPFD. Preserve existing labels, calibration, outputs, and live browser work. Record reproducible findings and fix integration defects in owned tools when supported by evidence.

Status at start: Claude reports automatic mask drafts, heuristic landmark candidates, and geometric point-pair proposals. Real detection performance and appearance matching are explicitly unverified/unimplemented. Inspect acceptance boundaries rather than treating candidate count or test totals as reconstruction accuracy.

## Review result

The new implementation is present. Automatic backend drafts are class-agnostic, landmark proposals derive from region geometry, and cross-view matching is geometry-only. These are useful draft/review capabilities, not verified tomato detection or automatic physical correspondence. Two integration defects were reproduced without model execution. This user turn requested a check; application source was not modified.

### R1 / P1: splitting or relinking a view leaves new metadata on the old identity

`tools/leaf_point_annotator.html::moveLeafView` moves point observations, contours, boxes and regions but does not move `landmark_candidates[image_key]` or the corresponding `point_provenance[point_id][image_key]`. New automatic draft `assigned_to` references are also not reconciled by this function.

Reproduction: create/assign a draft, accept a landmark as b0 in one.jpg, then split that view. The destination has the accepted b0 observation but no candidate list or provenance. The original leaflet still holds the candidate and provenance for a photograph whose observation moved. This breaks source tracking and permits remaining candidates to be offered under the wrong leaflet identity.

Requested fix: transfer per-view candidates and accepted-point provenance with the observation, reconcile assigned draft references, and preserve an explicit move history. Test both split and relink, with accepted and pending candidates, preservation of other views, undo, and backup round-trip. Do not erase the old history or merge unrelated observations.

### R2 / P2: match ambiguity is checked in only one direction

`proposePointMatches` checks multiple eligible target partners per source, but not multiple source partners per target. In the existing synthetic camera fixture, source points [300,380] and [300.1,380] both pass gates against target [480,380]. Both proposals are reported eligible, although they compete for the same target candidate.

Requested fix: determine ambiguity from the complete geometrically eligible bipartite candidate set, checking degree on both sides before changing statuses. Preserve explicit human selection and do not silently choose a winner. Add reverse-direction and many-to-many regression cases. Current accept-state protection prevents accepting the same candidate twice, but it does not fix the misleading proposal status.

## Evidence generated now

- `build/auto_draft_review_20260920/reproduce.cjs`: read-only in-memory reproduction using the existing Node fixture; asserts and prints both defects. Run `node build/auto_draft_review_20260920/reproduce.cjs` from the project root.
- `build/auto_draft_review_20260920/source_hashes.json`: hashes of the reviewed annotator, segmenter, server and rebuild sources.
- `node --test tools/tests/leaf_annotator_auto.test.cjs`: **9 passed**. These existing tests do not cover R1 or reverse-direction R2.
- `python -m pytest -q tools/tests/test_automatic_masks.py tools/tests/test_serve_leaf_edit_session.py`: **11 passed in 59.85 s**, including mock HTTP requests and current/stale surface attachment. No learned model was run.
- The first reproduction harness attempt did not initialize the leaflet and failed before checking the application behavior; initializing it through the existing draft assignment path then reproduced both defects successfully.

## Runtime and remaining limitations

Inspected the active editor process: it still runs with `--segmenter unavailable` and without the saved `--patches` option. Code presence does not mean actual automatic mask generation is enabled in the user's current server. This review did not restart it or reload browser labels.

No real-model accuracy, landmark localization accuracy or correction-time claim is supported. The automatic mask filters use fixed pixel-area thresholds and a size-sorted cap; small-leaf retention is not guaranteed by the existing synthetic test. Inferred centerline candidates are correctly prevented from single-point acceptance. Actual midrib/vein detection and appearance-based matching remain unimplemented.

No original photo, label, calibration, previous reconstruction, config or core file was changed. Address R1/R2 before treating the automatic draft workflow as fully integrated.
