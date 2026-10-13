# Claude Code prompt: synthetic dwarf tomato generator — stage 1 (100 scenes)

Date: 2026-10-05. Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.
Talk to the user in Korean. Code, handoffs and logs in English. Tables CSV, settings/provenance JSON.

## Goal

Build a reproducible generator that renders synthetic dwarf tomato plants **in this project's capture rig geometry**, with exact ground truth that real photos cannot give: per-leaflet **visible** and **amodal (full, including occluded)** masks, depth, and the 3D plant graph. Stage 1 = 100 scenes plus a realism check. This feeds architecture C (2D amodal leaflet completion) and later B (structure fitting) from `CLAUDE_TOPVIEW_3D_DIFFUSION_REVIEW_2026-10-05.md` (ask the user to copy it into `handoff/` if it is not there).

Synthetic data is training/validation material only. It never becomes observation, never enters light (PPFD) or growth-coefficient fitting, and every artifact carries `origin=synthetic`.

## Division of work (user decision 2026-10-05)

| Level | Tool | What it decides |
|---|---|---|
| Plant structure | existing P3 engine `tools/probabilistic_compound_growth.py` (sample/decode) | main-stem nodes, internode lengths, compound-leaf attachment, direction, rachis length and side extents per compound leaf |
| **Compound-leaf interior** | **L-Py (OpenAlea) + PlantGL** | leaflet pair count, spacing, size order along the rachis, terminal leaflet, small intercalary leaflets, petiolule angles, rachis bending, leaflet curvature (longitudinal bend, transverse roll) |
| Leaflet outline | real contour library from human-reviewed leaflet masks | outline shape (serration, asymmetry, tip), mapped onto the PlantGL leaflet surface |
| Rendering | **Blender (`bpy`, headless)** — default chosen; switch to pyrender only if Blender is impossible in the runtime | RGB, masks, depth, normals |

Contract between P3 and L-Py: the L-Py compound leaf **must stay inside** the P3 rachis length and left/right extents it receives (tolerance declared in config). Violations are rejected and resampled, never clipped silently.

## Read first

- `tools/PROBABILISTIC_COMPOUND_GROWTH.md`, `tools/probabilistic_compound_growth.py` (synthetic fixture/demo, `sample_forecast`, `decode_trajectory`)
- Dwarf FSP source parameters (topology priors only, not defaults): `build/fsp_physiology_spec_20261003_01/sources/` (`dwarf_parameters.rgg`, `dwarf_organs.rgg`, CSV), `tools/growth_calibration_evidence.json` (137° is a modelling assumption)
- Rig geometry: a real `capture.json` (intrinsics + measured poses) under `build/plants_dwt_test_20261002/plants/dwt_t1/` and `build/plants_e2e_20261002/`; board spec `config/board_spec.json`; `tools/make_square_board.py`
- Leaf colour statistics: `tools/rgb_ratio_batch.py` outputs
- Human-reviewed leaflet masks (AL4 / annotator exports for dwt_01–04; locate via `build/al_4plants_20261002/AL4_RESULTS.md` and the annotator batch folders)
- Real trait ranges: `build/ONE_PIPELINE_2026-10-01.md`, dwt_test S8 results (height ~60–90 mm, side leaf-area proxy ~10–17 cm², stem ~5.5–6.2 mm)
- Parent `공통규약.md`, `AGENTS.md`, `CONVENTIONS.md`, latest LOG/TODO. Check for active sessions before editing shared files.

## Steps

1. **Environment.** Isolated environment only (never the project's main Python). L-Py needs conda (`openalea.lpy`, `openalea.plantgl`); Blender via its own Python or `bpy` wheel. Prefer Colab/Kaggle or a conda env; record exact versions in `runtime_env.json`. If L-Py cannot be installed, stop and report — do not substitute a different grammar silently.
2. **Leaflet contour library.** From human-reviewed masks: extract outlines, normalise (base at origin, midrib on +x, unit length), store with source mask hash, plant, view, rank if known. Exclude occluded/partial masks (keep only `visibility=full` or equivalent). Output `leaflet_contours.json` + preview PNG.
3. **Structure sampling.** Use the P3 engine with an explicitly synthetic parameter set (wide declared ranges; no fitted values exist). Record every drawn parameter. Output one plant graph JSON per scene.
4. **Compound-leaf L-Py module** (`tools/synthetic_plant/compound_leaf.lpy` + Python wrapper): input = rachis length, left/right extents, compound rank, random seed, declared ranges (pairs, spacing, size taper, angles, bend, roll). Output = PlantGL scene → per-leaflet mesh with stable IDs `plant/compound/leaflet`. Leaflet surface = contour from step 2 mapped onto a bent/rolled PlantGL patch.
5. **Scene assembly.** Stem and petioles as tubes; pot; ChArUco board texture at real board scale; background similar to real photos. Board-frame mm coordinates throughout.
6. **Rendering (Blender).** Use the **real capture poses and intrinsics** from one or more `capture.json` (randomly assign a real session's camera set per scene). Per view render: RGB; visible instance mask (leaflet IDs); **amodal mask per leaflet** (render that leaflet alone, others hidden); depth (mm); normals; organ class mask (leaflet / petiole+rachis / stem / pot / board). Domain randomisation within declared ranges: light position/intensity, leaf colour from step 3 statistics, slight translucency, sensor noise, white balance.
7. **Manifest.** `manifest.jsonl`, one row per scene×view: `scene_id, plant_graph_path, view_id, camera_source_session, rgb, visible_mask, amodal_masks_dir, depth, normals, organ_mask, seed, parameter_hash, origin='synthetic', generator_version`. Plus `scene_params.csv` (all drawn parameters).
8. **Realism check (gate).** Compare 100 synthetic scenes against real plants: height, outer-envelope area, leaflet count per photo, visible leaflet mask area distribution, occlusion fraction, colour histogram. Also run the existing detector v4 + SAM v5 on synthetic photos and compare detection/mask metrics to their real plant-held-out values (leaflet AP50 ≈ 0.74–0.77, SAM IoU ≈ 0.82–0.86). Report `realism_report.json/.csv` and side-by-side previews. Pre-declare the pass criteria in `stage1_contract.json` **before** rendering (e.g. synthetic trait medians inside the real min–max; detector AP50 within ±0.15 of real). Do not change criteria after seeing results.

## Constraints

- No literature or synthetic parameter becomes a default for the real models. Ranges live only in the generator config with `source_kind` (`literature_prior` / `user_assumed` / `measured_range`).
- Do not modify `tomato3d/`, `config/`, human masks/labels, original photos, or the P3 engine's behaviour (call it; do not edit it). New code under `tools/synthetic_plant/` and `tools/tests/test_synthetic_plant*.py`.
- Outputs to a fresh `build/synthetic_dwarf_tomato_20261005_01/`. Keep all scenes, including failures/rejections, with reasons.
- Amodal mask ⊇ visible mask for every leaflet (assert). A leaflet invisible in a view has an empty visible mask but a non-empty amodal mask.

## Tests

1. Same seed → identical scene, masks and manifest hashes.
2. L-Py compound leaf stays within P3 rachis length/extents; violations rejected.
3. Amodal ⊇ visible per leaflet per view; IDs consistent across views.
4. Rendered board corners reproject onto the real camera model within a declared pixel tolerance (rig geometry correct).
5. Depth units mm, board frame; organ mask classes complete.
6. Manifest rows all carry `origin='synthetic'`.

## Deliverables

- Code, config, tests (JUnit XML), 100 scenes, `manifest.jsonl`, `scene_params.csv`, `leaflet_contours.json`, `realism_report`, preview sheet.
- English handoff `handoff/CLAUDE_SYNTHETIC_DWARF_TOMATO_STAGE1_RESULT_2026-10-05.md`; one LOG line; TODO for stage 2 (1,000–5,000 scenes after range tuning).
- Korean summary for the user: pass/fail of the realism gate, main mismatches, and what to tune before stage 2.

## Superseded

Superseded on 2026-10-05 by `CLAUDE_CODE_CLI_SYNTHETIC_DWARF_TOMATO_STAGE1_2026-10-05.md` (code location moved to Claude-owned `tomato3d/synth/`; safety rules added).
