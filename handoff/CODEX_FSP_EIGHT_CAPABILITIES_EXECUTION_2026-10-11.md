# Native FSP eight-capability extension execution

Work-order date 2026-10-11; executed through 2026-10-12. Status: implementable optical/schedule/hook/intake mechanics delivered, with explicit partial/pending capabilities. **Not all eight capabilities are complete.** E2 terminal photon accounting, E6 developmental deformation and E7 causal nutrient growth remain unavailable. Real-photo prediction and biological validation are not established.

The subsequently assigned declared-side-axis work is integrated in the same native authority and documented separately in `P4_SIDESHOOT_EXECUTION_2026-10-12.md`. It does not replace or silently cancel the extension work order.

## Artifacts and status

Contract written before code: `FSP_EIGHT_CAPABILITIES_CONTRACT_2026-10-11.md`. Guide and field migration: `tools/FSP_EXTENSIONS.md`. Core additions: `fsp_extensions.py`, `fsp_extensions_native.rgg`, `fsp_extensions_acceptance.py`, `fsp_observation_intake.py`, `fsp_nutrient_transaction.py`, plus their integration into the existing V3 and pipeline files. Tests: `tools/tests/test_fsp_extensions.py` and affected regression suite.

Final evidence: `build/fsp_extensions_axes_20261012_delivery_01/acceptance.json`, `axis_acceptance.json`, `source_hashes.json`, `source/`. The consolidation script `build/fsp_delivery_checks_20261012.py` exited 0 after independently checking **30 native runs / 150 intervals**, including the separate **9 side-axis runs / 29 intervals**. Historical preliminary repeats and the additional actual forecast-wrapper invocation are not added into that 30-run total. Each native execution has its actual command, Java version, core hash, frozen model/input hashes, exit code and output hashes. All successful executions use GroIMP 2.2.1, Java 21.0.12.1 and 4.8M rays.

| Capability | Delivered evidence | Remaining limit |
|---|---|---|
| E0 contract | Pre-code inventory/contract, opt-in versioning, frozen inputs and source snapshot | Biological choices remain conditional |
| E1 intake | Explicit observed_metric/conditional_completion/observation_only/fixture_truth routing; source hashes, field evidence and separate hidden state; observed-metric **fixture** native round trip; genuine real-package audit | Real metric surfaces unavailable. Full metre-based producer packages unsupported; only m/mm conversion primitive tested. Actual producer completion adapter/manifest not delivered. |
| E2 photon accounting | Independent raw first-hit received, absorption, reflection/transmission tallies; emitted W; leaf/nonleaf split; explicit wavelength conversion; empty/plane/dark controls | Total repeated incidence for nonblack leaves and terminal escape/cutoff/residual categories unavailable. No fabricated photon closure. |
| E3 reflection/transmission | Actual native Phong Lambertian reflection and straight transmission; black compatibility, clear/reflector limits, reflected receiver effect above two-seed variation | Grey monochromatic scenario, no spectral/angle calibration. Nonblack P4 growth blocked pending NRH fit-basis decision; multi-bounce terminal closure unavailable. |
| E4 scene objects | Static explicit meshes, roles/materials/rigid transforms, native nonleaf absorption and duplicate-surface gates; object shadow/reflector controls | Actual pot/shelf/non-target geometry still needs inputs; no non-target growth model |
| E5 schedules | Aware piecewise source/environment intervals, midnight/off/dimming/staggered lamp execution, actual elapsed maintenance/thermal clock, analytical source integrals, refinement comparison and elapsed-time viewer | Frozen geometry per interval; physiological temperature/CO2 response unmodeled; convergence demonstrated only in tested cases |
| E8 H1-H3 | Exact-count normalized bend vectors; stable per-compound posture draws; reporting-only area correction; three native 30-day runs; actual H3-enabled wrapper invocation | Imported posture unchanged; observed bend classification thresholds and blade curl remain on hold |
| E6 imported deformation | Exact initial imported meshes and existing funded scaling preserved; independently tested anchored rigid-rotation primitive | No reviewed developmental age/anchor/mass-area law. Runtime imported_deformation rejects; no bending/phototropism claim. |
| E7 nutrient transaction | Explicit interface fixture with IDs/hash/interval/plant bindings, available/used/unused checks, atomic commit, timeout/stale/retry/conflict/partial failure tests | No native proposal/pause/finalize handshake or causal growth constraint. Science contract missing; prescribed ledger remains plant-level diagnostic. |

## Backend inspection and optical results

Official GroIMP documentation describes independent received/absorbed/reflected/transmitted power, and source power in watts:
https://wiki.grogra.de/doku.php?id=tutorials:light-modeling-lm-functions and
https://wiki.grogra.de/doku.php?id=tutorials:light-modeling-light-sources.
Matching tag 2_2_1 source was inspected and frozen under `build/fsp_extensions_20261011_api_01`, with URLs/hashes in sources.json (tag commit 1fcd4e4a89e6b71b10d3b69188f797b4b2972510). LightModelProcessor suppresses repeated received-power hits on the same object along a path and does not export miss/cutoff terminal bookkeeping. Phong supports separate diffuse reflection and straight transmission with interpolated transparency disabled. No native JAR was modified; available API/source limitations are exposed.

Extension input power is umol/s converted to watts at the explicitly assumed monochromatic 550 nm fixture wavelength. Raw radiometric fields remain separate. `escape_W`, `termination_W`, `estimator_residual_W` and their photon counterparts are unavailable. Reflection and transmission tallies are internal transfers. Legacy requests retain their previous numerical-power convention; none is silently treated as a measured spectrum.

Optical controls are in `build/fsp_extensions_20261011_optics_01` (black/clear/mixed), `_optics_02` (successful reflector/shade/clear plate/floors/dark) and `build/fsp_extensions_20261012_optics_seed_01` (alternate seed).

| Optical result | Value |
|---|---|
| Legacy black leaf total | 0.6450000000000002 umol/s |
| Extension black leaf total, same seed | 0.6450000050160447 umol/s |
| Alternate-seed extension black | 0.6232500048468991 umol/s |
| Mixed A=.5/R=.2/T=.3 leaf total | 0.4058237255926607 umol/s; alternate seed 0.388212886310272 |
| Clear-leaf raw residual absorption | 9.924173354612326e-9 umol/s |
| Perfect-reflector raw signed absorption | -2.0071864521419925e-8 umol/s |
| Black upper occluder / no sources | Both zero leaf absorption |
| Transparent upper plate | 0.6312500000513348 umol/s; small difference from empty control lies within measured seed variation |
| Reflected receiver gain | Mean 0.5665000178687639 umol/s above black floor; maximum tested two-seed floor-case variation 0.018000000139982708 |

Perfect-limit signed residuals arise from native float32 spectral subtraction. Raw values are preserved. A relative float32 roundoff bound is checked before negative near-zero absorption is clamped for physiology; this is not a physical uncertainty or terminal energy remainder. The first perfect-reflector attempt in `_optics_01` failed the earlier strict nonnegativity check and remains a failed artifact; the corrected fresh `_optics_02` run is the success evidence.

`build/fsp_extensions_20261012_planes_01`: the empty optical scene has zero leaf/nonleaf absorption. The single 4x4 m absorbing plane, 0.3 m below an isotropic point source, intercepts fraction **0.4330864617013685** versus the analytic solid-angle fraction **0.43310027357496234**. Bernoulli ray standard error is **0.000226165696358267** at 4.8M rays; the declared six-standard-error engineering gate passes. This tests direct interception, not measured escape or full photon closure.

## Schedules, geometry and optional hooks

`build/fsp_extensions_20261012_schedule_02` replaces the earlier display-time snapshot with correctly elapsed-time-labelled publication. Scenario: 21:30 to 02:15 Asia/Seoul (17,100 seconds), full lamp until 22:15, off until 00:15, half power thereafter; temperature boundary at 23:15. Coarse has four intervals, refined has ten. Both integrate **6,300 full-power-equivalent seconds**, thermal increment **3.517708333333333 degree-days**, and final total mass **2.264901669676923 gDM**. Off-interval absorption is zero. Maintenance is independently recomputed from starting tissue mass times the full elapsed interval. Identical final mass in this particular short, adequately funded target-curve case is not a universal convergence or equal-DLI/equal-assimilation claim. Native validation recomputes nonlinear NRH separately for every interval.

`build/fsp_extensions_20261012_intake_01/run` adds an explicit observed_metric **synthetic main-table** route and two staggered lamps: emitted photon flux 1200 then 150 umol/s over 30 and 45 minutes. It demonstrates routing/geometry consumption and source-specific schedule execution, not real photo reconstruction.

`build/fsp_extensions_20261012_hooks_02`: disabled, hooks and reporting-only variants each execute 30 native seed days at 4.8M rays. H1 actual segment bends pass independent returned-state checks. H2 retains both 0 and 20 degree declared templates under stable organ-ID/seed draws. H3 changes factor 1 -> 1.25: maximum state difference **1.3877787807814457e-17**, flux difference **5.551115123125783e-17**, and mesh-coordinate difference **0**. These are floating summation differences, with identical optical geometry; corrected reporting areas equal uncorrected areas times 1.25. Imported human posture labels are never overwritten.

## Real readiness and wrapper compatibility

Initial real audit consumed P1 `_02`; after the parallel owner delivered user-confirmed camera timezone metadata, a fresh audit consumed `build/p1_state_20261011_03` into `build/fsp_extensions_20261012_real_intake_02`. The earlier audit is preserved. Current producer gaps are **130**: 117 missing metric scales and 13 unavailable optical surfaces; timestamp gaps are resolved in that new package. The intake also names simulation-not-requested and hidden-state requirements. It performs no truth substitution, shape completion or native real-data forecast. Per-field source statuses and source hashes are preserved.

The delivered Claude B1-B6 wrapper was exercised unchanged through its public CLI:

```powershell
python -X utf8 -m tools.microtom_forecast scenario --engine pipeline --p1 build/fsp_integration_20261011_p1_fixture_01 --state-source main --horizons 1 --members 1 --rays 4800000 --out build/fsp_extensions_20261012_wrapper_scenario.json
python -X utf8 -m tools.microtom_forecast issue --scenario build/fsp_extensions_20261012_wrapper_scenario.json --out-root build/fsp_extensions_20261012_wrapper_01 --date 20261012 --timeout 600 --enable-hooks
```

Both exit 0. Issued immutable fixture forecast: `build/fsp_extensions_20261012_wrapper_01/forecast_20261012_01`, three instances, one member/one committed interval. Manifest confirms native_advance_count=1 and H3 activation. H1 remains contract-unmet because the wrapper registry lacks exact per-count mapping; H2 remains unavailable. Neither is silently enabled from PARAMS membership. Axis forwarding/evaluation and new optical/schedule options are not claimed to exist in that wrapper; P3 side-shoot work belongs to its separately assigned owner.

## Tests, commands and remaining work

Combined focused regression: **192 passed**, zero failures/errors; additional producer-column alias test: **1 passed**. JUnit files `build/fsp_extensions_axes_20261012_regression.xml` and `build/fsp_axes_20261012_producer_columns.xml`. This includes existing V3/integration/bridge (102), forecast consumers (43), and new axis/extension cases (47), plus the additional alias case. Earlier subset and historical full-suite counts overlap and are not summed.

Native acceptance CLI modes: `tools.fsp_extensions_acceptance optics|schedule|hooks|intake|planes --out <fresh build path> --rays 4800000`. Alternate-seed optics used `execute_optics(..., names=('black','black_floor','reflector_floor','mixed_leaf'), seed=5100)`. All successful commands exit 0. Exact failures, actual command lines, output hashes and inspected source versions remain in their fresh run directories; later source changes never relabel old Model.rgg snapshots as current.

Remaining science/input decisions: real metric geometry and hidden physiology; measured lamps/materials and spectrum; fixed NRH light basis under nonblack optics; developmental deformation with supported anchors and mass/area law; nutrient uptake/exchange/demand/allocation and native causal handshake; substem development/dominance/truss applicability. No biology was fitted, and no protected docs/config/records/original VTC were edited.

Verified flow rows are supplied in `FSP_EXTENSION_SIDESHOOT_FLOW_ROWS_2026-10-12.csv`, with a LOG request to the active P1 flow-map owner to merge them. This avoids simultaneous rewriting of the shared OneDrive file. Pending decisions are separately appended in `VTC_V3_PENDING_DECISIONS_2026-10-11.md`; successful interface fixtures do not close E2/E6/E7 science/backend gaps.

Final audit supplement: `build/fsp_extensions_axes_20261012_delivery_01/delivery_addendum.json` binds the timezone-corrected real audit, failure gates, tests and initial delivery documents. Later A4 adapter evidence is an additive snapshot; the original 30-run source snapshot and acceptance are not overwritten.

A4 completion addendum: parent-node mapping was reconciled after Amendment A4 arrived. One added native A4-format fixture (two intervals, 4.8M rays) and 23 rerun axis cases passed, including two new attachment/failure cases. Final unique focused tests: **195**; accumulated native evidence: **31 runs / 152 intervals** (side-axis subset 10 / 31). Earlier 30-run acceptance/source snapshots are preserved; see `build/fsp_extensions_axes_20261012_delivery_01/a4_delivery_addendum.json` and the side-shoot execution report. This does not change E2/E6/E7 limitations or claim actual producer side-export completion.
