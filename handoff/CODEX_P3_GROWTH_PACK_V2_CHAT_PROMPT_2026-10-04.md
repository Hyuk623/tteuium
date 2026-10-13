# P3 prompt for growth pack V2 observation options

Recipient: existing P3 growth-direction chat, including calibration ownership. Date: 2026-10-04.

Implement the remaining P3 delta in [V2 handoff](CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md). Read rules, LOG/TODO, [D11-D18](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), [ownership index](CODEX_GROWTH_PACK_V2_CHAT_PROMPTS_INDEX_2026-10-04.md) and your [completed Science delivery](CODEX_P3_GROWTH_SCIENCE_EXECUTION_2026-10-04.md). V2 supersedes the older optional-feature and undecided-Q2 descriptions.

Write a brief and inspect actual `_remaining`, `update_forecast`, likelihood, event and input-validation paths. Do not rely on obsolete line numbers. Own only P3/calibration runtime, related tests/templates/guides and your report. P4 owns physiology and registry.

Also apply [technical review fixes](CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md), which overrides conflicting V2 wording through D19-D21 and P3-a through P3-f. Merge overlapping requirements into one implementation.

## Preserve delivered behavior

F2/F3/F7/F8/F9/F11 and D11/D13 were delivered with 174 passing tests. Verify them against V2, retaining existing sub-base zero-knot behavior, original trajectory denominators, reference-DLI width meaning, beta restriction, ordered ESS stages and calibration guards. Repair genuine gaps; do not reimplement already correct functions.

P3 still receives incident reference-position full-local-day DLI, not P4 absorbed tissue light. Preserve distinct coefficient identities per curve, applicability bounds, frozen pre-run calibration and no L02-to-direction binding. Do not change biological coefficient values, covariance laws or growth equations through this task.

## New implementation

### D14a Reanchor weights

Add explicit `reanchor_weight` in [0,1], default 1 for the existing manual-weight path. Default outputs must reproduce current reanchoring, including the remaining-increment interpretation for beta.

For opt-in covariance-derived weights only, use `omega = variance_state/(variance_state+variance_measurement)` with declared compatible trait/unit covariance. Missing, invalid or non-identifiable variance evidence must not silently become a fitted weight or fallback certainty. Define zero-denominator and unsupported cross-covariance handling as unavailable, consistent with V2's missing-science rule. Do not introduce an unapproved multivariate Kalman update.

Apply the weighted observation displacement consistently to exponential and beta reanchoring. Record current displacement and cumulative `sum(abs(omega*delta))` in update.json per organ/trait/unit, carrying the previous accumulated value through continuation. Never sum mm, cm2 and radians into one scalar. Do not double-count repeated processing of the same update or apply the correction twice.

Tests: omega=1 matches the delivered baseline; omega=0 adds no observation displacement to the anchor; an intermediate weight gives the stated displacement; covariance mode is opt-in and uses declared variances; invalid scientific evidence produces structured reasons; cumulative reporting survives consecutive updates. Preserve valid geometry or report unsupported trait correction rather than inventing a new shape law.

### D14b Observation-only posture offset

Add the optional observation model `theta_observed = theta_state + delta(phase) + error`, with delta(reference_phase)=0. Correct the likelihood residual under declared angle units, phase/time reference and offset evidence. Do not add delta to the structural state, growth parameters or future geometry.

Offsets remain null/disabled unless explicitly supplied; never fit them from this task's fixtures or infer phase from nominal photoperiod duration. Nonzero reference offset or missing evidence in an enabled model must have an explicit outcome. Preserve angle wrapping.

Tests: disabled/zero offset preserves previous likelihoods; enabled offset changes the appropriate likelihood and may change posterior weights, while each pre-existing trajectory state is unchanged by the posture term itself. Ordinary separately specified reanchoring can still alter anchors; do not conflate these effects.

### D14c Explicit truss observation meaning

Add `truss_observable` to the truss rule/evidence contract and relevant event outputs. D21 now fixes visible_bud for newly recorded Day-1 protocol data. This is an explicit protocol declaration, not permission to infer a meaning for legacy records. An undeclared legacy meaning makes the truss rule unavailable; do not invent visible-bud observations from old counts or first-open-flower records.

Preserve distinct leaf, node-budget and terminal logic. Unavailable truss evidence is not zero trusses, an absent plant or grounds to delete a trajectory. Match event evidence only under compatible declared observable semantics. Do not add anthesis timing, reproductive biomass or sympodial growth.

Tests: missing observable gives structured truss unavailability; explicit supported meaning is retained; incompatible event meaning cannot silently condition trajectories; unrelated leaf/terminal behavior and counts remain correct. This explicit missing-field rule takes precedence over generic default-preservation wording.

## V2 input and failure contract

Audit new required scientific inputs and existing strict entry points. Missing domain/evidence/observable is structured unavailable with a reason, not an uncaught exception or fabricated default. Malformed data may still raise. Publish the classification and test real CLI/JSON/CSV behavior; do not broadly swallow programming errors.

Current DLI field is `light_response.applicability_interval`, while V2 names `dli_applicability_interval`. Document an explicit compatibility mapping/canonical field in schema/templates/guide and reject conflicting duplicate declarations. No numeric interval is inferred. Keep F3 trait-level availability and original ensemble coverage.

Keep existing F9 tests for remaining increment versus absolute target, clock-before-binding, fitted p_stop versus node budget and light-direction provenance. P4 policy updates do not permit its outputs to adjust P3 weights or geometry.

## Technical review P3 changes

| Item | Required delta | Acceptance |
|---|---|---|
| D19 | Import DLI_UNIT from tools.leaf_light.common; use it in ENV_UNITS, applicability checks, _validate_d9, calibration-facing inputs and templates | mol/m2/day passes; legacy mol/m2/d returns legacy_dli_unit_spelling with missing/different-field diagnostics, no auto-correction or numeric conversion |
| P3-a | Split summary support into existence_mass, computable_mass and available_mass, the intersection, with explicit original-ensemble denominator | Not-yet-appeared/terminated-scope biological outcomes are distinguishable from parameter/low-DLI computational failure; neither is silently dropped or called zero growth |
| P3-b | Name the event likelihood stage hard_admissibility; report n_particles_rejected_by_events alongside ESS | Geometry likelihood times Boolean event indicator applied once; same final normalized weights for either multiplication order on a fixed bank; stage ESS remains order-dependent |
| P3-c | Confirm absolute_extent_target_at_reference_DLI versus absolute_potential_maximum protection already exists | Add only a missing cross-binding regression; do not rewrite the working taxonomy |
| P3-d | Check helper-generated lower zero knots against _validate_d9 knot equality/normalization validation | Generated explicit sub-base knot passes full validation and pauses development; undeclared out-of-domain and other normalization failures remain refused |
| P3-e | Missing legacy light-response fields produce legacy_light_response_underspecified with the complete missing/different-field list | No inferred basis, applicability interval, time basis, plane/day, or coefficients; scientific unavailable is structured, malformed input remains distinct |
| P3-f | Inspect supplied P2 tissue manifest and reject reference basis collisions in the P3 consumer direction | Collision refused even when the producer metadata claims validity; valid distinct reference passes |

P2 alone adds the shared DLI_UNIT constant; inspect its published change or existing file before importing. Do not define a second constant, edit the common module concurrently, or temporarily accept the legacy spelling. Complete independent P3 work while that small dependency is pending and report it accurately. Historical frozen configs remain unchanged; regenerate explicit new configs rather than patching hashes.

Require applicability provenance carried from reference_position.json::applicability_source_ref to reference_dli.json and the P3 interval object; it must identify the P3 parameter-pack coefficient domain. Do not accept arbitrary sensor metadata as a model domain. Update the bounded synthetic P2-to-P3 validation fixture using canonical units only; no growth-model integration run is implied.

For P3-a, define each mass per reported trait/scope and retain IDs/weights/reason provenance. A terminated apex does not imply that all existing leaves cease to exist; apply terminal biological scope to the relevant prediction, not indiscriminately to every organ. Report unavailable computational support separately from biologically not-yet-present states. Document whether each reported mass is a sum of normalized original weights and how conditional quantiles use available_mass.

For P3-b, order invariance concerns multiplication of fixed geometry/event likelihoods before normalization, not reanchoring between stages. All-zero support remains incompatible. Do not claim that sequential ESS losses form an order-independent causal decomposition. Make the rejected-particle count definition explicit and test raw count versus weighted rejected mass separately where both are reported.

## D21 read-only Day-1 import and back-fill

P1 owns the template `measurements/day1_protocol.template.csv` beneath its fresh build output. Implement or extend P3-owned G06/G07 record loaders to consume its exact columns without editing original human files:

```text
plant_id,capture_session_id,captured_at,capture_phase,node_count,node_count_source_ref,truss_observable,truss_visible_bud_count,sowing_date,transplant_date,notes
```

Preserve source hash/row identity, declared aware times and phase labels. early_photoperiod means 2 h after actual lights-on, late_photoperiod 2 h before actual lights-off. Back-fill new schema fields only from explicit recorded information; do not retrospectively estimate phases or dates. Preserve visible_bud semantics and zero versus blank. Day-0 node count requires the reviewed counting-rule source, feeds the existing N_max lower truncation, and is not derived from visible leaf count. Sowing/transplant dates do not establish existing organ ages.

Test header-only templates, valid explicit synthetic records, missing timestamps/source/observable, incompatible event meaning and source immutability. Do not treat a template row as an actual observation or fabricate historical records. Human recording starts now independently of loader completion.

## Validation and delivery

Freeze a valid current baseline and run focused D14/failure tests, then relevant P3/calibration regressions including `test_p3_growth_decisions` and existing semantic cases. Confirm `test_legacy_golden_numerical_payload` and `test_prepare_light_delegates_existing_bridge` in the Windows environment if included in the owning suites; report pre-existing failures honestly.

Use synthetic explicit assumptions only. Save JUnit and an isolated demo to your own fresh P3 subdirectory under `build/growth_pack_fixes_20261004_01/`. No real fitting, new parameter adoption, cross-project run or experiment.

Save `handoff/CODEX_P3_GROWTH_PACK_V2_EXECUTION_2026-10-04.md`: per-item implemented/already satisfied/deferred status; changed APIs/fields/units/reasons; default numerical compatibility versus intentional truss availability change; commands/results/hashes; equation-to-function map for P4. Append LOG/TODO. Do not edit P4's registry or the shared final roll-up report.

Include D19/D21 and P3-a through P3-f in that report, retaining done/already present/deferred distinctions. Save the technical-review suites and synthetic demos under fresh `build/technical_review_fixes_20261004_01/P3/`; verify the named Windows regressions. Coordination owns the eventual CODEX_TECHNICAL_REVIEW_FIXES_EXECUTION_2026-10-04.md, preventing concurrent final-report edits.
