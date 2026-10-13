# Claude → Codex master handoff: everything Claude did, 2026-09-15 to 2026-10-03

Purpose: one entry point for Codex to take over or continue. It lists what was done, where it is, what was measured and what is still open. It points to the detailed handoff for each topic instead of repeating it.

- **Read first:**
  - §1 Goals and rules
  - §6 Current state
  - §7 Open items
- **Chat with the user:** Korean.
- **Handoff files:** English.

---

## 1. Goals and standing rules

### Research goal
Set by the user on 2026-10-01.
- 24 tomato plants.
- Outputs:
  - **whole-plant leaf area**, not per leaflet;
  - **PPFD / DLI**;
  - plant-intercepted light.
- Calibration must be **non-destructive**: ruler length × width per leaflet, and a coefficient k from a few leaflets flattened on the board.
- Minimise human review.
- Leaf-level work is optional and should not be pushed on the user: S4 pairs, cross-view identity, vein landmarks, per-leaflet 3D.

### Rules
- **Ownership:**
  - `CONVENTIONS.md`, `CLAUDE.md` and `AGENTS.md` define the split: Claude `tomato3d/` and `tests/`, Codex `tools/` and `tools/tests/`.
  - In practice, since about 09-19 the user moved many `tools/` tasks to Claude, and Claude wrote most of the auto-pipeline tools listed in §5.
  - Since 10-03, Claude's dwt_test fixes are in `build/dwt_test_fill_20261003/`, not in `tools/`.
- **Agents do not write `config/`.** The human writes `config/light_scene.json`.
- **No base or untuned models** (user, 2026-09-28): use the user's labels and our tuned models (§4). If a fair held-out model is missing, retrain one on Kaggle.
- **Git push only when the user says so in that turn:**
  - repo `fish-444/tomato`, branch `claude/tomato-pipeline-20260929`;
  - local clone `build/github_tomato_20260929/`;
  - code and small results only: no photos, masks, weights or credentials.
- **Board pose is the authority; SfM is advisory.** SfM alignment failed for all four plants.
- **XL / GroIMP freeze** (09-28): Claude does not edit `groimp_structure_export.py`, `groimp_static_verify.py` or `groimp_bridge.py`. These are Codex files.
- **Never enter credentials.** For Colab, the user picks `Downloads/kaggle_colab.json`, a copy of `~/.kaggle/kaggle.json`. The older `Downloads/kaggle*.json` keys get 403.
- **Kaggle and Colab uploads and collection belong to Claude** (user, 10-01). Codex may read the results.
- Long local jobs: start them detached (PowerShell `Start-Process`). Background shells get killed when only about 3 GB of RAM is free.
- **Kaggle CLI:** set `PYTHONUTF8=1`. Otherwise logs come out as 0 bytes because of cp949 errors.

---

## 2. Timeline

### 09-15 – 09-16: setup, board and protocol
- Shared working agreement: `CONVENTIONS.md`, `CLAUDE.md`, `AGENTS.md`.
- Board divergence recorded; the human chose **ChArUco 7×7, 190 mm**. Claude rewrote `config/board_spec.json` (schema 1.1).
  - Claude's own error: that file first failed `BoardSpec` validation. The fix spec is in `CLAUDE_CODE_FIX_BOARDSPEC_2026-09-16.md`.
- `board_variant_id` made mandatory in session manifests.
- Stage 1 (`io`, `calib`, `mask`) review:
  - R1, R3 and R4 fixed with mutation-checked regressions;
  - R2 fixed only as a fail-closed interim.
  - See `CLAUDE_CODE_STAGE1_REVIEW_RESPONSE_2026-09-16.md`.
- Turntable angle strip PDF, shooting-day checklist, conference schedule (deadline 10-31) and the RNN design memo, all in `docs/`.

### 09-17: light track
- `tomato3d/light/` and `python -m tomato3d.cli.run_light`. They take value/status/source for every environment variable, and "unavailable" is never 0.
- Leaf point annotator artifact.
- See `CLAUDE_CODE_LIGHT_PIPELINE_HANDOFF_2026-09-17.md` and `CLAUDE_BRIEF_3D_LEAF_LIGHT_CALCULATOR_2026-09-17.md`.

### 09-19 – 09-21: manual 3D tools
- Leaflet bbox, diagnostic cuboid and XYZ in the existing editor/rebuild/viewer: `build/photos1_manual3d_20260919/edit_session07`, `edited_roundtrip08`. Serve on port 8821.
- Hybrid ChArUco leaflet reconstruction and the three-route fusion briefs (09-20).
- Compound-leaf membership in `leaf_point_annotator.html`. It reads COCO polygons; sub-stem is the attachment evidence.
- Held-out board geometry check on dwt_01/02:
  - held-out board points triangulate at a median of 1.5–2.2 mm;
  - the trial intrinsics' principal point is about 400 px off.
- GroIMP 2.2.1 headless API set up: port 58081, Temurin 21.

### 09-22 – 09-26: dwt_01–04 pipeline (S0–S7)
- `tools/plant_pipeline.py --all` builds `build/pipeline_<ts>/` with `STATUS.md`, `HUMAN_TASKS.md` and `site.html`.
- Compound naming is **bottom-up**: L01 is the lowest leaf, and the unfolding leaf takes the top id.
- Human-check loop: a review artifact saves `human_checks_*.json` to Downloads, and `tools/human_check_watcher.py` reruns the pipeline.
- Codex led the sensitivity web UI until 09-26. See `CLAUDE_LEAD_HANDOFF_UNTIL_2026-09-26_1800_KST.md`.

### 09-27 – 09-29: models, offload, decision learning
- Kaggle training runs:
  - leaflets4-obb: held-out mAP50 0.81–0.86;
  - leaflets4-sam: median IoU about 0.90;
  - organ detector v4 (`dolgfish/tomato-organ-v4-{full,window,tiles}`), trained on 1,163 reviewed masks;
  - stem model.
- Heavy-compute offload design: `CLAUDE_HEAVY_COMPUTE_OFFLOAD_DESIGN_2026-09-28.md`; `tools/offload_job.py` is used by `plant_auto --offload kaggle-gpu`.
- `tools/plant_auto.py`: a photo-only run, from 18 photos to S0–S8.
- `tools/decision_learning.py` auto-accepts about 64 % of masks at 95.6 % precision. It never auto-rejects.
- S3 fixes:
  - `stem_from_hull` fallback;
  - drop a photo when the hull explains less than 80 % of its silhouette;
  - `stem_completion`.
- Documents:
  - `build/NEW_PLANT_WORKFLOW_2026-09-29.md`;
  - `build/PIPELINE_3D_OVERVIEW_2026-09-29.html`;
  - `CLAUDE_CODE_REVIEW_2026-09-29.md`;
  - XL light phase 1 passed; phase 2 documents dated 09-29.
- User decision: the top compound region of dwt_01 and dwt_03 is `growing_leaf`.

### 09-30: leaf surface and masks
- Leaf vein results, RGB preprocessing and midrib, mask-learning scope, MATLAB/Simulink study, human masks for Codex, and density / first-flowering notes. See the `CLAUDE_*_2026-09-30.md` files.

### 10-01: one pipeline, photos to traits (S8)
- `tools/plant_batch.py --photos-root <dir>`: one folder per plant. It skips finished plants, resumes stopped ones and continues past failures.
- `plant_auto` S0b: marker-corner pose rescue (`tools/marker_pose_rescue.py`, copy in `pose_session`).
- S8 `tools/plant_traits.py`:
  - takes the union of all non-rejected leaflet masks per photo;
  - converts pixels to area with the hull depth;
  - computes the side-ring mean proxy, top area, footprint, volume, height and stem diameter.
- Calibration k comes from `measurements/leaf_area.csv` and DLI from `measurements/light.csv`. Templates and a README are in `measurements/`.
- Four-plant run `build/pipeline_20261001_s8`: proxy 16.85 / 11.06 / 16.29 / 19.62 cm².
- Docs: `build/ONE_PIPELINE_2026-10-01.md` and `CLAUDE_ONE_PIPELINE_S8_2026-10-01.md`.

### 10-02
- **End-to-end test**, `build/plants_e2e_20261002`:
  - raw dwt_01 photos only, about 1 h 16 min on local CPU;
  - −2 % against human masks on the same photos;
  - but the models had seen dwt_01.
- **dwt_01 human-in-the-loop AL**, 8 rounds on Colab (`build/al_dwt01_20261001/AL_RESULTS_2026-10-02.md`):
  - dwt_02 detector AP50 rose 0.430 → 0.523, mostly after at least 8 of 14 photos were corrected;
  - SAM IoU stayed flat at about 0.83, so the detector is the bottleneck.
- **PPFD validation**: `tools/ppfd_validation.py`; see `CLAUDE_PPFD_VALIDATION_COMPLETION_2026-10-02.md`.
  - GroIMP facts:
    - PhysicalLight is broken on the CPU LightModel;
    - AreaLight on a Parallelogram is an exact cos^(m) emitter.
  - All real inputs are still missing.
- **Landmark hypothesis check** (read-only, `CLAUDE_LANDMARK_HYPOTHESIS_CHECK_2026-10-02.md`):
  - with a pose RMS of 8–8.6 px, epipolar distances do not discriminate;
  - one boundary point per pair is not a surface.
- **Four-plant model-only leaf area**: see §3.
- Colab control: `googlecolab/colab-mcp` registered, but `open_colab_browser_connection` returned false twice. Chrome clicking was used instead.

### 10-02 – 10-03: dwt_test T1–T3 (new capture)
See §3.2.

---

## 3. Latest results

### 3.1 Four plants: model-only leaf area vs human masks
Source: `build/al_4plants_20261002/AL4_RESULTS.md` and `kout/results.json`.

| Item | Detail |
|---|---|
| Models | LOPO start: organ v4 `full_lopo_<P>` + SAM v5 decoder `heldout_<P>` |
| Trait | S8 side proxy, fixed S3 hull from `pipeline_20261001_s8` |
| Script | `build/al_4plants_20261002/kernel/train.py` (env `AL_MAX_STEP`; 0 = model-only) |
| Notebooks | Drive `tomato_al_4plants_v4.ipynb` (AL) and `tomato_al_4plants_v5_step0.ipynb` |

| Plant | Human | Model | Error |
|---|---|---|---|
| dwt_01 | 16.84 | 16.58 | −1.5 % (per-photo errors cancel; photo 28 is −19.5 %) |
| dwt_02 | 11.06 | 12.90 | **+16.6 %** (6 of 7 photos over) |
| dwt_03 | 16.29 | 16.75 | +2.8 % |
| dwt_04 | 19.61 | 19.97 | +1.8 % |

- One common factor (1.049) leaves −6 / +11 / −2 / −3 %. Correlation across plants is r = 0.984.
- Three plants fall within ±3 %, which calibration can absorb. dwt_02 is an outlier; its cause has not been checked.
- AL retraining helps area mainly by replacing the posed side photos with human masks. That curve was stopped at dwt_02 step_1 because it adds little for area.
- **Caveat:** the truth here is human masks on the same photos, not measured leaf area.

### 3.2 dwt_test T1–T3 (captured 2026-10-02)
Source: `build/plants_dwt_test_20261002/DWT_TEST_RESULTS.md`.

**Inputs**
- Photos: Drive `dwt저장/dwt_test/T1..T3`, 18 HEIC each. The user downloaded them to `tomato_photos_by_view_/dwt_test/T*-…/T*/`.
- Run copies: `build/dwt_test_photos_20261002/dwt_t1..t3/`.
- Growth records:
  - run copies are the `growth.json` files;
  - **`is_unfolding` was inverted** because the user said they entered it reversed;
  - the T2 date was corrected from 2026-09-20 to 2026-10-02;
  - the original JSONs are unchanged.

**Run**
- `plant_batch` on local CPU, about 2.7 h. Output: `build/plants_dwt_test_20261002/`.

**Finding 1 – capture order is not the protocol**
- Measured elevations put the top photos (83–89°) at 27/28 for T1 and T3, and at 17/18 for T2.
- The two rings are at about 20–45°.
- `plant_auto` maps EXIF order to protocol codes. So `plant_traits`' code-prefix groups mixed top and ring photos for these plants.
- The earlier dwt_01–04 captures did follow the protocol.

**Finding 2 – T3: the pot moved twice on the hand-held board**
- Three groups, each self-consistent (S3 silhouettes 87–100 %), that disagree with each other:
  - A = 01–16
  - B1 = 17–23
  - B2 = 24–28
- `build/dwt_test_fill_20261003/pose_fill.py`:
  - filled 6 poses (17, 18, 21, 22, 23, 25) with marker PnP;
  - each candidate had to pass a ring prior on elevation, distance and azimuth;
  - result: 9–14 inliers, 2.9–3.9 px.
- `align_groups.py`:
  - found the plant motion for B1 (θ −1.5°, shift (−8.0, −3.5) mm);
  - B1 silhouettes went from 70–81 % to 82–91 %;
  - B2's best rigid fit (θ −100°, 20 mm) reached only 65–83 %, so B2 was **not merged**.
- `group_session.py` writes pose-subset sessions and their configs.
- A+B1 run (`plants/dwt_t3/pipeline_AB1`): hull from 11 photos; compounds L01–L04 match the growth record.

**Traits by measured elevation**
Source: `regroup_traits.py` → `traits_by_elevation.csv`. Model only, not calibrated.

| Plant | Ring leaf area (16 photos) | Top (2) | Hull cm³ | Footprint cm² | Height mm | Stem mm |
|---|---|---|---|---|---|---|
| dwt_t1 | 11.77 | 10.03 | 68.7 | 23.6 | 77 | 6.19 |
| dwt_t2 | 13.99 | 17.50 | 81.3 | 37.8 | 62 | 5.48 |
| dwt_t3 | 13.35 | 16.11 | 59.6 (A+B1) | 33.7 | 71 | 5.78 |

- The rings at 20–45° are lower than the old side ring (about 50°). **Do not compare dwt_test proxies directly with dwt_01–04**; calibrate within one capture style.
- T2 has 6 compound regions against 4 recorded, so they stay unnamed.
- The first batch table (`traits/traits.csv`) uses code-prefix groups and is superseded for the dwt_test plants.

---

## 4. Models in use (tuned, no base models)
- **Organ detector v4:**
  - full model plus a 2×2 tile model with per-class scale rules;
  - mean AP50 0.55 (compound 0.88, leaflet 0.76, petiole 0.46, main stem 0.44, growing point 0.23);
  - LOPO weights `full_lopo_dwt_0N.pt`;
  - paths are in `tools/plant_auto.py` (`DEFAULT_MODELS`, `DEFAULT_TILE_MODELS`).
- **SAM 2.1 tiny, v5 decoder**, tuned on 1,163 human masks; held-out `sam2_tiny_decoder_tuned_heldout_dwt_0N.pt`.
- **Mask decision model:** `DEFAULT_MASK_MODEL`.
- **Kaggle datasets:**
  - `dolgfish/tomato-al-4plants` (LOPO weights, `capture_*.json`, `hull_*.csv`, `al4_train.py`);
  - `tomato-organ-v4`, `tomato-leaflets-v5`, `tomato-leaflets-4plants`, `tomato-split-exp-photos`;
  - `dolgfish/tomato-al-start-weights`.

## 5. Main tools Claude wrote or extended (in `tools/`)
- **Pipeline:** `plant_batch.py`, `plant_auto.py`, `plant_pipeline.py` (S0–S8), `plant_traits.py` (+5 tests).
- **S3 and poses:** `marker_pose_rescue.py`, `plant_structure.py` (S3 view selection, `stem_from_hull`), `stem_completion.py`.
- **Learning and offload:** `decision_learning.py`, `offload_job.py`, `organ_detector_dataset.py` (`--v4` / `--stems --from-config`).
- **Review and output:** `human_check_watcher.py`, `plant_site.py`, `ppfd_validation.py`.
- **Edits to Codex tools:** the leaf editor, `leaflet_mask_batch` and `serve_leaf_edit_session`, made when the user transferred those tasks. Logged in `LOG.md`.

---

## 6. Current state (end of 2026-10-03)
- No job is running. The Colab sessions ended, and the Kaggle weekly GPU quota resets on 2026-10-03.
- Human inputs still missing:
  - `measurements/leaf_area.csv` (4–6 plants, non-destructive);
  - `measurements/light.csv`;
  - `config/light_scene.json`.
- So every leaf-area value is an uncalibrated proxy and every pose is diagnostic: 0 photos pass the 1 px gate, and residuals are 5–10 px.
- Only 7 of 24 plants have photos (dwt_01–04 and dwt_test T1–T3).

## 7. Open items (suggested order)
1. **Fix capture-order handling in the pipeline** (in `tools/`, owner to be decided):
   - assign top/ring groups from measured elevation when poses exist, instead of from code prefixes. The reference logic is `build/dwt_test_fill_20261003/regroup_traits.py`;
   - or check the order at S0 and warn.
2. **Detect a moving plant mid-capture:**
   - flag self-consistent photo groups that disagree with each other;
   - optionally run the plant-motion alignment. The reference is `align_groups.py`; use its fast search score at 1/4 scale.
3. **The 24-plant run** once photos exist: `python -X utf8 -m tools.plant_batch --photos-root <dir> --offload kaggle-gpu`.
4. **Calibration:** once `leaf_area.csv` is filled, run `tools.plant_batch --out <run> --summary-only`. Calibrate within one capture style (dwt_test style vs the dwt_01–04 style).
5. **The dwt_02 +16.6 % outlier:** cause unknown. Candidates are the small plant and the known label issue (one bottom compound box covers two compounds, so a relabel is needed).
6. **T3 B2 (24–28):** non-rigid change, unresolved. Low priority, because whole-plant traits already use B2's per-photo areas.
7. Capture guidance for the user:
   - shoot in protocol order;
   - keep the pot fixed on the board, so that the pot and the board turn together.
8. Pending from earlier:
   - task #16 (English completion handoff for the CLAUDE_MASK_LEARNING prompt);
   - optional leaf-level work (S4 pairs, name checks, dwt_02 conflicts).

## 8. Detail documents (most recent first)
- `build/plants_dwt_test_20261002/DWT_TEST_RESULTS.md`
- `build/al_4plants_20261002/AL4_RESULTS.md`
- `handoff/CLAUDE_SESSION_HANDOFF_2026-10-02.md`
- `handoff/CLAUDE_PPFD_VALIDATION_COMPLETION_2026-10-02.md`
- `handoff/CLAUDE_LANDMARK_HYPOTHESIS_CHECK_2026-10-02.md`
- `build/al_dwt01_20261001/AL_RESULTS_2026-10-02.md`
- `build/ONE_PIPELINE_2026-10-01.md`
- `handoff/CLAUDE_ONE_PIPELINE_S8_2026-10-01.md`
- `build/NEW_PLANT_WORKFLOW_2026-09-29.md`
- `build/PIPELINE_3D_OVERVIEW_2026-09-29.html`
- `handoff/CLAUDE_CODE_REVIEW_2026-09-29.md`
- `handoff/CLAUDE_HEAVY_COMPUTE_OFFLOAD_DESIGN_2026-09-28.md`
- `handoff/CLAUDE_USER_PROPOSED_FIXES_2026-09-28.md`
- `handoff/CLAUDE_LEAD_HANDOFF_UNTIL_2026-09-26_1800_KST.md`
- `handoff/CLAUDE_DWT01_04_PIPELINE_PLAN_2026-09-22.md`
- `handoff/CLAUDE_CODE_LIGHT_PIPELINE_HANDOFF_2026-09-17.md`
- `handoff/CLAUDE_CODE_STAGE1_REVIEW_RESPONSE_2026-09-16.md`
- The full list is `handoff/CLAUDE_*.md`; one line per action is in `handoff/LOG.md`.
