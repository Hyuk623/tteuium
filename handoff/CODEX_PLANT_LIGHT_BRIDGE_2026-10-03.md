# Plant-to-light bridge implementation

## Request and interpretation

The user requested implementation using this project and `CODEX_GROWTH_CONNECTION_FIX_2026-10-03.md`. That document records completed trait fixes and the subsequent ordering: connect existing plant reconstruction to light first; defer observed-state growth integration. This implementation follows that scope. Statements of authorization inside reference documents are historical context, not separate permission for jobs or uploads.

## Inspected behavior

- `groimp_structure_export.load_snapshot` verifies plant/session and annotation backup hashes; its graph separates display positions/axes from leaf meshes.
- `ppfd_validation` already audits optical studies, gates reviewed leaf triangles, prepares directional GroIMP jobs, executes explicitly, and collects sensor/leaf flux. Reuse it unchanged where possible.
- Its source manifest does not recursively freeze geometry/review dependencies; its leaf loader can include other plants in a selected variant. The bridge must enforce scope and record all consumed dependencies before delegation.
- Saved S8 areas are projected proxies, not optical surfaces. Dates and completeness cannot be inferred from filenames, photo numbering, or triangle counts.

## Intended changes

Add `tools/plant_light_bridge.py`, regression tests, and a linked viewer. Accept an explicit pipeline run, plant/session, PPFD study/case and optional source metadata. Produce fresh build-only audit, immutable input snapshots/hashes, geometry inventory, prepared jobs and source-linked result tables. Verify stale dependencies and isolate the requested plant/session/date. Keep markers, hulls and structural axes display-only. Reuse existing reviewed surface and directional light gates. Missing physical inputs produce actionable blocker reports. Preserve measured-elevation and movement evidence when supplied; unknown motion/grouping stays explicit.

Expose preparation and explicit execution through the existing PPFD workflow; no native GroIMP run is part of this session. Exercise preparation/collection with synthetic fixtures and audit existing real runs without reconstruction or inference. Growth laws, coefficient fitting, physical acceptance thresholds, source-data edits, training, uploads and Git pushes are outside this work.

## Validation

Run targeted bridge, PPFD, geometry and trait regressions. Cover identity/date/hash conflicts, duplicate/foreign geometry, safe fresh outputs, missing/partial geometry, stale edits, transforms, weighted aggregation, HTML escaping and source preservation. Report software checks separately from real physical validation. Append actual results below at completion.

## Delivered

- Added `tools/plant_light_bridge.py` and its local HTML viewer. CLI actions: `audit`, `prepare`, `stale`; native execution requires `prepare --execute` and respects the declared job budget. This session did not run GroIMP.
- Reused `load_snapshot`, `make_graph`, the surface gate, shared board-to-grow placement, directional PPFD preparation, native execution/collection interfaces and frozen-split comparison. Frozen XL tools and `tomato3d/`, `config/`, `docs/`, photos, masks, source measurements and `growth_simulator.py` were not edited.
- Plant/session/date conflicts, foreign/duplicate surfaces, duplicate sensors/cases and source/review hash mismatches fail explicitly. Source dates can come from the capture or the growth record explicitly referenced by the structure; they never come from filenames. Optional metadata date mappings require hash-backed provenance. The first audit reported unavailable dates; the final adapter also reads the existing explicitly linked growth capture metadata, resolving those dates without editing sources.
- Fresh result directories hold input snapshots, source/media/code/artifact hashes, surface inventory, measured-elevation diagnostics, missing-input CSV, prepared jobs, source-linked leaf/sensor CSVs, plant summary and viewer. Large source photographs are hashed in place, not copied. Historic structure bytes have no independently recorded historic hash; this limitation remains explicit.
- DLI is calculated only for identical full-output fixture schedules. Missing or different/dimmed schedules stay unavailable. Both-face received flux, absorbed flux, sensor-plane incident PPFD and the legacy projected-area proxy remain distinct. Aggregation is area-weighted and incomplete geometry never becomes whole-plant absorption. All outputs retain false physical-validation flags.
- Added optional `--light-result` support to `tools.plant_site`; it accepts only a matching, non-stale bridge run and writes a fresh site file. The bridge viewer links/embeds the original source viewer, with its historical-label caveat. Surface selection preserves automatic/source IDs and photo names without creating biological identity.
- Source-backed optional `view_grouping` reuses the measured elevation equation. No default centre or threshold is inserted. Movement groups and reported transforms are retained; failed included groups or absent registered-geometry provenance block preparation. No registration or original S8 trait recomputation occurs here.

## Verification and actual artifacts

Final command (146 passed):

```powershell
python -X utf8 -m pytest tools/tests/test_plant_light_bridge.py tools/tests/test_ppfd_validation.py tools/tests/test_groimp_density.py tools/tests/test_groimp_structure_export.py tools/tests/test_groimp_light_scene.py tools/tests/test_groimp_light_sanity.py tools/tests/test_canopy_light.py tools/tests/test_plant_traits.py tools/tests/test_growth_simulator.py -q
```

31 new bridge tests cover the adapter, transforms, preparation reproducibility, area weighting, unavailable data, source integrity, stale detection, safe output, site linking, and execution/collection with explicitly synthetic fixture logs. Existing transport/sensor tests were also run. No new native convergence or physical-light experiment was performed.

Read-only smoke exercise: `python -X utf8 build/plant_light_bridge_smoke_20261003.py`. Final outputs: `build/plant_light_bridge_20261003_135615/`.

- `dwt_01`, `dwt_t1`, `dwt_t2`, `dwt_t3`: blocked real-input reports, with original source and media hashes unchanged. No optical leaf table or LightScene was supplied, and the header-only study has no plant case. T3 uses its existing A+B1 structural run, records B2 as excluded/failed, and separately reports unavailable registered optical geometry provenance. No unrelated newer run is selected automatically.
- `synthetic_prepared`: four explicitly synthetic triangles, directional native projects prepared, no native execution. This is software evidence only.
- `linked_plant_site.html`: fresh existing site with a link to the dwt_01 light audit. Historical source site was not modified.
- Browser verification: real blocker report rendered; synthetic report rendered with four surface IDs, selection showed source identity/area, selecting absorbed flux showed unavailable values, and browser error log was empty.

Reproducible entry points:

```powershell
python -X utf8 -m tools.plant_light_bridge prepare --run build/pipeline_20261001_s8 --plant dwt_01 --session dwt_01_20260920 --study build/ppfd_validation_inputs_20261002_202720/study.json --out build/my_fresh_plant_light
python -X utf8 -m tools.plant_light_bridge stale --result build/plant_light_bridge_20261003_135615/dwt_01
python -X utf8 -m tools.plant_site --run build/pipeline_20261001_s8 --light-result build/plant_light_bridge_20261003_135615/dwt_01 --out build/my_fresh_linked_site.html
```

The existing `ppfd-validation-study-1` plant case supplies `plant_id`, `session_id`, `geometry_snapshot_date`, `geometry`, `geometry_variant_id`, `surface_review` and `case_id`; geometry/review paths resolve relative to that study. Geometry columns and review gates are unchanged. Select among multiple matching cases with `--case`.

Optional `--metadata` JSON carries `plant_id`, `session_id`, optional `capture_date`, `source_hashes` (path to SHA-256), `view_grouping` (`centre_board_mm`, `top_elevation_gt_deg`, `source`) and `movement`. Movement records preserve `groups` with `group_id`, `alignment_status`, `included_in_optical_scene`; combining included groups requires `registered_geometry_sha256`. These are adapter provenance fields, not new geometry or biological laws. See smoke metadata for the source-linked T3 example.

## Remaining prerequisites

Supply reviewed optical leaf triangles, explicit whole/partial completeness, accepted normal conventions, measured lamp/optics/placement/sensor inputs and prospective numerical/accuracy settings through existing contracts. New native reflected-light validation remains a separate experiment. Generic capture regrouping and movement detection in the source reconstruction pipeline are still open; the bridge only audits supplied evidence. Observed-state growth initialization and biological transition models remain deferred as ordered in the original reference document.
