# P1 prompt for leaf area and geometry evidence alignment

Recipient: existing P1 3D reconstruction chat.

Date: 2026-10-05. This is a bounded follow-up to your completed Growth Pack V2 work, not a request to repeat that work. When this prompt is submitted to your project chat, inspect and implement only missing engineering corrections within your ownership; report already-correct behavior without rewriting it. Preparing this prompt did not execute or dispatch it.

## Required reading and precedence

Read repository rules, LOG tail/TODO, your current source/contracts and your `handoff/CODEX_P1_GROWTH_PACK_V2_EXECUTION_2026-10-04.md` report. Then read:

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


## P1 work

1. Inspect `tools/plant_traits.py`, `tools/leaf_area_geometry.py`, `tools/plant_structure.py`, and `tools/compound_surface.py::audit_area_evidence` / `audit_surface`, plus `tools/COMPOUND_MODEL.md`. The versioned S8 path already supports measured-elevation aggregation. Trace the actual caller and enabled policies before claiming a missing feature. Separate grouping changes from switching fx-squared area integration to v2 footprint integration. Preserve legacy values with explicit methods; do not silently reinterpret an old time series.
2. Audit each exposed quantity: image mask area in pixels, projected area in cm2, hull-derived diagnostic area, supported physical one-sided area, and any estimated total area. Preserve existing proxy columns and evidence gates. Carry method, scale/calibration/pose source, view selection, capture time/phase, support/coverage, identity/partition lineage, occlusion assumptions and uncertainty status through the applicable exports. Reuse current `area_basis.csv` / `downstream_leaf_surfaces.csv` contracts where supported; do not declare a new real area basis merely because metadata fields are populated.
3. Prevent projected union masks, inflated hull surface/footprint, unreviewed regions, unsupported A1/A2 estimates or generated tissue from being exported as validated physical lamina area. Preserve their diagnostic use. Report the recovered fx/fy difference and dilation scale as diagnostics, not correction factors that certify real accuracy. Small dilation does not itself establish correct depth.
4. Keep geometric normal axis, chosen sign convention and actual biological face evidence distinct. Export any independently supported orientation without fabricating face identity. A top view or stem-away convention cannot certify adaxial/abaxial identity. Missing biological face must remain traceable for P2/P4.
5. Create a readiness/dependency table for area-review A1-A7. For A2 specify the still-needed stable leaflet masks, measured poses, metric projection/depth observations, sufficient view coverage and identifiability checks. For A3 name the missing position, shape and surface sources, and the need for convergence/failure criteria. Do not implement a three-parameter fit as if it also reconstructed full surfaces. No new A1/A2/A3 estimator or matcher is adopted by this prompt; request a corrected executable contract from Claude and continue independent boundary fixes.
6. For top-view diagnostics, distinguish a supported projected-area ratio from mean-angle inference. Whole-plant ratios need not wait for leaflet matching if their masks/geometry are otherwise supported. Do not claim a measured LAD or normal merely from this ratio. Do not redesign board rejection or imaging acquisition without the corresponding specification.
7. Inspect existing individual -> canopy -> individual identity/geometry handling. Preserve plant/session/compound/leaflet IDs and exact source partitions; propagate declared rigid placements consistently to positions and normals. Verify existing round-trip behavior and absence of tissue duplication. Scope is fixing existing identity/provenance behavior, not implementing an unrelated new canopy engine. Send P2 a manifest of independently supported geometry, assumptions and unavailable fields.

## P1 acceptance cases

- Existing valid evidence passes unchanged; separately omit required scale, pose, area or identity evidence and verify that real eligibility is withheld without erasing diagnostic outputs.
- Projected proxy or hull area cannot masquerade as supported one-sided tissue area; unspecified lambda/G produces no fabricated true-area interval.
- Normal sign convention without biological evidence does not become a biological-face claim.
- A2 area/angles without located geometry cannot become an optical surface.
- Existing measured grouping is exercised through the real entry point; grouping and integrator effects remain separately auditable. Unknown views are not silently omitted from a claimed complete result.
- Existing canopy round trip preserves supported geometry, identity and tissue accounting; generated/unavailable regions retain their status.

Do not rerun completed P1 reconstruction or Day-1 template work merely because this review exists. Independent scan references and repeat acquisitions remain missing until actually supplied; templates are not measurements.

## Delivery and validation rules

Save your report as `handoff/CODEX_P1_AREA_REVIEW_EXECUTION_2026-10-05.md` and generated audits/tests in a fresh `build/area_review_alignment_20261005_NN/P1/` directory. Include: implemented/already present/design pending/unavailable for each item; exact files/functions and input/output fields with units; provenance and reason-code changes; relevant commands/results; preserved baseline evidence; downstream owner and unresolved questions. Reuse established reason codes and schemas where possible. Document/version genuinely needed additive metadata without silently breaking accepted inputs.

For changed boundaries, test a supported explicit synthetic case and the listed failure cases, including API/CLI/export behavior where affected. Synthetic fixtures must remain visibly synthetic and must not alter human evidence. Do not create tests merely to mirror unchanged code. Run focused relevant regressions after changes; do not rerun unrelated inference or completed project campaigns.

Scientifically unsupported quantities remain unavailable with reasons; zero is an actual measured/modelled zero, not a missing-value substitute. Malformed inputs remain distinct from missing science. Preserve source hashes/row lineage, historical reports and existing valid numerical behavior. Do not edit another project's runtime, `docs/`, `config/`, raw photos or human records. Do not fit biological coefficients, launch GPU training/inference, run a new acquisition campaign, or claim full-system/physical validation. Append LOG and any unresolved design items to TODO. Finish with a short Korean briefing.
