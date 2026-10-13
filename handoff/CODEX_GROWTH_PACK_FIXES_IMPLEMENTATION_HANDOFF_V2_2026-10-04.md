# Implementation handoff v2: growth/carbon pack fixes (D11–D18, F1–F11, A1–A7)

Date: 2026-10-04, Asia/Seoul. From Claude to Codex (P3 growth, P4 carbon, calibration owners).
This v2 consolidates and **supersedes** `CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_2026-10-04.md` (main text + addendum A). Use only this file.

Authorization: user decisions D11–D18 in `CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` sections 8–9.
Background and line references: `CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md`.
Claude Science did not read: `tools/growth_calibration.py`, `_remaining`, `update_forecast`, P3 L262–619 and L1050–1830, P4 L800–1025. Line numbers below are approximate (≈); re-verify before editing.

## 0 Decisions in force

| ID | Decision |
|---|---|
| D11 | P3 DLI = incident, whole-plant, one declared reference position, complete local day. `light_response.basis_id` names sensor plane/position and must not equal any P2 tissue `area_basis_id`. Required DLI applicability interval; outside → refused. P2 absorbed tissue flux is not a P3 input. |
| D12/D15 | P4 `respiration_accounting='before_mito'`; P4 `light_basis='absorbed'` (D15 replaces the earlier incident choice); `measured_light_basis` on alpha/P_sat/theta records, mismatch = issue, computation continues; `illuminated_faces='adaxial_only'` only. P3 (incident) and P4 (absorbed) light inputs stay disjoint. |
| D13 | `c_DLI` declared per growth curve (exponential vs determinate_beta); one coefficient bound to both refused. |
| D14 | F1–F11 approved. Opt-in fields approved with defaults preserving current behaviour: G03 `reanchor_weight`, G06 posture offset (observation model only), G07 `truss_observable`. |
| D16 | `before_mito` confirmed by source (Butturini eq 5 p.6 no Rd, P_T(0)=0; eq 8 p.7 A_net = max(0, A_gross − R_m,plant); Table 2 p.6; `Thornley.calc()` 4 args, no Rd). `net_leaf` only with Rd_day/Rd_night evidence from a non-dwarf source. |
| D17 | Maintenance unit confirmed g CH2O g⁻¹ DM_str d⁻¹ (Butturini eq 7 p.7); code and 12.011/30.026 correct; no 1.466× error. Dwarf-sourced packs: Tref = 25 °C. |
| D18 | `rgr5_scope='plant'` only; identical RGR5 payload across included organs per interval. No basal maintenance floor. Two-face illumination unavailable. |

## 1 Rules

- No biological coefficient values are added or changed. Templates keep new biological fields blank/null (except declared structural constants already decided: Tref = 25 °C documented for dwarf-sourced packs, not installed as a global default).
- Legacy inputs missing a newly required field → structured `unavailable` with reason, not a silent default, not an exception.
- Scientific unavailability = structured result with reason code; only malformed input may raise.
- Keep Claude's 2026-10-04 meaning guard and tests (`build/p3_semantic_guard_20261004_01/`).
- Outputs to fresh `build/` folders; do not edit `config/`, human observations, original photos.

## 2 Work items

### P3 growth (`tools/probabilistic_compound_growth.py`, guide)

| # | Item | Functions | Acceptance |
|---|---|---|---|
| F2 | Clock: explicit lower knot below T_base with multiplier 0 → development pauses; undeclared out-of-domain still refused. | `normalized_temperature_clock`, `_clock` (≈L742–756) | Sub-base inside declared knot → m=0; outside all knots → refused. |
| F3 | `x_max < x_birth` (≈L79–80) and negative width target (≈L1046–1047) → per-trajectory unavailable (`dli_target_below_birth`, `dli_negative_width_target`); trajectory stays in denominators. | `_beta_value`, `_trajectory`, summaries | Low-DLI fixture completes; reason codes present. |
| F7 | Side-target meaning `absolute_extent_target_at_reference_DLI`; document realized asymptote `w0 + f_DLI·(target − w0)`; `narrowing_assumption` evidence required when target < min observed station. | `_decode_block` (≈L902–944), guide | Asymptote test with f_DLI ≠ 1; narrowing without evidence refused. |
| F8 | Docs: beta hard-refused for existing organs (≈L712–718). | guide | — |
| F11 | Update output: ESS loss from event evidence reported separately from geometry; manifest note that cross-organ measurement correlation (shared pose/scale) is not modelled. | `update_forecast`, `_event_likelihood` | Both ESS components present. |
| D11 | DLI basis rules + required `dli_applicability_interval`. | `_validate_d9`, `_size_response` | Tissue basis_id refused; out-of-interval refused; missing interval → unavailable. |
| D13 | `c_DLI` per growth curve; shared coefficient refused. | `_size_response` (≈L194–203), `_decode_block` (≈L941) | Shared c_DLI refused; per-curve values apply to own family only. |
| D14a | `reanchor_weight ω ∈ [0,1]`, default 1 (current). ω = σ²_state/(σ²_state+σ²_meas) only with declared covariance and explicit opt-in. Cumulative Σ|ω·δ| in update.json. | beta/exponential reanchor, `update_forecast` | Default reproduces current outputs. |
| D14b | Posture offset δ(phase) in observation model only (δ(reference)=0); never enters state. | observation likelihood | Changes likelihood only; state unchanged. |
| D14c | `truss_observable` field; truss rule unavailable if undeclared (recommended `visible_bud`, not a default). | truss rule, `_event_likelihood` | Undeclared → truss unavailable. |

### Calibration (`tools/growth_calibration.py`)

| # | Item | Functions | Acceptance |
|---|---|---|---|
| F9 | Split meaning categories: remaining increment; absolute extent target at reference DLI; absolute potential maximum (`*_x_max_*`); birth value; rate; angular offset; angular amplitude; positive wait; beta timing; dimensionless ratio. `validate_calibration_clock` must pass before any binding. Fitted `p_stop` → node_budget axis refused (structural mismatch). L02 light-direction outputs may not bind to P3 direction coordinates. | `ROLE_MEANING`, `COORDINATE_MEANING`, `_check_binding_meaning`, `apply_parameter_set` | Existing 5 guard tests pass; one new test per refusal. |

### P4 carbon (`tools/fsp_carbon_diagnostic.py`, guide)

| # | Item | Functions | Acceptance |
|---|---|---|---|
| A1 | Keep `before_mito` (`_ownership` ≈L410–411 forces `maintenance='downstream'`). Refuse `net_leaf` without Rd_day/Rd_night evidence from a non-dwarf source: `net_leaf_requires_rd_bearing_source`. | `_ownership`, pack validation | before_mito + non-downstream row → MissingEvidence (existing); net_leaf without Rd → refused. |
| A2 | `pack['light_basis']='absorbed'` for dwarf-sourced packs. Required `measured_light_basis` ∈ {incident, absorbed} on alpha, P_sat, theta records. At the `_parameter` calls (≈L470–472): mismatch → issue `alpha_calibration_basis_conflict`, continue. Light-sample basis check (≈L459–460) unchanged; no absorptance conversion. | `compute_leaf_exchange`, evidence schema | Mismatch → issue in every supply row; computation continues. |
| A3 | Required per-patch `illuminated_faces` ∈ {adaxial_only, both}; `both` → `_missing('two_sided_exchange_unavailable', …)`. | `compute_leaf_exchange` (≈L484) | `both` → unavailable. |
| A5/F5 | Required `rgr5_scope`, only `plant`. RGR5 payload (≈L570–579) identical for all included organs in the interval; differing → `_missing('rgr5_scope_inconsistent', …)`. No basal floor; `maintenance_activity_zero` flag when activity = 0; assert activity ∈ [0,1). | `compute_respiration` (≈L534–585) | Missing scope → unavailable; unequal payloads → unavailable; flag present. |
| A6 | SLA unit guard: accept only `m2/g_structural_blade_DM`; reject `m2/mg` (paper Table 2 unit, 1000× trap). | `infer_structural_demand` | m2/mg refused. |
| F6 | `primary_inverse` required with more than one inverse. | `infer_structural_demand` (≈L700–702) | Agreeing inverses without primary refused. |
| F4 | Rows carry `reserve_propagation='none'`, `interval_independence='independent_single_interval'`; contiguous rows reusing identical reserve refused unless `reserve_reuse_assumption`; `status='maintenance_deficit'` when U<0. | `_budget` (≈L740–754), `compute_carbon_sufficiency` | Multi-interval fixture triggers guard; deficit status distinct. |
| A7 | Disclosure fields on every sufficiency row: `respiration_accounting`, `light_basis`, `rgr5_scope` (as declared); `source_buffer_feedback='not_modelled'` (Butturini eq 6 down-regulation absent → S over-predicts when sink-limited); `nonfoliar_assimilation='not_modelled'` (source f_org in eq 5); `maintenance_temperature_integration='sub_daily'` (source uses daily mean; Q10 Jensen term ≈ +0.4 % at 22/19 °C, Q10 = 2). | `compute_carbon_sufficiency` output | All non-null on every row. |
| F10 | `audit_carbon_balance` requires matching `pack_id` with the C04 run. | `audit_carbon_balance` | Mismatch refused. |
| A4 | No code change for maintenance units (≈L541, ≈L582). Document Tref = 25 °C for dwarf-sourced packs. | guide, pack templates | — |

### Evidence registry

| # | Item | Acceptance |
|---|---|---|
| F1 | New versioned `equation_registry` (keep old): `implemented: true` + function locator for live equations (nrh, maintenance, activity, beta, inverse_area, inverse_dimension, available_budget, sufficiency, balance); NRH string = code form `sqrt((αI−Pmax)² + 4(1−θ)αI·Pmax)`; close CO2-vs-CH2O limitation as resolved (Butturini eq 7 p.7); record before_mito evidence (eq 5, eq 8, Table 2, `Thornley.calc()`). | Live equations marked; strings match code; limitation closed with locator. |
| S3 | Record NRH calibration domain as applicability: ≈23 °C, ≈798 µbar CO2, 50:50 R:B, 0–2000 incident PPFD, n=3, rank-3 mature leaf. Re-verify locators. Empirical NRH not valid at ambient ≈400 ppm without new evidence. | Domain stored with locators. |

## 3 Tests and evidence

- New tests per row; rerun calibration, P3 (incl. `test_p3_growth_decisions`), P4 suites. Save JUnit XML and a synthetic demo to fresh `build/growth_pack_fixes_20261004_01/`.
- Software checks only — none test biological accuracy.
- In Claude's Linux check, `test_legacy_golden_numerical_payload` and `test_prepare_light_delegates_existing_bridge` failed before and after its change (environment). Confirm they pass in the Windows project environment.

## 4 Still out of scope

Buffer feedback (Butturini eq 6), nonfoliar assimilation, reserve propagation between intervals (C05), two-sided exchange model, light-direction → leaf-orientation response, sympodial continuation, senescence/abscission, root demand (whole-plant P4 scope needs measured root mass).

## 5 Deliverables

- `handoff/CODEX_GROWTH_PACK_FIXES_EXECUTION_2026-10-04.md`: per-item status, changed functions, new fields/units/reason codes, tests, hashes, deferred items.
- One LOG line; TODO for anything deferred.
- Korean summary for the user.
