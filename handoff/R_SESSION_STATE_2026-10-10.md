# Prompt R — session state (2026-10-12: R.1/R.2 COMPLETE)

## Final state (read this first)
- 600 synthetic side views (150 scenes x 4) generated, rendered and finalized in build/sideprop_20261009_01/:
  per-view rgb.png + layers + labels.json, yolo/images + yolo/labels (600 each), synside_coco.json,
  labels_manifest.csv, manifest.jsonl, R2_label_summary.json (quadrant check exact on 3,247 samples).
- Render quality: batches a/b (scenes 0-99) 64 spp, batch c (100-149) 16 spp (R_contract R-A3; R-A3e corrects
  its reason: rendering took ~15 min per batch, the hours were Kaggle's post-run phase). Per-view field
  cycles_samples records which.
- Generation: scenes 0-34 local Windows, 35-149 Colab CPU (R-A2; platform probe exact).
- Nothing is pending on Kaggle/Colab; no cron is running.
- Next (human): label the 52 real side photos per real_eval/LABELING_GUIDE_ko.md in tom_side_seg_bbox; confirm the
  real capture rotation. Then R.5 (R5_training_plan.md + Amendment 1) can run: real-only vs synthetic-only vs
  synthetic+real on the real held-out set (dwt_102/103/111/112).
- Known realism gaps (decide before R.5 if they should be fixed by a re-render; labels would not change for colour
  fixes): dark round pot, dark soil, gray walls vs real translucent white square pot, orange soil, white paper;
  pale smooth leaves and bright-green stems; O-mature 6-8 compounds per plant vs real ~4-5.

---
(history of the session below)

# Prompt R — session state (2026-10-10, Claude Code; updated during R.1)

Prompt: `handoff/CLAUDE_CODE_CLI_PROMPT_R_SIDEVIEW_DIRECTION_SET_2026-10-09.md`.
User decisions: `handoff/R_DECISIONS_2026-10-10.md` (N/O records; R.1 on O-mature; rotation; compound_unclear).
Run folder: `build/sideprop_20261009_01/`. Read `R_contract.json` (incl. amendment R-A1) before touching anything.

## Done
- N/O records (decision 1): `_05_03/c6_steps.csv` rows N, O, NO; `_05_03/C6_REPORT.md` "Addendum N/O"; LOG line.
- R.0 contract + amendment R-A1 (decisions 2-4); declared text byte-identical (sha before a53f68fd1a44...).
- R.3 `tomato3d/synth/sideview.py` (+ `tests/test_synth_sideview.py`, 11 pass, project env).
- R.4 `real_eval/` split (now with `capture_rotation`), labeling guide; R.5 plan + Amendment 1.
- Pre-render check PASSED (`R1_precheck.json`): cy p50 0.438 in [0.42, 0.58]; plant_frac 0.067 vs real 0.072,
  bbox_h 0.352 vs 0.375, bbox_w 0.401 vs 0.402.

## STOPPED 2026-10-10 ~16:10: memory-pressure reaper
Claude Code killed the background generation shell while the session was idle (free RAM ~0.6 of 15.6 GB).
35/150 scenes DONE (scene_0000-0034, 0 rejected); scene_0035 half-built (rebuilt from its seed on resume).
Do NOT restart without the user's go. Options the user can pick: free memory (close heavy apps) and ask for a
foreground run in 10-scene chunks (the idle reaper only stops background shells), or start Claude Code with
CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1 in its environment. Collect on the 35 scenes: 942 boxed compounds,
unclear 19.9 %, classes balanced, R.3 quadrant check exact on 771 samples (`R2_label_summary.json`).

## Remote generation on Colab CPU (user request, R_contract amendment R-A2)
- Notebook (user's Drive, Colab Notebooks): https://colab.research.google.com/drive/170hzmeL6pjFY6wb8zDgT9NueD9scPxcH
  (source: build/sideprop_20261009_01/remote/make_notebook.py -> synside_colab_cpu.ipynb). The person keeps the CPU
  runtime, chooses Runtime > Run all, picks Downloads/kaggle_colab.json, keeps the tab open until `UPLOADED`.
- Inputs: private dataset dolgfish/tomato-synside-gen-inputs (remote/make_bundle.py; record remote/bundle_record.json).
- Results: dolgfish/tomato-synside-gen-out (synside_gen_out.zip, paths relative to the project root);
  failures: dolgfish/tomato-synside-gen-diag (diag.zip with logs and reports).
- Pick-up when gen-out is ready (remote/poll_gen_out.sh downloads it; refuses unless the remote probe passed,
  removes only local half-built scenes such as scene_0035, never overwrites a DONE scene, then runs collect):
  ```bash
  cd "/c/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis"
  bash build/sideprop_20261009_01/remote/poll_gen_out.sh        # or download by hand into the folder below
  PYTHONPATH=. python -X utf8 build/sideprop_20261009_01/remote/pickup_gen_out.py "$LOCALAPPDATA/Temp/synside_stage/gen_out"
  ```
  then the Kaggle render batches a/b/c below.
- colab-mcp: `open_colab_browser_connection` returned false (the tab never connected back within 60 s). Its logs show
  no successful browser connection in any past session either, so the Drive notebook is the working route.

## Colab result pickup (status 2026-10-10 20:07)
- Colab finished scenes 35-149 (115/115, probe exact). Kaggle registered all 14,059 files of
  dolgfish/tomato-synside-gen-out but still reports size 0, so the whole-dataset download answers 404.
- A session cron (job c4c84813, minutes 7/27/47) checks in the foreground and runs the pickup once size > 0. It dies
  with the Claude session. In a new session run `bash build/sideprop_20261009_01/remote/fetch_gen_out.sh` in the
  FOREGROUND, or, if the size stays 0, re-zip the dataset in a Kaggle CPU kernel and fetch it with `kaggle kernels output`.

## Render status (2026-10-11 15:54)
- All 150 scenes generated and picked up (R2_label_summary.json; quadrant check exact on 3,247 samples).
- Kaggle T4 kernels dolgfish/tomato-synside-render-a/-b RUNNING since 15:17 at 64 spp; -c waits for a GPU slot
  (Kaggle allows 2) and renders at 16 spp (R_contract amendment R-A3, user decision 2026-10-11).
- One step = `bash build/sideprop_20261009_01/kaggle/render_step.sh` (foreground): downloads + finalizes finished
  batches into the run folder (rgb.png, yolo/images, yolo/labels), pushes c when a slot frees, logs to
  kaggle/klog/render_steps.log. Session cron 7c00ca81 runs it every 20 min (dies with the session).

## In flight (check in this order)
1. Generation (tomato_synth env, ~35 s/scene, one process at a time - the machine has ~1 GB free RAM):
   `tail build/sideprop_20261009_01/generate.log`; done scenes = `ls build/sideprop_20261009_01/scenes/*/DONE | wc -l`.
   Resume any gap (DONE/REJECTED scenes are skipped, half-built ones are rebuilt):
   ```bash
   cd "/c/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis"
   PY="$USERPROFILE/miniforge3/envs/tomato_synth/python.exe"; export PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1
   "$PY" -X utf8 -m tomato3d.synth.sideview generate --out build/sideprop_20261009_01 --start 0 --count 150
   ```
2. Kaggle batches (a = scenes 0-49, b = 50-99, c = 100-149), each when its 50 scenes are DONE:
   ```bash
   STAGE="$LOCALAPPDATA/Temp/synside_stage"          # outside OneDrive
   python -X utf8 build/sideprop_20261009_01/package_side_batch.py a "$STAGE"
   kaggle datasets create -p "$STAGE/synside_a/dataset" --dir-mode zip -q
   kaggle datasets status dolgfish/tomato-synside-jobs-a        # wait for "ready"
   kaggle kernels push -p build/sideprop_20261009_01/kaggle/kernel_a
   bash build/sideprop_20261009_01/kaggle/poll_side_batch.sh a   # background; downloads to kaggle/kout_a/
   ```
   `kaggle/batches.json` records what was staged; `kaggle/klog/status_<b>.log` the polling.
3. After each download: extract `kaggle/kout_<b>/renders.zip` with Python zipfile (the CLI's own extraction stalls
   on OneDrive) to a scratch dir, then
   `"$PY" -X utf8 -m tomato3d.synth.sideview finalize --out build/sideprop_20261009_01 --renders <dir>/synside`
   (idempotent; writes rgb.png, yolo/images + yolo/labels, re-runs collect, fails loudly if the R.3 quadrant check
   is not exact).

## Findings to report (not fixed)
- Background domain gap visible only in side views: synthetic pot is a near-black round cylinder, soil dark brown,
  walls gray with a dark floor beyond the sheet; real side photos show a translucent white square pot, orange-brown
  granular soil, white paper, a ruler and a box. Changing pot/soil colour = renderer change + re-render only (labels
  unchanged); changing pot SHAPE changes occlusion, so labels too. User decision.
- O-mature draws 6-8 compounds/plant vs real ~4-5 (user_stated): more boxes per synthetic image (caveat in R-A1).

## Open for the human
- Label the 52 real side photos (guide `real_eval/LABELING_GUIDE_ko.md`); R.5 training waits for them.
- Real capture rotation stays `clockwise_assumed_unverified` until someone checks it.
