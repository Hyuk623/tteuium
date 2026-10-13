# P2 actual light-direction delivery

Date: 2026-10-04, Asia/Seoul. Objective: `CODEX_P2_LIGHT_CHAT_PROMPT_2026-10-04.md`.

## Outcome and scope

The authorized P2 software scope is implemented and verified: existing direct transport -> actual per-emitter callback -> bounded collector -> spatial/fixture/time/hierarchy/frame moments -> serialized package -> independent consumer -> canopy-preserving instance splits. No second tracer or lamp-center approximation was added. The prior protected-core ownership blocker was revoked by the user. The immediately preceding turn only reconfirmed lamp operating metadata; this continuation made implementation/verification progress, not a dependency wait.

Physical lamp/plant accuracy remains unverified. P3/P4 integration, growth geometry/prediction, physiology, native execution, inference/training and uploads were not performed. The three real REF-30-40 lamps are kept in a separate intentionally incomplete draft; their latest confirmed operation is 16 h/day at 100%, superseding older unconfirmed-duration/fraction wording.

## Changed implementation and contract

| File / function | Result |
|---|---|
| `tomato3d/light/raytrace.py::direct_light`, `_emit_direction_chunks` | Optional synchronous actual contribution callback; original scalar/side transport and positional interface retained |
| `tools/light_direction_diagnostics.py::DirectionCollector` | Adopted `direct-angular-1`, complete bounded inventories, same-call scalar/normal parity and serializable summary |
| `tools/light_growth_bridge.py::export_spatial_light`, `integrate_light_schedule`, `export_compound_light_features`, `_regions`, `build_package` | Real stream connection, grow sample moments, schedule scaling, aggregate/frame/region moments and honest direct/native capabilities |
| `tools/light_growth_consumer.py` | Independent serialized moment/inventory/scaling/frame/region checks; no exporter arithmetic imported |
| `tools/light_growth_schema.json` | Additive raw sample moments/global receiver/count columns and required angular diagnostics JSON; existing meanings unchanged |
| `tools/light_growth_demo.py` | Explicit synthetic extended emitters, independent fixture schedules and source-copy canopy demonstration |
| `tests/test_light_angular_transport.py` | Actual core transport/occlusion/off-on/rotation/lifetime/budget tests |
| `tools/tests/test_light_angular_exports.py` | Actual producer through independent export consumer, invalid output/chunk rejection, unknowns, background, reused callback buffers and opposing sources |
| `tools/tests/test_light_direction_diagnostics.py` | Description updated to distinguish adopted protocol unit tests from actual producer evidence |
| `tools/LIGHT_GROWTH_BRIDGE.md`, `tools/DIRECT_ANGULAR_CONTRACT.md` | Current IO, capabilities, exact callback contract, memory/lifetime and missingness documentation |

```python
direct_light(receivers, fixtures, occluders, leaf_transmittance, settings, *,
    diagnostic_callback: Callable[[Mapping[str, Any]], None] | None = None,
    diagnostic_max_paths_per_chunk: int | None = None) -> DirectLight
```

Exact event fields and reasons are in `tools/DIRECT_ANGULAR_CONTRACT.md`. Known fixture events include global receiver and stable emitter indices, S/E/S*E inventory and ordered half-open chunk ranges, actual attenuated receiver-cosine PPFD in umol/m2/s before area or absorptance, and receiver-to-emitter grow-frame unit vectors (opposite photon travel). Zeros and unknown paths are included. Unknown fixtures produce one explicit unavailable event, not an empty/zero inventory. Arrays/mappings are synchronous borrowed read-only values; retain by copying. Callback exceptions abort; missing/duplicate paths fail closed. Default calls allocate no diagnostic arrays.

For one-sided metric area w, F=sum(w*p), M=sum(w*p*u), B=sum(w*p*u*u.T), all in umol/s. Sample columns store F, M x/y/z, B xx/xy/xz/yy/yz/zz in grow frame plus global receiver index and unknown-path count. Features sum raw moments before normalization and rotate M/B into board or reviewed full-axis/transverse compound frames. Unknown paths/schedules invalidate complete moments. F=0 leaves raw zero with unavailable normalized fields. Opposing directions retain B/F and zero mean/concentration; dominant direction is unavailable. Observed rachis directions are separate from light directions.

No extra environment variables were introduced. Existing scene/prepared-result/request loaders and explicit limits remain authoritative. `max_receiver_emitter_pairs` bounds known paths and accumulator pairs; the diagnostic chunk cap is the minimum of this limit and existing `max_ray_triangle_pairs_per_chunk`. This bounds diagnostic additions, not the original core S*E arrays. Source fixtures and `all` are never added twice. Incident/absorbed quantities, supported area and time-dependent flux integration retain their original semantics.

## Verification

**240 distinct tests passed:** 83 core light tests, 154 adapter/hierarchy/light regression tests, 2 final focused background/lifetime integration checks and 1 explicit actual beam-exclusion path check. All suites have zero failures/errors. Results are in `build/p2_angular_20261004_01/{core_final,tools_final,background_lifetime,beam_exclusion}.junit.xml`. Core and tools suites are separate commands because the existing two test trees both import their own top-level `conftest`; combined collection conflicts. Earlier failed collection XML and the initial scalar-region fixture failure are preserved; the latter was corrected by permitting scalar-only helpers without inventing an angular frame.

Numerical comparison policy: absolute 1e-10, relative 1e-9; cancellation criterion |M| <= 1e-12*F. Lamp layout/orientation arithmetic uses absolute 1e-9, relative 0. These are software tolerances, not physical PPFD acceptance thresholds. Existing unrelated analytic approximations retain their own declared test tolerances.

Actual core tests cover single and extended emitters, asymmetric/equal opposing fixtures, zero emission, unknown PPF and transmittance, opaque background, physical leaf crossings counted once, own-triangle exclusion, coincident emitter/receiver, disabled callback allocation path, invalid budgets and propagated callback errors. Same-call sums reproduce received and positive-normal PPFD with matching NaN masks. Rotation/inverse/translation tests move actual emitters, receivers and occluders together.

Actual adapter tests cover unknown/zero/known results, independent fixture schedules, reviewed local frames, complete blacking by preserved background, callback-buffer reuse, lost first/last chunks and duplicated chunks. After updating only artifact hashes in deliberately corrupted test packages, the independent consumer rejects wrong sample F/M/B, time M, board M, local B, regional M, path counts, missing fixture inventory, receiver indices and unknown counts. Production hashes are never bypassed or rewritten to make stale results acceptable.

### Measured overhead and parity

`build/p2_angular_20261004_01/diagnostic_overhead.json` records actual calls on the fresh synthetic canopy. Two fixtures have 4 emitters each; 14 occluder triangles are preserved. Diagnostic and ray-triangle chunk caps are 127. Five timing repetitions per setting; separate tracemalloc runs measure traced allocations, not whole-process RSS or every native allocation.

| Receivers / paths | Disabled median | Enabled median | Traced peak off / on | Max callback ndarray bytes |
|---|---:|---:|---:|---:|
| 56 / 448 | 2.678 ms | 3.172 ms (1.18x) | 110370 / 125568 | 6350 |
| 896 / 7168 | 30.791 ms | 38.889 ms (1.26x) | 1618168 / 1834733 | 6350 |

In both measurements, maximum absolute differences were **0.0** for all three off/on DirectLight arrays and for collected received/normal-side path sums. Accumulator array storage was 10752 and 172032 bytes; largest callback chunk stayed 127 paths. The larger case repeats receivers strictly to measure workload, not to represent additional plant area. These local measurements are not a throughput guarantee.

## Fresh artifacts and hashes

Numerical demo: `build/light_growth_directional_20261004_01/`.

- Fresh `inputs/`, `prepared/`, `hierarchy_results/`, `request.json`; no historical input hashes were patched.
- `package/`: independent consumer passes 1344 sample rows, 1080 feature rows, 14 intervals and 48 dose rows; 56 original receivers and 448 actual full-output paths across two extended fixtures.
- `P1_in_canopy/`, `P1_COPY_in_canopy/`: both independently pass. Every split table equals the corresponding parent selection exactly; global receiver IDs and full shared canopy inventory/hashes remain unchanged. No isolated-plant retracing occurs.
- `consumer_checks.json`, `copy_roundtrip.json`; final current-state revalidation in `build/p2_angular_20261004_01/delivery_verification.json`.

All source/code/artifact hashes are in each `package.json`; final package-manifest SHA256 values are in `delivery_verification.json`. The old `build/light_growth_readiness_20261003_05/package` artifact hashes still verify unchanged; its older code freshness is intentionally superseded. `core_audit.json` records adopted signature and SHA256; its signature-only execution flags remain false by design, so use actual tests and package validation as execution evidence.

Real lamp draft: `build/lighting_REF_30_40_three_20261004_03/`, generated after implementation. It contains scene draft, separate reference/provenance metadata, readiness/layout reports, protected-input/artifact hashes and a header-only PPFD template. Center coordinates [300,326.5,400], [300,229.5,400], [300,132.5,400] mm, 50 mm rear/inter-lamp gaps, 109 mm front clearance and 41.5 mm lateral clearances are verified against the reported envelope. Core axes confirm downward aim and X long axis. The draft has the expected 16 missing required fields and is explicitly not runnable. Earlier drafts remain preserved.

## Requirement-by-requirement completion audit

| Prompt requirement | Current evidence and verdict |
|---|---|
| §1 rules/brief/authorized ownership and restrictions | Current rules and implementation brief inspected before edits; only authorized light/tools/tests/handoff/build files changed; satisfied |
| §2 reuse current code and preserve history | Actual existing transport/collector/bridge inspected; historical artifact hashes verified; satisfied |
| §3.1 compatible optional callback | Implemented signature, default calls and 83 core regression tests; satisfied |
| §3.2 actual per-emitter contributions | Core uses existing shaded_per_emitter/direction; extended-emitter B differs from center approximation; satisfied |
| §3.3 inventory/zeros/unknowns/lifetime/errors | Explicit protocol plus actual chunk-loss/duplication/reuse, unknown-fixture and core error tests; satisfied |
| §3.4 disabled allocations/budgets/overhead | Disabled helper-not-called test, mandatory limits, budget regressions and measured overhead report; satisfied |
| §3.5 adopted producer/collector | direct-angular-1 at both ends; fresh diagnostic inventory and same-call parity; satisfied |
| §3.6 fixture/organ/plant/canopy/time/frame/native capabilities | Fresh non-null angular rows across leaflet/compound/plant/canopy and grow/board/compound_local; separate native-unavailable tests; satisfied |
| §3.7 raw F/M/B, cancellation and transforms | Actual extended/opposed transport, schedule/frame consumer recomputation, moved-geometry rotation/inverse/translation; satisfied |
| §3.8 shared canopy and instance identity | Exact split row equality, parent/context hashes and source-copy coordinates; satisfied |
| §4 quantities/area/absorption/time/DLI/D9 | Existing scalar and time tests, full-day/dimming/unknown/DST/area-change regressions and 48 validated dose rows; D9 basis remains explicit, no representative day or growth response selected; satisfied |
| §5 lamp draft/provenance/unknowns | Fresh _03 verification, 16 h and 100% confirmed, no lumens-to-PPF conversion, no invented clock/beam/aperture; draft preparation satisfied; physical inputs deliberately incomplete |
| §6 listed acceptance cases | Actual core + end-to-end negative/positive tests, independent current package validation and benchmark; satisfied |
| §7.1–2 changed files, contract, IO | This report, DIRECT_ANGULAR_CONTRACT.md, LIGHT_GROWTH_BRIDGE.md and updated IO summary; satisfied |
| §7.3–4 test/overhead/fresh package/splits/hashes | 240 tests plus three valid packages and audit JSONs; satisfied |
| §7.5–6 real draft and limitations | Separate _03 draft and limits below; satisfied |
| LOG/TODO and Korean result | Completion record appended and current P2 queue item closed; Korean user report accompanies delivery |

No required P2 software implementation remains open. Physical validation requires actual emitting aperture/center/height, PPF, supported beam parameters and optical boundary assumptions, reviewed metric surfaces and leaf optics, real clock windows and independent quantum-sensor measurements with a calibration/held-out split and predefined acceptance criteria. 30 W/4000 K/3300 lm/110 lm/W do not supply these optical measurements. Growth/physiological validity is outside this objective.

## Commands executed

```powershell
python -X utf8 -m pytest tests/test_light_inputs.py tests/test_light_raytrace.py tests/test_light_pipeline.py tests/test_light_angular_transport.py -q --basetemp=build/p2_angular_20261004_01/core_final_tmp --junitxml=build/p2_angular_20261004_01/core_final.junit.xml
python -X utf8 -m pytest tools/tests/test_light_direction_diagnostics.py tools/tests/test_light_growth_bridge.py tools/tests/test_light_angular_exports.py tools/tests/test_hierarchical_light.py tools/tests/test_leaf_light_study.py tools/tests/test_leaf_light_phone.py -q --basetemp=build/p2_angular_20261004_01/tools_final_tmp --junitxml=build/p2_angular_20261004_01/tools_final.junit.xml
python -X utf8 -m pytest tools/tests/test_light_angular_exports.py -q -k 'background or reused' --junitxml=build/p2_angular_20261004_01/background_lifetime.junit.xml
python -X utf8 -m pytest tests/test_light_angular_transport.py -q -k beam_exclusion --junitxml=build/p2_angular_20261004_01/beam_exclusion.junit.xml
python -X utf8 -m tools.light_growth_demo --out build/light_growth_directional_20261004_01
python -X utf8 -c "import runpy; runpy.run_path('build/lighting_REF_30_40_three_20261004_03/prepare_draft.py', run_name='__main__')"
python -X utf8 -c "import runpy; runpy.run_path('build/p2_angular_20261004_01/verify_delivery.py', run_name='__main__')"
```

Use new output directories for future preparation/export. Final audit was refreshed after the last three added tests without rerunning the unchanged benchmark. No Git metadata exists in this checkout, so file/hash/test evidence is the delivery record; no commit or PR was created.
