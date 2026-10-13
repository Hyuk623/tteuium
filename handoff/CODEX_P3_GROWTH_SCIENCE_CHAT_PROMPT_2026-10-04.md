# P3 prompt for accepted growth science fixes

Recipient: existing P3 growth-direction chat. Date: 2026-10-04.

Implement the P3 and calibration safety fixes below and the user's accepted decisions 1 and 3 from the growth Science review. Preserve numerical biology except for the explicitly specified domain/failure/meaning corrections. Do not supply or fit new biological coefficients.

## Read first

Read repository rules, LOG tail and TODO, then:

- [Science review](CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md), including its uninspected-code disclosure.
- [Decision record](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), including the 2026-10-04 addendum.
- [Prompt ownership](CODEX_GROWTH_SCIENCE_CHAT_PROMPTS_INDEX_2026-10-04.md).
- [D8-D10 delivery](CODEX_P3_GROWTH_DECISIONS_EXECUTION_2026-10-03.md).
- [Existing semantic guard verification](CODEX_P3_SEMANTIC_GUARD_REVIEW_2026-10-04.md).
- Current `tools/probabilistic_compound_growth.py`, `tools/growth_calibration.py`, their schemas/guides/tests, especially `_remaining`, `update_forecast` and calibration functions not inspected by Science.

## Accepted and deferred decisions

**Question 1 accepted:** P3 DLI is incident, at one declared reference position/plane, over a complete local day, used at whole-plant model scope. `basis_id` identifies that reference and must be distinct from tissue `area_basis_id` values in supplied provenance. Require a declared DLI applicability interval and refuse out-of-interval inputs; do not invent bounds. This is not a tissue-area-weighted average. Preserve fixed-horizon DLI.

**Question 3 accepted:** declare c_DLI separately per growth_curve; refuse one coefficient binding shared by exponential and beta families. Independently supported coefficients may happen to have the same numerical value; validation must check identity/role rather than rejecting numerical equality. Preserve increments versus maxima as different roles. Apply the accepted interval and structured unavailable rules below.

**Question 2 undecided:** do not choose P4 respiration, light-basis or face policy. Optional G03 reanchor_weight, G06 transient-posture offset and G07 truss_observable selection are not adopted. Keep current reanchoring and event behavior; report their assumptions without adding these options. The M1 correction means the original pack's beta endpoint-drift description was correct.

## Work and ownership

Write an English brief before editing. You are the sole editor of P3 and `tools/growth_calibration.py` for this task. P4 owns physiology and the new equation registry. Do not edit their runtime files. Inspect actual current functions rather than relying on the Science line numbers.

| Item | Required change | Acceptance |
|---|---|---|
| Decisions 1/3 | Update `_validate_d9`, `_size_response`, decoding/config/schema/provenance as needed for reference DLI, domain and per-family binding | Valid separate-family fixture passes; shared coefficient binding, wrong reference basis, incomplete provenance and out-of-domain DLI are refused with clear reasons |
| F2 | Extend `normalized_temperature_clock` to accept an explicitly declared lower knot below T_base with multiplier zero; retain no extrapolation | Within the declared sub-base zero interval, development pauses; outside declared knots, refuse; existing reference normalization remains valid |
| F3 | Replace the two specified DLI-induced target failures with structured per-trajectory unavailable reasons `dli_target_below_birth` and `dli_negative_width_target` | Low-DLI run completes, affected trajectories remain in the ensemble denominator, summaries expose availability and reasons; unrelated invalid configurations are not silently swallowed |
| F7 | Use meaning `absolute_extent_target_at_reference_DLI`; document realized station asymptote `w0+f_DLI*(target-w0)`; require narrowing_assumption evidence under the review's condition `target < min(observed stations)` | Nonunit-DLI asymptote matches; required evidence is enforced; do not silently broaden the threshold to every station without recording the design question |
| F8 | State that beta is hard-refused for existing organs/segments, not merely an omitted default | Documentation and validation agree; retain exponential existing-organ behavior |
| F9 | Extend existing ROLE_MEANING / COORDINATE_MEANING / `_check_binding_meaning`; check clock compatibility before applying bindings; refuse fitted p_stop into node_budget and L02 outputs into P3 direction coordinates | Existing five guard cases pass; new semantic, clock, stop-budget and directional-provenance refusal cases pass |
| F11 | Report event-evidence ESS effects separately from geometry evidence in `update_forecast`; disclose unmodeled cross-organ measurement correlation | A fixture with event rejection and geometry likelihood reports distinguishable ESS stages without changing final weights or double-applying evidence |

For F9, distinguish remaining increment, absolute extent target at reference DLI, absolute potential maximum, birth value, rate, angular offset, angular amplitude, positive wait, beta timing and dimensionless ratio. Verify the existing closed guard and extend it; do not reintroduce automatic conversions. Preserve frozen pre-run pack application and hashes.

For F11, document the conditioning order and stage definitions, because ESS contributions are order-dependent. Do not label a sequential ESS difference an order-independent causal decomposition. Preserve incompatible all-zero support and finite-bank behavior.

For F3, distinguish a curve's realized availability from trajectory existence/weight. Do not delete unavailable trajectories, renormalize the original ensemble silently, or substitute zero growth. Any conditional available-only numerical summary must also expose its original ensemble coverage.

No changes to validate_calibration_clock's accepted fixed-setpoint evidence rule or `_validate_d9` environment ownership are implied beyond the listed input refinements. The review's observation about means within a linear ramp is not authorization to accept arbitrary fluctuating-history calibration.

## Validation and delivery

Add focused tests for changed guards and failure modes, then run relevant P3/calibration regressions, including existing D8-D10 and semantic-guard tests. Use synthetic explicit parameter assumptions only. Validate exported schema/reasons, family provenance, summary denominators and unchanged valid-baseline behavior. Do not run real fitting, new model selection or a cross-project pass.

Save `handoff/CODEX_P3_GROWTH_SCIENCE_EXECUTION_2026-10-04.md` with F2/F3/F7/F8/F9/F11 and decision 1/3 status, changed files/functions/fields/units, commands/results/hashes, compatibility handling and deferred items. Publish an equation-to-function mapping for P4's F1 registry update via the handoff; do not concurrently edit its registry. Append LOG and precise Codex-to-Claude questions to TODO. Missing numeric evidence remains unavailable or explicitly assumed; no biological validation claim.
