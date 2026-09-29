# New board-only photographs: inspection and calibration diagnostic

## Outcome

The user added 41 files, `IMG_7928.DNG` through `IMG_7968.DNG`, to `C:/Users/sho36/Downloads/Photos-1-001/` and requested a checkerboard check. All new files decode and have sufficient ChArUco corners. The resulting calibration and existing plant poses still fail to support the current metric 3D workflow. Trial intrinsics were **not** promoted to operational data or configuration.

## Observed inputs

- The new files are HEIF RGB containers named `.DNG`, like the previous 18 images; they are not RAW DNG. Full-size upright working PNGs were generated without resizing or cropping.
- All 41 new images are 3024 x 3024, iPhone 16 back camera 5.96 mm f/1.6, 26 mm-equivalent EXIF. These observable settings match the previous images; metadata cannot prove unchanged focus or computational processing.
- Existing user-confirmed/configured board: 7 x 5 squares, 38 mm cells, 266 x 190 mm, DICT_4X4_50, non-legacy pattern. Configuration was read, not edited; physical print size/flatness flags were not changed.
- All 59 original input hashes (18 plant + 41 new board) were rechecked unchanged.

## Detection

| Check | Result |
|---|---:|
| Readable new photographs | 41 / 41 |
| At least 6 ChArUco corners | 41 / 41 |
| All 24 ChArUco corners | 21 / 41 |
| Detected corners per image | 16–24 |
| Detected markers per image | 14–17 |

Several photographs visibly show unsupported/curling paper, with some held by an edge. The central marker region contains dirt or damage. These are observed issues, not a numerical attribution of all error to paper warp. Detection success alone does not establish a flat, geometrically reliable calibration target.

## Calibration and pose checks

Used the existing `tomato3d.calib.intrinsics.calibrate_intrinsics` with all 41 views, without outlier deletion, relaxed thresholds, SfM or nominal angles. Calibration RMS: **9.0644 px**.

The existing preparation tool applies the configured 1 px reprojection limit to each pose. With the new full calibration:

| Image group | Solvable | Pass 1 px pose limit | Pose RMS range | Median |
|---|---:|---:|---:|---:|
| New board views used for fitting | 41 / 41 | 0 / 41 | 3.1095–13.3285 px | 8.4398 px |
| Existing tomato photographs | 17 / 18 | 0 / 18 | 2.6640–17.5046 px | 8.2387 px |

A separate diagnostic split used sorted indices divisible by 5 as held-out views (9 held-out, 32 training), specified in the script before execution. Training calibration RMS was 9.0949 px. Held-out board pose RMS was 3.9016–12.0327 px, median 9.1704 px; 0 / 9 passed the existing pose gate. No parameters were tuned using held-out errors.

RMS values from the earlier plant-only calibration and this board-only fit describe different training sets; they are not a controlled improvement comparison. Reprojection errors combine target shape, camera/image processing, parameter fitting and corner detection. The present check cannot isolate a single cause.

## Next input that can resolve the blocker

Use a clean print firmly attached across its surface to a rigid, flat backing, without bubbles or unsupported bowed edges. Move/tilt the entire backing rather than lifting the paper. Keep the same phone/lens/square capture mode, and collect approximately 20–25 sharp board-only originals with varied tilts, distances and positions in the image. The current core needs at least 15 eligible views. Remeasure the printed cell length and retain the actual board identity.

After that, rerun calibration and test the existing plant photographs again. A better calibration may still not rescue plant captures made with a warped board; replacement plant photographs may then be needed. The current labeling/SAM review can continue in 2D, but no metric leaf mesh, internode length or PPFD validation is established by these inputs.

## Artifacts and reproduction

All generated results: `build/photo_audit_board_20260919/`.

- `audit.py`, `audit.json`, `photo_metrics.csv`: source metadata, hashes and detection statistics.
- `images/`: 41 full-resolution working PNGs. `previews/` and `contact_1.jpg` through `contact_4.jpg` are visual-review images only.
- `check_calibration.py`: calls existing calibration and pose implementations.
- `intrinsics.board_only.trial.json`, `intrinsics.holdout_training.trial.json`: diagnostic models only.
- `calibration_pose_metrics.csv`, `calibration_check.json`: all failures retained and summarized.

```powershell
python -u build/photo_audit_board_20260919/check_calibration.py
```

No core, config, docs, ground-truth records, original photo, existing capture manifest, or active intrinsics file was changed. Reference: [OpenCV ChArUco calibration](https://docs.opencv.org/4.13.0/da/d13/tutorial_aruco_calibration.html), [camera calibration and planar object coordinates](https://docs.opencv.org/4.13.0/dc/dbb/tutorial_py_calibration.html).
