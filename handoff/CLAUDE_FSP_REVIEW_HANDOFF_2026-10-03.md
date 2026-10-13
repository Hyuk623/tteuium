# Tomato FSP calibration and physiology handoff for Claude

Date: 2026-10-03, Asia/Seoul. Author: Codex. Recipient: Claude for scientific review and the next exact implementation contract.

The growth-response calibration foundation is implemented and tested. The physiology extension is a proposed mathematical contract with recovered source evidence; its production module and carbon-sufficiency index are not implemented. Review the scientific assumptions and return actionable retain/revise/unresolved decisions. Preserve P3 as the sole owner of realized geometry and P4 as a diagnostic consumer.

This document consolidates the completed P4 work. Preparing this handoff performs no model run, fitting, new literature acquisition, integration or source-code change. Earlier verification results below are historical execution evidence, not tests rerun for this document. The current document's reference/status check is saved separately under `build/fsp_claude_handoff_20261003_01/`.

Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.
Paths below are relative to that root. Read parent `공통규약.md`, project `AGENTS.md` / `CONVENTIONS.md`, and current `handoff/LOG.md` / `handoff/TODO.md`. Handoff documents are English; user discussion is Korean. Preserve active ownership, source observations and protected `tomato3d/`, `tests/`, `config/`, and `docs/` files.

## Current decisions and reading order

1. Read `handoff/CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md`. P3 owns direction and size increments; P4 cannot alter P3 states, rates, events, weights or seeds. Linking is deferred until the independent goals finish. The first integration target is synthetic conversion correctness, not biological accuracy.
2. Read `handoff/CLAUDE_FSP_PHYSIOLOGY_CONTRACT_2026-10-03.md`, starting with section 10. It takes precedence over older replacement/override language in sections 4-7. Allocation and mass-to-form equations there are isolated counterfactual definitions, not authorization for another realized-growth engine. The contract was authored by Codex; its filename does not imply Claude approval.
3. Read `handoff/CODEX_GROWTH_CALIBRATION_EXECUTION_2026-10-03.md` and `tools/GROWTH_CALIBRATION.md` for implemented capabilities.
4. Inspect `build/fsp_physiology_spec_20261003_01/parameter_candidates.json`, `equation_registry.json`, and `source_registry.json` for actual source facts, conflicts, nulls and applicability.
5. Use `handoff/CODEX_FOUR_PROJECT_INTEGRATION_DECISIONS_REVIEW_2026-10-03.md` and the current `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md` for integration review. The light interface has progressed since the initial P4 source snapshot.

The older prompts explain requested scope: `handoff/CODEX_GROWTH_RESPONSE_CALIBRATION_HANDOFF_2026-10-03.md` and `handoff/CLAUDE_FSP_PHYSIOLOGY_ACCURACY_PROMPT_2026-10-03.md`. Their physiology-to-growth feedback wording is subordinate to the diagnostic-only decision.

## Implemented calibration foundation

| Artifact | Current behavior |
|---|---|
| `tools/growth_calibration.py` | Separate evidence validation, input/identifiability audit, explicit bounded fitting, held-out validation, parameter adapter and CLI |
| `tools/tests/test_growth_calibration.py` | Missing-input, unit/identity, fitting, uncertainty, leakage and engine-integration regressions |
| `tools/growth_calibration_evidence.json` | Literature candidate provenance; no installed crop defaults |
| `tools/GROWTH_CALIBRATION.md` | Exact schemas, fitting laws, limitations and CLI usage |
| `tools/probabilistic_compound_growth.py` | Existing P3 engine reused read-only by this task; not a new P4 growth engine |

Public calibration functions are `validate_evidence_registry`, `audit_calibration_data`, `fit_growth_parameters`, `validate_parameter_set`, `apply_parameter_set` and `export_calibration`. CLI operations are `templates`, `audit`, `fit`, `validate`, `forecast`, and `demo`. Run from project root; generated outputs require fresh `build/` paths.

Supported fitting families are `anchored_expansion`, `azimuth_rotation` and `lognormal_wait`. They are not photosynthesis, maintenance, allocation or allometry fit families. The fit plan fixes equations, fitted/fixed parameters, units, bounds, likelihood, independent assignment units, split and uncertainty. Cluster bootstrap particles preserve joint fitted-parameter dependence. Failed, boundary or locally nonidentifiable optima are rejected as calibration results.

Schema is `growth-calibration-1`. Observation inputs retain confirmed plant/organ IDs, aware timestamps, frame, coverage/age basis, measurement errors, assignment units, actual historical exposure and censoring/visibility. Lengths are mm, supported area cm2, angular observations rad, event times calendar days and growth rates inverse calendar days. CSV missing values are empty; JSON missing values are null. The engine adapter requires explicit bindings, compatible calendar clock and matching scenario/domain. Forecast does not start fitting or light calculations.

The historical offline `apply_parameter_set` capability returns a new P3 configuration and parameter particles. It is distinct from the future runtime carbon diagnostic. **Claude must specify whether D4 excludes that adapter or explicitly selects a frozen fitted pack before P3 runs.** Diagnostic-only integration must never call it implicitly. Preserve the separately requested calibration capability rather than delete it to simplify terminology.

## Verified results and their limits

| Evidence | Result | Interpretation |
|---|---|---|
| `build/growth_calibration_20261003_02/final_tests.xml` | 93 combined tests passed | Software regressions across calibration, probabilistic growth and observed-growth tooling |
| `build/growth_calibration_blank_20261003_02/` and `build/growth_calibration_missing_audit_20261003_02/` | Blank templates and unavailable audit exported | Missing science produces actionable reasons rather than invented coefficients |
| `build/growth_calibration_20261003_02/` | Integrated synthetic demonstration | 60 synthetic rows; 8 training and 4 held-out assignment units |
| `build/growth_calibration_explicit_fit_20261003_01/` | D=24.0627626396 mm, k=0.1202885048 day^-1, beta=0.2461351595 | Synthetic truths were 24, 0.12 and 0.25; not measurements of user plants |
| `build/growth_calibration_validation_20261003_01/` | Separate synthetic validation | Does not establish field/cultivar predictive accuracy |
| `build/growth_calibration_forecast_20261003_01/` | Existing engine forecast from explicit parameters | Assumption-conditioned; no automatic domain acceptance |
| `build/fsp_physiology_spec_20261003_01/worked_example.json` | 16 bookkeeping checks passed | Synthetic dimensional/carbon proof, not a production integrator |
| `build/fsp_physiology_spec_20261003_01/verification.json` | 89 delivery/reference/hash checks passed | Recorded verification of that delivery snapshot |

All delivered fitted parameter sets retain `accepted_for_domain=false`. The earlier `build/growth_calibration_missing_audit_20261003_01/` attempt failed during export; use the corrected `_02` result above. Do not interpret a folder's existence as successful execution.

## Physiology contract and evidence package

The proposed contract covers exclusive respiration ownership, carbon supply, maintenance, reserve balance, organ demand, growth cost, conditional mass/form relations, initialization, event material, numerical grids and independent validation. Proposed functions include `audit_physiology_inputs`, `compute_leaf_exchange`, `compute_respiration`, `allocate_carbon`, `update_form`, `advance_physiology`, `audit_carbon_balance`, and diagnostic-only `compute_carbon_sufficiency`.

There is no implemented `tools/fsp_physiology.py` in this delivery. Do not interpret function names in a JSON map as callable production code. Proposed model/schema version is `fsp-physiology-1`; current calibration's optimizer cannot silently acquire physiology targets.

The evidence directory `build/fsp_physiology_spec_20261003_01/` contains:

| File | Purpose |
|---|---|
| `source_registry.json` | 18 source records, access history, local hashes and transfer limitations |
| `equation_registry.json` | 28 source/proposed equations, units, roles and limitations |
| `parameter_candidates.json` | 64 records: 52 recovered candidates and 12 explicit unidentified target inputs; unknown uncertainty remains null |
| `coefficient_summary.csv` | Compact value/unit/evidence/limitation inventory |
| `unit_accounting.csv` | Stocks, fluxes, signs, owners and conversions |
| `organ_state_schema.json` | Proposed organ/root/reserve state and semantic invariants |
| `input_requirements.csv` | Exact missing evidence per calculation |
| `integration_map.json` | Inspected existing interfaces versus proposed functions and ownership |
| `validation_plan.json` | Separate module/trajectory evidence, software invariants and deferred biological acceptance |
| `worked_example.py` and `worked_example.json` | Reproducible synthetic arithmetic example |
| `known_real_input_audit.json` | Existing T1 evidence limits without another data search |
| `requirement_audit.csv`, `verification.json`, `manifest.json` | Delivery scope, verification and hashes |

The dwarf paper is available at `build/growth_calibration_20261003_01/dwarf_fsp_source.pdf`. Its model uses Heartbreakers F1 Twiggy Red, which is not confirmed as the user's cultivar. The official code/input snapshot is pinned to commit `2d727a3364f87392b3f8b74d8ff7127cc5090c3a` and saved in the evidence pack's `sources/` directory. `sources/heuvelink_thesis.pdf` and `sources/farquhar_1980.pdf` are also available. The digital-twin paper is cached at `build/probabilistic_compound_design_20261003/tomato_digital_twin.pdf`.

Earlier full-text failure for the dwarf paper is resolved. Publisher supplementary material and current TGFS full-text access remain limited as recorded; no author contact or access-control bypass occurred. The retrieved official input CSV is not claimed identical to the inaccessible supplement.

## Scientific choices requiring a decision

| Priority | Review item | Evidence and requested decision |
|---|---|---|
| P0 | NRH exchange definition | Source has no Rd intercept and calls the argument absorbed PAR, whereas gas-exchange fitting used chamber incident light. Decide the matching incident/absorbed and before-mito/net interpretation before using Pmax=27, alpha=0.06, theta=0.7. Do not turn the paper's point conditions into an invented validity range. |
| P0 | Respiratory ownership | Select one route. Before-mito supply includes photorespiration but excludes mitochondrial costs; charge maintenance/growth once downstream. A net-leaf route requires a phase/organ/component ledger identifying exactly what is already subtracted. Rd is not automatically organ maintenance. |
| P0 | Growth cost and composition | Paper equations 15-16 conflict dimensionally with ASR>1; code divides substrate by ASR. Review `deltaW=F/(chi*q)` and `Rgrowth=F-c*deltaW`, requiring `0<c<=chi*q`. Carbon fractions are still missing; do not derive them from molecular masses. |
| P0 | Source units and organ coefficients | Paper maintenance is gCH2O/g structural DM/day; CSV comments say gCO2/g plant mass/day. Heuvelink printed p109/PDF p114 confirms CH2O and root/fruit ASR 1.39/1.37; CSV labels reverse the latter pair. Original DM versus structural/minimum-pool mass still needs reconciliation. |
| P0 | Initialization and organ scope | Require initial structural masses, root/reproductive scope, reserve and uncertainty. Photos and relative area cannot establish these pools. Missing nonfoliar assimilation needs an explicit approximation or an unavailable whole-plant claim. |
| P0 | P3 geometry to demand | Decide which independently supported mass/form inversion is identifiable. Leaf blade versus rachis/petiole partition, new-organ mass, roots and any reproductive demand must be explicit. Inconsistent area/length inversions cannot be silently averaged. |
| P1 | Activity and development | Source f=33 needs day units with RGR in day^-1. Review five-day history, startup/negative-growth handling, thermal-time origin and temperature domain. Tbase=5.7 is borrowed, not target calibrated. |
| P1 | Sink and reserve hypotheses | Review proportional capped potential demand, root ratio, no deferred catch-up, finite/unbounded scenario storage and failure on deficit/overflow. No silent clipping, excess deletion or invented starvation/remobilization. |
| P1 | Variable SLA and anchoring | Review `A=A0+s(t)W(t)-s0W0`, supported area scope and rank/age/light dependence. Source density relation does not prove a universal constant SLA. Preserve measured geometry exactly at origin. |
| P1 | Independent acceptance | Define practical thresholds and held-out plant/cultivation-unit comparisons. Match future environmental information across models. Synthetic tests establish no biological accuracy gain. |

The proposed primary empirical model is a conditional nonrectangular hyperbola, with a linear low-light comparator. FvCB remains deferred until capacities, chloroplast CO2/conductance and temperature responses are identifiable. Ambient CO2 must not silently equal chloroplast CO2. Foreign-cultivar/source-model coefficients remain candidates, with separate applicability review.

## Diagnostic carbon sufficiency contract to review

Use gC, seconds and metric one-sided tissue area. `1 umolCO2 = 12.011e-6 gC`; `chi=12.011/30.026 gC/gCH2O` is the declared carbohydrate-equivalent conversion. Biological structural carbon fraction `c` is separate. Convert source day-based maintenance by `dt_s/86400` and account for darkness.

For a coherent P3 trajectory/plant/interval, the proposed diagnostic uses:

```text
S = integrated compatible leaf exchange [gC]
U = reserve + S + import - export - maintenance_charged_here [gC]
V = max(U - minimum_reserve, 0), only if U >= 0 [gC]
D = sum(chi * ASR_o * inferred_structural_increment_P3_o) [gC]
ratio = V / D, only if U >= 0 and D > 0
```

Negative U reports maintenance deficit and a null ratio. D=0 reports `no_growth_demand` and a null ratio. Missing evidence gives unavailable. A ratio is conditional on its assumptions; it never scales or clips P3 growth. Proposed output fields are `available_growth_carbon_gC`, `required_growth_carbon_gC`, `sufficiency_ratio`, `maintenance_deficit_gC`, `growth_deficit_gC`, `status`, `limiting_inputs`, `assumptions`, and `source_hashes`. Preserve trajectory identity/weight and per-plant pools.

Observation re-anchoring is an estimate correction, not photosynthetic uptake or physical import. Initial/future P3 envelopes remain `optical_eligible=false` and `suitable_for_ppfd=false`. First-leaf=1 ratios remain dimensionless image comparisons, not metric area or gC inputs. Nonlinear leaf exchange must be evaluated before spatial aggregation when supported samples exist.

## Updated integration status and corrections

The current machine map now includes `compute_carbon_sufficiency` and an explicit `coordination` block assigning realized growth to P3. Thus the earlier review's specific claim that this function is missing from `integration_map.json` is stale. No prior review was rewritten. Earlier counterfactual trajectory wording remains in parts of the map/contract; the next adopted implementation contract should remove ambiguity by listing active diagnostic APIs separately from inactive counterfactual analysis.

P3 already has environment/light paths through conditional families, stopping, the development clock and calibrated parameters. The integration review reports that current `environment_used`/`light_used` flags describe clock coupling rather than every path. Inspect the complete frozen configuration; those flags alone cannot prove independence or rule out double counting.

P2 now supplies the additive `light-growth-1` interface described in `tools/LIGHT_GROWTH_BRIDGE.md` and `tools/light_growth_schema.json`; the latest cited package is `build/light_growth_readiness_20261003_04/`. Spatial samples, side/scalar light, time intervals, area and reversible reporting transforms are implemented according to its handoff. Its remaining angular transport hook is blocked on the protected core owner. Scalar carbon diagnostics and directional-response readiness have different prerequisites; do not make an unsupported angular result necessary for an otherwise scoped scalar calculation, or claim complete readiness from the scalar subset.

For future adapters, preserve plant instance versus source plant, compound/leaflet mapping, `trajectory_id`, timestamp/interval, geometry hash, frame, area basis, backend, replicate, uncertainty and missingness. m2 to cm2 is *10000; mm2 to m2 is *1e-6. Absorbed PPFD already includes absorptance. Flux in umol/s, density in umol/m2/s and time-integrated dose are distinct. Keep original samples/shapes for lossless interchange; aggregation, photosynthesis and forecasting are not invertible transformations.

No P1-P2-P3-P4 end-to-end run has been performed by this task. Do not start linking while the coordination decision defers it.

## Known missing real inputs

The saved T1 audit has five candidate regions and zero eligible full observed states. Reasons include unconfirmed temporal identity/attachment/frame, missing whole rachis/extents/tissue area and missing capture time. Repeated observations were confirmed absent; do not search the project again for an already-known missing dataset.

Real calibration needs confirmed longitudinal identities and comparable observations, error models, actual exposure histories, replicated assignment units, a reviewed identifiable fit plan and separate later targets. Absolute physiology additionally needs compatible metric tissue/light time coverage, organ masses including roots, initial reserves, carbon fractions, yields and respiratory accounting. Use published or separately collected references consistent with the non-destructive project preference; this handoff authorizes no destructive sampling or experiment.

## Requested Claude response

Return a new English review handoff, suggested path `handoff/CLAUDE_FSP_REVIEW_RESPONSE_2026-10-03.md`, with a Korean explanation to the user. This is a requested review deliverable, not an already-existing file or automatic message to another chat.

1. Give a retain/revise/unresolved verdict for each scientific decision above. Cite source equation/table/page and distinguish recovered source facts, proposed adaptations and remaining hypotheses.
2. State which parameters can be used only as named assumptions, which need target evidence, and whether every chosen unit/mass/respiration basis is compatible. Never label literature values target calibrated.
3. Freeze P4's diagnostic-only input/output/error contract, organ scope, zero-demand/deficit semantics and whether offline calibration is included in the later integration plan.
4. Return a prioritized Codex implementation contract: exact owned file/function, input/output fields and units, equations, unavailable behavior and meaningful acceptance checks. Keep counterfactual geometry routines inactive unless a separate decision changes ownership.
5. List minimal external evidence by blocked calculation and owner; distinguish it from software work that can proceed with explicitly synthetic fixtures. Keep whole-plant and partial-scope diagnostics distinct.
6. Identify any remaining discrepancy between prose and machine-readable interfaces. Preserve previous evidence and append decisions; do not edit another active chat's implementation.

The next code stage, if separately invoked, should implement the reviewed isolated diagnostic with unit/carbon/immutability checks before deferred cross-project integration. The present task delivers this review entry point only.
