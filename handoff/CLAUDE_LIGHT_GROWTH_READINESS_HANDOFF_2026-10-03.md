# Claude handoff: light simulator and missing angular diagnostics

Date: 2026-10-03 (Asia/Seoul). Project: `Tomato 3D phenotyping analysis`.

## Immediate next action

**Claude/core owner: add a backward-compatible optional angular diagnostic interface to `tomato3d/light/raytrace.py::direct_light`, document its exact contract, and verify parity with the existing scalar/side arrays.** Then return the interface and test evidence to Codex for the owned export integration.

The light-growth readiness goal is **blocked, not complete**. Independent owned work is delivered. The remaining obstacle is an actual missing core interface, not a failed installation or running background job. Do not replace it with lamp-center directions or another ray tracer.

This handoff was prepared at the user's request. Preparing it did not execute core changes, send another chat a message, or resume the blocked implementation goal.

## Working boundaries and reading order

Read parent `공통규약.md`, project `AGENTS.md` / `CONVENTIONS.md`, latest `handoff/LOG.md` and relevant `handoff/TODO.md`. Codex owns `tools/` and `tools/tests/`; the core owner handles `tomato3d/` and root `tests/`. Preserve human configuration/observations and avoid simultaneous edits in OneDrive.

Primary references:

1. `handoff/CODEX_LIGHT_GROWTH_READINESS_PROMPT_2026-10-03.md` — full objective and completion gates; section 2 requires the core-owner hook.
2. `tools/LIGHT_GROWTH_BRIDGE.md` — current request, numerical and export contracts.
3. `tools/light_growth_schema.json` — authoritative CSV fields, types, units, keys and missingness.
4. `handoff/CODEX_LIGHT_GROWTH_READINESS_EXECUTION_2026-10-03.md` — implementation, corrections and blocker history.
5. `build/light_growth_readiness_20261003_04/requirement_audit.json` and `blocker_audit_3.json` — requirement evidence and unresolved scope.

Coordination decisions remain separate: P3 owns realized direction/size increments; P4 is diagnostic only. Cross-project linking is deferred. See `handoff/CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md`. The core diagnostic change must not add growth feedback, physiology or P3/P4 integration.

## Implemented and available

| File | Responsibility |
|---|---|
| `tools/hierarchical_light.py` and `hierarchical_light_native.py` | Existing eight-subset retained-target shading, signed Shapley/source-removal accounting, native preparation/collection. Unchanged by this extension. |
| `tools/light_growth_bridge.py` | Full-scene direct samples and sides; weighted area/flux/quantiles; reviewed compound joins; supported local regions; schedules/dose/DLI; reversible transforms; native scalar import; reporting-only instance splits. |
| `tools/light_growth_consumer.py` | Independent serialized schema, freshness, identity, frame, schedule, quadrature, dose, region and capability checks. Does not import exporter arithmetic. |
| `tools/light_growth_schema.json` | Schema `light-growth-1`: five CSV tables and explicit scalar components. |
| `tools/light_growth_demo.py` | Artificial canopy, observed-state associations and same-source copies. No native execution. |
| `tools/tests/test_light_growth_bridge.py` | Current 32 focused software checks. |

Public bridge functions: `audit_growth_light_inputs`, `export_spatial_light`, `compute_directional_features`, `integrate_light_schedule`, `export_compound_light_features`, `split_canopy_results`, `validate_growth_light_package`; `build_package` orchestrates exports. Spatial export additionally requires explicit `snapshot`, `run_id` and `max_receiver_emitter_pairs` keyword arguments.

`compute_directional_features` already checks complete path inventories and computes F/M/B from supplied contributions. It is algebra only. Production feature export currently rejects supplied directional records with `production_directional_hook_pending_use_algebra_API_only`; no live angular transport or time/frame directional adapter is connected. Its existence does not mean the blocked feature is implemented.

## Current core gap and required semantics

Current inspected signature:

```python
direct_light(receivers, fixtures, occluders, leaf_transmittance, settings) -> DirectLight
```

`DirectLight` exposes `fixture_ids`, `ppfd_umol_m2_s`, `unoccluded_ppfd_umol_m2_s`, and `upper_side_ppfd_umol_m2_s`. Each numerical array is `(F, S)`: fixtures by receivers. Per-emitter `direction` and `shaded_per_emitter` exist internally but are not returned.

Core source SHA256 at handoff: `6936a154b67a0cd796f36c8e75760eea61588da9971c7349a29584f1f13747d8`. Recheck the current file before editing; this hash is a snapshot, not a requirement to revert later work.

Required diagnostic semantics (the core owner should finalize exact API spelling and layout):

- An optional keyword-only callback or optional diagnostic return; the default call and `DirectLight` behavior remain compatible.
- Each contribution identifies fixture, global receiver index and stable emitter/path index. Include an expected inventory/count and chunk coverage sufficient to detect duplicate or omitted paths.
- `incident_ppfd_umol_m2_s`: contribution after existing attenuation and receiver cosine, before receiver area weighting. Preserve actual zero contributions and unknown contributions separately; do not discard NaNs/missing paths.
- `arrival_unit_grow_xyz`: unit vector pointing **receiver toward the arriving-light origin**, opposite photon travel. Use the actual emitter direction for direct transport. Reflected transport would require the final path segment, not the original lamp center; native angular channels remain outside this direct-hook change.
- State validity/completeness explicitly. A zero-length direction on a zero-flux path must not become a meaningful light direction. Define callback array lifetime/ownership and chunk ordering so a consumer can retain or stream data safely.
- Preserve existing physical-surface crossing counts, own-triangle exclusion, fixed occluders, unknown transmittance behavior and resource controls. Do not introduce a second optical calculation with different semantics.

For supported one-sided sample area `w_i` [m2], positive received contribution `p_ij` [umol/m2/s], and arrival unit vector `u_ij`:

```text
W_ij = w_i * p_ij
F = sum(W_ij)                   [umol/s]
M = sum(W_ij * u_ij)            [umol/s, xyz]
B = sum(W_ij * u_ij u_ij.T)     [umol/s, xx xy xz yy yz zz]
mean_arrival = M/F
directionality = norm(M)/F
dominant_arrival = M/norm(M)
angular_second = B/F
```

Sum unnormalized moments before normalization. At F=0 retain zero unnormalized moments and unavailable normalized values. At cancellation retain B but mark dominant direction unavailable. Current numerical policy: absolute `1e-10`, relative `1e-9`, directional degeneracy ratio `1e-12`; these are numerical tolerances, not biological thresholds.

## Core acceptance checks and return to Codex

1. Callback disabled preserves existing results; callback enabled produces the same scalar and normal-side arrays at declared tolerances.
2. Per-receiver contribution sums reproduce `ppfd_umol_m2_s`; contributions on the existing normal-side convention reproduce `upper_side_ppfd_umol_m2_s`. Fixture totals and unknown values remain consistent.
3. Test one known direction, asymmetric emitters, equal opposing emitters (M cancels, B remains), darkness, unknown optics, duplicated/omitted chunk detection and receiver index mapping.
4. Retain own-leaf folds and fixed background; preserve existing core raytrace and hierarchy regression behavior. Show resource use and optional diagnostic overhead.
5. Return exact callable signature, payload field names/shapes/units, validity rules, chunk/inventory semantics, changed core files/hashes and executed test evidence in an English handoff.

After that delivery, Codex must implement the **remaining owned work**: callback adapter, spatial/time/per-fixture F/M/B export, grow/board/measured-compound-local transforms, consumer capability/validation updates, and actual transport scalar/side/angular parity. The pure-helper tests alone cannot close these items. Only after the original light prerequisite passes should the separate growth-direction implementation prompt be prepared.

## Inputs, outputs and downstream joins

Shared key: `(run_id, scenario_id, geometry_snapshot_id, plant_instance_id, session_id, compound_id, time_step_id, backend, replicate)`, refined by fixture/entity/region/frame or triangle/sample.

`compound_id -> compound_leaf_id` requires an explicit reviewed association with source geometry/evidence hashes. Keep source plant distinct from canopy instance, capture date distinct from an aware observation timestamp, and copied plants explicitly hypothetical/synthetic. Source-board **observed rachis** fields map to growth `direction_unit_xyz`; light arrival is a separate covariate.

Units: mm geometry; m2 supported one-sided area; `cm2 = m2 * 10000`; umol/s flux; umol/m2/s PPFD; seconds; mol/m2 interval dose. Never convert first-leaf=1 image ratios to metric tissue. Missing CSV numerics are `unavailable`, JSON values null with reasons in `availability.json`.

Package files: `package.json`, `schema.json`, `instance_map.csv`, `transforms.json`, `light_samples.csv`, `compound_light_features.csv`, `light_intervals.csv`, `light_dose.csv`, `consumer_mapping.json`, `capabilities.json`, `availability.json`, `audit.json`.

Important invariants: sum flux before dividing by area; never sum actual fixtures plus `all`; do not double-apply absorptance; integrate changing area through time-indexed flux; only complete declared local days are DLI. Schedule absence is not blackout. Native combined-fixture responses cannot support unequal fixture schedules by guessed decomposition. Native spatial/side/angular channels remain unavailable. Instance splits retain full-canopy shading and context, not isolated optical results. Future CompoundLeaf envelopes are not optical tissue.

## Delivery and verification evidence

Current export: **`build/light_growth_readiness_20261003_04/`**. Main `package/`, `P1_in_canopy/` and `P1_COPY_in_canopy/` pass the strengthened independent reader. `_03` remains the immutable source request/prepared/legacy-results bundle used by `_04`; do not delete it. Earlier final-export labels in append-only history are superseded.

- Recorded related regression run: **266 passed**. This predates the final consumer strengthening.
- Final focused bridge/consumer run: **32 passed** in `build/light_growth_readiness_verification_20261003_01/consumer_strengthening.junit.xml`.
- The earlier reader accepted incorrect board area/flux and invented direction; those failures were reproduced and fixed. Final checks include frame invariance, signed observed rotations, local-region accounting/contrasts and unsupported channels.
- See `_04/consumer_checks.json`, `copy_roundtrip.json`, `requirement_audit.json`, `blocker_audit_3.json` and `REPRODUCTION.md`. Synthetic tests prove software behavior only. Counts and historical checks are not new execution or physical-validation claims.

Useful commands from the project root (new outputs must be fresh):

```powershell
python -X utf8 -m tools.light_growth_bridge --help
python -X utf8 -m tools.light_growth_bridge validate --input build/light_growth_readiness_20261003_04/package
python -X utf8 -m pytest tools/tests/test_light_growth_bridge.py -q
python -X utf8 -m tools.light_growth_demo --out build/light_growth_example_new
```

A core change intentionally makes prior code-hashed prepared/output packages stale. Preserve the old evidence; generate fresh hierarchy preparations and bridge outputs after integration instead of disabling freshness checks or rewriting old hashes to appear current.

Real-input audit: `build/light_growth_readiness_20261003_01/real_audit/real_readiness.json`. Supplied dwt_01/T1/T2/T3 snapshots lack required scene, accepted leaf surfaces and selected plant case; T3 additionally lacks registered geometry provenance. Original hashes were unchanged. No broader search, fabricated observations or native run is needed to implement this core interface. Physical/biological accuracy remains unvalidated, and no growth direction, new area or physiology has been predicted.
