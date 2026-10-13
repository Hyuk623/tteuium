# Growth/carbon equation pack — Claude Science review, handoff for Codex

Date: 2026-10-04, Asia/Seoul. Source: Claude Science response to `CLAUDE_SCIENCE_GROWTH_PACK_REVIEW_PROMPT_2026-10-04.md` (reviewing `CLAUDE_GROWTH_EQUATION_REVIEW_PACK_2026-10-04.md`). Consolidated by Claude.
Status: **review result.** Section 3 items are software-safety fixes that need only user approval of this handoff. Section 4 items are blocked on three user decisions. Section 5 items need source reading, not choice. Do not change biological coefficients.

Tags: [VSF] verified source fact, [DP] design proposal, [OA] open assumption.

## 0 Scope Claude Science actually read

Read: `tools/fsp_carbon_diagnostic.py` L1–799; `tools/probabilistic_compound_growth.py` L3–261 and L620–1049; `build/fsp_physiology_spec_20261003_01/equation_registry.json`, `source_registry.json`; `tools/growth_calibration_evidence.json`; cached Butturini PDF pp. 3, 5, 9–11.
Not read (no claims made): `tools/growth_calibration.py` (K01/K02 judged from pack only, including the 2026-10-04 meaning guard); `_remaining`, `update_forecast`; P3 L262–619 and L1050–1830; P4 L800–1025; `verification.json`. Codex: verify any item touching these before changing it.

## 1 Mismatches found (M1–M10)

| ID | Finding | Action |
|---|---|---|
| M1 | Claude's prompt misdescribed G03. `_beta_value` (L82) preserves the remaining increment; after an observation shift δ the asymptote drifts by δ (x_max is not kept). The pack wording was correct. | No code change; see G03 in section 4/6. |
| M2 | `equation_registry.json`: all 26 rows `implemented: false`, but nrh, maintenance, activity, beta, inverse_area, inverse_dimension, available_budget, sufficiency, balance are live. | Section 3 item F1. |
| M3 | NRH written forms differ but are algebraically identical; code form `sqrt((αI−Pmax)² + 4(1−θ)αI·Pmax)` (L487) is better conditioned. | F1: update registry string to the code form. |
| M4 | `left/right_target_mm` asymptote under DLI is `w0 + f_DLI·(target − w0)` (L941): equals target only when f_DLI = 1, and is station-dependent. Not an absolute extent under DLI ≠ 1. | F7 (meaning/docs); decision 3. |
| M5 | RGR5 scope undeclared: registry says whole plant; code reads per-organ `maintenance_history` row (L572). Per-organ → mature leaves get zero maintenance. | F5. |
| M6 | Temperature below the lowest knot (T_base) raises `StudyError('Response outside supplied domain')` in `_clock` (L747) instead of pausing development. | F2. |
| M7 | Two DLI paths crash instead of returning unavailable: `_beta_value` L79–80 (`x_max < x_birth`), `_trajectory` L1046–1047 (negative width target). | F3. |
| M8 | T_base 5.7 °C: Butturini Table 1 borrowed it from Adams et al. 2001 (not inspected). Zeist et al. 2018 (abstract only): 4.5–14.8 °C across tomato germplasm. | Evidence note; never a default. |
| M9 | Dwarf-paper root fraction 0.1 traces to Marcelis 1994 (cucumber), value unverified. `_mass_scope` (L615) requires root mass for whole_plant but no root demand exists → whole-plant scope unreachable without measured root mass. | Evidence note; keep unavailable. |
| M10 | Beta is hard-refused for existing segments/blocks (L712–713, L717–718), stronger than "opt-in for newborns". | F8 (docs only). |

Confirmed good, leave alone: `validate_calibration_clock` (L103–116, m(T_ref)=1 identity and fluctuating-history rejection) and `_validate_d9` (L165–191).

## 2 Verdict summary

| ID | Verdict | Core point |
|---|---|---|
| L01 | revise | P3 gets incident, whole-plant, one reference position, full local-day DLI; basis_id names sensor plane/position; disjoint from P2 tissue basis; add applicability interval. (Decision 1) |
| L02 | retain | Add guard: no P3 direction coordinate may bind to an L02 output. |
| G01 | revise | Allow explicit sub-base knot with multiplier 0 (M6). Daily-mean T is exact while T stays within the linear ramp; "fluctuating mean insufficient" binds only when crossing T_base or the cap. |
| G02 | revise (semantics) | Rename meaning to `absolute_extent_target_at_reference_DLI`; document realized asymptote; narrowing needs `narrowing_assumption` evidence. |
| G03 | revise | Keep increment-preserving re-anchor as default; add `reanchor_weight ω ∈ [0,1]` (ω=1 current), ω = σ²_state/(σ²_state+σ²_meas) when observation covariance declared; report cumulative Σ|ω·δ| in update.json. Source: Butturini eq 12 p.8 with Yin erratum (Ann Bot 91(6):753, DOI 10.1093/aob/mcg091). No beta fitter → x_max, a_m, a_e are user_assumed. |
| G04 | revise | c_DLI per growth_curve; refuse one c_DLI bound to both families (increment elasticity is 1 for exponential, f·x_max/(f·x_max − x_birth) > 1 for beta). Crash → unavailable. DLI applicability interval. (Decision 3) |
| G05 | retain | Use small sensitivity ensemble of particles (e.g. ρ ∈ {0, 0.3, 0.6}); no code change. |
| G06 | revise | Add transient-posture term to observation model only: θ_obs = θ_state + δ(phase) + ε, δ(reference phase) = 0. Phyllotaxis 137° is an assumption [VSF Butturini p.11]. |
| G07 | revise | Required `truss_observable`; recommended `visible_bud`. Truss rule unavailable if undeclared. |
| G08 | retain + notes | Event evidence is hard rejection (L254, L257–259): report ESS loss from events separately. Σ block-diagonal across organs ignores shared pose/scale error → over-confident updates; declare it. Repeatability capture unblocks this. |
| C01 | unresolved | Algebra correct. H(0)=0 (L488) implies before-mito; must confirm source fit (section 5). Empirical NRH valid only at its calibration CO2 (≈798 µbar, ≈23 °C, 50:50 R:B). Add light_basis equality check; `illuminated_faces` (refuse `both`). (Decision 2) |
| C02 | revise | `rgr5_scope` required = plant; `maintenance_activity_zero` flag, no basal floor; CH2O vs CO2 unresolved (if CO2, current maintenance is 1.466× too high). |
| C03 | revise | `candidates[0]` silently wins (L700–702): require one inverse or explicit `primary_inverse`. |
| C04 | retain | Growth respiration inside D; `_budget` subtracts maintenance only (L752); ASR convention follows organs.rgg 300–307, printed eq 15–16 discarded. Root demand absent (M9). |
| C05 | revise (labelling) | Add `reserve_propagation='none'`, `interval_independence='independent_single_interval'`; reject contiguous multi-row tables reusing identical reserve unless `reserve_reuse_assumption`; distinct `maintenance_deficit` status when U<0. |
| C06 | retain | Ledger must carry the same `pack_id` as the C04 run. |
| K01 | retain | No beta fitter; fitted p_stop must be refused as structural mismatch on a node_budget axis. |
| K02 | revise | Split meaning categories (section 3 F9) and require `validate_calibration_clock` to pass before any binding. |

## 3 Software-safety fixes (no biological choice; implement after user approves this handoff)

Owner: Codex (P3/P4/calibration owners). All additive or failure-mode corrections; no coefficient values.

| # | Change | Files / functions | Acceptance test |
|---|---|---|---|
| F1 | Sync `equation_registry.json`: set `implemented` per live code with function locator; replace NRH string with the code form. New dated version, keep old file. | `build/fsp_physiology_spec_20261003_01/equation_registry.json` (copy to new versioned file) | Every live equation has `implemented: true` and a function locator; NRH strings match. |
| F2 | Clock: allow an explicit lower knot below T_base with multiplier 0; temperatures in that declared interval pause development. Undeclared out-of-domain still refused. | `normalized_temperature_clock`, `_clock` (L742–756) | T below T_base inside declared zero knot → m=0, development pauses; outside all knots → refused as now. |
| F3 | Convert `x_max < x_birth` (L79–80) and negative width target (L1046–1047) from `StudyError` to structured per-trajectory unavailable with reason codes (`dli_target_below_birth`, `dli_negative_width_target`); trajectory stays in the denominator. | `_beta_value`, `_trajectory`, summaries | Low-DLI fixture runs to completion; affected trajectories report reason codes; probabilities computed over all trajectories. |
| F4 | P4 labelling: `reserve_propagation='none'`, `interval_independence='independent_single_interval'` on every row; reject contiguous rows reusing identical reserve unless `reserve_reuse_assumption` declared; `status='maintenance_deficit'` when U<0. | `_budget` (L740–754), `compute_carbon_sufficiency` | Multi-interval synthetic fixture triggers the guard; U<0 row has the distinct status. |
| F5 | `rgr5_scope` field (required; only `plant` accepted for now); emit `maintenance_activity_zero` flag; assert RGR5 activity ∈ [0,1). | `compute_respiration` (L534–585) | Missing scope refused; zero-activity flag present when RGR5=0. |
| F6 | `primary_inverse` required when >1 inverse supplied. | `infer_structural_demand` (L700–702) | Two agreeing inverses without primary → refused; with primary → that one used. |
| F7 | Rename side-target meaning to `absolute_extent_target_at_reference_DLI` in docs and in the K02 meaning table; document realized asymptote; require `narrowing_assumption` evidence when target < min observed station. | `tools/PROBABILISTIC_COMPOUND_GROWTH.md`, `_decode_block` (L902–944), `growth_calibration.COORDINATE_MEANING` | Asymptote test with f_DLI ≠ 1 matches documented expression; narrowing without evidence refused. |
| F8 | Docs: state beta is hard-refused for existing organs. | P3 guide | — |
| F9 | K02 meaning categories split: remaining increment; absolute extent target at reference DLI; absolute potential maximum (`*_x_max_*`); birth value; rate; angular offset; angular amplitude; positive wait; beta timing; dimensionless ratio. Require `validate_calibration_clock` to pass before any binding. Refuse fitted `p_stop` → node_budget axis as structural mismatch. Refuse binding any L02 output to a P3 direction coordinate. | `growth_calibration.ROLE_MEANING`, `COORDINATE_MEANING`, `_check_binding_meaning`, `apply_parameter_set` | Existing 5 guard tests still pass; new tests for each refusal. |
| F10 | C06 audit requires matching `pack_id` with the C04 run. | `audit_carbon_balance` | Mismatched pack_id refused. |
| F11 | G08 reporting: ESS loss attributable to event evidence reported separately from geometry; manifest note that cross-organ measurement correlation is not modelled. | `update_forecast`, `_event_likelihood` | Update output has both ESS components. |

Note F9 extends Claude's 2026-10-04 guard (`build/p3_semantic_guard_20261004_01/`); keep its tests.

## 4 Blocked on user decisions

Decision 1 (L01, DLI for P3) — recommended: incident, whole-plant, one declared reference position, complete local day; `basis_id` names sensor plane/position and may not equal any P2 tissue `area_basis_id`; declared DLI applicability interval with out-of-interval refusal. Rationale: absorbed per-plant DLI would make c_DLI depend on the architecture P3 predicts and overlap P4 supply.
→ Implements in `_validate_d9`, `_size_response`.

Decision 2 (C01/C02 semantics) — recommended: `respiration_accounting='before_mito'`, `light_basis='incident'`, required `light_basis` on α/Pmax evidence with equality check, `illuminated_faces='adaxial_only'` (refuse `both` until a two-sided model exists). Final numeric use also needs section 5 answers.
→ Implements in `compute_leaf_exchange` (L470–501), evidence records.

Decision 3 (G04, DLI across curve families) — recommended: `c_DLI` declared per growth_curve; refuse one coefficient bound to both; F3 unavailable handling; DLI applicability interval.
→ Implements in `_size_response` (L194–203), `_decode_block` L941, K02 table.

Optional, also needs user OK: G03 `reanchor_weight` (default 1 = current), G06 posture offset in observation model, G07 `truss_observable` (recommended `visible_bud`).

## 5 Source checks (read, do not choose)

1. Were Butturini α/Pmax fitted to net or gross exchange? Check `dwarf_photosynthesis.rgg` / parameter CSV (commit 2d727a3) and paper eq 5 p.6. H(0)=0 in code presumes gross/before-mito.
2. Is source maintenance `m` in g CH2O or g CO2 per g DM per day? Factor 12.011/30.026 vs 12.011/44.009 (1.466× difference).
3. Record calibration conditions of NRH as the applicability domain: n=3 plants, rank 3 mature leaf, ≈23 °C, 798 µbar CO2, 50:50 red:blue, 0–2000 incident PPFD [VSF per Science; re-verify locator].
Report answers in an evidence update; do not change coefficients.

## 6 Observations that unblock science (no experiment authorized here)

- Repeatability pair (same plant captured twice back-to-back with re-mounting): unblocks G08 Σ.
- Paired captures at two fixed photoperiod phases on ≥3 dates: G06 posture.
- PPFD logging at ≥3 positions over complete local days: L01.
- Dated first-visible leaf/truss log; plants grown to termination: G07.
- Repeated same-organ length/extent/area ≥6 time points: G02/G03.
- Light-response/dark-exchange curves on target cultivar: C01. Organ dry mass, structural/nonstructural split: C02–C04.

## 7 Deliverables requested from Codex

- Implement section 3 after user approval; section 4 only after decisions are recorded in `CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md`.
- Execution report `handoff/CODEX_GROWTH_PACK_FIXES_EXECUTION_2026-10-04.md`: changed functions, new fields/units, tests, hashes, items deferred.
- Verify items in "not read" scope before relying on Science's line numbers.
