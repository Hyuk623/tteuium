# Probabilistic CompoundLeaf growth calculator

An extension of `tools.compound_growth` for assumption-conditioned 30-day trajectories. Existing observation extraction, persistence/recent-change forecasts and viewers retain their behavior. The implementation is in `tools/probabilistic_compound_growth.py`; it does not run images, light transport or training.

All commands run from the project root. Outputs must use a **new** directory under `build/`. No custom process environment variables are required by this CLI: input paths are explicit. Shared `TOMATO3D_*` settings are not biological inputs.

## Commands

```powershell
python -X utf8 -m tools.compound_growth probabilistic --help
python -X utf8 -m tools.compound_growth probabilistic templates --out build/growth_inputs_new
python -X utf8 -m tools.compound_growth probabilistic demo --out build/growth_demo_new
```

The demo writes `inputs/` and `results/`; every measurement and coefficient in it is explicitly synthetic. The blank template supplies no biological values. Fill it from reviewed measurements and explicit assumptions before forecasting. Each table entry contains its filename and SHA256; recompute that hash after intentionally preparing input tables.

```powershell
python -X utf8 -m tools.compound_growth probabilistic audit --history build/growth_inputs_new/observations --structure build/growth_inputs_new/structure.json --origin build/growth_inputs_new/origin.json --model build/growth_inputs_new/model.json --out build/growth_audit_new
python -X utf8 -m tools.compound_growth probabilistic forecast --history build/growth_inputs_new/observations --structure build/growth_inputs_new/structure.json --origin build/growth_inputs_new/origin.json --model build/growth_inputs_new/model.json --summary-config build/growth_inputs_new/summary_config.json --out build/growth_run_new
python -X utf8 -m tools.compound_growth probabilistic decode --run build/growth_run_new --days 0 3 7 14 21 30 --out build/growth_query_new
python -X utf8 -m tools.compound_growth probabilistic summarize --run build/growth_run_new --summary-config build/growth_inputs_new/summary_config.json --out build/growth_summary_new
python -X utf8 -m tools.compound_growth probabilistic update --run build/growth_run_new --observations build/new_observations --associations build/association.json --observation-model build/observation_model.json --out build/growth_update_new
python -X utf8 -m tools.compound_growth probabilistic evaluate --runs build/growth_run_new --targets build/heldout_observations --plan build/evaluation_plan.json --out build/growth_evaluation_new
```

The standalone entry point `python -X utf8 -m tools.probabilistic_compound_growth` accepts the same subcommands. Omitting `--observation-model` performs measured re-anchoring without claiming a parameter posterior. Omit `--structure` if it is unavailable: event-only forecasts may still be possible with explicitly assumed apex status and event parameters.

## Inputs

### Observations and structure

`--history` is the existing `compound-observations-1` manifest or a directory containing `observations.json`. The adapter delegates to `tools.compound_growth.load_history`: confirmed persistent identities, whole observed axes, aware timestamps, stable board frames, matching hashes and separate area basis are retained. It does not convert a petiole segment into a full rachis.

`origin.json` supplies `plant_id`, `session_id`, timezone-aware `observed_at`, `numeric_tolerance` and `projection_tolerance_mm`. All existing origin geometry is copied exactly. Earlier observations initialize baselines; later records cannot condition the origin.

`structure.json` supplies matching `plant_id`, `observed_at`, `frame_id`, `coordinate_frame="board_mm"`, and:

- `parent_axis_points: {path, sha256}`: CSV columns `parent_stem_id,point_id,order,x_mm,y_mm,z_mm,source_ref,review_status`.
- `attachments: {path, sha256}`: CSV columns `compound_leaf_id,parent_stem_id,segment_start_id,segment_end_id,fraction,material_node_id,predecessor_id,adjacency_status,projection_residual_mm,review_ref`. Optional reviewed `order_status,order_index` may be added. Fraction is in `[0,1]`.
- `axes`: entries with `parent_stem_id`, `apex_status` (`active`, `stopped`, `unknown`), `apex_point_id`, `apex_review`, and `reference_vector` in board coordinates. The reference vector establishes local azimuth; the stem tangent alone cannot do so.
- An observed lateral axis optionally has `base_attachment: {parent_stem_id,segment_index,fraction,offset_mm,review_ref}`. Its base must reproduce the measured polyline start and the axis graph must be acyclic.

Polyline points must have `review_status="confirmed"`. Source attachment offsets are preserved, not projected away. A material segment ID is `start_point_id:end_point_id`. Axis IDs cannot contain `/`, which is reserved for trajectory-local future IDs. Existing measured bends remain unchanged at initialization; segment directions remain fixed under the proposed elongation model.

### Model and parameter particles

`model.json` uses schema `probabilistic-compound-1` and model `stochastic-grammar-proposal-1`. Required fields:

| Field | Contract |
| --- | --- |
| `horizon_days`, `topology_scope` | `30`, `provided_axes` |
| `sampler` | `joint_gaussian`; `flow_matching` returns unavailable |
| `leaf_retention_assumption` | Explicit `no_loss_over_horizon`; no mortality/senescence model |
| `clock` | Calendar, supplied piecewise multipliers, or one explicit response below |
| `parameter_particles` | Weighted list of explicit parameter sets; weights sum to one |
| `computation` | Integer `seed`, positive `sample_count`, `max_events_per_axis`, `numeric_tolerances` with positive `absolute`, unique `output_days` in `[0,30]`. Scalar `numeric_tolerance` is also accepted as a compatibility alias; conflicting values fail. |

Each parameter particle contains:

- `id`, `weight`, `source_kind`, `source_ref`. Allowed evidence kinds: measured, user_assumed, literature_informed, fitted. Fitted runs additionally need model-level `fitting_plant_ids` for evaluation.
- `coordinates`: ordered `{name,unit,transform,...}` entries. Supported transforms are `identity`, `exp` with positive dimensional `reference`, `bounded` with `lower/upper`, and `elevation` mapping to `(-pi/2,pi/2)`. Do not mix coordinate/covariance order.
- `plant_covariance`: square covariance in the transformed coordinates. A shared plant draw couples organs. Exact zeros are an explicit deterministic assumption.
- `families`: named conditional distributions, each with `mean`, `features`, `coefficients`, `standardization`, scalar `rho` with `abs(rho)<1`, `initial_covariance`, `innovation_covariance`, and optional `constants` mapping quantity names to `{value,unit}`. `coefficients` has one row per coordinate and one column per feature; intercept-only families use empty rows. Constants cannot duplicate transformed coordinates.
- `existing_blocks`: observed compound ID to family name. Existing leaves have their own remaining-growth family, not a newborn prior.
- `axes`: parent ID to `residual_family`, `inter_event_family`, `stop_probability` OR `stop_logit`, `segment_families` keyed by material segment ID, `direction_reference` (`absolute` or `predecessor`), and optional confirmed `predecessor_id`, `area_basis_id`, `assumed_apex_status`.

Conditional features include measured axis length, side extents, confirmed predecessor spacing/order, sine/cosine of local azimuth and declared environment values. Each used continuous feature needs a supplied center and positive scale. Missing features require their explicit `<name>_missing` feature/coefficient; otherwise that conditional calculation is unavailable. No covariance or feature coefficient is guessed.

`stop_logit` contains `intercept`, a `coefficients` mapping from supported feature to coefficient, and `standardization`. Stop probability is logistic of the standardized linear predictor. Missing stop features are unavailable, not zeros.

Supported quantity names:

| Quantities | Unit / meaning |
| --- | --- |
| `wait_dev_days` | Positive development-day residual/inter-event wait |
| `birth_axis_length_mm`, `birth_left_extent_mm`, `birth_right_extent_mm` | Initial block descriptors; full axis length is positive |
| `azimuth_rad`, `elevation_rad` | Parent-local initial direction; azimuth is wrapped through vectors |
| `D_length_mm`, `k_length` | Remaining axis increment, inverse-development-day rate |
| `left_target_mm`, `right_target_mm`, `k_width` | Absolute extent targets at reference DLI (mm), inverse-development-day rate |
| `rotation_x_rad`, `rotation_y_rad`, `rotation_z_rad`, `k_rotation` | Local rotation vector, inverse-development-day rate; explicit zeros disable rotation |
| `D_segment_mm`, `k_segment` | Remaining material-segment extension, inverse-development-day rate |
| `D_area_cm2`, `k_area`, `birth_area_cm2` | Optional independent area trajectory; requires comparable area basis |

The transition is `initial + remaining*(1-exp(-rate*development_age))`; widths approach the specified target and may decrease. Direction follows a smooth local rotation. At appearance the previous terminal keeps growing and a new zero-length terminal is added. Birth/segment/continuous values are drawn jointly in the event family. This preserves event/size correlations without independent daily resampling.

### Environment and external light

Optional `environment_scenario` contains `id`, `values`, and `response_ref=null`. Values use existing names: `temperature_c` (deg C), `relative_humidity_pct` (%), `ppfd_umol_m2_s` (umol/m2/s), `photoperiod_h` (h/day), `ec_ms_cm` (mS/cm), `ph` (dimensionless), `co2_ppm` (ppm).

`clock.kind="calendar"` uses elapsed days. `piecewise_constant` uses contiguous `[start_day,end_day]` intervals covering day 0 through 30, each with a nonnegative `multiplier`, plus `source_kind/source_ref`. This is a user-supplied development schedule, not inferred environmental physiology.

`piecewise_linear_response` evaluates one explicit input-response table. Required fields: `source_kind`, `source_ref`, `input_metric`, `input_unit`, `target="development_clock"`, `equation_version="piecewise_linear-1"`, `applicability`, increasing `knots` of `{value,multiplier}`, and contiguous intervals with `{start_day,end_day,input_value}`. No extrapolation or automatic product of responses is allowed. Values are declared future scenarios. Zero multipliers pause development; event inversion skips those intervals.

Optional `light_features` contain `id`, plant/compound IDs, aware `observed_at`, `area_basis_id`, `metric`, `unit`, `backend`, `source_ref`, `value`. A light response additionally needs `light_feature_id` and `fixed_over_horizon=true`; its metric/unit and fixed interval values must match that feature. Later measured light cannot condition an earlier forecast; a future scenario must be explicitly marked `state_source="scenario"`. Incident PPFD and absorbed flux remain distinct. No future shading is recomputed. Without an enabled response, the model reports coupling unavailable and retains input metadata.

## Output and availability

`events.csv`, `block_states.csv`, `trajectories.csv`, `trajectory_parameters.json`, `summary.csv`, `origin.json`, `model.json` and `manifest.json` are emitted. Update/evaluation runs add their corresponding JSON/CSV files. `trajectory_parameters.json` preserves all measured axis points, decoder parameters and joint sample identities. The CSV state table summarizes geometry without replacing the measured shape.

Missing JSON is null and missing CSV is an empty cell. Zero remains zero. Stopping uses a stopped event and null time, not infinity. Per-component reasons live in the bank/decoded state and summary. An event-count forecast may remain eligible when XYZ is unavailable. Invalid input raises `StudyError`; unavailable conditional features and failed numerical/support samples are distinguished. Invalid/rejected sample weights are retained and summary denominators report the available mass.

Set explicit summary quantiles in `summary_config.json`, for example `{"quantiles":[0.1,0.5,0.9]}`. Quantiles are computational reporting levels, not calibrated biological confidence. Summaries retain occurrence/count probabilities, conditional length/extent/area/XYZ quantiles and directional concentration. Samples preserve multimodality; no mean plant is fabricated.

Future blocks are always optical-ineligible. No exported envelope becomes tissue, opacity, transmittance, an optical receiver or training ground truth. All outputs keep `validated_growth=false` and `suitable_for_ppfd=false`.

## Observation updates

Association JSON contains `observed_at` and `records`, each with `source_ref` and status:

- `confirmed`: `observed_id`, `predicted_id`.
- `ambiguous`: `observed_id`, `candidates` of `{predicted_id,probability}`. Missing probabilities remain unresolved; nearest-neighbor matches are never forced.
- `missed` / `occluded`: prior `predicted_id`; no death or negative detection is inferred.
- `unmatched`: measured `observed_id`; retained as a new measured anchor, not a successful prediction.

Observed existing IDs or future rank keys such as `stem/new_1` can identify predicted blocks across samples. A trajectory-specific ID identifies only that trajectory.

The optional observation model has `source_kind/source_ref`, `fields`, matching `units`, positive-definite `covariance`, and `numeric_tolerance`. Fields may be `rachis_arc_length_mm`, side extents, `supported_area_cm2`, `attachment_x/y/z_mm`, or `direction_tangent_1/2_rad`. Direction likelihoods use an observed tangent chart and reject antipodal ambiguity. Event-only likelihoods use empty fields/covariance. Optional `events` include a parent, event index, confirmed visibility, and either `kind="interval"` with last-absent/first-present days, or `kind="right_censored"` with `through_day`. No evidence may extend beyond the update time.

Reweight in log space; export posterior candidate probabilities, parameter-particle masses and effective sample size. All-zero/nonfinite support returns `update_incompatible`, never uniform replacement. Without a justified likelihood, only measured re-anchoring/discrepancies are returned. Prior files remain unchanged.

The continuation bank covers the **remaining original forecast horizon**, explicitly `available_horizon_days`. It does not silently manufacture another 30 days of events. Remaining increments/rotations are decayed before re-anchoring, avoiding double-counted growth. Compound observations do not measure a new stem: `next_origin` marks new parent geometry unavailable while the continuation retains its predicted parent trajectories. For a fresh 30-day run use new-origin geometry/parameter assumptions and `sample_forecast`; a continuation-only config is rejected as a fresh forecast input.

## Evaluation and verification

Evaluation plans require disjoint `train_plant_ids` / `test_plant_ids`, `split_provenance`, `interval_quantiles` and explicit `targets`. Each target has `plant_id`, `forecast_origin`, `target_at`, and:

- Geometry: `compound_leaf_id`, `association_status="confirmed"`, optional `predicted_id`.
- Count: `kind="count"`, `visibility="confirmed"`, observed `count` on provided axes.
- Timing: `kind="event"`, confirmed visibility, parent/event index and interval or right-censor bounds.

Optional positive `energy_scales` for attachment/direction define fixed normalized vector scores. Do not select scales using test errors. Report scalar CRPS, count/occurrence scores, interval timing loss, representative geometric errors, coverage/width and optional energy loss. Missing targets/matches are reported with denominators, not dropped as successes. Existing-leaf persistence/recent-change baselines reuse the original module. For a context-free new-leaf comparator, submit its frozen configured run alongside the conditional run; no new biological prior is invented by evaluation.

Only actual target times are scored; 7/14/21/30 days require independent targets at those horizons. Zero event probability produces an explicit infinite-loss reason with null JSON value. Software/synthetic checks are distinct from prospective biological accuracy.

```powershell
python -X utf8 -m pytest tools/tests/test_probabilistic_compound_growth.py tools/tests/test_compound_growth.py tools/tests/test_monthly_growth.py -q
```

Known biological dependencies: eligible longitudinal measured states/parent geometry, appearance/visibility intervals, parameter/response evidence, observation-error models and independent acceptance targets. Flow Matching, automatic fitting, unobserved lateral-axis initiation, senescence, carbon allocation, tissue reconstruction and light execution are excluded.

## Adopted D8–D10 extensions (2026-10-03; verified 2026-10-04)

These are opt-in additions to `probabilistic-compound-1`. The user resolved the
handoff's byte-compatibility conflict: old calculated values/random streams remain
unchanged; new audit fields, event columns and explicit unavailable summaries are
added. Do not compare whole-file hashes across these output-schema additions.

### D8: newborn beta growth

Set `growth_curve="determinate_beta"` on a newborn event family (residual or
inter-event). Existing block and existing material-segment bindings refuse this
curve. The exponential decoder remains the default. Each optional trait has its
own target and time coordinates:

| Prefix | Target coordinate | Unit |
|---|---|---|
| `length` | `length_x_max_mm` | mm |
| `left`, `right` | `left_x_max_mm`, `right_x_max_mm` | mm |
| `segment` | `segment_x_max_mm` | mm |
| `area` | `area_x_max_cm2` | cm2; still needs an area basis |

For each supplied target, also supply `<prefix>_a_e_dev_days` and exactly one of
`<prefix>_a_m_dev_days` or `<prefix>_a_m_over_a_e`. Times are development days;
the ratio is dimensionless. These use the existing ordered particle coordinates,
family mean/covariance/feature arrays, or explicit family constants with units.
Stochastic targets require `exp`; a stochastic ratio requires `bounded` with
lower=0 and upper=1. Direct peak/end times are checked for strict ordering per
draw; invalid draws remain failed samples, without clipping or redraws.

`beta_shape(alpha,a_m,a_e)` follows the handoff's equation, saturating at one.
The decoded value is `birth + (target-birth)*shape`. Existing birth-length,
extent, area and zero-length terminal-segment semantics remain intact. Optional
missing targets stay unavailable. A reference target below birth remains an invalid
sample. A valid reference target falling below birth only after DLI scaling makes
that trait unavailable with `dli_target_below_birth`; the sample remains in the
ensemble. Direction rotation and event waiting laws do not change. Beta is
hard-refused for existing blocks and existing segments, whose remaining growth
continues to use the exponential law.

When a known-age beta organ is re-anchored during a bounded observation update,
the continuation retains its original developmental age and remaining beta-shape
increment (`beta_birth_values`, `beta_anchor_age`). It neither restarts the curve
nor extrapolates another 30 days. Observed geometry becomes the new anchor.
This is a continuation of an originally newborn organ, not a conversion of
age-unknown origin organs to beta. It preserves the remaining increment, so an
observed anchor displacement also shifts the future endpoint by that displacement.
Optional observation weights are described below; the default weight 1 preserves this behavior.

### D9: explicit temperature and DLI entry

`environment_profile="d9"` activates the restricted profile. Omit it to retain
legacy responses; legacy responses are not represented as D9 compliance.

`normalized_temperature_clock` builds the existing piecewise-linear clock from
explicit keyword arguments `t_base_c`, `t_ref_c`, `m_max`, `upper_knot_c`,
`intervals`, `source_kind`, `source_ref`, `applicability`. It implements
`clip((T-T_base)/(T_ref-T_base),0,m_max)` over the supplied knots, requires
`T_base < T_ref <= upper_knot` and `m_max >= 1`, and records `normalization`.
By default the lower knot is T_base. Optional `lower_knot_c` must be explicitly
declared below T_base and adds a zero-multiplier knot; temperatures between it and
T_base pause development. Inputs outside the declared knot domain are refused.
No extrapolation or default crop temperature is supplied.
Intervals cover the horizon and temperatures are degrees C. D9 checks the actual
knots against that declaration. Calendar time is also allowed.

Optional top-level `light_response` requires:

| Field | Meaning |
|---|---|
| `kind` | `size_target_dli` |
| `value`, `unit` | Fixed daily dose, `mol/m2/day` |
| `light_basis` | `incident`; absorbed and tissue-averaged DLI are refused |
| `basis_id` | Identity of one reference position/plane, disjoint from supplied tissue `area_basis_id` / `area_basis_ids` provenance |
| `scope` | `whole_plant`; heterogeneous per-organ inputs are not implemented |
| `fixed_over_horizon` | `true` |
| `center`, `scale` | Same DLI units; scale strictly positive |
| `reference` | `position_mm[3]`, unit `normal_unit_xyz[3]`, `frame_id`, `coordinate_frame`, `source_kind`, `source_ref` |
| `local_day` | Aware `start_at`/`end_at`, IANA `timezone`, `coverage="complete"`, `source_kind`, `source_ref` |
| `applicability_interval` | Inclusive `min`/`max`, `unit="mol/m2/day"`, `source_kind`, `source_ref`, `applicability_source_ref`; outside values are unavailable |
| `time_basis` | `complete_local_day` |
| `coefficients.exponential` | `coefficient_id`, `role="remaining_increment"`, dimensionless `c_DLI`, `source_kind`, `source_ref`, `applicability_source_ref` |
| `coefficients.determinate_beta` | Separate `coefficient_id`, `role="absolute_potential_maximum"`, dimensionless `c_DLI`, `source_kind`, `source_ref`, `applicability_source_ref` |
| `source_kind`, `source_ref` | Explicit response/basis assumption provenance |

The local day spans midnight to the next midnight in its declared timezone
(including 23/25-hour daylight-saving days). Its complete coverage is a supplied
evidence declaration, not a reconstruction of a PPFD history. No reference plane,
day coverage, applicability bounds or coefficient evidence is inferred. A binding
is required for every active curve family. Distinct coefficient identities are
mandatory across exponential and beta; equal numerical values are allowed.
The former shared root `c_DLI` contract is rejected and requires explicit migration.

For each curve family the factor is `exp(c_DLI*(value-center)/scale)`. It scales
remaining D for exponential lengths/areas/segments and absolute beta x_max for
newborn organs. These meanings remain distinct. `reference_size_targets` stores
unscaled values and `dli_binding` preserves curve, coefficient, role and basis
provenance in each draw. Existing widths have meaning
`absolute_extent_target_at_reference_DLI`: the station asymptote is
`w0 + factor*(target-w0)`, retaining the measured anchor. If a side target is below
the minimum of that side's observed stations, the family must provide
`narrowing_assumption={source_kind,source_ref}`. Equality or a target between the
minimum and maximum does not trigger this evidence requirement. A negative
effective station asymptote makes that side unavailable with
`dli_negative_width_target`. Rates, directions, waits and stop rules are unchanged.
If `environment_scenario.values.dli_mol_m2_day` is also supplied, it must match.

These two DLI failures retain trajectory existence, IDs and original weights.
Birth/day-zero geometry stays present; unavailable future values are null in JSON
and blank in CSV, never replaced by zero growth. Other invalid parameters still
fail normally. The per-trajectory `availability` list and per-state
`growth_unavailable` field identify affected quantities and reasons. For DLI runs,
every summary row adds `ensemble_weight`, `available_fraction_of_ensemble`,
`unavailable_weight` and `unavailable_reasons` (reason code, weight and probability
of the original ensemble). Conditional quantiles remain available-only and must
be interpreted with this coverage; no trajectories are dropped or renormalized
because a curve is unavailable. Reason lists identify the specified DLI failures;
coverage can also be reduced by nonappearance or other existing unavailable states.

D9 refuses environment/light family features and stop features (including
missingness indicators), non-temperature clock inputs, unknown fitted feature
aliases, and legacy PPFD/photoperiod or CO2/RH/EC/pH responses. Unknown aliases
are never silently mapped to authorized drivers. Temperature is clock-only;
DLI has the single explicit size-response entry. Cultivation values with no
response remain metadata. Supplying `size_target_dli` also rejects competing
light family/stop/clock entry paths outside D9, avoiding hidden double coupling.

`environment_audit` inspects the whole frozen config: clock, family coefficient
paths, stop coefficients, light response and frozen calibration `applied_features`.
`p3_environment_paths` is a list of `{path,metric,target}` records. Evaluations
add `run_id` to distinguish input runs. Both run JSON and new manifests expose
`p3_light_coupling` (`none` or `size_target_dli`) and derived `environment_used`,
`light_used`, `environment_audit_status`. `none` means the new DLI size response
is inactive; legacy light effects must still be checked in paths/flags. Old
calibration packs without response provenance report an unknown dependency and
audit status unavailable, and cannot pass D9. P4 remains entirely disconnected.

For calendar-fitted packs, see `GROWTH_CALIBRATION.md`: a normalized temperature
clock requires an explicit fixed-setpoint reference in the hashed fit plan.
A period mean of a fluctuating calibration history is not sufficient.

### D10: persistent node budget and event observations

The reviewed main-axis entry in `structure.json` supplies `observed_node_count`
(nonnegative integer) and `node_count_source_ref`. This is the observed terminal
node rank/count along that axis, not the number of currently visible blocks or
the number of sampled polyline points. Missing count gives unavailable.

An axis parameter may declare `node_budget={pmf:[{n,p},...],source_kind,source_ref}`.
Ranks are unique nonnegative integers; probabilities sum to one. The sampler
removes mass below the observed count, renormalizes, then draws once using a
separate stable stream. Empty mass gives unavailable. Budget and free
`stop_probability`/`stop_logit` are mutually exclusive. `n_max_drawn` is a map
from axis ID to count in each trajectory JSON; the CSV cell encodes this map as
JSON (blank when inactive). No new axes or sympodial continuation are created.

Optional axis `truss_rule` supplies `first_truss_rank_pmf` (same `{n,p}` records),
positive integer `interval_leaves`, `truss_observable`, `source_kind`, `source_ref`. Undeclared observable or missing rule evidence makes only the truss rule unavailable. First truss rank
is drawn once per trajectory/axis. Truss events occur when a new leaf reaches a
matching rank. Terminal occurs when rank reaches N_max, at the same time as that
leaf; N_max equal to origin count gives terminal at day zero. Their geometry and
block/material IDs are null; optical flags are false. No CompoundLeaf is created
for either event. Without a rule, truss summaries are unavailable.

Events carry `event_kind=leaf|truss|terminal` and optional `node_rank`. Legacy
events default to leaf. `event_index` remains the original appearance-sequence
index; use kind plus node rank to disambiguate truss/terminal from leaf events.
If any positive-weight trajectory has terminated by a query time, the whole-plant
count is unavailable with `sympodial_continuation_not_modeled`, and
`post_termination_scope="unavailable"`. The supported main-axis count distribution
is still reported as `main_axis_new_leaf_count`, separately from whole-plant growth.

An observation bundle can reference an additional top-level
`event_observations={path,sha256}` CSV, with columns
`plant_id,parent_stem_id,event_kind,node_rank,observed_at,visibility,source_ref,truss_observable`.
Timestamps are timezone-aware; visibility is confirmed, occluded or missed.
Only confirmed events constrain particles. Origin events constrain budget/rule
support; later events are consumed by explicit event-only or joint observation
models. A confirmed observed timestamp means present by that time, not an exact
emergence time. Explicit interval/right-censor likelihoods remain supported.
Models may also supply `events` with event_kind/node_rank instead of event_index.
Updates change weights without resampling N_max, truss ranks or trajectories.
No observation model means no claimed parameter posterior.

`update_forecast.conditioning_diagnostics` reports ordered stages: `prior_ess`,
`after_geometry_ess`, then `after_geometry_then_events_ess`. The signed differences
`geometry_ess_loss` and `event_stage_ess_loss` are order-dependent diagnostics,
not an order-independent causal decomposition; either can be negative. Evidence
is applied once in the existing log-weight calculation. Missing likelihoods give
unavailable stage values and no weight update. All-zero support remains
`update_incompatible` (ESS diagnostic 0, no replacement distribution). Geometry
uses the supplied within-organ covariance and conditional independence across
organs; cross-organ measurement correlation is not modeled. Both diagnostics and
export manifests disclose that limitation. No resampling or new fitting occurs.

Evaluation event targets accept `event_kind`, `node_rank`, parent ID, confirmed
visibility and `target_at` (or `observed_at`). Use interval bounds where available;
otherwise the target is presence by that time. Whole-plant count scoring after
termination is unavailable; explicit `scope="main_axis"` and parent ID allow the
supported main-axis count score.

Optional `max_leaf_age_dev_days` plus `leaf_age_evidence={source_kind,source_ref}`
adds `retention_assumption_exceeded=true` only after a known-age predicted leaf
exceeds that limit. The age remains known through continuations. Age-unknown
existing leaves are not assigned age zero as biological truth. No abscission.

Templates include blank `d8_d10_parameters.json` and `event_observations.csv`.
The former is a field reference, not an executable model or automatic merge.
Place filled fields at the locations above. No literature coefficient is a default.

```powershell
python -X utf8 -m pytest tools/tests/test_p3_growth_decisions.py tools/tests/test_probabilistic_compound_growth.py tools/tests/test_growth_calibration.py tools/tests/test_compound_growth.py -q
```


## V2 observation options, D19 and D21

No new crop coefficient or fitted covariance is supplied. New scientific missing
inputs yield structured unavailable reasons; malformed numeric arrays, invalid
weights, hash mismatches and conflicting declarations remain input errors.
`validate_model_config` and `sample_forecast` return unavailable contracts;
low-level `_validate_d9` raises `ScienceUnavailable` carrying `reason_code` and
`details`. This is caught by the public validation API. No broad exception
suppression is added. Blank template fields are not observations.

### Canonical DLI and provenance

Import `DLI_UNIT` from `tools.leaf_light.common`; its sole value is `mol/m2/day`.
Legacy `mol/m2/d` returns `legacy_dli_unit_spelling` with the complete
missing/different-field list. Missing scientific declarations return
`legacy_light_response_underspecified`. Neither spelling nor numeric values are
auto-converted; regenerate a new explicit config and retain old frozen hashes.

The canonical interval is `light_response.applicability_interval`.
`light_response.dli_applicability_interval` or top-level
`dli_applicability_interval` maps to this field on a copied config. Conflicting
duplicates are malformed; equal duplicates are accepted. No bounds are inferred.
`applicability_source_ref` must pass unchanged from P2's reference-position
record to its reference-DLI record and the P3 interval, and equal the explicit
`applicability_source_ref` on each curve coefficient. This ties the domain to the
selected P3 coefficient evidence, not an arbitrary sensor setup. The field may
carry an evidence identifier or a structured source reference; equality is exact.
Structured references require `path`, `sha256`, and `json_pointer`; P3 independently
checks the hash and selected domain min/max/unit. A sensor metadata object cannot
stand in for that domain. Evidence identifiers still denote explicitly declared
assumptions. P3 does not authenticate the scientific truth of a source claim.

Optional `p2_tissue_manifest` is an embedded manifest or `{path,sha256}` file
reference. P3 reads it independently and rejects reference `basis_id` collisions
with any nested `area_basis_id` / `area_basis_ids`, regardless of a producer's
validity claim. Hash mismatch is malformed. No tissue averaging, absorbed-light
conversion or multi-day-to-single-day fabrication is performed.

### Weighted observation anchors (D14a)

Place optional `reanchor_weight` in association JSON; default 1 retains the exact
previous measured-anchor path. A value 0 adds no observed displacement; 0.25 adds
one quarter. Applies to both exponential and beta continuations via the existing
`_remaining`; beta retains its remaining increment, not its old absolute endpoint.

Alternatively supply association `reanchor_covariance` with
`mode="diagonal_variance"`, `cross_covariance=null`, and `traits` keyed by
`rachis_arc_length_mm`, `left_extent_mm`, `right_extent_mm`,
`supported_area_cm2`, `attachment_xyz_mm` or `direction_unit_xyz`. A record is:

```json
{"variance_state": null, "variance_measurement": null, "unit": "mm^2",
 "identifiable": null, "source_kind": null, "source_ref": null}
```

Fill compatible variance evidence explicitly. Units are `mm^2`, `cm2^2` or
`rad^2` according to the trait. For vector/station profiles this is a declared
common marginal variance for each component, not a full covariance matrix.
Only opt-in mode calculates omega = variance_state / (variance_state +
variance_measurement). Missing/nonfinite/negative/non-identifiable variances,
wrong units, zero denominator or supplied cross-covariance give trait-specific
unavailability; no weight is fit from ensemble spread or replaced with certainty.
Manual and covariance modes are mutually exclusive.

Intermediate anchors reuse the existing predicted-shape dilation and attachment
translation. Extent correction requires matching station arrays. Intermediate
rotation/shape interpolation has no adopted law: retain the predicted direction
and report `reanchor_direction_correction_unsupported`. Missing shape support is
explicit; a weighted anchor is labelled `weighted_observation_anchor`, not a new
measurement. Full manual weight 1 preserves measured geometry exactly.

`update.json` contains `reanchor_corrections` (trajectory, organ, quantity, unit,
omega, observed displacement, applied displacement, reason, update ID) and
`reanchor_cumulative`. The latter is carried in the bank and stores
`cumulative_absolute_displacement` separately per trajectory/organ/trait/component
and unit. Each update ID contributes once. Reprocessing a previous bank is
reproducible; trying to apply the same timestamp to the already-updated bank is
refused. No mm/cm2/rad values or distinct organ/trajectory corrections are summed.

### Observation-only posture (D14b)

`observation_model.posture_offset` is absent/null/disabled by default. Enabled
records require `reference_phase`, `source_kind`, `source_ref`, `observed_at`,
`time_reference="declared_capture_phase"`, and `offsets` keyed by phase. Each
phase record has `unit="rad"`, `source_ref`, and `values` keyed by existing
`direction_tangent_1_rad` / `direction_tangent_2_rad` likelihood coordinates.
These refer to the existing observed-direction tangent chart, not absolute
azimuth or nominal lamp duration. Reference-phase offsets must all be zero.
Association `capture_phase` (or an exactly matching Day-1 record) selects a phase;
no phase is inferred from the photoperiod duration.

The existing state-minus-observation residual gains the declared phase offset,
then wraps with atan2(sin,cos). Disabled/zero offsets preserve the likelihood.
Missing phase/evidence, time mismatch or nonzero reference offset is structured
unavailability and disables parameter reweighting. `posture_diagnostics` records
that outcome. The posture term changes only likelihood, never structural state,
future geometry, growth coefficients or the separate reanchoring displacement.

### Event meaning and ordered update diagnostics

Each truss rule and confirmed truss evidence must explicitly declare matching
`truss_observable`. New Day-1 protocol records use `visible_bud`; it is not silently
assigned to old records. Missing meaning/rule evidence makes truss calculations
unavailable while retaining leaf, node-budget, terminal and trajectory behavior.
`first_open_flower` cannot condition a `visible_bud` rule. Event and truss summary
outputs carry the label. Mixed observable summaries are unavailable.

The event stage is `hard_admissibility`: geometry likelihood times a Boolean
event indicator, once each. `n_particles_rejected_by_events` counts unique valid
positive-prior-weight trajectories rejected by confirmed events;
`event_rejected_prior_mass` sums their original weights. Count and mass are
separate. Fixed likelihood multiplication commutes before normalization;
sequential ESS changes remain order-dependent. No reanchoring occurs between
these likelihood stages. All-zero support is still incompatible, never uniform.

### Summary support (P3-a)

Each row reports sums of the original bank weights (normalized at forecast/update
creation): `existence_mass`, `computable_mass`, `available_mass` (their
intersection), and `ensemble_weight`. `not_present_mass`, `existence_unknown_mass` and
`computational_unavailable_mass` distinguish known biological scope/nonappearance,
unknown existence in failed draws, and
computational failure. Reason mass and source trajectory IDs remain traceable in
the bank; `computational_reasons` lists failure mass by reason.

For a block trait, existence means the block has appeared; computability means
its declared trait can be evaluated independently of whether it has appeared yet.
For absent blocks in a complete event model, biological absence itself is not a
failed parameter draw. For plant counts, whole-plant continuation after main-axis
termination is outside biological scope; existing leaves retain their existence.
Axis counts retain supported main-axis scope. Truss computability additionally
requires a declared rule/observable. Conditional quantiles use available_mass;
occurrence probabilities include both present and absent computable trials, so
their trial mass is not the present-only intersection. Legacy `available_weight`
is retained for compatibility. A null whole-plant count after terminal is not
zero growth; no unsupported sympodial continuation is generated.

### Read-only Day-1 import (D21)

```powershell
python -X utf8 -m tools.growth_day1 --records <day1_protocol.csv> --out build/day1_import_new
```

Consumes exactly P1's eleven columns, preserving aware times, explicit phase,
source SHA256 and CSV row identity. Header-only templates contain no observation.
Zero counts remain zero; blanks remain null. Missing time, counting-rule source
or observable is recorded as unavailable. Malformed timestamps/counts/dates are
refused. early_photoperiod means 2 h after actual lights-on; late_photoperiod means
2 h before actual lights-off. Dates never establish existing organ ages.

An observation manifest may reference `day1_protocol={path,sha256}`. The P3 history
loader attaches recorded phase only to exact plant/session/time matches. An
origin config's explicit `day1_axis_id` maps a matching reviewed node count onto
an existing axis for the unchanged N_max lower truncation. Conflicting counts are
refused. Visible-bud counts are retained as count evidence and are not invented
node ranks/emergence timestamps. Historical records and human files are never
rewritten. No import schedules or experimental acquisition are started.
