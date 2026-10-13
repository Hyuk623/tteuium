# Claude Code — implement the Micro-Tom fork remainder + Stage-3 forecast layer on top of V3 (2026-10-11)

Implementer: Claude Code. **All new code goes in `tools/`** (where the P3 growth/direction code lives:
`compound_growth.py`, `probabilistic_compound_growth.py`, `growth_calibration.py`, `vtc_development*`), tests in
`tools/tests/`. Two specs are being implemented:
- **Fork spec** `handoff/CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md` (Claude/claude.ai; Tasks 1, 1-2, 2, 3 + Addendum A).
- **Forecast spec** `handoff/CODEX_FORECAST_SPEC_2026-10-10.md` (+ `_KO`, Amendment L1, owner reconciliation) (Claude Code).

## 0. Read first; list files read and missing in the report
`CONVENTIONS.md`, `AGENTS.md`, `CLAUDE.md`, last 40 LOG lines, both specs above,
`handoff/VTC_WHOLE_PLANT_DEVELOPMENT_EXECUTION_V3_2026-10-11.md`, `handoff/VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3_2026-10-11.md`,
`handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md`, `handoff/CLAUDE_VTC_SCIENCE_PARAMETER_REVIEW_HANDOFF_2026-10-11.md`,
`handoff/MTG_CONVENTION_2026-10-10.md` (A1, A2, §13), `handoff/CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md` (P3 candidates),
`handoff/CLAUDE_P1_P2_P3_P4_END_TO_END_INTEGRATION_PROMPT_2026-10-11.md` (§7, §8), `flow/flow_map.csv`, and the source of
`tools/vtc_development.py`, `vtc_development_io.py`, `vtc_development_native.rgg`, `compound_growth.py`,
`probabilistic_compound_growth.py`.

## 1. Binding rules
- **V3 already delivers most of the fork spec** (native 30→65-day seed spin-up, determinate stop after two successive
  trusses, first 9 leaves before the first truss, leaflet pairs by true order, middle-pair ramp, full_outline, parameter
  registry with `source_kind`). **Do not re-implement any of it.** Step 2 maps every fork/forecast item to
  done-in-V3 / remainder / blocked; you implement only the remainder.
- File claims: Codex holds `tools/vtc_development*`, `tools/vtc_growth_bridge.py` and the queued
  `tools/tomato_fsp_pipeline.py`, `tomato_fsp_io.py`, `tomato_fsp_canopy.py`, `tomato_fsp_acceptance.py`,
  `TOMATO_FSP_PIPELINE.md`, `tests/test_tomato_fsp_pipeline.py`. **Never edit claimed files.** Consume them through their
  public inputs/outputs (request JSON, parameter registry, output CSVs). If a needed hook is missing, append a request
  line to LOG naming the exact function/field, and build your side against a fixture of that interface.
- Append your own claim to LOG before creating files (list them). `config/`, `data/records/`, `docs/` read-only; the
  original `Downloads/vtc-main` untouched; vtc code has no LICENSE — local use only, never upload or redistribute.
- Every number carries `source_kind` (`measured` / `literature_other_cultivar` / `literature_wild_species` /
  `user_assumed` / `unavailable`) and a source key; no Merlice/diaf024/Chen value becomes a Micro-Tom value.
- MTG decisions: area_basis `full_outline`; blade curl and θ flat/bent thresholds **on hold** (no field, no threshold,
  `rachis_bend_type` is a human label only); A2 angle names/references; compound vs leaflet insertion angle prefixed.
- Runs are `run_status = assumption_conditioned` until fitted to our records; never reported as validated growth.
- Light: phone ratios are relative only (value ÷ 16-cell mean, ÷1.047 when the base is the 3 trays); absolute PPFD/DLI
  only from `light_input.csv` with its `source_kind`; never multiply ratios into already ray-traced light.
- No training, remote jobs, uploads. Quantitative light claims need ≥ 4.8M rays (V3 setting).

## 2. Step 0 — coverage map (write before coding)
`handoff/MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md`: one row per item of fork Tasks 1/1-2/2/3 + Addendum A and per
forecast-spec section §4–§12, columns: item · V3 file:function or output proving it · status
(done_in_V3 / remainder / blocked_by_claim / blocked_by_human_input) · what this prompt does. Expected remainder
(verify, do not assume): items in §3 below.

## 3. Work orders (file names are proposals; keep them unless a V3 equivalent already exists)

### A. Micro-Tom parameter set — `tools/microtom_parameters.py` + `tools/microtom_parameters.csv`
- One registry of Micro-Tom priors in the exact column format V3's request `parameter_registry` accepts
  (value, unit, source_kind, source_ref, cultivar, uncertainty). Rows: `FINAL_VEG_PHYT_NUM` (prior 8/9 per Carvalho),
  `SP_STOP_RULE`, `TRUSS_INTERVAL` cadence, `NR_LEAFLET_PAIRS_BY_RANK` (both candidates kept: Carvalho 5-leaflet vs our
  dissected 3-pair leaf), middle-pair ramp, `CURVE_RATIO` α1:α2:α3 (Chen 1:2:2, literature_other_cultivar),
  `BENT_FRACTION` (0, unavailable — our bend-type share is unmeasured), `AREA_CORRECTION` (1.0, flagged; intercalary +
  secondary leaflets are not geometry), internode cap (`unavailable` until calipers; never 72 mm), phyllochron
  (37.9 °Cd, literature_other_cultivar), T_base 5.7 (user_assumed), `DAYS_AT_START = 30` (user decision 2026-10-11).
- `build_request_overrides(registry) -> dict` that writes these into a V3 request JSON **without editing V3 code**.
  Items V3 cannot express yet (per-segment curve ratio, BENT_FRACTION, AREA_CORRECTION) → LOG hook request + recorded
  as `inactive_in_engine` in the run manifest. Tests: every row has unit + source_kind; no row claims `measured`;
  overrides round-trip into a valid V3 request fixture.

### B. Climate + lamp light flow — `tools/microtom_environment.py`
- `make_climate_csv(start_date, days, day_c=26, night_c=22, photoperiod_h=14, rh=60)` → daily CSV in V3's environment
  format, values flagged `user_stated` (set-points, not logs).
- `load_light_input(path)` for `light_input.csv` (`reference_ppfd_umol_m2_s, source_kind, measured_at`); DLI = PPFD ×
  0.0504 (14 h); `source_kind = user_assumed` until the meter arrives → outputs flagged conditional.
- `resolve_ratio_pointer(pointer_txt)` reading `light_ratio_latest.txt` (one relative path to a slot-ratio CSV in
  `data/records/env_light_*`); validates header (`slot_id`, `ratio_now`, …) else aborts loudly; records the target hash
  so V3's frozen-pointer rule is honoured. Re-measurement = new CSV + pointer edit, no code edit.
- `light_validation(sim_cells_csv, measured_cells_csv)` → `light_validation.csv` with both sides normalised by their
  16-cell mean, ratio RMSE and Pearson r. If V3 native has no 16-cell virtual-sensor output, request the hook in LOG
  and test against a fixture; lamp placement stays a declared guess until this comparison exists.

### C. Stage-3 forecast layer — `tools/microtom_forecast.py`, `tools/microtom_forecast_io.py`, `tools/microtom_forecast_eval.py`
Implements forecast spec §4, §9–§12 using V3 runs as the simulator; nothing here changes biological state.
1. **Inputs**: Stage-2 state snapshot (or the V3 seed route while P1 is not delivered — labelled `seed_route`), environment
   scenario, parameter registry, horizon list (days). Snapshot hash recorded.
2. **Ensemble**: draw parameter sets from each registry row's declared uncertainty (seeded), build one V3 request per
   member, run via V3's public entry point, collect. Ensemble size and seed in the manifest.
3. **Outputs per horizon** (forecast MTG in its own namespace `forecast_id`, never observation IDs): continuous changes
   (leaflet area, internode length, compound dimensions) as median + interval; discrete events (new node/compound/truss,
   apex stop, organ loss if modelled) as probability + timing distribution; attachment position/orientation as
   distributions with source_kind. Direction kept in three mechanisms (fixed generation / extrapolated observed change /
   tropism); tropism stays `not_modelled`. Side shoots: `topology_scope = provided_axes`, completeness `unavailable`.
4. **Immutability**: each issued forecast written once under `build/forecast_<YYYYMMDD>_<nn>/` with issue time, input
   snapshot hash, code + parameter hash; re-issuing creates a new ID; old forecasts never overwritten.
5. **Rolling-origin evaluation** (`microtom_forecast_eval.py`): compare a forecast only with observations taken after
   its issue time at the same photoperiod phase (`time_since_lights_on_min`); forecast↔observation ID linkage via a
   correspondence table, never ID renaming; metrics = interval coverage, event timing error, count error, area error;
   leakage check (no observation later than issue time enters the forecast inputs).
6. **Baselines**: reuse `compound_growth.forecast_persistence` / `forecast_recent_change` if the spec §11 preconditions
   hold (check each, cite file:function); else wrap them with the missing precondition reported.
7. **Candidate forms (register only, Amendment L1)**: phyllochron + internode logistic (maxlen fitted, never from the
   paper), Chen eq.(7) insertion angle vs leaf length, next-leaf azimuth = previous + b with the Kanahama range as
   uncertainty — present in the registry as `candidate`, inactive unless a fit exists.

### D. Tests (`tools/tests/test_microtom_*.py`) — software pass criteria only
Reproducibility (same seed → identical forecast files), ID non-collision (forecast vs observed namespaces), old forecasts
preserved, zero future-information leakage, zero un-sourced defaults (every value traced to a registry row), pointer
re-target changes only the frozen ratio file and its hash, light-validation math on a hand-computed fixture, climate
CSV thermal time = 18.63 °Cd/day at T_base 5.7. Full existing suite still passes; report counts.

## 4. Deliverables
- Coverage map (§2), code + tests (§3), one fixture forecast run and one seed-route forecast run under `build/`.
- `tools/MICROTOM_FORECAST.md` (English guide: commands, inputs, outputs, flags) and
  `handoff/MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md` + `_KO.md`: commands with exit codes, what is done in V3 vs
  here, hooks requested from V3, inactive parameters, and growth-accuracy status = `not testable` until ≥ 3 capture
  dates of the same plants exist.
- Update `flow/flow_map.csv` rows for the fork spec and the forecast spec (status + new paths) and rerun
  `python -X utf8 flow/check_flow.py --md`.
- LOG: claim line first, result line last.

## 5. Out of scope / forbidden
Editing Codex-claimed files, the original vtc-main, `config/`, `data/records/`, `docs/`; P1 photo reconstruction;
nutrient-growth coupling; fitting coefficients to data; any claim of validated Micro-Tom growth; blade-curl or θ
threshold definitions.
