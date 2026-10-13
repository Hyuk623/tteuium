# P3 review request: growth state, direction and calibration

Perform a read-only full-scope P3 code review. Read [common instructions](CODE_REVIEW_COMMON_2026-10-07.md). Use the frozen snapshot and `P3/scope.json`. Output only to `build/code_review_20261007_01/P3/`.

## Entry points and scope

`tools/compound_growth.py`, `probabilistic_compound_growth.py`, `monthly_growth.py`, `growth_simulator.py`, `growth_calibration.py`, `growth_observation_evidence.py`, `growth_observation_options.py`, `growth_day1.py`, adjacent JSON contracts, guides and browser assets. Follow real CLI/import/update/forecast/calibration callers, including older deterministic/scenario routes. Cross-read P1 observation producers, P2 `reference_dli_p3.py`, and P4 requirement/registry consumers.

## Priority counterexamples

1. Initial-state fidelity: starting from measured observations must not silently regenerate a different plant, reset IDs or treat a partial petiole as a complete compound axis. Independent scenarios must not mutate caller-owned state or each other.
2. Time and events: irregular intervals, equal/out-of-order timestamps, zero horizon, emergence, missing/removed organs, local day versus UTC and event ordering. Preserve real zero versus unavailable values.
3. Direction: degrees/radians, angle wrapping, signed directions, unit-vector normalization, rotations, undefined azimuth and distinction between whole-rachis direction and leaflet normal. No implicit phototropism equation absent a supported model.
4. Update/reanchor: per-trait eligibility, stable plant/organ/session identity, within-ring-only IDs, renamed aliases, duplicate source observations, cross-plant data, source-row reuse and stale evidence. Rejected observations must not corrupt unrelated traits or be relabelled as measurements.
5. Geometry/area/method comparability across time: old proxy area cannot become physical tissue growth; changed pose/calibration/partition/placement/phase needs the adopted mapping/evidence. Check state and metadata travel together through update/export/reload.
6. Uncertainty and calibration: supported covariance, units and positive definiteness; hard admissibility before likelihood; normalized weights, zero-weight/degenerate cases, sampling reproducibility. Keep plant/time splits and train-only preprocessing independent of validation. Do not fit real coefficients during review.
7. P3 light input is supported incident reference DLI for a declared complete local day. Absorbed/tissue or unsupported multi-day values must not enter through an alternative caller. Explicitly adopted nonfatal versus fatal policies must match the contract.
8. Scenario controls must not claim empirically fitted growth. Inspect UI/CLI parity, JSON/CSV round trips, defaults, unavailable reasons and deterministic replay. Verify that future geometry is not automatically certified for P2 optics.

## Contract references

- `handoff/CODEX_P3_GROWTH_PACK_V2_EXECUTION_2026-10-04.md`
- `handoff/CODEX_P3_AREA_REVIEW_EXECUTION_2026-10-05.md`
- `handoff/CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md`, especially D19/D21 and P3 items
- `tools/GROWTH_OBSERVATION_EVIDENCE.md`, `tools/PROBABILISTIC_COMPOUND_GROWTH.md`, `tools/MONTHLY_GROWTH.md`, other current adjacent guides
- Referenced accepted specification/decision documents in the frozen handoff tree. Resolve precedence explicitly.

## Validation entry points and handoff

Inspect `tools/tests/test_compound_growth.py`, `test_probabilistic_compound_growth.py`, `test_monthly_growth.py`, `test_growth_simulator.py`, `test_growth_calibration.py`, `test_p3_growth_decisions.py`, `test_p3_growth_science.py`, `test_p3_growth_pack_v2.py`, `test_p3_area_review.py`, and observation/day1/UI tests discovered through imports. Use hand-checkable fixed-seed fixtures and isolated CLI input/output. A passing fitter on training data is not an independent prediction validation.

Boundary report: P1 observation -> P3 state/update; P2 incident DLI -> P3 domain gate; P3 potential/realized growth quantities -> P4 requirements; P3 future geometry -> prospective P2 eligibility. Document actual direction/area/time units and missing adapters. The carbon/nutrient constrained growth loop remains deferred; audit representation/readiness without inventing or implementing it.
