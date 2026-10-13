# Nutrient uptake and growth science contract for the dwarf tomato FSP (review prompt 2026-10-08)

I need the scientific contract that turns my existing fertilizer/water **accounting** layer into a conditional nutrient model for dwarf tomato. Codex has built and tested the bookkeeping; it deliberately left every scientific law empty. Your job is to supply those laws, or to state clearly which ones cannot be supplied yet and what each gap blocks. This is a design discussion: do not write production code and do not install literature coefficients as defaults.

## 1 Inputs

Primary request (attached; also in the project):
`handoff/CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_REQUEST_2026-10-06.md`

Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`
Do not list the whole OneDrive tree (it times out). Open these files directly:

- Accounting layer (what already exists): `tools/FSP_NUTRIENTS.md`, `tools/nutrient_contract.py`, `tools/nutrient_composition.py`, `tools/nutrient_balance.py`, `tools/nutrient_fsp_bridge.py`
- Implementation report: `handoff/CODEX_FSP_NUTRIENTS_EXECUTION_2026-10-06.md`, `handoff/CODEX_FSP_NUTRIENTS_IMPLEMENTATION_BRIEF_2026-10-06.md`
- Demo and verification outputs: `build/fsp_nutrients_20261006_01/` (`demo/`, `verification.json`, `verify_delivery.py`)
- Adopted integration decisions D1–D21: `handoff/CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md`
- Existing P4 carbon diagnostic: `tools/fsp_carbon_diagnostic.py`; physiology evidence registry `build/fsp_physiology_spec_20261003_01/`

If you cannot open a file, say so and work from the attached request. Before proposing anything, check that the request's description of the accounting layer matches the code (state names, event kinds, species list, units, unavailable behaviour), and report any mismatch first.

## 2 Fixed facts and choices

- **Crop and setting:** dwarf determinate tomato, small potted plants (roughly 60–90 mm tall at the current stage), indoor under artificial light.
- **Root zone:** reported 60 × 60 mm pot footprint; upper layer 50 mm fine vermiculite, lower layer 10 mm perlite. Internal filling dimensions are not yet confirmed. Geometric volumes (180 mL and 36 mL) are **not** water-holding capacities.
- **Fertilizer:** soluble inorganic fertilizer. The goal is to compare **compositions (ratios) and total concentrations** conditionally — not to estimate true ion uptake and not to optimize a real recipe.
- **Available observations:** fertilizer/irrigation records, EC, pH and photographs. There is **no** solution or tissue chemical analysis. Product labels, initial ion stocks and water-holding capacities have not been supplied yet.
- **Out of scope for v1:** nutrition-driven changes in growth *direction*.
- **Accounting namespace:** mg of element; N tracked as `NO3_N` / `NH4_N` / `unspecified_N` input-form labels (not a tissue speciation model); P, K, Ca, Mg, S, Fe, B, Mn, Zn, Cu, Mo, Na, Cl. Tracking a species does not give it a response model.

## 3 Decisions already made (constraints — do not reopen silently)

- **D1:** P3 (growth model) is the only owner of realized growth — size and direction.
- **D2:** P4 (FSP) is a read-only diagnostic index. It never adds an increment, overwrites P3 state, rejects trajectories or multiplies P3 rates.
- **D9:** temperature enters only P3's development clock; fixed whole-plant DLI enters only P3 size targets. **EC, pH, CO2 and VPD do not enter P3.**
- **D11:** P3 receives incident whole-plant reference DLI; P2 absorbed patch flux is not a P3 input.
- **D12/D15–D18:** P4 uses `respiration_accounting='before_mito'`, `light_basis='absorbed'`, `illuminated_faces='adaxial_only'`, carbohydrate maintenance in g CH2O g⁻¹ DM_str d⁻¹, Tref 25 °C, no basal maintenance floor, no reserve propagation between intervals.
- The current P4 module is a diagnostic, **not** a dynamic carbon allocator. Existing provenance and area-eligibility gates stay.

## 4 Conflict to resolve first

The request asks for `nutrient_growth_response` ("which P3/P4 parameter/state is affected") and a `carbon_nutrient_growth_controller` ("potential versus realized growth"). Read literally, both would let nutrients change growth — which D1, D2 and D9 currently forbid.

Before writing these two contracts:

1. State plainly whether each can be written **within** D1/D2/D9 (for example, a diagnostic nutrient-sufficiency index alongside the carbon-sufficiency index, with no feedback to P3).
2. If a useful nutrient → growth link requires changing a decision, describe the minimum change as a separate option (e.g. "a nutrient term enters only the P3 size target, analogous to DLI, with its own applicability interval"), with its double-counting risk against the DLI/light terms already in P3, and mark it **requires user decision**. Do not adopt it.
3. Never put a universal stress multiplier on P3 rates, and never let a nutrient term re-count light or carbon effects P3 or P4 already uses.

## 5 Required contracts

For each of the seven contracts below, give for every equation: exact expression; input/output quantities and units; state vs parameter classification; time basis; source paper with equation/table/page; parameter range, uncertainty and applicability domain; parameter correlations; required initial state; failure behaviour (structured `unavailable` with reason, never silent zero or clipping); and one independent hand-checkable verification example. Separate tomato evidence from other species, and tomato evidence from what applies to a dwarf cultivar in this pot.

| Contract | What must be settled |
| --- | --- |
| `substrate_water_transport` | Two-compartment retention, drainage and root water extraction; whether within-layer well-mixing is defensible for 50 mm vermiculite over 10 mm perlite; irrigation/reuse boundary; hydraulic parameters and the measurements that would supply them for these actual materials |
| `ion_retention_release` | Which species need reversible exchange (e.g. NH4⁺/K⁺ on vermiculite), fixation, precipitation/dissolution or initial release; how retained pools are represented so losses are not booked as uptake; uncertainty for vermiculite vs perlite |
| `root_nutrient_uptake` | Concentration–uptake relation per ion/form; root mass vs length basis; saturation/threshold terms only if justified; coupling to water flux and temperature; supply limits; why any borrowed kinetics applies here |
| `plant_nutrient_demand_allocation` | Initial plant pools; critical/dilution tissue concentrations; storage vs structural pools; organ allocation; remobilization; root development; explicit distinction between calculated demand and actual uptake; the transformation from N input-form labels to elemental tissue N |
| `nutrient_growth_response` | Supported mapping from nutrient state to photosynthetic capacity, leaf expansion, SLA or growth demand — constrained by section 4 |
| `salinity_and_ion_interactions` | When excess salt and antagonism matter; responses only where supported; **do not infer individual concentrations or osmotic state from EC alone**; list which missing species block each calculation |
| `carbon_nutrient_growth_controller` | Shared step and geometry timing; potential vs realized growth; carbon and element ledgers; same-step vs lagged updates; convergence/failure policy; conservation without double charging — constrained by section 4 and by the absence of reserve propagation in P4 |

## 6 Evidence

Open each source before using exact equations or coefficients. If full text could not be opened, label it unverified and do not give its numbers as verified.

- VegSyst macronutrient uptake — https://doi.org/10.1016/j.scienta.2020.109862 . Separate demand/uptake prediction under its conditions from nutrient-deficiency feedback. Full text failed in the earlier planning pass; no coefficient from it has been installed.
- Hydroponic nutrient replenishment — https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2022.965964/full . Separate nutrient vs water uptake, root-zone composition, salt control. A hydroponic bulk solution is not this layered substrate.
- Tomato root P uptake kinetics — https://apct.sede.embrapa.br/pab/en/article/view/16112 . Candidate for evaluating uptake laws, not a universal parameter set.

Add other primary sources you find relevant (substrate hydraulics and cation exchange of vermiculite/perlite, tomato critical N dilution, tomato uptake kinetics), with the same verification rule.

## 7 Identifiability and measurement plan

- Which combinations of hidden root state (root mass/length, distribution between layers) and response parameters are **not** identifiable from EC, pH and photos alone? Give conditional ranges only where supported; otherwise mark `unidentified`.
- Propose a **minimal** optional measurement escalation, in order of cost: water in/out and pot weight → drainage volume and EC → end-of-trial dry mass by organ → chemical samples (solution, tissue). For each step, say which parameters it would make identifiable.
- Separate pilot parameter estimation from independent testing (held-out plants, times or treatments).

## 8 Synthetic reference cases

Provide isolated synthetic cases with hand-checkable water, nutrient and carbon balances that Codex can turn into tests — at least one each for: transport only; retention/release only; uptake only; demand/allocation only; and one combined case. Keep them consistent with the existing demo format in `build/fsp_nutrients_20261006_01/demo/`. State explicitly that synthetic correctness is not validation of real uptake or growth.

## 9 Output

**First response (keep it to this):**
1. Any mismatch between the request and the code.
2. Your answer to section 4 (what fits inside D1/D2/D9, what needs a decision).
3. A one-row-per-contract table: `implementable now` / `implementable after user input X` / `unresolved` — with what each unresolved item blocks.
4. A parameter–evidence table (measured / literature candidate / explicit assumption / unavailable; species, cultivar, stage, medium, source locator, verified or not).
5. At most **3 decisions** I must make first.

Keep the full equations and synthetic cases for follow-ups.

Label every statement **verified source fact**, **design proposal** or **open assumption**. Do not silently replace existing approved models, claim certainty, or leave a scientific law for Codex to choose.

**After we agree:** write only the agreed items to `handoff/CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_2026-10-06.md` in English, as an implementation contract for Codex with file/function/input/output/unit references to the existing `tools/nutrient_*.py` layer. Leave unresolved items listed as unresolved, each with the computations it blocks.

> Pointer (2026-10-08, literature intake): a published fixed nutrient recipe for pot-grown dwarf tomato exists - Maree et al., Sensors 2025, Appendix A, EC 2.8 dS/m - and is the citable baseline for the step-3 fertiliser treatments. See handoff/PRIOR_ART_DWARF_TOMATO_FSP_2026-10-08.md.
