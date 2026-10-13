# Connected conditional P1 -> P2 -> P4 -> P3 workflow

Python consumes a versioned P1 package, freezes inputs, applies boundary checks, invokes one native GroIMP trajectory and validates its checkpoints. GroIMP alone updates carbon, age, organs and geometry. Python's existing nutrient ledger remains the sole prescribed water/element authority. Nutrient-growth feedback is disabled.

## Commands and public functions

Run from the project directory; all output directories must be fresh and under `build/`.

```powershell
python -X utf8 -m tools.tomato_fsp_pipeline inventory --out build/my_inventory
python -X utf8 -m tools.tomato_fsp_pipeline prepare --p1 build/my_p1 --scenario build/my_scenario/scenario.json --out build/my_fsp
python -X utf8 -m tools.tomato_fsp_pipeline run --run-dir build/my_fsp --timeout 1200
python -X utf8 -m tools.tomato_fsp_pipeline collect --run-dir build/my_fsp
python -X utf8 -m tools.tomato_fsp_pipeline replay --run-dir build/my_fsp --out build/my_replay
python -X utf8 -m tools.tomato_fsp_pipeline compare-observation --forecast build/my_fsp/committed/step_0003 --p1 build/later_p1 --out build/my_comparison
```

`audit_p1_package` is in `tomato_fsp_io`; `assemble_canopy` and `split_by_instance` are in `tomato_fsp_canopy`. The pipeline functions have the CLI responsibilities above. `advance_interval(folder, native_checkpoint)` and `commit_step` only validate and publish an already-produced native interval; they never call a second growth engine or advance the clock again. Stage-3 forecast wrappers should call `prepare_run/run` once per independent scenario and consume immutable results. Do not treat `advance_interval` as another physiology invocation.

Native P2 evaluation, development-demand proposal, resource allocation and realized growth occur in `vtc_development_native.rgg::simulate`. The proposal is exported before applying organ mass changes, and the graph is updated after allocation. All stages share the same native state. `light_only=true` evaluates a frozen scene without advancing mass, reserves, age or topology; it is a diagnostic mode.

## P1 boundary and explicit initialization

Supported schema: Claude's `p1_state_v1`, using the actual validators from `tomato3d.state.schema`. Read the generated `producer_consumer_map.csv`: the producer writes shared triangle CSV files per capture, so the adapter selects rows by `external_leaflet_id`; it must not read the whole file as a single leaf.

`canopy_placement.json` uses `instances[].transform.matrix_4x4`, from `plant_local_mm` to `canopy_mm`. Runtime organ IDs are `<instance>|<producer vertex>`. Duplicate source plants keep separate instance IDs and carbon/element pools. Local triangles and coordinates are converted from mm to m once. The native mesh applies the rigid placement once, while state coordinates stay plant-local. Normals rotate without translation; reflection/scale matrices are rejected. `app_ratio` is never multiplied into ray results.

The scenario explicitly chooses `captures_by_instance` at one aware `start_time`. Main-path observations require metric scale, located local geometry, supported leaf surfaces and confirmed identity. Unavailable values are never converted to measured zero. An explicit fixture-only `state_source=fixture_truth` can read the producer's separate `truth/truth_mtg_vertices.csv`; that is ground truth testing, not the observation path. Other declared candidates are not automatically mixed into it. Real mode cannot select truth.

Physiology is a separate scenario: per-organ mass (gDM), target mass, thermal age (degree days), true developmental order, units and provenance; per-plant reserves (gC), root and stem compartments, stem width, clock and apex counters. The P1 source remains unchanged. `scenario_fixture` declares synthetic mass/SLA, age/reserve/root assumptions explicitly; it does not infer measurements from photographs. A root and stem proxy are explicit compartments. Imported aggregate axis/compound nodes do not duplicate tissue mass.

Imported leaf meshes preserve their initial outline and posture, expanding isotropically with the square root of funded mass ratio. Imported structural segments use cube-root scaling; generated organs use the existing V3 conditional developmental law. This geometry extension is an assumption, not a calibrated response. Original P1 angle/area statuses remain in the frozen source; native rachis alpha is derived from the imported segment directions. No phototropism, nutrient-induced direction or blade-curl law is introduced.

## Time, light and state publication

Default duration is 86400 s. Numerical fixtures may use 43200 s; daily real input remains the supported boundary. For half-day refinement, `environment.light_hours` is the illumination duration within that interval, never a daily value repeated twice. Maintenance and thermal time scale by elapsed duration; growth respiration follows allocation. Emergence waiting time stays in elapsed days. CSV `day`, `state` and event indices are boundary indices; authoritative times and `duration_s` are in checkpoint metadata. Viewer days are scaled by the actual interval duration.

The refinement fixture distributes the declared photoperiod across equal intervals to test numerical sensitivity under interval-average climate. It is not a measured diurnal schedule. Within-interval lamp schedule changes and arbitrary substeps are rejected as unsupported scenario fields. Temperature affects thermal development only; fixed-coefficient NRH has no temperature or CO2 response.

Native light consumes the exact current placed meshes. Absorbed photon flux (umol/s) and one-sided-area-normalized absorbed PPFD are exported. Incident PPFD is explicitly unavailable. Black absorbing optics expose no tissue transmission/scattering; lower-leaf light through geometric gaps is not tissue transmission. Leaf absorption sums are a partial scene budget because non-leaf absorption and escape are not exported. Absolute point-lamp power is an explicit fixture assumption, not calibrated from phone ratios.

Each native boundary writes a checksummed prefix checkpoint. Python independently checks mass/demand/carbon, native topology, current-versus-consumed vertices and the scaled/placed original P1 triangles. It then writes a temporary directory and atomically renames it into `committed/step_NNNN`. Each directory contains current-light evidence, provisional resources, next-state candidate, final carbon/allocation/event tables, native geometry and synchronized nutrient ledger. Hash lineage binds the preceding checkpoint, source input, engine, geometry, topology, placement, lamps/optics, time/climate and random settings. No light cache is reused; every native interval recalculates light.

Repeated collection checks hashes and returns `already_committed` without charging anything. Resume semantics are fresh deterministic replay plus verification of the existing prefix; in-place native mutation/resume is unsupported. On native or required nutrient failure, only validated earlier checkpoints survive. Uncommitted future candidates are not a successful state. Intentional deficit rejects publication; it is not a biological starvation model.

## Nutrients, observations and limits

Optional `nutrient_scenarios` are existing `nutrient_balance.simulate` requests keyed by exact plant instance and covering the same interval. They are replayed from their immutable initial stocks through each checkpoint, and only the resulting snapshot is committed. Prescribed uptake remains prescribed. A required ledger failure blocks that checkpoint. No nutrient multiplier or joint allocation is invented.

`compare-observation` uses matching time, instance/organ identity and full-outline one-sided area. It preserves the forecast, marks unavailable correspondences, and performs no assimilation. Synthetic later packages test the interface; they do not validate predictions. A future state correction needs its own reviewed assimilation ledger and cache invalidation.

Scientific settings and real-input gaps remain in `handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md` and the staged execution report. V3's 65-day seed/birth/truss/stop evidence remains separate from short P1 integration runs. Full real photo reconstruction, independently validated Micro-Tom prediction, unrestricted branches, fruit/yield, transmissive leaf optics and nutrient-growth feedback are not established here.

## Delivered P1 example and verification

Claude delivered `build/p1_state_20261011_01` (fixture) and `build/p1_state_20261011_02` (real audit). The fixture observation path still has unresolved reconstruction/identity information. This explicit truth-route example selects four placed instances from the separate truth table; it does not promote their main observations to ground truth.

```powershell
python -X utf8 -m tools.tomato_fsp_acceptance --scenario-p1 build/p1_state_20261011_01 --state-source fixture_truth --intervals 3 --rays 4800000 --out build/my_truth_scenario
python -X utf8 -m tools.tomato_fsp_pipeline prepare --p1 build/p1_state_20261011_01 --scenario build/my_truth_scenario/scenario.json --out build/my_truth_run
python -X utf8 -m tools.tomato_fsp_pipeline run --run-dir build/my_truth_run --timeout 600
```

Use a fresh output directory for every attempt. The completed reference is `build/fsp_integration_20261011_producer_run_02`; its actual GroIMP optical geometry is in `native/results/viewer.html`. Initial organ creation is split into bounded native methods to avoid Java's per-method bytecode limit; triangle coordinates are loaded from the frozen, checksummed `initial_shapes.csv`. Neither changes the single-engine update order.

Later observation comparisons scope capture IDs by plant instance because the producer legitimately reuses a capture ID across duplicate instances. Observations without an aware timestamp remain unavailable. The existing forecast is never changed.

`tools.tomato_fsp_acceptance.summarize_delivery(out)` verifies hashes in the recorded delivery runs and produces `acceptance.json` plus a source snapshot. `controlled_light(out)` executes deliberately stacked and tilted fixture geometries for optical sensitivity; these are consumer test placements, not measured shelf geometry. `render_native_delivery(out)` plots returned native triangle coordinates.
