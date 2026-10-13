# Claude Code — P3 F10: run the declared fixture out until it binds (2026-10-13)

Implementer: **Claude Code** (owner of `tools/microtom_*`). One work item, following F9
(`handoff/P3_F9_CARBON_LIMIT_EXECUTION_2026-10-13.md`).

## 1. Why this is allowed — and why it is not fixture tuning
F9 found that the declared **0.2 gC** reserve never binds the allocation cap over 8 days, but that the trajectory is
**not monotone**: the reserve peaks after day 5 and falls from day 6 as new-leaf demand outgrows gross assimilation.
The threshold is **0.1420 gC** — only 1.4× below the declared value, and the trajectory is heading toward it.

Shrinking the reserve would choose the answer and stays forbidden. **Lengthening the horizon changes no declared
assumption at all** — it only asks what the already-declared state does given more time. So run it.

## 2. Work order
**H1. Diagnostic sweep first, cheaply.** `base` scenario only, declared 0.2 gC unchanged, horizon extended to **30
days** (the same length as the existing native seed runs). Reduced ray budget is fine here and must be stated beside
every number. Export the **full per-interval reserve trajectory**, not just the first crossing — F9 showed the curve
turns, so it may turn again.

Report, in this order:
1. the day the allocation cap **first binds**, or that it does not within 30 days;
2. the reserve trajectory with its turning points;
3. whether any other event (determinate stop, apex stop, truss generation) ends growth before binding — if so, that
   is the answer and the cap never becomes reachable in this fixture.

**H2. Only if it binds: re-issue the F8 scenario set** (`SUBSTEM_SINK_SCALE` 0.5 / 1.0 / 2.0) over a horizon that
**contains the binding period**, at the declared 4.8M rays, with the usual member ensemble inside each scenario.
Report `low_high_distance` per per-axis quantity. If it is non-zero, say so plainly: that is the first time this
parameter has been answerable at all, and the size of the spread is what a real measurement of it would be worth.
Keep `base` as the reference and keep every earlier forecast untouched.

**H3. Label the result correctly.** The binding day is a **property of this fixture's declared state**, exactly like
`RESERVE_CAP_THRESHOLD_GC` — `source_kind = model_property`, never a Micro-Tom prediction. State explicitly that
assumption error accumulates with horizon and name the assumptions that now matter more than they did over 3 days:
fixed light schedule, no truss or fruit sink, assumed age-target demand curves, nutrient feedback disabled,
no real P1 geometry. A 30-day number from a 3-day-validated fixture is a model statement, not a forecast.

## 3. Acceptance
The declared reserve is unchanged (diff it); the trajectory table is complete and reproducible; the ray budget is
printed beside every number; if H2 runs, its scenarios carry `scenario_id` as in F8 and nothing is pooled; stress
fixtures and their `reuse_as_prediction = forbidden` outputs are not involved; existing suites pass with counts.

## 4. Deliverables
`handoff/P3_F10_HORIZON_EXECUTION_2026-10-13.md` (+ `_KO.md`) with the trajectory table and the binding day (or its
absence), the new forecast folder if H2 ran, registry row for the binding day, flow rows + `check_flow.py --md`,
LOG claim first and result last.
