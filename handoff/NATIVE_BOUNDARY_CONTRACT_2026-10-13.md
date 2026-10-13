# Native continuation boundary contract (before implementation)

Request: PROMPT_CODEX_NATIVE_CONTINUATION_2026-10-13.md. All flow/ files, producer code/observations, empirical-field code and forecast wrappers remain untouched. Existing schedules, optics and H1–H3 are reused. No wall-reflectance fitting. Claims are in LOG.

Inspected gaps: revision-7 capture planes are validated by the producer but the consumer does not pass plane_by_capture to area validation or freeze frame_transforms. Completion manifests are only shallowly checked. V3 computes an entire native trajectory before advance_interval publishes checkpoints; neither an external light handshake nor a causal nutrient pause exists. Imported meshes retain funded scaling; an age/deformation law remains absent.

## 1. P1 intake

Consume actual revision-7 packages using the producer validators, including scale reference planes and frame transforms; freeze these evidence files. Preserve plant-local mm and canopy m conversions once. Explicitly reject metre/pixel relabelling of a producer mm schema. Solved 2-D scale never implies supported 3-D optical surfaces. Conditional completion requires a versioned, hash-bound manifest with observation links, declared scale/depth/posture assumptions and selected identity mapping. It must cover actual selected geometry; no generated completion may enter observed_metric. Independent physiology remains a separately supplied assumption. Audit real and fixture packages separately.

## 2. Opt-in native light boundary

Proposed executable schema `fsp-native-boundary-1`, absent by default. Enabled only with the integration consumer. Before each interval's light and growth, native code emits its actual consumed mesh and live leaf identity/area inventory, then atomically publishes a request bound to run/input/engine, interval start/end, geometry/leaf files and predecessor completion. It waits for one immutable response with a bounded explicit timeout. Python may validate/submit a response; Python does not advance the plant.

The incoming quantity is an **absorbed** per-leaf photon flux in umol/s, both geometric faces over one-sided lamina area, already including exactly one canopy transport calculation. Incident per-leaf flux must retain its distinct basis and is rejected by the growth boundary until a reviewed optical/NRH mapping exists. Scalar reference DLI, a second shading multiplier, and automatic interpretation of intercepted empirical flux as absorbed are forbidden. Source/configuration/code hashes, interval, all live leaf IDs/areas and exact actual native geometry lineage must match. Config changes invalidate a response. Zero-area/non-optical leaves are excluded explicitly by the native inventory.

First implementation scope is absorbed-flux interface mechanics: engineering fixture growth may use an explicit `fixture_black_absorbed_equivalence` basis only when fixture=true. This reuses the already selected black-leaf V3 numerical law and is not empirical biological approval. Real or non-fixture incoming growth stays blocked with `nrh_light_basis_unreviewed`. External light-only diagnostics are permitted only with absorbed basis; incident empirical output requires a future reviewed adapter. The native engine owns reserves, clock and mass exactly once. A response expires before consumption; an identical retry is idempotent and a conflicting retry fails. There is no process restart from a half-mutated plant state: failed runs require a fresh output directory.

No native canopy light computation runs for incoming-light intervals. The old empty reference-grid comparison is a separate diagnostic and must be labelled unavailable for external light (zero sentinel sensor rows must not be presented as computed physical light). Output lineage retains request/response and native light audit. Default-off native behavior remains numerically unchanged.

## 3. Imported shape API, default off

Validate declared imported organ/parent/anchor identity, local-metre frame, finite anchor and reference geometry hash. An enabled developmental deformation request is rejected with `developmental_shape_law_unavailable`; no new bend/age/area law is selected. Supplied anchor metadata alone never changes initial mesh or mass. Existing funded scaling and carbon closure remain authoritative. A future law must specify age response, anchor support, mass/area consistency and permitted geometry evolution.

## 4. Reservoir proposal/pause/finalize contract — gated

Required causal order: committed predecessor → consumed geometry/light → provisional gross exchange and organ demands on a scratch next-state → source-bound reservoir proposal → pause → time-bounded reservoir response → apply the reviewed law once → verify plant/resource ledgers → atomic final state/resource commit. A response must bind transaction, predecessor, native model/parameter/geometry/configuration hashes, interval and plant membership. Same transaction/response retry returns the same commit; changed/stale response fails. Timeout or partial publication exposes no accepted future state.

No-feedback remains the current path. The existing proposals.csv is retrospective diagnostics and MUST NOT be used to constrain already-computed growth. EC-equivalent reservoir bookkeeping is not element-resolved demand/allocation. This task supplies a validated default-off resource hook declaration/readiness gate; actual causal nutrient finalization stays unavailable until the reservoir owner supplies the exact executable law, units, response semantics and rollback/commit coordination. A generic file pause is not claimed as a complete nutrient handshake.

## Validation plan

Actual real/fixture producer intake; plane/frame/unit and completion corruption; native mesh/ID/source/predecessor tamper refusal; default-off and geometry preservation; a fresh native boundary fixture with external absorbed light, replay and carbon/clock/area checks; native timeout/failure before publication; affected V3/integration/forecast-consumer regression. Report terminal photon closure, E6 law and E7 causality separately as still absent. No biological accuracy claim.

## 5. Implemented wire format and receiving API

The native request is `boundary_<i>_request.json`, published after `boundary_<i>_geometry.csv` (canopy metres, actual native triangle order) and `boundary_<i>_leaves.csv` (organ_id, plant_instance_id, area_m2). It includes schema_version, run_id, zero-based interval, interval_start/end, coordinate_frame=canopy_m, geometry_sha256, leaves_sha256, configuration_sha256, input_hash, engine_hash, predecessor_sha256 and deadline_epoch_ms. Interval zero binds the frozen input hash; later intervals bind the previous native checkpoint completion file. Every optical leaflet must have exactly one response row, including zero flux where appropriate. Non-optical organs are not response rows.

`tools.tomato_fsp_native_boundary.read_request(working, interval)` validates the live geometry/inventory and predecessor. `submit_light(working, interval, response)` validates and publishes response JSON and light CSV, then ready CSV last. The native process freezes the request hash before waiting and checks request/response/light hashes plus expiry before assigning photons. The response schema is:

```json
{
  "schema_version": "fsp-native-light-response-1",
  "request_sha256": "<SHA-256 of the exact native request file>",
  "configuration_sha256": "<same configured source/placement hash as request>",
  "basis": "absorbed_photon_flux", "unit": "umol/s", "transport_count": 1,
  "source_kind": "derived", "source_ref": "<source manifest>",
  "source_files": {"<absolute source file>": "<SHA-256>"},
  "code_files": {"<absolute producer code file>": "<SHA-256>"},
  "expires_epoch_ms": 0,
  "leaves": [{"organ_id":"<exact ID>", "plant_instance_id":"<exact owner>", "area_m2":0.01, "absorbed_umol_s":0.0}]
}
```

The numeric examples above illustrate the schema, not selected biology; expires_epoch_ms must be in the future and no later than the native deadline. The run-level native_boundary declaration additionally requires enabled=true, area_basis=one_sided_lamina_full_outline, transport_authority=external_once, nrh_basis, integer timeout_s (1..300), and source_kind/ref. Omit native_boundary to use the existing native light authority. This version explicitly rejects simultaneous `extensions` transport; schedule/material combinations require a reviewed reconciliation and must not be silently averaged before nonlinear NRH. Response flux denotes the selected light-on flux over the native environment's light_hours. Varying light-on PPFD requires explicit compatible subintervals, not a daily average. No reference-grid sensor values are fabricated for external authority.

Python CLI: `python -m tools.tomato_fsp_native_boundary --working <native/working> --interval 0 --response <response.json>`. Run the existing pipeline process and its responder concurrently. A failed attempt is immutable; start a fresh run. Idempotent response submission is not a restart API. Existing `advance_interval` remains publication of a native-produced checkpoint, never a second growth calculation. P2 owns `empirical_native_response.py`; the native owner does not rewrite that adapter or certify its optical science.

## 6. Completion and anchor compatibility details

Completion manifest schema is `fsp-p1-completion-1`; producer_version and scale_assumptions/depth_assumptions/posture_assumptions lists are required. Every assumption has source_kind and source_ref. `files` binds selected geometry and core producer tables. `simulation_identity_map` must exactly cover selected compound-leaf and leaflet simulation IDs. `observation_links` carry simulation_organ_id, plant_instance_id, capture_id, observed_organ_id and source_ref; links must exist in the selected producer identity table and agree with the mapping. Synthetic completion fixtures remain fixture=true and never enter observed_metric. A real producer completion package has not been supplied by this task. P1 must publish it; the consumer cannot generate missing 3-D surfaces from rim scale.

Revision 7 uses complete frame columns and checks capture/frame plane agreement. The historical nine-column frame schema is validated explicitly only for older packages; absent plane/uncertainty remains unavailable. Supported legacy fields are not upgraded to revision 7. The frame file is frozen and hash-bound in both cases.

`imported_shape_api`: schema_version=fsp-imported-anchor-1, enabled=false, anchors list. Each anchor requires organ_id, parent_id, frame=plant_local_m, anchor_m=[x,y,z], reference_geometry_sha256 (canonical digest of that organ's imported triangles_mm), source_kind and source_ref. The supplied point must equal the declared organ base; metadata cannot relocate the mesh. enabled=true fails until E6 has an exact law. Initial mesh and funded area/carbon checks remain in the native output validator.

## 7. Exact future reservoir transaction envelope (not activated)

The implementation accepts only resource_hook={schema_version: fsp-native-resource-hook-1, enabled: false, quantity_basis: EC_equivalent_not_element_resolved}. enabled=true reports native_nutrient_causal_law_unavailable. No f_nut value is selected here.

For a future enabled protocol the proposal MUST include transaction_id, run_id, scenario_id, tray_id, sorted plant_instance_ids, interval index/start/end, predecessor_commit_sha256, native_state_sha256, reservoir_state_sha256, model_sha256, parameter_sha256, geometry_sha256, configuration_sha256, selected_law_sha256, source_kind/ref, quantity_basis, deadline_epoch_ms, and per-plant provisional gross_gC, maintenance_gC and organ demand_gC. Hashes identify canonical immutable bytes. transaction_id must derive from that complete frozen envelope; it cannot be an arbitrary reusable name. The reservoir response must echo proposal_sha256 and all bindings, name its source/law, include its expiry and a complete per-plant response with explicit units. The science owner must define the exchange law and f_nut response before these payload values can be meaningful. If selected later, f_nut multiplies provisional gross once before plant allocation, never after mass has advanced.

Both owners verify the unchanged predecessor and publish to one transaction staging directory. Finalization validates both ledgers and state hashes, then atomically publishes one joint commit manifest referring to both immutable states. Neither a plant-only future state nor a reservoir-only update is accepted as the joint result. Same transaction/response returns the same commit; changed response fails. Timeout, partial staging, or conflicting predecessor means no accepted commit and requires a fresh attempt from the committed predecessor. Different plants never share the plant carbon pool. The no-feedback route bypasses this protocol unchanged. Existing standalone reservoir fixture transactions and retrospective native proposals are separate diagnostics, not evidence that this causal native protocol exists.
