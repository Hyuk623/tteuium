# Dwarf tomato growth calculator implementation handoff

Date: 2026-10-03. Recipient: the next Codex implementation session. Prepared at the user's request as a growth-calculation-only prompt. This handoff has not been executed and does not claim scientific review or validated predictive accuracy.

## Objective

Implement the numerical growth calculator for the dwarf tomato simulator. Given a measured plant state, optional observed history, a declared future environment and explicit biological parameter assumptions, calculate joint 30-day trajectories of CompoundLeaf appearance, attachment, direction, size and supported growth quantities.

The deliverable is a callable Python module and CLI with CSV/JSON outputs and focused tests. It must work independently of image processing, canopy assembly and light simulation. Those systems provide inputs or consume results; do not rebuild or run them here.

Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.

## Required context and ownership

Read the parent `공통규약.md`, project `AGENTS.md`, `CONVENTIONS.md`, latest five LOG lines and relevant TODO items. Create an English execution brief before implementation and update it with results. Codex owns `tools/` and `tools/tests/`; keep `tomato3d/`, `tests/`, `config/`, `docs/` and human observations read-only. Use fresh `build/` output directories and append an English completion entry to `handoff/LOG.md`.

Read these existing contracts:

1. `handoff/CODEX_GROWTH_IO_BRIEF_2026-10-03.md`: input/output vocabulary, environment units and scope.
2. `handoff/CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md`: detailed proposed mathematics, identities, event grammar, decoder, update method, schemas and verification.
3. `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md`: interpretation of optional area evidence only.
4. `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md`: interpretation of optional externally supplied light results only.

This handoff narrows the integrated simulator task to growth calculation. It does not replace the detailed growth schemas or make its proposed biological rules scientifically accepted. Implement the specified mathematics with explicitly labelled assumption configurations; refer scientific model changes to Claude through the existing handoff. Do not invent coefficients while resolving software details.

## Existing work to reuse

Inspect current source before adding files. Reuse `tools/compound_growth.py` for measured-state extraction, checks and persistence/recent-change baselines, and `tools/leaf_light/common.py` for applicable I/O. Inspect `tools/monthly_growth.py` for compatible environment vocabulary and scenario handling; its assumed multiplier product and fixed-attachment behavior are not automatically the new model's laws.

The detailed contract proposes `tools/probabilistic_compound_growth.py`. If it now exists, assess and extend it within scope rather than creating a second growth engine. No production code was inspected or executed for this handoff; the receiving session must verify actual implementation status.

## Calculation scope

| Component | Required calculation | Dependency |
| --- | --- | --- |
| Leaf appearance | Residual time to the next event, subsequent appearance intervals, event count and stopping state | Explicit event distributions and supported apex state |
| Existing leaf growth | Remaining axis-length and left/right-extent changes, with optional rotation | Measured initial shape and explicit remaining-growth parameters |
| Future leaf growth | Birth direction/dimensions and subsequent coherent changes | Conditional birth and growth parameters |
| Stem growth | Material-segment elongation and movement of associated attachments | Directed measured stem, reviewed attachments and explicit segment parameters |
| Spatial placement | New attachment XYZ and direction relative to the parent | Reviewed parent geometry, local frame and apex evidence |
| Optional area growth | Area trajectory on a declared comparable tissue basis | Independent area evidence and a separately supplied area-growth relationship |
| Environment response | Modification of enabled growth parameters or development clock | Explicit response functions, units, valid domains and coefficients |

The prediction unit is a CompoundLeaf. Do not generate individual leaflets, optical meshes or unsupported branches. Preserve the provided-axes and retained-leaf applicability of the detailed contract. Root growth, fruit yield, sugar content, senescence and mechanistic photosynthesis/carbon allocation are outside this version.

## Inputs and units

Use the exact versioned schemas in detailed specification section 9.2, including `origin.json`, `parent_axis_points.csv`, `attachments.csv` and `model.json`. Build adapters to the existing observation bundle without changing it.

Required input groups are:

- Identity and origin: plant, session, parent-stem and confirmed compound IDs; observation timestamp; stable frame; source paths and hashes.
- Measured state: attachment coordinates, complete supported axis points, direction, axis length, left/right extent, shape references and field-level availability. Optional area retains its coverage basis and provenance.
- Parent topology: directed stem polylines, reviewed apex/attachments, confirmed order and adjacency. Visible neighboring leaves do not prove biological adjacency.
- Optional history: earlier comparable observations and appearance/visibility intervals. A first detection after occlusion does not establish birth time.
- Parameter evidence: values or distributions, units, transform order, source, cultivar/conditions where known, uncertainty, applicability and status such as measured, user-assumed, literature-informed, fitted or unidentified.
- Computation: `horizon_days=30`, explicit `sample_count`, `seed`, `output_days` and numerical tolerances. No biological value is supplied by a computation default.

Positions and lengths are mm; area is cm2; directions are unit vectors. Internal angular calculations use radians. Preserve each detailed-schema field's explicit angular unit, including radian-valued model parameters; use the project's degree convention for degree-labelled display/export fields and never silently convert coefficients or covariance entries. Time is calendar days or separately labelled development days. Do not mix the two clocks.

Retain these optional environment fields: `temperature_c`, `relative_humidity_pct`, `ppfd_umol_m2_s`, `photoperiod_h`, `ec_ms_cm`, `ph`, `co2_ppm`. Their units are deg C, %, umol/m2/s, h/day, mS/cm, dimensionless, and ppm respectively. Future values are a declared scenario, not observations.

Cultivar, sowing/transplant dates, histories and future environment values were not supplied in the source brief. Keep templates blank and inputs adjustable. Do not assign a cultivar, infer exact age from leaf size, or manufacture temporal rates from a single snapshot.

## Growth mathematics and state handling

Implement the detailed contract's event-driven stochastic graph grammar, joint parameter sampler and continuous decoder. Use its waiting/stop and conditional trait definitions without silently changing their meaning. At the origin use the residual wait to the next appearance; do not assume a leaf was born at time zero and apply a complete inter-event interval.

Preserve observed day-zero geometry exactly, including bends and attachment offsets. Use separate conditional remaining-growth parameters for existing leaves; do not apply a newborn prior to them. Follow material-segment attachment movement from the detailed specification instead of copying fixed attachments from the monthly scenario tool.

Sample parameters and events coherently for a trajectory, then decode requested times without new random draws. Do not independently generate a new plant on each output day. Retain plant-level effects, cross-trait covariance and temporal dependence only where their values/assumptions are supplied. Unknown covariance is not silently zero.

Maintain trajectory-local future IDs, birth/stop states, and coherent spatial references. Prebirth geometry is unavailable, not zero-sized measured tissue. Preserve multimodal outcomes and distinguish unconditional occurrence probability from geometry conditional on existence.

Area requires its own evidence and relationship. A block's axis length times width is not automatically tissue area. Never combine supported partial area with an estimated whole-plant total or present envelope expansion as measured leaf-area growth.

## External light and environmental coupling

Accept optional light features from an external calculation with plant/compound identity, date/time, receiving-area basis, metric, unit, backend and provenance. Do not run GroIMP or the hierarchy calculator. Distinguish incident PPFD from absorbed photon flux; neither automatically specifies a growth rate.

Environment or light affects the calculation only through a declared response contract identifying input metric, affected growth quantity, equation/version, parameters, applicability domain and evidence/review status. Do not assume that a leaf turns toward the brightest point, or that all environment multipliers can be multiplied together. If no response exists, retain the fields as metadata and explicitly report that environmental/light coupling is unavailable.

A forecast may use a declared fixed-light scenario, but it must not imply recalculated future shading. Future blocks remain `optical_eligible=false` and `suitable_for_ppfd=false`. Canopy feedback, future optical tissue and current-leaf reconstruction belong to other tasks.

## Functions and outputs

Implement the proposed public functions from specification section 9.1, preserving its arguments and behavior:

```text
prepare_origin(history_dir, structure_path, origin_config)
validate_model_config(config, origin)
sample_forecast(origin, config)
decode_trajectory(trajectory, elapsed_days)
summarize_forecast(bank, summary_config)
update_forecast(previous_run, observation_dir, associations, observation_model)
evaluate_forecasts(run_paths, target_dir, evaluation_plan)
export_run(result, output_path)
```

Produce `events.csv`, `block_states.csv`, `trajectories.csv`, `trajectory_parameters.json`, `summary.csv` and `manifest.json` with the detailed schema. When applicable, also produce `update.json`, `associations.csv` and `evaluation.csv`. Keep source shape references and full decoder parameters; a summary table must not replace measured geometry or erase trajectory dependence.

For this growth interface, unavailable JSON values are null and unavailable CSV values are empty cells with the prescribed status/reason. A true numeric zero stays zero. Represent infinite stopping time as a stopped state and null time, not JSON Infinity. Separate malformed input, numerical failure and scientific unavailability. Use existing `StudyError` conventions for invalid input and structured component/reason/source records for unavailable science.

When a component lacks inputs, calculate independently eligible components. For example, supplied event parameters may allow count forecasts while missing parent geometry prevents attachment XYZ. Never manufacture a stem or mark the entire spatial forecast valid to satisfy an output schema.

## Observation updates and evaluation

Preserve historical forecasts and immutable observations. Associate new measurements through supported confirmed/ambiguous/unmatched records; a predicted ID is not a newly observed identity by itself.

Use the detailed specification's finite-bank update only with a supplied observation likelihood and association evidence. Without a likelihood, allow discrepancy reporting and deterministic re-anchoring while marking parameter updating unavailable. Do not label unchanged assumptions a calibrated posterior. Re-anchor remaining growth without counting prior expansion twice.

Evaluate frozen forecasts chronologically with independent plant groups. Report appropriate available scores for appearance, counts, size, attachment, direction and uncertainty at supported 7/14/21/30-day horizons, and compare persistence/recent-change baselines. Missing targets stay missing. No automatic coefficient fitting or Flow Matching training belongs to this task; Flow Matching remains disabled.

## Implementation sequence and acceptance

1. Inspect existing functions and contracts. Record a requirement/status map and any unresolved scientific choice; do not start with a new framework or UI.
2. Implement origin validation, parameter evidence, units/frames and availability reporting. Deliver a blank model template without invented biological values.
3. Implement the specified event sampler and continuous decoder with explicit synthetic assumption fixtures; keep simulation examples separate from real observations.
4. Add joint summaries, immutable exports, update and evaluation functions, and a standalone CLI with `--help`. Document actual commands in `tools/PROBABILISTIC_COMPOUND_GROWTH.md` or an existing equivalent.
5. Run meaningful focused tests under `tools/tests/` and one bounded synthetic demonstration in a fresh `build/` directory. Audit supplied real data without repeating searches for inputs already confirmed absent.

Acceptance checks must cover exact day-zero state preservation, material attachment continuity, residual wait versus full interval, within-day birth and stop handling, unit vectors and angular wrap, missing/invalid parameters, probability/covariance validation, optional-area eligibility, and reproducible joint trajectories. Changing output frequency, row order or worker count must not change a keyed trajectory within the recorded numerical environment. Decoding must not draw randomness.

Check update history preservation, all-zero/nonfinite likelihood failure, re-anchoring without double-counted growth, future IDs, chronological evaluation and the inability to export a future envelope as optical tissue. Scientific accuracy thresholds must come from an explicit evaluation plan, not synthetic tolerances.

Deliver implementation, tests, templates, commands, outputs and an execution report. Do not stop at preparing another prompt when this handoff is later invoked for implementation. Conversely, missing biological evidence must remain visible even when all software tests pass.

## Completion report

Report in Korean what the calculator actually computes, the implemented files, verified commands and fresh test results. Separate software correctness, assumption-conditioned scenarios and independently validated forecasts. List only the specific remaining data/model dependencies, including any absent environment response. Append the required English LOG entry. No new image analysis, canopy integration, light execution, UI, training, remote job or source-data modification is included.
