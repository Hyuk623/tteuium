# Light growth readiness execution

Date: 2026-10-03. Status: implementation in progress; no physical or biological validation claimed.

## Authorized request and inspected state

Execute CODEX_LIGHT_GROWTH_READINESS_PROMPT_2026-10-03.md. Current invocation authorizes the implementation described by that prompt, superseding its historical preparation-only sentence. Keep core, configuration, observations and other active tools unchanged. Use additive tools and fresh build outputs. No native execution, training, inference, upload or growth execution.

Inspected current hierarchy exports, compound observation loader, core DirectLight, authoritative board placement and ScheduleSegment. Public direct arrays support spatial quadrature and normal-side PPFD. Per-emitter angular contributions remain internal: no diagnostic callback exists. Directional production readiness must remain pending until the core owner supplies and verifies that interface. Synthetic angular algebra tests cannot close this dependency.

## Interfaces and implementation order

1. Finalize tools/light_growth_schema.json before executable implementation: exact CSV columns, types, units, nullable rules and keys. JSON carries structured transforms, source evidence and field availability reasons.
2. Add tools/light_growth_bridge.py and focused tests. Public entry points: audit_growth_light_inputs(request_path), export_spatial_light(prepared_run, full_scene_results, out), compute_directional_features(sample_contributions, memberships, frames), integrate_light_schedule(full_output_data, schedule, intervals), export_compound_light_features(spatial, directional, temporal, compound_states), split_canopy_results(package, instance_id, out), validate_growth_light_package(package). Helper functions may expose independently testable algebra without claiming transport capability.
3. Reuse full-scene core receiver arrays, hierarchy weights and immutable prepared inputs. Recheck freshness and parity against ABC full-scene flux, never counterfactual baselines. Explicitly budget the additional full-scene evaluation.
4. Reversible transforms are derived by applying board_to_grow_mm to the origin and basis. Schedule segments reuse the core model. Missing schedule remains unavailable; an explicitly supplied daily schedule has zero output outside its listed lit intervals. Geometry validity and schedule changes bound integration intervals.
5. Reviewed associations join existing compound history by source plant, compound_leaf_id, session, observation timestamp and board frame. Observed rachis is distinct from light arrival. Future envelopes are never optical input. Missing mappings/axes gate only affected features.
6. Export package schema, samples, compound/spatial summaries, intervals, doses, transforms, source-instance map, capabilities, consumer mapping and audit. Independent consumer validation must check freshness, exact headers/keys, units, identities, times, frames, quadrature and consistency. Split reporting preserves full canopy context.

## Verification and remaining completion gates

Focused tests cover directional moments/cancellation/rotation, area weighting and missingness, schedule boundary/dimming/midnight/blackout/gaps, changing supported area, transforms, review joins, native restrictions and schema validation. Run relevant existing regressions after integration. Produce a fresh synthetic package and requirement evidence, plus a scoped audit of the supplied real snapshots. Preserve known missing real surfaces/calibration without another global search.

Software delivery remains partial while the protected-core directional hook is absent. Real readiness also requires reviewed metric tissue, identity/time/axis observations and independently validated light calibration. None of these may be replaced by relative image areas or synthetic examples. Append actual results below; do not mark the goal complete on a partial delivery.

## Delivery checkpoint (2026-10-03)

Implemented additive `tools/light_growth_bridge.py`, independent `tools/light_growth_consumer.py`, machine-readable `tools/light_growth_schema.json`, synthetic `tools/light_growth_demo.py`, CLI/contract guide `tools/LIGHT_GROWTH_BRIDGE.md`, and `tools/tests/test_light_growth_bridge.py`. No existing hierarchy, growth, protected core, configuration or observation file was edited.

Supported functionality: strict metric quadrature exports and weighted distributions; normal/opposite/received/absorbed scalar light; full-scene ABC parity; source/instance and reviewed compound associations; distinct per-instance observation clocks; observed signed rachis orientation; measured-frame local partitions with unassigned/unequal support; bounded fixture schedule splitting and dose/DLI accounting; changing-geometry flux integration; reversible canopy placement and reporting-only splits; native scalar imports retaining replicates without invented sample/side/angular channels; independent serialized consumer checks and source/code/artifact freshness.

The public spatial function adds keyword-only `snapshot`, `run_id` and `max_receiver_emitter_pairs` arguments to the proposed signature, making identity, frame and resource contracts explicit. `build_package(request_path, out)` orchestrates all supported outputs. `compute_directional_features` is pure algebra on complete explicit contribution/path inventories, not a second ray tracer. Production angular fields remain unavailable with a field-specific reason.

Verification: 266 related regressions passed (core light, hierarchy, canopy, bridge, native preparation/collection, PPFD, observed and probabilistic growth contracts). After final read-only association-audit and per-instance clock changes, 24 focused bridge checks passed on the final implementation. JUnit: `build/light_growth_readiness_verification_20261003_01/regression.junit.xml` and `bridge_delivery.junit.xml`. The old core/hierarchy/growth files were unchanged between these runs.

Final fresh delivery: `build/light_growth_readiness_20261003_03/`; earlier `_01` and `_02` examples are superseded. Main package and P1/P1_COPY splits pass independent consumer checks. Main counts: 5 instance/compound mapping rows, 1344 sample/fixture/time rows, 1080 feature rows, 14 fixture intervals, 48 dose rows. Source-copy inverse coordinates match while separate instance IDs and full canopy shading/context remain. See `REPRODUCTION.md`, `consumer_checks.json`, `copy_roundtrip.json` and `requirement_audit.json`. Counts are not unique biological organs or real observations.

Real audit: four explicitly known snapshots were rechecked at `build/light_growth_readiness_20261003_01/real_audit/real_readiness.json`. All remain blocked by missing scene/accepted leaf surfaces/selected plant case; T3 also lacks registered geometry provenance. Original source/media hashes remained unchanged. No broader search or fabricated observations.

Remaining mandatory dependency: current protected `direct_light` still has only scalar/normal-side outputs and no angular callback. The exact backward-compatible per-path hook request is in TODO. Once the core owner supplies it, owned callback wiring, time/frame directional exports and actual transport scalar/side/angular parity remain necessary. Pure algebra tests cannot close this gate. No cross-chat message was sent. No native optical job, training, new inference, upload or biological forecast was launched by the bridge.

Readiness is partial. Scalar/area/time consumer software is available with explicit evidence gates; real inputs remain unavailable and physical validation is false. The full prerequisite for the subsequent growth-direction implementation prompt is NOT ready. The active objective is not complete, and its scope has not been reduced. This is the first delivery turn encountering the verified external hook dependency after independent work; do not mark blocked before the required repeated-turn audit.

## Continuation audit 2 — 2026-10-03

Previous goal turn made substantial implementation progress. Rechecked current core, LOG/TODO and the final package: the angular hook is still absent and the _03 package is fresh/valid under its existing checks. New coordination D1-D4 documents defer cross-project linking and keep P4 diagnostic; this continuation does not change P3/P4 or add cross-project execution.

An owned verification gap remains: the independent reader currently checks whole-supported grow-frame scalar totals but skips scalar invariance and observed-direction transforms in other frames, as well as detailed local-region consistency. Strengthen the serialized consumer and add producer-error regression fixtures before claiming that frame/region outputs meet the export contract. Reject unsupported angular/native channel claims according to capabilities. Reproduce the gap with a failing test first. This work is within the original consumer/frame gate; the external core blocker remains unchanged (second consecutive delivery/continuation turn).

Continuation-2 outcome: reproduced three consumer false acceptances (incorrect board-frame area, board-frame flux, and invented directional channel), then corrected the independent reader. Added full-frame scalar/identity invariance, observed-axis rotation/signed-angle checks, local-region area/flux/weighted-quantile/contrast checks, missing-region rejection and unsupported native/angular capability gates. Eight added regression cases cover the reproduced issues plus region/axis errors. Final focused suite: 32 passed in 33.95 s; JUnit `build/light_growth_readiness_verification_20261003_01/consumer_strengthening.junit.xml`.

Current export is `build/light_growth_readiness_20261003_04/`, superseding _03 as a consumer-verified package. It reuses the immutable _03 request/prepared/legacy hierarchy results instead of rerunning counterfactuals. Main package and two same-source splits pass the strengthened checker; source-board coordinate equality and full canopy context are reverified. `requirement_audit.json` retains historical evidence, the new tests, and current hashes. The core raytrace source hash is unchanged and has no angular diagnostic hook. No core/P3/P4 edits, native execution, new real-data search or cross-project linking occurred. Only the external angular interface and subsequent dependent wiring/parity remain for the full light objective; this is the second consecutive verified blocker turn, so the goal remains active rather than prematurely blocked or complete.

## Blocked audit 3 — 2026-10-03

Previous turn was progress: independent-consumer defects were reproduced and fixed, with 32 focused checks and new _04 outputs. This third consecutive goal turn rechecked the exact core signature and source hash: the mandatory angular diagnostic hook is still absent. All source/code/artifact hashes for the main _04 package and both splits remain valid. No tests or simulations were rerun merely to show activity.

The invoked prompt section 2 explicitly prohibits editing protected core or copying another ray tracer, and requires leaving direct directional readiness incomplete until the hook and parity exist. Independent owned work is delivered; the remaining callback wiring, time/frame angular exports and actual transport parity depend on the missing interface. No actionable independent required work remains at this checkpoint. Blocked audit threshold is met; preserve the full objective as blocked, not complete. Resume when the core owner supplies the reviewed backward-compatible diagnostics and parity contract (or the user explicitly changes scope/ownership). See build/light_growth_readiness_20261003_04/blocker_audit_3.json. No cross-chat message or deferred integration was initiated.


## Resumed angular request: passive callback preparation, 2026-10-03

See CODEX_ANGULAR_CALLBACK_EXECUTION_2026-10-03.md and CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md. Core still has no callback; ownership preserved. Added a bounded tools-only receiving collector and exact proposed contract. Combined protocol/bridge tests: 60 passed; final collector guard: 28 passed. Existing _04 main/splits independently valid with original hashes. New evidence: build/light_direction_callback_20261003_01. No live core angular export or new angular result package exists; completion remains partial, physical validation false.
