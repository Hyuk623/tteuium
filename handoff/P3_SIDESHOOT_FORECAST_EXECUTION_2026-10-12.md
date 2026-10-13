# P3 — axis-, truss- and segment-aware forecasting: execution report (V3 prompt, 2026-10-12)

Author: Claude Code. Work order: `handoff/CLAUDE_CODE_CLI_PROMPT_P3_SIDESHOOT_FORECAST_V3_2026-10-12.md` (supersedes V2, which was not run).
Coverage map written first: `handoff/P3_SIDESHOOT_COVERAGE_2026-10-12.md`. Guide: `tools/MICROTOM_FORECAST.md` ("P3 V3"). Korean companion: `_KO.md`.

**Status in one line.** Implemented and tested in the forecast layer only (`tools/microtom_*`); one axis-aware forecast issued at 4.8M rays on the
current truss fixture package; the engine, `tomato3d/`, `config/`, `data/records/`, `docs/` untouched. Everything is **format-verified, not
real-plant verified**: the engine has never run from a real P1 package (Codex's main-route attempt stopped on missing leaf geometry; the
successful runs use the fixture's `fixture_truth` route), and real-photo scale is unclosed (0 of 117 gaps), so no real forecast can carry mm values.

## 0. Prerequisites read and what each delivered
See the coverage map header: P1 side shoots (A4, revision 3), P1 trusses/segments (A5, revisions 4–5; `build/p1_state_20261012_09` is the current
truss fixture, `_05` superseded, `_10` the real audit), P4 side shoots (fsp-axes-1: declared M/S axes, one carbon pool, per-axis stop flag,
`axis_flux.csv`), P4 substem trusses (user-authorised conditional truss generation, immutable organ segment vs current axis counter, truss geometry
supplement), the resource contract §2 / §7.1–7.3. Also read: MTG §15 A4 / §16 A5, `docs/정의집_토마토_2026-10-11.md` §0, §1-1, `tools/TOMATO_FSP_PIPELINE.md`,
the forecast spec + L1, my B1–B6 report, the last 40 LOG lines, and the engine code consumed: `tools/fsp_axes.py::validate_records/select_axes`,
`tools/fsp_axes_segments.py::prepare_segments/axis_inventory`, `tools/tomato_fsp_io.py::make_native_inputs` (truss supplement rule),
`tools/tomato_fsp_pipeline.py::commit_step` (axis inventories), Codex's build scripts for the actual-P1 run, and the committed outputs of
`build/fsp_truss_20261012_acceptance_04/side_stop` and `build/fsp_truss_20261012_producer_native_02/run`.

## 1. Scope decisions applied
- Declared axes only; no side-shoot axis is ever created (engine rejects undeclared axes; the layer emits `topology_scope = provided_axes`,
  `completeness = unavailable`; test: a legacy package yields zero S rows, flagged `legacy_single_axis`).
- Generated trusses on declared axes are allowed and labelled `generated_truss`; imported/registry trusses are `registry_truss`; the two never share a label
  (test). The user_stated applicability is a separate registry row from the user_assumed program flag.
- Shared `CADENCE` only. Per-axis cadence is **blocked** (engine/contract extension, owner Codex) — registry row `AXIS_CADENCE_PER_AXIS =
  blocked_engine_extension`, LOG hook request **H4**; never faked by a per-member draw.

## 2. Name collisions handled (§2)
| Collision | Handling | Test |
|---|---|---|
| `parent_rank` = axil rank on M (axis rows) vs above-rank on the bearing axis (truss rows) | `microtom_axes.read_axis_tables` removes the ambiguous key and writes `axil_parent_rank` / `truss_above_rank`; `axis_attachment_rank()` refuses truss rows, `truss_above_rank()` refuses axis rows; forecast tables carry `axil_parent_rank` only (engine state `parent_rank` = side attachment rank, 0 for M) | `test_f2_two_parent_rank_meanings_never_cross` (S1 axil 2, S2 axil 5; F0001 above-rank 4 on M, F0002 above-rank 3 on S1; cross read raises) |
| immutable organ `segment_index` vs current axis counter | `organ_segment_index` (state/organ_inventory) and `axis_segment_index` (committed `axis_inventory.csv`) are separate columns on every MTG row; `manifest.axis_columns` defines both | `test_f4_axis_columns_round_trip_and_counters_kept_apart` (side_stop: S1 organs carry 1–4, the axis counter reads 5 after the generated truss) |

## 3. Per work order
| Item | Status | What was done |
|---|---|---|
| F1 registry | done (+ 1 blocked) | `SUBSTEM_SINK_SCALE` 1.0 user_assumed, `APPLY_DETERMINATE_STOP` true user_assumed (program), `SUBSTEM_TRUSS_APPLICABILITY` user_stated (observation, layer-only), `TRUSS_INTERVAL` noted SHARED, `AXIS_CADENCE_PER_AXIS` blocked (H4). New `engine_status` values `axis`, `blocked_engine_extension`; axis rows are checked against `fsp_axes.validate_records` |
| F2 input state | done | `microtom_axes.build_axis_records`: producer values verbatim (vertex ids, order, stage, axil node, `segment_index`, `truss_count`), registration leaves = the two lowest-ranked leaves of the axis, hidden counters `user_assumed` (clock formula stated; `apex_stopped=false` supplied, not inferred); validated and completed (`truss_history`, `truss_rule_status`) by the engine owner's public `select_axes`. `segment_index` never derived: test shows an `unavailable` producer value stays `unavailable` and that axis reports `truss_rule_status = unavailable` and cannot truss. Truss geometry supplement: zero-extent bookkeeping points labelled `zero_extent_bookkeeping_point_casts_no_shadow; not an observed truss location` |
| F3 ensemble | done (nothing drawable) | eligibility per declared axis (its own controls); `SUBSTEM_SINK_SCALE` structurally eligible iff ≥ 1 substem, `APPLY_DETERMINATE_STOP` iff an axis can still truss — both reported, both excluded `no_declared_uncertainty` (no candidate set is declared anywhere; no range invented). On package 09 the thermal rows: `FINAL_VEG_PHYT_NUM` inert, `NR_LEAFLET_PAIRS_BY_RANK` + `MIDDLE_PAIR_RAMP` eligible |
| F4 outputs | done | MTG rows + `axis_id, axil_parent_rank, organ_segment_index, axis_segment_index, developmental_axis_id, truss_provenance`; per-axis intervals (`axis_leaf_count`, `axis_leaf_area_mm2`, `axis_stem_length_mm`, `axis_truss_count_generated`, `axis_truss_count_registry`) and events (`new_leaf`, `new_truss_generated`, `apex_stop`) with `probability_basis` (the axis's stop flag joins the governing set) and `truss_provenance`; `manifest.headline` (conditional: main stop does not stop live substems); `manifest.axis_sums_check` (axis_flux sums vs plant ledger per committed step) |
| F5 evaluation | done | `forecast_map.csv` + `axis`; observations + `axis`, `truss_source`; metrics `substem_leaf_count_error`, `truss_timing_error_days` (only `truss_source = registry`; a generated-truss reference is reported `unavailable`); diurnal gate and leakage unchanged; growth accuracy `not testable` |
| F6 route | done | pipeline engine; `v3_direct` single-plant labelled |
| F7 forecast | done | `build/forecast_20261012_04` on `build/p1_state_20261012_09` (revision 5 confirmed via `p1_manifest.schema_revision`), `fixture_truth`, 4.8M rays — section 5 |

Existing verified pipeline runs can be consumed as members without Java (`--from-results`, pipeline engine); the deterministic tests use Codex's
`side_stop` and the legacy `producer_run_02` this way, reading only committed checkpoints.

## 4. Commands and exit codes
| Command | Exit | Result |
|---|---|---|
| `python -X utf8 -m tools.microtom_parameters validate` | 0 | 26 rows: axis 2, blocked_engine_extension 1, layer_only 2 |
| `… microtom_forecast issue --scenario <p1_pipeline 09, 300k, diagnostic> --from-results build/fsp_truss_20261012_acceptance_04/side_stop` (smoke) | 0 | axis mode, S1 stop at +1, generated `Truss4` vs registry HT1–3, axis sums match ledger (3.5e-18 gC) |
| `… microtom_forecast issue --scenario <p1_pipeline 09, 100k, diagnostic, 1 member, horizon 1 2>` (native smoke) | 0 | 1 min 12 s; M generates `Truss2` at +2 (`generated_truss`), F0001/F0002 `registry_truss`, S1 new leaf at +2 |
| `… microtom_forecast issue --scenario build/forecast_scenarios_20261012/scenario_p3_axes_pipeline.json --date 20261012` | 0 | **`build/forecast_20261012_04`**, 8 min 45 s wall (P1 freeze + prepare per member; native 20.7 / 58.1 / 43.7 / 33.8 s for 3 intervals each) |
| `pytest tools/tests/test_microtom_axes.py -q` | 0 | 12 passed (11 deterministic + 1 native) |
| `pytest tools/tests/test_microtom_*.py -q` (6 files) | 0 | **55 passed** (323.9 s, includes the two native tests) |
| `pytest tools/tests -q` (full) | 0 | **1832 passed, 1 skipped** (1014.1 s); the count includes the other owners' concurrent additions (P1/P4 tests), no existing test changed status |
| `python -X utf8 flow/check_flow.py --md` | 0 | all mapped paths present (after this report) |

## 5. The issued forecast `build/forecast_20261012_04` (conditional; `assumption_conditioned` / `evaluated_unaccepted`)
Input: `build/p1_state_20261012_09`, `state_source = fixture_truth`, capture c2 (2026-10-13 08:00 +09:00), plant `fx_ss0` with axes M (segment 2, 1 registry truss
F0001 above rank 4), S1 (substem, axil rank 2, segment 2, registry truss F0002 above its rank 3) and S2 (substem, axil rank 5, segment 1, no truss). Horizons 1/2/3 days,
4.8M rays, `quantitative_light_sampling = true`, ensemble seed 11.

| | Result (4 members, all `verified`, 3 committed checkpoints each, `native_advance_count = 1`) |
|---|---|
| Eligibility | `NR_LEAFLET_PAIRS_BY_RANK` and `MIDDLE_PAIR_RAMP` eligible (a new compound is initiated within the horizon); `FINAL_VEG_PHYT_NUM` inert (every axis past its first truss or far from it); `SUBSTEM_SINK_SCALE` / `APPLY_DETERMINATE_STOP` structurally eligible but `no_declared_uncertainty` |
| Members | ([1,1,2], 0.35) ([1,1,3], 0.35) ([1,1,3], 0) ([1,1,3], 0) |
| Spread | `present`: 55 of 965 interval rows differ (new leaflets' area/length/width, rachis segments, height) — axis totals identical across members |
| Axes at issue | M: segment 2, registry truss F0001 (above rank 4), `truss_rule_status = available`; S1: substem, axil rank 2, segment 2, registry truss F0002 (above its rank 3); S2: substem, axil rank 5, segment 1, no truss |
| Per-axis events | M: `new_truss_generated` p = 1.0 at +2 d (`generated_truss`, closes segment 2 → counter 3), no new leaf, no stop; S1 and S2: `new_leaf` p = 1.0 at +2 d, no truss, no stop. All `rule_deterministic` (every member shares the thermal and per-axis stop parameters; only PAIRS/ramp vary) |
| Per-axis totals at +3 d | M: 6 leaves, 5377 mm² leaf area, stem 60.2 mm, 1 registry + 1 generated truss; S1: 4 leaves, 1997 mm², 19.0 mm, 1 registry truss; S2: 3 leaves, 1086 mm², 11.2 mm |
| Truss provenance | F0001, F0002 `registry_truss` on every boundary; `fx_ss0/Truss2` `generated_truss` (organ segment 2; axis counter 3 afterwards) |
| Checks | axis_flux sums = plant carbon ledger per step (max 1.39e-17 gC, every member); checkpoint hashes recorded per member; `topology_scope = provided_axes`, `completeness = unavailable`; `sowing_source = unavailable` |


Honesty notes for this run: the P1 package is a synthetic fixture read through its truth table (no photo reconstruction); hidden axis clocks, masses and
`apex_stopped = false` are declared assumptions; the two trusses are zero-extent bookkeeping points (no shadow, no location); the same shared `CADENCE`
drives every axis; `sowing_source = unavailable`.

## 6. Blocked items (owner)
| Item | Why | Owner |
|---|---|---|
| Per-axis cadence (`AXIS_CADENCE_PER_AXIS`) | engine shares one `CADENCE`; needs an fsp-axes-1 contract extension (hook H4) | Codex |
| Drawing `SUBSTEM_SINK_SCALE` / `APPLY_DETERMINATE_STOP` | no declared candidate set; eligibility machinery exists | human (declare candidates) |
| Real-plant forecast | engine never ran from a real P1 package; main route stops on missing leaf geometry; real scale 0/117 closed | P1 owner + human (pot rim points, Q2) |
| Growth accuracy | no repeated observations of identified plants; lights-on clock time varies by hand ('내외') | human |

## 7. Tests (software criteria)
Axis ids and both counters round-trip input → request → outputs; the two `parent_rank` meanings never cross (explicit failing read); no invented axes on a
legacy package; generated trusses never labelled registry/observed; per-axis sums equal plant ledger totals (max 3.5e-18 gC on side_stop); a stopped axis
emits no `new_leaf` while its leaf area still grows; reproducibility (byte-identical from the same committed checkpoints), immutability, leakage, zero
un-sourced defaults (inherited B-layer tests, all passing with the new columns).

## 8. F8 (added 2026-10-12) — `SUBSTEM_SINK_SCALE` as a declared SCENARIO SET: executed
Implemented: registry row `uncertainty_kind = scenario_set`, candidates 0.5 / 1.0 / 2.0 (labels low / base / high, base = reference, `user_assumed`,
ref user decision 2026-10-12; no cultivar dominance coefficient). On an axis-aware pipeline route `issue` runs one forecast per value with the **same**
member draw inside each (`scenarios/<label>/members/mNN`), aggregates each scenario separately (never pooled; `n_members` per row = members per
scenario), writes `scenario_id` + `scenario_value` on every MTG / interval / event / member row, and uses ids `F:<run>:<label>:<organ>` so scenarios
never share an id. `manifest.scenario_set` states what scenarios vary (the scale on every S axis; M and root 1.0) vs what members vary, and carries
`comparison.low_high_distance`. `APPLY_DETERMINATE_STOP` has **no** scenario set and stays `true`. Legacy routes and `--from-results` issue `base` only and say so.
Tests: `test_f8_*` (3) — 58 microtom tests pass; full `tools/tests` **1835 passed, 1 skipped** (3806 s, slowed by concurrent native runs).

Re-issue on the same package (`build/p1_state_20261012_09`, fixture_truth, 4.8M rays, 3 scenarios x 4 members x 3 intervals):
**`build/forecast_20261012_07`** (75 min 48 s wall; 0 member retries). `build/forecast_20261012_05` and `_06` are FAILED folders (no manifest):
Windows/OneDrive denied the engine's atomic folder rename (`.step_0003_partial` -> `step_0003`; `publication_partial` -> `results`) while the
full test suite was writing to `build/`; the native runs themselves were verified. A member-level retry (rebuild from a fresh folder, at most 2,
recorded in `manifest.transient_retries`) was added before the successful third attempt and was not needed in it. `_04` untouched.

**Result - the three scenarios are identical.** Per-axis leaf count / leaf area / stem length at +3 d (low = base = high): M 6 / 5377 mm2 / 60.2 mm;
S1 4 / 1997 mm2 / 19.0 mm; S2 3 / 1086 mm2 / 11.2 mm; no apex stop in any scenario; `low_high_distance = 0` for every quantity. Cause, verified in the
committed `axis_flux.csv` of every step and scenario: `allocated_gC == demand_gC` for every axis - the engine's capped sink-weighted allocation only
acts when the plant carbon budget binds, and in this fixture the declared 0.2 gC seed reserve plus daily gross assimilation (~0.017 gC) exceed the daily
demand (0.154 gC on day 1, then < 0.005 gC) throughout the 3-day horizon. **One sentence on what the parameter is worth:** in this fixture and horizon
the unmeasured sink scale is worth exactly nothing (0 mm2, 0 leaves), so a real measurement would buy nothing until a carbon-limited state is simulated
(smaller declared reserve, more demand, or a longer horizon) - that limitation is the fixture's declared hidden state, not evidence about Micro-Tom.
