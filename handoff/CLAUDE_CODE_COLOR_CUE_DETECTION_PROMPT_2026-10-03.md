# Claude Code prompt: improve leaflet detection/segmentation with color and brightness cues (no new labels)

Date: 2026-10-03. Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.
Talk to the user in Korean. Code, handoffs and logs in English. Tables CSV, settings/provenance JSON.

## Goal

Raise leaflet detection and leaf-area accuracy of the current pipeline (detector v4 + SAM v5 + mask judge) using only image-intrinsic cues — RGB chromatic ratios, vegetation indices, brightness/lightness normalization — **without any new human labels**. Existing labels may be used for evaluation and for choosing thresholds under leave-one-plant-out.

Baseline to beat (`build/al_4plants_20261002/AL4_RESULTS.md`, model-only step_0, LOPO):

| plant | leaflet AP50 | SAM IoU | e2e IoU | area error vs human masks |
|---|---|---|---|---|
| dwt_01 | 0.774 | 0.824 | 0.655 | −1.5 % |
| dwt_02 | 0.756 | 0.838 | 0.648 | +16.6 % (6/7 photos over) |
| dwt_03 | 0.757 | 0.857 | 0.627 | +2.8 % |
| dwt_04 | 0.736 | 0.840 | 0.628 | +1.8 % |

Ground truth is human masks on the same photos, not physical leaf area.

## Read first

- `build/al_4plants_20261002/AL4_RESULTS.md`, `kout/results.json`, notebooks `tomato_al_4plants_v5_step0.ipynb`
- `build/ONE_PIPELINE_2026-10-01.md` (S1 detection, S2 masks, S8 area)
- `tools/rgb_ratio_batch.py`, `tools/leaf_preprocess_lab.py`, `tools/preprocess_study.py`, `tools/preprocess_compare.py`, `build/color_ratio_20260929/`, `build/preprocess_study_20260929/`
- LOG entries 2026-09-29/30 on preprocessing, grayworld, and the opt-in detector-input smoothing (`organ_prelabel.run(smoothing=)`, gauss5 compound FP 10→5)
- `tools/reject_reasons.py` (user's four rejection reasons: occluded, duplicate_box, box_misses_leaf, false_positive)
- Parent `공통규약.md`, `AGENTS.md`, `CONVENTIONS.md`, latest LOG/TODO. Check for active Codex sessions on any file before editing it.

## Step 1 — Baseline reproduction and error attribution

1. Locate cached step_0 LOPO predictions (boxes, masks, scores) per plant/photo. If not cached, rerun step_0 inference only (no training) with the same LOPO weights on Colab/Kaggle GPU, or locally if time is acceptable; record runtime.
2. Reproduce the baseline table above within rounding before changing anything. If it does not reproduce, stop and report.
3. Attribute area error per photo into: (a) background bleed — predicted mask pixels outside any human mask; (b) false-positive detections; (c) duplicate/merged boxes (one box covering two compounds or two leaflets); (d) missed leaflets; (e) under-segmentation inside true leaflets. Write `error_attribution.csv` (plant, photo, component, pixels, mm2 where scale exists). Explain dwt_02's +16.6 % specifically.

## Step 2 — Unsupervised color/brightness cues

Compute per photo, from original RGB (8-bit and linearized where relevant), reusing existing helpers rather than copying formulas:
- Chromatic coordinates r, g, b = channel/(R+G+B); ExG = 2g − r − b; ExR = 1.4r − g; ExG − ExR; Lab a* and L*; HSV hue/saturation.
- Lighting normalization variants: none, grayworld, white balance from the ChArUco board's white squares (board pose already known), Lab-L CLAHE, existing gauss5 smoothing.
- A per-photo vegetation mask from ExG−ExR (zero threshold) and from Otsu on ExG; record which is used. No learned model.

Save maps as compressed arrays plus PNG previews; keep the original pixel grid.

## Step 3 — Candidate improvements (each an opt-in, separately evaluated arm)

| Arm | Change | Purpose |
|---|---|---|
| A | Detector input normalization (grayworld / board white balance / CLAHE / gauss5) | Stabilize detection across lighting |
| B | Mask trimming: final mask = SAM mask ∩ dilated vegetation mask (dilation radius declared) | Remove background bleed (likely dwt_02 cause) |
| C | False-positive filter: drop detections whose mask green fraction (vegetation-mask overlap) < τ | Reject board/pot/stem/shadow boxes |
| D | Duplicate/merged-box check: split or flag boxes whose vegetation mask has ≥2 large components or whose mask overlaps another accepted mask ≥ declared fraction | Address merged-box overcount |
| E | Color-proposal recall: vegetation connected components not covered by any detection → SAM box/point prompts, tagged `origin=color_proposal` | Recover missed leaflets; counted separately, never auto-accepted unless they pass the existing mask judge |
| F | Mask-judge features: add green fraction, mean a*, ExG contrast to the judge's inputs (refit on existing labels only, LOPO) | Raise auto-accept rate at ≥96 % precision |
| G | Best combination of the above | — |

Rules:
- Thresholds (τ, dilation, overlap fraction, Otsu vs zero) are chosen **leave-one-plant-out**: select on three plants, test on the fourth, rotate. Report the selected values per fold; never tune on the test plant.
- No new labels, no detector/SAM retraining in this task. (Retraining with color augmentation on existing labels is a separate later option; mention it only as a recommendation.)
- Stems and petioles are green too: arm C/B must not delete leaflet pixels at petiole junctions; report pixels removed that fall inside human leaflet masks.
- Flowers/buds (yellow) and fruits are other organ classes; do not let vegetation masks remove them from their own classes.

## Step 4 — Evaluation

For baseline and every arm, per plant and per photo: leaflet AP50, SAM IoU, e2e IoU, area error vs human masks, auto-accept rate and precision of the mask judge, pixels removed inside human masks. Also report mean |area error| over the four plants and the spread across photos.

Then apply baseline and the best arm, without ground truth, to dwt_test T1/T2/T3 (`build/plants_dwt_test_20261002`) and report distribution shifts only (area, number of detections, removed pixels, proposals). These have no human masks; make no accuracy claim for them.

Acceptance for recommending an arm as the new default:
- mean |area error| decreases, and dwt_02 error decreases;
- no plant's |area error| worsens by more than 2 percentage points;
- leaflet AP50 does not drop by more than 0.01 on any plant; SAM/e2e IoU do not drop on average;
- pixels removed inside human masks ≤ 2 % of human mask area per plant.
If no arm meets this, say so and keep the baseline.

## Constraints

- Do not modify `tomato3d/` core semantics, `config/`, human labels/masks, or original photos.
- New behavior is opt-in (flags/parameters, default off) until the user accepts it. Existing runs must reproduce unchanged.
- All outputs in a fresh `build/color_cues_20261003_01/` (or later date). Record source hashes and code version.
- Vegetation masks are evidence for filtering, not ground truth; color proposals are never observed leaves unless accepted through the existing review/judge path.
- Report what failed as failures.

## Deliverables

- `build/color_cues_.../`: `baseline_check.json`, `error_attribution.csv`, `arm_results.csv` (plant, photo, arm, metric, value), `fold_thresholds.json`, `dwt_test_shift.csv`, preview PNGs, JUnit XML for new tests.
- Tests for: vegetation index math on synthetic images, threshold selection never using the test plant, mask trimming never growing a mask, proposals tagged and excluded from area unless accepted, opt-in default off reproduces baseline.
- English handoff `handoff/CLAUDE_COLOR_CUE_DETECTION_RESULT_2026-10-03.md`; one LOG line; TODO for open items.
- Korean summary for the user: which arm helped, by how much, the dwt_02 cause, and whether to make it default.
