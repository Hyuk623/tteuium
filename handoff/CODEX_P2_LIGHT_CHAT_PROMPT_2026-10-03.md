# P2 light simulator continuation prompt

Target chat: **광시뮬레이터**

Date: 2026-10-03. This is a paste-ready continuation prompt for the named project chat.

Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.
All paths below are relative to this root unless stated otherwise.

Read the parent `공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, the last five lines of `handoff/LOG.md`, and `handoff/TODO.md` first. Create an English work brief before implementation. Respect file ownership and active OneDrive edits: Codex owns `tools/` and `tools/tests/`; protected core changes belong to Claude Code. Do not edit human configuration, observations or `docs/`. Record specification conflicts for Claude rather than inventing a scientific decision.

Read [the integration decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), including D1-D10. The latest explicit decisions take precedence over older proposals; the Science review was not adopted in full. Inspect current source and execution records before repeating work.

Shared boundaries:
- P3 owns realized growth increments and future geometry. P4 is a read-only carbon diagnostic at runtime.
- Cross-project linking remains deferred under D3. Continue this project's own work; do not launch an end-to-end pipeline.
- An explicitly selected, frozen and hashed calibration pack may be applied before P3 runs under D5; never fit or apply it implicitly at runtime.
- The first later synthetic pass requires numerical P1-P2-P3 results. P4 may be unavailable with reasons under D6.
- Round-trip checks apply to reversible units, frames, IDs and representations. Light transport, aggregation, photosynthesis and forecasting require forward correctness checks, not inversion.
- Preserve source samples, complete shapes, identity, uncertainty, missingness and provenance. Follow each producer's actual missing-value contract rather than replacing unknown values with zero.

Continue work already authorized in this chat. A missing prerequisite should block only dependent work. Do not treat this prompt as permission for new private-data uploads, paid services, training or cross-chat messaging. Finish with an English handoff and a Korean explanation, distinguishing implemented software, synthetic evidence, scientific assumptions and remaining dependencies.

## Objective and source documents

Finish the light simulator's own remaining directional-output work using actual transport contributions. Preserve the delivered scalar, spatial, side, time and canopy-split outputs.

Read:
- [Light readiness handoff](CLAUDE_LIGHT_GROWTH_READINESS_HANDOFF_2026-10-03.md).
- [Core callback contract](CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md).
- [Angular callback execution record](CODEX_ANGULAR_CALLBACK_EXECUTION_2026-10-03.md).
- `tools/LIGHT_GROWTH_BRIDGE.md` and `tools/light_growth_schema.json`.

## Required work

1. Inspect the current `tomato3d/light/raytrace.py::direct_light` signature and latest core-owner delivery. The recorded state had no adopted callback; `tools/light_direction_diagnostics.py::DirectionCollector` is a tested passive collector for a proposed protocol. Its tests do not establish a real producer connection.
2. If the protected producer is still missing, document the exact dependency for Claude Code and continue independent owned work. Do not edit the protected core as Codex, wire a guessed signature, extract local variables through tracing, build another ray tracer or substitute lamp-center directions.
3. Once an explicit compatible producer exists, connect its actual attenuated, receiver-cosine-weighted per-path incident contributions. Preserve stable fixture/receiver/emitter inventory, chunk completeness, zero paths, unknown paths, missing reasons, buffer lifetime and resource limits.
4. Prove callback off/on scalar parity and same-call contribution parity against received and positive-normal-side PPFD. Follow the tolerances and strict side convention in the adopted contract. Exercise multiple emitters, asymmetric/opposite lighting, occlusion, darkness, missing attenuation, incomplete streams and chunk boundaries.
5. Use the existing moment contract for unnormalized area-weighted flux F, first moment M and second moment B. Sum compatible contributions before normalization. Preserve opposing-direction degeneracy; a zero resultant vector is not evidence of no light. Use explicit vector convention and frame. For rotations, check M'=R*M and B'=R*B*R^T; translations do not rotate direction.
6. Extend owned exports and consumer validation through `tools/light_growth_bridge.py`, `tools/light_growth_consumer.py`, `tools/light_growth_schema.json` and their existing tests only as the adopted contract permits. Cover fixture aggregation, timestamps, intervals, coordinate transformations and instance-preserving canopy splits.
7. Keep incident PPFD, absorbed PPFD, photon flux and integrated dose distinct. Do not multiply absorptance twice. For daily incident light, DLI = sum(PPFD_i * dt_i) / 1e6 in mol/m2/day, with dt in seconds and explicit time coverage. A snapshot alone is not a measured daily exposure.
8. Under D9, P3 uses a fixed-horizon DLI covariate for size targets only. Export the light basis, spatial scope, timing and coverage needed to select that covariate explicitly later. Do not silently convert an absorbed dose to incident DLI or choose an undocumented canopy/organ average.
9. Directional light remains a physical output. D9 does not adopt a light-to-growth-direction response; do not rotate leaves, maximize light biologically, apply growth coefficients or calculate carbon sufficiency in P2.
10. Preserve full-canopy transport context when splitting results by plant instance. Retain mutual shading from the shared scene; an isolated-plant rerun is a different experiment. Carbon pools belong to individual plants downstream.

## Validation and delivery

Keep existing verified packages immutable. Generate a fresh package with fresh source hashes after real producer integration. Run focused scalar/side/angular, time, frame, missingness and canopy-split checks. Preserve explicit capability limits for unsupported native angular channels.

Deliver a new English P2 continuation report in `handoff/` stating the adopted producer signature, changed functions and schema fields, units, test results, provenance, package paths and remaining real-input limitations. If the core is still absent, report directional integration as incomplete, not delivered. Do not run P3/P4 or claim biological prediction accuracy.


## User ownership override, 2026-10-04

The user revoked the Claude-only light calculation core restriction. Codex may now implement `tomato3d/light/` and relevant light tests under `tests/` directly, then connect and validate the existing tools collector/export path. The former requirement to wait for a separate core-owner delivery is superseded. The callback and angular export still require implementation; this notice is not completion evidence. See `CODEX_LIGHT_CORE_RULE_UPDATE_2026-10-04.md` and the replacement prompt `CODEX_P2_LIGHT_CHAT_PROMPT_2026-10-04.md`. Historical results and blocked-status records above are preserved.
