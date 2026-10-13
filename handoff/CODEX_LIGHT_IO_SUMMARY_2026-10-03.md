# Codex handoff: hierarchical light inputs and outputs

Project: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`

This is a short handoff for the existing light-interaction program, not a new implementation request. Read the parent `공통규약.md`, project `AGENTS.md`, `CONVENTIONS.md`, latest LOG and TODO before changes. Codex owns `tools/` and `tools/tests/`; preserve protected sources and human data. Generate outputs in fresh `build/` directories.

## Existing implementation

- Entry point: `tools/hierarchical_light.py`; native adapter: `tools/hierarchical_light_native.py`.
- Synthetic demo: `tools/hierarchical_light_demo.py`; viewer: `tools/hierarchical_light.html`.
- Detailed contract: `tools/HIERARCHICAL_LIGHT.md`.
- Delivered example: `build/hierarchical_light_20261003_04/` (see `REPRODUCTION.md`, `verification.json`, `results/viewer.html`).
- Recorded verification: 113 related tests passed; final focused suite 41 passed. These are historical results, not a new test run for this summary. Native jobs were prepared, not executed.

## Environment and physical inputs

The hierarchy CLI requires no custom OS environment variables. Paths come from `--input` and `--out`; output is restricted to project `build/`. Shared project settings exist but are not directly consumed here: `TOMATO3D_DATA_ROOT=./data`, `TOMATO3D_CONFIG_DIR=./config`, `TOMATO3D_CAMERA_ID=cam_a`, `TOMATO3D_LOG_LEVEL=INFO`, `TOMATO3D_MAX_WORKERS=4` (defaults). Native execution accepts `--java` and `--core`; default Java is resolved through PATH.

| Input | Content |
|---|---|
| `input.json` | Schema `hierarchical-light-1`, file paths, scenario, instances, source dates, selection filters and resource limits. Paths are relative to this JSON. |
| `scene.json` | Lamp position/size in mm, orientation in degrees, PPF in umol/s, beam distribution, plant placement/yaw, uniform leaf absorptance/reflectance/transmittance (0–1). Physical values retain value/status/source provenance. |
| `leaf_surfaces.csv` | Existing leaf triangle vertices in board-frame mm; plant/session/variant/organ/leaflet/triangle IDs and normal convention. Area and normals are derived from triangles. |
| `membership.csv` | Source plant, instance, session, date, variant, organ, leaflet, compound, identity status and evidence path/hash. Join: instance + session + organ + leaflet. |
| Surface review JSON | Accepted leaf-triangle review, reviewer/time, matching geometry hash, variant/date and completeness. |
| Optional `background_csv` | Fixed walls/supports/occluders: geometry and optical properties using the existing PPFD rig-surface schema. |

PPF is lamp photon output; PPFD is calculated at the receiving tissue. Temperature, RH, CO2, EC, pH and wind are not used. Schedule and electrical power exist in the shared scene schema, but this tool reports full-output light and does not calculate DLI or energy efficiency.

Numerical controls: `triangle_subdivisions` (n² samples/triangle), `emitter_grid`, `ray_offset_mm`, `max_ray_triangle_pairs_per_chunk`; total limits: `max_transport_calls`, `max_receiver_emitter_pairs`. Optional `target_ids` and `source_entity_ids` filter reporting without removing other occluders. Native controls: `rays`, `max_depth`, `seeds`, `max_jobs`, `max_total_rays`.

## Calculation and outputs

Keep the receiving leaflet, including its own folds, and fixed background in every calculation. Partition other tissue into A = same compound, B = other compounds on the same plant, C = other plants. Evaluate all eight subsets. Report baseline/full light, total loss, standalone/marginal effects, signed three-group Shapley allocation and overlap terms. Shapley allocations sum to total loss; individual source-removal effects are nonadditive. Aggregate flux before dividing by supported area.

| Output | Meaning |
|---|---|
| `interaction_cases.csv` | Eight raw subset results, fixture/replicate/status, received and absorbed flux (umol/s), PPFD (umol/m2/s), supported one-sided area (m2). |
| `leaflet_interactions.csv`, `compound_interactions.csv`, `plant_interactions.csv` | Hierarchy summaries: `baseline_*`, `full_*`, `total_loss_*`, `loss_fraction`, `shapley_A/B/C_*`, `overlap_*`. A zero baseline makes the loss fraction unavailable. |
| `source_target_interactions.csv` | Directed removal effects at leaflet/compound/plant levels; diagonals unavailable because target tissue must remain. |
| `replicate_summary.csv` | Replicate means and paired-effect standard errors; no uncertainty estimate from a single deterministic run. |
| `viewer.html`, `results.json` | Interactive 3D inspection and complete results. Visibility controls do not recalculate physics. |
| `audit.json`, `manifest.json` | Blockers, reviews, source/code/artifact hashes, placements, settings and provenance. |

Unavailable values are `unavailable` in CSV and null in JSON, never zero. Preserve signed effects. Partial supported surfaces are not whole-plant estimates. Direct transport excludes reflections and supports opaque background blockers; native transport can model reflection/transmission and is not equivalent to direct transport. Leaf optics are shared across leaves; heterogeneous optics are unsupported.

## Run and continue

Run from the project root, always using fresh output paths:

```powershell
python -X utf8 -m tools.hierarchical_light --help
python -X utf8 -m tools.hierarchical_light demo --out build/light_demo_new
python -X utf8 -m tools.hierarchical_light templates --out build/light_inputs_new
python -X utf8 -m tools.hierarchical_light audit --input build/light_inputs_new/input.json --out build/light_audit_new
python -X utf8 -m tools.hierarchical_light prepare --input build/light_inputs_new/input.json --out build/light_prepared_new
python -X utf8 -m tools.hierarchical_light calculate --input build/light_prepared_new --out build/light_results_new
python -X utf8 -m tools.hierarchical_light stale --input build/light_results_new
python -X utf8 -m pytest tools/tests/test_hierarchical_light.py -q
```

Fill actual inputs before prepare/calculate. Native preparation uses `--backend native`; execution requires a separate `execute` command with explicit `--execute` and declared budgets. Preparation/demo does not launch native jobs.

Last scoped real audit: `build/hierarchical_light_real_audit_20261003_01/`. Known dwt_01/T1/T2/T3 snapshots lacked the light scene, accepted optical surfaces and selected plant light case; T3 also lacked registered geometry provenance. Real hierarchy attribution additionally needs reviewed compound membership. Re-audit supplied current inputs, preserve gates and do not fabricate missing values or optical surfaces. All physical-validation flags remain false. No growth or photosynthesis prediction is provided.

## Implemented consumer-extension supplement — 2026-10-03

The historical hierarchy full-output contract above remains unchanged. A new additive `light-growth-1` package is now available through `python -X utf8 -m tools.light_growth_bridge --help`; request/column details are in `tools/LIGHT_GROWTH_BRIDGE.md` and `tools/light_growth_schema.json`.

- Implemented: full-scene direct samples and one-sided area weights; normal/opposite/incident/absorbed PPFD; weighted scalar/quantile exports; reviewed compound-state joins with separate source/instance identities and observation clocks; observed rachis direction and measured-frame supported regions; fixture schedule intervals, dose and complete-day DLI; reversible board/grow transforms and canopy-preserving per-instance reporting; independent package validation.
- Native: retain existing scalar outputs/replicates. Equal known fixture fractions may scale the combined response. Unequal schedules, sample distributions, side and directional channels remain unavailable. No native execution is initiated.
- Pending: core per-path angular diagnostic hook, then consumer callback wiring and transport parity. Synthetic F/M/B algebra is verified but does not supply missing live directional transport. No biological growth, area forecast, photosynthesis or respiration is calculated.

Join `(run_id, scenario_id, geometry_snapshot_id, plant_instance_id, session_id, compound_id, time_step_id, backend, replicate)` to an explicitly reviewed `compound_leaf_id`. Source-board `observed_rachis_x/y/z` maps to growth `direction_unit_xyz`; light arrival is a separate covariate and currently unavailable in production. `supported_area_cm2 = supported_area_m2 * 10000` requires the same reviewed area basis. Physiology uses time-indexed direct samples, m2 weights and duration; absorbed PPFD already contains absorptance. Never use first-leaf=1 image ratios as metric area or multiply absorptance twice.

Final synthetic package: `build/light_growth_readiness_20261003_03/`. Related regressions: 266 passed; final focused bridge checks: 24 passed. Main package and two same-source-instance splits pass the independent serialized consumer. Full requirement evidence and remaining gates are recorded there. Known real snapshots remain missing required scene/surfaces; all original hashes checked unchanged. Full growth-direction readiness is not yet achieved because the angular hook is still missing. See `handoff/CODEX_LIGHT_GROWTH_READINESS_EXECUTION_2026-10-03.md`.

Consumer verification correction (continuation 2): the original checker accepted incompatible scalar values in non-grow frames and unsupported invented direction values. These producer-error fixtures now fail. Frame-invariant scalars/IDs, observed direction rotations, local-region areas/flux/quantiles/contrasts and channel capabilities are independently verified. Final focused checks: 32 passed. Current package: `build/light_growth_readiness_20261003_04/`; _03 remains immutable input/legacy evidence. The directional core hook is unchanged and still missing; no new growth or cross-project integration readiness is claimed.


## Incident-direction receiving preparation, 2026-10-03

The protected direct_light interface remains scalar/side-only. tools/light_direction_diagnostics.py now accepts the explicitly proposed direct-angular-proposal-1 callback stream, validates complete fixture/global receiver/emitter inventories and chunk order, distinguishes unknown from actual zero, and accumulates per-receiver area-weighted grow-frame F/M/B (umol/s). Supplied-chunk protocol checks are not actual transport evidence. Production exports and native capabilities stay unchanged/unavailable. Exact callback contract, borrowed-array lifetime, missingness, limits and required core-owner tests: handoff/CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md. Outcome: 60 combined checks and 28 final collector checks passed; existing _04 main/two splits remain consumer-valid; new evidence is build/light_direction_callback_20261003_01. Real producer wiring, schedule/frame directional export and independent serialized angular validation remain pending.


## P2 continuation / D9 basis supplement, 2026-10-03

Current scalar delivery is build/light_growth_readiness_20261003_05, freshly prepared/calculated/exported with two canopy-preserving instance splits. DLI unit metadata is clarified as mol/m2/day (generic interval dose remains mol/m2); all numerical values and missingness match preserved _04 exactly. 60 related checks and all three independent consumers pass. Exact D9 identity, supported-area, incident/absorbed, timing, schedule, geometry-mode and coverage field map is in CODEX_P2_LIGHT_CONTINUATION_2026-10-03.md. No representative day or fixed-horizon P3 covariate was silently chosen. Protected core still has no callback; actual angular output and physical validation remain incomplete.

## Actual angular output delivered, 2026-10-04

This supplement supersedes the historical missing-callback statements above. The authorized P2 software path now uses `tomato3d.light.raytrace.direct_light` with optional keyword-only `diagnostic_callback` and `diagnostic_max_paths_per_chunk`, protocol `direct-angular-1`. Actual attenuated receiver-cosine PPFD paths and receiver-to-emitter grow-frame unit vectors feed the existing collector; no second tracer or fixture-center approximation.

Inputs remain the existing scene, accepted optical geometry/membership, placement, optics, explicit per-fixture schedules and resource budgets. No new environment variables. The same-call collector checks full fixture/global receiver/emitter inventories, contiguous chunks and scalar/normal-side parity. Callback arrays are read-only and borrowed until return; copy to retain. Unknown paths remain explicit and invalidate complete moments.

New sample fields: global `receiver_index`, `arrival_path_unknown_count`, `arrival_flux_umol_s`, `arrival_M_{x,y,z}_umol_s`, `arrival_B_{xx,xy,xz,yy,yz,zz}_umol_s`. F/M/B use supported one-sided metric area and grow-frame arrival vectors; all raw moment components are umol/s. Per-fixture clock fractions scale raw moments before aggregation. Feature rows normalize after summation and rotate M/B into board and reviewed full-axis/transverse compound frames. Observed rachis direction stays separate from illumination. F=0 has unavailable normalized outputs; opposing directions preserve B/F while dominant direction is unavailable. Native spatial/side/angular channels remain unavailable.

`angular_diagnostics.json` adds per-snapshot inventory/chunk/parity evidence. Existing columns retain their meanings under the additive exact-schema/hash check. The independent consumer verifies serialized F=area*PPFD, raw fixture/time/region/frame sums, normalization and path inventories. Canopy splits preserve original global indices, shading and context hashes.

Current verified synthetic delivery: `build/light_growth_directional_20261004_01/{package,P1_in_canopy,P1_COPY_in_canopy}`. 240 tests pass; all three consumers pass. Actual off/on and path-sum maximum errors in measured workloads are 0.0 with atol 1e-10, rtol 1e-9. Complete report: `CODEX_P2_DIRECTIONAL_DELIVERY_2026-10-04.md`; exact callback contract: `tools/DIRECT_ANGULAR_CONTRACT.md`.

Fresh real-lamp draft: `build/lighting_REF_30_40_three_20261004_03/`. Three rear-offset REF-30-40 lamps, floor-relative height 400 mm, confirmed 16 hours/day at 100%. Clock windows, PPF, actual emitting aperture, beam and electrical boundary remain unresolved. It is intentionally incomplete; specifications are user-reported and no real PPFD accuracy is claimed. Physical geometry/optical validation, growth prediction and cross-project integration remain separate.

## Growth Science reference-DLI clarification, 2026-10-04

This supersedes any earlier suggestion that supported-tissue DLI can directly supply P3's accepted reference DLI. P3 requires incident DLI at one declared reference position and sensor plane over a complete local day, with whole-plant model scope, a reference basis distinct from tissue area bases and a declared DLI applicability interval. P3 owns model applicability and c_DLI binding by growth_curve.

P2 light-growth-1 has no supported reference-position daily channel. Current output explicitly declares reference_dli unavailable with null value/basis/interval; the independent consumer rejects invented values/capabilities, tissue-basis reuse and incompatible unit/quantity/spatial/time semantics. No sensor, sampler, numeric reference value or model range was added. Tissue dose/DLI, scalar/side/angular values and canopy splits are unchanged. L02 outputs remain illumination, not growth orientation; P3 owns that binding guard. Future P4 exchange must sum simultaneous fixture light on the same patch/time before nonlinear response; no unselected face/respiration policy is imposed.

Current fresh package and splits: build/light_growth_science_20261004_01. Verification: 181 tests pass (84 core, 97 tools), all three independent consumers pass, all five tables in all three deliveries exactly match prior numerical values, historical hashes and real-lamp draft are preserved. Execution/required future reference fields: CODEX_P2_GROWTH_SCIENCE_EXECUTION_2026-10-04.md. Audit: build/p2_growth_science_20261004_01/verification.json. Real lamps remain 16 h/day at 100%; actual clock windows/PPF/optical evidence and physical accuracy remain unresolved. No P3/P4/calibration changes or interproject execution.
