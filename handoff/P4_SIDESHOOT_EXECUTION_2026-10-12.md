# P4 declared side-shoot execution

Date: 2026-10-12. Status: native declared-axis resource/development mechanics implemented and executed on explicitly synthetic P1-format fixtures. Actual P1 side-shoot exporter integration is pending its parallel delivery; no natural branching, side-shoot emergence or validated Micro-Tom growth claim.

## Contract and implementation

The science/IO contract was saved before code as `P4_SIDESHOOT_SCIENCE_AND_IO_CONTRACT_2026-10-12.md`. After the reference work order was saved with its exact deliverable filename, the preserved contract was copied to the canonical P3 entrypoint `P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md`, with an append-only column-mapping addendum. Section 2 selects one plant carbon pool, unity default SUBSTEM_SINK_SCALE, capped weighted demand allocation, independent per-axis conditional apex programs, shared tissue demand curves and unchanged plant-level prescribed nutrient accounting. Pending scientific decisions were appended to `VTC_V3_PENDING_DECISIONS_2026-10-11.md`.

Read CONVENTIONS, AGENTS, LOG/TODO, V3 contract and decisions, staged execution, MTG convention. A4 was absent at contract preparation. The named claude.ai definition/Carvalho notes were not accessible as local files, so the explicit user assignment supplied the normative axis definitions. The Carvalho primary article was checked at https://link.springer.com/article/10.1186/1746-4811-7-18; it supplies developmental context, not a fitted resource-sharing law for this implementation. No other-cultivar dominance coefficient was activated.

Changed native graph/controller code in `tools/vtc_development_native.rgg`, preparation/validation/observation adapters in `tools/vtc_development.py`, `_io.py`, `_observation.py`, consumer and publication in `tools/tomato_fsp_io.py`, `tomato_fsp_pipeline.py`, and output preservation in `vtc_growth_bridge.py`. Added `tools/fsp_axes.py`, `fsp_axes_acceptance.py`, `tools/tests/test_fsp_axes.py`; usage/migration in `tools/FSP_EXTENSIONS.md`.

`fsp-axes-1` declares M/S1 identities per plant and separate active-apex controllers. Native graph segments remain separately identified by developmental_axis_id; sympodial succession stays on the same logical axis. Existing M and S tissues share one plant reserve, with each demand and maintenance charge represented once. Native axis_flux.csv records diagnostic source attribution, not separate photosynthate pools. Committed states, events and mesh rows carry axis_id/parent_rank; commits also contain an axis inventory and per-axis parameter registry.

Side attachment must name an actual selected main-axis node with matching rank and a leaf axil. Two registration leaves and explicit hidden-state supplements are required. Unprovided axes never appear. `APPLY_DETERMINATE_STOP=false` disables new initiation on that declared axis while retaining existing tissue expansion; it does not invent an indeterminate program. Axis state is retained as a declaration, never advanced to substem from a guessed age.

## Executed acceptance

Evidence: `build/fsp_axes_20261012_growth_02` and `build/fsp_axes_20261012_shading_01`. Every run used 4,800,000 rays, Java 21.0.12.1 / GroIMP 2.2.1 and exited 0. Core SHA256: `35c605d65d9b54fe64cdf93bf28ae44ae7a1b6ded03b461dedcb0156a5c22147`. Actual commands, runtime versions, frozen Model.rgg hashes, native output hashes and publication bindings are in each native execution/prepared/completion file.

Final independent acceptance: `build/fsp_extensions_axes_20261012_delivery_01/axis_acceptance.json`, with the shared `acceptance.json` and source snapshot. Nine side-axis native runs, 29 intervals: unity, weighted, main_stopped, axis_stop and deterministic replay each have five intervals; four shading controls each have one.

| Criterion | Executed result |
|---|---|
| Once-only funding / closure | All returned organ demand, mass and funding checked by the existing independent validator. Maximum plant carbon residual **4.163336342344337e-17 gC**. Common root imported once. |
| Per-axis sums | Maximum difference between summed axis physiological fluxes and plant ledger **2.0816681711721685e-17 gC**, numerical summation roundoff. Every interval/plant/axis and every organ covered. |
| Sink multiplier | At first interval, S1 allocation rises **0.005078283850977462 -> 0.01068842689856515 gC** when its multiplier changes 1 -> 3. M falls **0.01879932100900715 -> 0.013189177961419466 gC**. Total funded budget unchanged; native allocations independently checked with a bisection oracle and capped by each demand. |
| Initially stopped M | Over five days, M compounds remain **5**, S1 compounds grow **2 -> 5**. Existing M leaf dry mass still increases **0.07754659578992089 gDM**. |
| M stop generated during run | Declared conditional truss-history fixture produces an M determinate_stop at day 1. S1 produces three new compounds, including after that boundary. Existing M leaves gain **0.07669538979865136 gDM**. The supplied historical truss counters are assumptions, not observed truss evidence. |
| Shading | M absorption near/far = **0.4525 / 0.63575** umol/s at seed 5000 and **0.42325 / 0.61075** at seed 5100. Receiver fixture_a#2\|fixture_a/C0001/T mean effect **0.08025 umol/s**, above the maximum tested individual-leaf seed difference **0.009 umol/s**. |
| Replay | Five committed boundaries agree within the pipeline's 1e-9 state tolerance. No second call advances an already-produced checkpoint. |
| Invalid axes | Missing parent and duplicate axis declarations reject preparation with no published checkpoint; evidence `build/fsp_axes_20261012_failures_01/failures.json`. Additional tests cover wrong rank/axis, missing registration/source/flag/mass, higher order, negative scale and unsupported stage. |

The near/far control moves declared side leaves using an explicitly synthetic geometry transform. It demonstrates geometry-mediated shading, not a natural Micro-Tom architecture or measured shelf placement. The viewer is `build/fsp_axes_20261012_growth_02/main_stopped/native/results/viewer.html`; the inspected figure of returned native triangles is `build/fsp_axes_20261012_visual_01/native_axes.png`.

Executed native commands:

```powershell
python -X utf8 -m tools.fsp_axes_acceptance --out build/fsp_axes_20261012_growth_02 --rays 4800000
python -X utf8 -m tools.fsp_axes_acceptance --out build/fsp_axes_20261012_shading_01 --mode shading --rays 4800000
```

Both exited 0. `growth_01` is a preserved failed fixture-preparation attempt: newly assigned order had an unavailable sibling status. The fixture generator was corrected to label the synthetic order explicitly; no native success or publication is claimed for that attempt.

## Regression and parallel-owner integration

Final combined focused suite: **192 passed, zero failures/errors** (530.76 seconds), JUnit `build/fsp_extensions_axes_20261012_regression.xml`. It includes **102** existing V3/integration/bridge cases, **43** forecast-consumer cases, **20** new axis cases and **27** extension cases. One additional producer column-alias case passed afterward, JUnit `build/fsp_axes_20261012_producer_columns.xml`: **193 unique passing cases in total**. Counts from earlier subset runs overlap and are not added again.

The actual delivered forecast wrapper was also executed through the public pipeline at 4.8M rays, one member/three instances/one interval, with H3 enabled: `build/fsp_extensions_20261012_wrapper_01/forecast_20261012_01`. It consumes committed checkpoints once. This verifies current wrapper compatibility, not the later P3 side-shoot forwarding/evaluation work assigned to Claude Code.

At this report's initial publication, the P1 owner has claimed the side-shoot task and explicitly agreed in LOG to emit fsp-axes-1 exchange columns alongside A4 names. The adapter accepts producer axis/axis_state aliases with disagreement rejection. The executed fixture is not falsely described as an actual completed P1 side-shoot export. A4/producer delivery reconciliation will be appended when available. P3 should consume the resource contract and use explicit fixtures until that prerequisite is delivered.

No edits to tomato3d/, tests/, tools/microtom_*, config/, data/records/, docs/ or original VTC. Source license remains unresolved/local-only. The parallel forecast owner recorded a transient failed prepare while native source was being edited; its failed forecast_20261012_01 remains unissued, and its later issued runs/tests passed. Final source snapshots and this task's tests identify stable verified versions.

Flow rows are supplied in `handoff/FSP_EXTENSION_SIDESHOOT_FLOW_ROWS_2026-10-12.csv` and requested through LOG for the active P1 flow-map owner to merge. The shared flow file is not concurrently rewritten. Pending human/science choices remain substem truss applicability, axis-specific timing/dominance, real attachment/registration and hidden state; nutrient growth feedback stays disabled.

## A4 reconciliation during delivery (2026-10-12)
A4 section 15 is now available and was read. It explicitly keeps numbering basis and simultaneous-first-leaf tie order as proposals and order-2 axes open; the consumer preserves supplied identities/ranks without choosing these policies. A4 uses the main-axis CompoundLeaf vertex as parent_node_id. The canonical resource contract section 6 records the explicit adapter: a matching-rank main-axis CompoundLeaf represents its own axil; the older Metamer representation still needs a compound child. CompoundLeaf is a zero-length native attachment at its observed base. No missing attachment is inferred. Actual P1 side-shoot package delivery remains distinct from the format-fixture test.

### Final A4 verification result
`build/fsp_axes_20261012_a4_01`: one additional native run, two intervals, 4,800,000 rays; native and pipeline validation passed. CompoundLeaf parent reference is retained in every state. A jointly consistent but nonexistent parent in axes.csv, MTG and request is rejected with `side axis parent node missing`, with no publication. Maximum carbon residual in this run is 1.3010426069826053e-17 gC. This is an explicitly labelled A4-format consumer fixture, not a delivered producer export.

The complete axis test file was rerun after the adapter change: **23 passed** (231.88 seconds), JUnit `build/fsp_axes_20261012_a4_tests.xml`. Twenty-one overlap prior cases; two are new A4 attachment/missing-node cases. Final unique focused passing count is therefore **195**, not 216. Total native evidence is **31 runs / 152 intervals**, with **10 declared-axis runs / 31 intervals**; the separately executed forecast wrapper remains additional. Only tools/fsp_axes.py changed in the prior 16-file source snapshot after the earlier combined regression. The additive source/hash/evidence snapshot is `build/fsp_extensions_axes_20261012_delivery_01/a4_delivery_addendum.json`. A4 is reconciled; actual P1 exporter delivery, P3 forwarding and shared flow-map merge remain with their active owners.
