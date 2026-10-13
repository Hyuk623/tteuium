# Nutrient uptake and growth science contract request

Recipient: Claude scientific design owner. Prepared by Codex on 2026-10-06 for the
user's approved nutrient/FSP plan. This document has not been sent to another chat.

## Objective and fixed user choices

Develop a conditional model comparing soluble inorganic fertilizer compositions
and total concentrations for dwarf tomato growth. The root zone is a reported
60 by 60 mm pot footprint, upper fine vermiculite 50 mm, lower perlite 10 mm.
Available observations are fertilizer/irrigation records, EC, pH and photographs.
Individual solution/tissue chemical analyses are not available. Root and internal
nutrient states must therefore be explicitly uncertain/assumed unless measured.
Nutrition-driven direction changes are excluded from v1. Comparison is conditional,
not a claim to estimate actual ion uptake or optimize a real recipe.

The software accounting layer exists. Read `tools/FSP_NUTRIENTS.md`,
`tools/nutrient_contract.py`, `tools/nutrient_composition.py`,
`tools/nutrient_balance.py`, `tools/nutrient_fsp_bridge.py`, and
`handoff/CODEX_FSP_NUTRIENTS_EXECUTION_2026-10-06.md`.
It implements label conversion, finite batches, two-layer accounting, prescribed
fluxes, explicit retained pools, plant nutrient allocation accounting and a P4
diagnostic binding. It intentionally does not invent the science below.

## Required executable specification

For every equation provide the exact expression, input/output quantity and unit,
state/parameter classification, time basis, source paper and equation/page,
parameter range/uncertainty and applicability, parameter correlations, initial
state requirements, failure behavior and independent verification example.
Distinguish tomato evidence from other species and dwarf-cultivar applicability.
Do not mark papers or supporting files verified if they could not be opened.

| Contract | Questions that must be resolved for implementation |
| --- | --- |
| `substrate_water_transport` | Two-compartment water retention, drainage and root water extraction law; validity of within-layer mixing; boundary for irrigation/reuse; required measurements and hydraulic parameters for the actual materials |
| `ion_retention_release` | Which constituents need reversible exchange, fixation, precipitation/dissolution or initial release; how retained species are represented without treating all losses as uptake; parameter uncertainty for vermiculite/perlite |
| `root_nutrient_uptake` | Concentration versus uptake relation by ion/form; root mass/length basis, saturation/threshold terms if justified, water/temperature coupling and supply limits; why any borrowed kinetics applies |
| `plant_nutrient_demand_allocation` | Initial nutrient pools, tissue requirements/dilution, storage versus structural pools, organ allocation, remobilization and root development; distinction between calculated demand and actual uptake |
| `nutrient_growth_response` | Supported mapping from nutrient state to photosynthetic capacity, leaf expansion, SLA or growth demand; exactly which P3/P4 parameter/state is affected, avoiding unsupported universal stress multipliers |
| `salinity_and_ion_interactions` | Applicability and response to excess salts and antagonism; do not infer individual concentrations or total osmotic state from EC alone; define which missing species block this calculation |
| `carbon_nutrient_growth_controller` | Common step/geometry timing, potential growth versus realized growth, carbon and elemental allocation ledgers, same-step versus lagged updates, convergence/failure policy and conservation without double charging |

Existing P4 before_mito, absorbed-light dwarf input, carbohydrate maintenance and
adaxial-only policy remain adopted. The current P4 module is a read-only diagnostic;
do not describe it as a dynamic carbon allocator. P3's incident reference DLI is
separate from absorbed patch flux. Proposed controller contracts must preserve
these boundaries and existing provenance/area eligibility.

The nutrient accounting namespace tracks mg element with NO3_N/NH4_N/unspecified_N
input-form labels. The current plant pool labels are not a tissue speciation model.
Specify any transformation to elemental tissue N explicitly. Micronutrients and
Na/Cl can be tracked in the ledger; tracking alone supplies no response model.

## Evidence search and experimental identifiability

Review the following primary candidates, verifying full-source access before
using exact equations or coefficients:

- [VegSyst macronutrient uptake](https://doi.org/10.1016/j.scienta.2020.109862):
  distinguish demand/uptake prediction under its conditions from nutrient-deficiency
  feedback. Full publisher access failed in the earlier planning pass; no numeric
  coefficient from this paper has been installed.
- [Hydroponic nutrient replenishment study](https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2022.965964/full):
  review separate nutrient/water uptake, root-zone composition and salt controls;
  do not equate hydroponic bulk solution with this layered substrate.
- [Tomato root phosphorus uptake kinetics](https://apct.sede.embrapa.br/pab/en/article/view/16112):
  a candidate for evaluating uptake laws, not a selected universal parameter set.

Explain which combinations of hidden root state and response parameters are not
identifiable from EC/pH/photos. Provide conditional ranges only when supported;
otherwise mark unidentified. Specify a minimal optional measurement escalation
(water input/output/pot weight, later dry mass or chemical samples) and separate
pilot parameter estimation from independent testing. The user has not supplied
fertilizer product labels, initial ion stocks or water-holding capacities yet.

## Deliverable

Return `handoff/CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_2026-10-06.md` with a complete
implementable contract and parameter-evidence table, or explicit unresolved items
with the computations they block. Include isolated synthetic reference cases with
hand-checkable water, nutrient and carbon balances. Synthetic correctness is not
validation of real uptake or growth. Do not silently replace the existing approved
models, claim certainty, or direct Codex to choose missing scientific laws.
