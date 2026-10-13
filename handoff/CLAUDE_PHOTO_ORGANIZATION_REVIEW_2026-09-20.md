# Claude handoff: organized photographs and manual growth records

## Request and scope

The user requested verification of `SIDE_CHAT_PHOTO_ORGANIZATION_2026-09-20.md` and an English handoff for Claude Code. This document is the main-thread receipt and follow-up checklist. The original side-chat handoff remains intact. Verification is read-only: do not change photographs, filenames, biological observations, calibration, accepted labels or the running editor. No conversion, segmentation, reconstruction, training or PPFD calculation is part of this task.

## Current storage and capture contract

Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis/`.

Use `tomato_photos_organized_/260920/dwt_XX/260920/` for the current dataset. Preserve the outer date directory introduced by the user; do not re-copy Downloads or silently normalize the hierarchy.

Photo names are `dwt_XX_YYMMDD_ZZ.heic`; manual records are `dwt_XX_YYMMDD.json`. There are two plants, each with 18 expected views:

| View group | Nominal polar angle from vertical | Codes |
|---|---:|---|
| Top | 0 degrees | 01, 03 |
| Side | 90 degrees | 11 through 18 |
| Middle / oblique | 45 degrees | 21 through 28 |

These codes follow the user's input-order protocol; visual view classification was not independently established. They are capture labels, not ArUco IDs or measured poses. In particular, 27 means oblique direction 7, while 17 means side direction 7. Preserve that distinction unless the user changes the convention. The exact top-view roll convention for 01 versus 03 remains unconfirmed.

Board-relative directions, with the printed heading above the diagram:

```text
6 --- 5 --- 4
7   plant   3
8 --- 1 --- 2
```

Do not infer camera poses from these directions or transfer calibration/accepted annotations from the older IMG_791x dataset. Verify camera settings, image orientation, board variant and session identifiers before later geometry work. The board variant for these new captures is not established by the naming convention.

## Manual metadata contract

Keep `compound_leaf_count`, per-leaf `compound_leaf_id`, `leaflet_count`, `is_unfolding`, `unfolding_compound_leaf_count`, `growth_shoot_count`, `truss_count` and `notes`.

Future blank templates must include `growth_shoot_count: null`. Its finer biological counting boundary is not yet specified. Keep it separate; do not add it to compound-leaf totals automatically. Unknown values are null; zero denotes a confirmed absence. Completed records must have unique compound-leaf IDs, a matching entry count, and a consistent unfolding subset. The user's current biological values must not be guessed or silently repaired.

## Verification

A fresh audit will check expected filenames, mapping resolution, HEIC signatures, SHA-256 hashes and strict JSON parsing. Results and specific follow-up actions are appended below after the audit. This is not an image-quality, organ-count or 3D-accuracy validation.

### Audit completed: 2026-09-20 18:34 KST

Evidence: `build/photo_handoff_review_20260920/audit.json`; reproducible read-only check: `python build/photo_handoff_review_20260920/audit.py` from the project root.

- 36 mapping rows; 18 expected HEIC filenames in each plant folder. Both filename/code sets match exactly.
- All 36 current image SHA-256 hashes match the mapping CSV. All 36 have HEIC-compatible file-type signatures. This verifies bytes/container identity, not successful image decoding or visual quality.
- Mapping entries such as `dwt_01/260920/...` resolve using `tomato_photos_organized_/260920/` as the base. They do not resolve directly beside the CSV because of the additional date directory. The CSV was not rewritten.
- **dwt_01 is blocked for strict metadata import.** JSON parsing fails at line 9, column 25. Raw numeric tokens include `08`, `09`, `09`, and `03`; JSON numbers cannot have these leading zeroes. Separately, all three `is_unfolding` values are false while the apparent unfolding total is 3. Do not choose which biological value is correct. `growth_shoot_count` is absent. The file remains unchanged.
- **dwt_02 is syntactically valid and internally consistent.** Compound leaves: 3; L01/L02/L03 leaflet counts: 7/7/5; all unfolding flags false; unfolding total: 0; growth shoots: 2; trusses: 0. IDs are unique and the compound-leaf entry count agrees. These are user observations, not independently measured plant counts.

## Claude follow-up checklist

This is a handoff for subsequent work, not evidence that the following items are already implemented. Follow the user's next implementation instruction and repository ownership rules; the present request authorizes documentation and verification only.

1. Re-read current records before changing anything, as the user edits them manually. For dwt_01, obtain the intended unfolding status/count from the user. Distinguish a syntax-only leading-zero correction from a biological correction. Preserve an original copy and a correction record if an edit is subsequently requested; never silently repair or coerce invalid input.
2. When integrating organized captures, allow the actual outer-date hierarchy and explicitly resolve mapping paths against the date directory. Reject missing paths, duplicate/conflicting mappings and changed hashes rather than silently shifting view codes. Preserve the existing CSV and folder layout unless a change is requested.
3. Treat manual growth JSON and photo labeling as separate records. A compound-leaf ID such as L01 is not automatically an existing editor leaflet ID. Any future link must explicitly retain plant, capture session, compound-leaf and leaflet identity; never merge plants based on repeated short IDs.
4. Add `growth_shoot_count: null` to future blank templates and retain entered values such as dwt_02's 2. Missing fields in old files mean unentered, not zero. Keep the unfolding count a subset of the compound-leaf count.
5. Before an image-import/conversion implementation, check actual HEIC decoder support. If conversion is later requested, produce derived copies, record source/output hashes, dimensions and orientation transforms, and maintain the mapping to original image coordinates. Renaming a HEIC extension to JPG is not decoding/conversion. Do not reuse old pixel annotations after an unrecorded rotation/crop/resize.
6. Confirm the capture board and compatible intrinsics before pose recovery. Use measured ChArUco poses; view codes are only capture metadata. Do not attach the older calibration or labels to these two new sessions by filename order.

Suggested validation for future integration: two distinct plants with repeated view codes; missing view without renumbering; moved-root path resolution; invalid JSON and contradictory unfolding totals reported without writes; null versus zero retained; future-template growth_shoot_count included; HEIC orientation/coordinate round-trip; existing photos and accepted labels preserved.

## Main-thread status to keep separate

`CODEX_AUTO_DRAFT_FIX_2026-09-20.md` records the earlier editor changes: identity split/relink metadata migration and bidirectional match ambiguity were fixed and tested. SAM was configured and real model loading verified, but the original-photo CPU automatic request exceeded 1800 seconds; useful automatic-generation throughput is not validated. That trial used the older IMG_7913 capture, not these new 36 HEIC photographs. This handoff check did not run a model or change a server.

New photographs are organized and integrity-checked; neither new plant has been decoded/visually assessed, labeled, reconstructed or validated for PPFD by this audit. Do not describe them as completed 3D models or training-ready ground truth.

## Message to Claude Code

Read `handoff/CLAUDE_PHOTO_ORGANIZATION_REVIEW_2026-09-20.md` and `handoff/SIDE_CHAT_PHOTO_ORGANIZATION_2026-09-20.md` before the next capture-import task. Use the current organized folders as read-only inputs, preserve the 18-view naming convention, and carry the growth metadata contract forward. Start by reporting the dwt_01 record conflict and the CSV base-directory caveat; do not infer the missing biological answer. Coordinate any tools/ changes with Codex and keep application implementation separate from this documentation-only handoff.

## User clarification after this audit — authoritative intended dwt_01 values

The user supplied the corrected record in chat: L01/L02/L03 have leaflet counts 8/9/9; every is_unfolding is false; unfolding_compound_leaf_count is 0; growth_shoot_count is 3; truss_count is 0; notes is an empty string. These values are internally consistent with compound_leaf_count=3. This resolves the earlier biological ambiguity; do not ask the user to choose the unfolding count again.

However, a fresh disk read and strict audit at 2026-09-20 18:35:53 KST still found the old dwt_01 file (SHA-256 31f75ada8602fd7c6730b44fa79c64f9933b4955affae5ce21e847e9651e9756): 08/09/09, unfolding total 03, no growth_shoot_count. The corrected chat values and the current saved file are therefore distinct states. Saving/synchronization is not yet verified; do not claim the on-disk JSON now passes. Re-read the file before integration, use the user's explicit values above when a file correction is requested, and preserve any newer manual edits. No source record was overwritten by this check.

## Saved dwt_01 correction completed — 2026-09-20 19:19 KST

The user explicitly authorized correction from chat. The saved dwt_01 JSON now parses and has leaflet counts 8/9/9, all is_unfolding=false, unfolding total 0, growth_shoot_count=3, truss_count=0. Original bytes backed up; dwt_02 and all photographs unchanged. Earlier invalid-file/save-pending statements in this document are historical and superseded. See CODEX_GROWTH_JSON_CORRECTION_2026-09-20.md for hashes, backup and validation.
