# Proposed FSP physiology contract v1

Date: 2026-10-03. Author: Codex, executing the user-selected physiology prompt.
Scientific review: pending Claude/human review. The filename is the requested
deliverable name, not a claim that Claude authored or approved it.

Status: mathematical/interface specification and evidence recovery completed;
production physiology module not implemented; biological acceptance unavailable.
Existing growth/calibration behavior remains the comparator. This contract extends
the earlier physiology exclusion only for a separate, explicit future mode.

Integration precedence: the newly inspected coordination record
`CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` assigns realized geometry
to P3 and P4 to diagnostics, with linking deferred. Section 10 below constrains
all proposed integration actions accordingly. Sections 4-5 retain the requested
isolated physiological accounting/form equations as counterfactual definitions;
they do not authorize a second realized-growth engine or feedback to P3.

Evidence pack: `build/fsp_physiology_spec_20261003_01/`. Individual records in
`source_registry.json`, `equation_registry.json`, and `parameter_candidates.json`
retain units, source locations, applicability, uncertainty and unresolved conflicts.
All numeric literature values below are candidates, never installed defaults.

## 1. Decisions and evidence

| Candidate | Inspected evidence | Proposed decision and limits |
|---|---|---|
| Nonrectangular hyperbola (NRH) | Butturini et al., diaf024, pp.5-10, equations 5-18; complete WUR PDF and pinned official code | Primary conditional model for a narrow light/temperature/CO2 domain. Few identifiable response parameters. The source's respiration and absorbed/incident-light interpretations need reconciliation before using its fitted values in a physical balance. |
| Linear light response | Low-light tangent of the same NRH | Simpler comparison only inside independently declared low-light domain; never extrapolate a linear curve to saturating irradiance. |
| FvCB | Farquhar et al. 1980, equations 1 and 9 and electron-transport sections; complete paper | Deferred comparison. Missing chloroplast CO2, biochemical capacities and conductance/temperature-response evidence make a full model unidentifiable here. No fixed Ci/Ca or Ca=Cc shortcut. |
| Existing CompoundLeaf growth | Inspected current engine and separate calibration adapter | Preserve as baseline. It predicts geometry, not an organ carbon balance. Its light-response coefficients must not also drive the same expansion variable in physiology mode. |
| Tomato digital twin | diaf022, cached institutional full text, section 2.3 | Supports testing rank/stage dependence and separate development/geometry responses. Merlice coefficients cannot establish this target dwarf cultivar's allometry. |
| TOMSIM/TOMGRO and TGFS | TOMSIM full thesis recovered, chapter 4.2 equations 1-2 and Table 1 inspected; TOMGRO abstract; TGFS access attempts recorded | TOMSIM corroborates CH2O cost conventions. Context only for inaccessible alternatives; never fill coefficients from memory. |

Primary source: https://edepot.wur.nl/708598 (DOI 10.1093/insilicoplants/diaf024).
Official implementation: https://github.com/Micbut/FSP-model-dwarf-tomato,
commit `2d727a3364f87392b3f8b74d8ff7127cc5090c3a`.
The paper uses cv. Heartbreakers F1 Twiggy Red, not a confirmed identity for the
user's plants. Photosynthetic measurements used three plants, mature rank-3 leaves,
approximately 23 degC, CO2 partial pressure 798 microbar, 50:50 red:blue chamber
light, and 0-2000 umol photons m-2 s-1. These conditions do not identify separate
temperature, CO2, water, age, spectrum or VPD responses.

### Source inconsistencies that must remain visible

1. Paper equations 15-16 print growth respiration as `ASR*A` and subtract it
   from assimilates, although Table 1 gives ASR > 1 in gCH2O/gDM. That expression
   is not a dimensionally valid conversion to structural mass. Official
   `organs.rgg` lines 300-307 instead divides allocated substrate by ASR.
   This proposal adopts the dimensional conversion below, not the printed pair.
2. Table 1 gives root/fruit ASR 1.39/1.37, while the pinned input CSV labels
   fruit/root 1.39/1.37. Preserve both candidates; do not choose automatically.
3. Paper maintenance units are gCH2O/g structural DM/day; CSV comments say gCO2/g
   plant biomass/day. Carbon conversion and mass basis depend on this difference.
   Heuvelink's reproduced 1995 Table 1 (thesis printed p.109 / PDF p.114)
   confirms CH2O and the paper's root/fruit ordering. It labels mass simply DM,
   so the structural-versus-reserve mass interpretation still needs review.
4. The activity coefficient `f=33` is printed dimensionless, but `f*RGR` requires
   days when RGR is day^-1. Record dimensional correction as proposed, not quoted.
5. Source NRH has no Rd intercept but was fitted to gas-exchange observations;
   source light is called absorbed whereas the chamber reports incident PPFD.
   Recover fitting/absorptance/respiration preprocessing before interpreting its
   `27, 0.06, 0.7` as before-mitochondrial parameters.
6. Source equation 8 clips negative daily carbon to zero. It cannot represent
   depletion. This contract keeps signed budgets and stops when its declared
   physiological domain is exhausted. Equation 9's displayed hour/micromole
   conversion is incomplete; official code includes photoperiod*3600.
7. Paper allometry says structural mass; some code uses structural plus minimum
   pool. Code SLA applies to blade mass, not the full compound including rachis.
   Never apply blade SLA to all CompoundLeaf mass.

These are explicit review items, not silent edits to the source or existing model.

## 2. Canonical state and accounting

Version: `fsp-physiology-1`. Internal time is seconds; biological development time
is a separate labelled clock. Internal stocks/flows use gC. Structural dry mass
uses gDM, true one-sided area m2, lengths mm, angles radians internally/degrees in
files. Every scalar has a unit and evidence status. Missing = null plus reason.

For each plant maintain reserve `B_gC >= 0` and disjoint organ structural masses
`W_o_gDM >= 0`. Each organ has fixed structural carbon fraction `c_o_gC_gDM` for
this version, `0 < c_o <= 1`. Structural carbon `C_o=c_o*W_o`. Composition changes
need a new explicit transfer ledger and are unsupported here. Pool membership is
exclusive: a leaf blade, petiole and rachis cannot be counted both separately and
again in a compound total. Compound totals are aggregations only. Include roots
as nonvisual masses. Reproductive pools are required when present; omission is
allowed only by a documented nonreproductive stage assertion.

Use `kC=12.011e-6 gC/umolCO2`. For the declared carbohydrate equivalent CH2O,
`chi=12.011/30.026 gC/gCH2O`. The molecular-mass convention is recorded in the
pack. It is not a biological carbon-fraction estimate. CO2 mass converts with
`12.011/44.009`; gDM requires biological `c_o`, and fresh mass is unsupported
without an independent dry-matter fraction. Area: cm2*1e-4 or mm2*1e-6 -> m2.

Total plant carbon `Cplant=B+sum(c_o*W_o)`.
If displaying total dry mass under an explicit CH2O reserve composition,
`DMtotal=sum(W_o)+B/chi`. Never add B again to each organ. Do not use DMtotal as
structural mass in maintenance, allometry or potential-growth equations.

### Respiration ownership: exclusive modes

Selected route: `before_mito`. Photosynthetic input `P_b` is after photorespiration
and before mitochondrial respiration. Leaf/stem/root/reproductive maintenance
and growth respiration are each charged exactly once downstream. NRH has no Rd
subtraction in this route. Its coefficients must be fitted/reconciled for this
definition. Photorespiration is not subtracted again.

Alternative input route: `net_leaf`. Signed leaf exchange includes explicitly
listed leaf respiratory components, each with phase, organ IDs, rate basis and
source. Downstream excludes precisely the overlapping components. A vague
`net=true` flag is insufficient. This version accepts this route only when an
accounting review identifies whether leaf maintenance and/or growth respiration
are included. If matching net leaf exchange includes maintenance but not growth,
exclude leaf maintenance and retain leaf growth costs. If it also includes growth
respiration, a cost convention that already charges that carbon is incompatible;
return `respiration_overlap_unresolved` until a partitioned model is supplied.
Do not assume Rd equals the organ maintenance coefficient. Adding back Rd is
allowed only for the same model, interval and organ and an approved replacement
budget; never reconstruct gross exchange from a different paper's Rd.

The net route must cover darkness with signed observed/modelled dark leaf
exchange. In the selected before_mito route P_b=0 at lights-off and maintenance
continues. A light-only calculation is a subdaily balance, never a full day.

Conservation per plant, interval and trajectory:

```text
B_next-B + sum(c_o*(W_next_o-W_o))
 = S_gC - Rmaint_charged_gC - Rgrowth_charged_gC
   - export_gC + import_gC
```

`S` is signed if the net route is used; absorbed photons themselves are not carbon.
Internal allocations cancel. Neighbors affect light but share no carbon pool.
Harvest, abscission and exudation are disabled only by explicit retained-organ,
no-export stage assumptions; otherwise demand measured/prescribed export records.
Remobilization and starvation mass loss are unsupported, not inferred defaults.

An observation update is a state-estimation correction `analysis_delta_gC` in a
separate ledger. It is never photosynthesis or a physical import. The physical
balance is evaluated within each forecast segment; changes between posterior
origins are audited separately against analysis_delta.

## 3. Exchange equations and domains

For each nonoverlapping receiving patch j, define absorbed PPFD `I_j >= 0`,
one-sided supported area `a_j`, and before-mito exchange rate:

```text
H(I) = [alpha*I + Pmax - sqrt((alpha*I+Pmax)^2-4*theta*alpha*I*Pmax)]/(2*theta)
     = 2*alpha*I*Pmax / [alpha*I+Pmax+sqrt((alpha*I+Pmax)^2-4*theta*alpha*I*Pmax)]
P_b,j = H(I_j)
S_gC = kC * integral(sum_j(P_b,j(t)*a_j(t)), dt_seconds)
```

Use the stable second form; H(0)=0. Require Pmax>0, alpha>0 and 0<theta<=1.
alpha has units umolCO2/umol absorbed photons, Pmax umolCO2/m2/s. Photons cover
400-700 nm PAR unless an independently calibrated alternate basis is declared.
If fit on incident light, record `light_basis=incident` and use matching incident
PPFD; never apply absorptance both to light and quantum yield. Converting an
incident slope to absorbed basis requires measured compatible absorptance
(`alpha_abs=alpha_inc/absorptance` for a constant scalar), including spectral
and side convention. This conversion is unavailable for the current real plant.

The optional fitted net curve is `A_n=H(I)-Rd_phase`, with an explicit compatible
Rd/night model and ownership ledger. It is not obtained by renaming the source H.
The simple comparator is `P_b=alpha*I` within its declared low-light domain.

The selected supply module includes leaves only. Ignoring nonfoliar assimilation
must be an explicit reviewed stage approximation or sensitivity scenario; otherwise
the missing component prevents a complete physical whole-plant claim. The source
factor 0.3 is an assumption and is not silently replaced by measured zero.

Compute patch nonlinear responses before aggregation. If only leaf/compound mean
PPFD is available, `area*H(meanI)` is a labelled uniform-light approximation.
Store aggregation bias as unknown until tested with finer receivers; it cannot
be called exact integration. Sum concurrent fixtures before H; sum samples after
H. Do not sum counterfactual/Shapley quantities or random replicates as physical
light. Each optical replicate is a separate scenario/uncertainty realization.

No automatic T/CO2/VPD/EC/pH/stress multiplier. Require declared valid T/CO2 ranges
or a fixed-condition sensitivity scenario. Outside range => unavailable with
timestamp/patch reason. Temperature is leaf temperature; an air substitution is
explicitly assumed. Ambient `co2_ppm` is not the paper's CO2 partial pressure
without total pressure. Paper-fit conditions do not establish a tolerance band.

For each step use start-state areas and midpoint forcing (piecewise-constant
forcing is exact on its declared intervals). Split at forcing boundaries,
lights-on/off, appearance and externally scheduled export/import. Gaps never
become zeros or interpolated data. Zero area is legitimate only for confirmed
absent tissue; unknown area produces unavailable exchange. Partial tissue gives
partial supply only, never whole-plant carbon. A full-output light snapshot needs
an explicit time/scenario mapping before daily integration.

FvCB comparison definitions: `A=Vc-0.5*Vo-Rd`; with compatible chloroplast CO2/O2
partial pressures, `Wc=Vcmax*Cc/[Cc+Kc*(1+O/Ko)]`, and with `phi=Vo/Vc`,
`Wj=J/(4+4*phi)`, `Vc=min(Wc,Wj)`. These are the inspected foundational forms,
not an executable modern FvCB pack. Missing Rubisco specificity/phi, capacities,
electron transport, temperature dependence, conductances and pressure conventions
preclude deployment. TPU is inactive. No ambient-to-chloroplast equality assumed.

## 4. Maintenance, demand, allocation and deficits

Maintenance coefficient `m_o` is gCH2O/g structural DM/calendar day at Tref.
Convert every interval, including night:

```text
Rmaint_o_gC = chi * m_o * W_o * Q10_o^((T_o-Tref_o)/10) * activity_o * dt_s/86400
activity_o = 1-exp(-f_day*RGR5_per_day)    [source-derived optional form]
```

Require nonnegative finite RGR5, positive prior structural mass and complete
preceding five-calendar-day history for that activity form. Proposed exact RGR
definition: `(log(Wplant(t))-log(Wplant(t-5 days)))/5`, excluding reserve and
correcting declared exports. This definition is a reviewable adaptation, not a
claim about the source's unpublished history calculation. Negative/undefined RGR
returns `activity_model_out_of_domain`; it must not imply negative respiration.
The baseline option `activity=1` is a separately declared assumption, not an
automatic fallback. There is no extra leaf Rd in before_mito mode.

Thermal organ age `tau` is independent of forecast elapsed days:
`delta_tau=integral(max(Tdev-Tbase,0),dt_s)/86400` in degC day, valid only for the
reviewed temperature range and declared sensor basis. Source uses daily means;
the subdaily positive-part version is a proposed adaptation requiring comparison.
Keep organ initiation/birth age and degree-day origin; no reset at observation.
Below-base development pause is explicit; above-domain stress is unsupported.

Potential structural growth (source beta curve with corrected exponent):

```text
G(tau)=0                                      tau<=0
G(tau)=Wmax*(1+(te-tau)/(te-tm))*(tau/te)^(te/(te-tm))  0<tau<te
G(tau)=Wmax                                   tau>=te
delta_Wpot_o=G(tau_next)-G(tau) >= 0
```

Require `Wmax>0, 0<=tm<te`, all ages in the same thermal clock. Wmax is potential
structural mass, not the current measured mass. For an existing organ remaining
potential is `W_anchor + G(tau)-G(tau_anchor)`; do not replace W_anchor with G.
Proposed v1 follows interval potential demand without deferred catch-up; missed
growth is not automatically recovered. That is a source-style hypothesis to test,
not evidence that biological sink strength is permanently lost during shortages.

One growth-cost convention only. Let `q_o` be ASR gCH2O/g structural DM and
`Y_o=1/(chi*q_o)` gDM/gC. Required substrate `D_o=chi*q_o*delta_Wpot_o`.
If growth receives F_o gC:

```text
delta_W_o=F_o/(chi*q_o)
Rgrowth_o=F_o-c_o*delta_W_o
```

Require `0<c_o<=chi*q_o`, or equivalently `c_o*Y_o<=1`. If incompatible, reject
the parameter pack. The above residual leaves only as respiratory carbon in v1;
other biochemical losses require a separate flux. Do not subtract `(q_o-1)` as
gC or multiply realized mass by an additional yield. Published ASR does not
identify c_o. Source source-code division establishes substrate/mass conversion,
not independently measured carbon fractions.

Root potential demand must have its own trajectory, or a reviewed explicit
scenario `delta_Wroot_pot=froot/(1-froot)*sum(delta_Wvegetative_aboveground_pot)`.
`0<=froot<1`, excludes fruit and truss reproductive masses. Source froot=0.1 is
borrowed from cucumber-related work, not a measured target-dwarf root fraction.
Roots must have measured/assumed initial mass and respiration even without 3D.

Per step, `R=sum(Rmaint charged here)`, `U=B+S+import-export-R`.
If U<0 beyond numerical tolerance, return `carbon_deficit`, unmet maintenance
`-U`, previous valid state and failure interval. Do not commit a clipped next
state or call the full interval simulated. No tissue catabolism is invented.
Locate failure by grid refinement if a depletion time is reported.

With U>=0 and explicit minimum reserve `Bmin>=0`:
`V=max(U-Bmin,0)`, `D=sum(D_o)`, `F_o=D_o*min(1,V/D)` for D>0; F_o=0 for D=0.
Then `B_next=U-sum(F_o)`. Maintenance can draw below Bmin; growth cannot. Every
organ respects its potential cap. If carbon exceeds sinks it stays in reserve.
No epsilon sink, deletion of excess, cross-plant sharing or arbitrary mass weight.

Require an explicit `capacity_policy`: `unbounded_scenario` (assumed, report
scope) or `finite_stop` with Bmax>=Bmin; B_next>Bmax yields
`reserve_capacity_exceeded` with no committed transition. Source buffer feedback
thresholds are recoverable scenario candidates but are not activated in v1.
They have no validated target-C stock conversion. Overflow is not respiration.

## 5. Structural mass to measured form

Primary proposed bridge is anchored, stage-indexed allometry; fit and test it
against the separate-expansion alternative. For variable blade SLA `s(t)` in
m2/g structural blade DM:

```text
A(t)=A_anchor + [s(t)*Wblade(t)-s(t_anchor)*Wblade_anchor]
delta_A=s_next*Wblade_next-s_now*Wblade_now
```

The second term is essential: variable SLA can change area at constant mass.
It represents a structural/expansion relationship, not new carbon. Origin area
is exact; inconsistency with unanchored literature values is reported as an
initialization discrepancy. Nonpositive predicted area or unsupported shrinkage
returns unavailable; no clipping or automatic senescence. s(t) must be positive,
source/domain linked and independently supplied; no unseen rank interpolation.

Source density-only example (code, not a generic constant):
`SLA_mm2_per_mg=0.11858*density_plants_m2+17.57084`;
`s_m2_per_g=0.001*SLA_mm2_per_mg`. At source density 50 this is 0.02349984 m2/g.
It applies to blades, with full-compound allocation fractions separately required.
It does not establish age, rank or LED acclimation responses for current plants.

For a length/diameter dimension x in mm, and compatible organ mass W in gDM:
`h(W)=lambda_mm_per_mg_gamma*(1000*W)^gamma`.
`x(t)=x_anchor+h(W(t))-h(W_anchor)`. lambda's units depend on gamma; switching
mg to g without `1000^gamma` changes the model. Geometry at t0 is copied exactly.
Source internode lengths have rank-dependent coefficients (pack); petiole and
rachis cannot be equated without suborgan mass definitions. This v1 proposes no
volume/density conversion because no applicable dry density is established.

Leaf length/width alternative: if a reviewed shape family supports
`A=k_shape*L*width` and ratio `r=L/width`, then
`L=sqrt(A*r/k_shape)`, `width=sqrt(A/(k_shape*r))`, in compatible metric units;
anchor increments separately. k_shape and r need evidence. Paper's ratios 1/2
and flat-leaf assumptions are not a universal area-to-CompoundLeaf envelope map.
Absent a reviewed shape/mass partition, area may be computed while extents and
rachis remain unavailable. Hydration-driven changes are not dry-mass increments.

Direction and appearance stay with the existing event/rotation subsystem. Carbon
does not select light-facing angles. Physiology overrides size only; do not also
apply the empirical light multiplier to potential demand/allometry. An optional
residual hybrid needs a separate identifiable joint fitting contract, inactive here.

Births require material: either (a) an explicit pre-existing bud mass transfer
from a tracked bud compartment with matching carbon, or (b) fully funded new
structural mass using the same growth cost. The event stays at its exogenous time;
if material cannot fund its prescribed initial geometry, return
`birth_mass_unfunded`. Do not delay appearance or create zero-cost tissue without
a new scientifically reviewed rule. A transfer cannot create geometric area
beyond its reviewed mass/form mapping. No new optical tissue is generated.

## 6. Exact proposed interfaces

These functions do not yet exist. Add an isolated `tools/fsp_physiology.py` and
`tools/tests/test_fsp_physiology.py` only in the later implementation task. Version
its CLI and outputs separately; never silently reinterpret the old model schema.

Common IDs: `run_id,trajectory_id,plant_id,organ_id,organ_kind,compound_id(optional),
parent_id,observed_at,frame_id,parameter_pack_id,scenario_id`. Plant instance ID
from light data needs a confirmed map to plant_id; cloned canopy instances are
not automatically independently measured plants. Every evidence reference is
`{path,sha256,locator,status}`. All timestamps are timezone-aware ISO8601.

State JSON fields and conditional requirements are defined in organ_state_schema.
CSV light columns: `plant_id,organ_id,patch_id,t_start,t_end,area_m2,
ppfd_absorbed_umol_m2_s,ppfd_incident_umol_m2_s,light_basis,coverage_basis,
quantity,replicate,geometry_hash,source_hash,status,reason`.
Exactly the selected PPFD column is required. `quantity=physical_full`; all
fixtures are aggregated once. No duplicate patch intervals or tissue overlap.
Environment CSV: `plant_id,t_start,t_end,leaf_temperature_c,air_temperature_c,
temperature_basis,co2_ppm,pressure_pa,environment_kind,status,source_hash`.
Required fields follow the active model; unused RH/EC/pH metadata has no response.

Parameter pack JSON: `schema_version,pack_id,model_id,respiration_accounting,
light_basis,applicable_domain,stage_scope,parameters,source_registry_ref,
organ_parameter_map,uncertainty,review,numerics,capacity_policy,initial_state_refs`.
Each parameter has `value,unit,evidence_kind,source_id,locator,uncertainty,
applicability,review_state`; null coefficients disable the dependent calculation.
Uncertainty contains joint parameter particles/weights or explicit fixed values;
no zero SD is substituted for unknown uncertainty. Keep shared covariance across
organs/dates, and distinct measurement/process/parameter/scenario uncertainties.

| Function | Exact input contract | Returned fields/invariants |
|---|---|---|
| audit_physiology_inputs(origin, light_series, environment, parameter_pack) | Immutable objects or hashed file manifests; state and tables above | `status,eligible_components,issues[{component,reason,ids,interval}],source_hashes`; no execution, modification or default filling |
| compute_leaf_exchange(leaf_state, light, environment, photosynthesis_parameters) | One plant/organ/step, disjoint supported patch areas, matching light basis/domain, scalar/joint-particle coefficients | `patch_rates_umol_co2_m2_s,organ_rate_umol_co2_s,exchange_basis,included_respiration_components,coverage_basis,status`; signed rates; integration done once by caller |
| compute_respiration(organ_states, environment, accounting_policy, dt_s) | Start-state structural masses, organ-specific m/Q10/Tref/activity, ownership list | `maintenance_by_organ_gC,total_charged_gC,excluded_components,status`; positive costs, no growth respiration in this function |
| allocate_carbon(carbon_state, organ_demands, cost_parameters, dt_s) | B, already integrated S/R/import/export, Bmin/capacity, D_o_gC, q/c_o | `allocations_gC,mass_increments_gDM,growth_respiration_gC,reserve_next_gC,unmet_maintenance_gC,status`; no state commit on deficit/overflow |
| update_form(measured_anchor, prior_state, mass_increment, development, allometry) | Same organ identity, anchor geometry/mass/age, cumulative mass, explicit compatible maps | `geometry,initialization_residual,availability,optical_eligible=false`; anchored dimensions, independent direction, no source edits |
| advance_physiology(state, inputs, parameters, dt_s) | One canonical step or requested enclosing interval; canonical internal grid and particle ID | `next_state,flux_ledger,event_ledger,status,available_until`; atomic step; only valid state committed |
| audit_carbon_balance(previous_state, next_state, flux_ledger) | All plant pools including roots, same composition, actual committed flux | `residual_gC,tolerance_gC,passed,per_plant`; analysis corrections excluded and audited separately |

Additional proposed pure helpers: `potential_demand`, `query_physiology_trajectory`
and `export_physiology_run`. CLI `templates|audit|simulate|check-balance` requires
fresh build paths. Simulation is explicit; audit/forecast never starts fitting or
light tracing. Invalid schema, negative dt, unit/identity mismatch => hard error.
Missing scientific inputs => component unavailable with reason. A null result
must not disappear from coverage denominators.

Flux ledger CSV: common IDs + `t_start,t_end,photosynthetic_supply_gC,
maintenance_charged_gC,growth_respiration_gC,import_gC,export_gC,
reserve_before_gC,reserve_after_gC,structural_before_gC,structural_after_gC,
balance_residual_gC,status`. Separate organ allocation, appearance and analysis
correction CSVs. Manifest records command, environment, hashes, model version,
seed, numerical policy, limitations and independent-acceptance status.

## 7. Integration and numerical protocol

Read-only inspected integration map is machine-readable in integration_map.json.
Existing `prepare_origin` supplies measured-state/identity checks;
`sample_forecast` supplies event/direction trajectories;
`decode_trajectory` supplies the old comparison and direction/attachment queries.
Do not mutate its analytic latent parameters to masquerade as carbon integration.
New mode uses a separate integrated trajectory representation and explicit adapter.
Old `supported_area_cm2` converts only with the same supported tissue/identity;
`estimated_total_area_cm2` and envelope extents never manufacture missing tissue.

`growth_calibration` currently fits anchored_expansion, azimuth_rotation and
lognormal_wait. Its evidence fields can be reused through a versioned adapter,
but physiological likelihoods/units/demands are unsupported. A future fit module
needs its own `physiology-fit-1` plan, independent gas exchange/respiration/mass
targets and review. Fitting all rates and allometry to a few photos is forbidden.

`hierarchical_light.aggregate_receivers` reports area and quantity-dependent
`full_umol_s/full_umol_m2_s` in counterfactual aggregates. Select physical full
configuration plus absorbed quantity at disjoint receiving tissue; do not sum
plant counterfactual summaries. `plant_light_bridge.audit`, `connect` and
`result_tables` retain existing optical reviews, placement and source hashes.
Their schedules/snapshots do not supply a complete physiology forcing history.
Native/angular hooks belong to the core owner; this spec requests no core edit.

Future size envelopes remain `optical_eligible=false,suitable_for_ppfd=false`.
Implementable first mode is fixed-light/external-light scenario physiology with
explicit validity interval. A dynamic geometry-light-growth loop additionally
requires reviewed future metric tissue and updated occlusion, which this contract
does not supply. Do not extrapolate a present partial receiver set to new leaves.

Canonical internal grid is anchored at origin with explicit `max_step_s`, plus
all forcing/event discontinuities. It is independent of requested output dates.
Use fixed seeds keyed by trajectory/organ/component; sample parameter particles
once per trajectory, not per query/step. Start-state explicit Euler for masses,
midpoint forcing for rates; thermal and potential increments on step boundaries.
Outputs between integration nodes use documented interpolation of stored valid
states (piecewise linear stocks, existing analytic directions); output requests
never cause extra integration steps or fresh random draws. Ledger audits apply
at committed nodes; partial-step outputs are labelled interpolated, not new flux.

Numerical tolerances are explicit required fields, not biological thresholds:
`balance_abs_gC,balance_rel,geometry_abs_mm,area_abs_m2,convergence_abs,
convergence_rel,max_step_s`. Conservation acceptance is
`abs(residual)<=abs_tol+rel_tol*max(abs(C_before),abs(C_after),abs(total_flux))`.
Reject nonfinite states and incompatible units before tolerance checks. Test h,
h/2,h/4 with the same event/forcing/particle draws. Publish maximum per-state
differences and whether the declared convergence thresholds are met. A passed
floating-point identity is not physiological accuracy.

## 8. Evidence gaps and independent validation

Source-recovered candidates include NRH 27/0.06/0.7; maintenance leaf/stem/root/
fruit 0.03/0.015/0.01/0.01 gCH2O/gDM/day at 25 degC; Q10=2; ASR values; beta
organ growth and multiple allometry coefficients. The full pack keeps conflicts,
reported versus inferred units, unspecified uncertainty and transfer limits.

| Calculation unavailable now | Exact minimum additional evidence |
|---|---|
| Absolute leaf carbon exchange | Confirmed physical leaf IDs; metric nonoverlapping tissue area and scope; compatible time-resolved light; reviewed absorbed/incident and respiration interpretation; gas-exchange response/domain for target or explicit borrowed scenario |
| Whole-plant carbon balance | Above plus complete organ inventory, separate root mass, initial structural masses and reserve, carbon fractions and compatible growth yields, night costs, import/export/stage policy |
| Thermal potential demand | Organ birth/thermal-age origin, T history, reviewed beta parameters and temperature domain, root/reproductive demand definition |
| Mass-to-form | Paired compatible mass/area/dimensions or suitable published reference by organ/rank/stage; blade versus support mass allocation; initial measured anchors |
| Target-specific response fitting | Repeated state/exchange data with measurement errors; actual varied exposure; independent treatment assignment units; frozen identifiable fit plan |
| Accuracy gain | Independent later plants/cultivation units, matched environmental information and 7/14/21/30-day targets where supported; predefined practical thresholds |

Dimensionless first-leaf image ratios do not meet the first row. No repeated
search for already-confirmed missing local measurements is requested. Prefer
published/separately collected references compatible with the non-destructive
project; this contract does not authorize destructive harvesting or new experiments.

Validation separates exchange, respiration, allocation/mass and geometry. Freeze
train/model-selection/final-test splits by plant and true cultivation/treatment
unit, preserve chronology and observation noise. Compare current FSP, linear
low-light supply, NRH physiology, and allocation/allometry ablations on identical
available environment and origins. Compare FvCB only after its inputs are
identifiable. Measure area/length/position/mass and supported direction/count
errors, probabilistic coverage and proper scores; report missingness and eligible
denominators. Block-bootstrap independent units when supported. No result is
accepted on complexity or synthetic parameter recovery.

Software checks and experiment/measurement prerequisites are enumerated in
validation_plan.json. Practical accuracy limits are null pending an evaluation
owner's declared use case; this is a scientific acceptance gap, not a software
conservation tolerance. Label sensitivity ranges assumed unless calibrated.

## 9. Owner-specific next implementation

1. Claude/human: review the explicit source conflicts, respiration/irradiance
   ownership, RGR definition, demand/catch-up/deficit policy, mass partition and
   anchored allometry. Approve a versioned applicability/parameter pack or retain
   assumptions as scenario-only. Review experimental contrasts and thresholds.
2. Codex: in a separate authorized implementation stage, add the isolated APIs,
   schema validator, balance ledger, synthetic checks and fixed-light scenario
   CLI. Integrate only through a new explicit mode; preserve old defaults and
   the completed growth-calibration files. No cross-session edits.
3. Core owner: only if subsequently authorized, expose required eligible tissue
   receiver/time outputs through existing light contracts. No new tracer or
   conversion of predicted envelopes into leaves.
4. Human/reference provider: supply actual state/forcing/reference evidence or
   explicitly choose a labelled assumption scenario. No biological defaults are
   implied by this handoff.

`worked_example.py` and `worked_example.json` in the evidence pack demonstrate
only dimensional conservation with invented, explicitly synthetic states. They
are not a fitted physiology engine or validation of dwarf-tomato growth.

## 10. Coordination compatibility: P4 diagnostics, P3 realized growth

The coordination record was found during the final LOG check. Its D1-D4 specify
P3 ownership of realized increments, diagnostic-only P4, deferred linking and a
first integration based on synthetic unit/identity round trips. No integration
code or cross-chat message was created in this task. This section takes precedence
over any future bridge wording above that could imply automatic size replacement.

Affected parts of the earlier physiology prompt: work package 4's carbon-constrained
expansion and work package 5's replacement/hybrid transition. In this deliverable,
`allocate_carbon`, `update_form` and `advance_physiology` specify an isolated
counterfactual for accounting review. They must not write P3's state, rates, weights
or geometry. Section 9's later implementation plan first targets the diagnostic
API below; enabling a realized physiological transition remains a separate decision.

Proposed `compute_carbon_sufficiency(p3_interval, carbon_state, light_series,
environment, parameter_pack)` is a pure function. Inputs require the same plant,
trajectory, interval, geometry/mass anchor and compatible domains as sections 2-6.
Outputs: `available_growth_carbon_gC,required_growth_carbon_gC,sufficiency_ratio,
maintenance_deficit_gC,growth_deficit_gC,status,limiting_inputs,assumptions,
source_hashes`. P3 interval is immutable; output cannot feed back by default.

Carbon demand cannot be identified from arbitrary length/area/count increments
alone. Require independent organ mass increments or an invertible, reviewed
mass/form relation with the correct blade/support/root compartments. For area:
`W_target=(A_P3-A_anchor+s_anchor*W_anchor)/s_target`. For power dimensions:
`W_target=((x_P3-x_anchor+h(W_anchor))/lambda)^(1/gamma)/1000`, with gamma>0,
valid positive base and source-consistent units. These inversions are conditional
inferences with uncertainty, not new mass observations. Conflicting length/area
inversions return `inconsistent_mass_form`; do not average them without a joint
measurement model. Missing root/new-organ demand blocks whole-plant sufficiency.

For nonnegative inferred increments, `D=sum(chi*q_o*delta_W_P3_o)`, including
funded births and any supported root/reproductive demands. Let
`U=B+S+import-export-Rmaintenance`, and `V=max(U-Bmin,0)` only if U>=0.
For D>0 and U>=0, `ratio=V/D`, `growth_deficit=max(D-V,0)`; report sufficient if
V>=D under an explicit numerical comparison tolerance, otherwise deficit. If
U<0, report `maintenance_deficit`, its magnitude and a null ratio; do not conceal
it behind zero availability. If D=0 report `no_growth_demand` and a null ratio,
never infinity. Missing inputs => unavailable. Neither sufficiency nor deficit
changes P3's increment. Any balanced hypothetical state is labelled diagnostic
and stored separately. A deficit is not permission to clip P3.

P3 already supports explicit environmental/light response through its configured
features and the calibration adapter. Applying a P4 light/carbon multiplier to
those same size increments would count the response twice. The diagnostic route
avoids that operation; any future residual coupling requires a separate reviewed
identification and acceptance plan.

The first integration must later check ID mapping, metric area, photons versus
flux density, phase/time, board/grow/parent vectors, angle sign, missingness and
hash round trips on synthetic fixtures. This specification creates no integrated
end-to-end pass, no future optical tissue and no biological validation.
