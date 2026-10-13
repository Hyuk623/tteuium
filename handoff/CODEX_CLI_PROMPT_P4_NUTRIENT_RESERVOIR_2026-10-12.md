# Codex — P4: tray-reservoir nutrient balance and the first nutrient→growth coupling (2026-10-12)

Implementer: **Codex** (owner of `tools/vtc_development*`, `tools/tomato_fsp_*`, `tools/fsp_*`, the nutrient ledger
and the bridge files). Scope: replace the prescribed plant-level water/element replay with a **tray-reservoir
balance driven by the user's real EC records**, and select — explicitly, as one declared law — the first
nutrient → growth coupling. Contract before code. Every number carries `source_kind` + ref.

**This document is the science contract E7 has been waiting for.**
`handoff/CODEX_FSP_EIGHT_CAPABILITIES_EXECUTION_2026-10-11.md` records E7 as blocked: an interface fixture exists
(IDs, hashes, interval and plant bindings, atomic commit, timeout/stale/retry tests) but there is **no native
proposal/pause/finalize handshake and no causal growth constraint**, because no reviewed uptake/demand/allocation
model existed. The law selected below supplies that missing piece for the tray-reservoir case, so build on the E7
fixture rather than starting a new transport; and keep E7's own rule — a successful interface fixture does not by
itself close the science gap, so state engineering status and biological status separately.

## 0. Read first
`CONVENTIONS.md`, `AGENTS.md`, last 40 LOG lines;
`handoff/VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3_2026-10-11.md` (§5: the carbon chain this must plug into);
`handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md` (the "Nutrients" and "Nutrient coupling" rows this closes
partially); `handoff/P4_SIDESHOOT_SCIENCE_AND_IO_CONTRACT_2026-10-12.md` §2 (allocation law) and §4 (nutrients
out of scope — superseded by this prompt); `handoff/CODEX_FSP_NUTRIENTS_EXECUTION_2026-10-06.md`;
`tools/fsp_nutrient_transaction.py` (today a labelled fixture only); `build/nutrient_records_template/`
(the human record form, written 2026-10-12 — reconcile with it, keep its columns unless you have a reason and
document any change); `docs/정의집_토마토_2026-10-11.md`.

## 1. User-stated facts binding this task (2026-10-12, all `user_stated`)
- Irrigation is **sub-irrigation and the solution STANDS in the tray**; pots sit in it and draw from it. So the
  tray is a **reservoir**, not a flow-through drain.
- EC can be measured **per tray only** — drainage from the individual pots mixes in the tray. Per-pot nutrient
  state is not observable.
- Medium is **vermiculite + perlite**. Vermiculite has a large cation exchange capacity; perlite almost none.
- Pots are 60 mm square cells, 70 mm deep (existing `data/records/pots/pot_spec.csv`).
- Supply EC, supply volume, pool EC and pool depth are obtainable; **tissue element analysis is not**.

## 2. Contract first — `handoff/P4_NUTRIENT_RESERVOIR_CONTRACT_2026-10-12.md`
Resolve each of these explicitly, as a selected law with its assumptions named:

1. **Compartments and lumping.** Pool solution + medium-held solution + adsorbed cation pool, per tray. State
   whether pool and medium-held water are treated as one well-mixed compartment (recommended: yes, lumped) and
   that the lumping is an assumption, not a measurement. Capillary exchange is not instantaneous.
2. **Units.** All ion quantities in **EC-equivalent** (mS/cm × L). `element_resolved = false` on every row.
   **Never name the quantity nitrogen.** EC→concentration conversion depends on the ion mix; if a conversion is
   used at all, it is a declared assumption valid only near the supplied recipe.
3. **Water balance.** `dV = supply − evaporation − plant_water_uptake`. Pool volume comes from tray inner
   dimensions × pool depth. Evaporation is taken from the **blank tray** (no plants, same medium, same supply,
   its own tray) — and the contract must say that a leafy tray shades its pool, so the blank's evaporation is an
   upper bound for a planted tray, and state which direction that biases plant water uptake.
4. **Adsorption.** The blank tray's EC trajectory gives adsorption + evaporation together; adsorption saturates,
   so the apparent "uptake" of a fresh medium declines for a non-biological reason. Scale the blank's adsorption
   by medium volume/mass per tray and declare that scaling. Vermiculite adsorbs **cations only** — nitrate is not
   retained — so the EC balance cannot separate cation uptake from cation adsorption; say so.
   **AMENDED 2026-10-13 by measurement — the medium is BIDIRECTIONAL, not a sink only.** Measured the same day:
   supply 1520 uS/cm, and the standing pool **20 minutes after feeding** was 1649 / 1675 / 1691 uS/cm in the three
   trays (+9.2 / +10.9 / +11.2 %). Twenty minutes is far too short for evaporation to concentrate the solution by
   ~10 %, so the rise is salt RELEASED by the medium (previously accumulated salt plus vermiculite cation
   exchange). Model the stored pool as a two-way compartment with both an adsorption and a release term; a
   sink-only medium makes the solver attribute the release to the plant and **overestimates uptake**. The release
   differs per tray (9.2 vs 11.2 %), so the stored amount is a per-tray state, not a shared constant.
   Record: `data/records/env_20261013/nutrient_log_20261013.csv`.
5. **Uptake estimate.** `uptake = supply_ions − Δpool_ions − adsorption_estimate`, per tray per interval, with
   uncertainty propagated from EC-meter resolution and depth-reading error. **Without the blank tray, uptake is
   `unavailable` — never estimated, never 0.** Fitting the uptake parameters requires ≥7 supply events including
   the blank; until then they stay `user_assumed` with the literature candidates registered inactive.
6. **Tray → plant split.** The state is tray-level. Split tray uptake across the tray's plants **in proportion to
   each plant's modelled demand** (the same rule as carbon allocation), flagged `modelled_split` — it is a model
   output, never a measurement. A per-plant nutrient claim may not be published as observed.
7. **The growth coupling — the actual decision.** One limitation factor `f_nut ∈ [0,1]` per tray, applied at a
   **single site: gross assimilation**, so the shortage propagates through the existing resource → demand →
   allocation chain without inventing a second mechanism. Say plainly that this site cannot distinguish lost
   photosynthetic capacity from lost expansion — that distinction needs tissue data the user cannot obtain.
   Shape: inverted-U with a deficiency branch and a **high-EC osmotic branch** (standing solution + evaporation
   makes salt accumulation the expected failure mode, not deficiency alone).
8. **`f_nut` cannot be fitted** — there is no repeated growth observation yet. So its severity is a **SCENARIO
   SET**, exactly like `SUBSTEM_SINK_SCALE` in P3 F8: `none` (reference = today's behaviour, feedback off) /
   `moderate` / `strong`, each a declared parameter triple, `user_assumed`. One run per scenario, reported side by
   side, **never pooled into an interval and never drawn as a member sample**; `scenario_id` on every row.
9. **Gate.** `ENABLE_NUTRIENT_FEEDBACK` defaults **false**. With feedback off the engine must reproduce today's
   numbers **exactly** (regression). Missing records → `unavailable` and the gate refuses to open; a missing EC
   record never becomes 1.0 silently.
10. **Out of scope, stated:** pH, element resolution, root-mass-driven uptake, per-pot nutrient state,
    nutrient-driven direction change (the user excluded direction from version 1), fruit/yield.

## 3. Implementation
- Tray entities in the request JSON: `trays[]` with id, plant ids, inner dimensions, medium mix and volume,
  `has_plants`; parameter registry rows for every new knob with mandatory `source_kind`.
- Reservoir integrator per interval, replacing the prescribed replay on this path; water and ion closure reported
  as a residual in the same style as the carbon ledger (~1e-16).
- Human record ingest: read-only from `data/records/nutrient/` (`tray_spec.csv`, `nutrient_log.csv`); honour the
  `__status` vocabulary; **never write into `data/records/`** — ship any template change under `build/`.
- `f_nut` applied at gross assimilation behind the gate; per-tray and per-plant diagnostics labelled as in §2.6.
- Keep `tools/fsp_nutrient_transaction.py`'s identity/timeout checks; the causal handshake now has a real law to
  carry, so say whether it is used or bypassed.

## 4. Acceptance evidence (label every run conditional)
1. Feedback off → bit-identical to the current engine on an existing fixture (regression, report the comparison).
2. Blank-tray-only fixture → estimated uptake 0 within its stated uncertainty; adsorption saturation reproduced.
3. Water and ion closure every interval; residual reported.
4. Missing blank tray, missing volume, or missing EC → `unavailable` and a refusal to publish an uptake number
   (test the refusal).
5. Feedback on → the three severity scenarios differ, are reported separately, and each carries `scenario_id`;
   the high-EC branch is exercised by a declared salt-accumulation fixture.
6. Existing V3 / integration / forecast-consumer tests still pass (report counts).

## 5. Rules and deliverables
Do not edit `tomato3d/`, `tests/` (Claude Code), `tools/microtom_*` (Claude Code), `config/`, `data/records/`,
`docs/`, original vtc-main (no LICENSE — local only). LOG claim first, result last.
Deliver: the contract MD (§2), code under your claims, `handoff/P4_NUTRIENT_RESERVOIR_EXECUTION_2026-10-12.md`,
the pending-decisions register updated (which rows this closes and which stay open), `flow/flow_map.csv` rows for
your files + `check_flow.py --md` rerun, and a one-paragraph statement of what a real EC record series will and
will not be able to verify.
