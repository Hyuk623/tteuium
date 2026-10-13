# P3 F9 — why the F8 scenarios were identical, and what was done about it: execution report (2026-10-13)

Author: Claude Code. Work order: `handoff/CLAUDE_CODE_CLI_PROMPT_P3_F9_CARBON_LIMIT_2026-10-13.md`. Follows F8
(`handoff/P3_SIDESHOOT_FORECAST_EXECUTION_2026-10-12.md` §8, `build/forecast_20261012_07`). Guide: `tools/MICROTOM_FORECAST.md` ("F9").
Korean companion: `_KO.md`.

**Status in one line.** The F8 finding is kept and its cause is now recorded as a registry assumption; a separate stress fixture
(`stress_20261013_01`, 12 native cases at 4,800,000 rays, software verification only, every output flagged
`reuse_as_prediction = forbidden`) made the allocation cap bind for the first time and passed every contract check; a reserve sweep found
the model's threshold (**the cap binds below about 0.1420 gC; at the declared 0.2 gC it never binds, not even over 8 days**); the
main fixture, `build/forecast_20261012_04` and `_07` are unchanged. Nothing here is a forecast or a plant measurement.

## 0. The finding this starts from (kept)
F8: 3 scenarios × 4 members × 3 intervals, `low_high_distance = 0` for every per-axis quantity. Cause, verified again here on the committed
F8 base member (`tools/tests/test_microtom_stress.py::test_f8_member_is_unbound_and_closed`): `allocated_gC == demand_gC` in every step because
`reserve_start + gross - maintenance` (0.2 + 0.0118 - 0.0002 = 0.2115 gC on day 1) exceeds demand (0.1536 gC), so the capped sink-weighted
allocation never enters its binding branch. The question "does `SUBSTEM_SINK_SCALE` matter" **cannot be asked in this fixture**.

## 1. User decision applied (2026-10-13)
1. The main fixture is **not** tuned. No declared value changed: the engine-owner fixture still declares `reserve_gC = 0.2`
   (`tools/tomato_fsp_acceptance.py::scenario_fixture`, verified before every stress edit: `checks.main_fixture_unchanged`), `_04` and `_07`
   are untouched (their member `scenario.json` files still read 0.2 and carry no stress mark — tested).
2. A separate stress fixture exists for software verification only (§2).
3. The real verdict waits for measured light (§4). Whether carbon limitation arises on the main fixture is left to be a finding.
4. Nutrient feedback untouched: `ENABLE_NUTRIENT_FEEDBACK` false everywhere, no second scenario set introduced.

## 2. G1 — stress fixture that exercises the allocation cap
**What.** `tools/microtom_stress.py` runs the same engine, on the same P1 package (`build/p1_state_20261012_09`, `fixture_truth`), through the same
public pipeline functions the forecast uses (`prepare_run` → `run`; committed checkpoints only; `advance_interval` never called), with ONE
change made in this module's **own** engine scenario JSON: `plant_initialization.reserve_gC` = **0.1 gC, `source_kind = fixture_declared`**
(replacing the fixture's 0.2). Everything else is held fixed (organ hidden state, climate set-points, lamps, assumed PPFD 300, 4.8M rays,
light seed 11, registry declared values, `APPLY_DETERMINATE_STOP = true`). No member draw. Three runs: low 0.5 / base 1.0 / high 2.0.
The reserve is declared on the engine side (the acceptance fixture), but it is an engine **input field**, so no engine code was edited and no
hook was strictly needed; an optional convenience hook (`scenario_fixture(..., plant_reserve_gC=)`) is noted in LOG as H5, low priority.

**Checks** (all computed from the committed `carbon_ledger.csv`, `organ_allocations.csv`, `axis_flux.csv`, `state.csv`; manifest `checks`):

| check (P4 resource contract §2) | result | evidence |
|---|---|---|
| the cap binds | pass | first binding step 1, funded fraction 0.7263 |
| demand-proportional under the cap (base) | pass | max cross-organ allocation/demand spread 1.1e-16 |
| native allocation = independent oracle (organ level, per-axis scale) | pass | max abs diff 1.6e-17 gC over every case/step |
| budget law funded = min(max(0, reserve+gross-maint), demand) | pass | max abs diff 4.2e-17 gC |
| SUBSTEM_SINK_SCALE shifts the split in the declared direction | pass | S: low < base < high; M: low > base > high at step 1 (table below) |
| carbon closure | pass | max abs residual 4.9e-17 gC, max deficit 0.0 |
| per-axis sums = plant ledger | pass | max abs diff 9.7e-17 gC; axis_flux vs organ sums 0.0e+00 |
| main fixture unchanged | pass | engine fixture reserve before edit {'fx_ss0': 0.2} = registry 0.2 |
| no-reuse mark in every frozen engine scenario | pass | `initialization_provenance` → native `plants.csv` |

**Allocation split at the first binding step** (plant `fx_ss0`; the cap fixes the total, the scale moves the split):

| scenario (SUBSTEM_SINK_SCALE) | step | M allocated gC | S allocated gC (S1+S2) | funded total gC |
|---|---|---|---|---|
| low (0.5) | 1 | 0.08764 | 0.02389 | 0.11153 |
| base (1.0) | 1 | 0.07218 | 0.03935 | 0.11153 |
| high (2.0) | 1 | 0.05736 | 0.05417 | 0.11153 |

**Per-axis leaf count / area at the last step (3 d), three scenarios side by side** — software evidence that the shifted split reaches the organs:

| axis | low: leaves / area mm2 | base: leaves / area mm2 | high: leaves / area mm2 |
|---|---|---|---|
| M | 6 / 5324.8 | 6 / 5160.1 | 6 / 5031.5 |
| S1 | 4 / 1780.8 | 4 / 1897.8 | 4 / 1984.7 |
| S2 | 3 / 959.2 | 3 / 1023.1 | 3 / 1074.8 |

**These numbers are never a forecast of anything.** The reserve was chosen to make the cap bind; the outputs may not be quoted as a
prediction, and no headline, interval or scenario range is drawn from them. Mechanics that enforce it: folders are `build/stress_*`
(never `forecast_*`); every table row and the manifest carry `reuse_as_prediction = forbidden`; the mark is written into the engine scenario's
`initialization_provenance` and so into native `plants.csv`; `microtom_forecast` refuses such runs as `--from-results` members (tested);
`verify_forecast` / `evaluate` reject the folder (tested); `finalize_stress` refuses a manifest with a `headline` (tested).

## 3. G2 — the dominant assumption recorded; threshold found, not adopted
**Registry.** `PLANT_RESERVE_GC` = 0.2 gC, `user_assumed`, `engine_status = hidden_state`, source `tools/tomato_fsp_acceptance.py::scenario_fixture`:
no seed/plant carbon reserve has ever been measured, and this single number decides whether the cap binds at all. Every forecast manifest now
lists it under `hidden_state_passed_through`. `RESERVE_CAP_THRESHOLD_GC` = 0.14203 gC, `source_kind = model_property`, `layer_only`, note
"never adopted".

**Sweep** (base scenario, everything else fixed, 4,800,000 rays, 3 intervals, `fixture_declared` reserves; `sweep_summary.json`):

| reserve_gC (fixture_declared) | cap binds? | first binding step | funded fraction at step 1 |
|---|---|---|---|
| 0.0500 | yes | 1 | 0.4007 |
| 0.1000 | yes | 1 | 0.7263 |
| 0.1200 | yes | 1 | 0.8566 |
| 0.1400 | yes | 1 | 0.9868 |
| 0.1415 | yes | 1 | 0.9966 |
| 0.1425 | no | None | 1.0000 |
| 0.1500 | no | None | 1.0000 |
| 0.1700 | no | None | 1.0000 |
| 0.2000 | no | None | 1.0000 |

Analytic day-1 law (`vtc_development_native.rgg`): the cap binds iff `reserve_start < demand_1 - gross_1 + maintenance_1` =
**0.14203 gC** (identical across all sweep runs: spread 0.0e+00 gC, because the day-1 state and light
are identical). The sweep brackets it: binds at 0.1415, not at 0.1425; monotone in the reserve: True.
**Statement:** the cap binds below about 0.1420 gC; at the declared 0.2 gC it never binds. This is a property of the model
conditional on the fixture's imported demand, the assumed PPFD and lamps — it will move when measured light lands — and it is not adopted
as a reserve value.

**Horizon, separately** (`horizon.json`; base scenario at the **declared** 0.2 gC, 8 intervals): the cap never binds through day 8 at the declared reserve.
The reserve trajectory:

| day | reserve start gC | demand gC | gross gC | reserve end gC |
|---|---|---|---|---|
| 1 | 0.2000 | 0.1536 | 0.0118 | 0.0580 |
| 2 | 0.0580 | 0.0049 | 0.0169 | 0.0695 |
| 3 | 0.0695 | 0.0073 | 0.0169 | 0.0788 |
| 4 | 0.0788 | 0.0083 | 0.0169 | 0.0870 |
| 5 | 0.0870 | 0.0146 | 0.0169 | 0.0888 |
| 6 | 0.0888 | 0.0197 | 0.0173 | 0.0859 |
| 7 | 0.0859 | 0.0287 | 0.0183 | 0.0751 |
| 8 | 0.0751 | 0.0379 | 0.0201 | 0.0569 |

The trajectory is not monotone: the reserve peaks at 0.0888 gC after day 5 and falls from day 6 on because the demand of the newly initiated leaves grows faster than gross assimilation (day 8: demand 0.0379 vs gross 0.0201 gC). So "never binds" is established for 8 days only; whether the declared reserve binds at a longer horizon is open and was not run (no horizon was chosen to make it bind).

## 4. G3 — re-run conditions (recorded; not waited on)
`tools/microtom_forecast.RERUN_TRIGGERS` and every forecast manifest's `rerun_trigger` (claimed trigger + the three conditions; CLI
`--rerun-trigger`). Re-issue on the main fixture when any becomes true, naming it in the manifest:
1. **measured_light_landed** — `tools/reference_dli.py` takes the calibrated field (`handoff/CODEX_CLI_PROMPT_P2_LAMP_CALIBRATION_2026-10-13.md`,
   `data/records/env_20261013/`); carbon limitation then appears or not **as a result** (the shaded point reads ~21 % of the exposed one, so it is
   plausible — plausible is not a finding).
2. **real_p1_package** — the engine has never run from real plant geometry.
3. **nutrient_feedback_enabled** — `f_nut` on gross assimilation could itself create the limited state (out of scope today).
Each re-run keeps `base` as the reference and reports `low_high_distance` beside the headline, as F8 does.

## 5. Acceptance (§5 of the work order)
- Stress fixture binds the cap and the three scenarios separate in the declared direction — **yes** (§2 tables; `all_checks_passed = True`).
- Closure and per-axis sums hold — yes (residual ≤ 4.9e-17 gC; axis sums match the plant ledger in every case).
- The no-reuse flag is tested — yes (refusal as member, folder rejection by the forecast verifier/evaluator, mark in frozen engine scenarios and native `plants.csv`).
- Threshold sweep reproducible — yes (`python -X utf8 -m tools.microtom_stress run --scenario build/forecast_scenarios_20261012/scenario_p3_axes_pipeline.json --stress-reserve 0.1 --sweep 0.2 0.17 0.15 0.1425 0.1415 0.14 0.12 0.1 0.05 --horizon-days 8`; verify with `verify stress_20261013_01`).
- Main fixture's declared values unchanged — yes (diffed: engine fixture reserve before every edit = 0.2; `_04`/`_07` member scenarios read 0.2; registry row says 0.2).
- Tests: microtom set 71 passed (1100 s, native included); full tools/tests 1879 passed / 1 skipped (1582 s).

## 6. Files
Written/changed: `tools/microtom_stress.py` (new), `tools/microtom_parameters.py` (+ `.csv`: `PLANT_RESERVE_GC`, `RESERVE_CAP_THRESHOLD_GC`; vocabulary `hidden_state`,
`fixture_declared`, `model_property`), `tools/microtom_forecast.py` (`scenario_edit` hook for stress runs, refusal of marked runs, `RERUN_TRIGGERS` /
`rerun_trigger`), `tools/microtom_forecast_io.py` (`NO_REUSE_MARK`), `tools/tests/test_microtom_stress.py` (new), `tools/MICROTOM_FORECAST.md`, this report (+ `_KO`),
`flow/flow_map.csv`, `handoff/LOG.md`. Not touched: every Codex-claimed file, `tomato3d/`, `config/`, `data/records/`, `docs/`, `build/forecast_20261012_04`, `_07`.
Native: 12 cases, total native time 499 s, 0 transient retries, GroIMP ['2.2.1'], Java ['openjdk version "21.0.12.1" 2026-08-18 LTS'].

## 7. What this does not say
Nothing here is a plant result: the stress reserve is a declared number, the threshold is conditional on assumed light and the fixture's
imported organ state, and the engine has still never run from real geometry (`real_plant_verified = false`). The scenario set stays declared
and currently inert on the main fixture until a G3 trigger fires.
