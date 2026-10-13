# P4 review request: carbon physiology and nutrient accounting

Perform a read-only full-scope P4 code review. Read [common instructions](CODE_REVIEW_COMMON_2026-10-07.md). Use the frozen snapshot and `P4/scope.json`. Output only to `build/code_review_20261007_01/P4/`. Include the October 6 nutrient module; do not limit review to the older carbon implementation.

## Entry points and scope

- `tools/fsp_carbon_diagnostic.py`, `fsp_carbon_diagnostic_schema.json`, demo and guides; source/equation evidence registry references.
- `tools/nutrient_contract.py`, `nutrient_composition.py`, `nutrient_balance.py`, `nutrient_fsp_bridge.py`, `fsp_nutrients.py`, `fsp_nutrients_demo.py`, `FSP_NUTRIENTS.md`.
- `tomato3d/rules/` and any P4-routed rule/knowledge consumers; identify whether active or disconnected legacy paths.
- P2 absorbed light/face/area producers and P3 growth requirements/state are read-only dependencies. Follow actual public API/CLI calls and serialization, not only scientific helper functions.

## Priority counterexamples

1. Source applicability, PPFD/absorbed-light basis, coefficient metadata and adopted nonfatal basis-conflict policy. No second absorptance multiplication, unsupported face conversion or doubled one-sided area.
2. Photosynthesis/respiration/maintenance: instantaneous rate versus interval amount, day/night integration, before_mito/net_leaf treatment, required Rd evidence, temperature reference/Q10 domain and no double subtraction.
3. Carbon versus carbohydrate versus structural/total dry mass; keep conversion factors and SLA/RGR5 conventions attached to the correct quantities. Hand-calculate zero-light, zero-growth and interval-length cases. Negative balance need not imply an invalid model, but resource accounting must remain explicit.
4. Source/sink/reserve/tissue partition identity: count each organ and plant once; reject overlapping/reused intervals and incompatible endpoints. Check non-mutating diagnostics, reserve lineage and partial-unavailable behavior. Missing pool/evidence is not zero.
5. Nutrient labels: mass percent versus g/L, mass/volume dose with density, final solution volume, P2O5/K2O elemental conversion, total N versus its forms, raw-water contribution and complete tracked-species coverage.
6. Two-layer water/element ledger: dissolved/retained pools, well-mixed transfer order, capacity versus geometric volume, finite irrigation batches, evaporation/transpiration/uptake, drainage/discard/reuse and internal plant allocation. Detect overdraw, duplicate events, chronology/context errors and successful partial results after an invalid late event.
7. Optional bridge: disabled mode preserves existing P4 output; enabled accounting never silently applies growth constraints or spends carbon twice. Prescribed uptake inputs are not a predictive uptake law. EC/pH cannot substitute for measured element pools.
8. CLI/templates/comparisons/export: enforce exact plant/scenario/time units, missing-input reasons, model-validation flags, hash provenance, output path rules and input immutability. Ensure failure statuses reach the caller/UI.

## Contract references

- `handoff/CODEX_P4_GROWTH_PACK_V2_EXECUTION_2026-10-04.md`
- `handoff/CODEX_P4_AREA_REVIEW_EXECUTION_2026-10-05.md`
- `handoff/CODEX_FSP_NUTRIENTS_EXECUTION_2026-10-06.md`
- `handoff/CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_REQUEST_2026-10-06.md`
- `handoff/CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md`, adopted D15-D20 and current tool/schema guides.

The registry's saved source snapshot is not necessarily identical to later runtime files; verify hashes and applicability. Historical source interpretation does not establish dwarf-cultivar empirical accuracy. Science choices that remain unspecified go to Claude with a precise missing contract, not a guessed coefficient.

## Validation entry points and handoff

Inspect and run isolated relevant cases from `tools/tests/test_fsp_carbon_diagnostic.py`, `test_fsp_growth_science.py`, `test_fsp_growth_pack_v2.py`, `test_fsp_area_review.py`, `test_fsp_nutrients.py`, and rule/schema tests. Reproduce conservation with independent arithmetic, including multi-event and failure sequences; do not just assert the implementation's own summary is zero. Inspect examples before invoking CLI demos to avoid overwriting existing evidence.

Boundary report: P2 absorbed tissue light -> P4; P3 growth/area interval -> P4; nutrient ledger -> P4 binding; proposed P4 growth constraints -> P3. Explicitly identify the last boundary as unimplemented if that remains the case. Distinguish implemented accounting, incomplete biological processes and actual bugs in the available computations.
