# Integrated dwarf tomato growth simulator implementation prompt

Prepared on 2026-10-03 for a Codex implementation session at the user's request. This document connects the three supplied handoffs. Writing this prompt does not execute it, approve biological coefficients, or establish physical or predictive accuracy.

## Task

Implement a local program that connects image-derived measurements of existing dwarf tomato leaves, reversible assembly of individual plants into a canopy, hierarchical light calculation, and a 30-day distribution of future CompoundLeaf appearance, direction and growth. Return canopy light results to their original plants and organs without losing identity or observation provenance.

Reuse the existing programs. Deliver working integration code, a command-line interface, focused tests and reproducible outputs. Complete independently implementable work even when some real inputs are missing. Report blocked components precisely; do not claim the full scientific objective is complete because the orchestration or synthetic demonstration works.

Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.

## Read first and preserve ownership

Read the parent `공통규약.md`, project `AGENTS.md`, `CONVENTIONS.md`, the last five lines of `handoff/LOG.md`, and relevant current `handoff/TODO.md` items. Then read these authoritative integration inputs:

1. `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md`.
2. `handoff/CODEX_GROWTH_IO_BRIEF_2026-10-03.md`.
3. `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md`.

Follow their referenced detailed contracts where needed: `tools/LEAF_AREA_COMPARISON.md`, `tools/HIERARCHICAL_LIGHT.md`, and `handoff/CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md`. The probabilistic specification remains a proposed contract pending scientific review. Inspect actual source interfaces before calling them; historical test counts are not current verification.

Codex owns `tools/` and `tools/tests/` in this nested project. Keep `tomato3d/`, `tests/`, `config/`, `docs/`, source observations and human ground truth read-only. Record necessary changes outside your ownership in the existing handoff channel. Write a scoped English execution brief before implementation, update it with actual results, and append one English LOG entry at completion. Do not concurrently edit another session's files.

Use fresh output directories under `build/`. Retain CSV for tables and JSON for configuration and provenance. Do not rewrite the three source handoffs to make integration appear easier.

## Established capabilities and unresolved dependencies

| Component | Reuse | Preserve the current limit |
| --- | --- | --- |
| Existing leaf area | `tools/leaf_area_geometry.py`, `tools/leaf_area_compare.py`, `tools/leaf_surface_compare.py`, opt-in `tools/plant_traits.py` features | Supported partial surface, projected area and independently calibrated whole-plant estimates are different quantities. Curved fitting and physical qualification remain incomplete. |
| Observed compound state | `tools/compound_growth.py` | Reuse extraction, checks and persistence/recent-change baselines. Do not infer a growth rate from one snapshot. |
| Adjustable scenarios | `tools/monthly_growth.py` | Supplied multipliers are assumptions, not established environmental response laws. |
| Light interactions | `tools/hierarchical_light.py`, `tools/hierarchical_light_native.py` | Existing light requires accepted optical tissue, reviewed membership and physical scene inputs. Native jobs have not been established as executed by the supplied summary. |
| Optical eligibility | `tools/compound_surface.py`, `tools/plant_light_bridge.py` | Candidate surfaces and block envelopes must not bypass existing review gates. |
| Common I/O | `tools/leaf_light/common.py` | Preserve existing status and missing-value semantics at module boundaries. |

Known absent inputs include a reviewed curved-fitting contract, confirmed physical correspondences and independent area references; eligible real light scenes/surfaces/membership; and identified biological parameters or suitable longitudinal growth data. The leaf-area handoff explicitly says these missing references were already checked. Do not repeat broad searches or path requests for them. Audit any newly supplied inputs, then record the remaining dependencies once.

## End to end data flow

Implement this flow with explicit stage status and dependency records:

```text
Existing photos, masks, calibration and confirmed correspondences
    -> measured area and surface evidence per plant
    -> separate optical acceptance gate
    -> identity-preserving canopy assembly
    -> current canopy light interactions
    -> per-plant and per-compound light attribution
    -> explicitly defined growth response inputs
    -> conditional 30-day joint CompoundLeaf trajectories
    -> later observation association, comparison and re-anchoring
```

Geometry analysis may remain available while optical simulation is unavailable. Event forecasts may remain available without spatial placement if their parameters exist but directed stem geometry is missing. Report availability per output; do not replace a missing component with zero or suppress all useful independent results.

### Existing leaf geometry

Use supplied masks with original image coordinates, calibrated camera intrinsics/distortion, measured board poses and confirmed physical point identities. Keep camera calibration, capture style, grouping policies, fit views and disjoint held-out views attached to the results.

Preserve holes, disconnected tissue, folds and multiple local charts. Do not sum repeated photo projections as tissue area, add partial area to a calibrated total, fill hidden leaflets, or turn a bounding envelope into a leaf surface. Forward the original source and policy hashes and review status. A low reprojection error is not an independent physical-area validation.

### Reversible plant and canopy assembly

Distinguish **assembly and splitting of known digital plants** from **recovering plant identity in an unlabelled crowded photograph**. This task implements the former. Unresolved membership in a crowded observation remains an input/review dependency; geometry proximity alone must not assign ownership.

Maintain an immutable source hierarchy: source plant, placed instance, session/date, geometry variant, parent stem, compound, leaflet and triangle. Use the existing membership join of instance + session + organ + leaflet and retain all source keys. A placed copy of one source plant receives a separate instance identity; copied instances are not independent observed plants.

Assemble each plant in the shared grow frame using recorded placement and yaw. Reuse `tomato3d/light/frames.py::board_to_grow_mm` through its actual interface; do not duplicate the forward conversion or infer lamp placement from the capture board. Store the exact placement transform, its inverse and unchanged source geometry references. Check units, handedness, date compatibility, placement provenance and posture changes since capture. Do not silently combine incompatible dates into a simultaneous measured canopy.

Split by provenance and membership, never by spatial clustering. Return each instance's original local geometry and organ mapping, plus the associated canopy-context results. Retain immutable original coordinates rather than relying solely on floating-point inverse reconstruction. Conflicting IDs, duplicate physical tissue and ambiguous membership produce actionable audit errors.

Splitting a result preserves the light that plant received **inside the canopy**. It does not mean the other plants have been physically removed. A calculation with those plants removed is a separately labelled intervention requiring recomputation. Likewise, viewer visibility and reporting filters must not remove occluders from the calculation.

### Hierarchical light

Reuse the eight-subset A/B/C calculation: A is other tissue in the same compound, B is other compounds on the same plant, and C is other plants. Always retain the receiver, its own folds and fixed background.

Preserve baseline/full light, signed effects, overlap terms and Shapley allocation. Aggregate photon flux before dividing by supported one-sided area. Do not sum individual source-removal effects as an additive loss. A zero baseline has an unavailable loss fraction.

Keep received flux and absorbed flux in umol/s, PPFD in umol/m2/s, and supported area in m2 in the existing light outputs. Retain separate incident/absorbed definitions in every adapter. Lamp PPF is not leaf PPFD; electrical power is not photon flux. Partial supported tissue does not establish whole-plant absorption.

Direct transport and native reflected/transmitted transport remain distinct backends. Preserve current shared leaf-optics limits. Reuse native preparation and its explicit execution/budget interface; default integration and tests do not launch native jobs. Never silently substitute direct results for requested native physics.

The current hierarchy reports full-output light, not DLI. If an integration adapter adds DLI, require a declared schedule and documented PPFD over time. Integrate incident PPFD as `sum(ppfd_umol_m2_s * duration_s) / 1e6`, yielding mol/m2/day. A constant-PPFD simplification must explicitly state constant light and geometry over the lit period. Do not label a full-output snapshot as measured daily exposure.

### Growth prediction and coupling

Implement the proposed stochastic graph/event and correlated continuous-trajectory interfaces from the detailed growth specification, preserving their scientific-review status. Numerical operation may use explicitly supplied, labelled assumptions; missing biological values stay unidentified. No default cultivar, growth rate, angular distribution, stop probability or covariance may be invented.

At the forecast origin, preserve existing measured attachment and axis geometry exactly. Use confirmed order/adjacency, directed parent stem and apex evidence. Forecast the appearance time, existence, attachment XYZ, direction unit vector, axis length and left/right extent of future **CompoundLeaf** units. Do not generate individual future leaflets in this scope. Keep future IDs trajectory-local until an observation association is supported.

Use 30 calendar days, explicit sample count, seed and output days. Preserve coherent joint trajectories across organs and dates, within-day birth events and output-step independence. Retain multimodal outcomes and conditional geometry summaries. Follow the provided-axes and retained-leaf limits; do not imply unrestricted branching or senescence.

Keep `temperature_c`, `relative_humidity_pct`, `ppfd_umol_m2_s`, `photoperiod_h`, `ec_ms_cm`, `ph`, and `co2_ppm` as scenario inputs with their source units. Distinguish externally supplied incident PPFD from organ-level canopy results, and record the chosen coupling input and time/area basis.

Add an explicit light-to-growth adapter contract containing the input metric, supported tissue/organ scope, time basis, response function/version, parameters with units and sources, valid domain, and applicability/review status. Only an explicit applicable response may turn light into a growth-rate or direction change. Do not infer that leaves always turn toward the brightest direction, equate absorbed photons with biomass, or copy the monthly multiplier product as physiology. Without the response contract, export light and growth outputs separately and report `light_growth_coupling` unavailable.

Future block envelopes remain `optical_eligible=false` and `suitable_for_ppfd=false`. Their probability density is not opacity. Do not feed them back into native/direct light as actual tissue. A dynamic loop that recalculates light on newly grown leaves requires an additional reviewed tissue-development and optical-eligibility contract; identify that dependency explicitly. A fixed current-light scenario can be offered only with its fixed-geometry assumption visible. Full future canopy feedback remains an open scientific capability until that contract exists.

Keep Flow Matching disabled. No model training, new physiology/yield model, tissue generator, new renderer or UI is part of this integration. Reuse existing viewers where possible and clearly distinguish measured geometry, candidates and forecast envelopes. On later observations, preserve prior forecasts and immutable measured records; use confirmed/ambiguous/unmatched association states. Re-anchoring without an observation likelihood must not claim Bayesian calibration.

## Integration interfaces and deliverables

The names below are proposed integration interfaces, not claims that these files already exist. Check for equivalents before adding them; reuse an equivalent implementation rather than maintaining duplicates.

| File | Responsibility |
| --- | --- |
| `tools/integrated_tomato.py` | CLI and stage orchestration with `audit`, `prepare`, `run`, `split`, and `evaluate` operations. |
| `tools/canopy_state.py` | Validated instance assembly, source mappings, transforms and reversible splitting, reusing existing placement semantics. |
| `tools/growth_light_adapter.py` | Explicit organ-light to growth-feature mapping and response eligibility. |
| `tools/probabilistic_compound_growth.py` | Proposed numerical forecast implementation, only if not already present. |
| `tools/tests/test_integrated_tomato.py` and focused adjacent tests | Cross-stage identity, units, eligibility and dependency regressions. |
| `tools/INTEGRATED_TOMATO.md` | Exact installed CLI, schemas, example commands, output meanings and limitations. |

Use these logical contracts, resolving actual Python types against existing code before implementation:

```text
audit_inputs(input_manifest) -> stage_statuses, blockers, dependency_hashes
assemble_canopy(plant_sources, instances, scene_ref) -> canopy_state, membership, transform_records
split_canopy(canopy_state, result_refs, selected_instance_ids) -> per_instance_states_and_results
build_growth_inputs(observed_states, organ_light_results, environment_scenario,
                    response_contract) -> eligible_growth_inputs, limitations
run_forecast(growth_inputs, parameter_spec, horizon_days, sample_count,
             seed, output_days) -> events, block_states, trajectories, summaries
```

Create one versioned input JSON referencing existing geometry studies/results, measured growth states, light input/scene/membership/reviews, plant placements, future environment, parameter evidence and optional independent evaluation data. Resolve relative paths from that manifest. Reuse the source schemas instead of flattening away provenance. Document required versus optional fields, units, exact composite keys and dependency rules. Unknown data in a blank template remain null; any complete demonstration uses visibly synthetic fixtures.

Output one fresh run with `audit.json`, `manifest.json`, an instance/transform manifest, membership CSV, references to area outputs, existing hierarchical light CSVs, optional explicit growth-coupling CSV, the growth brief's forecast/update/evaluation files, and a per-instance export index. Empty or skipped stages carry a reason rather than fabricated rows. Preserve existing module missing-value representations with documented, lossless adapter conversions; JSON missing values are null. Retain hashes, versions, seeds, backend/resource settings, coordinate frames, units, and dependency/staleness information.

Prepare a blank input template and a separate synthetic multi-plant demonstration. A run should support auditing real references without triggering geometry, inference or native transport automatically. Scope execution to local authorized code and bounded tests/direct demonstrations; do not launch training, remote jobs, uploads or publication.

## Literature and parameter evidence

Do not delay software plumbing for an open-ended literature review. Create a compact parameter-evidence register with value/status, unit, equation or model version, source locator, cultivar, developmental stage, growing conditions, uncertainty and applicability. Missing values stay unset. Request scientific review through the existing handoff when needed.

The evidence categories required for later scientific completion are: dwarf cultivar architecture and growth habit; leaf appearance intervals; compound/leaflet expansion and angle trajectories; responses to temperature/light spectrum/intensity; leaf optics and lamp emission; carbon assimilation/allocation if mechanistic physiology is later requested; canopy density and shading; image geometry/area measurement error; and longitudinal independent validation. Literature supplies candidate priors or laws, not automatic calibration for the user's plants.

## Implementation order and verification

1. Inspect source contracts and produce a requirement-to-module/status map. Record conflicts without silently changing protected specifications.
2. Implement manifest validation, immutable references, identity mapping, transform records and reversible assembly/splitting first.
3. Connect current eligible geometry and existing light calculations. Demonstrate multi-plant shading using synthetic optical tissue; do not promote real candidates to meet the demo.
4. Implement or reuse the specified forecast mathematics with explicit assumed parameters and provenance. Connect light only where the response contract permits it.
5. Add later-observation and independent-evaluation plumbing; preserve unavailable metrics when ground truth is missing.
6. Run focused checks and a bounded integration demonstration, then audit supplied real inputs and report actual missing dependencies. Do not repeat completed suites without a relevant code change or failure.

Required acceptance checks:

- Assembly followed by splitting restores source identity and immutable local geometry, with transform round trips checked against declared numerical tolerances. Test rotation/translation, identical source plants in different instances and membership conflicts.
- mm/cm2/m2 and flux/PPFD conversions are explicit. Reject incompatible frames, unresolved time alignment, stale hashes and ambiguous joins.
- Current measured state is unchanged at the forecast origin. Holes/partial coverage and missing observations stay explicit through every stage.
- Reporting or viewer filtering leaves occlusion unchanged. Physical removal is a separately recomputed intervention. Splitting preserves the full-canopy result context.
- Hierarchical signed Shapley allocations sum to total loss within the existing solver tolerance; aggregation uses total flux and supported area. Source-removal effects remain nonadditive.
- Candidate surfaces and predicted envelopes cannot become optical inputs. Missing scene, review, response parameters or stem evidence produces component-specific unavailable states.
- Seeds reproduce trajectories and requested output sampling frequency does not alter the underlying trajectory. Event times and IDs remain coherent across birth and stop events.
- Later data cannot overwrite historical forecasts or become available before the forecast origin in evaluation. Use chronological evaluation with independent plant groups and compare persistence/recent-change baselines at supported 7/14/21/30-day horizons.
- Synthetic correctness, assumed scenarios, real physical validation and independent predictive performance are reported separately. No arbitrary scientific accuracy threshold or biological acceptance flag is created by the implementation.

## Final report

Report in Korean: implemented files and usable commands; demonstrated stages and fresh test results; real-input audit results; and exact remaining scientific/data dependencies. Link the execution brief and reproducible artifacts. Report software completion separately from full physical/predictive completion. Do not describe a disconnected scenario as a validated light-driven growth simulator.
