# Evidence based tomato growth calculator implementation handoff

Date: 2026-10-03. Recipient: Codex implementing the growth calculator, with scientific model and experiment review by Claude. This is a prompt-authoring deliverable; no implementation, coefficient fitting or experiment has been performed by this document.

## Objective and scope

Build the numerical growth engine inside the existing growth-direction program. It must predict joint 30-day trajectories of CompoundLeaf appearance, size, direction and stem/attachment growth from measured plant state, environmental scenarios and traceable parameters.

Extend that engine with an explicit evidence workflow:

```text
Primary literature and supplementary material
    -> candidate equations and parameter evidence
Repeated observations and documented treatment contrasts
    -> measurement and identifiability audit
Reviewed model and fitting plan
    -> parameter estimation and uncertainty
Independent validation
    -> versioned parameter set for the growth calculator
```

Reuse `handoff/CODEX_GROWTH_CALCULATOR_HANDOFF_2026-10-03.md` as the base implementation prompt. This revision adds literature-evidence ingestion and bounded statistical parameter fitting when eligible data and a specified fit plan exist. It supersedes the base prompt's exclusion of coefficient fitting for this explicit workflow only. It does not authorize neural training or activate Flow Matching. All base observation, geometry, optical, forecast and ownership protections remain in force.

Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.

Do not implement image analysis, canopy assembly/splitting, optical tissue generation, a light solver, UI, roots, fruit yield or a new mechanistic photosynthesis/carbon-allocation model. Accept externally supplied measured geometry and light summaries. Return forecast states for downstream programs without executing them.

## Read first and record work

Read parent `공통규약.md`, project `AGENTS.md`, `CONVENTIONS.md`, recent LOG entries and relevant TODO items. Then read:

- `handoff/CODEX_GROWTH_CALCULATOR_HANDOFF_2026-10-03.md`.
- `handoff/CODEX_GROWTH_IO_BRIEF_2026-10-03.md`.
- `handoff/CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md`, especially mathematical definitions and section 9 interfaces.
- `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md` and `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md` for external input semantics only.

Inspect actual source status and reuse existing functions. Codex edits `tools/` and `tools/tests/`; preserve protected core, config, design documents and all source/human observations. Write an English execution brief first, generate artifacts in fresh `build/` directories, and append the outcome to LOG. Do not repeat searches for observations already confirmed absent unless new evidence is supplied.

Implement and test independent software components while scientific inputs are missing. Report the affected scientific component as unavailable instead of guessing a coefficient or abandoning all software work. Claude reviews biological model choices and the experiment protocol; a code test cannot approve either.

## Define the response targets separately

| Target | Evidence needed | Prohibited substitution |
| --- | --- | --- |
| Appearance timing | Last confirmed absence, first confirmed appearance, apex state and environmental history | First detection after occlusion treated as exact birth |
| Leaf/axis expansion | Repeated comparable lengths, extents and supported area with identity/age evidence | One snapshot used to identify rates or final size |
| Stem expansion | Repeated directed stem geometry and reviewed attachments | Artificial stem inferred from leaf count |
| Initial direction | Parent-local direction at an operationally defined appearance event | Mature leaf angle treated as a newborn direction |
| Subsequent direction change | Repeated unit vectors/local angles, timestamps and parent-frame evidence | Final treatment angle divided by elapsed days as a rotation rate |
| Environmental response | Variation in a measured input, supported contrast and response observations | A constant-condition growth curve claimed to identify sensitivity |

Separate natural age/stage progression, plant differences, temporary within-day movement and sustained growth changes. Record capture time relative to the lighting schedule. Do not attribute changes from camera/plant registration, stem movement, occlusion or different visible support to growth.

## Literature evidence acquisition

Use primary research, author/institution repositories, supplements and available source code. The following are verified discovery starting points, not approved parameter packs:

- [Dwarf tomato functional structural model](https://research.wur.nl/en/publications/a-functionalstructural-plant-model-for-dwarf-tomato-ideotype-iden/), DOI `10.1093/insilicoplants/diaf024`: relevant organ growth, architecture and light/biomass model context. Inspect the actual equations, cultivar, tables and supplement before extraction.
- [Light quality and tomato morphology](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2019.00839/full), DOI `10.3389/fpls.2019.00839`: measured morphology/angle differences under spectral treatments; endpoint differences do not establish direction dynamics.
- [Continuous and end of day far red treatments](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2019.00322/full), DOI `10.3389/fpls.2019.00322`: treatment-specific morphology evidence; do not generalize its angle response beyond the tested conditions.

For every candidate equation or coefficient, retain the exact equation/table/page locator, source version, unit, angle reference, organism/cultivar, organ/leaf rank, stage/age, temperature, spectrum, light intensity and photoperiod where reported. Record which inputs were manipulated and which were only observed. Missing supplementary data remain unavailable; never fill them from a search snippet. Do not contact authors without explicit user authorization.

Distinguish a value measured in a paper, a fitted parameter, a fixed modeling assumption and a value borrowed by that paper from elsewhere. Follow the original citation for borrowed values. Record uncertainty as reported; distinguish SD, SE and confidence interval, and retain the experimental unit/sample count. No uncertainty reported means unknown, not zero.

A single endpoint can constrain an endpoint or treatment contrast, not all rates/asymptotes of a trajectory. A prescribed phyllotactic angle is not evidence that light causes azimuth rotation. Inspect angle conventions before comparing studies.

Keep foreign-cultivar values as literature-informed candidates until applicability is reviewed. Use applicable literature as candidate priors/ranges or a named fixed assumption, not as measured truth for the user's plants. Publish limitations when only abstracts or portions of a source were accessible.

## Repeated observations and experiment dependencies

Create read-only adapters and an audit for available measurements. Preserve the project's source format and null/QC rules. Do not write observations or fabricated rows into human ground truth.

The audit must establish plant/organ identity; observation timestamp/frame; comparable length/area support; age or appearance intervals; measurement error/repeated-capture evidence; actual environment histories; and treatment/replicate structure. Optional growth rate summaries are derived outputs, never replacements for the raw measurements.

Where spectral or directional responses are enabled, require the corresponding spectrum or source-direction features. Total PPFD alone does not identify a direction to turn toward or distinguish spectra. Future inputs are scenarios; training inputs are the actually observed historical exposures, including changes and gaps.

Prepare an evidence-gap matrix for Claude to review. Candidate contrasts are light intensity with spectrum/photoperiod controlled, source direction with irradiance differences measured/controlled, and temperature with light conditions controlled. These are protocol questions, not an approved experiment. Do not invent treatment levels, plant counts, duration, safety ranges or acceptance thresholds. Determine necessary replication from a reviewed design using pilot variability and a declared effect/precision target.

Record the true treatment-assignment unit, such as a lamp zone, chamber or independent cultivation run. Leaves on the same plant and plants sharing one treatment unit are not independent treatment replicates. Retain randomization/blocking and placement records. One unreplicated zone per treatment cannot identify treatment effects independently of zone effects.

Audit confounding, input range and collinearity before fitting. For example, fixed photoperiod makes PPFD and its constant-light DLI conversion dependent features; do not estimate separate effects as if independently varied. Limited temperature variation may not identify both a base temperature and a development slope. Report unsupported terms rather than allowing an optimizer to supply apparently precise values.

Observed geometry also affects received light. An association between larger leaves and more absorbed photons is not by itself evidence that the photons caused the size difference. Preserve temporal ordering, treatment evidence and measurement/model errors; label observational associations and causal claims separately. Simulated light used as a predictor must retain its independent validation and uncertainty status.

## Parameter estimation contract

First implement the growth engine's existing proposed equations with explicit assumption configurations. Add fitting through a separate declared `fit_plan.json`; never silently refit while producing forecasts or choose a new biological law merely because it optimizes better.

The reviewed fit plan must specify the model family/equation version, eligible targets, fitted versus fixed parameters, transforms/bounds and their sources, time/area basis, likelihood or loss, observation error, plant/treatment-unit dependence, censoring treatment, prior distributions if any, fit/validation split, convergence criteria and uncertainty method. Missing scientific definitions make fitting unavailable while templates/audits remain usable.

Fit repeated states with their measurement model where specified; do not blindly differentiate noisy observations. Use the actual interval for appearance events and an appropriate circular/vector treatment for directions. Preserve joint parameter dependence and uncertainty needed by the forecast sampler. Method choices such as nonlinear regression, mixed effects or Bayesian estimation must match the specified plan and available data; do not build multiple model families without a need.

Inspect identifiability, residual patterns, bounds, convergence and uncertainty. Do not export a failed or nonidentifiable numerical optimum as calibrated coefficients. A model that cannot distinguish alternative coefficients should report that limitation. Do not fit more environmental response terms merely because their field names exist.

Start with the target cultivar and present LED setup's base trajectories, then evaluate identifiable light-intensity responses, then direction responses. This is a staged implementation/evidence priority, not a claim that the earlier stage identifies all later effects. Unmodeled environmental fields remain metadata with inactive response terms.

Keep data provenance and validation status separate. A fitted value may be unevaluated; a literature value may be plausible but uncalibrated. Only a recorded independent evaluation and explicit acceptance for a stated domain may qualify a parameter set for that domain. No automatic flag promotes an assumed or synthetic parameter set.

## Proposed additions to the existing growth interfaces

Preserve the base forecast functions and CSV/JSON schemas. Reuse existing equivalents before adding these proposed support interfaces:

```text
validate_evidence_registry(registry) -> validated_records, issues
audit_calibration_data(observation_refs, treatment_manifest, fit_plan)
    -> eligible_targets, missing_evidence, identifiability_flags, source_hashes
fit_growth_parameters(observation_refs, evidence_registry, fit_plan)
    -> fitted_parameter_set, diagnostics, uncertainty, status
validate_parameter_set(parameter_set, independent_targets, evaluation_plan)
    -> scores, coverage, baseline_comparisons, applicability, status
```

Keep fitting isolated in `tools/growth_calibration.py` or an existing equivalent. The numerical forecasting engine remains `tools/probabilistic_compound_growth.py` if implemented as proposed. Tests belong under `tools/tests/`; a standalone CLI must expose `--help` and separate audit, explicit fit, validation and forecast operations. Forecast never starts a fit or light job implicitly.

Produce the following additional artifacts in a fresh run directory:

| Artifact | Required content |
| --- | --- |
| `evidence_registry.json` | Source/equation locators, parameter values or nulls, units, uncertainty meaning, cultivar/conditions, evidence type and applicability/review status |
| `data_audit.json` | Identity, comparability, missingness, measurement errors, treatment replication, confounding, identifiability and per-target availability |
| `fit_plan.json` | Frozen model, estimation method, target/parameter definitions, dependence, split and uncertainty settings |
| `parameter_set.json` | Versioned values/distributions, units/transforms, covariance or posterior-particle references, training provenance, applicable domain and separate validation status |
| `fit_diagnostics.csv` | Target/parameter-level convergence, residual or identifiability diagnostics and limitations |
| `validation.csv` | Independent horizon/target scores, uncertainty coverage, denominators, missingness and baseline comparisons |
| `requirements.csv` | Missing equation, coefficient, observation, treatment contrast or review; affected component and responsible reviewer/provider |
| `manifest.json` | All dependency hashes, commands, seed/numerical environment, artifact versions, mode and limitations |

These schemas are additions, not permission to change the detailed forecast schema silently. Define full field names and units in the execution brief before implementation and use explicit adapters into `model.json`. Preserve the source observations, earlier parameter sets and forecasts. No field missing from the fit plan gets a hidden biological default.

## Independent validation and tests

Freeze fitting/model-selection decisions before the final test evaluation. Keep observations from the same plant and treatment unit together as required by the scientific question; include independent cultivation runs/units where available. Use chronological forecast origins, with only information available at each origin. Report future environment as known, forecast or assumed consistently with the intended evaluation.

Report supported 7/14/21/30-day appearance/count, length/extent, position and angular errors plus predictive coverage. Compare persistence and recent-change baselines. Separate occurrence probability from geometry conditional on existence, and separate assumed scenario variability from calibrated uncertainty. Missing 30-day targets do not become a validated 30-day result. Parameter confidence alone is not predictive validation.

Preserve all base calculator invariants. Add tests that catch source-unit/angle-reference mismatch, endpoint-only evidence used as a dynamic rate, missing replication, collinear response terms, event censoring, angular wrap, data leakage, failed optimization and unauthorized parameter promotion. Use synthetic recovery checks for identifiable fixture parameters; do not claim real biological calibration from them.

The completed software must support three explicit operating cases: blank/missing inputs with actionable audit output; a synthetic or user-assumed scenario with an honest label; and an eligible fitted parameter set with its independent-validation status. Implement available cases without inventing the missing real dataset.

## Final deliverables and report

Deliver working growth/calibration code, focused tests, blank evidence/fit templates, one bounded synthetic demonstration and an audit of any supplied real inputs. Keep Flow Matching disabled and perform no remote jobs, uploads, source-data edits or physical experiment actions. Literature research and fitting artifacts do not authorize outreach or deployment.

Report in Korean the implemented capabilities, actual test results, sourced candidate equations/parameters, fitted versus still-unidentified values, validation limits and exact missing evidence. Identify scientific decisions needing Claude review without blocking unrelated software work. Do not say that light-driven growth or direction prediction is validated unless the independent evidence supports that specific claim.
