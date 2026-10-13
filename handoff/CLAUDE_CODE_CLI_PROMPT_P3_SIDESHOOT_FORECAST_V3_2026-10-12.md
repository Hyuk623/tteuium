# Claude Code — P3: axis-, truss- and segment-aware forecasting (V3, 2026-10-12)

**Supersedes V2** (`handoff/CLAUDE_CODE_CLI_PROMPT_P3_SIDESHOOT_FORECAST_V2_2026-10-12.md`), whose no-new-truss
clause conflicts with the engine as delivered. Do not run V2. Implementer: **Claude Code** — the files to change
are the forecast layer `tools/microtom_*`, which Claude Code owns; the engine is consumed, never edited.

Prerequisites, all now present — list what each delivered:
`handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md`, `handoff/P1_SEGMENT_TRUSS_EXECUTION_2026-10-12.md`,
`handoff/P4_SIDESHOOT_EXECUTION_2026-10-12.md`, `handoff/P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md`,
`handoff/P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md` (§2 and §7.1–7.3 are the binding consumer contract).

## 0. Read first
The prerequisites above; `handoff/MTG_CONVENTION_2026-10-10.md` §15 A4 and §16 A5; `docs/정의집_토마토_2026-10-11.md`;
`handoff/CODEX_FORECAST_SPEC_2026-10-10.md` (+ Amendment L1, owner reconciliation);
`handoff/MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md` + its coverage map;
`handoff/FORECAST_FIXES_EXECUTION_2026-10-11.md` (B1–B6 state — build on it); `tools/TOMATO_FSP_PIPELINE.md`;
last 40 LOG lines.

## 1. Scope — read this before anything else
Forecast the growth and development of **declared axes only**. V2 forbade both new axes and new trusses in one
sentence; that was wrong, and this replaces it:

| | Allowed? |
|---|---|
| A side-shoot **axis** the input state does not declare | **Never.** `topology_scope = provided_axes`, `topology_completeness = unavailable`. |
| A **truss** generated on a declared axis by the engine's conditional determinate program | **Yes** — the user authorised it (P4 X1, `source_kind = user_stated`), and the two-successive-truss stop rule cannot run without it. |
| Labelling a generated truss as observed | **Never.** Generated trusses carry the model's own provenance; the P1 `Truss` rows (human registry) stay distinguishable in every output. |

All runs `assumption_conditioned`; nothing becomes `measured`; never edit Codex-claimed files or `tomato3d/`
(request hooks via LOG); issued forecasts immutable; 4.8M rays for issued forecasts (or `--diagnostic`); never
advance an already-produced checkpoint.

Coverage map first: `handoff/P3_SIDESHOOT_COVERAGE_2026-10-12.md` — every item below against what P1, P4 and
B1–B6 already provide (done / remainder / blocked), with file:function evidence.

## 2. Two name collisions that will corrupt results silently — handle explicitly
1. **`parent_rank` means two different things.** On a `trusses.csv` row it is the **above-rank on the bearing
   axis** (the truss sits directly above that leaf rank of its own axis). On an axis row it is the **main-stem
   leaf rank at whose axil the side shoot attaches**. Carry them in separate fields through the whole forecast
   layer and name them differently in your own code; a test must fail if one is read as the other.
2. **Two segment counters.** The engine exports an organ's **immutable** `segment_index`
   (`organ_inventory.csv`) and an axis's **current** counter (`axis_inventory.csv`, `apices.csv
   axis_segment_index`), which increments at each truss. Preserve both, never collapse them, and say which one
   each forecast column reports.

## 3. Work orders (`tools/microtom_*`, tests in `tools/tests/`)
**F1. Registry.** Add the axis and truss parameters the P4 contract now exposes, each with `source_kind` + ref:
`SUBSTEM_SINK_SCALE` (default 1.0, `user_assumed`), the per-axis `APPLY_DETERMINATE_STOP` flag (default true,
`user_assumed` program; the *applicability* to substems is `user_stated` from the user's observation — keep those
two provenances separate), and the shared truss `CADENCE` with its existing source. Per-axis cadence is NOT
available in the engine (it shares one CADENCE); if a scenario needs different cadence per axis, request the
contract extension in LOG and mark it blocked — do not fake it with a per-member draw.

**F2. Input state.** `microtom_forecast_io` reads P1 packages (or explicit fixtures) carrying `axes.csv`,
`trusses.csv`, `axis`, `axis_state`, both `parent_rank` meanings and `segment_index`, and passes them into the
engine request unchanged. **Never derive `segment_index`** from rank, age or counts — the engine rejects that and
so must you; missing stays `unavailable` and the axis's truss rule reports `unavailable`. Supply the explicit
truss **geometry supplement** the engine requires (`geometry_source_kind`, `geometry_source_ref`, `base_xyz_m`,
`tip_xyz_m`); the acceptance fixtures use zero-extent bookkeeping points that cast no shadow — label them that
way and never present them as observed truss locations.

**F3. Ensemble.** Axis and truss parameters join the eligibility-aware draw: `SUBSTEM_SINK_SCALE` only when the
state has ≥ 1 substem; a stop-flag or cadence draw only on an axis that can still truss. Inert parameters named
in the manifest; spread reported.

**F4. Outputs.** Forecast MTG rows and event tables carry `axis` and both segment counters. Per-axis events: new
leaf, **new truss (generated)**, determinate stop — each with `probability_basis` (`rule_deterministic` vs
`scenario_fraction`, per the B4 scheme) and a provenance field separating generated trusses from registry
trusses. Report per-axis leaf count, leaf area and stem length with intervals. Make the headline explicit and
conditional: after the main apex stops, growth continues on live substems until their own trusses stop them too.

**F5. Evaluation.** Rolling-origin comparison per axis via `forecast_map.csv` (gains `axis`); diurnal-phase gate
and leakage check unchanged; new reported metrics: substem leaf-count error and truss-timing error — the latter
compared only against **registry** trusses, never against generated ones. Growth accuracy stays `not testable`
until repeated observations of the same plants exist; say so.

**F6. Route.** Prefer the pipeline route (B1) for any multi-plant or canopy forecast so substem shading enters
the light step; `v3_direct` stays single-plant and labelled.

**F7. Issue one forecast** on the newest P1 fixture package containing a substem and trusses
(`build/p1_state_20261012_09`, revision 5 — confirm it is the current one; `_05` is superseded). 4.8M rays or a
declared diagnostic. New folder under `build/forecast_*`; earlier forecasts untouched.

## 4. Tests (software criteria only)
Axis ids and both segment counters round-trip input → request → outputs; the two `parent_rank` meanings never
cross (explicit failing test); no invented **axes** (an input without substems yields zero S rows, flagged);
generated trusses are never labelled observed; per-axis sums equal plant totals in collected ledgers; a stopped
axis emits no new-leaf events while its existing organs still grow; reproducibility, immutability, leakage, no
un-sourced defaults. Full `tools/tests/` suite passes (report counts).

## 5. State plainly in the report, do not work around
- The engine has **not** been run from a real P1 package: Codex's attempt stopped on missing leaf geometry and
  the successful run used the fixture's `fixture_truth` route. Anything you issue is format-verified, not
  real-plant verified.
- Real-photo scale is still unclosed (0 of 117 gaps), so no real forecast can carry mm values yet.

## 6. Deliverables
Coverage map, code + tests, the F7 forecast package,
`handoff/P3_SIDESHOOT_FORECAST_EXECUTION_2026-10-12.md` + `_KO.md` (commands, exit codes, blocked items with
owner), flow_map rows — also upsert Codex's pending rows from
`handoff/P4_SUBSTEM_TRUSS_FLOW_ROWS_2026-10-12.csv` by path — and rerun `python -X utf8 flow/check_flow.py --md`.
LOG claim first / result last.

---

## F8 (added 2026-10-12) — declare `SUBSTEM_SINK_SCALE` as a SCENARIO SET

The first issued forecast (`build/forecast_20261012_04`) drew nothing for the two axis parameters because
neither had a declared candidate set. Not inventing a range was right. The consequence, though, is that every
member silently assumed `SUBSTEM_SINK_SCALE = 1.0` — a side shoot competing exactly like the main stem — and
that single assumption never appears in any interval. The user has decided to make it explicit.

**Declare a scenario set, not a distribution.**

| | value | meaning |
|---|---|---|
| `low` | **0.5** | main stem favoured (apical dominance) |
| `base` | **1.0** | no dominance — the current default |
| `high` | **2.0** | side shoot favoured |

Geometric spacing (×0.5, ×1, ×2) because the parameter is a multiplier. `source_kind = user_assumed`,
ref: user decision 2026-10-12. **No cultivar dominance coefficient is adopted or fitted**, and no literature
value enters.

Rules:
1. **A scenario is not a probability.** Run one forecast per scenario value and report them side by side.
   Never pool the three into one interval, never call the spread between them an uncertainty band, and never
   let a scenario value enter the member draw as if it were sampled from a distribution.
2. Every forecast row, event row and manifest carries its `scenario_id` (`low` / `base` / `high`) and the
   value used. A reader must be able to see which scenario produced which number without opening the request.
3. The existing member ensemble runs **inside** each scenario, so the output is 3 scenarios × N members. Say
   in the manifest what the members vary and what the scenarios vary — they are different kinds of thing.
4. `base` remains the reference: comparisons and any headline number quote `base` and state the `low`/`high`
   range beside it as a scenario range, labelled as such.
5. **`APPLY_DETERMINATE_STOP` gets no scenario set.** Its substem applicability is `user_stated` (the user
   observed that side shoots bear trusses), and `false` means "this axis initiates nothing new", which is not a
   biological alternative to that observation. Keep it `true` and say so.
6. Re-issue on the same fixture package as F7 so the two are comparable; the earlier forecast stays untouched.

Report: the three scenarios' per-axis leaf counts, leaf areas and any stop timing, plus one sentence on how far
apart `low` and `high` are — that difference is the honest size of what this unmeasured parameter is worth, and
it tells the human how much a real measurement would buy.
