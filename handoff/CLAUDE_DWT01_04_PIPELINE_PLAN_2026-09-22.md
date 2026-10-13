# dwt_01..dwt_04 pipeline: fixed flow and plan to Sunday 2026-09-27

User goal (2026-09-22): by Sunday, fix the implementation flow for dwt_01, dwt_02, dwt_03 and dwt_04 and implement it.
Claude leads until 2026-09-26 18:00 KST (see CLAUDE_LEAD_HANDOFF_UNTIL_2026-09-26_1800_KST.md); the Saturday
handoff below returns the column to Codex. The user has explicitly asked Claude to work in `tools/` during this period.

## 1. Flow (one per plant, same stages, reusing existing tools)

| Stage | What | Tool | State |
|---|---|---|---|
| S0 | Prepared session: photos, measured ChArUco poses (gates unchanged) | `tools.import_organized_capture` | exists; dwt_01/02 done |
| S1 | Roboflow labels to original pixels (crop/scale checked, F1 fixed) | `tools.roboflow_session_import` | exists; dwt_01/02 done |
| S2 | Leaflet masks (SAM 2.1 tiny, local CPU) + human accept | `tools.leaflet_mask_batch` + editor | exists; dwt_01 268 accepted, dwt_02 0/285 |
| S3 | Whole-plant structure: hull, compound regions, stem axis, petioles | **new `tools.plant_structure`** (ports scratchpad code, fixes F2) | to build |
| S4 | Cross-view leaflet candidates -> human review -> editor identities | **new `tools.cross_view_candidates`** + `tools.cross_view_identity_import` | importer done; candidates to port |
| S5 | Model-2 labels (tip-direction class, optional tip/base keypoints) | **new importer on S1 contract** | to build after labels exist |
| S6 | Evidence: Document 06 fusion (needs visibility) and tip/base triangulation | `tools.instance_workflow`, `tools.rebuild_leaf_edit_session` | exists |
| S7 | Organ hierarchy JSON (plant > stem > petiole > compound > leaflet; position, azimuth, elevation or `unavailable`) + 3D viewer | **new `tools.plant_hierarchy`** | to build |
| S8 | Optional side poses from >= 8 reviewed physical points | `tools.side_pose_candidate` | exists; needs S5 points |

**New orchestrator `tools.plant_pipeline --plant dwt_0X`:** runs S0..S7 in order into a fresh `build/pipeline_<date>/<plant>/`.
Each stage reports `done`, `waiting_for_human` (with the exact missing input), or `unavailable` (with reason).
It never invents a missing input. One status table covers the four plants.

Rules carried over: measured poses only (no nominal angles, SfM or pose averaging); 1 px pose gate kept,
outputs `validated_metric=false`, `suitable_for_ppfd=false`; growth JSON is a count reference, never a quota;
compound membership only from reviewed evidence; review decisions enter the editor backup through the importer,
not a parallel store.

## 2. Model-2 label criterion (user, 2026-09-22)

Class by the direction the **leaflet tip** points in the photo: tip to the right = `side_right`, to the left =
`side_left`; `front` / `back` for tips pointing toward / away from the camera (definition to be written down by the
user before labelling). Copy model-1 leaflet boxes and change only the class so both models join on the same box.
Use: cross-view consistency (the class must rotate with camera azimuth; sign to be verified against measured poses
before use) and a ~45 degree leaflet azimuth estimate for S7.

## 3. Current per-plant state

| | dwt_01 | dwt_02 | dwt_03 | dwt_04 |
|---|---|---|---|---|
| Photos organised | 18 | 18 | 18 (260921) | 18 (date 260920, stored under tomato_photos_organized_/260921; view 01 is 3024x4032) |
| S0 session | done, 6 solved poses | done, 8 solved | done 2026-09-22: 5 solved (01/03/21/24/25) | done: 3 solved (25/26/28); view 01 excluded (portrait) |
| S1 labels | 388 | 388 | 432 mapped | 534 mapped |
| Growth JSON | 8/9/9 | filled | **blank** | **blank** |
| S2 masks | 268 accepted | 285 unreviewed | needs authorization to run SAM | same |
| S4 identities | 7 leaflets (19 obs) | 0 | 0 | 0 |

## 4. Days

- Tue night / Wed: S0 + S1 for dwt_03/04 (after checking JPEG input and the portrait view); port hull / compound /
  stem / petiole code into `tools.plant_structure` with explicit paths and tests (closes F2); orchestrator skeleton
  and status table.
- Thu: `tools.cross_view_candidates` (co-occurrence + compound prior + direction-rule filter, as review proposals
  only); `tools.plant_hierarchy` schema and builder from S3/S4/S6.
- Fri: model-2 importer (once an export exists); S6 wiring; per-plant viewer; full run on four plants.
- Sat until 18:00: tests, LOG/TODO, handoff back to Codex.
- Sun: rerun the plants whose human inputs arrived; final status table.

## 5. Human inputs that decide how far each plant gets

1. Growth JSON for dwt_03 and dwt_04 (compound leaf and leaflet counts).
2. Authorization to generate SAM masks for dwt_03/04 (the 2026-09-22 authorization covered dwt_01/02 only).
3. Mask acceptance: dwt_02 (285), dwt_03/04 (after generation).
4. Cross-view review pages as they are produced.
5. Model-2 labels (Roboflow) with the written tip-direction rule.
6. Visibility (full/partial) for confirmed leaflets, unless model-2 labels carry it.

## 6. Roboflow model routing in the 8821 editor (user, 2026-09-22)

Photos 11-18 use the side model, photos 21-28 the middle model. Current models (read-only API listing):
`tom_side_seg_bbox/2` (yolo26n-seg, mAP 13.51) and `tom_middle_seg_bbox/2` (yolo26n-seg, mAP 4.90), each trained on
31 images of these same dwt plants. On dwt_01..04 their output is therefore not independent evidence and cannot
replace the imported human labels; it is a proposal layer, mainly useful for new plants/dates. Running them is remote
inference (serverless endpoint) and needs an explicit go-ahead; the API key must stay server-side (read from the
user's key file by `tools.serve_leaf_edit_session`), never in the page. Top views (01/03) have no model.

## 7. Implemented 2026-09-22 (Claude)

One command: `python -X utf8 -m tools.plant_pipeline --all` (plants in `tools/plant_pipeline_plants.json`). Each run writes
`build/pipeline_<timestamp>/` with per-plant `status.json`, `STATUS.md` and `HUMAN_TASKS.md` (Korean, human work only,
with the file/page to open). New tools: `tools.plant_structure` (S3; replaces the scratchpad hull/stem/compound code, F2),
`tools.cross_view_candidates` + `tools/cross_view_review.html` (S4 proposals and visibility questions as a local page that
saves one decision file to Downloads), `tools.plant_hierarchy` + `tools/plant_viewer.html` (S7). `tools.cross_view_identity_import`
now reads saved review files and applies explicit visibility answers. S5 waits for model-2 exports; S2 for dwt_03/04 waits
for SAM authorization (prepare is hard-limited to dwt_01/02 by the earlier authorization and was not widened).
Tests: tools/tests/test_plant_pipeline_tools.py (9) plus the importer/F1/session suites.

## 8. Decision 2026-09-23: poses for unposed photos from a feature map (user)

The user asked for both routes, in parallel, and stated the plants are in a controlled setting and do not move, so
plant texture is as usable as the rigid background.

1. **Feature-map PnP (new, `tools.feature_pose_candidate`)**: SIFT features from the photos that do have measured
   ChArUco poses are matched pairwise and triangulated with those fixed poses into a sparse 3D feature map in the
   board frame; an unposed photo is then located against that map with RANSAC PnP. This uses image matching across
   photos, which earlier handoffs excluded ("no SfM"). It is admitted here on the user's instruction with these
   limits: measured ChArUco poses are never re-estimated, moved or averaged; no bundle adjustment; scale comes only
   from the board; every result is a candidate with `validated_metric=false`, `suitable_for_ppfd=false`, and it is
   kept apart from measured poses in every file and view.
2. **Landmark PnP (existing `tools.side_pose_candidate`)**: unchanged contract, needs >= 8 reviewed physical points.

Accuracy is measured, not assumed: each posed photo is solved as if it were unposed (its own features excluded from
the map) and compared with its measured pose. Those numbers decide whether any unposed candidate is used at all.
