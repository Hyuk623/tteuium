# P4 carbon diagnostic implementation contract

Date: 2026-10-03. Revision: `p4-carbon-diagnostic-2`. Author: Codex.
Status: exact proposed software contract aligned with adopted D1-D10; unresolved
physiological choices remain pending Claude review. Production implementation is
not authorized by this document alone and was not performed in this continuation.

This revision supersedes the active-runtime interpretation of sections 4-7 and 9
of `CLAUDE_FSP_PHYSIOLOGY_CONTRACT_2026-10-03.md`; source equations and historical
evidence remain intact. Its section 10 is retained and made explicit here.
The prior review's open choice about offline calibration is settled by D5.

## 1 Ownership and execution boundaries

D1/D2: P3 is the sole writer of realized geometry, increments, events and forecast
distribution. P4 reads immutable inputs and produces diagnostic rows. It never
clips or scales P3, overwrites state, changes seeds, resamples or reweights P3
particles, or calls its forecasting/update functions. A diagnostic deficit changes
only the diagnostic status. Feedback requires a separate explicit decision.

D5: `tools/growth_calibration.py::apply_parameter_set` is an existing, separate
offline preparation capability. An explicitly selected, frozen and hashed pack
may be applied before P3 starts. Record the fit-plan hash, parameter-set ID,
source/code hashes, original and resulting config hashes, selected scenario,
bindings, clock mapping and every embedded response feature. Do not call this
function, a fitter or a light solver from any runtime P4 API or implicit adapter.
P4 consumes the already frozen result as provenance, not mutable parameters.

D3/D6/D7: no linking in this task. The later first synthetic acceptance requires
numeric P1-P2-P3 results; P4 may be unavailable with reasons. Only reversible
units/frames/identity/time/missingness representations round-trip. Photosynthesis,
aggregation, transport and forecasts need forward-correctness checks. Keep source
samples, shapes, trajectory weights and provenance; never reconstruct them from
summaries or insist that a reduction be invertible.

## 2 Future owned files and callable surface

Future Codex-owned files, only after the diagnostic implementation is invoked:
`tools/fsp_carbon_diagnostic.py`, `tools/fsp_carbon_diagnostic_schema.json`,
`tools/tests/test_fsp_carbon_diagnostic.py`, `tools/FSP_CARBON_DIAGNOSTIC.md`.
Use this distinct diagnostic name to avoid implying an active growth integrator.
Do not edit P3's active engine/calibration files or protected core/configuration.

Proposed public functions:

| Function | Inputs | Output |
|---|---|---|
| `audit_diagnostic_inputs(request, parameter_pack)` | Immutable objects or explicit hashed local manifests with the fields below | `status,components,issues,source_hashes,coupling_audit_status`; read-only, no coefficient substitution |
| `inspect_p3_coupling(p3_manifest, frozen_config, calibration_provenance)` | Source manifest plus complete frozen config/pack trace | Declared paths, evidence status and D9 compatibility; never infer no coupling from legacy flags |
| `compute_leaf_exchange(leaf_samples, environment, parameters)` | One identity-matched spatial/time quadrature with compatible light basis | Signed `supply_gC`, per-patch exchange, coverage and respiratory ownership; no growth action |
| `compute_respiration(organ_states, environment, accounting_policy, dt_s)` | Scoped structural mass history/start-state approximation and component ownership | `maintenance_charged_gC`, per-organ/component costs and exclusions |
| `infer_structural_demand(p3_interval, mass_state, mass_form_parameters)` | Immutable endpoint geometry and independently supported mass mapping, or explicitly supplied mass increments | `organ_demands_gC`, required substrate sum, uncertainty and unavailable reasons |
| `compute_carbon_sufficiency(p3_interval, carbon_state, light_series, environment, parameter_pack)` | The section-10 signature retained exactly; request metadata below travels inside these objects | One diagnostic result per plant instance, P3 trajectory, parameter draw and interval; no state mutation |
| `audit_carbon_balance(diagnostic_ledger)` | Only a funded, explicitly hypothetical calculation with compatible compartments | Residual/tolerance/availability; never approves an unfunded negative reserve |
| `export_diagnostic(result, output_path)` | Complete result and a fresh path under project build | CSV/JSON diagnostics, availability and immutable manifest |

Inactive runtime APIs: `allocate_carbon`, `update_form`, `advance_physiology`,
potential beta sinks, organ-size generation and reserve-feedback growth correction.
They remain isolated counterfactual analyses in the earlier evidence pack. Do not
implement them as automatically invoked helpers or return their form as P3 output.

Future CLI: `python -X utf8 -m tools.fsp_carbon_diagnostic templates|audit|diagnose`.
`audit` is read-only; `diagnose` is an explicit operation, not a default import side
effect. No `fit`, forecast, optics, state-update or integration command is included.

## 3 Identity and immutable input contract

`p3_interval` requires `schema_version, run_id, scenario_id, plant_instance_id,
source_plant_id, trajectory_id, trajectory_weight, t_start, t_end, frame_id,
geometry_hash_start, geometry_hash_end, area_basis_id, organ_states_start,
organ_states_end, events, post_termination_scope, p3_manifest_ref,
frozen_config_ref, calibration_provenance`.

IDs are explicit strings with a reviewed mapping; do not substitute source plant
for placed instance. Trajectory weight is finite/nonnegative and preserved, not
normalized across missing outputs. Organ keys include `organ_id,compound_leaf_id`
and nullable `leaflet_id`; group mappings cannot double-count leaf suborgans.
Times are timezone-aware ISO8601, t_end>t_start; dt is elapsed seconds, independent
of thermal/development age. Missing identity or conflicting hashes is an input
error, not unavailable biological evidence. Unmapped optional tissue is reported
as coverage loss, never absorbed into a guessed plant total.

Each supplied P3 endpoint preserves its actual fields (`rachis_arc_length_mm`,
`left_extent_mm`, `right_extent_mm`, `supported_area_cm2`, `area_basis_id`,
`direction_unit_xyz`, source/existence/retention status). Retain original arrays;
do not infer length/width from a mean summary or area from an envelope. A complete
stored mapping must explain each source field used by the diagnostic.

`carbon_state` requires `scope, included_organ_ids, excluded_organ_ids,
coverage_statement, stock_at, reserve_gC, minimum_reserve_gC, organ_masses,
external_import_gC, external_export_gC, boundary_policy, source_refs`.
`stock_at` equals t_start. Each disjoint mass compartment has `organ_id,organ_kind,
structural_dm_g,carbon_fraction_gC_gDM,mass_basis,evidence_kind,source_ref,
uncertainty`. Root mass and reproductive scope are required for whole-plant
claims. Structural mass excludes reserves; compartment parent totals cannot be
added to their children. Initial masses/reserves may be labelled assumptions in
a hypothetical fixture, never inferred from first-leaf=1 or absence of records.

`scope` is `whole_plant` or `supported_leaf_subset`. For a subset, supply/cost
components can be computed independently, but a sufficiency ratio requires an
explicit scoped reserve allocation and boundary transfers. A leaf is not a closed
carbon system. Never award the plant's full reserve to each leaf or set unknown
root/export demand to zero. Absent scoped budget => ratio unavailable while
supported leaf exchange remains reported.

`light_series` requires sample records with `patch_id,organ_id,plant_instance_id,
t_start,t_end,area_weight_m2,ppfd_umol_m2_s,light_basis,one_sided_area_basis,
geometry_hash,backend,replicate,coverage_basis,status,source_ref`. `light_basis`
is incident or absorbed and must match the fitted model. The weights partition
supported physical tissue without overlap. Concurrent fixtures are combined once
at a receiver before nonlinear response; transport replicates remain separate.
Counterfactual removals and Shapley effects are not incoming physical light.

An interval with unknown/partial samples retains coverage/reasons. A light snapshot
can be repeated only under an explicit fixed-geometry/fixed-light scenario with a
valid interval. P3 future envelopes remain optical-ineligible; no implicit future
light evaluation or metric tissue creation is allowed.

`environment` is an interval table with `plant_instance_id,t_start,t_end,
leaf_temperature_c,air_temperature_c,temperature_basis,co2_ppm,pressure_pa,
relative_humidity_pct,vpd_kpa,ec_ms_cm,ph,environment_kind,status,source_ref`.
Columns can be null when unused; active dependencies are declared by the pack.
Measured history and future assumptions/forecasts retain their distinct labels.
Gaps never become zeros or interpolated exposure without an explicit separate
assumption scenario. Gas partial pressure and mole fraction require pressure and
a documented basis; do not substitute one numeric value for the other.

## 4 Parameter evidence and availability

`parameter_pack` requires `schema_version,pack_id,sha256,model_id,
respiration_accounting,light_basis,scope,applicable_domain,parameters,
organ_parameter_map,respiration_ownership,mass_form_mapping,uncertainty,
review_status,source_registry_ref,numerics,assumptions`.

Each parameter record preserves `value,unit,evidence_kind,source_id,locator,
cultivar,conditions,uncertainty,applicability,review_state`. Evidence kind is
measured/fitted/borrowed/assumed/unidentified. Unknown uncertainty is null, not SD=0.
Store correlated joint draws with stable draw IDs; do not independently redraw
coefficients by output interval or destroy cross-organ dependence. P4 draw IDs
are distinct from P3 trajectory IDs; never reweight a P3 trajectory using the index.

Pack file hash is checked against a reference external to the file's own content;
do not define a self-referential hash. Scope/domain or source-unit mismatch blocks
the affected calculation. Numeric biological values are never package defaults.
Only an explicitly reviewed compatible pack, or an expressly labelled hypothetical
assumption pack, enables a numeric result. D1-D10 do not approve any such biology.

Synthetic/hypothetical output carries `evidence_status=hypothetical`, and always
`accepted_for_domain=false`. Real measured inputs alone do not promote borrowed
coefficients or an unreviewed response law to target-calibrated status.

## 5 P3 environment and calibration provenance

Consume `p3_light_coupling` (`none|size_target_dli`) and the complete
`p3_environment_paths` list when exported with a verified frozen-config hash.
Current in-progress helper uses path records `{path,metric,target}`. Preserve
unknown/additional producer fields and source schema; the future adapter must
pin the completed owner export instead of guessing field aliases. Retain
`environment_audit_status` if supplied.

Record the full list, including `calibration.applied_features`, and the frozen
pack/scenario/binding references. `p3_light_coupling=none` alone does not establish
absence of embedded historical light effects. Older `environment_used/light_used`
flags alone do not establish complete path coverage. If audit fields are absent,
hashes differ or older calibration lacks feature provenance, set
`coupling_audit_status=unavailable`, with `p3_environment_audit_missing` or
`embedded_response_provenance_missing`; do not replace the paths with empty proof
of independence. This blocks a claim of D9-compatible integration readiness, not
otherwise supported standalone exchange arithmetic. Return component results and
their limitations separately.

Under D9, temperature enters P3's development clock only; fixed-horizon DLI
enters size targets only. The P3 policy auditor must account for all paths, not
only a declared profile string. Unsupported direction/event/stop/clock light
paths or CO2/RH/VPD/EC/pH response make `d9_compatibility=incompatible`. P4 reports
the finding and does not repair or rerun the P3 configuration. Generic legacy
P3 behavior must not be relabelled as D9.

DLI in P3 does not remove physical light dependence from P4 photosynthesis. Keep
the appropriate time/spatial light supply calculation; never subtract a guessed
"DLI effect" from carbon uptake. Double counting is prevented by **no feedback**,
not by dropping photosynthesis. `feedback_action` is always `none`.

D8 uses exponential remaining growth for existing age-unknown organs and beta
timing for newborns. Neither produces structural mass without an independent
mapping. Never bind exponential D/k to beta x_max/a_m/a_e or infer physiological
sink coefficients from geometric beta parameters. No new fitting family is adopted.

Calendar-fitted bindings retain the old calendar guard until P3's owner completes
and verifies the normalized-temperature exception. D9 requires evidence for the
declared calibration setpoint, a matching normalized clock with m(T_ref)=1 within
explicit tolerance, and applicable parameter/time semantics. Passing that identity
does not experimentally validate temperature response away from T_ref. P4 records
the mapping, not implements or bypasses it. Unknown clocks/bindings are unavailable.

## 6 Variable policy in P4

| Variable | P3 D9 | P4 role in this revision | Missing or unsupported behavior |
|---|---|---|---|
| Time-resolved incident/absorbed PPFD | No extra general response beyond DLI target policy | Candidate NRH input with matching basis, area and spectrum/domain | Missing basis/history blocks supply; no silent absorptance factor |
| DLI | Fixed size-target effect only | Preserve as P3 provenance/context; cannot uniquely recover an instantaneous light history | No DLI-to-hourly curve without explicit scenario; no second size correction |
| Leaf temperature | P3 clock uses its declared temperature basis | Source-supported Q10 maintenance form, conditional coefficients; photosynthesis-domain check | Require leaf sensor or labelled air substitution; no invented NRH temperature multiplier |
| CO2 | Metadata, no P3 response | NRH calibration-domain dependency; FvCB response deferred | No active CO2 response function; outside/missing required domain data => supply unavailable |
| VPD and RH | Metadata, no P3 response | Metadata/applicability only; no stomatal/stress multiplier | Missing is not zero; block only if an explicit domain predicate requires it |
| EC and pH | Metadata, no P3 response | Treatment metadata/applicability only | No direct assimilation/allocation response; preserve unknown stress evidence |

The exclusion of a variable from P3 is not evidence for including it in P4.
Conversely, compatible P4 respiratory/domain calculations are not an extra P3
growth response. Every active dependency must name its equation and source.

## 7 Conditional equations and carbon accounting

Retain exact section-10 supply-demand semantics below. These are a software
contract conditional on scientific review/explicit assumptions, not newly adopted
physiological defaults. Internal stock/flux units are gC; exchange integration
uses seconds and one-sided metric area. `kC=12.011e-6 gC/umolCO2`;
`chi=12.011/30.026 gC/gCH2O-equivalent`. Structural gDM and fresh mass are distinct.

Candidate NRH, after photorespiration/before mitochondrial respiration only if
that interpretation is evidenced:

```text
H(I)=2*alpha*I*Pmax / (alpha*I+Pmax+sqrt((alpha*I+Pmax)^2-4*theta*alpha*I*Pmax))
H(0)=0; Pmax>0, alpha>0, 0<theta<=1
S_gC=kC*sum_over_time(sum_over_disjoint_samples(H(I_j)*area_weight_j)*dt_s)
```

Sample weights are m2; I is umol photons/m2/s, H is umolCO2/m2/s and alpha is
umolCO2/umol photons in the selected basis. Absorbed I already contains absorption.
Do not apply H to mean irradiance unless a uniform-light approximation is explicit.
Different optical replicates are not added as simultaneous irradiance.

For `before_mito`, dark H=0 and compatible organ maintenance remains active.
For `net_leaf`, signed exchange includes a reviewed list of already-subtracted
respiration components. Matching components are excluded downstream. If net input
includes growth respiration while ASR also charges it, the pack is incompatible
until partitioned/reconciled. Never insert an unrelated Rd or assume Rd=maintenance.

Conditional maintenance:
`R_o=chi*m_o*W_o*Q10_o^((T_o-Tref_o)/10)*activity_o*dt_s/86400`.
Mass is explicitly structural and excludes reserve. The paper/CSV DM-basis conflict
must be resolved or labelled hypothetical. Activity=1 needs an explicit assumption;
`1-exp(-f_day*RGR5_per_day)` requires the reviewed history definition. No missing
history fallback, negative respiration, stock clipping or default temperature.

P3-implied structural increments must be nonnegative under this no-remobilization
contract. Negative differences or changes of support produce unavailable demand,
not a carbon credit. Direct independently supported mass increments are preferable
to inversion. Conditional inverses retained from section 10:

```text
W_target=(A_P3-A_anchor+s_anchor*W_anchor)/s_target
h(W)=lambda*(1000*W_gDM)^gamma  [output mm, lambda in mm/mg^gamma]
W_target=((x_P3-x_anchor+h(W_anchor))/lambda)^(1/gamma)/1000
D_o=chi*q_o*deltaW_o; D=sum(D_o)
Rgrowth_required_o=D_o-c_o*deltaW_o
```

SLA is m2/g structural **blade** DM. The geometry inverse needs positive s or
positive base/lambda/gamma, compatible mass/area scope and measured anchor.
Conflicting inversions => `inconsistent_mass_form`. No averaging without a joint
evidence-backed error model. q is ASR gCH2O/g structural DM; require
`0<c_o<=chi*q_o`. Do not charge the growth residual again in U: q already includes
growth cost. An unfunded residual is required cost, not actual measured respiration.

Demand includes all scoped compartments and any supported new-organ mass cost.
Birth count alone is insufficient. A pre-existing bud transfer requires an explicit
stock/transfer record; internal transfers cancel and cannot create tissue for free.
Truss/terminal event metadata with null geometry is not measured reproductive mass.
Under D10, `post_termination_scope=unavailable` blocks whole-plant future demand
where continuation is missing; observed leaves may retain scoped component outputs.
`retention_assumption_exceeded` is not death or zero future respiration; flag the
affected scope and do not extend a retained-leaf assumption silently.

Budget and statuses:

```text
U=B_start+S+external_import-external_export-Rmaintenance_charged
if U<0: maintenance_deficit_gC=-U; ratio=null
otherwise: V=max(U-Bmin,0)
if D=0: ratio=null, status=no_growth_demand
if D>0: ratio=V/D, growth_deficit_gC=max(D-V,0)
```

No physical next state is returned. Optional funded hypothetical ledger has
`B_end=U-D`, `deltaCstr=sum(c_o*deltaW_o)` and
`deltaB+deltaCstr=S-Rmaintenance-Rgrowth-external_export+external_import`.
Audit only when
U>=D and required quantities are present. A deficit may have an algebraic
required balance but not a feasible reserve; do not certify it as a physical
trajectory. Subsequent intervals require their own source-linked reserve state
or a separately reviewed diagnostic-only propagation contract. Never reuse the
same initial reserve independently across intervals and sum the resulting ratios.

All biological ambiguity above remains in the decision register. Molecular/unit
identities and immutability can be implemented/tested independently once authorized.

## 8 Results and deterministic availability

One output row preserves identity, trajectory weight and interval. Required core
fields are the nine section-10 fields: `available_growth_carbon_gC`,
`required_growth_carbon_gC`, `sufficiency_ratio`, `maintenance_deficit_gC`,
`growth_deficit_gC`, `status`, `limiting_inputs`, `assumptions`, `source_hashes`.
Additional metadata:
`schema_version,diagnostic_scope,evidence_status,component_status,
coupling_audit_status,d9_compatibility,feedback_action,accepted_for_domain,
numerical_tolerance_applied,p4_parameter_draw_id` and all identity keys in section 3.

Status precedence and exact null behavior:

| Condition | status | V | D | ratio | Maintenance deficit | Growth deficit |
|---|---|---|---|---|---|---|
| Required biological input unresolved/missing | `unavailable` | available component or null | available component or null | null | known value or null | null unless both budget/demand known |
| Compatible complete inputs and U<0 | `maintenance_deficit` | null | known D | null | -U | null |
| U>=0 and D=0 | `no_growth_demand` | V | 0 | null | 0 | 0 |
| U>=0, D>0, V>=D within declared tolerance | `sufficient` | V | D | V/D | 0 | max(D-V,0) |
| U>=0, D>0, V<D beyond tolerance | `growth_deficit` | V | D | V/D | 0 | D-V |

If D is missing but negative U is independently established, retain the known
maintenance deficit in component results; global status remains unavailable.
Numeric tolerance is required in the pack, in gC absolute and dimensionless
relative terms: eps=abs_gC+rel*max(abs(V),abs(D)). If used at the sufficient
boundary, mark it; preserve raw ratio/deficit and do not clip stocks. Unknown or
contradictory science is never within a floating-point tolerance.

Malformed schema, hashes, units, duplicates, identity mismatch, nonfinite values
and invalid intervals raise a validation error before arithmetic. Missing evidence
returns a typed unavailable result with reasons. Each reason includes component,
code, identity/interval and source reference; it remains in coverage denominators.
CSV missing numeric is empty, JSON null. Never serialize NaN/Infinity; preserve
producer sentinels separately until explicit adapter conversion.

Suggested reason codes are enumerated in the machine contract. Every result uses
`feedback_action=none` and `accepted_for_domain=false`; real acceptance needs a
separate evaluation/version. Component exchange results can remain available when
whole-plant demand, coupling provenance or boundary accounting is unavailable.

## 9 Exports and validation to implement later

Future outputs: `diagnostics.csv`, `component_fluxes.csv`, `availability.json`,
`coupling_audit.json`, `manifest.json`. JSON holds sources/assumptions/IDs/status
metadata; CSV rows reference these records. Do not flatten entire source arrays
into an undocumented string or lose the original producer artifact. Manifest
contains input/config/code/artifact hashes, schema versions, assumptions, scopes,
command, numerical policy and immutable P3 before/after hashes.

Future tests must independently catch: units and day/second conversion; mixed
area/incident/absorbed basis; signed night exchange; respiration and yield double
counting; missing root/reserve; partial-control-volume boundaries; zero demand,
maintenance and growth deficits; incompatible carbon fractions; negative inferred
mass; inconsistent geometry inverse; variable SLA; new-organ material; D10 terminal
and retention scope; full-config and frozen-pack coupling provenance; no P3 mutation
or reweighting; numerical tolerance boundaries; changed hash/identity; unknown time
coverage; nonlinear spatial aggregation and fixture versus replicate handling.

Use fixed input interval/quadrature partitions independent of reporting dates.
No timestep-dependent random draws. Check h/h2/h4 numerical convergence on an
explicit synthetic forcing fixture separately from biological validation. Reporting
subdivision must preserve total integrated supply when the physical quadrature is
unchanged. This is a forward computation check, not inverse photosynthesis.

For D5 future owner checks: refusal of beta-coordinate bindings by exponential
fits; normalization at the declared calibration setpoint; full embedded response
audit; no silent double application of a fitted light effect and new DLI response.
P4 records those results and has no permission to patch P3 during this continuation.

Scientific validation remains separate: compatible gas-exchange and respiratory
references, organ mass/composition/reserve evidence and independently identified
mass/form relations. P4 diagnostic truth cannot be validated using the P3 prediction
it is checking as its own ground truth. No geometry-improvement claim follows from
a read-only diagnostic. Practical thresholds are unset until reviewed.

## 10 Review and implementation gates

Claude returns retain/revise/unresolved for each record in `equation_decisions.csv`
with the evidence, exact adopted formula/units/domain and applicable parameter IDs.
Missing coefficient/applicability must disable the dependent component, not all
software delivery. Adopted D1-D10 are not reopened; unresolved physiology is not
approved by the Science review's existence.

Next isolated diagnostic implementation requires an explicit invocation and the
reviewed subset or explicit hypothetical mode. Cross-project adapters and the
end-to-end run require the separately deferred integration step. Under D6 their
first numeric success is not conditional on obtaining a numeric P4 index.

## 11 Delivery clarifications and complete equation disposition

These implementation-level clarifications complete this proposed revision; they
do not adopt unresolved physiology. The synchronized machine contract is in
`build/p4_diagnostic_contract_20261003_01/`. `equation_disposition.json` classifies
all 28 earlier equations and embeds their original records unchanged, including
source locators, cultivar/conditions, limitations and evidence type. Fourteen
decision groups in `equation_decisions.csv` identify review responsibility.

The `growth` equation is retained only in the diagnostic direction:
`D=chi*q*deltaW_P3`, `Rgrowth_required=D-c*deltaW_P3`. P4 does not calculate a
realized deltaW from allocation. Forward allocation, reserve-update, beta potential
sinks, root-ratio demand and form-generation equations stay inactive. A funded
hypothetical ledger is an audit, not a returned or propagated plant state.
The source SLA/allometry records remain unresolved inverse dependencies; the
low-light linear comparator and FvCB are inactive runtime alternatives.

Output metadata also requires `light_basis=incident|absorbed|unavailable`; original
sample metadata remains preserved. Output geometry hashes are SHA256 strings.
Every `limiting_inputs` record includes `component,code,reason,plant_instance_id,
trajectory_id,t_start,t_end,source_ref`. `source_ref` can be null only when the
referenced evidence is absent (or for explicitly invented schema examples).
Reason identity and interval must match its output row.

`maintenance_deficit` requires a known nonnegative D, null V/ratio/growth deficit,
positive maintenance deficit and reason `maintenance_budget_negative`.
`no_growth_demand` requires known nonnegative V, D=0, null ratio, zero deficits
and reason `zero_growth_demand`. `sufficient` and `growth_deficit` require numeric
V, D, ratio and growth deficit. Global `unavailable` requires at least one reason;
an incomplete coupling audit alone does not make known component arithmetic
unavailable. These rules implement the section-8 table, not new biological choices.

JSON Schema checks field types, required metadata and these status-specific
constraints. Semantic checks must additionally enforce finite numbers, positive
ordered intervals, matching reason identity/interval, hash validity against actual
inputs, dependency coverage and arithmetic/tolerance consistency. Shape validation
alone is not a functioning carbon diagnostic or a physiological test.

The five invented status examples are serialization fixtures only. The delivery
verifier exercises their schema and intentional invalid mutations, checks all
equation dispositions and preserved source hashes, and maps every prompt
requirement to reviewed evidence. Future module tests in section 9 remain unrun.

Producer status update, 2026-10-04: the subsequent P3 source now calls its
normalized-clock validator from `apply_parameter_set` and records applied feature
provenance. The earlier calendar-only observation in section 5 describes the
original snapshot. Consumers still require the owner's completed versioned export
and evidence-backed mapping; this source update does not authorize bypassing the
guard or certify all producer behavior. See the continuation report and the
pack's separately preserved follow-up snapshots.
