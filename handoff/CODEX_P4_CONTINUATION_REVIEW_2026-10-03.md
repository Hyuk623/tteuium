# P4 diagnostic continuation review and delivery

Date: 2026-10-03. Author: Codex. Scope: the review and specification requested by
`CODEX_P4_FSP_CHAT_PROMPT_2026-10-03.md`.
Delivery completed: 2026-10-04, Asia/Seoul; original dated artifact names retained.

P4 now has a consistent proposed diagnostic contract aligned with D1-D10.
It consumes P3 increments and estimates conditional carbon supply/demand; it does
not generate or modify realized growth. This delivery completes the requested
specification work, not production physiology or scientific acceptance.
No isolated production implementation was adopted in the inspected authorization,
so no production module, cross-project adapter or model run was started.

## Authoritative artifacts

- [Exact implementation contract](CODEX_P4_DIAGNOSTIC_IMPLEMENTATION_CONTRACT_2026-10-03.md), revision `p4-carbon-diagnostic-2`, including section 11 clarifications.
- [Machine integration map](../build/p4_diagnostic_contract_20261003_01/integration_map.json), separating active proposed diagnostic APIs, offline preparation and inactive/forbidden runtime operations.
- [Complete equation disposition](../build/p4_diagnostic_contract_20261003_01/equation_disposition.json): all 28 earlier equations, with their original provenance records preserved.
- [Review decisions](../build/p4_diagnostic_contract_20261003_01/equation_decisions.csv): 14 retained, revised, inactive or unresolved decision groups.
- [Environment policy](../build/p4_diagnostic_contract_20261003_01/environment_policy.csv), [IO contract](../build/p4_diagnostic_contract_20261003_01/diagnostic_io.json), [output schema](../build/p4_diagnostic_contract_20261003_01/diagnostic_output_schema.json) and [five status fixtures](../build/p4_diagnostic_contract_20261003_01/status_examples.json).
- [Requirement audit](../build/p4_diagnostic_contract_20261003_01/requirement_audit.csv), [verification](../build/p4_diagnostic_contract_20261003_01/verification.json), [manifest](../build/p4_diagnostic_contract_20261003_01/manifest.json) and [future validation plan](../build/p4_diagnostic_contract_20261003_01/validation_plan.json).

The earlier [consolidated Claude handoff](CLAUDE_FSP_CURRENT_HANDOFF_2026-10-03.md)
remains a reading guide. Its statement that this continuation had pending delivery
checks describes the earlier snapshot; the evidence above records this delivery.
Past source/evidence files have not been rewritten.

## Disposition of the six required changes

| Prompt item | Result and evidence |
|---|---|
| 1 Offline versus runtime | D5 is settled: explicitly apply a frozen, hashed pack before P3 runs. Record bindings, clock, source/config hashes and embedded effects. No runtime fitting/application or exponential-to-beta coercion. Contract sections 1 and 5; machine map `offline_calibration` |
| 2 Pure diagnostic | The five-argument `compute_carbon_sufficiency` signature is retained. No geometry writes, clipping, rate multipliers, reweighting or hidden growth calls. Contract sections 1-2 and 8 |
| 3 Counterfactual equations | The prior map already contained the carbon function; no false absence claim is repeated. Its mixed API/trajectory wording is superseded by the new map. All 28 equations are classified; forward allocation/form/reserve updates remain inactive |
| 4 Complete coupling provenance | Preserve `p3_light_coupling`, all `p3_environment_paths`, frozen config and fitted-pack features. Unknown provenance means unavailable coupling audit, not an empty list proving independence. D9 compatibility and component arithmetic are separate |
| 5 Light supply versus feedback | Retain light-driven photosynthetic supply with compatible samples and basis. Prevent a second growth correction through `feedback_action=none`; do not subtract a guessed DLI contribution |
| 6 Other environment variables | CO2 has a conditional NRH calibration-domain role, with no active CO2 response law; VPD/RH/EC/pH are metadata/applicability inputs. Missing required domain evidence disables the affected component. No response coefficients were invented |

## Equations and scientific availability

The original source registry and parameter candidates remain the provenance
authority. `equation_disposition.json` preserves each source record's locator,
cultivar/conditions, evidence type, units, uncertainty and limitations. Source
facts are not target calibration. D1-D10 settle software ownership/policy, not
the following physiological choices:

| Review dependency | Current treatment |
|---|---|
| Incident/absorbed NRH and net/before-mito exchange | Unresolved; compatible reviewed interpretation or explicitly hypothetical pack required |
| Respiration ownership across organs, day and night | Exclusive accounting required; unknown overlap blocks the affected supply/budget |
| ASR multiplication/division and CH2O/CO2 units | Preserve documented source conflicts; proposed diagnostic demand is `chi*q*deltaW_P3`, not P4-generated growth. Composition and mass basis still require review |
| Root/fruit ASR ordering and structural/total mass | Original paper, code and Heuvelink evidence retained; no automatic target coefficient assignment |
| Initial masses, roots, reproduction, reserves and carbon fractions | Required by scope; missing pools do not become zeros. Whole-plant ratios remain unavailable without complete compatible accounting |
| Geometry-to-mass inversion | Conditional independently supported mapping only; dimensionless image ratios cannot produce grams, and conflicting inversions are not averaged |
| Activity, five-day history, thermal age and SLA | Candidate forms remain conditional/unresolved; no clock equivalence or missing-history fallback is invented |

The candidate growth-cost identity is used in reverse to infer demand from an
external increment, with required growth respiration reported as a cost. It is not
measured respiration or permission to realize that growth. A funded hypothetical
balance can be audited without returning a next plant state. No reserve is silently
spent repeatedly across intervals. FvCB, potential beta sinks, root-ratio allocation
and forward form generation remain inactive runtime alternatives.

No new literature was needed for these policy/contract corrections. The existing
18-source, 64-parameter evidence pack was reused with hashes. Its historical
93 regression tests, 16 synthetic bookkeeping checks and 89 delivery checks are
not tests rerun by this continuation, and establish no target biological accuracy.

## IO and availability guarantees

The exact contract names future owned files/functions and all input groups,
required metadata, units, parameter evidence, unavailable dependencies and error
conditions. It preserves the nine section-10 core outputs plus plant/trajectory/
interval/scope/hash/light metadata. Schema refinements enforce numeric known
budgets for zero-demand and complete statuses, null ratios for maintenance deficit
and zero demand, and explicit reasons. Missing/invalid science is not numerical
zero or infinity; malformed identity, units and hashes are validation errors.

Use metric one-sided area, elapsed seconds, day-to-second maintenance conversion
and sample-level nonlinear leaf exchange. Sum concurrent fixture irradiance once
before nonlinear response, and keep alternative transport replicates separate.
Never apply absorptance twice or use Shapley removal effects as incoming light.
Preserve original samples and shapes rather than attempting inverse photosynthesis.

Carbon pools remain per plant. A leaf subset may retain supported exchange
components, but its ratio additionally requires a scoped reserve/boundary budget.
Missing roots or post-terminal growth scope prevent whole-plant sufficiency.
Future P3 envelopes remain optically ineligible. Unknown coupling provenance
blocks D9 integration-readiness claims without erasing independently known fluxes.

## Inspected producer readiness

The [source snapshot](../build/p4_diagnostic_contract_20261003_01/source_snapshot.json)
captures the P3 engine, calibration source, D1-D10 and the P3 owner handoffs.
At that snapshot the engine contained beta/clock/audit helpers, while the calibration
source still contained its calendar-clock guard. The P3 execution record contained
its implementation/validation plan without a final results section. Source presence
is not completion or proof that final exports obey D9.

The verifier compares these immutable snapshots and separately records live-source
hash changes. It does not execute or edit another chat's files. Future consumers
must pin the owner-completed export/schema, including all embedded fitted effects;
they must not guess field aliases or bypass calibration-clock validation.

P2 scalar/sample timing and metric-area eligibility remain necessary. Its directional
callback completion is a separate producer task; an unavailable angular channel is
not by itself a reason to disable an otherwise supported scalar carbon calculation.
No new whole-plant real optical or physiological inputs are claimed.

## Validation scope and next actions

The delivery verifier checks the proposed JSON Schema, all five deliberately
invented status examples and invalid mutations, complete equation coverage,
environment/API separation, source hashes and requirement-to-evidence mapping.
These are specification/serialization checks. They do not simulate photosynthesis,
exercise a production diagnostic, or validate physiological coefficients.
Reproduce with `python -X utf8 build/p4_diagnostic_contract_20261003_01/verify_contract.py`
from the project root; inspect its JSON result and manifest.

Claude should return retain/revise/unresolved decisions for the 14 groups, with
exact adopted units/formulas/domains and parameter IDs. Unknown biological inputs
can remain unavailable or explicitly hypothetical. Future isolated implementation,
when invoked, must test units, carbon balance, respiration ownership, immutability,
missingness, zero demand, deficits and the other checks in the validation plan.

D3 still defers cross-project adapters and the end-to-end run. D6 allows P4
unavailable in the first numeric P1-P2-P3 pass. D7 limits round trips to reversible
representations. Completing this specification does not close those later tasks.

## Recorded delivery verification

`verify_contract.py` completed successfully: 227 specification/reference/hash
checks, including five accepted status fixtures and 34 intentionally invalid
schema mutations rejected. All 17 requirement rows are verified at specification
scope. The 28 original equation records are preserved exactly; 14 decision groups
and eight environment variables have explicit dispositions. No physiological
coefficient was adopted and no production diagnostic or model test was run.

In particular, schema validation does not establish interval/identity semantic
correctness on arbitrary future inputs or physical accounting behavior. Those
remain implementation checks in the exact contract and future validation plan.
Live-producer hashes are observations, not owner-completion evidence.

Final reinspection on 2026-10-04 found subsequent P3 source changes:
`apply_parameter_set` now calls `validate_calibration_clock` with the frozen
fit-plan `calibration_clock_reference`, records `applied_features` and checks D9.
The owner execution record reports initial passage of 93 existing regressions
and legacy numerical parity, while its broader D8-D10 delivery remains in progress.
These are owner-reported results, not additional tests run by P4. Three follow-up
source snapshots and hashes are saved in `producer_followup.json` and
`inspected_sources_followup/` within this pack. Original snapshots remain intact.
No completed versioned producer export is certified by this specification task.
