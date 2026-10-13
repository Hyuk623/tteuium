# Scope: human masks -> model improvement -> cross-view leaflet proposals (Claude, 2026-09-30)

Source prompt: `C:/Users/sho36/OneDrive/바탕 화면/CLAUDE_MASK_LEARNING_TO_MULTIVIEW_2026-09-30.md` (user).
Inputs: handoff/CLAUDE_HUMAN_MASKS_FOR_CODEX_2026-09-30.md.
This task implements code and prepares cloud training. It does not run a training job and does not push to GitHub.

## Split (isolated experiment; shared configs untouched)

| Plant | Role | Why |
|---|---|---|
| dwt_03, dwt_04 | train | the prompt's clean split |
| dwt_01 | development | thresholds / choices only (also the instance workflow's development plant) |
| dwt_02 | evaluation | never fitted: no supervised, pseudo-label, normalisation or matching fit |

The frozen manifest is `build/split_exp_20260930/manifest.json` (tools/split_experiment.py). It records:
- per-plant photo hashes and sizes, the newest accepted export with every mask hash, the organ-label hash, rejected drafts with reasons, and cross-view decision sources;
- counts: accepted 278/369/268/248, edited 262/338/268/235; visibility partial is 5 (dwt_04) and 2 (dwt_02), the rest unspecified.

**Disclosure:** dwt_02 was inspected while earlier methods were chosen (LOPO reports, conflict review). Results on it are a held-out-plant check, not an untouched final test.

## Lineage (why new baselines are needed)

No existing tomato checkpoint is valid for this split: every one saw dwt_01 or dwt_02 in training.
- organ v4, SAM v5 and OBB v5: final_all models and LOPO folds.
- decision models 20260929.

Valid start points are the public SAM 2.1 tiny (also the "unchanged checkpoint" of the prompted-mask comparison) and COCO YOLO11s-seg. COCO has no tomato classes, so an unchanged detector baseline does not exist.

## Work items

1. **4A supervised baseline (prepared Kaggle kernel, not pushed)**
   - Organ detector: YOLO11s-seg full arm on dwt_03+04, v4 recipe. Class-wise AP50, precision/recall at the production threshold and missed organs on dwt_01 (dev) and dwt_02 (eval).
   - SAM 2.1 tiny decoder: the unchanged checkpoint vs fine-tuned on dwt_03+04 accepted masks. Same box prompts, crop rule and candidate rule. IoU, Dice, boundary F-score, empty masks and split/merge on dwt_01 and dwt_02.
   - End-to-end detector -> SAM on dwt_01/dwt_02. Missed leaflets count as failures (IoU 0).
2. **4B semi-supervised: prepared, pending.** All 72 photos carry human labels, so there are no eligible unlabeled training photos.
   - Deliver: pseudo-label storage separate from human exports (model hash, image hash, transform, thresholds, reasons), geometric transform mapping for boxes/masks, the teacher-student policy (EMA teacher, weak/strong views, development-only thresholds, human override) and tests.
   - Not activated until the weak-supervision policy is recorded and agreed and unlabeled photos exist.
3. **5 cross-view proposals**
   - Frozen public DINOv2 (ViT-S/14) features of masked leaflet crops. No trained Re-ID: training identities are too few once dwt_02 is excluded (70 answered pairs, 3 plants).
   - Ranking evaluation on human same/different pairs; unresolved pairs are unknown, not negatives.
   - Per view-pair one-to-one assignment with an unmatched option; ties and conflicts go to review.
   - Integrated as an appearance score and reasons in the existing candidate review page. Physical leaflet IDs stay separate from observation IDs (existing identity import).
4. Completion handoff in English: code prepared / training executed / measured / pending human input.

## Out of scope

Midrib promotion, physical landmarks, depth, curvature, leaf area and PPFD. The 51 midrib polylines stay proposals.
