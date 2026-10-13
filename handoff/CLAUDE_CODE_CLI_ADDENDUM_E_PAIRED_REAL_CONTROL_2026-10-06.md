# Addendum E: paired real control for C6 (2026-10-06)

Supersedes the planned D.3 reweighting diagnostic, which is **on hold**: a reweighting corrects for the two sides
being different populations after the fact; this holds the population fixed and measures directly. If E settles the
question, D.3 is not run.

Runs **in parallel with B5c**. Entirely local: **no rendering, no Kaggle**. The detector stays frozen
(sha256 `609fd7ae…`). **The real photos taken here are evaluation-only and must never be used for training or for
tuning any threshold.**

## E.0 The question

C6 compares real 0.73 against synthetic 0.328, but on **different plants in different scenes**, so rendering,
arrangement and leaflet-size distribution are all confounded. Measured facts to date: the gap is concentrated by size
(recall `<150 px` 0.08, `150-500` 0.40, `500-1500` 0.70, `>1500` 0.79 against real 0.69 / 0.84 / 0.93 / 0.96), the
synthetic set carries ~23 % of its GT below 150 px against real ~10 %, and `C4_median_ratio` is 0.61.

A real photograph taken at a **matched camera angle and matched in-frame plant size** on a plant of similar form makes
the comparison paired. Then:

- detector finds the real leaflets but not the matched synthetic ones -> **rendering** is the cause, and the
  recall-by-size tables say in which size bucket;
- detector misses both -> the configuration is genuinely hard and/or the **GT rule** is the problem, not the renderer.

A second gain: the user labels the real photos under a **written rule**, and the same rule is then applied to the
synthetic GT. Today real GT is "human-accepted SAM masks" while synthetic GT is "every instance over
`min_visible_px`" - the two have never been measured with the same ruler.

## E.1 Step 1 - Claude Code produces the shooting pack (local, no render)

From the **B5a** run (`build/synthetic_dwarf_tomato_20261005_03/B5a`), select **6 views** of the 5 pilot scenes:

- **4 failing views** - lowest per-view recall under the B1 rule; among those prefer views whose GT is richest in
  `<150 px` leaflets, since that bucket holds the gap. State the ranking rule and the numbers used.
- **2 control views** - highest per-view recall. They test whether the matching procedure itself works: if the real
  counterpart of a *good* synthetic view also scores well, the pairing is sound.

Write `build/paired_control_20261006_01/` containing, per selected view:

- `view_<id>_synth.png` - the synthetic `rgb.png`, for the user to imitate;
- `view_<id>_detections.png` - the same image with GT in one colour and the frozen detector's detections in another,
  so the user can see what was found and what was missed;
- a row in `shoot_sheet.csv` with: `view_id, scene, view_name, per_view_recall, n_gt, n_gt_lt150,
  camera_elevation_deg, plant_height_mm, plant_bbox_frac_height, plant_bbox_frac_width, n_leaflets_total,
  n_leaflets_visible, gt_area_px_p10, gt_area_px_p50, gt_area_px_p90`.

`plant_bbox_frac_height` (the plant's bounding box as a fraction of frame height) is the number the user matches in
the viewfinder. B4a showed framing changes leaflet pixel size by ~2x, so an unmatched framing would reintroduce the
confound this whole step exists to remove. Azimuth is **not** a target - it is arbitrary in both sets; only elevation
and in-frame size are matched.

## E.2 Step 2 - capture (user)

- **Rig setup**: ChArUco board, the same lights and the same camera as the dwt_01-04 captures. Not the handheld
  dwt_101 arrangement - the detector was trained in the rig, so a different background or light is a new variable.
- Pick a real plant whose height and leaflet count are close to the sheet's values; one plant may serve several views.
- Per target view: match `camera_elevation_deg` and `plant_bbox_frac_height`, then take **one** photo.
- Record `build/paired_control_20261006_01/capture_log.csv`:
  `view_id, plant_id, photo_file, camera_elevation_deg, plant_bbox_frac_height, captured_at, notes`.
- Photos are human-owned: copy them to `data/raw/paired_control/pc_20261006/` with sha256, as in Addendum A.

## E.3 Step 3 - labelling rule (write it before labelling, apply it to both sides)

Claude Code writes `build/paired_control_20261006_01/labelling_rule.md` **first**, as an explicit, testable rule.
Starting point, to be confirmed by the user on the first photo before the rest are labelled:

> A leaflet is labelled when it is recognisable as a leaflet by its shape and has at least **N** visible pixels at
> 512 px. Fragments that are only a sliver between other leaves, where the shape is not recognisable, are not
> labelled. The rule has a version number and every labelled photo records it.

Pick `N` from the real pool (do not reuse the B1 value without checking), state how it was chosen, and keep the
version in every output row. Then:

- the user labels with the existing SAM review tool; output per photo is an instance mask PNG (uint16 ids) plus
  `leaflets.csv` with `view_id, photo_file, leaflet_id, area_px, rule_version`;
- **the same rule is then applied to the synthetic GT** of the 6 matched views, producing a second synthetic GT
  alongside the existing one. Report both.

## E.4 Step 4 - comparison (Claude Code, no render)

Run the frozen detector on the 6 real photos and on the 6 matched synthetic views, both at 512 px, resized the same
way B0 used (`INTER_AREA` for images, `INTER_NEAREST` for masks).

Report, pair by pair and pooled: AP50 and recall by size bucket (`<150 / 150-500 / 500-1500 / >1500`), under
**(a)** each side's existing GT and **(b)** the common E.3 rule. Four numbers per pair; the (b) pair is the one the
decision uses.

### Decision rule, declared before running

- **real >= 0.60 and synthetic <= 0.40** (common rule, pooled): rendering is confirmed as the cause at matched
  population. The recall-by-size tables name the bucket, and the next factor is chosen from that - not guessed.
- **both <= 0.45**: the renderer is not the binding problem for these configurations. Re-examine the GT and the
  scoring (the acceptance-rate curve of D.3.3) before any further appearance work.
- **both >= 0.60**: the selected views were not representative of the failure. Re-select with a stated reason;
  do not conclude anything about rendering.
- any other combination: report and ask the user.

## E.5 Output

`build/paired_control_20261006_01/` (shoot sheet, capture log, labelling rule, per-pair results, one figure showing a
real and its matched synthetic side by side with detections), an `E0` row in `c6_steps.csv` marked `paired_control`,
and an Addendum E section in `C6_REPORT.md`. **No contract change, no generator change, no detector change in this
step.** Korean 5-line summary in your reply, ending with which branch of E.4 the result selects.
