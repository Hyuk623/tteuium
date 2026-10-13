# FSP nutrient implementation brief

Date: 2026-10-06. User authorized implementing the nutrient/FSP plan. Scope is a conditional scenario tool for soluble inorganic fertilizer in a 60 by 60 mm pot, with upper 50 mm fine vermiculite and lower 10 mm perlite. Geometry is not water-holding capacity. No nutrition-driven direction model is requested.

## Inspected state and boundary

Existing P3 forecasts and P4 carbon diagnostics do not implement a root nutrient balance or nutrient response. No finalized nutrient science contract was found in handoff/. The approved plan explicitly reserves uptake, substrate exchange, tissue demand/allocation and growth-response equations for Claude. Do not invent these laws or adopt example coefficients. Existing production modules and frozen parameter packs will remain unchanged.

Implement the complete independent accounting layer now: label-to-element conversion, explicit solution formulation, two-layer water/dissolved/retained nutrient accounting, prescribed uptake into a plant nutrient ledger, drainage/reuse, scenario comparison and read-only P4 diagnostic binding. Prescribed flux replay is not predictive uptake. Enabled FSP output must expose the missing science contracts and unavailable automatic growth constraint; disabled behavior must exactly match the current P4 call.

## Engineering contract

New tools: nutrient_contract.py (strict evidence/units/time), nutrient_composition.py (products/recipes), nutrient_balance.py (pure event ledger), nutrient_fsp_bridge.py (read-only P4 binding), fsp_nutrients.py (CLI), fsp_nutrients_demo.py (synthetic fixtures), FSP_NUTRIENTS.md and focused tests. CLI: templates, formulate, audit, simulate, compare, fsp, demo. New outputs only in fresh build/ directories. Measurements/events are CSV; metadata/configuration/results/audits are JSON, with derived tabular exports as CSV.

Mass basis: mg of element, with NO3_N and NH4_N tracking nitrogen form, unspecified_N kept separate, and P/K/Ca/Mg/S plus supported trace elements. Never add total N to its form components, or P to the same P2O5 declaration. Product composition coverage must explicitly declare absent tracked species; unknown fractions remain unavailable. Distinguish mass-percent, g/L product, mass doses and volume doses with sourced density as needed. Final solution volume is explicit; EC/pH are observations, not ion estimators.

Events: irrigation from finite formulated batches, within-pot water/solute transfer, drainage, explicit reuse of retained drainage, pure water loss (evaporation/transpiration), prescribed root uptake, retention/release and internal plant allocation. Each has a unique ID, aware time, plant/scenario context and evidence. Water transport uses explicitly declared well-mixed aliquots; transfer rates/capacity/uptake are inputs, not derived crop laws. Missing initial pools, capacities or process declarations are scientific unavailability, never zeros. No negative stocks, overdraw, duplicate replay, hidden drainage or invented exchange.

Each scenario retains initial/end states, event/source hashes, conservation residuals, elapsed times, observation provenance and incomplete predictive status. Compare absolute concentrations and molar ratios separately. Unknown botanical/root/response parameters cannot be fitted from EC or photos alone.

## Verification and delivery

Tests: P2O5/K2O and N accounting, liquid basis/density, unknown coverage, ratio versus dose, dilution, two-layer water/element conservation, retained stock, uptake overdraw, drainage/reuse, chronology/context/duplicates, source immutability, missing science and nonfinite input. Exercise actual CLI CSV/JSON exports, build-only/fresh outputs, independent aggregate checks, scenario differences and disabled P4 parity. Run existing P4 regressions and preserve production hashes.

Deliver executable templates/demo, user guide, implementation report and a specific Claude science-contract request in handoff/. No docs/config/human-data edits, new nutrient biological coefficients, optimization recommendation, physical validation, training or cross-chat dispatch. The overall scientific integration remains pending the explicitly required contract and real inputs; report this boundary clearly.

## Completed engineering outcome

2026-10-06: independent accounting, CLI/template/demo/comparison and opt-in read-only P4 binding delivered. 67 new tests plus 186 retained P4 tests pass (253 total); eight real CLI runs and 244 independent delivery checks recorded. Scientific contracts were not supplied, so predictive uptake and realized-growth feedback remain explicitly unavailable. See CODEX_FSP_NUTRIENTS_EXECUTION_2026-10-06.md and the concrete Claude contract request.
