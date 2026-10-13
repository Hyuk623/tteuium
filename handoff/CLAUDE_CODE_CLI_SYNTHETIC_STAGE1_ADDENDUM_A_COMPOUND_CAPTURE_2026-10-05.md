# Addendum A to the synthetic dwarf tomato Stage 1 task: compound-leaf close-up capture

> For the Claude Code CLI session already running
> `handoff/CLAUDE_CODE_CLI_SYNTHETIC_DWARF_TOMATO_STAGE1_2026-10-05.md`.
> Paste into that session: `Read handoff/CLAUDE_CODE_CLI_SYNTHETIC_STAGE1_ADDENDUM_A_COMPOUND_CAPTURE_2026-10-05.md and apply it to the current task.`

Date: 2026-10-05. User decision. Talk to the user in Korean; code/logs/handoffs in English.
All safety rules of the main task (§0: write paths, no `tools/`/`config/`/`pyproject.toml`/existing-file edits, lazy imports, before/after test comparison) still apply unchanged.

---

## 1. What changes

The user adds a **dedicated generator capture** next to the normal 18-view sessions:

- per plant: **1 top-view photo of the whole plant** + **1 close-up photo of each compound leaf** (e.g. 3 compound leaves → 4 photos);
- planned for **6–8 plants, all compound leaves of each plant** (including lower leaves);
- the **18-view sessions are not replaced**. They remain the source for insertion angle, rachis droop, leaflet bend/roll, internode length, height, colour statistics, the realism gate and the amodal test.

Use of the new photos:

| Generator part | Before this addendum | After |
|---|---|---|
| Leaflet contour library | unoccluded leaflets from human-reviewed 18-view masks | **primary:** leaflets from compound-leaf close-ups; **secondary:** 18-view reviewed masks (keep source tagged) |
| Compound-leaf priors for L-Py (pair count, spacing, size taper along rachis, terminal leaflet, small intercalary leaflets) | wide `user_assumed` ranges | `measured_range` from close-ups (per rank where possible) |
| Plant layout (compound azimuths, footprint) | P3 engine ranges | check against the plant top view |
| Angles, droop, bend/roll, internodes, height | 18-view middle/side rings | unchanged (18-view) |

## 2. Where the photos are (human-owned, read-only for you)

The user places them in the raw-data tree (per `CONVENTIONS.md` §4):

```
data/raw/<plant_id>/<plant_id>_gen_<YYYYMMDD>/
    plant_top.jpg
    <compound_id>.jpg            # e.g. L01.jpg, L02.jpg … bottom → top, same IDs as the existing compound-leaf IDs
    generator_capture.csv        # written by the user
```

`generator_capture.csv` columns (human-written; you only read and validate):
`plant_id,session_id,photo_file,photo_kind,compound_id,rank_from_bottom,captured_at,scale_reference,scale_reference_size_mm,scale_at_leaf_height,camera_normal_to_leaf,leaf_pose,notes`
- `photo_kind ∈ {plant_top, compound_closeup}`
- `scale_reference ∈ {charuco_board, ruler, marker}`; `scale_at_leaf_height ∈ {yes, no}`
- `camera_normal_to_leaf ∈ {yes, approx, no}`
- `leaf_pose ∈ {natural, lightly_supported}` (leaves are **not** flattened by pressing)

Resolve `data/` through `tomato3d.config.get_settings()`; never hard-code `./data`. Never write, rename or "repair" anything under `data/`. If the CSV is malformed, report the rows and continue without them.

If the photos are **not there yet**: continue the main task with 18-view masks and `user_assumed` ranges, write `compound_capture_status: pending` into `generator_config.json`, and integrate later without changing the contract criteria already declared.

## 3. Processing (inside `tomato3d/synth/`, outputs under the task's `build/` folder)

1. **Validate** the CSV against files (hash every photo into `inputs_manifest.json`).
2. **Scale:** from ChArUco detection (existing detector code in `tomato3d/` may be imported read-only) or the declared ruler/marker. If `scale_at_leaf_height=no`, mark mm values `scale_uncertain` and use them only for shape (normalised) not size.
3. **Leaflet segmentation:** reuse the existing detector + SAM path read-only, or an interactive/manual mask if the user provides one. Keep only leaflets that are fully visible and not strongly curled; record exclusions with reasons (`occluded`, `curled`, `out_of_focus`, `cut_by_frame`).
4. **Perspective:** if `camera_normal_to_leaf ∈ {approx, no}`, do not use the outline as an undistorted shape unless a plane fit (board or leaf-plane estimate) corrects it; otherwise tag `foreshortened` and exclude from the primary library.
5. **Contour library:** normalise as in the main task; tag `source ∈ {compound_closeup, view18_reviewed}`, `plant_id`, `compound_id`, `rank_from_bottom`, leaflet position on the rachis (terminal / pair index / intercalary).
6. **Compound priors:** per compound leaf: leaflet pair count, terminal leaflet presence, intercalary count, spacing along the rachis (normalised to rachis length), size taper (leaflet length vs position), left/right asymmetry. Aggregate by rank class; write `compound_priors.csv` and set the L-Py ranges in `generator_config.json` with `source_kind='measured_range'`, `source_ref` = file hashes. Keep the old assumed ranges in the config history.
7. **Plant top view:** compare synthetic top-view footprint and compound azimuth spread with these photos; add to the realism report (it does not change the pre-declared gate).

## 4. Bias controls (report each)

- Coverage by rank: count compound leaves per `rank_from_bottom`; flag if lower ranks are under-represented.
- Excluded fraction by reason; flag if exclusions are concentrated in one rank or plant.
- Flatness: compare leaflet roll/bend measured in 18-view with close-up outlines; do not let close-ups make synthetic leaves flatter than real ones (bend/roll ranges stay from 18-view).
- Plant-level split: the generative **test-set plants** (≥6–8, per the review) must not contribute contours or priors. Record which plants were used.

## 5. Tests (new `tests/test_synth_*.py` only)

1. CSV validation: missing file, unknown `photo_kind`, duplicate `compound_id` per session → reported, not crashed; nothing under `data/` modified (hash before/after).
2. `scale_at_leaf_height=no` → mm values flagged, not used for size ranges.
3. Contour library sources tagged; test-set plants excluded.
4. `compound_priors.csv` → `generator_config.json` ranges carry `measured_range` + hashes.
5. With no capture folder present → status `pending`, generator still runs on fallback ranges.

## 6. Report

Add a section to `handoff/CLAUDE_SYNTHETIC_DWARF_TOMATO_STAGE1_RESULT_2026-10-05.md`: photos received/used/excluded (by reason and rank), measured compound priors vs previous assumed ranges, effect on the realism report. One LOG line. Korean summary to the user, including any capture-rule problems to fix in the next batch.

## 7. Capture guide to show the user (Korean summary in your reply)

- 18-view sessions stay as they are; this capture is extra.
- Camera **perpendicular to the leaf surface** (not just "from above"); tilt to match a drooping rachis.
- Do not press leaves flat; photograph natural pose; very curled leaflets will be excluded.
- Scale reference (small ruler/marker) **at leaf height**.
- Label compound leaves bottom → top (L01, L02, …) matching existing IDs; filename or small number tag.
- Photograph **all** compound leaves of the plant, including the lower ones.
- Plain background, the same lighting as the rig, focus on the leaf (macro if needed).

---

## Revision A.1 (2026-10-05 16:41 KST, user decision) — replaces the capture set in §1, §2 and §7

**New per-plant generator capture: 1 top view + 4 side views, a ruler in every photo.** Per-compound-leaf close-ups are no longer required.

| Photo | How | Scale |
|---|---|---|
| `top.jpg` | camera 40–50 cm above, 2× zoom, level, focus on leaves | ruler lying on the pot rim |
| `side_000.jpg`, `side_090.jpg`, `side_180.jpg`, `side_270.jpg` | camera fixed, **looking down 20–30°** (not horizontal) so lower compound leaves show their leaf surface; **pot rotated** 90° each time from a marked 0° direction | ruler standing next to the stem, soil surface = 0 |

Order fixed: top → 0° → 90° → 180° → 270°. Plant ID visible in every photo.

Folder (unchanged location): `data/raw/<plant_id>/<plant_id>_gen_<YYYYMMDD>/`. `generator_capture.csv` columns become:
`plant_id,session_id,photo_file,photo_kind,azimuth_deg,camera_elevation_deg_approx,captured_at,scale_reference,ruler_plane,exposure_note,notes`
- `photo_kind ∈ {top, side}`; `azimuth_deg ∈ {0,90,180,270}` for side, empty for top
- `ruler_plane ∈ {pot_rim, beside_stem_vertical}`

Processing changes:
- **Top scale:** the ruler is on the pot rim, below the leaves. Correct perspective with leaf height above the rim measured from the side photos (scale factor ≈ D/(D−h)); if leaf height or camera distance cannot be estimated, mark top-view mm values `scale_uncertain` and use the top view for shape/layout only.
- **Compound priors:** count leaflets/pairs/taper from the top view for visible compound leaves and from the four elevated side views for lower/hidden ones; record per compound which photo(s) supported it. Compounds not resolvable in any photo → `unresolved`, not guessed.
- **Angles/droop/height:** from the four side views (all azimuths), combined with 18-view sessions where available.
- **Leaflet contours:** only fully visible, not strongly curled leaflets from these photos plus 18-view reviewed masks; tag `source`.
- **Exposure:** photos may be somewhat darker than the rig photos. Do not take leaf colour statistics for the generator from these photos (use rig photos). Segment after a per-photo normalisation (gray-world/CLAHE as in the existing preprocessing study) without changing the original files. Exclude photos with clipped highlights or heavy noise and record the reason `exposure`.

Bias controls, tests and reporting in §4–§6 apply to this capture set; replace "compound close-up" by "top/side view" where relevant, and add a test that a compound not visible in any photo is reported `unresolved`.

## Revision A.2 (2026-10-05 16:59 KST, user decision) — adds one height photo to A.1

Per plant: **`top.jpg` + `height.jpg` + `side_000/090/180/270.jpg` (6 photos)**, order top → height → 0° → 90° → 180° → 270°.

- `height.jpg`: camera **level (horizontal)** at about mid-plant height, white background, whole plant and the pot rim visible, ruler standing upright **beside the pot at the same depth as the stem**. Used for plant height and stem/insertion geometry only.
- Height rule: read the ruler at the **pot rim** and at the plant top **in the same photo**; height above rim = top − rim. Do not rely on where the ruler's 0 stands (it may stand on a base). Height above soil = height above rim + soil depth below rim (per-pot value in `notes`).
- The four `side_*` photos stay at 20–30° looking down (leaflet counts on lower compounds, angles/droop); they are not used for height.
- CSV: `photo_kind ∈ {top, height, side}`; add to `notes` per plant: `pot_height_cm`, `soil_depth_below_rim_cm`.

## Revision A.3 (2026-10-05 17:09 KST, user decision) — 9-photo set, replaces the photo list in A.2

Per plant: **`top.jpg` + `side_000/090/180/270.jpg` (angled) + `level_000/090/180/270.jpg` (level) = 9 photos**. Order: top → side 0/90/180/270 → level 0/90/180/270. The single `height.jpg` from A.2 is replaced by the four `level_*` photos.

| Photo | Camera | Ruler | Used for |
|---|---|---|---|
| `top.jpg` | 40–50 cm above, level, 2× zoom | lying on the pot rim | layout, top-view leaflet shape/count |
| `side_000…270.jpg` | looking down 20–30°, pot rotated 90° each | standing beside the stem | lower/hidden compound leaflet counts, droop, angles |
| `level_000…270.jpg` | horizontal at mid-plant height, pot rotated 90° each | standing beside the pot at stem depth, pot rim visible | plant height, stem/insertion geometry, petiole angles in profile |

- Height rule (unchanged from A.2): ruler reading at the plant top minus reading at the pot rim **in the same photo**. Report height per `level_*` photo and use the **median of the four** as `height_above_rim_cm`; report max−min spread. If spread > 1.0 cm, flag `height_inconsistent` and list it in the report.
- Top-view perspective correction: scale factor ≈ D/(D−h), where D = camera height above the rim and h = leaf height above the rim (from `level_*`). Per-plant `camera_height_above_rim_cm` is recorded in `notes` when known; if missing, estimate D from the pot rim's apparent diameter vs. its known diameter, else mark top-view mm values `scale_uncertain`.
- CSV: `photo_kind ∈ {top, side, level}`; `azimuth_deg ∈ {0,90,180,270}` for side and level, empty for top; `ruler_plane ∈ {pot_rim, beside_stem_vertical, beside_pot_vertical}`. Per-plant `notes` keys: `pot_height_cm`, `soil_depth_below_rim_cm`, `camera_height_above_rim_cm` (optional).
- Features observed in the first test plant that the generator must be able to express (or report as out of scope): strong leaflet curl/droop, a dead/senesced leaf fragment on the stem, exposed adventitious roots at the stem base. Do not filter these out of real-photo statistics silently; tag them.
- Add a test: a session with the four `level_*` heights whose spread exceeds 1.0 cm is reported `height_inconsistent`; a session missing any of the 9 files is reported `incomplete` and listed, not silently processed.

Everything else in A.1/A.2 (folder, exposure handling, bias controls, `unresolved` rule) is unchanged.

## Revision A.4 (2026-10-05 18:10 KST) — first real capture batch is in place

- 13 plants, `dwt_101` … `dwt_113`, session `<plant_id>_gen_20261005`, 9 photos each (117 total), under `data/raw/<plant_id>/<plant_id>_gen_20261005/`.
- Files are the **original HEIC** (byte-identical copies, sha256 in the CSV), named `top.heic`, `side_000…270.heic`, `level_000…270.heic`. Read HEIC with `pillow-heif` inside the `tomato_synth` env only (do not add it to `pyproject.toml`); never re-encode the originals.
- `generator_capture.csv` per session has the A.3 columns plus `source_filename`, `sha256`, `azimuth_basis`, `height_above_rim_cm`.
  - `azimuth_basis=capture_order_assumed`: the 0° mark was not recorded; azimuths follow capture order. Treat azimuths as relative, not absolute.
  - `height_above_rim_cm` is empty: measure it from the `level_*` photos with the A.3 rule and report it; do not write back into `data/raw/`.
  - `soil_depth_below_rim_cm` is empty (pot height 7 cm is known).
- Combined manifest and contact sheets: `build/gen_capture_20261005_01/` (`generator_capture_all.csv`, `inventory.csv`, `sheets/group_01…13.jpg`).
- `dwt_113` top photo: the ruler lies horizontally on the rim (still the rim plane — valid).
- Per-plant visual notes (curl, dead leaflets, adventitious roots, yellowing) are in the `top` row `notes`; tag them, do not filter them out.
