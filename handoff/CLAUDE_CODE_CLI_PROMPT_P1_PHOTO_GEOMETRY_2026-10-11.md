# Claude Code — P1 (photos → current plant state → canopy placement), built from existing renders and code (2026-10-11)

Scope: **only P1** of `handoff/CLAUDE_P1_P2_P3_P4_END_TO_END_INTEGRATION_PROMPT_2026-10-11.md` (its §4, the P1 half
of §5, the P1 rows of §8–§10). P2/P4/P3 are out of scope; this prompt ends at a published P1 state package that
P2 can consume. Implementer: Claude Code. Assemble from what already exists (synthetic render outputs, `tomato3d/`,
shared `tools/`); write new code only for missing glue. Do not start any model training, remote job or upload.

## 0. Read first (list every file read at the top of your report; say which do not exist)
- `CONVENTIONS.md`, `CLAUDE.md`, `AGENTS.md`, `../공통규약.md`, last 40 lines of `handoff/LOG.md`.
- Integration prompt above (§1, §2, §4, §5, §8–§10).
- Contracts: `handoff/MTG_CONVENTION_2026-10-10.md` (§11 A1, §12 A2, **§13 decisions**),
  `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` (Stage-2 schema, §3 frames, §4 area kinds, §5 identifiability,
  §6 outputs, §7 update rules, + Amendment L1 + 2026-10-11 decision note),
  `handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md` (§3 frames, §4 observations, §5 association,
  §6 generator candidates, **§7 output contract**), `handoff/STAGE1_IMPLEMENTATION_RESULT_2026-10-11.md`,
  `handoff/CROSS_STAGE_ISSUES_2026-10-11_KO.md`, `handoff/DETECTOR_POLICY_2026-10-09.md`,
  `handoff/CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md` (P1 items), `handoff/R_SESSION_STATE_2026-10-10.md`.
- Records (read-only): `data/records/env_light_20261010/`, `data/records/plant_registry/`,
  `data/records/compound_bend_types_20261010/`.

## 1. Binding rules
- Ownership: `tomato3d/`, `tests/` = yours. `tools/`, `tools/tests/` = shared (override 2026-10-11) — append a file
  claim to LOG before editing, never touch a file under an active claim (Codex V3 claims `tools/vtc_development*`,
  `tools/vtc_growth_bridge.py`). `config/`, `data/records/`, `docs/` = human, read-only. LOG append-only.
- `phynotype2/` is **absent** at its recorded path (it held only a README). Do not recreate it or infer deletion
  intent: put the tracker in `tomato3d/track/` (your folder; `link.py` is a stub) and record in LOG + report that the
  phynotype2 §7 contract is implemented there. If the human later restores `phynotype2/`, it imports from tomato3d.
- Board-free is the product line ("보드에 집착하지 말고"); `dwt_01~04` board sessions are droppable — no new work
  depends on them. Board use is optional evidence only.
- Detector: product series is `tomato_top_nonboard`, which **does not exist yet** (Roboflow `dwt_top_seg_bbox` empty).
  So real top-view detection = `unavailable`; accept human-provided boxes/masks via the existing importers
  (`tools/roboflow_session_import.py`, `tools/annotator_import_coco.cjs`). The synthetic-trained C6 detector
  (pooled AP50 0.28 on synthetic, not validated on real) may run on real photos only as a labelled
  `detector_status = unvalidated_synthetic_trained` proposal, never as an observation.
- MTG decisions: rank anchoring (lowest leaf at the reference capture = 1, never renumbered); A2 angle references;
  petiole-base vs blade azimuth separate; compound vs leaflet insertion angle class-prefixed on export;
  **area_basis = `full_outline`** (green-only only as an extra field); **blade curl and flat/bent θ thresholds are
  on hold** — no definition, no threshold, `rachis_bend_type` = human label only.
- No physical unit without a scale source (scale block height and `pot_rim_inner_diameter_mm` are unmeasured);
  no frame conversion between `board_mm` / `plant_local_mm` / `image_px`; top view alone → insertion angle,
  elevation and true surface `unavailable`.
- Record `capture_time` and `time_since_lights_on_min` on every capture; posture change between different phases
  is never fitted as growth. Lights-on clock time is unrecorded → `unavailable` until the human gives it.
- Fixtures vs real: every synthetic-derived result carries `evidence = synthetic_fixture` and can never count as
  photo reconstruction.

## 2. What exists to combine (verify each against source/outputs first; correct this table if wrong)
| Asset | Where | Use in P1 |
|---|---|---|
| Top-view synthetic scenes with known meshes, poses, GT boxes/masks (N/O, O-mature) | `build/synthetic_dwarf_tomato_20261008_07/` (+ `_05_*`, `_06_04`, `_08_06`, `_08_08`); locate the O-mature run from `NO_analysis.json` / `C6_REPORT.md` | ground-truth fixtures: truth MTG, area kinds, occlusion, tracking sequences |
| Side-view R.1 set: 150 scenes × 4 views, compound boxes, 4-class direction labels, quadrant check exact | `build/sideprop_20261009_01/` (batch a finalized; b/c may still be rendering — use only finalized views, read `R2_label_summary.json`, `manifest.jsonl`, `views_intrinsics.json`) | side-view geometry fixtures: insertion angle, α_i, θ, blade-azimuth quadrant |
| Generator | `tomato3d/synth/compound_leaf.py` (`build_compound`, `fixed=` whitelist), `structure.py`, `scene.py`, `leafarea.py`, `leaflet_surface.py`, `sideview.py` | truth export, generated candidates (separate sub-MTG), controlled perturbations |
| Stage 1 | `tomato3d/calib`, `tomato3d/mask/silhouette.py`, `tomato3d/io/*` (261 tests pass) | capture manifest, frame tokens, `unavailable` sentinel; silhouettes blocked until scale block measured |
| Graph/organ stubs | `tomato3d/graph/*`, `tomato3d/organ/*`, `tomato3d/track/link.py` (stub) | fill the parts this prompt needs |
| Shared tools | `tools/leaflet_segmenter.py`, `sam_*`, `detected_leaf_area.py`, `leaf_area_geometry.py`, `plant_structure.py`, `plant_hierarchy.py`, `multiview_*`, `observation_records.py`, `instance_*` | reuse for masks, area, hierarchy where they fit the contracts — cite file:function |
| Historical photo-derived 3D | `build/plant3d_regroup_20261004_01/` (dwt_t1, board era) | diagnostic only, not a P1 input |
| Real photos | `data/raw/dwt_1xx/…` (board-free handheld top views), `tomato_photos_by_view_/`, 52 real side photos in `real_eval/` (unlabelled) | real-data audit (§4 P1.9) |
| Light layout | `data/records/env_light_20261010/` (slot ratios rule v3, tray layout) | slot_id → canopy placement; light_ratio attribute only |

## 3. Output package (one per run): `build/p1_state_<YYYYMMDD>_<nn>/`
Follow the Stage-2 spec §6 file names where they exist; add only what P2 needs. Minimum:
- `captures.csv` (capture_id, plant_instance_id, source_plant_id, capture_time, time_since_lights_on_min, view,
  frame token, scale_source, image sha256 — reference raw photos by path+hash, do not copy).
- `observations/` per capture: detections/masks with provenance (`human`, `detector_proposal`, `synthetic_gt`).
- `identity_manifest.csv`: organ track IDs (`dwt_101/C0001` style), parent IDs (plant → axis → compound → leaflet),
  `correspondence_status` (proposed / confirmed / rejected), track state + events (split, merge, occluded,
  disappeared_unconfirmed, removed_confirmed, new). Absence in one image ≠ removal.
- `mtg_vertices.csv` (MTG §9 + A1/A2 columns, each value with `__status`), one snapshot per capture.
- `areas.csv`: four separate columns per leaflet — visible projected (px², mm² only with scale),
  occlusion-completed (+method, coverage, uncertainty), one-sided lamina surface (+geometric evidence),
  optional green-only; `area_basis = full_outline`.
- `optical_surfaces/` + `optical_surface_manifest.csv`: located leaflet polygons/meshes in `plant_local_mm` with
  stable external leaflet IDs, face/area convention, `optical_readiness` (`supported` / `conditional_completion` /
  `unavailable`) and reason. Never a bbox, hull, compound envelope or unlocated area+angle tuple.
- `canopy_placement.json`: one rigid transform per plant instance (plant_local → canopy), slot_id, light_ratio
  (`app_ratio`), provenance of tray geometry (assumed until measured), duplicate-instance handling.
- `p1_manifest.json`: schema version, input snapshot hashes, code version, run_status per segment
  (`executed` / `fixture_only` / `unavailable` + reason), and the producer→consumer field map to P2.
- `viewer/` display-only (may reuse the existing display viewer; "눈속임도 ㄱㅊ" applies to the viewer only).

## 4. Work orders (each: files, functions, tests; software pass criteria only)
**P1.0 Inventory.** `handoff/P1_INVENTORY_2026-10-11.md`: every P1 feature classified executed /
implemented-unverified / specification-only / absent / scientifically-unresolved, with file:function or output
path evidence; render runs listed with scene/view counts actually present on disk.

**P1.1 Schema module** `tomato3d/state/schema.py` (+ `tests/test_state_schema.py`): dataclasses/validators for every
file in §3, status vocabulary, frame tokens, `unavailable` sentinel; validators reject mm without scale, cross-frame
mixing, unprefixed insertion angles, green-only in the main area column, invented curl/θ-threshold fields.

**P1.2 Synthetic truth exporter** `tomato3d/state/fixture_truth.py`: synthetic scene → truth MTG + truth areas
(all four kinds computable from the mesh) + truth optical surfaces + projected observations. Also an
"observation-like" view that drops what a camera cannot see (occluded leaflets, top-view angles) so the P1 path is
tested on what a photo would give. Tests: truth/observation separation, IDs stable, area kinds differ as expected
under occlusion and bending.

**P1.3 Observation ingest** `tomato3d/state/ingest.py`: real captures (Stage-1 manifest or board-free handheld
import), human boxes/masks, optional C6 proposals (flagged), synthetic GT. Masks by existing SAM/segmenter tools
where they fit. Record per-image mask quality. No detector → `unavailable`, not an empty list pretending success.

**P1.4 Tracking** `tomato3d/track/link.py` (implement the stub per phynotype2 §5/§7): compound = track unit,
terminal leaflet by explicit membership, six track states, proposed vs confirmed, no azimuth prior (MTG 8.5 open).
Test sequences built with the generator from fixed seeds + controlled changes (rotation, occlusion, one compound
removed, one new compound, split/merge ambiguity). Pass: ID preservation, no forced identity, absence ≠ removal.

**P1.5 Structure update** `tomato3d/state/update.py`: observations + tracks → MTG snapshot per Stage-2 §5/§7: rank
assignment rule, status per value, no promotion of estimates to observed, generated candidates only as a separate
sub-MTG (`candidate_id`), top view → insertion/elevation/surface `unavailable`.

**P1.6 Side-view geometry** `tomato3d/state/sidegeom.py`: from P0–P3 points (human points on real photos; projected
GT on R.1 fixtures) compute `compound_insertion_angle_deg`, `rachis_bend_alpha_<i>_deg`, `rachis_curvature_deg`, θ
(excluding the last α), straight/path ratio, blade-azimuth quadrant. Validate against R.1 truth (error per view,
foreshortening vs view angle). Do not classify flat/bent (thresholds on hold).

**P1.7 Optical surfaces** `tomato3d/state/optical.py`: export located leaflet surfaces. Synthetic: from truth
(fixture). Real: board-free 3D (Q2) is not implemented → `unavailable`, or an explicitly
`conditional_completion` built from generator candidates constrained by observed 2-D masks, flagged and never
mixed with observed geometry. Area/face convention stated so P2 can compute incident/absorbed per leaflet.

**P1.8 Canopy placement** `tomato3d/state/canopy.py`: slot_id → rigid transform using the env_light layout (3 trays +
col4 separate, col1 = right end by the post, row1 = wall); tray spacing/pot pitch unmeasured → declared assumed
values in `canopy_placement.json`. plant_id ↔ slot is human-pending → per-plant `slot_id unavailable` blocks real
placement (fixtures use declared slots). Other-variety plants: plant-level only; omit from optical scene with a flag
unless a conditional proxy is explicitly requested. Tests: transform round trip, duplicate source plant as two
instances, per-plant re-split of IDs.

**P1.9 Real-data audit** (integration §10 item 1): run `data/raw/dwt_1xx` and the real side photos through every
supported operation; report per segment what ran and the exact missing input (scale block height, pot rim
diameter, top detector/labels, plant_id↔slot, lights-on time, side P0–P3 points). No synthetic substitution.

**P1.10 Engineering run** (integration §10 item 2, P1 part): one synthetic multi-plant fixture (≥ 3 instances incl.
a duplicate, ≥ 2 time points) through P1.3→P1.8 into a full package; P2 dry-read of the package by a schema check
only (do not run light).

**P1.11 Entry point** `tomato3d/cli/run_p1.py` with `inventory | prepare | run | collect | compare-observation |
replay`; deterministic replay from snapshot hashes; stale outputs invalidated when code/schema hashes change.

## 5. Failure handling (must refuse to publish success)
Wrong/missing IDs, frames, times or units; mm without scale; fixture data labelled as real; tracker forced to
match; partial run; missing optical readiness silently filled. Each → `run_status` with reason, non-zero exit.

## 6. Done when
- Inventory written; schema, fixture exporter, ingest, tracker, updater, side geometry, optical export, canopy
  placement, CLI implemented with tests in `tests/` (full suite still passes; report counts).
- Fixture run package exists and validates; real-data audit package exists with every gap named.
- `handoff/P1_EXECUTION_2026-10-11.md` (English) + `_KO.md`: commands run and exit codes, schema version,
  producer→consumer map to P2, completion reported separately for: observation reconstruction (real),
  interfaces, fixture engineering path.
- LOG: claim line before editing shared files, one result line at the end.

## 7. Out of scope
P2/P4/P3 engines, VTC fork edits, Q2 board-free 3D implementation, R.5 training, any detector training, Roboflow/Kaggle
uploads, edits to `config/`, `data/records/`, `docs/`, the original vtc-main, and Codex's claimed V3 files.
