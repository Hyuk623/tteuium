# Implement the downstream FSP loop in gated stages

Date: 2026-10-11
Recipient: Codex implementation owner
Project: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`
Companion: `handoff/CLAUDE_P1_P2_P3_P4_END_TO_END_INTEGRATION_PROMPT_2026-10-11.md`, amendment S1.

## Shared instructions for every stage

The user assigns P1 implementation to Claude Code. Codex implements the P1 consumer adapter, runtime canopy assembly, P2 light, P4 physiology/allocation, P3 growth/direction and the feedback controller. Claude retains scientific review of new biological laws. This allocation supersedes older instructions asking Codex to implement P1 tracking or reconstruction for this integration.

Claude's producer work order is `handoff/CLAUDE_CODE_CLI_PROMPT_P1_PHOTO_GEOMETRY_2026-10-11.md`. Read its actual execution report and exported schema when available; a prompt is not a delivered package. P1 supplies local geometry and placement metadata; Codex materializes the runtime canopy. Do not apply the placement twice or build a second tracker.

Read `../공통규약.md`, `AGENTS.md`, `CONVENTIONS.md`, LOG/TODO, MTG sections 11–13, the integration prompt and `CLAUDE_FOUR_PROJECT_SCIENCE_EQUATION_PARAMETER_REVIEW_2026-10-11.md`. Check active V3 claims and delivered native artifacts before editing. The current LOG reports a 65-day native trajectory; independently inspect its report before treating any V3 feature as accepted. Reuse that work instead of rebuilding the bounded demo. Claim shared files before editing; do not overwrite another active owner's changes. Keep human config/records/docs and the original VTC read-only.

Python orchestrates and validates. GroIMP/VTC is the single runtime authority for light, carbon, development and geometric state. Existing Python calculations are separate diagnostics. The Python substrate ledger is the single water/element bookkeeping authority. No duplicate physiological calculations may update the same state.

Proceed in stages 0–7. Passing a software gate allows the next dependent stage without repeated user confirmation. Missing real inputs permit explicitly labelled fixtures for independent engineering work, never a claim of real reconstruction or biological validation. Do not invent a missing response law. Continue independent work and record the exact blocked capability. Do not train models, dispatch chats or start remote work.

Suggested implementation homes are `tools/tomato_fsp_pipeline.py`, `tools/tomato_fsp_io.py`, `tools/tomato_fsp_canopy.py` and `tools/tests/test_tomato_fsp_pipeline.py`; reuse existing equivalents and document exact file:function mappings. Native changes belong in the coordinated V3 fork. Names below specify callable responsibilities, not a demand for duplicate implementations. Generated artifacts go into a fresh `build/fsp_integration_<date>_<id>/`.

## Stage 0 prompt — freeze the producer/consumer contract

Implement inventory and boundary validation before the downstream physics.

Read the Claude-produced P1 package read-only. Expect the producer's existing names: `captures.csv`, identity manifest, `mtg_vertices.csv`, `areas.csv`, `optical_surface_manifest.csv`, located optical surfaces, `canopy_placement.json` and `p1_manifest.json`. Confirm exact names from the producer and write a field map rather than guessing. Map the existing Stage-2 current state to native initialization without converting unknown root mass, reserves or age into measured quantities.

Implement `audit_p1_package(package_path)` and `prepare_run(p1_package, scenario, output_dir)` in the pipeline/IO modules. Export `contract.json`, `producer_consumer_map.csv`, immutable input hashes and `initialization.json`. Existing schema names may differ; the map must specify the conversion and tests.

Required normalized fields:

| Group | Required meaning |
| --- | --- |
| Identity | run_id, plant_instance_id, source_plant_id, axis/organ/parent IDs, organ class and birth/removal state |
| Time | state_time, interval_start, interval_end, timezone, duration_s, step_id |
| Geometry | geometry_version/hash, topology_hash, frame_id, length_unit, surface IDs, vertex/face representation, one-sided area basis and optical readiness |
| Evidence | source/package hashes, measured/reconstructed/generated/assumed status, uncertainty or explicit unknown, unavailable reason |
| Biology | dry mass by organ, mobile carbon, developmental age and initial hidden compartments, each with units and provenance |
| Models | schema, code, parameter and scientific-contract versions/hashes; response activation flags |

Use mm at the P1 boundary and explicit mm-to-m conversion in the native adapter. Keep projected, completed and one-sided surface area separate. Preserve full_outline as the user's main area basis; optional active/green area is a separate physiological input. Keep MTG angle signs and classes. A generic normal does not certify botanical face.

Gate 0: malformed IDs, unknown schema, missing scale, incompatible frames, unsupported optical surfaces or missing physiological initialization yield specific unavailable/errors. A conditional run may use separately declared assumptions. Real-mode readiness and fixture-mode readiness must be separate. Test one genuine P1-schema fixture through the adapter and audit available real inputs without substitution. Deliver `stage_0_contract_report.json` with exact mappings and stage status.

## Stage 1 prompt — assemble and split the canopy correctly

Implement `assemble_canopy(local_states, placement)` and `split_by_instance(scene_outputs, identity_map)` in the canopy adapter.

Consume only validated P1-local surfaces and explicit placement. Claude owns the placement metadata producer; Codex validates and applies it. For a rigid transform, use `x_canopy=R*x_local+t`, `n_canopy=R*n_local`; convert length units exactly once. Reject non-rigid transforms unless an explicitly reviewed schema supports them. Keep normals normalized and winding consistent. Preserve one-sided area under rigid placement.

Output `canopy_state_t.json`, geometry tables, `surface_identity_map.csv` and placement/source hashes. Each instance of the same source plant gets distinct runtime IDs. Native geometry remains associated with its original plant, organ and surface. Include all declared shading objects with provenance; report missing neighbors/proxies explicitly.

Gate 1: round-trip position/normal checks; area invariance; duplicate-instance isolation; exact per-plant membership after merge/split; no lost or duplicated triangles. Test at least three plant instances including a duplicate source. Do not multiply an app_ratio into physical ray results during placement. Deliver `stage_1_canopy_report.json`.

## Stage 2 prompt — calculate P2 light on a frozen canopy

Implement `evaluate_light(canopy_state, environment_interval, optical_parameters)` through the actual native backend. Start with fixed geometry so transport can be validated independently of growth.

Consume the full canopy, lamp geometry/emission/schedule, tissue optics and interval. Export `leaf_light.csv`, `plant_light.csv`, `canopy_light.json` and `consumed_geometry.json`. Bind every record to run, interval, instance, organ, surface, geometry hash, lamp/optics hashes and engine configuration.

Distinguish incident PPFD, absorbed PPFD and absorbed photon flux, with explicit one-sided area and face aggregation. If the engine does not expose a requested quantity, mark it unavailable rather than deriving it with an unsupported absorption assumption. Integrate light subintervals when schedules change. Do not silently treat DLI as PPFD. Relative phone ratios cannot establish absolute carbon supply; absolute light may be a labelled scenario assumption.

Gate 2: demonstrate controlled inter-plant shading, orientation sensitivity and downstream transmission when supported. Separate light through gaps from light transmitted through tissue. Check absorption accounting under the selected backend; do not count interception as absorption. Measure ray/seed convergence for tested scenes. Verify leaf-to-plant sums without duplicate faces, consistent no-source results and zero growth in this frozen stage. Deliver `stage_2_light_report.json`.

## Stage 3 prompt — calculate P4 supply and provisional allocation

Implement `propose_resources(state_t, light_t, environment_interval, development_demand)` in the native model, with independent Python ledger verification. P3's development rules may propose organ demand before P4 allocation, but must not create committed organs at this point.

Choose the currently reviewed exchange model and parameter registry. Preserve incident/absorbed light basis, gC versus gDM, gross/net conventions and the declared active tissue fraction. Temperature/CO2 inputs only affect results when an implemented supported response is enabled. Report inactive paths explicitly.

Compute carbon exchange, maintenance, reserve availability, potential demands and funded allocations by plant, including non-leaf pools and proposed birth costs. Do not transfer carbon between neighbors. Include all structural pools once; compound and leaflet totals must not duplicate biomass. In dark/deficit cases record the selected failure or starvation behavior without hidden reserve resets.

Output a provisional `resource_proposal.json`, `carbon_ledger.csv`, `organ_allocations.csv` and deficit diagnostics. A proposal is not a committed time step. Any residual/unrealized allocation must return to reserves or be handled by the reviewed ledger, never disappear.

Gate 3: independent unit/carbon closure tests, dark and limited-supply cases, nonnegative feasible stocks, no duplicate respiration, no free birth biomass and no cross-plant transfer. Keep geometry_t unchanged. Missing required science blocks the affected real response, not unrelated ledger tests. Deliver `stage_3_resources_report.json`.

## Stage 4 prompt — realize P3 growth and produce a candidate next state

Implement `realize_growth(state_t, resource_proposal, development_plan)` in GroIMP/VTC. Reuse the active V3 implementation and its exact contracts after coordination.

Apply resource-funded mass changes and reviewed mass-to-dimension relations. Age curves provide potential demand/envelopes, not a second growth update. Include new internodes, compounds, individual leaflets and inflorescences under the selected axis/apex rules; retain the V3 long-horizon/spin-up requirements. Do not claim unimplemented side branching, fruit set or yield.

Produce actual graph-managed optical geometry. Preserve existing IDs and allocate stable new IDs with birth timestamps and parents. Preserve botanical angle definitions. Developmental direction changes are not automatic phototropism; nutrient-driven direction remains excluded. Do not substitute a viewer animation for the model state.

Export `candidate_state_next.json`, `development_events.csv`, `geometry_next` tables and a reconciled final allocation ledger. Update local plant geometry and apply canopy placement exactly once. Do not feed world-space coordinates back through the same placement as if they were local.

Gate 4: actual births and growing organs have funded mass, compatible geometry and valid topology; stopped apices obey the selected rules; unchanged organs retain identities. No negative stocks, duplicate allocation or uncharged optical area. Candidate state and ledgers agree before publication. Demonstrate native event output, not only screenshots. Deliver `stage_4_growth_report.json`.

## Stage 5 prompt — commit once and recalculate light from the new geometry

Implement `advance_interval(committed_state, interval_inputs)` and `commit_step(candidate, ledgers)` in the orchestrator. The stage separation is logical: do not launch independent native runs that each reset internal reserves or advance the developmental clock again.

Use this explicit sequence:

```text
1. Freeze S_t, G_t, environment [t,t+dt), model hashes and placement.
2. P2 evaluates G_t for that interval (with declared illumination substeps).
3. Development proposes demands/events without committing them.
4. P4 calculates supply and funded allocations.
5. P3 realizes a candidate S_next/G_next and reconciles actual costs.
6. Validate all ledgers/IDs/times/geometry; atomically publish S_next.
7. Reassemble canopy from G_next; P2 evaluates it for the next interval.
```

Default numerical coupling is an explicitly recorded frozen-geometry interval, conditional on the model contract. Do not silently present this as continuous growth. New tissue is charged at realization and first intercepts light at its defined next interval; no retroactive photosynthesis. If the adopted native model uses within-interval births/growth, expose reviewed substeps and recalculate light at those boundaries instead. Compare timestep refinement on representative cases.

Cache keys must bind geometry content/topology, placement, lights, optics, time schedule, backend version, parameters and stochastic settings. Do not reuse initial light after growth. Export native consumed-geometry evidence, not just a Python filename pointing at new geometry.

Gate 5: run at least three successive native intervals; prove input/output hash lineage, exactly one state advance and no same-interval carbon double credit. Compare dynamic against frozen geometry with matched random seeds/settings; a controlled shading change must exceed measured numerical noise. On failure retain the last valid checkpoint and publish a failed attempt separately. Replay/resume must not charge birth or respiration twice. Deliver `stage_5_feedback_report.json`.

## Stage 6 prompt — synchronize nutrients and later observations without altering their meaning

Attach the existing Python water/element ledger by plant ID and interval. Default `nutrient_feedback_enabled=false`; prescribed uptake remains prescribed. Water/nutrient totals, irrigation/drainage and state hashes belong to the same committed checkpoint. A failure of an enabled required ledger prevents a complete step commit.

Growth coupling is a separate milestone requiring Claude's executable nutrient contract. Only then use proposal -> availability -> actual joint allocation -> one carbon/nutrient commit. Do not subtract potential uptake/growth before actual allocation or penalize a deficiency twice. EC/pH and photos do not establish elemental uptake.

Implement `compare_observation(forecast_snapshot, new_p1_package)` read-only. Claude produces later P1 packages; Codex does not redo tracking. Compare aligned times, identities, area bases and units. Preserve the untouched forecast. Any accepted correction uses a separate assimilation ledger/checkpoint and invalidates downstream caches; it is not physiological growth or a silent source of carbon.

Gate 6: water/element conservation, ID/time matching, disabled-feedback equivalence, clear separation of diagnostic and growth-enabled modes, comparison without future leakage, explicit handling of uncertain identities and missing observations. Deliver `stage_6_extensions_report.json`.

## Stage 7 prompt — deliver the connected workflow and state its limits

Provide one CLI with documented `inventory`, `prepare`, `run`, `collect`, `compare-observation` and `replay` responsibilities, mapped to actual commands. Publish `handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md`, an English user guide and `acceptance.json` with all stage results, input/code/schema hashes, actual command exits and output paths.

Demonstrate one Claude-compatible P1 package through canopy -> native P2 -> P4 -> P3 -> new-canopy P2. Keep a real-data readiness audit alongside a separately labelled conditional/fixture run. Preserve V3 long-horizon organ development evidence as well as short integration checks. Include failure tests for wrong units/IDs/frames, stale light, partial native output, schema mismatch and restart double charging. Tests must exercise actual producer/consumer boundaries, not only handwritten matching fixtures.

Report separately: P1 producer delivery (Claude), consumer compatibility, canopy/optics, carbon/allocation, development/direction, closed-loop execution, nutrient bookkeeping, nutrient-growth feedback and independent biological validation. Do not declare real plant prediction validated from software tests. Update LOG with completed files, checks and outstanding inputs. This prompt authorizes implementation when given to the implementation chat; creation of this document itself does not execute it.

## Ownership update S2 (2026-10-11)

The user assigns the Micro-Tom fork remainder and Stage-3 forecast specification implementation to Claude Code, using `handoff/CLAUDE_CODE_CLI_PROMPT_MICROTOM_FORK_FORECAST_IMPL_2026-10-11.md`. See amendment S2 in the master integration prompt for precedence and contract-reconciliation requirements. Codex retains the actively claimed native boundary/checkpoint and connected runtime loop. Stage 4 here integrates/reuses native funded development; it does not authorize a duplicate Micro-Tom forecast layer. Claude's forecast/evaluation wrapper must invoke the single engine/pipeline authority without advancing the same state twice. Coordinate missing hooks and claimed files through LOG.
