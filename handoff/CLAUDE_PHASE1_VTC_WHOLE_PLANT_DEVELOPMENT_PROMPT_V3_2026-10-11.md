# Phase 1 V3: dynamic tomato organ development in GroIMP/VTC

Date: 2026-10-11
Recipient: Claude Code, with Claude responsible for scientific choices. Codex may implement agreed contracts under the current repository permissions.
Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

## Objective

Continue the incomplete Phase-1 V2 implementation until the GroIMP engine generates and grows new tomato stem internodes, compound leaves with individual leaflets, and inflorescences over time. Implement the declared Micro-Tom determinate developmental program, whole-plant carbon allocation and structural feedback to light. Python remains the input adapter, local execution controller, independent checker and result collector.

The existing `phase1_leaflet_subset_v1` is useful verified infrastructure, but it only expands supplied rectangular leaflets. It is not the requested developmental model. Do not mark this task complete by adding more pre-existing rectangles, showing a scheduled animation, or relabelling the subset engine.

This prompt extends `CLAUDE_PHASE1_GROIMP_PYTHON_INTEGRATION_PROMPT_V2_2026-10-11.md` and its unfinished acceptance criteria. Keep the existing mode and regression evidence; introduce a separately versioned developmental mode. Preparing this prompt is not evidence of implementation or biological validation.

## 1. Reconcile current evidence first

Read parent `공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, LOG/TODO, and:

- `handoff/PHASE1_GROIMP_PYTHON_EXECUTION_2026-10-11.md`
- `handoff/PHASE1_VTC_PYTHON_SCIENCE_AND_IO_CONTRACT_2026-10-11.md`
- `handoff/CLAUDE_PHASE1_GROIMP_PYTHON_INTEGRATION_PROMPT_V2_2026-10-11.md`
- `handoff/CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md`, including Addendum A
- `handoff/CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md`
- `handoff/MTG_CONVENTION_2026-10-10.md`, including sections 11 and 12
- Stage-2 structure and Stage-3 forecast specifications, including all owner reconciliations
- `tools/VTC_GROWTH_BRIDGE.md` and the existing bridge, IO, fork and tests

Important updates and corrections:

- MTG A1 is now incorporated by reference and A2 is now actually appended. Do not repeat the obsolete claim that A2 is absent. Read its exact axes, signs, class-qualified insertion angles, two azimuth fields and alpha/theta distinction. Blade curl and flat/bent classification thresholds remain unresolved unless newer evidence resolves them.
- The existing fork directory now exists, but its original VTC sources under `upstream/` are not executed by the bounded mode. A directory named Micro-Tom is not proof of a developmental engine.
- Original VTC leaf/internode dimension curves are not automatically driven by allocated carbon. Inspect `calcDimensions`, `calcAssimilateAllocation`, apex rewriting and `step`/`renew` ordering before reuse.
- The bounded mode stores temperature/CO2 but does not use them in its fixed-coefficient response. Its potential demand is an input fixture, not an age-dependent sink law.

Preserve original `Downloads/vtc-main`, existing results and protected human data/config/docs. Claim shared files in LOG before editing and check other claims. Keep the unlicensed reference copy local and retain attribution; no redistribution or upload. No training, remote rendering or other-chat messages are required.

## 2. Architecture and scientific contract

GroIMP must own developmental events, topology, physiological exchange, reserve accounting, organ allocation, realized growth and geometry. Python may independently recalculate checks but must not apply a second biological update. The old Python P2/P3/P4 engines remain independent diagnostics, not additional state updaters in this run.

Before implementing biological rules, create:
`handoff/VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3_2026-10-11.md`.

Claude must select executable conditional rules using the existing fork/literature contracts and verified reference sources. Record equation/function, units, applicability, cultivar, source, uncertainty, missing-input policy and exact interfaces. Do not invent missing coefficients or use Merlice parameters as measured Micro-Tom values. Clearly labelled synthetic coefficients may test software, but cannot establish a scientific choice or biological accuracy.

The contract must resolve:

1. Chronological age, thermal/developmental age, phyllochron, initiation versus visible emergence, floral transition and determinate termination. Do not confuse fruit-appearance delay with leaf phyllochron.
2. Whether and how carbon availability gates organ initiation, emergence and expansion. Separate a developmental clock from biomass creation. No unsupported claim that every developmental event must stop under carbon limitation.
3. Organ-specific potential growth/sink demand as a function of age/state, realized allocation, growth respiration and mass-to-geometry mapping. Constant fixture demands are not sufficient for this developmental mode.
4. Leaf exchange model, temperature/CO2 response scope, organ maintenance, reserves and starvation handling. If a response is not active, reject claims that changing that input changes the corresponding physiology.
5. Root/shoot/reproductive allocation, non-photosynthetic organ demands, and carbon cost of organ birth. Prevent double counting between a compound aggregate and its component tissues.
6. Main-axis and sympodial continuation representation, pruning/side-shoot assumptions, and how the selected termination rule applies. Do not interpret every new inflorescence as total plant death.
7. Structure initialization from seed and from observed state, including unknown age, hidden tissues, initial mass and reserve assumptions.

No silent copying of the original VTC clipping, reserve reset, gross/net exchange interpretation or date-specific harvest update. Adopt reviewed corrections and expose deficits rather than hiding missing carbon.

## 3. Dynamic organ graph and identity

Represent at least:

- Plant and explicit shoot axes/apices.
- Stem internodes and attachment nodes.
- Compound leaves, petioles/rachis segments, and individual leaflet blades.
- Inflorescence/truss axes and their explicitly modelled flower units.
- A physiological root compartment with mass, demand and respiration. Detailed root geometry is not required.

Do not require fruit set, fruit maturation or yield prediction for this stage; if included, they need their own reviewed rules and tests. Unmodelled processes must be labelled, not represented as zero measured demand.

Generate stable IDs when organs are born. Preserve plant-instance/source identity, parent, axis, true developmental order where known, MTG rank, birth time, developmental stage and provenance. Never renumber surviving organs when another organ appears. Keep true leaf order distinct from the lowest-visible-leaf rank of an observation.

Separate meristem initiation, visible emergence and expansion events. Define events on interval boundaries or substeps so repeated execution cannot create the same organ twice. Export an event ledger with parent, triggering rule, time, reason and associated carbon transaction.

For a funded new organ, transfer its starting structural carbon from an explicit source and include it in the ledger. A zero-mass primordium must not have a finite photosynthetic/occluding blade until the contract funds its emergence. No creation of biomass or leaf area by advancing the calendar alone.

Support variable organ counts throughout the native engine, input schemas, collectors, independent checks and viewer. Do not retain a fixed-length initial-leaf array as the developmental state.

## 4. Micro-Tom architecture and geometry

Adapt the actual VTC apex/rewrite/development routines into the new active mode, or document the exact reviewed replacement and source mapping. Keeping original files inert under `upstream/` does not satisfy reuse of the developmental model.

Deliver an annotated `parametersMicroTom.rgg` or a formally equivalent versioned cultivar parameter module loaded by the engine. Apply the earlier fork contract with all priors labelled:

- Parameterized first reproductive transition and truss cadence; do not silently retain Merlice's every-fourth-phytomer rule.
- Explicit `SP_STOP_RULE` with the earlier proposed two-successive-truss condition treated as a declared conditional rule pending applicability review. Show which apex/axis stops and how existing organs continue growing.
- Internode growth with an evidenced or explicitly hypothetical limit; never present the Merlice limit as a Micro-Tom measurement.
- Rank-dependent leaflet-pair counts; no universal 13-leaflet template and no duplicated rank for separate leaves.
- Petiole and multi-segment rachis with the current A2 bending convention; support the actual number of lateral-pair nodes rather than hardcoding three.
- Explicit per-pair size pattern, including the selected middle-pair ramp; no claim that it is fitted without data.
- Individual planar leaflet polygons with declared length/width/outline assumptions. Do not substitute compound envelopes or black rectangles for the delivered developmental leaf representation.

Keep compound insertion angle and leaflet insertion angle distinct in flat tables. Preserve petiole-base and blade azimuth independently. Growth-related orientation laws may use a reviewed conditional rule; automatic light-seeking orientation is not implied. Blade rugosity/curl is a recorded limitation, not equivalent to rachis bending.

Any intercalary/secondary area correction must state where its area and mass enter accounting. Do not absorb photons on nonexistent tissue or multiply represented geometry and its area by the same correction twice. Unsupported hidden surfaces remain unresolved or explicitly assumed.

All changes in mass-funded dimensions, organ birth and topology must reach the GroIMP graph through managed updates and verified derive/apply boundaries. Preserve the existing fix for non-notifying setter updates.

## 5. Carbon-driven whole-plant growth

At each step, bind environment and light to the correct current geometry, calculate supply and maintenance, evaluate age/state-dependent potential demands, allocate resources, update reserves, realize growth and commit graph changes.

Define exactly when newly initiated/emerged leaves can intercept light and photosynthesize. Avoid one-step lag from original `step`/`renew` ordering and avoid giving an organ light before its geometry exists.

Potential age-based size curves define demand or upper bounds; they must not independently overwrite carbon-funded dimensions. A low-carbon scenario with unsaturated demand must produce lower realized structural growth, even if the developmental clock continues.

Close the ledger over leaves, petioles/rachis, stem, root compartment, reproductive organs and reserves. Separate growth respiration from structural carbon. Export all transfers once, with organ and plant totals that reconcile. New organs, reserve mobilization and any turnover must be included.

Missing initial masses or reserves cannot be inferred from photos as measurements. Use explicit conditional initial-state values with provenance, or return unavailable. Do not silently assign zero maintenance to unimplemented tissues.

Nutrient feedback remains disabled. Do not claim nutrients are measured or non-limiting. Preserve the existing nutrient ledger unchanged.

## 6. Initialization and Python integration

Reuse the existing bridge's input freezing, hashes, actual Java/GroIMP launch, initialization acknowledgement, completion manifest, timeout handling, independent checks and atomic publication. Version schemas for the expanded organ graph; retain the bounded mode's regression behavior.

Provide both routes:

**Seed route:** execute a real climate-driven seed-to-day-30 spin-up. Export the complete trajectory and initialized day-30 state; assigning `age_days=30` is not spin-up. Continue beyond day 30 in the same state without resetting reserves or IDs.

**Observation route:** implement the Stage-2/P1 input adapter for the agreed schema. Import supported topology/geometry and separate any assumed age/mass/reserves/hidden tissues. If a real producer is absent, test the exact contract using a labelled fixture and report real observation execution unavailable. Do not make missing real data block the whole synthetic developmental implementation.

Do not let the original hardcoded harvest-date structure replacement overwrite either route. Distinguish generated biological age, sowing date and observation date. Keep metre/mm and angle/frame conversions explicit; no fabricated board-to-plant transform.

Python commands must select the new developmental mode explicitly. A requested developmental run must fail if only the bounded engine is available; it must not silently fall back. Record the actual active native entrypoint, source hashes, scenario and mode in every manifest.

The viewer must show returned organ birth, stem extension, compound-leaf development, truss appearance and apex termination, with IDs/time/assumption labels. Preserve a displayed distinction between observed starting geometry and model-generated future organs.

## 7. Runtime and outputs

Use the verified local GroIMP/Java runtime and fresh output directories. Keep original sources and existing accepted evidence immutable. Proposed fork version: `build/vtc_microtom_development_v3_20261011/`; choose a fresh suffix if already occupied.

Export configuration/provenance/state metadata as JSON and numerical/event tables as CSV. Required outputs:

- Parameter registry with source/cultivar/units and active scientific contract.
- Dynamic organ inventory, parent/axis mapping, lifecycle/events and apex states.
- Per-organ age, demand, allocated carbon, respiration, structural mass and geometry.
- Per-plant whole-system carbon ledger, reserves, deficits and residuals.
- Leaflet-level light and pre-light consumed geometry for every step.
- Initial, day-30 and subsequent committed graph/geometry states, plus the native returned-state viewer.
- Runtime command/version/exit/logs, completion hashes, replay recipe and validation report.

For definitive development events, run a sufficiently long declared horizon to observe birth, reproductive
transition and the selected stop event. Do not reduce the test to three days if that avoids the requested
development. Synthetic test coefficients may shorten event timing only in a separately labelled fixture;
also run a documented default conditional scenario long enough to reach its declared events, or report
that acceptance item incomplete.

For quantitative light comparisons, follow current sampling guidance (at least 4.8M rays for the named
acceptance comparisons) and retain multiple-seed assessment. That count is not a universal accuracy
guarantee. Cheaper smoke runs must be labelled accordingly. Report the supported time step; do not
claim subdaily convergence if the engine is daily-only.

## 8. Required acceptance evidence

1. **Actual engine:** Python launches the new developmental entrypoint and verifies native completion. No mocked launcher or old subset run counts as this proof.
2. **New leaves:** inventory after initialization contains newly born compounds and leaflet children with unique IDs, correct parents, timestamps, rank rules and evolving geometry.
3. **New stem:** associated new internodes appear and extend through funded growth; connectivity and stem-length versus top-leaf-height definitions remain correct.
4. **New trusses:** the declared floral transition generates a new inflorescence/truss and explicit modelled flower units. A coloured marker or renamed leaf is insufficient.
5. **Determinate stop:** the selected apex rule triggers exactly once, stops only the declared future organ production, and allows existing organs to keep growing when resources are available. No accidental infinite every-fourth-node sequence.
6. **Carbon causality:** paired sufficient/limited scenarios with identical developmental inputs demonstrate different realized mass and dimensions. No age-curve overwrite. Darkness tests distinguish reserve-funded growth from unmet obligations.
7. **Birth conservation:** an independent ledger accounts for structural carbon assigned to every new organ, including roots and reproductive tissues; no free seed mass after initialization or duplicate compound/leaflet mass.
8. **Dynamic optics:** new and enlarged leaves alter the actually consumed native graph and subsequent shading. Use a controlled canopy and a frozen-topology/geometry diagnostic to isolate the effect; preserve separate plant pools.
9. **Compound structure:** verify rank-indexed pair counts, terminal leaflet identity, variable rachis segment count, A2 angle conventions and individual blade meshes; export checks must reject envelopes masquerading as leaflets.
10. **Real spin-up:** execute all 30 initialization days, preserve intermediate carbon/topology states, then continue without reinitialization. Compare uninterrupted continuation with supported checkpoint/replay semantics.
11. **Observation adapter:** round-trip the reviewed Stage-2 contract and identity/frame/units through a labelled fixture; separately list missing inputs preventing actual real-data execution.
12. **Robustness:** duplicate births, orphan IDs, carbon overdrafts, stale geometry, wrong mode, nonfinite dimensions, failed native runs and partial results must fail visibly without publishing a successful state.
13. **Replay and regression:** deterministic replay or stated stochastic tolerances include event times and dynamic topology. Existing bounded-mode and relevant P2/P3/P4/nutrient regressions remain unchanged.
14. **Evidence boundary:** generated organs stay predictions, borrowed parameters stay priors, and independent biological validation remains unestablished. Temperature/CO2 effects are tested only if scientifically specified and active; otherwise the limitation is explicit.

The acceptance report must cite actual native output rows, states and commands, not only boolean checks
written by the same implementation. Independently recompute representative birth/allocation/carbon
cases and verify that tests fail for deliberate errors in those mechanisms.

## 9. Completion and deliverables

Deliver the active developmental fork, Python adapters/collector changes, tests, schema/API documentation,
reproducible runs and `handoff/VTC_WHOLE_PLANT_DEVELOPMENT_EXECUTION_V3_2026-10-11.md`. Append LOG/TODO.
Provide a concise Korean briefing linking the real returned-state viewer and describing what remains.

Use separate statuses for software-scope completion, conditional simulation validity and independent
Micro-Tom accuracy. Do not rewrite historical `full_v2_acceptance=incomplete` manifests; create a new
acceptance report mapping both remaining V2 items and every V3 requirement to evidence.

The delivered architecture is a **conditional whole-plant model with explicit shoot-axis scope**. Root
physiology is represented, but detailed root branching, unrestricted side shoots, fruit maturation,
nutrient stress and leaf-blade curl are not implied. Do not claim a complete natural plant architecture
when only the specified main/sympodial axes are modelled.

Do not declare implementation complete while new leaf, internode or inflorescence generation, funded
growth, the selected termination rule, 30-day spin-up, or dynamic light feedback is missing. Missing real
observations may prevent biological validation without invalidating a properly labelled synthetic
software test. Unresolved scientific rules must be identified precisely; finish independent work but
keep dependent implementation and overall acceptance incomplete rather than replacing the objective
with another bounded-leaflet demo.
