# Review of four project integration decisions

Date: 2026-10-03, Asia/Seoul. Reviewed: `CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md`. Scope is read-only review and this new handoff. No active program files, prior specifications or configuration were edited; no model, fitting, integration or test execution occurred.

## Verdict on D1 to D4

- **D1 is compatible with P3's current architecture.** `tools/probabilistic_compound_growth.py::decode_trajectory` produces the realized geometric trajectory, including direction, attachment, length, extents and optional supported area. Preserve P3 as the only geometry/size writer.
- **D2 is coherent and already acknowledged by the newer proposed physiology contract section 10.** It supersedes part of the earlier physiology prompt and does not describe all current P4 behavior. Current P4 implements a response-parameter fitter and `apply_parameter_set`, not the proposed carbon-sufficiency index. The existing adapter returns modified P3 parameter particles, although it does not itself add geometric increments. Decide explicitly whether that historical offline calibration route is retained as a separately selected P3 parameter source or excluded from D4. Under the requested diagnostic-only integration, do not call it automatically.
- **D3 is respected.** No integration implementation is started by this review. Existing independent goals continue under their own scope. Their completion must come from updated execution evidence, not file presence.
- **D4 is appropriate as a software integration target, with a required clarification:** reversible representation changes can round-trip; reductions and physical/model calculations generally cannot. Preserve original detail and metadata for lossless interchange rather than require inversion of PPFD, photosynthesis, aggregation or forecasts. Numerical equality uses explicit unit-specific tolerances; IDs/statuses must match exactly.

The decisions are ready to guide the final integration specification after the corrections below. The four-project end-to-end pass has not been executed or established by this review.

## 1 P3 already has several environment and light paths

Source: `tools/probabilistic_compound_growth.py`.

| Path | Inspected symbols and fields | Implication |
|---|---|---|
| Conditional parameter distributions | `FEATURES`, `_features`, `_draw`, `_trajectory`; `environment_scenario.values`, `families.features`, `coefficients`, `standardization` | Environment values, including `ppfd_umol_m2_s`, may alter sampled organ/segment/event parameters when explicitly configured. Calendar clock does not imply environment independence. |
| Conditional stopping | Axis `stop_logit.coefficients` over supported `FEATURES` | Environment can affect stopping where supplied; inspect axis as well as continuous-growth coefficients. |
| Development clock | `_clock`, `clock.kind=piecewise_linear_response`, `input_metric`, `input_unit`, `knots`, `intervals` | An explicit environment response changes developmental age and therefore timing and expansion. A supplied piecewise schedule may also already embody environmental effects. |
| Fixed external light | `validate_model_config`; `light_features`, `light_feature_id`, `fixed_over_horizon` | Non-environment metrics can drive a matching explicit fixed-over-horizon response. An environment-named metric follows the environment response branch; light-array presence alone does not prove that branch is active. |
| Previously fitted response | `tools/growth_calibration.py::_roles`, `apply_parameter_set` | Fitted feature effects can already be embedded in P3 particles for the supplied scenario. |

Important review finding: `sample_forecast` currently sets `environment_used`, `light_used` and coupling status from the clock branch alone. Those metadata are not an exhaustive audit of conditional-family or stop-logit dependencies. Do not use `environment_used=false` to conclude that a P4 correction cannot duplicate an existing environmental effect. The final integration auditor should inspect the complete frozen config and calibration provenance; any future flag correction belongs to P3's owner and is not applied here.

The current P4 `physical_location` binding rejects a coordinate with nonzero existing response coefficients, and `apply_parameter_set` requires a calendar clock. These are useful local safeguards, not proof that every possible feedback path is free of duplicate effects. Under D2, a P4 diagnostic must not alter P3 rates, geometry, sample weights, trajectories, events or seeds. Future reweighting would change the prediction distribution and requires the separately stated decision even without mesh edits.

## 2 Exact earlier sections affected by D1 and D2

Do not rewrite these documents in the active chats during this review. The final integration document should explicitly supersede the affected clauses while retaining the sources and history.

| Document and section | Existing implication | Required interpretation under D1/D2 |
|---|---|---|
| `CLAUDE_FSP_PHYSIOLOGY_ACCURACY_PROMPT_2026-10-03.md`, Task and required result | Allocation -> structural dry matter -> dimensions -> FSP state | Recast as diagnostic supply versus demand implied by the P3 trajectory; do not advance geometry from P4. |
| Same, Work package 3 | Potential demands, realized allocation, reserves and growth costs | May support a separate diagnostic carbon ledger. It must not allocate a second realized increment to P3. Demand must cover the stated organ/scope and accounting convention. |
| Same, Work package 4 | Carbon-constrained expansion and dry matter to form | Use an explicitly justified geometry-to-demand estimate or consistency check; do not invert a non-identifiable allometry by assumption or overwrite measured/P3 form. |
| Same, Work package 5 | Proposed `update_form`, `advance_physiology`, and replacement/residual/hybrid growth coupling | `update_form` is not an active P4 role. Any P4 state advance is diagnostic bookkeeping only. No replacement, residual multiplier or automatic feedback in D4. |
| Same, Accuracy and validation plan / completion communication | Evaluate geometry improvements from physiology integration | First D4 acceptance is conversion and diagnostic correctness. Biological evidence remains a later independent objective; do not claim improved P3 forecasts from a read-only index. |
| `CLAUDE_FOUR_PROJECT_ENV_IO_HANDOFF_2026-10-03.md`, sections 6 future physiology and 7 connections/checklist | P4 passes growth/area constraints to P3; ownership still to decide | Superseded by D1/D2: P3 supplies trajectory increments to P4; P4 returns diagnostic results with no state mutation. |
| `CLAUDE_SCIENCE_FSP_EQUATION_PROMPT_2026-10-03.md`, sections 1, 5 and 7 | Includes shape-growth equations and asks who determines increments | D1 answers ownership. Study equations for P4 demand/consistency purposes; prospective growth feedback is out of current scope. |
| `CODEX_GROWTH_CALIBRATION_EXECUTION_2026-10-03.md`, adapter requirement, and `tools/GROWTH_CALIBRATION.md`, Connecting to the existing engine | Offline fitter produces P3 parameter ensembles | Existing separate calibration capability, not the carbon diagnostic. Freeze whether it is excluded from D4 or explicitly selected before the P3 run. Do not silently delete this independently requested work. |

## 3 Carbon-sufficiency proposal needs a diagnostic contract

The ratio in the decision document is a proposed index, not a currently computed field. A newer file found during this review, `CLAUDE_FSP_PHYSIOLOGY_CONTRACT_2026-10-03.md`, explicitly implements D1-D4 at specification level in section 10. It proposes the pure function `compute_carbon_sufficiency(p3_interval, carbon_state, light_series, environment, parameter_pack)` and already defines conditional inverse allometry, maintenance deficit, no-growth demand and no P3 feedback. Its status is proposed specification with scientific review pending, not production implementation. Do not re-request those definitions as if no specification existed.

**Remaining synchronization gap:** `build/fsp_physiology_spec_20261003_01/integration_map.json` still lists only `audit_physiology_inputs,compute_leaf_exchange,compute_respiration,allocate_carbon,update_form,advance_physiology,audit_carbon_balance`; it omits `compute_carbon_sufficiency` and still describes a separate integrated physiology trajectory. Sections 5-7 retain old override/trajectory language, explicitly subordinated by section 10. This is resolved by prose precedence but not yet cleanly reflected in all machine-readable interface artifacts. Final integration must pin a synchronized pack and treat the counterfactual functions as isolated diagnostic analysis, never a second realized geometry writer.

The following checklist validates or completes that section 10 proposal; it is not an adoption of crop coefficients.

1. Define `carbon_supply_gC` and `carbon_demand_gC` on the same plant, interval, organ scope and respiration basis. State whether available supply includes allowed reserve withdrawal, whether maintenance is already removed, and whether demand includes growth costs. Do not compare net supply to a denominator that charges the same respiration again.
2. P3 currently outputs no root biomass, stem diameter, organ dry mass or reserve carbon. Length, projected/partial area and organ count do not uniquely determine those quantities. Require source-backed mass/composition/yield relations and initial states, or declare partial-scope/unavailable diagnostics. Missing root/reproductive demand is not zero; an area-only index cannot be labelled whole-plant carbon sufficiency.
3. Calculate demand from coherent P3 trajectory states at matched interval endpoints, retaining `trajectory_id` and weight. New organs need explicit birth cost/demand handling. Negative area/extent changes can reflect a change in shape/support and must not automatically become carbon release. Missing area or changed `area_basis_id` prevents a simple area difference.
4. Demand zero requires a distinct `zero_demand` reason; do not divide by zero or silently assign ratio=1/infinity. Signed/negative available supply, unmet maintenance, unknown inputs and uncertainty around the threshold need explicit status semantics. Keep `sufficient` conditional on the stated assumptions, not a statement of biological truth.
5. The P2 full-output snapshot is not automatically interval supply. Match actual schedules/time coverage and supported tissue scope; fixed geometry over time is a declared scenario. Future P3 envelopes remain optical-ineligible, so the first integration is not a closed future-canopy light loop.
6. Section 10's exact proposed outputs are `available_growth_carbon_gC,required_growth_carbon_gC,sufficiency_ratio,maintenance_deficit_gC,growth_deficit_gC,status,limiting_inputs,assumptions,source_hashes`. Freeze those in the machine-readable diagnostic schema together with plant-instance/source keys, `trajectory_id`, interval bounds, geometry/light/model references and supply/demand scope. There is no production producer yet. Additional context names are review proposals, not implemented fields.

For the full synthetic D4 path, supply explicitly synthetic mass/allometry/respiration/initial-state fixtures or label the P4 index unavailable. An expected-unavailable test is useful, but does not prove a numeric P4 index path passes. Test both paths if the index is part of acceptance.

## 4 Field inventory for the final adapters

This section covers the exchange fields in the four-project boundary described by D4. Preserve complete original artifacts and source hashes for unrelated columns rather than silently discard them. Appendix A enumerates every column of the current evolving P2 exchange schema directly from its JSON; it is a snapshot, not evidence of final implementation or a frozen contract.

Missing forms: **L** = P1/common and P2 numeric CSV `unavailable`; **G** = P3/P4 calibration CSV empty cell; **J** = JSON null. For required IDs missing/invalid usually rejects or gates the record; do not replace it with a numeric missing token. Original source files stay unchanged. `__all__` and `__unassigned__` in P2 v1 have distinct semantics and must not become real IDs.

### P1 surfaces and observations

| Source and fields | Unit and missingness | Adapter action |
|---|---|---|
| `tomato3d/io/schemas.py::LEAF_SURFACES_CSV_COLUMNS`: `plant_id,session_id,geometry_variant_id,geometry_source,organ_class,organ_id,leaflet_id,triangle_id,normal_convention` | Categorical IDs/provenance; required optical fields must pass loader/review | Preserve original identity, evidence and provenance; explicit source-to-instance mapping, no inferred physical association. |
| Same: `v0_x_mm,v0_y_mm,v0_z_mm,v1_x_mm,v1_y_mm,v1_z_mm,v2_x_mm,v2_y_mm,v2_z_mm` | Board mm; L at serialization, invalid geometry cannot become a valid optical face | Unit/rigid-frame conversion only; retain face vertex order and normal convention. |
| `tools/leaf_surface_compare.py` exports `candidate_surfaces.csv` with the above schema | Same schema, candidate status | Format compatibility is already present. Matching geometry review and optical eligibility are additional requirements, not a filename conversion. |
| Same `compound_areas.csv`: `plant_id,session_id,geometry_variant_id,organ_id,supported_area_cm2,total_area_cm2,supported_faces,input_faces,geometry_status,capture_date` | cm2, integer face counts, status/date; L | Preserve exact source names; never interpret `total_area_cm2` as an independently calibrated whole-plant truth. Join area basis/evidence before P3 use. |
| Same `patch_inventory.csv`: `plant_id,session_id,capture_date,organ_id,leaflet_id,tissue_patch_id,status,observed_point_count` | IDs/date/status/count; L when missing | Preserve patch identity, coverage and support; no merging across alternative reconstructions. |
| `tools/detected_leaf_area.py::COLUMNS`: `plant_id,session_id,capture_date,area_method,area_scope,view_id,label_id,area_px2,reference_label_id,reference_area_px2,relative_area,ratio_status,organ_class,source_annotation_id,generation,review,visibility,observation_status,manual_edit_present,image_sha256` | px2 / dimensionless / metadata; L | Keep as relative-image evidence only; no conversion to metric leaf tissue. Preserve grouping/reference label. |
| `tools/compound_growth.py::OBS_COLUMNS` | See exact fields below; G/J | P1 must supply independently reviewed whole-compound observation evidence; surface triangles alone cannot populate this table. |

Exact P3 observation fields are `plant_id,compound_leaf_id,session_id,observed_at,parent_stem_id,identity_status,review_source,geometry_status,development_state,first_observed_at,supported_area_cm2,area_basis_id,estimated_total_area_cm2,transverse_x,transverse_y,transverse_z`. Area is cm2, transverse is dimensionless, times are aware timestamps where required. Axis table fields: `plant_id,compound_leaf_id,session_id,station,x_mm,y_mm,z_mm`; extent fields: `plant_id,compound_leaf_id,session_id,station,left_mm,right_mm`. Station is normalized position; coordinates/extents are mm. Preserve all axis samples and transverse/area-basis evidence.

### P2 current hierarchy and evolving bridge

| Source and fields | Unit/missing | Adapter action |
|---|---|---|
| `tools/hierarchical_light.py::MEMBERSHIP`: `source_plant_id,plant_instance_id,session_id,capture_date,geometry_variant_id,organ_id,leaflet_id,compound_id,identity_status,evidence_path,evidence_sha256` | IDs/date/evidence; invalid/missing hierarchy gates | Reviewed join, retaining both source and instance. Source -> instance is one-to-many for clones, not an invertible two-column rename. |
| `write_report` / `interaction_cases.csv`: `target_id,plant_instance_id,source_plant_id,session_id,capture_date,compound_id,leaflet_id,area_m2,scenario_id,backend,fixture_id,replicate,seed,case_id,subset,received_umol_s,absorbed_umol_s,ppfd_umol_m2_s,absorbed_umol_m2_s,status,absorbed_status,reason,run_id` | area m2, flux umol/s, density umol/m2/s, seed integer; L | Select full physical scene, fixture scope and replicate explicitly. Do not sum all-fixture totals again with individual fixtures. Preserve statuses. |
| Hierarchy summaries: identity/scope plus `baseline_*`, `full_*`, `total_loss_*`, `standalone_A/B/C_*`, `marginal_A/B/C_*`, `shapley_A/B/C_*`, `overlap_*`, `loss_fraction`, method/status/reason | Suffixes `_umol_s` or `_umol_m2_s`; ratios dimensionless; L | Keep as diagnostic attribution with schema intact. Only full-scene flux is a candidate physiological supply input; baseline is a collection of counterfactual scenes. |
| `tools/light_growth_schema.json`, all five CSV tables | Full list in Appendix A; L; per-field reasons through `availability_id` | Producer files now exist; execution brief still reports in progress. Angular transport remains pending. Revalidate final schema hash before integration. |
| `light_growth_bridge._consumer_mapping`: `observed_states` | JSON `attachment_xyz_mm,rachis_points_mm,direction_unit_xyz,transverse_unit_xyz,region_partition`, identity/time/frame/area basis; J | Reuse reviewed observation payload and preserve full shape. Light arrival vector is not observed rachis direction. |
| `transforms.json`, package/capabilities/availability/audit metadata | Matrices, mm translation, units, hash/evidence, J | Preserve original transform, inverse, normal/arrival conventions, canopy context and capabilities. Their field dictionary must be frozen from final producer. |

Existing `light_growth_bridge.py` already contains `rigid_transform`, `transform_moments`, `aggregate_samples`, `integrate_light_schedule`, `split_canopy_results` and a consumer mapping; `light_growth_consumer.py` validates packages. Do not commission duplicate implementations from the older proposal. Their presence does not prove all acceptance tests passed. Existing split is reporting-only and retains canopy context; it does not restore a biologically isolated light field.

### P3 state and light input; P3 to diagnostic P4

| Source and fields | Unit/missing | Adapter action |
|---|---|---|
| P3 config `light_features`: `id,plant_id,compound_leaf_id,observed_at,area_basis_id,metric,unit,backend,source_ref,value`, optional `state_source` | Metric carries explicit unit; J, required fields checked | Reviewed instance/source and compound mapping; no arbitrary multi-fixture/time-series collapse. Pin metric/side/area basis and scenario. |
| P3 `environment_scenario.id,values,response_ref`; values `temperature_c,relative_humidity_pct,ppfd_umol_m2_s,photoperiod_h,ec_ms_cm,ph,co2_ppm` | deg C, %, umol/m2/s, h/day, mS/cm, dimensionless, ppm; J | Freeze exact values/units/domain and source. `response_ref` alone is not executable. |
| `export_run` / `block_states.csv`: `trajectory_id,block_id,source_compound_leaf_id,parent_stem_id,elapsed_days,target_at,existence,state_source,frame_id,attachment_x_mm,attachment_y_mm,attachment_z_mm,direction_x,direction_y,direction_z,axis_length_mm,left_extent_mm,right_extent_mm,supported_area_cm2,area_basis_id,optical_eligible` | day, timestamp, mm, unit vector, cm2, boolean; G | Difference matched states in the same trajectory for diagnostic intervals; retain birth/existence and origin. Do not convert displacement or summary width to mass automatically. |
| `events.csv`: `trajectory_id,parent_stem_id,predicted_block_id,event_index,event_state,appearance_elapsed_days,appearance_development_days,material_node_id` | IDs/count/calendar or development days; G | Preserve stopped/censored distinctions and future identity; newborn demand is a separate specified rule. |
| `trajectories.csv`: `run_id,trajectory_id,parameter_particle_id,scenario_id,weight,valid,status_reason,random_stream_id` | IDs, dimensionless weight, boolean; G | Retain joint samples/failed mass; diagnostic must not change weights under D2. |
| `trajectory_parameters.json`, `origin.json`, `model.json` | Full shapes, frames, parameter order/covariance, clocks, assumptions, hashes; J | Required for lossless reconstruction. `block_states.csv` contains max side extents and a chord direction, not the complete curved rachis/profile. Summary quantiles cannot reconstruct samples. |

Current P3 does not export a canonical interval-increment CSV or gC demand. A future adapter must explicitly derive increments from frozen decoded states and carry all unavailable/basis changes; P4 diagnostic fields remain proposed in section 3 above.

### P4 existing calibration versus the not-yet-defined index

| Source and fields | Unit/missing | Adapter action |
|---|---|---|
| `tools/growth_calibration.py::COLUMNS`: `record_id,plant_id,organ_id,target_id,unit_id,observed_at,origin_at,elapsed_days,value,initial_value,unit,frame_id,identity_status,coverage_basis,age_basis,measurement_sd,lower_day,upper_day,censoring,visibility_status,split,capture_phase,exposure_kind` | Values/SD use declared target unit; elapsed/censor bounds calendar days; G | Preserve treatment assignment, temporal basis, actual historical exposure and held-out status. These are calibration records, not P3 predictions relabelled as observations. |
| Calibration feature columns and manifest `feature_units`, `feature_provenance`, `target_metadata` | Explicit units; G/J | Map environmental features only through reviewed fit definitions; no fixed schema for arbitrary features. |
| Parameter set `values,particles,fit_plan,eligible_targets,parameter_set_id,source_hashes,validation_status,uncertainty_kind`; `engine_bindings` in plan | Per-parameter units, transforms, covariance/weights; J | Separate optional offline P3 configuration input from the D2 runtime diagnostic. Current adapter uses calendar clock and explicit bindings. |
| Proposed P4 index: exact section 10 outputs listed in section 3 above | gC supply/demand/deficits, dimensionless ratio; JSON null plus status/reason when unavailable | Proposed contract now exists; needs scientific review and synchronized machine schema. No production implementation claimed. |

The new physiology specification section 6 also names a proposed light-input CSV: `plant_id,organ_id,patch_id,t_start,t_end,area_m2,ppfd_absorbed_umol_m2_s,ppfd_incident_umol_m2_s,light_basis,coverage_basis,quantity,replicate,geometry_hash,source_hash,status,reason`. These differ from P2's `sample_id,start_at,end_at,quadrature_area_m2,absorbed_ppfd_umol_m2_s,received_ppfd_umol_m2_s`; map units and semantics explicitly. A quadrature receiver is not automatically a whole patch, and simultaneous fixtures must be combined exactly once before the nonlinear exchange function.

The proposed physiology state JSON requires `schema_version,plant_id,trajectory_id,at,reserve_gC,organs,stage_scope,frame_id,source_refs`; each organ requires `organ_id,organ_kind,structural_dm_g,carbon_fraction_gC_gDM,mass_basis,evidence_kind,development,geometry,anchor`. Units are gC, gDM, gC/gDM and declared developmental units; geometric fields carry mm/m2 and named frames. Root geometry may be null, but required mass/reserve values are not nullable in this state schema: missing states must fail an audit or return an unavailable result, not be inserted into a nominally valid state object. Source references include path/hash/status; the section 6 reference convention additionally requires locator. Freeze those conditional differences explicitly for the diagnostic input/output package.

Other section 6 proposed exchange fields, still subject to section 10 precedence:

- Environment CSV: `plant_id,t_start,t_end,leaf_temperature_c,air_temperature_c,temperature_basis,co2_ppm,pressure_pa,environment_kind,status,source_hash`. Temperatures deg C, CO2 ppm, pressure Pa; time strings aware. Air temperature cannot silently populate a leaf-temperature field, nor can ppm silently replace partial pressure. Existing P3 environment values have no pressure/leaf-temperature measurement.
- Parameter pack: `schema_version,pack_id,model_id,respiration_accounting,light_basis,applicable_domain,stage_scope,parameters,source_registry_ref,organ_parameter_map,uncertainty,review,numerics,capacity_policy,initial_state_refs`; each parameter retains `value,unit,evidence_kind,source_id,locator,uncertainty,applicability,review_state`. Null coefficients gate calculations; this is not a lossless conversion from P3's unrelated empirical parameter names.
- Proposed diagnostic/counterfactual flux ledger: common IDs `run_id,trajectory_id,plant_id,organ_id,organ_kind,compound_id,parent_id,observed_at,frame_id,parameter_pack_id,scenario_id`, followed by `t_start,t_end,photosynthetic_supply_gC,maintenance_charged_gC,growth_respiration_gC,import_gC,export_gC,reserve_before_gC,reserve_after_gC,structural_before_gC,structural_after_gC,balance_residual_gC,status`. Carbon fields use gC per stated stock/interval, not gC/s. Missing result rules must be frozen in a diagnostic schema; the proposed pack uses null plus reason for unavailable scientific quantities. Such a ledger must not be written back as P3 growth state.

## 5 Corrections and additions to D4 acceptance

1. **Classify conversions.** Unit/frame changes are reversible within precision. Clone expansion needs the full mapping to reverse. Angular wrap is equivalent orientation, not original unwrapped degrees; preserve raw angles if literal restoration is required. UTC normalization preserves the instant, not the original timezone label unless saved. A paused/nonmonotone development clock cannot have an assumed unique inverse.
2. **Do not demand inversion of reductions.** Tissue-to-light, sample-to-mean, P3 state-to-summary and geometry-to-carbon-demand are computations, not lossless codecs. Preserve the source samples, shapes, weights and provenance; test aggregate consistency separately.
3. **Freeze source versions after goals finish.** Pin producer schema, code, settings and test evidence. New artifacts get new hashes while retaining source hashes and lineage; copying an old hash onto transformed bytes is invalid. Do not use live mutable files as the acceptance fixture.
4. **Separate scope from readiness.** Define which current goals must be complete and their required evidence. P1 completion-trial and P2 angular-hook dependencies must not disappear merely because a synthetic simpler route passes. D4 itself can use synthetic geometry without proving P1 reconstruction accuracy, but must not call that proof the original P1 goal's completion.
5. **Require all edges, not just a linear diagram.** P1 -> P3 observation/axis input is separate from P1 -> P2 tissue. P2 -> P3 needs a declared response binding. P3 -> P4 and P2/environment -> P4 need matched interval/scope/trajectory. P4 -> P3 runtime mutation must be absent under D2.
6. **Preserve optical boundaries.** The requested pass can exercise held-geometry light plus P3 forecast and P4 diagnostic. It does not authorize routing future CompoundLeaf envelopes back to optical transport. Use explicit time/geometry scenario and no absorption extrapolation to unseen tissue.
7. **Negative and boundary fixtures.** Include missing/zero demand/light, opposite signed elevations, angle wrap/poles, unknown local frame, two copies of one plant, unmatched/ambiguous IDs, duplicate sample keys, mixed area basis, partial tissue, stale hashes, schedule gaps/midnight, full-output versus interval confusion, and missing native channels. Require no state/seed/weight change when diagnostic values vary.
8. **Per-field tolerances and exact categorical equality.** Length, area, angle, flux and time need different scale-aware absolute/relative tolerances. P2's current numerical policy is a producer check, not automatically the complete cross-project acceptance policy. Preserve signed losses and uncertainty types; never clamp unavailable or negative diagnostic values into a success state.

## 6 Decisions requested from Claude before the final integration prompt

- Confirm D2 applies to the **runtime carbon index**, and explicitly retain/exclude the existing **offline calibration-to-P3 configuration route**. Neither route should be accidentally deleted or auto-enabled by an adapter.
- Review the new physiology contract section 10 and synchronize its diagnostic API/output/status definitions into the evidence pack. Its no-growth and maintenance-deficit cases are already specified; remaining review includes applicability/uncertainty, input scope, mass prerequisites and synthetic fixtures. State whether numeric P4 output is mandatory in the first pass; if optional, name that acceptance scope explicitly rather than claiming a full numeric four-project pass.
- Correct the lossless requirement to source-preserving reversible interchange plus declared computation invariants, and identify the actual four-goal completion evidence required before D4 starts.

These are specification clarifications, not a request to start implementation. Current decision documents and active owners' code are preserved. Append this review to the final integration evidence; issue no integration work until D3 is satisfied and the final prompt is explicitly invoked.

## Appendix A Current P2 exchange field snapshot

The following inventory is extracted from `tools/light_growth_schema.json` at review time. All five tables are from an in-progress producer. Names/types/units below are exact schema declarations; unit `1` on strings is the producer's metadata convention, not a physical quantity. Timestamp/timezone strings must receive semantic validation. Nullable numeric missing values serialize as `unavailable`; every affected field needs its `availability.json` reason. Required IDs use explicit producer sentinels only where allowed.

Schema SHA256: 605e14aff16f99ca3d293ed7bd8c239aed3cc4c7c5fbb43f4e66edb4da4f1cb3.

### instance_map.csv

Primary key: run_id, scenario_id, geometry_snapshot_id, plant_instance_id, session_id, compound_id.

| Field | Type | Unit | Nullable |
|---|---|---|---|
| run_id | string | 1 | false |
| scenario_id | string | 1 | false |
| geometry_snapshot_id | string | 1 | false |
| plant_instance_id | string | 1 | false |
| source_plant_id | string | 1 | false |
| session_id | string | 1 | false |
| compound_id | string | 1 | false |
| compound_leaf_id | string | 1 | false |
| observed_at | string | 1 | false |
| frame_id | string | 1 | false |
| transform_id | string | 1 | false |
| geometry_sha256 | string | 1 | false |
| data_kind | string | 1 | false |
| association_status | string | 1 | false |
| evidence_sha256 | string | 1 | false |
| availability_id | string | 1 | false |

### light_samples.csv

Primary key: run_id, scenario_id, geometry_snapshot_id, plant_instance_id, session_id, compound_id, time_step_id, backend, replicate, organ_id, leaflet_id, triangle_id, sample_id, fixture_id.

| Field | Type | Unit | Nullable |
|---|---|---|---|
| run_id | string | 1 | false |
| scenario_id | string | 1 | false |
| geometry_snapshot_id | string | 1 | false |
| plant_instance_id | string | 1 | false |
| session_id | string | 1 | false |
| compound_id | string | 1 | false |
| time_step_id | string | 1 | false |
| backend | string | 1 | false |
| replicate | string | 1 | false |
| source_plant_id | string | 1 | false |
| capture_date | string | 1 | false |
| observed_at | string | 1 | false |
| geometry_variant_id | string | 1 | false |
| data_kind | string | 1 | false |
| organ_id | string | 1 | false |
| leaflet_id | string | 1 | false |
| compound_leaf_id | string | 1 | false |
| frame_id | string | 1 | false |
| transform_id | string | 1 | false |
| area_basis_id | string | 1 | false |
| triangle_id | string | 1 | false |
| sample_id | string | 1 | false |
| fixture_id | string | 1 | false |
| position_grow_x_mm | number | mm | true |
| position_grow_y_mm | number | mm | true |
| position_grow_z_mm | number | mm | true |
| normal_grow_x | number | 1 | true |
| normal_grow_y | number | 1 | true |
| normal_grow_z | number | 1 | true |
| position_board_x_mm | number | mm | true |
| position_board_y_mm | number | mm | true |
| position_board_z_mm | number | mm | true |
| normal_board_x | number | 1 | true |
| normal_board_y | number | 1 | true |
| normal_board_z | number | 1 | true |
| quadrature_area_m2 | number | m2 | true |
| normal_side_ppfd_umol_m2_s | number | umol/m2/s | true |
| opposite_side_ppfd_umol_m2_s | number | umol/m2/s | true |
| received_ppfd_umol_m2_s | number | umol/m2/s | true |
| absorbed_ppfd_umol_m2_s | number | umol/m2/s | true |
| normal_convention | string | 1 | false |
| availability_id | string | 1 | false |

### compound_light_features.csv

Primary key: run_id, scenario_id, geometry_snapshot_id, plant_instance_id, session_id, compound_id, time_step_id, backend, replicate, level, entity_id, fixture_id, region_id, quantity_frame.

| Field | Type | Unit | Nullable |
|---|---|---|---|
| run_id | string | 1 | false |
| scenario_id | string | 1 | false |
| geometry_snapshot_id | string | 1 | false |
| plant_instance_id | string | 1 | false |
| session_id | string | 1 | false |
| compound_id | string | 1 | false |
| time_step_id | string | 1 | false |
| backend | string | 1 | false |
| replicate | string | 1 | false |
| source_plant_id | string | 1 | false |
| capture_date | string | 1 | false |
| observed_at | string | 1 | false |
| geometry_variant_id | string | 1 | false |
| data_kind | string | 1 | false |
| organ_id | string | 1 | false |
| leaflet_id | string | 1 | false |
| compound_leaf_id | string | 1 | false |
| frame_id | string | 1 | false |
| transform_id | string | 1 | false |
| area_basis_id | string | 1 | false |
| level | string | 1 | false |
| entity_id | string | 1 | false |
| fixture_id | string | 1 | false |
| region_id | string | 1 | false |
| quantity_frame | string | 1 | false |
| supported_area_m2 | number | m2 | true |
| estimated_total_area_m2 | number | m2 | true |
| supported_area_cm2 | number | cm2 | true |
| coverage_fraction | number | 1 | true |
| coverage_status | string | 1 | false |
| received_umol_s | number | umol/s | true |
| absorbed_umol_s | number | umol/s | true |
| received_supported_subtotal_umol_s | number | umol/s | true |
| absorbed_supported_subtotal_umol_s | number | umol/s | true |
| normal_side_ppfd_umol_m2_s | number | umol/m2/s | true |
| opposite_side_ppfd_umol_m2_s | number | umol/m2/s | true |
| received_ppfd_umol_m2_s | number | umol/m2/s | true |
| absorbed_ppfd_umol_m2_s | number | umol/m2/s | true |
| received_p10_umol_m2_s | number | umol/m2/s | true |
| received_p50_umol_m2_s | number | umol/m2/s | true |
| received_p90_umol_m2_s | number | umol/m2/s | true |
| observed_rachis_x | number | 1 | true |
| observed_rachis_y | number | 1 | true |
| observed_rachis_z | number | 1 | true |
| observed_azimuth_deg | number | degree | true |
| observed_elevation_deg | number | degree | true |
| arrival_flux_umol_s | number | umol/s | true |
| arrival_M_x_umol_s | number | umol/s | true |
| arrival_M_y_umol_s | number | umol/s | true |
| arrival_M_z_umol_s | number | umol/s | true |
| arrival_B_xx_umol_s | number | umol/s | true |
| arrival_B_xy_umol_s | number | umol/s | true |
| arrival_B_xz_umol_s | number | umol/s | true |
| arrival_B_yy_umol_s | number | umol/s | true |
| arrival_B_yz_umol_s | number | umol/s | true |
| arrival_B_zz_umol_s | number | umol/s | true |
| mean_arrival_x | number | 1 | true |
| mean_arrival_y | number | 1 | true |
| mean_arrival_z | number | 1 | true |
| dominant_arrival_x | number | 1 | true |
| dominant_arrival_y | number | 1 | true |
| dominant_arrival_z | number | 1 | true |
| directionality | number | 1 | true |
| angular_second_xx | number | 1 | true |
| angular_second_xy | number | 1 | true |
| angular_second_xz | number | 1 | true |
| angular_second_yy | number | 1 | true |
| angular_second_yz | number | 1 | true |
| angular_second_zz | number | 1 | true |
| left_right_flux_difference_umol_s | number | umol/s | true |
| proximal_distal_flux_difference_umol_s | number | umol/s | true |
| left_right_mean_contrast | number | 1 | true |
| proximal_distal_mean_contrast | number | 1 | true |
| availability_id | string | 1 | false |

### light_intervals.csv

Primary key: run_id, scenario_id, geometry_snapshot_id, time_step_id, backend, replicate, fixture_id.

| Field | Type | Unit | Nullable |
|---|---|---|---|
| run_id | string | 1 | false |
| scenario_id | string | 1 | false |
| geometry_snapshot_id | string | 1 | false |
| plant_instance_id | string | 1 | false |
| session_id | string | 1 | false |
| compound_id | string | 1 | false |
| time_step_id | string | 1 | false |
| backend | string | 1 | false |
| replicate | string | 1 | false |
| fixture_id | string | 1 | false |
| start_at | string | 1 | false |
| end_at | string | 1 | false |
| timezone | string | 1 | false |
| geometry_mode | string | 1 | false |
| schedule_evidence_id | string | 1 | false |
| duration_s | number | s | true |
| output_fraction | number | 1 | true |
| availability_id | string | 1 | false |

### light_dose.csv

Primary key: run_id, scenario_id, plant_instance_id, session_id, compound_id, backend, replicate, level, entity_id, fixture_id, start_at, end_at.

| Field | Type | Unit | Nullable |
|---|---|---|---|
| run_id | string | 1 | false |
| scenario_id | string | 1 | false |
| geometry_snapshot_id | string | 1 | false |
| plant_instance_id | string | 1 | false |
| session_id | string | 1 | false |
| compound_id | string | 1 | false |
| time_step_id | string | 1 | false |
| backend | string | 1 | false |
| replicate | string | 1 | false |
| source_plant_id | string | 1 | false |
| organ_id | string | 1 | false |
| leaflet_id | string | 1 | false |
| level | string | 1 | false |
| entity_id | string | 1 | false |
| fixture_id | string | 1 | false |
| area_basis_id | string | 1 | false |
| start_at | string | 1 | false |
| end_at | string | 1 | false |
| timezone | string | 1 | false |
| requested_seconds | number | s | true |
| covered_seconds | number | s | true |
| absorbed_covered_seconds | number | s | true |
| incident_dose_mol_m2 | number | mol/m2 | true |
| absorbed_dose_mol_m2 | number | mol/m2 | true |
| incident_supported_dose_mol_m2 | number | mol/m2 | true |
| absorbed_supported_dose_mol_m2 | number | mol/m2 | true |
| dli_mol_m2_day | number | mol/m2 | true |
| incident_photons_mol | number | mol | true |
| absorbed_photons_mol | number | mol | true |
| complete_local_day | boolean | 1 | false |
| integration_method | string | 1 | false |
| availability_id | string | 1 | false |
