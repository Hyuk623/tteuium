# Codex handoff: technical review fixes (D11–D21), checked against current code

Date: 2026-10-04 18:22, Asia/Seoul. From Claude to Codex (P2 light, P3 growth, P4 carbon, calibration owners).
Source: agreed Claude Science technical review of `CODEX_FOUR_PROJECT_GROWTH_SCIENCE_SUMMARY_2026-10-04.md`. Decisions D19–D21: `CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` section 10.

## 0 How this relates to pending work

- `CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md` and the per-project V2 chat prompts (`CODEX_P2/P3/P4_GROWTH_PACK_V2_CHAT_PROMPT_2026-10-04.md`) are still pending. This file **adds to and, where it differs, overrides** them. Run V2 and this file together in each project chat; do not implement the same item twice.
- `CODEX_REFERENCE_DLI_CHANNEL_HANDOFF_2026-10-04.md` (already folded into the P2 V2 prompt) is extended by section 5 here.
- Review-only items are excluded. Unresolved items stay unresolved (section 8).
- "Status now" below is Claude's grep of the current source at 18:22 KST; line numbers drift — re-verify before editing.

## 1 D19 — DLI unit spelling (blocker)

| Location (current) | Status now | Change |
|---|---|---|
| `tools/probabilistic_compound_growth.py` L55 `ENV_UNITS['dli_mol_m2_day'] = 'mol/m2/d'` | still `mol/m2/d` | use `DLI_UNIT` |
| same file L205 applicability unit check | still `mol/m2/d` | `DLI_UNIT` |
| same file L237 `_validate_d9` light unit check | still `mol/m2/d` | `DLI_UNIT` |
| same file L1909, L1913 template `unit='mol/m2/d'` | still `mol/m2/d` | `DLI_UNIT` |
| `tools/fsp_carbon_diagnostic.py` L319 `inspect_p3_coupling` | still `mol/m2/d` | `DLI_UNIT` |
| `tools/light_growth_bridge.py` L884 | already `mol/m2/day` | import `DLI_UNIT` |
| `tools/leaf_light/common.py` | no `DLI_UNIT` yet | add `DLI_UNIT = 'mol/m2/day'`; no second spelling anywhere in code |

- Legacy frozen configs carrying `mol/m2/d` → refused with `legacy_dli_unit_spelling` and a list of missing/different fields. No auto-correction; regenerate configs.
- `reference_position.json::applicability_interval_mol_m2_day` requires `applicability_source_ref` pointing to the P3 parameter-pack coefficient domain; a sensor-setup author may not invent it.

Acceptance: (1) `mol/m2/day` passes, `mol/m2/d` refused by name; (2) synthetic P2 `reference_dli.json` → P3 `_validate_d9` round trip passes; (3) missing `applicability_source_ref` refused.

## 2 D20 — illuminated faces (blocker)

- P2: required per-patch `illuminated_faces ∈ {adaxial_only, abaxial_only, both}`. Physics unchanged; exposes information only.
- P4 `compute_leaf_exchange` patch validation loop (≈L438–447): undeclared → `_missing('illuminated_faces_undeclared', …)`; `both` → `_missing('two_sided_exchange_unavailable', …)`. Keep the fixture sum (≈L484, `math.fsum`): same-face fixture summation is correct.
- Status now: no `illuminated_faces` handling in P4.

Acceptance: synthetic two-fixture opposite-face input → `two_sided_exchange_unavailable`; two fixtures on the same face → normal sum.

## 3 Metadata/docs only (no algorithm change)

| Item | Action |
|---|---|
| Maintenance unit conflict | Close the registry `maintenance` limitation as resolved. Evidence: `dwarf_plant_level.rgg::calcSourceStrength()` subtracts `maintenance_demand_mg` from `gross_assimmilates_mg` (= MOLAR_MASS_CO2/1000 × µmol × CONVERSION_FACTOR_CO2_TO_CHO, i.e. mg CH2O), so MAINT is g CH2O g⁻¹ DM d⁻¹; the CSV "CO2" label is a label error. No rescaling. |
| Q10, Tref | Record Q10 = 2, Tref = 25 °C (hard-coded in the same function) for dwarf-sourced packs. |
| SLA `m2/mg` | No new guard: `_parameter` strict unit match (≈L188–189) already refuses it. Add a named reason code and a comment only. |
| Registry status label | Replace `P3_in_progress_pending_final_refresh` by a new registry version recording the final P3 report hash; keep the old snapshot. |
| NRH fit convention | Keep unresolved. Fixed interpretation note in outputs/docs: "If a 3-parameter origin-passing fit was applied to net data, both α and P_sat are underestimated → supply under-predicted and leaf respiration double-counted. The bias is conservative: ratio ≥ 1 is credible; ratio < 1 is not evidence of carbon shortage." |

## 4 Code changes

### P4 (`tools/fsp_carbon_diagnostic.py`)

| ID | Location | Change | Status now |
|---|---|---|---|
| P4-a | `_parameter` calls ≈L470–472 | α/P_sat/θ records require `measured_light_basis ∈ {incident, absorbed}`; mismatch with `pack['light_basis']` → issue `alpha_calibration_basis_conflict`, continue | not present |
| P4-b | `_ownership` ≈L400 | `net_leaf` only with Rd_day/Rd_night evidence and a non-dwarf source; else `net_leaf_requires_rd_bearing_source` | not present |
| P4-c | sufficiency rows | add disclosure fields: `respiration_accounting`, `light_basis`, `source_buffer_feedback='not_modelled'`, `nonfoliar_assimilation='not_modelled'`, `maintenance_temperature_integration='sub_daily'`, `diagnostic_interpretation='cross_cultivar_consistency_check'` | `rgr5_scope`, `maintenance_activity_zero` already present (≈L560–606); others missing |
| P4-d | reserve rows | `reserve_gC` requires `source_ref`; output `reserve_provenance_chain_id` so reuse is detectable from outputs even when calls are split | not present |
| P4-e | RGR5 evidence record | note `rgr5_mass_basis_deviation_from_source`: source RGR5 uses total dry mass incl. roots and buffer (`plant_level.rgg`: ln(dry_biomass_plant_with_roots_mg) differences; `dry_biomass_structural_and_min_pool_mg = with_roots − buffer`), P4 requires `structural_dm_excluding_reserve`; f's meaning differs when borrowed | not present |
| P4-f | `total_dm_substitute` basis note | bias placeholder ≈10 % from source static-branch comment "90% of dry weight is structural"; source-supported assumption, not a target-cultivar value | not present |
| — | `pack['light_basis']='absorbed'` for dwarf packs; `before_mito` only (D15/D16) | as V2 A1/A2 | pending V2 |

### P3 (`tools/probabilistic_compound_growth.py`, `tools/growth_calibration.py`)

| ID | Change | Status now |
|---|---|---|
| P3-a | Quantile coverage split into `existence_mass` (not appeared / apex terminated = biological prediction), `computable_mass` (parameter / low-DLI failure = model failure), `available_mass` (intersection) | not present |
| P3-b | Event ESS stage named `hard_admissibility` (`_event_likelihood` ≈L236–259 is a boolean indicator); report `n_particles_rejected_by_events`; document that final weights are multiplicative and order-invariant | not present |
| P3-c | Separate meanings `absolute_extent_target_at_reference_DLI` (exponential width) and `absolute_potential_maximum` (beta x_max); refuse cross-binding | **already implemented** (`growth_calibration.COORDINATE_MEANING` L60/L68, `_validate_d9` roles ≈L212); add a regression test for cross-binding only if missing |
| P3-d | Verify the sub-base zero knot passes the knot-equality check in `_validate_d9`. `normalized_temperature_clock` now has `lower_knot_c`; if the generated knots and the checker disagree, extend the helper or relax the check | verify |
| P3-e | Legacy migration: refuse with `legacy_light_response_underspecified` and list missing fields; never infer `basis_id`, interval or `time_basis` | not present |
| P3-f | Reverse basis separation: P3 refuses a `basis_id` that appears in a supplied P2 tissue manifest (pairs with P2-h) | check |

## 5 P2 reference-DLI channel additions (extend the reference-DLI handoff)

| ID | Change |
|---|---|
| P2-a | Required `logger_sample_semantics ∈ {instantaneous, interval_mean}`. `interval_mean` → step rule; `instantaneous` → trapezoid, but forced step at declared schedule transitions. Add a test with a light transition **inside** a sampling interval (the 200 µmol × 16 h = 11.52 test passes under both rules and does not discriminate). |
| P2-b | Sensor cosine response: required `cosine_corrected ∈ {true, false, unknown}` and `levelled`; if not corrected, flag `cosine_response_uncorrected` on every row. |
| P2-c | `ambient_light` required on outputs of all routes; without one lights-off daytime measurement, value `asserted_not_measured`. |
| P2-d | Position tolerance derived from local gradient in `spot_survey.csv`: allowed DLI error → distance. |
| P2-e | `plant_association{plant_instance_ids, association_evidence, uniformity_basis}`; when several plants share one reference, show via survey that all positions are within tolerance. |
| P2-f | If spread of `days_used` exceeds tolerance → `dli_not_constant_over_horizon` (lamp decay conflicts with `fixed_over_horizon=true`). |
| P2-g | Explicit `dst_policy`, or refuse timezones with transitions (Asia/Seoul low risk). |
| P2-h | `basis_id` separation is two-way (see P3-f). |
| — | Emit per-patch `illuminated_faces` (D20). |

Status now: `tools/reference_dli.py` does not exist; channel pending via the P2 V2 prompt.

## 6 P1 minimum evidence before issuing any `area_basis_id`

All four required: scale (ChArUco square-size calibration record + residual), pose (per-frame reprojection residual + declared threshold), time (timezone-aware + `capture_phase`), area (declared one-sided basis + coverage fraction + occlusion statement). Identity associations bound to the partition hash and a reviewer.

Never supply to P2/P3: per-photo dimensionless ratios (current 433 rows), projected mask area, generated RGB views, unreviewed candidate regions, `estimated_total_area` without evidence.

## 7 D21 — Day-1 recording protocol (start now; plants exist)

Do not wait for V2 schema fields. Record from today so G06/G07 fields can be back-filled later; only unrecorded information is unrecoverable.

| Record | Format | Later maps to |
|---|---|---|
| Capture phase label | `early_photoperiod` / `late_photoperiod` (2 h after lights-on / 2 h before lights-off) | G06 `capture_phase` → posture offset δ(phase) |
| Truss observation definition | fixed `visible_bud`; do not record anthesis or fruit set as truss appearance | G07 `truss_observable` |
| Day-0 node count | integer per plant + source of the counting rule | `observed_node_count` + `node_count_source_ref` (code ≈L215–220 requires a reviewed value and source) |
| Seedling history | sowing and transplant dates if known, else blank | absolute organ age stays unknown |

Implications: existing organs have unknown absolute age (this is why D8 keeps them exponential; do not estimate it). The N_max PMF is truncated below the Day-0 node count (D10), so an accurate Day-0 count is a prerequisite for all determinacy predictions.

Codex task: provide a CSV template for this protocol (`measurements/day1_protocol.template.csv`: plant_id, capture_session_id, captured_at, capture_phase, node_count, node_count_source_ref, truss_observable, truss_visible_bud_count, sowing_date, transplant_date, notes) and ensure G06/G07 loaders can back-fill from it. Do not edit existing human measurement files.

## 8 Unresolved — do not implement

NRH fit preprocessing (net → gross correction), buffer feedback (source eq 6), nonfoliar assimilation (source f_org, eq 5), reserve propagation, two-sided exchange model, sympodial continuation, light → orientation response, FvCB. Expose each as named `not_modelled` / `unavailable`; no implementation.

## 9 Tests, evidence, deliverables

- One test per acceptance line above; rerun P2, P3 (incl. `test_p3_growth_decisions`), P4 and calibration suites; JUnit XML and synthetic demos in fresh `build/technical_review_fixes_20261004_01/`.
- Confirm in the Windows environment that `test_legacy_golden_numerical_payload` and `test_prepare_light_delegates_existing_bridge` pass (they failed in Claude's Linux check before and after its change).
- Report: `handoff/CODEX_TECHNICAL_REVIEW_FIXES_EXECUTION_2026-10-04.md` with per-item status (done / already present / deferred), changed functions, new fields and reason codes, test results, hashes. One LOG line; TODO for deferred items; Korean summary for the user.
