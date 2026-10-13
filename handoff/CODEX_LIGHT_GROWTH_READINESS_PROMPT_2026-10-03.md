# Light simulator extension before compound growth direction modeling

Date: 2026-10-03. Recipient: Codex for owned light tooling; Claude for any required core interface change or biological interpretation. This is an implementation prompt authored at the user's request, not an executed implementation or a claim of validated plant prediction.

## Objective and order

First extend the existing light simulator so its results can be consumed reliably by the CompoundLeaf direction/area project and the FSP physiology calculator. Audit missing interfaces, implement the light-side changes, verify export/import behavior, and deliver a revised light IO handoff. Only then prepare the separate growth-direction implementation prompt. Do not implement biological growth, fit phototropism parameters, or turn maximum light into a predicted leaf direction in this task.

Required chain:

```text
Reviewed metric leaf surfaces + compound identity/axis observations
  -> reversible placement of individual plants into a canopy
  -> full-scene spatial, directional and time-resolved light calculation
  -> per-sample, leaflet, compound, plant and canopy outputs
  -> per-instance exports in the original plant frame, retaining canopy context
  -> direction/area covariates and physiology-ready light inputs
```

User authorization here is to prepare this prompt. Executing it is a later task. Do not describe the requested outputs below as already available.

## Repository and source requirements

Project: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.

Read parent `공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, latest LOG and relevant TODO. Codex owns `tools/` and `tools/tests/`; `tomato3d/` and `tests/` are Claude-owned, `config/` is human-owned. Keep raw/human observations unchanged. Use English handoff/code, Korean discussion, CSV tables, JSON settings/provenance and fresh `build/` outputs. No concurrent edits to files another session owns actively.

Read these existing interfaces and inspect their current implementation before editing:

- `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md`, `tools/HIERARCHICAL_LIGHT.md`, `handoff/CODEX_HIERARCHICAL_LIGHT_IMPLEMENTATION_2026-10-03.md`.
- `handoff/CODEX_GROWTH_IO_BRIEF_2026-10-03.md`, `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md`, `handoff/CLAUDE_FSP_PHYSIOLOGY_ACCURACY_PROMPT_2026-10-03.md`.
- `tools/hierarchical_light.py`, `tools/hierarchical_light_native.py`, `tools/canopy_light.py`, `tools/plant_light_bridge.py`, `tools/compound_growth.py` and any current probabilistic-growth implementation.
- Read-only core: `tomato3d/light/raytrace.py`, `pipeline.py`, `frames.py`, `scene.py`, `budget.py`, `geometry.py`, and `tomato3d/io/schemas.py`.

The physiology prompt specifies downstream carbon accounting. This light task supplies photons, geometry and provenance; it does not compute respiration, dry mass or biological orientation responses.

## Evidence-based gap assessment at prompt preparation

The following findings come from the actual source, contract and saved synthetic CSV headers inspected on this date. Recheck them because other sessions may progress. Historical test counts are not current verification.

| Need | Existing evidence | Required change or limit |
|---|---|---|
| Metric supported area and scalar light | `hierarchical_light.load_context`, `calculate_direct`, `write_report` compute supported one-sided area and received/absorbed flux | Preserve; expose area basis and completeness in every consumer export. No reconstruction from relative image areas. |
| Hierarchical shading | Eight retained-target subsets, A/B/C Shapley and directed source-removal tables already exist | Reuse, preserving signs, target/background retention and nonadditivity. Counterfactual baseline sums are not physical whole-canopy flux. |
| Fine spatial inputs | Core `DirectLight` has per-fixture/per-receiver arrays; hierarchy currently reduces them to leaflet totals | Export full-scene quadrature samples and weights before reduction for nonlinear physiology and spatial contrasts. |
| Leaf sides | Core has `upper_side_ppfd_umol_m2_s`; hierarchy discards it. Receivers are two-sided | Export normal/opposite side values and normal convention. Normal side is not necessarily biological adaxial side. |
| Light arrival direction | `raytrace.direct_light` computes `direction` and `shaded_per_emitter` internally, but does not return angular contributions | Requires a reviewed core diagnostic hook or another exact supported backend interface. Lamp-center direction is insufficient. |
| Compound orientation and lateral basis | `compound_growth.axis_traits` supplies signed direction; whole rachis and transverse observations exist in its contract | Explicit observation join and frame transformation required. Triangle normal is not compound rachis direction. |
| Time and DLI | Hierarchy reports full output only. Shared `ScheduleSegment` has `start_hhmm`, `end_hhmm`, `output_fraction`; `scene.full_output_hours_per_day` and `budget.dli_mol_m2_day` exist | Reuse schedule semantics, add dated/timezone-aware light-series export and explicit geometry validity. Do not claim DLI is missing everywhere in the project. |
| Canopy assembly | `canopy_light.materialize_case` preserves source/instance provenance; `frames.board_to_grow_mm` implements yaw plus translation | Add explicit reversible instance/transform mapping and context-preserving per-plant result exports. No new registration inferred from photos. |
| Native capabilities | Current collector returns combined-fixture received/absorbed flux, without angular or side channels | Publish per-backend capabilities. Preserve valid scalar results while marking unsupported direction/side values unavailable. Do not synthesize them from direct-only outputs. |
| Reliability and physical use | Hashes, reviewed surfaces, identity gates and diagnostic validity flags exist | Add consumer-specific availability states; synthetic/software checks do not establish physical or biological accuracy. |

Saved evidence inspected: `build/hierarchical_light_20261003_04/results/interaction_cases.csv` and `compound_interactions.csv`. Their fields have no time-resolved directional features. These are synthetic historical outputs, not new real-plant validation.

## 1 Preserve geometry, area and identity

Retain existing source hashes, accepted surface reviews and exact physical leaflet identities. Keep source plant distinct from canopy instance. Define the export join key as `(run_id, scenario_id, geometry_snapshot_id, plant_instance_id, session_id, compound_id, time_step_id, backend, replicate)`, adding leaflet/triangle/sample/fixture keys at finer levels. `compound_id` maps to growth `compound_leaf_id` only through an explicit reviewed association, never a height-rank guess. Keep unassigned tissue as unassigned; do not drop it from optical occlusion.

Record `source_plant_id`, `capture_date`, `observed_at` where supplied, `geometry_variant_id`, review/evidence hash and `data_kind` separately. A capture date does not establish an observation clock time. Future trajectory-local IDs remain different from observed biological identities. Copied plants are explicit hypothetical instances, never independent measured individuals.

Canonical optical units: geometry in mm, area in m2, photon flux in umol/s, photon flux density in umol/m2/s, duration in s and dose in mol/m2 over the named interval. Export growth area in cm2 using `area_cm2 = area_m2 * 1e4`; `area_m2 = area_mm2 * 1e-6`. Dimensionless first-leaf=1 ratios and image/bbox pixels remain in separate fields and cannot supply metric area, absolute intercepted flux or gC.

Use `area_basis_id`, `supported_area_m2`, `coverage_status`, `estimated_total_area_m2` and `coverage_fraction` with independent availability. The latter two stay unavailable unless supported by separate evidence. Never set coverage=1 because every supplied triangle was processed. Do not sum different photographs or overlapping alternative surface variants as extra tissue. Holes and folds remain geometric facts, not filled envelopes.

Aggregate sample flux before division: `Q = sum(q_i * w_i)` and `mean_q = Q / sum(w_i)`, where `w_i` is supported one-sided area in m2. Preserve sample weights and completeness. Missing required components make the full aggregate unavailable; a separately named supported subtotal may remain available. A real zero-light result is different from a missing result. Compute distributions/quantiles with area weights, not triangle counts.

Keep total two-face received photons per one-sided area explicit. Export `normal_side_ppfd_umol_m2_s`, `opposite_side_ppfd_umol_m2_s`, `received_ppfd_umol_m2_s` and `absorbed_ppfd_umol_m2_s`. For direct transport with matching finite channels, opposite = total - normal side within numerical tolerance. Unknown botanical surface orientation must not become an adaxial/abaxial label. State the supported spectral band; unknown spectral calibration remains unknown. Broadband PAR cannot manufacture blue-light or red/far-red signals.

## 2 Direction and spatial features

Proposed feature contract, not a biological response law: preserve positive incident contribution `p_ij` at receiver i from emitter/path j after attenuation and receiver cosine, and unit vector `u_ij` pointing from receiver toward the arriving-light origin (opposite photon travel). Export this sign convention and coordinate frame. For reflected paths, last-path arrival direction is required; original lamp-center direction is not its substitute.

For a compound or named supported region use weights `W_ij = w_i * p_ij`. Calculate:

```text
F = sum(W_ij)                                  [umol/s]
M = sum(W_ij * u_ij)                           [umol/s, 3 components]
B = sum(W_ij * outer(u_ij, u_ij))              [umol/s, symmetric 3x3]
mean_arrival_vector = M / F                    [dimensionless, not generally unit length]
directionality = norm(M) / F                   [dimensionless]
dominant_arrival_unit = M / norm(M)            [dimensionless, only when nondegenerate]
angular_second_moment = B / F                  [dimensionless]
```

At F=0, normalized features are unavailable with `zero_received_flux`; keep actual F=0. At cancellation, dominant direction is unavailable, while the second moment retains opposing-light information. Declare numerical degeneracy tolerance without representing it as a biological threshold. Retain per-fixture features and, where feasible, an explicitly defined angular-bin export; sum unnormalized moments before normalization. Do not average unit directions or angles naively. All these features describe light captured by current tissue, not an orientation-independent ambient field or an optimum growth direction.

Use measured `attachment_xyz_mm`, full rachis direction and reviewed transverse vector from the compound-state input to express M and B in a compound-local frame. Export signed azimuth/elevation of the observed rachis separately from incident-light angles. A stem axis alone cannot determine azimuth; an unsigned triangle normal cannot determine left/right. If the frame is incomplete, retain grow/board-frame features and mark only local features unavailable.

Where supported tissue can be assigned unambiguously to measured local regions, export left/right and proximal/distal area, flux and area-weighted mean PPFD. Define the partition and boundaries in JSON, preserve unassigned area, and report unequal coverage. Publish raw numerator/denominator and signed contrast; do not infer a whole-compound growth asymmetry from unequal partial support. Do not create transverse axes or hidden leaflets from convenience defaults.

A separate opt-in probe mode may sample the local environment using specified locations and receiver orientations with all actual occluders retained. Probes have no tissue mass/area and must not enter plant absorption totals. Changing a probe normal does not simulate rotation of the real leaf or its changed shadow. Actual candidate-geometry optical comparisons require reviewed metric tissue, recalculation and their own hypothetical scenario, not display rotation or an opaque CompoundLeaf envelope.

Core ownership dependency: first reuse public arrays for sample and side export. Request a backward-compatible optional diagnostic return/callback from Claude for the per-path/per-emitter moments in `tomato3d/light/raytrace.py`. The default `DirectLight` behavior must remain compatible. Do not copy a second ray tracer into `tools/` or edit protected core files as Codex. Record the exact hook request in `handoff/TODO.md`; continue independent owned work, but leave direct directional readiness incomplete until the hook and parity checks actually exist. Do not send another chat a message without human authorization.

## 3 Time-resolved light and downstream physiology

Create an explicit interval request with timezone-aware `start_at`, `end_at`, timezone, schedule provenance and geometry validity interval. Reuse existing schedule start/end, midnight-crossing and output-fraction rules. Validate conflicting intervals and missing schedule inputs; do not treat an absent schedule as lights off. Export clock time, duration and whether environment/geometry is observed, held fixed, or forecast scenario. Split at fixture schedule boundaries and supplied geometry/optics changes.

For fixed geometry, optics, beam pattern and spectrum within the declared model, scale each fixture's full-output contribution by its specified photon-output fraction, then sum fixtures at each time. Record that condition; current native `fixture_id=all` cannot support different per-fixture schedules without separate responses or reruns. Do not linearly scale electrical watts to obtain PPFD, and do not distribute a combined native result across lamps by guesswork. Distinct dimming spectra/geometry require their own supported inputs or an unavailable state.

Integrate `incident_dose_mol_m2 = 1e-6 * sum(PPFD_k * dt_s_k)` over covered intervals; likewise keep absorbed dose separately and `absorbed_photons_mol = 1e-6 * sum(absorbed_umol_s_k * dt_s_k)`. Report `covered_seconds`, requested duration and gap status. Only a complete declared daily interval may be labelled DLI; partial intervals are doses. For changing geometry, integrate time-indexed flux and area consistently; never multiply total dose by the final day's area to invent intercepted photons.

Preserve the underlying spatial/time series for nonlinear assimilation; DLI or daily mean alone is not a substitute. The external physiology module joins temperature, RH/VPD, CO2 and optional leaf-temperature/water information by time and identity. Light code may carry hashes/references to these inputs but must not invent them, apply growth multipliers, or subtract respiration. Absorbed PPFD already includes absorptance and must not be multiplied by it again downstream.

Current future CompoundLeaf envelopes remain `optical_eligible=false`. A held-current-geometry time series is a labelled scenario, not a fully coupled future-canopy simulation. Do not synthesize future tissue to conceal this limitation.

## 4 Reversible canopy assembly and separation

Reuse `canopy_light.materialize_case` and the authoritative `frames.board_to_grow_mm` mapping. Serialize instance/source identities and the resolved rigid transform `T_board_to_grow` plus inverse, units, source placement status and geometry hash. Derive the matrix consistently from the existing helper; do not invent a competing sheet-to-board or board-to-grow convention.

With column-vector convention `x_g = R*x_b + t`, recover `x_b = R.T*(x_g-t)`. Directions/normals transform with R only, and second moments with `B_g = R*B_b*R.T`; translations never affect vectors. Validate orthonormal rotation and a round trip. Reject unsupported tilt/scale rather than claiming the existing yaw-only placement implements arbitrary registration.

Export per-instance results back in the source board frame without changing source files or removing neighbors from the computed scene. Preserve `canopy_run_id`, complete context geometry hashes and placement. A plant split out for reporting retains canopy shading; a standalone plant requires a separately labelled new optical calculation. Matching IDs or coordinates alone cannot make standalone and canopy PPFD interchangeable. Two copies of one source plant remain distinct export instances even when both inverse-transform to the same source geometry.

## 5 Proposed files and consumer interface

Prefer additive `tools/light_growth_bridge.py` with focused `tools/tests/test_light_growth_bridge.py`, reusing the hierarchy pipeline. Inspect first for an equivalent. Extend `tools/hierarchical_light.py` only for necessary nonbreaking hooks and export integration, coordinating active file ownership. Preserve old outputs; use an explicit new schema, proposed `light-growth-1`, for the additional package.

Proposed public functions to finalize in the execution brief:

```text
audit_growth_light_inputs(request_path) -> report
export_spatial_light(prepared_run, full_scene_results, out) -> manifest
compute_directional_features(sample_contributions, memberships, frames) -> records
integrate_light_schedule(full_output_data, schedule, intervals) -> records
export_compound_light_features(spatial, directional, temporal, compound_states) -> records
split_canopy_results(package, instance_id, out) -> manifest
validate_growth_light_package(package) -> report
```

Produce `package.json` with schema, source/code/artifact hashes, units, coordinate conventions, backend capabilities, per-feature status/reason, geometry validity, timestamps and uncertainty scope. Geometry, optics/calibration, numerical and Monte Carlo uncertainties must remain distinct. A deterministic run has no invented replicate uncertainty.

Required tables and metadata:

| File | Minimum content beyond shared identity/run keys |
|---|---|
| `instance_map.csv` and `transforms.json` | Source/instance/compound associations, review status, transform identifiers, forward/inverse matrices, frame definitions and placement provenance |
| `light_samples.csv` | Stable triangle/sample keys, grow/board XYZ, normal, quadrature area, fixture, time step, side/received/absorbed PPFD, status/reason and geometry snapshot |
| `compound_light_features.csv` | Supported area/basis/coverage; received/absorbed flux and means; observed rachis direction; M/B and normalized directional values in named frames; supported spatial contrasts with coverage |
| `light_intervals.csv` | Time step bounds/duration, fixture output fraction, snapshot/scenario, values, availability and fixed-geometry assumptions |
| `light_dose.csv` | Per-organ and plant interval dose/absorbed photons, time coverage, area basis, complete-day flag and integration method |
| `consumer_mapping.json` | Exact key/field/unit conversions to compound-state/growth and physiology contracts, unsupported fields and required inputs |
| `capabilities.json`, `audit.json` | Capability by backend/quantity, blockers, partial products, code/data freshness and diagnostic/physical-validation distinction |

Finalize every CSV column name, type, unit and join key in a machine-readable schema before implementation. Do not leave x/y/z component names or second-moment order implicit. Encode structured arrays in JSON metadata or explicit scalar columns, not opaque Python repr strings in CSV. Unavailable numeric CSV values are `unavailable`; JSON uses null, always with reasons. Do not duplicate `fixture_id=all` totals when summing per-fixture rows.

Mapping to growth must include `compound_id -> compound_leaf_id` via reviewed mapping, source-board `direction_unit_xyz`, `supported_area_cm2`, `area_basis_id`, observation time and canopy-context references. Mark light arrival direction as a separate covariate. Mapping to physiology must include metric sample area, time duration, incident versus absorbed convention, both-side basis, spectral scope and provenance. Do not populate biological growth/respiration fields.

Provide per-feature readiness, rather than one broad ready flag. Valid scalar direct outputs may survive missing membership or local axes; compound features require reviewed membership, local features require local frames, absolute physiology requires metric tissue, directional features require actual angular data, and physical validity requires independent calibration. This separation must not hide missing required deliverables: report software capability completion separately from real-input readiness.

## 6 Verification and completion gate

Implement focused checks appropriate to this extension, then run existing relevant regression suites once after integration. Do not cite historical counts as new results. Required evidence:

1. Legacy scalar/hierarchy parity; same eight subsets, own-target/background retention, signed effects, Shapley accounting and source-removal nonadditivity. Report exact numerical tolerances used.
2. Sample quadrature sums equal leaflet/compound/plant full-scene scalar results; mean uses area weights; missing samples and duplicate faces/IDs fail explicitly. Do not use counterfactual baseline totals as physical canopy totals.
3. Known source direction and asymmetric source fixture; opposing equal sources yield near-zero first moment with nonzero second moment; rotation transforms moments correctly; normal+opposite equals total; biological side labels remain gated.
4. Uniform and spatially uneven test lighting, unequal receiver areas and partial left/right coverage; distinguish full-light zero from unknown contributions. No conversion from normalized image area to metric physiology.
5. Different fixture schedules, dimming, midnight crossing, actual blackout, absent schedule, time gaps and geometry changes. A synthetic constant 100 umol/m2/s for 12 h gives 4.32 mol/m2; this checks units only. Verify time-grid refinement and boundary splitting.
6. Assembly/split round trip for points, vectors and moments; two instances of one source remain separate; split exports preserve canopy shading and context. Isolated rerun is a distinct scenario.
7. Native combined-fixture restrictions, unavailable side/direction channels, resource budgets and no implicit native execution. Never silently combine native scalar transport with direct direction under one backend label.
8. Load the exported package through an independent consumer/schema check using current compound keys and physiology units. Reject stale geometry, wrong time/frame, ambiguous IDs and incompatible area bases. Preserve future-envelope exclusion and day-zero observations.

Use synthetic direct-light fixtures for executable software evidence; re-audit explicitly supplied real inputs without fabrication. A synthetic end-to-end run plus an honest real-input blocker audit is software verification, not evidence that real direction/area prediction is accurate. If a core hook remains unimplemented, report the extension as partially delivered and keep directional readiness open.

Respect existing native opt-in and explicit budgets; preparation/collection fixtures do not authorize GroIMP execution. No training, new inference, remote upload or growth-model execution is required. Unknown biological or physical acceptance thresholds remain inactive; do not invent them to pass.

Deliver a fresh `build/light_growth_readiness_<run>/` example with all supported exports, schema/consumer checks, test results and requirement-by-requirement evidence. Write `handoff/CODEX_LIGHT_GROWTH_READINESS_EXECUTION_2026-10-03.md` before implementation and append actual results afterward. Append a dated supplement to `CODEX_LIGHT_IO_SUMMARY_2026-10-03.md` distinguishing implemented, unavailable and pending core/physical work; preserve its historical text. Append LOG and relevant TODO records.

The final Korean response must list the actual light changes and remaining dependencies, show how a growth consumer joins direction/area/light fields, and explicitly state whether the prerequisite is ready for writing the subsequent growth-direction prompt. Completion of this light task never claims that leaf growth direction, new area or physiology has been predicted.
