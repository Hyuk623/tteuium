# Literature grounded physiology extension for the tomato FSP

Date: 2026-10-03. Recipient: Claude for scientific design/review, producing an implementation-ready contract for Codex and the ongoing FSP work. User objective: establish units and respiration accounting, select a photosynthesis model, obtain organ respiration/allocation coefficients, and connect dry matter to geometry to improve prediction accuracy.

This file is a prompt, not completed scientific design, adopted parameter values or an implementation. Its authoring changed no model code and ran no fitting, training, photosynthesis or light simulation.

## Task and required result

Develop a source-backed physiological extension to the current dwarf tomato FSP. Complete the mathematical and parameter contracts for this chain:

```text
Eligible organ light and metric leaf area plus environment
    -> photosynthetic carbon assimilation
    -> respiration accounting and nonstructural carbon storage
    -> organ carbon demand and allocation
    -> structural dry matter increments
    -> leaf area and stem/leaf dimensions
    -> existing FSP state and forecast interfaces
```

Deliver explicit equations, units, source-linked candidate coefficients, applicability/uncertainty, missing-evidence gates, integration interfaces and an independent accuracy-comparison plan. Do not stop at a bibliography, a generic list of models or empty parameter templates when a value is actually recoverable from an inspected source. Distinguish recovered literature values from target-cultivar calibrated values; never fabricate either.

Accuracy improvement is a hypothesis to test, not a promised outcome of adding complexity. Compare with the existing growth model and simpler photosynthesis alternatives. Retain the existing default behavior until the new version is evaluated for its stated domain.

This prompt is a scientific specification task. Produce the contract and review decisions first; implementation belongs to the receiving Codex task within its authorized scope. Do not modify currently active growth files, start experiments, train models, execute remote/native jobs or contact authors while preparing the specification.

## Current project and constraints

Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.

Read parent `공통규약.md`, project `AGENTS.md` / `CONVENTIONS.md`, recent LOG and relevant TODO. Preserve active file ownership, human records, raw data and original configuration. Write English handoff artifacts, Korean user explanations. Tables are CSV; configuration, equations, evidence and provenance metadata are JSON. Generated research outputs belong to fresh `build/` directories.

Read these contracts and current execution briefs:

- `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md`.
- `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md`.
- `handoff/CODEX_GROWTH_IO_BRIEF_2026-10-03.md`.
- `handoff/CODEX_GROWTH_CALCULATOR_HANDOFF_2026-10-03.md`.
- `handoff/CODEX_GROWTH_RESPONSE_CALIBRATION_HANDOFF_2026-10-03.md`.
- `handoff/CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md`.
- `handoff/CODEX_GROWTH_CALCULATOR_EXECUTION_2026-10-03.md` and `handoff/CODEX_GROWTH_CALIBRATION_EXECUTION_2026-10-03.md`.

Read-only inspection during prompt preparation found `tools/probabilistic_compound_growth.py` and `tools/growth_calibration.py` already present, with execution briefs still in progress. Recheck actual status and interfaces; do not assume their existence means verified completion. The calibration source currently supports `anchored_expansion`, `azimuth_rotation` and `lognormal_wait`, not physiological parameter estimation. Its units and optimizer cannot silently be reused for photosynthesis/respiration targets.

This task explicitly extends the earlier exclusion of mechanistic photosynthesis and carbon allocation. Include nonvisual root and reproductive carbon pools when required for a whole-plant balance; this does not require root 3D reconstruction or a fruit-quality/yield product. Retain existing optical and identity gates. Existing future CompoundLeaf envelopes are not optical leaf tissue.

The latest geometry handoff includes first-labelled-leaf image-area ratios with reference value 1. These are dimensionless, per-image detection comparisons, not metric area or confirmed cross-view organ identity. They cannot establish absolute absorbed flux, gC per plant, organ dry mass or SLA. Relative scenarios may be specified separately, but absolute physiology remains unavailable until metric scale and area/identity evidence exist. Do not silently assume a reference leaf size.

## Source starting points and verification standard

Use primary papers, supplements, original parameter sources and official code where available. Inspect the equations and units rather than adopting search snippets. Record source version and exact equation/table/page, including distinctions between measured, fitted, borrowed and assumed quantities.

| Source | Why inspect it | Verified scope and transfer limit |
|---|---|---|
| [Farquhar, von Caemmerer and Berry 1980](https://doi.org/10.1007/BF00386231); [accessible paper copy](https://biocycle.atmos.colostate.edu/Documents/SiB/Farquhar_1980.pdf) | C3 assimilation, photorespiration and mitochondrial respiration definitions | Foundational model, not dwarf-cultivar coefficients. Original paper inspected in this conversation. |
| [Dwarf tomato FSP, diaf024](https://doi.org/10.1093/insilicoplants/diaf024); [institutional record](https://research.wur.nl/en/publications/a-functionalstructural-plant-model-for-dwarf-tomato-ideotype-iden/) | Directly relevant architecture, organ physiology and allocation framework; compare its photosynthesis choice with FvCB | Abstract/indexed methods were accessible; direct full-text/PDF requests failed during this preparation. Do not claim verified equations or table values until recovered. |
| [Tomato FSP digital twin, diaf022](https://doi.org/10.1093/insilicoplants/diaf022); [institutional PDF](https://edepot.wur.nl/706749) | Photosynthesis coupling, parameter fitting, potential growth and geometric relationships | Cached full author/institution PDF is available locally. Baseline uses Merlice, not the unspecified target dwarf cultivar. Section 2.3 reports changing mass/geometry relationships and separate area/elongation fitting. |
| [TOMGRO model description, Dayan et al. 1993](https://doi.org/10.1016/0308-521X(93)90024-V) | Carbon balance, maintenance/growth respiration and relative sink demand | Abstract supports the architecture; full text was unavailable during this preparation. Indeterminate-tomato parameters require transfer review. |
| [TGFS, Zhou et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10186270/), DOI `10.1093/hr/uhad045` | Leaf gas exchange, nonstructural carbon, organ growth and carbon allocation | Article accessible during preparation. Its crop, water/nitrogen treatments and broader fruit model do not directly validate this indoor dwarf project. |

The cached digital-twin source is `build/probabilistic_compound_design_20261003/tomato_digital_twin.pdf`, with extracted text alongside it. SHA256 verified during this preparation: `a950a3458d902bf0d7c142ce202f5db48d9bc81fa1c2ca3e62daca626887e49b`. Reuse it rather than treating the current remote fetch failure as missing local evidence. Do not assume supplements were cached too.

Produce a model/evidence decision table comparing the actually inspected alternatives. Clearly distinguish source facts, proposed adaptations and unresolved hypotheses. Retain access failures and incomplete evidence; fill no coefficient from memory or an unrelated species merely to make the model run.

## Work package 1 Units and respiration ownership

Propose one canonical internal carbon basis, preferably gC, and explicitly map every source parameter into it. Keep gDM, gCO2, gCH2O-equivalent and fresh mass distinct. Define structural versus total dry mass and nonstructural reserves so the same stored carbohydrate is not counted twice in biomass.

Specify variables, signs, time basis and compartment ownership in a unit/accounting table. Use seconds for exchange-rate integration, explicit calendar/development clocks for phenology, metric one-sided tissue area and signed net assimilation. Never use a daily dose as an instantaneous PPFD or mix thermal days with seconds.

For verified conversion only, `1 umol CO2` corresponds to `12.011e-6 gC`; `1 cm2 = 1e-4 m2`, `1 mm2 = 1e-6 m2`. Source respiration rates per day must be converted to the actual integration interval. CH2O is a stated carbohydrate equivalent, not the composition of all biomass. Molar conversion constants do not supply biological carbon fractions or growth yields.

Require an explicit `respiration_accounting` mode with mutually exclusive routes:

- Before-mitochondrial-respiration assimilation: photosynthesis supply already accounts for photorespiration; organ maintenance and growth costs are charged once downstream.
- Net-leaf-assimilation input: the leaf respiration already included must be recorded and excluded from downstream overlapping costs. Root/stem/fruit and any genuinely unaccounted costs remain explicit.

Choose a coherent route for the selected model; do not combine leaf net assimilation with all-organ respiration without a reconciliation. Leaf day respiration is not automatically identical to a maintenance coefficient on leaf dry mass. Restoring `Rd` to a net-assimilation output is valid only when it is the matching model component and the replacement respiration accounting is justified. Dark-period respiration must be defined explicitly; no day-only ledger may claim a full daily carbon balance.

The minimum balance to enforce is the accounting identity below, not an empirical growth law:

```text
delta(storage_C) + delta(structural_C)
    = photosynthetic_supply_C - respiration_charged_here_C
      - external_export_C + external_import_C
```

Define whether abscission, harvest, exudation and remobilization are included, absent by a stated stage assumption, or unavailable. Internal transfers cancel at plant scale. Keep per-plant pools separate: neighboring plants exchange light context, not carbon. Negative budget, unmet maintenance and depletion require named handling; do not silently clip a deficit to zero, create negative reserve pools, or infer starvation/remobilization rules without evidence.

ATP and radiation energy are not required intermediate states for this version. If an energy display is later desired, declare spectral photon-energy conversion and chemical-energy assumptions separately; neither replaces carbon conservation.

## Work package 2 Select and specify the photosynthesis model

Compare a source-supported empirical light-response model, such as an appropriate nonrectangular hyperbola, with FvCB and the actual dwarf-tomato paper's implemented choice. Select the least complex model justified by the intended conditions and available identifiable parameters. Retain a simpler model for comparison. Do not assume FvCB improves forecasts merely because it is more mechanistic.

For every alternative, state whether its response is gross carboxylation, assimilation after photorespiration, or net of mitochondrial respiration. Specify whether the light argument is incident or absorbed photons and whether quantum yield already contains absorptance/photosystem allocation. Prevent double application of absorption factors.

If choosing FvCB, write the exact supported version and equations for the active limitations, electron transport, temperature responses and respiration. Include TPU only if justified for the target domain. Define `Ca`, `Ci`, `Cc`, gas-pressure/concentration units, O2, stomatal/boundary-layer/mesophyll treatment and convergence. Ambient CO2 cannot silently equal chloroplast CO2. A fixed Ci/Ca or infinite-mesophyll-conductance approximation is a labelled assumption with a valid domain.

If choosing an empirical curve, specify the fitted light/temperature/CO2 domain and how other environment variables enter. A curve measured at one temperature and CO2 level does not identify their response functions. Missing responses remain inactive, not arbitrary multipliers.

Use leaf temperature when supported; otherwise label air-temperature substitution and assess its effect. Record leaf age/rank or acclimation effects only where evidence supports their form and coefficients. VPD, water stress, EC and pH are not independent direct multipliers unless a reviewed response links them to the selected model.

Calculate photosynthesis on supported receiving tissue at sufficient spatial/temporal resolution, then aggregate. Nonlinear response to mean PPFD is not generally equal to the mean response. Define the aggregation approximation when only compound-level mean light exists. Missing/zero tissue area and the current full-output light snapshot must not become an inferred whole-day, whole-plant supply.

Supply the exact conversion of area-based CO2 exchange into organ/plant gC per integration step, with lights-off, missing-time, high/low-domain and signed-exchange behavior. Numerical tolerances and timestep convergence are separate from biological accuracy.

## Work package 3 Organ respiration and allocation parameters

Recover source-linked candidates for organ-specific maintenance rates and temperature response, growth conversion efficiency or explicit growth costs, potential organ demand, nonstructural storage and carbon fraction. Cover leaves, stem, roots, and reproductive demand only when relevant to the declared stage. A missing root/fruit pool is not silently zero; a seedling-only model must declare its scope.

Record units carefully: a coefficient per g structural DM, per g total DM, per organ area or per gC is not interchangeable. Document reference temperature, organ age, composition, day/night conditions, cultivar and estimation method. Do not substitute fresh mass for dry mass without a source-backed dry-matter fraction and uncertainty.

Choose exactly one growth-cost convention. If substrate-to-biomass yield already includes growth respiration, do not charge it again. For example, the following is a proposed bookkeeping relationship to review and define fully, not an adopted coefficient set:

```text
F_o = substrate carbon consumed by organ growth [gC]
delta_Wstr_o = Y_o * F_o [g structural DM]
growth_respiration_C_o = F_o - carbon_fraction_o * delta_Wstr_o
```

This relationship assumes the unretained growth substrate leaves as respiratory carbon; any alternative loss/storage pathway needs its own term. Enforce compatible composition/yield bounds. Do not multiply an existing realized-growth curve by another yield factor without deriving the mapping.

Specify source-supported potential demands and the allocation rule: their temporal/thermal age, sink units, caps, competition, zero-demand case and excess-carbon storage. A mass-weighted allocation default is not automatically a physiological sink law. State whether a single well-mixed plant pool is sufficient or a transport limitation is necessary; do not add a transport network without evidence.

Initial organ masses, reserve carbon and their uncertainty are required state inputs. 3D measurements alone do not establish these pools. Unknown initial values may support labelled sensitivity scenarios but not a unique real-plant balance. Do not make local carbon stores identical across plants as an unnoticed initialization shortcut.

## Work package 4 Connect dry matter to form

Determine whether the evidence supports a mass-to-geometry relation, a stage-dependent allometry, or separate development-driven expansion with an explicit carbon constraint. Do not force one constant SLA across leaf ranks/ages because it is easy to implement. The digital-twin paper's section 2.3 provides a reason to test this assumption rather than treat it as universal.

If using `leaf_area = SLA * leaf_dry_mass`, define total versus structural leaf mass, SLA units, organ/rank/age/light dependence and applicable range. If SLA changes, the area increment is not simply `SLA * delta_mass`; account for the changed relationship or use the chosen expansion model. Keep true tissue area separate from projected pixels, partial supported area, envelope area and first-leaf ratios.

For stem length/diameter and leaf length/width, provide source-backed equations, parameters and uncertainty, including volume/density assumptions if used. Distinguish hydration-driven shape/size from dry-matter accumulation. Do not use fresh-mass or projected-area changes as interchangeable structural growth.

Preserve the measured FSP state exactly at the forecast origin. A literature allometry must not snap the observed geometry to a generic plant. Specify reconciliation of inconsistent measured mass/geometry as measurement uncertainty or a documented initialization issue, not silent data repair. Use a derived remaining-growth/anchoring contract with explicit state and parameter semantics.

Carbon supply can constrain expansion; it does not define azimuth or elevation. Preserve the existing direction/appearance subsystem and its evidence limits. If birth geometry consumes structural material, account for that mass in the event rather than creating tissue without cost. Any carbon effect on appearance timing, stop events, branching or direction needs its own evidence-backed rule.

Future CompoundLeaf envelopes still cannot be sent to the optical solver as leaf tissue. Distinguish fixed-light physiology scenarios from a genuinely coupled geometry-light-growth loop. The latter additionally needs an eligible future optical-tissue contract; do not claim this physiology work supplies it.

## Work package 5 Integrate with the running FSP

Inspect `tools/probabilistic_compound_growth.py`, `tools/growth_calibration.py`, `tools/compound_growth.py`, `tools/hierarchical_light.py` and `tools/plant_light_bridge.py` read-only. Map actual public functions, data keys and evidence statuses into the extension. Do not change their active files concurrently or send other chats instructions without user authorization.

Propose a distinct versioned physiology mode and additive module such as `tools/fsp_physiology.py`, only if no equivalent exists. Supply proposed function contracts, for example:

```text
audit_physiology_inputs(origin, light_series, environment, parameter_pack)
compute_leaf_exchange(leaf_state, light, environment, photosynthesis_parameters)
compute_respiration(organ_states, environment, accounting_policy, dt_s)
allocate_carbon(carbon_state, organ_demands, cost_parameters, dt_s)
update_form(measured_anchor, prior_state, mass_increment, development, allometry)
advance_physiology(state, inputs, parameters, dt_s)
audit_carbon_balance(previous_state, next_state, flux_ledger)
```

Define exact input/output fields, units, identity keys, missingness, errors, applicability and tested invariants before implementation. Distinguish proposed functions from inspected existing functions. Reuse the calibration evidence registry where compatible, but version extensions and identify unsupported physiological fit families rather than pretending they are already implemented.

Specify how potential-growth targets and realized increments interact with the current analytic stochastic decoder. Do not apply an empirically fitted light effect and a mechanistic light/carbon effect twice. Choose a documented replacement or residual/hybrid construction with identifiable roles; leave the old model as an explicit comparator.

Preserve stable seeds and joint parameter uncertainty. Physiological integration must use a documented internal time grid independent of requested output dates; test numerical convergence separately. Observation re-anchoring changes a state estimate, not past photosynthetic uptake: record assimilation corrections in a separate ledger and never count them as physical carbon production.

## Coefficient and deliverable requirements

Produce an evidence pack containing one row/record per equation and parameter with source locator, original/converted unit, actual reported value/distribution, cultivar/conditions, measured/fitted/assumed status, uncertainty type, transfer limitations, review state and model dependency. If a source is inaccessible or a coefficient cannot be identified, use null with the precise reason. Search the original cited source and supplements before declaring it unavailable; do not repeatedly scan the project for known absent local measurements.

Required handoff outputs are:

1. `handoff/CLAUDE_FSP_PHYSIOLOGY_CONTRACT_2026-10-03.md`: complete equations, accounting policy, model selection rationale, interfaces and owner-specific implementation plan.
2. In a fresh `build/fsp_physiology_spec_<run>/`: `source_registry.json`, `equation_registry.json`, `parameter_candidates.json`, `unit_accounting.csv`, `organ_state_schema.json`, `input_requirements.csv`, `integration_map.json`, and `validation_plan.json`.
3. A worked dimensional/carbon-balance example, with any invented numbers labelled synthetic, proving the bookkeeping convention without claiming calibrated biology.
4. A concise table of source-recovered coefficients, usable conditional assumptions, and values requiring target-cultivar measurement. Include the exact minimal evidence needed for each unavailable calculation.

The final specification must be self-contained for implementation; references supplement rather than replace formulas and unit definitions. Do not mutate prior contracts, active parameter sets or source measurements to hide an incompatibility.

## Accuracy and validation plan

Validate modules as well as the final geometry. Separate photosynthesis response against gas-exchange measurements, organ/whole-plant respiration against appropriate exchange data, allocation/dry matter against independent biomass evidence, and geometry against independent later observations. Preserve the project's non-destructive measurement preference: request suitable published or separately collected reference data rather than silently authorize destructive harvesting. State which quantities remain unidentifiable from photos alone.

Predefine matched-input comparisons: current FSP, a simple light-response alternative and the proposed physiology model; isolate allocation/allometry changes where useful. Compare on held-out plants and independent cultivation/treatment units with chronological forecast origins. Calibration, model selection and final test data must remain separate. Do not give one model measured future environment while the comparator gets an unknown scenario.

Report area, axis/length, mass and available direction/count errors at supported 7/14/21/30-day horizons, coverage, missingness and predictive uncertainty. Test whether extra parameters are identifiable; do not fit all physiology coefficients to the same few image trajectories. Use sensitivity/uncertainty analysis to prioritize measurements, not to relabel assumed variation as calibrated confidence.

Required future software checks: unit conversions, zero/dark light, signed exchange, partial-area scope, nonuniform-light integration, leaf-respiration double counting, growth-yield double counting, missing root/initial storage, carbon deficit, zero sinks, conservation, birth mass, reserve/structural-mass separation, variable SLA, day-zero geometry preservation, timestep/output-grid independence and observation-correction bookkeeping.

Set practical accuracy thresholds through a declared evaluation plan. Report improvement, no improvement or degradation honestly; complexity is not an acceptance criterion. Without independent targets, report a completed mathematical contract or conditional scenario, not an accuracy gain.

## Completion communication

Explain in Korean which photosynthesis/accounting/allocation/allometry choices are supported, what equations and coefficients were actually recovered, what can be implemented now, and what evidence remains missing. Link the English contract and evidence pack. Append the required English LOG entry. No biological default or physical/predictive validation is created merely by citing a paper.
