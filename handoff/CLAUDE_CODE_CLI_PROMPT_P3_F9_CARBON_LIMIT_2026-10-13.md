# Claude Code — P3 F9: why the F8 scenarios were identical, and what to do about it (2026-10-13)

Implementer: **Claude Code** (owner of `tools/microtom_*`). Follows F8
(`handoff/P3_SIDESHOOT_FORECAST_EXECUTION_2026-10-12.md` §8, `build/forecast_20261012_07`).

## 0. The finding this starts from
F8 ran 3 scenarios × 4 members × 3 intervals and the three scenarios came out **identical**
(`low_high_distance` = 0 for every per-axis quantity). The flux tables show why: every axis got its full demand in
every step, because the fixture's declared **0.2 gC seed reserve** plus daily gross assimilation exceed demand over
the 3-day horizon, so the capped sink weighting never binds.

That is a correct result and it is kept. It means: **the question "does `SUBSTEM_SINK_SCALE` matter" cannot be
asked in this fixture** — not that the parameter is unimportant.

## 1. User decision (2026-10-13) — binding
1. **Do NOT tune the main fixture.** Shrinking the reserve until the scenarios differ chooses the answer: the
   resulting low–high spread would be a property of the number we picked, not of the plant. `build/forecast_20261012_04`
   and `_07` stay untouched, and the scenario set stays declared and currently inert.
2. **A separate stress fixture is allowed, for software verification only.**
3. **The real verdict waits for measured light** (see §4). Whether a carbon-limited state arises must be a finding,
   not a setting.
4. **Nutrient feedback is out of scope here** — it is designed (`handoff/CODEX_CLI_PROMPT_P4_NUTRIENT_RESERVOIR_2026-10-12.md`)
   but not implemented, `ENABLE_NUTRIENT_FEEDBACK` stays false, and no second scenario set is introduced by this task.

## 2. G1 — stress fixture that exercises the allocation cap
The capped sink-weighted allocation has **never executed its binding branch**. Untested code, not a biology question.
- New fixture carrying `fixture_purpose = exercise_allocation_cap` in its manifest, declared hidden state only
  (reserve, imported demand, horizon — whichever you must change, each with `source_kind = fixture_declared`).
- Its only job: prove the engine does what the contract says when demand exceeds supply — allocation is
  demand-proportional under the cap, `SUBSTEM_SINK_SCALE` shifts the split in the declared direction, carbon closure
  still holds, per-axis sums still equal the plant ledger.
- **Its numbers are never quoted as a forecast of anything.** Outputs carry a flag that forbids reuse as a prediction,
  the report states it once in plain words, and no headline, interval or scenario range is drawn from it.
- If the reserve is declared on the engine side rather than in your layer, request the hook in LOG and say so;
  do not edit Codex-claimed files.

## 3. G2 — record the dominant assumption, and find the threshold instead of picking a value
The sensitivity of this forecast is currently governed by the **0.2 gC seed reserve**, which is `user_assumed` with
no measurement behind it. That is the finding to record, in the parameter registry and the report.

Then do the honest version of "make it bind": **search for the threshold, do not adopt it.** Holding everything else
fixed, report the reserve value (and, separately, the horizon) at which the allocation cap first binds and the three
scenarios begin to separate — e.g. "the cap binds below X gC; at the declared 0.2 gC it never binds." A threshold is a
property of the model and can be published; a chosen reserve is an assumption pretending to be a result.
Report the threshold with the sweep that produced it. Do not change the fixture's declared value.

## 4. G3 — re-run conditions (write them down; do not wait on them in this session)
Re-issue on the main fixture when **any** of these becomes true, and state in the manifest which one triggered it:
1. **Measured light lands** — `tools/reference_dli.py` stops using an assumed reference and takes the calibrated
   field from `handoff/CODEX_CLI_PROMPT_P2_LAMP_CALIBRATION_2026-10-13.md` / `data/records/env_20261013/`.
   Gross assimilation then rests on measurement, and carbon limitation appears or does not **as a result**.
   (The measured field already says the shaded leaves get ~21 % of the exposed ones, so limitation is plausible —
   but plausible is not a finding.)
2. **A real P1 package replaces the fixture** — the engine has still never run from real plant geometry.
3. **Nutrient feedback is implemented and enabled** — then `f_nut` multiplies gross assimilation and can itself
   create the limited state. Out of scope today; listed so the trigger exists.
Each re-run keeps `base` as the reference and reports `low_high_distance` beside the headline, as F8 does.

## 5. Acceptance
Stress fixture binds the cap and the three scenarios separate in the declared direction; closure and per-axis sums
hold; the no-reuse flag is tested; the threshold sweep is reproducible and the main fixture's declared values are
unchanged (diff it); existing microtom and `tools/tests` suites pass (report counts).

## 6. Deliverables
Code + tests; `handoff/P3_F9_CARBON_LIMIT_EXECUTION_2026-10-13.md` (+ `_KO.md`); registry rows for the reserve with
its `source_kind` and the threshold result; flow rows + `check_flow.py --md`; LOG claim first, result last.
