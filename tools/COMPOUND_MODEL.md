# Compound surface and growth calculations

These tools audit supported leaf tissue and calculate short-horizon compound-axis forecasts. They do not provide a calibrated tomato growth law. Install/use the project's Python environment; these tools use its existing NumPy, OpenCV, SciPy and Shapely libraries. No files in human config or observation records are modified.

## Commands

Run from the Tomato 3D phenotyping analysis directory. Every output directory must be new and beneath project `build/`.

```powershell
python -X utf8 -m tools.compound_growth --help
python -X utf8 -m tools.compound_surface --help
python -X utf8 -m tools.compound_growth templates --out build/my_compound_inputs
python -X utf8 -m tools.compound_growth extract --input build/my_compound_inputs/observations.json --out build/my_compound_states
python -X utf8 -m tools.compound_growth forecast --input build/my_compound_inputs/observations.json --plant PLANT_ID --compound LEAF_ID --origin 2026-10-03T12:00:00+09:00 --horizons 1 2 --settings build/my_compound_inputs/forecast_settings.json --out build/my_compound_forecast
python -X utf8 -m tools.compound_growth evaluate --input build/my_compound_inputs/observations.json --plan build/evaluation_plan.json --out build/my_compound_evaluation
python -X utf8 -m tools.compound_surface --study build/surface_study.json --out build/my_surface_audit
```

Replace the example timestamp/IDs with explicit source values; the examples are not capture records. Blank templates are intentionally not forecast-ready. After entering real inputs, record their current SHA256 hashes in the manifest. The tool rejects changed files instead of silently updating an input manifest. PowerShell `Get-FileHash -Algorithm SHA256 -LiteralPath <path>` reports a hash; manifest hashes use lowercase hexadecimal.

To inspect an existing structure without pretending it is a full growth observation:

```powershell
python -X utf8 -m tools.compound_growth audit-legacy --structure build/plants_dwt_test_20261002/plants/dwt_t1/pipeline_growth/dwt_t1/structure/structure.json --out build/my_t1_input_audit
```

This keeps `proposed_name` and visible petiole segments separate from confirmed compound IDs, attachments and whole rachises. It computes signed segment direction for diagnosis. It never guesses capture time from a session name or treats an unsigned legacy angle as signed.

## Observation contract

`observations.json` has schema `compound-observations-1`, `coordinate_frame: board_mm`, an explicit `frame_id`, `frame_stability`, `frame_evidence`, `data_kind` (`observed` or `synthetic`), `reference_status`, and `tables`. Each table entry has `path` and `sha256`. Use `reference_status: independent_observation` only for independent observations; `synthetic_truth` labels known synthetic references. `model_generated` and `unverified` cannot serve as evaluation truth.

The three CSV headers are emitted by `templates` and exported as module constants. Observation keys are plant, compound and session. Each compound also requires an aware `observed_at`, parent stem identity, confirmed temporal identity with a review source, and `geometry_status: observed_axis` before forecasting. Missing/ambiguous fields remain in extraction results but make the state ineligible. Blank or `unavailable` numeric values remain null in JSON/`unavailable` in CSV. Do not fill them with zero.

`axes.csv` has ordered `station` parameters from 0 at the observed attachment to 1 at the observed tip, plus board-frame `x_mm,y_mm,z_mm`. All timestamps used together must use consistent station semantics and count. The station parameter is the declared correspondence along the sampled axis; changing the sampling between dates is not growth. Length is recomputed as polyline arc length. A visible petiole end alone is not the distal compound tip.

`extents.csv` has station, `left_mm` and `right_mm`. Left is negative and right positive along the observation's `transverse_unit_xyz`; supplied transverse components must be a unit vector perpendicular to attachment-to-tip direction. Width bars are extent descriptors, not tissue polygons. The viewer interpolates station positions on the axis and displays these bars without filling tissue gaps.

`supported_area_cm2` means area of a specifically tracked support/coverage basis. `area_basis_id` is required for any supplied area; a change of basis prevents an apparent area growth rate. `estimated_total_area_cm2` remains separate and must not be obtained by relabeling a partial area. Provenance for supplied values belongs in the review source and source manifest. Source review declarations are preserved, not independently certified by the software.

A stable frame must be supported by capture provenance. Do not mix T3 movement groups or invent a registration to make them agree. Board coordinates do not remove motion of the plant relative to its board. Parent attachment translation is separated from local shape change. Parent rotation is not independently identified by this contract; the angular baseline predicts observed compound orientation, without attributing the movement to a biological mechanism.

## Models and domain

`forecast_settings.json` requires `model`, positive `max_horizon_days`, and `provenance`. The horizon maximum is the caller's declared applicability limit, not a recommended biological value.

- `persistence` retains the most recent state, including attachment position.
- `recent_change` uses the latest two timestamps and their actual time gap. It predicts attachment translation separately, transports the earlier shape into the latest orientation, extrapolates local shape and arc length, and applies the observed angular velocity. Width and area rates require comparable support. Antipodal/half-turn rotation, collapsed/reversed axes, negative dimensions and invalid horizons produce unavailable forecasts. Orientation follows the minimal observed rotation; multiple unseen rotations between captures cannot be recovered.
- `reviewed_growth` returns unavailable with a reason. The prompt assigns biological transition choice and coefficient justification to Claude; no such reviewed specification or target-cultivar coefficients were available. This is not a fitted third model.

No model uses future environment or converts a scalar DLI into a preferred direction. Environment scenarios are retained as metadata only; `environment_used=false`. Prediction intervals are uncalibrated. Predicted states have `eligible_state=false` so they cannot be recycled as observed truth. Forecasts are diagnostic and keep `validated_growth=false` and `suitable_for_ppfd=false`.

The evaluation plan requires disjoint `train_plant_ids`/`test_plant_ids`, `split_provenance`, `model_parameters`, and `forecasts` with plant/compound, `forecast_origin`, and exact `target_at`. Origins use only earlier history. Test-time past observations are allowed for initialization; future test observations are only targets. These baselines do not fit on the training plants. Errors and available-target coverage are reported by horizon. No independent statistical confidence claim is made from repeated compounds/dates.

## Surface audit contract

`surface_study.json` uses schema `compound-surface-study-1`, a standard `LEAF_SURFACES_CSV_COLUMNS` geometry table and a separate evidence CSV, each with a path and SHA256. Evidence keys are `plant_id,session_id,geometry_variant_id,organ_id,leaflet_id,triangle_id`; additional fields are `tissue_patch_id,identity_status,support_kind,topology_review,review_source`.

`visible_support` entries declare tissue patch, `visibility`, review source, hashed capture/mask paths, and image filename. Only explicitly visible views support a face; occluded views do not contradict it. Masks must occupy the original calibrated image grid. A patch cannot span plants or sessions. The full rasterized face footprint is checked using the existing `inside_mask`, including its sampling of distortion along edges. This is an image-resolution check, not an exact continuous proof.

`policy` requires `coordinate_tolerance_mm`, `minimum_face_area_mm2`, `minimum_supported_views` (at least two), and `maximum_pair_checks`. These numerical audit settings must be supplied explicitly; null settings are not silently defaulted. Coordinate tolerance must remain a numerical geometry tolerance, not an inflated biological tolerance for merging tissues.

Duplicate physical faces are counted once only for the same confirmed patch; coincident ambiguous tissues and intersecting faces require review. Legitimate shared edges of folded faces remain valid. Pair-budget exhaustion marks the audit incomplete and prevents area eligibility. Geometry sources are never repaired. `local_patch_faces(points_mm,boundary,holes)` supports separate local charts, discarding boundary/hole-crossing faces; it is conservative interpolation and does not establish complete coverage.

Outputs include per-face JSON reasons, `compound_areas.csv`, a derived `supported_leaf_surfaces.csv` using the existing geometry schema, and a pending surface review. The only aggregate is supported partial one-sided blade area; totals and optical eligibility remain unavailable. Petiole/rachis cylinders and duplicated back faces do not become blade area.

### Real-area evidence boundary (technical review section 6, 2026-10-04)

`eligible_supported_area`, `supported_area_cm2` and `supported_leaf_surfaces.csv` remain **diagnostic geometry-support outputs**, not downstream real-area approval. The additive gate in `compound_surface.audit_area_evidence`, called by every `audit_surface`, emits `eligible_real_area`, `area_basis_id` and explicit reason codes. Legacy calls without evidence keep their diagnostic values but cannot issue a real area basis. No reconstruction or triangulation formula changes.

A study may reference `area_evidence: {path, sha256}`. The JSON uses schema `p1-area-evidence-1`, explicit `data_kind: observed` or `synthetic`, `geometry_digest`, `partition_source_ref`, `sources`, and `patches`. `geometry_digest` is `tools.leaf_light.common.digest(rows(geometry_csv))` over the exact loaded geometry rows (CSV cells are strings). This binds the claim to geometry content. `sources` maps source IDs to `{path, sha256}`; paths resolve relative to the evidence JSON. Every required source must exist and match its SHA256. Missing scientific evidence returns unavailable; a changed hash, duplicate claim, or claim for an absent patch is an integrity/input error. The CLI also hashes its study, geometry, evidence CSV, capture files and masks.

Each patch claim has `plant_id, session_id, geometry_variant_id, organ_id, leaflet_id, tissue_patch_id`, a declared `area_basis_id`, and these required groups:

| Group | Required fields | Meaning / validation |
|---|---|---|
| identity | partition_sha256, reviewer, source_ref | Exact hash of the file named by partition_source_ref; explicit reviewer and hashed association evidence |
| scale | square_size_mm, calibration_residual_mm, source_ref | Positive physically calibrated ChArUco square size and nonnegative calibration residual in mm; source must describe actual scale calibration, not only PnP reprojection |
| pose | max_reprojection_error_px, source_ref | Declared nonnegative threshold; every visible support frame needs finite residual <= threshold, solved pose and passes_pose_gate=true |
| capture | captured_at, capture_phase, source_ref, schedule_source_ref | Aware ISO timestamp, explicit early_photoperiod or late_photoperiod and actual timing/schedule evidence; software does not infer phase from daily duration |
| area | quantity, coverage_fraction, occlusion_statement, source_ref | quantity=one_sided_physical_tissue; fraction in (0,1]; explicit coverage/occlusion statement and hashed supporting evidence |

Coverage describes the submitted patch. All its faces must pass the original geometry/support checks before its basis can be issued; dropping a failed face cannot silently reuse a larger coverage declaration. Each patch coverage has a distinct basis ID. The gate never divides area by coverage to estimate a total. Only reconstructed/manual tissue geometry can pass, with the same observed-support restrictions as before; assumed/simplified geometry cannot become a real measurement through a metadata label.

`area_basis.csv` reports declared ID separately from eligible ID, nullable `downstream_supported_area_cm2`, status and reasons per patch. `downstream_leaf_surfaces.csv` contains only passing real-area faces. Explicit synthetic data retain their declared identifiers for software tests but always have unavailable real eligibility. A synthetic study cannot override this by declaring observed evidence in its attached manifest. No area basis is auto-generated.

Passing means **the declared evidence contract is complete**, not independent verification of the evidence author's scientific claims. Source files may include manually reviewed records; hashing cannot establish that a calibration or anatomical review was performed correctly. `validated_metric=false`, `suitable_for_ppfd=false` and pending surface-review status remain. Optical acceptance still needs its existing separate gates. Historical diagnostic files must not be relabelled downstream.

The gate reports `biological_face_status=unavailable` and `illuminated_faces=null`. Triangle winding, unsigned plane normal, upward orientation and camera visibility do not prove botanical adaxial/abaxial identity. P1 must supply reviewed face evidence; P2 owns illumination exposure and P4 its exchange-policy gate. No botanical or illumination certificate is manufactured here.

Current approved Day-1 record template/checklist and P3 mapping are delivered separately in `build/technical_review_fixes_20261004_01/P1/measurements/` and `handoff/CODEX_P1_GROWTH_PACK_V2_EXECUTION_2026-10-04.md`. D14 options/D21 visible-bud recording supersede older unadopted-policy notes; they supply no measured covariance, posture offset, event or organ age.

## Light integration

Use the existing bridge through the wrapper; it prepares only and never executes GroIMP:

```powershell
python -X utf8 -m tools.compound_growth prepare-light --run build/EXISTING_RUN --plant PLANT_ID --session SESSION_ID --study build/EXISTING_STUDY/study.json --case CASE_ID --out build/my_light_preparation
```

It invokes `tools.plant_light_bridge.connect(..., execute=False)` with all existing source, placement, surface, lamp and sensor gates. A new surface CSV requires its own matching review and explicit study reference; this command does not accept the audit's pending review or a forecast envelope as eligible geometry. No second optical solver or unit conversion was added.

## Verification outputs

`states.csv`, axis/extent CSVs and forecast CSVs are the numerical exports. JSON retains provenance, flags and a serialized diagnostic state for replay/viewing; it is not a replacement human observation table. `viewer.html` is self-contained and labels synthetic examples. Original inputs and code are hashed. Re-running writes to a new directory.

The saved `build/compound_model_20261003_01/reproduce.py` uses explicitly synthetic test fixtures to exercise CLI extraction, two forecasts, evaluation, surface audit and existing light preparation, then audits an explicit saved T1 structure read-only. To rerun without overwriting earlier outputs:

```powershell
python -X utf8 build/compound_model_20261003_01/reproduce.py build/my_fresh_compound_verification
python -X utf8 -m pytest tools/tests/test_compound_growth.py tools/tests/test_compound_surface.py -q
```

Real directional accuracy still requires timestamped stable-frame whole-axis observations, confirmed compound IDs, comparable width/area evidence and independent later targets. The saved T1 data support a partial diagnostic audit, not that validation.
