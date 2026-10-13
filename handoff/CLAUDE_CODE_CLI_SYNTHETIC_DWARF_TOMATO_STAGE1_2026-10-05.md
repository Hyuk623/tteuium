# Claude Code CLI task: synthetic dwarf tomato generator — Stage 1

> Run from the project root with Claude Code CLI, e.g.
> `claude "Read handoff/CLAUDE_CODE_CLI_SYNTHETIC_DWARF_TOMATO_STAGE1_2026-10-05.md and carry it out step by step."`
> This file supersedes `CLAUDE_CODE_SYNTHETIC_DWARF_TOMATO_STAGE1_PROMPT_2026-10-05.md` (that draft put code under `tools/`, which Claude Code does not own).

Date: 2026-10-05. Talk to the user in **Korean**. Write code, logs and handoffs in **English**. Tables CSV, settings/provenance JSON.

---

## 0. Safety rules for this task (read before doing anything)

These keep the existing project unchanged. If any step would break one of them, **stop and ask the user**.

### 0.1 Where you may write

| Path | Allowed |
|---|---|
| `tomato3d/synth/` (new subpackage) | create and edit — this is the generator code |
| `tests/test_synth_*.py` (new files only) | create and edit |
| `build/synthetic_dwarf_tomato_20261005_01/` (and later fresh `build/synthetic_dwarf_tomato_<date>_NN/`) | all outputs, scratch, logs, env records |
| `handoff/` | **append** one LOG line; create the result handoff file named in §8; nothing else |

### 0.2 Where you must not write

- `tools/`, `tools/tests/` — Codex owns them. You may **import** from `tools/` (e.g. the P3 engine) but never create, edit or delete files there.
- `config/`, `docs/`, `data/`, original photos, human labels/masks, any existing `build/` folder you did not create in this task.
- Existing files in `tomato3d/` and `tests/` — do not modify them. In particular do not touch `tests/conftest.py` (`render_charuco_view` is the project's only ChArUco renderer; do not duplicate or move it).
- `pyproject.toml` — do **not** add L-Py, PlantGL, Blender or any new dependency. New heavy dependencies live only in a separate environment (§2). `tomato3d.synth` must import them lazily so `import tomato3d` and the existing test suite keep working without them.
- Do not create files outside `build/` for scratch, and do not leave `__pycache__`/`.pytest_cache` noise in synced folders (set `PYTHONDONTWRITEBYTECODE=1`, run pytest with `-p no:cacheprovider`).

### 0.3 Existing behaviour must stay identical

- Before writing any code, run the existing core test suite once and save the result: `python -X utf8 -m pytest tests -q -p no:cacheprovider --junitxml=build/synthetic_dwarf_tomato_20261005_01/preflight/tests_before.xml`.
- At the end, rerun it; the same tests must pass (new `test_synth_*` tests are additional). If anything that passed before now fails, revert your change and report.
- Record SHA256 of every file you read as an input (contours, capture.json, board PNG) in `inputs_manifest.json`. Do not modify them.
- OneDrive: do not edit a file another agent is working on. Check the latest entries of `handoff/LOG.md` and `handoff/TODO.md` first.

### 0.4 Data rules

- Every synthetic artifact carries `origin='synthetic'`. Synthetic data never becomes observation, never enters light (PPFD) calculations or growth-coefficient fitting.
- No literature or synthetic parameter becomes a default of any real model. Generator ranges live only in `build/.../generator_config.json` with `source_kind ∈ {literature_prior, user_assumed, measured_range}` and a `source_ref`.

---

## 1. Goal and design (decided by the user)

Render synthetic dwarf tomato plants **in this rig's geometry** with ground truth real photos cannot give: per-leaflet **visible** and **amodal (full, incl. occluded)** masks, depth, organ classes and the 3D plant graph. Stage 1 = **100 scenes** + a realism gate. Purpose: training/validation data for 2D amodal leaflet completion (architecture C) and later structure fitting (B), per `CLAUDE_TOPVIEW_3D_DIFFUSION_REVIEW_2026-10-05.md` (if missing from `handoff/`, ask the user for it; do not block Steps 2–4 on it).

| Level | Tool | Decides |
|---|---|---|
| Plant structure | existing P3 engine, **imported read-only** from `tools/probabilistic_compound_growth.py` | nodes, internodes, compound-leaf attachment and direction, rachis length, left/right extents |
| **Compound-leaf interior** | **L-Py + PlantGL** | leaflet pair count, spacing, size taper, terminal and small intercalary leaflets, petiolule angles, rachis bend, leaflet longitudinal bend and transverse roll |
| Leaflet outline | contour library from human-reviewed leaflet masks | outline shape (serration, asymmetry, tip) mapped onto the PlantGL leaflet surface |
| Masks, depth, organ classes | own numpy z-buffer rasteriser from meshes + real camera model | exact per-leaflet visible and amodal masks (fast, no per-leaflet re-render) |
| RGB image | **Blender (`bpy`, headless)**; pyrender only if Blender is impossible (ask first) | realistic photo-like images |

Contract P3 → L-Py: the compound leaf must lie inside the P3 rachis length and extents (declared tolerance). Violations are **rejected and resampled**, never clipped.

---

## 2. Step 1 — Preflight and environment  → **checkpoint: report to user and wait**

1. Read: `CONVENTIONS.md`, `CLAUDE.md`, latest `handoff/LOG.md`/`TODO.md`, `tools/PROBABILISTIC_COMPOUND_GROWTH.md`, `build/ONE_PIPELINE_2026-10-01.md`, `build/al_4plants_20261002/AL4_RESULTS.md`.
2. Run the preflight test suite (§0.3).
3. Create a **separate** environment (never the project's main Python):
   - conda env `tomato_synth` (Python version compatible with `openalea.lpy` / `openalea.plantgl` from conda-forge/openalea channels) + `numpy`, `opencv`, `scipy`, `trimesh`.
   - Blender: system install or `bpy` wheel in the same env; record path/version.
   - Record `runtime_env.json` (exact versions, channels, OS). If L-Py cannot install on this PC, stop and offer the user: (a) Colab/Kaggle with conda, (b) another machine. Do not substitute another grammar silently.
4. Resource check: this PC has no NVIDIA GPU and little free RAM. Estimate render time per view at 512 px; if 100 scenes × 18 views exceeds ~3 h, propose to the user: fewer views per scene (e.g. top + 6 ring), lower resolution, or Colab/Kaggle.

**Report to the user in Korean:** env status, test baseline, time estimate, proposed scale. Wait for "진행".

---

## 3. Step 2 — Inputs (read-only)

- **Camera rigs:** real `capture.json` files (intrinsics + measured poses; keep only views that passed the pose gate) from `build/plants_dwt_test_20261002/plants/*/` and `build/plants_e2e_20261002/plants/*/`. Board frame mm, conventions in `CONVENTIONS.md` (+Z into the board).
- **Board texture:** operational 7×7 board image `build/charuco_board_7x7_190mm.png` with `config/board_spec.json` dimensions (read only).
- **Leaflet contours:** human-reviewed leaflet masks for dwt_01–04 (locate via AL4 notes / annotator batch exports). Use only masks marked fully visible; skip occluded/partial. Normalise (base at origin, midrib +x, unit length). Save `leaflet_contours.json` (+ source mask hash, plant, view) and a preview sheet.
- **Colour statistics:** existing `rgb_ratio_batch` outputs (locate under `build/`); if none usable, compute leaflet RGB stats from the same reviewed masks.
- **Trait ranges for the gate:** height ~60–90 mm, side leaf-area proxy ~10–17 cm², stem ~5.5–6.2 mm (from S8 results); confirm from files and cite them.

---

## 4. Step 3 — Generator code (`tomato3d/synth/`)

Suggested modules (adjust names if needed, keep them inside `tomato3d/synth/`):

| Module | Responsibility |
|---|---|
| `config.py` | load/validate `generator_config.json`; every range has `source_kind`, `source_ref` |
| `structure.py` | call the P3 engine (import only) with an explicitly synthetic parameter set; output plant graph JSON |
| `compound_leaf.lpy` + `compound_leaf.py` | L-Py rules for the compound-leaf interior; wrapper takes rachis length, extents, rank, seed, ranges; returns per-leaflet meshes with IDs `plant/compound/leaflet` |
| `leaflet_surface.py` | map a contour onto a bent/rolled PlantGL patch |
| `scene.py` | stem/petiole tubes, pot, board plane with texture, background |
| `raster.py` | z-buffer rasteriser: visible instance mask, amodal mask per leaflet, depth (mm), organ class mask, using the real camera model (incl. distortion) |
| `render_blender.py` | RGB per view via Blender, domain randomisation (lights, leaf colour, slight translucency, noise, white balance) |
| `manifest.py` | `manifest.jsonl` + `scene_params.csv` |
| `realism.py` | realism statistics and the gate |
| `cli.py` | `python -X utf8 -m tomato3d.synth.cli {contours,generate,render,realism} --out build/...` |

Heavy imports (`openalea`, `bpy`) only inside functions, so the core package imports without them.

---

## 5. Step 4 — Pre-declare the gate, then a 5-scene pilot  → **checkpoint**

1. Write `stage1_contract.json` **before** any rendering: scene count, views, resolution, seeds, and pass criteria, e.g.
   - synthetic medians of height, envelope area, leaflets per photo, visible leaflet area, occlusion fraction inside the real min–max;
   - existing detector v4 + SAM v5 on synthetic photos: leaflet AP50 within ±0.15 of the real plant-held-out value (≈0.74–0.77), SAM IoU within ±0.10 (≈0.82–0.86).
   Criteria may not be changed after results are seen.
2. Render 5 pilot scenes. Show the user a preview sheet (RGB + visible + amodal masks side by side) and the rejection log.

**Report in Korean and wait for "진행"** before the 100-scene run.

---

## 6. Step 5 — 100 scenes and realism gate

- Render 100 scenes per the contract. Keep every scene, including rejected ones, with reasons.
- Outputs per scene × view: `rgb.png`, `visible_mask.png` (instance IDs), `amodal/<leaflet_id>.png`, `depth_mm.npy` (or 16-bit PNG + scale), `organ_mask.png`, plus `plant_graph.json`, `meshes.obj`.
- `manifest.jsonl` row fields: `scene_id, view_id, camera_source_session, rgb, visible_mask, amodal_dir, depth, organ_mask, plant_graph, seed, parameter_hash, origin='synthetic', generator_version`.
- Run `realism.py`; write `realism_report.json/.csv` and a preview sheet. Detector/SAM inference on synthetic images: use existing weights read-only; if inference needs GPU and none is available, run on a 20-scene subset and say so.

---

## 7. Tests (`tests/test_synth_*.py`, new files only)

1. Same seed → identical plant graph, masks and manifest hashes.
2. L-Py compound leaf stays within P3 rachis length/extents; violations rejected and resampled.
3. For every leaflet and view: amodal ⊇ visible; fully hidden leaflet → empty visible, non-empty amodal; IDs consistent across views.
4. Board corners rasterised through the real camera model match `cv2.projectPoints` within a declared pixel tolerance.
5. Depth in mm, board frame; organ mask classes complete.
6. All manifest rows carry `origin='synthetic'`.
7. `import tomato3d` works in an environment **without** `openalea`/`bpy` (lazy imports), and tests that need them are skipped there, not failed.

Then rerun the full existing suite (§0.3) and compare with `tests_before.xml`.

---

## 8. Finish

- Result handoff (English): `handoff/CLAUDE_SYNTHETIC_DWARF_TOMATO_STAGE1_RESULT_2026-10-05.md` — what was built, env, contract, gate pass/fail with numbers, failures, file hashes, before/after test comparison, what to tune for Stage 2 (1,000–5,000 scenes).
- Append one line to `handoff/LOG.md` (date | Claude Code | summary | paths). Add Stage 2 to `handoff/TODO.md` only by appending.
- Korean summary to the user: gate result, main mismatches between synthetic and real, and the decision needed for Stage 2.

## Stop conditions (ask the user instead of continuing)

- Any needed change outside §0.1.
- L-Py or Blender cannot be installed locally.
- The pre-existing test suite does not pass before you start, or changes result after your work.
- Required inputs (reviewed masks, capture.json with passing poses) cannot be found.
- Estimated runtime or disk use is far above the pilot estimate.
