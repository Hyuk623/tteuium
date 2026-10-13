# Design prompt for probabilistic 30 day CompoundLeaf growth

## Assignment and delivery boundary

You are Claude, responsible for scientific design, literature assessment and the implementation specification. Codex will implement the reviewed contract. Design the smallest defensible model that forecasts the next 30 calendar days of tomato architecture while preserving existing measurement evidence.

The user wants to investigate stochastic L-systems and conditional Flow Matching for the distribution of future CompoundLeaf blocks. Evaluate a hybrid in which a stochastic grammar represents organ appearance and attachment topology, and a conditional generative model represents continuous placement and growth trajectories. This is a design candidate, not an already validated architecture. Recommend the simpler model if Flow Matching is not justified by the available data.

Deliver one self-contained English Markdown specification for Codex. Complete the scientific and interface decisions that available evidence permits; identify unresolved decisions explicitly. Do not implement production code, train a model, run inference or start a simulation campaign in this assignment. Do not replace missing decisions with plausible numerical defaults.

Project root:

```text
C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis
```

Read the parent working agreement, project AGENTS.md and CONVENTIONS.md, the last five lines of handoff/LOG.md and relevant handoff/TODO.md entries before writing. Respect current ownership and append-only handoff history. Preserve other agents' work in the OneDrive workspace. Source observations, human configuration and measurement records are read-only for this task.

## User requirements that must remain intact

### Existing leaves

- Use image-derived measured position, direction, dimensions and supported shape as the current state. Do not regenerate the current plant using literature-derived or procedural geometry.
- Preserve the original observations and their provenance. Represent a model's estimated latent state separately if measurement uncertainty is modelled.
- Forecast future changes from the measured current state. Distinguish observed geometry, estimated state and predicted geometry at every time point.
- Missing or partial shape remains missing or partial. A visible petiole segment is not a measured whole rachis; an unresolved region name is not a confirmed persistent compound identity.

### Future leaves

- The prediction unit is a CompoundLeaf block, not an independently generated set of leaflets.
- Represent uncertainty in whether and when new blocks appear, where they attach, their growth directions, spatial extents and dimensions.
- Condition the predictions on both supported plant-development literature and measurable relationships among the current plant's blocks.
- Candidate relationships include order along the parent stem, attachment spacing, relative orientation and relative dimensions. Select only relationships with a clear definition and adequate measurement support.
- Preserve dependencies between blocks and over time. Independent random angles and sizes for each block are not sufficient to represent a coherent plant trajectory.
- A predicted block is a spatial/developmental representation, not a solid sheet of leaf tissue.

### Literature and measurements

- Literature supplies candidate rules, prior information and applicable ranges. Current measurements constrain those rules to the observed plant.
- Literature coefficients, fixed phyllotactic angles and parameters from other cultivars are not validated values for this plant or cultivation environment.
- Current spatial relationships can inform spatial priors. One snapshot alone does not identify appearance rates, expansion rates, temporal covariance or environment-response functions.
- The user currently has no supplied cultivar, sowing/transplant dates, longitudinal growth records or future environment schedule for this model. These must be configurable or explicitly unavailable. Do not require invented values to make the specification appear complete.
- A user-entered scenario is permissible when its assumptions are explicit. It must not be presented as fitted or calibrated prediction.

### New observations

- When a predicted block is observed, associate it with the observation where supported and use the measured block in the updated state.
- Preserve the earlier forecast and the original observation separately so their discrepancy remains evaluable.
- Use discrepancies to update subsequent appearance, placement and expansion predictions under an explicit update method.
- Do not assume every newly detected block was newly born. It may have been occluded, missed or unmatched previously.

## Inspect and reuse the current tools

Inspect actual source before proposing additions. These descriptions are the current handoff baseline, not proof that files have remained unchanged:

| Existing module | Relevant capability and limitation |
| --- | --- |
| `tools.compound_growth` | Observed-state extraction, identity/frame checks, signed axis traits, persistence and recent-change baselines, chronological evaluation and exports. `reviewed_growth` is explicitly unavailable. |
| `tools.compound_surface` | Supported partial tissue area and topology audit. It does not complete hidden tissue or automatically approve optical use. |
| `tools.monthly_growth` | User-entered 30-day arithmetic scenario with bounded expansion, periodic emergence and optional explicit environment-response tables. It is not a measured-plant adapter, stochastic grammar or fitted biological model. |
| `tools.growth_simulator` | Procedural illustrative plant generation. Its display anatomy and response coefficients are not growth evidence. |
| `tools.plant_structure` and `tools.plant_traits` | Existing reconstruction-derived relationships and traits; distinguish proposed identities, visible segments and area proxies from validated measurements. |
| `tools.plant_light_bridge` | Existing provenance/eligibility checks and light workflow integration. Reuse its boundary; do not build a second transport pipeline. |
| `tools.groimp_structure_export`, `tools.groimp_static_verify`, `tools.groimp_bridge` | Existing graph/geometry transport and verification helpers. Reuse unchanged; their existing freeze remains in effect. |

Relevant local context is in handoff/CODEX_COMPOUND_MODEL_IMPLEMENTATION_2026-10-03.md, handoff/CODEX_MONTHLY_PARAMETER_MODEL_2026-10-03.md and handoff/CODEX_LSYSTEM_XL_INTEGRATION_REVIEW_2026-09-27.md. The last document contains historical recommendations and later qualifications; do not replay obsolete phases or expand this task to all organ types described there.

The current monthly tool's fixed existing attachments, apical-only stem elongation, shared rates/caps, multiplicative environment responses and periodic emergence are explicit scenario assumptions. None is automatically the biological rule for the proposed model. State which components can be reused and which assumptions must be replaced or remain unavailable.

Existing T1/T2/T3 run copies have the same capture date, 2026-10-02, for different plants. Do not treat them as successive dates of one plant. Check actual provenance before using any other records as time-series evidence.

## Define the smallest useful probabilistic state

Specify a measured plant graph and the minimum CompoundLeaf state required for the forecast. Define each field's meaning, units, coordinate frame, availability and provenance. Reuse existing fields whenever their semantics match.

At minimum address:

- Persistent plant, parent-stem and observed compound identifiers; separate scenario-local identifiers for future blocks.
- Observed attachment and supported order along the stem, including uncertain ordering or missing intervening organs.
- Direction with a representation that handles angular wraparound and signed elevation. Define a local reference for azimuth; a stem axis alone does not determine it.
- Measured rachis/axis information and spread descriptors at the resolution the existing data support.
- Length, extent and tissue-area semantics. Partial supported area, estimated total area and spatial envelope area must remain distinct.
- Developmental state and organ age only to the extent identifiable. Do not assign an age merely from leaf rank or size without a stated model and uncertainty.
- Status distinguishing observed, inferred pre-existing, and predicted future blocks; missing is not absent.

Retain the existing board-frame measurements and measured-pose provenance. Any plant-local relational representation must have an explicit mapping back to the measured frame. Do not repair moving-plant groups by assuming a common frame, introduce SfM or use nominal turntable angles.

Define the forecast target as a joint distribution over appearance events, topology and continuous trajectories, conditional on observations available at the forecast origin and a declared future-environment scenario. State which quantities are latent, measured or supplied assumptions. Use separate notation for biological forecast time and generative-model time.

## Specify the stochastic L-system or RGG component

Choose the minimum symbols/modules and rewriting rules needed for parent-stem development and CompoundLeaf appearance. Reuse the existing graph vocabulary where possible. Additional organ types require a demonstrated need for this forecast.

For each rule, provide:

1. The predecessor state and measured or latent context used by the rule.
2. The event definition and time basis: initiation, emergence and first visibility are different events. Select the endpoint that can actually be observed or clearly model their distinction.
3. The event-time model, conditional parameters and evidence for their forms. Specify how no appearance within 30 days is represented.
4. The successor nodes/edges and how their attachment is derived from the evolving parent stem.
5. The joint distribution of the new block's placement and initial state, including dependencies on existing blocks.
6. Validity constraints, numerical handling, unresolved parameters and the meaning of any rejected sample.

Determine whether chronological time is sufficient or whether a supported developmental clock is needed. Do not invent a base temperature, phyllochron or environmental response. Define within-step event timing so the forecast does not depend arbitrarily on daily versus finer numerical stepping.

Specify how existing leaves change without overwriting the current measured state, and how parent movement is distinguished from leaf-local rotation or expansion. Avoid forcing projected area or leaf angles to be monotone. Consider dwarf-tomato growth habit only where cultivar/stage evidence supports it; unknown habit must not silently become determinate or indeterminate.

Explain which rules and uncertainty components can operate as explicitly assumed scenarios now, and which require repeated observations before they can be fitted. A complex grammar is not required merely because the platform can express one.

## Assess conditional Flow Matching as a bounded extension

Flow Matching must have a specific predictive responsibility. Do not add it solely to produce diverse or visually smooth plants. Compare it with the stochastic grammar plus a simpler conditional parameter distribution.

If recommending Flow Matching, define:

- **Training target:** the continuous variables or trajectory representation to generate. Prefer the existing block-level state over raw mesh vertices unless there is a demonstrated need for finer geometry.
- **Conditioning:** the measured current graph, supported relational features, observation missingness, forecast horizon and available environment. No future measured geometry or environment may enter a retrospective forecast's conditioning.
- **Discrete structure:** how the number of future blocks, attachment topology and existence masks are obtained. A fixed-dimensional continuous flow does not by itself specify organ birth or variable topology. State the interface with the grammar rather than assuming this issue disappears.
- **Two time variables:** use biological time for the 30-day trajectory and a separate flow interpolation time for sample generation. The path from a reference distribution to a generated sample is not automatically a physical growth trajectory.
- **Temporal coherence:** choose a joint trajectory generator or a conditional transition method and justify the choice. Preserve identity and consistency across dates; do not generate unrelated daily plants and call their sequence growth.
- **Geometry:** handle periodic orientation, nonnegative dimensions and relational coordinate frames explicitly. Do not average wrapped angles as ordinary scalar values.
- **Learning contract:** define the reference distribution, probability path, conditioning encoder, vector-field objective and sampling procedure at implementation-specification level. Keep architecture and hyperparameters minimal and identify which require empirical selection.
- **Constraints and uncertainty:** explain how constraints enter training/sampling and how rejection or projection would alter the generated distribution. Sample diversity alone is not calibrated predictive uncertainty.
- **Training evidence:** identify the records, time correspondence and independent trajectories required. Do not assert an arbitrary sufficient dataset size. Define readiness through identifiable targets, coverage and held-out learning/validation evidence.

Synthetic L-system samples may support software tests or a clearly labelled surrogate/pretraining experiment. Learning to reproduce the generator's distribution does not independently validate real tomato growth or resolve a bias in its rules. Do not make synthetic pretraining a prerequisite or start it in this task.

If the current evidence does not justify Flow Matching, retain a precise future interface and implementable grammar-only baseline in the specification. State what observation evidence and measured improvement would justify activating the extension.

## Define uncertainty and observation updates

Separate, at the resolution the evidence supports:

- Measurement and identity uncertainty in the current plant.
- Biological variation among possible future events and trajectories.
- Uncertainty in model parameters and model form due to limited data.
- Differences between declared future-environment scenarios.

Specify how these enter the predictive distribution. An ensemble produced with fixed parameters does not automatically cover parameter or model uncertainty. If probabilities come from assumed ranges rather than calibrated evidence, label the outputs accordingly; do not describe nominal intervals as empirically validated coverage.

Choose one tractable initial update method. Define the observation likelihood or discrepancy model, association handling, update inputs and outputs, and which parameters or scenario weights can be updated. State the limitations of the choice rather than implementing several filtering frameworks.

The update contract must handle a confirmed match, an ambiguous match, a missed/occluded block and an observed block with no prior predicted match. Do not infer death from non-detection or force an uncertain association. Define how newly measured state anchors subsequent forecasts while preserving the original observation, previous forecast, association evidence and update version.

No-observation behavior must be explicit. Where an uncertainty model cannot yet be justified, report it as unavailable rather than assigning an arbitrary Gaussian variance. Do not replace unresolved identification with invented organ identities.

## Keep the optical boundary explicit

CompoundLeaf envelopes, bounding volumes, swept regions and probabilistic occupancy are spatial prediction outputs. They are not fully occupied leaf tissue and must not automatically become opaque receivers or occluders.

Preserve existing measured leaflet/tissue geometry and optical identities when available, even though growth is forecast at compound level. This matters for gaps, within-compound shading and repeated transmission through different leaflets. Compound-level summaries do not authorize merging the underlying optical surfaces.

For future blocks, define only the interface and eligibility status for a possible later tissue-surface model. Without supported tissue allocation and optical assumptions, light transport for those blocks remains unavailable. Do not add tissue reconstruction, a new renderer or a new light solver to this task. Current spatial occupancy probability must not be silently reinterpreted as optical transmittance or occupied tissue fraction.

## Give Codex a concrete implementation contract

After the scientific choices, specify exact proposed modules/functions, input/output fields, units, failure modes and reproducibility controls. Reuse current extraction, validation, baseline and export functions rather than creating parallel pipelines. Add a new module only where responsibilities genuinely differ.

Cover only these operations:

1. Construct eligible measured block states and supported relationships from existing outputs.
2. Generate joint 30-day block-event/trajectory samples under an explicit model configuration.
3. Summarize occurrence, placement and growth distributions without replacing multimodal distributions with misleading mean geometry.
4. Associate new observations and update the forecast state under the chosen method.
5. Evaluate forecasts against independent observations.

Use CSV for tables and JSON for schemas, configuration and provenance. Provide minimal example schemas with unavailable placeholders or explicitly synthetic examples, not purported crop defaults. Define a versioned forecast origin, elapsed/target time, sample identity, stable block identity, existence/event state, frame, parameter/evidence source and random-seed contract. Existing measurements and generated samples must not share an undifferentiated observation table.

Record input/model/parameter provenance and retain prior runs. Specify which parameters can be user-adjusted, literature-informed, fitted or unidentified. Separate computational settings such as sample count and solver tolerances from biological coefficients. Use the existing local execution environment and generated-output conventions.

## Validation that determines whether the model is useful

Define software checks and scientific evaluation separately.

Software checks must cover measured-state preservation, unit/frame consistency, identity continuity, topology and event validity, variable block count, signed/wrapped orientation, missing data, within-step births, time-step sensitivity, reproducibility and observation-update history. Confirm that no block envelope is exported as approved tissue and that forecasts never become training ground truth merely because they exist.

Scientific evaluation must use chronological forecast origins and independent plant groups. All records of a plant stay together for held-out generalization tests; past observations of a held-out plant may initialize its forecast, but future observations may only evaluate that forecast. Respect existing parameter fitting and validation splits.

Compare against persistence/recent-change for existing blocks where eligible, and the simplest defensible appearance/placement baseline for new blocks. Include a grammar-only baseline before claiming benefit from Flow Matching.

Select a compact metric set covering:

- New-block occurrence/count and event timing, with observation intervals, visibility and right censoring handled explicitly.
- Attachment, direction, axis/extent and size error for supported correspondences, with units and angular conventions stated.
- Forecast-distribution quality using suitable proper scores and interval/region coverage together with sharpness. Avoid relying only on point error or visual plausibility.
- Identity/matching failures, missing-target coverage and rejected samples, rather than reporting only easy matches.

Report performance by horizon, including 7, 14, 21 and 30 days when independent targets exist. Do not fabricate 30-day validation from shorter records. Retrospective interpolation, synthetic generator reproduction and prospective prediction are different evaluations. Define evidence-based acceptance criteria where possible; leave unsupported numerical thresholds inactive.

## Scope exclusions

Do not add a dashboard, web application, animation system, new reconstruction pipeline, leaflet generator, neural model zoo, cloud service, deployment workflow, scheduler or automated training campaign. Do not redesign existing viewers. No carbon-allocation, nutrient-uptake, flowering, fruit, yield or economic model is required for this block-architecture task. Environmental features are optional conditioning when justified, not a requirement to invent a full physiological model.

Do not introduce detailed manual annotation of every leaflet as a prerequisite. Request only the measurements needed to identify the chosen block-level variables and evaluate their forecasts. If some data are missing, provide the useful bounded specification and a precise missing-input list rather than expanding the project.

## Primary sources to inspect

These are starting points, not transferable coefficients or proof that a particular hybrid works on these plants. Check the original methods before adopting a formula. Some publisher full-text requests were previously inaccessible; identify any remaining access limitation instead of reconstructing methods from snippets.

- [Generating Functions of Stochastic L-Systems and Application to Models of Plant Development](https://dmtcs.episciences.org/en/articles/3574) — stochastic organogenesis and distributions over plant structure.
- [Modelling architecture of crop plants using L-systems](https://library.wur.nl/ojs/index.php/frontis/article/view/1369) — parameterized plant architecture and context/information transfer.
- [A functional-structural plant model for dwarf tomato ideotype identification in vertical farming](https://doi.org/10.1093/insilicoplants/diaf024) — dwarf-tomato architecture and GroIMP/RGG precedent; inspect cultivar, environment and validation scope.
- [Development of a tomato functional-structural plant model for digital twin applications](https://academic.oup.com/insilicoplants/article/7/2/diaf022/8342854) — tomato architecture/development representation.
- [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747) and [Flow Matching Guide and Code](https://arxiv.org/abs/2412.06264) — flow objectives, probability paths, conditioning and sampling; not evidence of plant-growth accuracy.

For each selected biological rule, give the primary citation, applicable species/cultivar and conditions, exact supported relationship, parameter units, transfer limitation and local calibration requirement. Clearly distinguish literature findings from your proposed model choices. Search for additional primary sources only where needed to resolve an actual design decision.

## Required final specification

Write one English Markdown document containing:

1. The recommended minimum model and a justified decision on when Flow Matching is useful.
2. The measured-state/relationship definitions and the joint forecast target.
3. The selected grammar, continuous dynamics/distributions and evidence for each rule.
4. The uncertainty and observation-association/update method.
5. Concrete reusable code interfaces and minimal CSV/JSON contracts.
6. Software checks, independent scientific evaluation and a short list of unresolved parameters/data.

Separate work that Codex can implement now from work that needs future observations. Keep the future Flow Matching extension bounded and do not make it block an evidence-labelled stochastic baseline. Save the specification in handoff/ under a new descriptive filename, append the required LOG entry and return a concise Korean explanation with its path. Do not send it to another chat or execute its implementation as part of this design task.

Success is an actionable, scientifically qualified design for measured-state-conditioned distributions of future CompoundLeaf architecture. Attractive procedural plants, arbitrary randomization and uncalibrated neural sample diversity do not establish real 30-day predictive accuracy.
