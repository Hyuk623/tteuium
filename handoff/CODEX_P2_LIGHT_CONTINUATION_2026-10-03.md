# P2 continuation: actual direction output and D9 light basis

Date: 2026-10-03. Request: execute `CODEX_P2_LIGHT_CHAT_PROMPT_2026-10-03.md`.

## Work brief before further work

The previous turn made progress by implementing and testing a passive proposed-protocol collector; it did not connect an actual producer. This is the first audit turn for the newly active P2 continuation objective. Current inspection still finds the five-argument protected `direct_light` signature with no callback. Latest LOG/TODO and matching handoff filenames contain no adopted core-owner delivery. No process or core-owner job is known live, so this is a dependency, not a verified running-job wait.

Parent/project agreements and the prompt's referenced readiness, callback, execution, schema and integration decisions apply. D1-D10 are now recorded, including D9: fixed-horizon DLI affects P3 size targets only; no adopted light-to-growth-direction response. D3 still defers linking. Do not edit protected core, guess a producer API, introduce another tracer or execute P3/P4/native/inference/training/upload work.

Planned independent work: audit the current exported light basis, spatial scope, timing and coverage against requirement 8/D9; identify exact existing fields and any real gap before changing a schema. Validate the current immutable package and splits, and record a requirement-by-requirement status using current files and hashes. Reuse the delivered scalar/time and collector work instead of repeating implementations. No diagnostic test with supplied chunks will be reported as actual transport parity.

Core dependency: `CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md` already specifies the exact proposed callback, metadata, missingness, buffer lifetime, budgets, units and real-producer acceptance tests. Codex may only connect an explicitly adopted compatible producer after its delivery.

## Audit finding and scoped correction plan

The first current-state audit verified 48 incident-DLI rows and their explicit spatial/temporal support. It also exposed a unit metadata ambiguity: `dli_mol_m2_day` is labelled `mol/m2` in the schema, the same as generic interval dose, whereas the user's daily indicator contract explicitly uses `mol/m2/day`. Correct only this column's unit metadata and document it. Do not change values, divide again by day length, turn partial intervals into DLI, or alter actual DST-day seconds. Preserve `incident_dose_mol_m2` as `mol/m2` and photon totals as `mol`.

This necessary metadata change makes historical schema/code hashes stale against the live workspace; preserve those records and generate fresh preparation, calculation, export and instance splits. Re-run the focused bridge/protocol checks against the final schema. This correction is independent of the missing core callback and does not enable angular output or P3 covariate selection.

## Delivered outcome

**Partial; active goal remains incomplete.** The only production change in this continuation is `tools/light_growth_schema.json`: the `dli_mol_m2_day` column unit is now `mol/m2/day`. No function signatures, formulas, numeric values, columns or availability gates changed. `tools/LIGHT_GROWTH_BRIDGE.md` documents the unit clarification and D9 field-selection boundaries. Consumer code needs no arithmetic change: it already checks exact authoritative schema, DLI/incident-dose identity, full-local-day coverage, time integration and unsupported angular claims.

Current producer remains:

```python
direct_light(receivers, fixtures, occluders, leaf_transmittance, settings) -> DirectLight
```

No adopted callback. Protected-core SHA256 remains `6936a154b67a0cd796f36c8e75760eea61588da9971c7349a29584f1f13747d8`. The existing proposed collector has not been wired to this signature. Core scalar/normal-side return values cannot recover actual per-path direction, and no attempt was made to infer it.

## Exact D9 field map

| Required basis | Existing authoritative output |
|---|---|
| Incident versus absorbed | `light_dose.csv::dli_mol_m2_day` and `incident_dose_mol_m2`; absorbed dose and photon totals remain separate fields. DLI uses incident received PPFD only. |
| Units | DLI `mol/m2/day`; interval dose `mol/m2`; integrated photons `mol`; duration `s`; PPFD `umol/m2/s`; area `m2`. |
| Spatial scope | Dose primary key plus `level`, `entity_id`, source/instance/session/compound, fixture, backend and replicate. No default organ or canopy average. |
| Surface/area convention | `schema.json::conventions` and `area_basis_id`: supported one-sided metric area, two-face receipt per that area. Join time-resolved `compound_light_features.csv` rows for supported area, estimated-total availability and spatial coverage status. |
| Timing/coverage | Dose `start_at`, `end_at`, `timezone`, `requested_seconds`, `covered_seconds`, `complete_local_day`; exact per-fixture boundaries/fractions and schedule evidence in `light_intervals.csv`. |
| Geometry versus exposure | `package.json::geometry_validity`, including observation clock, validity window and `geometry_mode`; `schedule.provenance` distinguishes artificial assumptions from actual schedule evidence. |
| Missingness | Numeric `unavailable` in CSV, field-specific reasons in `availability.json`; unknown exposure is never off. Incomplete days do not receive a finite DLI. |
| Provenance | Package source/code/artifact hashes and full canopy geometry hashes; source/instance identity preserved in reporting splits. |

Dose-to-feature matching uses `(run_id, scenario_id, plant_instance_id, session_id, compound_id, backend, replicate, level, entity_id, fixture_id)`, restricting feature rows to time-resolved `region_id=whole_supported`, `quantity_frame=grow`. Follow each feature's snapshot/time-step into geometry validity and fixture intervals. The `all` aggregate refers to the actual fixture schedules; there is no additional aggregate lamp schedule to add.

The new synthetic package contains 48 daily dose rows: 21 leaflet, 15 compound, 9 plant and 3 canopy records across fixtures/aggregates. All 48 are finite complete-declared-day DLI records and match the supporting features/intervals. This is a **held-current-geometry synthetic scenario**, not a measured future or daily plant exposure. Whole-surface coverage remains unknown; supported tissue is not promoted to whole plants. No fixed-horizon covariate, representative day, biological coefficient or calibration match was selected for P3.

## Fresh outputs and verification

Fresh preparation, existing-core scalar calculation and exports were generated in:

- `build/light_growth_readiness_20261003_05/inputs`, `prepared`, `hierarchy_results`, `request.json`.
- `build/light_growth_readiness_20261003_05/package`.
- `build/light_growth_readiness_20261003_05/P1_in_canopy` and `P1_COPY_in_canopy`.
- `consumer_checks.json`, `copy_roundtrip.json`, `p2_regression.junit.xml`, `delivery_verification.json` in that run directory.

All three serialized packages pass independent consumer validation. **60 focused tests passed in 55.29 s**, including existing scalar/side/time/frame/native-unavailable and canopy checks plus supplied-chunk protocol tests. Absolute tolerance is 1e-10 and relative tolerance 1e-9. Matching all numeric fields and missingness in all five tables of the main package and both splits against immutable `_04` produced **maximum absolute numeric difference 0.0**. The only schema content change is the one unit string. `_04` manifests and every artifact still match their original hashes; their older live-schema/code freshness is intentionally superseded, never rewritten.

Current requirement/D9/core evidence: `build/p2_light_continuation_20261003_02/core_audit.json` and `verified/{consumer_checks,d9_basis_audit,requirement_audit}.json`. `_01` retains the pre-correction audit. Its first join attempt incorrectly expected a schedule for aggregate `fixture_id=all`; the audit was corrected to join the real fixture schedules, without changing production calculations.

Executed commands:

```powershell
python -X utf8 -m tools.light_growth_demo --out build/light_growth_readiness_20261003_05
python -X utf8 -m pytest tools/tests/test_light_direction_diagnostics.py tools/tests/test_light_growth_bridge.py -q --junitxml=build/light_growth_readiness_20261003_05/p2_regression.junit.xml
python -X utf8 -m tools.light_direction_diagnostics --out build/p2_light_continuation_20261003_02
python -X utf8 -c "import runpy; runpy.run_path('build/p2_light_continuation_20261003_02/audit.py', run_name='__main__')"
```

Use new output paths for any later execution; all listed paths now exist.

## Completion audit against the P2 prompt

| Item | Current evidence/status |
|---|---|
| 1 | Current signature/hash and latest delivery records inspected; actual producer absent. |
| 2 | Ownership respected; exact dependency already documented; independent D9 metadata work completed. |
| 3 | Blocked: no adopted actual contribution stream. |
| 4 | Unverified: real callback off/on, same-call path, occlusion and performance parity cannot run. |
| 5 | Partial: existing algebra/passive protocol verified; actual transport moments/rotation/translation still unavailable. |
| 6 | Partial: scalar schema metadata and new packages delivered; angular bridge/consumer/schedule/frame connection blocked. |
| 7 | Scalar quantity/DLI separation and timing checks pass; daily-unit metadata clarified. |
| 8 | P2 basis/scope/time/coverage exported and verified; downstream selection deliberately unperformed under D3/D9. |
| 9 | No growth-direction response, geometry change, biological coefficients or carbon calculation added. |
| 10 | Fresh per-instance exports retain complete source-canopy shading/provenance; actual angular split awaits producer. |

The scope is not complete. Core owner must return the adopted interface and real producer evidence specified in `CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md`. Only then can Codex connect actual contributions to fixture/time/compound/frame outputs, independent angular consumer validation and a fresh directional package. This new scalar package must not be presented as directional evidence.

Known real-input limitations remain reviewed metric leaf surfaces, measured lamp/optics/schedule data, supported compound observations and independent physical calibration. Synthetic tests establish software accounting only. No new search for already-known absent observations was performed; physical and biological validation remain false. No P3/P4 integration, Native execution, inference, training or uploads occurred.


## Continuation dependency audit 2

Previous turn was progress (daily unit clarification, fresh _05 outputs and verification). Current source signature/hash and relevant prompt/decision/callback documents are unchanged; no new adopted producer delivery was found. _05 main and both split package manifests plus all recorded source/code/artifact hashes remain valid. No live job is known; this is not a verified wait. Independent authorized preparation is delivered. Actual path extraction/export/parity still requires protected-core owner work. Evidence: build/p2_light_continuation_20261003_02/blocker_audit_2.json. This turn makes no implementation progress; tests/simulations were not repeated. Goal remains active, incomplete, at consecutive dependency audit 2.


## Dependency audit 3 and goal status (2026-10-04)

The third consecutive audit confirmed the unchanged protected direct_light implementation and unchanged relevant prompt/decision/callback contracts. No adopted producer or verified live owner job exists in the inspected evidence. The previous and current audit turns made no implementation progress. Independent authorized scalar/time/D9 and passive collector preparation is delivered; actual contribution extraction/export/parity cannot proceed without the protected owner interface. Evidence: build/p2_light_continuation_20261003_02/blocker_audit_3.json. The goal service returned status blocked (not complete). No tests or simulations were repeated. Resume after Claude/core owner delivers the adopted callback and actual transport validation described in CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md.

## User ownership override, 2026-10-04

The user revoked the Claude-only light calculation core restriction. Codex may now implement `tomato3d/light/` and relevant light tests under `tests/` directly, then connect and validate the existing tools collector/export path. The former requirement to wait for a separate core-owner delivery is superseded. The callback and angular export still require implementation; this notice is not completion evidence. See `CODEX_LIGHT_CORE_RULE_UPDATE_2026-10-04.md` and the replacement prompt `CODEX_P2_LIGHT_CHAT_PROMPT_2026-10-04.md`. Historical results and blocked-status records above are preserved.
