# Phase 1 V2: GroIMP/VTC growth engine with Python integration

Date: 2026-10-11
Recipient: Claude Code, with Claude responsible for scientific choices; Codex may implement the agreed Python interfaces within current repository rules.
Project: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`
Reference model: `C:/Users/sho36/Downloads/vtc-main/vtc-main/tomatoFSPM_basic_isP`

## 1. Objective and supersession

Implement the first conditional carbon-driven FSP loop using **GroIMP/VTC as the single authoritative light and growth engine**, and **Python as the observation adapter, run controller, validator and results collector**.

```text
Python: observed or explicitly synthetic initial plant state + scenario inputs
    -> versioned input package + stable identity mapping
GroIMP/VTC fork:
    current leaflet geometry -> light -> photosynthesis/respiration
    -> source/sink allocation -> realized organ growth -> new leaflet geometry
    -> next-step light recomputation
Python: collect committed state, verify units/identities/carbon ledger,
        compare observations/scenarios and display the returned trajectory
```

This supersedes the Python-owned allocation and growth-loop architecture in
`handoff/CLAUDE_PHASE1_CARBON_GROWTH_LOOP_PROMPT_2026-10-11.md` for Phase 1.
Do not build a second Python allocation engine or drive growth with the existing Python P3 forecasts.
Keep the old prompt and existing Python tools intact as historical/reference material.

This also extends the earlier VTC fork prompt: its structural adaptation remains the starting scope,
but its manual-run-only restriction and prohibition on Python bridge work are superseded for this task.
Python must actually launch and collect a verified local GroIMP run. A manual guide is supplementary.
Do not modify historical specifications in place; record necessary changes as new contracts/addenda.

The four project roles remain useful: P1 supplies observations; the VTC backend performs Phase-1 P2/P3/P4
simulation functions; existing Python P2/P4 remain optional independent diagnostics. A comparison result
must not feed the same running plant a second light, respiration or growth update.

## 2. Inspect current state and coordinate edits

Read the parent `공통규약.md`, `AGENTS.md`, `CONVENTIONS.md`, current LOG/TODO and:

- `handoff/CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md`, including the Sarlikioti addendum.
- `handoff/CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md`, including Addendum A.
- Stage-2 `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` and Stage-3 `handoff/CODEX_FORECAST_SPEC_2026-10-10.md`, including owner reconciliations after Amendment L1.
- `handoff/MTG_CONVENTION_2026-10-10.md` and any actually existing amendments.
- `handoff/CROSS_STAGE_ISSUES_2026-10-11_KO.md`.
- `tools/FSP_CARBON_DIAGNOSTIC.md`, `tools/FSP_NUTRIENTS.md`.

Recheck files before asserting completion: A2, `tools/phyllotaxis_fit.py`, the Micro-Tom fork and its light
files were planned rather than present when V2 was prepared. Do not treat L1's present-tense wording as
proof that they exist. Missing angle definitions remain unresolved except where a current authoritative
contract actually defines them. Do not claim leaflet blade tilt is defined solely by rachis bending.

Inspect `main.rgg`, `updates.rgg`, `rewrites.rgg`, `modules_base.rgg`, `modules_organs.rgg`,
`modules_light.rgg`, `photosynthesis.rgg`, `parameters.rgg` and `parametersMerlice.rgg` in the reference.
Inspect existing launchers, particularly `tools/groimp_light_sanity.py::run_groimp` and
`tools/hierarchical_light_native.py`, before implementing another process controller.

Never edit the original download, `config/`, `data/records/` or `docs/`. Claim shared code files in LOG
before editing; append outcomes afterward. Do not overwrite another agent's work. Create a new execution
brief in handoff before implementation. No training, remote rendering, uploads or cross-chat messaging
are part of this task. Check applicable model-code licensing before copying/redistributing it, preserve
attribution, and report unclear terms without inventing permission.

## 3. Keep VTC as the calculation authority

Create or safely continue the requested fork at `build/vtc_microtom_20261011/`; inspect existing work
before choosing a fresh versioned location if necessary. Record the original and modified file hashes.
Keep fork sources separate from fresh per-run working copies and result directories.

Apply the reviewed Micro-Tom adaptation from the earlier fork prompt:

- Parameterized determinate apex termination, truss cadence and internode limits.
- Rank-dependent leaflet counts, segment-specific rachis bending, middle-pair size pattern, and explicit intercalary/secondary area-correction limitations.
- Individual planar leaflet blades for V1; no fixed 13-leaflet template and no compound envelope as optical tissue.
- Declared sowing-plus-30-day spin-up and climate inputs for the generated-initial-state route.
- LED scene and swappable measurement-ratio inputs in place of unexamined sun/sky defaults.

All biological coefficients retain source/cultivar/domain/uncertainty labels. Merlice or another dwarf
cultivar is not Micro-Tom. Candidate equations in the literature prompt are candidates until the
scientific contract selects them. Do not silently turn literature angles or developmental intervals into
universal constants. Blade curl, automatic phototropism, nutrient responses and unobserved side shoots
remain outside Phase 1.

Before changing scientific behavior, produce
`handoff/PHASE1_VTC_PYTHON_SCIENCE_AND_IO_CONTRACT_2026-10-11.md`. Claude must specify:

1. Which existing VTC photosynthesis path is active, its incident/absorbed-light basis, face/area convention, and whether leaf respiration is already included.
2. Maintenance and growth-respiration ownership, CO2/CH2O/carbon/dry-matter conversions, source/sink allocation, reserve semantics and deficit behavior.
3. Time-step ordering: bind each light result to the geometry and environment actually used. Check VTC's `step`/`renew` ordering; do not assume it is already free of one-step light lag.
4. How organ mass becomes dimensions and geometry, including consistency of area-correction factors with represented optical area.
5. Initial-state routes, biological age, treatment of observed dimensions versus unobserved mass/reserves, and the scope of allowed topology changes.

Audit existing code rather than mechanically endorsing it: source strength uses clipping, reserve reset
and conversion factors that must be reconciled with a carbon ledger. Separate inherited assumptions from
reviewed corrections. A reference implementation is not evidence that its parameters or bookkeeping
are valid for this experiment. No carbon/photosynthesis coefficient fitting is requested without data.

## 4. Python-to-VTC input contract

Freeze a complete run package with schema version, run/scenario IDs, source hashes and provenance.
Use JSON for metadata/configuration and CSV for tables. Specify exact headers and units before coding.

Required content:

- Plant-instance and source-plant IDs, axis/compound/leaflet IDs and parent links. Preserve one-to-one external-ID to VTC-node mappings; create new IDs explicitly for any simulated new organs.
- Aware start/end times, time step, observation time, photoperiod and environment coverage.
- Coordinate-frame identifier, length/angle units, explicit plant-local to canopy transform and its provenance. VTC's metre geometry and Python millimetres must be converted explicitly.
- Leaflet geometry or a reviewed mapping from measured traits to VTC geometry, with observed/generated/assumed support per field.
- Initial structural masses and reserves where required. Unknown values may be declared scenario assumptions, never observations or implicit zero.
- Lamp geometry/emission, light-input basis, climate, model switches and parameter evidence.

Provide two distinct initialization routes:

**A. Conditional generated plant:** run the declared spin-up or use a labelled synthetic fixture; output
retains generated provenance. It can demonstrate integration before real observation gaps are resolved.

**B. Observation-initialized plant:** import supported P1/Stage-2 values, identity and geometry through a
reviewed adapter. Do not require a fully implemented phynotype2 pipeline to test the adapter with fixtures,
but never claim a fixture is an actual P1 observation. Unknown hidden geometry, organ age, mass and
reserves must stay explicit; reject insufficient input or require a declared conditional scenario.

Do not infer age from capture date or silently replace imported organs with a separately generated
spin-up plant. Disable or parameterize original experiment-specific date triggers, including the hardcoded
harvest-structure update, so they cannot overwrite imported structure with Merlice observations.

No fabricated board-to-plant transformation and no changing a frame label to bypass a gate. New
plant-local support must be explicit, with unchanged historical board-mode behavior.

## 5. Light inputs and ownership

GroIMP computes the authoritative within-run per-leaflet light. The existing Python ray tracer may run
separately as a diagnostic; it must not contribute additional photons to the GroIMP state.

Implement the fork's `light_input.csv` and `light_ratio_latest.txt` contract, reading human measurement
files without editing them. Resolve and freeze the pointer target and hash at run start; later pointer
changes must not affect an already running or resumed scenario.

Keep normalized phone measurements separate from absolute PPFD. An assumed reference PPFD/DLI must
be flagged as assumed, never measured; normalized ratios cannot establish absolute carbon supply.
For constant illumination only, the checked conversion is PPFD = DLI * 1e6 / illuminated_seconds;
otherwise integrate the supplied schedule. Confirm reference area/height and normalization population.

Document whether measured ratios constrain source calibration or define an approximation. Do not scale
the lamps and then multiply each leaflet result by the same spatial ratio again. Do not substitute a
per-pot reference value for ray-traced leaflet illumination. Unknown measurement height cannot support
physical validation; a hypothetical height is a labelled scenario.

Keep the earlier fork's virtual-sensor comparison with the measured grid, but distinguish ratio agreement
from absolute-light validation. Record the chosen GroIMP backend, optical properties, ray counts, random
seeds, transport depth and convergence/sampling limits.

## 6. Python execution and collection

Use a verified installed GroIMP/Java runtime. The reference recommends GroIMP 2.2.1, but record the actual
version and verify project compatibility. Do not invent headless arguments or assume a light-only launcher
can execute a full growth project unchanged. Prove that the chosen launcher opens this fork, initializes
the intended state, executes the requested number of steps and writes its own completion manifest.

Python must:

1. Audit and freeze inputs into a fresh `build/vtc_python_phase1_<date>_<id>/` run directory.
2. Prepare an isolated fork working copy and exact launch request.
3. Launch locally with safely separated arguments, capture logs, and enforce a timeout and exit status. Preserve non-ASCII Windows paths; avoid shell-built command strings.
4. Require a run-specific completion record with expected interval count and hashes; neither exit zero nor old CSV files alone prove success.
5. Parse, validate and publish results atomically only after identity/time/unit/conservation checks. Keep partial/error outputs separate and never label them successful.
6. Export an inspectable trajectory from the returned GroIMP states, with source/assumption labels. Do not substitute the old growth animation.

If no verified noninteractive launch works, provide the exact manual fallback and completed independent
work, but report automated integration as incomplete. Do not claim a manual-only run meets this prompt.
A GUI process launched for interactive user control may be visible; background helpers should be hidden.

For resume, use complete verified state including reserves, ages, topology, geometry and random state,
or perform a deterministic replay from frozen inputs with explicit semantics. Do not resume from CSV
dimensions alone. Every completed time step must export the geometry actually consumed by the next one.

## 7. Output and carbon-accounting contract

Export per-interval and per-organ tables for light, exchange, maintenance, potential demand, allocated
resources, growth respiration, realized dry-matter increment, reserves, area and dimensions. Export
geometry, stable identity mapping and provenance as well. Preserve signed deficits and unavailable data.

Provide a normalized gC audit ledger without silently treating VTC biomass-equivalent reserves as gC.
Keep raw native outputs beside converted fields and document every conversion. The scientific contract
must identify all terms in the conservation balance:

```text
initial stored carbon + signed photosynthetic exchange
  = final stored carbon + structural carbon increment
    + respiration not already included in exchange + explicit exports/losses
```

Do not charge leaf respiration twice, conceal clipping losses, reuse initial reserves each day, or invent
unreported storage. If inherited VTC behavior cannot support this balance, instrument it and obtain a
reviewed correction in the fork; do not mask the discrepancy in Python.

Allocate carbon within each plant while tracing canopy shading across plants. Report potential versus
realized growth. Label all conditional runs `run_status=assumption_conditioned`,
`nutrient_feedback_enabled=false` and biological validation as not established. Keep software pass status
separate from scientific acceptance; no `accepted_for_domain` from synthetic demonstrations.

## 8. Proposed deliverables

Reuse equivalent existing code where possible; finalize exact function signatures in the contract.

- Versioned Micro-Tom VTC fork and documented source diff; original download unchanged.
- `tools/vtc_growth_bridge.py`: `audit`, `prepare`, `run`, `collect`, `demo` CLI operations.
- `tools/vtc_growth_io.py`: schemas, conversions, identities and output verification.
- `tools/tests/test_vtc_growth_bridge.py`: unit/adapter/regression tests plus clearly marked runtime integration tests.
- `tools/VTC_GROWTH_BRIDGE.md`: exact commands, runtime prerequisites, assumptions and failure handling.
- English science/I/O contract and `handoff/PHASE1_GROIMP_PYTHON_EXECUTION_2026-10-11.md`.
- Fresh demo inputs, runtime logs, normalized/native ledgers, geometry sequence, manifest and viewer under `build/`.

Existing Python P2, P3, P4 and nutrient tools remain operational. Their outputs are not automatically
interchangeable with the new engine: comparison adapters must state model, area and accounting differences.

## 9. Acceptance tests and completion

Run meaningful tests and actual local engine executions. A mocked subprocess is not an engine test.

1. Runtime: Python launches the fork and collects at least three consecutive committed growth intervals. Retain command, versions, exit code, completion manifest and outputs.
2. Initialization: synthetic input round-trips identities, units and supported initial geometry. An observation-like fixture exercises route B without claiming real observation validation.
3. Mass/geometry: funded organ increments change actual exported leaflet dimensions/area under the selected mapping; unsupported area corrections do not manufacture optical tissue.
4. Carbon: independent per-plant, per-step balance checks include reserves and every charged respiration term. Hand-check representative conversion and allocation cases.
5. Causality: controlled carbon-limited versus sufficient cases with positive unsaturated demand produce different realized growth. Darkness with depleted reserves cannot yield free positive growth; deficit policy is observable.
6. Feedback: a controlled two-leaf scene demonstrates that growth changes geometry and the next-step lower-leaf light. Geometry hashes, current-step scheduling and a frozen-geometry comparison must prove actual feedback, not only an animation or hash change.
7. Canopy: two plants shade each other while identity and carbon pools remain separate; per-plant totals reconcile with canopy reporting.
8. Failure: invalid units, stale outputs, wrong run IDs, malformed ratios, missing parameters and failed/timeout engine runs cannot be reported as successful. No partial state commit.
9. Reproducibility: frozen inputs and supported seeds reproduce results within declared stochastic tolerances; resume/replay matches uninterrupted execution under the declared method.
10. Numerical quality: assess time-step behavior where supported and ray-sampling convergence. If VTC is daily-only, disclose that limitation rather than pretending a smaller step has been validated.
11. No duplication: engine-off behavior and relevant existing Python tests remain unchanged. Python diagnostics cannot double-apply illumination, respiration, growth or nutrient effects.
12. Evidence: real missing scale/PPFD/state remains unavailable or explicitly assumed. Test that generated geometry and borrowed coefficients cannot be promoted to measured or Micro-Tom-validated results.

Complete only when Python runs and collects a genuine multi-step VTC trajectory in which resource
availability affects growth and updated geometry affects later light, with traceable identity and carbon
accounting. A copied fork, successful compilation, CSV adapter, or attractive animation alone is insufficient.

End with a concise Korean briefing and the English execution report, separating implemented behavior,
actual tests, conditional assumptions, unresolved science and real-data validation gaps. Update LOG/TODO
without rewriting history. This document is an implementation prompt, not evidence that its requested
changes have already been made.
