# Existing pipeline to static XL: implementation brief

## Request and inspected baseline
Update `build/PIPELINE_FLOW_2026-09-28.md` using the user's problem/solution record, finish the path through XL export preparation, and prepare a Claude handoff. The latest immutable input is `build/pipeline_20260928_122948/`, containing Claude's dwt_04 hull-trunk fix. Previous progress was documentation consolidation; this work connects executable export and verifies its outputs.

## Changes and boundaries
- Revise the Korean flow document to map the user issues to existing stages, separate deployed functionality from proposals, and include concrete XL readiness/export/verification commands.
- Add a terminal handoff operation reusing `groimp_structure_export` and `groimp_static_verify`, with per-plant results, source hashes, upstream limitations and a clear generated/verified/failed distinction. Expose it through an opt-in `plant_pipeline --xl` path and a standalone existing-run CLI. Never modify the input run's status after its hashes are captured.
- Preserve hull-trunk metadata and single-view petiole limitations. S7 positions stay S7 diagnostic estimates, never relabeled S6 evidence. Do not invent leaf meshes, membership, hidden organs or growth rules.
- Correct the documented S2 incomplete-generation completion accounting; leave other S6/S7 research integration gaps explicit rather than claiming they have been repaired by an export step.
- Export and locally verify all four plants from the fixed current run into new build outputs. No production reconstruction rerun, learned inference, training, Kaggle/Colab job or user-label mutation is required for this validation.
- Existing source snapshots and earlier outputs remain unchanged. Claude receives exact commands, verified artifacts and remaining human/implementation gates.

## Verification
Test mixed export success/failure, upstream failed-stage propagation, retained stem/petiole metadata, explicit runtime-verification state and input preservation. Run the relevant export/pipeline tests. Execute GroIMP compile/reset/save/reopen for each new real export. Update this handoff and LOG with actual outcomes; do not equate static transport completion with research completion.

## Completed implementation and execution

- Updated the requested Korean flow document in place. Previous version preserved at `build/pipeline_to_xl_20260928/PIPELINE_FLOW_before.md`. Added E1–E18 stage mapping, corrected model-deployment/S5/S6/S7 statements, and added executable XL delivery instructions and remaining-work gates.
- Added `tools/plant_xl_handoff.py`, reusing the existing exporter and verifier. It exports a fixed run into a fresh directory, retains per-plant upstream open stages and human tasks, records source/output hashes, and distinguishes generated, runtime-verified and failed deliveries. Failed plants remain in the report; CLI returns failure for any failed delivery.
- `tools/plant_pipeline.py` now supports optional `--xl` and `--groimp-core`. The terminal operation runs after normal status/site generation without rewriting hashed source statuses. Existing invocations without these options retain their workflow.
- S2 completion accounting now includes all unfinished review/generation states and cannot count an accepted-but-not-generated item as complete. This does not alter historical snapshots or labels.
- Tests: `python -X utf8 -m pytest tools/tests/test_plant_xl_handoff.py tools/tests/test_groimp_structure_export.py tools/tests/test_groimp_bridge.py tools/tests/test_plant_pipeline_tools.py -q` → **32 passed in 9.77 seconds**. The pipeline terminal hook was tested using isolated fixtures; no production S0–S7 rerun was needed.
- Real command: `python -X utf8 -m tools.plant_xl_handoff --run build/pipeline_20260928_122948 --out build/xl_handoff_20260928_122948 --core ../groimp/core.jar` → **all four plants runtime_verified**.
- Every plant passed GroIMP CLI compile/reset/save/reopen; source hashes were rechecked. Maximum coordinate transport error was below `0.001 mm` (largest observed approximately `2.25e-14 mm`). This is file transport precision, not plant measurement accuracy.
- The new dwt_04 export preserves `method=hull_trunk`, unavailable diameter, and its single-view sub-stem evidence. dwt_01 also has one limited sub-stem axis. All four contain zero leaf meshes; automatic candidates remain separate and hidden by default. GUI visual inspection remains unverified.

## Claude entry point

Read `build/xl_handoff_20260928_122948/CLAUDE_README.md` and `handoff.json`, then each plant's `export/` and `verification/verification.json`. The new delivery supersedes the old run for this static XL check; do not alter the older export or republish the remote Claude Artifact implicitly.

For a future reviewed pipeline run:

```powershell
python -X utf8 -m tools.plant_pipeline --all --xl --groimp-core ../groimp/core.jar
```

For an existing immutable run:

```powershell
python -X utf8 -m tools.plant_xl_handoff --run build/<run> --out build/<new-delivery> --core ../groimp/core.jar
```

Omit `--core` for generation only. Static export remains possible while S6 fails, but failure and provenance remain explicit. Pending research integration stays in `CODEX_PIPELINE_REVIEW_2026-09-27.md`: classified metadata freshness, four-plant S6/diagnostic pose scope, S6→S7 consumption, partial-visibility handling, and the S5 import adapter. Only S2 completion accounting from that review was fixed here. Heavy Colab offload, PPFD, growth rules, new training and validated surfaces are outside this completed connection.
