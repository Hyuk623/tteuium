# FSP nutrient accounting implementation

Date: 2026-10-06. Author: Codex. User request: implement the approved fertilizer
composition, substrate uptake and growth integration plan.

## Outcome and scope

The independent accounting layer, actual CLI, templates, conditional scenario
comparison and optional existing-P4 diagnostic binding are implemented and tested.
The complete uptake-to-growth model is **not** implemented: the plan explicitly
requires Claude's executable science contract first, and none was found. No
physiological, uptake, adsorption or hydraulic coefficient has been invented.

| Plan stage | Actual status |
| --- | --- |
| 1 Input and two-layer conservation | Implemented for explicitly supplied initial states, capacities and prescribed fluxes |
| 2 Scientific equation/parameter contract | Pending; detailed request supplied for Claude |
| 3 Conditional integration | Ledger and read-only P4 binding implemented; predictive uptake, growth constraints, carbon/nutrient allocation and shape feedback unavailable |
| 4 Observation comparison | CSV observations retained with lineage; predictive EC/pH/photo residuals unavailable without corresponding observation model |

Conditional comparison distinguishes the same fertilizer ratio at different
concentrations, changed P ratio at equal N, and an explicit uptake-flux assumption.
It does not infer a causal fertilizer-growth curve from these examples. Root-mass
or physiological-parameter sensitivities remain pending their model contracts.

## Changes

- `tools/nutrient_contract.py`: strict evidence, quantities, aware times, missing
  science and conventional atomic-weight unit identities.
- `tools/nutrient_composition.py`: mass-percent/g-per-litre labels, mass/volume
  doses with required density, P2O5/K2O element conversion, total/form N accounting,
  complete tracked-species coverage, raw water and explicit final solution volume.
- `tools/nutrient_balance.py`: upper vermiculite/lower perlite compartments,
  explicit water capacity, dissolved/retained pools, finite irrigation batches,
  well-mixed transfers, drainage/discard or explicit reuse, evaporation/transpiration,
  prescribed uptake and internal plant nutrient allocation. No implicit process zeros.
- `tools/nutrient_fsp_bridge.py`: existing P4 call with exact disabled parity and
  optional nutrient accounting under checked plant/scenario/time identities.
- `tools/fsp_nutrients.py`: `templates`, `formulate`, `audit`, `simulate`, `compare`,
  `fsp`, `demo`; read-only CSV input, JSON/CSV output and input/code/output hashes.
- `tools/fsp_nutrients_demo.py`: labelled invented examples and blank real-input
  templates. Pot dimensions are retained as reported metadata, not water capacity.
- `tools/FSP_NUTRIENTS.md` and `tools/tests/test_fsp_nutrients.py`: complete contract,
  runnable examples and 67 focused tests.

The source initial-state and event dictionaries are not mutated. Invalid later
events do not yield a successful partial simulation. Nutrient/water overdraw,
capacity violations, duplicate events, incorrect chronology, wrong context or
units are refused. Missing pools/evidence/process contracts are unavailable, not
zero. Carbon spending and growth are never changed by the new bridge.

## Verification

Final regression command, from project root:

```powershell
python -X utf8 -m pytest tools/tests/test_fsp_nutrients.py tools/tests/test_fsp_carbon_diagnostic.py tools/tests/test_fsp_growth_science.py tools/tests/test_fsp_growth_pack_v2.py tools/tests/test_fsp_area_review.py -q --basetemp build/fsp_nutrients_20261006_01/pytest_final --junitxml build/fsp_nutrients_20261006_01/combined_tests.xml
python -X utf8 build/fsp_nutrients_20261006_01/verify_delivery.py
```

Results: **253 passing tests = 67 new nutrient tests + 186 existing P4 tests**.
The independent delivery script passes **244 checks**, including hand-recomputed
mass/water closure, exact P4 parity, declared ratios/doses, unavailable science,
blank template readiness, and input/code/output hashes.

Eight actual CLI executions covered demo, templates, blank audit, formulation,
replay, comparison, disabled FSP and enabled FSP. Additional CLI failure cases are
tested for wrong CSV context, existing output directories and outputs outside build.
Examples are under `build/fsp_nutrients_20261006_01/`:

- `demo/`: four separate input/output scenarios plus the synthetic P4 binding.
- `templates/`: header-only events/observations and scenario metadata with unknown
  physical inputs null. `template_audit/` correctly reports unavailable.
- `formulation/`, `replay/`, `compare/`, `fsp_disabled/`, `fsp_enabled/`:
  actual CLI exports with per-run provenance.
- `verification.json`, `combined_tests.xml`, `verify_delivery.py`: evidence.

The first test attempt exposed a missing pytest temporary parent and an erroneous
test selection of the unchanged lower-layer concentration; these were corrected.
The final suite includes actual CSV loading and export, not just in-memory checks.

## Remaining dependencies and truthful interpretation

The public `status=available` refers to computable **prescribed-flux accounting**.
All outputs retain `validated_nutrient_model=false`. Enabled FSP reports
`growth_constraints.status=unavailable`, `nutrient_constrained_growth=null`,
`carbon_and_nutrient_growth_commit=null` and `growth_feedback_applied=false`.
Existing P4 arithmetic and adopted physiological policy remain unchanged.

The next design input is
`handoff/CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_REQUEST_2026-10-06.md`.
It specifies the missing water transport, ion exchange, root uptake, internal
nutrient demand/allocation, growth response, salt interactions and dynamic controller
contracts. Merely calling a supplied document approved does not implement a model.

Actual fertilizer labels/doses, source water, water capacities, initial pools,
irrigation/drainage and uptake evidence remain unsupplied. EC/pH/photo metadata do
not reconstruct them. No real measurement files, config/docs, P1-P4 runtimes or
historical parameter packs were changed. No literature coefficients, automatic
growth-direction law, GPU work, physical validation or cross-chat dispatch occurred.
