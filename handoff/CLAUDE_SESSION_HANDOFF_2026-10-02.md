# Claude session handoff (2026-10-02, ~15:40 KST) — read this first in the next session

The user ended this session so the next one loads the new **colab-mcp** server. Chat in Korean; handoff files in English.

## 1. Running right now (do not restart it)

**4-plant human-in-the-loop + S8 leaf-area experiment, on Colab (T4).**

- Colab notebook: Drive `tomato_al_4plants_v4.ipynb`, id `1VdX0JpMENuiTbfuUcBktstopd4CDewDZ`. It is open in the user's Chrome tab.
- Script: `build/al_4plants_20261002/kernel/train.py`. A copy, `al4_train.py`, is in Kaggle dataset `dolgfish/tomato-al-4plants`, together with:
  - LOPO start weights: `full_lopo_dwt_0N.pt` and `sam2_tiny_decoder_tuned_heldout_dwt_0N.pt`;
  - `capture_dwt_0N.json` (pose_session poses);
  - `hull_dwt_0N.csv` (S3 hull from `build/pipeline_20261001_s8`).
- Output: Drive `MyDrive/tomato_al_4plants/`. `results.json` is rewritten after every step. `log.txt` holds the filtered lines, plus the last 60 lines if the run fails.
- Design: per plant P (dwt_01..04):
  - start from models that never saw P;
  - correct 0, 1/4, 2/4, 3/4, then all of P's photos, most uncertain first;
  - retrain from P's start models each step (12 retrainings in total);
  - score on P's uncorrected photos (AP50, SAM IoU, end-to-end, correction effort);
  - per step, compute the S8 side-ring leaf-area proxy. Human masks are used for corrected photos and model masks for the rest, with the fixed hull. Compare against `truth` (all human masks).
- Status at handoff: training had started. The first line was `dwt_01 truth 16.84 cm2 side, 4 posed`; it matches the pipeline's 16.85, so the coordinate frames line up. Expected total time is about 3 h.
- If the Colab session drops: open the notebook and choose **런타임 > 모두 실행**. It resumes from `results.json`.
  - The user allows Drive access.
  - The user picks `Downloads/kaggle_colab.json`, a copy of `~/.kaggle/kaggle.json`. The older `Downloads/kaggle*.json` keys get 403.
  - Never enter the key yourself.
- The 30-minute cron check of this session (`2a415520`) dies with this session. **Re-create a check in the new session**, or poll with colab-mcp / Drive (`search_files title = 'results.json'` in folder `tomato_al_4plants`).
- When all 4 plants reach `step_4`:
  - save the results to `build/al_4plants_20261002/kout/results.json`;
  - write `build/al_4plants_20261002/AL4_RESULTS.md` (Korean) with one table per plant: corrected photos, uncorrected det mean AP50 / leaflet AP50 / SAM IoU / e2e IoU, effort per photo, leaf area and % error vs human truth;
  - compare with the dwt_01 result below;
  - add a LOG line.

## 2. New tool: colab-mcp

- Cloned to `C:\Users\sho36\colab-mcp`. Registered with `claude mcp add --scope user colab-mcp -- uv run --directory C:/Users/sho36/colab-mcp colab-mcp`; it shows as Connected.
- It exposes `open_colab_browser_connection`. That tool opens `colab.research.google.com/notebooks/empty.ipynb#mcpProxyToken=..&mcpProxyPort=..` in the browser. Once the page connects back over a localhost websocket, notebook-editing tools appear (tools/list_changed).
- Untested: whether the same `#mcpProxyToken` fragment works on an existing notebook (e.g. the v4 one) rather than the scratch notebook. Try it before falling back to Chrome clicking.
- The user wants Colab driven this way. Kaggle's weekly GPU quota resets on **2026-10-03**; use Colab until then. Kaggle and Colab are both Claude's job (Codex does not touch them).

## 3. Finished this session

- **One pipeline, photos to traits** (`build/ONE_PIPELINE_2026-10-01.md`, handoff `CLAUDE_ONE_PIPELINE_S8_2026-10-01.md`):
  - `tools/plant_batch.py`: all plants, skip / resume / continue;
  - `tools/plant_auto.py`: S0b marker-pose rescue built in;
  - `tools/plant_pipeline.py`: S8 traits; HUMAN_TASKS split into required / optional;
  - `tools/plant_traits.py` + 5 tests;
  - `measurements/` templates for the person: `leaf_area.csv`, `light.csv`.
  - 4-plant run: `build/pipeline_20261001_s8`. Leaf-area proxy 16.85 / 11.06 / 16.29 / 19.62 cm².
  - End-to-end photo-only test: `build/plants_e2e_20261002`. 1 h 16 min on local CPU; −2 % vs human masks on the same photos (models had seen dwt_01).
- **dwt_01 human-in-the-loop (Colab, 8 rounds)** (`build/al_dwt01_20261001/AL_RESULTS_2026-10-02.md`):
  - dwt_02 detector AP50 rose 0.430 → 0.523, mostly after ≥ 8 of 14 photos were corrected.
  - SAM IoU stayed flat at ~0.83, so the detector is the bottleneck.
  - Correcting costs less than drawing from scratch only at ~12 / 14 photos.
- Colab fixes, now built into v4:
  - a cancelled upload left an empty `kaggle.json`;
  - an old key gave 403;
  - `kernels output --file-pattern` found nothing on Colab, so the start weights are now datasets downloaded per file (`-f`).
  - A newly created Kaggle dataset can 404 on whole-zip download for a few minutes; per-file download works at once.

## 4. Next (in order)

1. Collect and write up the 4-plant result (section 1).
2. After the Kaggle reset (10-03): 24-plant runs with `python -X utf8 -m tools.plant_batch --photos-root <dir> --offload kaggle-gpu` once the photos exist. Local CPU takes about 1 h per plant.
3. The person fills in `measurements/leaf_area.csv` (4–6 plants, non-destructive) and `light.csv`. Then run `tools.plant_batch --out <run> --summary-only`.
4. Task #16: English completion handoff for the CLAUDE_MASK_LEARNING prompt.
5. Optional, leaf-level only: S4 pairs, name checks, dwt_02 conflicts. Do not push these on the user.

## 5. Standing rules (unchanged)

- Git push only when the user says so. Target: `fish-444/tomato`, branch `claude/tomato-pipeline-20260929`; code and small results only.
- No base (untuned) models; build on our tuned models.
- Do not edit Codex XL files: `groimp_structure_export.py`, `groimp_static_verify.py`, `groimp_bridge.py`.
- Do not write `config/`.
- Board pose is the authority; SfM is advisory.
- Never enter credentials into any field.
- Upload prepared training kernels without asking.
- Background shells get killed when memory is low. Launch long local jobs detached (PowerShell Start-Process) and watch them with Monitor.
