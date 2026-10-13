# Observed leaf geometry and area revisions

Use reviewed observations to improve leaf calculations. Generated RGB remains a separate hypothesis and never supplies mask pixels, depth, physical scale or organ identity to these paths.

## Reviewed leaf exclusions

`python -m tools.detected_leaf_area --batch BATCH --selection POLICY.json --out build/FRESH`

The optional policy has schema `observed-leaf-selection-1`, matching `plant_id`/`session_id`, `origin=observed_annotation_review`, a hashed `evidence` path, and `excluded_items`. Each entry contains `item_id`, `item_sha256`, `image_file`, `image_sha256`, and a nonempty `reason`. All paths in the policy are relative to its file unless absolute. Evidence is an explicit review decision, not an automatic biological classifier.

Exclusions leave original labels/masks untouched. The CSV retains excluded rows with unavailable area. If the first saved reference label is excluded, all ratios for that photograph remain unavailable; another label is never substituted. Stem masks are not added to leaf blade area. Full original-resolution mask/crop checks remain mandatory; 256-pixel generative crops cannot replace observed rasters.

`tools.leaf_area_compare` accepts the same policy through each study case's optional `mask_selection` path. `mask_decisions.csv` and the existing comparison viewer expose the excluded IDs and reasons. Selected mask policy identity participates in area-calibration compatibility, preventing silent reuse of coefficients from a different selection. Pixel area, partial projected coverage, complete projected coverage and actual tissue area retain distinct meanings.

## Measured grouping for 3D regions

`python -m tools.plant_structure --session SESSION --backup BACKUP --view-grouping GROUPING.json --out build/FRESH`

The grouping JSON supplies `centre_board_mm`, `top_elevation_gt_deg` and `source`, using the existing `leaf_area_geometry.view_geometry` calculation. This labels camera direction relative to an explicit board-frame reference; it neither solves a pose nor passes its quality gate. A missing policy, threshold or posed ring reference leaves compound assignment unavailable rather than guessing from photograph numbers. The legacy `_is_top` utility is retained for historical compatibility but is not used for current region assignment.

The pipeline also accepts `view_grouping` in each plant configuration and passes a snapshot to S3. The status page uses that grouping and the selected `pose_session`. No shared configuration is edited automatically.

Changing grouping may change the number and IDs of candidate regions. These IDs are local to the current partition, not persistent leaf identities. To apply reviewed names, supply `{"region_assignment_hash": "HASH_FROM_CURRENT_STRUCTURE", "regions": {"0": {"name": "L01", "median_z_mm": 50}}}`. The existing name checks still apply. Old/unbound names remain unapplied with an explicit status and pipeline review task. A corrected grouping rule does not prove that more regions are more accurate leaves.

## Current real example

Inputs and outputs for the r03-derived review are under `build/p1_r03_program_update_20261004_01/`. `observed_leaf_selection.json` excludes the two reviewed image-27 non-leaf items. `area_study.json` and `view_grouping.json` reuse the previously recorded T1 camera reference and threshold. `regrouped_hull_diagnostic.csv` reassigns existing hull voxels; it does not reconstruct a new surface, transfer historical leaf identities or change XYZ coordinates.

There is no new inference, model-weight change or accepted metric/optical geometry. Scientific accuracy still requires reviewed correspondences, valid camera mapping and independent measurements.
