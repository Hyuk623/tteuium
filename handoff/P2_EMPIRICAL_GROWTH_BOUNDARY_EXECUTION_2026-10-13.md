# Empirical light to native growth boundary

Request: continue PROMPT_CODEX_EMPIRICAL_GROWTH_BOUNDARY_2026-10-13.md. Scope is a versioned per-interval/per-surface light adapter and native hook/instrumentation handoff. Preserve flow, human records, forecast files and the native owner's controller/template.

Inspection: empirical_canopy provides derived incident interception by receiver/leaf and explicit direction scenarios. Native simulate() currently reads lm.getAbsorbedPower into Organ.photons and applies NRH at absorbed flux / one-sided area. There is no empirical input branch. Native received power is explicitly first-hit, while escape/cutoff remain unavailable. Existing per-position reference DLI is not tissue illumination.

Plan: consume explicitly registered physical triangle snapshots; hash namespace/geometry/registration/interval/configuration; sample true triangle areas, reuse existing empirical canopy shading exactly once; integrate explicit constant-output segments, preserving each scenario and incident/absorbed basis. Unknown absorption blocks absorbed/P4 use. Reject missing support, transforms, tissue coverage and already-shaded field claims. Export is not native integration; native owner must implement and jointly test the exact hook in a fresh run.

Validation: independent area/flux/dose consumer; schedule coverage, geometry and identity mismatch, absorptance/no-double-application, no-extrapolation after growth and source compatibility; labelled metric triangle fixtures plus a separate real-input readiness report. Inspect local GroIMP sources/APIs read-only and specify repeated-hit and terminal event accounting without inventing escape residuals.

## Delivered implementation and tests

Added tools/empirical_growth_boundary.py, tools/empirical_growth_consumer.py, tools/empirical_native_response.py, tools/tests/test_empirical_growth_boundary.py and tools/EMPIRICAL_GROWTH_BOUNDARY.md. Existing empirical producers, original 46-point records and earlier output packages were reused unchanged. No flow, forecast, native-owner source or human record edits.

Request/export/consumer schemas: empirical-growth-request-1, empirical-growth-boundary-1, empirical-native-context-1. The exporter publishes segment and interval CSVs, receiver evidence and a manifest with source/configuration/code/geometry/namespace/registration hashes. All vertices and samples must lie in measured support. Incident and absorbed fields remain separate; explicit per-face absorptance is required for absorbed-basis use. Local field interpretation and omitted canopy scattering are explicit sourced contract fields, not defaults. Frozen geometry and area are integrated separately for every interval.

Native API was added concurrently by its owner, and coordinated through LOG/NATIVE_BOUNDARY_CONTRACT_2026-10-13.md. Our adapter reuses verify_prepared/read_request/submit_light without editing the controller. It verifies actual consumed triangle coordinates/leaf IDs/area and matching on-hours, selects one direction scenario and submits already-absorbed flux once. Nonfixture growth remains gated; black-equivalence growth fixtures require alpha=1/tau=0. Nonblack diagnostic use must disable NRH. Protocol tests include idempotent retry and conflicting retry rejection; these alone are not native integration.

Focused regression: **86 passed in 58.86 s**. Command: `python -m pytest tools/tests/test_empirical_growth_boundary.py tools/tests/test_empirical_light_field.py tools/tests/test_reference_dli_consumer.py tools/tests/test_reference_dli_frozen.py -q --tb=short`. New boundary module has 32 cases; prior empirical field has 29. Coverage includes area-first flux, changing interval area, side convention under a proper 180-degree rotation, complete schedule coverage, unsupported dimming, all-vertex extrapolation, duplicate/cross-plant IDs, stale geometry/configuration/registration, missing absorption, no second shading/absorption and independent dose arithmetic tamper refusal. Export consumer atol=rtol=1e-10; native triangle coordinates are compared exactly, live area atol=1e-12/rtol=1e-10, native flux matching atol=rtol=1e-12.

Fresh export package: build/p2_empirical_growth_boundary_20261013_01/export. Two explicit metric triangle leaves, two intervals with doubled area at the second boundary, three separate diffuse scenarios and 14 h/day full output generate 36 segment rows and 12 interval totals. All 46 measured field samples remain source-bound. Independent consumer and CLI both passed. The selected lamp pose/grid and all leaf geometry remain fixture/conditional assumptions, not actual crop reconstruction. `real_readiness.json` separately reports unavailable real geometry/pose/registration/NRH basis/calibration. `api_coverage.json` verifies all three frozen 2_2_1 source hashes.

Commands: `python build/p2_empirical_growth_boundary_20261013_01/reproduce.py --out build/NEW`, then `python -m tools.empirical_growth_consumer build/NEW/export/boundary.json --configuration build/p2_empirical_light_field_20261013_01/synthetic_direction_configuration.json --context build/NEW/expected_context.json --required-basis absorbed`.

## Native and instrumentation coordination

Exact owner handoff is P2_EMPIRICAL_NATIVE_HOOK_2026-10-13.md. Current source/API exposes first-hit-per-volume received power, not complete repeated incidence. Terminal escape/sky/depth/min-power paths are not tallied by the published getters. No diagnostic escape remainder is fabricated. A versioned weighted-event/chunk instrumentation contract and controls are provided; no installed JAR or shadow tracer was changed.

Native owner supplied fresh constant-PPFD handshake evidence and authorized this P2 adapter to prepare a new light-only run in LOG. The original 13,062-triangle native fixture needs at least 682 million naive ray-triangle pairs even at four directions, exceeding the existing 500M safety cap. Instead of bypassing that cap or claiming a coarse original leaf is real, the joint runner uses a NEW, explicitly replaced engineering geometry: 45 one-triangle leaves on a metric grid, including tilted surfaces, with topology/unused hidden-state copied from the owner's labelled fixture. It is not the original P1 geometry. Actual native consumed vertices are re-read before empirical export, then a grow-frame translation of +110 mm Z is applied with provenance. NRH/growth is disabled. Old fixture inputs and outputs are untouched.

Joint driver: `python build/p2_empirical_growth_boundary_20261013_01/run_native_joint.py --out build/NEW_NATIVE_JOINT`. Three separate diffuse scenarios are planned. The first driver attempt stopped before native preparation due to a string/Path argument error; it is preserved in native_joint_01/FAILED.json, corrected and restarted in a fresh directory. Actual native success/limits will be recorded in the final addendum; export success is not used as a substitute.

## Final native evidence, 2026-10-13

The earlier no-hook/no-native-evidence statements above describe inspection and intermediate work. The owner subsequently supplied the hook. Actual empirical consumption is now verified for **three fresh native light-only runs, three intervals, 135 leaf-interval comparisons**, using 45 explicitly replaced engineering triangles per run. No native/controller source was edited by this task. This verifies the light interface, not growth or real plant geometry.

| Assumed diffuse fraction | Fresh run below build/p2_empirical_growth_boundary_20261013_01 | Total absorbed flux (umol/s) | Maximum native versus supplied leaf flux error (umol/s) | Native elapsed (s) |
|---|---|---:|---:|---:|
| 0.5 | native_joint_04/diffuse_50 | 0.3705594027149651 | 0 | 23.436 |
| 0.6 | native_joint_03/diffuse_60 | 0.38580846167063393 | 0 | 106.912 |
| 0.7 | native_joint_04/diffuse_70 | 0.4010575206263027 | 0 | 17.258 |

Every native results/manifest.json reports verified_native_light_only; boundary_audit.csv records external_once transport. Native gross carbon is zero and mass/thermal age/area remain unchanged. Actual consumed mesh vertices were used to construct the empirical snapshot, with exact coordinate comparison before submission. The independent consumer accepted 90 segment rows per scenario. These are synthetic geometry/assumed direction scenarios with measured scalar field support, not measured directional data or PPFD accuracy validation. Black absorptance=1 and transmittance=0 are fixture inputs, not measured leaf properties.

`delivery_verification.json` independently rechecks source/code hashes, all published native artifact hashes, exactly 45 unique leaf flux rows per run, external_once audit and zero carbon. `finalize_delivery.py` completed successfully. The export manifests deliberately retain unverified_hook_required as their original export-stage status; subsequent native evidence is separate and hash-bound, not retroactively inserted into old exports. `regression_results.json` records the 86-test completion; the full repository suite was not rerun.

Executed commands:

```text
python build/p2_empirical_growth_boundary_20261013_01/run_native_joint.py --out build/p2_empirical_growth_boundary_20261013_01/native_joint_03 --fractions 0.6 --timeout-s 900 --startup-timeout-s 840
python build/p2_empirical_growth_boundary_20261013_01/run_native_joint.py --out build/p2_empirical_growth_boundary_20261013_01/native_joint_04 --fractions 0.5 0.7 --timeout-s 900 --startup-timeout-s 840
python build/p2_empirical_growth_boundary_20261013_01/finalize_delivery.py
```

Failure history is retained. native_joint_02 reached the GroIMP base CLI but produced no boundary request before the outer 360 s timeout; no empirical response was submitted. Its FAILED.json points to the original execution/log evidence. A fresh retry allowed 900 s startup/execution and passed without a native source change. The precise earlier timeout cause is unresolved. The successful 60% log includes nonfatal CLI window NullPointerException messages before READY; completion, audit, published hashes and flux validation subsequently passed. No failed run has been relabelled successful.

### Remaining conditions

- Real application still needs reviewed optical leaf meshes, observed lamp/grid pose and canopy registration, sensor calibration and a scientifically accepted local-field/absorptance contract. No plants above 150 mm at acquisition does not cover later tissue outside support.
- Growth-mode NRH basis, actual growth advance and repeated changing native geometries were not validated by these light-only runs. The adapter's nonfixture growth gate remains closed; fixture protocol/rejection tests do not replace biological review.
- The original 13,062-triangle fixture exceeds the present naive transport cap at the minimum direction count; it was not run or silently decimated. More complex geometry needs an independently reviewed acceleration/resource route, not a higher hidden limit.
- Repeated native incidence and terminal escape/cutoff accounting remain unavailable. Their exact source/API map and bounded instrumentation contract are delivered, but published aggregate getters cannot implement them. This limitation does not invalidate the independently verified empirical input path.
- No flow, human records, forecasts, old empirical outputs, installed GroIMP JARs or native-owner code were modified.
