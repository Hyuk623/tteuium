# P4 prompt for growth pack V2 physiological policy

Recipient: existing P4 tomato FSP chat. Date: 2026-10-04.

Implement the remaining P4 delta from [V2 handoff](CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md). Read repository rules, LOG/TODO, [D11-D18 decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), [ownership index](CODEX_GROWTH_PACK_V2_CHAT_PROMPTS_INDEX_2026-10-04.md), [previous P4 delivery](CODEX_P4_GROWTH_SCIENCE_EXECUTION_2026-10-04.md), runtime/schema/guide and existing source snapshots.

Q2 is now resolved by D15-D18. Adopt the specified implementation policy without repeating the earlier approval question. Preserve historical contrary source records as history, and distinguish the adopted model interpretation from target-cultivar validation. Write a brief before editing and inspect actual source, including export/CLI paths the Science review did not read.

Also apply [technical review fixes](CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md). Its D19-D21 and P4-a through P4-f supplement and override conflicting earlier details. Q2 implementation policy is resolved; empirical NRH fitting preprocessing remains unresolved. Do not confuse those statuses.

## Existing work to retain

F1/F4/F5/F6/F10 were delivered with 105 passing tests. Retain explicit independent-interval metadata, table reserve-reuse guard, plant-scoped RGR5 history, explicit primary inverse and verified originating-demand association. Add V2 requirements where missing, not parallel implementations. No reserve propagation, growth feedback or P3/calibration edits.

## A1 to A7 and adopted source policy

| Item | Required implementation and evidence | Acceptance |
|---|---|---|
| A1 / D16 | Keep before_mito with maintenance downstream. net_leaf requires evidence-bearing Rd_day and Rd_night from a non-dwarf source | Unsupported net_leaf returns unavailable with net_leaf_requires_rd_bearing_source; compatible explicit evidence exercises the alternate path; maintenance remains charged once |
| A2 / D15 | Dwarf-sourced packs use absorbed light. Require measured_light_basis in {incident, absorbed} on alpha, saturation and theta evidence records | Missing required scientific evidence is unavailable; evidence-basis mismatch produces alpha_calibration_basis_conflict in every supply row and continues computation; sample/pack basis mismatch still follows its rejection gate; no hidden absorptance conversion |
| A3 / D18 / D20 | P2 per-patch illuminated_faces has adaxial_only, abaxial_only or both; current exchange accepts only evidenced adaxial_only | Undeclared -> illuminated_faces_undeclared; both -> two_sided_exchange_unavailable; abaxial_only remains explicitly unsupported under the adopted adaxial-only model, never relabelled |
| A4 / D17 | Keep maintenance g CH2O/g structural DM/day and 12.011/30.026; document dwarf-source Tref=25 C | No 1.466 rescaling; no global 25 C default; source-specific reference requirement/evidence is traceable |
| A5 / F5 / D18 | Only plant RGR5; identical supported payload across included organs for each interval | Conflicting payloads return rgr5_scope_inconsistent; missing scope/history unavailable; zero activity flagged; [0,1) enforced, no basal floor |
| A6 | Existing _parameter strict-unit check already requires m2/g_structural_blade_DM | Retain that check; add a named SLA unit refusal reason/comment and a regression if missing, not a second conversion/guard |
| A7 | Add all required disclosures to every sufficiency row and preserve them through serialization | Available, deficit, unavailable and diagnostic-table exports carry truthful non-null disclosures; no invented evidence |

The existing saturation role is `photosynthesis.Pmax`; V2 also writes P_sat. Document the role mapping and check the referenced parameter record. Do not create a second coefficient or silently break existing valid packs. No values for alpha/Pmax/theta, Rd, ASR, SLA or other biological coefficients are introduced.

Identify dwarf-source provenance using explicit pack/parameter evidence, not substring guesses or making every synthetic pack a dwarf-source pack. Specify any required provenance discriminator in the schema and leave missing scientific evidence unavailable.

A2's mismatch issue must identify which parameter record conflicted, its measured basis and the pack basis. Preserve the required issue code even when theta or saturation is affected. Carry issues into supply rows and top-level/CSV output so a numeric result does not hide the conflict. Computation continues only subject to all independent availability/domain requirements.

A3 is a physiological gate, not authority to change P2 transport. Current two-face aggregates cannot be relabelled, halved or clipped into adaxial-only measurements. No two-face model or new P2 adapter is included.

A5 should reuse the delivered shared plant_rgr5_history representation. A single canonical interval payload can structurally ensure consistency; conflicting retained per-organ declarations must not be silently ignored. Compare meaningful payload fields/provenance, not incidental dictionary ordering. Do not require invented history for constant activity mode.

## A7 disclosure contract

Every sufficiency row must expose:

- `respiration_accounting` and `light_basis` as actually declared.
- `rgr5_scope` as declared when applicable.
- `source_buffer_feedback='not_modelled'`.
- `nonfoliar_assimilation='not_modelled'`.
- `maintenance_temperature_integration='sub_daily'`.
- `diagnostic_interpretation='cross_cultivar_consistency_check'` (technical review P4-c).

For missing packs/declarations or constant activity, use explicit reporting statuses for undeclared/not-applicable values, with reasons; do not fill physiological defaults to satisfy non-null output requirements. Document allowed reporting values separately from valid model-input enum values. If an existing schema cannot distinguish these cases, make that representation explicit in the brief rather than silently claiming plant RGR5.

Explain buffer-feedback omission as a possible overprediction under sink limitation, not a blanket validated bias for every case. Document that sub-daily Q10 integration differs from using daily-mean temperature. The cited approximately 0.4 percent example is a conditional source comparison, not a correction factor to apply to calculations. Nonfoliar assimilation remains unmodeled, subject to the existing scope assumptions.

## Registry and domain

Create a fresh version of equation_registry; preserve historical registries/source_checks and their hashes. Retain implemented/partial/deferred distinctions rather than marking a whole physiological model implemented from a matching algebra fragment.

- F1: link live formulas to exact current functions and frozen hashes; stable NRH discriminant as in code. Record maintenance-unit interpretation as resolved under D17 with eq7/p7 evidence and retain the old CSV-label discrepancy as historical provenance, not an active request to rescale coefficients.
- Record adopted before_mito evidence under D16: eq5, eq8, Table2 and Thornley.calc(). Separate model convention evidence from any unverified raw empirical fitting preprocessing; do not claim newly inspected raw data that do not exist.
- S3: verify and record calibration domain locators for approximately 23 C, 798 microbar CO2, 50:50 R:B, 0-2000 incident applied PPFD, n=3 and mature rank-3 leaf. Do not convert partial pressure to ppm without justification or treat this as validated ambient-400-ppm applicability. Do not confuse applied measurement light with the adopted absorbed-model input.
- Refresh final P3 producer association after its V2 report exists. If work is still ongoing, record the actual snapshot and pending final metadata refresh; do not edit P3 or claim synchronized final status prematurely.

## Technical review delta

**D19:** import the single DLI_UNIT from tools.leaf_light.common into inspect_p3_coupling and relevant P4 fixtures/schema-facing comparisons. P2 alone adds the shared constant; do not concurrently edit that file or define a local duplicate. Canonical mol/m2/day passes; legacy mol/m2/d yields legacy_dli_unit_spelling with field diagnostics, without correction or division by 86400. Preserve frozen historical artifacts and regenerate new fixtures explicitly.

**D20:** P2 emits face provenance and P4 enforces the model gate. Validate all fixture contributions for a patch/time before an accepted combined exchange result. Two opposite-face fixtures imply both and return two_sided_exchange_unavailable; same-face fixtures retain the existing math.fsum followed by one nonlinear evaluation. Absence of a field is illuminated_faces_undeclared, not adaxial_only. Use synthetic supported biological face mappings for tests, not invented real mappings.

**P4-a/P4-b/P4-c:** implement through the existing A2/A1/A7 work once. measured_light_basis conflict still emits alpha_calibration_basis_conflict and continues under other valid conditions; net_leaf needs non-dwarf Rd evidence; all sufficiency rows carry the full disclosure set including cross_cultivar_consistency_check. Confirm existing rgr5_scope and maintenance_activity_zero reporting rather than duplicating them.

**P4-d reserve provenance:** reserve_gC requires source_ref and outputs carry reserve_provenance_chain_id. Bind that identity to the supplied reserve evidence/lineage and accounting boundary; it must remain traceable when diagnostic calls are exported separately. Do not generate a fresh per-run ID that hides reuse or invent reserve measurements. Reuse existing table validation rather than implementing reserve propagation or claiming that an isolated stateless call can detect unseen rows. Test missing source, stable lineage through separate calls, changed evidence and exported/table-level reuse detection.

**P4-e RGR5 source deviation:** record rgr5_mass_basis_deviation_from_source in evidence/output disclosures when borrowing source activity meaning. The technical handoff reports source RGR5 from total DM including roots/buffer, while P4 uses structural_dm_excluding_reserve. Preserve the adopted P4 basis; do not change f, substitute total mass, or claim source-equivalent calibration. Include exact source-function/variable locators in the registry/evidence.

**P4-f total-DM substitution:** only where an explicit total_dm_substitute assumption is already supplied, disclose the source static-branch 90-percent structural-mass comment and its approximate 10-percent basis caveat. It is a source-supported assumption, not a target-cultivar conversion or permission to introduce a new total-mass input path. Never auto-multiply a measured mass by 0.9. Keep unsupported mappings unavailable.

## Source and interpretation metadata

Close the maintenance-unit limitation in a new registry version using the stronger locators from technical section 3: dwarf_plant_level.rgg::calcSourceStrength subtracts maintenance_demand_mg from carbohydrate-equivalent gross_assimmilates_mg. Preserve the old CSV CO2 label as a historical label error; no coefficient rescaling. Record source Q10=2 and Tref=25 C with locators for dwarf-sourced packs only; these are source metadata, not newly imposed target defaults.

Refresh the final P3 report hash and registry status in a new version, preserving the historical pending snapshot. Check current functions/hashes rather than changing a status string without verification.

Keep NRH empirical fitting preprocessing unresolved. Include the technical review's fixed interpretation note, explicitly as a conditional source-model interpretation: if an origin-passing three-parameter curve was fitted to net data without correction, alpha/saturation and supply may be underestimated and leaf respiration counted again; under that specified conservative-bias interpretation, ratio >= 1 is credible while ratio < 1 alone is not evidence of carbon shortage. Do not turn this conditional note into an unconditional adequacy guarantee, overwrite numerical status/ratio, remove other uncertainty warnings or claim target biological validation. Unknown light, mass, reserve, calibration domain and other omitted processes remain independent limitations.

Retain named not_modelled/unavailable disclosures for unresolved fit preprocessing, buffer feedback, nonfoliar assimilation, reserve propagation, two-sided exchange, sympodial continuation, light-to-orientation response and FvCB. None is authorized for implementation by this supplement.

## Failure behavior, tests and delivery

Apply V2's distinction across API/CLI/schema/export: scientifically missing required fields yield structured unavailable and reason codes; malformed inputs may raise. Test legacy missing-fields paths; do not catch arbitrary defects as unavailable. D15 coefficient-basis conflict is explicitly nonfatal and distinct from missing evidence or incompatible light samples.

Add tests only for actual new/changed behavior and retain existing F4/F5/F6/F10 regression coverage. Include actual JSON/CSV exports for conflict issues and A7 fields, missing-face/two-face cases, net_leaf evidence, source-specific basis/Tref provenance, RGR5 consistency and SLA unit rejection. Save JUnit and an isolated synthetic demo to your own fresh P4 build subdirectory. Do not change source coefficients, fit measurements, run a cross-project model or claim biological validation.

Save `handoff/CODEX_P4_GROWTH_PACK_V2_EXECUTION_2026-10-04.md` with per-item status, exact functions/fields/units/reasons, test results/hashes, versioned registry and domain evidence, and remaining physical/model limitations. Append LOG/TODO. Leave the shared final execution roll-up to coordination and keep P3/calibration files read-only.

Include D19/D20, P4-a through P4-f and technical section 3 metadata as done/already present/deferred. Save new JUnit and synthetic demos under fresh `build/technical_review_fixes_20261004_01/P4/`; test reserve provenance, disclosures on unavailable rows, face fixtures, existing SLA refusal and legacy spelling. Coordination owns the shared CODEX_TECHNICAL_REVIEW_FIXES_EXECUTION_2026-10-04.md after actual deliveries.
