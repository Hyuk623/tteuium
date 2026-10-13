# Colour/brightness cues for leaflet detection and area — result (executed 2026-10-04)

Brief: `handoff/CLAUDE_CODE_COLOR_CUE_DETECTION_PROMPT_2026-10-03.md`. Outputs: `build/color_cues_20261004_01/`.
**Outcome: no arm meets the acceptance rules. Keep the baseline.** Nothing in the pipeline changed; every new path is
opt-in and unused by default.

## Status at write time (session cut by usage limit)
- Run 1 of `evaluate` and the diagnostic grid finished. A rerun was started with two guards on arm E (degenerate
  vegetation masks, component <= 2 % of frame); it reproduced A–D/F selections and E = off, G = D for dwt_01 at write
  time. When it finishes it overwrites summary.json, arm_results.csv, fold_thresholds.json, dwt_test_shift.csv,
  diagnostic_grid.csv and judge_results.csv. **Check those files** (logs: evaluate.err.log, diagnostic.err.log; run-1
  logs kept as evaluate_run1.*). Numbers below are from run 1 except where noted. Arm E numbers from run 1 are invalid
  (see below).

## Code (new files only)
- `tools/color_cues.py`: chromatic r,g,b (reuses leaf_preprocess_lab.colour_ratios / linear_rgb), ExG, ExR, ExG−ExR,
  Lab L*/a*, HSV, normalisations none/grayworld (rgb_ratio_batch.grayworld)/board_wb/clahe/gauss5 (preprocess_study),
  board white balance from detected ArUco marker margins (no pose needed), vegetation masks exgr_zero / exg_otsu with
  `degenerate` flag, trim_mask (can only remove), mask features, lopo_select, pack/unpack.
- `tools/color_cue_eval.py`: `wb`, `bundle`, `evaluate`; arms A–G, LOPO selection, error attribution, judge refit,
  dwt_test shift. `build/color_cues_20261004_01/diagnostic_grid.py`: fixed-setting diagnostics (not selection).
- `tools/tests/test_color_cues.py`: 20 tests (index math, Otsu, WB, trim never grows, LOPO never sees test plant,
  proposals tagged/excluded unless judge accepts, default arm = baseline, degenerate flag). JUnit:
  `tests_color_cues.xml` (26 passed incl. rgb_ratio_batch and decision_learning tests).
- Ownership note: CLAUDE.md says tools/ is Codex's; recent practice (rgb_ratio_batch, plant_batch, plant_traits) put
  Claude tools there. New files only, no Codex file edited. Move if the human prefers.
- Kaggle: dataset `dolgfish/tomato-color-cues-code`, kernel `dolgfish/tomato-color-cues-infer` v2 (T4, 59 min,
  inference only, no training). Source `kernel/infer.py`, hashes in `bundle_manifest.json`.

## Step 1 — baseline reproduction: exact
`baseline_check.json`: leaflet AP50, SAM IoU, e2e IoU and every per-photo area reproduce AL4 step_0 to all printed
digits for all four plants (diff 0). Mask-judge redraft features also reproduce redraft.json (score diff <= 1.2e-5).

## Step 1.3 — error attribution (`error_attribution.csv`), cm², summed over side posed photos
| plant | a bleed | b false positive | c dup/merged | d missed | e under-seg | total |
|---|---|---|---|---|---|---|
| dwt_01 | +4.65 | +3.43 | +0.33 | −4.65 | −4.84 | −1.05 |
| dwt_02 | +7.54 | **+10.99** | +1.63 | −3.04 | −4.37 | **+12.92** |
| dwt_03 | +6.77 | +4.95 | +1.31 | −3.84 | −5.86 | +3.27 |
| dwt_04 | +7.39 | +9.57 | +0.77 | −3.54 | −11.59 | +2.50 |

**dwt_02 +16.6 % explained:** bleed is ordinary (same as dwt_04). The difference is "false positives" that are mostly
real green tissue absent from the human masks: 15 of 112 leaflet boxes on dwt_02 side posed photos have no accepted
human mask (dwt_01 3, dwt_03 7, dwt_04 2; list `leaflet_boxes_without_human_mask.csv`), ~40 % of dwt_02 FP pixels sit
on such boxes; the rest are unlabelled leaflets and one main stem segmented as a leaflet (photo 27). FP masks have
green fraction 0.96–1.0 and a* ≈ −18, so colour cannot remove them. The truth is low, not (only) the model high.
Overlays: `previews/dwt_02_20260920_{21,25,27}_false_positives.png`.

## Step 2 — cues
- ExG−ExR > 0 is stable: 4–11 % of each photo (median 4.4 %). **Otsu on ExG fails in 20–23 of 62 photos** (covers
  > 30 %, up to 99 %: it splits board black/white, the plant is ~5 % of the frame). Recorded as a failure.
- Board WB gains from marker margins: 56/62 photos (0.90–1.12); 6 photos show no markers → board_wb falls back to
  none (recorded). Grayworld and board WB disagree in direction on some photos (scene-content bias of grayworld).
- Maps: `veg/<photo>.npz` (packed masks, all photos/norms/methods), `previews/*_cues.png` (all photos), full-grid uint8
  maps only for dwt_02 side photos (`maps/`) to limit size; others regenerate deterministically.

## Steps 3–4 — arms, LOPO held-out (`arm_results.csv`, `fold_thresholds.json`)
Baseline mean |area err| 5.73 % (dwt_02 16.71 % with unrounded means).
| arm | per-fold choice | mean \|err\| | failing rule |
|---|---|---|---|
| A input norm | clahe / none / board_wb / none | 6.08 | mean err up, e2e IoU down |
| B trim | off ×4 | 5.73 | no gain (trimming removes 6–28 % of human pixels) |
| C FP filter | τ 0.1 (dwt_01 only) | 6.32 | dwt_01 worse >2 pp, e2e down |
| D duplicates | overlap 0.5/0.5/0.5/0.7 | **5.51** (dwt_02 16.49) | **e2e IoU drops on all plants** (0.655→0.640, 0.648→0.631, 0.627→0.611, 0.628→0.611) |
| E proposals | off ×4 | 5.73 | run 1 invalid: degenerate Otsu gave whole-frame proposals (+2158 %); accepted proposals matched 0 human leaflets (background mesh fragments). Rerun with guards: still off |
| F judge colour | off (no area effect) | 5.73 | see judge below |
| G forward selection | D only ×4 | 5.51 | as D |

Diagnostic (fixed settings, `diagnostic_grid.csv`): trimming at any radius lowers area by removing 6–28 % of human
leaflet pixels (thin/curled leaflet edges are not ExG−ExR > 0); fixed C τ 0.2 gives 5.22 % mean but AP50 −0.015 and
e2e −0.016. No colour arm reduces dwt_02 meaningfully, consistent with the attribution.

**Judge (arm F), refit LOPO on the 1,281 reviewed redraft items:** auto-accept 59.0 % → 62.8 %, pooled precision
96.3 % → 96.2 %; per plant precision 0.958/0.958/0.962/0.967 (dwt_01 drops below 0.96, dwt_02 rises from 0.939). On
step_0 masks (correct = IoU ≥ 0.5 to a human mask) the colour judge auto-accepts more but with lower precision on
dwt_01/03/04 (`judge_results.csv`). Promising but not safe as default.

## dwt_test T1–T3 (no ground truth; `dwt_test_shift.csv`, production plant_auto masks)
Best arm D (final setting dup 0.5 on all four plants): masks 435→388, 489→383, 394→337; mask union pixels −2.7 %,
−2.8 %, −2.4 %. No accuracy claim. A/E need new inference and were not applied.

## Assumptions and deviations
- Judge drafts at leaflet default sensitivity 20 (the judge's training drafts all use 20; kernel v1 used 50 and was
  replaced). Judge correctness on model masks = IoU ≥ 0.5 to a human mask (proxy, human masks incomplete).
- LOPO objective: mean |area err| on the three training plants; settings excluded if a training plant loses > 0.01
  AP50 or > 2 % of human pixels; judge for proposals refit without the held-out and the scored plant.
- Arm C uses original-photo vegetation only; arm D "split" uses vegetation components; AP50 for E excludes proposals.
- Crops in SAM-IoU trimming carry their photo's grayworld/board gains.

## Recommendation
Keep baseline. Fix the truth first: add human masks for the 15 dwt_02 (and 12 other) boxes without one, then re-score;
the +16.6 % outlier is mostly a truth gap. Stem-as-leaflet needs a shape cue (elongation), not colour. Later option:
retrain detector/SAM with colour augmentation on existing labels; F (colour judge) could be revisited after that.

## Addendum 2026-10-04 18:15: rerun outputs checked

- The guarded `evaluate` rerun (finished 15:50) matches every number above: A-G mean |err| 6.08/5.73/6.32/5.51/5.73/5.73/5.51; D folds 0.5/0.5/0.5/0.7; E off on all four folds; G = D on all four plants (not only dwt_01); judge 59.0->62.8 % at 96.3->96.2 %; dwt_test masks 435->388, 489->383, 394->337, union -2.7/-2.8/-2.4 %. No text change needed.
- The diagnostic-grid rerun had been killed during the E rows; rerun to completion. Run-1 files kept as `diagnostic_grid_run1.csv`, `judge_results_run1.csv`, killed log `diagnostic_run2_killed.err.log`. All non-E rows and `judge_results.csv` are byte-identical to run 1.
- Guarded arm E (fixed settings, diagnostic only): area error now equals baseline (dwt_01 -1.53, dwt_02 16.71, dwt_03 2.86 %), except dwt_04 2.02 % vs 1.81 % at unc 0.5/0.7. 3-10 proposals are accepted per plant, and none match a human leaflet (matched_human 0 for every setting). The invalid run-1 values (+2158 % etc.) are gone. Conclusion unchanged: proposals add no real leaflets; keep the baseline.
