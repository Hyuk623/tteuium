# P1 review request: 3D observation, geometry and synthetic evidence

Perform a read-only full-scope P1 code review. First read [common review instructions](CODE_REVIEW_COMMON_2026-10-07.md). Use the same frozen snapshot as P2-P4. Output: `build/code_review_20261007_01/P1/`. Start with `P1/scope.json`; account for every routed primary file, including older paths and frontend/CLI support. Follow shared dependencies; do not confuse review ownership with edit permissions.

## Entry points and scope

- Capture/calibration/pipeline: `tomato3d/calib/`, `tomato3d/io/`, `tomato3d/mask/`, `tomato3d/organ/`, `tomato3d/fuse3d/`, `tomato3d/recon/`, `tomato3d/graph/`, `tomato3d/pheno/`, `tomato3d/track/`, `tomato3d/twoview/`; applicable `tomato3d/cli/` paths.
- Runtime and observations: `tools/plant_pipeline.py`, `plant_batch.py`, `plant_auto.py`, `plant_site.py`, `plant_structure.py`, `plant_hierarchy.py`, `plant_traits.py`, `observation_records.py` and called modules.
- Identity/masks/editing: `leaflet_mask_batch.py`, `serve_leaf_edit_session.py`, import/export/annotation tools, `cross_view_*`, `xview_*`, `instance_*`, `vein_*`, `midrib_*` and corresponding browser assets. Review save/undo/export semantics, not only model wrappers.
- Surfaces and P2 handoff: `tools/compound_surface.py`, `leaf_area_geometry.py`, `leaf_area_proxy.py`, `leaf_surface_*`, `vein_surface_bridge.py`, `visible_leaf_patch.py`, `tools/leaf_light/reconstruction.py`, `mesh.py`, `capture.py`, `annotations.py`. Cross-read `plant_light_bridge.py`/`canopy_light.py` under P2 for compatibility.
- Synthetic structure/evaluation: all `tomato3d/synth/`, especially `compound_leaf.py`, `leaflet_surface.py`, `scene.py`, `raster.py`, `contours.py`, `evaluate.py`, `leaflib.py`, `textures.py`; the separate `tools/f2_*` helpers and their reports. This is a code/evidence audit, not authorization to execute training/rendering/inference.
- Remaining P1-routed support scripts and guides: triage and account for them explicitly. Inspect import side effects before execution.

## Priority counterexamples

1. Sheet/board/grow transforms, units, origin shifts, rotation signs, normals and lengths. Use measured ChArUco poses; identify any path using nominal turntable angles as measured geometry.
2. Pixel-edge versus pixel-center coordinates, resized/stretched masks, camera intrinsics/distortion and scale provenance. Cross-view joins must not silently associate different organs or duplicate observations.
3. Preserve accepted raster masks and human review state; inspect overwrite/undo/cache invalidation and image/hash mismatches in the actual editor/import paths.
4. Separate projected area, supported patches, hull/envelope and physical tissue. Test holes, overlapping triangles, disconnected patches, degenerate meshes, unknown views and incomplete coverage. Inspect `Plant.s8` policy forwarding and export consumers, not just helper functions.
5. Trace geometry/identity/uncertainty into P2 and temporal observations into P3. Check canopy instance-copy keys, per-plant partitioning and provenance; do not promote unavailable botanical faces or generated geometry.
6. Synthetic evaluation: visible versus amodal masks, instance IDs, area bins, scene/view grouping, camera framing, contour selection, GT rule application and metric denominators. Check that diagnostic filters never become contract C6 passes. Read October 7 Addenda G/H/I and later log context without running the queued experiments. Trace code changes and cached-detection identity where applicable.
7. F2/F7 source mapping and thresholds: source images/contours/bank links, fit versus validation, uncertain classification and coordinate annotations. Provisional projected ratios must never become approved generator priors. `intercalary_count` exists; audit its actual semantics rather than repeating an outdated claim that no small-leaf code exists.

## Contract references

- `handoff/CODEX_P1_AREA_REVIEW_EXECUTION_2026-10-05.md`
- `handoff/CODEX_P1_GROWTH_PACK_V2_EXECUTION_2026-10-04.md`
- `handoff/CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md`
- `handoff/CLAUDE_CODE_F2_F7_RESULTS_HANDOFF_2026-10-07.md`
- `handoff/CLAUDE_CODE_CLI_ADDENDUM_F_COMPOUND_STRUCTURE_2026-10-06.md`
- `handoff/CLAUDE_CODE_CLI_ADDENDUM_G_CONTOUR_POOL_BIAS_2026-10-07.md`
- `handoff/CLAUDE_CODE_CLI_ADDENDUM_I_LOCAL_AND_DESTRUCTIVE_2026-10-07.md`

## Validation entry points

Inspect and select `tools/tests/test_area_review_alignment.py`, `test_p1_area_evidence.py`, `test_compound_surface.py`, `test_leaf_area_geometry.py`, identity/editor tests, `test_f2_f7_analysis.py`, `test_f2_f7_evidence.py`; relevant `tests/test_board_pose_synthetic.py`, `test_synth_*.py` and geometry/IO tests. Determine heavy optional-dependency tests before running; missing OpenAlea/Blender/model weights do not authorize installation or execution of campaigns. Enumerate untested paths.

Report six coverage groups separately: calibration/IO; segmentation/editors/identity; reconstruction/surfaces; traits/exports; synthetic generation/scoring; remaining support/UI. A claim of full P1 review must account for all six. In boundary_contracts.json provide actual P1->P2 surface and P1->P3 observation payloads, including evidence gates and unavailable outputs. Scientific identifiability questions go to Claude, not an invented implementation fix.
