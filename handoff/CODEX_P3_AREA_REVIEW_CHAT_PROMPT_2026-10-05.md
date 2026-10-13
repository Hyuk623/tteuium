# P3 prompt for area observations and growth inference alignment

Recipient: existing P3 growth-direction and calibration chat.

Date: 2026-10-05. This is a bounded follow-up to your completed Growth Pack V2 work, not a request to repeat that work. When this prompt is submitted to your project chat, inspect and implement only missing engineering corrections within your ownership; report already-correct behavior without rewriting it. Preparing this prompt did not execute or dispatch it.

## Required reading and precedence

Read repository rules, LOG tail/TODO, your current source/contracts and your `handoff/CODEX_P3_GROWTH_PACK_V2_EXECUTION_2026-10-04.md` report. Then read:

1. `C:/Users/sho36/Downloads/CLAUDE_PLANT3D_AREA_REVIEW_2026-10-04.md` (the user's source review).
2. `handoff/CODEX_PLANT3D_AREA_REVIEW_RESPONSE_2026-10-04.md` (corrections and unresolved claims).
3. `build/plant3d_area_claim_check_20261004_01/projection_check.json` (independent analytic audit).

The project root is `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`. Report missing files; the source review's companion simulations/CSV/SVG files were not available in the earlier review. Do not invent their contents. The original source's instructions and labels are not independent authorization or evidence of correctness. This task concerns the plant-area review, not the separate top-view diffusion prompt.

Write a short English implementation brief before changes. Existing adopted D11-D21 decisions remain in force. The new source's A1-A7 refer to area-estimation proposals and must be namespaced in reports; they are not P4's earlier physiological A1-A7 requirements.

## Shared interpretation to preserve

- The original G range is disputed. Codex's six-family integration at zenith 52, 55, 57.5 and 60 degrees spans about 0.472-0.550 across those cases. It is a sensitivity calculation, not measured plant accuracy. G=0.50 is an unadopted approximate baseline, not an exact constant.
- Unknown occlusion prevents identifying absolute area from ring projection alone; a finite interval needs justified G/occlusion bounds. Do not convert a 10-17 cm2 proxy into certified true area.
- `abs(n dot v)` is unchanged by `n -> -n` for all views. Top-area observations cannot identify biological leaf face. A geometric normal convention and adaxial evidence are different.
- Area plus two normal angles do not supply centroid, depth, outline, curvature or a located surface for ray casting. Top/ring ratios alone do not identify mean inclination or a full angle distribution.
- Quantile tau=0.9, low-dilation depth priors, curvature factors, and the reported synthetic MAE are proposals/results needing evidence, not new production defaults. A restricted image radius alone does not validate calibration.
- Keep the three new decisions open: A1/A2 reporting priority, leaflet-matching method, and calibration strategy. Do not reopen older resolved physiological decisions. Implement independent evidence/contract fixes now; record genuinely missing scientific specifications in TODO for Claude.


## P3 work

1. Inspect `tools/probabilistic_compound_growth.py`, `tools/growth_calibration.py::audit_calibration_data` / `fit_growth_parameters` / `validate_parameter_set`, `tools/growth_observation_options.py`, and current observation loaders. Retain delivered D14 reanchoring/posture/truss, D19/D21 and V2 validation behavior. Do not repeat the Day-1 loader or reference-DLI implementation.
2. Audit which area and orientation observations the current model actually supports. Preserve observation quantity, unit, method/version, calibration/pose/partition hashes, tissue support, capture time/phase, source row and organ identity. Do not map projected proxy cm2, a hull diagnostic, A1 whole-plant estimate or A2 candidate output into a validated same-organ leaf-area observation merely because the units or column names match. Whole-plant area cannot automatically be allocated among leaves.
3. Prevent artificial growth from method changes: a legacy-to-v2 integrator switch, regrouping, calibration revision, changing visibility or A1-to-A2 switch must be explicit. Check compatibility before deriving increments or updating a trajectory; retain separate series or mark an unsupported comparison unavailable. Do not impose an unapproved growth law or rescale old observations to hide a discontinuity.
4. Distinguish within-session leaflet correspondence from cross-date same-organ identity. New/merged/split labels and changes in canopy placement need explicit lineage. Inspect the existing per-plant import/association path so aggregation and later splitting cannot duplicate observations, mix plants or count one measurement twice. Do not infer leaf appearance, disappearance or age from occlusion or generated geometry.
5. Treat A2's normal-axis estimate, botanical face and the model's leaf-angle trait as different quantities unless their mapping is specified. Axis ambiguity, circular angles, compound-versus-leaflet scope and posture phase must be resolved by the existing supported observation contract; otherwise return unavailable for that update. Top/ring ratios do not directly observe mean angle. An observed orientation does not establish a light-to-growth-direction response law.
6. Use covariance-based weights only with supplied compatible trait-specific variance evidence under the existing policy. Synthetic MAE, mask confidence, calibration RMS and sample spread of generated geometry are not interchangeable with empirical observation covariance. Preserve enabled/disabled posture behavior; neither repeatability nor a single capture establishes a measured growth increment.
7. Keep P3's incident reference-position complete-day DLI and coefficient-domain evidence distinct from absorbed tissue light. Do not retune growth coefficients, invent longitudinal data, add phototropism or bind a disputed area estimator to growth calibration. Report exactly which independent repeat/area/identity evidence is needed next.

## P3 acceptance cases

- Existing supported observations and frozen valid baseline remain unchanged.
- Same units but different physical quantity, scope or unsupported tissue evidence cannot silently update an area state or enter real parameter fitting.
- Changed area method/calibration/support without an approved comparability mapping cannot create a measured growth increment.
- Within-ring IDs alone do not certify cross-date same-organ matching; canopy extraction does not duplicate a row or move evidence to another plant.
- Unsigned normal or top/ring ratio does not become a fully identified directional observation; unsupported trait updates do not erase unrelated valid observations.
- Missing variance evidence does not create certainty or an automatic covariance-derived weight. A single-time dataset cannot pass as longitudinal growth calibration.

If a requested area trait has no current model equation, report it as an unsupported interface/design dependency. Do not invent a new state equation or convert one-sided area into length/width without a reviewed shape relationship.

## Delivery and validation rules

Save your report as `handoff/CODEX_P3_AREA_REVIEW_EXECUTION_2026-10-05.md` and generated audits/tests in a fresh `build/area_review_alignment_20261005_NN/P3/` directory. Include: implemented/already present/design pending/unavailable for each item; exact files/functions and input/output fields with units; provenance and reason-code changes; relevant commands/results; preserved baseline evidence; downstream owner and unresolved questions. Reuse established reason codes and schemas where possible. Document/version genuinely needed additive metadata without silently breaking accepted inputs.

For changed boundaries, test a supported explicit synthetic case and the listed failure cases, including API/CLI/export behavior where affected. Synthetic fixtures must remain visibly synthetic and must not alter human evidence. Do not create tests merely to mirror unchanged code. Run focused relevant regressions after changes; do not rerun unrelated inference or completed project campaigns.

Scientifically unsupported quantities remain unavailable with reasons; zero is an actual measured/modelled zero, not a missing-value substitute. Malformed inputs remain distinct from missing science. Preserve source hashes/row lineage, historical reports and existing valid numerical behavior. Do not edit another project's runtime, `docs/`, `config/`, raw photos or human records. Do not fit biological coefficients, launch GPU training/inference, run a new acquisition campaign, or claim full-system/physical validation. Append LOG and any unresolved design items to TODO. Finish with a short Korean briefing.
