# Codex Task List — Tomato 3D Phenotyping, Support Tooling

- Date: 2026-09-15
- Owner split: **Claude Code owns `tomato3d/` (pipeline core). Codex owns `tools/` (support tooling).**
- Related: `handoff/TOMATO_3D_PHENOTYPING_ALGORITHM_SKELETON_2026-09-15.md`,
  `handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md`,
  `docs/파일럿_촬영_프로토콜_2026-09-15.md`

---

## 0. Ground rules

**Do not create, edit or delete anything under `tomato3d/`, `tests/` or `config/`.**
Those are owned by another agent. If a task appears to need a change there, stop and report it
instead of making the change.

- Everything you write lives under `tools/`, plus its own tests under `tools/tests/`.
- Read configuration from `config/board_spec.json`, `config/capture_config.json` and
  `config/quality_thresholds.json`. Never hardcode a value that exists in those files, and never
  write to them.
- Tabular data is CSV. Configuration and metadata are JSON. No other formats.
- Every length variable carries its unit in the name (`square_size_mm`, `height_mm`). Angles are
  `_deg` or `_rad`. No bare `size`, `height`, `angle`.
- Python 3.11+, type hints everywhere, `pathlib.Path` for paths.
- A value that cannot be determined is written as `unavailable`, never `0` and never an imputed
  number.
- Each tool is a standalone CLI module runnable as `python -m tools.<name>` with `--help`.

Coordinate frame used everywhere: origin at the board's origin inner corner, `+X`/`+Y` along the
board rows/columns, `+Z` up away from the board surface, all lengths in millimetres.

### 0.1 Path map — the single authority for where anything lives

All paths are relative to the repository root. `<plant_id>` e.g. `DT-001`,
`<session_id>` e.g. `DT-001_20260915_0900`.

```
tomato3d/                                   Claude Code owns      DO NOT TOUCH
tests/                                      Claude Code owns      DO NOT TOUCH
config/                                     Claude Code owns      read-only for Codex
  board_spec.json
  capture_config.json
  quality_thresholds.json

tools/                                      Codex owns
  make_square_board.py                      T1  (shipped; board variants in build/)
  charuco_render.py                         T2  CANCELLED - do not create
  charuco_render.py                         T2
  make_session.py                           T3
  records.py                                T4
  mask_contact_sheet.py                     T5
  pilot_sweep.py                            T6
  tests/                                    Codex owns

build/                                      generated, gitignored, either agent may write
  charuco_board_<squares_x>x<squares_y>_<square_size_mm>mm_<page>.pdf   T1
  charuco_board_<...>.png                                              T1, optional
  <session_id>_masks.png                                          T5
  pilot_report.csv                                                T6
  pilot_sweep.png                                                 T6

data/
  raw/<plant_id>/<session_id>/
    images/side_000.jpg ... side_035.jpg
    images/top_T0.jpg ... top_T4.jpg
    session_manifest.json                                         T3 writes
  calib/
    intrinsics_shots/                       raw board-only shots for intrinsic calibration
    intrinsics_<camera_id>.json             pipeline writes
  records/<plant_id>/                       HUMAN-RECORDED, T4 init/validate only
    manual_events.csv
    manual_measurements.csv
    environment.csv
    organ_label_map.csv
  derived/<plant_id>/<session_id>/          pipeline writes, T5/T6 read
    poses.csv
    masks/side_000.png ...
    depth/side_000.npy ...
    pointcloud.ply
    organs.csv
    keypoints.csv
    connectivity.csv
    phenotypes.csv
    quality.json
  tracks/<plant_id>/tracks.csv              pipeline writes
  outputs/<plant_id>/<session_id>/          pipeline writes
    diagnoses.csv
    actions.csv
  knowledge/
    crop_pack_dwarf_tomato.json
```

Resolve `data/` from `TOMATO3D_DATA_ROOT` and `config/` from `TOMATO3D_CONFIG_DIR` — read both via
`tomato3d.config.get_settings()`. Do not hardcode `./data` or `./config`, and do not build these
paths by string concatenation at call sites.

`build/` may not exist on a fresh clone. Create it with `mkdir(parents=True, exist_ok=True)`
before writing, and add `build/` to `.gitignore` if it is not already there.

---

## T1 — ChArUco board print generator  **(highest priority: blocks all capture)**

`tools/make_square_board.py`

> Originally specified as `tools/make_board_pdf.py`. Codex shipped it as
> `tools/make_square_board.py`; that name is now the one to keep. Do not rename it.

No photograph can be taken until a dimensionally correct board exists. Do this first.

**Input:** `config/board_spec.json`
**Output:** a print-ready PDF, default
`build/charuco_board_<squares_x>x<squares_y>_<square_size_mm>mm_<page_size>.pdf`
(operational board: `build/charuco_board_7x7_190mm_A4.pdf`)

Requirements:

1. Render the ChArUco board at **exact physical scale** — `square_size_mm` on paper must measure
   `square_size_mm` with a ruler. Set the PDF page box in points (1 pt = 1/72 inch) and do the
   mm→pt conversion explicitly; do not rely on any viewer's page scaling.
2. Use `cv2.aruco.CharucoBoard` with the dictionary named in `aruco_dict` so the generated markers
   match exactly what the detector expects.
3. **Cell codes — read this whole item before implementing.** Write a cell code (`A1`…`G6`,
   row letter + column number) **only in squares that do not contain a marker**, drawn in white,
   **centred in the square**, at no more than 25% of the square size.
   - Decide which squares are free by sampling a pixel **just inside the square's corner**
     (about 6% in). **Never sample the square's centre** — a marker's centre bit can be black, so a
     centre test misclassifies marker squares as free and the label then destroys the marker. This
     exact mistake was made and caught during the reference build: it cost 1 marker and 1 corner.
   - Centred, not in the corner. The square's corners are precisely where ChArUco subpixel corner
     refinement happens; ink near a corner corrupts the measurement the whole pipeline rests on.
   - Verify after drawing: marker count, corner count and **every detected corner position** must be
     identical to the un-labelled board. Corner displacement must be exactly 0.0 px.
4. Print column numbers and row letters in the page margin outside the board, and a thin cut border
   drawn exactly on the board edge.
5. Print outside the board area, in the page margin: `square_size_mm`, `marker_size_mm`,
   `aruco_dict`, `squares_x`×`squares_y`, board size in mm, inner corner count, marker count, a
   "print at 100% / actual size" warning, and a 100 mm ruler bar with millimetre ticks labelled
   "100 mm" for a one-glance print-scale check.
6. `--page-size` option: **`A4` (default)** and `A3`. If the board does not fit the chosen page,
   fail with a message stating the required page width in mm — **do not silently scale down.**
7. `--dpi` option for an optional PNG export alongside the PDF, default 600.

**Status:** shipped. `build/charuco_board_5x5_190mm_A4.pdf` and `build/charuco_board_7x7_190mm_A4.pdf`
exist and passed the equivalent checks (recorded in their `*_validation.json`).
`build/charuco_board_6x7_30mm_A4.pdf` remains as the styling reference.

**Resolved 2026-09-15:** the human chose **`charuco_7x7_190mm`** as the operational board, and
`config/board_spec.json` now matches it. `build/charuco_board_5x5_190mm_A4.pdf` is a built spare;
`build/charuco_board_6x7_30mm_A4.pdf` remains only as a styling reference. Do not change
`config/board_spec.json` — see `CONVENTIONS.md` §2 and §6b.

The table below is the regression target for whichever board is chosen; the counts scale with the
grid. Still owed: `tools/tests/test_make_square_board.py` asserting it automatically.

| check | required |
|---|---|
| markers detected on the generated image | all expected for the grid (5x5 -> 12, 7x7 -> 24) |
| ChArUco corners detected | all expected (5x5 -> 16, 7x7 -> 36) |
| corner displacement caused by cell codes | exactly 0.0 px |
| board size measured on a 300 dpi raster of the PDF | nominal within 0.2 mm |
| square size back-computed from that raster | nominal within 0.05 mm |
| detection re-run on the rasterised PDF | same counts as the generated image |

Write `tools/tests/test_make_square_board.py` asserting every row of that table, rasterising the PDF
with `pdftoppm -r 300` (or `pypdfium2` if poppler is unavailable).

**Acceptance:** the table above passes, and a physical print on A4 at 100% / "actual size" measures
30 mm ± 0.5 mm per square with the 100 mm bar measuring 100 mm.

---

## T2 — Synthetic ChArUco renderer  ~~**CANCELLED 2026-09-15**~~

**Do not implement this. Do not create `tools/charuco_render.py`.**

Claude Code implemented the renderer as `tests/conftest.py::render_charuco_view` before this task
was picked up, and its pose tests pass against it. A second implementation under `tools/` would be
duplicate work and a second source of truth for the most safety-critical fixture in the repo.

Kept here as a record of the decision. Priority order below is updated accordingly.

---

## T3 — Session organiser and manifest generator

`tools/make_session.py`

Turns a folder of camera files into a valid session directory.

**Input:** a folder of images straight off the camera, plus
`--plant-id`, `--captured-at` (ISO8601 with offset), `--camera-id`
**Output:** `data/raw/<plant_id>/<session_id>/` containing `images/` and `session_manifest.json`

Requirements:

1. `session_id` = `<plant_id>_<YYYYMMDD>_<HHMM>` derived from `--captured-at`.
2. Sort source images by EXIF capture time (fall back to filename order, and say so in the run
   summary when it does).
3. Rename: the first `side_view_count_pilot` images become `side_000.jpg` … in rotation order;
   the remaining 5 become `top_T0.jpg` … `top_T4.jpg` in capture order. Counts come from
   `config/capture_config.json`.
4. Assign `nominal_angle_deg = index * side_view_step_deg` for side views, `null` for top views.
   These are recorded for bookkeeping only.
5. Write `session_manifest.json` with every field listed in the algorithm skeleton §3.1.
5b. **`board_variant_id` is mandatory.** Add a required `--board-variant` argument; do not default
   it. Several printed board variants exist and their marker IDs overlap, so the board cannot be
   inferred from the images. Validate it against `config/board_spec.json::variant_id` and **warn
   loudly** when they differ — the user may be shooting the spare board deliberately, but a silent
   mismatch produces wrong dimensions that nothing downstream catches.
6. **Copy, never move.** The originals stay untouched.
6b. Set `environment_log_ref` to `data/records/<plant_id>/environment.csv`. Warn (do not fail) when
   that file does not yet exist — T4 `init` creates it.
7. Validation, reported as errors before anything is written:
   - image count ≠ expected total
   - any image unreadable
   - EXIF focal length or ISO **varying across the set** (the protocol requires fully manual camera
     settings; variation means the camera was on auto and the session is compromised)
   - duplicate timestamps
8. `--dry-run` prints the planned renaming without touching disk.

**Acceptance:** a folder of 41 images produces a session directory that the pipeline's manifest
reader accepts. A folder with mixed ISO values is rejected with the differing values named.

---

## T4 — Record templates and validator

`tools/records.py`

The human-recorded tables from `docs/파일럿_촬영_프로토콜_2026-09-15.md` §3.

**Location:** `data/records/<plant_id>/` — one set of four files per plant, shared across all that
plant's sessions. They are *not* per-session, because `manual_events` and `environment` are
continuous records while sessions are discrete.

Subcommands:

- `init --plant-id <id>` — create `data/records/<plant_id>/` and the four CSVs with exact headers:
  `manual_events.csv`, `manual_measurements.csv`, `environment.csv`, `organ_label_map.csv`.
  Refuse to overwrite an existing non-empty file; report which ones already exist and exit 0.
- `validate --plant-id <id>` — check every row; report file, line number and the specific problem

The session manifest's `environment_log_ref` must point at `data/records/<plant_id>/environment.csv`.
T3 writes that reference; T4 is what guarantees the file is there and well-formed.

Validation rules:

| table | checks |
|---|---|
| all | header matches the spec exactly, including column order; timestamps are ISO8601 with offset |
| `manual_events` | `event_type` in the allowed set; `truss_index`/`node_index` are positive ints or blank; `count` ≥ 1 |
| `manual_measurements` | `trait` in the allowed set; `unit` matches the trait (`mm` or `count`); `method` in `{ruler, caliper, visual_count}`; `value` > 0 |
| `manual_measurements` | **warn** when a session has no `reference_block_height` row — scale error cannot be computed without it |
| `environment` | numeric ranges sane (`air_temp` −10…60 °C, `rh` 0…100 %, `solution_ph` 0…14, `solution_ec` ≥ 0, `ppfd` ≥ 0, `photoperiod` 0…24 h); `bottom_water_level` in `{full, low, refilled}` |
| `organ_label_map` | `match_status` in the allowed set; no `organ_label` mapped to two different `organ_id` within one session |

**Never modify a record file** — `validate` is read-only and reports only. These are the ground
truth; a tool that "fixes" them destroys the evaluation.

**Acceptance:** a deliberately corrupted CSV produces one clear message per problem, with line
numbers. A clean CSV exits 0 and prints a row count per table.

---

## T5 — Mask contact sheet

`tools/mask_contact_sheet.py`

Manual mask review is the cheapest real check available at this stage, and the automatic metric
(`silhouette_area_cv`) cannot catch an error that repeats identically across every view.

**Input:** a session's `data/derived/<plant_id>/<session_id>/`
**Output:** `build/<session_id>_masks.png` (or a multi-page PDF with `--pdf`)

Requirements:

1. One tile per view, in view order, labelled `side_000` … / `top_T0` …
2. Each tile: the original image with the mask edge drawn in a high-contrast colour, and the mask
   region tinted at ~35% opacity. The underlying image must stay readable — this is for spotting
   a clipped leaf, so a solid fill is useless.
3. Overlay on each tile: mask pixel area, and `pose_status` from `poses.csv`. Tiles whose pose
   failed get a clearly marked border.
4. A header strip with `session_id`, view count, `pose_solved_ratio`, `silhouette_area_cv`.
5. `--max-width` to cap output resolution, default 4000 px.

**Acceptance:** a 41-view session renders one readable sheet where a deliberately corrupted mask is
obvious at a glance.

---

## T6 — View-count sweep runner  *(after the pipeline's Stage 2 exists — do not start early)*

`tools/pilot_sweep.py`

This is the tool that decides the operational side-view count (decision D2).

**Input:** one or more sessions captured with 36 side views
**Output:** `build/pilot_report.csv`

Requirements:

1. For each session and each subset size in `--subsets 8,12,18,36`, select **evenly spaced** side
   views by `measured_angle_deg` from `poses.csv` — not by filename index, and never at random.
2. Run reconstruction on each subset via the pipeline's public entry point. Do not reimplement any
   reconstruction logic; if no suitable entry point exists, stop and report that instead.
3. For each run, record one row:
   `session_id, subset_size, view_indices, hull_volume_mm3, plant_height_mm, plant_height_error_mm,
   scale_block_height_mm, scale_block_error_mm, leaf_count_pipeline, leaf_count_manual,
   pose_solved_ratio, runtime_s`
4. Errors are computed against `manual_measurements.csv`. When a manual value is missing, write
   `unavailable` — do not skip the row and do not substitute a value.
5. `--plot` writes `build/pilot_sweep.png`: error and hull volume against subset size, one line per
   session, subset size on a log-2 axis.

**Acceptance:** runs end to end on pilot data and produces a report from which the error curve's
knee is readable.

---

## Priority order

1. ~~T1~~ — shipped as `tools/make_square_board.py`; 5x5 and 7x7 A4 variants built and digitally
   verified. **Remaining:** physical print measurement, and a `tools/tests/` test asserting the
   validation table. Operational board choice is the human's and is still open.
2. ~~T2~~ — **cancelled**, see above.
3. **T3**, **T4** — start here. Needed the day the first session is shot.
4. **T5** — needed to review that first session.
5. **T6** — only after pipeline Stage 2 lands.

Report back after each task with: files added, how to run it, and anything in this brief that
turned out to be wrong or underspecified. Do not fix a specification problem by guessing.
