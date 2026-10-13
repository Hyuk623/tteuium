# Four project changes and remaining work

Date: 2026-10-03, Asia/Seoul. Prepared for the user and Claude coordination from the four chats' latest review handoffs. This is a consolidation and proposed work list, not implementation authorization. No active code, prior handoffs, configuration or observations were changed. No tests, models, fits or integration runs were executed for this document.

Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`. Paths below are relative to that root. Preserve ownership in `AGENTS.md` / `CONVENTIONS.md`: core and root tests belong to Claude/core owner; support tools and their tests belong to Codex. Each chat retains its current scope. No cross-chat message was sent.

## 1 Authoritative sources and current status

| Project | Latest consolidated source | Current status supported by that source |
|---|---|---|
| P1 `3d구현` | `handoff/CLAUDE_DETECTION_DIFFUSION_HANDOFF_2026-10-03.md` | Detection relative-area baseline and isolated ViewFusion trial tooling delivered. Actual GPU trial blocked on execution destination/upload choice. No generated result bundle or completed inference. |
| P2 `광시뮬레이터` | `handoff/CLAUDE_LIGHT_GROWTH_READINESS_HANDOFF_2026-10-03.md` | Spatial/side/area/time exports, reviewed observation joins, consumer checks and reversible reporting splits delivered. Full readiness blocked on protected-core angular diagnostics and subsequent export integration. Latest package is `_04`. |
| P3 `생장방향` | `handoff/CLAUDE_GROWTH_CALCULATOR_REVIEW_HANDOFF_2026-10-03.md` | Assumption-conditioned 30-day calculator delivered. Scientific review, cultivar fitting and independent biological validation remain distinct. A specific environment-dependency metadata issue is identified below. |
| P4 `토마토 FSP` | `handoff/CLAUDE_FSP_REVIEW_HANDOFF_2026-10-03.md` | Calibration foundation and proposed physiological specification/evidence delivered. Production carbon diagnostic is not implemented; scientific review remains pending. |

Cross-project authority: `handoff/CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` (D1-D7, including the 22:24 KST follow-up). Background inventories: `CLAUDE_FOUR_PROJECT_ENV_IO_HANDOFF_2026-10-03.md` and `CODEX_FOUR_PROJECT_INTEGRATION_DECISIONS_REVIEW_2026-10-03.md` in the same directory. Later evidence below supersedes stale status claims in those dated snapshots; history is not rewritten.

Rules retained: P3 alone realizes growth/direction/size; P4 runtime output is diagnostic and cannot modify P3 geometry, parameters, weights or seeds. Cross-project linking remains deferred until current goals finish. First integration tests synthetic conversion correctness, not biological accuracy.

Follow-up decisions are settled, not questions to reopen: **D5** includes the offline calibration route before P3, with an explicitly selected frozen/hashed fitted pack and recorded light/environment dependence; never an implicit runtime operation. **D6** requires numeric P1 -> P2 -> P3, with optional frozen calibration-pack selection; P4 may return unavailable with reasons and is not a numeric first-pass blocker. **D7** limits inverse round trips to reversible representations; computations/reductions use forward correctness invariants and preserved source detail.

Priorities below describe dependencies, not permission: **P0** resolves a current blocker or must precede the affected code; **P1** is needed before the final integration/acceptance; **P2** is later real-data or biological validation. Kind distinguishes a code correction, specification decision, execution dependency and external evidence.

## 2 P1 3D implementation and diffusion

Retain the delivered first-label area normalization and immutable cached-mask workflow. The 1,318 rows are per-photo observations, not unique physical leaves. Keep relative areas dimensionless. Public pretrained models are already permitted for this comparison; do not reopen that exception. It does not authorize private-photo upload.

| ID / priority / kind | Required change or remaining work | Responsible owner and files | Completion evidence |
|---|---|---|---|
| P1-A / P0 / execution dependency | Resolve the already pending GPU destination and private-photo transfer choice. There is no live job to monitor. Do not launch an unapproved upload or CPU fallback. | User provides destination/transfer choice; P1 Codex records it in `CODEX_MULTIVIEW_COMPLETION_EXECUTION_2026-10-03.md`. | Specific usable runtime and authorized data-transfer scope recorded; this alone is not a successful model run. |
| P1-B / P0 / comparison specification | Define common target views and evaluation coordinates for multiview versus top-only trials. Current target azimuths differ. Use target definitions that do not leak side/held-out information into top-only conditioning; preserve failed pose gates and unavailable camera mapping. | Claude specifies comparison; P1 Codex adjusts request/preparation/evaluator under `tools/multiview_completion.py`, `completion_package.py`, `completion_viewfusion.py` only when separately invoked. | Frozen conditioning/target/evaluator split, dependency-closure audit, comparable output view definition or explicit lack of comparability. No score for an unverified alignment. |
| P1-C / P0 / runtime verification | Validate isolated GPU dependencies and checkpoint loading, including legacy imports/CLIP and the actual `weights_only`/memory assumptions. Document compatible versions/patches; do not change the existing program's global environment or silently patch the pinned vendor tree. | P1 Codex in selected isolated runtime; runner/package docs and manifest. | Successful imports and checkpoint construction, observed resource use, source/checkpoint hashes and bounded-run settings, or explicit failure evidence. |
| P1-D / P1 / authorized trial completion | Execute both trial arms after A-C, preserve every declared seed, return/import complete candidate bundles and inspect their evaluation/review artifacts. | P1 execution owner; `tools/MULTIVIEW_COMPLETION.md` and `build/multiview_completion_20261003_01/` current preparations/archives are references. | Actual runtime outputs, generated PNGs, candidate/status manifests and hashes; no inference claim from preparation/tests. Scientific unavailable metrics remain unavailable. |
| P1-E / P1 / interface boundary | State precisely what the trial produces: `novel_view_rgb`, not metric leaf surface or observed hidden anatomy. Keep candidates separate from observed masks/triangles. Identify reviewed metric tissue/compound-axis inputs required by P2/P3 as separate prerequisites. | Claude review plus P1 final IO supplement. | Explicit representation/provenance/scale/optical eligibility and observation identity; no RGB-to-metric or ratio-to-gC promotion. |

P1-E does not ask to build a new reconstruction engine in this task. If metric hidden-surface reconstruction becomes a requirement, Claude must supply a separate reviewed contract. Known absent confirmed correspondences, independent leaf-area references and missing metric evidence are external limitations, not something to repair by inventing data.

## 3 P2 light simulator

Do not rebuild the delivered spatial, scalar/side, time, area, transforms, splits or independent consumer. The latest handoff records 266 earlier regressions and 32 final focused checks; these counts are historical and have not been rerun here. The prior reader gaps were reported fixed. Preserve `_03` as the source bundle used by `_04`.

| ID / priority / kind | Required change or remaining work | Responsible owner and files | Completion evidence |
|---|---|---|---|
| P2-A / P0 / missing core interface | Add optional backward-compatible per-emitter/path diagnostics to `direct_light`: fixture/receiver/path identities, expected inventory/chunk coverage, attenuated cosine-weighted PPFD, actual receiver-to-light arrival vector and validity. Preserve zero versus unknown and existing transport behavior. | Claude/core owner: `tomato3d/light/raytrace.py` and core tests. Exact contract is in `CLAUDE_LIGHT_GROWTH_READINESS_HANDOFF_2026-10-03.md`. | Legacy scalar/side parity with diagnostics disabled/enabled; contribution sums reproduce arrays; chunk omissions/duplicates and unknowns are detectable; resource overhead documented. |
| P2-B / P0 after A / export integration | Connect real diagnostic contributions to F/M/B angular moments, fixture/time scaling and grow/board/observed-local frame exports. Update consumer/capabilities only for channels actually supplied. | P2 Codex: `tools/light_growth_bridge.py`, `light_growth_consumer.py`, `light_growth_schema.json`, focused tests. | Actual transport-to-export-to-consumer evidence for direction, scalar/side parity, opposing-light cancellation, rotation and temporal aggregation. Algebra-only fixtures do not complete this requirement. |
| P2-C / P1 after B / fresh artifacts | Regenerate affected prepared inputs and outputs because core/code hashes intentionally change. Preserve old evidence and avoid disabling freshness checks. Finalize the schema/IO and requirement audit. | P2 Codex; fresh `build/` package and execution/IO handoffs. | New complete package plus per-instance split validation, reproducible source/config/code hashes, completed original angular requirements and honest remaining real-input blockers. |
| P2-D / P2 / physical input evidence | Supply reviewed metric optical tissue, lamp scene/optics/placement, compound/time/axis associations and independent light calibration for real use. | Human/reference provider plus Claude review; P2 validator reports missing inputs. | Actual scoped measurements/reviews and validation. Synthetic transport does not close physical accuracy. |

Native spatial/side/angular channels remain unsupported unless separately implemented. Do not mix native scalar results with direct angles under one backend label. Keep normal-side distinct from botanical upper surface. Reporting separation retains full-canopy shadows; it is not an isolated-plant rerun. The scalar prerequisites for a future carbon index are distinct from the still-open full directional-light objective.

## 4 P3 growth direction and realized size

Retain the existing engine and its measured-origin preservation, trajectory dependencies and optical-ineligible future envelopes. D1 already matches the architecture. Do not replace it with a second growth engine or rewrite it merely to consume a diagnostic score.

| ID / priority / kind | Required change or remaining work | Responsible owner and files | Completion evidence |
|---|---|---|---|
| P3-A / P1 / confirmed metadata limitation | Audit environmental dependence across conditional families, stop logits, development clock and preselected calibrated parameters. Current `sample_forecast` derives `environment_used`/`light_used` only from the clock branch; this can hide real feature dependence. Clarify the handoff's statement that environment is metadata unless a response is declared: family/stop coefficients are response paths too. | Claude agrees metadata semantics; P3 Codex later updates `tools/probabilistic_compound_growth.py`, associated docs/tests. Preserve old field compatibility or version the changed meaning explicitly. | Config with calendar clock + nonzero PPFD family coefficient is reported as dependent; clock-only, stop-only, no-effect and provenance-unknown cases are differentiated. Reporting change does not change seeded forecasts. |
| P3-B / P0 before biological adoption / scientific review | Give retain/revise/unresolved decisions for appearance versus initiation, stopping/no-loss/provided-axis scope, fixed stem directions, anchored expansion/rotation and shared/AR covariance. No actual biological change is mandated until a reviewed discrepancy or better-supported contract exists. | Claude scientific review of `CLAUDE_GROWTH_CALCULATOR_REVIEW_HANDOFF_2026-10-03.md`; P3 Codex implements only exact later requirements. | Decision table with evidence/domain/identifiability; every requested code change identifies failing case, function, expected behavior and acceptance. Unknown coefficients remain unknown. |
| P3-C / P1 / export and future diagnostic boundary | Preserve full trajectory/source shapes, not just `block_states.csv` maximum extents/summary quantiles. Specify how later adapters derive matched per-trajectory interval increments, including births, missingness and changed area basis; no P4-driven clipping or reweighting. | P3 documents exact exported state; final coordinator specifies the adapter after D3. Do not implement cross-project linking now. | Frozen IDs/time/units/area basis and full-shape references; synthetic origin/increment consistency and P4 nonmutation checks planned. Summary outputs are not misrepresented as reversible full geometry. |
| P3-D / P2 / real validation | Obtain repeated confirmed whole-compound/parent states, visibility/event intervals and independent targets; review update likelihood/support and fresh-horizon restrictions. | Human/reference provider, Claude, then P3 validation owner. | Actual chronological held-out plant/unit scores at available horizons. Existing synthetic example cannot establish real 30-day accuracy. |

The current legacy flags are an evidence/reporting issue, not proof that the growth arithmetic is wrong. Adding a broad boolean alone is insufficient if it conflates configured response, nonzero active effect, historical fitted dependence and unknown provenance. Prefer an explicit reviewed per-path dependency record.

## 5 P4 FSP calibration and diagnostic physiology

Retain the completed calibration foundation (`anchored_expansion`, `azimuth_rotation`, `lognormal_wait`) and its recorded 93-test delivery. The physiological specification/evidence stage is also delivered; its production diagnostic was not part of that completed code delivery. New runtime code requires its own reviewed, separately invoked task.

| ID / priority / kind | Required change or remaining work | Responsible owner and files | Completion evidence |
|---|---|---|---|
| P4-A / P1 / apply settled D5 | Retain offline `apply_parameter_set` before P3 as an explicit step when a frozen fitted pack is selected. Record pack/config hashes, scenario/domain and fitted light/environment dependencies. Runtime `compute_carbon_sufficiency` must not invoke fitting or parameter adaptation. No new scope decision is needed. | Final integration specification owner, then P4/P3 adapter owner after D3. Update stale review wording by supplement. | Explicit pre-run selection/config creation; provenance survives into P3 and diagnostic reporting. Runtime diagnostic leaves P3 parameters, states, events, weights and seeds unchanged. |
| P4-B / P0 before diagnostic implementation / scientific decisions | Resolve NRH incident/absorbed and net/before-mito interpretation, respiration ownership, CH2O/CO2 and structural/total-mass conflicts, growth-cost conversion, root/fruit coefficient ordering, initial pools and P3 geometry-to-demand identifiability. | Claude scientific review using contract and source/equation/parameter registries. Return a review response, not guessed defaults. | Per-item retain/revise/unresolved plus source locator, compatible units, applicability and unavailable conditions. Target-cultivar validity remains separate from source recovery. |
| P4-C / P1 / contract consistency | Separate active diagnostic APIs from inactive counterfactual allocation/form/trajectory APIs in final adopted prose and machine map. Preserve section 10 precedence. Earlier missing-function issue is already fixed; remove only remaining ambiguity about a separate realized trajectory. | P4 specification owner: `CLAUDE_FSP_PHYSIOLOGY_CONTRACT_2026-10-03.md` and a versioned successor/supplement to `build/fsp_physiology_spec_20261003_01/integration_map.json`. Preserve original evidence. | Consistent active entry points, outputs/statuses and no geometry-override interpretation. Runtime implementation flags remain false until actual code exists. |
| P4-D / P2 after A-C / optional later diagnostic implementation | If separately invoked, implement pure carbon-sufficiency calculation using same-plant/trajectory/interval supply, reserves, demand and accounting basis. Keep no-demand, maintenance deficit, growth deficit, inconsistent mass inference and missing-input states. D6 makes numeric diagnostic implementation optional for the first pass; a reasoned unavailable result is acceptable. | P4 Codex, proposed isolated `tools/fsp_physiology.py` and tests; not implemented by this consolidation. | If implemented: synthetic unit/carbon/nonmutation tests and finite/null ratio rules. For first-pass unavailable: correct status/reasons without fabricated gC values or a claim of a numeric four-project pass. |
| P4-E / P2 / physical and biological evidence | Supply compatible mass/allometry, root/reproductive scope, reserves, carbon fractions, gas-exchange/respiration evidence and independent comparisons. | Human/reference provider and Claude. | Evidence supports each active quantity/domain; missing values continue to gate affected outputs rather than become zero. |

The new diagnostic contract already includes `available_growth_carbon_gC,required_growth_carbon_gC,sufficiency_ratio,maintenance_deficit_gC,growth_deficit_gC,status,limiting_inputs,assumptions,source_hashes`. Its zero-demand and maintenance-deficit rules are specified; do not ask another agent to invent them from scratch. Review assumptions and synchronize the serialization/error contract before writing code.

## 6 Completed or corrected items that must not be reopened

| Earlier issue | Current evidence | Treatment |
|---|---|---|
| P1 public pretrained model restriction | P1 handoff records an explicit trial-only exception | Resolved for this comparison; GPU destination/upload remains a different unresolved dependency. |
| P2 had no time/spatial/area/split package | Current bridge, consumer, schema and `_04` package/handoff | Delivered supported channels. Only actual angular transport and associated integration remain in the full light objective. |
| P2 reader accepted invented direction or inconsistent transformed totals | Latest handoff records reproduced failures and strengthened final checks | Recorded fixed; do not relist as an outstanding bug without new evidence. |
| P3 calculator merely proposed | Completed execution report and code, 92 recorded tests | Software delivered; scientific review is separate. |
| P4 calibration still in progress | Latest execution/review handoffs report completed code and 93 recorded tests | Update future snapshots to delivered; no need to refit or rebuild to prove activity. |
| `integration_map.json` omits `compute_carbon_sufficiency` | Direct read now shows the function and `coordination` with P3 ownership/P4 diagnostics | Specific omission resolved. Remaining `proposed_use` phrase still says separate integrated physiology trajectory, so P4-C concerns clarity, not absence. |
| Dwarf tomato full source inaccessible | P4 source recovery and review handoff | Resolved for the recovered paper/code. Source inconsistencies/applicability and other access limits remain. |
| Offline calibration inclusion, mandatory numeric index and universal inverse round trips were unresolved | Coordination D5-D7, added 22:24 KST | Resolved: explicit pre-P3 frozen pack route included; numeric P4 optional in first pass; inverse tests only for reversible representations. Do not ask these decisions again. |

## 7 Shared changes after independent work, not now

The coordinator's final integration document should resolve these items without directing active chats to edit each other's files:

1. **Goal gate:** record what evidence closes each chat's actual current goal. P1 trial and P2 directional-hook goals are still incomplete. P3 code and P4 calibration/specification goals are delivered; do not retroactively redefine them as requiring real biological validation or a new P4 production module. D6 permits first-pass P4 unavailable with reasons, so diagnostic implementation is not an added blocker. D6 does not close P1/P2's original incomplete goals.
2. **Versioned adapter contract:** freeze completed producer code/schema/config hashes and explicit mappings for source plant versus instance, physical leaf/compound versus prediction ID, session/time, area basis and frame. Preserve clones, ambiguity and source evidence.
3. **Conversion policy:** name mm/m2/cm2, rad/deg, incident/absorbed photons, instantaneous/integrated light, calendar/development time and missing-token differences. Existing helpers should be reused. Preserve original detailed data for round trips; aggregation and physiological/model computation are not invertible conversions.
4. **Complete path:** P1 supplies both reviewed optical geometry to P2 and reviewed axes/attachments to P3. P2 supplies light with explicit scenario/time/area basis. P3 alone advances geometry; P4 reads matching increments and light/environment for diagnostics. P4 outputs have no automatic path back into P3.
5. **Acceptance fixture:** use explicitly synthetic tissue/axis/parameter inputs with fixed seeds, and an explicitly selected frozen calibration pack where that route is exercised. Verify numeric P1 -> P2 -> P3, conversion/import/export invariants, missing-input behavior and runtime P3 nonmutation. P4 unavailable with reasons passes its D6 reporting requirement; describe the result as numeric three-project integration plus P4 diagnostic status. Synthetic mass/carbon inputs are required only if a numeric diagnostic is additionally exercised, not fabricated to force it.
6. **No implicit closed optical loop:** future P3 envelopes remain ineligible. Label any held-current-geometry supply scenario. D4 does not quietly authorize future tissue generation, inference, native jobs or feedback.

Deliver final adopted fields/functions/units/statuses and scoped commands only after these decisions and D3's goal gate are satisfied. This document is not that final implementation prompt.

## 8 Suggested order and expected returns

1. Claude/core owner resolves **P2-A**, while the user/P1 owner resolves **P1-A** and Claude specifies **P1-B**. These independent blockers can be addressed without cross-project integration.
2. Respective owners complete **P2-B/C** and **P1-C/D**, retaining their boundary reports. No duplicate scalar exporter or detection pipeline is needed.
3. Claude reviews **P3-B**, agrees **P3-A** reporting semantics, applies settled D5 through **P4-A**, and reviews **P4-B/C**. Scientific unresolved values remain disabled; they do not prevent writing an honest contract or a D6 unavailable diagnostic.
4. Each owner returns a dated retain/revise/unresolved response plus exact files/functions, fields/units, statuses, evidence and remaining prerequisites. The coordinator records completed versus blocked versus new-scope tasks.
5. After the current-goal gate, finalize the D4-D7 synthetic integration contract without requiring numeric P4. Any later numeric diagnostic implementation is a separately invoked extension. Do not launch an end-to-end run merely because this plan exists.

This ordering is a proposal within the recorded no-linking decision, not delegation or a message to another chat. The four source handoffs remain the detailed entry points for their owners.

## Source snapshot verification

Reference existence and document coverage were checked during authoring. Hashes identify this read-only snapshot; they are not new execution or independent accuracy evidence.

| Source | SHA256 |
|---|---|
| handoff/CLAUDE_DETECTION_DIFFUSION_HANDOFF_2026-10-03.md | 2504044337aee012517c427f2de64894934aade5d3587a067510d340779d26d1 |
| handoff/CLAUDE_LIGHT_GROWTH_READINESS_HANDOFF_2026-10-03.md | 5e6dce5e5477c1e9dd542d597b7627a4dee25cc35aa7e88dc96e5221e2af9bc0 |
| handoff/CLAUDE_GROWTH_CALCULATOR_REVIEW_HANDOFF_2026-10-03.md | e1fb1ed0c54954a2b46dc6f99effc6295fcc3a164d31572a973df4405f1d0a0a |
| handoff/CLAUDE_FSP_REVIEW_HANDOFF_2026-10-03.md | e6dc6905d65335120ed9d8c536583e1565fbb0a5a386b640d8464ed5b90e1d89 |
| handoff/CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md | 846d02e30a8c3e319a70f42b7d5e98de68b55f957c6b8be0019176a3c95d8680 |
| build/fsp_physiology_spec_20261003_01/integration_map.json | 0145587acf3eec2aad6d64096b84e0f204f0c15dadede3bb4a1934a1edfc737b |
| tools/probabilistic_compound_growth.py | 4ca7dbe5a7f90ee27626b9d86fab38b0fbcdd4614baaa98d42d4a777de950523 |
| tomato3d/light/raytrace.py | 6936a154b67a0cd796f36c8e75760eea61588da9971c7349a29584f1f13747d8 |
