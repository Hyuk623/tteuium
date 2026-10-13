# Integration review request: P1 -> P2 -> P4 -> P3

Read [common instructions](CODE_REVIEW_COMMON_2026-10-07.md). Review the same source snapshot. Output only to `build/code_review_20261007_01/INTEGRATION/`. This is a review and coordination task, not implementation of the missing closed loop.

## Prerequisites and independence

Consume actual `REVIEW.md`, `findings.json`, `coverage.csv`, `validation.json`, and `boundary_contracts.json` from P1-P4. Check each snapshot ID, file hashes, command evidence and unresolved scope. A missing project report is `pending`, not approval. You may map interfaces early, but do not issue a final four-project verdict until all four reports are available or clearly report a partial review.

Independently verify cross-project findings and at least the critical producer/consumer paths in code. Do not simply concatenate reports or treat four passing test counts as end-to-end validation. Deduplicate shared-file issues while preserving each reporter's evidence and assigning exactly one fix owner.

## Boundary matrix to inspect

| Boundary | Critical checks |
|---|---|
| P1 -> P2 | Geometry identity, mm/frame transforms, one-sided tissue area, located surfaces, support/coverage, uncertainty, botanical-face evidence, optical eligibility versus proxy/generated geometry |
| P1 -> P3 | Same plant/compound/session/time, complete axis direction, physical area basis, method/pose/partition/capture-phase comparability, raw observation immutability |
| P2 reference -> P3 | Incident reference DLI, mol/m2/day, complete local day and supported horizon/domain; never tissue-absorbed light disguised as reference |
| P2 tissue -> P4 | Absorbed PPFD, face/source basis, per-patch area and per-plant partition, schedule/time alignment, no second absorption or side duplication |
| P3 -> P4 | Growth requirement basis, start/end states, structural versus total DM, interval and organ identity, no reuse/double demand |
| P4 -> P3 | Actual adapter existence versus deferred design; one-time resource spending and future constraints only if explicitly implemented and specified |
| P3 -> next P2 | Future geometry availability and optical-evidence gate; predicted state is not automatically measured or optically validated |
| Individual -> canopy -> individual | Stable source and instance identity, transforms, disjoint attribution, retained neighbor occlusion, no double carbon/area/nutrient counting |

## Reproduction strategy

Build one minimal labelled synthetic plant/leaf fixture with explicit units, frame, timestamps and independent expected quantities. Exercise the **existing** adapters with real producer outputs, including save/reload. Probe one missing/unsupported field per boundary and one mismatched identity/basis/time case. A stub that invents an unavailable scientific field does not demonstrate integration. If a link does not exist, report its exact dependency and stop that path honestly while testing independent links.

Check that a real producer result passes the declared compatible consumer and that incompatible results fail/return unavailable as specified. Include mixed-source geometry, canopy duplication, opposite faces, observed versus predicted state and partial interval cases where relevant. Tests that only reproduce matching example JSON are insufficient to prove the live producer path.

## Required outputs

- `INTEGRATION_REVIEW.md`: verified findings, interface readiness, per-project limits and Korean summary.
- `findings.json`: common issue schema, IDs `INT-B001`, including linked originating Pn finding IDs and deduplication notes.
- `boundary_matrix.csv`: producer/function, consumer/function, schema, field, unit/frame/basis/time/identity, adapter location, tested case, result, gap category and owner.
- `fix_order.csv`: ordered issue IDs, single owner, prerequisites, shared files, expected validation and severity. Avoid simultaneous shared-file edits; do not execute fixes during this review.
- `review_rollup.json`: each project's baseline/report hashes, coverage status, demonstrated defects, questions, skipped tests, review status and integration readiness. Status is not a physical-validity claim.
- `validation.json` and `repros/`: exact commands and outputs; independent expected versus actual assertions.

Classify unimplemented resource feedback, unresolved science and missing physical data separately from software defects. Preserve current decisions and protected data. End with a concrete review disposition and repair order; never claim the full FSP loop works merely because its four modules execute separately.
