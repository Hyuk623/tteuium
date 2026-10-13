# P1 prompt for growth pack V2 observation support

Recipient: existing P1 3D reconstruction chat. Date: 2026-10-04.

Read the repository rules, LOG tail/TODO, [V2 implementation handoff](CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md), [current decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), [ownership index](CODEX_GROWTH_PACK_V2_CHAT_PROMPTS_INDEX_2026-10-04.md) and your [previous readiness report](CODEX_P1_GROWTH_SCIENCE_READINESS_2026-10-04.md).

Also read [technical review fixes](CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md), which overrides conflicting earlier instructions through D19-D21. Deliver the P1 evidence-gate and Day-1 protocol delta alongside the V2 observation-support work. Write a brief before work; do not rerun unrelated reconstruction or the previous full audit without a new reason.

## Latest decisions

D14 now approves optional reanchor weights and posture offsets, plus explicit truss-observable support. The previous wording that these features are unadopted is historical. P3 owns their implementation. V2 does not supply weights, covariance, posture offsets or observed events.

D15-D18 resolve the P4 policy: absorbed light for the dwarf route, before_mito, carbohydrate-equivalent maintenance and evidenced adaxial-only exchange. Both-face exchange is unavailable. P3 continues to use reference-position incident DLI. No root/physiology measurement or biological acceptance follows from an image.

## Work

1. Inspect only evidence relevant to these new consumers and report exact current producer fields/functions, units, provenance and missing values:
   - Matched same-organ observations and trait-specific measurement uncertainty for optional reanchor weights.
   - Timezone-aware capture time, actual lamp schedule and declared reference phase for posture-offset evidence.
   - Event observations with their explicitly recorded meaning; first-open flower and visible bud are not interchangeable.
   - Reviewed patch/leaflet identity, one-sided physical tissue area, surface orientation and any actual biological adaxial/abaxial evidence.
2. Preserve the prior findings where unchanged: real supported physical area and longitudinal identity are not yet accepted. Do not promote segmentation confidence, reprojection error or seed variation into a covariance estimate.
3. Do not infer botanical adaxial identity merely from a mesh winding, a positive normal, camera visibility or upward orientation. Document what orientation evidence exists and what P4 cannot yet accept. P2 owns illumination exposure; P1 alone cannot certify that a patch receives only adaxial illumination.
4. Document the P3 input dependencies without creating a new covariance model or automatic event mapping. Prepare the now-approved D21 recording template below; do not invent a different measurement protocol. Range/order checks on normalized stations do not establish anatomical correspondence.
5. Update current P1-owned readiness guidance in a new addendum/report. Preserve historical audit files and human records. Missing observations remain unavailable; the newly fixed visible_bud protocol definition does not supply an observed bud count, lamp phase, leaf face or organ ID.

## Technical review evidence gate

Before issuing a downstream-eligible real `area_basis_id`, require all four evidence groups: physical scale (ChArUco square-size calibration record and residual), pose (per-frame reprojection residual and declared threshold), aware capture time with capture_phase, and one-sided area basis with coverage fraction and occlusion statement. Bind physical identity associations to the exact partition hash and reviewer.

Inspect existing P1-owned surface/area export gates, including `tools/compound_surface.py::audit_surface`, and add only missing evidence validation/reporting at the proper boundary. Distinguish identifiers in explicit synthetic tests from accepted real area-basis claims. Missing evidence produces unavailable and a reason; do not manufacture evidence from reprojection quality alone. Do not change reconstruction physics.

Do not supply dimensionless per-photo ratios, projected mask areas, generated RGB, unreviewed regions or unsupported estimated_total_area as physical tissue area to P2/P3. Tests should remove each required evidence group from a valid synthetic fixture and verify refusal of the real-eligibility claim; preserve source data and intentional synthetic status.

## D21 Day-1 recording template

Plants already exist; the user's recording protocol starts now rather than waiting for V2 software or the PPFD meter. P1 owns the blank template and user checklist; P3 owns read-only G06/G07 back-fill/import. Do not edit P3 loaders concurrently.

Generate `measurements/day1_protocol.template.csv` beneath your fresh build output directory with these exact columns:

```text
plant_id,capture_session_id,captured_at,capture_phase,node_count,node_count_source_ref,truss_observable,truss_visible_bud_count,sowing_date,transplant_date,notes
```

Use a header-only template and a clearly separate synthetic example if needed. Do not populate live plant observations. In the accompanying checklist specify:

- early_photoperiod: 2 h after actual lights-on; late_photoperiod: 2 h before actual lights-off. Record aware timestamps and actual schedule evidence; unknown clock times do not justify inferred phase.
- New protocol truss_observable is explicitly visible_bud, not anthesis or fruit set. Zero means observed zero; blanks mean unknown. Do not relabel older ambiguous truss records.
- Day-0 node count is a per-plant integer supported by a reviewed counting-rule source. Visible leaf count is not automatically cumulative node rank.
- Sowing/transplant dates are entered only if known. Existing organ absolute age remains unknown unless independently supported; do not estimate it from these dates alone.

Provide a mapping note to P3 and retain source hashes for any supplied records. Template preparation and loader support do not mean that the human has already taken measurements.

## Scope and delivery

This scope now includes evidence-gate corrections and the approved Day-1 template/checklist, superseding the prior read-only/no-protocol restriction. Human recording under D21 may start immediately; this task must not invent records or perform physical acquisition on the user's behalf. No GPU generation, inference/training, new physical reconstruction algorithm, photosynthesis code or P3/P4/calibration edit is requested.

Save `handoff/CODEX_P1_GROWTH_PACK_V2_EXECUTION_2026-10-04.md` with a compact field/evidence/gap table, changes from the previous readiness report and exact downstream owners. Put generated audit metadata in your own fresh build subdirectory, preserving source hashes. Verify references and append LOG/TODO. If no evidence changed, state that directly rather than rerunning unrelated tests or declaring improved physical accuracy.

Use a fresh `build/technical_review_fixes_20261004_01/P1/` subdirectory for this supplement, including the measurements template and JUnit for any changed gate. Report technical-review section 6 and D21 separately as done/already present/deferred. Do not overwrite the shared final technical-review report; coordination will consolidate the per-project reports.
