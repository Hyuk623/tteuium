# Coverage map — Micro-Tom fork spec + Stage-3 forecast spec against delivered V3 (2026-10-11)

Author: Claude Code. Written **before** any code of this work order, as Step 0 of
`handoff/CLAUDE_CODE_CLI_PROMPT_MICROTOM_FORK_FORECAST_IMPL_2026-10-11.md`.
Every "V3 evidence" cell below was checked by opening the cited file at the cited line/function on
2026-10-11; nothing is inferred from a report alone.

Status vocabulary: `done_in_V3` (nothing to build), `remainder` (built by this work order, in `tools/`),
`blocked_by_claim` (needs a change inside a Codex-claimed file; hook requested in LOG, built here against the
public interface or a fixture), `blocked_by_human_input` (no value/decision exists; stays `unavailable`).

Files read for this map: `CONVENTIONS.md`, `AGENTS.md`, `CLAUDE.md`, `handoff/LOG.md` (last 40 lines),
`handoff/CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md` (+ Addendum A),
`handoff/CODEX_FORECAST_SPEC_2026-10-10.md` (+ L1, owner reconciliation), `handoff/CODEX_FORECAST_SPEC_2026-10-10_KO.md`,
`handoff/VTC_WHOLE_PLANT_DEVELOPMENT_EXECUTION_V3_2026-10-11.md`, `handoff/VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3_2026-10-11.md`,
`handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md`, `handoff/CLAUDE_VTC_SCIENCE_PARAMETER_REVIEW_HANDOFF_2026-10-11.md`,
`handoff/MTG_CONVENTION_2026-10-10.md` (§6–8, §11 A1, §12 A2, §13), `handoff/CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md`,
`handoff/CLAUDE_P1_P2_P3_P4_END_TO_END_INTEGRATION_PROMPT_2026-10-11.md` (§7, §8, S2), `flow/flow_map.csv`,
`flow/check_flow.py`, `tools/vtc_development.py`, `tools/vtc_development_io.py`, `tools/vtc_development_native.rgg`,
`tools/vtc_development_observation.py`, `tools/vtc_growth_io.py`, `tools/vtc_growth_bridge.py` (run/prepare),
`tools/VTC_DEVELOPMENT.md`, `tools/compound_growth.py`, `tools/probabilistic_compound_growth.py` (gates only),
`data/records/env_light_20261010/*` (read-only), `build/vtc_dev_v3_delivery_sufficient/results/*` (verified 65-day, 4.8M-ray run).
Not on disk: `build/vtc_microtom_20261011/parametersMicroTom.rgg` as a *development* fork (the folder holds only the
V2 leaflet-subset template + RUN_GUIDE); no `light_validation.csv` with RMSE/r anywhere; no Stage-2 producer output;
no `tools/phyllotaxis_fit.py`.

Engine boundary facts used throughout (verified): V3 request `parameters` must equal the fixed key set
`vtc_development_io.PARAMS` (`vtc_development_io.py:19-20`, `load_package` "parameter registry incomplete or unknown
fields"); each entry = `{value, unit, source_kind, source_ref, cultivar, uncertainty}`; `source_kind` must be one of
`user_assumed | synthetic_assumed | literature_other_cultivar` (`load_package`, "coefficient cannot be promoted to
measured"). Therefore `unavailable` and `literature_wild_species` rows of this work order can **never** enter a request;
they are carried in the layer's own registry and manifest only.

---

## Part A — fork spec, Task 1 (determinate growth)

| # | Item | V3 evidence (file:function / output) | Status | What this work order does |
|---|---|---|---|---|
| 1.1 | New cultivar parameter file, every line annotated with provenance | `vtc_development.py::cultivar_module` writes `working/parametersMicroTom.rgg` with a JSON provenance comment per constant; `vtc_development.py::parameters` registry with `source_kind/source_ref/cultivar/uncertainty`; hash-bound (`prepared.json::parameter_hash`) | done_in_V3 | Supplies the Micro-Tom *values* through the request (`tools/microtom_parameters.py::build_request_overrides`); the module text itself stays V3's |
| 1.2 | Apex `stopped` state; trusses until `SP_STOP_RULE`; after stop no new phytomers, existing organs keep growing | `vtc_development_native.rgg::develop` (`apex.stopped=true`, event `determinate_stop` with rule `SP_STOP_RULE` when `count>1 && target==0`); `vtc_development_io.py::validate_outputs` "new organ after declared final stop"; delivery `events.csv` day 44 stops, mass rises to day 65 | done_in_V3 | Registry row `SP_STOP_RULE = two_successive_trusses` (the only value V3 accepts, `load_package` "unsupported stop rule") |
| 1.3 | `FINAL_VEG_PHYT_NUM` prior (first truss above leaf 9; 8/9) | `FIRST_LEAVES` = 9 in `vtc_development.py::parameters`; `develop` uses `FIRST_LEAVES` for the first axis; delivery: `Truss1` initiated day 32 under `I9` | done_in_V3 (value) / remainder (registry) | Registry row `FINAL_VEG_PHYT_NUM → FIRST_LEAVES`, candidates {8, 9} kept; sampled in the ensemble as a declared scenario set |
| 1.4 | Truss cadence parameterised (`TRUSS_INTERVAL`), Micro-Tom prior unknown | `CADENCE = [2,1,0]` (leaves between successive trusses, last must be 0: `load_package` "conditional stop cadence must end in zero") | done_in_V3 (mechanism) / blocked_by_human_input (value) | Registry row `TRUSS_INTERVAL → CADENCE` with `uncertainty = unavailable` (not sampled); fit from the 화방 sheet when it has rows |
| 1.5 | `MAX_LEN_INT` from calipers, never 0.072 m | `INTERNODE_CAP_M = 0.012` user_assumed in `parameters`; `updateGeometry` `len = INTERNODE_CAP_M*cbrt(mass/maxMass)` | blocked_by_human_input | Registry row `INTERNODE_CAP → unavailable`; engine default retained and recorded as `engine_default_retained` in every forecast manifest; one caliper exists (50.71 mm compound, not an internode) |
| 1.6 | No side shoots; `topology_scope = provided_axes` | `develop` creates one declared sympodial successor only (`sympodial_continuation`, `one_declared_successor`); request `source_plant_scope = main_and_declared_sympodial_axes` | done_in_V3 | Forecast outputs carry `topology_scope = provided_axes`, `completeness = unavailable` |
| 1.7 | `PHYLLOCHRON` 37.9 flagged other-cultivar; our thermal time 18.63 °Cd/day at T_base 5.7 | `PHYLLOCHRON_DD` 37.9 `literature_other_cultivar` Merlice; `BASE_C` 5.7 user_assumed; `validate_outputs` recomputes dd = (26·14+22·10)/24−5.7 = 18.633 | done_in_V3 | Registry rows `PHYLLOCHRON`, `T_BASE`; `make_climate_csv` test asserts 18.63 °Cd/day |
| 1.8 | Fork README: det-vs-indet source situation | `handoff/VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3` states the two-successive-truss rule is a conditional program | remainder (doc) | Stated in `tools/MICROTOM_FORECAST.md` and the execution report |

## Part B — fork spec, Task 1-2 + Addendum A (compound leaf structure)

| # | Item | V3 evidence | Status | What this work order does |
|---|---|---|---|---|
| 2.1 / A.1 | Rank-indexed leaflet-pair table, both candidates (Carvalho 1,1,2 vs dissected 3 pairs) | `PAIRS = [1,1,2]` "pairs_by_true_leaf_order_last_repeated"; `native.rgg::pairs(rank)`; acceptance scenario `three_pairs` = [1,1,3] verified (`build/vtc_dev_v3_acceptance_01/three_pairs`) | done_in_V3 | Registry row `NR_LEAFLET_PAIRS_BY_RANK → PAIRS`, candidates {[1,1,2],[1,1,3]}; sampled as a scenario set in the **seed route** only (an observation fixture fixes the inventory, see Part E) |
| 2.2 / A.2 | Per-segment bending `CURVE_RATIO = [r1,r2,r3]` (Chen 1:2:2) | `updateGeometry`: `alpha = TOTAL_BEND_DEG*(pair==1?1:2)/(2m-1)` — the 1:2:2 pattern is **hard-coded**, there is no ratio array in `PARAMS`; `BENT_FRACTION` absent | blocked_by_claim | Registry row `CURVE_RATIO` = [1,2,2] `literature_other_cultivar` (Chen2014), `engine_status = inactive_in_engine`; hook requested in LOG: `CURVE_RATIO double[]` in `PARAMS` + `updateGeometry`. `BENT_FRACTION` row value `unavailable` (share unmeasured), `inactive_in_engine` |
| 2.3 / A.3 | Middle pair largest — per-pair size ramp | `MIDDLE_RAMP = .35`; `native.rgg::pairWeight` | done_in_V3 | Registry row `MIDDLE_PAIR_RAMP → MIDDLE_RAMP`, candidates {0 (fork default: off until fitted), 0.35 (V3 hypothesis)} |
| 2.4 / A.4 | Intercalary + secondary leaflets: `AREA_CORRECTION` flag only, no geometry | Not present (contract §6: "no intercalary area multiplier") | blocked_by_claim (if ever activated) / remainder (flag) | Registry row `AREA_CORRECTION = 1.0` user_assumed, `inactive_in_engine`; never multiplied into any area in this layer |
| 2.5 | Insertion angle eq.(7), `LEAF_ANGLE/K_LEAF_ANGLE` to be fitted | V3 uses a fixed `COMPOUND_INSERTION_DEG = 80` (no length dependence) | blocked_by_human_input (fit) | Candidate row `CAND_INSERTION_ANGLE_CHEN7` registered inactive (Part F item 7); engine value stays 80 user_assumed |
| 2.6 | No shared rank for first two leaves | `true_leaf_order` increments per compound (`develop` `++leafOrders[p]`) | done_in_V3 | — |
| A.5 | Blades planar polygons v1; blade curl on hold | two-triangle diamond per leaflet (`vertices`), `leaflet_traits.csv` `outline_source = conditional_diamond`; no curl field | done_in_V3 | No curl field, no threshold anywhere in this layer |
| A.6 | Sarlikioti basal→terminal leaflet-angle gradient as prior shape | `BASAL_LEAFLET_ANGLE_DEG = 35`, `beta = side*BASAL*(m+1-pair)/m` (gradient to 0 at the terminal) | done_in_V3 | Registry row `LEAFLET_ANGLE_GRADIENT_BASAL → BASAL_LEAFLET_ANGLE_DEG`, 35 `literature_other_cultivar` (Sarlikioti2011 shape prior) |
| §13 | `area_basis = full_outline` | `leaflet_traits.csv` `area_basis = full_outline`; contract §6 | done_in_V3 | Forecast rows copy `area_basis = full_outline` |

## Part C — fork spec, Task 2 (start at sowing + 30 d)

| # | Item | V3 evidence | Status | What this work order does |
|---|---|---|---|---|
| 3.1 | Seed spin-up with our climate (26/22, 14/10 h) for 30 days, then continue | seed route executes all days 0..N in one process (`VTC_DEVELOPMENT.md`; delivery day 30 = 194 organs, 65 boundaries) | done_in_V3 | `DAYS_AT_START = 30` registry row (layer-only); forecast issue boundary = day 30 in the seed route; `days_after_sowing = DAYS_AT_START + horizon` in forecast rows |
| 3.1b | Daily climate CSV generator (`make_climate_csv.py`) | `vtc_development.py::demo` writes a fixed 26/22/14 h/400 ppm table only inside `demo`; no standalone generator | remainder | `tools/microtom_environment.py::make_climate_csv` (exact V3 header, `source_kind = user_stated`; RH in a sidecar because the V3 header has no RH column) |
| 3.2 | `DELAY` 206.3 °Cd stays flagged other-cultivar | `GERMINATION_DD` 206.3 `literature_other_cultivar` | done_in_V3 | Registry row `GERMINATION_DD` |
| 3.3 | Declared assumption in README + `run_assumptions` | request fields `seed_assumption`, `run_status`, `biological_validation` | done_in_V3 (engine) / remainder (forecast manifest) | `forecast_assumptions.csv` + manifest `declared_assumptions` (sowing+30 d interim, reference DLI, lamp placement) |
| 3.4 | Human: actual sowing dates (파종일 column) | none | blocked_by_human_input | Listed in the execution report; nothing substituted |

## Part D — fork spec, Task 3 (lamps + swappable measured distribution)

| # | Item | V3 evidence | Status | What this work order does |
|---|---|---|---|---|
| 4.1 | Indoor lamp scene instead of sun + sky | `lamps.csv` → `PointLight` per lamp (`vtc_development.py::prepare` `LAMPS`), no sun/sky in `native.rgg` | done_in_V3 (lamp scene) / blocked_by_human_input (placement, emission) | Lamp rows stay `synthetic_assumed_point_LED`; placement declared a guess in the manifest |
| 4.2a | `light_input.csv` (`reference_ppfd_umol_m2_s, source_kind, measured_at`), DLI = PPFD × 0.0504 | V3 reads the file (`TABLES['light_input.csv']`), allows `measured` only outside fixtures; **no DLI derivation anywhere** | remainder | `microtom_environment.py::load_light_input` derives DLI from PPFD × 3600 × photoperiod_h / 1e6 (= 0.0504·PPFD at 14 h), flags `conditional` unless `measured` |
| 4.2b | Pointer file `light_ratio_latest.txt` → slot-ratio CSV in `data/records`; header validation; abort loudly | `load_package` reads the pointer (one relative path), `vtc_growth_io.ratio_table` accepts grid **or** slot schema and raises `ContractError` otherwise; `prepare` freezes the target as `inputs/ratios_frozen.csv` + sha | done_in_V3 (freeze) / remainder (standalone resolver with hash record) | `microtom_environment.py::resolve_ratio_pointer` returns target path + sha256 + schema; test: re-targeting changes only the frozen file and its hash |
| 4.2c | Per-plant target = reference × `ratio_now`; ÷1.047 when the base is the 3 trays | `env_light_20261010.json::tray_area_base` = 1.047 (read-only record); V3 `light_ratio_role = comparison_only` (ratios never multiplied into traced light) | remainder (relative bookkeeping only) | `microtom_environment.py::slot_relative_targets` writes *relative* targets only; absolute µmol only when `light_input.csv` is `measured`; never applied to V3 photons |
| 4.3 | Validation: virtual sensors at the 16 grid centres, simulated ÷ 16-cell mean vs measured `ratio_to_mean`, RMSE + Pearson r | `native.rgg::simulate` writes `sensors.csv` (16 cells, empty-scene, `GRID_*` parameters); `vtc_development_observation.py::derived_tables` writes `light_validation.csv` with `simulated_ratio` and `phone_ratio` per cell but **no RMSE, no r**, and `phone_ratio` is `unavailable` for the slot schema | done_in_V3 (sensor hook exists) / remainder (metrics) | `microtom_environment.py::light_validation(sim_cells_csv, measured_cells_csv)` → RMSE + Pearson r on the hand-checked normalisation; sensor height stays a flagged parameter (`GRID_Z`) |
| 4.4 | Lamp placement = declared guess until comparison exists | as above | blocked_by_human_input | Manifest field `lamp_placement_status = declared_guess` |

## Part E — forecast spec §4–§12

| § | Item | V3 evidence / existing code | Status | What this work order does |
|---|---|---|---|---|
| §4 | Output folder `build/forecast_<YYYYMMDD>_<NN>/`, never overwritten | `vtc_growth_io.fresh_build` enforces fresh folders below `build/`; no forecast folder convention exists | remainder | `microtom_forecast_io.py::new_forecast_dir` (next free NN per date; write-once) |
| §4 | `manifest.json` with input sha256, config hash, code version, `forecast_published_at`, `input_snapshot_sha256`, `run_status`, `evaluation_status`, `topology_scope` | V3 `prepared.json`/`manifest.json` hash the engine inputs, not a forecast | remainder | `microtom_forecast_io.py::write_manifest` |
| §4 | `forecast_mtg.csv` (own `forecast_id` namespace, `rooted_at_vertex_id`, `horizon_day`, `status = generated_candidate`) | V3 `states.csv` organ ids (`p1/C0001`) are engine ids, not observation ids | remainder | `microtom_forecast.py::aggregate` → ids `F<run>-<organ-key>`; non-collision test against every observed `vertex_id` |
| §4 | `forecast_events.csv` (probability, interval, horizon) | V3 `events.csv` per member (initiation, funded_birth, emergence, axis_terminated, determinate_stop, sympodial_continuation) | remainder | member-fraction probability + timing quantiles; `organ loss` → `not_modelled` row in `unresolved.csv` |
| §4 | `forecast_intervals.csv` (point, low, high, nominal level) | none | remainder | ensemble median / min / max with `interval_kind = declared_scenario_envelope`, `calibrated = false` |
| §4 | `forecast_assumptions.csv` (every parameter: symbol, value, unit, source_kind, source_ref) | V3 `parameter_registry.json` per run | remainder | union of registry rows + V3 defaults retained + scenario values; zero-unsourced-defaults test joins every numeric cell to a row |
| §4 | `forecast_map.csv` append-only link forecast_id ↔ observed vertex_id | none | remainder | `microtom_forecast_eval.py::link_observation` (append-only, never renames) |
| §4 | `baselines/` from `tools/compound_growth.forecast()` | `compound_growth.py:296 forecast()` (public dispatcher), `:213 forecast_persistence`, `:221 forecast_recent_change`, `:183 validate_history` | remainder (wrapper) | `microtom_forecast_eval.py::run_baselines` calls the dispatcher only after the six §11 preconditions pass; else writes `baselines/preconditions.csv` and no values |
| §4 | `unresolved.csv` | none | remainder | every quantity not forecast + blocking reason |
| §5 | Estimability table: nothing writable as measurement; conditional trajectories allowed for area/length only when labelled | V3 outputs are `assumption_conditioned` | done_in_V3 (labels) / remainder (table) | continuous rows limited to leaflet area, internode length, compound dimensions; direction/curvature/unfolding/abscission → `unresolved.csv` |
| §6 | Direction in three mechanisms | V3: fixed `DIVERGENCE_DEG` 137.5, `COMPOUND_INSERTION_DEG` 80 (mechanism a, user_assumed); no (b), no (c) | done_in_V3 (a) / blocked_by_human_input (b,c) | `direction_mechanism` column: `fixed_generation` for engine orientations, `extrapolated_observed_change = unavailable` (no repeated observation), `tropism = not_modelled` |
| §7 | Closure contract: links 1–2 run, 3–5 do not exist in `tools/` track (a) | V3 **does** close carbon → allocation → growth → structure inside GroIMP (`native.rgg::simulate`: `o.alloc`, `o.mass += ...`, `updateGeometry`, `commitGeometry`; `validate_outputs` recomputes it) — this is L1's track (b), labelled conditional | done_in_V3 (track b) | Forecast manifest states `closure = native_conditional_v3`, `track = b`; CR-3 honoured (per-leaflet polygons, `surface_role = individual_leaflet_polygon`, never `compound_envelope`) |
| §8 | Side shoots excluded; horizon ceiling | V3: declared sympodial successor only; intervals 1..365 (`load_package`); probabilistic engine literal 30 (`probabilistic_compound_growth.py:796-797, 818`) untouched | done_in_V3 / remainder | horizons are boundary days inside the member run (`[1, 3, 7, 14]` default); the 30-day literal of the probabilistic engine is not touched (CR-1 stays with Codex/human) |
| §9 | Forecast identity: own namespace, rooted at observed vertex or parent axis, `generated_candidate`, append-only map | none | remainder | as §4 rows above; `rooted_at_vertex_id` = source organ id (continuation) or parent organ id (new organ) |
| §10 | Rolling-origin: compare only observations after issue time at the same photoperiod phase; exact-timestamp targets; frozen parameters; leakage | `compound_growth.evaluate_compound_forecasts` cut exists for its own history format | remainder | `microtom_forecast_eval.py::evaluate` + `leakage_check` (every input observation `observed_at ≤ issued_at`; deletion-equivalence test) |
| §11 | Six baseline preconditions | `compound_growth.py:124` board_mm gate, `:183-195` mm/arc-length, `:94` identity confirmed, `:221-233` recent_change diurnal reason, no interval output, `:346-355` exact timestamp | remainder (checks) / blocked_by_human_input (#1 frame, #2 scale) | `run_baselines` reports each precondition with file:function; with today's inputs all are `blocked` |
| §12 | Module list (`forecast_structure.py` etc.) and 12 software pass criteria | — | remainder, under the names this work order was given (`microtom_forecast*.py`) | criteria 1–12 → `tools/tests/test_microtom_forecast*.py`; §12 growth-accuracy criteria stay `not testable` |

## Part F — Amendment L1 candidate forms (register only)

| # | Candidate form | Reference location (verified) | Status | What this work order does |
|---|---|---|---|---|
| 7a | phyllochron + internode logistic (maxlen fitted, never from the paper) | `parametersMerlice.rgg:26 MAX_LEN_INT 0.072` (reference only); V3 uses a cube-root funded length with cap, not the logistic | remainder (registry row) | `CAND_INTERNODE_LOGISTIC`, `engine_status = candidate`, `value = unavailable`, maxlen `fit_required` |
| 7b | Chen eq.(7) insertion angle vs leaf length | original `modules_organs.rgg:355 calcAngle` (not ported to V3) | remainder (registry row) | `CAND_INSERTION_ANGLE_CHEN7`, reference 81.5°, 0.045 /cm recorded as `literature_other_cultivar` reference values, inactive |
| 7c | next-leaf azimuth = previous + b, Kanahama range as uncertainty width | MTG §12.5; `tools/phyllotaxis_fit.py` absent | remainder (registry row) | `CAND_AZIMUTH_SUCCESSION`, b `unavailable`, prior width 119.3–154.7° `literature_wild_species`, inactive |

## Hooks requested from V3 (LOG request lines; built here against the public interface)

| Hook | Exact field / function | Why |
|---|---|---|
| H1 | `vtc_development_io.PARAMS` + `vtc_development_native.rgg::updateGeometry`: `CURVE_RATIO` (`double[]`, per rachis segment, normalised) replacing the hard-coded `(pair==1?1:2)/(2m-1)` | fork Task 1-2.2 per-segment bending |
| H2 | `BENT_FRACTION` (`double`, share of base-bent compounds) + a per-compound bend-type draw in `native.rgg::compound` | fork Task 1-2.2 flat/bent split (value stays `unavailable` until measured) |
| H3 | `AREA_CORRECTION` as an *accounting* field in `derived_tables` (never in optical geometry) | fork Task 1-2.4 |
| H4 | `derived_tables` light_validation: add `ratio_rmse`, `pearson_r` and slot-schema support — **not required**: delivered here as `microtom_environment.light_validation` reading V3's `sensors.csv` | fork Task 3.3 |

No hook is needed for the 16-cell virtual sensors (`sensors.csv` exists), the frozen pointer (`prepare` freezes it), the
determinate stop, the rank table, the ramp, the spin-up, or `days_after_sowing` (`plant_metrics.csv`).
