# Micro-Tom fork remainder + Stage-3 forecast layer — execution report (2026-10-11)

Author: Claude Code. Work order: `handoff/CLAUDE_CODE_CLI_PROMPT_MICROTOM_FORK_FORECAST_IMPL_2026-10-11.md`
(assigned by Amendment S2 of the integration prompt). Korean companion: `_KO.md`.
Coverage map written first: `handoff/MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md`. Guide: `tools/MICROTOM_FORECAST.md`.

**Status in one line.** Software implementation complete and tested; two conditional forecasts issued natively through V3;
biological validation **not established**; growth accuracy **not testable** until ≥ 3 capture dates of the same identified plants exist.
Nothing here is validated Micro-Tom growth.

## 1. Files read / missing

Read (all opened, not summarised from reports): `CONVENTIONS.md`, `AGENTS.md`, `CLAUDE.md`, `handoff/LOG.md` (last 40 lines + later Codex
lines), both specs with Addendum A / Amendment L1 / owner reconciliation, `CODEX_FORECAST_SPEC_2026-10-10_KO.md`,
`VTC_WHOLE_PLANT_DEVELOPMENT_EXECUTION_V3`, `VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3`, `VTC_V3_PENDING_DECISIONS`,
`CLAUDE_VTC_SCIENCE_PARAMETER_REVIEW_HANDOFF`, `MTG_CONVENTION` (§6–8, §11 A1, §12 A2, §13), `CLI_PROMPT_LITERATURE_P1P4`,
`CLAUDE_P1_P2_P3_P4_END_TO_END_INTEGRATION_PROMPT` (§7, §8, S1, S2), `flow/flow_map.csv`, `flow/check_flow.py`, `tools/VTC_DEVELOPMENT.md`,
`tools/vtc_development.py`, `tools/vtc_development_io.py`, `tools/vtc_development_native.rgg`, `tools/vtc_development_observation.py`,
`tools/vtc_growth_io.py`, `tools/vtc_growth_bridge.py` (prepare/run), `tools/compound_growth.py`, `tools/probabilistic_compound_growth.py`
(gates at lines 792–797, 818), `tools/tests/test_vtc_development.py`, `tools/tests/test_compound_growth.py`,
`data/records/env_light_20261010/*` (read-only), `build/vtc_dev_v3_delivery_sufficient/results/*`, `build/vtc_dev_v3_acceptance_01/*`.

Missing / not on disk: a development-level Micro-Tom fork under `build/vtc_microtom_20261011/` (the folder holds the V2 leaflet-subset
template and a RUN_GUIDE only; V3 lives in `tools/vtc_development*`); any `light_validation.csv` with RMSE/r; a Stage-2 producer output
(phynotype2 absent); `tools/phyllotaxis_fit.py`; any Micro-Tom paper PDF in the repo (literature values are cited from the prompts, flagged).

## 2. What V3 already did vs what was built here

Coverage map verdicts (see the map for file:function evidence): **done_in_V3** — determinate stop after two successive trusses, first 9
leaves, parameterised truss cadence, rank-indexed leaflet pairs, middle-pair ramp, planar full-outline leaflets, basal→terminal leaflet-angle
gradient, 30→65-day seed spin-up, lamp scene, frozen ratio pointer, 16-cell virtual sensors, provenance-stamped parameter module, per-leaflet
surfaces (CR-3). **Remainder built here** — Micro-Tom registry + request mapping, standalone climate generator (`user_stated`), DLI
derivation, pointer resolver with hash record, 16-cell RMSE/Pearson validation, the whole Stage-3 layer (ensemble, forecast namespace,
write-once folders, assumptions/unresolved tables, append-only correspondence, rolling-origin evaluation, baseline preconditions, candidate
forms). **blocked_by_claim** — `CURVE_RATIO`, `BENT_FRACTION`, `AREA_CORRECTION` (no V3 field; hooks H1–H3 below).
**blocked_by_human_input** — internode cap (no caliper), truss cadence value, sowing dates, lights-on clock time, bent-type share, absolute PPFD.

New files (all claimed in LOG before creation): `tools/microtom_parameters.py`, `tools/microtom_parameters.csv`, `tools/microtom_environment.py`,
`tools/microtom_forecast.py`, `tools/microtom_forecast_io.py`, `tools/microtom_forecast_eval.py`, `tools/MICROTOM_FORECAST.md`,
`tools/tests/test_microtom_parameters.py`, `test_microtom_environment.py`, `test_microtom_forecast.py`, `test_microtom_forecast_eval.py`,
`handoff/MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md`, this report + `_KO`, `build/forecast_scenarios_20261011/*.json`,
`build/forecast_20261011_01/`, `build/forecast_20261011_02/`. Edited: `flow/flow_map.csv` (2 rows updated, 6 added), `handoff/LOG.md` (append).
**Not edited:** any `vtc_development*`, `vtc_growth_bridge.py`, `tomato_fsp_*`, `config/`, `data/records/`, `docs/`, `Downloads/vtc-main`.

## 3. Commands executed and exit codes

| Command | Exit | Result |
|---|---|---|
| `python -X utf8 -m tools.microtom_parameters validate` | 0 | 22 rows: 9 active, 3 inactive_in_engine, 1 engine_default_retained, 1 layer_only, 5 environment, 3 candidate; 3 sampled rows |
| `python -X utf8 -m tools.microtom_environment climate --out … --start 2026-10-11T06:00:00+09:00 --days 3 --t-base-c 5.7` | 0 | thermal time 18.633 °Cd/day, DLI factor 0.0504 |
| `python -X utf8 -m tools.microtom_environment light-input --path …` | 0 | 300 µmol → DLI 15.12 mol m⁻² d⁻¹, `conditional = true` |
| `python -X utf8 -m tools.microtom_environment pointer --pointer build/vtc_microtom_20261011/light_ratio_latest.txt` | 0 | slot schema, 25 rows, sha256 `7a86e150…2838` |
| `python -X utf8 -m tools.microtom_environment validate-light --sim build/vtc_dev_v3_delivery_sufficient/results/sensors.csv --measured data/records/env_light_20261010/light_ratio_map_20261010.csv --out …` | 0 | ratio RMSE 0.1175, Pearson r 0.402, 16 cells — shape check of the hypothetical point lamp against the phone map; no calibration implied |
| `python -X utf8 -m tools.microtom_forecast issue --scenario … --from-results build/vtc_dev_v3_acceptance_01/{sufficient,three_pairs}` (smoke) | 0 | deterministic aggregation path (no Java) |
| `… issue --scenario scenario_stage2_fixture.json --date 20261011` | 0 | **`build/forecast_20261011_01`**, 4 native members, 3 min 09 s wall |
| `… issue --scenario scenario_seed_route.json --date 20261011` | 0 | **`build/forecast_20261011_02`**, 4 native members, 1 min 54 s wall |
| first native smoke at `--rays 1000` (both routes) | 1 | V3 rejected every member: `unfunded obligations; carbon deficit` (too few rays → starving plants); re-run at 300k rays passed. `FAILED.json` marker + no manifest now mark such folders |
| `python -X utf8 -m pytest tools/tests/test_microtom_*.py -q` | 0 | **33 passed** (86.7 s, includes one native fixture-route issue) |
| `python -X utf8 -m pytest tools/tests -q` (baseline before this work) | 0 | **1675 passed, 1 skipped** (624.8 s); the one skip is the optional openalea.lpy |
| `python -X utf8 -m pytest tests -q` (tomato3d, untouched) | 0 | **331 passed, 1 skipped** (176.6 s) |
| `python -X utf8 flow/check_flow.py --md` | 0 | all mapped paths present after this report was written |

Full `tools/tests` after the new tests were added: **1736 passed, 1 skipped** (731.6 s). The count exceeds baseline + 33 because Codex's `tools/tests/test_tomato_fsp_pipeline.py` and another session's P1 tests landed in the same window; no existing test changed status.

## 4. The two issued forecasts (conditional; `run_status = assumption_conditioned`, `evaluation_status = evaluated_unaccepted`)

Common: registry sha `ab39e01d…ce9e`, GroIMP 2.2.1 / OpenJDK 21.0.12.1, 300,000 rays per member (`quantitative_light_sampling = false`;
4.8M needed for a quantitative light claim), climate 26/22 °C 14 h `user_stated`, CO₂ 400 ppm `user_assumed` (inactive in V3 physiology),
reference PPFD 300 `user_assumed` → DLI 15.12 (conditional), slot-ratio pointer frozen to `data/records/env_light_20261010/plant_slot_light_ratio_20261010.csv`
(comparison only), lamp `synthetic_assumed_point_LED` at 0.6 m (`lamp_placement_status = declared_guess`), horizons 1/3/7/14 days,
ensemble = 4 members drawn (seed 11) from the registry's declared candidate sets — a **scenario set, not a calibrated probability**.
Baselines: `blocked_by_preconditions` P1 (frame), P2 (mm scale), P3 (identity), P4 (diurnal), P6 (exact timestamps); P5 reported as a
structural limitation. `topology_scope = provided_axes`, `completeness = unavailable`, tropism `not_modelled`.

| | `forecast_20261011_01` (Stage-2 **fixture** route) | `forecast_20261011_02` (**seed** route) |
|---|---|---|
| Input snapshot | exact-column Stage-2 fixture from the verified day-30 state of `build/vtc_dev_v3_delivery_sufficient` (not a real producer), sha `e840f074…` | frozen seed inputs, declared sowing 2026-09-11 06:00 (+09:00) so boundary day 30 = issue day, sha `aad9cd1b…` |
| Members (FIRST_LEAVES / PAIRS / MIDDLE_RAMP) | 8/—/0.35, 9/—/0.35, 9/—/0, 9/—/0 (PAIRS fixed to the imported inventory [1,1,2]) | 8/[1,1,3]/0.35, 9/[1,1,3]/0, 9/[1,1,2]/0, 9/[1,1,2]/0.35 |
| Rows | mtg 3,864 · intervals 2,474 · events 222 · assumptions 59 · unresolved 16 | mtg 4,204 · intervals 3,006 · events 350 · assumptions 59 · unresolved 16 |
| Ensemble spread | **degenerate: 0 of 2,474 interval rows differ across members.** FIRST_LEAVES no longer acts once 9 leaves exist, and MIDDLE_RAMP is inert for two-pair compounds (`pairWeight` = 1 for both pairs). Reported, not hidden; the manifest of later issues carries `ensemble_spread` | 2,298 of 3,006 rows differ (leaflet area/length/width, rachis segments, internodes, plant totals) |
| p1 at +14 d (day 44) | compounds 12, trusses 4, stem 118.9 mm, structural mass 1.214 gDM (identical in all members) | compounds 12 [11, 12], trusses 4, stem 113.6 [106.9, 115.5] mm, mass 1.078 [1.033, 1.122] gDM |
| p1 events | new truss by +3 d (p = 1.0, first at +2 d); apex stop by +14 d (p = 1.0, at +14 d) | new truss by +3 d p = 0.75 (first at +2 d); new compound by +3 d p = 0.25; apex stop by +14 d p = 1.0, timing 12–14 d |
| Photoperiod phase | `unavailable` (lights-on clock time null in the records) → every future comparison is `unavailable_diurnal_confound` until CR-6 is answered | same |

Per-member native runs: fixture 84.4 / 27.2 / 24.6 / 33.2 s (14 intervals), seed 42.9 / 18.0 / 15.6 / 18.2 s (44 intervals); all `verified`
by V3's own `validate_outputs`. The first member of each run includes JVM warm-up.

## 5. Hooks requested from V3 (Codex-claimed files; requested in LOG, not implemented)

| Hook | Exact field / function | Status in this layer |
|---|---|---|
| H1 | `vtc_development_io.PARAMS` + `vtc_development_native.rgg::updateGeometry`: `CURVE_RATIO double[]` per rachis segment, normalised, replacing the hard-coded `(pair==1?1:2)/(2m-1)` | registry row `CURVE_RATIO = [1,2,2]` (Chen2014, other cultivar), `inactive_in_engine` |
| H2 | `BENT_FRACTION double` + per-compound bend-type draw in `native.rgg::compound` | registry value `unavailable` (share unmeasured), `inactive_in_engine` |
| H3 | `AREA_CORRECTION` as an accounting-only field in `vtc_development_observation.derived_tables` (never optical geometry) | registry 1.0 flagged, `inactive_in_engine`, never multiplied into any area |
| — | 16-cell virtual sensors, frozen pointer, determinate stop, rank table, ramp, spin-up, `days_after_sowing`: **no hook needed** (exist in V3) | consumed |
| note | Codex's staged-integration hooks (`tomato_fsp_pipeline.prepare_run/run/collect/compare_observation`, LOG 2026-10-11) define a future P1 route; this layer does not call them and never calls `advance_interval` (no second growth update) | follow-up when P1 is delivered |

## 6. Inactive / retained / unavailable parameters (every forecast manifest lists them)

`inactive_in_engine`: CURVE_RATIO, BENT_FRACTION, AREA_CORRECTION. `engine_default_retained`: INTERNODE_CAP → V3 keeps its 0.012 m
`user_assumed` hypothesis (registry value `unavailable`; never Merlice 72 mm). `v3_default_retained` (27 V3 parameters outside the registry,
e.g. AMAX/ALPHA/THETA Merlice NRH, SLA, organ sink curves) are copied into `forecast_assumptions.csv` with V3's own provenance.
Candidates registered inactive: CAND_INTERNODE_LOGISTIC (maxlen fit required), CAND_INSERTION_ANGLE_CHEN7, CAND_AZIMUTH_SUCCESSION
(Kanahama width, `literature_wild_species`). `TRUSS_INTERVAL` is active but not sampled (no truss record exists to declare a spread).

## 7. Software pass criteria (spec §12) — all tested

| # | Criterion | Test |
|---|---|---|
| 1 | Reproducibility | `test_reproducibility_same_inputs_same_files`: two issues from the same verified results are byte-identical except `issued_at`; native issues agree to 10 significant digits (GroIMP summation jitter ~1e-17 documented) |
| 2 | ID non-collision | `test_forecast_ids_never_collide…`: all ids `F:<run>:…`, disjoint from every engine organ id and rooted vertex id |
| 3 | Previous forecasts preserved | `test_previous_forecasts_preserved_and_write_once` (+ tamper detection, double-finalize refused) |
| 4 | Zero future leakage | `test_leakage_detected_and_deletion_equivalence`: later `input` observations abort evaluation; pre-issue inputs change nothing |
| 5 | Zero un-sourced defaults | `test_zero_unsourced_defaults`: every engine parameter of every member maps to an assumption row with `source_kind` + `source_ref`; no `measured` |
| 6 | No physical units without scale | seed/fixture routes are labelled; baselines blocked on P2; MTG values are model-generated `generated_candidate` (never `measured`) |
| 7 | Candidate segregation | forecast rows live only under `build/forecast_*`; `forecast_map.csv` empty at issue |
| 8 | Scope honesty | `test_status_labels_and_scope`: `provided_axes`, `completeness = unavailable` |
| 9 | Preconditions surface | `test_preconditions_blocked_today…`: six preconditions with `file::function`; baseline runs only on an admissible synthetic board-frame history |
| 10 | Status labels | `accepted_for_domain` asserted absent in every CSV/JSON |
| 11 | No compound envelope | `test_no_compound_envelope_and_full_outline` |
| 12 | Read-only inputs | registry/records are read; `config/`, `data/records/`, `docs/` untouched (no write path exists in the code) |
| + | Pointer re-target | `test_pointer_retarget_changes_only_frozen_ratio_and_hash`: only `resolved_ratio_target` (and the pointer text) differ |
| + | Light validation math | `test_light_validation_hand_computed`: RMSE 0.1 / r unavailable (constant), 0 / 1 (proportional), 0.2 / −1 (anti), tray-base factor |
| + | Climate thermal time | `test_climate_csv_matches_v3_header_and_thermal_time`: 18.63 °Cd/day at T_base 5.7, V3 header, V3 `load_package` accepts it |

## 8. Growth-accuracy status

**`not testable`.** Zero repeated per-organ observations of identified plants, zero truss observations, no lights-on clock time, no absolute
PPFD. The evaluation harness exists and is exercised on synthetic truth only (`growth_accuracy_status = software_check_only_synthetic_truth`).
It becomes meaningful when ≥ 3 capture dates of the same identified plants exist with `time_since_lights_on_min`, through
`forecast_map.csv` links produced by the Stage-2/phynotype2 review — never by renaming ids.

## 9. Assumptions made and spec gaps found

- Seed-route default sowing time = issue day − 30 d at 06:00 (+09:00) so the forecast origin is today; real sowing dates remain unrecorded
  (파종일 column request stands). The forecast spec's `start_time` otherwise had no definition for this route.
- `source_kind = user_stated` (MTG A1.2) is used for set-points; the work order's five-value vocabulary has no label for "declared set-point".
- The fixture route excludes PAIRS from sampling: V3's `validate_outputs` checks every compound's inventory against the member's PAIRS,
  so a 3-pair member would be rejected on a 2-pair imported plant. The spec did not anticipate this.
- The forecast's `source_kind` for simulated values is `user_assumed` (conditional on user_assumed/other-cultivar parameters); the spec gives
  no label for "model output".
- Evaluation against **independent** observations requires the issue boundary to lie in the past; synthetic-truth sets may run on the scenario clock (the
  from-results path has a synthetic clock). Both are reported in `leakage`.
- The fixture ensemble was degenerate (section 4); a `MIDDLE_RAMP` candidate set only matters for ≥ 3-pair compounds. The dissected-leaf candidate
  `[1,1,3]` is the one that creates spread.
- `GRID_Z` (sensor height) stays a V3 parameter flagged unrecorded; `light_validation` reports `sensor_height_status = parameter_unrecorded`.

## 10. Human inputs still required (unchanged list, nothing substituted)

Sowing dates per plant; lights-on clock time (CR-6); PPFD meter reading for `light_input.csv`; internode calipers (cap); truss sheet rows
(cadence, FINAL_VEG_PHYT_NUM); C3/leaflet sheet (pairs by rank, pair sizes); bend-type share; `plant_id` for the 18 slots; frame gate decision (CR-2);
`manual_events.csv` / `organ_label_map.csv` or abscission out of scope (CR-5); VTC license (local use only meanwhile).
