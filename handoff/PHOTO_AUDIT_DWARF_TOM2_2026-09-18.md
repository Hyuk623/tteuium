# Photo audit: dwarf_tom2_12_260918

Inspected on 2026-09-18 at the user's request. Source files were read only; all 21 SHA-256 hashes were rechecked after inspection. This is a capture/input audit, not a plant-health diagnosis or a validated reconstruction.

## Input and method

- Source: `C:/Users/sho36/Downloads/dwarf_tom2_12_260918-1-001/dwarf_tom2_12_260918/`.
- 21 images: `IMG_7878.HEIC` and `IMG_7879.DNG` through `IMG_7898.DNG`.
- All 21 decode as HEIF; the twenty `.DNG` files contain HEIC/HEIF bytes, not DNG raw data. Renaming a suffix does not convert pixels.
- Decoded with Pillow 12.3.0 and pillow-heif 1.7.0, respecting decoder/EXIF orientation. No raw files were rewritten or renamed.
- Board detection: OpenCV 4.13.0, the existing `tomato3d.calib.board` board builder and detector, and the current `config/board_spec.json` (7 by 5, DICT_4X4_50). No alternative board identity was inferred from overlapping marker IDs.
- Visual inspection: both contact sheets covering all 21 images, plus larger previews of IMG_7878, IMG_7881, and IMG_7892.
- Detection used original-size decoded pixels. A diagnostic repeat at maximum edge lengths 1500 and 1000 px checked scale sensitivity. These resized images are not calibrated pipeline inputs.
- The printed caption visible in photographs says 7 by 5 / 266 by 190 mm. This is consistent with the configured pattern, but does not establish actual printed dimensions or replace a session manifest.

## Findings

| Finding | Evidence | Consequence |
|---|---|---|
| Mixed physical camera/lens modes and image dimensions | IMG_7878: iPhone 16, lens label `back dual wide camera 2.22mm f/2.2`, 3024 x 4032, reported digital zoom about 1.909. Remaining 20: `back camera 5.96mm f/1.6`, 3024 x 3024; digital zoom unavailable. | A single unadjusted intrinsic calibration cannot be assumed valid for this set. Missing zoom metadata does not prove fixed zoom/focus. |
| Weak board detection | Native-size ChArUco corners: zero in 14/21; at least six only in IMG_7881 and IMG_7882 (six each, non-collinear). The number of frames reaching six remained 2/21 after both diagnostic resize checks. | Most views cannot pass the current `min_charuco_corners_for_pose = 6` input gate. This count is not a pose-success or reconstruction-accuracy result. |
| Leaf-versus-board focus tradeoff | IMG_7891–7898 show recognizable leaves with blurred/cropped board regions; no ChArUco corners were detected there. IMG_7881/7882 have sharper board details, but the plant is partly outside the image and leaf detail is blurred. | There is no demonstrated set of useful leaf views with reliable calibrated poses. Do not interpret the two corner-count candidates as two sufficient reconstruction views. |
| Leaf structure is visible in several views | Leaf edges, midribs, stem and petiole connections can be seen in several oblique/side photographs. | Useful for manual leaflet/point-labeling practice and selecting repeatable landmarks. This does not provide metric 3D positions without the missing camera geometry. |
| Packaging occludes the lower structure | Transparent wrapping rises around the pot and covers some lower stem/board regions; hands appear at the board edge in several frames. | Secure the wrapping below the observed organs/markers and keep the specimen stable during a capture set. Non-rigid leaf motion has not been measured here. |
| Required metadata/calibration absent | No capture/session manifest or intrinsics file accompanies this folder; no `intrinsics*.json` was found in the project's `data/calib` at inspection. | View identities/angles, calibrated camera poses and metric leaf reconstruction remain unavailable. Nominal 45-degree/8-view placement cannot substitute for camera pose. |

Native corner counts, in filename order:

`0, 0, 3, 6, 6, 4, 4, 0, 0, 0, 0, 1, 3, 0, 0, 0, 0, 0, 0, 0, 0`.

The images contain top/board-detail views, upper oblique views, and lower side views. Exact elevation and azimuth, and completion of a uniform eight-position ring, were not established. Do not assign capture indices from the file count alone.

## Practical next capture check

1. Keep one physical lens and one image aspect/resolution throughout calibration and plant captures. Avoid switching between macro/other lenses or between square and 4:3 crops within a calibrated set.
2. Start with a little more camera distance so the entire plant and multiple separated board regions are visible together. Enlarge on screen to check that both leaf landmarks and marker edges are sharp. If computational background blur is enabled, disable it; the photographs alone do not prove whether the observed blur is optical or computational.
3. Hold the phone/lighting steady, flatten and secure the printed board, and secure loose pot wrapping without moving the leaves during the session.
4. Inspect one top, one upper oblique and one lower view before taking a full ring. Aim to exceed, rather than merely equal, the configured minimum of six spatially distributed ChArUco corners. A corner count alone is not a complete calibration/pose acceptance test.
5. Preserve original files. Export correctly encoded, original-dimension JPEG/PNG working files and use the same orientation/crop conversion for calibration. Simply renaming these `.DNG` files to `.jpg` is insufficient.
6. Keep the manual labels as practice data; re-capture before claiming PPFD or quantitative geometry accuracy from this session. The proposed 8-per-ring versus 8-across-rings interpretation is still not fixed by this audit.

## Artifacts and reproducibility

- `build/photo_audit_20260918/audit.json`: input hashes, format/EXIF metadata, detection counts, limits.
- `build/photo_audit_20260918/photo_metrics.csv`: per-photo measurements, including scale checks.
- `build/photo_audit_20260918/contact_1.jpg`, `contact_2.jpg`: all 21 frames; captions show **native-size** counts only.
- `build/photo_audit_20260918/previews/`: resized inspection JPEGs, not metric input images.
- `build/photo_audit_20260918/audit.py` then `check_scale.py`: one-off read-only audit scripts; use the locally installed optional HEIF decoder under `build/leaf_light_image_runtime`.

No camera poses, leaf meshes, PPFD values, disease diagnoses or accepted photo-subset results were fabricated.

## Interrupted annotator/Drive work checkpoint

Before this audit request, the user-authorized local annotator usability changes were written to `tools/leaf_point_annotator.html` and `build/leaf_point_annotator/leaf_point_annotator.html`. The original is backed up under `build/leaf_point_annotator/backups/leaf_point_annotator_before_usability_20260918.html`; a build/serve launcher is `tools/leaf_point_annotator.py`. The browser rendered the new controls, but interaction/export regressions have **not yet been completed**. Do not treat these as a fully validated release.

The user selected Google Drive folders (not Google Photos) as the intended source. Google Picker + GIS OAuth + Drive blob download was researched; a Drive connector has **not yet been implemented or authenticated**. Public OAuth client ID / Cloud project number / API-key setup remains necessary. No user Drive files have been read or changed. This audit does not cancel that requirement.
