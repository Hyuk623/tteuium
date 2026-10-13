# P1 inventory — photos → current plant state → canopy placement (2026-10-11)

Author: Claude Code. Work order P1.0 of `handoff/CLAUDE_CODE_CLI_PROMPT_P1_PHOTO_GEOMETRY_2026-10-11.md`.
Every classification below cites a file:function or an output path that exists on disk. Counts were
measured (`python -m tomato3d.cli.run_p1 inventory` → `build/p1_inventory_20261011.json`), not recalled.

Classes: **executed** (ran in this session on real or fixture data, output named) ·
**implemented-unverified** (code + unit tests, never run on the data it is for) ·
**specification-only** · **absent** · **scientifically-unresolved** (blocked by a human decision on hold).

## 1. Corrections to the prompt's asset table (§2)

| Prompt says | On disk |
|---|---|
| `tomato3d/synth/compound_leaf.py` has `build_compound(..., fixed=)` with a whitelist | **No `fixed=` argument and no whitelist exist** (`compound_leaf.py:205` signature `build_compound(cfg, compound, contours, seed, plant_id)`). The completion adapter therefore uses pre-generated compounds (see P1.7) instead of pinned re-generation. |
| R.1 side set provides P0–P3 / α / θ | **No P0–P3 field is stored anywhere.** Points are derived from `plant_graph.json` `interiors.<id>.rachis_points_mm` + leaflet `rachis_station_mm` (`tomato3d/state/fixture_truth.py::compound_points`). |
| C6 detector is "synthetic-trained" | `full_final_all.pt` (sha256 `609fd7ae…`) is **organ detector v4, trained on reviewed masks of the real board-era plants dwt_01–04**; AP50 0.28 is its score *on synthetic scenes*. Proposal label used: `detector_status = unvalidated_on_boardfree_top` (`tomato3d/state/schema.py::DETECTOR_STATUSES`). |
| `real_eval/` holds the 52 real side photos | `build/sideprop_20261009_01/real_eval/` holds only the split (`eval_split.csv`, 16 eval / 36 train-pool) and the labeling guide. The images are JPG conversions in `build/roboflow_upload_20261009/side_views/` (52) and `top_level_views/` (13 top + 52 level). |
| `_08_08` is a render run | `build/synthetic_dwarf_tomato_20261008_08/` contains only `P_contract.json` — nothing rendered. |
| `phynotype2/` | Absent at its recorded path (`ls phynotype2` → not found). The tracker is in `tomato3d/track/link.py`; nothing was recreated there. |

## 2. Render runs present on disk (measured)

| Run / cell | Scenes (DONE) | Views | rgb.png | Notes |
|---|---|---|---|---|
| `synthetic_dwarf_tomato_20261005_01`, `_02` | 5 / 5 each | 60 | 60 | pilot, v2 |
| `_20261005_03` top, B4a, B5a, B6 | 5 each | 60 | 60 | |
| `_20261005_03` B2, B5b | 5 each | 60 | **0** | not rendered |
| `_20261006_04` | 5 | 60 | 60 | B5c |
| `_20261008_06` G2-0 / G2-a / G2-b | 15 each | 180 | 180 | |
| `_20261008_07` N-delight | 15 | 180 | 180 | |
| **`_20261008_07` O-mature** | **15** | **180** (150 ring + 30 top, 2 top views/scene, elevation 82–89°) | 180 | P1 top fixtures; per-leaflet `visible_mask.png` (uint16 instance ids) + `amodal/*.png`; plant-local meshes in `plant_graph.json` |
| **`sideprop_20261009_01`** (R.1) | **150 / 150** | 600 | **200** (batch a, scenes 0000–0049) | b/c not on disk; P1.6 uses only the 50 finalized scenes |
| `_20261008_08` | 0 | 0 | 0 | `P_contract.json` only |

Real inputs: 13 sessions `data/raw/dwt_101…113/dwt_1xx_gen_20261005/` × 9 HEIC = 117 photos (1 top, 4 side,
4 level each), all sha256 matching `generator_capture.csv`.

## 3. Feature inventory

| # | P1 feature | Class | Evidence |
|---|---|---|---|
| 1 | Capture rows for real board-free photos (path + sha256, capture time, lights-on/scale/rotation `unavailable`) | **executed (real)** | `tomato3d/state/ingest.py::real_capture_rows`; `build/p1_state_20261011_02/captures.csv` (117 rows) |
| 2 | Stage-1 board pose / silhouettes | implemented (Stage 1, 261 tests) — **not used**: board-free product line; silhouettes blocked by the unmeasured scale block | `handoff/STAGE1_IMPLEMENTATION_RESULT_2026-10-11.md` §6 |
| 3 | Physical scale for board-free photos (pot rim, ruler) | **absent (input)** — `pot_rim_inner_diameter_mm` never measured; `tomato3d/synth/ruler.py` exists but its scale was not adopted (I.4) | `audit_gaps.csv` item `scale` |
| 4 | Pot centre + rotation registration (phynotype2 W1 `fit_rim`) | **absent** | no implementation; real `rotation_status = unavailable` |
| 5 | Lights-on clock → `time_since_lights_on_min` | **absent (input)** — `lights_on_clock_time: null` | `data/records/env_light_20261010/env_light_20261010.json` |
| 6 | Product top detector `tomato_top_nonboard` | **absent** — Roboflow `dwt_top_seg_bbox` has 0 images (DETECTOR_POLICY) | — |
| 7 | C6 detector proposals on real top photos | **executed (real, flagged)** — 231 boxes on 13 tops, `review_state = unreviewed`, never tracked | `ingest.py::run_detector`, `proposal_rows`; `build/p1_state_20261011_02/observations/detector_proposals.json` |
| 8 | Human COCO boxes/polygons import | **implemented-unverified** (tests only — no human labels exist for dwt_1xx) | `ingest.py::import_coco`; `tests/test_state_ingest.py` |
| 9 | SAM masks from boxes | available in `tools/leaflet_segmenter.py::propose` (tuned config) — **not invoked**: no human prompts exist | — |
| 10 | Synthetic GT observations (top) | **executed (fixture)** | `fixture_truth.py::observe_top`, `observe_rendered_view`; `build/p1_state_20261011_01/observations/` |
| 11 | Truth MTG / four area kinds / truth surfaces | **executed (fixture)** | `fixture_truth.py::truth_mtg`, `truth_area_rows`, `truth_surfaces`; `…_01/truth/` |
| 12 | Compound tracker (6 states, proposed/confirmed, absence ≠ removal, split/merge suspects) | **executed (fixture)**; real `unavailable` (one capture per plant, no masks) | `tomato3d/track/link.py::track_plant`; `…_01/identity_manifest.csv`, `events.csv` |
| 13 | Terminal leaflet carried by explicit membership | **executed (fixture)** | `identity_manifest.csv` rows `<track>/T` |
| 14 | Human decisions (same / different / occluded / removal_confirmed) | **implemented-unverified** (tests) — no decision file exists | `link.py::load_decisions`; `tests/test_track_link.py` |
| 15 | `removal_confirmed` from records | implemented; **unreachable** — `data/records/manual_events.csv` absent | Stage-2 spec item f |
| 16 | Structure update (snapshot per capture, no promotion, unresolved accounting) | **executed (fixture)**; real → Plant/Axis rows only | `tomato3d/state/update.py::build_snapshot`; `…_01/mtg_vertices.csv`, `unresolved.csv` |
| 17 | Rank anchoring A1.1 | **executed (fixture truth)**; observation path `unavailable` (no heights from top view) | `update.py::anchor_ranks` |
| 18 | Side-view A2 geometry from P0..Pm points | **executed (fixture, 50 R.1 scenes)**; real `unavailable` (no human points) | `tomato3d/state/sidegeom.py`; `build/p1_side_validation_20261011/` |
| 19 | Blade-azimuth quadrant from direction class + view azimuth | **executed (fixture)**: exact 1073/1073 | `sideview.py::camera_relative_to_quadrant` via `sidegeom.validate_scene` |
| 20 | Side ↔ top cross-view association | **absent** for real; fixture join through the truth join, flagged | `package.py::_side_join` |
| 21 | Optical surfaces from truth | **executed (fixture)**, `supported` | `optical.py::export_truth` |
| 22 | Conditional completion constrained by 2-D masks | **executed (fixture)** via a pool-donor adapter (rotate + uniform scale + coverage check); `build_compound` not callable in the project env (L-Py) | `optical.py::complete_compound`; `…_01/completion_report.csv` (5 kept / 9 rejected) |
| 23 | Board-free 3-D (Q2) | **absent** | real optical readiness `unavailable` |
| 24 | Canopy placement (slot → rigid transform), duplicates, other-variety flag | **executed (fixture)**; real blocked (`plant_id ↔ slot` empty: 0/24) | `tomato3d/state/canopy.py`; `…_01/canopy_placement.json`, `canopy_merge_check.json` |
| 25 | P2 dry-read (schema only) | **executed** both packages | `package.py::p2_dry_read`; also Codex `tools/tomato_fsp_io.py::audit_p1_package` → fixture_ready true / real_ready false |
| 26 | Deterministic replay + stale invalidation | **executed** both packages (byte-identical) | `package.py::replay`, `validate` |
| 27 | Display viewer | **executed** | `…_01/viewer/index.html` |
| 28 | Blade curl / rugosity | **scientifically-unresolved** (MTG 8.3 on hold) — no column; validator rejects one | `schema.py::check_no_on_hold_fields` |
| 29 | Flat/bent θ thresholds | **scientifically-unresolved** (MTG 8.4 on hold); `rachis_bend_type` human label only | `schema.py::check_mtg_rows` |
| 30 | Azimuth prior for association | **scientifically-unresolved** (MTG 8.5 open) — none used | `link.py` docstring |
| 31 | Persistent ids for lateral leaflets | out of phynotype2 scope — anonymous observations only | phynotype2 spec §1 |
| 32 | `tools/phyllotaxis_fit.py` (A2 12.5 consumer) | **absent** (planned) | — |
| 33 | Historical photo-derived 3-D `build/plant3d_regroup_20261004_01/` | diagnostic only, not a P1 input | — |


## Addendum 2026-10-12 — generator caveat

Several synthetic-fixture numbers in this document are **generator-relative, not plant-verified**: the O-mature generator has leaflet L/W 1.19 (measured 1.4–1.7, 16 % inside) and 6–8 compounds per plant (real 4–5). Which numbers are affected and which appear little affected (A3 side angles — unverified): `handoff/P1_GENERATOR_CAVEAT_2026-10-12.md`.
