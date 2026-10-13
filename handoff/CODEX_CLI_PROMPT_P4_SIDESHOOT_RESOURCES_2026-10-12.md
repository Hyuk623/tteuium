# Codex — P4: carbon / light / nutrient relations between side shoots and the main stem (2026-10-12)

Implementer: Codex (owner of `tools/vtc_development*`, `tools/tomato_fsp_*`, bridge files — all under your
existing claims). Scope: make declared order-1 side-shoot axes (substems) first-class in the native V3 engine
and its ledgers, and write the science contract for how they share resources with the main stem. Observed axes
only — no side-shoot emergence model. Runs in PARALLEL with a Claude Code P1 task; a later P3 forecast prompt
consumes your output, so the deliverable contract below is its input format.

## 0. Read first
`CONVENTIONS.md`, `AGENTS.md`, last 40 LOG lines, `handoff/VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3_2026-10-11.md`,
`handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md`, `handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md`,
`handoff/MTG_CONVENTION_2026-10-10.md` incl. the new Amendment A4 (axes/side shoots — being written by Claude
Code in parallel; if absent, use claude.ai doc `정의집_토마토_2026-10-11` §1-1 and say so), Carvalho 2011 notes
(`논문확인_MicroTom_2026-10-10`).

## 1. User decisions binding this task (2026-10-12)
Side shoot = order-1 axis attached at a main-stem leaf axil (`parent_rank`); registered when its first two
leaves are visible; `axis_shoot` → `substem` when those two leaves are fully expanded; leaf ranks per axis by
the unfolding rule; sympodial continuation = main stem, not a substem; only observed/declared axes exist
(`topology_scope = provided_axes`, completeness `unavailable`).

## 2. Science contract first — `handoff/P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md`
Write it before code; every number carries `source_kind` + source ref; no Micro-Tom claim without data.
Resolve explicitly, as conditional selections listed in the pending-decisions register:
1. **Carbon pool.** One shared pool per plant across axes (current V3 behaviour) — state it as the selected
   law. Allocation = demand-proportional with a per-axis sink multiplier `SUBSTEM_SINK_SCALE` (default 1.0 =
   no dominance, `user_assumed`; apical-dominance values from other cultivars may be listed as candidates
   only). No carbon transfer between plants, unchanged.
2. **Light.** Substem leaflets are ordinary optical polygons in the same scene — mutual shading with main-stem
   leaves emerges from geometry; no separate light rule. Per-axis absorbed-light aggregation is a *diagnostic*
   output, never a claim that an axis keeps its own photosynthate.
3. **Apex rules per axis.** The determinate stop (two successive trusses) applies to the axis that bears the
   trusses; a main-axis stop must NOT stop substem development, and each substem apex has its own
   state (its own stop rule = same conditional program, flagged; whether Micro-Tom substems truss at all is an
   open decision for the human). After the main stop, new leaves may appear only on live substem apexes.
4. **Nutrients.** The prescribed water/element ledger stays plant-level and growth-feedback stays disabled;
   per-axis nutrient bookkeeping is out of scope. Say so; do not invent uptake differences.
5. **Birth and demand.** Substem organs use the same age-target demand curves (shared parameters), charged
   once from the plant pool; `axis_shoot` registration imports two leaves with observed/declared sizes and
   explicit hidden state (mass/age `user_assumed` or supplement-provided, never silently derived).

## 3. Implementation
- Native graph: order-1 axes with parent attachment at the declared main-stem node; stable axis IDs (`S1`…),
  organ inventory rows gain `axis_id` + `parent_rank`; committed states/events/meshes carry them.
- Request JSON: axis list with per-axis parameters (`SUBSTEM_SINK_SCALE`, per-axis stop rule flag); parameter
  registry rows for each, `source_kind` mandatory.
- Importer: accept P1 packages whose `axes.csv`/MTG rows declare substems (coordinate the exact columns with
  Amendment A4; if P1's exporter is not ready, use an explicit fixture of that format, labelled fixture).
- Ledgers: per-axis flux aggregation (gross assimilation attributed by leaflet axis, demand, funded growth)
  that sums exactly to the existing plant ledger; conservation residual unchanged (~1e-16 gC).
- Pipeline (`tomato_fsp_pipeline`): axis-aware collect; no double-charging; replay deterministic.

## 4. Acceptance evidence (synthetic, declared assumptions; label every run conditional)
1. Plant with M + one substem: substem leaves funded exactly once; whole-plant carbon closure holds.
2. Shading: substem leaflet measurably changes a main-stem leaflet's absorbed light at ≥4.8M rays (report the
   effect vs two-seed variation, as in the integration report).
3. Main-apex stop with a live substem: substem continues producing leaves; stopped-axis organs keep growing.
4. Per-axis ledgers sum to the plant ledger every interval; `SUBSTEM_SINK_SCALE` ≠ 1 shifts allocation in the
   declared direction without breaking closure.
5. Failure: an axis referencing a missing parent node, or duplicate axis IDs, refuses to publish.
6. Regression: existing V3/integration/forecast-consumer tests still pass (report counts).

## 5. Rules and deliverables
Do not edit `tomato3d/`, `tests/` (Claude Code's parallel P1 session), `tools/microtom_*` (Claude Code),
`config/`, `data/records/`, `docs/`, original vtc-main (no LICENSE — local only). LOG claim first.
Deliver: the contract MD (§2), code under your claims, `handoff/P4_SIDESHOOT_EXECUTION_2026-10-12.md`,
pending-decisions register updated with the new axis decisions, flow_map rows for your files, LOG result line.
