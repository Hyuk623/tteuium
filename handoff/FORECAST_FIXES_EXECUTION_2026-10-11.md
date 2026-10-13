# Forecast layer fixes B1–B6 — execution report (2026-10-12)

Author: Claude Code (forecast session). Work order: `handoff/CLAUDE_CODE_CLI_PROMPT_FORECAST_FIXES_2026-10-11.md`.
Korean companion: `_KO.md`. Guide updated: `tools/MICROTOM_FORECAST.md` ("Fixes of 2026-10-11/12").
Scope kept: only `tools/microtom_*`, `tools/tests/test_microtom_*`, this report, `flow/flow_map.csv`, LOG. Codex-claimed
`vtc_development*`, `vtc_growth_bridge.py`, `tomato_fsp_*`, `fsp_extensions*` and the other session's `tomato3d/state`, `tomato3d/cli/run_p1.py`,
`tests/` were not edited. `config/`, `data/records/`, `docs/`, `Downloads/vtc-main` untouched. Earlier `build/forecast_20261011_01/_02` untouched
(hash-verified).

Files read: `CONVENTIONS.md`, `CLAUDE.md`, `handoff/LOG.md` (last 40 + all later lines), `MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md`,
`MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md`, `CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md`, `tools/TOMATO_FSP_PIPELINE.md`,
`VTC_V3_PENDING_DECISIONS_2026-10-11.md`, `MTG_CONVENTION_2026-10-10.md` (A1, A2, §13), `tools/tomato_fsp_pipeline.py` (prepare_run, commit_step,
collect, run, replay), `tools/tomato_fsp_io.py` (selected_package, make_native_inputs), `tools/tomato_fsp_acceptance.py::scenario_fixture`,
`tools/fsp_extensions.py::hook_settings`, `tools/tests/test_tomato_fsp_pipeline.py` (fixture gating), `build/fsp_integration_20261011_producer_run_02/*`
(scenario, checkpoint, state, collection), `build/p1_state_20261011_01` (package layout, captures, placement), `data/records/plant_registry/*.xlsx`
(sheet headers only, read-only). Not present: a sowing column in the plant registry (개체목록 has 이식일 only); Codex's final RESULT for the
eight-capability extension (hooks are advertised, engineering verification "in progress").

## Per item

| Item | Status | What was done / why blocked |
|---|---|---|
| **B1** route through the pipeline | **done** | `--engine pipeline` (route `p1_pipeline`): each member = `tomato_fsp_acceptance.scenario_fixture(P1, …)` → member `parameters` written into the scenario (the pipeline scenario schema already accepts a `parameters` block, so no hook request was needed) → `tomato_fsp_pipeline.prepare_run` → `run` (which commits the checkpoints). Results are read only from `native_inputs/initial_state.csv` and `committed/step_NNNN/{state.csv, development_events.csv, checkpoint.json}`; every committed file is re-hashed against `checkpoint.json`, `native_advance_count == 1` is asserted, `advance_interval` is never called (test monkeypatches it to raise). Manifest records `instance_ids`, per-member `checkpoints` (sha256 of each `checkpoint.json`), `state_advance_authority`, `engine_scope = multi_instance_canopy_placement`. `--engine v3_direct` kept for seed/fixture routes, labelled `single_plant_no_canopy` + `canopy_shading` unresolved row. Plant-level quantities are now computed from states for both engines (`height_top_leaf_axis_mm` names the axis-tip basis; MTG 12.6). |
| **B2** 4.8M default | **done** | `default_scenario` rays = 4,800,000, `issue_class = quantitative`; `validate_scenario` refuses fewer rays unless `issue_class = diagnostic` (`--rays N --diagnostic`); manifest `issue_class` + `engine_runtime.quantitative_light_sampling`. Seed route re-issued at 4.8M as `build/forecast_20261012_02` (section below). |
| **B3** ensemble that varies | **done** | `microtom_parameters.thermal_schedule` replicates V3's thermal initiation program (the rule `validate_outputs` already re-codes); `eligibility()` runs it per candidate on the real input state (seed counters / fixture apex counters from the source run / P1 `plant_initialization`) and marks a `candidate_set` row eligible only if some candidate changes the schedule or the pair count of a compound initiated within the horizon. Inert rows are named with reasons in `eligibility.json` and `manifest.ensemble.excluded_parameters`; rows without declared uncertainty (`TRUSS_INTERVAL`, `PHYLLOCHRON`, …) are reported `no_declared_uncertainty` and never drawn — no range invented. Nothing eligible → one member, `ensemble_spread = none`. |
| **B4** probability_basis | **done** | New `forecast_events.csv` column `probability_basis ∈ {rule_deterministic, scenario_fraction, unavailable}`: `rule_deterministic` when every member shares the governing parameters (SP_STOP_RULE, CADENCE, FIRST_LEAVES, PHYLLOCHRON_DD, GERMINATION_DD, BASE_C, EMERGENCE_DAYS; plus PAIRS for leaflet/rachis initiations). Nothing else renamed. |
| **B5** sowing input | **done** | `--sowing-datetime` (aware ISO) → `sowing_source = user_stated`; optional plant-registry column (`파종일` / `sowing_datetime`, read-only, preferring `plant_id`) → `plant_registry_user_record` per plant (absent today → not used); seed-route default unchanged but labelled `assumed_issue_minus_days_at_start`; otherwise `unavailable`. `days_after_sowing` follows and is `unavailable` for the pipeline/fixture routes without a sowing record. |
| **B6** activate H1–H3 when they exist | **done, deliberately gated** | `resolve_engine_capabilities` reads `vtc_development_io.PARAMS` at runtime (36 keys today; the three hook keys ARE advertised) and records the engine file hashes. Per Codex's LOG notice (2026-10-11: "do NOT auto-enable from PARAMS membership alone … defer until the owner RESULT"), activation needs: key present + value not `unavailable` + Codex's `fsp_extensions.hook_settings` contract satisfied + explicit `--enable-hooks`. Today: CURVE_RATIO → `inactive_hook_present_contract_unmet` (the contract wants an exact-count vector or `by_segment_count` for every PAIRS count; Chen's [1,2,2] is three segments and no truncation may be assumed — a human mapping is required); BENT_FRACTION → `inactive_hook_present_value_unavailable`; AREA_CORRECTION → `inactive_hook_present_activation_deferred` (would activate with `--enable-hooks`, accounting-only with `area_basis = summed_one_sided_full_outline_lamina_m2`, never optical geometry). Decisions, reasons and engine hashes are in `manifest.engine_capabilities`. |

Hook requests to V3/Codex via LOG: none new. H1–H3 now exist; what is missing for CURVE_RATIO is a human-declared `by_segment_count` mapping
(registry metadata), and for all three the owner's final RESULT before `--enable-hooks` is used on an issued forecast.

## Commands and exit codes

| Command | Exit | Result |
|---|---|---|
| `python -X utf8 -m tools.microtom_parameters capabilities` / `--enable-hooks` | 0 / 0 | decisions above; with `--enable-hooks` AREA_CORRECTION → `activated_by_capability_check`, the other two unchanged |
| `… microtom_forecast scenario --engine pipeline --p1 build/p1_state_20261011_01 --members 4 --horizons 1 2 3` | 0 | `issue_class = quantitative`, 4.8M rays |
| `… microtom_forecast issue --scenario scenario_p1_pipeline.json --date 20261012` (first attempt) | 1 | `build/forecast_20261012_01`: **FAILED** at member m01 with V3 `unresolved native token` — Codex was saving `vtc_development*` (mtime 15:46–15:49) while the member prepared; the folder holds `FAILED.json` and no manifest, so it is not a forecast. Left in place as evidence of the fail-closed rule. |
| `… microtom_forecast issue --scenario scenario_seed_route_4p8M.json --date 20261012` | 0 | **`build/forecast_20261012_02`** (seed route, 4.8M, quantitative), 3 min 27 s |
| `… microtom_forecast issue --scenario scenario_p1_pipeline.json --date 20261012` (retry after the edit window) | 0 | **`build/forecast_20261012_03`** (pipeline route, 4.8M, quantitative), 14 min 49 s wall (the P1 freeze + `prepare_run` dominate; native 71.0 / 26.8 / 41.3 / 49.7 s for 3 intervals) |
| `pytest tools/tests/test_microtom_*.py -q` (5 files) | 0 | **43 passed**: 42 in 142 s plus the pipeline-route test, which first failed on the same transient `unresolved native token` and passed on rerun (167 s) |
| `pytest tools/tests -q` (full) | 0 | **1746 passed, 1 skipped** (950.8 s); Codex's concurrent extension tests are included in the count, no existing test changed status |
| `python -X utf8 flow/check_flow.py --md` | 0 | all mapped paths present |

## Issued forecasts (both `assumption_conditioned` / `evaluated_unaccepted`, 4.8M rays, `quantitative_light_sampling = true`)

| | `forecast_20261012_02` — seed route, v3_direct | `forecast_20261012_03` — P1 pipeline route |
|---|---|---|
| Input | frozen seed inputs; `start_time` 2026-09-12 06:00 (+09:00) = issue day − 30 d; `sowing_source = assumed_issue_minus_days_at_start` | `build/p1_state_20261011_01`, `state_source = fixture_truth` (four placed instances fx_om0, fx_om0#2, fx_om1, fx_sp0; synthetic fixture, not a photo reconstruction); `start_time` = capture time from the package; `sowing_source = unavailable` |
| Eligibility | FINAL_VEG_PHYT_NUM, NR_LEAFLET_PAIRS_BY_RANK, MIDDLE_PAIR_RAMP eligible; 6 active rows excluded `no_declared_uncertainty` | NR_LEAFLET_PAIRS_BY_RANK and MIDDLE_PAIR_RAMP eligible; FINAL_VEG_PHYT_NUM excluded as `inert on this input state within the horizon` (7 leaves + 3 days: leaf 8 is initiated under either candidate); 6 rows `no_declared_uncertainty` |
| Members | 4: (8,[1,1,3],0.35) (9,[1,1,3],0) (9,[1,1,2],0) (9,[1,1,2],0.35); native 31.7 / 35.0 / 53.5 / 50.5 s (44 intervals each) | 4: ([1,1,2],0.35) ([1,1,3],0.35) ([1,1,3],0) ([1,1,3],0); each member a full pipeline run with 3 committed checkpoints |
| Spread | `present`: 2,298 of 3,006 interval rows differ | `present`: 110 of 2,385 interval rows differ — only the newly initiated compound's leaflets/rachis (pair count, ramp); instance totals identical across members |
| probability_basis | every event `scenario_fraction` — FIRST_LEAVES (a governing parameter) differs between members, so no event is rule-deterministic in this set | `apex_stop`, `new_truss`, `new_compound`, `new_internode` → `rule_deterministic` (FIRST_LEAVES, cadence, phyllochron shared); `organ_initiation:Leaflet/RachisSegment` → `scenario_fraction` (PAIRS differs) |
| p1 / instance totals at the last horizon | day 44: compounds 12 [11, 12], trusses 4, stem 121.0 [113.2, 123.1] mm, mass 1.272 [1.206, 1.329] gDM | fx_om0 at +3 d: compounds 7 (6 imported + 1 initiated at +2 d, `new_compound` p = 1.0 by +2 d), trusses 0, stem 78.6 mm, mass 0.895 gDM, identical across members; `days_after_sowing = unavailable` |
| Checkpoints | — (v3_direct) | per member 3 sha256 of `checkpoint.json` (e.g. m00 96981fc4…, c27b6661…, 4961d265…), `native_advance_count = 1` each, recorded in `manifest.checkpoints` and `members.csv` |

The B4 column shows an honest consequence of B3: once FIRST_LEAVES is varied, apex-stop timing is a scenario fraction, not a shared rule.
A set that holds FIRST_LEAVES fixed (e.g. the earlier `forecast_20261011_02` members 1–3) yields `rule_deterministic` for the stop.

## Growth-accuracy status

Unchanged: **not testable**. No repeated observations of identified plants, no lights-on clock time, no PPFD meter reading, no sowing record.
Nothing here is a validated Micro-Tom prediction; the pipeline route's input is a synthetic P1 fixture read through the truth table.

## Observations for the owners

- The three hook keys are advertised but `vtc_development.parameters()` does not carry them; the layer adds an activated optional key to the
  request only when `--enable-hooks` is given and the contract passes. No forecast was issued with hooks enabled.
- Concurrent edits to `vtc_development*` by Codex (15:46–15:49) produced a transient `unresolved native token` in two of my runs; both are
  recorded as failures (`FAILED.json`, test rerun), nothing was relabelled.
- The P1 fixture plants (7 leaves, 490.55 °Cd) initiate one compound within a 3-day horizon under either FIRST_LEAVES candidate, so that prior
  is inert there; the dissected three-pair candidate and the ramp are what vary.
