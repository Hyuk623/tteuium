# Dwarf tomato FSP review handoff for Claude

Date: 2026-10-03. Author: Codex. Recipient: Claude for scientific review and an
actionable implementation handoff.

The user wants a dwarf-tomato FSP model connecting light interception,
photosynthesis and organ biomass accounting. Existing growth/calibration tools
and light interfaces provide foundations. Production physiology and biological
validation remain incomplete. Under the adopted coordination decisions, P3 owns
realized growth and P4 diagnoses whether its implied carbon demand is supported.

Use this document as the current reading entry point. It updates the review queue
without rewriting prior evidence or adopting new biology. Preparing it performs
no model execution, fitting or cross-project integration.

Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.
All links below are relative to this handoff directory. Read the parent
`공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, then current LOG/TODO.
Keep handoffs English and user explanations Korean. Preserve other active chats'
files, protected core/configuration and human observations.

## Reading order and precedence

| Order | Document | Use |
|---|---|---|
| 1 | [Integration decisions D1-D10](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md) | Adopted ownership, calibration, environment and determinacy decisions; takes precedence over older proposals |
| 2 | [P4 diagnostic implementation contract](CODEX_P4_DIAGNOSTIC_IMPLEMENTATION_CONTRACT_2026-10-03.md) | Latest proposed files, functions, inputs, units, status rules and future tests; not an implemented or scientifically approved module |
| 3 | [Earlier physiology contract](CLAUDE_FSP_PHYSIOLOGY_CONTRACT_2026-10-03.md) and [earlier review handoff](CLAUDE_FSP_REVIEW_HANDOFF_2026-10-03.md) | Source derivations, recovered evidence and historical results; read section 10 before older growth/allocation sections |
| 4 | [Calibration execution](CODEX_GROWTH_CALIBRATION_EXECUTION_2026-10-03.md) and [calibration API](../tools/GROWTH_CALIBRATION.md) | Implemented evidence audit, explicit fitting, validation and parameter application |
| 5 | [P3 adopted changes](CODEX_P3_GROWTH_DECISIONS_IMPLEMENTATION_HANDOFF_2026-10-03.md) and [P3 execution record](CODEX_P3_GROWTH_DECISIONS_EXECUTION_2026-10-03.md) | Producer changes and their actual delivery state; the inspected execution record contains a plan, not final validation results |

The four original user-supplied references were successfully read in full from
the local filesystem. Their role and age must remain explicit:

| Reference | Interpretation |
|---|---|
| [Leaf area handoff](CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md) | Supported geometry/area and dimensionless first-label ratios; ratios are not metric tissue area |
| [Growth IO brief](CODEX_GROWTH_IO_BRIEF_2026-10-03.md) | Original proposed IO; its statement that probabilistic implementation is absent is historical. Consult later execution records |
| [Light IO summary](CODEX_LIGHT_IO_SUMMARY_2026-10-03.md) | Existing hierarchy and appended light-growth interface updates, physical units and remaining angular dependency |
| [Growth calibration request](CODEX_GROWTH_RESPONSE_CALIBRATION_HANDOFF_2026-10-03.md) | Original implementation scope; use the later calibration execution record for achieved results |

## Settled decisions to preserve

- **D1-D2:** P3 alone changes geometry, size, events and trajectory distributions.
  Runtime P4 is read-only: no rate multiplier, clipping, state overwrite,
  reweighting or second realized-growth engine. Allocation/form equations retained
  from older work are inactive counterfactual analyses.
- **D5:** Offline `apply_parameter_set` is included before P3 starts, using an
  explicitly selected frozen, hashed pack. No implicit fitting/application during
  runtime diagnostics. The earlier handoff's question about including this route
  is settled; do not reopen it as an unresolved design choice.
- **D8-D9:** Existing age-unknown organs retain exponential remaining expansion;
  newborn organs may use the adopted beta decoder. Temperature enters a normalized
  development clock, and fixed-horizon DLI enters size targets only. CO2, VPD/RH,
  EC and pH do not enter P3 response equations. No conversion of exponential fitted
  coefficients into beta coordinates is implied.
- **D10:** Preserve per-trajectory node budgets, truss/terminal events with null
  geometry and unavailable post-terminal scope. An event count supplies no biomass.
- **D3-D4-D6-D7:** Linking remains deferred. The first synthetic pass requires
  numeric P1-P2-P3 results; P4 may be unavailable with reasons. Round-trip reversible
  representations; check model computations and reductions in the forward direction.

P4 must retain photosynthetic light supply even when P3 uses DLI. Prevent duplicate
growth correction by prohibiting feedback, not by deleting physical photosynthesis.
Consume complete `p3_environment_paths` and `p3_light_coupling` with frozen-pack
provenance when the producer supplies them. Legacy clock-only flags cannot prove
the absence of embedded environmental effects.

## Delivered evidence and unfinished work

| Component | Evidence and limit |
|---|---|
| Growth calibration | Historical 93 combined regression tests and explicit synthetic fit/validation/forecast are recorded in the calibration execution handoff. This document reruns none of them; target-cultivar acceptance is not established |
| Physiology evidence | [Earlier evidence pack](../build/fsp_physiology_spec_20261003_01/verification.json) records delivery checks; [source registry](../build/fsp_physiology_spec_20261003_01/source_registry.json), [equations](../build/fsp_physiology_spec_20261003_01/equation_registry.json) and [parameter candidates](../build/fsp_physiology_spec_20261003_01/parameter_candidates.json) retain provenance and unknowns |
| Latest P4 draft | [Continuation execution brief](CODEX_P4_CONTINUATION_EXECUTION_2026-10-03.md) still reports pending delivery checks. [Draft machine map](../build/p4_diagnostic_contract_20261003_01/integration_map.json), [equation decisions](../build/p4_diagnostic_contract_20261003_01/equation_decisions.csv) and [output schema](../build/p4_diagnostic_contract_20261003_01/diagnostic_output_schema.json) exist, but are not a completed verified delivery |
| P2 directional light | [Core callback contract](CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md) remains a producer dependency according to the latest inspected summary. Prepared callback fixtures do not prove real transport wiring. Scalar exchange has separate prerequisites |
| Real inputs | Confirmed repeated observations and independently supported mass/reserve/whole-plant optical inputs remain missing as recorded. Do not repeat broad searches for data already confirmed absent |

The older claim that the physiology machine map lacks `compute_carbon_sufficiency`
was already corrected in the earlier review handoff. The remaining task is
consistency and validation of the latest active-versus-counterfactual contract.
Do not mark another chat's in-progress work complete from source-file presence.

## Scientific review requested from Claude

Use [unit accounting](../build/fsp_physiology_spec_20261003_01/unit_accounting.csv)
and the source registries, rather than treating candidate numbers as defaults.
The [dwarf paper](../build/growth_calibration_20261003_01/dwarf_fsp_source.pdf)
is accessible locally; its reported cultivar is not confirmed as the user's cultivar.

| Priority | Decision needed | Required outcome |
|---|---|---|
| P0 | Photosynthesis light and exchange basis | Resolve incident versus absorbed PAR and net versus before-mitochondrial exchange for NRH. Match the parameter calibration basis; no duplicate absorptance |
| P0 | Respiration ownership | Declare which components are included in leaf exchange and which are charged downstream. Avoid counting maintenance or growth respiration twice |
| P0 | ASR, mass and source conflicts | Reconcile paper equations 15-16 against code division by ASR, CH2O versus CSV CO2 comments, and root/fruit coefficient ordering. Heuvelink evidence does not establish target applicability or settle structural versus total mass |
| P0 | Organ demand and initial pools | Specify supported geometry-to-structural-DM mappings, blade/rachis/petiole partition, roots, reproduction, new-organ material, carbon fractions and initial reserves. Unknown pools remain unavailable |
| P1 | Temperature, activity and SLA | State equation/time basis, applicable domain and evidence for Q10/activity/history and changing SLA. Do not invent temperature, CO2, VPD/RH, EC or pH multipliers |
| P1 | Independent evaluation | Separate arithmetic/software checks from held-out physiological evidence. Specify practical acceptance targets without validating P4 against the same P3 prediction it diagnoses |

For each item return **retain / revise / unresolved**, exact source equation/table/
page, units, mass/respiration basis, applicability and parameter IDs. An unresolved
dependency disables its calculation; it does not imply fabricated defaults or
blanket suspension of unrelated software work. Keep FvCB and active allocation/
form generation deferred unless separately adopted.

## Required diagnostic behavior

The proposed API is
`compute_carbon_sufficiency(p3_interval, carbon_state, light_series, environment, parameter_pack)`.
It preserves plant instance, trajectory identity/weight and interval. Use gC,
elapsed seconds and one-sided metric tissue area. Evaluate nonlinear exchange per
supported sample before spatial aggregation. Absorbed PPFD already includes absorption.

Return `available_growth_carbon_gC`, `required_growth_carbon_gC`,
`sufficiency_ratio`, `maintenance_deficit_gC`, `growth_deficit_gC`, `status`,
`limiting_inputs`, `assumptions`, and `source_hashes`, with identity/scope metadata.
Maintenance deficit and zero demand give null ratios; missing scientific evidence
gives explicit unavailable reasons. Preserve independently supported component
results. A partial leaf budget needs its own justified reserves and boundary flows
and must not be labelled a whole-plant result. Future P3 envelopes remain
optically ineligible.

## Claude return document

Please write a new English review response, with a Korean explanation for the user.
Include the decisions above and a prioritized exact Codex contract: owned file,
function, inputs/outputs, units, formulas, missingness, scope and acceptance checks.
Review the latest P4 draft for prose/schema/status consistency before adopting it.
Separate adopted D1-D10, proposed physiological assumptions and unresolved evidence.

The expected next step is the reviewed isolated diagnostic implementation when
explicitly invoked; deferred cross-project linking is a separate task. This handoff
does not authorize an experiment, new parameter defaults or edits to active P3/P2 code.

## Subsequent P4 specification completion

The pending P4 delivery-check status above is superseded by
[P4 continuation review and delivery](CODEX_P4_CONTINUATION_REVIEW_2026-10-03.md).
The proposed diagnostic contract and its machine pack now pass 227 specification,
schema and reference/hash checks, covering 17 requirements. This completes the
requested review/contract work; production physiology and Claude's scientific
decisions remain outstanding. Start the P4 technical review with that report and
the exact diagnostic contract, while retaining the scientific questions above.

## Authorized implementation completed on 2026-10-04

The user subsequently requested code/model changes. The isolated P4 diagnostic is
now implemented; read [the implementation handoff](CODEX_P4_IMPLEMENTATION_HANDOFF_2026-10-04.md)
and [runtime guide](../tools/FSP_CARBON_DIAGNOSTIC.md) for the actual callable model,
input representation and current evidence. This supersedes the earlier statements
that no production diagnostic exists. P3 also completed its D8-D10 software
delivery; P4 inspected its saved coupling metadata without running/linking it.

Results: 78 tests, 11 CLI commands, nine hypothetical cases, and 196 delivery checks
covering 24 software requirement groups. P4 remains diagnostic-only; scientific
review and target biological validation are still open. Source-cultivar values
were not installed as defaults. Cross-project adapters/integration remain deferred.

Final implementation refinement: parameter-pack scope is now enforced explicitly;
the final regression count is 79 and current executed cases are under
`build/p4_implementation_20261004_01/final_04/`. Earlier 78-test/final_03 records
remain historical. The implementation handoff and manifest identify current files.
