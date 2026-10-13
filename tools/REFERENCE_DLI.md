# Reference-position incident DLI

Measured producer, standalone independent consumer, hashed package attachment, reviewed D20 faces and a bounded P3 representation mapper are implemented. Final delivery verification is tracked in the execution report; this guide alone is not completion evidence.

`python -X utf8 -m tools.reference_dli --help` exposes:

```text
templates --out <fresh build directory>
compute --position <json> --schedule <json> --readings <csv> --survey <csv> --route logged|spot_schedule --out <fresh build directory>
simulate --position <json> --schedule <json> --scene <json> --out <fresh build directory>
```

Optional `--tissue-manifest <json>` checks every supplied nested `area_basis_id` / `area_basis_ids` against the reference basis. The later package consumer must repeat this against the actual tissue package. Output directories must be new descendants of project `build/`. Existing files and hashes are not repaired or overwritten.

`python -X utf8 -m tools.reference_dli_consumer <reference_dli.json>` validates the standalone output. It checks hashes, CSV/JSON consistency and independently reconstructs doses from the original readings. It shares input/evidence policy and existing scheduling, but never calls the producer or its day integrator. Arithmetic comparisons use absolute tolerance 1e-12 and relative tolerance 1e-12; these are software comparisons, not sensor accuracy or biological tolerances.

## Physical quantities and files

PPFD readings are incident `umol/m2/s`; DLI uses the shared `DLI_UNIT = 'mol/m2/day'`. `mol/m2/d` is refused by name, not rescaled. Lux or W/m2 readings are refused. This CLI does not perform spectral conversion; any separately converted photon dataset must retain its source/unit/spectrum evidence. It never derives PPF from lumens/CCT and never uses tissue area or absorptance.

`reference_position.json` declares a horizontal upward sensor, position in mm, named frame/coordinate frame and height basis. All reference/evidence identity, dates, sensor leveling and cosine response must be explicit. Evidence uses `{path, sha256}`, resolved relative to this JSON. Geometry does not prove that a real sensor was levelled. `cosine_corrected=false` and `unknown` remain distinct and add `cosine_response_uncorrected` to every affected row; no numerical correction is applied.

`reference_readings.csv` keeps the handoff columns. `interval_mean` additionally requires `support_start_at` and `support_end_at`. Aware ISO timestamps are mandatory. Empty/unavailable PPFD is missing; negative/nonfinite values, duplicate IDs/times and overlapping support are errors. Survey readings can share timestamps at distinct positions. Reference readings cannot, because reconstruction would be ambiguous.

`schedule.json` uses the existing fixture HH:MM windows and output fractions, with `timezone`, `provenance`, `fixed_optics_beam_spectrum=true`, and an explicit `dates` list covering the requested dates. Actual fixture IDs are required; `all` is not another lamp. `max_schedule_minutes` bounds the shared UTC minute scan. `tools/light_time.py` contains the extracted existing schedule/dose arithmetic; the bridge retains its previous function names through imports.

Real templates preserve three lamps, 16 h/day and output fraction 1.0 as operating metadata. Position, basis, clocks, domain, readings and biological evidence remain blank. The template normal only declares a plane; it is not an observed orientation. The 06:00–22:00 times in synthetic fixtures are never promoted to the real schedule.

## Explicit support and selection policy

- `dates` selects local days; no host date or meter-arrival estimate is used. `dst_policy` is `utc_elapsed` (actual 23/25-hour days) or `reject_transitions`. Missing policy is unavailable.
- `logger_sample_semantics=instantaneous` requires `max_gap_seconds`. Adjacent valid samples reconstruct a trapezoid. At one schedule transition they instead use explicit `transition_policy=hold_observed_endpoint_on_each_side` plus hashed `transition_source_ref`. Multiple unobserved transitions remain missing. Excluded/unknown samples are barriers; no endpoint extends to midnight.
- `logger_sample_semantics=interval_mean` integrates each explicit interval mean. A mean spanning a lamp transition is still the observed mean over its support, not two invented brightness levels. Splitting one mean across midnight requires `interval_mean_split_policy=constant_within_supported_interval` and hashed evidence; otherwise per-day distribution is unknown. Complete supported means may be integrated without known lamp clocks, but `on_duration_s` stays null.
- Spot/schedule requires `ambient_light=none`, `output_constant=true`, known dated clocks and synchronized fixture operation. `measurement_output_fraction` states the measurement basis. Target-matched readings scale by one. Full-output readings scale to a fractional target only with `dimming_response=linear_photon_output` and hashed `dimming_source_ref`. Other normalization is unavailable. Reference/schedule conflicts are refused.
- Ambient absence is `asserted_not_measured` without qualifying reference-position lights-off daytime evidence. Declare `daytime_ambient_reading_ids` and `daytime_source_ref`; each output day retains its own evidence. Nonzero accepted lights-off observations contradict declared absence and prevent an available input. Sparse spots remain schedule-based estimates, not continuous logging.

## Survey-derived tolerance and association

`position_tolerance` explicitly declares `method=affine_horizontal_survey`, `allowable_dli_error_mol_m2_day`, `survey_plane_tolerance_mm`, `max_fit_residual_umol_m2_s`, `source_ref` and `temporal_transfer_source_ref`. There is no default scientific tolerance. At least three noncollinear, identified, lights-on survey positions are needed. The fitted local plane must meet the declared residual tolerance. This is a local survey gradient, not a lamp PPF calibration or transport model.

The result records gradient in PPFD/mm, its DLI/mm equivalent, survey IDs, convex support hull and derived allowed distance `allowable_DLI_error / gradient_DLI_per_mm`. `gradient_exposure_basis` explicitly chooses `scheduled_on_duration`, or for logged data `full_elapsed_day`, under the supplied temporal-transfer evidence. Survey points never enter the reference mean. Flat/unsupported gradients cannot produce an infinite radius. Both the reference and accepted readings must remain inside the surveyed region and its declared plane tolerance.

`plant_association` requires `plant_instance_ids`, hashed `association_evidence`, and `uniformity_basis` with hashed `source_ref`. Multiple plants additionally need each `positions_mm` and `max_dli_difference_mol_m2_day`. All locations must be survey-supported and within that uniformity tolerance; a failing plant is not silently dropped.

## Domain, reduction and missingness

`applicability_source_ref` points to a hashed P3 coefficient-pack domain JSON and includes a `json_pointer` to its `{min,max,unit}` object (empty pointer selects the root). Supplied `applicability_interval_mol_m2_day` must match exactly. Sensor setup cannot invent these bounds.

`value_rule` is explicit: `mean_of_complete_days`, `single_representative_day` with `representative_date`, or `declared_scenario` with `scenario_value` and hashed scenario JSON containing the same value/unit. Scenario provenance remains distinct. Every contributing date is retained; incomplete selected days do not become a favorable subset. `fixed_horizon_tolerance` requires `spread_metric=max_minus_min`, `value`, canonical unit and hashed `source_ref`. Exceeded spread yields `dli_not_constant_over_horizon`; observed constancy does not prove future constancy.

`reference_dli.csv` uses empty cells for unavailable daily numbers. Coverage and domain status are separate. Complete out-of-domain daily values and `candidate_value` remain numeric audit evidence, while the usable `value` is null and status is `out_of_applicability`. Missing prerequisites yield `unavailable`; malformed data fails. Every row carries cosine/level flags and ambient evidence status.

`reference_dli.json` retains source/code hashes, actual UTC day bounds, reference identity, selection rule, days used, domain and association. `integration_evidence.json` preserves included/excluded IDs, schedule intervals, survey derivation and reconstruction support. The consumer checks CSV and audit hashes, then checks raw-reading arithmetic even if output manifests have been rehashed.

Simulation remains readiness only. Missing scalar or provenance-wrapped PPF gives `lamp_ppf_missing`; known PPF gives `simulation_execution_deferred`. Neither point transport nor `fit_empty_rig` is executed. Native execution, growth/physiology calculations, acquisition and full-system integration are outside this task.

## Delivery evidence

Current standalone CLI runs: `build/reference_dli_20261004_05/` (spot), `_06/` (logged), `_07/` (simulation readiness). Both measured fixtures produce 11.52 mol/m2/day. Blank real templates and the Korean checklist remain in `_02/`. Earlier `_01/`, `_03/`, `_04/` are preserved historical stage outputs; do not repair their old code hashes.

The full package, two canopy-preserving splits, actual-face annotations, read-only P3 input and independent checks are under `build/light_growth_v2_20261004_02/`. Its separately declared two-fixture synthetic logged schedule produces 9.72 mol/m2/day; it is not the real three-lamp installation. All numeric columns of the five tissue/angular tables exactly match both the unannotated fresh baseline and the historical Growth Science package. Physical accuracy remains unverified.

Run `python -X utf8 build/technical_review_fixes_20261004_01/P2/verify_delivery.py` for read-only final evidence verification. JUnit, per-requirement coverage, protected/current source hashes and independent-consumer results are recorded beside it. The two execution handoffs explain scope and remaining physical inputs.

## Package and P3 boundary

Use package request `reference_dli={path,sha256}` to attach the result. The original result/CSV/integration audit are copied byte-for-byte and revalidated with the actual tissue bases. The mapping exposes a usable value only for available, supported records and their explicitly associated plant IDs. Out-of-domain/failed evidence remains attached with no usable growth value. No reference request is required for an otherwise valid tissue-only package.

`tools.reference_dli_p3.map_single_day(result_path, predeclared_model_light, evidence_kind=...)` verifies the producer result and fills quantity -> light_basis, model_scope -> scope, reference position/normal/frame, actual day bounds/timezone, and value/unit/basis fields. P3's evidence vocabulary is measured/user_assumed/literature_informed/fitted; the caller must explicitly choose that classification. The original detailed measured_logged/measured_spot_schedule route is retained as producer_source_kind. The mapper does not choose model kind, center, scale, coefficients or applicability: the predeclared domain must already match the producer's resolved hashed domain, including coefficient bindings. Equal domain aliases are retained, conflicts rejected. Synthetic tests use user_assumed and explicit synthetic model evidence.

Only single_representative_day maps to P3's current one-local-day contract. mean_of_complete_days and declared_scenario retain all producer evidence but yield a named compatibility refusal. No fake day, automatic coefficient rebinding, unit conversion, forecast or full-system integration occurs.
