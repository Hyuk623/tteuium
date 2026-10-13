# P2 light simulator implementation prompt

Date: 2026-10-04, Asia/Seoul.
Target chat: 광시뮬레이터.
Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.

Continue the existing P2 implementation and complete actual light-direction output. The user has revoked the rule reserving the light calculation core for Claude Code. Codex may now implement the producer, connect the existing collector and exports, and validate the complete P2 path directly.

## 1 Authoritative instructions and scope

Read the parent `공통규약.md`, project `AGENTS.md`, `CONVENTIONS.md`, the last five LOG lines and current TODO entries.

Read these handoffs:
- [Ownership override](CODEX_LIGHT_CORE_RULE_UPDATE_2026-10-04.md).
- [Current P2 continuation report](CODEX_P2_LIGHT_CONTINUATION_2026-10-03.md).
- [Actual-path diagnostic contract](CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md).
- [Passive collector execution record](CODEX_ANGULAR_CALLBACK_EXECUTION_2026-10-03.md).
- [Integration decisions D1-D10](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md).

The ownership override supersedes older instructions requiring Codex to wait for a Claude core-owner delivery. The diagnostic contract still supplies the required physical semantics and validation; its old owner restriction no longer applies. The former blocked status records an earlier dependency, not a reason to keep waiting.

Allowed scope: `tomato3d/light/`, relevant light tests under `tests/`, existing `tools/` adapters and their `tools/tests/`, English handoffs and fresh generated `build/` artifacts. Preserve human `config/`, `docs/`, observations and unrelated implementation. Inspect current work before editing to avoid simultaneous OneDrive writes.

Create an English implementation brief first, then proceed without asking again for light-core ownership permission. Do not send messages to other chats or create a second tracer.

## 2 Inspect and reuse current work

Verify current source rather than assuming it matches the last report:
- `tomato3d/light/raytrace.py::direct_light`
- `tools/light_direction_diagnostics.py::DirectionCollector`
- `tools/light_growth_bridge.py`
- `tools/light_growth_consumer.py`
- `tools/light_growth_schema.json`
- `tools/LIGHT_GROWTH_BRIDGE.md`

The latest cited scalar package is `build/light_growth_readiness_20261003_05/`. Its DLI unit is `mol/m2/day`; numerical values were unchanged by that metadata correction. Preserve historical packages and hashes. The recorded 60 passing tests include synthetic and passive-collector checks, not an implemented real-producer angular path.

## 3 Implement the actual producer and connection

1. Add a backward-compatible optional keyword-only diagnostic callback to the existing `direct_light` path, following the referenced callback contract. Keep ordinary calls and the existing `DirectLight` return compatible.
2. Emit the actual already-computed attenuated, receiver-cosine-weighted per-emitter contributions and receiver-to-emitter unit vectors. Do not approximate with lamp centers or repeat ray tracing in tools.
3. Implement explicit fixture/receiver/emitter inventory, stable path indices, bounded ordered chunks, zero contributions, unknown contributions and missing reasons. Preserve read-only buffer lifetime and fail explicitly on callback errors.
4. With the callback disabled, avoid diagnostic allocations. With it enabled, validate declared budgets and report memory/runtime overhead. Keep existing occlusion, own-triangle exclusion, surface-crossing handling and resource limits.
5. Adopt and document the concrete producer protocol, then connect `DirectionCollector` to it. Update both ends consistently; never label a proposed or mocked stream as an actual producer.
6. Carry actual moments into fixture, organ, plant, canopy, time and frame exports through the existing bridge and consumer. Export availability truthfully by backend and field; unsupported native angular channels stay unavailable.
7. Accumulate unnormalized area-weighted F, M and B before normalization. Preserve the distinction between no light, unavailable light and cancellation of opposing directions. Verify rotations M'=R*M and B'=R*B*R^T and translation invariance.
8. Preserve per-instance identity when composing and splitting a canopy. A reporting split retains the original shared-scene shading; do not silently rerun each plant alone.

## 4 Keep physical light quantities distinct

- PPF: source photon output, umol/s.
- Incident and absorbed PPFD: umol/m2/s, separate quantities.
- Photon flux intercepted by supported tissue: umol/s.
- Interval dose: mol/m2.
- DLI: mol/m2/day, only for a complete declared local day.
- Absorptance is applied once.
- Unknown lamp output or schedule is not a dark lamp.
- DLI integration uses actual interval durations and supported geometry/time coverage.

Under D9, P3 may use a fixed-horizon DLI covariate for size targets only. Export explicit light basis, spatial scope and temporal coverage. Do not select an undocumented representative day or default canopy average. Do not add a light-to-growth-direction law, change plant geometry or calculate P4 carbon sufficiency.

D3 still defers cross-project linking. Complete P2 producer-to-export integration only; do not execute P1-P2-P3-P4 end-to-end linking.

## 5 Incorporate the user's lamp arrangement as a separate draft input

The user has now clarified the arrangement after the earlier partial lamp intake.

Shelf:
- Width 600 mm, depth 400 mm, height 400 mm.
- Grow-frame origin: front-left corner of the shelf floor.
- +X right, +Y rearward, +Z upward.

Lamps:
- Three REF-30-40 fixtures, each reported as approximately 517 × 47 mm.
- Long axes parallel to X and centered across the 600 mm shelf width.
- Reported height: 400 mm above the floor, not above the canopy.
- Downward aiming: aim tilt 0 degrees, aim azimuth 0 degrees.
- Long-axis azimuth: 0 degrees.
- Starting at the rear edge: 50 mm gap, lamp 1, 50 mm gap, lamp 2, 50 mm gap, lamp 3, remaining front gap.
- Gaps are edge-to-edge.

Derived coordinates using width 47 mm:

| fixture_id | Location | Center X mm | Center Y mm | Center Z mm |
|---|---|---:|---:|---:|
| LED-01 | Rear | 300 | 326.5 | 400 |
| LED-02 | Middle | 300 | 229.5 | 400 |
| LED-03 | Front | 300 | 132.5 | 400 |

Derived checks:
- Center spacing: 97 mm.
- Front clearance: 109 mm.
- Left and right clearances: 41.5 mm each.
- Do not recenter the group along Y.

These are calculated positions from user-reported dimensions, not independently measured emitting centers. Actual emitting-aperture dimensions, aperture offset and whether the height refers to the emitting face remain explicit assumptions to resolve.

Reported per-fixture product specifications:
- Electrical input 30 W.
- Color temperature 4000 K.
- Luminous flux 3300 lm.
- Luminous efficacy 110 lm/W.
- Supply 220 V / 60 Hz.

Still unknown:
- PPF in umol/s.
- Measured or manufacturer-supported half-intensity half-angle and cutoff.
- Actual daily schedule; 06:00-22:00 was an example only.
- Photon-output fractions/dimming response.
- Electrical power boundary, including driver losses.

Preserve these inputs in a fresh build-only intake/draft using existing provenance types. Unsupported metadata belongs outside strict scene objects. Do not silently label the housing dimensions as measured emitting dimensions, set a numerical PPF from lumens/4000 K alone, substitute example beam parameters or manufacture a schedule.

If the scene schema cannot represent unresolved inputs, save a clearly incomplete draft and readiness report rather than a falsely executable scene. Unavailable physical lamp inputs do not block software implementation and explicitly synthetic tests.

## 6 Acceptance checks

Run meaningful focused core and adapter regression tests:
- Identical default scalar/side behavior with diagnostics off and on.
- Actual path sums reproduce the same call's scalar and positive-normal-side outputs, with identical availability masks and inventory.
- Contract tolerances: atol 1e-10 and rtol 1e-9 unless a documented existing contract requires otherwise; these are software tolerances, not physical accuracy claims.
- Multi-emitter cases where a lamp-center approximation fails; asymmetric and opposing fixtures; zero emission; occlusion; unknown transmittance; unknown fixture inputs.
- Chunk boundary, omitted/duplicate path, borrowed-buffer reuse, callback exception and budget checks.
- Real-producer rotation/translation checks, not only supplied-chunk algebra tests.
- Actual angular time/frame/fixture aggregation and canopy reporting splits.
- Independent consumer validation and a fresh hashed directional package.
- Lamp placement arithmetic and explicit unresolved-input status.

Keep synthetic test values isolated from the real REF-30-40 draft. Actual physical accuracy still needs eligible geometry, optical evidence and independent PPFD measurements. Missing physical data must not be presented as tested real-lamp performance.

## 7 Deliverables

Write a new English execution report in `handoff/` and fresh outputs under `build/`, including:
1. Changed files and functions, adopted callback signature and protocol.
2. Input/output fields, units, vector/area conventions and availability rules.
3. Focused test results, real-producer parity evidence and diagnostic overhead.
4. Fresh package and split paths, source/artifact hashes and consumer checks.
5. REF-30-40 input draft with confirmed, derived, assumed and unavailable entries.
6. Remaining physical/scientific limitations, separated from any unfinished software work.

Append LOG/TODO updates and explain the outcome in Korean. Do not stop at preparing another passive collector or requesting Claude to edit the core: the user has authorized Codex to complete that light-core work. Report completion only for what was actually implemented and verified.

