# Micro-Tom parameter set, environment flow and Stage-3 forecast layer (on top of V3)

Owner: Claude Code (2026-10-11). Specs: `handoff/CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md` (fork remainder)
and `handoff/CODEX_FORECAST_SPEC_2026-10-10.md` (Stage 3). Coverage map: `handoff/MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md`.

Nothing in these modules changes biological state. The simulator is delivered V3 (`tools/vtc_development*`,
Codex-claimed, consumed only through `vtc_development.demo/prepare/collect`, `vtc_growth_bridge.run`,
`vtc_development_observation.fixture_from_native`, the request JSON and the result CSVs). Every run is
`run_status = assumption_conditioned`, `evaluation_status = evaluated_unaccepted`; `accepted_for_domain` never appears.

## Modules

| Module | Purpose |
|---|---|
| `tools/microtom_parameters.csv` | Registry of Micro-Tom priors: `key, value, unit, source_kind, source_ref, cultivar, uncertainty, uncertainty_kind, candidates, engine_key, engine_status, note`. No row is `measured`. |
| `tools/microtom_parameters.py` | `load_registry`, `build_request_overrides`, `apply_overrides`, `sample_member` (seeded draw over `candidate_set` rows), CLI `validate` / `overrides`. |
| `tools/microtom_environment.py` | `make_climate_csv` (V3 header, `user_stated` set-points, RH in `climate_setpoints.json`), `load_light_input` (DLI = PPFD × 3600 × photoperiod_h / 1e6), `resolve_ratio_pointer`, `slot_relative_targets`, `light_validation` (16 cells, ratio RMSE + Pearson r). |
| `tools/microtom_forecast_io.py` | Write-once `build/forecast_<YYYYMMDD>_<NN>/`, `F:<run>:<organ>` id namespace, table schemas, `finalize` / `verify_forecast` hashes. |
| `tools/microtom_forecast.py` | Scenario → ensemble members → V3 runs → `forecast_*.csv` + `manifest.json`. CLI `scenario` / `issue`. |
| `tools/microtom_forecast_eval.py` | Six §11 baseline preconditions (`run_baselines` → `tools.compound_growth.forecast` only), `link_observation` (append-only), `leakage_check`, rolling-origin `evaluate`. |

`engine_status` vocabulary: `active` (maps to a V3 `parameters` key), `inactive_in_engine` (V3 has no field; hook requested in LOG;
recorded in every manifest), `engine_default_retained` (registry says `unavailable`, V3 keeps its own hypothesis),
`layer_only` (`DAYS_AT_START`), `environment` (climate set-points → `environment.csv`), `candidate` (Amendment L1 forms, never active).

Mapping at the engine boundary (verified against `vtc_development_io.load_package`): V3 accepts exactly the key set
`vtc_development_io.PARAMS` and `source_kind ∈ {user_assumed, synthetic_assumed, literature_other_cultivar}`. Rows with
`unavailable` or `literature_wild_species` therefore never enter a request; they stay in the registry, `forecast_assumptions.csv`
and `unresolved.csv`.

| Registry key | V3 key | Status |
|---|---|---|
| FINAL_VEG_PHYT_NUM (9; candidates 8, 9) | FIRST_LEAVES | active, sampled |
| SP_STOP_RULE | SP_STOP_RULE | active |
| TRUSS_INTERVAL ([2,1,0]) | CADENCE | active, not sampled (no truss record) |
| NR_LEAFLET_PAIRS_BY_RANK ([1,1,2]; candidate [1,1,3]) | PAIRS | active, sampled in the seed route only |
| MIDDLE_PAIR_RAMP (0.35; candidate 0) | MIDDLE_RAMP | active, sampled |
| PHYLLOCHRON 37.9, GERMINATION_DD 206.3 | PHYLLOCHRON_DD, GERMINATION_DD | active, `literature_other_cultivar` (Merlice) |
| T_BASE 5.7 | BASE_C | active, `user_assumed` |
| LEAFLET_ANGLE_GRADIENT_BASAL 35 | BASAL_LEAFLET_ANGLE_DEG | active, `literature_other_cultivar` (Sarlikioti shape prior) |
| CURVE_RATIO [1,2,2], BENT_FRACTION, AREA_CORRECTION | — | `inactive_in_engine` (hooks H1–H3) |
| INTERNODE_CAP (`unavailable`) | INTERNODE_CAP_M | `engine_default_retained` (V3 keeps 0.012 m hypothesis; never 72 mm) |
| DAYS_AT_START 30 | — | `layer_only` |
| CLIMATE_* 26/22 °C, 14 h, RH 60; CO2_PPM 400 | environment.csv | `user_stated` / `user_assumed` |
| CAND_INTERNODE_LOGISTIC, CAND_INSERTION_ANGLE_CHEN7, CAND_AZIMUTH_SUCCESSION | — | `candidate`, inactive |

## Fixes of 2026-10-11/12 (fix prompt B1-B6)

| Item | What changed |
|---|---|
| B1 engines | `--engine pipeline` (route `p1_pipeline`): members are `tools.tomato_fsp_pipeline` runs built from a P1 package through Codex's public `tomato_fsp_acceptance.scenario_fixture` + `prepare_run` + `run`; results are read only from `native_inputs/initial_state.csv` and `committed/step_NNNN` (state, events, checkpoint hashes). `advance_interval` is never called. Multi-instance with canopy placement; manifest records `instance_ids` and per-member `checkpoints`. `--engine v3_direct` (routes `seed_route`, `stage2_fixture`) stays single-plant and is labelled `engine_scope = single_plant_no_canopy` with a `canopy_shading` unresolved row. |
| B2 rays | Default 4,800,000 rays and `issue_class = quantitative`. Fewer rays need `--rays N --diagnostic`; the manifest then carries `issue_class = diagnostic` and `quantitative_light_sampling = false`. |
| B3 eligibility | Before sampling, `eligibility.json` is written: `microtom_parameters.thermal_schedule` (a replica of V3's thermal initiation program) is run per candidate on the actual input state (seed counters / fixture apex counters / P1 plant initialization). A `candidate_set` row is drawn only if a candidate changes the schedule or the pair count of a compound initiated within the horizon; inert rows are named with their reason (`ensemble.excluded_parameters`). Rows without declared uncertainty are never drawn. Nothing eligible -> one member, `ensemble_spread = none`. |
| B4 probability_basis | `forecast_events.csv` gains `probability_basis`: `rule_deterministic` (every member shares SP_STOP_RULE, CADENCE, FIRST_LEAVES, PHYLLOCHRON_DD, GERMINATION_DD, BASE_C, EMERGENCE_DAYS, plus PAIRS for leaflet/rachis initiations), `scenario_fraction` (they differ), `unavailable`. |
| B5 sowing | `--sowing-datetime` (aware ISO) -> `sowing_source = user_stated`; a `파종일` / `sowing_datetime` column in the plant registry (read-only) -> `plant_registry_user_record` per plant; seed-route default -> `assumed_issue_minus_days_at_start`; otherwise `unavailable`. `days_after_sowing` follows. |
| B6 hooks | `microtom_parameters capabilities [--enable-hooks]` reads V3's live parameter list. A hook row activates only when the key is advertised, its value is not `unavailable`, Codex's `fsp_extensions.hook_settings` contract accepts the entry, and `--enable-hooks` is passed (Codex's LOG notice of 2026-10-11 asks to defer until their RESULT). Today: CURVE_RATIO `contract_unmet` (needs an exact-count vector / `by_segment_count` per PAIRS count; no [1,2,2] truncation), BENT_FRACTION `value_unavailable`, AREA_CORRECTION `activation_deferred` (activates with `--enable-hooks`, accounting-only, `area_basis = summed_one_sided_full_outline_lamina_m2`). Decisions and the engine file hashes are in `manifest.engine_capabilities`. |

```powershell
python -X utf8 -m tools.microtom_forecast scenario --engine pipeline --p1 build/p1_state_20261011_01 --out build/my_scenarios/p1.json --members 4 --horizons 1 2 3
python -X utf8 -m tools.microtom_forecast scenario --route seed_route --out build/my_scenarios/seed.json --sowing-datetime 2026-09-11T06:00:00+09:00
python -X utf8 -m tools.microtom_forecast issue --scenario build/my_scenarios/p1.json [--rays 100000 --diagnostic] [--enable-hooks]
python -X utf8 -m tools.microtom_parameters capabilities --enable-hooks
```

## P3 V3 — axis-, truss- and segment-aware forecasting (2026-10-12)

Module `tools/microtom_axes.py`; spec `handoff/CLAUDE_CODE_CLI_PROMPT_P3_SIDESHOOT_FORECAST_V3_2026-10-12.md`; coverage map
`handoff/P3_SIDESHOOT_COVERAGE_2026-10-12.md`. Scope: **declared axes only** (`topology_scope = provided_axes`,
`completeness = unavailable`); trusses generated on a declared axis by the engine's conditional program are allowed
(user_stated applicability) and are always labelled `generated_truss`, never observed.

| Item | What the layer does |
|---|---|
| Input (F2) | When the P1 package has `axes.csv`, the pipeline member scenario gets `axis_contract = fsp-axes-1` and one record per producer axis: producer values copied verbatim (`axis_vertex_id`, `order`, `stage`, `parent_node_id`, `segment_index`, `truss_count`), hidden counters labelled `user_assumed` (clock = GERMINATION_DD + PHYLLOCHRON_DD × (leaf_order + truss_count + 0.1); `apex_stopped = false` supplied, not inferred). Records are validated by the engine owner's public `fsp_axes.select_axes`, which fills `truss_history` and `truss_rule_status`. `segment_index` is never derived; `unavailable` stays `unavailable` and that axis reports `truss_rule_status = unavailable`. Every selected Truss vertex gets the explicit geometry supplement the engine requires: zero-extent bookkeeping points (`zero_extent_bookkeeping_point_casts_no_shadow`), never an observed location. |
| Two `parent_rank` meanings (§2.1) | `read_axis_tables` renames them apart: axis rows carry `axil_parent_rank` (main-stem leaf rank at the axil), truss rows carry `truss_above_rank` (rank on the bearing axis of the leaf below). `axis_attachment_rank()` refuses a truss row and `truss_above_rank()` refuses an axis row. Forecast tables carry `axil_parent_rank` only. |
| Two segment counters (§2.2) | `organ_segment_index` = the organ's immutable segment (engine `state.csv` / `organ_inventory.csv segment_index`); `axis_segment_index` = the axis's current counter at that boundary (committed `axis_inventory.csv segment_index` = 1 + trusses). Both appear on every `forecast_mtg.csv` row; `manifest.axis_columns` says which is which. |
| Registry (F1) | `SUBSTEM_SINK_SCALE` (1.0, user_assumed) and `APPLY_DETERMINATE_STOP` (true, user_assumed program) are `engine_status = axis` rows written into every axis record; `SUBSTEM_TRUSS_APPLICABILITY` (user_stated observation) is a separate provenance row; `TRUSS_INTERVAL`/`CADENCE` stays one shared engine parameter; `AXIS_CADENCE_PER_AXIS` is `blocked_engine_extension` (LOG hook H4), never a per-member draw. |
| Ensemble (F3) | Eligibility runs per declared axis (its own controls). `SUBSTEM_SINK_SCALE` is structurally eligible only with ≥ 1 substem, `APPLY_DETERMINATE_STOP` only on an axis that can still truss; both are reported, but neither has a declared candidate set, so neither is drawn (`no_declared_uncertainty`). |
| Outputs (F4) | `forecast_mtg.csv` + `axis_id, axil_parent_rank, organ_segment_index, axis_segment_index, developmental_axis_id, truss_provenance`; per-axis intervals `axis_leaf_count, axis_leaf_area_mm2, axis_stem_length_mm, axis_truss_count_generated, axis_truss_count_registry` (forecast_id `F:<run>:<plant>/<axis>/Axis`); per-axis events `new_leaf, new_truss_generated, apex_stop` with `probability_basis` (the axis's `APPLY_DETERMINATE_STOP` joins the governing set) and `truss_provenance`; `manifest.headline` states the conditional rule (main stop does not stop live substems); `manifest.axis_sums_check` compares summed `axis_flux.csv` with the plant carbon ledger per committed step. |
| Evaluation (F5) | `forecast_map.csv` gains `axis`; observation rows gain `axis`, `truss_source`; metrics `substem_leaf_count_error` (axis_leaf_count on S axes) and `truss_timing_error_days` — the latter only when `truss_source = registry` (generated trusses are never a reference). |
| Route (F6) | pipeline engine for anything multi-plant/canopy; `v3_direct` stays single-plant and labelled. |

### F8 (2026-10-12) — `SUBSTEM_SINK_SCALE` as a declared SCENARIO SET

The registry row carries `uncertainty_kind = scenario_set`, candidates `[0.5, 1.0, 2.0]` (labels `low` / `base` / `high`; base is
the reference; `user_assumed`, ref user decision 2026-10-12; no cultivar dominance coefficient). A scenario is **not** a probability:
on an axis-aware pipeline route `issue` runs one forecast per value (`scenarios/<label>/members/mNN/…`), the **same** member draw inside
every scenario, aggregates each scenario separately (never pooled; `n_members` per row = members per scenario) and writes `scenario_id`
and `scenario_value` on every MTG / interval / event / member row. Forecast ids become `F:<run>:<label>:<organ>` so the three scenarios
never share an id. `manifest.scenario_set` states what scenarios vary (the scale on every S axis; M and root stay 1.0) versus what
members vary, and `scenario_set.comparison` gives per-scenario per-axis leaf count / area / stem length at the last horizon plus the
`low_high_distance` (a scenario range, labelled as such, not an uncertainty band). `ensemble_spread` is reported for `base` only.
`APPLY_DETERMINATE_STOP` has **no** scenario set (user_stated applicability; `false` is not a biological alternative) and stays `true`.
Routes without declared axes, and `--from-results`, issue the single `base` scenario and say so in `scenario_set.status`.

Existing verified pipeline runs can be consumed as members without Java: `--from-results <run dir ...>` with `--engine pipeline`
(e.g. Codex's `build/fsp_truss_20261012_acceptance_04/side_stop`); the layer reads only `native_inputs/initial_state.csv` and
`committed/step_NNNN`.

```powershell
python -X utf8 -m tools.microtom_forecast scenario --engine pipeline --p1 build/p1_state_20261012_09 --out build/my_scenarios/p3.json --members 4 --horizons 1 2 3
python -X utf8 -m tools.microtom_forecast issue --scenario build/my_scenarios/p3.json
python -X utf8 -m pytest tools/tests/test_microtom_axes.py -q
```

### F9 (2026-10-13) — why the F8 scenarios were identical; stress fixture and reserve threshold (`microtom_stress`)

The F8 result stands: the three `SUBSTEM_SINK_SCALE` scenarios are identical because the engine-owner fixture's declared plant reserve
(0.2 gC, `tools/tomato_fsp_acceptance.py::scenario_fixture`, **user_assumed, unmeasured**) plus daily gross exceed demand, so the capped
sink-weighted allocation never binds. User decision 2026-10-13: the main fixture is **not** tuned to make the scenarios differ (that would
choose the answer); `build/forecast_20261012_04` / `_07` stay untouched; the real verdict waits for measured light (G3 below).

- **Registry.** `PLANT_RESERVE_GC` (0.2 gC, `user_assumed`, `engine_status = hidden_state`) records the dominant assumption; the forecast
  layer passes it through unchanged and lists it in `manifest.hidden_state_passed_through`. `RESERVE_CAP_THRESHOLD_GC` (`source_kind =
  model_property`, `layer_only`) records the sweep result; it is a property of the model and is never adopted as a reserve value.
  New vocabulary: `fixture_declared` (a stress fixture's declared hidden-state value) and `model_property`.
- **G1 stress fixture** (`tools/microtom_stress.py`): same package, same public pipeline functions, but this module's own engine scenario
  JSON replaces `plant_initialization.reserve_gC` with a `fixture_declared` value chosen to make the cap bind. Checks, all from the
  committed tables: the cap binds (`funded < demand`), allocation is demand-proportional under the cap (organ-level oracle
  `tools.fsp_axes.allocation_reference`, `budget = reserve_start + gross - maintenance`), `SUBSTEM_SINK_SCALE` shifts the split in the
  declared direction (S axes: low < base < high; M the reverse), carbon closure (`residual_gC`, `deficit_gC`), per-axis sums = plant ledger.
  No member draw (registry declared values only). **Outputs are never a forecast**: folders are `build/stress_<date>_<NN>` (never
  `forecast_*`), every row and the manifest carry `reuse_as_prediction = forbidden`, the mark is written into the engine scenario's
  `initialization_provenance` (and so into native `plants.csv`), `microtom_forecast` refuses such runs as `--from-results` members, and
  `verify_forecast` / `evaluate` reject the folder. No headline exists in a stress manifest (`finalize_stress` refuses one).
- **G2 threshold sweep.** `--sweep v1 v2 …` runs the base scenario at each `fixture_declared` reserve with everything else fixed and reports
  the bracket (largest non-binding, smallest binding reserve) beside the analytic day-1 value `demand_1 - gross_1 + maintenance_1`
  (`sweep_summary.json`). `--horizon-days H` runs the **declared** reserve for H intervals and reports whether the cap ever binds
  (`horizon.json`). Neither changes any declared value.
- **G3 re-run conditions** live in `microtom_forecast.RERUN_TRIGGERS`; every forecast manifest carries `rerun_trigger` (claimed trigger
  + the three conditions: measured light landed, real P1 package, nutrient feedback enabled), settable with `--rerun-trigger`.

```powershell
python -X utf8 -m tools.microtom_stress run --scenario build/forecast_scenarios_20261012/scenario_p3_axes_pipeline.json --stress-reserve 0.10 --sweep 0.20 0.17 0.15 0.1425 0.1415 0.14 0.12 0.10 0.05 --horizon-days 8
python -X utf8 -m tools.microtom_stress verify build/stress_20261013_01
python -X utf8 -m pytest tools/tests/test_microtom_stress.py -q
```

### F10 (2026-10-13) — run the declared fixture out until the cap binds (`carbon_trajectory.csv`, `--base-only`)

Lengthening the horizon changes no declared assumption, so it is allowed where shrinking the reserve is not. Every pipeline issue now writes
`carbon_trajectory.csv` (one row per committed day, plant and member: reserve start/end, gross, maintenance, budget, demand, allocated,
`funded_fraction`, `cap_binding`, turning points of the reserve, determinate stops and truss births that day; `rays` beside every number) and
`manifest.carbon_cap` (per scenario: first binding day or none, turning points, growth-ending events before binding, whether every declared axis
had already stopped). `scenario_set_mode = base_only` (`--base-only` on `scenario` or `issue`) issues the reference scenario alone for such a
diagnostic; the scenario set is still never pooled. A binding day found this way is a `model_property` of the fixture's declared state
(registry `RESERVE_CAP_BINDING_DAY`), never a Micro-Tom prediction: assumption error accumulates with horizon (fixed light schedule, no fruit sink,
assumed age-target demand curves, nutrient feedback disabled, no real P1 geometry).

```powershell
python -X utf8 -m tools.microtom_forecast scenario --engine pipeline --p1 build/p1_state_20261012_09 --out build/forecast_scenarios_20261013/h1.json --members 1 --horizons 3 7 14 21 30 --base-only
python -X utf8 -m tools.microtom_forecast issue --scenario build/forecast_scenarios_20261013/h1.json
python -X utf8 -m pytest tools/tests/test_microtom_horizon.py -q
```

## Commands (from the project root; all exit 0 on success, 1 with a `ContractError` message otherwise)

```powershell
python -X utf8 -m tools.microtom_parameters validate
python -X utf8 -m tools.microtom_parameters overrides --seed 11 --index 0
python -X utf8 -m tools.microtom_environment climate --out build/my_climate --start 2026-09-11T06:00:00+09:00 --days 44 --t-base-c 5.7
python -X utf8 -m tools.microtom_environment light-input --path build/my_inputs/light_input.csv --photoperiod-h 14
python -X utf8 -m tools.microtom_environment pointer --pointer build/my_inputs/light_ratio_latest.txt
python -X utf8 -m tools.microtom_environment validate-light --sim build/vtc_dev_v3_delivery_sufficient/results/sensors.csv --measured data/records/env_light_20261010/light_ratio_map_20261010.csv --out build/my_light_validation/light_validation.csv
python -X utf8 -m tools.microtom_forecast scenario --route seed_route --out build/my_scenarios/seed.json --members 4 --horizons 1 3 7 14 --rays 300000 --seed 11
python -X utf8 -m tools.microtom_forecast scenario --route stage2_fixture --out build/my_scenarios/fixture.json --members 4 --horizons 1 3 7 14 --source-run build/vtc_dev_v3_delivery_sufficient --fixture-day 30 [--lights-on 06:00]
python -X utf8 -m tools.microtom_forecast issue --scenario build/my_scenarios/seed.json [--date YYYYMMDD] [--from-results <verified V3 run dirs...>]
python -X utf8 -m tools.microtom_forecast_eval link --forecast build/forecast_20261011_01 --links links.json --source phynotype2_review
python -X utf8 -m tools.microtom_forecast_eval evaluate --forecast build/forecast_20261011_01 --observations obs.csv --out build/forecast_eval_01
python -X utf8 -m tools.microtom_forecast_eval preconditions --descriptor descriptor.json --out build/my_baselines
python -X utf8 -m pytest tools/tests/test_microtom_parameters.py tools/tests/test_microtom_environment.py tools/tests/test_microtom_forecast.py tools/tests/test_microtom_forecast_eval.py -q
```

`issue` needs GroIMP 2.2.1 (`C:\Program Files\GroIMP 2.2.1\core.jar`) and Java on PATH unless `--from-results` supplies
already-verified V3 run folders. Each v3_direct member at 300k rays takes about 20–35 s (3–4 min at 4.8M rays for 44 intervals); a pipeline member at 4.8M rays and 3 intervals about 3 min including the P1 freeze; 1,000 rays is too sparse for a 30-day run and V3
rejects the member with `unfunded obligations; carbon deficit` (the engine refusing to publish a starving plant, not a layer error).
A failed issue leaves `FAILED.json` and no `manifest.json`; the folder is then not a forecast.

## Inputs

- **Scenario JSON** (`microtom_forecast.default_scenario`): `route` (`seed_route` | `stage2_fixture`), `start_time` (aware; seed route
  default = today 06:00 (+09:00) minus `DAYS_AT_START`, i.e. the declared sowing time, real date unrecorded), `horizons_days`
  (boundary days after the issue boundary), `lamps`, `light_input`, `ratio_pointer` (relative to the project root; the member input
  gets a relative `light_ratio_latest.txt`, which V3 `prepare` freezes to `inputs/ratios_frozen.csv` + sha), `lights_on_clock_time`
  (`null` today → photoperiod phase `unavailable`), `rays`, `ensemble {size, seed}`, `source_run` + `fixture_day` (fixture route).
- **Registry** `tools/microtom_parameters.csv` (hash recorded as `parameter_sha256`).
- **Seed route**: V3 seed spin-up; the issue boundary is day `DAYS_AT_START` = 30 and `days_after_sowing = 30 + horizon`.
- **Stage-2 fixture route**: `vtc_development_observation.fixture_from_native(source_run, day)` builds the exact-column Stage-2
  fixture (not a real producer); `PAIRS` is excluded from sampling because the imported inventory fixes it. Labelled
  `stage2_observation_fixture`; `days_after_sowing = fixture_age_<n>`.

## Outputs (`build/forecast_<YYYYMMDD>_<NN>/`, written once)

| File | Content |
|---|---|
| `manifest.json` | issue time, route, scenario, `input_snapshot_sha256`, `code_sha256`, `parameter_sha256`, ensemble (size, seed, per-member values, `spread_kind = declared_scenario_set`, `calibrated_probability = false`), engine versions, rays, status labels, `topology_scope = provided_axes`, `completeness = unavailable`, direction mechanisms, inactive/retained parameters, light provenance, photoperiod phase, baseline status, artifact hashes |
| `forecast_mtg.csv` | one row per (member, organ, horizon): `forecast_id` (`F:<run>:<organ>`), `rooted_at_vertex_id`, `root_relation` (`continuation` / `new_organ`), class, parent forecast id, mm geometry, `area_basis = full_outline`, `surface_role = individual_leaflet_polygon` for leaflets (never `compound_envelope`), `direction_mechanism = fixed_generation`, `status = generated_candidate` |
| `forecast_intervals.csv` | per (forecast_id, quantity, horizon): median / min / max over members (`declared_scenario_envelope`, `calibrated = False`), `presence_probability`; leaflet area, internode length, compound length, attachment position / azimuth, plant stem length, height, mass, counts |
| `forecast_events.csv` | per plant and horizon: `new_compound`, `new_internode`, `new_truss`, `apex_stop` with probability = member fraction, count envelope, timing envelope; per new organ: `organ_initiation:<class>` |
| `forecast_assumptions.csv` | every registry row, every V3 parameter the registry leaves untouched (`v3_default_retained`), lamps, `REFERENCE_PPFD`, `DLI_DERIVED`, ratio pointer target hash, scenario controls |
| `forecast_map.csv` | append-only `forecast_id ↔ observed_vertex_id` links (header only at issue); the only file outside the frozen hash set |
| `unresolved.csv` | every quantity not forecast with its reason (direction change, tropism, curvature, unfolding, organ loss, side shoots, blade curl, fruit, accuracy, baselines, absolute PPFD, inactive/retained parameters) |
| `baselines/preconditions.csv`, `baselines/baselines.json` | the six §11 preconditions with `file::function`; baseline values only when they pass |
| `members.csv`, `members/mNN/{inputs,run}` | the frozen V3 input packages and verified native runs (or the consumed result dirs) |

Numeric cells are rounded to 10 significant digits; GroIMP's summation order jitters at ~1e-17, so two native issues of the same
scenario agree to that rounding while two `--from-results` issues are byte-identical.

## Evaluation (`microtom_forecast_eval`)

Observations CSV: `observed_vertex_id, plant_id, capture_id, observed_at (aware), time_since_lights_on_min, photoperiod_phase,
quantity, unit, value, reference_status (independent_observation | synthetic_truth), role (input | target)`. Rules: a target counts
only if `observed_at` is strictly after the issue boundary, falls on a forecast boundary horizon, and its
`time_since_lights_on_min` matches the forecast's phase (unknown lights-on time ⇒ every comparison `unavailable_diurnal_confound`);
linkage is through `forecast_map.csv`, ids are never renamed. Metrics: `interval_coverage`, `abs_error_<unit>` / `area_error_mm2`,
`event_timing_error_days` (`event_time:<type>`), `count_error` (`event_count:<type>`). `leakage_check` fails the evaluation if any
`input` observation post-dates the issue boundary. Growth-accuracy status stays `not testable` until ≥ 3 capture dates of the same
identified plants exist; synthetic-truth runs are software checks only.

## Flags carried in every output

`run_status = assumption_conditioned`, `evaluation_status = evaluated_unaccepted`, `conditional_simulation = true`,
`biological_validation = not_established`, `topology_scope = provided_axes`, `completeness = unavailable`, light `comparison_only`
for ratios, `lamp_placement_status = declared_guess`, `quantitative_light_sampling` true only at ≥ 4.8M rays.
