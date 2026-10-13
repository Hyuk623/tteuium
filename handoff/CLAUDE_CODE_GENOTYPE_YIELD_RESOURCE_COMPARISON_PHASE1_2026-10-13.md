# Claude Code: genotype/trait comparison and target-yield resource search — phase 1

Date: 2026-10-13
Implementer: Claude Code
Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

## 1. Implement this objective

Build an initial reusable comparison layer over the existing Python/GroIMP FSP pipeline, with MATLAB as an optional scenario-design and analysis client.

Support two experiments:

1. **Forward comparison:** reference line versus a variant under the same declared environment/management, comparing development, morphology, biomass and supported yield outputs.
2. **Target-yield search:** for each line, search declared management scenarios for those meeting the same yield, quality, area and deadline constraints, then compare electricity, fertilizer and water requirements.

Do not rewrite the native plant engine. Implement working schemas, scenario generation, execution adapters, resource ledgers, comparison and bounded search. Use actual native evidence for supported growth outputs. Fruit yield and genotype effects require the scientific contracts below; missing contracts must produce explicit unavailable outcomes rather than fabricated yield or a supposedly validated genetic effect.

The initial deliverable may establish working mechanics before all biology is available, but must report forward-growth comparison, actual fruit-yield prediction, resource accounting and target-yield optimization separately. Mock yield responses only test search mechanics and cannot count as end-to-end biological capability.

## 2. Read first, reuse and coordinate

Read parent/project rules, LOG/TODO, current claims and:

- `tools/MICROTOM_FORECAST.md` and `tools/TOMATO_FSP_PIPELINE.md` plus actual public APIs.
- `handoff/CODEX_USER_CONFIGURABLE_FSP_FULL_IMPLEMENTATION_PROMPT_2026-10-13.md`.
- `handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md`.
- `handoff/CODEX_FSP_EIGHT_CAPABILITIES_EXECUTION_2026-10-11.md`.
- `handoff/NATIVE_BOUNDARY_CONTRACT_2026-10-13.md` and latest completion reports.
- Latest empirical growth-boundary, nutrient-reservoir and P3 F8/F9/F10 reports/claims.
- `handoff/CLAUDE_FOUR_PROJECT_SCIENCE_EQUATION_PARAMETER_REVIEW_2026-10-11.md` and current MTG conventions.

The current LOG records a failed F10 run caused by native code changing during preparation. Preserve it. Before native execution, require a released/coordinated engine revision and freeze its source hashes. Do not repeatedly retry while another owner is editing native templates. Build and test independent comparison code meanwhile.

Claude Code owns this new comparison layer and its existing forecast wrappers. Codex's native, empirical-light and reservoir claims remain in effect. Use public APIs and request exact missing hooks through LOG. No automatic cross-chat dispatch. Never overwrite human records/config/docs, original VTC or historical runs. Claim shared files before changes.

Produce a coverage/gap map before coding, then execute the independently implementable work. New source belongs under shared `tools/` and `tools/tests/`; outputs/examples belong under a fresh `build/genotype_compare_<date>_<id>/`.

## 3. Reference and variant registry

Create a versioned JSON registry with:

- `reference_id`, cultivar, accession/line, supplier/lot/generation where known, source records and baseline model version.
- `genotype_id`, genetic background, comparison reference, gene ID with genome/annotation version, allele identifier, zygosity, and verified/unknown status.
- `comparison_kind`: `trait_scenario` or `genotype_supported`.
- Phenotypic/process parameter mappings, units, evidence source, source cultivar, environment/stage domain, uncertainty/dependencies and engine activity.

WT means the appropriate reference background at the investigated locus, not an assertion that Micro-Tom has no other mutations. Unknown genotype remains unknown. Do not declare all reference/variant background differences controlled merely because both are called Micro-Tom. Record near-isogenic status or known confounding explicitly.

`Solyc...` identifies a locus; it is not an effect magnitude. Do not invent a Solyc ID, assign an allele effect from a gene name, or infer loss-of-function from an unreviewed sequence. Phase 1 excludes sequence-to-function prediction, edit design and wet-lab protocols.

Trait scenarios may change supported model parameters without claiming a genetic cause. Genotype-supported scenarios need an explicit evidence-backed mapping. Mapping structure:

`genetic_background + allele + environment/stage -> parameter set or developmental rule`.

Allow several effects from one allele and reviewed interactions between loci/environment. Do not multiply independent effect factors by default. Preserve correlated uncertainty. Changes unavailable in the engine remain inactive with a reason, never silently accepted.

Use a neutral reference model and explicitly named hypothetical trait variants for software examples. No hypothetical percentage should be attributed to SP, SP5G, SlER or another real gene. These genes are literature-review candidates only until exact evidence and model mapping are accepted.

## 4. Fair comparison protocol

Define an immutable `comparison_protocol.json`:

- Unit of comparison: per plant, per ground/shelf area, or per facility batch; report denominators explicitly.
- Start basis: same sowing time, same transplant age, or matched observed state. These answer different questions; never force identical mature geometry for a lifetime genotype-effect claim.
- Fixed environment and management schedules, layout/density, facility, model version, simulation horizon and harvest definition.
- Initial seed/plant resource provenance and genotype-specific initialization where justified.
- Replicate seeds, uncertainty sampling plan and separate numerical/biological/scenario variation.

Default forward comparison varies the registered genetic/trait factor only. Emit a machine-readable diff of all effective inputs and fail if an uncontrolled setting differs. Changed geometry caused by the genotype is an outcome, not an unfair environment change. Initial matched-state experiments must disclose which earlier genotype effects they remove.

For target-yield search, distinguish fixed controls from decision variables. Genotype-specific management is intentionally allowed there; report its differences. Keep physical area, deadline and product quality constraints identical unless the user explicitly chooses another question. Treat density as fixed or optimized explicitly, never switch it silently.

Compare time series at common timestamps and consistent developmental definitions. Preserve plant/axis/organ identity namespaces without pretending that mutant and reference organs are necessarily homologous. Missing correspondence prevents organ-level pairing but need not prevent valid plant-level totals.

## 5. Yield is a separate model contract

A truss, leaf biomass or total dry mass is not harvested fruit yield. Before actual target-yield search, require a reviewed fruit model with flowering/fruit-set, abortion where modelled, fruit sink/allocation, growth, maturation/harvest criteria and relevant genotype/environment dependence.

Define `yield_basis` explicitly, e.g. marketable fresh fruit kg per m2 by a deadline. Fresh mass needs a supported water/dry-matter relation; do not apply a universal conversion to total plant mass. Prevent repeat harvest of the same fruit; track harvest exports in resource/carbon accounts. If quality is constrained, provide the actual quality model or mark the constraint unassessable.

Implement a yield-provider interface that returns value, unit, support/evidence, model version and unavailable reason. Missing fruit capability returns `yield_model_unavailable`, not zero, infinity or estimated fruit count from truss count.

If actual harvested records are supplied, permit comparison of measured yield/resource totals as a separate observational analysis. Do not label that a simulated genetic counterfactual. A dry-biomass target is allowed as a separately named proxy experiment, never as fruit-yield completion.

## 6. Resource accounting

Export per-run and per-harvest resource ledgers, with explicit start/end and facility boundary:

| Quantity | Accounting rule |
| --- | --- |
| Electricity | `E_kWh = sum(P_electrical_W * duration_s / 3600000)` for interval-constant power; integrate schedules otherwise |
| Equipment | Separate lighting, fans, pumps, heating, cooling and dehumidification; missing loads stay unknown |
| Fertilizer | Product mass plus element-resolved N/P/K/etc. input, stock change, uptake, drainage and reuse where supported |
| Water | External fresh input, recirculated volume, storage changes, evaporation/transpiration and discharge separately |
| Time/area | Days to target, occupation time and production per declared area/time |
| Cost | Optional explicit tariff/product-price inputs; keep currency and date, never invented defaults |

PPFD does not determine electrical watts without a supported fixture/efficiency model or measurement. Dimming-power curves need evidence. Climate setpoints do not determine HVAC electricity without an equipment/thermal model or measured electrical schedule. If only lamp power is known, report lighting electricity, not total facility electricity.

Fertilizer g and electricity kWh must not be summed as energy. Embodied fertilizer energy/carbon footprints require separately sourced conversion factors and an explicit life-cycle boundary; exclude from the initial default objective.

For a shared reservoir, count external supply once at tray/facility level. Allocation to individual plants is a labelled modelled split unless independently measured. Distinguish supplied versus absorbed nutrient; reused solution is not a second external input. An EC-equivalent ledger cannot generate elemental uptake totals.

Report both absolute inputs and specific consumption (`kWh/kg`, `L/kg`, `g element/kg`) only with a valid positive yield denominator. Zero/unavailable yield produces unavailable specific metrics. Define whether start/end residual fertilizer stocks are charged as purchase/input or consumption; display both where possible.

## 7. Execution and bounded optimization

Implement one adapter to the existing pipeline/forecast authority. Each genotype × management × replicate run has a unique immutable directory, full resolved inputs and source/model hashes. Do not advance native state twice or recalculate physiology in the comparison layer.

Forward mode aggregates plant morphology, growth, carbon and valid yield/resource outputs. Report reference-relative differences and effect denominators. Scenario spread is not a confidence interval or genetic probability. If a parameter is inert within the horizon or an allocation cap saturates, report that causal limitation; do not fabricate a difference.

Start inverse mode with a transparent finite grid or explicitly listed candidate schedules. Bounded exhaustive comparison is preferable to an opaque optimizer in phase 1. State: **best feasible among evaluated candidates**, not global optimum. Add more sophisticated optimization only after model/cost behavior and noise are characterized.

Use a declared target such as `yield >= Y_target` plus deadline, area and quality constraints. Also report achieved yield and overshoot; comparisons based on equality require a stated tolerance. Outcomes: feasible, target_not_reached_in_evaluated_set, model_unavailable, invalid_input or execution_failed. Failed/missing runs cannot prove biological infeasibility.

Expose at least: minimum electricity subject to yield and nutrient/water caps, and a Pareto comparison of electricity/fertilizer/water. No arbitrary weighted sum of incompatible units. If a scalar cost objective is selected, require explicit prices; if weights are selected, state normalization and preference basis.

Tie breaking, run budget, bounds and stopping conditions must be recorded. Use matched numerical settings/seeds for comparisons and additional seeds near ties when needed. Re-evaluate shortlisted candidates rather than ranking differences smaller than sampling noise. Do not let the search exploit unsupported light-field extrapolation, negative resource inputs or out-of-domain response laws.

## 8. MATLAB role and portable file boundary

MATLAB is a client for defining scenario tables, requesting batches and plotting comparisons/Pareto sets. Python orchestrates; GroIMP calculates the plant. MATLAB must not apply a second growth update.

Implement the Python CLI first, then add plain `.m` client scripts, preferably under `tools/matlab/`, for writing validated JSON/CSV inputs, invoking the documented CLI and loading results. Reuse public schema/functionality rather than a separate MATLAB schema. Handle spaces/Korean paths and command errors safely.

Inspect MATLAB availability and compatible Python configuration before claiming native MATLAB execution. If unavailable, deliver scripts and sample inputs/outputs, label MATLAB execution untested, and demonstrate the Python path. Do not install or purchase MATLAB. Simulink and App Designer are not requirements for this phase; an interactive MATLAB app can be a later wrapper.

Suggested source responsibilities (reuse existing equivalents):

- `tools/genotype_scenarios.py`: registry and genotype/trait mapping validation.
- `tools/genotype_comparison.py`: forward comparisons and CLI.
- `tools/fsp_resource_metrics.py`: equipment/resource ledger and yield-normalized metrics.
- `tools/fsp_target_yield_search.py`: candidate enumeration, feasibility and Pareto extraction.
- `tools/matlab/run_genotype_comparison.m`, `plot_genotype_comparison.m`.
- Focused tests under `tools/tests/` and `tools/GENOTYPE_COMPARISON.md`.

Required operations: `validate`, `forward`, `resources`, `search`, `summarize`. Document exact callable APIs and commands after implementation; these names do not claim existing files.

## 9. Outputs

Write `resolved_protocol.json`, `genotype_registry.json`, `scenario_matrix.csv`, `effective_input_diff.csv`, `run_manifest.json`, `trait_timeseries.csv`, `harvests.csv`, `resource_ledger.csv`, `comparison_summary.csv`, `feasibility.csv`, `pareto_candidates.csv`, and `unresolved.csv` as applicable.

Every comparison row retains genotype/trait scenario ID, environment/management ID, replicate, unit/area/time basis, engine/source hashes, evidence and missing-state reason. Keep separate growth, yield, resource-accounting and optimization statuses. Export graphs with units and distinguish actual native values, measured values and mock solver fixtures.

Final report: `handoff/GENOTYPE_YIELD_RESOURCE_PHASE1_EXECUTION_2026-10-13.md`. Include exact commands/exits, tests, coverage, current blockers, MATLAB execution status and a concise Korean user explanation in a permitted companion/output location.

## 10. Required tests and demonstration

1. Reference compared with itself reproduces results within numeric tolerances; identical IDs/settings cannot masquerade as distinct genetic effects.
2. Unsupported allele/effect or unknown mapping cannot silently modify an engine parameter. A hypothetical trait scenario never becomes genotype-supported.
3. Effective input diff proves the forward environment/management controls; preserve genotype-specific initial-state semantics.
4. At least one active existing trait parameter produces an interpretable native growth/structure difference over a sufficient horizon, with no invented gene attribution. Report saturation/inert parameters honestly.
5. Electricity example: 30 W for 14 h gives 0.42 kWh; independent scheduling tests cover off times and varying loads. Missing HVAC remains unknown.
6. Water-only refill adds no fertilizer mass; reservoir reuse is counted once; oxide/element labels remain distinct through existing converters.
7. Yield zero/missing blocks specific-consumption division and actual inverse optimization. Fruit dry/fresh mass, maturity and harvest identity are not conflated.
8. Synthetic analytic search fixtures with known feasible sets/frontiers prove optimization logic, including all-infeasible, missing-model and failed-run cases. Label them mock, never native tomato evidence.
9. Actual native forward runs and file-interface round trips execute on a stable frozen engine. Verify engine-version changes invalidate cached comparisons. A failed batch cannot publish a final success manifest.
10. If the reviewed fruit/genotype/resource contracts exist, execute actual target-yield comparisons. Otherwise demonstrate explicit refusal and keep that capability pending; no substituted biomass yield.

Scientific follow-up must specify exact missing genotype-to-parameter effects, fruit/harvest model, nutrient feedback and equipment power models. Do not stop after writing a missing-data list: finish registry, adapters, ledgers, supported forward native comparisons and search mechanics independently.

## 11. Literature starting points — verify before adopting effects

- SGN ID conventions: https://solgenomics.net/help/faq
- Tomato compact architecture / SP, SP5G and SlER: https://www.nature.com/articles/s41587-019-0361-2
- Genotype interactions and background effects: https://www.nature.com/articles/s41477-019-0422-z
- Temperature-dependent inflorescence architecture: https://www.nature.com/articles/s41467-024-45722-0
- Existing tomato FSP reference: https://academic.oup.com/insilicoplants/article/7/2/diaf022/8342854

These are review starting points, not approved Micro-Tom coefficient tables. Extract exact allele/background/environment/equation/effect evidence and uncertainty before creating a genotype-supported mapping. A gene's association with a trait alone does not establish a transferable causal parameter value.
