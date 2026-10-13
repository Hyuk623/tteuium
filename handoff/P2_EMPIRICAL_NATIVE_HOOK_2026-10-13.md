# P2 -> native owner: empirical light response and transport instrumentation

Owner: existing chat **Read GroIMP Python integration brief**. This file is the requested local handoff; no direct chat message or native source patch has been sent. Coordination entries are appended in LOG. Preserve flow and forecast files.

## Empirical hook now supplied

Producer: tools/empirical_growth_boundary.py, schema empirical-growth-boundary-1. Consumer: tools/empirical_growth_consumer.py. Native response adapter: tools/empirical_native_response.py. See tools/EMPIRICAL_GROWTH_BOUNDARY.md for units/fields. Existing empirical outputs are unchanged.

The newly added native owner API in NATIVE_BOUNDARY_CONTRACT_2026-10-13.md is compatible with our response envelope. `prepare(native_folder, boundary_path, configuration, context_path, interval, fraction, out, submit=False)` validates prepared lineage and actual consumed mesh, creates an absorbed response and optionally calls the owner's submit_light. Core APIs used: verify_prepared(native_folder), read_request(working, interval), submit_light(working, interval, response).

The response preserves source/configuration/code hashes and includes a selected empirical direction/orientation scenario. All native leaves must match exact snapshot triangles, namespace, owner and area. Source snapshot is in canopy metres; registration to the grow shelf is separately bound. One native interval may consume only constant on-period absorbed rate with matching native light_hours. Nonlinear NRH must not receive dose/duration averaged across dark and lit periods. Native must retain external_once transport and native_once state authority. No second shade/absorption multiplier.

Current native shape/hash conventions differ: boundary geometry_hash is digest([{surface_id,triangles_m},...]); native geometry_sha256 is byte hash of boundary_N_geometry.csv. The adapter checks actual coordinates/vertex inventory rather than equating these hashes. Use snapshots built from the exact native consumed vertices; never reuse initial P1 geometry after growth. No rounding or mesh-area rescaling is applied to force a match. If native o.area differs from current mesh area beyond atol=1e-12/rtol=1e-10, stop and resolve the area contract with evidence.

Please provide a stable fresh native fixture run with its live boundary request, registered physical geometry inside the measured support and the explicitly chosen black equivalence rule. Native regression remains your ownership. A passing joint result must include:

1. Native request produced before physiology from live consumed mesh, exact predecessor/input/engine/configuration binding.
2. The selected empirical scenario's absorbed rate appears in native flux exactly once; no lm.compute for incoming-light tissue.
3. Gross photosynthesis agrees with the native absorbed-basis formula using on-period rate and hours; carbon, age, reserve and geometry advance once.
4. Replay/stale request/wrong namespace/wrong geometry/wrong configuration/expiry fail or retry as specified. Later tissue outside 70..150 mm or the XY support is rejected before growth.
5. Each direction scenario runs separately. Failed/unsupported empirical data does not fall back to old lamps or whole-plant reference DLI.

Current software tests submit to a labelled protocol fixture only. No claim of actual native consumption is made until the real engine writes its audit/completion. Real/nonfixture NRH mapping remains unreviewed. For nonblack optical fixtures, retain light_only/disabled_diagnostic; for growth black equivalence require absorptance=1 and transmittance=0 explicitly.

## Independent diagnostic: source/API coverage

Read-only evidence: local build/fsp_extensions_20261011_api_01/{LightModelProcessor.java,RadiationModel.java,Phong.java,sources.json}, frozen from GroIMP tag 2_2_1; current tools/fsp_extensions_native.rgg, tools/fsp_extensions.py, tools/vtc_development_native.rgg and tools/tomato_fsp_native_boundary.py. Frozen source hashes are verified in this delivery's api_coverage.json. Installed runtime identity must be rebound by any future compiled instrumentation; the frozen source tag alone does not prove byte-identical compilation.

| Quantity | Actual source/API behavior | Required extension |
|---|---|---|
| Received power | LightModelProcessor.traceRay lines 436–466 tests earlier volume IDs and tallies only the first hit on that volume along the path | Separate every-hit incidence tally before firstHit gating; retain old tally unchanged |
| Received direction debug | Collector / getReceivedPowerD represents that estimator; traced RayPoint data is for debugging | Must not relabel either as complete weighted path accounting |
| Absorbed/reflected/transmitted power | Existing RadiationModel getters and extensionLight expose separate raw spectra/power | Preserve signed float32 subtraction effects, estimator weights and spectral basis |
| No intersection / infinite sky | traceRay lines 361–370 conditionally enters finite hit branch; no published terminal tally on return | Record explicit escaped path event for each terminal branch, distinguishing sky versus empty miss |
| Depth/minimum-power termination | traceRay lines 551–562 only recurses while depth and power predicates permit | Record residual outgoing spectrum with reason and exact weight BEFORE returning; do not count it as absorption |
| Source allocation | compute allocates rays by source power with normalizing factors | Record source ID, sampled launch power, normalization and emitted tally; account for integer allocation and zero-power sources |
| Native photon budget | extensionLight writes escape/termination/estimator_residual unavailable; validate_native_optics enforces this | Keep unavailable until corresponding events exist; residual is then a diagnostic difference, never an observed escape tally |

## Exact proposed instrumentation contract (not implemented)

Version `groimp-transport-events-1`, diagnostic callback or streamed chunks. Events carry run/seed/source_id, stable emission_ray_id/path_id/parent_path_id, bounce index, monotonically assigned event index, object/surface ID where relevant, entry point and incoming unit direction in canopy frame, raw spectral bins/unit, estimator normalization weight, weighted power W, event_kind, validity and missing reason. Preserve finite zeros separately from unknowns. Chunk headers declare expected launches/paths when knowable, sequence range, final counts and completion; missing/duplicate events invalidate closure. Do not retain all paths in RAM: bounded chunks and per-surface/terminal accumulators with deterministic merge, plus resource usage and truncation flags.

Kinds: launch, incidence_each_hit, absorption, reflection_transfer, transmission_transfer, escape_empty, escape_sky, cutoff_depth, cutoff_min_power, invalid_or_aborted. Multiple stopping predicates need deterministic precedence and a bitset of applicable predicates so a path is counted terminal exactly once. Internal reflection/transmission and repeated incidence are transfers, not terminal sink terms. Terminal energy accounting uses independently tallied absorbed + escaped + cutoff categories against sampled launched energy on the same estimator/spectral basis. A numerical residual is derived and stays separate. Invalid/aborted paths make closure incomplete; they are never discarded. No `escape = emitted - absorbed` shortcut is permitted.

Implement in a versioned local Raytracer extension only after the native owner verifies a supported hook/build/classpath route. The inspected aggregate getters do not expose terminal event callbacks; wrapping public getters cannot recover the missing events. Do not overwrite the installed GroIMP JAR or substitute a new shadow tracer. Required controls: black receiver, empty scene, transparent passage, mirror revisit (every-hit > first-hit), each cutoff reason, no source, paired seeds, unchanged scalar results with diagnostics off/on, chunk dropout/duplication and bounded-memory runs. Report absolute/relative tolerances and Monte Carlo uncertainty separately; no false exact closure over unrelated estimators.

This diagnostic extension is independent of the empirical growth adapter and must not restart wall fitting or block its conditional export path.

## Final coordination addendum: empirical native consumption verified

Superseding the intermediate protocol-only status above: fresh native light-only runs completed for the separate 0.5/0.6/0.7 diffuse scenarios using 45 declared engineering leaf triangles, one interval each. Evidence is build/p2_empirical_growth_boundary_20261013_01/delivery_verification.json and native_joint_03/diffuse_60 plus native_joint_04/diffuse_50 and diffuse_70. All 135 leaf-interval absorbed rates equal the submitted rates exactly; published audit says external_once. Native mass/thermal age/area are unchanged and gross carbon is zero. Owner API/controller reused unchanged. Source/code/artifact hashes and independent export consumers were rechecked by finalize_delivery.py.

These runs fulfill light-response consumption only. The growth/NRH and real-surface acceptance items above remain open; no growth was enabled and the original P1 mesh was not used. The engineering replacement and resource cap are documented in P2_EMPIRICAL_GROWTH_BOUNDARY_EXECUTION_2026-10-13.md. First-hit and terminal transport diagnostics remain contract-only. Prior failed preparations/timeouts are preserved rather than rewritten.
