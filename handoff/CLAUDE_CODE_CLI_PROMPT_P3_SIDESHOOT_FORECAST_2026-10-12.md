> **SUPERSEDED 2026-10-12** by `handoff/CLAUDE_CODE_CLI_PROMPT_P3_SIDESHOOT_FORECAST_V2_2026-10-12.md`
> (written before the truss / `segment_index` decisions of 2026-10-12). Do not run this file.

# Claude Code — P3: side-shoot-aware growth forecasting (2026-10-12, run AFTER P1 and P4)

Implementer: **Claude Code** (decision: the files to modify are the forecast layer `tools/microtom_*`, which
Claude Code built and owns; the engine side was delivered by Codex under P4 and is consumed, never edited).
Prerequisites — do not start until both reports exist, and list what each delivered:
`handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md` (axes in P1 packages) and
`handoff/P4_SIDESHOOT_EXECUTION_2026-10-12.md` + `handoff/P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md`
(engine axis support, `SUBSTEM_SINK_SCALE`, per-axis stop, per-axis ledgers).

## 0. Read first
The two prerequisite reports + contract above; `handoff/CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md`;
`handoff/CODEX_FORECAST_SPEC_2026-10-10.md` (+ Amendment L1, owner reconciliation);
`handoff/MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md` + coverage map;
`handoff/CLAUDE_CODE_CLI_PROMPT_FORECAST_FIXES_2026-10-11.md` and its execution report if B1–B6 ran
(build on that state; if that session has not run, say so and apply only what this prompt needs);
`handoff/MTG_CONVENTION_2026-10-10.md` A4; `tools/TOMATO_FSP_PIPELINE.md`; last 40 LOG lines.

## 1. Scope and binding rules
Forecast GROWTH of observed axes only: main stem + registered substems. Side-shoot **emergence** stays out of
scope (`topology_scope = provided_axes`, `completeness = unavailable`) — a forecast must never invent an S-axis
the input state does not declare. All runs `assumption_conditioned`; no value becomes `measured`; never edit
Codex-claimed files or `tomato3d/` (request hooks via LOG instead); issued forecasts immutable; 4.8M rays for
issued forecasts (or `--diagnostic`). Coverage map first:
`handoff/P3_SIDESHOOT_COVERAGE_2026-10-12.md` — each item below vs what P4/B1–B6 already provide
(done / remainder / blocked), with file:function evidence.

## 2. Work orders (`tools/microtom_*`, tests in `tools/tests/`)
**F1. Registry.** Add the axis parameters from the P4 contract to `tools/microtom_parameters.csv` exactly as
the engine request expects them (`SUBSTEM_SINK_SCALE` default 1.0 `user_assumed`, per-axis stop flag, any
other P4-contract knobs), each row with source_kind + ref; candidates (apical-dominance values from other
cultivars) registered inactive.
**F2. Input state.** `microtom_forecast_io` reads P1 packages (or fixtures) carrying `axes.csv` + axis columns
and passes the declared axes into the engine request unchanged — axis IDs, `parent_rank`, `axis_state`
preserved; an `axis_shoot` not yet `substem` is forecast only if the P4 engine accepts it, else reported
`blocked_by_engine` (never silently promoted).
**F3. Ensemble.** Axis parameters join the eligibility-aware draw (a `SUBSTEM_SINK_SCALE` draw is eligible only
when the state has ≥1 substem); members and inert parameters named in the manifest; spread reported.
**F4. Outputs.** Forecast MTG rows and event tables carry `axis`; events gain per-axis entries — new leaf on
S1 (`probability_basis` = rule vs scenario per the B4 scheme), per-axis leaf count / area / stem length with
intervals; main-stop vs substem-continuation shown separately (headline: post-stop growth now continues on
substems — state it as conditional).
**F5. Evaluation.** Rolling-origin comparison per axis via the correspondence table (`forecast_map.csv` gains
`axis`); diurnal-phase gate and leakage check unchanged; substem leaf-count error is a new reported metric.
Growth accuracy stays `not testable` until repeated observations of the same plants exist — say it.
**F6. Route.** Prefer the pipeline route (B1) for any multi-plant/canopy forecast so substem shading is in the
light step; `v3_direct` stays single-plant and is labelled. Never advance an already-produced checkpoint.
**F7. Issue one forecast** on the P1 synthetic substem package (fixture route, 4.8M rays or declared
diagnostic) showing per-axis outputs end to end; new folder under `build/forecast_*`; earlier forecasts untouched.

## 3. Tests (software criteria only)
Axis IDs round-trip input→request→outputs; no invented axes (input without substems → zero S rows, flagged);
per-axis sums equal plant totals in collected ledgers; reproducibility, immutability, leakage, no un-sourced
defaults — all existing microtom tests still pass (report counts; full `tools/tests/` suite too).

## 4. Deliverables
Coverage map, code + tests, the F7 forecast package,
`handoff/P3_SIDESHOOT_FORECAST_EXECUTION_2026-10-12.md` + `_KO.md` (commands, exit codes, blocked items with
owner), flow_map rows updated + checker rerun, LOG claim first / result last.
