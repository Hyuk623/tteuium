# Addendum B to the synthetic dwarf tomato Stage 1 task: raise C6 (detector AP50 on synthetic)

Date: 2026-10-05 22:25 KST. Author: Claude (chat), for the running Claude Code CLI session. User decision: **target = C6**.
Applies on top of the Stage 1 prompt and Addendum A (A.1–A.4). Ownership rules unchanged (`tomato3d/synth/`, `tests/test_synth_*.py`, `build/` only; nothing in `tools/`, `config/`, `data/`, `pyproject.toml`).

## 0. Meaning of C6 (do not change)
C6 is a **realism gate**: the real-trained detector (`build/organ_detector_v4_20260929/kout_full/full_final_all.pt`, sha256 `609fd7ae…`) stays **frozen**. We raise C6 by making synthetic images closer to real photos, never by training or fine-tuning any model on synthetic data, never by changing the detector, its conf/iou/imgsz, or the AP50 code. Record the detector sha256 in every result.

## 1. Run folder and contract
- New run `build/synthetic_dwarf_tomato_20261005_03/`. `_01` and `_02` stay as recorded failures (read-only).
- Write `stage1_contract.json` for `_03` before any rendering. It keeps C1–C7 and the same thresholds. Add only the items in §3 that are declared in advance.
- Heavy work (real control, re-renders, SAM) runs on Kaggle (`dolgfish/tomato-synth-render`, 2×T4). Do not run native-resolution SAM or detector on the local PC (it ran out of memory last time). Locally: geometry, masks, post-processing, small evaluations only.

## 2. Steps — change one factor at a time, report C6 after each
Each step reports: AP50, max recall, recall by leaflet visible-area bin (<150, 150–500, 500–1500, >1500 px at the evaluated resolution), recall by visible fraction (<0.5, 0.5–0.9, >0.9), and false-positive count by predicted class. Same 5 pilot scenes × 12 views throughout, so steps are comparable; the full 100 scenes only after a step passes.

| Step | Change | Re-render? | Question it answers |
|---|---|---|---|
| B0 | **Real control on Kaggle**: run `scratch_real_control.py` logic on dwt_01 (held-out weights) at native 3024, 1536, 1024, 512 px. Also report the real leaflet visible-area distribution (p10/p50/p90) at each size | no | Ceiling of C6 on real photos, and how much resolution alone costs |
| B1 | **GT rule match**: compute the minimum area and visible-fraction distribution of human-labelled real leaflets (accepted exports); declare a synthetic GT filter that mimics that labelling (e.g. drop leaflet fragments the annotators would not label). Declare the rule in the contract **before** re-scoring; report C6 under the old and the new GT | no | Is recall deflated by synthetic GT containing fragments humans never label? |
| B2 | **Resolution/scale**: re-render the same 5 scenes on Kaggle so leaflet pixel size matches real photos at the detector's regime (pixels per mm equal to real rig photos; either full frame at real resolution or a plant-centred crop with the same px/mm) | yes (Kaggle) | Main hypothesis from the `_02` report |
| B3 | **Camera artifacts** (post-process only, on B2 output): defocus/motion blur, sensor noise, JPEG quality, white balance and exposure jitter, all with ranges measured from the real rig photos (store the measurement) | no | Gap from "too clean" renders |
| B4 | **Leaflet size toward the real median**: `_02` median visible leaflet area (151 px) sits at the real p10 (147). Generator 0.3: raise the leaflet scale so the synthetic median approaches the real p50; keep C1–C3 inside their ranges | yes | Leaflets still too small even after the v2 fix |
| B5 | **Leaf surface texture**: vein/serration/surface normal + albedo maps taken from real leaflet crops (reviewed masks only, `source` tagged) | yes | Smooth leaves read as not-leaflet |

Stop at the first step where C6 ≥ 0.59 and C7 ≥ 0.72; report and wait for the user before the 100-scene run.

## 3. Rules
- One factor per step; each step's config is hashed and saved before scoring.
- Thresholds are never changed after seeing results. A GT filter (B1) or a resolution choice (B2) is declared in the `_03` contract before scoring that step.
- If B0 shows the real C6 at the chosen resolution is itself below 0.59, stop and report: the threshold or resolution must be decided by the user, not tuned by you.
- Memory: Kaggle for anything at ≥1024 px with SAM; locally keep peak RAM < 6 GB (log it).

## 4. Report (`build/synthetic_dwarf_tomato_20261005_03/C6_REPORT.md` + `c6_steps.csv`)
`c6_steps.csv` columns: `step,factor,config_sha256,resolution_px,gt_rule,ap50,recall_max,recall_lt150,recall_150_500,recall_500_1500,recall_gt1500,recall_vis_lt05,recall_vis_05_09,recall_vis_gt09,fp_count,sam_median_iou,detector_sha256,kaggle_run_id`.
Korean 5-line summary in your reply: which step moved C6 most, current C6/C7, next decision for the user.

## Revision B.1 (2026-10-05 22:30 KST, user decision) — what the C3 "real range" actually is, and the counting sheet

**Correction to record in the `_03` contract.** The C3 real range 8–30 is **not** a leaflet count the user ever labelled. It is the number of SAM masks the user accepted per photo in the leaflet mask review (`review: accepted_by_user`), counted afterwards. Measured: dwt_01 = 268 leaflets over 14 photos (13/19/30 min/median/max), dwt_02 = 248 over 16 photos (8/16/20). Only 4 plants have exports. The accepted set states "accepted 2D visible regions only; no cross-view identity or depth confirmation", and `visibility` is null on every observation, so occlusion per leaflet is unknown.

Consequences, to apply:
1. **Restate C3 in the `_03` contract** as `median_accepted_leaflet_masks_per_photo` with `real_source: "count of user-accepted SAM masks, not an exhaustive leaflet count"`, and demote it to **`report_only`**. A synthetic median far outside 8–30 still gets flagged in the report as over-fragmentation, but it no longer gates.
2. **B1 becomes mandatory and symmetric.** Compute from the accepted masks (all 4 plants, latest export each): the distribution of `mask_area_px` rescaled to the evaluated resolution — report p1/p5/p10/p50. Declare the synthetic GT minimum visible area as the real **p5** (not the current flat 20 px) in the `_03` contract before scoring, and apply the identical rule to the synthetic GT. Report C6 under both the old 20 px rule and the new rule so the effect is separable.
3. **B1b — manual count sheet (user task, after B0).** The user will count visible leaflets by eye on the Addendum A photos. Order: run B0 first, report it, then generate the blank sheet and hand it to the user; do not block B2–B5 waiting for it.
   - Generate `build/synthetic_dwarf_tomato_20261005_03/leaflet_count_sheet.csv` with one row per photo for all 13 plants × 9 photos (117 rows), columns `plant_id,session_id,photo_file,photo_kind,counted_leaflets,counting_rule_version,counted_at,notes`, `counted_leaflets` blank.
   - Also write the counting rule the user is to follow into `leaflet_count_rule.md`, derived from the accepted-mask statistics in (2): the minimum apparent size and the maximum occlusion at which a leaflet still counts, each stated in plain terms the user can apply by eye (e.g. "count it if more than half of the leaflet blade is visible and it is at least as wide as the ruler's 1 mm tick at that distance"). Keep it to one screen.
   - When the filled sheet comes back, recompute the real C3 from it, compare with the accepted-mask count (expected: higher), and report both. Do **not** overwrite the `_03` contract after the fact; record the new number as `C3_manual` in the report.
