# Four chat prompts for the consolidated growth pack revision

Date: 2026-10-04. Prepared by Codex for the user.

## Preparation brief

Read the [consolidated V2 handoff](CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md) and latest D11-D18 decisions, compare against the delivered Science fixes, and prepare separate English prompts for the four existing chats plus a user briefing. This preparation changes documentation only; it does not implement or dispatch the prompts, run models or select coefficients.

V2 is the controlling implementation handoff. Its D15-D18 supersede the earlier incident-P4 and undecided-Q2 wording. Earlier reports remain historical evidence. References by decision ID are preferable to section number because the decision record has two section 8 headings.

## Current decisions

| Topic | Current rule |
|---|---|
| P3 light | Incident DLI at one declared reference position/plane, full local day, fixed horizon and declared applicability; not tissue light |
| P4 light | Absorbed light for the adopted dwarf-source route; explicit coefficient measured_light_basis; mismatch emits alpha_calibration_basis_conflict and computation continues |
| P4 respiration | before_mito, maintenance downstream; net_leaf needs evidence-bearing Rd_day/Rd_night from a non-dwarf source |
| Maintenance | g CH2O per g structural DM per day; retain 12.011/30.026; dwarf-source Tref 25 C, not a global injected default |
| Faces | Only evidenced adaxial_only accepted for leaf exchange; both is unavailable |
| New P3 options | Reanchor weight, observation-only posture offset and explicit truss observable are approved; no fitted values are supplied |
| Role boundary | P3 owns realized growth; P4 remains diagnostic; linking, future optical geometry and reserve propagation remain deferred |

The accepted source interpretation does not establish target-cultivar accuracy. Coefficient-basis conflict is a reported issue rather than a stop under D15; other missing evidence and domain limits retain their own unavailable behavior.

## Prompts and ownership

| Existing chat | File | Delta from its previous delivery |
|---|---|---|
| P1 3d구현 | [P1 V2 prompt](CODEX_P1_GROWTH_PACK_V2_CHAT_PROMPT_2026-10-04.md) | Observation/evidence readiness for the newly approved options and leaf-face policy; no new reconstruction model |
| P2 광시뮬레이터 | [P2 V2 prompt](CODEX_P2_GROWTH_PACK_V2_CHAT_PROMPT_2026-10-04.md) | Update light-consumer guidance and audit face/basis provenance; no new reference channel or physiological model |
| P3 생장방향 | [P3 V2 prompt](CODEX_P3_GROWTH_PACK_V2_CHAT_PROMPT_2026-10-04.md) | D14a-c plus V2 structured unavailable behavior; retain completed growth/calibration guards |
| P4 토마토 FSP | [P4 V2 prompt](CODEX_P4_GROWTH_PACK_V2_CHAT_PROMPT_2026-10-04.md) | A1-A7/D15-D18, evidence registry/domain update, serialization and unavailable behavior |

P3 is the sole editor of growth runtime/calibration and their tests/guides. P4 is the sole editor of physiology runtime/schema/tests/guide and the new registry. P1/P2 own their own evidence/interface work and do not modify either runtime. Each chat writes a distinct execution report and separate build subdirectory; no concurrent shared report editing.

Use `build/growth_pack_fixes_20261004_01/P1/` through `P4/`, or fresh suffixed directories if already occupied. The eventual `CODEX_GROWTH_PACK_FIXES_EXECUTION_2026-10-04.md` roll-up has one coordination owner and is prepared only after receiving actual reports; none is claimed complete here.

## Coverage against V2

| V2 items | Implementation owner | Prior delivery status / remaining delta |
|---|---|---|
| F2, F3, F7, F8, F11, D11, D13 | P3 | Delivered; inspect compatibility and V2 missing-science behavior, preserve valid computations |
| F9 | P3 calibration | Delivered guard taxonomy/clock/stop/light-direction protection; retain tests and audit changed input paths |
| D14a, D14b, D14c | P3 | New reanchor weighting, posture likelihood option and truss definition availability |
| F4, F5, F6, F10 | P4 | Delivered interval/RGR5/primary/ledger safety; retain and extend where A5/V2 requires |
| A1, A2, A3, A5, A6, A7 | P4 | New source-specific restrictions, calibration-basis issues, face gate, payload consistency, unit regression and disclosures |
| A4, D17 | P4 | Keep maintenance calculation; update resolved interpretation and source-specific Tref documentation |
| F1, S3 | P4 | New versioned registry and source/domain records, with final producer references |

## Implementation details recipients must make explicit

1. Existing P3 code calls the DLI block `light_response.applicability_interval`; V2 also uses `dli_applicability_interval`. Document a single semantic mapping and reject conflicting duplicate declarations. Do not silently drop the already implemented field or invent domain bounds.
2. Existing P4 code uses `photosynthesis.Pmax`; V2 also calls the saturation parameter P_sat. Apply evidence checks to the referenced saturation parameter record and document the equivalence; do not create two independent saturation coefficients.
3. V2's default-preservation wording does not authorize inventing a truss observable. Its explicit D14c missing-field rule wins: missing definition makes the truss rule unavailable, not visible_bud by default. Preserve unrelated leaf/node/terminal behavior.
4. Cumulative reanchor movement must be reported per trait/unit; do not add mm, cm2 and radians together. Automatic covariance weights need compatible state/measurement variances and explicit opt-in.
5. A7 requires non-null disclosure fields but `rgr5_scope` may be undeclared or inapplicable for constant activity. Use explicit reporting states for missing/inapplicable declarations, never fabricate plant-scoped evidence. Distinguish these reporting categories from the allowed RGR5 model scope.
6. A2 mismatch is nonfatal. Missing required evidence, incompatible sample basis and two-face exposure have different outcomes; test them separately.

## User briefing points

The latest decision resolves the previous Q2 policy hold. P3 reference incident light and P4 tissue absorbed light remain deliberately distinct. Existing safety code is retained; the new work adds observation correction options, source/face/unit guards and transparent disclosure of missing physiology. Maintenance is not rescaled by 1.466. Dwarf-source 25 C is a reference condition, not an instruction to alter the user's environment.

Software can support opt-in weights and posture offsets without having measured values to use on real plants. P1 accepted physical area/identity and P2 reference-DLI production remain incomplete. The V2 policy does not turn two-face P2 output into adaxial-only input or validate real growth accuracy. Cross-project integration is still outside these prompts.

Completion: four prompts prepared from the current handoff and inspected source vocabulary. Verification of local references and item coverage is recorded in `build/growth_pack_v2_prompt_review_20261004_01/verification.json`. No runtime or coefficient changes, tests/models, or cross-chat messages were made here.

## P2 reference channel scope update on 2026-10-04

The user subsequently requested incorporating [the reference DLI channel handoff](CODEX_REFERENCE_DLI_CHANNEL_HANDOFF_2026-10-04.md). The linked [P2 prompt](CODEX_P2_GROWTH_PACK_V2_CHAT_PROMPT_2026-10-04.md) is now revised in place and supersedes this index's earlier P2 no-channel restriction. It adds logged and spot-times-schedule measured routes, a simulation interface/audit only, independent package validation and a bounded read-only P3 compatibility check. Full-system linking and P3/P4 runtime edits remain outside P2 ownership.

Real position, clock times, readings and applicability bounds stay blank; synthetic software work can proceed before the expected meter arrival. The compact producer JSON must be explicitly mapped to the existing P3 contract; multi-day reduction must not fabricate a single local-day provenance record. P1/P3/P4 prompt files are unchanged. Prior P2/index texts and source hashes are preserved in `build/p2_reference_dli_prompt_revision_20261004_01/before/` and its before_hashes.json. This update prepares the prompt only, with no implementation or dispatch.

## Technical review supplement on 2026-10-04

The user requested applying [technical review fixes](CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md) to the prompts. All four linked prompt files are now supplemented in place. D19-D21 and the technical-review items override conflicting older details; this section supersedes the prior unchanged-P1/P3/P4 status. Preparation remains documentation only. Previous texts are preserved under `build/technical_review_prompt_revision_20261004_01/before/`.

| Requirement | Single editor / owner | Prompt delta |
|---|---|---|
| D19 shared DLI_UNIT | P2 creates constant in tools/leaf_light/common.py; P3/P4 only import | mol/m2/day everywhere in new active contracts; named legacy refusal, no alias auto-conversion; P3-domain applicability_source_ref |
| D20 illuminated_faces | P2 produces, P4 validates; P1 supplies evidence | Per-patch adaxial_only/abaxial_only/both; unknown not fabricated; opposite-face refusal and same-face sum |
| P2-a through P2-h | P2 | Logger semantics, transition integration, cosine/level/ambient evidence, gradient-based tolerance, multi-plant association, horizon variability, DST and reverse basis checks |
| P3-a through P3-f | P3/calibration | Existence/computability/intersection coverage; hard-admissibility stage and rejection count; existing meaning guard regression; full sub-base validation; named legacy migration; reverse manifest basis validation |
| P4-a through P4-f | P4 | Existing V2 basis/Rd/disclosure delta plus reserve lineage, RGR5 mass-basis difference and explicit total-DM substitution caveat |
| Section 3 registry/source notes | P4 | Maintenance label-error evidence, source Q10/Tref metadata, existing SLA guard reason, final P3 report association; NRH empirical preprocessing remains unresolved |
| Section 6 area evidence gate | P1 | Scale, pose, aware time/phase, one-sided area/coverage/occlusion and partition/reviewer identity |
| D21 Day-1 protocol | P1 template/checklist, P3 read-only loader | Recording starts now; explicit visible_bud protocol, phase and sourced node count, dates only if known |

Do not have several chats edit common.py, the template generator or the final report. P2 publishes the shared constant change; P3/P4 can complete independent work before importing it. Use separate P1/P2/P3/P4 subdirectories under a fresh build/technical_review_fixes_20261004_01 and separate project reports. Coordination will create CODEX_TECHNICAL_REVIEW_FIXES_EXECUTION_2026-10-04.md only after actual deliveries.

The latest unit decision supersedes the earlier P2 conversion to mol/m2/d: frozen legacy spelling is refused, never auto-corrected. D21 supersedes the previous unselected-visible_bud and no-protocol wording for new recording; historical ambiguous records stay ambiguous. Human acquisition is not performed or claimed by prompt preparation.

Review-only verification: local references and technical item coverage are recorded in `build/technical_review_prompt_revision_20261004_01/verification.json`. No runtime files, biological coefficients, human measurements or source handoff were edited; no model/tests or cross-chat messages were run.
