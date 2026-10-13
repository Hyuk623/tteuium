# Extend the connected FSP pipeline: eight remaining capabilities

Date: 2026-10-11
Recipient: Codex native/integration implementer; Claude scientific reviewer and Claude Code P1/forecast owners
Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

## Objective and verified starting point

Extend the delivered P1 consumer -> canopy -> native P2 -> P4 -> P3 -> relight pipeline. Implement the eight capabilities below without replacing working V3 development, P1 tracking or the Micro-Tom forecast wrapper.

Read first:

- Parent rules, project AGENTS/CONVENTIONS, current LOG/TODO and active file claims.
- `handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md` and its frozen acceptance artifacts.
- `handoff/FOUR_PROJECT_INTEGRATION_CONTRACT_2026-10-11.md`.
- `handoff/P1_EXECUTION_2026-10-11.md`, actual `p1_state_v1` schema and producer packages.
- `handoff/MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md`, especially H1–H3.
- `handoff/VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3_2026-10-11.md`, `VTC_V3_PENDING_DECISIONS_2026-10-11.md`.
- `handoff/CLAUDE_FOUR_PROJECT_SCIENCE_EQUATION_PARAMETER_REVIEW_2026-10-11.md` and `CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_REQUEST_2026-10-06.md`.
- The S1/S2 ownership amendments and public APIs in `tools/TOMATO_FSP_PIPELINE.md` and `tools/MICROTOM_FORECAST.md`.

The inspected integration report delivers conditional native execution on actual P1 **fixture truth**, four instances and three intervals. It does not deliver real-photo reconstruction. Existing light outputs are absorbed leaf flux/PPFD on black tissue; full photon accounting is unavailable. Imported geometry expands with preserved initial posture. The half-day test repeats averaged light/dark durations and does not implement actual subdaily schedules. Nutrient bookkeeping is prescribed and feedback-disabled. H1–H3 are inactive. Confirm current code before treating this snapshot as unchanged.

The real audit lists 117 captures without solved metric scale/aware time and 13 plants without optical surfaces. Do not remove these evidence gates merely to make real runs pass. Metric coordinates may be in mm and converted to m; being expressed in meters is not itself a requirement for measured evidence.

## Ownership, sequencing and authority

Codex implements native hooks, transport, runtime scene/controller and consumer changes under coordinated claims. Claude Code retains P1 reconstruction/schema and Micro-Tom forecast wrappers. Request exact producer/wrapper changes through LOG and versioned contracts, rather than editing those paths unilaterally. Prior claims were released in the delivery report; recheck and claim files before new edits.

Use existing `tools/tomato_fsp_{pipeline,io,canopy,acceptance}.py`, `tools/vtc_development*`, bridge and native fork where appropriate. Add focused tests under `tools/tests/`. Write generated scenarios/results under a fresh `build/fsp_extensions_<date>_<id>/`. Human config/records/docs, original VTC and historical result snapshots remain read-only. No training, uploads, remote jobs or chat dispatch is implied.

Order: E0 inventory/contracts -> E1 observation intake; E2 photon accounting -> E3 optics -> E4 shading objects; E5 schedule/controller; E8 hooks before E6 imported-shape dynamics; E7 biological feedback after its scientific contract. Independent fixture/schema work may proceed while another dependency is missing. Do not stop after a design report when authorized executable work is possible.

GroIMP remains the single authority for runtime growth and carbon. Python owns orchestration/verification and the existing water/element ledger. Preserve one committed state and one clock. A forecast wrapper must not advance a state that the pipeline has already advanced.

## E0 — coverage and versioned extension contracts

Create `handoff/FSP_EIGHT_CAPABILITIES_CONTRACT_2026-10-11.md` before code changes. For each E1–E8 list existing file:function, missing behavior, proposed fields/API, unit/frame/time basis, default-off compatibility behavior and acceptance tests. Reuse existing schemas where compatible; version breaking changes and provide explicit migrations. Unknown values remain null/unavailable with reasons.

Publish three separate statuses: engineering implementation, real-input readiness, scientific/biological validation. Conditional examples may test mechanics without constituting approved biological coefficients. New response laws need Claude's executable scientific decision; the implementer may not choose an arbitrary law to close a gap.

## E1 — real P1 observation intake and declared initialization routes

Extend `audit_p1_package` / `prepare_run` and V3 observation initialization using the actual P1 schema. Add an explicit route selector and readiness result:

1. **Observed metric route:** consume supported current structure and located optical surfaces with physical scale, coordinate frame, organ identity and capture time. Convert declared mm/m exactly once; preserve local/canopy frame provenance. Do not apply canopy placement twice.
2. **Conditional completion route:** consume actual masks/keypoints/structure plus an explicitly selected, versioned P1 completion package and its scale/depth/posture assumptions. Claude P1 supplies geometry; Codex validates/initializes it. Keep observed and generated fields separate. No automatic fallback to synthetic truth, no acceptance as measured 3D.
3. **Observation-only route:** retain valid image-space observations and return exact missing requirements when no supported geometry/completion exists. This is successful intake with unavailable simulation, not a successful physical forecast.

Define a separate hidden-state supplement for initial dry mass, reserves, root state and developmental ages. Unknown hidden state must be measured, sourced or explicitly scenario-assumed, never inferred as measured from shoot photos. Reconcile snapshot time to run start; do not silently extrapolate unmatched capture times. Preserve proposed/confirmed identity states and require an explicit mapping for simulated organs.

Outputs: updated `producer_consumer_map.csv`, `initialization.json`, per-field evidence, `observation_readiness.json`, source hashes and unresolved reasons. Provide real-package intake evidence even if physical execution remains blocked. A genuine real-initialized native run may only be claimed when its prerequisites are supplied.

Acceptance: equivalent mm/m packages initialize identically; image px cannot be cast into metric space; unsupported frame changes fail; conditional geometry stays labelled; real audit contains no fixture-truth substitution; hidden-state assumptions are visible; geometry/ID round trip and native consumption are verified.

## E2 — incident PPFD and complete scene photon accounting

Inspect the actual GroIMP transport API and instrument its path/energy accounting. Do not infer incident light as absorbed/absorptance, which fails for transparent or zero-absorptance surfaces. Export incident and absorbed quantities independently, with front/back convention, area basis and time integration stated.

New outputs: `leaf_light.csv` additions and `scene_photon_budget.csv`, linked to exact geometry/source/optics/interval hashes. Track emitted photons, absorption by leaves, absorption by non-leaf objects, escape, path-termination/truncation or estimator residual categories. Keep internal reflection/transmission transfers separate from terminal sinks. Multiple incidence events are not independent photon sources.

For a declared spectral band and steady transport, reconcile emitted photon flux against terminal sinks plus explicitly accounted numerical residual. If output uses watts, retain a separate radiometric ledger and a spectrum-supported conversion; PAR photon flux is not interchangeable with energy in joules. Name outputs accordingly.

Inspect whether the backend accounts for rejected samples, Russian roulette and bounce cutoffs; do not conceal untracked energy under the word escape. If the API cannot provide closure, implement the necessary instrumentation or retain an explicit unavailable status. A backend limitation must not be bypassed with a fabricated remainder.

Acceptance: empty scene, one absorbing plane, dark scene, leaf/non-leaf split, multiple intersections and sampled escape; report numerical residual and convergence for declared settings. Leaf aggregate checks and whole-scene closure are distinct tests. Physical tolerances must follow sampling evidence rather than an unexplained universal epsilon.

## E3 — leaf transmission and reflection

Add supported per-material or per-face absorptance, reflectance and transmittance, with band, source, cultivar/condition and uncertainty. Validate nonnegative coefficients and their declared normalization. Preserve a legacy black-material mode for regression.

Implement actual reflected/transmitted transport supported by the selected native backend, including explicit scattering/directional assumptions. Do not call straight-through attenuation diffuse scattering. Do not claim wavelength or incidence-angle dependence unless implemented and parameterized. Missing measured leaf optics may be supplied only as a labelled scenario, not a calibrated Micro-Tom default.

Bind P4's exchange model to the correct incident/absorbed basis. Changing optical absorption must not cause the same factor to be applied again inside photosynthesis. Explain how model coefficients fitted on one light basis are handled; unresolved basis conversion blocks that response.

Acceptance: black-mode compatibility; transparent limit; reflecting limit; stacked leaves separating gap light from tissue transmission; reflected contribution to a receiver; photon closure with multiple bounces; face convention and no two-sided area double counting. Export path categories sufficient to support these claims.

## E4 — pots, shelves and other-variety plants as scene objects

Add a versioned scene-object table/manifest with object ID, role, frame/transform, geometry, optical material, evidence and optional source plant. Support pots, shelf boards/posts and non-target plant meshes or explicitly requested conditional proxies.

Non-target plants may cast shadows and absorb/reflect/transmit light without receiving Micro-Tom growth or sharing its carbon pools. Keep them static unless a separately supported dynamic model is explicitly selected. Do not silently exclude a known object or silently invent its dimensions. Reject duplicate object/organ surfaces.

Acceptance: object insertion/removal changes receiver light in controlled cases; object absorption appears in the correct photon-budget category; no non-target biomass/allocation created; native scene hash invalidates when placement/material changes; transforms applied once. Actual shelf dimensions remain assumptions until measured.

## E5 — actual subdaily illumination schedules

Replace duration-only synthetic refinement with timezone-aware, piecewise schedules: on/off boundaries, dimming fraction and source-specific output, environment sample intervals and explicit interpolation rules. Validate gaps, overlap and out-of-range output. Require missing timing information rather than assuming a lights-on clock.

Split native integration at relevant lighting/environment/events and run-end boundaries. Integrate PPFD over actual lit seconds for DLI; calculate respiration over the appropriate full elapsed interval and photosynthesis on the instantaneous/subinterval light basis. Do not infer equal carbon gain from equal DLI under a nonlinear exchange model.

Scale development/maintenance/uptake rates by their declared time units. Preserve seed spin-up age and event ordering. No clock reset at midnight or day-30 display offset. New organs first intercept light according to the selected substep boundary convention, never before birth.

Acceptance: midnight crossing, partial first/last day, off periods, staggered fixtures, dimming and irregular environment timestamps; no duplicate maintenance/thermal age; analytical DLI checks; coarse/refined schedule comparisons and growth convergence evidence. Retain the old daily mode explicitly for compatibility.

## E8 — V3 hooks H1–H3, before imported-shape dynamics

Coordinate public request/registry changes with Claude Code's `microtom_parameters` consumer. Version the native request and report active/inactive parameters truthfully.

### H1: CURVE_RATIO

Extend `vtc_development_io.PARAMS` and native `updateGeometry` to accept reviewed per-segment bend weights. Define order, length relative to the actual rachis segment count, normalization, zero-sum rejection and whether signs are stored in weights or in a separate bend amplitude. No silent truncation/interpolation of [1,2,2] onto arbitrary segment counts. Preserve MTG A2 signs and terminal-segment distinctions. Ratios redistribute a defined bend; they do not supply the missing amplitude/age law.

### H2: BENT_FRACTION

Accept a fraction in [0,1] or unavailable. For scenario-generated compounds, draw once per persistent compound using a stable seeded identity key; retain the draw across replay/substeps. Never redraw each geometry update or replace an observed human bend label. Both posture templates and their amplitudes need explicit definitions. Unknown fraction is not zero. Existing blade-curl and numerical flat/bent classification thresholds remain on hold; this scenario mixture must not invent an observation classifier.

### H3: AREA_CORRECTION

Add an accounting-only output in `vtc_development_observation.derived_tables`: separate uncorrected basis area, correction factor/source, corrected reporting estimate and uncertainty/status. Define exactly which area basis the factor multiplies. Do not overwrite full_outline observations, triangulated surface area, photon interception, photosynthetic area, SLA mass, allocation or geometry. Report unsupported omitted leaflet area without creating fictitious optical surfaces.

Acceptance: H1 variable segment counts and A2 sign checks; H2 deterministic per-organ assignment and preserved observed labels; H3 changes only the declared reporting column. Test parameter serialization, invalid values, inactive flags, consumer compatibility and native consumed geometry. Legacy behavior remains selectable and unchanged when hooks are disabled.

## E6 — growth-dependent shape and angle for imported P1 leaves

Use H1/H2 only within their reviewed meaning. Preserve exact observed initial meshes/posture at initialization. Add stable attachment points, local organ frames and a supported rachis/blade deformation representation. Do not guess a petiole pivot or vertex-to-organ mapping from an unsupported mesh.

Require a scientific contract specifying developmental age dependence, insertion angle, rachis curvature, leaflet orientation, shape/aspect change, parameters and domain. Keep posture, growth and phototropism distinct; light-seeking direction is not implied by developmental bending. Blade curl remains excluded until separately defined.

Apply funded mass-to-size changes and a constrained deformation to imported meshes, maintaining attachment continuity and valid triangles. Rigid rotation must preserve area; non-rigid deformation must recompute true area and reconcile the selected mass/area contract. Bending or observed state correction must not silently generate carbon or photosynthetic area. Imported organs without identifiable anchors retain explicit rigid/scaling-only mode with reason.

Acceptance: exact initial-shape preservation; pivot/parent continuity; known rigid rotation; reviewed deformation with non-inverted/nondegenerate surfaces; area/mass reconciliation; actual native light changes after orientation/shape update beyond sampled noise; disabled-deformation regression. Report supported versus unavailable morphology separately.

## E7 — nutrient demand/availability/actual-growth transaction

This stage requires Claude's executable scientific contract before biological coupling. Obtain exact uptake kinetics, root basis, substrate exchange/hydraulics, tissue demand/storage/remobilization, deficiency/excess responses and carbon-nutrient allocation priority, with units, sources, limits and uncertainty. Implement interface fixtures while waiting; do not supply arbitrary multipliers or identify ions from EC/pH.

Replace the current post-hoc ledger check with a genuine causal handshake:

1. Native V3 proposes organ growth/birth demands and carbon feasibility from committed state, without advancing or spending resources.
2. Python's authoritative root-zone/nutrient model returns element availability and reviewed limits for the same transaction/interval.
3. The reviewed allocation solver selects actual growth within both carbon and nutrient limits, including storage/remobilization semantics.
4. Native geometry and both resource ledgers are reconciled and committed together. Return unused reservations; no double subtraction of uptake and structural incorporation.

Choose and document an actual native pause/resume or equivalent proposal/finalize protocol. The existing `advance_interval` publishes already-produced native checkpoints; it cannot enforce nutrient limits on growth retrospectively. Do not relabel post-run rejection as interactive nutrient-constrained growth.

Bind proposals/responses to transaction ID, predecessor hash, interval, model/parameter hashes and plant IDs. On timeout/stale response/failure publish neither half of the new state. Make retry/finalize idempotent. No transfers between plant pools without an explicit supported shared-root-zone model.

Acceptance: carbon-only limit, nutrient-only limit, joint limit, zero nutrient availability, remobilization when supported, unused allocation, retry/crash recovery, wrong/stale response rejection, water/element/carbon closure and growth/geometry consistency. Feedback-disabled mode must reproduce the prior model. Prescribed-uptake fixtures do not validate predictive uptake. Report this stage pending if its science contract remains absent, even when interface tests pass.

## Final connected acceptance and delivery

Create `handoff/CODEX_FSP_EIGHT_CAPABILITIES_EXECUTION_2026-10-11.md`, API/user-guide updates, a field migration map, exact commands/exits and an acceptance JSON linking every E1–E8 result to frozen artifacts. Update flow entries only to evidence-supported status, preserving separate conditional and real readiness.

Run focused meaningful tests and existing affected regressions. Native evidence must include: observed/conditional initialization routes clearly separated; incident/absorbed outputs and scene photon accounting; transmissive/reflective leaves plus non-leaf occluders; a real piecewise schedule; imported-mesh deformation and subsequent light recomputation; H1–H3 behavior; and joint nutrient transaction only if its reviewed model is available. Keep optical sampling uncertainty and biological uncertainty separate.

Exercise the delivered Claude forecast wrapper against the new version through the single authoritative pipeline and preserve forecast IDs/immutability. Report any unsupported new feature in the wrapper rather than silently falling back to old direct-V3 behavior. Do not issue two independent growth steps for one interval.

Do not claim all eight capabilities complete from interface fixtures, approximate photon residuals, or missing real data. Conversely, finish authorized implementable mechanics instead of returning only another plan. List remaining scientific decisions and measurement gaps precisely. Append LOG with claims, actual changes and verified outcomes.
