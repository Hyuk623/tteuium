# P2 prompt for reference DLI implementation and V2 light interface alignment

Recipient: existing P2 light-simulator chat. Date: 2026-10-04.

Read rules, LOG tail/TODO, [reference DLI channel handoff](CODEX_REFERENCE_DLI_CHANNEL_HANDOFF_2026-10-04.md), [V2 handoff](CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md), [D11-D18 decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), [ownership index](CODEX_GROWTH_PACK_V2_CHAT_PROMPTS_INDEX_2026-10-04.md), [previous P2 delivery](CODEX_P2_GROWTH_SCIENCE_EXECUTION_2026-10-04.md), current light bridge/schema/consumer and guides.

Implement the newly scoped reference-position DLI channel as well as P2's V2 consumer-guidance alignment. This revised prompt supersedes its former restriction against reference-channel implementation. Write a brief, inspect current behavior, and preserve existing tissue/angular transport results. This prompt is for implementation when submitted to the P2 chat; its preparation in the coordination chat has not executed the work.

The source handoff reports a PPFD meter expected around 2026-10-10, not an established arrival date. Reference position and actual on/off clock times are unknown. Implement and test using explicit synthetic fixtures now; real measurement fields stay blank. Do not defer software work until the meter arrives.

Also apply [technical review fixes](CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md). D19-D21 and items P2-a through P2-h override conflicting earlier wording below; implement overlapping V2/reference items once.

## Current policy

- P3: incident reference-position complete-day DLI; it is not P2 absorbed tissue flux or tissue-average DLI.
- P4 dwarf-source route: absorbed patch PPFD; before_mito exchange; only evidenced adaxial_only patches can be used. Both-face exchange is unavailable in P4.
- Coefficient measured-light-basis disagreement is an issue carried by P4 while calculation continues; it does not authorize P2 to convert or relabel light silently.
- Q2 is no longer undecided. Replace active guidance saying it is undecided with a reference to D15-D18. Preserve historical archives.

## Existing interface work to retain

1. Inspect `tools/light_growth_bridge.py::_consumer_mapping`, `build_package`, current schema conventions, `tools/light_growth_consumer.py` and `tools/LIGHT_GROWTH_BRIDGE.md`. Update stale physiology-consumer policy descriptions where present; do not modify P3/P4 files.
2. Preserve incident and absorbed light as distinct fields, with absorptance applied once. P4 consumes absorbed PPFD with its existing one-sided tissue-area basis; do not multiply absorptance again or relabel incident values as absorbed.
3. Under D20, emit required per-patch `illuminated_faces` with supported values adaxial_only, abaxial_only or both, preserving physical transport. Use actual contribution-side information plus reviewed biological face mapping. Existing two-face sums cannot be labelled adaxial_only, divided by two or clipped to pass P4. If face mapping/exposure cannot be established, retain structured unavailability and provenance rather than inventing an enum value; P4 owns the refusal. Do not add a two-sided physiological model. Aggregate exposure across simultaneously contributing fixtures so opposite faces produce both, while same-face fixtures retain normal summation. Do not infer a lit face from zero-valued or unknown contributions.
4. Keep P4's `illuminated_faces` requirement distinct from a physical reference-sensor plane. P1 owns biological surface evidence, P2 supplies supported light/exposure provenance, and P4 owns `two_sided_exchange_unavailable` enforcement.
5. Retain simultaneous-fixture summation at the same patch/time before nonlinear exchange; never sum `all` together with constituent fixtures. Preserve full-canopy context when reporting per-instance results, source IDs/hashes, raw moments and receiver-to-emitter direction convention.
6. Replace the unsupported reference-channel implementation with the scoped producer below. Packages without valid reference inputs must still report unavailable with truthful reasons; do not label an implemented-but-unpopulated channel as not implemented. Existing tissue-only packages remain valid with reference unavailability. Physical reference location, clock windows and real values must not be invented.

## Reference channel implementation

Use `tools/reference_dli.py` with the handoff CLI, or a documented equivalent subcommand of the existing bridge. Own the new module/tests and necessary P2 bridge/schema/consumer changes. Inspect and reuse `integrate_light_schedule`, existing dose/time helpers, `tools/ppfd_validation.py::python_point_ppfd`, `fit_empty_rig` and `spectral_to_photon_umol` as applicable. Do not build a second independent scheduling/integration engine. If a logged-sample adapter is required, feed its explicit interval representation to shared integration arithmetic.

| Route | source_kind | Scope now |
|---|---|---|
| A logged | measured_logged | Implement incident PPFD time-series integration for each complete local day |
| C spot times schedule | measured_spot_schedule | Implement declared spot-mean PPFD times known on-duration and output fraction under explicit assumptions |
| B simulated | simulated | Interface and audit only; missing PPF/fit returns lamp_ppf_missing. Do not run fitting, invent PPF, or implement a second ray tracer |

### Inputs and provenance

Preserve the handoff's CSV/JSON structure:

- `reference_position.json`: schema `reference-dli-1`, basis_id, frame_id, position_mm, sensor_normal, horizontal plane, height_basis, timezone, ambient_light, output_constant, output_fraction, applicability_interval_mol_m2_day and source_ref.
- `schedule.json`: existing start_hhmm/end_hhmm/output_fraction schedule with timezone.
- `reference_readings.csv`: reading_id, measured_at, ppfd_umol_m2_s, position_x_mm, position_y_mm, position_z_mm, sensor_model, sensor_serial, lights_state, notes.
- Optional `spot_survey.csv`: other positions never enter the reference DLI mean; under P2-d/P2-e it supplies local-gradient and shared-reference uniformity evidence when those claims are made.

Templates leave basis_id, position, clock times, applicability bounds and biological/source evidence null. Preserve confirmed output_fraction=1.0 and 16 h/day as separate operating metadata, without deriving clock windows. A template sensor normal [0,0,1] declares a horizontal plane in its named frame; it does not prove a real measurement position or sensor orientation. Do not invent canopy height or sensor identity.

Require aware timestamps, explicit frame/plane association, photon units and supported position tolerance. Exclude mismatched-position readings with reasons; report included/excluded IDs and their effects on coverage or spot sample count. Never choose a numeric tolerance silently. Reject negative/nonfinite readings and ambiguous duplicates/overlapping support; distinguish malformed data from scientifically unavailable coverage.

Reject lux/W/m2 as direct PPFD inputs with `non_photon_unit`. Only an explicit spectrum-backed conversion via the existing spectral routine may supply photon data; retain its original input/unit/spectrum hashes and do not infer a spectrum from lumens or color temperature.

Numerical applicability bounds belong to the declared P3 model domain. Require `reference_position.json::applicability_source_ref` pointing to the P3 coefficient-pack domain, and preserve it through JSON/mapping. Missing evidence is refused/unavailable; a sensor setup cannot invent domain bounds. Reject `basis_id` collisions with every supplied P2 tissue `area_basis_id` using `basis_collides_with_tissue_basis`. P3 independently checks the reverse direction against the supplied tissue manifest (P2-h/P3-f).

### Route A logged

`DLI_day = 1e-6 * sum(PPFD_interval * interval_seconds)`.

Require `logger_sample_semantics` in {instantaneous, interval_mean} (P2-a). Interval means use step integration over explicit supported intervals; instantaneous samples use trapezoidal reconstruction with a forced step at declared schedule transitions. Split support at the transition rather than inventing a linear dimming ramp through it. A declared transition alone does not establish unknown ambient light or missing PPFD on either side; inadequate support stays unavailable. Timestamp samples alone do not establish coverage between arbitrarily distant readings. Never bridge a disallowed gap or extend the last reading to midnight without support. The constant-200-for-16-hours fixture also needs evidence for the remaining eight hours, such as supported zeros.

Split intervals at actual local midnight boundaries using aware-time helpers. Require explicit `dst_policy`, or refuse zones with transitions under the source contract (P2-g). When DST is explicitly supported, preserve actual 23/25-hour days and disambiguate repeated/missing wall times. Do not silently use the host timezone. An incomplete day exports an empty daily DLI and a reason. Keep recorded PPFD unscaled by schedule fraction when it already measures actual output; do not dim a measurement twice.

### Route C spot times schedule

`DLI_day = mean(PPFD_spot) * sum(on_duration_seconds) * output_fraction * 1e-6` under the source handoff's declared constant-output convention.

Require declared `ambient_light='none'` and `output_constant=true`; otherwise return `spot_schedule_assumption_undeclared`. Also follow P2-c: without at least one lights-off daytime measurement, report ambient evidence as `asserted_not_measured` on every output row. Preserve the declared assumption separately from its evidence status so the producer never claims measured absence of ambient light. A contradictory lights-off reading cannot pass as ambient none. Require actual dated/local-day schedule coverage; 16 h/day alone is not a dated on/off schedule. Specify needed date-selection input rather than choosing the host date or meter-arrival estimate.

Declare the output fraction under which spot readings were collected. Apply dimming exactly once: the above formula assumes readings referenced to the stated measurement-output basis. If readings already include the target dimming, do not multiply the same factor again. Current confirmed full-output operation is 1.0; unsupported fractional measurement normalization must remain unavailable, not be assumed linear. Resolve conflicting reference/schedule fractions explicitly, without multiplying both.

The mean uses only accepted lights-on readings at the declared reference. Optional survey points remain separate. No usable readings, unknown on/off times or insufficient provenance yield structured unavailability. This route provides schedule-based full-day estimation under assumptions, not continuous sensor logging; preserve that distinction in source_kind and disclosures.

### Route B simulated

Provide `simulate` inputs and a readiness audit for a declared virtual horizontal sensor. Inspect existing point-PPFD and empty-rig calibration interfaces, but do not fit lamp PPF or execute a new transport workflow in this task. Missing lamp PPF/fit returns `lamp_ppf_missing`; even when a scene contains PPF, the interface-only stage must not claim a numerical simulated reference channel has been delivered. Report any remaining deferred-execution condition truthfully.

Measured routes A/C do not require lamp PPF. No tissue-area multiplication, tissue absorptance, canopy-average DLI or plant optical geometry is substituted into them. Future simulated-route scene/occluder scope must be explicit; neither an empty rig nor a populated canopy is silently assumed equivalent.

## Outputs and package integration

Save into fresh `build/reference_dli_<date>_NN/` paths:

- `reference_dli.csv` with basis_id, source_kind, local_date, dli_mol_m2_day, coverage_status, on_duration_s, n_readings, mean_ppfd_umol_m2_s, ambient_light, applicability_low, applicability_high, reason.
- `reference_dli.json` with incident quantity, whole_plant model scope, mol/m2/day, complete_local_day basis, declared reference identity/source, value, value_rule, days_used, applicability_interval, fixed_over_horizon, status/reasons and input/code hashes.
- Input selection, exclusion, integration-rule and coverage evidence sufficient to reproduce the daily values; preserve reference geometry, actual day bounds and source support rather than dropping them from the compact JSON example.

`value_rule` must be explicit: mean_of_complete_days, single_representative_day or declared_scenario. Never silently average or select a favorable day. List every contributing date/value and keep measured versus scenario evidence distinct. For P2-f, compare the spread of days_used against a declared, evidence-bearing tolerance: exceeded tolerance yields `dli_not_constant_over_horizon`; do not retain an available fixed-over-horizon value or discard failing days silently. Missing tolerance/evidence is not an automatic pass. Document the spread metric and units. Mean PPFD has a route-specific definition: the spot arithmetic mean is not a time-weighted logged mean.

Keep coverage status (complete/incomplete/schedule_missing) separate from applicability status. A fully measured value outside the declared interval remains numeric in the producer audit with `out_of_applicability`; it is not an available P3 input. Extend the compact JSON example's status enumeration to represent this handoff-required state explicitly. Missing bounds must not silently count as in-domain.

Extend `_consumer_mapping()['growth']['reference_dli']`, capabilities and package request schema to accept a hashed channel result. Replace the usable reference entry only when status is available and its evidence/domain checks pass. Retain failed/out-of-domain measurement evidence and its reason without exposing it as usable growth input. Distinguish software capability from availability of one day's measurement.

The current independent consumer `_check_reference_channel_unavailable` only accepts unavailable placeholders. Refactor it into validation of both supported available results and explicit unavailable results. Validate source hashes, declared units/quantity/scope, reference-vs-tissue basis, day provenance, status and value consistency. Do not bypass or delete old false-claim protection merely to accept a new numeric value. Reject a forged available record even if its package manifest was rehashed.

## P3 compatibility check without P3 implementation changes

The handoff's compact reference_dli JSON is a producer record, not a literal replacement for the entire current P3 `light_response`. Inspect the current read-only `_validate_d9` / `_validate_reference_dli` contract before claiming P3 readiness.

Document and test the explicit field mapping:

- quantity -> light_basis; model_scope -> scope.
- D19 requires DLI_UNIT = 'mol/m2/day' end to end. Do not translate it to the legacy mol/m2/d spelling. Refuse legacy configs with legacy_dli_unit_spelling and diagnostic field differences; never divide by 86400 or auto-rewrite frozen inputs.
- position_mm/sensor_normal and their evidence -> reference.position_mm/normal_unit_xyz/frame_id/coordinate_frame plus source_kind/source_ref.
- Actual complete-day coverage and timezone -> local_day start_at/end_at/timezone/coverage and evidence.
- Applicability bounds -> the P3 min/max/unit/evidence object, honoring the current V2 field-name compatibility policy.
- Value and evidence -> fixed-horizon light response. kind, center, scale and per-curve coefficient records remain P3-owned model inputs; do not derive them from the readings.

Use an explicitly synthetic predeclared P3 model configuration for the read-only consumer acceptance test. Fill only reference-light fields from the producer. Do not edit P3 code or execute a P3 forecast. An in-domain single-representative-day fixture must validate; its out-of-domain counterpart must be refused/unavailable under the current P3 boundary.

For mean-of-complete-days or declared-scenario outputs, preserve full provenance. The current P3 validator expects a specific complete local day; do not fake one representative date or collapse several days into one day to obtain a pass. If that mode needs a P3 schema decision, report the exact incompatibility and complete the independently valid producer modes; do not claim all value rules are immediately P3-consumable.

This bounded producer/consumer validation is now in scope. Full P1 -> P2 -> P3 -> P4 integration, growth prediction and physiological feedback remain deferred.

## CLI and acceptance checks

Implement the source CLI or document the equivalent:

```text
python -X utf8 -m tools.reference_dli templates --out <fresh_path>
python -X utf8 -m tools.reference_dli compute --position <json> --schedule <json> --readings <csv> --route logged|spot_schedule --out <fresh_path>
python -X utf8 -m tools.reference_dli simulate --position <json> --schedule <json> --scene <json> --out <fresh_path>
```

Make required value_rule, date selection, position tolerance and integration/support policy explicit in documented input metadata or CLI options; do not hide scientific defaults in implementation choices.

## Technical review additions and shared ownership

**D19 shared constant:** P2 is the sole editor adding `DLI_UNIT = 'mol/m2/day'` to `tools/leaf_light/common.py` for this coordinated task. Import it in P2 bridge, channel and consumer rather than duplicating literals. P3/P4 import that same constant in their owned modules. Publish the small shared-file change/hash in your report so they can use it; do not edit their runtime. Existing historical artifacts and explicit legacy-rejection fixtures are not rewritten. New templates/configs use only the canonical value.

**P2-b sensor response:** require cosine_corrected in {true, false, unknown} and levelled metadata. Emit `cosine_response_uncorrected` on every affected row when correction is not established, retaining false versus unknown and leveling evidence. Do not interpret the flag as a numerical correction or invent a leveling tolerance.

**P2-c ambient:** every route reports ambient_light/evidence, with asserted_not_measured when no qualifying lights-off daytime measurement exists. Keep schedule assumptions separate from evidence claims; this also applies to logged and simulated readiness outputs.

**P2-d position tolerance:** derive allowed distance from declared allowable DLI error and a supported local gradient from spot_survey.csv; publish the gradient method, units, support region and derivation. Survey values inform uncertainty/uniformity, not the reference DLI mean. Missing/underdetermined gradients, zero gradients with inadequate evidence, and extrapolation outside the surveyed region must not produce an invented or infinite acceptance radius. No numeric error tolerance is supplied by this prompt.

**P2-e association:** require plant_association with plant_instance_ids, association_evidence and uniformity_basis. A shared reference for several plants needs survey evidence placing all associated locations within the declared uniformity tolerance. Do not imply that one reference measures every plant or include unverified plants in an accepted association.

**P2-h/D20:** retain two-way basis validation and per-patch face emission. Test tampered manifests and opposite/same-face fixtures through the independent consumer. Unknown biological face identity remains unavailable; no physics change is needed to expose supported side provenance.

Add discriminating tests beyond the original nine: a schedule transition strictly inside a sample interval (both a step/interval-mean and instantaneous case); cosine/levelled metadata and row flags; ambient assertion versus measured evidence; local-gradient tolerance and unsupported survey; invalid multi-plant uniformity; variable days_used -> dli_not_constant_over_horizon; explicit DST policy/refusal; canonical unit and missing applicability_source_ref. The 200-for-16-hours constant fixture alone does not verify transition semantics.

Cover all nine source acceptance checks:

1. Logged constant 200 umol/m2/s for 16 h plus supported night zeros -> 11.52 mol/m2/day; declared integration rule.
2. Gap -> incomplete/empty DLI, never darkness.
3. Declared timezone and midnight-crossing schedule/day boundary.
4. Spot mean times schedule; missing ambient/constant assumptions -> unavailable.
5. Lux/W/m2 direct input -> non_photon_unit; any explicit spectral conversion has provenance.
6. Tissue/reference basis collision -> basis_collides_with_tissue_basis.
7. Out-of-domain value retained with out_of_applicability, rejected for P3 use.
8. Simulation without PPF -> lamp_ppf_missing; no invented output.
9. Available producer replaces the usable mapping and validates with the read-only synthetic P3 fixture; unavailable/forged/out-of-domain records cannot pass as available.

Also check position exclusions, no survey averaging, no double dimming, explicit value-rule selection, old tissue-only packages and independent rehashed false-claim rejection. Use focused existing schedule/day/unknown/canopy regressions where touched; preserve tissue/angular numeric outputs. This verifies software, not sensor accuracy or biological prediction.

## Validation and delivery

Test changed metadata and independent-consumer expectations where relevant. Confirm numerical transport/CSV values and known-zero versus unavailable semantics are preserved. Do not repeat all historical tests unless touched behavior requires them; run core and tools suites separately where existing import constraints require it. No physical PPFD accuracy claim follows from these checks.

Save the channel implementation report as `handoff/CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md`, including exact APIs/fields/units/reasons, all nine acceptance outcomes, CLI runs, hashes, P3 compatibility limits and deferred B route. Record the V2 interface-alignment delta in `handoff/CODEX_P2_GROWTH_PACK_V2_EXECUTION_2026-10-04.md` and link the channel report rather than duplicating its evidence.

Deliver code, guide, blank-real templates and tests with JUnit in a fresh channel build folder. Preserve historical artifacts and the original handoff. No acquisition, real fitting, P3/P4 code edit, full-system integration or remote execution is authorized by this prompt.

Provide a Korean user summary and a one-page measurement checklist: choose and record the reference position/height basis; hold the sensor horizontal in the declared frame; record actual on/off times, ambient-light and constant-output conditions; take 3-5 lights-on readings 30 seconds apart with time/position/model/serial; keep optional survey points separate. Label these sparse readings as route C input, not a full-day logged series. Do not claim a completed measurement or an actual meter arrival date.

Append LOG and a TODO to fill real reference position, actual on/off times, applicability evidence and PPFD readings when the meter arrives (expected around 2026-10-10). Preserve confirmed three-fixture, 16 h/day, 100% operation. Missing physical inputs must not block completion of the explicitly synthetic software implementation.

Record D19/D20 and P2-a through P2-h as done/already present/deferred in the P2 report. Save technical-review JUnit/demos under a fresh `build/technical_review_fixes_20261004_01/P2/`, with links to channel artifacts. The shared `CODEX_TECHNICAL_REVIEW_FIXES_EXECUTION_2026-10-04.md` belongs to coordination after all project reports; do not concurrently edit it.
