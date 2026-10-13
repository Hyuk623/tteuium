# Four project environment and input output handoff

Date: 2026-10-03, Asia/Seoul. Recipient: Claude coordinating integration. Scope: the four chats named `3d구현`, `광시뮬레이터`, `생장방향` and `토마토 FSP`. This document consolidates current interfaces and explicitly proposed extensions. It does not execute or authorize implementation, model runs, training, or cross-chat messaging.

All four work in `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`. They are separate work streams sharing a codebase, not four isolated deployed applications. Read parent `공통규약.md`, project `AGENTS.md` / `CONVENTIONS.md`, and current LOG/TODO. Respect active file ownership. Code inspection and source documents below are the evidence; a chat title is not proof of a completed capability.

## 1 Current roles and maturity

| ID and chat | Responsibility | Current evidence and boundary |
|---|---|---|
| P1 `3d구현` | Current observed leaf area, supported surfaces, geometry/identity evidence | Area/surface tools and dimensionless detection ratios exist. Multiview completion adapter source has appeared but its execution brief remains ongoing; no completed eligible model trial inferred. Generated candidates do not become observed or optical-ready tissue. |
| P2 `광시뮬레이터` | Place plants into a canopy and compute received/absorbed photons and shading interactions | `hierarchical-light-1` is delivered. Spatial/time/direction/split export extension is now in progress. Core angular diagnostic dependency remains in TODO. Native preparation is not executed optical validation. |
| P3 `생장방향` | Forecast distributions of CompoundLeaf appearance, direction, extent, area and parent growth from a measured origin | `probabilistic-compound-1` implementation delivered; current execution report records 92 tests and synthetic CLI verification. These are historical recorded results, not tests rerun for this document and not real biological accuracy. |
| P4 `토마토 FSP` | Evidence, response-coefficient estimation and integration; intended future physiological carbon balance | Current active implementation is `growth_calibration.py`, schema `growth-calibration-1`; delivery brief still says in progress. Photosynthesis/respiration/allocation extension has a prompt, not a verified implemented physiology engine in the inspected interfaces. |

The older P3 IO brief says the probabilistic calculator is proposed. Its newer execution report and CLI documentation supersede that software-status statement. Conversely, do not promote the new light or physiology prompt's requested files to existing outputs.

## 2 Environment means three different things

Keep process settings, cultivation/physical inputs and numerical controls separate. None of the names below implies a measured value exists. No cultivar-specific optimum or biological coefficient is supplied by this handoff.

### Process environment and execution

Shared defaults are defined in `tomato3d/config.py::get_settings`; they apply only where that accessor is used. Configuration also loads dotenv; do not expose secrets or copy machine-local credentials into this handoff.

| Variable | Default | Meaning and applicability |
|---|---|---|
| `TOMATO3D_DATA_ROOT` | `./data` | Core data paths; human observations remain read-only. Relative paths depend on launch directory. |
| `TOMATO3D_CONFIG_DIR` | `./config` | Core configuration paths, human-owned and read-only. |
| `TOMATO3D_CAMERA_ID` | `cam_a` | Core camera selector; not a plant or treatment ID. |
| `TOMATO3D_LOG_LEVEL` | `INFO` | Logging configuration. |
| `TOMATO3D_MAX_WORKERS` | `4` | Core worker setting; not proof every standalone tool runs four workers. |
| OS `PATH` | Host-defined | Resolves Python and the default Java executable for optional native light execution. No host-specific value is prescribed. |

The standalone area, hierarchy, growth and calibration tools principally accept explicit CLI paths; they do not all consume these shared environment variables. No additional mandatory custom OS variables were found in the inspected main modules. Run from the project root with `python -X utf8 -m tools.<module>`. Runtime prerequisites follow each tool's documentation; do not assume the active Python environment has an optional diffusion or Java/GroIMP backend.

Native light uses explicit `--java` and `--core` overrides. Source data/config roots do not redirect the standalone tools' generated-output root: `tools.leaf_light.common` restricts outputs to a fresh project `build/` directory. Relative paths inside input manifests follow each loader's manifest/base-directory convention, not an assumed global working directory.

### Cultivation and physical variables

In this table, P4-current means calibration features with declared units/domain/exposure; P4-future means the not-yet-finalized physiological contract.

| Variable or quantity | Unit | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| `temperature_c` | deg C | Not used for geometric area | Not used in current optical transport | Optional scenario/conditional feature; effect needs explicit coefficient or response | Current: declared feature. Future: assimilation/respiration temperature response |
| `relative_humidity_pct` | % | Not a geometric input | Not used in optical transport | Optional scenario/response feature | Current: declared feature. Future: stomatal/VPD relation only with specified model |
| `co2_ppm` | ppm | Not used | Not used in current optical transport | Optional scenario/response feature | Current: declared feature. Future: assimilation input; ambient is not automatically chloroplast CO2 |
| `ec_ms_cm` | mS/cm | Not used | Not used | Optional scenario/response feature | Current: declared feature. Future: indirect stress response only when justified |
| `ph` | dimensionless | Not used | Not used | Optional scenario/response feature | Same evidence requirement as EC; no default multiplicative effect |
| `ppfd_umol_m2_s` | umol/m2/s | Optional independent light measurement/reference | Calculated receiving-surface quantity, not lamp PPF | Optional incident-light scenario or explicitly mapped light feature | Current: declared exposure. Future: incident/absorbed model argument must be distinguished |
| `photoperiod_h` | h/day | Optional light summary | Existing fixture schedule is the authoritative richer input; hierarchy v1 is full-output only | Optional scenario feature | Current: declared feature. Future: time integration with actual on/off intervals |
| Lamp PPF | umol/s | No optical calculation | Physical lamp input with status/source | Not a substitute for leaf PPFD | Not a substitute for absorbed photons |
| Lamp size/position, plant placement | mm, angles in degrees in files | Board/camera geometry is distinct from lamp geometry | Physical transport inputs | Placement/frame context for imported features | Spatial exposure provenance |
| Leaf absorptance/reflectance/transmittance | 0 to 1 | Not obtained from area alone | Uniform leaf optics in current scene; native requires sum=1 | No optical response calculation | Absorptance must not be charged again to already-absorbed input |
| Fixture schedule `start_hhmm`, `end_hhmm`, `output_fraction` | local time, 0 to 1 | Not geometric | Shared schema exists; new bridge adds dated interval export | Does not directly accept a full LightScene schedule | Future integration needs timestamps, timezone and duration |
| Spectral bands, leaf temperature, VPD, wind/water status | Explicit band units, deg C, kPa, m/s or defined water units | Not currently derived | Not supplied by broadband PPF alone | No automatic growth response | Candidate future inputs only where the chosen model requires/supports them |

P3's exact existing environment vocabulary is the seven fields from `tools/monthly_growth.py::ENV_FIELDS`, reused by `probabilistic_compound_growth.py`. These fields are data inputs, not OS variables. Merely populating a field does not activate a biological effect. The P3 engine can use declared conditional family coefficients and/or one explicit development-clock response; it does not infer their values or automatically multiply environmental responses.

P4 calibration currently supports declared constant exposure within a trajectory. Time-varying histories need a reviewed response contract; do not silently replace a changing environment with its mean and claim equivalent calibration.

### Numerical controls and provenance

| Project | Controls that are not biological/environment measurements |
|---|---|
| P1 | Camera intrinsics/distortion and metric board poses are measurement/calibration inputs. Inversion, triangulation, surface-support and held-out comparison tolerances are numerical/review settings. Optional completion model/version/seed/budgets belong to its separate request contract. |
| P2 | `triangle_subdivisions`, `emitter_grid`, `ray_offset_mm`, `max_ray_triangle_pairs_per_chunk`, `max_transport_calls`, `max_receiver_emitter_pairs`; native `rays`, `max_depth`, `seeds`, `max_jobs`, `max_total_rays`. |
| P3 | `horizon_days=30`, `sample_count`, `seed`, `output_days`, `max_events_per_axis`, numeric/projection tolerances, summary quantiles. Parameter covariance is a modelling assumption or fitted evidence, not a numerical tolerance. |
| P4 | Frozen fit plan, optimizer bounds/tolerances, resampling seed/count, success criteria, feature scaling, evaluation horizons and independent split IDs. Bounds and uncertainty assumptions need provenance. |

## 3 P1 current geometry and leaf area

Primary references: `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md`, `tools/LEAF_AREA_COMPARISON.md`, `handoff/CODEX_MULTIVIEW_COMPLETION_EXECUTION_2026-10-03.md`.

| Input | Required interpretation |
|---|---|
| Saved photos/masks and original pixel coordinates | Source image, crop mapping, labels and hashes. Detection identity alone is not confirmed physical cross-view identity. |
| Camera/board calibration and poses | Intrinsics in px, distortion, measured pose; geometry in board-frame mm. Use existing coordinate helpers and board variant. Commanded turntable angle is not measured pose. |
| Study JSON and optional measurements | Explicit files, capture date/session, grouping/motion provenance, estimator/calibration compatibility. Human measurement CSVs are immutable. |
| Surface evidence | Confirmed correspondences, boundary/hole IDs, visible support masks, per-view evidence and independent held-out views where supplied. |
| Detection-ratio route | `--batch` saved detection batch; explicit mask or bbox mode and first supplied label reference. No metric scale is inferred. |

Current tools: `leaf_area_compare.py`, `leaf_surface_compare.py`, `relative_leaf_area.py`, `detected_leaf_area.py`. Area/surface CLIs use `--study` and `--out`; detection ratios use `--batch` and `--out`.

| Outputs | Units/status and consumer |
|---|---|
| `photos.csv`, `groups.csv` | Per-view/projected area and estimator evidence; cm2 where metric estimate is supported. Not automatically true total tissue area. |
| `candidate_surfaces.csv`, `compound_areas.csv`, `patch_inventory.csv` | Candidate triangle vertices in board mm, supported area in cm2, patch topology and support. Requires optical review before P2. |
| `relative_detected_leaf_areas.csv` | Dimensionless per-image first-label=1 ratios; masks/bboxes and source references remain explicit. Cannot provide P2 absolute tissue or P4 carbon scale. |
| Audit/calibration JSON and `viewer.html` | Method, source hashes, observed/candidate distinction, missingness, review and comparison evidence. |

P2's input is reviewed `leaf_surfaces.csv` using the existing leaf triangle schema, not an arbitrary candidate CSV renamed to that filename. An adapter must preserve the geometry variant, source IDs, normal convention, unit and matching review hash. P3 additionally needs whole compound axes, attachment and temporal identity; a triangle export alone does not supply those observations.

Optional multiview adapter source currently offers `audit_request`, `prepare_request`, `import_candidate_bundle`, `evaluate_candidates`, `export_review_bundle`; visible artifact names include `backend_request.json`, `candidates.json`, `view_metrics.csv`, `evaluation.json` and `review.json`. This is ongoing work. Generated hidden geometry remains a hypothesis and never overwrites observed support or automatically passes optical eligibility.

## 4 P2 light simulation

Primary references: `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md`, `tools/HIERARCHICAL_LIGHT.md`, `handoff/CODEX_LIGHT_GROWTH_READINESS_EXECUTION_2026-10-03.md`.

Current public workflow: `tools.hierarchical_light` commands `audit`, `prepare`, `calculate`, `stale`; optional native `execute`/`collect`. Important functions include `audit_inputs`, `prepare_subset_cases`, `calculate_direct`, `write_report`. Reuse `tools.canopy_light.materialize_case` for instance placement.

| Input | Fields or role |
|---|---|
| `input.json` | `schema_version=hierarchical-light-1`, scenario/case, relative file paths, source instances, selection and limits |
| `scene.json` | Lamp PPF/beam/position/size/orientation, explicit placements and leaf optics; physical values retain value/status/source |
| `leaf_surfaces.csv` and surface review JSON | Accepted supported triangles in board mm, plant/session/variant/organ/leaflet/triangle IDs, normal convention, geometry hash |
| `membership.csv` | `source_plant_id,plant_instance_id,session_id,capture_date,geometry_variant_id,organ_id,leaflet_id,compound_id,identity_status,evidence_path,evidence_sha256` |
| Optional background | Existing rig-surface schema, optical properties and fixed wall/support occluders |

Membership join is `(plant_instance_id, session_id, organ_id, leaflet_id)`. Missing membership may preserve scalar optical results but blocks affected compound attribution. Keep all physical occluders when filtering which targets to report.

| Current outputs | Meaning |
|---|---|
| `interaction_cases.csv` | Eight retained-target subsets; fixture/replicate, supported area m2, received/absorbed flux umol/s, PPFD umol/m2/s |
| `leaflet_interactions.csv`, `compound_interactions.csv`, `plant_interactions.csv` | Baseline/full/loss, signed Shapley A/B/C contributions and overlap |
| `source_target_interactions.csv` | Directed source-removal effect; nonadditive, self-removal unavailable |
| `replicate_summary.csv` | Replicate means and paired-effect errors where available |
| `results.json`, `manifest.json`, `audit.json`, `viewer.html` | Context, hashes, methods, limitations and visual inspection |

Current hierarchy quantity convention is two-face received light per supported one-sided tissue area. Scalar absorption is not photosynthesis. Direct transport excludes reflected light; native reflection/transmission is a distinct backend. Partial area does not imply total plant absorption.

**Extension in progress, not a delivered contract yet:** `CODEX_LIGHT_GROWTH_READINESS_PROMPT_2026-10-03.md` requests `light-growth-1` with `light_samples.csv`, `compound_light_features.csv`, `light_intervals.csv`, `light_dose.csv`, `instance_map.csv`, `transforms.json`, `consumer_mapping.json`, capabilities/audits. Recheck its execution brief and actual schema before consuming exact columns. Required new data are spatial quadrature, normal/opposite-side light, angular moments, clock-time dose and reversible per-instance exports. The public core currently exposes scalar/side arrays but needs an owner-provided angular diagnostic interface. Do not infer a light direction from scalar PPFD or claim that new native channels exist.

## 5 P3 CompoundLeaf direction and growth

Authoritative current documentation: `tools/PROBABILISTIC_COMPOUND_GROWTH.md` and `handoff/CODEX_GROWTH_CALCULATOR_EXECUTION_2026-10-03.md`. Entry point: `python -X utf8 -m tools.compound_growth probabilistic`; standalone module also exists.

| Input | Fields and interpretation |
|---|---|
| `observations.json` / history | Schema `compound-observations-1`; hashed observations, axes and extents CSVs; confirmed IDs and aware times |
| Observation rows | `plant_id,compound_leaf_id,session_id,observed_at,parent_stem_id,identity_status,review_source,geometry_status,development_state,first_observed_at,supported_area_cm2,area_basis_id,estimated_total_area_cm2,transverse_x,transverse_y,transverse_z` |
| Axis rows | `plant_id,compound_leaf_id,session_id,station,x_mm,y_mm,z_mm`; whole attachment-to-tip rachis, not a partial petiole |
| Extent rows | `plant_id,compound_leaf_id,session_id,station,left_mm,right_mm`; explicit local-frame meaning |
| `origin.json` | Plant/session, aware `observed_at`, numeric/projection tolerances; preserve day-zero geometry exactly |
| `structure.json` | Parent polylines, reviewed material attachments, stem/apex status and reference vector for local azimuth; board frame |
| `model.json` | `probabilistic-compound-1`, `stochastic-grammar-proposal-1`, explicit weighted parameter particles, model scope, clock and computation |
| `environment_scenario` | `id,values,response_ref`; seven environment fields above with explicit provenance |
| `light_features` | `id`, plant/compound IDs, aware `observed_at`, `area_basis_id,metric,unit,backend,source_ref,value`; future scenario marker where applicable |
| Update/evaluation inputs | New observed history, confirmed/ambiguous association records, optional supported likelihood, independent evaluation plan/targets |

Eight existing functions: `prepare_origin`, `validate_model_config`, `sample_forecast`, `decode_trajectory`, `summarize_forecast`, `update_forecast`, `evaluate_forecasts`, `export_run`.

| Outputs | What they provide |
|---|---|
| `events.csv` | Appearance/wait/stop states with trajectory-local identities |
| `block_states.csv` | Predicted/existing compound direction, attachment, length/extents and optional independently parameterized area |
| `trajectories.csv`, `trajectory_parameters.json` | Joint samples, weights, parameters and measured shape needed by decoder |
| `summary.csv` | Occurrence/count probabilities and conditional geometry/area summaries |
| `origin.json`, `model.json`, `manifest.json` | Origin, assumptions, schemas and provenance |
| Update/evaluation artifacts | Association/discrepancy/reweighting state and independently scored available targets |

Units are mm, cm2, directions as unit vectors, explicit radian model parameters and degrees in angle report fields. Wait/rate parameters use development days and inverse development days. A calendar clock and an explicitly provided development schedule are not interchangeable without conversion. P3 supports calendar, piecewise-constant development multipliers or one supplied piecewise-linear clock response; fixed-light coupling must be explicit and source-linked. It does not yet consume an arbitrary time/spatial light package as a physiological solver.

P3 does not calculate light, carbon assimilation or allocation. A broad leaf envelope is not tissue. All future blocks retain `suitable_for_ppfd=false`; forecasts remain `validated_growth=false`. Flow Matching and automatic fitting are not part of this engine. Changing the rendering does not recalculate shadows.

## 6 P4 FSP calibration and proposed physiology

### Current calibration interface

Sources: `tools/GROWTH_CALIBRATION.md`, `tools/growth_calibration.py`, `handoff/CODEX_GROWTH_CALIBRATION_EXECUTION_2026-10-03.md`. The source and documentation exist; the inspected execution brief has not yet recorded final delivery. Inspect its latest outcome before making a completion claim.

| Input | Required content |
|---|---|
| `observations.json` | `growth-calibration-1`, observed/synthetic kind, hashed CSV, source hashes, declared feature units and angle/feature provenance |
| Calibration CSV | `record_id,plant_id,organ_id,target_id,unit_id,observed_at,origin_at,elapsed_days,value,initial_value,unit,frame_id,identity_status,coverage_basis,age_basis,measurement_sd,lower_day,upper_day,censoring,visibility_status,split`, capture phase and declared feature columns |
| `treatments.json` | Actual assignment units with treatment/run/source IDs; leaves are not independent treatment replicates |
| `fit_plan.json` | Reviewed frozen equations, parameters/bounds/units/evidence, feature links/domain, observation errors, train/validation split, optimizer and uncertainty controls |
| `evidence_registry.json` | Source/version/locator, cultivar/conditions, measured/fitted/assumed status, units and applicability |
| `evaluation_plan.json` | Held-out plants/assignment units, temporal rules, requested horizons, future-environment basis and scoring |
| Forecast adapter inputs | Existing P3 model, supported `engine_bindings`, matching scenario and compatible clock |

Functions: `validate_evidence_registry`, `audit_calibration_data`, `fit_growth_parameters`, `validate_parameter_set`, `apply_parameter_set`. Supported families are `anchored_expansion`, `azimuth_rotation`, `lognormal_wait`. These do not implement FvCB, organ maintenance respiration or carbon allocation.

Outputs documented by the module are `evidence_registry.json`, `data_audit.json`, `fit_plan.json`, `parameter_set.json`, `fit_diagnostics.csv`, `residuals.csv`, `validation.csv`, `requirements.csv`, `manifest.json`. A parameter set can be unavailable; a written artifact does not mean a successful or biologically accepted fit. `apply_parameter_set` creates a new P3 configuration through explicit family/unit bindings and joint particles. It does not silently overwrite biological defaults or run fitting during prediction.

### Future physiological interface

Source: `handoff/CLAUDE_FSP_PHYSIOLOGY_ACCURACY_PROMPT_2026-10-03.md`. The following is a **requested design**, not adopted function signatures, filenames or calibrated values:

| Future inputs | Future outputs |
|---|---|
| Metric sample area, incident or absorbed light with exact convention, time intervals and per-plant identity | Leaf/plant photosynthetic carbon input, suggested canonical basis gC per step |
| Environment including supported temperature/CO2/stomatal inputs and source-backed photosynthesis parameters | Signed assimilation with explicit day/night and respiration ownership |
| Initial structural dry mass and nonstructural reserves; organ carbon fractions; respiration/yield/demand coefficients | Respiration, available/stored carbon and organ allocation ledger |
| Organ age/development, independently supported mass-to-form relations and measured origin | Structural dry-mass increments in gDM; constrained area/length/diameter updates with uncertainty |

Do not invent these states from pixels or relative area. Respiration must be charged exactly once; gC, gDM, gCO2, carbohydrate equivalent and fresh mass are distinct. Physiology should pass a mass/area constraint or explicit transition contract to P3; it must not independently apply a second full growth increment or duplicate an empirical light effect. Carbon supply alone does not determine azimuth/elevation. Claude must define the interface and source-backed coefficients before implementation.

## 7 Connections and common keys

Current/near-term flow:

```text
P1 reviewed surfaces ------> P2 canopy photons
P1 observed compound state -> P3 measured origin and forecast
Observed history + evidence -> P4 calibration -> P3 parameter particles
P2 eligible light features ------------------> P3 explicit response inputs

Planned physiological extension:
P2 time/spatial absorbed light + environment -> P4 carbon and dry mass
P4 reviewed growth/area constraint ----------> P3 geometry transition
P3 future geometry -> P2 only after a separate eligible tissue contract exists
```

| Boundary | Exact mapping or unresolved requirement |
|---|---|
| P1 -> P2 | Reviewed metric surface schema, source variant/session, physical leaflet identity, normal convention, scale, optical review and matching hash. A candidate filename or relative ratio does not satisfy the gate. |
| P1 -> P3 | Reviewed `compound_leaf_id`, full rachis/attachment/transverse evidence, observation timestamp, parent geometry and supported-area basis. No automatic compound state from proposed labels. |
| P2 -> P3 | `compound_id` requires a reviewed mapping to `compound_leaf_id`; preserve source plant versus instance. Convert supported m2 to cm2, retain metric/unit/backend/source and real/scenario time. Current adapter needs explicit scalar feature/response binding; vector/time-series responses are not automatic. |
| P4 calibration -> P3 | `organ_id`/`target_id` and units bind explicitly to families/coordinates; use `engine_bindings`, joint parameter particles and matching scenario. Current calibration adapter requires compatible calendar clock; do not pass calendar rates as development rates. |
| P2 -> P4 physiology | Sample quadrature and time duration, incident/absorbed distinction, spectral/side/area basis and completeness; proposed light bridge prerequisites remain active. |
| P4 physiology -> P3 | Not yet finalized: define actual increment versus potential demand, reserve ownership, mass/shape reconciliation and replacement of overlapping empirical responses. |

Shared metadata must preserve `source_plant_id`, `plant_instance_id`, session, capture/observation time, compound/leaflet identities, geometry version/hash, scenario, frame and source evidence. Existing tables use different names; implement an explicit adapter, not an undocumented global rename. P2 instance names may differ from P3 source plant names. If two copies share a source, neither may overwrite the other or count as independent observations.

For assembly, reuse the measured board-to-grow transform. For reporting separation, inverse-transform points and rotate vectors without translation; keep the whole canopy's context and shadows. Separating an export does not recompute an isolated plant. New isolated-light results require a distinct scene/run. No carbon is shared between neighboring plant instances.

## 8 Unit, missingness and time compatibility

| Concern | Integration rule |
|---|---|
| Area | `m2 = mm2 * 1e-6`; `cm2 = m2 * 1e4`. Keep supported/estimated total/projected/dimensionless area separate. |
| Light | PPF umol/s is lamp output; PPFD umol/m2/s is receiving density; absorbed flux umol/s is area-integrated. A daily dose is not instantaneous PPFD. |
| Time | Geometry timestamp, source measurement timestamp, simulation interval and forecast origin are separate. Use timezone-aware times; a date alone is insufficient for LED phase. |
| Directions | Board/grow/parent-local frame and vector sign must be named. Rachis direction, surface normal and incoming-light direction are three different quantities. |
| Angles | Respect each source schema: P3 model/calibration angular targets use rad; many geometry/output files use deg. Convert explicitly. Signed elevation must retain up/down. |
| Missing values | P2 hierarchy CSV uses `unavailable`; P3 and P4 calibration CSV use empty cells. JSON uses null. Normalize at the adapter while preserving status/reason; never convert missing to zero. |
| Completeness | Successfully processing all supplied triangles does not imply whole-plant coverage. Unsupported tissue/time intervals cannot silently enter a complete total. |
| Evidence | Separate measured, fitted, assumed, literature-informed, generated candidate and predicted state. A proposal is not an implemented schema. |
| Status | Software tested, physical light validation and biological forecast validation are different states. Keep all three visible. |

Only supported chronological history may condition a forecast. Future environment is an explicit scenario; later observations must not be copied backward into fitting or earlier origins. All exports retain hashes and schema/model versions; stale associations or geometry invalidate affected joins.

## 9 Claude integration checklist and source precedence

1. Recheck current execution outcomes for the active P1/P2/P4 tasks; do not edit their files concurrently. Treat this document as a dated integration snapshot.
2. Resolve P1 metric surfaces, reviews and compound identity/axes separately from first-leaf ratios. Preserve the known missing-data states instead of assuming new measurements exist.
3. Finish and verify P2's spatial/time/reversible exports and owner-supplied angular diagnostic dependency. Use backend-specific capabilities; no direct/native mixing under one label.
4. Review current P3 assumptions and P4 calibration binding/clock compatibility. Freeze exact schema/field mappings and validate a consumer import with synthetic fixtures without claiming biology.
5. Design the P4 physiological contract from its dedicated prompt, choosing units/respiration accounting and evidence-backed parameters. Keep it distinct from the already existing phenomenological fitter.
6. Decide the single owner of realized growth increments when connecting carbon to P3, then require independent module and trajectory evaluation. Do not claim a closed geometry-light-growth loop while future tissue is optical-ineligible.

For exact current behavior, source plus the newest completed execution supplement takes precedence over an earlier short summary. Proposals govern only explicitly marked future work. Append discrepancies to TODO; do not silently rewrite protected specifications or human data.

Primary local reference index:

- `tomato3d/config.py`; `tools/monthly_growth.py`; `tools/leaf_light/common.py`.
- `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md`; `tools/LEAF_AREA_COMPARISON.md`; `tools/detected_leaf_area.py`; `tools/multiview_completion.py`; `handoff/CODEX_MULTIVIEW_COMPLETION_EXECUTION_2026-10-03.md`.
- `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md`; `tools/HIERARCHICAL_LIGHT.md`; `tools/hierarchical_light.py`; `tools/hierarchical_light_native.py`; `tools/canopy_light.py`; `tomato3d/light/raytrace.py`; `tomato3d/light/frames.py`; `tomato3d/io/schemas.py`.
- `handoff/CODEX_LIGHT_GROWTH_READINESS_PROMPT_2026-10-03.md`; `handoff/CODEX_LIGHT_GROWTH_READINESS_EXECUTION_2026-10-03.md`.
- `tools/compound_growth.py`; `tools/probabilistic_compound_growth.py`; `tools/PROBABILISTIC_COMPOUND_GROWTH.md`; `handoff/CODEX_GROWTH_CALCULATOR_EXECUTION_2026-10-03.md`; `handoff/CLAUDE_GROWTH_CALCULATOR_REVIEW_HANDOFF_2026-10-03.md`.
- `tools/growth_calibration.py`; `tools/GROWTH_CALIBRATION.md`; `handoff/CODEX_GROWTH_CALIBRATION_EXECUTION_2026-10-03.md`; `handoff/CLAUDE_FSP_PHYSIOLOGY_ACCURACY_PROMPT_2026-10-03.md`.

Prepared by read-only source/document inspection. No model, fit, native optical job, training or regression suite was executed for this handoff. No credentials or machine-local environment values were exported. Only this new handoff and required logs are written by the authoring task.
