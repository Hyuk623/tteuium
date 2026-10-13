# P1 execution — photos → current plant state → canopy placement (2026-10-11)

Author: Claude Code. Implements `handoff/CLAUDE_CODE_CLI_PROMPT_P1_PHOTO_GEOMETRY_2026-10-11.md` (P1 only).
Korean companion: `handoff/P1_EXECUTION_2026-10-11_KO.md`. Inventory: `handoff/P1_INVENTORY_2026-10-11.md`.

## 0. Verdict, reported separately as asked

| Completion axis | Status | Evidence |
|---|---|---|
| **Observation reconstruction from real photos** | **Not achieved — `unavailable`.** Real captures are ingested and hashed, but no segment past ingest can run: no top-view masks (no top detector, no human labels), no scale, no rotation, no lights-on time, no side points, no plant↔slot table, no board-free 3-D. | `build/p1_state_20261011_02/` (`overall_status = partial`, CLI exit 3), `audit_gaps.csv` (156 rows, 12 named gaps × 13 plants) |
| **Interfaces** | **Implemented and validated.** Schema, validators, ingest, tracker, updater, side geometry, optical export, canopy placement, package writer, P2 dry-read, replay, CLI. 65 new tests. Codex's downstream reader `tools/tomato_fsp_io.py::audit_p1_package` accepts both packages (fixture_ready true / real_ready false with 247 named gaps). | `tomato3d/state/`, `tomato3d/track/link.py`, `tomato3d/cli/run_p1.py`, `tests/test_state_*.py`, `tests/test_track_link.py` |
| **Fixture engineering path** | **Executed** end to end (P1.3→P1.8) on 3 synthetic source plants, 5 instances (one duplicate, one other-variety), 3 time points; validates; replays byte-identically. **It is not photo reconstruction** (`counts_as_photo_reconstruction = false`). | `build/p1_state_20261011_01/` |

Full suite: **331 passed, 1 skipped** (before this work: 266 passed, 1 skipped; the skip is the missing optional
`openalea.lpy`, unchanged). Schema version **`p1_state_v1`**; code version **`p1code-2fc8f7aea4acab70`**
(sha256 over the 15 P1 source/config files, recorded per file in each manifest; no git repository here).

## 1. Files read (and absent)

Read: `CONVENTIONS.md`, `CLAUDE.md`, `AGENTS.md`, `../공통규약.md`, `handoff/LOG.md` (last 40+ lines, re-checked before
writing), `handoff/CLAUDE_P1_P2_P3_P4_END_TO_END_INTEGRATION_PROMPT_2026-10-11.md` (all), `handoff/MTG_CONVENTION_2026-10-10.md`
(§1–13 incl. A1/A2/§13), `handoff/CLAUDE_CODE_CLI_PROMPT_MTG_AMEND_2026-10-10.md` (A1 text),
`handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` (all + L1 + reconciliation + decision note),
`handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md` (all), `handoff/STAGE1_IMPLEMENTATION_RESULT_2026-10-11.md`,
`handoff/CROSS_STAGE_ISSUES_2026-10-11_KO.md`, `handoff/DETECTOR_POLICY_2026-10-09.md`, `handoff/CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md`
(P1 items), `handoff/R_SESSION_STATE_2026-10-10.md`, `handoff/OWNERSHIP_OVERRIDE_2026-10-11.md`; records (read-only):
`data/records/env_light_20261010/{env_light_20261010.json, plant_slot_light_ratio_20261010.csv, light_ratio_map_20261010.csv}`,
`data/records/plant_registry/{개체기록,기관측정}_MicroTom_20261010.xlsx` (openpyxl, read-only),
`data/records/compound_bend_types_20261010/compound_bend_examples_20261010.csv`. Consumer code read-only:
`tools/vtc_development_observation.py`, `tools/vtc_growth_io.py` (HEADERS), `tools/tomato_fsp_io.py`.

Absent: **`phynotype2/`** (not at its recorded path; not recreated — the phynotype2 §7 contract is implemented in
`tomato3d/track/link.py` + `tomato3d/state/`; if the human restores `phynotype2/` it should import from there).
`data/records/manual_events.csv`, `organ_label_map.csv` (so `removal_confirmed` stays unreachable from records).

## 2. What was built

```
tomato3d/state/schema.py          P1.1 column contracts, vocabularies, validators (P1SchemaError names the rule)
tomato3d/state/geometry.py        A1/A2 quantities (azimuth, elevation, insertion, alpha_i, theta, chord ratio), 2-D and 3-D
tomato3d/state/topraster.py       orthographic top rasteriser for fixtures (leaflet laminae, painter order)
tomato3d/state/fixture_truth.py   P1.2 scene -> truth MTG / areas / surfaces; observation-like view; controlled modifications
tomato3d/state/fixture_sequence.py declared capture sequences (rotation, removal, addition, occlusion, merge, split)
tomato3d/state/ingest.py          P1.3 real captures, COCO, detector proposals (flagged), mask packing
tomato3d/track/link.py            P1.4 tracker (stub opened; link_organs still raises - no input contract)
tomato3d/track/tracking_config_template.json   all-null phynotype2 section 9 config (real runs)
tomato3d/track/tracking_config_fixture.json    fixture-declared weights/thresholds (fixtures only; links stay proposed)
tomato3d/state/update.py          P1.5 snapshot, rank anchoring, areas, change log, unresolved, diurnal guard, candidate sub-MTG
tomato3d/state/sidegeom.py        P1.6 side-view geometry + validation against R.1 truth
tomato3d/state/optical.py         P1.7 located leaflet surfaces + readiness; pool-donor conditional completion
tomato3d/state/canopy.py          P1.8 slot -> rigid transform, merge/split, placement document
tomato3d/state/package.py         P1.9/P1.10 builders, coherent publish, manifest, validate, P2 dry-read, compare, replay
tomato3d/state/p1_config.json     fixture_declared / assumed_unmeasured constants (config/ is the human's)
tomato3d/cli/run_p1.py            P1.11 inventory | prepare | run | collect | compare-observation | replay | side-validate
tests/test_state_{schema,fixture_truth,update,sidegeom,canopy_optical,ingest,package}.py, tests/test_track_link.py (65 tests)
tests/fixtures/p1/                 compact copies of O-mature scene_0000/0001 + R.1 scene_0000 (sources hashed in SOURCES.json)
```

## 3. Commands run and exit codes (full log: `build/p1_cli_log_20261011.txt`)

```
python -X utf8 -m pytest -q                                                    331 passed, 1 skipped
python -X utf8 -m tomato3d.cli.run_p1 inventory --out build/p1_inventory_20261011.json                exit 0
python -X utf8 -m tomato3d.cli.run_p1 side-validate --out build/p1_side_validation_20261011           exit 0
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode fixture --out build/p1_state_20261011_01         exit 0
python -X utf8 -m tomato3d.cli.run_p1 run --package build/p1_state_20261011_01                        exit 0
python -X utf8 -m tomato3d.cli.run_p1 compare-observation --package build/p1_state_20261011_01        exit 0
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261011_01                     exit 0 (61/61 files identical)
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode real --out build/p1_state_20261011_02            exit 0
python -X utf8 -m tomato3d.cli.run_p1 run --package build/p1_state_20261011_02                        exit 3 (valid, partial)
python -X utf8 -m tomato3d.cli.run_p1 collect --package build/p1_state_20261011_02                    exit 3
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261011_02                     exit 0 (13/13 identical, incl. detector)
```

Exit codes: 0 success (all segments executed, or a complete fixture run); 1 invalid / stale / replay differs /
failed; 2 usage or input error (changed inputs since `prepare`, existing package, wrong mode); **3 valid but
partial** — a partial run is never reported as success (prompt §5).

## 4. Package layout (`build/p1_state_<YYYYMMDD>_<nn>/`)

`p1_request.json` (frozen request + input sha256), `p1_manifest.json` (schema/code version, per-file code hashes,
input snapshot, `run_status` per segment, `overall_status`, P2 field map, file hashes, tracking scores),
`captures.csv`, `frame_transforms.csv`, `observations/observations.csv` (+ per-capture `masks.json`, lossless
intervals of `tools.leaflet_mask_batch.pack_mask`; fixture-only `truth_join.csv` the tracker never reads),
`identity_manifest.csv`, `events.csv`, `match_candidates.csv`, `mtg_vertices.csv`, `mtg_edges.csv`,
`structure_state.csv`, `change_log.csv`, `unresolved.csv` (every unavailable cell + reason), `comparisons.csv`
(diurnal guard), `areas.csv` (four kinds, `full_outline`), `candidates.csv` + `completion_report.csv` (sub-MTGs),
`side_geometry.csv` (+ fixture validation tables), `optical_surfaces/*.csv` + `optical_surface_manifest.csv`,
`canopy_placement.json`, `canopy_merge_check.json`, `truth/` (fixture only), `compare_observation.csv` (fixture),
`audit_gaps.csv` (real), `viewer/index.html` (display only). Published by one rename from a staging folder;
a failed build leaves nothing (tested).

## 5. Producer → consumer map to P2 (also in every `p1_manifest.json` as `p2_field_map`)

| P1 producer field | P2 consumer | Rule |
|---|---|---|
| `canopy_placement.json` `instances[].plant_instance_id`, `source_plant_id` | `tools/vtc_growth_io.py` `plants.csv` same names | duplicates are distinct instances (`<source>#<n>`) |
| `instances[].p2_plants_csv.{tx_mm,ty_mm,tz_mm,yaw_deg,transform_source}` (+ `transform.matrix_4x4`) | `plants.csv` `tx_mm, ty_mm, tz_mm, yaw_deg, transform_source`; `tools/tomato_fsp_io.py::read_placement` reads `matrix_4x4` | mm, deg; only `placement_status = placed` and `in_optical_scene` |
| `optical_surface_manifest.csv` `external_leaflet_id = <plant_instance_id>|<vertex_id>` | `leaflets.csv` `plant_instance_id, compound_id, leaflet_id`; per-leaflet light output key | split at `|`; compound = vertex id without the last `/<tag>` |
| `optical_surfaces/*.csv` triangles, `plant_local_mm`, `adaxial_ccw`, `one_sided_lamina_full_outline` | P2 located geometry | transform applied once; incident/absorbed per external id on the one-sided area |
| `optical_readiness` | P2 input gate | `supported` usable; `conditional_completion` scenario-only (flag); `unavailable` absent |
| `mtg_vertices.csv`, `mtg_edges.csv`, `structure_state.csv` | `tools/vtc_development_observation.py::validate_initial` | needs metric 3-D base/tip `observed|model_estimated` — top-view snapshots carry none, so the dry-read reports **not consumable as an initial state** (0 rows), never converted |
| `instances[].light_ratio` (`app_ratio`) | light-ratio pointer | ratio only; never an absolute PPFD; never multiplied into ray-traced light |
| — | `plants.csv` age/reserve/mass; `leaflets.csv` dry mass/age | **not a P1 product** → unavailable (no photograph supplies them) |

## 6. Results

### 6.1 Fixture engineering run `build/p1_state_20261011_01` (evidence `synthetic_fixture`)
- Sources: O-mature `scene_0000` (`fx_om0`), `scene_0001` (`fx_om1`), R.1 `scene_0000` (`fx_sp0`); donor `scene_0002`;
  completion pool O-mature `scene_0003…0014` (84 generator compounds). Instances: `fx_om0`, duplicate `fx_om0#2`,
  `fx_om1`, `fx_sp0`, other-variety `fx_other` (plant-level only, out of the optical scene).
- Sequences (declared in `p1_request.json`): `fx_om0` c0 am → c1 pm (pot +35°) → c2 am (−20°, compound C0001 removed,
  a donor compound added, C0003 occluded); `fx_om1` c1 with **rotation unknown**, c2 with two compounds **merged** by a
  simulated segmentation failure; `fx_sp0` rotations only.
- Tracking vs truth join: **0 wrong links, 0 fragmented truth compounds** on all three plants (16 / 15 / 21 linked
  observations). Removed and occluded compounds stay `unobserved` / reason `unknown` (no removal without a record);
  the added compound opened `C0007` as `first_observed` with emergence interval (c1, c2]; the merge produced one
  `merge_suspect` event and both tracks `ambiguous`; the rotation-unknown capture routed 6 links to `ambiguous`.
  Every link is `proposed` (no human decisions; fixture weights are declared, not fitted).
- Diurnal guard: 31 comparisons `unavailable_diurnal_confound` (am↔pm), 14 `compared_same_phase` (am↔am).
- Areas: observed visible area equals truth for 57/59 compound observations; the 2 others are the deliberately
  merged observation (one mask, two truths). Raster note: `cv2.fillPoly` includes boundary pixels, so rasterised
  areas are inflated by ~½ px along each outline (declared in the manifest).
- Side geometry joined into the MTG for all 7 `fx_sp0` compounds at c2 (side-on view rule, §7.6), status `derived`,
  join provenance recorded as the fixture truth join.
- Optical: 129 `supported` truth leaflets, 99 `conditional_completion` candidate leaflets (5 of 14 occlusion-touching
  compounds kept 2–5 candidates at coverage ≥ 0.98; 9 rejected — reported, not relaxed).
- Canopy: merge → split round trip max error 0.0001 mm over 37,109 triangles; duplicate instances keep distinct
  external ids. P2 dry-read ok (4 placed optical instances). Codex `audit_p1_package`: `fixture_ready = true`.
- Replay: 61/61 files byte-identical.

### 6.2 P1.6 side-geometry validation `build/p1_side_validation_20261011` (50 finalized R.1 scenes, 1,392 compound-views)
- Blade-azimuth quadrant from (direction class, protocol view azimuth): **exact 1073/1073**.
- 2-D insertion angle vs 3-D truth, median |error| by insertion-plane tilt from the image plane: 3.5° (15–30°),
  8.7° (30–45°), 18.2° (45–60°), 29.0° (60–75°), 45.7° (75–90°). Same picture for α_i, Σα and θ (θ: 1.1° → 12.0°).
- By the view's direction class: `cl_left` 5.4° / `cl_right` 6.1° median vs `cl_toward` 25.0° / `cl_away` 40.7°.
  **Adopted rule:** take a compound's side values from a view where its class is `cl_left`/`cl_right`; per compound
  this gives median 7.0° / p90 15.6° vs 14.6° / 49.5° for "first view". The rule needs only the direction label,
  which a real labelled side photo has. A compound without such a view gets no side values (stays unavailable).
- These are projection-geometry errors on synthetic truth, not accuracy on real photos (no real points exist).

### 6.3 Real-data audit `build/p1_state_20261011_02` (evidence `real_photo`)
- 117 captures (13 top, 52 side, 52 level) referenced by path + sha256; every hash matches `generator_capture.csv`.
- 231 C6 detector boxes on the 13 decoded top JPGs (192 leaflet, 38 compound, 1 stem) stored as
  `detector_proposal` / `unreviewed` / `unvalidated_on_boardfree_top`; never tracked, never an area.
- Every later segment `unavailable`, each with the exact missing input (`audit_gaps.csv`):

| Segment | Missing input |
|---|---|
| ingest: scale | scale-block height and `pot_rim_inner_diameter_mm` unmeasured; ruler scale pending (I.4) |
| ingest: time | `lights_on_clock_time` null |
| ingest: rotation | no pot orientation mark recorded |
| ingest: top detection / labels | `tomato_top_nonboard` does not exist; `dwt_top_seg_bbox` 0 images; no human top masks |
| tracking | accepted top masks over ≥ 2 captures of one plant (each dwt_1xx has 1 capture) |
| side geometry | no human P0..Pm points; 52 real side photos unlabelled |
| optical surfaces | board-free 3-D (Q2) not implemented |
| canopy | `plant_id ↔ slot` empty (0 of 24); pot yaw unrecorded |

## 7. Decisions, assumptions and deviations (each visible in code and outputs)

1. **Status `synthetic_truth`** added (P1 extension) for values read from a synthetic mesh; the validator rejects it on
   any non-fixture row. A1.5/A2 quantities computed from truth points carry `derived`.
2. **Frame `canopy_mm`** added; produced only by `canopy.py` from `plant_local_mm`. No board↔plant-local conversion is
   written. Fixture projection into R.1 render cameras uses the synthetic scene's own placement (fixture only).
3. **Petiole vertex code `PT`** (`<compound>/PT1`): MTG §4 gives the grammar but no petiole code, and A1.5 forbids
   reusing `P1L`-style leaflet tags. Rachis segments `R1..Rm`.
4. **`rachis_bend_alpha_1..8_deg`**: A2 12.3 asks for one column per node; a CSV needs a fixed header, so 8 columns are
   allocated (`MAX_BEND_NODES`); more nodes is a hard error, never truncation.
5. **`blade_azimuth_basis = top_mask_proximal_to_distal`** (extension of A2 12.4's two bases) for the top-view proxy;
   `compare_observation.csv` reports its difference from the truth P1→tip azimuth (it is a different definition).
6. **Detector label** `unvalidated_on_boardfree_top` instead of the prompt's `unvalidated_synthetic_trained` (§1 of the
   inventory: the C6 judge is real-trained).
7. **Tracking config**: real runs use the all-null template (everything to review; no new id without a threshold —
   the observation is `unassigned`/`ambiguous`); fixtures use declared values. Added key
   `split_merge_containment_min` (null in the template). An `ambiguous` capture is not an absence (no false
   `reappeared`).
8. **Completion adapter**: `build_compound` needs L-Py (tomato_synth env) and has no `fixed=`; the fixture completion
   draws pre-generated compounds (fixed seeds) and only rotates/scales them. Candidates are `generated_candidate`
   sub-MTGs and `conditional_completion` surfaces, never in the main snapshot.
9. **Canopy geometry**: tray pitch 300 mm, pot pitch 110 mm, row pitch 110 mm, equal soil height — all
   `assumed_unmeasured` in `p1_config.json` and in every `canopy_placement.json`. Canopy frame: origin row1/col1,
   +X col1→col4, +Y wall→front, +Z up (right-handed).
10. **Other-variety plants**: plant-level MTG row only (A1.3), omitted from the optical scene with a reason, no capture row.
11. **Fixture clock**: 2026-10-11 08:00+09:00 + declared hours; time since lights-on am 60 / pm 540 min (status `assumed`).
12. **Capture time of real photos**: device clock without UTC offset (`measured`, offset noted); Codex's reader asks for
    an aware time and lists it as a gap.

## 8. Ownership and coordination

No file under `tools/`, `tools/tests/`, `phynotype2/`, `config/`, `data/records/` or `docs/` was edited, so no LOG
claim was needed; `tools.leaflet_mask_batch` was imported read-only, and Codex's `tools/tomato_fsp_io.py` was run
read-only to check consumption. Written: `tomato3d/state/`, `tomato3d/track/`, `tomato3d/cli/run_p1.py`, `tests/`,
`build/p1_*`, and these handoff files. Concurrent sessions active today (Codex `tools/tomato_fsp_*`, a Claude Code
Micro-Tom forecast claim) touch none of these files.

## 9. What would unblock real P1, in order of effect
1. Assign `plant_id` to the 24 slots (plant registry) and record each pot's orientation mark → canopy placement.
2. Measure `pot_rim_inner_diameter_mm` (or adopt the ruler scale, I.4) → every mm value and candidate generation.
3. Record the daily lights-on clock time → diurnal guard and growth comparisons.
4. Top-view masks: label `dwt_top_seg_bbox` (→ `tomato_top_nonboard`) or provide human boxes for SAM.
5. Two or more captures per plant → tracking.
6. Side photos: direction labels (guide exists) and P0..Pm points on side-on views → insertion angle, α, θ.
7. Board-free 3-D (Q2) → `supported` optical surfaces from photos.


## Addendum 2026-10-12 — generator caveat

Several synthetic-fixture numbers in this document are **generator-relative, not plant-verified**: the O-mature generator has leaflet L/W 1.19 (measured 1.4–1.7, 16 % inside) and 6–8 compounds per plant (real 4–5). Which numbers are affected and which appear little affected (A3 side angles — unverified): `handoff/P1_GENERATOR_CAVEAT_2026-10-12.md`.
