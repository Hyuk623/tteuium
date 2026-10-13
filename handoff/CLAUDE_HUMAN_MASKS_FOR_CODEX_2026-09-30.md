# Human masking and review results — where they are and how to use them (Claude -> Codex, 2026-09-30)

User request: link everything the user masked, selected and decided by hand to Codex's work.
Everything below was produced by the person, not a model, unless marked. Read-only for both agents: never edit these files in place; derive new outputs.

## 1. Rules that come with the data

- **Human wins.** A human decision always overrides a model answer. Items with `review_source` `auto` or `auto_model` are model answers, not human ones. They exist only in auto runs (`build/auto_*`), never in the four batches below. They must never become training labels or references.
- **Newest export only.** Each batch has several `exports/accepted_*` folders; the newest is authoritative. `tools.organ_detector_dataset.plants_from_config()` and `tools.leaflet_obb_dataset.exports_from_config()` already select it.
- **Coordinates** are original-image pixels (3024 x 3024 for these captures); boxes use pixel edges. Masks are full-resolution PNGs, so no transform is needed.
- **Evaluation protocol for your instance workflow is unchanged.** dwt_01 is development and dwt_02 is frozen evaluation. dwt_03/04 must not silently become evaluation data (your CODEX_INSTANCE_IMPORT_SCOPE_FIX).
- **Photo-level observations.** One physical leaflet appears in several photos as several observations. Cross-view identity is a separate human decision (section 4).
- All values stay diagnostic: `validated_metric=false`, `suitable_for_ppfd=false`.

## 2. Leaflet masks the person accepted (1,163) and rejected (118)

| Plant | Newest accepted export (sha256 prefix of accepted.json) | Accepted | Hand-edited | Rejected (reason) |
|---|---|---|---|---|
| dwt_01 | `build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260929_092627_faeb15` (cd62f6e7f91c439e) | 268 | 268 | 24 (box misses leaf 15, false positive 4, duplicate box 5) |
| dwt_02 | `build/leaflet_mask_batch_20260922/dwt_02/exports/accepted_20260929_092727_139059` (fea37954d7157efc) | 248 | 235 | 37 (22 / 4 / 11) |
| dwt_03 | `build/leaflet_mask_batch_20260925_tuned/dwt_03/exports/accepted_20260929_092816_35b47e` (b4ff880d129eebed) | 278 | 262 | 18 (7 / 3 / 8) |
| dwt_04 | `build/leaflet_mask_batch_20260925_tuned/dwt_04/exports/accepted_20260929_092913_25d191` (31e281d14ce36084) | 369 | 338 | 39 (12 / 2 / 25) |

- `accepted.json` holds one `observations[]` entry per mask. The fields you need are:
  - `id`, `image_file`, `mask_file` (PNG next to it, same size as the photo), `prompts.box_px` (the box SAM was given), `review` (`accepted_by_user`), `changed` (edited by hand: sensitivity, candidate, brush or rings), `visibility`, `history` (timed actions), `rings` (outline in original px).
- Rejected items and their reasons are in `<batch>/items/<id>.json`: `review='rejected'`, `reject_reason`. Occluded masks were accepted as `visibility='partial'` rather than rejected. A rejection says the draft was wrong; it does not give a correct mask.
- Photos: `<capture>/edit_session/capture.json` -> `frames[].image_path` (relative to `edit_session`). The captures are `build/new_captures_20260920/dwt_01|dwt_02` and `build/new_captures_20260921/dwt_03|dwt_04`.

## 3. Organ polygons and boxes the person drew (Roboflow, mapped to original pixels)

| Plant | File (sha256 prefix) | leaflet / compound / main stem / petiole / growth shoot |
|---|---|---|
| dwt_01 | `build/dwt_01_02_3d_20260922/dwt_01/labels/seed_with_imports.backup.json` (488a8a98ced61321) | 292 / 49 / 12 / 27 / 8 |
| dwt_02 | `build/dwt_01_02_3d_20260922/dwt_02/labels/seed_with_imports.backup.json` (28574c08ba522811) | 285 / 41 / 15 / 32 / 15 |
| dwt_03 | `build/dwt_03_04_3d_20260922/dwt_03/seed_with_imports.backup.json` (8b601041d9dd5930) | 296 / 52 / 17 / 45 / 22 |
| dwt_04 | `build/dwt_03_04_3d_20260922/dwt_04/seed_with_imports.backup.json` (ab6034a4056c10be) | 408 / 68 / 11 / 31 / 16 |

- Path inside the file: `variants.__all__.membership.detections[image_file][]`, with `class_name` (`leaflet`, `compoundleaves`, `main-stem`, `sub-stem`, `growth-shoot`), `bbox` (x/y min/max px) and `rings` (polygons in original px).
- Leaflet and compound entries are boxes (5-point rings). Stem and petiole entries are real outlines.
- **Caveat (measured 09-30, tools/stem_thickness.py):** stem polygons mark the VISIBLE part. Pieces hidden by leaves read narrow, and some polygons include roots at the soil or a petiole base. Do not use a stem polygon's width as the stem width without the steady-width check that tool applies.
- No compound box was ever drawn on the top views (01, 03).

## 4. Cross-view decisions (same / different leaflet across photos) and names

- Loader: `tools.cross_view_identity_import.load_decisions(paths)`; the newest `decided_at` wins per question.
- Sources per plant:
  - `decisions` folders in `tools/plant_pipeline_plants.json` (dwt_01 review_db)
  - `C:/Users/sho36/Downloads/cross_view_decisions_<plant>_*.json` (dwt_01 2, dwt_02 3, dwt_03 3, dwt_04 1 files)
- Match answers: 142 (116 same, 26 different). Confirmed leaflets: 7 / 17 / 14 / 11.
- Open conflicts remain in dwt_02 (a373-a156 and a37<->a174); see `<run>/CONFLICTS_REVIEW.html`.
- Compound names: `C:/Users/sho36/Downloads/human_checks_*.json` (4 files). All four plants are named by the person. dwt_01 and dwt_03 top region = `growing_leaf` (user decision 09-29, it is the growth record's unfolding L04).
- Growth records (counts, unfolding leaf): the `growth` paths in `tools/plant_pipeline_plants.json`.

## 5. Other human-made material

- Rejection reasons page `build/reject_reasons_20260927/review.html`; saved answers: `Downloads/reject_reasons_*.json` (all 125 answered).
- The "토마토 작은잎 표시기" artifact (https://claude.ai/artifact/HEKuFH4sbesRBmne8e79aS) holds the person's clicked leaflet boundary points (tip = point 0, clockwise, per photo) in its artifact database. Codex cannot read it directly. Ask the user, and Claude will export it to CSV (`image_file, organ_id, leaflet_id, point_id, x_px, y_px, ...`). Its content was not inspected in this session.

## 6. Where Codex can use it now

| Codex work | Use |
|---|---|
| Preprocessing comparison (CLAUDE_SMOOTHING_COMPARISON, 14-photo phase) | Section 2 masks are the references; keep `accepted_by_user` only. Your pilot already does this. Add dwt_02 as the frozen check if you extend it. |
| Instance workflow / S6 (your scope fix) | Section 2 masks + section 4 confirmed identities. dwt_01 dev, dwt_02 frozen evaluation. |
| Leaf surface Phase 3 (CLAUDE_LEAF_SURFACE_OPTIONS) | Visible outlines = section 2 masks. Physical point correspondences = section 5 clicked points (after export) + section 4 identities. |
| Midrib review (tools/midrib_flow.py, Claude 09-30) | `build/midrib_flow_20260930/midribs.json`: 51 proposed midrib polylines in original px for dwt_01 views 11/18/24/25 (SG5 mask, original-pixel Gaussian ridge). The reference masks are section 2. Proposals only; a person must accept them before any 3D use. |
| Training (Claude, Kaggle) | Already consumed: organ v4, SAM v5, OBB v5, decision models. Held-out models for every plant are saved (build/leaflets5_20260929, build/organ_detector_v4_20260929). |

Quick loader (read-only):

```python
from pathlib import Path
from tools.leaf_light.common import read_json
cfg = read_json(Path('tools/plant_pipeline_plants.json'))['plants']
for plant, pc in cfg.items():
    exp = sorted((Path(pc['batch']) / 'exports').glob('accepted_*'))[-1]
    for o in read_json(exp / 'accepted.json')['observations']:
        if o['review'] == 'accepted_by_user':
            mask_png = exp / o['mask_file']           # full-resolution, original pixels
            photo = Path(pc['capture']) / 'edit_session' / 'images' / o['image_file']
```
