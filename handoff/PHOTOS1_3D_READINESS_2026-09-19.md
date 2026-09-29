# Photos-1: actual-photo 3D readiness

The active user goal is photo-based 3D reconstruction before PPFD. This goal is not complete.

## Observed input and user confirmations

- Read-only input: `C:/Users/sho36/Downloads/Photos-1-001/`, IMG_7910 through IMG_7927, 18 photographs.
- All .DNG filenames contain HEIF RGB images, not RAW/DNG. All decode at 3024 x 3024 pixels. EXIF identifies the iPhone 16 back camera, 5.96 mm, 26 mm equivalent. Digital zoom metadata is unavailable.
- User confirmed a 7 x 5 board with 38 mm cells. This confirmation is recorded in generated metadata; config was not edited. Flatness and the separate scale block remain unverified.
- Visual grouping is two near-top pictures, eight higher oblique pictures and eight lower-camera oblique pictures. Exact polar/azimuth angles are unavailable. Do not label the set as the previously planned 25-view capture or infer camera poses from order.
- User has no separate intrinsics or calibration photos and will take new board-only calibration photos.

## Executed checks

- Existing configured ChArUco detector: 17/18 images have at least six corners; IMG_7910 has four.
- Existing core calibration, using the 17 eligible plant-session views: RMS 7.8048 px. The result is a failed trial, not approved intrinsics.
- Per-frame PnP RMS: 3.3710 to 14.1490 px for the 17 solvable frames. The current 1 px acceptance limit approves **0/18** frames. The checked capture preserves failed statuses.
- Raw-image homography residuals range from 2.43 to 17.56 px. These conflate lens distortion, target shape, and detection error; they do not isolate board warp as the sole cause. The sheet visibly curls in some views.
- Diagnostic constrained calibrations did not resolve the issue: 9.9730 px with square pixels/fixed principal point/zero tangential distortion; 11.3004 px with an additional zero-radial-distortion constraint. Neither was promoted.
- Source SHA-256 hashes rechecked for all 18 originals. No source changes. No leaf geometry or PPFD output was produced from failed poses.

## Artifacts

- `build/photo_audit_photos1_20260919/`: audit JSON, photo_metrics.csv, contact sheets, previews and reproducible inspection scripts.
- `build/photos1_3d_20260919/images/`: full-size upright decoded RGB PNG working images, no resize or crop.
- `image_provenance.json`, `intrinsics.trial.json`, `trial_poses.json`, `board_diagnostics.json`, `IMG_*_board.jpg` overlays, `capture_plan.json`, `capture_checked/capture.json`, `readiness.json` under the same 3D folder.
- `build/photos1_3d_20260919/calibration_input/`: empty destination prepared for the user's new photos. No claim that these photos already exist.

## Code change and verification

Updated `tools/leaf_light/phone.py` to inspect container bytes and accept HEIF mislabeled .DNG. True TIFF/RAW DNG is rejected instead of being silently decoded as developed RGB. Originals remain unchanged. Removed the old 41-view-only wording from the generic phone-profile notice; capture order still requires explicit session labels.

Tests: `tools/tests/test_phone_container.py`, `tools/tests/test_leaf_light_phone.py`, `tools/tests/test_multiview_plant.py`: **16 passed**, including real HEIF encoder/decoder coverage, source preservation, rejection of TIFF/DNG, and existing reconstruction regressions. Pillow/HEIF runtime was loaded from `build/leaf_light_image_runtime`. Updated reader also successfully decoded actual IMG_7910.DNG.

## Next action when calibration photos arrive

1. Confirm the same device, lens, crop/resolution and capture mode; normalize through the same phone-image path. User guidance: empty board, rigid flat backing, same 1x lens and 1:1 framing, approximately 20 sharp original images from varied tilts and image positions.
2. Use the existing core ChArUco calibration (minimum 15 eligible views), then evaluate residuals and stability. Keep new runs in new build directories.
3. Re-run per-frame board PnP on the existing 18 working images. New intrinsics do not guarantee that warped-board capture frames become usable. Request replacement plant photos only if the new checks still fail.
4. Use accepted poses with the existing cross-view leaf annotator and `tools.multiview_plant reconstruct`. Retain physical landmark identities; do not fill hidden leaves or represent a plant silhouette hull as resolved leaf surfaces.
5. Verify a real leaf surface and its reprojections before any PPFD calculation. The Python light and GroIMP export modules remain downstream.

Reference: [OpenCV ChArUco calibration](https://docs.opencv.org/4.13.0/da/d13/tutorial_aruco_calibration.html). Target count and acceptance thresholds above come from this repository, not from a claimed universal accuracy guarantee.
