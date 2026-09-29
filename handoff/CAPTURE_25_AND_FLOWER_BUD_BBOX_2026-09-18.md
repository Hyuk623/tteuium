# Confirmed 25-view capture and separate flower/bud boxes

User confirmations on 2026-09-18 supersede the earlier unresolved 17-versus-9 interpretation.

## Capture arrangement

The user defines the viewing angle from the top-view direction, not elevation above the horizon:

| User polar angle from the overhead direction | Equivalent viewing position | Azimuth positions | Image count |
|---|---|---|---:|
| 0 degrees | Central overhead / top | One central view; azimuth not applicable | 1 |
| 45 degrees | Upper oblique | 0, 45, 90, 135, 180, 225, 270, 315 degrees | 8 |
| 90 degrees | Horizontal side | Same eight positions | 8 |
| 135 degrees | Lower oblique, looking upward | Same eight positions | 8 |
| Total | | | 25 |

These are nominal acquisition labels, not measured camera poses. Do not feed these angles into metric reconstruction in place of calibrated per-image extrinsics. A central top view is counted once.

**Unresolved geometry prerequisite:** the existing horizontal ChArUco sheet is nearly edge-on from 90 degrees and its printed top face is generally unavailable from 135 degrees. The pattern/fixture placement must support these views, or there must be a separately calibrated rigid camera/target transform. This turn does not choose a new target layout, fabricate an extrinsic matrix or change `config/`. A future multi-plane target needs known rigid transforms into the common plant/board frame, not unrelated boards treated as the same plane.

The standalone annotator accepts arbitrary photo counts and does not require exactly 41. However, the existing research protocol and subset generator assume 36 side + 5 top = 41; they do not automatically become a valid 25-view experiment. Claude/human must revise the protocol and then hand off the exact subset definitions. Preserve independent reconstruction per subset.

## Flower and bud annotation

Explicit request: separate flowers and buds as bounding boxes.

- `flower`: one manually identified flower per box.
- `bud`: one manually identified bud per box.
- Leaflets retain boundary/interior landmark and contour annotations.
- These boxes are **2D per-image observations**, not 3D geometry, cross-view organ identities or an automatic flowering assessment.
- The same flower in multiple photographs can have multiple observation IDs. Do not sum those boxes as unique plant-level flower count.
- Ambiguous/hidden objects must not be guessed. Annotation completeness is not inferred from zero boxes or a single marked object.
- Boxes are separate from the leaf mesh and PPFD path. No detector has been trained by adding this UI.

## Implementation and CSV contract

Maintained source: `tools/leaf_point_annotator.html`.

Generated local program: `build/leaf_point_annotator/leaf_point_annotator.html`.

Build: `python -m tools.leaf_point_annotator`.

Serve: `python -m tools.leaf_point_annotator --serve --open`, default `http://127.0.0.1:8817/leaf_point_annotator.html`.

Choose Leaf points, Flower bbox, or Bud bbox. In a bbox tool, drag empty image space to create; drag inside an existing box to move; drag the selected box's corner to resize. The New box button allows overlapping/nested boxes. The list supports selection, class correction and deletion. Undo covers leaf and bbox edits together. Space/right drag still pans.

`bboxes.csv` columns:

`plant_id, session_id, variant_id, image_file, annotation_id, class_name, x_min_px, y_min_px, x_max_px, y_max_px, image_width_px, image_height_px`

Coordinates are continuous **pixel-edge** coordinates, with top-left edge `(0,0)` and bottom-right edge `(width,height)`; max edges are exclusive for ordinary pixel indexing. Width is `x_max_px - x_min_px`, height is `y_max_px - y_min_px`. This differs intentionally from OpenCV point-center coordinates in the existing `points.csv`. Round-trip export preserves the image dimensions and observation ID. Imported rows must match current plant/session/variant, a selected image, dimensions and legal class/geometry; an existing matching ID is updated rather than duplicated. An invalid row is reported and skipped; no coordinate resizing or class imputation occurs.

Local browser storage and JSON backups include boxes under each variant's `boxes` map, keyed by image key. Legacy leaf-only variants gain an empty boxes map. Optional Claude artifact DB payloads also include boxes, but that remote service has not been exercised locally. Publishing this local HTML does not update an already hosted Claude artifact.

## Background advice

The user asked for a capture background recommendation. Suggested a matte neutral mid-gray background as a starting point for combined leaf/flower/bud imaging and later RGB analysis, keeping the ChArUco print unchanged and using a separate neutral reference card. This is a practical recommendation, not an empirically selected best background or a claim that arbitrary gray paper is colorimetric calibration. Reference for neutral color targets: https://calibrite.com/why-you-need-to-calibrate/?noredirect=en-GB .

## Prior requirements still open

- Google Drive folder import was selected by the user. Google Picker/OAuth integration and actual account setup/testing are still pending; this bbox task did not silently implement or validate that connection.
- Revised 25-view acquisition/pose fixture and view-subset experiment need a design handoff before modifying core/config.

## Validation completed in this turn

- `node --check build/leaf_point_annotator/check.js`: syntax passed for the extracted application script.
- `python -m pytest tools/tests/test_leaf_annotator.py -q`: 1 pytest wrapper passed; it runs 11 JavaScript model/controller tests in Node. Direct Node report: 11 passed, zero failures.
- Regressions cover reverse drag/clipping, zero/invalid rectangles, moving/resizing, cancelled gestures, separate leaf/bbox exports, class/ID/dimension-preserving CSV round trips, no duplicate import IDs, cross-session/subset rejection, local persistence/undo, camera/view isolation, and the earlier M/partial-contour fixes.
- Actual browser UI: flower box created by dragging, changed to bud, moved and resized; live coordinates, class and per-photo counts updated. These were synthetic demo annotations, not ground-truth flower labels on user photographs.
- A later browser file-chooser attempt lost its tab before the upload happened. No actual download/re-import or OAuth/cloud service success is claimed from that attempt. Local CSV serialization/import and storage behavior are covered by the Node regression harness.
- Maintained and generated HTML SHA-256 matched at verification (`353c47ac1e626cbe676731f345a3f1a13ec09e5238ab245f3847f9e9ce8e0a8b`). Core pipeline/config/docs were not edited.
