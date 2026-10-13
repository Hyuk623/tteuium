# Tray solution EC-equivalent accounting

Entrypoint: `python -m tools.nutrient_reservoir --help`. Contract:
`handoff/P4_NUTRIENT_RESERVOIR_CONTRACT_2026-10-12.md` (2026-10-13 continuation).
This is independent tray bookkeeping. It preserves the old element-resolved plant
ledger and never changes native photosynthesis, carbon allocation or plant state.
`flow/`, human records and native/controller files are outside this delivery.

## Run

From the project root, use a new output folder for each invocation:

```powershell
python -m tools.nutrient_reservoir audit-records --log data/records/env_20261013/nutrient_log_20261013.csv --out build/reservoir_audit_new
python -m tools.nutrient_reservoir audit-records --log build/nutrient_records_template/nutrient_log.csv --tray-spec build/nutrient_records_template/tray_spec.csv --out build/reservoir_template_audit_new
python -m tools.nutrient_reservoir replay --request build/reservoir_continuation_20261013_01/prescribed_request.json --out build/reservoir_replay_new
python -m tools.nutrient_reservoir estimate --request build/reservoir_continuation_20261013_01/estimate_request.json --out build/reservoir_estimate_new
```

Outputs are JSON metadata and CSV tables where flat. An existing output directory
or an output outside `build/` is refused. `status=unavailable` is a successful
refusal to infer a quantity; the value is null, never zero. Invalid contradictory
inputs exit 2. Human CSVs are only read, with original rows and SHA256 retained.

The actual October 13 observations have approximate timestamps and unknown tray
identity. EC is normalized from uS/cm to mS/cm without converting TDS to elements.
No volume, event sequence, blank or initial medium pools can be recovered from
these rows. pH and nitrate-strip fields remain observations, not model inputs.
The user's typical **400 mL per tray** is approximate user-stated metadata;
it is not capacity, an event supply, endpoint measurement or medium-held water.

## Required quantities and compartments

`schema_version=tray-reservoir-1`, explicit scenario and aware interval boundaries.
Each numeric quantity has `value,unit,source_kind,source_ref`. Missing quantities
are null or unavailable. Bound-based inference additionally requires `abs_error`
in normalized units and `uncertainty_evidence={source_kind,source_ref}`.

`trays[]`: unique tray_id, has_plants, plant_ids, positive inner_length_mm,
inner_width_mm, medium_volume_L, and medium_mix. Plants cannot occur in two trays.
An independent blank has no plants. Pool geometry uses internal dimensions,
not outside tray dimensions. Depth-derived volume assumes the declared rectangular
area is appropriate for free solution; submerged displacement is not inferred.

`initial[tray_id]`: reservoir and medium solution, each with water_L and
ec_equivalent; separate stored_ec_equivalent. EC-equivalent unit is `mS/cm*L`.
It is a scalar additive proxy under an explicit assumption, not a physical element
mass or an inferred nitrogen stock. Unknown initial stores withhold replay.
`mixing_model=well_mixed_each_solution`, mixing_evidence and schedule_evidence
are mandatory. Reservoir and medium remain separate; capillary equilibration is
not automatic. The explicitly complete event list can be empty with provenance.

Events have event_id, at, tray_id, kind, source_kind/ref. `supply` adds water_L
and water_L*ec_ms_cm to the selected pool. `remove` withdraws a well-mixed aliquot;
`transfer` moves it to to_pool. `evaporate` and `plant_water` remove pure water.
`adsorb`/`release` transfer EC-equivalent between medium solution and stored stock.
`uptake` removes EC-equivalent from medium solution into a labelled prescribed
uptake ledger. No negative stores or overdraw are clipped. A late invalid event
invalidates the whole replay. There is no automatic adsorption saturation law;
declining prescribed adsorption is only a software fixture.

## Observations to inference

`estimate` requires `observations[tray_id]`, bound to the same interval, containing
start/end pool_depth_mm, pool_ec_ms_cm, medium_water_L and medium_ec_ms_cm;
supplied/removed water_L and ec_equivalent totals are explicit, including zeros.
`uncertainty_mode=absolute_bounds` is a conservative range model, not a fitted
probability distribution. Shared-error dependence may make the bounds loose.

`comparisons[planted_tray]` declares blank_tray_id, same_medium_and_supply,
exchange_scaling=medium_volume_ratio, evaporation_scale (a separate quantity),
blank_evaporation_is_upper_bound, exchange_discrepancy_bound and
evaporation_discrepancy_bound, plus provenance. No implied zero discrepancy.
The medium-volume ratio scales **net** adsorption minus release. Blank EC cannot
separately identify either transfer or the initial stored amount.

For D=V_pool*EC_pool+V_medium*EC_medium:

```
net_blank_exchange = supplied_blank - removed_blank - (D_blank_end - D_blank_start)
plant_uptake = supplied_plant - removed_plant - (D_plant_end - D_plant_start)
               - medium_volume_ratio * net_blank_exchange
```

Release makes net_blank_exchange negative. Negative planted residuals stay signed
diagnostics and uptake becomes unavailable; no exudation law or clipping follows.
Subtracting an upper-bound blank evaporation biases inferred plant water uptake
downward. A blank's no-plant uptake constraint is zero by declaration, not an
independent validation of an exchange law.

`records-estimate --log ... --tray-spec ... --request <supplement.json>` binds the
existing template to this estimator. The supplement freezes both source hashes,
selects exact endpoint CSV line numbers, and supplies uncertainty, medium states
and comparability. `pool_depth_mm_after` is the endpoint depth. The listed event
lines must cover every same-tray record at start < time <= end; initial endpoint
events are already contained in initial stock. Simultaneous supply/removal needs
separate records. Removal concentration must be explicitly supplied. Blank
fields are never inferred to mean zero. The sample supplement in the delivery
build is a complete synthetic example. Existing CSV columns are not changed.

`modelled_split` consumes a conditional tray total and complete same-interval
plant demand weights: U_i=U*d_i/sum(d). The unit/provenance of weights is explicit;
the output is always `modelled_split`, never observed. It is not an elemental
demand conversion or another carbon allocation step. Positive U with zero demand
is unavailable.

## Insert the later reviewed response

1. Fill `response_registry_template.json`: exact EC meaning/time/temperature
   convention, equations and domain, breakpoints, none/moderate/strong parameter
   records, exchange/initial-pool contract references and review provenance.
2. Supply a callable `evaluator(ec_ms_cm, scenario_id, registry)` and its exact
   `(law_id,law_version)` to `response_diagnostic(...,evaluate=True)`.
   No arbitrary code string is evaluated. Registry metadata alone does not prove
   that an evaluator implements the reviewed equation; science/code review is
   still required. A missing field returns unavailable; invalid values are refused.
3. The result is diagnostic only, bounded to [0,1]. The `none` reference remains
   disabled and returns f_nut=null/engine unchanged. No missing EC becomes 1.0.
4. The native owner must separately implement and accept proposal/pause/finalize
   and apply the factor once to gross assimilation before allocation. Until that
   actual native evidence exists, `feedback_gate(True)` always refuses. No replay
   of completed growth can claim causal coupling. No joint N/P/K law is implied.

The only example response evaluator lives in tests and is explicitly an invented
triangle for low/high input software checks. It is not a delivered crop response.
No biological parameter triple has been selected. Scenario rows stay separate.

## Transaction adapter limitations

`nutrient_reservoir_transaction.begin/finalize` uses a distinct fixture schema,
preserving the existing element-resolved transaction fixture's semantics. It
binds proposal/run/scenario/trays/plants, interval, predecessor, model, parameters,
geometry, configuration and both resource/native initial state hashes. The native
candidate is expressly fixture-only. It replays the reservoir candidate without
mutating live stocks, verifies exact response hashes and expiry, and atomically
renames one directory containing both candidates. Identical retries return the
same commit; conflicting retries fail. `stage_only=True` tests interruption just
before publication. An identical staged retry may commit before expiry; timeout
cannot publish. A torn file or leftover writer lock fails closed for inspection.

This is single-transaction persistence, not a global stock service, native resume
or crash-recovery plant engine. New transaction directories must be coordinated
by the future native owner against a single committed predecessor. No OS power
loss durability guarantee is claimed. Default-off native compatibility is
established by leaving the native path unchanged and running its regression tests.
