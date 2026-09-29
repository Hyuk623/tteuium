# Photos-1 editor backup to diagnostic reconstruction — 2026-09-19

## Implemented

`tools/rebuild_leaf_edit_session.py` connects an explicit saved annotator backup to the existing diagnostic reconstruction and depth exporter. It verifies the prepared capture, source photographs, intrinsics, board hash, and unchanged camera/quality evidence. Harmless fields added by the browser's capture normalization are accepted. Changed poses, calibration, quality thresholds, photographs or session identity are rejected.

The current backup is authoritative for edits and deletions. Missing points are not refilled from seed metadata. Separate organ/leaflet identities are preserved; split labels sharing `leaflet_id=unavailable` get a deterministic reversible viewer mapping. The complete backup, boxes, contours, identity history and provenance are retained. Saving a backup never establishes human review or metric validity.

An explicit current context annotation file preserves excluded partial/2D regions. Unchanged seed labels use the latest context, preventing the older A1 patch or B3 mesh from silently returning. A context-only identity explicitly edited in the backup replaces that context entry. Metadata-only partial-outline edits remain partial. Sparse and interior physical points have independent depth records; only complete boundary views form candidate surfaces. These point estimates may use more views than the coarse mesh, so separate tables identify the calculation scope.

`tools/editor_point_review.py` displays all saved editor points on original-resolution photographs, including incomplete/single-view labels and failed-pose frames. It draws observed boundary/interior points with different colors, never inferred contours or projected points. Its table shows IDs, original pixels, unvalidated depth or a reason for unavailable depth, and actual detected marker/corner IDs. Unknown and unavailable observations remain visible as records. Labels are escaped; stale source image hashes are reported.

## Current real-photo artifacts

`build/photos1_manual3d_20260919/edited_roundtrip01/index.html` is the new result entry point. It links:

- `preview/index.html`: six partial/coarse 3D candidates and eight 2D-only candidate regions, from current `manual_candidates.review06.json`.
- `labels/index.html`: all 18 photographs with the 60 saved editor observations.
- `editor_point_depths.csv`: saved editor observations including sparse/interior support. The 12 old B3 observations remain in the record but have unavailable depth because the current visual review rejects their physical correspondences.
- `depth/`: 62 mesh-source observations, 31 landmarks, all 18 frame statuses, six leaf records.
- `editor.backup.source.json`, `annotations.context.source.json`, `rebuild_report.json`, `verification.json`: exact inputs, source hashes and processing records.

This actual round trip used the prepared seed backup, **not a newly downloaded user's browser backup**. It did not read or modify browser-local user edits. Edited-pixel, deletion and interior-point paths were exercised in controlled regression fixtures. The editor does not invoke reconstruction automatically; export a backup and run the command below.

Independent visual review moved B3 to 2D-only regions in IMG_7913/7921. Newly inspected basal E1 and basal_right_2D regions are also preserved in 2D. E1's terminal tip is clear, but its two proposed side-lobe matches are not established; the three-point proposal is historical only and was not triangulated. Old source versions remain unchanged. Source review reports and inspected crops are under the same build directory.

## Reproduction

From the project root, with a new output folder:

```powershell
python -m tools.rebuild_leaf_edit_session --session build/photos1_manual3d_20260919/edit_session01 --backup PATH_TO_SAVED_BACKUP.json --context build/photos1_manual3d_20260919/manual_candidates.review06.json --out build/photos1_manual3d_20260919/edited_run_new
```

The original-resolution point gallery can also be rebuilt from existing records:

```powershell
python -m tools.editor_point_review --capture build/photos1_manual3d_20260919/edited_roundtrip01/capture.json --depth-csv build/photos1_manual3d_20260919/edited_roundtrip01/editor_point_depths.csv --out build/photos1_manual3d_20260919/edited_roundtrip01
```

## Verification and limits

Eleven rebuild tests and three point-gallery tests passed. Coverage includes actual synthetic edited-pixel reconstruction, deletion without seed resurrection, current-context downgrade, active replacement of nonseed identities, partial metadata, split IDs, tampered source/camera/quality rejection, independently triangulated interior points, inactive threshold status, original-resolution point colors, output confinement, HTML escaping, and exclusion of projected-only positions. Real-photo builders completed and artifact counts, copied-input hashes, withheld B3 depths and 18 labeled JPEGs were checked independently. Browser verification confirmed the per-photo saved-point table, actual marker IDs and B3's unavailable depths.

No deep learning, core pipeline, config, design, original photographs or human ground-truth records were changed. Whole-plant reconstruction and metric accuracy are still incomplete. Existing failed camera gates remain visible; none of these candidates are validated PPFD geometry.
