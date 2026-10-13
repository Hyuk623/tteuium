# Leaf area / 3D implementation execution

## Request

Execute CODEX_LEAF_AREA_3D_IMPLEMENTATION_PROMPT_2026-10-03.md. Keep future growth work untouched. Implement permitted numeric and geometric tooling, verify it, and retain unresolved physical/specification requirements explicitly.

## Current evidence and scope

The working folder has no Git metadata. Existing files must be snapshotted and hash-checked before modification. The separate growth session has added monthly_growth; those files are outside this work. plant_traits still uses fx squared, hard-coded view-code grouping and unversioned calibration. Current local surface tools are reusable. The September surface-options brief is explicitly a proposal, not a reviewed curved-fit model contract.

## Planned implementation

- Add a chunked inverse-distortion pixel-footprint integrator with explicit numerical policy. Original pixel centres are integers and corners are at +/-0.5 px. Subdivide curved pixel boundaries until area convergence and check inverse projection residuals. Return unavailable/partial coverage rather than treating failed geometry as measured zero. No global cache.
- Add an opt-in estimator version to plant_traits, retain legacy behavior for existing callers, compare in fresh outputs and guard calibration mixing. Extend measured camera/elevation diagnostics using supplied group policy and movement provenance.
- Add supported surface comparison using current mesh and observed local plane with held-out diagnostics. Record the curved model as unavailable pending a reviewed contract; do not invent model form/regularization. Reuse face-support gates and existing camera projection helpers.
- Add CLI, source-linked viewer, frozen input/policy hashes, focused tests and saved T1/T2/T3 comparison.

## Restrictions and validation

No source photos/masks/human records, docs/config/core modules, growth code, training/inference, remote jobs or native light execution are changed. Settings files for isolated numerical experiments are generated under build only. Test independent planar/distorted references, convergence, missingness, overlap, version mixing, view geometry, surfaces and provenance. Preserve physical validation=false; do not claim whole-plant surface completeness from partial geometry or proxy tests.

## Completion ledger

Implementation in progress. Curved model specification and independent physical measurement remain open. Final source/tests/artifacts and execution outcomes will be appended here.

## Continuation audit
The saved real_compare_03 run finished: 54 photos, 4048 source hashes verified. Inspection found an additional opt-in plant_traits gap: missing/unposed/excluded photos were filtered before the corrected summary. Preserve those unavailable rows in versioned summaries, while retaining legacy default behavior. Also guard empty hull compatibility and failed-pose surface evaluation, add independent tilted-plane and noisy-curvature checks, then rerun affected verification. Real review audit: seven pending points, zero human confirmations in the existing pilot; measurements/leaf_area.csv is absent.

## Verified delivery checkpoint, 2026-10-03

Full objective remains OPEN. This checkpoint delivers the versioned projected proxy and fixed-camera mesh/plane comparison, not a validated complete plant surface.

### Files and execution

- Added tools/leaf_area_geometry.py, tools/leaf_area_compare.py/.html, tools/leaf_surface_compare.py/.html, tools/LEAF_AREA_COMPARISON.md and three focused test modules under tools/tests/.
- Extended tools/plant_traits.py with opt-in area_policy/capture_style/grouping, legacy comparisons, compatibility-bound calibration and retained unavailable photo rows. Legacy default callers keep their prior estimator.
- Run: `python -X utf8 -m tools.leaf_area_compare --study build/leaf_area_implementation_20261003/study.json --out build/<fresh-area-directory>`.
- Run: `python -X utf8 -m tools.leaf_surface_compare --study build/leaf_area_implementation_20261003/synthetic_flat_inputs/study.json --out build/<fresh-surface-directory>`. This example is synthetic only. Both --help commands were exercised.
- Current results: build/leaf_area_implementation_20261003/real_compare_04; synthetic_flat_03; synthetic_curved_03; numerical_checks_01; analytic_recheck_01. Older numbered outputs are retained for provenance.
- Local viewer: http://127.0.0.1:8856/build/leaf_area_implementation_20261003/real_compare_04/viewer.html. Source images and saved-mask toggles, plant/photo selectors, measured groups, missing states and source links were verified in the browser. Surface mesh/plane and fit/held-out selectors were verified on synthetic_curved_03. No console errors were returned.

### Verification

101 focused tests passed in 28.63 seconds: test_leaf_area_geometry, test_leaf_area_compare, test_leaf_surface_compare, test_plant_traits, test_compound_surface and test_plant_light_bridge. JUnit evidence: build/leaf_area_implementation_20261003/verification.junit.xml. Coverage includes independent inverse-Jacobian quadrature for off-axis radial/tangential distortion, exact unequal-focal area, explicit resampling, partial/missing/empty coverage, failed poses, independent third-view errors, tilted plane, local/global topology and duplicate tissue, calibration versions and date/plant joins. Numerical tolerances reflect requested integration convergence and exact synthetic geometry; they are not physical acceptance gates.

The eight original analytical tables were reproduced in analytic_recheck_01 with seven consumed sources unchanged. Curved-sample/chord subdivision, depth sensitivity, tilt and dense flat-noise inflation remain separate from implemented curved fitting. Additional numerical_checks_01 tables vary fit-view pixel noise (0, 0.05, 0.15 px; eight trials each) and retain a noise-free independent third view. The bent synthetic patch has analytically known area 9.430631 cm2; the plane fit gives 8.051282 cm2 and 0.755921 px held-out RMS without noise. This demonstrates flattening bias, not measured leaf accuracy.

### Saved real comparisons

All three cases refer to 2026-10-02. The final run finished, verified 4048 consumed input/code hashes and produced 54 photo rows. Timing: T1 49.82 s, T2 62.82 s, T3 44.58 s (per-case work).

| Plant | Complete projected coverage | Partial | Unposed | Excluded |
|---|---:|---:|---:|---:|
| T1 | 12 | 6 | 0 | 0 |
| T2 | 16 | 2 | 0 | 0 |
| T3 | 4 | 7 | 5 | 2 |

Complete projected coverage means all supplied mask-union pixels have numeric support; it does not mean complete plant tissue or passed pose/scale validation. T2's two top images give legacy mean 17.5 cm2 and corrected projected mean 18.032824 cm2. Other incomplete group means remain unavailable. No per-photo sum is reported as whole-plant tissue. T3 preserves supplied A+B1 selection and B2 exclusion; this tool does not detect or estimate new plant motion.

### Open requirements and exact evidence

- The reviewed curved polynomial/spline contract is absent from the inspected surface-options proposal. Claude must specify basis/chart domain, loss and weights, regularization/parameter selection, minimum boundary/interior evidence, meshing convergence and held-out acceptance before that candidate can be implemented.
- real_surface_readiness.json hashes the latest two pair reviews in the existing pilot: seven pending points, zero human confirmations. The comparison must not turn these proposals into real physical correspondence evidence.
- measurements/leaf_area.csv and measurements/light.csv are absent. Corrected calibration reports no_measurements. Whole-plant calibration, metric scale/pose validation and physical accuracy remain unverified.
- Current contour CSV cannot encode holes; explicit hole-bearing comparison input is rejected. Existing compound_surface raster/hole/chart helpers are tested and reused for auditing, but the new comparison input adapter still needs richer patch/visibility support for such inputs. Do not omit holes to force acceptance.
- Dedicated source-linked comparison viewers exist; automatic legacy-site linking is not implemented. Normals remain unsigned and optical eligibility gates are unchanged.
- requirement_audit.json preserves requirement-level status. No training, inference, remote jobs, uploads, Git push, native light execution or growth-file changes occurred. No physical acceptance threshold was selected.

## Local-chart continuation plan
Reuse explicit compound_surface local charts with boundary/hole point IDs, fixed-pose triangulation and hashed original-coordinate visibility masks. Multiple charts may belong to one leaflet; each keeps a unique physical patch ID and global overlap audit. Occluded/unknown views are not negative tissue evidence. Preserve legacy contour inputs and explicit unavailable states. Verify holes, disconnected charts, folds and stale/mismatched masks before updating outputs. No biological fitting contract is added.

## Local-chart completion checkpoint, 2026-10-03

The previous contour-only limitation is superseded. tools/leaf_surface_compare now accepts explicit observation-ID charts with outer/hole rings, multiple charts for one leaflet, and hashed original-coordinate visible masks. It reuses fixed-camera triangulation and compound_surface.local_patch_faces; no new biological surface form is selected. Occluded/unknown views remain evidence metadata and are excluded from negative-mask checks. Held-out masks cannot constrain fitting/support. All charts retain unique patch IDs and a global duplicate/intersection audit; signed upper/lower normals and optical approval remain unavailable.

The existing comparison viewer was extended with chart-scoped observations/reprojections, original/support-mask toggle and source links, and side-by-side responsive canvases. It exports compound_areas.csv and patch_inventory.csv with explicit capture-date availability. No historical plant site is overwritten; automatically linking every old plant site was a preference, not a required physical-validation step.

Verified artifacts: build/leaf_area_implementation_20261003/chart_hole_03, chart_disconnected_03 and chart_fold_03. Known one-sided areas are respectively 15.0, 8.0 and 8.472135955 cm2, reproduced by both supplied-chart mesh and observed-plane candidates. All input hashes verified. Independent third-view residuals are near numerical precision. These remain synthetic checks and are not evidence of real-plant scale or surface accuracy. The browser verified hole masking, same-leaf chart selection, held-out reprojections, unavailable-mask fallback and source links without console errors.

Validation: 111 tests passed in 18.52 seconds across the prior six suites plus tools/tests/test_leaf_surface_charts.py. JUnit: verification_03.junit.xml. Added cases cover holes, disconnected/folded charts, stale/mis-sized masks, visibility semantics, missing/duplicate IDs, fit/held-out mask isolation and repeated patch identity. Final CLI smoke results include compound/date and patch-inventory CSVs.

Completion audit: requirement_audit_02.json supersedes the earlier matrix; the full objective is NOT achieved. blocker_recheck_02.json confirms unchanged latest pilot review hashes (7 pending points, 0 human confirmations) and absent measurements/leaf_area.csv. Inspected surface/leaf-area handoffs still do not supply a reviewed regularized curved-fitting contract. That contract and real physical/metric evidence have remained the same blockers through the initial implementation and subsequent goal continuations. Permitted baseline/comparison/topology work is now delivered. Do not generate approvals, anatomical correspondences, physical reference measurements, curvature or acceptance thresholds to bypass those dependencies. Claude's specification request remains open in TODO.

## User confirmation after resume
The user explicitly answered that no alternate reviewed curved-model specification, confirmed correspondence data or independent leaf-area measurements exist. Treat these dependencies as unavailable, not undiscovered files. Do not repeat path requests or fabricate substitutes. Implemented proxy/mesh/plane/chart tools and synthetic checks remain available; full real-surface/accuracy validation remains open.

## User requested dimensionless leaf area ratios

The user explicitly selected area normalization: the first labelled leaf has area 1. Implement A_i / A_reference within the same plant/session/date/estimator/area scope/view. Preserve the supplied label order; no inferred height-based naming or replacement of an unavailable first leaf. Zero/missing reference area yields unavailable ratios. Retain absolute areas and partial-surface provenance. Add a reusable CSV calculator and surface-comparison leaf summary; tests use explicitly synthetic areas. This does not supply the missing real curved fitting or physical references.

### Dimensionless ratio implementation outcome

Implemented the user-confirmed area-ratio convention in `tools/relative_leaf_area.py` and integrated per-label ratios into `tools/leaf_surface_compare.py` and its HTML viewer. Group references preserve supplied label order. Missing/zero references remain unavailable. Surface areas aggregate eligible faces across all patches of the same label before normalization; absolute areas and supported-partial scope are retained.

Validation: `python -X utf8 -m pytest tools/tests/test_relative_leaf_area.py tools/tests/test_leaf_surface_charts.py tools/tests/test_leaf_surface_compare.py -q` passed 32 tests in 8.82 s. Exercised CLI help, CSV round-trip and fresh synthetic outputs under `build/relative_leaf_area_20261003/`. Browser inspection confirmed the CSV link and dimensionless ratio 1 for the folded two-chart reference leaf (summed area 8.472135955 cm2). Example CSV areas 20, 30, 10 yield 1, 1.5, 0.5. No real labelled-leaf ratio or physical validation is claimed. Existing full-objective blockers remain unchanged.

## Detection-only normalization requested, 2026-10-03

User requests calculation before physical area measurement, from detection alone. Current relative-area code accepts cm2 and the surface route requires geometric observations. Existing T1/T2/T3 batches contain original-image boxes and cached per-instance segmentation masks; first T1 mask is unreviewed. These are usable for image-space ratios without claiming measured tissue area.

Implement `tools/detected_leaf_area.py`: read saved Batch metadata and masks only, count visible mask pixels (default), optionally use explicitly selected bbox width*height as a separate proxy. Output area_px2/reference_area_px2 and dimensionless ratios with source label, image, review, visibility and availability. First manifest label per image is the reference, including unavailable/rejected first entries (no substitution). Do not merge views or invent persistent physical IDs. Preserve source order and hashes. Generalize existing normalize with an explicit pixel-area column while preserving legacy callers. No cm2, board scale, camera poses, 3D, independent area measurements or environmental inputs are required. No new inference/training, source edits, upload or native simulation. Generated outputs use fresh build directories.

Validate independent mask counts, bbox-vs-mask separation, zero/missing/rejected reference, grouping, image/crop consistency and hash checks; run focused regression tests and read-only T1/T2/T3 saved detection calculations. Update the quick handoff with actual outputs and limits.

### Detection-only delivery outcome

Implemented `tools/detected_leaf_area.py` and extended `relative_leaf_area.normalize` with explicit area_px2 support while keeping default cm2 callers unchanged. Default mask mode counts saved original-resolution foreground; explicit bbox mode stays a separate proxy. Source review/manual edits/visibility, missing/rejected references, original image/crop checks and hashes are retained. No new inference, physical measurements or 3D reconstruction is needed.

40 focused detection/normalization/surface tests passed in 6.32 s. CLI help passed. Real read-only results: T1 435 observations/18 photos, T2 489/18, T3 394/18; all 1318 observations have computable ratios in these saved batches. These are per-photo detections, not 1318 unique physical leaves. The 54 first-label references equal 1; independent exported-CSV division checks passed. Per-case audits verified 1330, 1492 and 1207 source/code hashes respectively. T3 views remain independent and were not merged across movement groups. Unknown capture dates remain unavailable.

Artifacts: `build/detection_relative_leaf_area_20261003_01/relative_detected_leaf_areas_all.csv`, per-plant CSV/audit folders, `summary.json`, `result_verification.json`. T1 first-image examples: a6 8478 px2 -> 1; a7 29700 px2 -> 3.5031847133757963; a8 3742 px2 -> 0.4413776834159. These are actual saved detection-mask counts, including unreviewed observations; no physical leaf-area accuracy claim.

The user replaced the former full physical-area objective with this preliminary relative-area calculation followed by the named diffusion specification task. The latter is delivered separately in CODEX_MULTIVIEW_DIFFUSION_INTEGRATION_SPEC_2026-10-03.md. Former physical/curved-model gaps remain documented but are not prerequisites for the newly requested image-space calculation.
