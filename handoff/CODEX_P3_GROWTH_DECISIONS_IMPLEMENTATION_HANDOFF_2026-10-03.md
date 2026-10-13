# P3 growth decisions D8–D10 — implementation handoff for Codex (`생장방향`)

Date: 2026-10-03, Asia/Seoul. From Claude (coordination) to Codex, P3 owner.
User decisions: D8, D9, D10 in `CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` section 7.
Background: `CLAUDE_GROWTH_EQUATION_REVIEW_FOR_CODEX_2026-10-03.md` (Claude Science review, equations E1, E3, E9, E10).
Scope: P3 internal changes only. Cross-project linking stays deferred (D3). P4 stays diagnostic (D2).

## 0 Before editing

1. Read parent `공통규약.md`, `AGENTS.md`, `CONVENTIONS.md`, latest LOG/TODO.
2. Complete review item 7 of the review handoff first if not done: verify the 9 discrepancies against current source and record findings. Where a discrepancy changes a requirement below, stop and report instead of guessing.
3. Files in scope: `tools/probabilistic_compound_growth.py`, `tools/compound_growth.py` (delegation only), `tools/growth_calibration.py` (only where bindings must recognize new families/fields), their tests under `tools/tests/`, `tools/PROBABILISTIC_COMPOUND_GROWTH.md`, `tools/GROWTH_CALIBRATION.md`. Do not edit `tomato3d/`, root `tests/`, `config/`, `docs/`, human observations.
4. All changes are **additive and backward compatible**: existing `probabilistic-compound-1` configs must produce byte-identical outputs unless they opt into a new feature. Bump to a minor schema version only if needed and document it.

## 1 D8 — newborn organs use `determinate_beta`

Existing organs (present at origin): unchanged exponential remaining-growth, D and k as now.

Organs born inside the horizon may declare `growth_curve="determinate_beta"` (default remains the exponential):

```text
x(alpha) = x_max * (1 + (a_e - alpha)/(a_e - a_m)) * (alpha/a_e)^(a_e/(a_e - a_m)),  0 <= alpha <= a_e
x(alpha) = x_max,                                                                    alpha > a_e
constraint 0 < a_m < a_e; rate is zero at alpha = 0 and alpha = a_e
```

- Parameters: `x_max` (target units: mm or cm2), `a_m`, `a_e` (development days). Optional declared ratio `a_m_over_a_e` reducing free parameters to two.
- Literature ratios (Butturini 2026, cv. Twiggy Red) 0.584 leaf, 0.444 internode are **prior candidates only**; record with provenance, never as defaults.
- Applies per coordinate: rachis length, width extents, segment length, optional area.
- Birth values (`birth_area_cm2`, zero-length terminal) stay as now; `x(0)` from the formula is 0, so define birth explicitly: `x(alpha) = x_birth + (x_max - x_birth) * beta_shape(alpha)` where `beta_shape` is the formula with `x_max = 1`. Reject particles with `x_max < x_birth`.
- Parameter particles: add the new coordinates through the existing ordered `coordinates` with explicit transforms (`exp` for x_max, bounded/ordered handling for a_m < a_e). Missing covariance remains an explicit assumption, not zero.
- Calibration: no new fit family is required now. If `apply_parameter_set` meets a beta-coordinate binding, it must refuse with a clear reason rather than bind exponential parameters to it.

## 2 D9 — environment entry and `p3_light_coupling`

Temperature → clock only:
- Use existing `clock.kind="piecewise_linear_response"` with `input_metric="temperature_c"`.
- Provide a template/helper that builds knots for `m(T) = clip((T - T_base)/(T_ref - T_base), 0, m_max)` with `T_ref` = declared calibration setpoint, so `m(T_ref) = 1`. `T_base` and `m_max` are declared inputs with provenance; no default value. Upper knot declared; existing no-extrapolation rule applies.
- Document that a calendar-fitted pack stays valid only because `m(T_ref) = 1`; the calibrated-forecast path must check that the clock response evaluates to 1 (within tolerance) over the calibration setpoint, else refuse.

DLI → size target only:
- New optional light response `light_response.kind="size_target_dli"`: `D_eff = D * exp(c_DLI * z(DLI))` for existing organs and `x_max_eff = x_max * exp(c_DLI * z(DLI))` for beta organs. DLI in mol/m2/d, fixed over horizon, `z` with declared centre/scale. `c_DLI` declared with provenance (no default).
- DLI must not enter the clock, direction, events or stop rule. Validation rejects configs where a light/DLI feature appears in `families.features` for direction/event coordinates, in `stop_logit`, or as a clock input, when `size_target_dli` is used. Report the rejection reason.
- Environment features `co2_ppm`, `relative_humidity_pct`, `ec_ms_cm`, `ph` must not drive any P3 coefficient under this decision profile. Keep them as metadata. Implement as a declared `environment_profile="d9"` validation mode (default off for backward compatibility).

Manifest field (required in every new output):
- `p3_light_coupling`: `none` | `size_target_dli`.
- `p3_environment_paths`: list of every active environment/light path found by inspecting the **whole frozen config** (clock response, family features, stop_logit features, light response, calibrated-pack provenance). Replace the current clock-only `environment_used`/`light_used` logic with this full audit; keep the old flags as derived values for compatibility.
- P4 reads these fields to exclude effects already in P3.

## 3 D10 — node budget, truss events, post-termination scope

Node budget:
- Per main axis, optional `node_budget = {pmf: [{n, p}], source_kind, source_ref}`; probabilities sum to 1 within tolerance. Values are declared assumptions (literature candidate: Butturini N_phytomers_max = 10 for cv. Twiggy Red; not a default).
- Draw `N_max` once per trajectory per axis. Truncate the pmf below the observed node count at origin and renormalize; if no mass remains, return `unavailable` with reason.
- Stop the axis when node rank reaches `N_max`. When `node_budget` is present, the free `stop_probability`/`stop_logit` for that axis must be absent (validation error if both are set).
- Record `n_max_drawn` per trajectory in `trajectory_parameters.json` and `trajectories.csv`.
- Observation updates: existing finite-bank reweighting must treat `N_max` as part of the particle, so observed truss/terminal or continued leaf appearance reweights it. Do not resample.

Event kinds:
- Add `event_kind` to `events.csv` and event state: `leaf` (current behavior), `truss`, `terminal`. Default `leaf` for existing configs.
- `truss` and `terminal` carry null geometry and never become CompoundLeaf blocks or optical surfaces.
- Truss placement: optional declared rule per axis, e.g. `truss_rule = {first_truss_rank_pmf, interval_leaves}`; declared assumption with provenance. Without it, no truss events are generated and truss summaries are `unavailable`.
- `terminal` occurs at rank `N_max`; it ends main-axis leaf appearance.
- Observation input: allow confirmed observed `truss`/`terminal` events (rank, observed_at, visibility) in history and evaluation targets.

Post-termination:
- After `terminal`, set `post_termination_scope="unavailable"` with reason `sympodial_continuation_not_modeled` in summaries for that axis and plant. Leaf-count summaries after termination must not report zero further leaves as a prediction; report main-axis count plus `unavailable` for whole-plant count.

Senescence flag (from review, keep minimal):
- Keep `leaf_retention_assumption = no_loss_over_horizon`. Optional declared `max_leaf_age_dev_days`; when a predicted leaf exceeds it, add flag `retention_assumption_exceeded` to that block state. No abscission logic.

## 4 Units, missingness, compatibility

- mm, cm2, rad for model angles, development days for alpha/a_m/a_e, mol/m2/d for DLI, °C for temperature.
- CSV missing = empty cell; JSON missing = null; never zero. `unavailable` reasons follow existing patterns.
- Optical boundary unchanged: all future blocks `optical_eligible=false`, `suitable_for_ppfd=false`, `validated_growth=false`.
- No literature value is installed as a default. Templates leave new biological fields blank/null.

## 5 Tests (add under `tools/tests/`)

1. Backward compatibility: existing synthetic demo config gives identical output hashes.
2. Beta curve: zero rate at 0 and a_e; reaches x_max at a_e; monotone; rejects a_m >= a_e and x_max < x_birth; birth offset handled.
3. Clock: helper knots give m(T_ref) = 1; calibrated forecast refuses a clock with m(T_ref) != 1.
4. DLI: scales D/x_max only; config with DLI in direction/stop/clock is rejected under `environment_profile="d9"`; `p3_light_coupling` and `p3_environment_paths` correct for none / DLI / calibrated-pack cases, including a family-feature path that the old flags missed.
5. Node budget: N_max never below observed count; truncation renormalizes; empty mass gives unavailable; budget plus stop_logit rejected; stop occurs exactly at N_max.
6. Events: truss/terminal have null geometry, never produce blocks; event_kind default leaf.
7. Post-termination: whole-plant leaf count after terminal is unavailable, not zero.
8. Update: an observed truss at rank r reweights trajectories by N_max consistently; no resampling.
9. Senescence flag appears only when declared and exceeded.

Save JUnit XML and a synthetic demo run under a fresh `build/p3_d8_d10_<date>_01/`.

## 6 Deliverables

- Code and docs within the scope above.
- Updated templates with blank new fields.
- English execution report `handoff/CODEX_P3_GROWTH_DECISIONS_EXECUTION_2026-10-03.md`: changed functions, new fields with units, test results, output hashes, anything refused or left unavailable.
- One LOG line; TODO entries for open items.
- Korean summary for the user: what changed, what stays assumption-only.

## 7 Still assumption-only after this work

All rates and targets (D, k, x_max, a_m, a_e), c_DLI, T_base, N_max pmf, truss rule. They need repeated captures and a dated leaf/truss log per plant (see review section 5). Software tests do not validate biology.
