# Implementation handoff: growth/carbon pack fixes F1–F11 and decisions D11–D14

Date: 2026-10-04, Asia/Seoul. From Claude to Codex (P3 growth, P4 carbon, calibration owners).
Authorization: user decisions D11–D14 in `CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` section 8.
Detail and line references: `CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md` (sections 1–5). Claude Science did not read parts of `growth_calibration.py`, `_remaining`, `update_forecast`, P3 L262–619/L1050–1830, P4 L800–1025: re-verify line references before editing.

## Rules

- No biological coefficient values are added or changed. Templates keep new biological fields blank/null.
- Existing configs keep current outputs unless they opt into a new field; where a new field is *required* (rgr5_scope, light_basis, illuminated_faces, basis_id rules, c_DLI per curve), legacy inputs without it return structured `unavailable` with a reason, not a silent default and not an exception.
- Scientific unavailability is a structured result with a reason code, never a `StudyError` crash. Malformed input (schema errors) may still raise.
- Keep Claude's 2026-10-04 meaning guard and its tests (`build/p3_semantic_guard_20261004_01/`).
- Outputs to fresh `build/` folders; do not edit `config/`, human observations, original photos.

## Work items

| # | Item | Functions | Acceptance |
|---|---|---|---|
| F1 | New versioned equation registry: `implemented` true + function locator for live equations; NRH string = code form. Keep old file. | `build/fsp_physiology_spec_.../equation_registry*.json` | All live equations marked; strings match code. |
| F2 | Clock: explicit lower knot below T_base with multiplier 0 → development pauses; undeclared out-of-domain still refused. | `normalized_temperature_clock`, `_clock` | Sub-base inside declared knot → m=0; outside knots → refused. |
| F3 | `x_max < x_birth` and negative width target → per-trajectory unavailable (`dli_target_below_birth`, `dli_negative_width_target`); trajectory stays in denominators. | `_beta_value`, `_trajectory`, summaries | Low-DLI fixture completes; reason codes present. |
| F4 | P4 rows carry `reserve_propagation='none'`, `interval_independence='independent_single_interval'`; contiguous rows reusing identical reserve refused unless `reserve_reuse_assumption`; `status='maintenance_deficit'` when U<0. | `_budget`, `compute_carbon_sufficiency` | Multi-interval fixture triggers guard; deficit status distinct. |
| F5 | Required `rgr5_scope` (only `plant` accepted); `maintenance_activity_zero` flag; assert activity ∈ [0,1). | `compute_respiration` | Missing scope → unavailable; flag on RGR5=0. |
| F6 | `primary_inverse` required with >1 inverse. | `infer_structural_demand` | Agreeing inverses without primary refused. |
| F7 | Side-target meaning `absolute_extent_target_at_reference_DLI` (docs + `COORDINATE_MEANING`); documented asymptote `w0 + f_DLI·(target − w0)`; `narrowing_assumption` evidence required when target < min observed station. | `_decode_block`, P3 guide, `growth_calibration` | Asymptote test with f_DLI≠1; narrowing without evidence refused. |
| F8 | Docs: beta hard-refused for existing organs. | P3 guide | — |
| F9 | Meaning categories split (remaining increment; absolute extent target at reference DLI; absolute potential maximum; birth value; rate; angular offset; angular amplitude; positive wait; beta timing; dimensionless ratio). `validate_calibration_clock` must pass before any binding. Fitted `p_stop` → node_budget axis refused. L02 outputs may not bind to P3 direction coordinates. | `growth_calibration.ROLE_MEANING`, `COORDINATE_MEANING`, `_check_binding_meaning`, `apply_parameter_set` | Existing 5 guard tests pass; one new test per refusal. |
| F10 | `audit_carbon_balance` requires matching `pack_id` with the C04 run. | `audit_carbon_balance` | Mismatch refused. |
| F11 | Update output reports ESS loss from event evidence separately from geometry; manifest note on unmodelled cross-organ measurement correlation. | `update_forecast`, `_event_likelihood` | Both ESS components present. |
| D11 | DLI: `basis_id` must name sensor plane/position and differ from every P2 tissue `area_basis_id`; scope whole_plant; incident; complete local day; required `dli_applicability_interval`, outside → refused. | `_validate_d9`, `_size_response` | Tissue basis_id refused; out-of-interval refused; missing interval → unavailable. |
| D12 | `respiration_accounting='before_mito'` profile; `light_basis` on alpha/Pmax evidence with equality check; `illuminated_faces` per patch, `both` refused. | `compute_leaf_exchange`, evidence schema | Mismatched light_basis refused; `both` refused; missing → unavailable. |
| D13 | `c_DLI` per growth_curve; a single coefficient bound to both families refused. | `_size_response`, `_decode_block`, K02 table | Shared c_DLI refused; per-curve values applied to their own family only. |
| D14 opt | `reanchor_weight ω∈[0,1]` (default 1; ω = σ²_state/(σ²_state+σ²_meas) only when declared covariance + explicit opt-in), cumulative Σ|ω·δ| in update.json; posture offset δ(phase) in observation model only (δ(reference)=0, never state); `truss_observable` field (truss rule unavailable if undeclared; recommended value `visible_bud`, not a default). | `_beta_value`/reanchor, observation model, `_event_likelihood`, node/truss rules | Default ω=1 reproduces current; posture term changes likelihood only, never state; undeclared truss_observable → truss unavailable. |

## Source checks (report, do not change coefficients)

1. Butturini alpha/Pmax fitted to net or gross exchange (`dwarf_photosynthesis.rgg`, parameter CSV, paper eq 5 p.6).
2. Source maintenance `m` unit: g CH2O or g CO2 per g DM per day.
3. NRH calibration conditions as applicability domain (≈23 °C, ≈798 µbar CO2, 50:50 R:B, 0–2000 incident PPFD; n=3, rank-3 leaf) — re-verify locators.
Record in a new evidence update file.

## Tests and evidence

- New tests per row above; rerun calibration, P3 (incl. `test_p3_growth_decisions`), P4 suites. Save JUnit XML and a synthetic demo to fresh `build/growth_pack_fixes_20261004_01/`.
- Note: in Claude's Linux check, `test_legacy_golden_numerical_payload` and `test_prepare_light_delegates_existing_bridge` failed before and after its change (environment). Confirm they pass in the Windows project environment.

## Deliverables

- `handoff/CODEX_GROWTH_PACK_FIXES_EXECUTION_2026-10-04.md`: per-item status, changed functions, new fields/units/reason codes, tests, hashes, deferred items.
- One LOG line; TODO for anything deferred.
- Korean summary for the user.

## Addendum A — Decision 2 final (2026-10-04 17:41 KST): replaces row D12 and refines F5 and source checks 1–2

Authorization: decisions D15–D18 (decisions file section 9). Where this addendum and the D12 row above differ, this addendum wins.

| # | Item | Functions | Acceptance |
|---|---|---|---|
| A1 | Respiration ownership: keep `before_mito` (no change; `_ownership` L410–411 already forces `maintenance='downstream'`). Add refusal of `net_leaf` unless pack supplies Rd_day/Rd_night with their own evidence and a source other than the dwarf model; reason `net_leaf_requires_rd_bearing_source`. | `_ownership`, pack validation | before_mito with any non-downstream row → MissingEvidence (existing); net_leaf without Rd records → refused with that reason. |
| A2 | Light basis: `pack['light_basis']='absorbed'` for dwarf-sourced packs. Required `measured_light_basis` ∈ {incident, absorbed} on each alpha, P_sat, theta record. At the `_parameter` calls in `compute_leaf_exchange` (≈L470–472): if `measured_light_basis != pack['light_basis']`, emit issue `alpha_calibration_basis_conflict` and continue. Light-sample basis check (≈L459–460) unchanged; no absorptance conversion. | `compute_leaf_exchange`, evidence schema | Mismatch → issue present in every supply row; computation continues. |
| A3 | Two-face: required per-patch `illuminated_faces` ∈ {adaxial_only, both}; `both` → `_missing('two_sided_exchange_unavailable', …)`. | `compute_leaf_exchange` (≈L484) | `both` → unavailable. |
| A4 | Maintenance units: no code change (`gCH2O/g_structural_DM/day` ≈L541, factor 12.011/30.026 ≈L582 correct per Butturini eq 7 p.7). Mark the registry's CO2-vs-CH2O limitation resolved in the F1 registry update. Dwarf-sourced packs set Tref = 25 °C (Tref stays a free parameter). | registry (F1), pack templates/docs | Registry limitation closed with locator. |
| A5 | RGR5 (refines F5): required `rgr5_scope`, only `plant`. In `compute_respiration` (≈L570–579) the rgr5 payload must be plant-level and identical for every included organ in the interval; differing → `_missing('rgr5_scope_inconsistent', …)`. No basal floor; `maintenance_activity_zero` flag when activity = 0. | `compute_respiration` | Unequal payloads → unavailable; flag present. |
| A6 | SLA unit guard: accept only `m2/g_structural_blade_DM`; reject `m2/mg` (paper Table 2 unit; 1000× trap). | `infer_structural_demand` | m2/mg refused. |
| A7 | Disclosure fields on every sufficiency row (reporting only): `respiration_accounting`, `light_basis`, `rgr5_scope` (as declared); `source_buffer_feedback='not_modelled'`; `nonfoliar_assimilation='not_modelled'`; `maintenance_temperature_integration='sub_daily'`. | `compute_carbon_sufficiency` output | All non-null on every row. |

Source checks 1–2 in the main handoff are answered (net/gross: source is gross/before-mito; maintenance unit: CH2O). Source check 3 (NRH calibration domain) remains to be recorded.

Still out of scope: buffer feedback (Butturini eq 6), nonfoliar assimilation, reserve propagation (C05), two-sided exchange model, posture term beyond the opt-in D14 field.

## Superseded

Superseded on 2026-10-04 by `CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md` (consolidates main text and addendum A). Use v2.
