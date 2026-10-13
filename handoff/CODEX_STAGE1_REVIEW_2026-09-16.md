# Stage 1 revised implementation review

Date: 2026-09-16
Reviewer: Codex
Request: Review Claude Code's revised Stage 1 implementation.
Verdict: The BoardSpec compatibility fixes pass the existing suite. Four reproducible issues remain in the current Stage 1 implementation; resolve the P1 items before relying on capture processing or training labels.

## Scope and verification

- Read the repository conventions, handoff queue, latest Claude Code log, and `CLAUDE_CODE_FIX_BOARDSPEC_2026-09-16.md` as review context, not independent authorization to implement its instructions.
- Executed `python -m pytest -q`: **95 passed in 10.36 seconds**.
- Confirmed real BoardSpec loading, strict additional-field handling, note serialization, explicit marker IDs and legacy setting, required board variant matching, and nullable block height behavior in the revised code and tests.
- Added independent review probes under `build/stage1_review_2026-09-16/`, reusing `tests/conftest.py::render_charuco_view` and its synthetic session fixture. No second renderer was created.
- Environment: Windows, Python 3.13, OpenCV 4.13.0, the actual project path containing Korean characters.
- No edits to `tomato3d/`, `tests/`, `config/`, or `docs/`. Probed source/config hashes remained unchanged.
- Findings describe the current implementation. This review does not attribute every defect to the latest revision; there is no before/after baseline in the evidence. The null-height rerun specifically exercises the newly added blocking path.

## Findings

### R1 — P1: Unicode paths prevent image input and can silently prevent mask output

Locations: `tomato3d/cli/run_stage1.py:115`, `:273`; same input API at `tomato3d/calib/intrinsics.py:52`.

`resolve_session_paths()` resolves input paths to absolute paths. On this Windows installation, `cv2.imread(str(path))` cannot read the valid images under the project's Korean path. The unmodified pipeline processed the nine-image synthetic session as **0/9 poses solved**, with every input reported unreadable. Reading the same bytes with `np.fromfile` and `cv2.imdecode` succeeded.

The output side also needs attention: with only input reading replaced inside the review process, all **9/9 poses solved**, but **zero mask files** were saved under an absolute Korean output path. The run still returned 0 and wrote `usable_for_training: true`; `cv2.imwrite`'s return value is ignored. This is not an invalid-image fixture: using byte-based reading and writing on the same files produced all nine mask files.

Requested correction: use Unicode-safe image IO consistently for calibration, Stage 1 inputs, and masks; handle encoding/write failure explicitly before publishing successful output quality. Add a regression with non-ASCII directories and validate that each expected output actually exists and decodes.

### R2 — P1: Projected board exclusion removes the complete T0 plant silhouette

Primary location: `tomato3d/mask/silhouette.py:263-266`.
Related quality path: `tomato3d/cli/run_stage1.py:185-195` and `tomato3d/io/quality.py::build_quality_record`.

The expression `candidate = prism & ~board & ~block` removes the entire projected board rectangle. A plant above the board can project inside that rectangle; the 2D rectangle does not identify which pixels belong to the physical board plane.

Using the existing synthetic session, T0 contains **60,077 green foreground pixels**. Its exported mask has **0 nonzero pixels** and retains **0 plant pixels**. All nine poses solve, side-view silhouette CV is 0, and the session is nevertheless marked `usable_for_training: true`. The current end-to-end test checks that the T0 mask file exists, not that the plant survives in it.

Impact: the operational top view can supply an empty plant label to later reconstruction or two-view training even when Stage 1 declares success.

Requested correction: the pipeline/design owner must reconcile board-plane rejection with preservation of foreground above the board, including T0. Until that is supported, explicitly reject unsupported/empty plant masks and prevent a successful training gate. Add a test that measures retained T0 foreground, not merely file existence. The numerical side-view CV threshold does not need to be changed to detect this failure.

### R3 — P1: Image size is not checked against the loaded calibration

Location: `tomato3d/cli/run_stage1.py:123-125` (after loading the image, before detection/PnP).

Stage 1 verifies the camera ID but never compares the image dimensions with `Intrinsics.image_shape`. A resized image can therefore be accepted with the unscaled original camera matrix.

The review passed an overhead image through the actual `_process_frame` path using 1600x1200 calibration:

| Input image | True camera height | Estimated camera height in board coordinates | Reprojection error | Pose status |
|---|---:|---:|---:|---|
| 1600x1200 | 550 mm | 550.589 mm | 0.1563 px | solved |
| 800x600, resized from the same image | 550 mm | 1100.932 mm | 0.0649 px | solved |

The wrong pose has a smaller residual and is below the configured 1 px limit. Reprojection quality cannot substitute for the missing calibration-size check.

Requested correction: reject incompatible image dimensions before pose estimation and record an explicit reason. Only support resizing/cropping if the transformation of the calibration is deliberate and validated. Add a regression through the frame/CLI path with the same camera ID and different resolution.

### R4 — P2: Reruns retain masks that the current run intentionally did not produce

Location: `tomato3d/cli/run_stage1.py:268-273`.

The output loop writes present masks but never invalidates old ones. First run the synthetic session with the test-only measured block height; then rerun the same session with the real `scale_block_nominal_height_mm: null` config. The second run correctly reports `silhouette_area_cv: unavailable` and `usable_for_training: false`, but **all nine previous PNGs remain byte-for-byte unchanged** beside the new pose and quality files.

This contradicts the observable output-state expectation that a blocked run has no usable current masks. A consumer listing `masks/`, or a human inspecting it, sees stale products with no run identity. The same conditional-write pattern also applies when a previously successful frame later fails.

Requested correction: publish a coherent set of artifacts for one completed run, or explicitly invalidate masks absent from that run. Limit any cleanup to pipeline-owned outputs. Add a same-session rerun regression, including a newly failed frame or missing block height.

## Evidence and reproduction

Run from the project root:

```powershell
python -X utf8 build/stage1_review_2026-09-16/reproduce.py
```

Evidence files:

- `build/stage1_review_2026-09-16/observations.json`: measured outcomes and source SHA-256 hashes.
- `build/stage1_review_2026-09-16/reproduction.log`: captured probe output.
- The `scratch` value in the observations points to the generated session, original synthetic images, masks, and separate quality snapshots for each case. Re-running creates another scratch directory and replaces the observations file.

Isolation details:

1. The first pipeline run uses unmodified image reading/writing and demonstrates R1.
2. The next run replaces only image reading inside the review process and exposes failed mask writes.
3. For R2 and R4, both image IO calls are temporarily replaced with byte-based equivalents **only in the review process**, so the path failure cannot hide later defects.
4. R3 uses `_process_frame` with the same temporary reader replacement and disables masking to isolate pose behavior.
5. The 30 mm block height exists only in the synthetic scratch BoardSpec and synthetic manifest. The real unmeasured block remains null.

These are reproducible synthetic integration findings, not measurements of a real tomato or physical calibration accuracy.

## Existing, intentional limitations

The real block height is still unmeasured/null, so fresh runs intentionally skip silhouettes and fail the active silhouette quality gate. This is not itself a new defect. Physical print verification and chart exclusion remain open as already recorded by Claude Code. The four findings above are additional to those known limitations.

## Suggested owner follow-up

Claude Code: fix R1, R3, and R4 in the owned pipeline and add regressions. Resolve R2's segmentation behavior with the design owner and ensure the quality gate cannot accept empty required plant labels. Keep physical measurements and operational configuration under human ownership. Codex can re-review the resulting implementation without changing Claude Code's files.
