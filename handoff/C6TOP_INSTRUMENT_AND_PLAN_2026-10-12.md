# C6-top: the real-photo top detector as realism judge — instrument declaration (DRAFT) + plan (2026-10-12)

User decision 2026-10-12: **purpose A** — `tomato_top_nonboard` judges whether synthetic top views look real; the
generator is changed to pass it, the detector is never trained on synthetic. This is the "declared instrument change"
of `handoff/DETECTOR_POLICY_2026-10-09.md` scope 2. Evidence for the plan: `build/topdet_synth_check_20261012_01/REPORT.md`.

## 1. Instrument declaration — DRAFT until the user confirms items marked (U)

| field | value |
|---|---|
| gate name | **C6-top** — a NEW, narrower gate (top views only). Old C6 rows (frozen `full_final_all.pt`, 12 views) are never rewritten; C6-top is its own column. |
| judge | Roboflow `tomato_top_nonboard/4` (rfdetr-2xlarge, 880 px, workspace `-ndul9`). Frozen: the instrument is version 4. A later version (v5…) is a NEW instrument and starts a new column. No local weights/sha256 exist; the pin is the Roboflow model id + its reported metrics (valid 0.6839 / test 0.706). |
| provenance | filename check 2026-10-12: all 49 project images are phone photos (`IMG_*`, `top.heic`), no `rgb.png`. **(U) user confirms no synthetic image was ever uploaded to this project.** v4 training images: IMG_8298, 8308, 8347, 8377, 8390, 8391, 4× `top.heic` (+ augmentations). |
| scoring | `build/topdet_synth_check_20261012_01/run_topdet_check.py`: confidence 1 %, overlap 60 %, ≤300 boxes, `tomato3d.synth.evaluate.ap50` (IoU 0.5 greedy, 101-point). Gate metrics: AP50 for `compond_leaf`, `leaf`, `terminal_leaf` and their mean; class-agnostic AP50 reported alongside; `leaf2`/`shoot`/`truss` reported only once the synthetic GT has enough instances (≥ 30 per class). |
| real reference | **(U) at least 10 real top photos, labelled with the six classes, never in any training split of the judge.** Today only 4 exist (valid 2 were used for model selection → optimistic). Candidates: the ~34 unannotated photos already in the project. Tag them `c6top_ref` and keep them out of every future version's train split; or put them in a separate real-only project. |
| noise floor | scene-bootstrap half-width per cell (as in I.1), computed under this judge before any delta is called real. |
| dual-scored re-baseline | the carry-forward baseline cell's top views scored under BOTH the frozen C6 detector and C6-top, side by side, once the real reference exists. |

## 2. Why the generator, not the judge, has to move (2026-10-12 diagnostics)
Common-3 mean AP50 real 0.863 vs synthetic 0.324 (full) / 0.376 (plant-framed crop); leaflets merged 0.810 vs 0.499.
- capture: synthetic has a ChArUco board, black round pot, dark soil; real top photos have white paper, a translucent
  white square pot, orange vermiculite, a ruler, hard top light, plant ≈ 66 % of the image side (synthetic ≈ 20 %).
- structure: visible leaflets/compound real 6.5–8.0 vs synthetic 3.7 (F.6: generator ~5 per compound, no
  second-order leaflets); real leaflets serrated/lobed; detector calls synthetic basal pairs `leaf2` and laterals
  `terminal_leaf` (75 of 134 terminal predictions on laterals).
- shoot: generator apex = sphere → shoot AP 0.

## 3. Plan — one factor per cell, each 15 scenes, scored under C6-top with its noise floor

| step | what | who | needs |
|---|---|---|---|
| 0 | real reference set (§1) + declaration confirmed | **user** labels ≥10 photos; confirms (U) items | — |
| 1 | dual-scored re-baseline of the current carry-forward cell (top views) | Claude Code | step 0 |
| 2 | **cell T0 "nonboard top capture"**: board-less top camera (look-at, no PnP), white paper ground, translucent white square pot, orange vermiculite, framing plant ≈ 0.66 of side, render ≥ 880 px; plant model unchanged. Becomes the C6-top baseline. | Claude Code (Kaggle render) | measured pot size/colour, camera height/zoom of the nonboard captures (user or from photos) |
| 3 | cell T1 leaflet count per compound to real (+ margin serration/lobes) | Claude Code | real count rule (F.6 user value 11–13 per compound) |
| 4 | cell T2 second-order + small intercalary leaflets (also gives `leaf2` GT) | Claude Code | — |
| 5 | cell T3 shoot bundle mesh (folded young leaflets) instead of a sphere | Claude Code | — |
| 6 | cell T4 plant age/size toward the real plants (longer rachis, more compounds) | Claude Code | real compound count per plant |

Order rationale: the judge never saw a board, so capture (T0) confounds every structure cell — it goes first and
becomes the new baseline; structure cells are then single-factor deltas against T0. Stop rule per cell: keep a factor
only if its C6-top delta exceeds the noise floor; label the result "realism not achieved" until the gate threshold
(to be declared with the user after step 1) is met.

## 4. Not changed by this plan
The old C6 column and its frozen detector; the side-view set; `tomato_top_nonboard` itself (never trained on
synthetic); real-photo projects stay real-only.
