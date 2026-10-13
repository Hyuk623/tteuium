# Label class schema — one class set for synthetic JSON and human labeling (2026-10-12)

Author: Claude Code. Source decisions: user, 2026-10-12 (recorded in LOG the same day). Executes
`handoff/CLAUDE_CODE_CLI_PROMPT_LABEL_SCHEMA_JSON_2026-10-12.md`.
Code: `tomato3d/synth/labels_json.py` (export, side verification, loader). Tests: `tests/test_labels_json.py`.
File schema id: `"schema": "tomato-synth-labels-1"`.

## 1. The class set (normative; spelling kept, including `compond_leaf`)

| id | name | 한국어 | what it is |
|---|---|---|---|
| 0 | `compond_leaf` | 복엽 | whole compound leaf: all its leaflets + rachis + petiolules |
| 1 | `leaf` | 소엽 (측소엽) | first-order lateral leaflet (MTG tags `P<i>L`/`P<i>R`) |
| 2 | `leaf2` | 소소엽 | second-order leaflet (MTG tag `S1`…) **and** intercalary leaflet (MTG tag `I1`…) |
| 3 | `shoot` | 신엽 묶음 | unexpanded apex bundle; `shoot′`/`shoot″` on side shoots are the same class, told apart by `axis` |
| 4 | `terminal_leaf` | 정소엽 | terminal leaflet (MTG tag `T`) — never also labeled `leaf` |
| 5 | `truss` | 화방 | truss — no synthetic instance exists (§4) |

Per-instance **attributes, never extra classes**: `axis` (`M`, `S1`, …), `rank`, `compound_id`, leaflet `tag`
(`T`/`P1L`/`I1`/`S1`), `direction` (side views only), `vis_frac`.

**Name collision to watch:** `tag = "S1"` is a second-order leaflet (MTG `SecondaryLeaflet`, §4 of the MTG
convention); `axis = "S1"` is side shoot 1 (MTG Amendment A4). They are different fields. Never infer one from
the other.

## 2. Labeling rules by view

### Side views — compound level only (user decision)
- One box per compound: class `compond_leaf`. No leaflet, stem or shoot boxes.
- Direction is the attribute `direction` ∈ `cl_left`/`cl_right`/`cl_toward`/`cl_away` (camera-relative, where the
  terminal leaflet points), with `direction_status` = `clear` | `unclear_boundary_band`. The absolute clockwise
  quadrant is derived afterwards from the view azimuth (`tomato3d.synth.sideview.camera_relative_to_quadrant`).
  Human labels on real photos use `unclear` for the boundary/ambiguous case.
- Synthetic file: `build/sideprop_20261009_01/labels_json/side_labels_compound_v1.json` (already written; not
  regenerated).

### Top views — every class
- `compond_leaf` box around the whole compound, plus one box per leaflet: `terminal_leaf` for `T`, `leaf` for
  `P*`, `leaf2` for `I*`/`S*`. A leaflet carries exactly one class.
- `shoot` box around the apex bundle; `axis` says which axis (`M` main stem, `S1`… side shoots).
- `truss` when one is visible (real photos only).
- Synthetic: leaflet class is read from the generator's own `kind`/`tag` in `leaflet_index.json`; a kind/tag
  disagreement raises instead of guessing. No geometry heuristic is used.

## 3. Synthetic files produced / checked

### Top: `build/labels_json_20261012/top_labels_v1.json`
- Source: `build/synthetic_dwarf_tomato_20261008_07/O-mature` (O-mature cell, generator `synth-stage1-0.2.0`),
  **15 scenes, 30 views** = every `view_kind == "top"` row of its `manifest.jsonl` (2 per scene, camera
  elevation 82.0–89.4°). The 150 ring views of the same scenes are **not** exported.
- 986 annotations: `compond_leaf` 203, `leaf` 557, `terminal_leaf` 193, `shoot` 30, `leaf2` 3 (all `I1`), `truss` 0.
- Inclusion: `visible_px >= 20` (`stage1_contract.json::min_visible_px` of the run). 108 instances below it are
  listed in `excluded_occluded` (leaf 43, leaf2 41, terminal_leaf 17, compond_leaf 7), not dropped silently.
- Occlusion: `vis_frac = visible_px / amodal_px` per instance (p10/p50/p90 = 0.148/0.662/0.995).
  Header `occlusion.min_vis_frac = 0.0`, `min_vis_frac_applied = false`: **no vis_frac rule has ever been declared
  for this run** (the Addendum B1 GT rule is `min_visible_px 49 + solidity 0.434`, for C6 only), so nothing is
  filtered by visibility fraction; a trainer that wants one sets it and records it.
- Compound and shoot masks: the run never stored them, so the mask layers (not RGB) were rasterised once more from
  `render_job/parts.npz` with the run's own camera geometry and rasteriser. The same pass recomputes the stored
  leaflet layer: **0 differing pixels over all 30 views** (7,864,320 px), so the reconstruction is the run's geometry.
- Header: `classes_absent = [truss]` with reason, `subtypes_absent = [leaf2/S1]`, `evidence = "synthetic ground
  truth"`, `counts_as_real_annotation = false`, source file sha256s, realism caveat (O-mature did not pass realism).

### Side: verification of the existing file — `build/labels_json_20261012/side_labels_compound_v1_verification.json`
Result **pass**. Checked against `synside_coco.json` and `R2_label_summary.json`:
- counts: 600 images = 600 COCO = 600 summary views; 150 scenes; 4,017 compound annotations = 4,017 COCO compound
  boxes (4 direction classes + `compound_unclear`) = summary `boxed_compounds`; dropped `main_stem` 600,
  `growth_shoot` 597 = COCO counts; `source_sha256` matches the COCO file.
- bbox identity: every annotation matches exactly one COCO box by (image, compound) with an identical box and
  identical delta/quadrant/vis_frac/visible_px/exclusion flags; no unmatched record either way.
- direction: counts equal the summary (right 799, toward 787, left 784, away 748); unclear 899 = summary
  `excluded_boundary_among_boxed`; every `direction` equals the bin of its own `delta_deg`.
- quadrant: converter == `quadrant_gt` on all **3,118** clear boxed compounds, 0 mismatches. The summary's 3,247 is
  not a discrepancy: R.2 ran its check over all 4,180 compound/view pairs outside the band, including occluded
  pairs that never got a box (3,247 − 3,118 = 129 such pairs).
- **Header gaps (not mismatches, file left unchanged):** the side file has no `classes_absent` field (so the
  absent `leaf`/`leaf2`/`shoot`/`terminal_leaf`/`truss` are absent by the compound-only rule, not stated) and no
  top-level `counts_as_real_annotation` key (it is stated only inside `evidence`). The loader reports these as
  gaps. Adding them means rewriting the side file — the prompt said not to; say if you want a `_v2` header.

## 4. Truss gap
`tomato3d/synth/` has no truss / inflorescence / flower code, so no synthetic image contains a truss, and class 5
has zero instances in every synthetic file (stated in `classes_absent`, never as an observed absence). `truss` in
`tomato3d/io/schemas.py` and `tomato3d/state/*` is the state layer, not the generator. **A truss detector can only
be trained from real photos.** Trusses were not added to the generator (out of scope).

## 5. Open items for the user

1. **Intercalary vs second-order leaflet inside `leaf2`.** Decided: both are `leaf2`, MTG tags unchanged, the tag is
   carried as an attribute. Still open:
   - Human labeling: if the labeling tool cannot hold a per-box attribute, the `I1`/`S1` distinction is lost for
     human labels. Choose: (a) accept the loss (class `leaf2` only), or (b) label as two temporary names merged into
     `leaf2` at export (e.g. `leaf2_i` / `leaf2_s`) — that would be a labeling-tool convention, not a new class.
   - Synthetic coverage: the generator makes no second-order leaflets at all, and intercalary leaflets are small
     (~8 mm): of 44 `I1` leaflet-views in the 30 top views, 41 are below 20 px. The top file has **3** `leaf2`
     instances — `leaf2` cannot be learned from this synthetic set; it depends on real labels.
2. **`main_stem` / `sub_stem` are not in the class set.** They exist in both populated Roboflow projects and were
   dropped from the synthetic side export. Decide whether human labeling keeps drawing them (outside this schema)
   or stops.
3. **Side-file header `_v2`** (§3) — only if wanted.
4. Ring views of O-mature (150, elevations 25.3–53.4°) are not exported. They are neither top nor side under the
   current rules; say if they should get their own `view_type`.

## 6. Mapping to the existing Roboflow projects (workspace 드워프토마토/홈팜)
Class lists are from the 2026-10-09 API check (`handoff/DETECTOR_POLICY_2026-10-09.md`); not re-queried today.

| this schema | `tom_middle_seg_bbox` (31 img) | `tom_side_seg_bbox` (31 img) | `dwt_top_seg_bbox` |
|---|---|---|---|
| `compond_leaf` | `compond_leaf` (same spelling) | `compound_leaves` → rename | empty project (0 images, 10-09): create the six names exactly as in §1 |
| `leaf` | part of `leaflet` → relabel | `leaflet` → not used (side = compound only) | — |
| `leaf2` | part of `leaflet` → relabel | — | — |
| `terminal_leaf` | part of `leaflet` → relabel | — | — |
| `shoot` | `shoot` | `growth_shoot` → rename (not used for side under the compound-only rule) | — |
| `truss` | none | none | — |
| (not in schema) | `main_stem`, `sub_stem` | `main_stem`, `sub_stem` | — |

`leaflet` cannot be split into `leaf` / `leaf2` / `terminal_leaf` automatically — it needs a human pass. Real-photo
projects stay real-only (detector policy: synthetic images are never uploaded into them).

## 7. Addendum (same day): the top-view detector exists — Roboflow `tomato_top_nonboard`
Checked 2026-10-12 via the Roboflow API (workspace 드워프토마토/홈팜, slug `-ndul9`; key from the user's uploads file,
not recorded). This is the `tomato_top_nonboard` series of `handoff/DETECTOR_POLICY_2026-10-09.md`; it is its **own
project**, not `dwt_top_seg_bbox` (which is still empty).
- Project: object-detection, created 2026-10-08, **public, CC BY 4.0**. Classes = this schema exactly
  (`compond_leaf` 66, `leaf` 293, `leaf2` 81, `terminal_leaf` 67, `shoot` 8, `truss` 13 annotations) plus Roboflow's
  default project class `tomato-top-nonboard` (0 annotations). 15 annotated images (train 10 / valid 2 / test 3),
  ~34 unannotated. Image names are all phone photos (`IMG_*.jpg`, `IMG_*.HEIC`, `top.heic`); no synthetic `rgb.png`
  — consistent with real-only training, but this is a filename check, not a provenance proof.
- Versions (all trained on Roboflow; weights live on Roboflow serverless, no local file / sha256):

| ver | date | model | input | mAP50 (valid) |
|---|---|---|---|---|
| 1 | 10-08 | yolo26n, from scratch | 640 | 0.175 |
| 2 | 10-09 | rfdetr-2xlarge | 640 | 0.481 |
| 3 | 10-09 | rfdetr-2xlarge | 640 | 0.415 |
| 4 | 10-12 | rfdetr-2xlarge (from v3 checkpoint) | 880, mosaic + gain aug | **0.684** |

- v4 per class, valid / test mAP50: compond_leaf 1.00 / 0.95, leaf 0.90 / 0.80, terminal_leaf 0.76 / 0.82,
  leaf2 0.68 / 0.38, shoot – / 0.75, truss 0.08 / 0.53; all 0.684 / 0.706. **Valid and test are 2 images each** —
  these numbers are very noisy; leaf2 and truss (few instances) cannot be judged from them.
- Endpoint `https://serverless.roboflow.com/tomato_top_nonboard/4`. Per the detector policy: usable now for
  labeling/prelabeling (scope 1); C6 judge only through a declared instrument change, top views only (scope 2).
