# Environment driven 3D growth simulator scaffold

## Authorized scope

The user requests only a foundation: a callable simulator with light, temperature, humidity and nutrient-solution inputs, producing time-dependent leaves, trusses and related organs in 3D. Implement under `tools/`; preserve photo reconstruction, reviewed annotations, calibration and the existing GroIMP pipeline.

Provide explicit input units, replaceable environmental response, stable parent/organ IDs, time snapshots, synthetic geometry, a local timeline viewer, JSON/CSV output and focused tests. A named illustrative rule set may exercise the interfaces. Its coefficients are software examples, not cultivar parameters, optimal environmental settings or validated flowering predictions. Agronomic equations and calibration remain for Claude/human review.

Existing `groimp_structure_export.py` transports static reconstructed structures; it does not implement dynamic growth. Reuse the shared millimetre-to-metre conversion for a separate display-only geometry export. Do not pass procedural demo leaves into the measured-plant or PPFD pipelines. No training, remote jobs, external services or new physiological claims are required.

## Completion checks

- Light, temperature, RH and solution EC/pH inputs are validated and passed to an explicit response function. Additional nutrient concentrations are retained with units and not silently interpreted as an uptake model.
- Sequential steps generate persistent organ IDs and growing 3D leaf surfaces, stems, trusses and illustrative flower shapes.
- A replaceable response callback changes development without changing the geometry contract.
- Missing/nonfinite inputs fail explicitly. The original inputs and previous snapshots remain unchanged.
- Runnable demo, timeline view, recorded parameters and deterministic tests distinguish a working software scaffold from a biological prediction model.


## Delivery

Implemented `tools/growth_simulator.py`, with a self-contained `tools/growth_simulator.html` timeline renderer and `tools/tests/test_growth_simulator.py`. No reconstructed plant data or existing pipeline code changed. The viewer is a scaffold preview, not a replacement labeling application.

### Function contract

```python
from tools.growth_simulator import Environment, demo_parameters, simulate

steps = [Environment(
    dt_days=1, ppfd_umol_m2_s=250, photoperiod_h=16,
    temperature_c=24, relative_humidity_pct=65,
    solution_ec_ms_cm=2, solution_ph=6,
    nutrients_mg_l={"N": 100}, water_available=True,
) for _ in range(30)]
result = simulate(steps, demo_parameters(), plant_id="synthetic_demo")
```

All numbers above are arbitrary software examples, NOT recommended tomato growing conditions. `environment_steps` contains sequential constant-condition intervals. PPFD is the lights-on incident input, not measured leaf absorption or a spatial light field. `simulate` returns an initial frame and one frame after each interval. Each frame contains elapsed day, accumulated illustrative development, original environmental inputs, named response factors and organs.

Replace the response with `simulate(..., response_model=my_response)`. The callback receives a validated copied `Environment` and explicit `Parameters`, returning a nonempty mapping of factors in [0,1]. The product of those factors is development-days per calendar day. This contract allows a later calibrated response to be plugged in; a full carbon-balance or organ-specific resource allocation model would require extending the state contract, not merely changing a coefficient.

The shipped response uses a light integral with a saturation cap, triangular illustrative temperature/RH/EC/pH responses, and a water switch. No CO2 is required. Individual `nutrients_mg_l` values are passed to callbacks and preserved but are NOT interpreted by the demo. No-light means zero development in this toy rule; it is not a biological assertion about plants in darkness. All durations, dimensions and response coefficients are explicit parameters in `input.json`; the demo topology uses five leaflets per compound and three flowers per truss, neither estimated from photos nor a biological standard.

### Geometry and time

Plant, MainStem, Internode, CompoundLeaf, SubStem, Leaflet, Truss, Flower and GrowthShoot IDs persist across frames. Parent IDs remain resolvable. Expansion changes stem segment lengths and leaflet triangles with accumulated development. Truss and flower nodes appear at explicit illustrative thresholds; flower appearance is not a prediction of first anthesis. At exact birth a node may have no nondegenerate geometry yet. Counts include those newly born nodes. Growth stops adding nodes at the configured cap. The output does not include senescence, nutrient uptake, disease, actual photosynthesis or yield.

Frame coordinates use a synthetic local plant frame: base origin, Z up, millimetres. These are NOT measured ChArUco coordinates. The display-only OBJ uses `tools.groimp_bridge.mm_to_m` exactly once. `display_only_m.obj` is for manual geometry inspection; it does not establish XL dynamics, real GroIMP import success or optical readiness. A future bridge must explicitly transform the synthetic/local frame and preserve origin/provenance.

### Commands and files

```powershell
python -m tools.growth_simulator --demo --out build/growth_demo_NEW
python -m tools.growth_simulator --input build/growth_scaffold_20261002/input.json --out build/growth_variant_NEW
python -m pytest tools/tests/test_growth_simulator.py -q
```

Generated folders must be new and under project `build/`; existing output is not overwritten. Edit a copied input JSON to try a different environmental schedule, keeping the demo source distinguishable from real observations. The CLI uses the illustrative response; custom response models are callable through Python.

Delivered example: `build/growth_scaffold_20261002/` contains `input.json`, `simulation.json` (31 frames), `timeline.csv`, `display_only_m.obj`, `viewer.html`, `manifest.json`, `completion_audit.json` and `viewer_proof.jpg`. Open the standalone HTML directly or use the current read-only local preview at `http://127.0.0.1:8835/viewer.html`. The preview server serves this generated directory only; it does not modify inputs or recompute the model. Controls provide time, playback and camera rotation; environmental editing currently uses JSON/Python.

### Verification

18 tests passed in 7.16 seconds: individual environmental driver influence, callback propagation and input isolation, finite/ranged inputs, stable IDs and parent links, expansion and nondegenerate triangles, interval-partition consistency, explicit demo dormancy, JSON round trip, mm/metre export, new-output enforcement and readiness flags. The browser displayed day 20 with 10 compound leaves, 50 leaflet nodes, 4 trusses and 9 flower nodes; time and yaw controls worked and no browser error logs were returned. These numbers test software operation, not growth accuracy. Full-page proof is retained.

The requested basic framework is complete. Agronomic response equations, cultivar-specific parameters, calibration against observations, measured-plant initialization and GroIMP light feedback remain future work. Do not present the synthetic shapes as the user's reconstructed leaves or the arbitrary event days as predicted flowering dates. Source hashes and requirement-specific evidence are in `completion_audit.json`.
