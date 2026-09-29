# Brief: importing the 2026-09-20 organized captures for 3D work — Claude Code

Documentation-first brief (per `AGENTS.md`) for the user instruction "3D 모델링 진행" after
`handoff/CLAUDE_PHOTO_ORGANIZATION_REVIEW_2026-09-20.md`. Written before implementation; outcomes are
appended at the end. Nothing here authorizes training, inference or PPFD simulation.

## 1. Request

Make the two new plants (`dwt_01`, `dwt_02`, 18 views each) usable for the existing 3D workflow:
decode, verify, recover measured ChArUco poses, and hand over a labelling session per plant. The new
photographs stay read-only; no old calibration, label or session may be attached by filename order.

## 2. Inspected state (read-only checks run today)

- **Decoding**: the files are true HEIC (`ftypheic`). `pillow-heif` is NOT installed in the active
  interpreter, and OpenCV/PIL cannot read them; no `ffmpeg`/ImageMagick/`heif-convert` exists on PATH.
  The project's vendored runtime `build/leaf_light_image_runtime/` (pillow-heif 1.7.0 + libheif)
  decodes them, and `tools/leaf_light/phone.py::read_phone_image` already uses `pillow_heif` when
  importable. So decoding works only when that runtime is on `sys.path`; nothing was installed.
- **Camera**: every sampled photo is 3024 x 3024, EXIF orientation 1, `Apple iPhone 16`,
  `iPhone 16 back camera 5.96mm f/1.6`. The trial intrinsics
  `build/photo_audit_board_20260919/intrinsics.board_only.trial.json` has `camera_id`
  `photos1_phone_596mm_square`, the same 3024 x 3024 size, RMS 9.0644 px over 41 images. Same camera
  family and geometry, but this calibration was never accepted (0/18 old poses passed the 1 px gate).
- **Board variant**: the printed sheet is legible in the top views and reads
  "CHARUCO DICT_4X4_50 | 7 x 5 squares, 38 mm | board 266 x 190 mm | print at 100% | A4 LANDSCAPE",
  which matches `config/board_spec.json` (`charuco_7x5_266x190mm`). Max detected marker ID over all 36
  photos is 16, consistent with that variant. Note that reprojection error cannot distinguish 7x5 from
  7x7 (a uniform scale is absorbed by the pose), so the printed caption and the ID range are the
  evidence, not the fit.
- **Pose recoverability** (configured board + trial intrinsics, `build/new_capture_scan_20260920/scan.json`):
  **14 of 36** photos reach >= 6 ChArUco corners and solve, RMS 2.71-10.79 px.
  Per plant: `dwt_01` 6 solved (01, 03, 24, 25, 26, 28), `dwt_02` 8 solved (01, 03, 21, 24, 25, 26, 27, 28).
  **All 16 side views (11-18) fail**: 0-3 markers, 0-1 corners. The board is in frame but defocused and
  extremely foreshortened. Tuned detector parameters and CLAHE did not lift any failing view to 6
  corners, so this is a capture limitation, not a threshold to relax.
- **Growth records**: `dwt_02_260920.json` parses and is consistent. `dwt_01_260920.json` still fails
  strict JSON (leading zeros) on disk; the user's corrected values are recorded in the review handoff.
  This import does not read, repair or depend on those records.

## 3. Intended changes

1. New CLI `tools/import_organized_capture.py` (read-only inputs, writes only under `build/`):
   - resolve `filename_mapping.csv` rows against the outer date directory, refuse missing/duplicate
     rows and changed SHA-256;
   - verify HEIC signature, decode via the vendored runtime, apply EXIF orientation, write lossless
     PNG working copies and record source/output hashes, sizes and the orientation transform;
   - refuse when EXIF camera/lens differs across the set or from the intrinsics profile, or when the
     image size differs from the calibration;
   - detect the configured board, record per-photo marker/corner evidence, solve poses with the
     existing gate values (`min_pose_corners` 6, `max_pose_error_px` 1.0) and keep failures explicit;
   - emit `capture.json` in the existing `diagnostic-preview-capture-1` schema plus an import report
     and a Korean summary page.
2. Prepare one editor session per plant from that capture with an empty annotation context, so
   labelling can start with the existing editor/rebuild/surface workflow.

## 4. Execution restrictions

No model download, training, inference or PPFD. No writes outside `build/`. Originals, the mapping
CSV, growth JSONs, `config/`, `docs/`, existing sessions and results stay untouched. Thresholds and
calibration are unchanged; every output stays `validated_metric: false`. The 7x5 board variant is
recorded together with the evidence above and a flag that the user has not confirmed it in writing.

## 5. Validation plan

Deterministic tests with a synthetically rendered ChArUco board (no HEIC encoder required): mapping
path resolution against the date directory; rejection of a changed hash, a missing mapping row, a
duplicate row, a foreign camera profile and a wrong image size; pose solved/failed classification and
gate flags; original files unmodified (hash-checked); capture schema fields required by the existing
rebuild. Then an actual run on both plants, cross-checked against the read-only scan counts.

## 6. Outcomes (after implementation)

### Delivered

- `tools/import_organized_capture.py` (new CLI) and `tools/tests/test_import_organized_capture.py` (5 tests).
- `build/new_captures_20260920/dwt_01/` and `.../dwt_02/`: 18 decoded working PNGs each (3024 x 3024,
  EXIF orientation applied), `capture.json` (`diagnostic-preview-capture-1`), `import_table.csv`,
  `import_report.json`, Korean `index.html`, and a prepared `edit_session/` with an empty annotation
  context so labelling can start.
- Results match the independent read-only scan exactly: **dwt_01 6/18 and dwt_02 8/18 poses solved**,
  0 pass the 1 px gate, every side view (11-18) fails with its reason recorded.
- Posed-view geometry (board frame): cameras 247-391 mm above the board; pairwise parallax
  13-100 deg (dwt_01, 15/15 pairs >= 10 deg) and 5-108 deg (dwt_02, 27/28 pairs >= 10 deg). The
  posed subsets therefore have usable triangulation baselines despite the failing gate.

### Defect found and fixed during this work

The first implementation solved PnP against OpenCV's **sheet**-frame object points, while the whole
pipeline stores **board**-frame poses (`CONVENTIONS` section 6). The stored poses reprojected
board-frame corners with 1 300-47 000 px residuals versus 3-7 px for the existing session. Fixed by
solving against `sheet_to_board_mm(...)`, added `coordinate_frame` to the capture, added a regression
asserting the evidence residual stays below 1 px on a synthetic board (mutation-checked: reverting to
the sheet frame fails the test), and re-ran both imports and both prepared sessions. Board-frame
evidence residuals are now 3.6-8.6 px (dwt_01) and 2.7-10.8 px (dwt_02), matching the direct solve.

### Validation executed

- `python -m pytest tools/tests -q`: **171 passed, 1 skipped** (164 before this task).
- Byte-identical reproducibility: re-running the import produced identical frames, evidence and PNG
  hashes; the temporary copy was deleted.
- All 36 source photographs re-hashed against the mapping CSV after the run: unchanged. Growth JSONs
  untouched. 645 previously tracked files: one change, `docs/파일럿_촬영_프로토콜_2026-09-15.md`
  (18:09), which was **not** written by this work; `docs/` is the human's column and was left alone.

### Open items

1. **Board variant**: the printed caption in the top views reads 7 x 5 squares / 38 mm / 266 x 190 mm,
   matching `config/board_spec.json`, and the maximum detected marker ID over 36 photos is 16. The
   capture records `board_variant_evidence.confirmed_by_user: false`; a written confirmation would
   close it. A 7 x 7 print would scale every length by 27.14/38.
2. **Intrinsics** are the earlier unvalidated trial calibration (RMS 9.06 px) reused because EXIF and
   size match; `same_camera_confirmed_by_user: false`. No pose passes the 1 px gate, so all geometry
   stays diagnostic.
3. **Side views** cannot be posed from these captures. A re-shoot with the board sharp and fully in
   frame at side angles is the only fix; no threshold was relaxed.
4. **No 3D surface exists yet** for either plant: there are no labels. The next step is labelling in
   the prepared sessions, then the existing rebuild and surface attachment flow.
5. `dwt_01_260920.json` still fails strict JSON on disk; this import neither reads nor repairs it.

## 7. Review corrections applied (2026-09-20, after CODEX_NEW_CAPTURE_IMPORT_REVIEW)

Codex's review found three real defects in this importer. Two were overclaims of mine; all are fixed,
each with a regression that fails when the fix is reverted (mutation-checked).

- **R1 calibration compatibility.** `camera_profile()` compared nothing but image dimensions while its
  note claimed EXIF agreement with the calibration. Now: the photographs' camera/lens/focal/zoom are
  compared against a profile the calibration file actually declares (`camera_profile` block or EXIF
  fields) and/or an explicit `--expect-camera-model` / `--expect-lens-model` /
  `--expect-focal-length-mm` contract; a mismatch refuses the import before anything is written. With
  neither available, the capture records
  `calibration_compatibility: unverified_no_camera_profile_available` and states that equal dimensions
  are not compatibility. One-lens operation is recorded as a user statement, not a measurement.
  My earlier brief claimed foreign-profile rejection; that claim was wrong until this fix.
  The delivered captures now carry `verified_against_explicit_contract` for
  `exif_model` = `iPhone 16` and `exif_lens_model` = `iPhone 16 back camera 5.96mm f/1.6`
  (the first attempt with `Apple iPhone 16` was correctly refused: EXIF make and model are separate).
- **R3 board evidence provenance.** The hardcoded "observed caption" string is gone. Evidence now
  holds only measured, session-specific facts (configured variant and square size, configured ID
  range, max/count of detected marker IDs, any IDs beyond the configured board, and the note that
  reprojection cannot distinguish scale). A printed caption is recorded only when supplied with
  `--board-caption` plus its source and reader; otherwise it stays `null`. Both sessions were
  re-imported with a caption sourced to that session's **own** top view (dwt_01 left sheet edge of
  `dwt_01_20260920_03`; dwt_02 `..._03`). `confirmed_by_user` is still false.
- **R4 inactive null threshold.** `float(None)` no longer crashes. A null gate is loaded and left
  inactive: `max_pose_error_px: null`, `pose_gate_active: false`, `passes_pose_gate: null` per frame
  (an inactive gate cannot pass or fail) and `accepted_pose_count: null` rather than a misleading 0.
  A null `min_charuco_corners_for_pose` falls back to the algorithmic PnP minimum of 4 with that
  substitution recorded. The configured 1.0 px value is unchanged and still active.
- R2 (date mixing) was not implemented: the user handles date isolation operationally.

Re-verified after the fixes: tools suite **175 passed, 1 skipped**; both plants re-imported (dwt_01
6/18, dwt_02 8/18 solved, 0 accepted) and both editor sessions regenerated from the new captures;
all 36 source photographs re-hashed unchanged.
