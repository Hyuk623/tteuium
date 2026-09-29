# Stage 1 review response

Date: 2026-09-16
Author: Claude Code
Responds to: `handoff/CODEX_STAGE1_REVIEW_2026-09-16.md` (R1–R4)
Result: R1, R3, R4 fixed. R2 fixed as a fail-closed interim; its design question stays open.
Suite: **116 passed** (was 95). Every new regression was mutation-checked: reverting its fix
in-process makes it fail (`build/mutation_check_stage1.py`, log beside it).

> **Why this is a separate file.** `handoff/LOG.md` was rewritten twice today (18:48 and
> 18:55) from a copy that predates entries appended in between, and both Claude Code entries
> were lost. This file records the work so it survives that. Whichever session rewrites
> LOG.md: please append instead of replacing the file (CONVENTIONS §5).

## All four findings reproduced before fixing

| | Verified how | Result |
|---|---|---|
| R1 | `cv2.imwrite` / `cv2.imread` on a temp dir named in Korean | `imwrite` returns `False`, writes nothing; `imread` returns `None`; `np.fromfile`+`imdecode` works |
| R2 | Straight-down synthetic render through `segment_plant_silhouette` | plant retained fraction < 0.05 (Codex: 0 of 60,077) |
| R3 | 1600x1200 intrinsics, same frame resized to 800x600 | still `solved`, camera distance 1413 mm instead of 713 mm |
| R4 | Code read: masks written conditionally, never removed | confirmed |

Why the suite missed R1: pytest's `tmp_path` is an ASCII path. The real project path is not.

## R1 — Unicode image IO: fixed

- New `tomato3d/io/images.py`: `read_image` (numpy bytes + `cv2.imdecode`, returns `None` on
  missing/undecodable) and `write_image` (`cv2.imencode` + `tofile`, raises `ImageIOError` on
  encode or write failure — never silent).
- Used by `tomato3d/cli/run_stage1.py` (inputs, masks) and `tomato3d/calib/intrinsics.py`.
  No `cv2.imread`/`cv2.imwrite` remains in `tomato3d/`.
- A mask write failure is a hard failure (exit 2) raised **before** anything is published.
- Tests: the whole CLI suite now runs under a data root named `데이터_한글 경로`; a regression
  asserts every published mask exists and decodes; `tests/test_images.py` covers round trips,
  unreadable inputs, unwritable targets, and pins the OpenCV defect itself (Windows only).

## R3 — image size vs calibration: fixed

- `_process_frame` compares the decoded size with `Intrinsics.image_shape` before detection.
  A mismatch records a failed pose (numeric columns `unavailable`) and the validity code
  `image_size_mismatch_with_intrinsics`, which gates the session.
- Undecodable inputs likewise record `unreadable_image`.
- Regression: same camera id, one frame resized to 800x600 → that frame fails, the other
  eight solve, the session is gated. Confirmed load-bearing: without the check the frame
  solves with a 2.26 px residual, which averages below the 1 px session threshold.

## R4 — stale outputs on rerun: fixed

- `_publish_outputs` stages `poses.csv`, `masks/` and `quality.json`, then swaps them in.
  `quality.json` is removed first and restored last, so a present `quality.json` always
  describes the files beside it. A failure while staging leaves the previous run untouched.
- Only those three artifacts are replaced; any other file in the derived folder is kept.
- Regressions: measured-config run then null-height rerun leaves no mask; a frame that newly
  fails loses its old mask; a simulated write failure exits 2 with the previous outputs
  byte-identical; a later-stage file survives a rerun; no staging folder is left behind.

## R2 — empty top silhouette: fail-closed interim, design question OPEN

Implemented:

- `tomato3d/mask/silhouette.py::SUPPORTED_VIEW_TYPES = ("side",)`. Top views get no mask.
  The reason is documented beside the constant and pinned by a test that *measures* the
  loss on a top view, so improving segmentation forces a deliberate re-enable.
- An empty side silhouette is not published.
- New validity codes in `tomato3d/io/quality.py` (not thresholds: never configurable, never
  skipped when thresholds are null): `operational_top_view_silhouette_unavailable`,
  `side_view_silhouette_unavailable`, `image_size_mismatch_with_intrinsics`,
  `unreadable_image`. Any one makes `usable_for_training` false.
- Regressions check content, not existence: each side mask keeps > 50 % of its plant pixels;
  T0 publishes no mask and gates the session.

**Consequence: no session is training-usable until R2 is resolved in design.** T0 is the
operational top view and now always lacks a silhouette.

**Open question for the design owner:** Stage 1 rejects the board by its 2D projection,
which cannot tell board-surface pixels from foreground standing above the board inside the
same quad. Options, none implemented:

1. Compare against the known board pattern. With the solved pose, render the ChArUco
   texture into the frame; pixels that disagree occlude the board. Geometric in origin, uses
   no colour rule for the board, but needs a tolerance for print gamma, blur and lighting —
   a new configured value.
2. Classify plant by greenness inside the board quad too. Simplest, but arguably
   "rejecting the board by colour" under hard constraint 3; needs an explicit ruling.
3. Leave top-view silhouettes to Stage 2 (multi-view consistency), and decide whether T0
   is then required for `usable_for_training` at Stage 1.

Also needed: whether the T0 silhouette is truly *required* at Stage 1. The gate currently
assumes yes (fail closed); relaxing it is a one-line change in `_validity_failures`.

## Restored record: BoardSpec fix (lost from LOG.md)

Executed `handoff/CLAUDE_CODE_FIX_BOARDSPEC_2026-09-16.md`; `config/board_spec.json` untouched
and validates. BoardSpec gains the 13 typed fields with `extra="forbid"` kept; `_` note keys
kept as never-read `human_notes` and flattened back on dump; marker/corner count and id
cross-checks; nullable `scale_block_nominal_height_mm`; optional `scale_block_footprint_mm`.
`build_charuco_board` sets the legacy flag **and** `marker_ids` explicitly.
`SessionManifest.board_variant_id` is required; `run_stage1` exits 2 naming both ids before
writing output. `scale_reference_block_mm` made nullable (a required float forced an invented
number while the block is unmeasured).

Spec correction, verified on OpenCV 4.13: `legacy_pattern` changes the layout only when
`squares_y` is even. 7x7, 5x5 and 6x7 render identically either way, so the requested
"layouts differ" test runs on an even-row derivation of the real spec, plus a test pinning
the 7x7 no-op.

Still open for the human: null block height means no silhouettes at all; the colour chart
beside the board is not excluded; the meaning of `board_center_mm` is unstated; the
`.gitignore` required by CONVENTIONS §7 is missing (root file, outside Claude Code's column).

## Files changed

`tomato3d/io/images.py` (new), `tomato3d/io/quality.py`, `tomato3d/io/manifest.py`,
`tomato3d/mask/silhouette.py`, `tomato3d/calib/intrinsics.py`, `tomato3d/cli/run_stage1.py`,
`tests/conftest.py`, `tests/test_cli_stage1.py`, `tests/test_images.py` (new),
`tests/test_schemas.py`, `tests/test_mask_geometry.py`, `README.md`, `handoff/TODO.md`,
`build/mutation_check_stage1.py` + `.log` (evidence).
