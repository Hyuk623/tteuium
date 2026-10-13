# Stage 3 — Future structure and growth forecast: science review and implementation contract

Date: 2026-10-10 (written 2026-10-11)
Author: Claude Code
Status: **Specification and science review only. Not an implementation authorization.**
Requested by: `handoff/PROMPT_FORECAST_SPEC_2026-10-10.md`
Korean companion: `handoff/CODEX_FORECAST_SPEC_2026-10-10_KO.md`
Upstream: `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` (Stage 2, written 2026-10-10)

---

## 0. Verdict first

**No growth rate and no emergence interval is estimable from measured data today.** The record
inventory is the gate, and it fails:

| Evidence | State on disk |
|---|---|
| Repeated per-organ observations of the same identified plant | **zero** — one organ-level date, no organ observed twice |
| Identified plants | **zero** — 18 Micro-Tom slots are registered but every `plant_id` cell is empty |
| Caliper lengths | **one** (50.71 mm, one compound leaf, one date, unidentified plant) |
| Truss observations | **zero** — the truss sheet is header-only |
| Measured rachis bend θ | **zero** — a 4-point definition exists, no values |
| Absolute PPFD | **none** — only an uncalibrated per-pot ratio (0.92–1.24), 9 distinct values over 18 plants, two plants per row perfectly confounded |
| Lights-on clock time | **null**, and not back-fillable |

Therefore Stage 3 is specified as a **conditional simulation**, and every run must carry
`run_status = assumption_conditioned` and `evaluation_status = evaluated_unaccepted`. The label
`accepted_for_domain` is forbidden until a time series exists. Software pass criteria (§12) and
growth-accuracy claims (§13) are kept in separate tables and must never be reported as one number.

---

## 1. Files read, and files that do not exist

Read: `../공통규약.md` (7,511 B, exists) · `CONVENTIONS.md` · `handoff/LOG.md` (recent) ·
`handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md` · `handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md` ·
`handoff/MTG_CONVENTION_2026-10-10.md` + `handoff/CLAUDE_CODE_CLI_PROMPT_MTG_AMEND_2026-10-10.md` ·
`handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` · `handoff/PROMPT_FORECAST_SPEC_2026-10-10.md` ·
`handoff/CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md` (65 KB) ·
`handoff/PRIOR_ART_DWARF_TOMATO_FSP_2026-10-08.md` ·
`tools/compound_growth.py` + `COMPOUND_MODEL.md` · `tools/probabilistic_compound_growth.py` (157 KB) +
`PROBABILISTIC_COMPOUND_GROWTH.md` · `tools/light_growth_bridge.py` · `light_growth_consumer.py` +
`LIGHT_GROWTH_BRIDGE.md` · `tools/canopy_light.py` · `tools/hierarchical_light.py` +
`HIERARCHICAL_LIGHT.md` · `tools/fsp_carbon_diagnostic.py` + `FSP_CARBON_DIAGNOSTIC.md` ·
`tools/growth_calibration.py` + `GROWTH_CALIBRATION.md` · `tools/groimp_structure_export.py` ·
`tools/monthly_growth.py` · `tomato3d/light/*` · `tomato3d/io/schemas.py` ·
`tools/tests/{test_compound_growth,test_probabilistic_compound_growth,test_p3_growth_decisions,test_light_reference_faces}.py` ·
`data/records/{env_light_20261010,plant_registry,compound_bend_types_20261010}` (read-only) ·
`docs/복엽구조_형태_2026-10-10.md` · and ~20 run folders under `build/`.

**Not on disk** (nothing substituted):

| Missing | Consequence |
|---|---|
| Any literature file for diaf024 / Butturini / Carvalho 2011 / Martí 2006 / Micro-Tom | The numbers are citable **only from the request text**. Every one is tagged `literature_other_cultivar` and **was not checked against the paper**. |
| `data/records/manual_events.csv`, `organ_label_map.csv` | Abscission/removal is structurally unreachable (Stage 2 §7.8). |
| A `LightScene` with absolute per-fixture photon flux | No absolute PPFD anywhere ⇒ every carbon quantity is conditional on an assumed reference PPFD. |

---

## 2. Scope — what Stage 3 owns and what it calls

| Element | Owner |
|---|---|
| current structure → future structure (the growth / next-structure step) | **Stage 3 owns** |
| the per-organ loop, the forecast-identity namespace, the rolling-origin harness | **Stage 3 owns** (nobody else does) |
| persistence and recent-change baselines | **calls** `tools/compound_growth.forecast()` unchanged, never the two inner functions directly |
| probabilistic event model | **calls** `tools/probabilistic_compound_growth` within its hard scope (§8) |
| per-leaflet light interception, photosynthesis | **calls** where it exists (§7), never re-implements |
| carbon → allocation → growth increment | **does not exist** — must not be called or claimed (§7) |

Code location: `tools/` (Codex's column). Stage 3 may import `tomato3d` but not modify it; any change
there goes to `handoff/LOG.md` as a request to Claude Code.

---

## 3. Inputs

1. **Stage-2 state snapshot** — `build/structure_<YYYYMMDD>_<NN>/<plant_id>/`: `mtg_vertices.csv`
   (with its mandatory `frame`), `structure_state.csv`, `area_estimates.csv`,
   `attachment_candidates.csv`, `unresolved.csv`, `manifest.json`.
2. **Environment scenario** — explicit, declared: setpoint temperature regime, photoperiod, and an
   **assumed reference PPFD** carrying `source_kind = user_assumed`. The per-pot light ratio may
   scale a scenario; it may never stand in for absolute light.
3. **Horizon list** — output days. See §8 for the hard 30-day ceiling.

### Blocker to settle before any reuse

Both existing calculators **hard-gate on `coordinate_frame == 'board_mm'`**, while Stage 2's
board-free default frame is `plant_local_mm`, and the Stage-2 spec forbids writing a transform
between the two because it is not recoverable from anything on disk. **This is the single hardest
structural blocker and it is a human decision**, not a coding task: require board sessions, declare
an adapter with a stated residual, or restate the gate.

---

## 4. Outputs

Under `build/forecast_<YYYYMMDD>_<NN>/<plant_id>/`. New folder per run; **previous forecasts are never
overwritten**.

```
manifest.json            inputs + sha256, config hash, code version, forecast_published_at,
                         input_snapshot_sha256, run_status, evaluation_status, topology_scope
forecast_mtg.csv         the forecast sub-MTG: forecast_id, trajectory_id, rooted_at_vertex_id,
                         horizon_day, every value status 'generated_candidate'
forecast_events.csv      discrete events: event_type, probability, interval_low/high, horizon_day
forecast_intervals.csv   per quantity per horizon: point, interval_low, interval_high, nominal_level
forecast_assumptions.csv one row per parameter used: symbol, value, unit, source_kind, source_ref
forecast_map.csv         append-only link forecast_id <-> later observed vertex_id (§9)
baselines/               persistence and recent_change columns from tools/compound_growth.forecast()
unresolved.csv           every quantity not forecast, with its blocking reason
```

Rules: every numeric value carries `source_kind ∈ {measured, literature_other_cultivar, user_assumed,
unavailable}` and a `source_ref`; every run carries `conditional_simulation = true` while §0 holds;
units are mm, mm², degrees in files and radians in code (`_rad`), thermal time in °Cd.

---

## 5. Continuous change versus discrete events, with estimability

`W` = may be emitted as a forecast now (conditional); `—` = must be `unavailable`.

| Quantity | Estimability | Min timepoints / plants to fit | W |
|---|---|---|---|
| projected area increase | with more timepoints | ≥2 phase-matched per organ for a line; **4–6** for a saturating beta / ≥8–12 plants in ≥2 disjoint groups | — |
| rachis / leaflet length increase | with more timepoints | ≥2 per organ; **4–6** to reach plateau / 1 plant for a rate, ≥8–12 for population | — |
| unfolding | **not estimable** — no recorded variable exists at all | define the stage first; then 3–5 sub-daily captures per leaf | — |
| direction change (azimuth / elevation) | **not estimable** — needs solved rotation *and* depth; more timepoints alone will not fix it | ≥2 phase-matched pairs after prerequisites / 5–10 plants | — |
| curvature change | **not estimable** | ≥7 static θ first to fix the flat/bent boundary, then ≥2 per organ from a side view | — |
| new node / compound leaf (phyllochron) | with more timepoints — **cadence-bound, not count-bound**: interval ≤ ⅓ of the interval estimated, daily or twice-daily, run to termination | ≥8–12 plants for the ~20–30 intervals a 2-parameter wait law needs | — |
| truss emergence and rank | with more **plants** | each plant followed to first truss; **30–50 plants** for a usable rank pmf (18 draws over 4–5 ranks is not a parameter) | — |
| main-stem stop | with more **plants** — one event per plant lifetime | **30–50** followed to termination; the 18-slot cohort supports only a declared rule | — |
| side-shoot emergence (unobserved axis) | **out of scope by design** (§8) | n/a | — |
| abscission / removal | **not estimable**, and the state is unreachable without `manual_events.csv` + `organ_label_map.csv` | full observed lifetimes, 10–20 plants | — |

Nothing in this table is writable as a measurement today. A conditional trajectory may still be
emitted for the first two rows **provided** it is labelled `user_assumed` and
`conditional_simulation = true`.

---

## 6. Direction — three mechanisms, kept separate

| Mechanism | Status | Rule |
|---|---|---|
| (a) fixed-angle generation | **specifiable now, as a declared assumption only** | `source_kind = user_assumed`; never a measurement. No Micro-Tom angle measurement of any kind exists on disk |
| (b) extrapolation of observed direction change | **not specifiable now** | needs two phase-matched observations of the same organ in a common frame; one timepoint, no lights-on clock |
| (c) light / gravity response (phototropism, gravitropism) | **separate research task** | no absolute PPFD, no light-direction description (only a horizontal ratio map), no depth source. The effective n for a light-response slope is **9, not 18**, and row-mates are perfectly confounded. **Do not give it a default** |

---

## 7. Closure contract — the loop is OPEN

| Link | Status |
|---|---|
| 1. structure → per-leaflet light interception | **implemented and run, synthetic geometry only.** For the real plant `dwt_01` the whole light stage returns `unavailable` for every quantity |
| 2. light → photosynthesis (non-rectangular hyperbola) | **implemented and run on hypothetical fixture input** |
| 1 → 2 adapter | **no production adapter** joining the light representation to the carbon representation |
| 3. carbon → organ sink allocation | **not connected** — there is no allocation engine anywhere |
| 4. allocation → organ growth increment | **not connected** — the growth engine is **carbon-blind**: zero occurrences of carbon/assimilate in 2,309 lines |
| 5. growth → next structure | **not connected**, and blocked on purpose |

**The spec must not describe links 3, 4 or 5 as existing in any form.** The one forecast artifact on
disk carries no light or environment coupling at all.

**Forbidden form already present:** the growth engine's forecast state is tagged
`surface_role = 'compound_envelope'`, while the light side correctly uses per-leaflet triangles.
A compound envelope must never be used as an opaque leaf surface for light. Stage 3 must not inherit
that tag; light computation consumes per-leaflet surfaces only. → change request CR-3.

---

## 8. Side shoots and horizon

**Side shoots: excluded.** Decided by the code, not by preference — the probabilistic engine
hard-raises on any scope other than `provided_axes`. Output therefore carries
`topology_scope = 'provided_axes'` and a whole-plant `completeness = unavailable`. Re-enabling
requires editing the scope gate and removing the post-termination completeness guard: a scope
decision for the human, implemented by Codex.

**Horizon:** the 30-day ceiling is hard-enforced with a literal `30` in the probabilistic model
(`probabilistic_compound_growth.py:796-797`). A list of output **days inside [0, 30] already works
and needs no change.** A list of different horizon **lengths** is a code change in `tools/`, owned by
Codex (→ CR-1). The baseline model already accepts a horizon list, so the two columns of Stage 3 do
not share one ceiling — state each column's horizon separately.

---

## 9. Forecast identity

A separate sub-MTG keyed by `forecast_id`, modelled on the MTG §7 candidate rule:

- rooted at the **observed vertex** for a continuation of an existing organ;
- rooted at the **parent axis vertex** for a predicted new organ;
- every value `status = generated_candidate`;
- a later observation is linked by an **append-only** `forecast_map.csv` keyed on
  `(forecast_run_id, trajectory_id, forecast_id)` → `observed_vertex_id`;
- **neither id is ever renamed**, and a forecast id never becomes an observed id.

---

## 10. Rolling-origin evaluation

The origin cut is already implemented correctly in `tools/compound_growth.py` — reuse it.

- **Held out:** for a given `(plant_id, compound_leaf_id, origin)`, every state with
  `observed_at > origin`, including the target's values.
- **Origin:** must be an actual eligible observation instant (the latest history timestamp must
  *equal* the origin), else the row is `unavailable` with reason
  `Eligible origin observation unavailable`.
- **Target:** must match the instant **exactly**, be unique and eligible, carry
  `reference_status ∈ {independent_observation, synthetic_truth}`, and `frame_id` and `parent_stem_id`
  must match between prediction and actual. Consequence: **plan targets must be copied verbatim from
  the recorded `observed_at` strings** — capture-time jitter makes a row unavailable rather than
  matching the nearest session.
- **Never read when producing a forecast:** any post-origin state, the target's values, any
  statistic/rate/fitted parameter derived from post-origin states. `model_parameters` are frozen once
  for the whole evaluation, never retuned per origin.
- **Two gaps to name, not hide:** the frozen train/test split currently does *nothing* for these
  baselines (`train_plant_ids` is read only for the disjointness check and never used again), and the
  forecast carries an input-snapshot field that must be populated rather than left blank.

---

## 11. Baselines — reusable, with six blocking preconditions

`forecast()` dispatches both baselines, timestamps them, forces `eligible_state = False`, and turns
domain violations into per-horizon `status = unavailable`; `evaluate_compound_forecasts` scores six
absolute error metrics. **No edit to `tools/` is needed for that path.** But:

| # | Blocking mismatch | Effect |
|---|---|---|
| 1 | **Frame** — both calculators gate on `coordinate_frame == 'board_mm'`; Stage 2's default is `plant_local_mm` and a transform is forbidden | no board-free capture can be scored. Human decision |
| 2 | **No millimetres** — `scale_status` unavailable for every plant; `validate_history` needs `rachis_points_mm` + matching `rachis_arc_length_mm` | **no state can be constructed at all today** |
| 3 | **Identity** — the probabilistic path refuses any state whose `identity_status != 'confirmed'`; every phynotype2 link is `proposed` until human review | blocked until review runs |
| 4 | **Diurnal** — `recent_change` needs two dates with identical axis/extent stations; Stage 2 emits `unavailable_diurnal_confound` unless `photoperiod_phase` matches and `time_since_lights_on_min` is present on both | lights-on time is null |
| 5 | **No interval** — `compound_growth` produces no prediction interval, so its baselines have nothing to cover | coverage is unscoreable for the baseline column |
| 6 | **Exact-timestamp targets** — see §10 | a plan built from session dates silently yields `unavailable` rows |

Items 1 and 2 mean the baselines have **no admissible input today**. List all six as preconditions in
the implementation, not as footnotes.

---

## 12. Codex implementation instructions

Priority order. Code under `tools/`; Codex-owned tests under `tools/tests/`.

| P | Module / function | Signature | Notes |
|---|---|---|---|
| 1 | `tools/forecast_structure.py::load_stage2_snapshot` | `(run_dir: Path, plant_id: str) -> Stage2Snapshot` | raises `InputContractError` naming the missing column; refuses a snapshot whose `frame` is absent |
| 1 | `…::check_preconditions` | `(snapshot, scenario) -> list[Precondition]` | the six of §11 plus §0's inventory gate; each returns `blocked` + reason, never a silent default |
| 2 | `…::forecast_assumptions` | `(scenario, parameter_table: Path) -> list[AssumptionRow]` | every parameter with `source_kind` + `source_ref`; a row without both is an error |
| 2 | `…::run_baselines` | `(snapshot, horizons_days: list[float]) -> BaselineResult` | calls `tools.compound_growth.forecast()` only |
| 3 | `…::forecast_continuous` | `(snapshot, scenario, horizons_days) -> list[ForecastRow]` | area/length trajectories, interval-valued, `generated_candidate` |
| 3 | `…::forecast_events` | `(snapshot, scenario, horizons_days) -> list[EventRow]` | emergence / truss / stop as probabilities + intervals, within `provided_axes` |
| 4 | `…::link_observation` | `(forecast_run_dir, stage2_snapshot) -> list[MapRow]` | append-only; never renames an id |
| 4 | `…::rolling_origin_plan` | `(states, origins, horizons) -> Plan` | targets copied verbatim from `observed_at` |
| 5 | `tools/forecast_cli.py` | `python -m tools.forecast_cli` | publishes the run folder as one coherent set |

### Software pass criteria (testable today — all must hold)

1. **Reproducibility** — same inputs + same config hash ⇒ byte-identical outputs except
   `forecast_published_at`.
2. **ID non-collision** — no `forecast_id` equals any observed `vertex_id`; no id is reused across
   runs over the same input.
3. **Previous forecasts preserved** — a second run creates a new folder and leaves every earlier
   folder byte-identical.
4. **Zero future leakage — deletion equivalence (decisive):** produce the forecast twice for one
   origin, once from the full state list and once truncated to `observed_at <= origin`; the two
   prediction envelopes must be **byte-identical**.
5. **Zero defaults without provenance** — every numeric cell joins to a `forecast_assumptions.csv`
   row with a non-empty `source_kind` and `source_ref`; count of violations must be 0.
6. **No physical units without scale** — with `scale_status = unavailable`, the count of
   non-`unavailable` `_mm`/`_mm2` cells is 0.
7. **Candidate segregation** — no forecast row appears in any Stage-2 observed file.
8. **Scope honesty** — `topology_scope = 'provided_axes'` and `completeness = unavailable` are present
   whenever side shoots are excluded.
9. **Preconditions surface** — with today's inputs the run exits with every §11 mismatch reported and
   writes no forecast value, rather than producing one.
10. **Status labels** — `run_status = assumption_conditioned`, `evaluation_status =
    evaluated_unaccepted`; a test asserts `accepted_for_domain` never appears.
11. **No compound envelope in light** — no forecast surface row carries
    `surface_role = 'compound_envelope'`.
12. **Read-only inputs** — Stage-2 run folder, `config/` and `data/records/` byte-identical before and
    after.

### Growth-accuracy criteria (NOT testable today)

Emergence timing, event counts, attachment position, direction, area, and **interval coverage** can be
judged only after a phase-matched time series accumulates, with the forecast cohort separated from the
validation cohort. Until then every accuracy field is `unavailable` — not 0, not "pending".

---

## 13. Change requests (do not apply; `tools/` and `config/` are not Claude Code's)

| CR | Request | Owner |
|---|---|---|
| CR-1 | Allow a horizon-length list in `probabilistic_compound_growth` (currently a literal `30` in the same `if` as the scope gate) | Codex, on the human's decision |
| CR-2 | Decide the `board_mm` / `plant_local_mm` gate (§3) — require board sessions, declare an adapter with a residual, or restate the gate | **human** |
| CR-3 | Remove `surface_role = 'compound_envelope'` from any path feeding light; keep per-leaflet surfaces | Codex |
| CR-4 | Populate the input-snapshot field in `forecast()`; make `train_plant_ids` actually constrain fitting | Codex |
| CR-5 | Create `manual_events.csv` and `organ_label_map.csv` with columns, or declare abscission out of scope | **human** |
| CR-6 | Record the daily lights-on clock time going forward; measure `pot_rim_inner_diameter_mm` | **human** |

---

## 14. Human decisions that gate this stage

1. The frame gate (CR-2) — **the hardest blocker**.
2. `pot_rim_inner_diameter_mm`, and the daily lights-on time (CR-6).
3. Definitions for leaflet surface tilt, petiole insertion angle, leaflet curvature — all three are
   undefined, so rows 3–5 of §5 and mechanisms (a)/(b) of §6 have no target quantity.
4. The flat/bent θ boundary (needs ≥7 static measurements).
5. Assign `plant_id` to the 18 registered slots — until then there are **zero identified plants** and
   nothing can be tracked across dates.
6. Whether to follow 30–50 plants to first truss / termination, or accept truss rank and stop as
   declared priors forever.
7. An assumed reference PPFD for conditional carbon runs, or a calibrated meter.

---

## 15. Out of scope

Code implementation; edits to `config/`, `data/records/`, `docs/`, `tomato3d/`, or to any document of
another owner; predicting unobserved side-shoot axes (§8); phototropism/gravitropism defaults (§6c);
any claim that links 3–5 of §7 exist.

---
## Amendment L1 (2026-10-11, appended by Claude/claude.ai) — candidate forms, the vtc fork, and resolved definitions

Sources: `CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md`, `CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md`
(+ Addendum A), read-only code `Downloads\vtc-main` (diaf022 GroIMP). Spec owner reconciles.

1. **Candidate model forms to register (register, never adopt as Micro-Tom laws):**
   - phytomer appearance: phyllochron (°Cd) + apex rules — reference implementation verified in
     `vtc-main/.../rewrites.rgg` (indeterminate: truss every 4th phytomer) and `modules_organs.rgg` Apex;
   - organ extension: logistic (max, k, tm) per internode/leaf — `parametersMerlice.rgg`;
   - insertion angle vs leaf length: Chen eq. (7) — already implemented in `modules_organs.rgg::calcAngle`;
   - next-leaf azimuth: previous + per-plant fitted divergence b, same handedness; uncertainty from the
     measured range 119.3–154.7° (Kanahama 1993, wild species), not ±σ around 135.
   All carry `source_kind = literature_other_cultivar` (or `literature_wild_species`).
2. **The vtc fork is the sandbox for the conditional-simulation track.** Two tracks now exist:
   (a) the contract-bound `tools/` engines (blocked by the six §11 preconditions), and (b) the GroIMP fork
   `build/vtc_microtom_20261011/` with determinate switches (SP_STOP_RULE, TRUSS_INTERVAL,
   NR_LEAFLET_PAIRS_BY_RANK, CURVE_RATIO) and the DLI/ratio light flow. Fork runs carry the SAME labels:
   `run_status = assumption_conditioned`, `evaluation_status = evaluated_unaccepted`. The fork is not a
   route around the record gate; `accepted_for_domain` stays forbidden for fork output too.
3. **CR-3 is satisfied by the fork's representation:** vtc leaves are per-leaflet surfaces (petiolule +
   leaflet polygons), no compound envelope; keep it that way in any port.
4. **Human decision 3 (angle definitions) is now two-thirds resolved** by MTG A1/A2 (insertion angle,
   rachis α1..α3, elevation sign); only leaflet blade curl remains open. §5 rows 3–4 gain defined targets;
   row 5 (blade curl) stays `unavailable` by definition.
5. **Human decision 7 (reference PPFD) has a concrete home:** `light_input.csv` + `light_ratio_latest.txt`
   pointer in the fork (Task 3 of the fork prompt); `source_kind = user_assumed` until the meter arrives.

## Owner reconciliation of Amendment L1 (2026-10-11, Claude Code — appended, nothing above edited)

Checked against `C:\Users\sho36\Downloads\vtc-main\vtc-main\tomatoFSPM_basic_isP` (read-only) and the
project tree on 2026-10-11.

| L1 item | Checked | Status today |
|---|---|---|
| 1 — candidate forms with vtc-main reference locations | **All verified in source:** `rewrites.rgg:65-66` "create a truss every fourth phytomer", `(i[rank] - FINAL_VEG_PHYT_NUM) % 4 == 1` — indeterminate, no apex stop; `modules_organs.rgg:355` `calcAngle()`, `:362-364` `LEAF_CURVE/segments` with the comment "hardcoded for 3 leaflet pairs + terminal leaflet", `:374` `calcNrLeaflets()`, `:774` `module Apex`, `:787` `numberVegPhyt = FINAL_VEG_PHYT_NUM`, `:789` `phylloAngle = PHYLLOTAXIS`; `parametersMerlice.rgg:5` `DELAY 206.3`, `:7` `PHYLLOCHRON 37.9`, `:8` `FINAL_VEG_PHYT_NUM 8`, `:26` `MAX_LEN_INT 0.072` | **Accepted.** Register these as candidate forms with `source_kind = literature_other_cultivar`; Codex references, never re-derives |
| 2 — the fork is the conditional-simulation sandbox, same labels, no gate bypass | `build/vtc_microtom_20261011/` does not exist | **Accepted as design; track (b) is planned.** Until the fork exists there is one track, and it is blocked by the six §11 preconditions |
| 3 — CR-3 satisfied by the vtc representation | **Verified:** `modules_organs.rgg:385` "leaf with leaflets", `:399` petiolule, `:406` first leaflet pair — per-leaflet geometry, no envelope | **Accepted for the fork only.** CR-3 stays **open for track (a)**: the `tools/` growth engine still carries `surface_role = 'compound_envelope'`. The fork satisfying the rule does not close CR-3 |
| 4 — angle definitions two-thirds resolved by MTG A1/A2 | A2 has not been appended to the convention (see the Stage-2 reconciliation) | **Not resolved yet.** §5 rows 3–5 and human decision 3 stand as written |
| 5 — reference PPFD has a home in `light_input.csv` + `light_ratio_latest.txt` | Neither file exists; they are Task 3 of the fork prompt | **Forward contract.** Human decision 7 remains open; the agreed location is recorded |

Net effect on this spec: §5, §11, §12, §13 and §14 are unchanged today. Two things become true the
moment their artifacts exist and should be re-checked then: the A2 append (rows 3–5 of §5), and the
fork with its light files (decision 7, track b).

**Follow-up to the reconciliation note (2026-10-11, Claude Code):** MTG Amendment A2 has now been appended
to `handoff/MTG_CONVENTION_2026-10-10.md` (§12), with A1 incorporated by reference (§11). The angle targets
L1 relied on now exist as definitions: CompoundLeaf `insertion_angle_deg` (stem axis vs petiole, side view
or 3-D only), `rachis_bend_alpha_<i>_deg` with signed Σ = `rachis_curvature_deg` (downward-positive, θ
excludes the last bend), and the two azimuth fields with the azimuth reference defined in §12.1. Human
decision 3 shrinks to leaflet blade curl (§8.3). `tools/phyllotaxis_fit.py` and the vtc fork are still
planned, not present.
