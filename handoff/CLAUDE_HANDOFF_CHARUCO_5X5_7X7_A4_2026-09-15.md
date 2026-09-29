# Claude Handoff — 5x5 and 7x7 ChArUco A4 Boards

Date: 2026-09-15
Status: Both print artifacts created and digitally verified. Physical printing and operational board selection remain pending.

## 1. User Request and Working Scope

The user requested two printable versions, **7x7 and 5x5**, using the existing `charuco_board_6x7_30mm_A4.pdf` as the visual reference. Both must fit on A4. The latest request is to document the result for Claude.

Both boards use the same **190 x 190 mm outer dimensions**, with 10 mm left/right margins on A4 portrait. The cell size changes with the grid count. The user has not selected one variant as the operational default.

All further work on this task must stay inside:

`C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis/`

Paths below are relative to this directory. This handoff records completed work and integration requirements; it does not claim that the pipeline configuration has been updated.

## 2. Exact Board Specifications

| Property | 5x5 version | 7x7 version |
| --- | --- | --- |
| Paper | A4 portrait, 210 x 297 mm | A4 portrait, 210 x 297 mm |
| Board width x height | 190 x 190 mm | 190 x 190 mm |
| Board placement on page | 10 mm from left, 20 mm from top | 10 mm from left, 20 mm from top |
| Squares | 5 x 5 | 7 x 7 |
| Square size | 38 mm | 190/7 mm = 27.142857142857142 mm |
| Marker size | 27.866666666666667 mm | 19.904761904761905 mm |
| Marker/square ratio | 22/30 | 22/30 |
| Dictionary | `DICT_4X4_50` | `DICT_4X4_50` |
| Legacy pattern | `false` | `false` |
| Marker IDs | 0 through 11 | 0 through 23 |
| Expected markers | 12 | 24 |
| Expected ChArUco corners | 16 | 36 |

Use the exact JSON values in calculations. Do not substitute the rounded labels shown on the printed sheet.

The marker/square ratio follows the supplied reference, which used 22 mm markers inside 30 mm cells. The new boards do **not** retain 30 mm cells.

## 3. Delivered Files

| Artifact | 5x5 | 7x7 |
| --- | --- | --- |
| Print PDF | `build/charuco_board_5x5_190mm_A4.pdf` | `build/charuco_board_7x7_190mm_A4.pdf` |
| Board-only PNG | `build/charuco_board_5x5_190mm.png` | `build/charuco_board_7x7_190mm.png` |
| Exact pattern specification | `build/charuco_board_5x5_190mm_spec.json` | `build/charuco_board_7x7_190mm_spec.json` |
| Digital validation report | `build/charuco_board_5x5_190mm_validation.json` | `build/charuco_board_7x7_190mm_validation.json` |

Generator: `tools/make_square_board.py`.

The PDFs preserve the reference's layout conventions:

- White human-readable cell codes on black, marker-free squares.
- Column numbers and row letters outside the board.
- A 100 mm ruler with tick marks below the board.
- Board dimensions, marker dimensions, dictionary, detection counts, and printing instructions in the footer.

Cell codes such as `A1` are human location labels, not ArUco marker IDs. Marker-bearing squares are never overwritten with text.

## 4. Verification Actually Performed

OpenCV version: **4.13.0**. The generator checks the original board and the labelled board, creates the PDF, rasterizes the final PDF at **300 dpi** with Poppler, and runs detection again.

| Check | 5x5 result | 7x7 result |
| --- | --- | --- |
| Generated image: markers | 12/12 | 24/24 |
| Generated image: ChArUco corners | 16/16 | 36/36 |
| Maximum corner displacement caused by cell codes | 0.0000 px | 0.0000 px |
| Rasterized PDF: markers | 12/12 | 24/24 |
| Rasterized PDF: ChArUco corners | 16/16 | 36/36 |
| Board extent measured in the 300 dpi raster | 190.0767 x 190.0767 mm | 190.0767 x 190.0767 mm |
| Cell size inferred from raster width | 38.0153 mm | 27.1538 mm |

The PDF places the board at exactly 190 x 190 mm. Raster extent measurements are pixel-based; their approximately 0.077 mm difference is not a revised board specification. The generator checks each board dimension within 0.2 mm of the nominal extent.

Both final page previews were visually inspected for clipping, label placement, and readability. The generator's `--help` command was also checked.

**Limits:** These results verify the generated artifacts and the frontal digital detection case. They do not establish physical print accuracy, camera pose accuracy, performance under plant occlusion, or which variant is better for the actual rig. `physical_print_verified` remains `false` for both variants. This delivery is not completion of all T1 acceptance conditions or the remaining support tools.

## 5. Printing Instructions

1. Select A4 portrait.
2. Print at **100% / Actual Size**; disable Fit to Page and any automatic enlargement.
3. Measure the 100 mm ruler on the actual print.
4. Check a cell against its nominal size: 38 mm for 5x5, or 190/7 mm for 7x7.
5. Mount the print flat on a rigid board using matte paper, without bubbles or wrinkles.

Record physical measurements separately from the digital validation results. Do not report the paper as verified until it has been measured.

## 6. Pipeline Integration Requirements for Claude

At handoff time, `config/board_spec.json` still specifies **6x6, 45 mm cells, 34 mm markers, and a 270 x 270 mm board**. It matches neither of these new PDFs. That file was not modified during artifact creation.

Before processing images of either new board:

1. Associate each capture session with the board variant actually used. Do not mix the two board models or infer the variant solely from marker IDs: IDs overlap between variants.
2. Synchronize square counts, exact square and marker sizes, dictionary, legacy-pattern setting, marker IDs, and board dimensions with the selected print's specification.
3. Treat the new `*_spec.json` files as **pattern specifications**, not complete replacements for the pipeline's `BoardSpec`. They omit rig-specific fields such as pot and scale-block placement, and contain additional artifact metadata. Integrate through the pipeline owner's schema rather than copying them blindly over the active config.
4. Recheck the coordinate convention and physical positions of the pot, reference block, and color chart for the 190 mm board. Do not automatically carry over locations from the 270 mm board or assume that cell labels define the pipeline origin.
5. Update the relevant capture documentation and manifest references once the operational choice is established. Preserve both print options and their provenance.

No automatic crop-pack changes, agronomic decisions, camera-setting changes, or shared pipeline edits were made as part of this delivery.

## 7. Reproduction

The generator supports `--squares 5` and `--squares 7`; both produce a 190 mm board on A4. Run from the working directory stated in section 1:

```powershell
python tools/make_square_board.py --squares 5 --pdf-python '<Python with ReportLab>' --pdftoppm '<Poppler pdftoppm executable>'
python tools/make_square_board.py --squares 7 --pdf-python '<Python with ReportLab>' --pdftoppm '<Poppler pdftoppm executable>'
```

The launching Python environment needs OpenCV and NumPy. `--pdf-python` selects the interpreter with ReportLab. Optional `--build-dir` changes the output directory; keep it inside this task's working folder.

The generator writes the PDF, PNG, pattern JSON, validation JSON, and QA raster/preview files. It does not modify `config/board_spec.json`. The original 6x7 reference PDF remains available.

## 8. Completion and Remaining Work

- Completed: both A4 PDFs, exact pattern metadata, digital detection checks, visual inspection, and this handoff.
- Pending: physical print measurements, real-camera comparison, operational board choice, and matching pipeline configuration/documentation.
- No claim is made that either grid is the better operational choice before real capture evaluation.
