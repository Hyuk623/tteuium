# P1 implementation status excluding GPU execution

Date: 2026-10-04. From Codex to Claude Code.

The user requested a concise handoff of the current P1 status excluding GPU execution. Local observation auditing, completion-runner corrections, package validation and transfer preparation are delivered. Real 3D tissue geometry, area accuracy and optical eligibility remain unvalidated. This document summarizes existing evidence; it does not authorize new runs or cross-project integration.

## Program definition and calculation

P1 audits detected leaf observations, calculates visible-area ratios against the first saved label, and prepares isolated generative view-completion trials while preserving measured geometry and provenance.

For each photograph, `relative_area_i = visible_mask_area_i_px2 / visible_mask_area_first_label_px2`. The first saved label is the fixed reference and has ratio 1. This is dimensionless and can be calculated before physical measurement. A missing or zero reference is unavailable; never silently choose another leaf. Ratios across photographs do not establish growth or persistent physical leaf identity.

## Completed work

| Item | Evidence and limit |
| --- | --- |
| Detection baseline | Audited 1,318 per-photo observations and 54 first-reference ratios; 4,021 source/code hashes matched the recorded baseline. These are not 1,318 unique physical leaves. |
| Area definitions | Mask pixel area, explicit bounding-box proxy, relative area, projected metric area and supported/actual tissue surface area remain separate. A box is not a mask and no ratio supplies absolute scale. |
| Geometry preservation | No replacement of measured poses, board configuration or observed geometry. ChArUco remains the camera-pose source; generated views and nominal rotation angles cannot establish measured scale. |
| Runner corrections | CPU EMA application and buffer release; cached CLIP/VAE conditioning; atomic partial bundles; refusal to import incomplete bundles; strict shared sampler/checkpoint/weight checks; exact-ID leak checks. |
| Trial preparation | Multiview and top-only archives share declared targets and budgets. Held-out image pixels/masks are excluded; top-only also excludes the side image and its derived inputs. |
| Local verification | Latest completion tests: 50 passed. Earlier baseline suite: 55 passed, plus 2 synthetic transform/split checks; these overlapping suites are not additive test counts. |
| Future geometry interface | Inventoried 13 field groups. Reviewed distinct source/instance IDs, inverse transforms and canopy splitting using synthetic evidence. No cross-project adapter implemented. |
| Claude transfer preparation | Both staged ZIP hashes and the launcher's approved manifest hashes/request IDs match the verified delivery. |

## Inputs and outputs

| Interface | Meaning and units |
| --- | --- |
| Observation inputs | Saved labels, images and masks, explicit box data, manifests and provenance; image coordinates in pixels. |
| Observation outputs | Visible area/proxy in pixel squared and first-label area ratios without units; availability reasons remain explicit. |
| Completion inputs | Frozen request, authorized conditioning assets, pinned vendor/checkpoint and declared camera targets. Target angles are degrees and radius uses model units, not measured millimetres. |
| Completion outputs | PNG hypotheses, hashes, runtime/status JSON, partial or final candidate bundle. `novel_view_rgb`, `origin=generative`, `validated_metric=false`, `suitable_for_ppfd=false`. |
| Geometry interface | Existing supported triangle coordinates in millimetres plus identity/frame/area/visibility/quality/eligibility provenance. Missing associations are not inferred. |

Repository data/config roots remain `TOMATO3D_DATA_ROOT` and `TOMATO3D_CONFIG_DIR` through `tomato3d.config.get_settings()`. The completion CLI takes explicit `--request`, `--vendor`, `--checkpoint`, and `--out` paths. No human configuration was changed for this handoff.

## Remaining work excluding GPU capacity

- Confirm cross-view leaf identity, compound/leaflet associations, capture times and frame evidence before temporal or cross-project joins.
- Supply reviewed supported tissue geometry, area basis, normal conventions, optical properties and independent accuracy evidence before real surface-area or light claims.
- Provide a reviewed camera mapping before silhouette IoU or boundary F-score evaluation. Current pose gates remain false; visual plausibility is not validation.
- Preserve P3 ownership of future growth and P4's diagnostic role. Integration remains deferred. Known absent independent area measurements and curved-surface specifications should not trigger repeated searches or invented substitutes.

Separately, genuine complete model returns still require Codex import, seed/target/hash checks and visual inspection after Claude's execution. This document does not report a successful GPU trial or change its blocked status.

## Authoritative delivery references

- [P1 baseline and geometry inventory report](CODEX_P1_CONTINUATION_2026-10-03.md): baseline audit and evidence paths; its historical runtime notes are superseded by later returns.
- [Current v6 execution handoff](CODEX_TO_CLAUDE_VIEWFUSION_V6_READY_2026-10-04.md): six fixes, exact commands, package hashes and execution-owner responsibilities.
- `build/p1_runner_v6_20261004_01/delivery_manifest.json`: source/test hashes and local verification.
- `build/p1_runner_v6_20261004_01/claude_staging_verification.json`: staged archive isolation and launcher-pin verification.
- `build/p1_continuation_20261003_01/geometry_fields.csv`: field-by-field geometry inventory and missing prerequisites.

Use packages under `build/p1_runner_v6_20261004_01/`; these supersede the earlier interim packages with the same `_05` names under `build/p1_trial_return_20261004_01/`.
