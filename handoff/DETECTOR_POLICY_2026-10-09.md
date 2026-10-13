# Standing policy: YOLO detector series (2026-10-09, user_stated)

**User instruction 2026-10-09: "앞으로 yolo모델은 tomato_top_nonboard 시리즈 사용" — from now on, the YOLO
model is the `tomato_top_nonboard` series.**

As of this date no weights, folder or LOG entry by that name exist in the repository, so the series is
external or upcoming (Kaggle naming style suggests a training series; the name suggests top views without the
ChArUco board — the 2x-zoom board-less capture thread). This policy says how the instruction is applied without
breaking the measurement discipline.

## Scope split

1. **Product, labeling, prelabeling, K (box fusion), future captures: switch to `tomato_top_nonboard` as soon
   as its weights are in the repo** — this is the user's call and needs nothing further, except that the
   weights file and its sha256 are recorded in LOG on arrival.

2. **C6 (the realism gate's judge): no silent swap.** Every C6 row to date is measured by the frozen
   `full_final_all.pt` (609f…), and in-flight cells (N/O, and P when it runs) are CONTRACTED to it — they
   finish under the contracted instrument. The new series becomes the C6 judge only through a declared
   instrument change:
   - its **provenance is verified first**: trained on real photos only, never on or tuned against synthetic
     (the freeze rule that makes C6 mean anything);
   - its sha256 is pinned and the training-set plant list recorded (for held-out scoring the LOPO convention
     needs an equivalent);
   - **one dual-scored re-baseline**: the current baseline cell (G2-0, or N if it supersedes) and the real
     reference set are scored under BOTH detectors, side by side, and the new numbers start a new column —
     old rows are never rewritten;
   - **the view-domain question is answered before adoption**: if the series is top-view-only, it cannot judge
     the 10 ring views, and "C6 under tomato_top_nonboard" is a DIFFERENT, narrower gate (top views only) —
     that is a redefinition to declare, not a drift to slip into.

3. Until the weights exist, nothing changes in running work.

## Open points for the user

- Where does the series live (Kaggle dataset/kernel name, or not yet trained)?
- Is it top-view-only, and was any synthetic image involved in training?

---

## Update 2026-10-09 (later same day): open points partially answered

**User answer:** the series is a **Roboflow self-trained labeling model, top-view-only bbox**
("로보플로우 자체 학습 라벨링 모델, top뷰 전용 bbox").

Consequences, applied to the scope split above:
- Top-view-only is now CONFIRMED → clause 2, last bullet is active: if this series ever judges C6, that is a
  **declared gate redefinition** to top views only. It cannot score the 10 ring views. In-flight N/O/P stay on
  the frozen `full_final_all.pt` as contracted.
- "Labeling model" matches scope 1 (product/labeling/prelabeling/K) — that switch happens on arrival of
  weights, as already written.

**API workspace check (2026-10-09, via Roboflow API with the user's own keys; keys live in the user's uploads
file, not recorded here):**
- Workspace 드워프토마토/홈팜 (`-ndul9`), 3 instance-segmentation projects:
  - `dwt_top_seg_bbox` — the only top project; **empty: 0 images, 0 versions** (created 2026-09-20);
  - `tom_middle_seg_bbox` — 31 images, 3 versions; classes sub_stem/shoot/leaflet/compond_leaf/main_stem;
  - `tom_side_seg_bbox` — 31 images, 4 versions; classes growth_shoot/compound_leaves/main_stem/sub_stem/leaflet.
- Workspace 알로카시아 (`s-workspace-br86f`): canopy-bbox1 (empty), canopy seg (29), "Find old, leaf, and
  others" (175 images, 13 versions), tom_seg (empty), tom_seg1 (1 image). No tomato-top project.
- **No project or model named `tomato_top_nonboard` exists in either workspace**, and no file by that name was
  found under config/, runs/ or tools/ locally.

**Reading:** the series does not exist yet as a trained model. The likely home is `dwt_top_seg_bbox`
(top-view project, currently an empty shell awaiting labels). The provenance question (synthetic in training)
therefore cannot be checked yet — the two populated projects hold 31 real photos each, which is consistent
with real-only, but the verdict applies to the actual training set of the actual weights when they exist.

**Still open for the user:** confirm that `tomato_top_nonboard` = the model to be trained from
`dwt_top_seg_bbox` (or name the third location if it lives elsewhere, e.g. another Roboflow account or a
Kaggle series).

---

## Side-view labeling policy (user decided 2026-10-09 evening)

**Granularity:** side-view photos are labeled at COMPOUND-LEAF level, not leaflet level.
Classes: compound boxes + main_stem + growth_shoot; individual leaflets only where clearly separable
(optional). Rationale: leaflet boxes in side views are inconsistent even for humans (the I.3 review:
all 118 rejections were box errors), and the pipeline consumes side views at compound level
(silhouette, attachment height, rachis elevation); leaflet instancing belongs to top/level views.

**Direction attribute — terminal-leaflet facing, 4 classes:**
- TRAINING label is CAMERA-RELATIVE (visual cue and label stay 1:1):
  `cl_left` / `cl_right` / `cl_toward` / `cl_away` (where the terminal leaflet points relative to the
  camera). `cl_toward` vs `cl_away` is the visually hard pair — report per-class accuracy, and if that
  pair dominates the confusion, fall back to a declared 3-class merge.
- REPORTED/STORED value is the ABSOLUTE clockwise quadrant 1-4 in plant coordinates, derived in
  post-processing: quadrant = f(camera-relative class, recorded view azimuth 0/90/180/270). The model
  never learns the absolute label directly.
- Human labels on real photos get a 5th option `unclear`; evaluation runs on the clear subset with the
  unclear fraction reported alongside.

**Synthetic images in training — allowed under all of:**
1. Scenes from the O-mature cell or later ONLY (compound size distribution before O is known-wrong:
   rank ratio 1.73 vs real 1.0-1.2), and only after the O analysis is accepted.
2. Auto direction labels come from generator azimuth minus camera azimuth; samples within 10 deg of a
   bin boundary are EXCLUDED from training (exact angles are known, so exclusion is clean).
3. Pre-registered eval: a synthetic-including model must beat the real-only baseline on a REAL held-out
   side-photo set (mAP50), or it is dropped (the PlantMDE lesson: low-fidelity synthetic can hurt).
4. Any detector with synthetic in its training set carries a `_synmix` name suffix and is PERMANENTLY
   barred from judging C6 (freeze rule). Product/labeling use only.
5. Synthetic images are never uploaded into the real-photo Roboflow projects (tom_side_seg_bbox stays
   real-only); if Roboflow self-training is used for the synmix model, it gets its own separate project.

## Status update 2026-10-12 (Claude, verified in the Roboflow UI)

`tomato_top_nonboard` **now exists** in workspace 드워프토마토/홈팜 (`-ndul9`), Object Detection, 49 images,
last edited 2026-10-12. The 2026-10-09 finding ("no project or model by that name exists") is superseded.

Classes and instance counts, exactly the user's 2026-10-12 class set:
`compond_leaf` 66 · `leaf` 293 · `leaf2` 81 · `terminal_leaf` 67 · `truss` 13 · `shoot` 8,
plus a stray auto-named class `tomato-top-nonboard` with **0** instances — delete it so it cannot appear as a
phantom class in exports.

Fine-tuned models (5): `tomato_top_nonboard-4-rfdetr-2xlarge-t1` (2026-10-12, valid-set **mAP 68.4 %**),
`-3-` (2026-10-09, 41.5 %), `-2-` (2026-10-09, 48.1 %), `-1-rfdetr-2xlarge-t2` (2026-10-08, 38.3 %),
`-1-yolo26n-t1` (2026-10-08, no metrics).

A sibling project `tomato_side_nonboard` exists as well: 168 images, **0 models**, last edited 2026-10-09.
The older `seg_bbox` folder still holds the three 2026-09 projects.

Cautions carried forward, not resolved by this check:
- 49 images is a small set and the reported mAP is that dataset's own valid split, **not** a pre-registered
  real held-out evaluation. The C6 / R.5 rule (real-only held-out eval before any synthetic-mixed claim) stands.
- Class imbalance is severe (`shoot` 8 and `truss` 13 against `leaf` 293); the rare classes are not yet usable.
- `truss` instances come from REAL photos only — the synthetic generator still contains no truss geometry.
