# Four-project integration decisions for Codex review

Date: 2026-10-03, Asia/Seoul. Author: Claude (coordination chat). Recipient: Codex, for review.
Scope: chats `3d구현` (P1), `광시뮬레이터` (P2), `생장방향` (P3), `토마토 FSP` (P4).
Base document: `handoff/CLAUDE_FOUR_PROJECT_ENV_IO_HANDOFF_2026-10-03.md`.

This records user decisions and requests. It authorizes review only: no implementation, model runs, fitting or edits to files owned by active chats.

## 1 User decisions

| ID | Decision | Consequence |
|---|---|---|
| D1 | P3 (`생장방향`) owns the realized growth increment. P3 already predicts both direction and size (length, width, area). | Only P3 changes organ geometry and size over time. |
| D2 | P4 (`토마토 FSP`) is an auxiliary index, not a second growth engine. | P4 never adds an increment, overwrites P3 state, or multiplies P3 rates by default. |
| D3 | Cross-project linking is deferred until all four projects finish their current goals. | Active chats continue independently. No integration code now. |
| D4 | The integration target is an end-to-end pass on synthetic data. Variable conversion between projects must be lossless and error-free. | Biological validation is out of scope for the first integration. Conversion correctness is the acceptance criterion. |

Planned sequence: finish all four goals → final integration document built on the base handoff and this file → Claude writes a Claude Code implementation prompt for D4.

## 2 Proposed P4 auxiliary-index role (needs review)

Risk: if P3 coefficients already include light effects (fixed-light coupling or calibrated light features), any P4 multiplier on P3 rates counts light twice.

Proposal: P4 is diagnostic only.
- Input: P3 predicted increments per plant and interval (area, length, organ count), plus P2 absorbed light and environment for the same interval.
- Output: a carbon-sufficiency ratio, e.g. `carbon_supply_gC / carbon_demand_gC` for the P3-predicted increment, with an explicit status flag (`sufficient`, `deficit`, `unavailable`) and the assumptions used.
- Effect on P3: none by default. Any future feedback (e.g. reweighting P3 trajectories by plausibility) needs a separate explicit decision and must exclude light terms P3 already uses.
- Per-plant carbon accounting stays separate even when plants share a canopy.

Review question: does this conflict with the P4 physiology prompt (`CLAUDE_FSP_PHYSIOLOGY_ACCURACY_PROMPT_2026-10-03.md`) or the FSP specification work, which assume physiology may pass a mass/area constraint to P3? If so, list the affected sections.

## 3 Conversion requirements for D4 (to be specified in the final document)

Every hand-off between projects goes through an explicit adapter with round-trip tests on synthetic fixtures. Minimum checks:

| Boundary | Conversion that must be exact or tolerance-declared |
|---|---|
| IDs | `plant_instance_id` ↔ `source_plant_id`/`plant_id`; `compound_id` ↔ `compound_leaf_id`; leaflet/organ IDs; session and timestamp. Reviewed mapping table, no implicit rename. |
| Area | mm² → m² (1e-6) → cm² (1e4); supported vs estimated-total vs projected vs dimensionless area never substituted. |
| Light | PPF (umol/s), PPFD (umol/m²/s), absorbed flux (umol/s), daily dose kept distinct; one-sided vs two-sided area basis stated. |
| Angles | rad (P3 model and calibration) ↔ deg (geometry and report files); signed elevation preserved. |
| Frames | board ↔ grow ↔ parent-local; points transformed, vectors rotated without translation; inverse round-trip. |
| Time | timezone-aware timestamps; calendar day vs development day not interchanged without an explicit clock conversion. |
| Missing values | `unavailable` (P2 CSV), empty cell (P3/P4 CSV), `null` (JSON) normalized with status/reason preserved; never converted to zero. |
| Provenance | schema/model versions and hashes carried through; stale geometry or associations invalidate joins. |

Acceptance for D4: synthetic fixture passes P1 → P2 → P3 (→ P4 index) and back-conversions reproduce inputs within declared tolerances; zero silent unit, ID, sign or missingness changes.

## 4 Separate request already issued

The user will send `handoff/CLAUDE_SCIENCE_FSP_EQUATION_PROMPT_2026-10-03.md` (Korean) to Claude Science for an equation and validation design discussion. Its section 7 still asks who owns the growth increment; D1 now answers that. Treat that discussion's output as input to P4, not as an adopted contract.

## 5 Requested Codex review

1. Confirm or object to D1/D2 against current P3 and P4 code and specifications, citing files.
2. Check whether P3 currently has any light/environment coupling that would double-count if P4 fed back into P3.
3. List every current cross-project field that the D4 adapter must convert, with source file, field, unit and missing-value form. Mark fields whose producer is still in progress (e.g. `light-growth-1`).
4. Identify anything in section 3 that is wrong, missing or already implemented.
5. Do not edit files owned by active chats. Report findings in a new Codex handoff file.

## 6 Follow-up user decisions (2026-10-03 22:24 KST)

Answers to the three questions in `CODEX_FOUR_PROJECT_INTEGRATION_DECISIONS_REVIEW_2026-10-03.md` section 6. These append to D1-D4; nothing above is rewritten.

| ID | Decision | Consequence |
|---|---|---|
| D5 | The offline calibration route (`tools/growth_calibration.py::apply_parameter_set`) is **included** in the integration, applied **before P3 runs**. | A frozen, hashed fitted parameter pack may be selected explicitly to build the P3 configuration. It is never called implicitly by an adapter and never at runtime. D2 (diagnostic-only) applies to the runtime P4 carbon index. Fitted light/environment effects inside the pack must be recorded so the P4 index can show they are already in P3. |
| D6 | Numeric P4 carbon-index output is **not mandatory** in the first synthetic pass. | Acceptance scope: P1 -> P2 -> P3 (with optional frozen calibration pack) must pass numerically. P4 may report `unavailable` with reasons. Do not describe the first pass as a full numeric four-project pass. |
| D7 | D4 is corrected: reversible representation changes (units, frames, ID maps, timestamps, missing-value forms) must round-trip exactly or within declared per-field tolerances. Reductions and model computations (aggregation, light transport, photosynthesis, forecasting, summaries) are **checked for correctness only**, not inverted. | Preserve source samples, shapes, weights and provenance; test declared computation invariants (e.g. flux sums before area division, no double absorptance, aggregate consistency) instead of requiring inverse reconstruction. |

## 7 P3 growth-equation decisions (2026-10-03 22:48 KST)

Answers to the three open decisions in `CLAUDE_GROWTH_EQUATION_REVIEW_FOR_CODEX_2026-10-03.md` section 6. Implementation handoff: `CODEX_P3_GROWTH_DECISIONS_IMPLEMENTATION_HANDOFF_2026-10-03.md`.

| ID | Decision |
|---|---|
| D8 | Size decoder: adopt option (c) only. Keep the current exponential `x0 + D(1-exp(-k*a))` for existing (age-unknown) organs; add `determinate_beta` for organs born inside the horizon. Options (a) `log x_inf` reparameterization and (b) rank law with scalar vigour are **not adopted**; D remains the sampled remaining-increment coordinate and existing covariance structures stay. |
| D9 | Environment entry: temperature enters the development clock only, as a piecewise-linear response normalized to 1 at the calibration setpoint. DLI enters the size target only (adapted to D8: D for existing organs, x_max for newborn beta organs), fixed over the horizon. CO2, VPD/RH, EC, pH do not enter P3. Manifest carries `p3_light_coupling` for P4 exclusion. |
| D10 | Determinacy: per-trajectory main-stem node budget `N_max` drawn from a declared pmf (assumption, not fitted), truncated below the observed node count and reweighted by observations; `event_kind ∈ {leaf, truss, terminal}` with null geometry for truss/terminal; after terminal, `post_termination_scope = unavailable`. |

## 8 Growth Science review user answers on 2026-10-04

Recorded by Codex from the user's explicit answers to section 4 of `CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md`: question 1 as recommended, question 2 undecided, question 3 as recommended. These are not answers to that review's three source checks.

| Item | Recorded decision | Scope |
|---|---|---|
| Growth Science question 1 | Adopt incident DLI at one declared reference position/plane over a complete local day, with whole-plant P3 model scope. The reference basis_id is distinct from P2 tissue area_basis_id values. Require a declared applicability interval and refuse out-of-interval use. | Clarifies D9; no reference location, interval bounds or numerical coefficient is invented. |
| Growth Science question 2 | Undecided. | The proposed before_mito / incident / adaxial_only P4 policy is not adopted. Preserve unresolved numerical-use gates; source checks may proceed. |
| Growth Science question 3 | Adopt c_DLI declarations per growth_curve; refuse one shared coefficient binding across exponential and beta families. Apply the specified low-DLI per-trajectory unavailable handling and applicability interval. | Distinguishes remaining increments from absolute beta maxima; no new fitted values. |

Optional G03 reanchor_weight, G06 transient-posture observation term and G07 truss_observable selection remain unadopted. D1-D10, diagnostic-only P4 and deferred integration remain effective. No photosynthesis/maintenance coefficient is accepted by these answers.

The current request is preparation of four chat prompts, not execution or dispatch in this coordination chat. Recipient work is scoped in `CODEX_GROWTH_SCIENCE_CHAT_PROMPTS_INDEX_2026-10-04.md` and its four linked prompts. P3 owns the calibration edits; P4 owns diagnostic runtime and the new versioned equation registry. Historical source handoffs are preserved.

## 8 Growth/carbon pack decisions (2026-10-04 17:37 KST)

Answers to section 4 of `CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md`. User accepted all recommendations.

| ID | Decision |
|---|---|
| D11 | P3 DLI input: incident light, whole-plant, one declared reference position, complete local day. `light_response.basis_id` names the sensor plane/position and must not equal any P2 tissue `area_basis_id`. A declared DLI applicability interval is required; DLI outside it is refused (no extrapolation). P2 absorbed tissue flux is not a P3 input. |
| D12 | P4 semantics: `respiration_accounting='before_mito'` (all maintenance charged downstream), `light_basis='incident'`, required `light_basis` field on alpha/Pmax evidence with an equality check against the pack, `illuminated_faces='adaxial_only'` (`both` refused until a two-sided model exists). Numeric use still waits on source checks (net vs gross fit; CH2O vs CO2 maintenance units). |
| D13 | `c_DLI` is declared per growth curve (exponential vs determinate_beta); one coefficient bound to both families is refused. Low-DLI failures become structured unavailable results (see F3), not exceptions. |
| D14 | Software-safety fixes F1–F11 are approved for Codex implementation. Optional items (G03 `reanchor_weight` default 1, G06 posture offset in observation model, G07 `truss_observable='visible_bud'`) are also approved as opt-in fields with defaults preserving current behaviour. |

## 9 Decision 2 (P4 C01/C02) final answer (2026-10-04 17:41 KST)

Source: user-supplied agreed implementation note "Decision 2 only (C01/C02 semantics)", 2026-10-04. Detailed in `CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_2026-10-04.md` addendum A.

| ID | Decision |
|---|---|
| D15 | **Supersedes the `light_basis='incident'` part of D12.** P4 `pack['light_basis']='absorbed'`. Each alpha/Pmax/theta record carries `measured_light_basis` ∈ {incident, absorbed}; a mismatch emits issue `alpha_calibration_basis_conflict` and computation continues (not a refusal). Light samples must still match `pack['light_basis']`; no hidden absorptance conversion. D11 (P3 receives incident whole-plant DLI) is unchanged, so P3 and P4 light inputs stay disjoint. |
| D16 | Respiration: `before_mito` confirmed by source (Butturini eq 5 p.6, eq 8 p.7, Table 2 p.6, `Thornley.calc()` has no Rd). `net_leaf` refused unless the pack supplies Rd_day/Rd_night evidence from a non-dwarf source (`net_leaf_requires_rd_bearing_source`). |
| D17 | Maintenance units resolved: source MAINT is g CH2O g⁻¹ DM_str d⁻¹ (Butturini eq 7 p.7); current code and 12.011/30.026 factor are correct; no 1.466× error. Close the registry conflict as resolved. Tref for dwarf-sourced packs = 25 °C. |
| D18 | `rgr5_scope='plant'` only; RGR5 payload identical for all included organs per interval, otherwise unavailable (`rgr5_scope_inconsistent`). No basal floor; `maintenance_activity_zero` flag. `illuminated_faces='both'` unavailable (`two_sided_exchange_unavailable`). |

## 10 Technical review decisions (2026-10-04 18:22 KST)

Source: agreed Claude Science technical review, consolidated in `CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md`.

| ID | Decision |
|---|---|
| D19 | DLI unit spelling is `mol/m2/day` everywhere, defined once as `DLI_UNIT` in `tools/leaf_light/common.py`. `mol/m2/d` is a notation variant only (never divide by 86400); legacy frozen configs using it are refused (`legacy_dli_unit_spelling`), not auto-corrected. The applicability interval lives in `reference_position.json::applicability_interval_mol_m2_day` with a required `applicability_source_ref` from the P3 parameter-pack domain, passed via `reference_dli.json`; P3 performs the refusal. |
| D20 | `illuminated_faces ∈ {adaxial_only, abaxial_only, both}` is emitted per patch by P2 (no physics change); P4 refuses undeclared (`illuminated_faces_undeclared`) and `both` (`two_sided_exchange_unavailable`). Same-face fixture summation stays. |
| D21 | Plants already exist: measurement starts now and is not gated on v2 implementation. Day-1 recording protocol (capture-phase label, `visible_bud` truss definition, Day-0 node count with counting-rule source, sowing/transplant dates if known) applies immediately; G06/G07 schema fields must support back-fill. |
| D17 note | Maintenance unit evidence upgraded: `dwarf_plant_level.rgg::calcSourceStrength()` subtracts `maintenance_demand_mg` from `gross_assimmilates_mg` in mg CH2O; the CSV "CO2" label is a label error. Q10 = 2 and Tref = 25 °C are hard-coded there. No coefficient rescaling. |
