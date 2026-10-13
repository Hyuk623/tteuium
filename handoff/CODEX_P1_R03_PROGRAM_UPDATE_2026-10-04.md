# P1 program update from r03 trial results

Date: 2026-10-04. User requested review of the r02/r03 comparison sheets, r03 visual note and Claude result handoff, followed by changes to this program rather than Claude's deep-learning files. The last sentence ends before naming the desired program behavior; a focused clarification is pending.

## Independent review before choosing the edit

Inspect actual returns and frozen inputs, verify all declared seeds/targets and hashes with the existing importer, and reproduce the supplied post-hoc consistency summary. Preserve model code, launchers, vendor files, all trial artifacts, original observations and human configuration. Write fresh evidence under `build/p1_r03_program_update_20261004_01/`. No upload, training, inference or cross-project integration is requested here.

The inspected sheets show larger in-frame content after the r03 input revision and continued separated leaf regions. Image 27 changed both mask and derived crop (1575 to 840 px); input-mask and scale effects are confounded. Pairwise generated-image IoU is seed variability, not anatomical accuracy. No validated camera mapping or accepted physical geometry is supplied by these outputs.

## Program surfaces found

`tools/multiview_completion.py` provides request preparation, import, evaluation and an image review export. `tools/plant_site.py`/`.html` provide the existing plant status page; `tools/serve_leaf_edit_session.py` provides the observation editor; `tools/leaf_preprocess_lab.py` provides RGB preprocessing inspection. These are distinct interfaces, so a result-only comparison panel must not be substituted for a requested 3D/area calculation change without establishing scope.

A concrete existing issue found during inspection: `plant_site.camera` assigns top/side groups from image-number codes (01/03 treated as top), contrary to this dataset's measured top views 27/28. Existing `tools/leaf_area_geometry.py::view_geometry` supports explicit-reference measured elevation and unavailable status without an arbitrary fallback. This finding is recorded for the eventual program change; no camera grouping policy or production code has yet been changed.


## Confirmed implementation scope

The user clarified: improve existing leaves' 3D shape and area calculations using the findings. Implement two concrete corrections in existing calculation paths: (1) explicit measured-elevation grouping for 3D compound-region assignment, using the already recorded board reference/threshold and no inferred camera pose; (2) immutable, image/item-hash-bound reviewed exclusions for detected leaf ratios and projected-area comparison. The r03 decisions identify a545/a549 as non-leaf objects; stems added for plant conditioning must not be counted as leaf blade area. Excluded labels retain rows and first-label references are never substituted.

Keep original-resolution mask coordinates and the existing distortion/depth estimator. Carry selection-policy identity into calibration compatibility, expose exclusions in the existing area report, and verify that model-resized crops cannot supply metric pixel counts. Extend focused regression tests and execute on saved observations/cached hull data, keeping real output eligibility false. Changes affect the owned observation/geometry support code; Claude's trial runner, launcher, vendor and all old results remain read-only.


## Delivered implementation and actual results

The scope question is resolved by the user's explicit reply: improve existing leaf 3D shape/area calculations. No model training, inference, renderer-only substitute or Claude deep-learning edit was performed.

Changed existing program paths:

- `tools/leaf_mask_selection.py`: image/item/evidence-hash-bound reviewed exclusion loader.
- `tools/detected_leaf_area.py`: optional `--selection`, retained excluded rows and fixed first-reference behavior.
- `tools/leaf_area_compare.py` and `.html`: apply the same observed leaf selection to original-resolution projected area, expose review decisions and policy identity in the existing viewer.
- `tools/plant_traits.py`: selection identity participates in calibration compatibility; old selection coefficients cannot silently carry across.
- `tools/plant_structure.py`: use explicit measured-elevation grouping for compound-region reference/matching; no current filename-based top inference. No measured ring reference yields unavailable grouping. Make cached XYZ slices contiguous for OpenCV projection. Bind human region names to current partition identity.
- `tools/plant_pipeline.py`: forward plant `view_grouping` into S3 and report unapplied stale names.
- `tools/plant_site.py` and `.html`: show measured grouping, use the configured pose session and render unavailable/ring labels correctly.
- `tools/tests/test_observed_leaf_revision.py`: regression coverage for exclusions/reference retention, stale/foreign/generated review refusal, calibration separation, misnumbered measured views, sliced-coordinate projection and stale identity refusal.

Actual T1 execution retained 435 detected rows: 433 have computable ratios and two reviewed non-leaf objects have unavailable area. First references were preserved. Image 27's selected visible union changed from 129,588 to 124,520 original pixels, removing 5,068 pixels. Supported projected area remained 11.29660018160603 cm2. Previously the extra objects lacked depth, making full selected-union coverage incomplete; after their explicit removal, all remaining selected pixels have supported projected coverage. This is not evidence of correct total tissue area or validated metric accuracy.

The recorded board reference/70-degree threshold identifies images 27/28 as top and 03 as ring. Reapplying the existing compound grouping to the cached hull gives 12 candidate regions versus five in the historical output, with image 18 still the reference. XYZ coordinates are unchanged. More candidate regions are not evidence of better biological segmentation; region IDs are run-local and cannot inherit old physical leaf identities. The full hull carving/3D reconstruction was not rerun; `regrouped_hull_diagnostic.csv` is a grouping diagnostic on the preserved hull, not a new accepted tissue surface. Human names without matching `region_assignment_hash` are left unapplied with a review status.

All 80 r03 images independently passed the existing importer (eight declared seeds and five targets per arm). Forty cells of the supplied post-hoc seed IoU summary were reproduced within its three-decimal rounding. Those values remain variation diagnostics, not image-13 accuracy. Cleaning mask and changing crop remain confounded; no causal model coefficient was introduced.

## Validation and runnable artifacts

**117 tests passed, zero failures/errors/skips** across observed-revision, detection area, area comparison/geometry, traits, pipeline tools and plant-light bridge suites. The first attempt exposed an incorrect test fixture box schema; it was corrected. Actual cached-hull execution also exposed an OpenCV contiguous-array requirement, which was fixed and regression-tested.

Evidence root: `build/p1_r03_program_update_20261004_01/`.

- `observed_leaf_selection.json`, `area_study.json`, `view_grouping.json`: explicit reproducible inputs derived from recorded r03 review and existing area-study geometry settings.
- `detected_areas/`: 435-row result and immutable-input audit (1,329 consumed hashes checked).
- **`projected_areas_final/viewer.html`** and `audit.json`: final 18-photo area calculation (1,341 consumed hashes checked at verification). Earlier `projected_areas/` is historical; values agree.
- `plant_status.html`: existing status page with corrected camera grouping/pose-session display; its displayed structure remains the historical structure, not the new diagnostic partition.
- `region_review.json`, `regrouped_hull_diagnostic.csv`, `area_changes.csv`, `actual_execution.json`: actual regrouping and area differences.
- `tests_delivery.xml`, `delivery_verification.json`, `delivery_manifest.json`: test/provenance records. A final CLI help-text correction after the area run has explicit before/after code hashes; calculation functions did not change.

Run from the project root, using a fresh output folder:

```text
python -X utf8 -m tools.detected_leaf_area --batch build/plants_dwt_test_20261002/plants/dwt_t1/masks --selection build/p1_r03_program_update_20261004_01/observed_leaf_selection.json --out build/FRESH_ratios
python -X utf8 -m tools.leaf_area_compare --study build/p1_r03_program_update_20261004_01/area_study.json --out build/FRESH_area_comparison
python -X utf8 -m tools.plant_structure --help
```

Full 3D builds accept `--view-grouping` or capture `view_grouping`; the existing pipeline accepts the same object in its plant entry. See `tools/OBSERVED_LEAF_REVISION.md` for selection schema and hash-bound region names. No human/shared configuration was changed automatically. Existing workflows without an explicit grouping policy now report unavailable compound assignment rather than infer it from numbered files. This behavior is intentional and must be respected by downstream consumers.

## Remaining scientific limits

Supported projection is still a depth/calibration-dependent estimate. This change does not solve missing correspondences, curved leaf surfaces, passing pose gates, hidden tissue, independent area calibration or physical optics. Candidate repartitioning needs review before persistent leaf identities are reassigned. Generated RGB stays outside measured geometry/area/light paths. Claude's executed deep-learning runner matches its r03 archive hash; original images, masks, prepared inputs, trial returns and prior artifacts were preserved.
