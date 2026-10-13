# Review of Claude's latest dwt_02 geometry and label-review implementation

## Request and scope

The user asked to inspect Claude's implementation. The latest LOG entries describe dwt_02 assistant-selected leaflet points, a whole-plant visual hull, a fitted main stem, compound-region proposals, an outside-compound label review page, camera overlays and a view-26 relabel reference. Review those artifacts and their generating code, along with the relevant original-pixel importer integration. Do not equate the independently completed Codex SAM mask batch with Claude's geometry work.

## Execution boundaries

Read existing photos, annotations, calibration, source code and generated results. Run focused tests and isolated reproducibility checks under a new build review directory. Preserve all original labels, human decisions, previous geometry, masks and running review servers. Do not run training, new model inference, PPFD, automatic human acceptance or new reconstruction on the original output paths. Do not edit Claude-owned pipeline/config/docs files. Record reproducible findings before proposing corrections.

## Validation plan

- Identify the actual latest files and distinguish implemented behavior from LOG claims.
- Inspect source-coordinate and camera-frame transformations, measured-pose usage, point quality gates, model assumptions and result provenance.
- Check that envelope/stem/compound-region proposals remain diagnostic and cannot silently become leaf surfaces or PPFD-ready geometry.
- Check label review persistence, identifier handling and preservation of original annotations.
- Run focused tests for the relevant importer/review interfaces and isolated checks for suspected defects.
- Append evidence, limitations and actionable findings here; append LOG/TODO handoff entries at completion.

## Outcome

Review in progress. No implementation change is asserted by this initial brief.

## Completed review — 2026-09-22

Reviewed the current local project files and Claude's latest LOG entries. This is a review, not a repair or an authorization to run new reconstruction. Source files and existing result files were not edited.

### Findings

**F1 / P1 — A centered crop can pass as a verified uncropped stretch.**

Location: `tools/roboflow_session_import.py`, lines 80-104 and 254. `alignment()` checks global correlation, orientation and translation but does not reject a changed scale from a symmetric crop. With the real prepared dwt_02 view 21, derived test images cropped by 10 px or 20 px on every edge and resized to 640x640 both return `accepted=true`, `(0,0)` offset and no reasons (correlations 0.985293 and 0.951818). The uncropped control returns 0.999952 and passes. A 40 px crop is rejected, showing this is an untested acceptance gap, not a broken probe.

A 20 px crop should map an export edge coordinate u through `20 + u*(3024-40)/640`; the current mapper instead uses `u*3024/640`. At u=100 this silently shifts the original coordinate by 13.75 px. The subsequent round-trip test cannot catch an incorrect transform because it just inverts the same assumed scale. This can shift boxes, masks and future 3D observations while reporting the mapping as verified.

Recommended correction: test local spatial agreement and scale/crop consistency before assigning `uncropped_stretch`; retain explicit unresolved mapping when evidence is insufficient. Add centered-crop regression cases, including a subtle crop and unchanged JPEG control. Do not silently tighten unrelated geometric quality gates or rewrite current source annotations. This finding does **not** establish that the current 30 provided export images were cropped; their recorded high correlations remain separate evidence.

**F2 / P2 — Saved geometry helpers cannot reproduce the latest geometry results.**

Locations: `build/dwt_01_02_3d_20260922/dwt_02/stem/stem.py:1`, `stem/tips.py:1`, and `visual_hull/hull.py:1`. Running the saved stem or tip file from its own directory raises `FileNotFoundError: hull.py`, because the `exec(open(...))` chain depends on files being in a different working directory. Running the saved hull file from its directory exits successfully but only defines image/mask helpers; it contains no voxel-carving/export driver. The stem file has centreline and intersection helpers, but no optimizer or report-writing driver. The compound-region assignment generator is absent from the reviewed local directory. `epi.py` also retains a Claude temporary scratchpad output path.

Consequently, correcting view-26 labels currently has no recorded project command that regenerates `stem_line.json`, `compound_assignment.json` and the voxel CSVs. Preserve these results as diagnostic snapshots, and hand over the complete executable generator, parameters, input hashes, output paths and focused checks. Replace working-directory-dependent execution with explicit imports/paths. Do not claim the latest geometry is a reusable integrated pipeline until that path is available.

### Implemented results verified

- Original-pixel import: 30 mapped photographs, 776 original human labels (388 each for dwt_01/dwt_02). All 46 input-file hashes recorded by the two import reports remain unchanged. The importer does not fabricate cross-view identities.
- dwt_02 visual hull CSV has exactly 7,630 unique 2 mm voxel centres, 2,756 surface-marked voxels, bounds x=67..127, y=-95..-21, z=35..105 mm. Its occupancy volume is 61.04 cm3 (report rounds to 61.0); this is not plant tissue volume or leaf area. The report sets `validated_metric=false` and `suitable_for_ppfd=false`.
- Compound-region CSV uses the same 7,630 voxels: A=1,084, B=3,482, C=2,176 and unassigned=888. Its detection IDs resolve to the saved seed. A/B/C remain proposals and are not mapped to L01/L02/L03 in the human growth JSON.
- The stored main-stem result represents a straight visible-lower-stem axis, z=23.27..75.71 mm; its own limits and false metric/PPFD flags are present. Fit statistics are in-sample agreement, not independent dimension validation; the reported optimizer could not be reproduced from the saved helpers.
- The assistant-selected leaflet has two 3D point estimates from views 26/27. Tip maximum reprojection error is 0.57 px and passes the configured point gate; attachment maximum is 7.57 px and fails. Both observations retain unconfirmed identity/human-review-pending status and fail pose quality. No accepted leaf surface is established.
- The 10 outside-compound review items resolve to existing detection IDs. View 26 has only two compound boxes, including one approximately 82.73x66.81 px; views 17/28 have no compound boxes. The annotated view-26 reference was visually inspected. These are annotation-review needs, not permission to enlarge boxes from predicted regions or delete leaflets.

### Integration and validation limits

The local project contains a `claude.ai/artifact/...` URL and a description of an external decisions collection, but no source for that review page or local decisions importer was found in the inspected implementation. Its actual persistence, camera-overlay rendering and synchronization with the local editor were not independently verified. Preserve external decisions explicitly before trying to merge them; do not infer that they already changed the source COCO or local mask review.

The stored hull report itself says that top views disagree and some real thin leaves were carved away. Therefore its phrase “upper-bound occupancy envelope” is not a guaranteed containment bound for the real plant with these inputs. Retain the diagnostic limitation and do not use the hull as a leaf surface/PPFD blocker. No new defect in the existing quality flags was observed.

### Evidence and tests

- `python -m pytest tools/tests/test_roboflow_session_import.py tools/tests/test_reconstruction_request.py -q`: **24 passed in 15.72 s**. Log: `build/claude_geometry_review_20260922/pytest.txt`. These existing tests do not cover the centered-crop acceptance case or the new scratch geometry helpers.
- `build/claude_geometry_review_20260922/reproduction_checks.json`: exact helper failures and crop-check outputs. `reproduce.py` records the reviewed probe; run it from the project root with Python. Derived image fixtures remain in that review directory.
- `build/claude_geometry_review_20260922/artifact_audit.json`: source hash, voxel, region and annotation-ID accounting.
- Source files, original labels, prior reconstruction artifacts, actual SAM review states and production review servers were preserved. No model inference, training, external review decisions, new geometry or PPFD was run.
