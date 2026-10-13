# Staged P1 consumer / P2 / P4 / P3 integration execution

Date: 2026-10-11. Status: conditional native connected workflow delivered; independent biological validation and real-photo forecasting are not established.

The queued staged prompt was implemented after the V3 development work. The user authorized conditional scientific choices for V3 and requested a separate settings list; that list is `VTC_V3_PENDING_DECISIONS_2026-10-11.md`, now extended for imported P1 geometry and integration. S2 assigns the separate Micro-Tom/Stage-3 forecast wrappers to Claude Code; this delivery owns the native boundary, checkpoints and connected loop only. No competing forecast wrapper, tracking implementation or nutrient-growth law was added. Protected docs/config/data/records and original VTC source were not edited.

## Delivered paths

| Item | Path relative to project |
|---|---|
| CLI/orchestrator | `tools/tomato_fsp_pipeline.py` |
| Actual P1 consumer and native initialization | `tools/tomato_fsp_io.py` |
| Canopy merge/split and rigid transform | `tools/tomato_fsp_canopy.py` |
| Fixtures, executed-result summarizer and native mesh plot | `tools/tomato_fsp_acceptance.py` |
| English guide | `tools/TOMATO_FSP_PIPELINE.md` |
| Conditional exchange contract | `handoff/FOUR_PROJECT_INTEGRATION_CONTRACT_2026-10-11.md` |
| Separate decisions/settings | `handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md` |
| Tests | `tools/tests/test_tomato_fsp_pipeline.py` |
| Main delivered-producer native run | `build/fsp_integration_20261011_producer_run_02` |
| Final acceptance/source snapshot | `build/fsp_integration_20261011_delivery/acceptance.json`, `source/` |
| Native optical geometry viewer | `build/fsp_integration_20261011_producer_run_02/native/results/viewer.html` |
| Inspected native mesh figure | `build/fsp_integration_20261011_visual_01/native_canopy.png` |
| Real-input readiness audit | `build/fsp_integration_20261011_real_audit_01/audit.json` |

The native V3 template/controller/validator, observation initializer, viewer and shared launch bridge were extended within existing claims. Seed-mode behavior and historical V2 remain separate. Native initialization is divided into bounded methods, and the exact imported triangles use a checksummed auxiliary CSV, to support larger real exporter meshes within the JVM method-size limit.

## Actual producer delivery and consumer route

Claude's actual P1 producer now provides `build/p1_state_20261011_01` (synthetic fixture) and `_02` (real-photo audit). The consumer calls `tomato3d.state.schema` validators; it does not invent a matching P1 schema. `producer_consumer_map.csv` records exact table/field mappings. Shared mesh CSVs are filtered by `external_leaflet_id`; capture IDs are scoped by instance, not globally unique.

The completed main example explicitly selects `state_source=fixture_truth` and reads `truth/truth_mtg_vertices.csv` separately from the P1 observation path. It imports `fx_om0`, `fx_om0#2`, `fx_om1`, and `fx_sp0`, including a duplicated source with isolated runtime IDs and pools. `fx_other` is excluded according to the producer's optical-scene flag. The fixture's main observed path contains unresolved reconstruction/correspondence, so successful truth-route execution is not successful image-to-3D reconstruction. The `fx_sp0` source morphology is not validation of the shared developmental parameterization for that cultivar.

Run start: 2026-10-12 08:00 +09:00; end: 2026-10-15 08:00 +09:00. Three daily native intervals, 4.8 million rays, seed 5000, Java 21 / GroIMP 2.2.1. Native process exit: 0; Python prepare/run/collect invocation exit: 0. The actual native command, runtime version, core hash and elapsed seconds are in `native/execution.json` and copied into final acceptance. The core hash is `35c605d65d9b54fe64cdf93bf28ae44ae7a1b6ded03b461dedcb0156a5c22147`.

Initial native graph: 250 organs, including 129 imported leaflets. Final graph: 294 organs, 44 generated additions; final dry mass 3.260420883171523 gDM. The native optical output contains 37,339 triangles at the final boundary. Maximum independent carbon ledger residual: 9.020562075079397e-17 gC. Initial-to-final mass and returned native meshes appear in the figure. These are conditional numerical outputs, not measured biomass.

## Stage results

| Stage | Executed evidence | Limits |
|---|---|---|
| 0 — contract | Actual producer fixture + real audit; frozen source, schema/code/input hashes, explicit hidden state; corrupt frame/scale/ID/schema/optics rejected | Real inputs are not ready; fixture truth and observed reconstruction remain separate |
| 1 — canopy | Three-instance duplicate-source control plus four-instance producer run; proper rigid transform, normalized normals, preserved area, exact merge/split membership; mm converted once | Shelf dimensions are assumptions; unprovided shading objects cannot be invented |
| 2 — light | Native frozen light-only runs; no-source zero; low/high-ray and seed comparison; separate stacked-occluder and rigid-tilt stress controls | Absorbed leaf flux/PPFD only; incident PPFD unavailable; no whole-scene escape/nonleaf energy budget |
| 3 — resources | Native pre-growth proposals; independent NRH, maintenance, demand, allocation and reserve closure; per-plant pools | Fixed NRH response, hypothetical optics and physiology; temperature/CO2 exchange responses inactive |
| 4 — growth | Funded native mass, births, graph edges and meshes; P1 imports preserve initial posture and expand from funded mass; generated organs reuse V3 | Imported shape scaling and V3 development remain conditional; no phototropism/fruit/yield |
| 5 — feedback | Three consecutive intervals, native consumed geometry, new hashes, one advance per checkpoint, matched dynamic/frozen control, fresh replay, half-day fixture comparison | Frozen geometry per interval; no in-place native resume; next-interval interception for new tissue |
| 6 — extensions | Prescribed water/element ledger synchronized by instance/time; disabled-feedback equivalence; required failure blocks step 2 while preserving step 1; read-only later observation comparison | Nutrient-growth feedback and assimilation disabled; no uptake inferred from photos or EC/pH |
| 7 — delivery | Documented CLI, immutable outputs, source snapshot, acceptance artifact, native mesh viewer/figure, tests and logs | No independent biological or real prediction validation |

Each successful run includes `stage_0_contract_report.json` through `stage_6_extensions_report.json`. Cross-scenario optical, timestep and failure evidence is consolidated in the final `acceptance.json`; individual stage files alone do not certify those cross-scenario gates.

## Controls and numerical interpretation

The matched three-instance exporter-API fixture has 171 initial organs, 84 leaflets and 24,468 source leaf triangles. `final_02` is a fresh replay of `final_01`; all three existing checkpoint states match within 1e-9. The native engine, rather than Python, owns all growth updates.

| Control | Evidence path under `build/` | Result |
|---|---|---|
| Dynamic | `fsp_integration_20261011_final_02` | Total leaf absorption 1.937 → 2.747 → 2.76075 umol/s; final mass 2.3323574374407596 gDM |
| Frozen geometry | `fsp_integration_20261011_controls_01/frozen` | Absorption stays 1.937 umol/s; final mass 2.3249354211126514 gDM |
| Alternate seed | `fsp_integration_20261011_controls_01/seed` | 1.87775 → 2.7385 → 2.751 umol/s; maximum matched dynamic difference 0.05925 umol/s |
| Resolved feedback | Above matched runs | Last-interval dynamic/frozen difference 0.82375 umol/s exceeds measured two-seed variation |
| No nutrient bookkeeping | `fsp_integration_20261011_controls_01/no_nutrient` | Same identities/mass/age/dimensions as dynamic; feedback disabled in both |
| Half-day refinement | `fsp_integration_20261011_refinement_01/run` | Six half-day intervals over the same three days: mass 2.337429183326465 gDM, approximately 0.21745% above daily |
| Frozen light | `fsp_integration_20261011_light_01/full`, `light_02/*` | No mass, age, reserve or topology advance; dark run has zero absorption |
| Original shelf isolation/yaw | `light_02/isolated`, `orientation_01/run` | Effects too small relative to tested sampling variation; not claimed as resolved sensitivity |
| Controlled optical stress | `fsp_integration_20261011_optical_stress_01/*` | Receiver shading effect 0.09675 umol/s; rigid-tilt effect 0.30825 umol/s; maximum tested receiver seed difference 0.0205 umol/s |

The half-day fixture repeats interval-averaged 7 h light + 5 h dark; the daily control uses 14 h + 10 h. This is a numerical refinement diagnostic, not an actual subdaily illumination schedule or a general convergence proof. Arbitrary/subdaily real schedules are rejected until supported. Low-ray (100,000) versus high-ray (4.8 million) total leaf absorption differs by 7.073%; the two high-ray seeds differ by 3.059%. These quantify variation for these scenes only; they are not confidence intervals or calibration against sensors.

The stacked plant is deliberately moved above the receiver along the source direction; the tilt is a proper rigid matrix, not simulated phototropism. Both are labelled consumer-derived synthetic optical stress fixtures. Black tissue absorbs and does not transmit: downstream illumination through geometric gaps must not be described as leaf transmission. Leaf sums are checked without duplicated faces; total emitted-photon closure remains unavailable.

## Transactions, failures and tests

The native trajectory exports `proposals.csv`, states, ledgers, topology, events, committed/consumed mesh vertices and per-boundary completion hashes. Python validates prefixes independently and atomically publishes `committed/step_NNNN`; each is bound to its predecessor, inputs and engine. `advance_interval` is an alias for validating/publishing an already-produced native checkpoint, not a second physiology calculation. Collection is idempotent. Fresh replay checks the prior prefix and cannot charge a published step twice.

`fsp_integration_20261011_failure_01/run` completes native calculation but intentionally overdraws the required water ledger after the first day. Python rejects step 2 (`Water loss exceeds available water`), leaves only checkpoint 1 committed, and records the failed attempt. Native future output is not advertised as committed state. `fsp_integration_20261011_comparison_01` compares a later explicit producer-API fixture without assimilation or changes to forecast hashes. A regression also covers duplicate capture IDs across instances at different observation times.

Development failures are retained, not relabelled as successful: `producer_run_01` exceeded the JVM method-size limit and timed out without a ready acknowledgement; `producer_run_02` fixes that by bounded initialization and succeeds. The bridge now recognizes this compile/open failure promptly. `light_01/full_seed` failed preparation during the interval-template edit; the fresh `light_02/full_seed` is the successful evidence. No native success is claimed for either failed attempt.

Earlier broad regression: **288 passed** (integration, V3, legacy bridge, light, carbon diagnostics, nutrient ledger and compound growth). After the final boundary/compiler fixes, the affected subset plus four new boundary regressions: **102 passed, zero failures/errors/skips**, JUnit in `build/fsp_integration_20261011_regression_final.xml`. These counts overlap and must not be added. Native compatibility smoke also reruns the seed mode after integration extensions; its evidence is `build/vtc_dev_postintegration_run_02`.

Executed final test command (exit 0):

```powershell
python -X utf8 -m pytest tools/tests/test_tomato_fsp_pipeline.py tools/tests/test_vtc_development.py tools/tests/test_vtc_growth_bridge.py -q -rA --junitxml=build/fsp_integration_20261011_regression_final.xml
```

The guide gives repeatable CLI commands using fresh output paths. Final acceptance succeeded with **16 verified native runs / 31 intervals**, checking each successful native exit, source/model/checkpoint hashes and ledger results. Its final source snapshot includes compatibility/performance fixes made after some earlier control runs; each run's frozen `Model.rgg`, inputs and prepared hashes identify the exact code-generated model actually executed. Historical evidence is never rewritten to pretend it used a later snapshot. `summarize_delivery` exited 0. The post-integration seed-mode smoke also exited 0 with `verified_native_trajectory`.

## Real readiness, preserved V3 evidence and next owner

The real audit contains 117 captures, all missing a solved metric scale and timezone-aware capture timestamp, and 13 plants with unavailable optical surfaces. Raw-photo hashes were checked. The producer's `audit_gaps.csv` additionally explains detector/scale/identity/environment limitations. No synthetic meshes, assumed masses or true IDs were substituted into this real audit. Even a complete geometry package would still need declared initial physiology and supported absolute illumination.

V3 long-horizon evidence remains `build/vtc_dev_v3_delivery_sufficient` (65 daily intervals, 4.8 million rays), `build/vtc_dev_v3_acceptance_01/acceptance.json` and `handoff/VTC_WHOLE_PLANT_DEVELOPMENT_EXECUTION_V3_2026-10-11.md`: 30-day spin-up, continued growth, funded trusses, determinate stops, deficit rejection and native geometry feedback. A three-day integration run does not substitute for that development evidence.

Claude/user follow-up: review the separate decision list, provide real scale/pose/identity/time/hidden state and absolute light/optics, and establish biological validation. Claude Code's S2 forecast wrapper should consume this single pipeline authority and preserve its conditional/unavailable flags. Nutrient-growth feedback needs a separate executable joint-allocation contract. VTC redistribution license remains unresolved; all source-derived execution artifacts stay local.
