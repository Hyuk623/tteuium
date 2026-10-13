# Conditional GroIMP/VTC growth bridge

This implements **phase1_leaflet_subset_v1**, a bounded native GroIMP extension
using the original VTC Thornley function. It is not the complete Micro-Tom
developmental fork requested by Phase-1 V2. Original apex/rachis/seed development
files are retained under the local fork's `upstream/` but are not executed by
this mode. Synthetic demonstration is not biological acceptance.

Python audits and freezes inputs, launches GroIMP, checks results and publishes
them. GroIMP owns all within-run light, assimilation, allocation, reserve and
mass/geometry updates. Python independently recomputes verification quantities;
it never applies a second biological update. Existing P2/P3/P4/nutrient tools
are unchanged and are not called by the engine.

## Reproduce

Run from the project root with Python 3.11+ (tested 3.13), Java (tested Temurin
21.0.12.1) and GroIMP 2.2.1 at `C:/Program Files/GroIMP 2.2.1/core.jar`.
Use **new output directory names** for every attempt:

```powershell
python -X utf8 -m tools.vtc_growth_bridge --help
python -X utf8 -m tools.vtc_growth_bridge fork --out build/my_vtc_fork
python -X utf8 -m tools.vtc_growth_bridge demo --out build/my_vtc_inputs --scenario sufficient --rays 300000
python -X utf8 -m tools.vtc_growth_bridge audit --input build/my_vtc_inputs
python -X utf8 -m tools.vtc_growth_bridge prepare --input build/my_vtc_inputs --fork build/my_vtc_fork --out build/my_vtc_run
python -X utf8 -m tools.vtc_growth_bridge run --run-dir build/my_vtc_run --timeout 180
python -X utf8 -m tools.vtc_growth_bridge collect --run-dir build/my_vtc_run
python -X utf8 -m pytest tools/tests/test_vtc_growth_bridge.py -q
```

`demo` generates input only; `run` launches the real engine. Other demo scenarios:
`limited`, `dark`, `dark_deficit`, `frozen`, `observation`. `dark_deficit` is an
intentional conservation failure: mandatory respiration cannot be funded with
zero carbon. It must never produce a published results folder. Observation is
an observation-like **fixture**, not a P1/Stage-2 producer run.

Public APIs: `load_package(folder) -> dict`, `prepare(package_dir, fork, out)
`-> dict`, `run(folder, java='java', core=CORE, timeout_s=180) -> dict`,
`collect(folder) -> dict`, `validate_outputs(package, native, binding) -> dict`.
Every path is pathlib.Path. Validation reports problems and never repairs input.
Exact headers and units are in `vtc_growth_io.HEADERS` and
`handoff/PHASE1_VTC_PYTHON_SCIENCE_AND_IO_CONTRACT_2026-10-11.md`.

## Frozen inputs and failure handling

Inputs are CSV tables with JSON metadata and coefficient evidence. The ratio
pointer is resolved and hashed once at prepare. Later pointer changes cannot
change the frozen run or replay. Phone ratios are comparison-only; they never
scale each leaflet after ray tracing. A reference PPFD row is a declared
comparison reference; lamp photon powers are the authoritative absolute scenario
input. They are not inferred from phone readings. Grid spacing and height remain
explicit hypothetical assumptions until measured; no physical calibration is
claimed. Temperature and CO2 columns are retained and bound to intervals but the
selected fixed-coefficient NRH does **not** respond to them.

`working/Model.rgg` is the exact engine request. `prepared.json` contains frozen
input, engine template and Python code hashes. `execution.json` records separated
process arguments, Java/GroIMP version, native exit, timeout and log hash. The
model prints a run-specific initialization acknowledgement and writes its own
hashed `completion.json` last, then exits the dedicated process. Failed or partial
outputs go to `partial/`; they cannot be collected as success. Fresh replay
starts from complete frozen inputs; there is no dimension-only resume.

GroIMP compiled setters such as `setLength` alone do not establish graph-change
notification. This implementation uses managed `b[length]` / `b[axis]` updates
and native apply/derive boundaries. `consumed_geometry.csv` reads actual blade
dimensions immediately before each light calculation. Python compares these
with the state committed by the previous interval. A changed array or animation
without a corresponding engine graph change fails this check.

Successful `results/` contains native geometry, consumed geometry, organ fluxes,
carbon ledger, empty-scene sensors and completion; independent normalized gC
ledger; source/native-node identity mapping; geometry/environment bindings;
ratio comparisons; a self-contained viewer of returned states; and a manifest.
Publication is a final directory rename. Every result retains
`run_status=assumption_conditioned`, `nutrient_feedback_enabled=false`,
`biological_validation=not_established`, and `full_v2_acceptance=incomplete`.

## Model boundary

Each supplied flat rectangular leaflet has explicit starting mass, dimensions,
age, potential demand and provenance. Its source plant and instance remain
separate IDs. Carbon is allocated independently within each plant; light traces
across all plants. The conditional constant-SLA mapping changes length and width
with square-root mass ratio. A frozen-geometry control deliberately disables
only that mapping. No intercalary area factor creates optical tissue.

Black blades (absorptance 1, reflection/transmission 0) and point LED sources are
arithmetic fixtures. Both faces share the same conditional response; anatomical
face evidence is absent. The existing VTC NRH coefficients are labelled Merlice,
and their empirical fit basis has not been revalidated. The main demonstration
sets leaf respiration to explicit zero to isolate geometry feedback; the
nonzero-respiration deficit test checks rejection. Neither is a cultivation
prediction or a fitted Micro-Tom model.

Still required for full V2: original VTC determinate apex/truss/rachis/rank-dependent
development with validated accounting; 30-day seed spin-up; direct Stage-2
observation mapping and supported nonrectangular surfaces; measured optics and
lamp inputs; organ/root/fruit coverage; independent scientific review. A plant
age of 30 in a fixture does not mean 30 days of growth were simulated. Existing
unknown leaflet tilt/curl definitions remain open. No native state checkpoint
resume, subdaily integration, nutrient response or real-data accuracy is claimed.

Upstream attribution: Katarina Smolenova, WUR 2022–2025, VTC; adapted from Jochem
Evers' FSPM_BASIC. Source: https://github.com/ksmolen2/vtc . No model-code LICENSE
was found in the local archive or inspected repository root; redistribution
terms remain unresolved. Original download hashes are checked; no upload occurs.
