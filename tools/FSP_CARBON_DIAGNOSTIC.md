# P4 carbon diagnostic

P4 computes conditional carbon supply, maintenance, P3-implied organ demand and
sufficiency. It never changes P3 geometry, growth rates, events, weights or seeds.
There is no fitter, light solver, allocation engine, reserve propagation or P3
execution inside this module. Scientific choices remain explicit reviewed inputs
or labelled hypothetical assumptions; no biological defaults are installed.

Schema: `p4-carbon-diagnostic-2`. Python 3.11+; standard library for arithmetic and
`jsonschema` for export validation (see `fsp_carbon_diagnostic_requirements.txt`).
Run commands from the project root. All outputs require a fresh subdirectory of
project `build/`. Missing CSV numbers are empty cells; missing JSON values are null.

## Commands

```powershell
python -X utf8 -m tools.fsp_carbon_diagnostic --help
python -X utf8 -m tools.fsp_carbon_diagnostic templates --out build/my_p4_blank
python -X utf8 -m tools.fsp_carbon_diagnostic audit --input build/my_p4_blank/request.json --out build/my_p4_audit
python -X utf8 -m tools.fsp_carbon_diagnostic_demo --out build/my_p4_fixture
python -X utf8 -m tools.fsp_carbon_diagnostic diagnose --input build/my_p4_fixture/request.json --out build/my_p4_result
python -X utf8 -m tools.fsp_carbon_diagnostic validate-table --input build/my_table.json --out build/my_table_checked
python -X utf8 -m pytest tools/tests/test_fsp_carbon_diagnostic.py tools/tests/test_fsp_growth_science.py tools/tests/test_fsp_growth_pack_v2.py -q
```

The demo numbers are deliberately invented arithmetic fixtures, not measurements,
literature estimates, an experiment prescription or target-cultivar defaults.
An audit with absent science returns unavailable reasons; malformed inputs fail.
The independent caller selects each P3 trajectory and correlated P4 parameter
draw. One call diagnoses one plant instance and interval. No resampling occurs.

## Public APIs

| Function | Contract |
|---|---|
| `audit_diagnostic_inputs(request, parameter_pack)` | Read-only input/component availability and coupling audit; blank input is supported |
| `inspect_p3_coupling(p3_manifest, frozen_config, calibration_provenance)` | Hash-checked whole-config dependency paths, D9 assessment, no producer imports |
| `compute_leaf_exchange(leaf_samples, environment, parameters)` | Signed gC supply plus patch/interval quadrature rows |
| `compute_respiration(organ_states, environment, accounting_policy, dt_s)` | gC maintenance charged exactly once and organ/time rows |
| `infer_structural_demand(p3_interval, mass_state, mass_form_parameters)` | Required gC, structural gDM/gC and required growth-respiration cost per organ |
| `compute_carbon_sufficiency(p3_interval, carbon_state, light_series, environment, parameter_pack)` | Pure complete diagnostic plus independent components, coupling audit, preserved inputs and immutability hashes |
| `audit_carbon_balance(diagnostic_ledger, originating_diagnostic)` | Verified C04/pack association and funded hypothetical balance residual; does not return plant state |
| `validate_diagnostic_table(results)` | Recompute supplied results and check contiguous identical reserve reuse within each accounting group |
| `export_diagnostic_table(results, output_path)` | Validate the complete supplied table before CSV/JSON export, with per-row snapshots |
| `export_diagnostic(result, output_path)` | Validated fresh CSV/JSON export and hashes; refuses modified provenance/inconsistent results |

All parameter arguments above are the same external hash envelope. Numerical
science missing from a valid input gives a component `unavailable`. Invalid units,
nonfinite numbers, hash/identity mismatches, duplicate inventories and overlapping
intervals raise `StudyError`; they are not repaired. The API does not read files
or call producers while doing arithmetic.

## Request and external hash envelopes

The request contains `schema_version` and five objects: `p3_interval`,
`carbon_state`, `light_series`, `environment`, `parameter_pack`.
`fsp_carbon_diagnostic_schema.json` defines the top-level request, envelope and
full output shape. Python performs the additional semantic validations below.

Parameter/producer envelopes are `{"payload": {...}, "sha256": "..."}`. The hash
is `tools.leaf_light.common.digest(payload)`: SHA256 of UTF-8 JSON with sorted keys,
`ensure_ascii=False`, `allow_nan=False`, standard JSON separators. It is external
to the payload. Do not put a hash of the complete file inside that same file.

At the CLI boundary each of the five top-level objects may instead be a local
`{"path": "relative-or-absolute.json", "sha256": "byte-hash"}` reference. Paths
are resolved relative to the request file. The referenced JSON must contain the
object (including its envelope where required). The byte hash is verified before
reading. No network loading, producer execution or inference occurs.

Measured tables should be CSV. `light_series.samples_csv`, `environment.records_csv`,
`carbon_state.organ_masses_csv` and `carbon_state.mass_increments_csv` may be hashed
file references replacing the corresponding inline arrays. Supply one route only.
CSV headers are the record field names below; numeric cells are parsed by their
declared names, booleans are `true`/`false`, and blanks become null. A producer's
literal `unavailable` sentinel must be converted through a separately reviewed
adapter; it is not silently read as zero. Nested histories/geometry and knowledge
remain JSON. Complete materialized inputs and original file hashes are preserved
for reproducibility. Inline arrays are convenient for synthetic fixtures and APIs.

## P3 interval and coupling

Required identity fields: `run_id, scenario_id, plant_instance_id, source_plant_id,
trajectory_id, trajectory_weight, t_start, t_end, frame_id, area_basis_id,
geometry_hash_start, geometry_hash_end`. Weight is finite/nonnegative and never
renormalized. Times are aware ISO8601 with positive elapsed interval.

`organ_states_start/end` are complete preserved arrays keyed by unique `organ_id`.
In this isolated request representation, `geometry_hash_start/end` are canonical
hashes of these arrays; original producer geometry/file hashes belong in their
preserved metadata. Do not relabel a native P2 mesh hash as this hash. A later
cross-project adapter needs the explicit geometry association before connecting
the representations; that adapter is not implemented here. States used by mass
inversion retain supported area/basis, metric length, kind and retention status.
`events` uses unique `event_id` and `event_kind`; truss/terminal geometry is null.
`post_termination_scope=unavailable` prevents whole-plant future demand.

`p3_manifest_ref` and `frozen_config_ref` are envelopes of the original producer
objects. The manifest's `config_hash` must match the config digest. The pinned
producer vocabulary is `probabilistic-compound-1` with `p3_light_coupling`,
`p3_environment_paths` records `{path,metric,target}`, and `environment_audit_status`.
P4 compares paths against the complete supplied config, including family features,
stop rules, clock, DLI response and `calibration.applied_features`. Additional
producer path metadata is retained. Old clock-only flags cannot prove independence.

If fitted calibration is present, supply a `calibration_provenance` envelope with
`parameter_set_id,fit_plan_hash,applied_features`; a non-calendar clock additionally
requires its frozen `calibration_clock_reference` (fixed-setpoint calendar-day
evidence). Missing old-pack provenance makes coupling unavailable. Invalid D9
paths or clock normalization are reported as incompatible; the diagnostic never
repairs a config. This checks the coupling contract, not every P3 forecasting rule.

D5 parameter application remains an explicit offline operation before P3 starts.
P4 never invokes it. DLI already in P3 does not remove photosynthetic supply.
Unknown/incompatible coupling does not erase separately supported component
arithmetic, but it prevents a D9 integration-readiness claim.

## Carbon state and organ demand

`context` carries `plant_instance_id,t_start,t_end`; `stock_at` must equal interval
start. `scope` is `whole_plant` or `supported_leaf_subset`. Supply explicit
`included_organ_ids,excluded_organ_ids,coverage_statement,organ_masses,reserve_gC,
minimum_reserve_gC,external_import_gC,external_export_gC,boundary_policy`.
Never give each leaf the full plant reserve. A subset requires an explicit policy
for its allocated stock and boundary transfers before its ratio is available.

Each mass record has `organ_id,organ_kind,structural_dm_g,mass_basis,
evidence_kind,source_ref`. The only active basis is
`structural_dm_excluding_reserve`. `child_organ_ids`, when present, must not overlap
included parent totals. Whole-plant accounting requires root compartments, no
excluded living compartments, and `reproductive_scope={status,organ_ids,source_ref}`:
status is `not_present` with an explicit assumption/evidence, or `accounted` with
included reproductive organs. Unknown reproductive scope is unavailable. Declare
`nonfoliar_assimilation_assumption` for leaf-only supply used in a whole-plant
budget. Each illuminated leaf mass record declares `supported_area_m2`; patch
weights must sum to that area within the explicit numerical tolerance.

Prefer `mass_increments`: `organ_id,structural_dm_start_g,structural_dm_end_g,
unit=g_structural_DM,evidence_kind,source_ref`. The start must match the mass stock.
New organs need `birth_mass_accounted=true`, zero initial mass and their complete
growth cost. Pre-existing bud transfers are unavailable until an explicit transfer
ledger exists. A truss event needs `material_source_ref` and accounted reproductive
compartments; event count alone supplies no mass. No abscission/remobilization model.

Alternatively, parameter-pack `mass_form_mapping[organ_id]` declares `source_ref`
and an `inverses` array. Area inverse: `{kind:"area",sla_start:<id>,sla_end:<id>}`,
blade `mass_compartment`, supported endpoint `supported_area_cm2` and matching
`area_basis_id`. Dimension inverse: `{kind:"dimension",field:<metric field>,
lambda:<id>,gamma:<id>}` with a supported length in mm. When multiple inverses are supplied, every inverse needs a unique string `inverse_id` and
the mapping needs `primary_inverse` naming the selected ID. All inverses must agree
with that primary within `mass_abs_tol_gDM`; they are never averaged. The selected
ID is preserved in demand component rows. One inverse may omit these IDs.

```text
W_target = (A_end - A_start + SLA_start*W_start) / SLA_end
h(W_gDM) = lambda*(1000*W_gDM)^gamma
W_target = ((x_end-x_start+h(W_start))/lambda)^(1/gamma)/1000
D_o = (12.011/30.026)*ASR_o*deltaW_o
Rgrowth_required_o = D_o - c_o*deltaW_o
```

Area enters these equations in m2 (cm2 multiplies by 1e-4). Negative growth or
inconsistent support returns unavailable, not a carbon credit. Demand includes
growth cost already; do not charge `Rgrowth_required` again in the supply budget.
It is a required cost, not measured respiration or realized biomass production.

## Light and environment tables

`light_series.context` declares plant, start/end, canonical interval geometry hash,
area basis, `backend` and one `replicate` string. This version integrates a
`geometry_policy="fixed_snapshot"` with a required `geometry_assumption`; it does
not manufacture future optical tissue. `patches` have unique `patch_id,organ_id`,
positive `area_weight_m2`, `optical_eligible=true`, and
`geometry_kind=measured_tissue|hypothetical_tissue`. Invented tissue requires
hypothetical mode. Tissue must be present in the initial supported state.

An explicit unique `fixture_ids` inventory is mandatory. Each sample includes
`patch_id,fixture_id,organ_id,plant_instance_id,t_start,t_end,geometry_hash,
area_basis_id,backend,replicate,area_weight_m2,ppfd_umol_m2_s,light_basis,
one_sided_area_basis=true,status=available,source_ref`. Every patch/fixture needs
complete nonoverlapping interval coverage, including true zeros. Unknown exposure
is unavailable. No mixing transport replicates or counterfactual removal cases.

`environment.records` contains plant/time, `environment_kind=measured|assumed|forecast`,
`source_ref`, `phase=day|night` when net exchange is used, and explicit required
temperature/domain fields. Temperature is deg C; CO2 ppm, pressure Pa, RH percent,
VPD kPa, EC mS/cm and pH dimensionless. Missing unused metadata is allowed.
The current NRH has no CO2/VPD/RH/EC/pH response coefficient. Domain checks can
require them without inventing a stress response. DLI alone cannot reconstruct
the time series. No ppm-to-partial-pressure substitution is performed.

Align the union of light/environment/mass-history boundaries and integrate their
explicit piecewise-constant values. Sum simultaneous fixture irradiance at each
patch before evaluating the nonlinear NRH. Sum weighted patch exchange afterward:

```text
H = 2*alpha*I*Pmax/(alpha*I+Pmax+sqrt((alpha*I-Pmax)^2+4*(1-theta)*alpha*I*Pmax))
H(0)=0
S = 12.011e-6 * sum((H-Rd_if_net)*area_m2*elapsed_seconds)
```

Absorbed PPFD already contains absorption. The pack must match incident/absorbed
basis; the code never applies an extra absorptance. Replicates are separate calls.

## Parameters and exclusive respiration ownership

The pack payload declares `schema_version,pack_id,draw_id,review_status,model_id=nrh,
light_basis,respiration_accounting,parameters,photosynthesis,organ_parameter_map,
respiration_ownership,mass_form_mapping,applicable_domain,numerics,assumptions`.
`review_status=hypothetical` needs explicit assumptions; `reviewed` needs `review_ref`
and reviewed parameter records. Both always export `accepted_for_domain=false`.

Every parameter ID maps to `{value,unit,evidence_kind,source_id,locator,cultivar,
conditions,uncertainty,applicability,review_state}`. Unknown value/uncertainty is
null, never zero. Evidence kind is measured/fitted/borrowed/assumed/unidentified.
Source facts and hypothetical declarations are preserved; the code does not
perform scientific review. Draw IDs preserve externally supplied joint parameters.

The pack also declares `scope=whole_plant|supported_leaf_subset`, matching the
requested carbon state. Incompatible or absent scope disables mass/budget terms;
independently supported leaf exchange can still be reported.

| Parameter role | Required unit |
|---|---|
| alpha | `umolCO2/umol_photon` |
| Pmax, phase Rd | `umolCO2/m2/s` |
| theta, Q10, activity, gamma | `dimensionless` |
| maintenance rate | `gCH2O/g_structural_DM/day` |
| Tref | `degC` |
| ASR | `gCH2O/g_structural_DM` |
| carbon fraction | `gC/g_structural_DM` |
| SLA | `m2/g_structural_blade_DM` |
| allometric lambda | `mm/mg^gamma` |
| activity f | `day` |

`photosynthesis` maps alpha/Pmax/theta and optional `Rd_day/Rd_night` to IDs.
`organ_parameter_map[organ_id]` maps maintenance_rate/Q10/Tref/activity/ASR/
carbon_fraction to IDs, with `activity_kind=constant|RGR5` and explicit
`temperature_metric`. Non-leaf/surrogate temperature needs `temperature_assumption`.
No implicit leaf-temperature-to-root-temperature transfer is installed.

`respiration_ownership` contains one record per scoped organ with
`maintenance=downstream|leaf_exchange` and `growth=demand`. `before_mito` requires
all maintenance downstream. In `net_leaf`, illuminated leaves must explicitly
assign their maintenance to leaf exchange and supply phase Rd. A net curve that
also charges growth respiration is refused because ASR already includes it.

Maintenance uses supplied `maintenance_history` mass records, or an explicit
`maintenance_start_mass_assumption`. Missing leaf temperature may use air only with
`air_temperature_substitution_assumption`. Formula:
`R=chi*m*W*Q10^((T-Tref)/10)*activity*dt_s/86400`.
Constant activity is a supplied parameter in [0,1] and needs no RGR5 evidence.
RGR5 requires `rgr5_scope="plant"` in each applicable organ parameter map and
separate `carbon_state.plant_rgr5_history` records. Each record declares
`t_start,t_end,plant_instance_id,rgr5_scope="plant",mass_basis="structural_dm_excluding_reserve",
whole_plant_coverage_complete=true,coverage_statement,history_complete=true,
window_days=5,source_ref,mass_at_now,mass_at_5days_ago,structural_dm_now_g,
structural_dm_5days_ago_g`. Both masses are positive whole-plant totals in g
structural DM, including root and reproductive coverage; partial organ sums are
not used. Evidence fields declare coverage, which remains the provider's
scientific responsibility. `mass_at_now` equals the activity record start and
is five elapsed days after `mass_at_5days_ago`. Activity is held constant over
the explicitly supplied record interval; no unsupplied rolling history is inferred.

`activity=-expm1(-f_day*(log(W_now)-log(W_5days_ago))/5)` must be in [0,1).
Negative RGR5 and floating-point saturation at 1 are unavailable, not clipped.
Zero activity is retained and flagged by `maintenance_activity_zero` on flux
and diagnostic rows; no basal floor is added. Organ-local `maintenance_history`
provides the organ mass multiplier only and cannot substitute for plant RGR5.

`applicable_domain` maps required environment fields to explicit [min,max] pairs.
No domain is inferred from a source's point conditions. Only hypothetical mode
can explicitly supply `domain_assumptions` in place of predicates. Numerical
policies are required: `carbon_abs_tol_gC,carbon_rel_tol,mass_abs_tol_gDM,
area_abs_tol_m2`; they are not biological acceptance thresholds.

## Status and export semantics

```text
U = reserve + S + import - export - maintenance_charged
if U < 0: maintenance_deficit; V=null, ratio=null
else V = max(U-minimum_reserve,0)
if D = 0: no_growth_demand; ratio=null
else ratio = V/D; growth_deficit = max(D-V,0)
```

Complete inputs give `sufficient` when V plus the declared absolute/relative
tolerance reaches D, otherwise `growth_deficit`. Raw ratios/deficits are retained;
tolerance application is flagged. Missing required components give global
`unavailable` while known components remain available. Never serialize infinity.
Maintenance deficit and zero demand have explicit reasons and null ratios.

Exports: `diagnostics.csv`, `component_fluxes.csv`, `availability.json`,
`coupling_audit.json`, `manifest.json`, plus `inputs.json` and `result.json` audit
snapshots. Diagnostic CSV references JSON metadata instead of flattening source
arrays. The nine contracted core fields remain unchanged. Manifest includes code,
schema, materialized/source-file/artifact hashes and unchanged P3 input hashes.
Each result retains instance/trajectory/weight, interval, draw, scope and sources.

`audit_carbon_balance(ledger, originating_diagnostic)` is a separate hypothetical check with
`reserve_start_gC,reserve_end_gC,supply_gC,maintenance_gC,growth_respiration_gC,
structural_increment_gC,external_import_gC,external_export_gC,funded=true,
hypothetical=true,abs_tol_gC,rel_tol`. A negative final reserve is rejected;
an unfunded ledger is unavailable. It does not propagate carbon to later calls.
The ledger also requires `pack_id`. The supplied originating diagnostic is verified
by recomputing its retained inputs; a bare echoed ID is insufficient. Ledger pack,
starting reserve, transfers, supply, maintenance, structural carbon and required
growth respiration must match that origin. Association tolerances come from the
originating pack, not an arbitrary ledger override. Residual tolerance remains
explicit in the hypothetical ledger. Missing associations return unavailable;
tampered diagnostics fail validation. This verifies internal provenance and
arithmetic, not the scientific authenticity of caller-supplied observations.

Each interval needs its own declared start stock. There is no timestep resampling.
Every row declares `reserve_propagation="none"` and
`interval_independence="independent_single_interval"`. A single call cannot see
other calls. Invoke `validate_diagnostic_table` or `export_diagnostic_table` for
multiple results; the `validate-table` CLI reads JSON
`{"schema_version":"p4-carbon-diagnostic-2","results":[{"path":"result.json","sha256":"<file hash>"}]}`.
It compares contiguous times within plant, trajectory, parameter draw/pack and
accounting boundary (scope, subset organ membership and boundary policy). Whole-plant
organ birth does not change that boundary; run/scenario labels do not bypass the guard. Equal non-null starting reserves require a nonempty
`carbon_state.reserve_reuse_assumption` on the later interval. The assumption is
preserved verbatim in CSV/JSON. Missing reserves remain unavailable. This does not
prove that unequal reserves are dynamically consistent, and does not validate
unseen intervals. There is no returned next reserve state.

The input schema version stays 2; the 2026-10-04 safety revision adds required
result metadata and stricter optional-path evidence. Regenerate historical
results for new export validation; do not rewrite historical evidence packages.
Old RGR5 organ histories, ambiguous multi-inverse maps and unassociated balance
ledgers are intentionally no longer accepted by their respective paths.

## Evidence limits

Software tests cover analytic identities, independent NRH expectations,
refinement, serialization, missingness and forbidden feedback. They do not validate
organ physiology, source transfer, cultivar parameters or future geometry.
D15-D18 resolve model light/respiration and CH2O maintenance conventions.
Scientific review still needs raw fit preprocessing, target applicability, source
mass/ASR reconciliation, independent allometry and initial pools.
Cross-project linking and a real four-project run remain outside this isolated
implementation. Numeric P4 is still optional in the first later synthetic pass.


## Adopted V2 policy and technical revision (2026-10-04)

D15-D18 resolve the implementation policy previously called Q2. This is distinct
from target-cultivar validation and the unresolved empirical NRH preprocessing.
The original numeric formulae and caller-supplied coefficient values are retained.
Dwarf-source model input is absorbed PPFD with before_mito respiration. Maintenance
is carbohydrate-equivalent g CH2O/g structural DM/day, using 12.011/30.026. The
historical official CSV CO2 label is retained in evidence as a label discrepancy;
D17 resolves the model convention from equation 7 and the source carbohydrate
budget. There is no 1.466 rescaling.

### Provenance and coefficient basis

Pack `source_family` must explicitly be `butturini_dwarf`, `non_dwarf`, or
`hypothetical`. Parameter records can declare their own source_family; missing
relevant provenance is unavailable (`source_family_undeclared`). No pack is
classified by its name or source-ID substring. Hypothetical arithmetic examples
are not silently classified as dwarf-source evidence. The pack and any dwarf NRH
parameter trigger the adopted absorbed-light gate. Dwarf maintenance provenance
requires supplied, evidenced Tref=25 C (`dwarf_maintenance_tref_conflict` otherwise);
25 C is never injected into missing or other-source parameters. Source Q10=2 is
recorded as source metadata, not a target default.

Each alpha, saturation and theta record requires measured_light_basis=incident
or absorbed. Missing evidence yields measured_light_basis_missing. A mismatch
with the pack emits alpha_calibration_basis_conflict and continues only while all
other evidence/domain gates pass. The issue identifies parameter_id, role,
measured basis, pack basis and source ID. Every supply flux contains the issues;
the sufficiency CSV carries issue_codes and calibration_basis_issues_json, with
full metadata in availability.json. Compound flux CSV cells are JSON encoded.
Sample/pack mismatch remains an incompatible-input error; no hidden absorptance
factor is applied. `photosynthesis.Pmax` is the saturation parameter reference;
`P_sat` is an alias referencing the same record, not a second coefficient. When
both are supplied they must be equal.

net_leaf requires both Rd_day and Rd_night with ordinary parameter evidence and
an explicit non_dwarf source family, even if the particular interval uses only
one phase. Dwarf pack/NRH evidence cannot be relabelled net_leaf. Unsupported
inputs give net_leaf_requires_rd_bearing_source. The existing ownership ledger
still charges leaf maintenance exactly once and ASR still includes growth cost.
A synthetic fixture may exercise non-dwarf Rd evidence with explicitly assumed
values; this does not claim an actual measured source or production acceptance.

### Biological face evidence

Each patch requires illuminated_faces in {adaxial_only, abaxial_only, both} and
face_source_ref naming biological mapping evidence. Missing face declaration
is illuminated_faces_undeclared; missing mapping evidence is
illuminated_faces_evidence_missing. Both is two_sided_exchange_unavailable;
abaxial_only is abaxial_exchange_unavailable. Only evidenced adaxial_only enters
exchange. The original transport intensity is not divided, clipped or relabelled.

A single fixture may inherit its explicit patch declaration. With several fixtures,
each contribution row must supply illuminated_faces and face_source_ref. All
contributions at each patch/time are checked before math.fsum and one nonlinear
NRH evaluation. Opposite-face contributions are both, hence unavailable. These
are P4 boundary requirements, not a new P2 adapter or transport algorithm.

### RGR5 and mass disclosures

The shared plant_rgr5_history remains canonical. Retained organ/spec `rgr5` or
organ maintenance_history[].rgr5 declarations must match its meaningful mass,
identity, dated-window, coverage and source-provenance payload for overlapping
intervals. Dictionary ordering does not matter. A mismatch is
rgr5_scope_inconsistent, including retained declarations on other included organs.
Constant activity requires no invented plant history.

When activity_f borrows butturini_dwarf meaning, every result discloses
rgr5_mass_basis_deviation_from_source: source total DM includes roots and buffer,
whereas P4 uses structural_dm_excluding_reserve. This is not source-equivalent
calibration; f and the P4 mass basis are unchanged. Source locators are in the new
registry/evidence: plant_level.rgg::updateBiomass uses logarithmic with-roots mass
history, while the structural-and-minimum-pool stock subtracts buffer.

An explicit carbon_state.total_dm_substitute or organ-mass total_dm_substitute
assumption activates the reported source static-branch 90-percent structural
mass / approximately 10-percent buffer caveat. This is a source assumption, not
a target-cultivar conversion. P4 does not multiply any measurement by 0.9 and
still refuses a total_dm mass basis. SLA remains strictly m2/g_structural_blade_DM;
its existing check reports sla_unit_incompatible for m2/mg without conversion.

### Reserve evidence and independent calls

reserve_gC requires carbon_state.reserve_evidence={source_ref,lineage_id}.
Missing source or lineage makes the budget unavailable (reserve_source_missing,
reserve_lineage_missing). reserve_provenance_chain_id hashes the supplied lineage
and accounting boundary (plant, scope, subset membership, boundary policy), with
no run or timestep identifier. reserve_evidence_hash separately binds the source
payload, stock_at, carbon amount and boundary. Thus new evidence can belong to the
same explicitly declared chain while changing its evidence hash; a changed
lineage/boundary changes the chain ID. Both are exported even in separate calls.
These hashes verify internal traceability, not authenticity of measurements.

The existing table guard still rejects identical reserves across contiguous
comparable intervals absent reserve_reuse_assumption. Its audit also carries
both chain IDs and same_reserve_lineage. Different IDs do not bypass the existing
equal-stock guard. Single-row calls cannot detect unseen rows, and no reserve
propagation or inferred measurements are introduced.

### Disclosures, missingness and interpretation

Every sufficiency row, including unavailable and deficit rows, exposes actual
respiration_accounting and light_basis, applicable rgr5_scope,
source_buffer_feedback=not_modelled, nonfoliar_assimilation=not_modelled,
maintenance_temperature_integration=sub_daily, and
diagnostic_interpretation=cross_cultivar_consistency_check. Missing declarations
report undeclared; constant activity reports rgr5_scope=not_applicable; invalid
or inconsistent RGR5 declarations report unsupported/inconsistent with declared
scopes in disclosure_reasons. These reporting statuses are not model-input enum
values. No physiological default is supplied to satisfy a non-null output field.

Named disclosures retain unresolved NRH preprocessing and unmodelled two-sided
exchange, sympodial continuation, light-to-orientation response and FvCB. Reserve
propagation remains none. Omitted source buffer feedback can overpredict supply
under sink limitation; this is not a blanket bias guarantee. Sub-daily Q10
integration differs from applying Q10 to mean temperature. The source comparison
of approximately 0.4 percent for a particular 22/19 C, Q10=2 schedule is
conditional, not a correction factor applied here.

Conditional source-model interpretation, preserved on every row: if an
origin-passing three-parameter curve was fitted to net data without respiration
correction, alpha/saturation and supply may be underestimated and leaf respiration
counted again. Under that specified conservative-bias interpretation ratio >= 1
is credible, while ratio < 1 alone is not evidence of carbon shortage. This is not
an unconditional adequacy guarantee; unknown light, domain, mass, reserve and
omitted processes remain independent limitations. Numeric status/ratio is not
overwritten by this interpretation.

D19 imports the single DLI_UNIT from tools.leaf_light.common. Canonical mol/m2/day
passes the read-only P3 coupling audit; legacy mol/m2/d yields
legacy_dli_unit_spelling with field/actual/expected diagnostics. It is a spelling
change, never division by 86400, and frozen historical artifacts are not repaired.
The audit also recognizes P3's explicit below-base zero-response knot.

New scientific requirements are checked in runtime and return structured
unavailable; malformed enums, unit-incompatible light samples, alias conflicts
and corrupt provenance remain errors. Schema definitions declare new evidence
fields but do not reject missing scientific fields before runtime can explain
them. Request schema stays p4-carbon-diagnostic-2 with a dated V2 safety revision;
regenerate previous result objects instead of rewriting historical evidence.


## Area review boundary revision (2026-10-05)

The additive metadata contract is `p4-area-evidence-1`; the request schema remains
`p4-carbon-diagnostic-2`. Existing explicitly hypothetical V2 fixtures retain their
arithmetic and are labelled hypothetical. A legacy measured_tissue declaration
alone no longer qualifies supply: missing physical area or anatomical face evidence
returns unavailable. `accepted_for_domain` and `physical_area_validated` remain false;
passing a declaration check does not authenticate a source or validate a plant.

Supply accepts `area_weight_m2` only, in both patch and sample records. A cm2 alias or
an incompatible area_unit gives area_unit_incompatible, never guessed conversion.
The rate is umolCO2/m2/s, multiplied once by the corresponding patch m2, elapsed
seconds and 12.011e-6 gC/umolCO2. There is no G, imaging occlusion lambda, curvature,
extra absorptance, doubled mesh, or extra respiration multiplier. All simultaneous
fixtures are still summed before one nonlinear exchange evaluation per patch/time.

Each measured patch requires `area_evidence` with:

- schema_version=p4-area-evidence-1, quantity=physical_one_sided_lamina,
  status=supported, spatial_support=located_tissue_partition, unit=m2 and value
  exactly equal to area_weight_m2.
- Exact plant_instance_id, organ_id, patch_id, area_basis_id and geometry_hash.
- source_ref, source_sha256, source_row_id, and support_source_ref identifying the
  independent support review. Metadata is a claim to audit, not proof of accuracy.
- tissue_partition_id, partition_source_ref and partition_sha256 identifying a
  reviewed disjoint partition. Duplicate partition IDs or duplicate source/hash-row
  pairs are refused even with distinct patch IDs. Overlap concealed by fabricated
  IDs cannot be detected from scalar metadata; P1 must actually review geometry.

Explicit projected_proxy, hull_surface, hull_envelope, two_face_mesh and A1 whole-
plant methods, unsupported quantities/statuses and proposed/unvalidated estimators
are refused with physical_area_unsupported. Missing fields give
physical_area_evidence_missing or tissue_partition_evidence_missing; a wrong tissue,
geometry or basis association gives area_identity_mismatch; duplicate tissue gives
 duplicate_tissue_partition. Whole-plant totals cannot allocate spatial area/light
support for nonlinear patch exchange. No estimator from area_review_A1..A7 is
implemented by this boundary check.

For measured tissue, biological_face_evidence requires kind=observed_anatomical_mapping
or reviewed_anatomical_mapping, face=adaxial, exact plant_instance_id and organ_id,
source_ref matching face_source_ref, and source_sha256. An unsigned normal, mesh
winding or top projection fails illuminated_faces_evidence_missing. Existing
illuminated_faces and contribution-exposure checks still apply; both faces remain
unavailable. Legacy hypothetical fixtures use their explicit invented face mapping;
if additional contradictory biological evidence is supplied it is checked.

Area inverses accept supported_area_cm2 only and convert once with CM2_TO_M2=1e-4.
Supply m2 fields are never converted again. Real endpoint support is supplied as
`p3_interval.area_evidence_start[organ_id]` and `area_evidence_end[organ_id]`, using
unit=cm2, spatial_support=organ_lamina, the exact endpoint value and corresponding
geometry_hash_start/end plus plant/organ/basis/source/support fields above. Keep
these maps OUTSIDE organ_states_start/end: those complete state arrays are hashed,
so embedding their own geometry hash would be self-referential. Existing hypothetical
parameter packs retain explicit diagnostic inversions unless an endpoint declares
non-hypothetical geometry or supplies contradictory evidence. Endpoint checks do
not replace compatible blade structural DM, independently supported positive SLA,
primary-inverse agreement, ASR or mass provenance. Area cannot create roots, reserve,
total DM, length/width, or future organ demand. Supplied evidence and hypothetical
fallbacks are recorded in demand rows as area_support; direct mass increments use
an empty list, since no area inverse was used.

P4 remains a single-plant consumer. All sample plant/organ/patch/geometry/basis and
fixture joins are exact; optional patch context cannot contradict the selected
plant. For canopy illumination set light_scope=canopy and canopy_provenance with
canopy_id, unique plant_instance_ids including the selected plant, full-canopy
geometry_hash, source_ref and source_sha256. Every selected sample must retain
canopy_id and canopy_geometry_hash. Missing lineage gives canopy_provenance_missing;
wrong membership/source geometry gives canopy_identity_mismatch. This does not
implement splitting or transport: P2 supplies an identified slice and preserves
whole-canopy provenance. P4 does not sum multiple plants' reserves or maintenance.

Supply rows now retain plant ID, geometry/basis, tissue partition, area_support,
canopy_provenance and each contributing fixture/source/sample hash. CSV compound
cells are JSON. Every sufficiency row includes area_evidence_contract,
area_evidence_status (hypothetical/supported_declaration/unavailable),
physical_area_validated=false, area_support_json and canopy_provenance_json.
Missing supply/face/mass stays unavailable, with null carbon/ratio where dependent,
never zero or an inferred biological shortage. Complete input hashes and JSON
preserve source row lineage; table export recomputes inputs and retains reserve
reuse checks. Real biological validation remains independent of these contracts.

The source proposal is namespaced area_review_A1..A7. G=0.50, quantile tau=0.9,
low-dilation depth, curvature and source-reported synthetic errors remain unadopted.
The existing analytic audit spans approximately G=0.472–0.550 over its six families
and selected zeniths, not measured accuracy. Unknown occlusion prevents absolute
area identification without justified bounds; |n dot v| cannot distinguish n from
-n; area and two angles cannot locate a lamina for ray casting. The three estimator-
priority, matching and calibration decisions remain open. See the new P4 execution
report and versioned registry addendum for the corrected evidence and dependencies.
