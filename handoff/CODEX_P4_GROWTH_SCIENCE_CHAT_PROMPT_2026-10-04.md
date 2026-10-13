# P4 prompt for diagnostic accounting safety and source checks

Recipient: existing P4 tomato FSP chat. Date: 2026-10-04.

Implement the P4 safety fixes from the Science review and verify the three original-source questions. Keep the diagnostic role and explicitly leave the user's question 2 undecided. This task does not select physiological coefficients or introduce growth feedback.

## Read first

Read repository rules, LOG tail and TODO, then:

- [Science review](CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md), including the uninspected-code disclosure.
- [Decision record](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), including the new addendum.
- [Prompt ownership](CODEX_GROWTH_SCIENCE_CHAT_PROMPTS_INDEX_2026-10-04.md).
- [P4 implementation](CODEX_P4_IMPLEMENTATION_HANDOFF_2026-10-04.md), [runtime guide](../tools/FSP_CARBON_DIAGNOSTIC.md), current runtime/schema/tests and [source registry](../build/fsp_physiology_spec_20261003_01/source_registry.json).

## User decisions and scope

Question 1 is accepted for **P3**: reference-position incident DLI, complete local day, declared domain and a basis separate from tissue light. This does not select P4's PPFD basis or eliminate P4 photosynthetic supply.

Question 3 is accepted for **P3**: DLI coefficients declared separately by curve family. P3 owns those changes and all calibration edits. You may inspect and report dependencies; do not edit its files.

**Question 2 remains undecided.** Do not enforce the proposed `before_mito` + `incident` + `adaxial_only` combination as the new adopted policy; do not silently replace existing explicit modes or adopt real-use coefficients. Existing unknown semantics remain unavailable or clearly hypothetical. Source checks can proceed and should report evidence without treating a source answer as the user's policy decision.

Optional reanchor weighting, transient-posture correction and truss-observable selection are unadopted. D1-D10 remain in force: P4 does not alter geometry, increments, probabilities or coefficients, and no adapters or reserve propagation are added.

## Implementation work

Write a brief first. Inspect actual current functions and downstream serialization, including the code beyond the ranges Science read. Own only the P4 runtime/schema/tests/guide and the fresh registry/evidence outputs for this task.

| Item | Required change | Acceptance |
|---|---|---|
| F1 | Create a newly versioned equation registry; preserve the historical file. Mark implementation status per actual equation/function and use the stable NRH form from code | Every status has a precise function/path and source snapshot; partial/deferred formulae are not marked fully implemented; original registry hash unchanged |
| F4 | Add `reserve_propagation='none'`, `interval_independence='independent_single_interval'` to diagnostic rows; guard contiguous interval rows reusing identical reserves absent explicit reserve_reuse_assumption; distinct maintenance_deficit status when U<0 | Covered exports/schema support fields/status; multi-interval fixture exercises guard; negative U retains null growth budget/ratio; no next reserve state is produced |
| F5 | Require `rgr5_scope='plant'` for the RGR5 activity path; use evidence for whole-plant five-day structural mass rather than silently treating per-organ history as plant history; flag maintenance_activity_zero | Missing/wrong scope refused or explicitly unavailable; zero RGR5 flagged; activity domain [0,1) is checked; constant-activity mode remains available without fictitious RGR5 evidence |
| F6 | When more than one mass-form inverse is supplied, require explicit primary_inverse | Agreeing inverses without primary are refused; declared primary selects the result; independent-inverse disagreement still fails the existing tolerance check |
| F10 | `audit_carbon_balance` must match pack_id with the originating demand/C04 diagnostic | Missing/mismatched association fails; a correctly associated ledger passes; echoing an unverified ID alone is insufficient evidence |

For F4, inspect whether a batch/table validation entry point already exists. Apply the reuse check where multiple intervals can actually be compared and expose that validation explicitly; do not claim a single-row stateless function can detect unseen previous rows. Scope comparison by the same plant, trajectory/draw, accounting boundary and contiguous time intervals. Preserve the declared assumption when reuse is permitted. Do not create a dynamic reserve engine to implement this guard.

For F5, do not sum an incomplete set of organ masses to fabricate whole-plant history. Missing plant history makes that activity path unavailable. No basal-maintenance floor or new activity law is adopted. Handle floating-point saturation explicitly in validation rather than quietly claiming that a computed value of 1 meets [0,1).

For F1, implementation status and biological acceptance are separate fields/concepts. Map all rows against code rather than marking the entire registry true. Read P3's current mapping or execution handoff for its equations; if it is still changing, record the inspected snapshot and any pending refresh instead of claiming final synchronized status. Do not edit P3's code or its original handoffs.

## Original-source checks

Use cached original material and the source registry first. If the required content is missing, retrieve the original paper/repository version, not a secondary paraphrase. Save exact page/equation/file/commit locators, retrieval status and content hashes in a fresh evidence output.

1. Determine whether Butturini alpha/Pmax were fitted to net exchange or a before-mito/gross convention. Inspect paper equation 5 and pinned `dwarf_photosynthesis.rgg` / parameter CSV at the recorded commit `2d727a3`. A mathematical curve with H(0)=0 alone does not establish the empirical fitting convention.
2. Resolve maintenance m units: g CH2O versus g CO2 per g DM per day. Document the corresponding carbon conversions, 12.011/30.026 versus 12.011/44.009. Do not change coefficients when evidence remains conflicting or before the remaining policy decision is resolved.
3. Verify the recorded NRH calibration conditions: n=3 plants, rank-3 mature leaf, approximately 23 degrees C, 798 microbar CO2, 50:50 red:blue and 0-2000 incident PPFD. These are claims to verify, not values to install. Keep CO2 partial pressure distinct from concentration without justified conversion.

Write each result as verified, conflicting or unresolved, including what it does and does not establish for the target cultivar. Do not promote borrowed temperature/root-fraction/ASR values to defaults. No source-check result alone accepts a whole-plant budget lacking root/reproductive mass and demand coverage.

## Validation and delivery

Run focused guard tests and the P4 regression suite; inspect serialized JSON/CSV and status/schema compatibility, not only in-memory results. Preserve respiration charged once, growth respiration already included in ASR demand, signed exchange, unavailable behavior and no P3 mutation. No real fitting, experiment, biological coefficient adoption or integration run.

Save `handoff/CODEX_P4_GROWTH_SCIENCE_EXECUTION_2026-10-04.md` with F1/F4/F5/F6/F10 completion, exact files/functions/fields/units, test results/hashes, versioned registry path, source-check answers and remaining question 2. Save a separate evidence JSON if needed under a fresh build directory. Append LOG/TODO. Explicitly distinguish completed software safety from unresolved physiological applicability.
