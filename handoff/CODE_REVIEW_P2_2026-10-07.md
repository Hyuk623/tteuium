# P2 review request: light transport and reference channels

Perform a read-only full-scope P2 code review. Read [common instructions](CODE_REVIEW_COMMON_2026-10-07.md). Use the frozen snapshot and `P2/scope.json`. Output only to `build/code_review_20261007_01/P2/`. Follow the actual P1 inputs and P3/P4 consumers; do not edit them.

## Entry points and scope

- All `tomato3d/light/` and `tomato3d/cli/run_light.py`.
- `tools/plant_light_bridge.py`, `canopy_light.py`, `hierarchical_light.py`, `hierarchical_light_native.py`, `light_study.py`, `ppfd_validation.py`, associated demos and UI.
- `tools/leaf_light/common.py`, `optics.py`, `evaluation.py`, `explorer.py`, `report.py`; cross-read geometry/reconstruction files under P1.
- `tools/light_growth_bridge.py`, `light_growth_consumer.py`, `light_time.py`, `light_face_evidence.py`, `light_geometry_evidence.py`, `light_direction_diagnostics.py`, `light_reference_channel.py` and schemas.
- All `tools/reference_dli*.py`, including `reference_dli_p3.py`, and relevant GroIMP bridge paths. Review external-engine adapters statically unless bounded local dependencies are already available; do not start external jobs.

## Priority counterexamples

1. Photon units, area conversions, inverse-square geometry, finite-emitter integration, receiver cosine and emitting-side conventions. Check limiting scenes by hand; numerical computability is not calibration.
2. Self-intersection, occluder ordering, duplicate hits, partial/missing geometry and transmittance. Verify direct-path attenuation and area weighting without duplicate absorptance or repeated tissue counts. Missing optics must not silently act as measured zero transmission.
3. Actual-path direction callback: chunk bounds, receiver/emitter identity, sign, borrowed-buffer lifetime, missing/dark paths, cancellation/errors and disabled-path numerical parity. Do not replace actual rays with a lamp-center approximation.
4. Canopy -> individual extraction must retain neighbor occlusion while preserving original instance/plant/organ/triangle identity and area partition. Rotations transform positions and directions consistently.
5. Schedule integration: instantaneous versus interval-mean samples, transitions inside intervals, aware timestamps, 23/25-hour days, local-day boundaries, gaps/overlaps, darkness versus unavailable and incomplete horizons. No unconditional representative-day reduction.
6. Botanical face evidence must bind to exact geometry and identity; winding alone is insufficient. Opposite-face sources cannot be relabelled same-face to satisfy P4. Rehashed output tampering must be detected semantically, not just by a checksum.
7. Incident reference DLI must stay separate from absorbed leaf light through producer, package consumer and P3 mapper. Check supported domains, source clock/position/level/cosine/ambient metadata and missing measurement rules.
8. CLI/serialization/UI should expose the same availability and method limitations as library APIs. Confirm scalar totals agree with sample/triangle/plant sums under the adopted definitions.

## Contract references

- `handoff/CODEX_P2_GROWTH_PACK_V2_EXECUTION_2026-10-04.md` (final section supersedes interim text)
- `handoff/CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md`
- `handoff/CODEX_P2_AREA_REVIEW_EXECUTION_2026-10-05.md`
- `handoff/CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md` and D19/D20
- Current guides/schema adjacent to the listed tools; P3/P4 accepted input contracts for cross-reading.

## Validation entry points and handoff

Inspect relevant `tests/test_light_inputs.py`, `test_light_raytrace.py`, `test_light_pipeline.py`, `test_light_angular_transport.py`, plus `tools/tests/test_canopy_light.py`, `test_hierarchical_light.py`, `test_plant_light_bridge.py`, `test_light_growth_bridge.py`, `test_light_angular_exports.py`, `test_light_direction_diagnostics.py`, `test_light_reference_faces.py`, `test_light_reference_provenance.py`, `test_light_area_review.py`, and all discovered reference-DLI tests. Run only isolated fixtures; record skips.

Boundary report must show P1 geometry -> P2 receiver eligibility, P2 reference channel -> P3, and P2 tissue exposure -> P4. Record existing adapters versus interfaces only. Absent physical PPF/PPFD calibration, unimplemented reflection/scattering and deferred simulation routes are not automatically bugs; false availability or unsupported claims are actionable.
