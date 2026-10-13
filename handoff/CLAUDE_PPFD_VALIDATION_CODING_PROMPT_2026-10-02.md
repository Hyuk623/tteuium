# GroIMP light distribution validation coding prompt

## Task and scope

Extend the existing tomato application with a reproducible light-distribution validation workflow:

**Empty rig calibration -> held-out empty rig validation -> known opaque occluder -> reviewed real leaf surfaces -> independent plant PPFD validation -> readiness for canopy comparisons.**

Implement the software and synthetic checks first. Real experiments require supplied measurements and reviewed physical inputs. Missing measurements must remain unavailable. This prompt does not request model training, new reconstruction, growth prediction, first-flowering prediction, GitHub publication, or an agronomic optimum.

Work only inside `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`. Read `CONVENTIONS.md`, applicable agent instructions, the latest five lines of `handoff/LOG.md`, and `handoff/TODO.md`. Preserve ownership boundaries and avoid concurrent edits. Where an existing support tool belongs to another agent, reuse it through imports or its CLI and record any requested owner-side change rather than silently rewriting it.

## Inspect and reuse the existing implementation

Read these handoffs before coding:

- `handoff/CLAUDE_XL_LIGHT_PHASE2_V2_2026-09-29.md`
- `handoff/CODEX_XL_LIGHT_PHASE2_V2_REVIEW_2026-09-29.md`
- `handoff/CLAUDE_DENSITY_FIRST_FLOWERING_2026-09-30.md`
- The latest reviewed partial-surface and session handoffs.

Inspect these existing modules and contracts:

- `tools/groimp_light_sanity.py`: analytic/Python/native GroIMP checks and `run_groimp`.
- `tools/groimp_light_scene.py`: export hashes, scene conversion, optical/display separation and directional-light gates.
- `tools/groimp_density.py`: `sensor_triangles`, `surface_gate`, `lamp_adapter`, `prepare`, `execute`, `collect`, `validate_ppfd`.
- `tools/canopy_light.py`: existing placement and geometry conventions.
- `tomato3d.light` and `tomato3d.io.schemas`: authoritative scene and CSV contracts.

The September 30 handoff reports native one-sided sensor plates, reviewed-surface gates, PPFD error tables and synthetic checks already implemented. Do not rebuild these features. Its pinned September 29 XL bundle contained zero leaf surfaces; recheck the explicitly selected current bundle rather than assuming this historical count applies to all newer outputs. The directional LED adapter was still pending in that handoff. Inspect current code before declaring any gap resolved.

Do not use geometry from `tools/growth_simulator.py` as real plant geometry: it is an illustrative growth scaffold.

## Execution stages

### 1. Freeze input and measurement contracts

Reuse existing CSV headers wherever possible. Add a versioned adapter for additional fields without breaking existing readers.

Required metadata includes `study_id`, `run_id`, `stage`, `case_id`, `plant_id` where applicable, `session_id`, geometry snapshot date, `sensor_id`, `point_id`, repeat ID and timezone-aware observation time. Measurement roles must distinguish calibration from independent validation. Repeated readings at one point must share a split; do not put repeats of the same point into both roles.

Record:

- LED emitter dimensions, position, orientation, angular distribution, flux, output setting, and available spectrum; preserve measured/assumed/fitted/missing provenance for each input.
- Rig walls, floor and reflective surfaces, their geometry and optical assumptions.
- Sensor model, calibration reference, actual sensing shape/dimensions, centre in mm and unit normal in the explicit coordinate frame.
- LED stabilization, ambient-light conditions and whether sensor insertion moved leaves.
- Source file paths and SHA-256 hashes, scene settings, GroIMP version, ray count, path depth and reproducibility controls actually supported by the backend.

Reuse board-to-grow conversion helpers and convert mm to m exactly once. Do not infer pose from nominal capture angles or identify board size from marker IDs. Preserve current geometry quality flags.

Generate header-only human-input templates under a fresh `build/` folder. Do not write fabricated readings or edit `data/records/`, source labels, calibration, model weights, `config/` or `docs/`.

### 2. Calibrate the empty rig and freeze the lamp model

Support plant-free cases without requiring a leaf mesh. The suggested acquisition layout is three heights with a 3 by 3 grid at each height. This is a configurable pilot proposal, not an established sample-size requirement or a filled measurement table.

Fit only explicitly enabled identifiable lamp parameters against calibration points. Prefer a low-dimensional flux/angular-distribution fit with measured fixture geometry fixed. Report bounds, residuals and parameter ambiguity. Do not simultaneously fit leaf properties in an empty-scene stage.

Freeze the resulting adapter and its calibration dataset hash before evaluating held-out points. Preserve fitted parameters as fitted, not measured. If the supplied points cannot identify the requested parameters, return an explicit insufficient-calibration status.

Implement or integrate a directional LED adapter that matches the declared distribution and its flux normalization. An isotropic PointLight surrogate must not be promoted to a real directional LED prediction. Check optical power or photon-flux conservation and emitter placement before physical comparison.

### 3. Validate a known opaque occluder

Add a configurable, measured opaque plate with known dimensions and pose. Compare illuminated, shadow-interior and shadow-edge points. Keep this physical fixture separate from biological leaves and display-only markers.

Exercise synthetic analytic cases first, then accept independent measured plate records when supplied. Preserve stage-specific failures so lamp, sensor and occlusion problems are distinguishable from plant reconstruction errors.

### 4. Connect reviewed real surfaces

Use existing leaf triangle contracts, original scoped organ IDs, surface review records and source hashes. Bboxes, hull envelopes, centres, axes and toy leaves are not optical leaf replacements.

Record incomplete geometry and its implications for each measurement case. A partial leaflet can support a limited isolated test; it cannot explain whole-plant shading when missing organs intersect relevant light paths. Do not automatically certify completeness from triangle count.

Leaf reflection, transmission and absorption must be physically admissible and explicitly sourced. Preserve the difference between native diffuse transport and the existing Python direct/straight-transmission model. A disagreement between different transport models is not automatically a code bug.

Maintain separate outputs for front-face sensor incident PPFD, leaf received flux and leaf absorbed flux. Document one-sided versus two-sided area conventions; never rename both-face leaf flux as planar sensor PPFD.

### 5. Match the actual sensor and physical quantity

Reuse the existing one-sided sensing mesh implementation where applicable. Match centre, normal, footprint and area averaging; support or explicitly reject an unsupported sensing shape. Calculate each receiver independently if receivers would otherwise shade one another. Distinguish the virtual sampling surface from any real probe body or support that disturbs the experiment.

Do not substitute a spherical GroIMP SensorNode for a planar cosine-response quantum sensor without a demonstrated measurement-equivalence adapter. Verify front-facing, tilted, edge-on and reversed cases.

Preserve the established photon-rate numerical convention unless introducing a separately tested spectral path. Under the existing achromatic convention, numeric source flux is encoded in micromoles per second even though native GroIMP labels power in watts; do not apply another watt-to-photon conversion to it.

If physical spectral irradiance is instead supplied, explicitly convert each wavelength-bin energy contribution to photons using its wavelength and integrate 400-700 nm. Record whether inputs are per-nm densities or bin-integrated values. Do not use one universal W-to-PPFD factor or interpret electrical input watts as optical watts. Unknown power semantics must block absolute output.

### 6. Validate, diagnose and prepare canopy readiness

The suggested plant pilot is three accessible points in each of three height bands, with three sensor re-placement repeats per point. Leave unavailable or disturbed points in the audit. This remains a configurable acquisition proposal.

Evaluate only frozen-model predictions against independent readings. Compare empty-scene and plant-scene predictions at the same evaluation positions to quantify the contribution of plant geometry. Keep calibration metrics separate.

For each case compute error = predicted minus measured, MAE, RMSE, bias and normalized RMSE = RMSE / mean measured PPFD. Report normalized RMSE as unavailable when the denominator is zero. Aggregate valid repeats at each point for primary spatial metrics and separately report repeat variability. Preserve row counts, point counts, exclusions and failures; avoid weighting points more heavily merely because they have more repeats.

Report height-stratified results and uncertainty at the independent plant/plot/session level when the design supports it. Do not treat multiple sensor points as independent biological replicates. Confidence intervals are unavailable when replication is inadequate.

Add ray-count/path-depth convergence checks and configurable geometry/pose/optics sensitivity cases. Use supported independent random streams only; identical deterministic reruns do not estimate Monte Carlo uncertainty. Keep numerical convergence thresholds separate from experimental accuracy criteria. Do not invent a biological pass threshold; an unset experimental threshold means no pass/fail conclusion.

Canopy readiness requires independent evidence for the actual lamp, receiver and plant geometry. A successful native execution or a low synthetic error must never automatically change `validated_metric=false` or `suitable_for_ppfd=false`.

## Integration interface and artifacts

Extend the existing job/result flow rather than creating another application. Reuse `groimp_density` prepare/execute/collect operations. Add empty-rig calibration and occluder orchestration in the current owner's permitted package; record final module names in the completion handoff.

Suggested function contracts, mapped onto existing functions where possible:

- `validate_inputs(study_path: Path) -> audit_dict`
- `fit_empty_rig(calibration_csv: Path, scene_path: Path, fit_settings: dict) -> lamp_fit_manifest`
- `prepare_validation_cases(study_path: Path, out: Path) -> run_manifest`
- `compare_ppfd(predictions_csv: Path, readings_csv: Path, split_manifest: Path) -> metrics_and_audit`

All lengths carry `_mm` or `_m`; optical power and photon flux have different names and units. Retain `predicted_ppfd_umol_m2_s` and `measured_ppfd_umol_m2_s` in adapters to existing tables. Missing is not zero.

Each new immutable `build/ppfd_validation_<timestamp>/` run should contain:

- Input/settings/hash manifest, frozen split and lamp calibration manifests.
- Generated RGG projects and native execution logs/status.
- Sensor predictions, per-point comparisons, repeat statistics, stage/height metrics and sensitivity tables as CSV.
- Machine-readable readiness/exclusion report and an existing-viewer or HTML comparison report.
- Measured/predicted maps with shared colour scales and residual plots. Interpolated visual maps must not add evaluation samples.

Source changes mark dependent results stale; recomputation produces a new run. Keep failed and excluded cases visible. No sensors supplied means templates and software checks only, with independent accuracy unavailable.

## Tests and delivery

Test unit/frame round trips, normalized sensor normals, finite-area cosine response, directional flux normalization, inverse-square behaviour for an applicable point-source fixture, complete/partial occlusion, display-object exclusion, optical coefficients, and correct spectral conversion or photon-rate preservation.

Test calibration/evaluation separation, duplicated repeats, zero PPFD, missing records, hash mismatch, incomplete geometry, unsupported lamp/sensor semantics, stale results and error propagation. Verify calibration rows never enter independent metrics and input files remain unchanged.

Reuse focused tests for `groimp_light_sanity`, `groimp_light_scene`, `groimp_density` and `canopy_light`, plus tests for added behaviour. Run bounded native synthetic checks with explicit output limits. Keep expensive parameter sweeps off the local CPU; prepare a remote job only after verifying the target supports the selected GroIMP backend, and do not replace it silently with another engine.

Deliver runnable commands, actual test/native-run results, output paths and hashes, unresolved physical inputs and an English completion handoff. Explain in Korean what is implemented and what still requires measurement. Do not report a validated plant light model, photosynthesis, growth, flowering prediction or optimal planting density without the corresponding independent evidence.

## References

- [GroIMP sensors](https://wiki.grogra.de/doku.php?id=tutorials:light-modeling-sensors): native SensorNode geometry and measurement behaviour.
- [GroIMP spectral light modelling](https://wiki.grogra.de/doku.php?id=tutorials:basic-spectral-light-modeling): spectral transport configuration and outputs.
- [Apogee quantum sensors](https://www.apogeeinstruments.com/quantum/): PPFD sensor selection for LEDs.
- [Apogee sensor FAQs](https://www.apogeeinstruments.com/quantum-sensor-faqs/): sensor mounting and orientation.

## Preparation record

2026-10-02: Codex prepared this coding prompt at the user's request after reading the project rules, current queue/log, prior light handoffs and existing function/CLI declarations. No light simulation, calibration, measurement import or source-code modification was performed during prompt preparation. Historical test counts in referenced handoffs were not rerun for this documentation task.
