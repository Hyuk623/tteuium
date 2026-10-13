# P1 rim inner plane — execution (2026-10-13)

Prompt: `handoff/CLAUDE_CODE_CLI_PROMPT_P1_RIM_INNER_PLANE_2026-10-13.md` (R1–R5). Korean: `_KO.md`.

## 0. Outcome in one paragraph
R1, R2, R4 and R5 are implemented and tested. Every mm scale now carries its reference line, plane and offset, and a
mm value with no stated plane is refused. R3 was run, and it does **not** confirm the prompt's premise. The 13
existing top-photo clicks lie on the **outer top edge, on the rim plane** (60 mm). They do not lie on the soil line.
Re-derived with the plane explicit, all 13 scales are **unchanged (0.0 %)**. The 3.6–5.2 % error the prompt warns
of would occur only if soil-line clicks were read as rim values, and no record contains such clicks. The soil line
in the top photos cannot replace the outer edge:
- leaves hide it (all four sides found in 1 of 13 photos);
- where it was found, it disagrees with the 10 mm geometry.

I therefore did **not** switch the top-photo primary to the medium plane. That choice stays with the user (§7, D1).

## 1. The finding that changes R3: which line the clicks are on
Evidence: close-ups `build/rim_inner_plane_20261013/top_clicks_closeup.jpg` and `side000_clicks_closeup.jpg`.

**Top photos.** The clicks sit on the outer silhouette of the translucent rim against the paper, within a few px. The
soil–wall junction is a separate line 45–60 px further in. Between the two lie the 0.5 mm lip and the inner wall face,
which is visible from above.

**Side photos (side_000), each side differs:**

| side | what is visible | line clicked | plane |
|---|---|---|---|
| front | The front wall's inner face points away from the camera, so the medium junction behind it is hidden. The sharp rim/soil line is the front **inner top edge** occluding the medium. Soil is visible *through* the translucent front wall from about 170 px lower, which matches 10 mm × cos(elevation). | `inner_top` | rim |
| left / right | outer silhouette against the background | `outer_top` | rim |
| back | top silhouette | `outer_top` | rim |

The soil–wall junction on the back and side walls is a separate, lower line, and nobody clicked it.

**Correction of my own 2026-10-12 wording.** I called the front line "inner edge (soil boundary)". That merged two
different lines: the inner top edge at the rim plane, and the junction 10 mm lower. The prompt read it as the
junction. The geometry is now explicit in code (`potscale` docstring, `rim_auto` docstring).

## 2. R1 — records
- `pot_spec.csv` gains six columns:
  - `pot_rim_inner_edge_mm` + `pot_rim_inner_edge_source_kind`;
  - `medium_surface_depth_below_rim_mm` + `medium_surface_depth_source_kind`;
  - `wall_taper` (`none` | blank) + `wall_taper_source_kind`.
- Rules for the new pot-spec values:
  - each value needs its source kind, and a source kind needs its value;
  - the inner edge must be smaller than the outer edge;
  - a tapered wall is refused because it is not implemented.
- `rim_points*.csv` gains `edge`: `outer_top` | `inner_top` | `medium_junction`. One side carries one line.
- New row kind `side_occluded`: a side number only.
- **Old files parse unchanged.**
  - An old pot spec reads with the inner edge, depth and taper unavailable.
  - An old rim-points file reads as `outer_top`, because that was its collection instruction. Its reference string
    is suffixed `edge_from_legacy_record_instruction`.
- Template `build/pot_records_template/` was regenerated:
  - `pot_spec.csv` has the user's values (60 / 59 / 10 / none, all `measured`);
  - README and `rim_points.csv` examples include `edge` and `side_occluded`.
- **The human still has to replace the `EXAMPLE_square_cell` row** in `data/records/pots/pot_spec.csv`. The new
  template row is the replacement. Nothing was written into `data/records/`.

## 3. R2 — the plane travels with every mm value
`potscale.reference_of`:
- maps each side's line to (half width, plane, offset): `outer_top` 30 mm at the rim; `inner_top` 29.5 mm at the rim;
  `medium_junction` 29.5 mm at −10 mm, which needs `wall_taper = none`;
- requires all four lines on one plane for the homography. Outer and inner may mix on the rim plane through per-side
  half widths.

Conventions: `pot_rim_outer_edge_square`, `pot_rim_edges_square` (mixed), `pot_medium_junction_square`.

Schema `p1_state_v1` **revision 7** (additive; the version string is unchanged for Codex):
- **`captures.csv`**
  - New columns: `scale_reference`, `scale_reference_plane` (`pot_rim` | `medium_surface` | `synthetic_camera`) and
    `scale_reference_plane_offset_mm`.
  - **A solved scale without plane or reference is refused.**
  - The plane must match the convention.
  - Offset rules: `pot_rim` offset = 0; `medium_surface` offset < 0; `synthetic_camera` has no offset.
  - A revision-5/6 header states its plane through `scale_plane` and is accepted.
  - A pre-T6 header with a real mm value is refused.
- **`frame_transforms.csv`**: gains the two plane columns. A solved row without a plane is refused
  (`check_frame_transforms`, also run in `collect`).
- **`areas.csv`**: `check_areas(..., plane_by_capture)` refuses an mm² value whose capture states no plane. Package
  build and `collect` use it. Codex's two-argument call still works.
- **`camera_poses.csv`**: gains `occluded_sides`. A three-edge pose may omit the self-check columns and can never be
  `validated`.
- `camera.analyse` solves on the reference plane and then moves the pose into the **rim frame**. Distance, tilt and
  vertical scale therefore always refer to the rim.

Tests: `tests/test_state_rim_plane.py`, 9 tests.

| case | expected result | outcome |
|---|---|---|
| outer, inner and mixed lines | true rim scale | to 1e-6 |
| medium-junction lines | true medium-plane scale | to 1e-6 |
| junction clicks recorded as the outer edge | error > 5 % | as expected (the prompt's warning made concrete) |
| lines on two planes, missing inner/depth record, taper, occluded side | unavailable, with the reason | as expected |
| unstated plane in captures, areas, frames, or a pre-T6 header | refused | as expected |
| three-edge solve | approximate; side named occluded; right pose with the right focal; >3 mm wrong with a 4 % wrong focal | as expected (three lines cannot fix the focal) |

## 4. R3 — the 13 top captures re-derived
- Old package `build/p1_state_20261012_14` is preserved.
- New real package `build/p1_state_20261013_01` (exit 3 = valid but partial; validation problems 0).
- Fixture rerun `build/p1_state_20261013_02` (problems 0).
- Table: `build/rim_inner_plane_20261013/top_before_after.csv`.

| plant | old µm/px | new µm/px | change | area change | area uncertainty (2σ/s) | reference / plane | leaflets with mm (Σ mm²) | compounds (Σ mm²) | d (approx.) | soil line found on sides | if the soil line had been read as 59 mm on the rim |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dwt_101 | 49.284 | 49.284 | 0 | 0 | ±0.44 % | outer top 60 / pot_rim, 0 | 30 (2686) | 5 (2724) | 278 | 2/4 | +3.6 % length, +7.3 % area |
| dwt_102 | 45.198 | 45.198 | 0 | 0 | ±0.44 % | same | 27 (1846) | 3 (1787) | 272 | 3/4 | +3.7 / +7.5 % |
| dwt_103 | 45.555 | 45.555 | 0 | 0 | ±0.45 % | same | 43 (3072) | 7 (3529) | 257 | 2/4 | +3.9 / +7.9 % |
| dwt_104 | 40.073 | 40.073 | 0 | 0 | ±0.39 % | same | 25 (2209) | 4 (1881) | 243 | 2/4 | +4.1 / +8.4 % |
| dwt_105 | 39.186 | 39.186 | 0 | 0 | ±0.38 % | same | 36 (2633) | 5 (2868) | 230 | 3/4 | +4.3 / +8.9 % |
| dwt_106 | 41.225 | 41.225 | 0 | 0 | ±0.41 % | same | 33 (2633) | 5 (3217) | 249 | 2/4 | +4.0 / +8.2 % |
| dwt_107 | 39.968 | 39.968 | 0 | 0 | ±0.36 % | same | 39 (2674) | 6 (2833) | 241 | 3/4 | +4.1 / +8.5 % |
| dwt_108 | 44.453 | 44.453 | 0 | 0 | ±0.43 % | same | 33 (2464) | 4 (2669) | 268 | 2/4 | +3.7 / +7.6 % |
| dwt_109 | 39.760 | 39.760 | 0 | 0 | ±0.46 % | same | 32 (2654) | 5 (2754) | 241 | 0/4 | +4.2 / +8.5 % |
| dwt_110 | 33.159 | 33.159 | 0 | 0 | ±0.32 % | same | 37 (1615) | 5 (2068) | 201 | 3/4 | +5.0 / +10.2 % |
| dwt_111 | 38.275 | 38.275 | 0 | 0 | ±0.37 % | same | 38 (2549) | 6 (3125) | 231 | 4/4 | +4.3 / +8.8 % |
| dwt_112 | 37.432 | 37.432 | 0 | 0 | ±0.37 % | same | 36 (1976) | 7 (2518) | 222 | 3/4 | +4.5 / +9.2 % |
| dwt_113 | 45.341 | 45.341 | 0 | 0 | ±0.44 % | same | 35 (2565) | 5 (2808) | 261 | 3/4 | +3.8 / +7.8 % |

- The 444 leaflet and 67 compound mm values in `build/topview_20261012_02` are unaffected. They come from the same
  outer-edge, rim-plane scale. The plane is now explicit.
- d is the camera distance to the rim centre from the approximate top pose (diagonal basis). It is shown only to size
  the hypothetical column and the bias.
- **Soil-line check** (`top_soil_line_check.{json,jpg,py}`): inward colour-step search (Lab b*) from the clicked
  outer lines, RANSAC per side.
  - Leaves hide most of the soil line: ≥8 inliers on all four sides in 1 of 13 photos (dwt_111).
  - On dwt_111 the medium-plane / rim-plane scale ratio is 1.093. The geometry predicts 1 + 10/d = 1.043. The
    implied distance is 108 mm against the pose's 231 mm.
  - So the detected square is about 4.6 % smaller than a flat medium surface 10 mm down would give, i.e. about
    1.4 mm per side further in.
    Possible causes: the granular edge, or a medium surface that is not flat at 10 mm next to the wall.
  - Either way, the soil line is not usable as a top-photo scale reference from these photos.

## 5. R4 — side records
- **side_000 (person, 13 photos)** converted to the new columns: `build/pot_records_template/rim_points_side_000.csv`.
  - front → `inner_top`; left, right and back → `outer_top`.
  - dwt_108's sides were numbered 3, 1, 2, 4 around the rim, so front and back were not opposite. They are renumbered
    by position, with a note in each row.
  - Preview (`build/rim_inner_plane_20261013/side_000_preview.json`): **7 validated, 6 approximate**. That matches
    the all-outer reading.
  - Rim-implied focal: 5658 ± 87 px (median 5721), against width basis 5824 and diagonal basis 6057. It still favours
    the width basis, provisionally.
  - Camera distance 234–324 mm. Reading the front as inner instead of outer moves the distance by about 1.3 mm.
  - **To use it, the human copies the converted file** (not the Downloads original: that file is in the old format
    and would read the front as the outer edge).
- **`build/rim_click_side_20261012_03` is void in place**:
  - `VOID.md` in the folder and in each sub-folder, plus a red banner in each page;
  - the same `VOID.md` in `build/rim_auto_20261012_02..05`;
  - `build/rim_click_side_20261012_02` is marked superseded, because it saves the old format;
  - no code reads any of these (grep: no references).
- **090 / 180 / 270 proposals** (`build/rim_auto_20261013_01`, `rim_auto` v2; every proposal names its line):

  | side | proposed line | photos with a proposal (of 39) |
  |---|---|---|
  | front | `inner_top` | 29 |
  | left | `outer_top` | 20 |
  | right | `outer_top` | 25 |
  | back | `side_occluded` (default) | 39 |

  - 14 photos have three lines plus the occluded back. Their three-edge pose is approximate by construction: width
    basis median distance 252 mm (225–314); the diagonal basis is +9 mm.
  - Pages: `build/rim_click_side_20261013_01/side_{090,180,270}/index.html`. Each side has a line selector and an
    "occluded" check. The page saves `rim_points_side_XXX.csv` with `edge`.
  - Look at `overlay_sheet.jpg`: **the back rim is visible beside the stem in many photos.** "Occluded" is only a
    default. Clicking the back where it shows gives four sides, which allows a validated pose and a published
    vertical scale.
  - The left/right proposals are mixed and must be reviewed.
- The package still has 104 scale gaps (52 side, 52 level). Side records exist only as templates or proposals until
  the human copies them.

## 6. R5 — plane bias
- `potscale.plane_bias_factor(d, h, offset)` = (d − offset) / (d − h). Areas use its square.
- Names: `PLANE_BIAS = {pot_rim: overestimates_above_rim, medium_surface: overestimates_above_medium_surface}`. The
  rim name is kept, because it is still correct for every published value.
- The magnitude is documented and tested. No correction factor is applied anywhere.

Illustration only, not written into a package:

| reference | d | leaf height above rim | length | area |
|---|---|---|---|---|
| rim plane | 230 mm | 20 mm | +9.5 % | +20.0 % |
| medium plane | 230 mm | 20 mm | +14.3 % | +30.6 % |

The table's last column extends this per capture (d 201–278 mm): +7.7 to +11.1 % with the rim plane, +11.6 to +16.6 %
with the medium plane. Choosing the medium plane for top photos would therefore **raise** every leaf's overestimate by
about 4 points.

## 7. For the user
- **D1, top reference plane.** The prompt decided "inner line primary". The evidence above argues for keeping the
  outer top edge on the rim plane for top photos:
  - it is what was clicked, and its silhouette is clean;
  - it is the plane nearest the leaves;
  - the soil line is mostly hidden and geometrically inconsistent.

  For side photos the "inner line" (front) **is** used, at the rim plane, where it actually lies. Switching the top
  photos would need new clicks with `edge = medium_junction`; the code supports that today.
- **Human copies:**
  - `build/pot_records_template/pot_spec.csv` replaces the EXAMPLE row;
  - `rim_points_side_000.csv` goes into `data/records/pots/`;
  - optionally, review the three side pages and save `rim_points_side_090/180/270.csv`.
- **Other owners:**
  - `tomato3d/topview/measure2d.py` (top→3D session) hardcodes `scale_plane=rim_plane`, `plane_bias=...above_rim`
    and the outer edge for its rim polygons. That is correct for today's records, but wrong if a top record ever uses
    `inner_top` or `medium_junction`. It should read `PotScale.reference_plane` and the per-side lines.
  - Pre-existing and not caused by this change: `run_p1 collect` crashes on the revision-2 package
    `build/p1_state_20261012_02` in `p2_dry_read` (MTG header).
- Tests: full `tests/` **495 passed, 1 skipped** (481 s).

## 8. Follow-up (same day): user decision and records placed
- The user said in chat: "테두리 평면 유지, 직접 복사해서 올려". So **D1 = keep the rim plane** for top photos, and I
  placed the records myself.
- Records placed:
  - `data/records/pots/pot_spec.csv` now holds the template row: `square_cell`, outer 60, inner 59, medium 10 mm,
    taper none, all `measured`. The previous file (EXAMPLE row) is kept at
    `build/rim_inner_plane_20261013/records_before_copy/pot_spec.csv`.
  - `data/records/pots/rim_points_side_000.csv` was added: the converted person clicks.
- New real package `build/p1_state_20261013_03` (validation problems 0; `collect` clean; it supersedes `_01`):
  - **Top:** 13 scales unchanged.
  - **Side_000 poses:** 8 validated, 5 approximate. dwt_108 now validates with the width basis at the package's 400
    draws; the 300-draw preview had it approximate.
  - **Vertical scale published for those 8**, on the pot axis at the rim centre, plane `pot_rim`. Values range from
    52.0 to 84.6 µm/px. Relative sd is 2.8–13 %; the largest is dwt_108 at ±13 %, where both focal bases pass.
  - **Scale gaps: 104 → 96** (44 side, 52 level).
- The top→3D path (`measure2d.pot_scale`) still returns the same rim-plane scale (dwt_101 49.284 µm/px, `pot_rim`).
