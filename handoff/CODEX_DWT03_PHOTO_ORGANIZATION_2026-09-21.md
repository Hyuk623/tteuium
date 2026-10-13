# dwt_03 photo organization

User requests organizing C:/Users/sho36/Downloads/iloveimg-converted (2) like the previous captures, using plant ID dwt_03. Preserve source bytes and existing datasets. Inspect actual image formats, EXIF capture dates and chronological/view groups before assigning filenames. Initial inventory contains 45 JPEG-named files in two numeric groups (IMG_7101..7129 with gaps and IMG_8059..8076); do not assume a single 18-view set. Unknown growth counts remain null. No reconstruction or inference.

## Expanded scope and inspected selection

User also requested iloveimg-converted (4) as dwt_04. Visual contact-sheet review and EXIF identify:
- dwt_03: IMG_8059..8076, 18 genuine JPEG images, 2026-09-21; 3024 square. Exclude the unrelated 27 ornamental-plant images dated 2026-07-25 from folder (2), leaving originals untouched.
- dwt_04: IMG_8032, IMG_8036..8052, 18 genuine JPEG images, 2026-09-20. First top image is 3024x4032, others 3024x3024; preserve bytes and report mixed resolution for downstream calibration compatibility.

Contact sheets support 2 top + 8 side + 8 oblique ordering. Assign direction codes by existing capture-order protocol, not measured pose or independently proven board-relative directions. Preserve existing outer-date/plant/date layout; append new mapping rows only after backup and duplicate checks. Create blank manual growth templates including growth_shoot_count=null; do not infer biological counts.

## Completion

- Organized dwt_03 (18 JPEGs, EXIF date 2026-09-21) under tomato_photos_organized_/260921/dwt_03/260921/.
- Organized dwt_04 (18 JPEGs, EXIF date 2026-09-20) under tomato_photos_organized_/260920/dwt_04/260920/.
- Filenames use dwt_XX_YYMMDD_ZZ.jpg with codes 01,03,11..18,21..28. Capture order was chronological; contact sheets support the broad view groups. Exact direction geometry/top roll is not independently validated.
- Each session has its blank human growth JSON (including growth_shoot_count), and filename_mapping.csv. Master filename_mapping.csv now has 72 rows, preserving old bytes and appending 36 rows. Exact old mapping backed up in build/dwt03_organization_20260921/filename_mapping.before.csv.
- Mapping organized_path values remain relative to the appropriate OUTER date directory, not the mapping CSV location: --source tomato_photos_organized_/260921 for dwt_03 and --source tomato_photos_organized_/260920 for dwt_04. Master mapping supports selection by plant; session mapping also carries the same base convention.
- Verified all 63 supplied source hashes unchanged, all 36 new copies byte-identical, original 36 dataset images and existing growth JSONs unchanged, and no duplicate plant/date/view keys in the 72-row master mapping. All selected JPEGs passed PIL structural verification.
- The 27 unrelated 2026-07-25 ornamental photographs in folder (2) were excluded and left untouched; exact paths/hashes are in organization_result.json.
- dwt_04_260920_01.jpg (source IMG_8032.jpg) is 3024x4032; other dwt_04 views and all dwt_03 views are 3024x3024. No cropping/resizing/rotation/re-encoding occurred. Current uniform-size importer may refuse dwt_04 as a whole; do not apply square-image intrinsics to the portrait image or silently crop it. File organization is complete independently of calibration compatibility.
- No camera pose calculation, label creation, inference or 3D reconstruction was performed. Audit scripts and contact sheets are under build/dwt03_organization_20260921/.
