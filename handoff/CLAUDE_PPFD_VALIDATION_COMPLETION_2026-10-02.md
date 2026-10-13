# PPFD validation workflow — completion handoff (Claude Code, 2026-10-02)

Spec: `handoff/CLAUDE_PPFD_VALIDATION_CODING_PROMPT_2026-10-02.md` (Codex).

Scope delivered: software plus native synthetic checks. **No real PPFD reading, lamp value, sensor, rig surface or reviewed leaf surface exists in the project.** Every independent-accuracy result is therefore `unavailable`. `validated_metric=false` and `suitable_for_ppfd=false` everywhere. No training, reconstruction, growth or flowering work, and no GitHub push.

## Files

| File | Owner | Change |
|---|---|---|
| `tools/ppfd_validation.py` | Claude (new; tools/ by the usual user authorization) | whole workflow, CLI below |
| `tools/tests/test_ppfd_validation.py` | Claude (new) | 27 tests |
| `tomato3d/io/schemas.py` | Claude | (1) new `InputStatus` value `fitted`, also listed in `NON_OBSERVED_INPUT_STATUSES`; (2) bug fix: `ScheduleSegment` rejected `00:00-24:00` although its own error message tells users to write exactly that (start/end are now compared in raw minutes) |

No Codex file was edited. Reused by import, unchanged:
- `tools.groimp_density`: `mesh_node`, `sensor_triangles`, `surface_gate`, `execute`, `parse_log`, `verify_prepared`. The prepared `jobs.json` is in the format `groimp_density.execute` expects.
- `tools.groimp_light_sanity.run_groimp`.
- `tomato3d.light`: `build_emitters`, `cosine_exponent`, `fixture_axes`, `direct_light`, `input_records`, geometry placement.

## Directional LED adapter: what GroIMP actually does (native measurements)

Native probes ran on the installed GroIMP 2.2.1 CPU `LightModel`. Scripts are in `build/ppfd_led_probe_scripts_20261002/`; outputs are in `build/ppfd_led_probe*`.

| Light class | Result |
|---|---|
| `PointLight` | Isotropic; matches the analytic point source (ratios 0.97–1.03 at 10M rays). |
| `PhysicalLight` (GPUFlux, tabulated `double[][]`) | **Not usable on the CPU path.** `LightDistribution` itself behaves as documented: columns = polar angle from +z (u = j/(W−1)), rows = azimuth φ = π(2v−1) (periodic), entries = intensity, normalised; `getPower` of an all-ones table = 4π. The ray sampler, however, sends rays only along a few discrete directions. A *uniform* 72×181 table put all light into the horizontal plane; 64×64 and 181×72 tables gave other wrong patterns. A one-row table emits into one azimuth only. Separately, literal tables above ~10k non-zero entries fail to compile with `MethodTooLargeException`, which the CLI shows only in its log. |
| `AreaLight` on a `Parallelogram` | **Exact cos^m emitter.** Exponent e gives intensity ∝ cos^(e+1)θ about the emitting normal. Exponents 0 / 0.5 / 4 matched analytic cos^1 / cos^1.5 / cos^5 within MC noise at every sensor. `setPower` = total emitted flux. The Parallelogram emits along local +y, spans local x (centred) and local +z (0 → length). |

Adapter (`arealight_node`, `lamp_adapter`):
- Each LightScene fixture becomes one emitting rectangle with its measured length and width. AreaLight exponent = m − 1, with m from `cosine_exponent(half-angle)`.
- Placement uses `Null().(setTransform(Matrix4d))`: rotation columns = (width axis, aim, long axis) from `fixture_axes`; origin = centre − long_axis·L/2.
- Refused with an explicit reason, never replaced by a surrogate: cutoff < 90°; m < 1 (half-angle > 60°, which would need a negative exponent); zero length or width; missing inputs.
- Output `lamp_adapter.json` uses the `groimp_density` contract (`initialization_rgg`, `scene_sha256`, `coordinate_frame=grow_m`, `power_convention=photon_umol_s`). `review_state` is `pending`, so `groimp_density.prepare` keeps refusing it until a person accepts it.
- Power: AreaLight numeric power = photon flux in µmol s⁻¹, written verbatim (a test asserts `setPower(123.5f)`). Electrical watts are never used.

Native synthetic checks, `build/ppfd_validation_synthetic_20261002_161322/` (10M rays, all **passed**):

| Check | Result |
|---|---|
| Point source: front, off-axis far plate, 60° tilt, edge-on, reversed | within 3σ+0.5 %; edge-on and reversed exactly 0; near/far ratio 4.086 vs analytic 4.157 |
| Tilted (25° toward az 20°) 300×40 mm bar, cos², 6 sensors incl. a wall | GroIMP vs python finite-rectangle reference: −0.6 % … +1.7 %, all within 3σ+0.5 % |
| Flux conservation (closed black 2×2×1 m box around the bar) | absorbed / emitted − 1 = 4e-13 |
| Opaque 100 mm plate at half height | lit −0.3 %, interior 0 = 0, edge −3.4 % (σ 2.7 %); classes illuminated / shadow_interior / shadow_edge (unshaded fraction 0.50) |
| Random streams | seeds 11 vs 12 differ; seed 11 repeated reproduces (1e-16) → `lm.setSeed` gives independent streams |

## Workflow (`python -X utf8 -m tools.ppfd_validation ...`)

| Subcommand | Purpose / spec function |
|---|---|
| `templates --out` | Header-only CSVs: `lamp_conditions`, `rig_surfaces`, `sensors`, `measurement_points`, `ppfd_readings` (`ppfd-readings-2`), `spectrum`. `study.json` has every numeric setting `null`. Includes an English README and a Korean `작성안내.txt`. |
| `audit --study` | `validate_inputs`: read-only. Lists every missing or non-measured physical input explicitly (`missing_physical_inputs.csv`). Checks split leakage, duplicated repeats, timezone-less times, unit normals, unsupported sensor shape / angular response, unsupported fixtures. |
| `run --study --out [--execute]` | One immutable `build/ppfd_validation_<ts>/` folder. Steps: input copies + hashes → audit → frozen split manifest → `fit_empty_rig` (calibration rows only) → fitted scene copy (status `fitted`) → `prepare_validation_cases` → `groimp_density.execute` → collect → `compare_ppfd` → sensitivity → readiness → `report.html`. |
| `compare --predictions --readings --split` | `compare_ppfd`: validation rows only. Point means of valid repeats (each point weight 1). Reports MAE / RMSE / bias / NRMSE (NRMSE unavailable at zero mean), by stage and by height, repeat SD/CV, exclusions with reasons, independent-unit count. Cluster-bootstrap CI only when `min_independent_units_for_ci` is declared and met. Acceptance verdict only for declared thresholds (otherwise `no_threshold_set`). |
| `convergence --prepared --case --study` | Bounded native ray × seed sweep. Refuses when `max_local_native_jobs` is undeclared or would be exceeded. Numerical only, never an accuracy criterion. |
| `synthetic --out` | The native checks above. |
| `stale --run` | Re-hashes recorded sources and tool code; a change marks the run stale (recompute = new folder). |

Stage behaviour:
- **Empty rig.** Plant-free; no leaf mesh needed. The fit backend is python direct light. Only `photon_flux_scale` (closed-form least squares) and `half_intensity_half_angle_deg` (bounded grid + 95 % profile interval) can be fitted, and only when enabled; fixture geometry stays fixed. A bound hit or too few points gives `insufficient_calibration`. A reflective rig is refused for this backend (`blocked_reflective_rig_not_in_fit_backend`). The fit manifest records the calibration dataset hash and is frozen before any evaluation.
- **Occluder.** Plates come from `rig_surfaces.csv` with role `physical_occluder`. Each point is classified illuminated / shadow_interior / shadow_edge by the python unshaded fraction (tolerance from settings; `null` → unclassified). Surfaces with role `display_only` never enter any optical scene; listing one as an occluder blocks the case.
- **Plant.** Leaves come through `groimp_density.surface_gate` (review state, hash, variant, date, session); blockers are never bypassed. A review JSON without `geometry_completeness: whole_plant_reviewed` is recorded as a limited isolated test and blocks canopy readiness. Completeness is never inferred from triangle count. Every plant case gets an automatic `__empty_twin` case at the same points; `plant_contribution_umol_m2_s` = plant − twin.
- **Sensors.** Rectangle (reused `sensor_triangles`) or disc (area-matched polygon fan); any other shape is refused. Probes are one-sided (`SideSwitchShader(BLACK, transparent)`). They are batched in one job only when python ray tests prove no probe shades another *and* nothing reflects; otherwise there is one job per point. The test fixture with stacked sensors is correctly split into 10 jobs. GroIMP `SensorNode` is not used.
- **Quantities kept apart.** Front-face sensor PPFD (`sensor_predictions.csv`). Leaf received flux on both faces and absorbed flux (`leaf_triangle_light.csv`, per one-sided triangle area, named as such).
- **Absolute output.** `predicted_ppfd_umol_m2_s` is filled only when every consumed lamp input is `measured` or `fitted`, the fixture is adapter-supported, full output is confirmed, rig/point/sensor geometry is measured, and (plant) leaf optics and placement are measured. Otherwise it stays `unavailable`; the diagnostic `simulated_ppfd_declared_inputs_umol_m2_s` is kept next to it.
- **Spectral path.** `spectral_to_photon_umol` converts each bin with E·λ/(h c N_A) over 400–700 nm. It distinguishes per-nm densities from bin-integrated values (a bin-integrated value straddling a band edge is refused) and rejects electrical watts.
- **Readings adapter.** `to_tomato3d_readings` maps `ppfd-readings-2` rows onto `PPFD_READINGS_CSV_COLUMNS` (validation → evaluation), leaving old readers unchanged.

## Actual runs on the project's current state

| Output | Content | SHA-256 (key file) |
|---|---|---|
| `build/ppfd_validation_inputs_20261002_202720/` | header-only templates to fill | — |
| `build/ppfd_validation_20261002_202720/` | run on those templates: audit `templates_only_no_measurements`; fit / prepare / compare unavailable (no LightScene, no readings) | run_manifest `29029f5f…`, missing_physical_inputs.csv `3b8117bb…`, readiness `7694fba4…` |
| `build/ppfd_validation_20261002_202720_xl_readiness/` | fresh hash-verified recheck of the newest XL bundle `xl_handoff_20260929_092848` (no newer bundle exists): **dwt_01–04 each 0 leaf surfaces**, `blocked_no_leaf_surfaces`. `build/leaf_surface_pilot_20261001/readiness.json`: 0 human-confirmed points, 0 triangles. | `a4fe0653…` |
| `build/ppfd_validation_synthetic_study_20261002_202743/` (+ `_inputs`, `_convergence`) | SYNTHETIC software exercise (example scene, assumed values, no readings): 12 native jobs completed, 0 failures. GroIMP vs python −3.8 % … +6.9 % (10 mm sensors, 2M rays ≈ 300 hits each); absolute PPFD unavailable as intended. Convergence on the dim lit point: seed CV 0.44 at 1M rays → 0.08 at 4M. **Exclude from research.** | sensor_predictions `91b34699…`, convergence `b21bd0bc…` |
| `build/ppfd_validation_synthetic_20261002_161322/` | native synthetic checks (above) | synthetic_checks.json `294e592f…` |

Code: `tools/ppfd_validation.py` `0867eaca…`, `tools/tests/test_ppfd_validation.py` `d60bf015…`, `tomato3d/io/schemas.py` `77728e2a…`.

## Tests

- `python -X utf8 -m pytest tools/tests/test_ppfd_validation.py tools/tests/test_groimp_density.py tools/tests/test_groimp_light_scene.py tools/tests/test_groimp_light_sanity.py tools/tests/test_canopy_light.py -q`: **74 passed** (47 existing + 27 new).
- Light-schema tool suites (`canopy_light`, `groimp_light_scene`, `leaf_light_study`): 92 passed.
- `python -X utf8 -m pytest tests -q` (tomato3d): **191 passed**.
- Mutation check: 10 guards broken one at a time, and each made its test fail. The guards: calibration rows entering metrics; missing probe-shading test; watt conversion on flux; silent normal normalisation; unchecked split hash; NRMSE at zero mean; disturbed repeats kept; sub-90° cutoff accepted; display object accepted as occluder; unchecked execution-log hash.

## Unresolved physical inputs (all required before any accuracy statement)

1. **LightScene** (`config/light_scene.json`, human-owned, does not exist). Needs measured fixture centre, aim tilt/azimuth, long-axis azimuth, emitting length/width, PPF (µmol s⁻¹, not electrical W), and angular distribution. The distribution must be cos^m with m ≥ 1 and a 90° cutoff, or a new verified light class is needed.
2. **Lamp conditions**: output setting, full-output confirmation, stabilisation time, spectrum (optional).
3. **Rig surfaces**: walls/floor/shelf/reflectors with geometry and R/T plus their sources; a measured opaque plate for the occluder stage.
4. **Quantum sensor**: model, serial, calibration reference/date, actual sensing shape and dimensions, cosine-corrected response. Codex records that no sensor is currently available.
5. **Measurement points** (grow mm, unit normals, height band, split role) and **readings** (`ppfd-readings-2`, timezone-aware, repeats sharing a split, ambient/disturbance flags).
6. **Reviewed whole-plant leaf triangles** with `geometry_completeness` stated, plus measured leaf optics A/R/T and plant placement.
7. **Decisions left `null` on purpose**: rays, max_depth, seed, convergence grid and tolerance, max local jobs, python sampling, shadow-class tolerance, sensitivity deltas, acceptance thresholds, CI unit minimum and bootstrap settings, fit bounds and grid.

## Limitations and open points

- The python comparator is direct light only (no reflections, straight leaf transmission). GroIMP uses diffuse R/T with finite depth. Their disagreement in reflective or leafy scenes is a model difference, not automatically a bug.
- Unverified: whether the emitting Parallelogram itself absorbs or blocks light reflected back to the lamp in a reflective rig. Check it with a reflective-box case before trusting depth > 1 results.
- Sensor batching relies on python straight-ray shading tests; any reflective rig falls back to one job per point.
- `fit_empty_rig` uses the python backend, so a reflective rig blocks fitting. A native flux-only fit (linear in flux) is possible later if needed.
- Owner-side notes for Codex (no change made): `groimp_density` uses split role `validation` while `tomato3d` uses `evaluation`; the adapter handles both. `groimp_density.MEASUREMENTS` has no point/repeat IDs; `ppfd-readings-2` adds them. `ppfd_validation.lamp_adapter` output can feed `groimp_density --prepare` once a person sets `review_state=accepted` and attaches the empty-scene validation.
