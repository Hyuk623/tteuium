# Claude Code CLI prompt — Addendum K: multi-view box fusion for SAM prompting (2026-10-08)

Paste the block below. Context for the person pasting: I.3 showed that ALL 118 rejections among the 1,281 real
SAM candidates were box errors (box_misses_leaf 56, duplicate_box 49, false_positive 13) and none were mask
errors — the bottleneck is box quality, not SAM. The user has decided (2026-10-08) to skip the GT-box vs
detector-box quantification and go straight to the one lever that uses this project's structural advantage:
**camera poses are measured by the ChArUco board, so detections can be transferred between views geometrically.**
Single-image cascades cannot do this; we can.

---

## Paste from here

Standing corrections: the detector (sha256 609dfae…) and SAM v5 (sha256 161b9c6…) are frozen instruments — no
retraining, no threshold change after a score is seen. C6 and C7 keep their exact current definitions (C6 = raw
single-image frozen detector; C7 = GT-box prompt). Fusion is a **product/labeling improvement measured beside the
gates, never inside them**. All fused outputs live under a `fused_` namespace and are never fed into a C-gate
number. Scenes (plants) are the independent unit of every reported number.

### What exists and is used as-is

- dwt_01–04 teacher sessions: multi-view photos with board poses, cached frozen-detector detections, and the
  1,163 human-accepted leaflet masks (the evaluation ground truth — nothing new to label).
- `calib/pose.py` poses. **Known caveat A7**: `solve_pose` has no per-frame reprojection gate and can report
  degenerate corner sets as solved. Do not fix A7 inside K (it is its own queued item); instead K.0 below screens
  the poses it consumes.

### K.0 — pose screening (prerequisite, read-only)

For every view used, reproject the board model with the stored pose and report the corner reprojection error.
Declare BEFORE looking at results: views above a stated error bound (write the bound into `K_contract.json`
first) are **excluded from fusion and listed**, not repaired. This protects K from A7 without touching A7.

### K.1 — 3-D anchors from multi-view detections (teacher geometry)

1. Match detections across views: a pair of boxes in two views may be the same leaflet only if their centre rays
   satisfy the epipolar constraint within a declared pixel band; break ties by ray–ray distance.
2. Triangulate matched detections into a 3-D anchor per leaflet (least-squares over ≥2 rays); reject anchors whose
   reprojection error into any member view exceeds a declared bound.
3. **Merge before adding**: anchors must absorb duplicate detections (the duplicate_box 49 class must go DOWN, and
   this is a declared falsification: if duplicate rate rises, K.1 has failed — report, do not tune it away).
4. Output per scene: `fused_anchors.json` (3-D points, member views, reprojection errors).

### K.2 — recovery: project anchors into views where the detector missed

For each anchor and each view with no matched detection: project the anchor, build a prior box from the anchor's
median projected box size in member views, prompt the frozen SAM with it (same 3-candidate, highest-score rule as
C7), and record the mask.

Report, per plant and pooled with scene-level bootstrap (I.1 method):

- **recovery recall**: share of GT leaflets unmatched by the raw detector in a view whose fused SAM mask reaches
  IoU ≥ 0.5 against that view's GT mask;
- **false-recovery rate**: fused masks with no GT leaflet (must stay below a bound declared in `K_contract.json`
  before any score is seen);
- the before/after per-view leaflet recall, beside the raw frozen-detector recall — labelled `fused_recall`, never
  replacing any existing number.

### K.3 — the two-view product variant (top + side)

The product has 2 views, so triangulation only covers leaflets detected in both. Implement and report separately:
a leaflet detected in exactly one view contributes a **ray**; intersect the ray with the plant's height interval
(from the session's own silhouette extent) to get a segment, project the segment into the other view as a search
band, and prompt SAM along it (declared number of prompts per band, fixed in the contract). Report K.3 with its
own recovery/false-recovery numbers — do not average it with K.2; the 36-view and 2-view regimes are different
products.

### Do not

- Do not touch C6/C7 definitions, the B1 GT rule, gate thresholds, or anything in
  `build/synthetic_dwarf_tomato_20261008_06/` (G.2 in flight — K is real-photo-side and independent).
- Do not retrain or re-tune the detector or SAM; do not adjust `conf`/`iou`/NMS after seeing K results — all
  operating points go into `K_contract.json` first.
- Do not repair poses, masks or GT rows (A7 stays queued; `data/records/` is human-owned).
- Do not report a pooled number without the per-plant table next to it.

Run folder: `build/box_fusion_20261008_01/` (`K_contract.json` written and logged BEFORE the first fusion run;
`K1_anchors_report.md`, `K2_recovery.csv`, `K3_twoview.csv`, `K_REPORT.md`). Record: `K` rows in `c6_steps.csv`
marked `diagnostic`, one line in `handoff/LOG.md`.
