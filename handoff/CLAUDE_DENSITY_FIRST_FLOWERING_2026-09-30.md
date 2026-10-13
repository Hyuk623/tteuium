# Density, light distribution and first flowering: implementation brief

## Authorized scope

Implement the user's approved Phase 3–6 track in the existing tools. The primary endpoint is human-confirmed first open flower, not yield. CO2 is not recorded. Photosynthesis is optional, assumption-dependent reference output and must not be a required prediction input. Six weeks is an initial observation period, not a flowering guarantee.

## Inspected foundation

Reuse `tools/canopy_light.py` placement/geometry conventions, the read-only `tomato3d.light` schemas, and the existing GroIMP runner and static mesh conventions. Phase 2 uses sensor planes and display-only organ geometry; its isotropic surrogate is not a validated directional LED model. No current display boxes, axes, hulls or centres qualify as optical leaves.

## Intended implementation

- Add a versioned study CLI for input templates, immutable provenance, reviewed-surface preflight, fixed-area/lighting density cases, GroIMP jobs and measured PPFD comparison.
- Retain organ/plant/session/snapshot IDs and original triangles. Require explicit review and matching source hashes. Missing surfaces remain a blocking status, never a fabricated mesh.
- Record flowering visits, photo evidence, last negative/first positive intervals, right censoring and already-flowered plants. Aggregate by plot before density comparison.
- Add an optional interval/right-censored time-to-event baseline and light-augmented comparison, using pre-prediction features only and disjoint plot/plant evaluation groups. No results without sufficient supplied observations.
- Keep original photos, annotations, calibration and weights unchanged. No deep-learning training, GitHub push, or changes to `docs/`, `config/` or `tomato3d/`.

## Validation and reporting

Test coordinate/unit transfer, surface eligibility, fixed treatment inputs, sensor matching, flowering intervals/censoring, future-feature and group leakage, and missing-data reporting. Exercise synthetic examples separately from real-plant status. Record actually executed GroIMP checks separately from generated projects. Do not claim validated PPFD, improved flowering prediction, or an optimum without independent observations.

## Delivery status

Implementation in progress. Actual commands, tests, limitations and artifact locations will be appended after verification.

## Implementation delivery — 2026-09-30

The support-tool implementation and synthetic execution checks are delivered. This is **not completion of the biological experiment**. Real Phase 3 is still blocked by absent reviewed leaf surfaces and an unverified directional LED adapter. First-flowering observations and independent sensor measurements have not been invented.

### Added tools

1. `tools/groimp_density.py`
   - `--templates`: empty triangle, sensor, PPFD and review contracts plus study settings.
   - `--readiness-xl`: verifies the existing XL handoff hashes and reports actual exported leaf-surface counts; never converts markers, axes or hulls to optical leaves.
   - `--prepare`: validates fixed plot dimensions and one shared LightScene; checks surface review/hash/session/date/normal conventions; materializes density instances using the existing `canopy_light.materialize_case` and `place_in_grow_frame` helpers; writes native RGG projects and immutable artifact hashes.
   - `--execute`: runs the existing installed GroIMP CLI in fresh output folders. Each sensing plate runs separately so plates cannot shade each other. Native leaf triangles retain plant/session/organ/leaflet/triangle IDs in a mapping table. Failed jobs remain failed.
   - `--collect`: checks hashes and complete finite output, exports triangle/leaf light tables, density comparisons, a top-projection triangle light map, sensor predictions, PPFD errors/repeat variability and MAE/RMSE/bias/normalized RMSE. Calibration readings are excluded from independent validation errors.
2. `tools/first_flowering.py`
   - Empty CSV templates and a runnable records-to-analysis CLI.
   - Human-confirmed first-open events with existing photo evidence; buds are negative observations, not flowers.
   - Interval censoring, right censoring at the last verified negative visit, already-open-at-entry, unknown baseline and no-confirmed-observation states remain distinct.
   - Plot-level summaries precede density summaries. Multiple plants in one plot do not become independent density replicates.
   - Optional lognormal AFT comparison handles interval/right censoring directly, conditional on survival through a predeclared landmark day. Baseline features: observed height, leaf count and reviewed leaf area; augmented features: lower/upper light and light CV. Growth/light records after the landmark are never used. Light dates must equal geometry snapshot dates.
   - Both models use the same complete-case cohort, development-only normalization, plot-weighted likelihood, and disjoint development/evaluation plots and plants. Outputs include conditional median and predictive quantiles, interval-distance diagnostic and plot-averaged held-out negative log likelihood. Interval distance is **not exact-date MAE**. The AFT distribution is an exploratory statistical choice, not a calibrated tomato flowering mechanism.
   - Sample-count gates are intentionally null until specified before evaluation. Null/unmet gates, absent references or optimizer failure produce unavailable results. The templates contain no observations and generated no fitted model.
3. `tools/density_flowering_report.py`
   - Joins light cases and plot-based flowering summaries by density ID, retaining missing results.
   - Produces CSV/HTML for candidate review; does not silently optimize an unspecified agronomic objective. Candidate selection remains unavailable pending independent validation and follow-up review. This is an intentional remaining decision, not a computed optimum.

### Physical input / adapter boundary

The authoritative numerical lamp inputs remain the existing `LightScene` JSON. The human-owned `config/` currently contains no `light_scene.json`; none was created or altered there.

`lamp_adapter.json` contains reviewed native XL declarations (`header_rgg`) and graph nodes (`initialization_rgg`), uses grow-frame metres and photon-rate numerical encoding, names the exact source scene SHA-256, and records an empty-scene validation reference. It must be independently reviewed before a real run. **This implementation does not automatically translate the existing cosine-power LED model into GroIMP.** Do not use the isotropic synthetic adapter for real LED predictions. The adapter is an explicit integration boundary for the Claude light-model work, not proof of a measured lamp distribution.

GroIMP native light power normally denotes watts. The existing project's photon-rate convention is retained: numerical photon flux is transported with achromatic coefficients and interpreted as micromoles per second. No watts-to-photons conversion, CO2 concentration, photosynthesis or growth yield is inferred. Independent quantum-sensor calibration remains necessary.

GroIMP settings explicitly select `diffuse_reflection_and_transmission`; this is recorded separately from the existing Python schema's `reflections="not_modelled"`. The original scene is preserved. It is **not** a claim that the original Python direct/straight-transmission engine was modified. Leaf A+R+T must equal 1. Native Phong shaders use diffuse R/T; finite path depth and ray count require convergence checks for a real canopy. The maximum path depth is not a physiological parameter.

Leaf outputs are the received flux on **both faces**, divided by supplied triangle/leaf area. Sensor outputs are **front-face incident PPFD**, computed using a one-sided absorbing mesh with the supplied centre, unit normal and rectangular sensing area. Do not rename these into the same quantity. Nonrectangular sensors need an additional measured-shape adapter. The simulation state is all fixtures at full output; measurement records must explicitly match it. Fixture schedules remain fixed in the source scene; this version does not integrate differing fixture schedules into daily absorbed light.

The current tools always retain `validated_metric=false` and `suitable_for_ppfd=false`. Successful execution or small synthetic errors never promote these flags.

### Actual artifacts and checks

- `build/density_flowering_inputs_20260930/light/`: empty physical input/review templates.
- `build/density_flowering_inputs_20260930/flowering/`: empty plants, visits, growth and light time-series CSVs; six-week planning metadata, no CO2 column.
- `build/density_flowering_inputs_20260930/empty_analysis/`: zero actual plants, unavailable prediction/photosynthesis, no fitted model.
- `build/density_flowering_inputs_20260930/current_readiness/readiness.json`: hash-verified inspection of `build/xl_handoff_20260929_092848`; **dwt_01, dwt_02, dwt_03 and dwt_04 each export 0 leaf surfaces**. All four remain `blocked_no_leaf_surfaces`. This is a statement about that pinned bundle, not every newer intermediate reconstruction.
- `build/density_flowering_synthetic_20260930/prepared/` and `executed/`: two purely synthetic density layouts, four native GroIMP 2.2.1 jobs, all completed. Total measured CLI runtime approximately 33.09 seconds. These are software fixtures, not actual tomato density treatments.
- `build/density_flowering_synthetic_20260930/results_v2/`: 12 triangle rows, leaf aggregation, two sensor rows, diagnostic light maps and unavailable independent validation. `results/` is retained as the earlier collection.
- `build/density_flowering_synthetic_20260930/joint_report/`: light/flowering report exercised against empty flowering records; no flowering outcome or optimum is generated.
- `build/density_sensor_direction_check_20260930/checks.json`: independent analytic finite-area comparison for a synthetic isotropic point source, two million rays, explicit seed 100. Front-facing sensor: GroIMP 311.4 versus analytic 315.1635 (−1.19%); tilted sensor: 248.45 versus 254.3744 (−2.33%); reversed sensor: both zero. These are Monte Carlo software checks, **not actual sensor accuracy**.
- `build/density_leaf_optics_check_20260930/check.json`: native triangular leaf with A=0.7/R=0.1/T=0.2 returned absorbed/received=0.6999999578; passed the stated 0.02 absolute tolerance.
- Targeted regression suite: **54 passed**, including existing canopy and GroIMP Phase 1/2 tests. New tests cover censoring, missing photo evidence, future geometry, plant/plot leakage, survival probability partition, unavailable-data behavior, source mutation, copies versus actual plants, sensor normals/area, fixed lighting, and incomplete optical output.

The initial synthetic prepared bundle predates addition of the explicit transport metadata field; its generated RGG already uses the same recorded Phong transport. It is retained unchanged with its original hashes. New study settings must declare `groimp_optical_transport` explicitly.

### Reproduction commands

Run from the project root; every output path must be new. A working local interpreter is `C:/Users/sho36/AppData/Local/Programs/Python/Python313/python.exe`; local Java is `C:/Program Files/Eclipse Adoptium/jre-21.0.12.101-hotspot/bin/java.exe`.

```powershell
python -m tools.groimp_density --templates --out build/density_inputs_NEW/light
python -m tools.first_flowering --templates --out build/density_inputs_NEW/flowering
python -m tools.groimp_density --readiness-xl build/xl_handoff_20260929_092848 --out build/density_readiness_NEW

# After the human supplies reviewed physical inputs and records:
python -m tools.groimp_density --prepare build/density_inputs_NEW/light/study.json --out build/density_prepared_NEW
python -m tools.groimp_density --execute build/density_prepared_NEW --out build/density_execution_NEW --java "C:/Program Files/Eclipse Adoptium/jre-21.0.12.101-hotspot/bin/java.exe"
python -m tools.groimp_density --collect build/density_execution_NEW --measurements build/density_inputs_NEW/light/ppfd_readings.csv --out build/density_results_NEW
python -m tools.first_flowering --input build/density_inputs_NEW/flowering --settings build/density_inputs_NEW/flowering/analysis_settings.json --out build/flowering_results_NEW
python -m tools.density_flowering_report --light build/density_results_NEW --flowering build/flowering_results_NEW --out build/density_flowering_report_NEW

python -m pytest tools/tests/test_first_flowering.py tools/tests/test_groimp_density.py tools/tests/test_density_flowering_report.py tools/tests/test_canopy_light.py tools/tests/test_groimp_light_scene.py tools/tests/test_groimp_light_sanity.py -q
```

### Next integration tasks for Claude

1. Supply actual accepted leaf triangles; preserve existing metric failures. A bbox, visual hull, centre or display axis is not a substitute. The required triangle contract is `LEAF_SURFACES_CSV_COLUMNS` from the existing schema; the template has those exact headers.
2. Implement/review the directional LED RGG adapter against empty-scene measurements, with angular normalization, fixture positions and power preserved. Automatic cosine-power translation is still pending.
3. Confirm the native diffuse optical-transport choice versus the existing Python straight-transmission comparison. No source schema was changed here.
4. Fill independent PPFD records and prospective plot/plant visits. Each density needs independently replicated plots for inferential density comparisons. Four reconstructed plants or many photographs alone do not provide such replication.
5. Before model evaluation, specify sample sufficiency and candidate-selection criteria, a common follow-up horizon, and frozen feature/landmark settings. Use observed flowering intervals and right censoring; do not select on event-only mean flowering date.
6. Optional CO2-assumed photosynthesis remains unimplemented/unavailable and is outside the required first-flowering path. No yield, profit optimum, six-week flowering guarantee or proven predictive benefit is claimed.

Primary API references inspected: [GroIMP shader tutorial](https://wiki.grogra.de/doku.php?id=tutorials:light-modeling-light-shader), [GroIMP light-source tutorial](https://wiki.grogra.de/doku.php?id=tutorials:light-modeling-light-sources), plus installed GroIMP 2.2.1 class signatures and actual native executions.
