# Claude Code Fix — BoardSpec schema and legacy pattern

Date: 2026-09-16
Priority: **blocking** — `config/board_spec.json` currently fails validation, so nothing runs.
Scope: `tomato3d/io/schemas.py`, `tomato3d/calib/board.py`, `tomato3d/cli/run_stage1.py`, `tests/`.

Paste everything between the markers into Claude Code.

--- BEGIN PROMPT ---

`config/board_spec.json` was rewritten for the newly confirmed operational board
(`charuco_7x7_190mm`) and it no longer validates against `BoardSpec`. Fix the schema and two
related correctness issues. Do not edit `config/board_spec.json` — it is the human's file and the
values in it are correct; the schema is what is behind.

## 1. `BoardSpec` rejects the new config — two separate failures

**(a) Unknown keys.** `_StrictModel` forbids extras. The config now carries 17 additional keys:

```
variant_id, legacy_pattern, marker_ids, expected_marker_count, expected_inner_corner_count,
position_frame, print_page_size, print_pdf_ref, pattern_spec_ref, board_center_mm,
scale_block_cell_code, color_chart_on_board, physical_print_verified,
_position_frame_note, _scale_block_note, _color_chart_note, _spare_variant_note
```

Add them as typed fields. Keep `extra="forbid"` — do not loosen it to `allow`; the point of the
strict model is that a typo in a config is an error, and that is still what we want.

| field | type | notes |
|---|---|---|
| `variant_id` | `str` | identifies the printed board; see §3 |
| `legacy_pattern` | `bool` | see §2 |
| `marker_ids` | `list[int]` | IDs present on the print |
| `expected_marker_count` | `int` | cross-check, see below |
| `expected_inner_corner_count` | `int` | cross-check, see below |
| `position_frame` | `Literal["sheet"]` | every `*_position_mm`/`*_center_mm` in this file is sheet-frame |
| `print_page_size` | `str` | e.g. `"A4"` |
| `print_pdf_ref` | `str` | repo-relative path |
| `pattern_spec_ref` | `str` | repo-relative path |
| `board_center_mm` | `tuple[float, float]` | sheet frame |
| `scale_block_cell_code` | `str` | human cell label, e.g. `"A1"` |
| `color_chart_on_board` | `bool` | false means the chart is beside the board, not on it |
| `physical_print_verified` | `bool` | stays false until a printed sheet is measured |

The four `_`-prefixed keys are human notes. Accept them without modelling each one: allow any key
matching `^_` as a free-text `str`. Do not let a note key ever affect behaviour.

Add a validator: `expected_marker_count` must equal `(squares_x * squares_y) // 2`,
`expected_inner_corner_count` must equal `(squares_x - 1) * (squares_y - 1)`, and `len(marker_ids)`
must equal `expected_marker_count`. These are cheap and catch a hand-edited config immediately.

**(b) `scale_block_nominal_height_mm` is `null` and the field is `Field(gt=0.0)`.**

Change it to `float | None`, still `gt=0.0` when present. The block has not been measured yet, and
the project rule is that a value which is not yet known is null and inactive — never a placeholder
number. `scale_block_box_board_mm` must raise a clear error naming the field when it is called with
a null height, rather than producing a degenerate box.

While you are there: the docstring for `scale_block_box_board_mm` says the block's footprint is one
board square. On the 7x7 board a square is 27.14 mm, and the physical block may be wider than that,
so the exclusion box can be too small and block pixels leak into the plant silhouette. Add an
optional `scale_block_footprint_mm: float | None = None` to `BoardSpec`, default to
`square_size_mm` when null, and use it for the footprint. Note it in the docstring.

## 2. `legacy_pattern` is not applied — silent wrong-ID risk

`tools/make_square_board.py` calls `board.setLegacyPattern(False)` explicitly when generating the
printed board. `tomato3d/calib/board.py::build_charuco_board` never calls `setLegacyPattern` at all
and relies on the OpenCV default.

They agree today only by coincidence of the installed OpenCV version. If they ever diverge, markers
are still detected but are matched to **different object points**, so the pose is wrong while every
count and every quality metric looks healthy. That is the worst failure mode in this pipeline.

Call `board.setLegacyPattern(spec.legacy_pattern)` explicitly in `build_charuco_board`, right after
constructing the board. Never rely on the default.

Add a test that builds the board both ways and asserts the two patterns produce different marker
layouts, so the flag is proven to matter and cannot be silently dropped later.

## 3. `board_variant_id` must be enforced, not just recorded

Several printed board variants exist — `charuco_7x7_190mm` (operational) and
`charuco_5x5_190mm` (spare) — and **their marker IDs overlap**. A session's board can never be
inferred from detected IDs.

- `SessionManifest` gains a required `board_variant_id: str`.
- `run_stage1` compares it with `BoardSpec.variant_id` and **exits non-zero with a clear message on
  a mismatch**, before doing any work. Processing a 5x5 session with the 7x7 spec gives a 40% scale
  error in every dimension and nothing downstream detects it.
- Test: a manifest with a mismatched `board_variant_id` causes a non-zero exit naming both values.

## 4. Done when

- `pytest` passes.
- `python -c "from tomato3d.io.tables import *"` — sorry, instead: loading the real
  `config/board_spec.json` through `BoardSpec` succeeds, and a test asserts that (do not use a
  fixture copy; load the actual file, so the config and the schema can never drift apart again).
- A test asserts `build_charuco_board` sets the legacy flag from the spec.
- A test asserts the `board_variant_id` mismatch guard.

Append what you changed to `handoff/LOG.md`.

--- END PROMPT ---
