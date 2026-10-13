# Native conditional VTC development V3

This is a separate mode: `vtc_development_v3`. Python prepares, launches and verifies; GroIMP owns organ initiation, clocks, carbon allocation, realized dimensions, graph geometry and light. The VTC NRH routine is reused; the developmental routines are explicitly replaced under the task-specific user exception. See the V3 science/IO contract in `handoff/` for the exact equations and source mapping. No coefficient is fitted or independently validated for Micro-Tom.

From the project directory:

```powershell
python -X utf8 -m tools.vtc_development --mode vtc_development_v3 demo --out build/my_dev_inputs --intervals 65 --rays 4800000
python -X utf8 -m tools.vtc_development --mode vtc_development_v3 audit --input build/my_dev_inputs
python -X utf8 -m tools.vtc_development --mode vtc_development_v3 prepare --input build/my_dev_inputs --out build/my_dev_run
python -X utf8 -m tools.vtc_development --mode vtc_development_v3 run --run-dir build/my_dev_run --timeout 1200
python -X utf8 -m tools.vtc_development --mode vtc_development_v3 collect --run-dir build/my_dev_run
python -X utf8 -m tools.vtc_development --mode vtc_development_v3 observation-fixture --run-dir build/my_dev_run --day 30 --intervals 8 --out build/my_observation_fixture
```

Every output directory must be fresh. The frozen `inputs/` directory is a replay input; prepare it into another fresh directory, then run and collect. Numerical replay tolerance is 1e-10 for mass/dimensions/carbon; identity and event dates must match exactly. A failed attempt cannot be collected. Old subset mode remains separate and is not a fallback.

`request.json` selects daily intervals, explicit initialization route, scenario, coefficient provenance, ray count/seed, and the conditional optical hypothesis. Exact CSV headers are in `vtc_development_io.TABLES`. Climate carries daily temperature, hours and CO2; only temperature-dependent thermal development is active. There is no temperature/CO2 physiology response. All coefficients require units, source, cultivar and uncertainty. `light_ratio_latest.txt` is resolved and frozen; ratios are comparison-only.

The observation route requires Stage-2 vertices/edges/structure plus a separately declared `initial_state.csv` and `initial_controls.json` for mass, age, reserves, roots, reproductive compartments and apex state. These hidden variables cannot be measured from photos. `fixture_from_native` is explicitly a synthetic adapter test, not the Claude P1 producer. The next producer adapter must consume its actual versioned schema.

Returned CSVs: `states` (dynamic organs at boundaries 0..N), `events` (initiation, funded birth, emergence, axis termination), `flux` (per-organ interval allocation), `ledger` (per-plant carbon), `meshes` (native triangle vertices by boundary), `consumed` (actual graph before each light calculation), `edges` (native graph parents), `apices` (clocks/stops), `sensors` (separate empty-scene light comparison). Derived tables expose class-qualified angles, plant height versus summed internode length and phone-ratio comparison. `completion.json` is written last by GroIMP. `execution.json` records the real command/log/exit. The results folder is published only after independent validation.

The seed route executes all 30 days and continues in the same process. New primordia are massless; funded tissue first intercepts light in the following interval. The supported model uses frozen geometry per day. `freeze_at` and fixed-receiver settings are optical diagnostics: mass may continue to change while geometry stays fixed. Do not use these diagnostics as ordinary growth predictions.

Limits: conditional main/sympodial axes; planar diamond leaflets and slender diamond stem/flower proxies; no cotyledon/hypocotyl morphology, unrestricted lateral shoots, fruit set/yield, curl, nutrient feedback or independently validated prediction. Root physiology is a compartment without a root mesh. The original VTC license remains unresolved; source/evidence are local only.
