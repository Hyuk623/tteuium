# Claude handoff: capture conditions and JSON-guided label correction

## Purpose and latest user decisions

Read this handoff before continuing the two new plant sessions. It consolidates the user's latest instructions and supersedes conflicting historical open-item descriptions. This turn prepares documentation only; it does not run reconstruction, learned inference, training, or PPFD.

1. The user physically prevents different capture dates for the same plant from being mixed. Treat date-isolated input folders and selected mapping rows as an operating precondition. Importer R2 is accepted operationally; no additional date-mixing code work is requested.
2. The user photographs with one lens. Do not describe lens switching as an observed fault. Matching the earlier calibration's zoom/crop/focus/processing settings is still unverified; same resolution alone is not proof of calibration compatibility.
3. The user will check leaflet/landmark identity by comparing photo views. Keep the same physical point across views, not merely the same screen-relative position or view code. Leave occluded/unobserved landmarks unfilled.
4. When leaf counts or positions appear wrong, consult the corresponding plant/date manual JSON while reviewing and correcting annotations. The JSON is the user's biological reference; do not change it merely to make a model's output agree.

## Current files and authoritative counts

Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis/`.

Manual records:

- `tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json`
- `tomato_photos_organized_/260920/dwt_02/260920/dwt_02_260920.json`

| Record | Compound leaves | L01 / L02 / L03 leaflet counts | Unfolding compound leaves | Growth shoots | Trusses |
|---|---:|---|---:|---:|---:|
| dwt_01 | 3 | 8 / 9 / 9 | 0 | 3 | 0 |
| dwt_02 | 3 | 7 / 7 / 5 | 0 | 2 | 0 |

All listed is_unfolding flags are false. Both saved records now parse and have consistent entry counts and unique compound-leaf IDs. dwt_01's former leading-zero syntax and unfolding conflict were corrected by Codex at the user's explicit request, with a byte backup; see `CODEX_GROWTH_JSON_CORRECTION_2026-09-20.md`. Later read-only checks confirmed the correction. Do not reopen the resolved question or claim that dwt_01 is still invalid. Re-read records before future work in case the user updates them.

The leaflet sums are 26 and 19 respectively for the listed compound leaves; these are count references, not required per-photo detections. Do not add growth_shoot_count to leaflet totals or assume those shoots already have individually countable leaflets. Unknown values remain null, not zero. Future blank templates include growth_shoot_count=null.

## How to use the JSON when correcting labels

1. Match plant_id and capture_date to the selected annotation session before reading its counts. IDs such as L01 are local to a plant and require an explicit connection to image annotations.
2. Distinguish a compound leaf from an individual leaflet. Link each reviewed leaflet to its parent compound leaf only when supported by the photos or user confirmation; do not invent the parent relationship from count order alone.
3. Compare the JSON counts with unique reviewed leaflet identities across the session. Repeated views of one leaflet count once. Report missing, duplicate and uncertain identities separately. A partly occluded photograph need not show all leaflets in the JSON.
4. For count discrepancies, inspect overlays and other views, then correct duplicate IDs, merged/split instances, missed visible leaflets or incorrect parent links when visually supported. Do not create hidden geometry simply to reach the expected count. A manual record can guide review without proving the model has observed every organ.
5. For position discrepancies, use the JSON to verify the intended plant/compound-leaf identity, then compare original photos, bbox/masks and the same physical landmark across posed views. Correct the supported 2D observation or identity link and recompute depth. Preserve original-image pixel coordinates and edit history.
6. **The current growth JSON contains counts and IDs, but no 2D/3D positions, pose, orientation, or spatial ordering.** It cannot determine where a leaflet belongs in XYZ or which side of the plant L01 occupies. Do not infer those facts from array order, IDs or counts. If the evidence is insufficient, retain unknown/partial status and identify the ambiguity for human review.
7. Correct annotation/model output against the user's record when the photo evidence supports it. If a biological record itself appears wrong, show the discrepancy for user confirmation rather than overwriting it. Preserve backups/history for accepted corrections.

## Board explanation and remaining code issues

R3 means the importer always writes the same text claiming that a 7x5 / 38 mm caption was observed. This is a provenance defect, not evidence that the user's physical board is wrong. PnP uses configured board geometry; the caption string does not itself change geometry. Record actual session-specific board evidence or unavailable, instead of copying an observed-caption claim into every future session. A correct match between the real square size and configured square size is the relevant scale condition; do not infer a new user confirmation from this explanation.

Remaining review items from `CODEX_NEW_CAPTURE_IMPORT_REVIEW_2026-09-20.md`:

- R1: check calibration compatibility explicitly, or state it is unverified. Do not claim calibration EXIF agreement solely from equal image dimensions. One-lens operation is recorded as mitigation.
- R3: replace hardcoded observed board-caption evidence with sourced per-session evidence or unavailable.
- R4: preserve inactive null quality thresholds instead of crashing on float(None). Current 1.0 px threshold is not affected.
- R2: operationally handled by the user; no code action requested.

## Geometry and runtime status

Prepared sessions are under `build/new_captures_20260920/dwt_01/edit_session/` and `build/new_captures_20260920/dwt_02/edit_session/`.

- Each contains 18 photos: top 01/03, side 11-18, oblique 21-28. Codes are capture labels, not measured camera poses.
- dwt_01 has 6 solved poses; dwt_02 has 8. None passes the 1 px gate. All 16 side views lack a solved pose.
- Unposed side images may assist human identity review but cannot currently supply calibrated triangulation rays. Do not invent their poses from nominal view numbers.
- Annotation and diagnostic reconstruction can proceed with supported observations, while retaining unvalidated/partial flags. Do not claim accurate dimensions, a completed plant surface or PPFD-ready geometry.
- A bbox cuboid is a location guide, not a leaf surface or a PPFD occluder. JSON counts do not supply missing surfaces.
- Earlier editor split/relink metadata and bidirectional point-match ambiguity defects were fixed and tested. The original-photo CPU SAM automatic trial timed out after 1800 seconds; successful automatic throughput remains unverified. This task does not restart or repeat it.

## Suggested follow-up validation

For later implementation, check that repeated photo views do not inflate counts, compound leaves and leaflets remain distinct, growth shoots stay separate, unknown/occluded organs are not synthesized to meet totals, and all identity/point corrections retain backups and original pixel coordinates. Corrected points must invalidate/recompute dependent depths; stale surfaces must not be presented as current.

Read `AGENTS.md` and `CONVENTIONS.md`, coordinate file ownership, and reuse the existing editor/rebuild workflow. Preserve source photos, accepted annotations and manual growth records. Report which changes are implemented versus proposed, and which values are observed versus inferred.
