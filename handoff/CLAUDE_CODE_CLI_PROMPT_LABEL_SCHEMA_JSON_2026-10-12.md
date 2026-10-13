# Claude Code — one label class schema + JSON label export for the synthetic sets (2026-10-12)

Implementer: Claude Code (owns `tomato3d/synth/`, `tomato3d/state/`, `tests/`). User requests of 2026-10-12.
Side views are already done by hand and must not be regenerated — see §2.

## 0. Read first
`CONVENTIONS.md`, last 40 LOG lines, `handoff/DETECTOR_POLICY_2026-10-09.md`,
`handoff/MTG_CONVENTION_2026-10-10.md` (A1/A2/§13 + the new axes amendment),
claude.ai doc `정의집_토마토_2026-10-11` (§1 names, §1-1 axes/shoot),
`build/sideprop_20261009_01/labels_json/side_labels_compound_v1.json` (already written — the format to follow).

## 1. The class set (user decision 2026-10-12, normative)
Keep the user's spelling exactly, including `compond_leaf`.

| id | name | 한국어 | notes |
|---|---|---|---|
| 0 | `compond_leaf` | 복엽 | whole compound leaf |
| 1 | `leaf` | 소엽 (측소엽) | first-order lateral leaflet |
| 2 | `leaf2` | 소소엽 | second-order leaflet (MTG tag `S1`) **and** intercalary leaflet (MTG tag `I1`) — see below |
| 3 | `shoot` | 신엽 묶음 | unexpanded apex bundle; `shoot′`/`shoot″` on side shoots are the same class, distinguished by the `axis` attribute |
| 4 | `terminal_leaf` | 정소엽 | terminal leaflet — never also labeled `leaf` |
| 5 | `truss` | 화방 | see §4: no synthetic instances exist |

**Intercalary leaflet (`I1`, 사이 소엽) → class `leaf2`** (user decision 2026-10-12). So `leaf2` covers both
second-order leaflets (MTG tag `S1`) and intercalary leaflets (MTG tag `I1`). The MTG tags themselves are
unchanged — `I1` stays `I1` in the structure records; only the detector label class is shared. Put the MTG tag
in the `tag` attribute so the two can always be separated again.
Per-instance attributes, never extra classes: `axis` (`M`/`S1`…), `rank`, `compound_id`, leaflet `tag`
(`T`/`P1L`/`I1`/`S1`), `direction` (side views only), `vis_frac`.

## 2. Side views — DO NOT re-render or re-label
User decision: **side views are labeled at compound level only.** This is already produced:
`build/sideprop_20261009_01/labels_json/side_labels_compound_v1.json` (600 images, 4,017 `compond_leaf`
annotations; `main_stem` 600 and `growth_shoot` 597 dropped from the source COCO; the 4 camera-relative
direction classes kept as the `direction` attribute with `direction_status` = `clear` | `unclear_boundary_band`).
Your only job here: verify it against `synside_coco.json` + `R2_label_summary.json` (counts, bbox identity,
quadrant consistency) and report any mismatch. The original COCO and YOLO files stay as they are.

## 3. Top views — produce the JSON
Export, in the same schema (`"schema": "tomato-synth-labels-1"`, `view_type: "top"`), from the existing
top-view synthetic runs (locate them: `build/synthetic_dwarf_tomato_*`, O-mature config; report exactly which
run and how many scenes/views you used):
- one annotation per visible instance of classes 0–4 with its attributes from §1;
- `leaf` vs `terminal_leaf` taken from the generator's own tag, never from geometry heuristics;
- `leaf2` where the generator produced secondary leaflets (`S1`) or intercalary leaflets (`I1`), each keeping its own `tag`;
- occlusion: `vis_frac` per instance and an explicit `min_vis_frac` threshold recorded in the file header,
  not silently applied;
- `evidence: "synthetic ground truth"`, `counts_as_real_annotation: false`.
If a class cannot be exported from a given run, list it in `classes_absent` with the reason — never emit an
empty class as if it were observed-and-absent.

## 4. The truss gap — report, do not fake
Verified 2026-10-12: `tomato3d/synth/` contains no truss / inflorescence / flower code, so **no synthetic image
contains a truss** and class 5 will have zero instances in every exported file. `truss` does appear in
`tomato3d/io/schemas.py` and `tomato3d/state/*` (state layer), which is a different thing.
State this in the file header (`classes_absent`) and in the report. A truss detector can only be trained from
real photos; do not add trusses to the generator in this task.

## 5. Deliverables
- `build/labels_json_20261012/top_labels_v1.json` (+ the verification result for the side file).
- `handoff/LABEL_CLASS_SCHEMA_2026-10-12.md`: the §1 table, the side/top labeling rules, the truss gap, the
  intercalary-leaflet open item, and how these names map to the existing Roboflow projects
  (`dwt_top_seg_bbox`, `tom_side_seg_bbox`, `tom_middle_seg_bbox`) so human labeling uses the same names.
- A loader + schema test in `tests/` (class ids/names exact, no instance carries two classes, attributes typed).
- flow_map rows + LOG claim/result lines.

## 6. Out of scope
Re-rendering any synthetic set, adding trusses to the generator, training any detector, editing `tools/`,
`config/`, `data/records/`, `docs/`, or another session's claimed files.
