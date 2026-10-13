# Four project delivery review and improvement priorities

Date: 2026-10-04, Asia/Seoul. Author: Codex. Audience: user and project owners.

## Review brief

Review the four user-selected P1/P2/P3/P4 handoffs, compare implemented scope with integration decisions D1-D10, inspect relevant runtime contracts and recorded verification evidence, and identify improvements with owners and acceptance criteria. This is a review and documentation task. Do not change active implementations, run model jobs, fit parameters or start deferred integration.

The review distinguishes delivery statements, inspected code/contracts, checked saved evidence, and recommendations that still require adoption. Findings and verification results follow below.

## Overall finding

P2 actual direction export, P3 D8-D10 growth behavior and the isolated P4 carbon diagnostic are implemented. P1's selected report establishes local observation/ratio and completion-preparation delivery; it does not establish accepted real optical tissue geometry. The main remaining work is trustworthy measured input, semantic conversion contracts and target-specific validation. Adding another growth engine or repeating the completed angular callback work would not resolve these gaps.

The original ambition to predict light-driven growth direction remains only partly addressed. P2 now supplies physical light directions and P3 supplies direction trajectories, but D9 adopts light effects on size targets only. There is no adopted transfer from P2 direction moments to P3 phototropic bending. Treat this as an explicit future scientific/model decision, not an adapter omission to fill by pointing leaves toward the largest light vector.

The current architecture is observation geometry → light exposure → growth forecast, with a read-only carbon diagnostic beside it. It is not a closed loop that creates validated future optical leaves, reruns light on those leaves and propagates carbon reserves. Current P3 envelopes remain optically ineligible, and P4 uses a fixed supported-tissue snapshot.

## Sources and verification scope

The four requested reports were read in full:
- [P1 non GPU status](CODEX_P1_NON_GPU_STATUS_HANDOFF_2026-10-04.md).
- [P2 directional delivery](CODEX_P2_DIRECTIONAL_DELIVERY_2026-10-04.md).
- [P3 growth execution](CODEX_P3_GROWTH_DECISIONS_EXECUTION_2026-10-03.md).
- [P4 implemented diagnostic](CODEX_P4_IMPLEMENTATION_HANDOFF_2026-10-04.md).

Supporting inspection included the current P2/P3/P4 runtime guides, P1 geometry-field inventory, P3 calibration binding implementation and D9 validator, integration decisions D1-D10, and current real-lamp readiness draft.

Fresh review evidence:
- [Review evidence](../build/four_project_delivery_review_20261004_01/review_evidence.json).
- [Hash comparisons](../build/four_project_delivery_review_20261004_01/hash_checks.json).

All 291 recorded hash comparisons matched: P1 recorded files; P2 main/split manifests, code, sources and artifacts; P3 final outputs/code; P4 code, handoffs and saved evidence. This is not a repository-wide integrity audit or a new proof of physical accuracy.

Saved JUnit records confirm 240 distinct P2 test IDs across the four cited final suites, 142 P3 tests and 79 P4 tests, with zero final errors/failures. P1's current manifest records 50 local completion tests; its older overlapping suites are not added to that count. P4 records 196 delivery checks, 11 CLI commands and nine hypothetical scenarios. No tests, simulations or verifier programs were rerun during this review; hashes and saved evidence were checked directly.

## Project status and next actions

| Project | Delivered scope | Remaining limitation | Most useful next action |
|---|---|---|---|
| P1 | Per-photo first-label visible-area ratios, preserved observations, corrected local completion runner, validated packages and geometry inventory | Ratios are not absolute tissue area or cross-date identity; generated RGB is not an optical mesh; pose/camera and real surface gates remain open | Prioritize one fully traceable observed plant/organ dataset with scale, poses, timestamp, identity, area basis and reviewed surfaces |
| P2 | Actual transport callback, F/M/B directions, scalar/side/time integration, independent consumer and canopy-preserving instance splits | Real REF-30-40 scene is incomplete; direct transport does not model reflection; no physical accuracy acceptance | Complete optical/clock inputs, select numerical settings explicitly, then compare predictions with independent PPFD measurements |
| P3 | Existing exponential plus newborn beta, restricted temperature/DLI entry, full dependency audit, node budget, truss/terminal events and finite-bank updates | Rates and responses remain assumptions; only whole-plant fixed DLI is accepted; no sympodial continuation, abscission or adopted light-direction response | Add semantic calibration safeguards and obtain repeated observations for identifiable calibration and held-out forecast evaluation |
| P4 | Immutable conditional supply, respiration, mass demand and carbon sufficiency; available/unavailable components; explicit accounting | Scientific parameter/accounting review remains open; fixed optical snapshot; initial pools/allometry needed; no reserve propagation | Freeze one reviewed scope and compatible parameter pack before interpreting numeric diagnostic outputs for real plants |

P1 GPU execution was intentionally excluded from the selected summary. Genuine completed returns still need import/validation, but this review does not make GPU success a substitute for metric geometry or expand the requested review into remote execution.

## Immediate improvements before real use or later integration

### A P1 observation and optical eligibility

Owner: P1 implementation plus Claude's measurement/geometry review.

Use the existing geometry inventory to make the next handoff identify each real dataset's status for capture time, camera pose/scale, cross-view organ identity, compound/leaflet association, source/instance identity, metric area basis, upper-surface normal and optical eligibility. Preserve partial support and holes. Do not interpret first-label ratios across photographs as biological growth or use model-generated anatomy as measured tissue.

Acceptance: a traceable metric fixture with reviewed evidence links and hashes, an explicit coverage statement, and independent area/geometry error evidence or explicit unavailable status. Valid partial tissue may support a labelled partial calculation; it must not become whole-plant coverage by renaming an output.

Repeated capture plans should retain plant and organ IDs, actual timestamps, environmental history and capture phase. Existing Science sampling suggestions remain proposals until adopted; this review does not prescribe new experiments or destructive sampling.

### B P2 real lamp readiness

Owner: user for actual setup information and measurements; P2 for input validation and numerical setup; Claude for physical-model applicability.

The latest draft is `build/lighting_REF_30_40_three_20261004_03/`. It confirms three lamps at [300,326.5,400], [300,229.5,400], [300,132.5,400] mm using the reported 517 × 47 mm envelope. Daily duration 16 hours and full photon output fraction 1.0 are now recorded as user-confirmed. Do not repeat earlier requests to confirm those two values.

Still needed: actual PPF; emitting aperture and center/height interpretation; supported beam parameters; actual clock windows/timezone; ambient-light assumptions; eligible receivers/surfaces and relevant optics. The 30 W rating and luminous units are not PPF.

Separate physical unknowns from routine simulation choices. Emitter grid, receiver sampling and ray/diagnostic budgets need explicit convergence/resource checks, not a request for the user to measure an algorithm setting. Electrical input boundary affects energy reporting and schema completeness; it does not determine optical PPF.

Acceptance: a schema-valid scene whose unknown physical quantities are not replaced by defaults; documented convergence at the intended canopy size; independent calibration/evaluation PPFD records and predefined physical error criteria. The current 16 schema errors are a draft-readiness result, not 16 software bugs. Reflective shelf effects cannot be assumed to disappear through fitting one lamp multiplier.

### C P3 semantic calibration binding

Owner: P3 and calibration implementation; Claude for any new mathematical conversion.

Confirmed inspection: `tools/growth_calibration.py::apply_parameter_set` checks coordinate and fitted-role units, and rejects unsupported beta and stop-budget bindings. The generic constant/physical-location branch does not establish that a fitted increment and an absolute target mean the same thing. `tools/probabilistic_compound_growth.py` uses `left_target_mm` and `right_target_mm` as absolute side targets. The current guide warns against the mismatch, but a documentation warning is weaker than a runtime guard.

Recommendation: add an explicit source-role/destination-meaning compatibility check, rejecting increment-to-absolute-width binding unless a separately reviewed conversion with its required measured anchor is declared. This is a semantic safety improvement, not authorization to invent that conversion.

Acceptance: a regression that rejects a same-unit invalid binding, while valid existing bindings and frozen-pack provenance remain intact. This review identified the missing semantic guard by source inspection; it did not execute a corrupt forecast or show that any delivered fixture used the invalid binding.

### D P2 to P3 DLI selection

Owner: Claude coordination for the definition; P2/P3 owners for a later authorized adapter.

P2 exports incident DLI over supported tissue with explicit spatial and temporal coverage. P3 currently accepts `scope=whole_plant`, `unit=mol/m2/d`, an explicit `basis_id` and a value fixed over the horizon. These are not automatically compatible merely because both fields contain DLI.

Define the exact plant-instance and fixture selection, full-day requirement, supported-versus-whole-plant area basis, treatment of missing tissue, selection of a representative day or explicitly assumed scenario, and compatibility with the calibration basis. A shelf-sensor horizontal DLI is also not automatically the same covariate as mean incident DLI over both leaf faces per one-sided tissue area.

Acceptance: no partial-supported value is relabelled whole-plant; no actual-fixture and aggregate double counting; no incomplete day is promoted to DLI. `mol/m2/day` to `mol/m2/d` is a notation mapping with unchanged numbers, not division by 86400. Future scenario assumptions remain explicit.

### E P3 to P4 demand and geometry mapping

Owner: Claude for mass/form applicability; P3/P4 owners for a later authorized adapter.

P3 sizes/areas/events do not directly supply structural dry mass, roots, reproductive demand or initial reserve. Preserve the distinction among supported blade area, rachis/petiole/stem dimensions, newly created organs and null-geometry truss events. Select an independently supported inverse or declare demand unavailable. Different inverses must not be averaged to hide inconsistency.

P4's isolated `geometry_hash_start/end` hashes canonical endpoint state arrays. P2's native mesh/file hashes identify different objects. Preserve both hash namespaces and an explicit association record; never overwrite one with the other.

Acceptance: per-organ identity and compartment checks, explicit cm2/m2 and mass units, fully charged new-organ material, no overlap of parent and child mass pools, and no whole-plant sufficiency after unsupported post-terminal development.

### F P4 scientific and temporal interpretation

Owner: Claude Science for scientific acceptance; P4 for enforcing the adopted contract.

Resolve incident/absorbed NRH basis, net/before-mito exchange and exclusive respiration ownership, source CH2O/CO2/ASR/mass-basis conflicts, organ parameter assignments, initial pools and valid domains. Tests and `reviewed` input labels do not by themselves establish target-cultivar predictive accuracy; current output correctly retains `accepted_for_domain=false`.

The runtime guide explicitly states that the present NRH has no CO2/VPD/RH/EC/pH response coefficients. Accepting these fields for metadata or domain checks is not a model of their influence. Add such responses only through a reviewed model extension and suitable evidence.

P4 diagnoses one plant instance and interval. It does not propagate reserve state. Reusing the same starting reserve independently for each interval cannot be interpreted as a conserved multi-day trajectory. For the current scope, require declared interval-start stocks and label intervals as independent where appropriate. A stateful reserve ledger or future-geometry optical loop needs a separate contract; do not add P3 feedback implicitly.

Acceptance: a reviewed pack and a clearly supported leaf-subset or whole-plant scope; no duplicate respiration/growth cost; correct missing/zero-demand/deficit statuses; no claims of multi-day stock conservation without an explicit ledger.

## Cross project interface checklist

This is a proposal for the deferred integration contract, not an implemented adapter.

| Boundary | Required explicit mapping | Acceptance example |
|---|---|---|
| P1 → P2 | Accepted triangle/patch geometry, source and instance IDs, frame, timestamp, area and normal/optical evidence | Reject generative RGB and dimensionless ratios as optical surfaces |
| P2 → P3 | Incident daily exposure, exact instance/scope/basis, coverage, scenario/calibration match | Reject partial tissue masquerading as whole-plant DLI |
| P3 → P4 | Trajectory and weight, interval endpoints, full organ state/event identity, reviewed mass demand | New-organ mass is charged; terminal events add no fabricated surface |
| P2 → P4 | Original samples, fixture inventory, area weights, interval coverage, compatible light basis | Sum simultaneous fixtures before nonlinear photosynthesis; keep replicates separate |
| Shared | mm/cm2/m2, degree/radian conventions, aware times, calendar/development clocks, hashes, null/empty/unavailable mappings | Round-trip reversible representations with reasons preserved; check model computations forward only |
| Canopy ↔ instance | Placement transform plus original shared-canopy context | Splits retain neighbor shading; each plant retains separate carbon pools |

Schema strings alone are insufficient pins: P2 uses an additive `light-growth-1` extension and P3 retains `probabilistic-compound-1` with new fields. Freeze schema/code hashes and capabilities in the eventual adapter manifest, or adopt an explicit version policy before migration. Current strict hash checking already prevents silently treating older packages as current.

## Recommended order

1. Keep completed P2 angular, P3 D8-D10 and isolated P4 software work closed; do not recreate them.
2. Fix the P3 semantic binding guard and complete P1/P2 real-input readiness records within their own projects. Obtain Claude decisions for DLI basis, organ mass mapping and physiological accounting.
3. Decide whether the original light-driven direction and dynamic geometry/reserve objectives are later extensions or explicitly deferred scope. The current D9 and fixed-snapshot contracts do not implement them.
4. Freeze one small synthetic common fixture and the conversion contract for later integration. Under D3, do not start adapter execution until the coordination gate is released after current project goals.
5. When authorized, require numerical P1-P2-P3 correctness; allow an explicit unavailable P4 under D6. Then validate physical light and longitudinal growth with independent real observations. Software tests, GPU success and biological accuracy remain separate acceptance levels.

## Historical statements now superseded

- P2 is no longer waiting for a core-owner callback; actual producer-to-consumer software is delivered.
- P4 is no longer specification-only; the isolated runtime is implemented.
- P3 clock-only environment flags have been replaced by a full dependency audit; legacy unknown provenance still needs truthful unavailable status.
- The strict byte-identical versus new-fields ambiguity was explicitly resolved for P3.
- Lamp duration/full-output fraction are confirmed; start/end clock windows remain open.
- Old TODO entries must be interpreted with their appended completion/supersession records. Do not reopen settled work or erase history.

No active source code, original handoff contents, human configuration or observations were modified by this review. Recommendations remain review findings, not newly adopted biological equations.

