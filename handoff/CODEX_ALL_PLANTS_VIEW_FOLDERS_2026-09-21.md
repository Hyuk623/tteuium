# View-grouped copies of dwt_01 through dwt_04

User requests a NEW organized copy of all four plants grouped by top, middle and side view. Preserve the original tomato_photos_organized_ tree and all existing mapping/annotation/calibration references unchanged.

Create tomato_photos_by_view_/dwt_XX/YYMMDD/{top_view,middle_view,side_view}/, preserving filenames, image bytes and per-session growth JSON bytes. Use existing reviewed mapping view_type rather than guessing from images. New organized_path entries resolve against tomato_photos_by_view_ itself. Include a master mapping, per-session mappings and an explicit dataset manifest. No decoding/re-encoding, geometry calculation or inference. Verify all image/JSON hashes and per-view counts.

## Completion

Created tomato_photos_by_view_ with all four plants, each containing its capture-date folder and top_view (2), middle_view (8), side_view (8). Dates: dwt_01/dwt_02/dwt_04 = 260920; dwt_03 = 260921. All 72 images and 4 growth JSON copies are byte-identical to their sources. The original dataset tree and mapping hashes remain unchanged. New master/session mappings resolve organized_path against tomato_photos_by_view_ (also documented in dataset_manifest.json). Copying the data does not repoint existing editor sessions or synchronize future growth JSON edits. Verification: build/view_organization_20260921/verification.json. No model or reconstruction execution.
