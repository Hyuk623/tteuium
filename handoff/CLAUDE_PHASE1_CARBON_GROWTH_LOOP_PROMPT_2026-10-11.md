# Phase 1 carbon-driven FSP integration

Date: 2026-10-11
Recipient: Claude for the scientific contract, followed by Claude Code or Codex for implementation within repository ownership rules.
Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

## User objective

Implement the first carbon-driven integration of the existing four-project tomato FSP system:

```text
P1 initial structure and identity
  -> P2 light on individual leaflets
  -> P4 photosynthesis, respiration and available carbon
  -> organ carbon allocation
  -> P3 realized growth and updated leaflet geometry
  -> P2 light recomputation at the next time step
```

The deliverable must execute this loop over multiple steps. Producing another standalone diagnostic, an animation with prescribed growth, or a document without the integration is not completion of the implementation task.

Phase 1 excludes nutrient-limited growth. Report `nutrient_feedback_enabled=false`; do not imply nutrients were measured or proven non-limiting. Preserve the existing nutrient ledger and disabled-mode behavior. Do not add automatic phototropism, gravitropism, nutrient-driven orientation, or unobserved side-shoot generation.

This prompt authorizes the scoped implementation when submitted to the implementing chat. Its preparation does not mean implementation or scientific approval has already occurred.

## 1. Read the current project before changing it

Read the parent `공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, the last entries of `handoff/LOG.md`, and relevant open items in `handoff/TODO.md`. Recheck current source rather than relying on historical line numbers.

Read these contracts and reports, including their appended owner reconciliations:

- `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md`
- `handoff/CODEX_FORECAST_SPEC_2026-10-10.md`
- `handoff/CROSS_STAGE_ISSUES_2026-10-11_KO.md`
- `handoff/OWNERSHIP_OVERRIDE_2026-10-11.md`
- `tools/FSP_CARBON_DIAGNOSTIC.md`
- `tools/PROBABILISTIC_COMPOUND_GROWTH.md`
- `tools/FSP_NUTRIENTS.md`

Inspect the actual APIs and integration boundaries in:

- `tomato3d/light/{geometry,raytrace,pipeline,budget}.py`
- `tools/hierarchical_light.py`, `tools/plant_light_bridge.py`
- `tools/compound_growth.py`, `tools/probabilistic_compound_growth.py`
- `tools/fsp_carbon_diagnostic.py`, `tools/nutrient_fsp_bridge.py`

At prompt preparation, P4 was a pure diagnostic with no allocation, reserve propagation, P3 execution or geometry mutation. Existing P3 growth did not consume carbon. `phynotype2/` contained only README. The proposed `build/vtc_microtom_20261011/` fork did not exist. Treat these as facts to recheck, not instructions to duplicate work if another owner has since implemented them.

Keep `config/`, human records and `docs/` unchanged. Claim shared code files in LOG before editing and check for another owner's claim. Append to handoffs rather than rewriting their history. Save generated cases and outputs in fresh `build/` directories. No training, remote rendering, uploads or other-chat messages are required by this task.

## 2. First produce the executable scientific contract

Claude must resolve the scientific choices before an implementer selects new biological equations. Start from existing reviewed P4 conventions. Inspect original literature where new choices require support and record equation/page, cultivar, conditions, units and applicability. VTC is a reference implementation, not automatic authority for Micro-Tom parameters:

`C:/Users/sho36/Downloads/vtc-main/vtc-main/tomatoFSPM_basic_isP/`

A separate GroIMP fork does not satisfy integration of the existing Python modules. Do not edit the downloaded original. If borrowing code rather than only studying it, check the applicable reuse license first.

Create `handoff/PHASE1_CARBON_LOOP_SCIENCE_CONTRACT_2026-10-11.md` with these decisions:

1. Time stepping: interval boundaries, environment quadrature, start-state or substep geometry, day/night handling, and event ordering. Declare the numerical approximation and time-step convergence check.
2. Carbon basis: use gC for the common ledger and g dry matter for structural mass. Specify every CO2/CH2O/dry-matter conversion. Never treat 1 gC as 1 gDM.
3. Respiration ownership: leaf exchange convention, maintenance by organ, growth respiration, and when each is charged. Preserve accepted P4 `before_mito`/`net_leaf` rules; debit each cost exactly once.
4. Storage: initialization, accessible versus reserved carbon, release limits, surplus storage/export, and deficit handling. A missing storage measurement is not zero. No negative pool or silent clipping that hides unpaid respiration.
5. Organ demand and allocation: a documented potential-demand law, allocation rule, saturation, leftover redistribution or storage, and dry-matter conversion. Demand may not depend circularly on the already realized increment.
6. Morphology: supported mass-to-area and mass-to-length mappings, their inverse/forward consistency, and a method for updating individual leaflet surfaces. A leaf area alone does not determine its contour, depth or orientation.
7. Existing environmental growth factors: decide how the P3 reference-DLI size response and the new carbon limitation interact. Do not blindly multiply both and count the same light limitation twice. Preserve the old path outside the new opt-in mode.
8. Topology and direction: initial Phase 1 runs may use explicitly supplied axes and organs. State that scope. Preserve initial directions unless a separately evidenced, explicitly selected rotation scenario applies. No invented emergence ranks, angles or new side shoots.

For every equation and coefficient record identifier, input/output units, valid domain, source, evidence kind, uncertainty/range, and missing-input behavior. Separate measured values, reviewed model choices, other-cultivar priors and synthetic arithmetic fixtures. Other-cultivar coefficients must remain conditional scenario inputs, never target-cultivar defaults.

If executing as Codex without a completed scientific contract, implement only contract-independent infrastructure and clearly report the unresolved contract; do not claim the loop complete. If executing as Claude, perform the scientific review first and then proceed with the agreed conditional model. Missing real observations need not block synthetic integration tests, but synthetic fixtures cannot certify biological accuracy.

## 3. Implement a shared, versioned state and explicit adapters

Use one versioned state per run/scenario/trajectory and time. It must contain:

- Stable plant-instance, source-plant, axis, compound, leaflet and parent identifiers. Keep instanced copies separate from source plant identity.
- Aware timestamps, explicit coordinate frames and transformations, geometry hashes and source hashes.
- Structural organ masses in gDM, declared structural carbon fractions, carbon reserves in gC, and model-state provenance.
- Individual leaflet vertices/triangles, one-sided area, normals, optical material/face conventions, and derivation method.
- Observation versus simulation status and unavailable reasons.

Support an explicitly defined synthetic plant-local frame for synthetic tests. For real board-free data, resolve the reviewed `plant_local_mm` versus `board_mm` contract; do not rename a frame to bypass validation or invent an unrecoverable transform. A canopy placement transform must be separate, explicit and reversible.

Create a P2-to-P4 adapter that maps individual receiving patches to physiological organs without duplicating area or carbon. Retain incident versus absorbed PPFD, face convention, timestamps, geometry version, units and missing values. Do not substitute reference-point DLI, projected-area proxies or compound-envelope area for leaf-level absorbed light.

Reuse existing P4 public calculations where their contract fits, including `compute_leaf_exchange`, `compute_respiration` and the reviewed demand arithmetic. Keep the old `compute_carbon_sufficiency` diagnostic pure and backward compatible. Introduce the state-changing loop as a separate opt-in caller rather than silently making diagnostics mutate plant state.

## 4. Execute each time step transactionally

For interval `[t, t + dt)`:

1. Freeze and validate the complete start state, environment, lamp schedule, parameters and identity mapping.
2. Build the full-canopy optical scene from that state's individual leaflet surfaces. Run P2 using the declared geometry/time approximation. Cache only against complete geometry, material, light and numerical-setting hashes.
3. Map P2 output into P4 exchange inputs; integrate carbon exchange and maintenance using the same interval and state. Record known light-model limits, including direct/straight-through transport without reflected scattering where that is the selected backend.
4. Compute potential organ demands from the reviewed law. Allocate only available carbon after the contract's respiration and reserve rules. Record potential versus realized increments and each limiting reason.
5. Convert funded structural growth to dry-matter increments and geometry. Growth-respiration cost must be based on funded growth, not unfunded demand. Do not subtract an entire potential demand and then reduce it afterward.
6. Regenerate per-leaflet optical surfaces using the reviewed mapping. Verify area/mass consistency within declared tolerances and preserve anatomical identity. Do not relabel a `compound_envelope` as a leaflet to pass a gate.
7. Audit the carbon ledger and geometry. Commit masses, storage, geometry and time together only if all validations pass. A failed interval must leave its starting state unchanged and export the failure reason.
8. Use the committed geometry in the next P2 call. Do not reuse the original light series for all subsequent geometries.

Define the conservation identity symbolically in the science contract. One suitable accounting layout, with terms assigned by that contract, is:

```text
initial stored carbon + signed leaf-exchange carbon
  = final stored carbon + structural carbon increment
    + maintenance not already included in leaf exchange
    + growth respiration + explicitly modelled carbon exports/losses
```

This is a bookkeeping requirement, not an authorization to choose reserve mobilization, tissue turnover or starvation laws. Unmet obligations must be reported or trigger the specified failure path. Use explicit absolute/relative tolerances and retain residuals; do not hide them through normalization.

For multi-plant canopies, calculate mutual shading together but allocate carbon within each plant unless a reviewed transport mechanism explicitly says otherwise. No accidental sharing of reserves between neighbors.

Generated future geometry must carry simulation provenance. It can be geometrically valid for a conditional optical run without being relabelled as measured tissue or independently validated real geometry. Preserve existing real-data evidence gates.

## 5. Implementation layout and outputs

After checking for equivalents already present, use the following proposed entry points or document an equivalent existing location:

- `tools/fsp_carbon_loop.py`: CLI and multi-step orchestration; `audit`, `run`, `demo` subcommands.
- `tools/fsp_carbon_loop_state.py`: validation, immutable snapshots and atomic commit.
- `tools/fsp_carbon_loop_adapters.py`: identity/frame-aware P1/P2/P3/P4 mappings.
- `tools/fsp_carbon_allocation.py`: only the reviewed allocation and storage contract.
- `tools/tests/test_fsp_carbon_loop.py`: integration and conservation tests.
- `tools/FSP_CARBON_LOOP.md`: exact inputs, units, outputs, commands and limitations.

The science contract must pin the final public function signatures and schemas before implementation. Suggested boundaries are `audit_loop_inputs(request)`, `step_carbon_loop(state, interval_inputs, model_pack)` and `run_carbon_loop(request)`; verify API compatibility instead of assuming these exist.

Use JSON for configuration, parameter packs, state snapshots, geometry metadata and provenance; CSV for numeric ledgers and time series. A fresh run directory must include:

- Materialized input snapshots, source/code hashes, chosen scientific contract and deterministic seeds where applicable.
- Initial and committed interval states with matching geometry artifacts and hashes.
- Light results identifying the geometry used for every interval.
- Per-organ potential/realized mass and area increments, allocation and respiration ledgers, per-plant reserves and conservation residuals.
- Availability/assumption reports and a concise execution summary.
- A multi-step viewer or compatible export showing the actual committed trajectory, not a separate hardcoded animation.

Keep missing numbers unavailable rather than zero. Labels for synthetic or borrowed-parameter demonstrations must include `run_status=assumption_conditioned`, `nutrient_feedback_enabled=false` and an explicit biological-validation status. Keep software verification separate from forecast evaluation; do not report `accepted_for_domain` from synthetic tests.

## 6. Required acceptance tests

1. Backward compatibility: disabling the new loop preserves existing P3/P4 behavior and representative numeric baselines. Nutrient-ledger behavior is unchanged.
2. Unit and identity checks: reject mismatched frames, intervals, organ IDs, geometry hashes, nonfinite values and incompatible PPFD/area conventions. Check known CO2/CH2O/gC conversions against hand calculations.
3. Adapter correctness: aggregate multiple patches to an organ exactly once; verify a known single-leaf case against an independent light/carbon calculation.
4. Conservation: independently recompute carbon closure per plant and interval, including final storage, funded structural carbon and each respiration term.
5. Resource limitation: an otherwise identical low-carbon case realizes less growth than a carbon-sufficient case with unsaturated positive demand. Neither exceeds potential demand or available carbon.
6. Darkness and storage: no positive light-driven fixation with lights off. Any growth draws on explicitly available reserves. Test depleted-storage/maintenance-deficit behavior without negative pools or free growth.
7. Feedback: a funded growth case changes leaflet geometry; the next P2 call uses its new hash. Use a controlled two-leaf shading configuration to independently demonstrate a change in lower-leaf illumination. A changed hash alone does not prove correct light feedback.
8. Canopy accounting: two plants share shading but not carbon stores; aggregate per-plant outputs recover canopy totals without double counting.
9. Atomicity and reproducibility: force a late geometry or accounting failure and verify no partial state commit. Compare resumed and uninterrupted runs with identical inputs.
10. Assumption/evidence gates: missing real scale, optical evidence, physiological coefficients or state cannot be silently filled using demo values. A conditional synthetic run remains distinguishable from a real observation run.
11. No double limitation: demonstrate the declared handling of P3's existing DLI size response and P4 carbon supply, and test respiration ownership under each supported exchange convention.
12. Numerical convergence: repeat a deterministic case with a smaller time step and report discrepancies in reserves, mass, area and light against the contract's tolerance.

Run at least one actual CLI demonstration covering three or more committed intervals and a deliberately rejected input case. Capture commands, exit codes, generated outputs and relevant regression results. Do not count repeated runs of the same tests as independent evidence.

## 7. Completion and handoff

Deliver the science contract, code, tests, guide and an English execution report at `handoff/PHASE1_CARBON_LOOP_EXECUTION_2026-10-11.md`. Append LOG and relevant TODO outcomes. The report must map every acceptance test to actual evidence and distinguish:

- Already present versus newly implemented components.
- Executed synthetic integration versus unavailable real-data execution.
- Equations accepted for this conditional model versus coefficients not validated for Micro-Tom.
- Remaining requirements for nutrient feedback and biological validation.

Do not mark Phase 1 complete unless a carbon budget changes realized organ growth, that growth changes actual leaflet geometry, and the subsequent light calculation consumes that geometry with a closed per-plant carbon ledger. If a scientific decision remains unresolved, name it precisely, finish independent authorized work, and report the loop as incomplete.

## Superseded architecture for Phase 1 (2026-10-11)

The user selected GroIMP/VTC as the authoritative simulation engine and Python as the integration layer. For new Phase-1 work, use [the V2 GroIMP/Python prompt](CLAUDE_PHASE1_GROIMP_PYTHON_INTEGRATION_PROMPT_V2_2026-10-11.md). Its engine ownership and execution scope supersede the Python-owned allocation/growth-loop instructions above. The original text remains for history; no implementation is claimed by this amendment.
