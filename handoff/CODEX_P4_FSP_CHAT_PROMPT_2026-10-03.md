# P4 FSP carbon diagnostic continuation prompt

Target chat: **토마토 FSP**

Date: 2026-10-03. This is a paste-ready continuation prompt for the named project chat.

Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.
All paths below are relative to this root unless stated otherwise.

Read the parent `공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, the last five lines of `handoff/LOG.md`, and `handoff/TODO.md` first. Create an English work brief before implementation. Respect file ownership and active OneDrive edits: Codex owns `tools/` and `tools/tests/`; protected core changes belong to Claude Code. Do not edit human configuration, observations or `docs/`. Record specification conflicts for Claude rather than inventing a scientific decision.

Read [the integration decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), including D1-D10. The latest explicit decisions take precedence over older proposals; the Science review was not adopted in full. Inspect current source and execution records before repeating work.

Shared boundaries:
- P3 owns realized growth increments and future geometry. P4 is a read-only carbon diagnostic at runtime.
- Cross-project linking remains deferred under D3. Continue this project's own work; do not launch an end-to-end pipeline.
- An explicitly selected, frozen and hashed calibration pack may be applied before P3 runs under D5; never fit or apply it implicitly at runtime.
- The first later synthetic pass requires numerical P1-P2-P3 results. P4 may be unavailable with reasons under D6.
- Round-trip checks apply to reversible units, frames, IDs and representations. Light transport, aggregation, photosynthesis and forecasting require forward correctness checks, not inversion.
- Preserve source samples, complete shapes, identity, uncertainty, missingness and provenance. Follow each producer's actual missing-value contract rather than replacing unknown values with zero.

Continue work already authorized in this chat. A missing prerequisite should block only dependent work. Do not treat this prompt as permission for new private-data uploads, paid services, training or cross-chat messaging. Finish with an English handoff and a Korean explanation, distinguishing implemented software, synthetic evidence, scientific assumptions and remaining dependencies.

## Objective and source documents

Update the FSP review and implementation contract to the settled diagnostic role and the new P3 environment policy. Complete the current specification/evidence work. Do not treat the Science review or this prompt as blanket approval of unresolved physiological equations.

Read:
- [FSP review handoff](CLAUDE_FSP_REVIEW_HANDOFF_2026-10-03.md).
- [Physiology contract](CLAUDE_FSP_PHYSIOLOGY_CONTRACT_2026-10-03.md), especially section 10.
- [P3 D8-D10 implementation handoff](CODEX_P3_GROWTH_DECISIONS_IMPLEMENTATION_HANDOFF_2026-10-03.md).
- The latest calibration execution record, physiology evidence pack and its machine-readable integration map referenced by those handoffs.

## Required review and contract work

1. Separate the existing offline calibration route from runtime physiology. D5 includes explicit pre-run `tools/growth_calibration.py::apply_parameter_set` with a frozen, hashed pack. It does not authorize runtime fitting, implicit adapter application or converting an exponential fit into a beta fit.
2. Freeze the runtime role around the proposed pure `compute_carbon_sufficiency` contract. P3 geometry and increments are read-only inputs. P4 must not create realized growth, overwrite state, clip predicted increments or multiply P3 growth rates.
3. Classify potential-growth and form equations as inactive counterfactual analyses where appropriate. Inspect the current machine map: a prior claim that the carbon diagnostic was absent has already been superseded. Fix only actual remaining inconsistencies through the authorized owner.
4. Consume the proposed `p3_light_coupling` and full `p3_environment_paths` audit when available; do not infer independence from old clock-only flags. D9 allows P3 temperature-clock and size-target DLI effects only. Explicitly record any effects embedded in fitted packs.
5. Distinguish diagnostic photosynthetic supply from growth feedback. P4 still needs physically appropriate light inputs to estimate supply. The double-counting restriction does not mean deleting photosynthesis because P3 used DLI; it means avoiding a second growth correction. Any future feedback requires a separate decision.
6. P3's exclusion of CO2/VPD/RH/EC/pH does not itself validate a P4 response for those variables. Assign each a supported equation, a metadata-only role or an unavailable dependency. Never invent response coefficients.

## Scientific issues to resolve through Claude review

For every choice, distinguish verified source facts, proposed adaptations, declared assumptions and target-calibrated parameters. Preserve source equation/table/page, cultivar, growing conditions and applicability.

- Incident versus absorbed light in the selected photosynthesis model, and net versus before-mitochondrial exchange.
- Which leaf/organ/day/night respiration components are already subtracted, so each cost is charged exactly once.
- Growth cost/ASR multiplication versus division, CH2O versus CO2 source-unit conflicts, root/fruit coefficient ordering and structural versus total dry-mass basis.
- Initial organ masses, roots, reproductive scope, reserves, carbon fractions and minimum-pool assumptions.
- Independently supported conversion from P3 geometry increments to structural mass demand. Do not derive grams from dimensionless image ratios, silently average inconsistent allometries or treat missing root demand as zero.
- Calendar versus development time at calibration bindings. P3 beta timing parameters are not automatically fitted physiological coefficients.

Leave unresolved choices unavailable or explicitly hypothetical. Do not install source-cultivar values as target defaults. Reuse existing evidence; obtain additional literature only for a specific unresolved question.

## Diagnostic IO and accounting

Preserve plant instance, trajectory identity/weight, interval, frame, geometry hash, area basis, light basis, source hashes, assumptions and missingness.

The section-10 candidate output fields are:
- `available_growth_carbon_gC`
- `required_growth_carbon_gC`
- `sufficiency_ratio`
- `maintenance_deficit_gC`
- `growth_deficit_gC`
- `status`, `limiting_inputs`, `assumptions`, `source_hashes`

Follow the reviewed contract's exact equations and statuses. Maintenance deficit and zero growth demand have null ratios with explicit reasons. Missing required evidence is unavailable, not zero, infinity or fabricated sufficiency.

Use compatible metric one-sided tissue area and seconds for exchange integration, with explicit conversions for day-based source coefficients. Evaluate nonlinear leaf exchange before spatial aggregation where supported samples exist. Absorbed PPFD already includes absorptance.

Keep carbon pools and demands separate per plant even when the light scene is a shared canopy. A supported leaf-only diagnostic must be labelled partial scope rather than whole-plant sufficiency. P3 future envelopes remain optically ineligible under the current contract.

## Delivery and next implementation boundary

Deliver a new English P4 continuation/review report and an exact implementation contract: retained/revised/unresolved equations, owned files/functions, fields/units, required inputs, availability rules and meaningful validation. Preserve past evidence and append decisions.

If an adopted isolated diagnostic implementation is already authorized in this chat, continue it within that exact scope and test units, carbon balance, respiration ownership, state immutability, missingness, zero demand and deficits. Otherwise finish the review contract without starting production physiology.

Do not make numeric P4 output a prerequisite for the first synthetic integration pass. Report the actual current readiness; cross-project adapters and the end-to-end run remain deferred.

