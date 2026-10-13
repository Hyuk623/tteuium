# Integrate P1, P2, P3 and P4 into one traceable tomato FSP workflow

Date: 2026-10-11
Recipient: Claude scientific reviewer and Claude Code implementation owner; Codex implements reviewed contracts within current ownership rules.
Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

## 1. User objective and execution authority

Connect the four projects into one executable workflow, retaining observations, identities, units, uncertainty and provenance across every transition:

```text
P1: photos -> detections/masks -> organ correspondence -> current plant structure
    -> place individual plants in the actual or explicitly assumed canopy
P2: canopy geometry -> leaflet light distribution
P4: light + environment + plant state -> carbon supply/respiration -> resource allocation
P3: funded growth + development -> updated organs, dimensions, directions and topology
    -> update canopy -> P2 next-step light
New photos -> P1 updated observations -> forecast comparison -> reviewed state update
```

Project numbering is not execution order: physiology P4 precedes realized geometry updates P3.

Keep the agreed architecture: Python owns observation processing, package preparation, native execution control, validation and collection. GroIMP/VTC owns the authoritative within-run light, carbon allocation, development and geometry. Existing Python P2/P3/P4 tools remain available as independent diagnostics/baselines; do not calculate and apply the same light, respiration or growth twice.

This is an integration task, not a request to rewrite every subsystem. Continue the V3 developmental work, reuse accepted bridge infrastructure and fix missing adapters. Preserve historical prompts and reports; this document does not claim their requested functions already exist.

## 2. Read current contracts and coordinate

Read parent `공통규약.md`, project `AGENTS.md`, `CONVENTIONS.md`, LOG/TODO and these current documents:

- `CLAUDE_PHASE1_GROIMP_PYTHON_INTEGRATION_PROMPT_V2_2026-10-11.md`
- `PHASE1_GROIMP_PYTHON_EXECUTION_2026-10-11.md`
- `CLAUDE_PHASE1_VTC_WHOLE_PLANT_DEVELOPMENT_PROMPT_V3_2026-10-11.md`
- `CLAUDE_VTC_SCIENCE_PARAMETER_REVIEW_HANDOFF_2026-10-11.md`
- `CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` and `CODEX_FORECAST_SPEC_2026-10-10.md`
- `CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md`
- `MTG_CONVENTION_2026-10-10.md`, including A1/A2 and section13 decisions
- `CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md`
- `CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md`
- `CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_REQUEST_2026-10-06.md`

All filenames above are under `handoff/`. Inspect current source and actual execution artifacts before judging status. At preparation, new `tools/vtc_development*` files existed under an active V3 claim, while `phynotype2/` was not found at its historical path. Locate the current owner/path and reconcile this discrepancy; do not infer completion, deletion intent or authorization to recreate somebody else's work.

Create an integration inventory classifying each feature as executed, implemented-unverified, specification-only, absent or scientifically unresolved. Record exact producer/consumer APIs and schemas. Before editing shared files check claims and append your file claim to LOG. Never overwrite active work. Do not modify human records, protected config/docs or the original downloaded VTC. No training, remote jobs, uploads or messages to other chats are implied by this prompt.

## 3. Scientific contract before new response laws

Claude must resolve scientific choices using the parameter-review handoff; the implementer must not invent missing biology. Write `handoff/FOUR_PROJECT_INTEGRATION_CONTRACT_2026-10-11.md` containing exact interfaces, units, timestep/event ordering, error policies and selected scientific equations.

Explicitly resolve photon/CO2 units, incident versus absorbed light, gross versus net assimilation, respiration ownership, reserve/birth costs, mass-to-area/length relations, developmental events and orientation. A unit mismatch is not repaired by silently scaling a coefficient.

Conditional numerical examples are allowed for software testing, with their assumptions recorded. They must not become measured or fitted Micro-Tom values. Missing real measurements need not block independent synthetic engineering tests, but real execution and biological acceptance remain separate statuses.

## 4. P1: turn actual observations into an explicit current-state package

Reuse existing capture, detection, mask and geometry tools. Inspect model availability and local execution prerequisites; do not call a detector trained or validated because a filename exists. Implement missing glue and contract-bound tracking/structure updates without starting unrelated model training.

Use stable plant-instance/source IDs and organ-parent identities at the axes, compound and leaflet scales. Separate proposed correspondences from confirmed identities. Preserve split/merge, occlusion, disappearance, removal and new-organ evidence; absence in one image is not confirmed removal. Record capture timestamps and LED phase so posture changes are not automatically fitted as growth.

Keep these area concepts separate:

- Visible projected area, with image/pose and px2 or supported physical units.
- Occlusion-completed estimate, with method, assumptions and coverage uncertainty.
- Estimated one-sided lamina surface area, with its distinct geometric evidence.
- Optional green-only/active-tissue area, separate from the user-selected main `full_outline` basis.

Do not convert a bounding box, hull, compound envelope or unlocated area-plus-angle tuple into certified optical tissue. Optical readiness requires supported located leaflet surfaces or an explicitly conditional geometry completion. Unsupported scale/pose/angle stays unavailable. Preserve observed, reconstructed, generated and assumed fields individually.

Follow MTG A2 angle references and separate petiole-base/blade azimuths and compound/leaflet insertion angles. Blade curl and numerical flat/bent thresholds are on hold; do not invent them. Do not reintroduce compulsory board capture where the user selected board-free operation.

Export the agreed Stage-2 current-state schema plus optical-surface and identity manifests. If a producer is incomplete, implement the adapter and test fixtures, but report that the actual photo-to-state segment remains incomplete until a real package runs through it.

## 5. Canopy merge, light and per-plant separation

Maintain one explicit rigid transform per plant instance from plant-local to canopy coordinates. Merge for transport without losing organ identity; split outputs back by the original instance/organ mapping. Test round-trip transforms and duplicate source plants placed as distinct instances.

GroIMP evaluates the full scene, including inter-plant shading and supported optical properties. Native surfaces must expose stable external leaflet IDs and area/face conventions. Export per-leaflet incident/absorbed quantities, per-plant aggregates and canopy summaries, each bound to geometry version and time interval.

Use frozen lamp geometry/emission/schedule and measured or explicitly assumed optics. Relative phone ratios describe spatial variation, not absolute PPFD. Absolute lamp power or reference PPFD/DLI must have independent measurement or explicit scenario provenance. Freeze measurement-pointer targets and normalization metadata per run.

Do not multiply measured spatial ratios into already calibrated or ray-traced leaf light twice. A Python P2 comparison remains a separate engine result with its own assumptions. Report sampling uncertainty and use the current quantitative-run settings without claiming a universal accuracy bound.

## 6. P4: resource supply, physiological state and allocation

Use native GroIMP per-leaflet exchange with the selected physiological model. Bind every environmental interval to the same plant state and clock. Temperature/CO2 columns are not response models: wire supported responses explicitly or mark them inactive. Do not claim their effects from a fixed-coefficient NRH run.

Include leaves, petioles/rachis, stem, roots as a physiological compartment, reproductive structures and reserves in the whole-plant carbon account. Charge maintenance and growth respiration exactly once. Select age/stage-dependent potential demand and allocate within each plant. No carbon sharing between neighboring plants.

Birth mass, stored-carbon use and any loss/export must appear in the ledger. Insufficient carbon cannot yield uncharged tissue. Return explicit deficits or the scientifically selected starvation response; never conceal failure through clipping or reserve reset.

### Water and nutrients: connect the ledger without inventing growth effects

Python's existing two-layer substrate module remains authoritative for water/element bookkeeping. Bind fertilizer treatment, irrigation, drainage, layer state, uptake and plant nutrient stocks to the same plant IDs and intervals. Preserve current evidence labels: prescribed uptake is not predicted uptake, and EC/pH does not identify N/P/K concentration.

The accepted first carbon integration has `nutrient_feedback_enabled=false`. Include synchronized nutrient-ledger outputs in the orchestration, clearly labelled diagnostic-only when no reviewed biological response exists. Do not imply this completes nutrient-driven growth.

Keep a separate explicit second milestone for reviewed uptake kinetics, nutrient demand/availability and carbon-plus-nutrient constrained growth. Before enabling it, Claude must supply the existing requested scientific contract and define a two-pass exchange:

1. GroIMP produces proposed organ demand and carbon feasibility without committing growth.
2. The nutrient authority returns availability/constraints under the reviewed model.
3. GroIMP determines the funded final growth; Python validates one jointly committed carbon/nutrient/water state.

No hardcoded universal nutrient multiplier or unsupported repeated deficit deduction. If that contract is missing, complete the carbon-connected workflow and ledger integration but label nutrient-growth coupling pending; never mark the full nutrient-responsive objective achieved.

## 7. P3: dynamic development and updated optical geometry

Continue the V3 development requirements: new internodes, compounds, individual leaflets and inflorescences, funded size changes, stable birth IDs and the reviewed Micro-Tom apex termination rule. Existing organs may continue growing after the specified apex stops. Respect declared main/sympodial axis scope; do not imply unobserved side branches or fruit maturation are modelled.

Age curves define potential demand/envelopes, not an independent overwrite of carbon-funded dimensions. New optical area must have a documented mass/geometry basis. Generate actual leaflet polygons and graph-managed updates, not a compound envelope or an unrelated viewer animation.

Direction updates use only selected, sourced developmental rules or explicit scenarios. Distinguish insertion angle, rachis bending and blade orientation. Do not advertise automatic phototropism merely because light affects size. Excluded nutrient-driven orientation remains excluded.

Export the committed graph and consumed-geometry evidence. The next P2 evaluation must use the new graph, not a cached initial light series. Atomic per-interval publication must include time, topology, masses, reserves, geometry and all active resource ledgers.

## 8. New observation updates and reproducibility

When later photos arrive, first compare their independently produced P1 observations with forecasts at matching times and definitions. Do not use the prediction itself as evidence that an occluded organ was observed.

State correction requires a declared assimilation/reinitialization policy. A measured area replacement cannot silently create/remove structural mass or reserves. Record the correction, model-state discontinuity and uncertainty in a separate assimilation ledger; physical process conservation and observation corrections are different accounts.

Freeze input snapshots and maintain time-ordered calibration/evaluation separation. Reusing a later observation to correct a trajectory invalidates any claim that the corrected segment was an untouched forecast. Preserve original forecasts and support deterministic replay or declared stochastic tolerances.

## 9. Implementation and deliverables

Use one Python entrypoint, preferably `tools/tomato_fsp_pipeline.py` or an existing equivalent, with documented operations for inventory/audit, prepare, run, collect, compare-observation and replay. Finalize exact functions and schemas in the contract rather than assuming these commands exist.

One fresh run package under `build/` must contain source photos/references, P1 observation provenance, current organ state, canopy placement, native engine request, per-leaflet light, physiological/resource ledgers, development events, returned geometry, per-plant outputs, manifests and a returned-state viewer. CSV is for tables; JSON is for settings/state metadata/provenance. Do not duplicate raw photos unnecessarily; immutable references and hashes may be used.

Provide an English guide and `handoff/FOUR_PROJECT_INTEGRATION_EXECUTION_2026-10-11.md`. Include a producer-to-consumer mapping for every field, actual commands/exits, schema versions and stage-specific unavailable reasons. A user should be able to see which input is missing rather than receiving a plausible fabricated number.

## 10. Required acceptance evidence

1. Real-data audit: process an available photo package through all supported P1 operations; report exact missing dependencies and unavailable outputs without synthetic substitution.
2. Engineering end-to-end run: use a fully declared synthetic or conditional package through the actual P1-state adapter, canopy transforms, native light, physiology, development and collection. Label any fixture boundary explicitly; a fixture cannot prove photo reconstruction.
3. Merge/split identity: verify transform round trips, stable organ attribution, duplicate-instance separation and per-plant/canopy totals.
4. Inter-plant shading: demonstrate a controlled change in a lower leaflet's light from another plant, without cross-plant reserve transfer.
5. Carbon and birth: independently recompute full-system closure and prove that new organs and growth consume resources exactly once.
6. Development: demonstrate new leaves, internodes, trusses and the selected apex stop with actual native event/geometry output, over a sufficient horizon; retain the V3 spin-up checks.
7. Feedback: prove that later light consumes updated geometry and differs from a frozen-geometry diagnostic beyond declared numerical noise.
8. Input causality: supported light/environment changes affect only the selected response paths; recorded-only temperature/CO2 must not be presented as active mechanisms.
9. Nutrient ledger: prove ID/time linkage and water/element conservation; disabled feedback must not change carbon-only growth. Enabling biological nutrient feedback requires separate demand/availability/joint-commit tests.
10. Observation comparison: a later observed package can be compared without leakage or forced identity; any state correction is logged separately from physical growth.
11. Failure handling: wrong IDs/frames/times/units, missing science, stale outputs, partial execution and engine failure cannot publish success. No fallback from developmental mode to the bounded subset.
12. Regression/replay: existing supported tools remain usable, snapshots reproduce results within stated tolerances, and modified science/version hashes invalidate stale caches.

Report completion separately for observation reconstruction, interfaces, conditional carbon-development loop, nutrient-ledger integration, nutrient-growth coupling and independent biological validation. Do not claim four-project real-data forecasting is complete from synthetic engine tests alone. Work through missing authorized adapters rather than delivering another disconnected demonstration, while keeping unresolved science and actual-data gaps explicit.

---

## Amendment S1 — user-assigned implementers and staged execution (2026-10-11)

**Read this amendment before executing the historical sections above.** The user now explicitly assigns **P1 implementation to Claude Code** and **the downstream adapter, runtime canopy, P2/P4/P3 and feedback implementation to Codex**. This amendment supersedes the opening recipient and any earlier wording that asks either implementer to build all four projects. Original scientific constraints and acceptance requirements remain unless explicitly clarified below. This is a prompt revision, not an implementation-completion report.

### S1.1 Ownership boundary

| Work | Implementation owner | Handoff boundary |
| --- | --- | --- |
| P1 ingestion, masks, correspondence, current structure, local surfaces | Claude Code | Versioned P1 state package with per-field evidence/readiness |
| P1 placement metadata | Claude Code | `canopy_placement.json`, measured or explicitly assumed; no native light execution |
| P1 package validation/native initialization | Codex | Read-only consumer adapter; never replace Claude's tracker or reconstruction |
| Runtime canopy assembly and result separation | Codex | Apply local-to-canopy transforms once, retain plant/organ/surface IDs |
| P2, P4, P3 native calculations and repeated feedback | Codex | Reuse coordinated GroIMP/VTC work; Python orchestrates and verifies |
| New biological equations/coefficient review | Claude scientific reviewer | Executable scientific contract; conditional fixtures are not validation |

This role assignment does not authorize simultaneous edits to claimed files or changes to protected human inputs. Check current claims and execution reports. A later LOG reports a 65-day V3 trajectory, so the earlier preparation snapshot must not be treated as the latest implementation status without inspection.

### S1.2 Prompt for the Claude P1 implementation chat

Implement P1 using `handoff/CLAUDE_CODE_CLI_PROMPT_P1_PHOTO_GEOMETRY_2026-10-11.md`. Keep its work orders, real-versus-fixture separation, MTG definitions and output schema. Deliver local optical surfaces, identity/state/area manifests and placement metadata for Codex to consume. Do not implement or edit the downstream native P2/P4/P3 engines for this task.

Freeze a versioned producer-to-consumer field map and supply at least one validated synthetic multi-plant package plus an honest real-data readiness audit. Preserve per-field unavailable reasons and distinguish observed, reconstructed and generated geometry. Report the actual export command and outputs. A schema dry-read is enough at the P1 boundary; do not claim downstream light/growth execution from it.

Resolve interface discrepancies through an explicit contract amendment and matching adapter tests rather than silently renaming fields. Later photos remain P1's responsibility; publish a new immutable observation package rather than modifying a forecast state. Codex performs comparison and any separately contracted state assimilation.

### S1.3 Prompts for the Codex implementation chat

Use the complete staged work orders in [CODEX_P2_P4_P3_STAGED_INTEGRATION_PROMPT_2026-10-11.md](CODEX_P2_P4_P3_STAGED_INTEGRATION_PROMPT_2026-10-11.md). Give the common instructions together with the desired stage, or execute the whole document sequentially. Each stage names inputs, outputs, functions and a gate:

| Stage | Work | Required gate before dependent work |
| --- | --- | --- |
| 0 | P1 contract audit and native initialization | Exact schema/units/IDs/evidence map; fixtures and real readiness separated |
| 1 | Assemble canopy and preserve per-plant separation | Transform round trip, area invariance, duplicate-instance isolation |
| 2 | P2 on frozen geometry | Actual native light, shading/transmission tests, quantity/unit and geometry binding |
| 3 | P4 physiology and provisional allocation | Whole-plant carbon closure, respiration once, no uncharged birth or inter-plant carbon transfer |
| 4 | P3 funded growth/direction and candidate geometry | Stable IDs, actual topology/events, funded dimensions and reconciled costs |
| 5 | Atomic commit and P2 on the new canopy | Native consumed-geometry proof, multi-step feedback, no stale cache or double clock advance |
| 6 | Nutrient ledger and later P1 comparison | Synchronized accounting, feedback-disabled equivalence, separate assimilation ledger |
| 7 | Connected delivery | Actual end-to-end run, failure/replay evidence and separate biological-validation status |

The gate order controls dependencies, not a requirement to wait for a user confirmation after each stage. Independent adapter/fixture work may proceed while real P1 inputs are incomplete. Never relabel that as a completed real-data path.

### S1.4 Mandatory temporal and resource ordering

```text
Claude P1 package at t
  -> Codex validation + explicit physiological initialization
  -> canopy G_t (local-to-world applied once)
  -> P2 light over [t, t+dt) using G_t
  -> provisional development demand (no committed organ creation)
  -> P4 supply, respiration and funded allocation
  -> P3 realized growth/direction and candidate G_next
  -> reconcile costs + validate + commit S_next once
  -> canopy G_next -> P2 for the next interval -> repeat
```

P3 must provide potential developmental demand to P4 before realized P3 growth; this is not a second growth pass. Use the same interval and committed starting state throughout. Do not reset reserves or replay time when entering a new logical stage. An interval-frozen geometry scheme must be declared and checked with timestep refinement. Within-interval development requires explicitly supported substeps; newborn tissue cannot photosynthesize retroactively.

Bind light to exact consumed native geometry, topology, placement, optics, source schedule and model versions. Publish ledgers and geometry atomically. Failure leaves the previous valid checkpoint intact. Replaying or resuming may not deduct respiration, nutrients or birth costs a second time. A newly observed area correction belongs to a separate assimilation account and invalidates subsequent cached light.

Keep nutrient growth feedback disabled until its reviewed scientific contract exists, while synchronizing the existing ledger. Preserve the exclusions on unreviewed phototropism and fertilizer-driven direction. Software gates establish a working conditional loop; independent observations are still needed for biological accuracy.

## Amendment S2 — Micro-Tom fork remainder and Stage-3 forecast assigned to Claude Code (2026-10-11)

The user explicitly assigns implementation of the Micro-Tom fork specification and Stage-3 forecast specification to Claude Code. Execute `handoff/CLAUDE_CODE_CLI_PROMPT_MICROTOM_FORK_FORECAST_IMPL_2026-10-11.md` for this scope. This supersedes S1 only where its broad P3 ownership wording would assign that remainder/forecast layer to Codex.

Claude Code owns the coverage audit, remaining Micro-Tom parameter/environment adapters, forecast namespace, ensemble runner, immutable forecast outputs and evaluation layer. Reuse delivered V3 behavior; do not create a second native growth engine. Codex continues the already claimed native boundary/checkpoint work and the P1 consumer -> canopy -> P2 -> P4 -> P3 -> relight integration. Native P3 realizes growth once; Claude's forecast layer invokes the engine/pipeline and packages predictions, without applying another growth or allocation update. Missing native hooks require an exact field/function request and coordinated file handoff; this assignment does not release active file claims.

Before executing the companion prompt, reconcile its API names against actual code and the forecast specification. Use the supported public baseline dispatcher rather than assuming private/direct baseline functions are callable. Preserve the existing forecast horizon/domain gates. Unknown coefficients/uncertainty remain unavailable, not numeric zero or invented distributions. Distinguish scenario ensemble spread from calibrated predictive probability; preserve parameter dependencies. Derive DLI and thermal time from the declared schedule/model, rather than fixing a coefficient for every photoperiod. Inspect source-kind vocabulary and parameter-registry format at the actual engine boundary, and map them explicitly. Do not mark a setting as active merely because an override file contains it.

Report implementation completion separately from conditional native execution and biological validation. Do not dispatch another chat automatically. This amendment records assignment and instructions, not completed implementation.
