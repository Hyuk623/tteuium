# FSP nutrient accounting

This opt-in tool formulates soluble inorganic fertilizer and replays explicit water
and nutrient transfers in two substrate layers. It can run alongside the existing
P4 carbon diagnostic. It does **not** predict root uptake, nutrient-limited growth,
EC, pH, or phototropism. Missing Claude science contracts are reported explicitly.
An available ledger means that the supplied accounting can be computed, not that
the supplied fluxes are biologically correct.

## Quick start

Run from the project root; every output directory must be new and under `build/`.

```powershell
python -X utf8 -m tools.fsp_nutrients --help
python -X utf8 -m tools.fsp_nutrients templates --out build/nutrients_inputs_new
python -X utf8 -m tools.fsp_nutrients demo --out build/nutrients_demo_new
python -X utf8 -m tools.fsp_nutrients audit --scenario build/nutrients_inputs_new/scenario.json --out build/nutrients_audit_new
python -X utf8 -m tools.fsp_nutrients simulate --scenario build/nutrients_demo_new/baseline/scenario.json --out build/nutrients_replay_new
python -X utf8 -m tools.fsp_nutrients compare --scenarios build/nutrients_demo_new/baseline/scenario.json build/nutrients_demo_new/double_dose/scenario.json --out build/nutrients_comparison_new
python -X utf8 -m tools.fsp_nutrients fsp --request build/nutrients_demo_new/fsp/p4_request.json --scenario build/nutrients_demo_new/fsp/scenario.json --enabled --out build/nutrients_fsp_new
```

The template contains no fertilizer recipe, initial ion content, water capacity,
uptake, or biological coefficient. Known reported dimensions are 60 by 60 mm,
upper vermiculite 50 mm and lower perlite 10 mm. The user must establish that these
are internal filling dimensions. Geometric volumes (180 and 36 mL) are never used
as water-holding capacities. The demo has entirely invented values, including
initial nutrient stocks and fluxes. It is not a fertilizer recommendation.

## Python interfaces

| Function | Input | Output |
| --- | --- | --- |
| `nutrient_composition.formulate(recipe)` | Explicit product labels, doses, source water and final volume | Element mg, mg/L, mmol element/L, N-normalized molar N:P:K where defined |
| `nutrient_balance.simulate(scenario)` | Two-layer initial state and ordered, evidenced flux events | Initial/final states, water/element conservation and prescribed uptake |
| `fsp_nutrients.compare_scenarios(requests)` | Distinct scenarios with the same source plant, interval and species | Individual results and comparison rows; unavailable cases retained |
| `nutrient_fsp_bridge.compute_with_nutrients(request, scenario, enabled=False)` | Existing P4 request and optional nutrient scenario | Exact original P4 result when disabled; side-by-side diagnostics when enabled |

Pure APIs do not write or mutate inputs. `StudyError` means malformed or physically
inconsistent input. Missing scientific values/evidence produce `status=unavailable`
with reason/detail. A bad later event invalidates the whole replay; no prefix is
committed. JSON missing values are null; CSV missing values are blank. Zero is
never an inferred replacement for missing evidence. The bridge checks plant,
source plant, scenario and interval before binding the nutrient result.

## Formulation contract

`recipe` has `batch_id`, `tracked_species`, `final_volume_L`,
`source_water_volume_L`, `source_water_mg_L`, `source_water_evidence`, `evidence`,
`products` and `doses`. Source-water concentrations must cover every tracked
species, including explicit known/assumed zeros. Final solution volume is an
explicit prepared-volume input, not inferred from EC or additive volumes.

Species use **mg of the element**, not mg of the ion. Supported names are
`NO3_N`, `NH4_N`, `unspecified_N`, `P`, `K`, `Ca`, `Mg`, `S`, `Fe`, `B`, `Mn`,
`Zn`, `Cu`, `Mo`, `Na`, `Cl`. `NO3_N=10 mg` means 10 mg nitrogen in nitrate form,
not 10 mg nitrate. The tracked scope is explicit and is not necessarily a complete
electrolyte composition. No electroneutrality, osmotic pressure or EC model is
implied. N form names in the plant ledger retain the input-origin accounting label;
they do not predict tissue N chemical speciation.

A product has `product_id`, `label_basis=mass_percent|g_per_L_product`, `labels`
(`analyte`, `value`), `unlisted_tracked_species=declared_absent|unknown`, and
`evidence`. Labels may use species names, `total_N`, `P2O5` or `K2O`.
The oxide-to-element factors are computed from the documented conventional atomic
weights in `nutrient_contract.ATOMIC_MASS`; these are unit identities, not crop
parameters. N forms are subtracted from declared total N and any remainder stays
`unspecified_N`. Total N is never added on top of its forms. Conflicting duplicate
oxide/element or N declarations fail. An unlisted species is zero only under an
explicit absence declaration; otherwise the composition is unavailable.

Each dose has `dose_id`, `product_id`, `amount`, `unit=g|mL` and `evidence`.
Mass-percent labels give mg/g product; g/L-product labels give mg/mL product.
Crossing these dose bases requires `density_g_ml` and `density_evidence` on the
product. Values are neither interpreted as oxide-free elemental ratios by default
nor automatically converted from unspecified percentages. Each solution batch is
a finite stock: total irrigation cannot exceed its prepared volume.

## Scenario and initial state

`scenario.json` uses schema `fsp-nutrients-1`. Required metadata:

- `scenario_id`, `plant_instance_id`, `source_plant_id`, aware `t_start/t_end`,
  `tracked_species`, `evidence` and `numerics.water_abs_tol_ml/mass_abs_tol_mg`.
- `geometry`: `width_mm`, `depth_mm`, `dimension_basis=internal_filled`, evidence.
- Two `layers`, top vermiculite then bottom perlite. Each has `layer_id`,
  `material`, `height_mm`, `water_ml`, `water_capacity_ml`, `capacity_evidence`,
  `dissolved_mg`, `retained_mg`, `evidence`.
- `plant_initial`: `labile_mg`, `organs` mapping each declared organ ID to a full
  species vector, and evidence. This is not an inferred dry-mass state.
- `drainage_initial`: `water_ml`, `dissolved_mg`, evidence.
- `mixing_model=well_mixed_each_layer` plus `mixing_evidence` explicitly declaring
  the compartment mixing assumption; no mixing coefficient is silently adopted.
- `drainage_mode=discard|retain_for_explicit_reuse`; discarded runoff is an
  accounting output compartment and cannot be reused.
- `processes` covers irrigation, layer_transport, drainage, reuse, evaporation,
  transpiration, uptake, exchange and plant_allocation. Each declares
  `mode=prescribed_events|assumed_zero` with evidence. Assumed zero requires
  `kind=assumed`; unspecified exchange is not automatically zero. A prescribed
  process needs at least one event (an evidenced zero event is allowed).

Evidence objects contain `kind=measured|assumed|borrowed|fitted` and `source_ref`.
Assumptions also require an explicit `assumption` description. These labels retain
provider provenance; they do not themselves certify a source. Each pool must list
every tracked species. Dry dissolved-ion pools are unavailable because no
precipitation/dry-pool law has been adopted. Water cannot exceed the declared
capacity; excess irrigation is not silently turned into drainage.

## Event and observation tables

CLI templates provide `events.csv` and `observations.csv`; `scenario.json` points
to them with `events_file` and `observations_file`. Pure APIs also accept inline
arrays for explicit synthetic or programmatic inputs. Do not provide both routes.

Event columns are:

```text
scenario_id,plant_instance_id,event_id,at,kind,layer_id,from_layer_id,to_layer_id,batch_id,water_ml,organ_id,evidence_kind,source_ref,assumption,<each tracked species>_mg
```

Headers must exactly match the generated template. Each row is one unique event
at an aware timestamp. Rows must already be ordered; simultaneous events execute
in row order, which makes prescribed operator ordering explicit. Replayed IDs,
unknown layers/organs/batches and inconsistent plant/scenario IDs are refused.
Unused cells must be blank. Species-flux events must supply every species,
including explicit zeros. Recorded file hashes and CSV line numbers survive loading.

| Kind | Fields and accounting |
| --- | --- |
| `irrigate` | `batch_id,layer_id,water_ml`: finite formulated aliquot into the layer |
| `transfer` | `from_layer_id,to_layer_id,water_ml`: well-mixed layer aliquot |
| `drain` | `layer_id,water_ml`: layer aliquot into the runoff ledger |
| `reuse` | `layer_id,water_ml`: available retained-runoff aliquot returned explicitly |
| `evaporate`, `transpire` | `layer_id,water_ml`: pure water loss; ions remain |
| `uptake` | `layer_id,nutrient_mg`: supplied uptake transferred to plant labile stock |
| `retain`, `release` | `layer_id,nutrient_mg`: transfer between dissolved and retained stocks |
| `allocate` | `organ_id,nutrient_mg`: labile-to-organ nutrient transfer; no DM/area change |

Transport nutrient amounts come from the explicitly assumed mixed source pool;
they are not supplied a second time. Root uptake is a separate prescribed flux
from water transpiration. No process can withdraw more water or nutrients than
available, and no growth clipping/uptake saturation law is invented to repair it.

Observation columns are `observation_id,plant_instance_id,at,metric,value,unit,
evidence_kind,source_ref,assumption`. Supported metadata metrics are EC (`mS/cm`),
pH (`dimensionless`), pot mass (`g`), supported area (`cm2`) and height (`mm`),
using the exact names in the template/API (`ec_ms_cm`, `ph`, `pot_mass_g`,
`supported_area_cm2`, `height_mm`). These records do not change ion stocks or fit
coefficients. Predictive observation comparison is explicitly unavailable.

## Conservation, exports and interpretation

For each tracked species, initial layer + retained + plant + drainage mass plus
new irrigation mass equals final mass in those compartments. Allocation, uptake,
retention and reuse are internal transfers. Water closure includes explicit
evaporation/transpiration loss. Discarded runoff remains visible in the output
ledger rather than disappearing. Unused prepared batches are reported separately,
outside the root-zone system boundary, and irrigation counts only withdrawn water.

`result.json` retains full states, evidence, input hash, process declarations and
scientific readiness. `layer_states.csv` is event/layer/species data: water repeats
across species and must not be summed across those rows. `water_ledger.csv` is
one row per event. `event_ledger.csv` is nutrient transfer per event/species.
`formulation.csv` is produced by the formulate command. Scenario comparisons use
`scenario_comparison.csv`. `provenance.json` records input files, code and output
hashes. Numeric residuals are checked after each event with supplied tolerances.

The demo contrasts equal ratios at two concentrations, different P ratio at equal
N, and a different prescribed uptake assumption. Unchanged uptake in a double-dose
case is intentional: no fertilizer-to-uptake response has been fitted. These are
conditional sensitivities of accounting, not probability intervals, real root-mass
sensitivity or biological treatment effects.

## FSP boundary and remaining science

Without `--enabled`, the bridge returns the existing P4 result exactly and ignores
nutrient inputs. With it, the output has `p4_diagnostic`, `nutrient_accounting`,
`binding` and `growth_constraints`. Identity/time binding does not establish shared
physiological state or an approved nutrient response. P4's existing light/time,
respiration, carbon and area gates are unchanged. No carbon is deducted by this
bridge and no reserve is propagated, so no new double-charge is introduced.

`nutrient_constrained_growth` and `carbon_and_nutrient_growth_commit` remain null.
To enable predictive coupling, Claude must supply executable water transport,
exchange, uptake, tissue demand/allocation, growth-response, salt-interaction and
carbon/nutrient-controller contracts. Those require applicable coefficients,
initial roots/plant nutrients, units, uncertainty and failure criteria. Passing a
document labelled approved into this v1 does not magically install an equation.
See the implementation handoff and science-contract request. No existing P1-P4
producer, human observation or parameter pack is rewritten by this tool.
