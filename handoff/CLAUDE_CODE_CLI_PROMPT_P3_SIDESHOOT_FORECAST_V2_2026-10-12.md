> **SUPERSEDED 2026-10-12** by `handoff/CLAUDE_CODE_CLI_PROMPT_P3_SIDESHOOT_FORECAST_V3_2026-10-12.md`.
> Its scope sentence forbids new trusses, which conflicts with the engine as delivered
> (P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12 X1: the user authorised the conditional program to create trusses).
> Do not run this file.

# Claude Code — P3: side-shoot- and truss-aware forecasting (V2, 2026-10-12)

**Supersedes `handoff/CLAUDE_CODE_CLI_PROMPT_P3_SIDESHOOT_FORECAST_2026-10-12.md`** (written before the
2026-10-12 truss/segment decisions; that file is not to be run). Implementer: **Claude Code** — the files to
change are the forecast layer `tools/microtom_*`, which Claude Code owns; the engine is consumed, never edited.

Prerequisites — do not start until all four exist, and list what each delivered:
`handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md`, `handoff/P1_SEGMENT_TRUSS_EXECUTION_2026-10-12.md`,
`handoff/P4_SIDESHOOT_EXECUTION_2026-10-12.md`, `handoff/P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md`
(+ the resource contract `P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md`).

## 0. Read first
The prerequisites above; `handoff/MTG_CONVENTION_2026-10-10.md` §15 A4 and §16 A5;
`docs/정의집_토마토_2026-10-11.md`; `handoff/CODEX_FORECAST_SPEC_2026-10-10.md` (+ Amendment L1, owner
reconciliation); `handoff/MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md` + coverage map;
`handoff/FORECAST_FIXES_EXECUTION_2026-10-11.md` (B1–B6 state — build on it);
`tools/TOMATO_FSP_PIPELINE.md`; last 40 LOG lines.

## 1. Scope and binding rules
Forecast GROWTH of **declared axes only** — main stem plus registered substems. Side-shoot **emergence** and
truss *emergence* stay out of scope: a forecast never invents an axis or a truss the input state does not
declare (`topology_scope = provided_axes`, `completeness = unavailable`). All runs `assumption_conditioned`;
nothing becomes `measured`; never edit Codex-claimed files or `tomato3d/` (request hooks via LOG); issued
forecasts immutable; 4.8M rays for issued forecasts (or `--diagnostic`).
Coverage map first: `handoff/P3_SIDESHOOT_COVERAGE_2026-10-12.md` — each item below vs what P1/P4/B1–B6 already
provide (done / remainder / blocked), with file:function evidence.

## 2. Work orders (`tools/microtom_*`, tests in `tools/tests/`)
**F1. Registry.** Add the axis and truss parameters the P4 contract now exposes — `SUBSTEM_SINK_SCALE` (default
1.0, `user_assumed`), the per-axis determinate-stop flag and its default, truss cadence per axis — each row with
`source_kind` + ref. The user observation "side shoots bear trusses" enters as `user_stated`, the cadence stays
`user_assumed` until the 화방 sheet has rows.
**F2. Input state.** Read P1 packages (or explicit fixtures) carrying `axes.csv`, `axis`, `parent_rank`,
`axis_state`, truss nodes and **`segment_index`**; pass them into the engine request unchanged. Never derive
`segment_index`; a missing one stays `unavailable` and is reported, not defaulted.
**F3. Ensemble.** Axis and truss parameters join the eligibility-aware draw (a `SUBSTEM_SINK_SCALE` draw is
eligible only when the state has ≥1 substem; a truss-cadence draw only when that axis can still truss). Inert
parameters named in the manifest; spread reported.
**F4. Outputs.** Forecast MTG rows and event tables carry `axis` and `segment_index`. Per-axis events: new leaf,
new truss, determinate stop — each with `probability_basis` (`rule_deterministic` vs `scenario_fraction`, per
the B4 scheme). Report per-axis leaf count, leaf area and stem length with intervals, and make the headline
explicit: after the main apex stops, growth continues on live substems until they stop too — conditional.
**F5. Evaluation.** Rolling-origin comparison per axis via `forecast_map.csv` (gains `axis`); diurnal-phase gate
and leakage check unchanged; new reported metrics: substem leaf-count error and truss-timing error. Growth
accuracy stays `not testable` until repeated observations of the same plants exist — say so.
**F6. Route.** Prefer the pipeline route (B1) for any multi-plant or canopy forecast so substem shading enters
the light step; `v3_direct` stays single-plant and labelled. Never advance an already-produced checkpoint.
**F7. Issue one forecast** on the newest P1 fixture package that contains a substem and a truss (4.8M rays, or a
declared diagnostic), showing per-axis outputs end to end; new folder under `build/forecast_*`; earlier
forecasts untouched.

## 3. Tests (software criteria only)
Axis ids and `segment_index` round-trip input → request → outputs; no invented axes or trusses (an input with
neither yields zero such rows, flagged); per-axis sums equal plant totals in collected ledgers; a stopped axis
emits no new-leaf events while its existing organs still grow; reproducibility, immutability, leakage, no
un-sourced defaults. Full `tools/tests/` suite passes (report counts).

## 4. Deliverables
Coverage map, code + tests, the F7 forecast package, `handoff/P3_SIDESHOOT_FORECAST_EXECUTION_2026-10-12.md`
+ `_KO.md` (commands, exit codes, blocked items with owner), flow_map rows + checker rerun, LOG claim first /
result last.
