# Pipeline implementation review — 2026-09-27

## Scope
Review the current S0–S8 wiring, source provenance, human-decision propagation and current run status against Claude's accepted implementation and handoffs. Preserve settled design decisions, including the explicitly authorized diagnostic feature-map pose route. This is an implementation review, not a redesign.

## Execution
Inspect existing code and generated manifests. Run focused existing tests and read-only diagnostic checks where useful. Do not run training, inference, the production pipeline, or change source data, human decisions or application code during this review. Record concrete findings and distinguish pending human inputs from implementation defects.

## Outcome

Reviewed `tools/plant_pipeline.py`, its plant configuration, identity importer, candidate integration, hierarchy builder, Document 06 runner, watcher, and the latest completed production snapshot `build/pipeline_20260927_202748/`. Claude's accepted architecture remains the baseline. No application code or research data was changed.

### Current execution

S0/S1/S2/S3 produced outputs for all four plants. S4 awaits human cross-view decisions; S5 has no direction-label exports. S6 failed for dwt_01 and waits for identities for dwt_02/03/04. S7 generated diagnostic hierarchy/viewer artifacts independently of S6. Therefore its `done` state does not establish successful Document 06 fusion or a leaf surface.

Mask review totals in this snapshot: dwt_01 268 accepted / 24 rejected; dwt_02 246 / 39; dwt_03 278 / 18; dwt_04 364 / 44. These are photo-level observations. Existing metric/PPFD flags remain false.

### Implementation findings

1. **P1 — Four-plant orchestration still calls a two-plant S6 runner.** `tools/instance_workflow.py:266` rejects plants other than dwt_01/dwt_02. After identities become available, dwt_03/04 will fail rather than execute fusion. Align execution scope with the accepted four-plant pipeline while keeping the separate development/evaluation protocol explicit. Do not silently turn additional plants into evaluation references.

2. **P1 — S7 hard-intersects masks regardless of visibility.** `tools/plant_hierarchy.py:52–73` records `full`/`partial`/`unknown` but uses every usable mask in `inside_all &= raw`. Partial visibility can remove valid hidden portions; unknown visibility is also used as a full spatial restriction. The current dwt_01 artifact contains six regions whose contributing observations all have unknown visibility. Preserve these as historical diagnostic intersection proposals, and align future supported-evidence computation with the accepted Document 06 positive-only treatment of partial observations. Never reinterpret these regions as verified full leaf extents.

3. **P2 — S2 can report done with ungenerated masks.** `tools/plant_pipeline.py:143–145` counts only `unreviewed` and `edited` in unfinished work. An isolated in-memory reproduction with one accepted item and one pending-generation item returns `done` and `not_generated=1`. Include generation failures/pending items in completion accounting. This is a latent defect; the current four-plant snapshot has zero ungenerated items.

### Current blocker and incomplete connections

- **Exact S6 source mismatch:** SHA-256 comparison of every recorded batch input found only the human growth JSON changed for dwt_01 and dwt_02. The paths end in `dwt_01_260920.json` and `dwt_02_260920.json` under `tomato_photos_organized_/260920/`. dwt_03/04 have no recorded input-hash mismatch. The catch-all error at `tools/instance_workflow.py:280–282` incorrectly suggests crop validation for this metadata change. Preserve the guard and history; classify changed dependencies and refresh derived metadata through a verified import path. This finding does not justify blindly replacing stored hashes. dwt_02 has the same latent blocker after identities are supplied.
- **S6 -> S7 is not connected:** `Plant.s7` passes structure, backup, masks and candidate proposals; it does not pass or read S6 evidence. The current six dwt_01 regions therefore come from S3 hull/mask intersections, not a completed Document 06 run. Distinguish these outputs in the viewer/status and preserve their provenance when integrating supported evidence.
- **Feature poses currently enter S4 and S7 only.** The S6 call has no extra-pose input and its runner loads the original capture. Human confirmation of a pair supported only by feature-posed photos will not by itself make those photos eligible for S6. Keep measured poses intact and carry the accepted diagnostic provenance if this connection is implemented.
- **S5 remains an implementation placeholder as well as a data wait:** with `direction_labels` set, it still reports `unavailable` because no export adapter is connected. Supplying labels alone is not sufficient. S8 is an optional separate tool, not a step in the current orchestrator loop.

### Validation

- Existing pipeline/mask tests: 32 passed.
- Existing Document 06 evidence/workflow/identity-import tests: 20 passed.
- Read-only hashes checked for all four active batch manifests.
- S2 incomplete-generation completion defect reproduced in memory using mocked inputs; no research masks were altered.
- No production pipeline, training or inference was run. Passing unit tests do not cover the integration gaps above.

### Follow-up order

Keep Claude's design. First resolve the classified metadata freshness blocker; align S6's plant scope and diagnostic pose inputs; make S7 evidence provenance and occlusion behavior consistent; correct S2 completion accounting. Continue human identity/visibility review in parallel. Implement the S5 adapter when the first real export is available. Document 05 remains deferred.
