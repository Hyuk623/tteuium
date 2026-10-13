# Incident-direction callback preparation

Date: 2026-10-03. Status before implementation: partial; protected producer absent.

## Request and inspected behavior

The user explicitly resumed the light-only angular completion task. Parent and project agreements, the Claude readiness handoff, readiness execution history, four-project change plan/decisions, bridge documentation and schema were inspected. P3/P4 integration, native execution, inference, training and uploads remain excluded.

`tomato3d/light/raytrace.py::direct_light(receivers, fixtures, occluders, leaf_transmittance, settings) -> DirectLight` still has five positional-or-keyword parameters and no diagnostic callback. Its internal `direction`, `shaded_per_emitter` and `cos_incidence` already contain the required transport quantities. Its returned arrays contain only fixture IDs, received, unoccluded and upper-side PPFD. SHA256 at inspection: `6936a154b67a0cd796f36c8e75760eea61588da9971c7349a29584f1f13747d8`.

The user explicitly preserves Claude/core ownership of `tomato3d/` and root `tests/`. Those files will not be changed. Existing bridge production exports deliberately reject directional records and advertise `pending_core_diagnostic_hook`; existing synthetic algebra is not live angular transport.

## Independent owned work

Add a passive, bounded callback collector in `tools/light_direction_diagnostics.py`, with protocol tests under `tools/tests/`. It will validate explicit fixture/path inventories, global receiver/emitter indices, contiguous chunks, zero versus unknown, buffer lifetime and received/normal-side reconciliation with a supplied `DirectLight` result. It will accumulate receiver-level area-weighted unnormalized F/M/B only. It will not trace rays, infer lamp-center directions, execute native transport, or automatically enable a guessed producer API.

Publish an exact proposed keyword-only callback/payload contract for the core owner. This proposal is not evidence that the core adopted or emits that interface. Keep current production schema/capabilities/consumer gating intact until actual producer integration can be tested. No speculative production schema expansion is necessary for the already-defined F/M/B fields.

## Validation and artifact policy

Exercise protocol completeness, invalid metadata, unknown values, normal-side reconciliation, resource bounds and reused buffers, plus existing angular algebra regression. All numerical comparisons use `tools/light_growth_schema.json::numerical_policy` (absolute 1e-10, relative 1e-9; direction degeneracy 1e-12). Protocol tests with supplied chunks are explicitly not actual transport off/on parity or physical validation.

Record a new read-only core capability audit and test evidence under a fresh `build/` path. Independently validate the existing package without rewriting its hashes. If a hashed producer/schema/exporter/consumer file changes, regenerate preparation/calculation/export under a fresh path. Append results and exact remaining core acceptance conditions after validation.

## Execution outcome

**Partial completion. Actual angular transport/export remains blocked by the absent protected producer interface.** No files in `tomato3d/`, root `tests/`, `config/` or `docs/` were edited. The core hash remains the inspection hash above. No P3/P4 linking, native execution, inference, training or upload occurred.

Added `tools/light_direction_diagnostics.py` and `tools/tests/test_light_direction_diagnostics.py`; updated the bridge documentation. The collector consumes supplied chunks and reconciles total and normal-side PPFD against a supplied reference before returning area-weighted receiver F/M/B. It enforces explicit inventories/budgets, global indices, zero/unknown distinction, chunk completeness, unit directions and borrowed-buffer lifetime. It does not extract actual core paths yet. The detailed producer proposal and acceptance checklist are in `CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md`.

Validation:

- Combined collector and existing bridge suites: **60 passed in 43.25 s** (28 protocol checks + 32 existing bridge checks).
- A subsequent explicit-null inventory metadata guard and regression assertion: **28 collector tests passed in 0.77 s**. No other production dependency changed afterward.
- Independent consumer reread of the current `_04/package`, `P1_in_canopy`, `P1_COPY_in_canopy`: **all valid**, with original source/code/artifact hashes intact. This is validation of the existing scalar/spatial/time packages, not a newly generated directional result.
- New evidence: `build/light_direction_callback_20261003_01/verification.json`, `consumer_checks.json`, final/initial core audits and both JUnit reports. Initial `core_audit.json` preserves the pre-final-guard collector hash; `final_core_audit.json` identifies the tested final source. The core hash is identical in both.
- No live diagnostic off/on parity, actual-path scalar/side reconciliation, real-producer translation/rotation, schedule-to-direction export, or diagnostic core runtime/peak-memory measurement was possible. All remain explicitly unverified. The sink's 1000-path, one-path-per-chunk check only establishes bounded retained accumulator storage, not a core performance result.

No schema fields were added: existing `light-growth-1` already defines the requested F/M/B output components. Exporter/consumer/capability code was not modified to accept fabricated production paths. The new collector is not imported by those producers, so the current packages remain fresh and did not need recalculation. No old package hash was changed, and no fake angular package was created.

Next dependency: core owner implements/reviews the proposed callback and returns actual producer tests. Then Codex can wire the full-scene call, per-fixture schedules, supported compound frames/regions, independent angular consumer checks and fresh preparation/calculation/export. Real reviewed surfaces/light/calibration are still absent; no physical accuracy or growth-direction readiness claim.

The verification driver is a generated build script. `python -m build...` failed because an installed `build` package shadows the output directory namespace; running it with `runpy.run_path` from the project root succeeded. This did not change simulation inputs or results.
