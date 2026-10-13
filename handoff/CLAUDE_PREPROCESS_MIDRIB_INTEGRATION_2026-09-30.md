# Claude handoff: preprocessing comparison and midrib-analysis integration

Date: 2026-09-30
Status: recovered smoothing summary; full result archive recovery in progress.
Detailed implementation and execution history: `handoff/CLAUDE_SMOOTHING_COMPARISON_2026-09-29.md`.

## Read this first

The user requests downloaded comparison outputs and a handoff connecting preprocessing to within-leaf midrib analysis. No model training is authorized. Keep heavy inference on Colab. Preserve source images, labels, accepted masks, calibration and weights. No GitHub push.

The frozen comparison uses dwt_01-held-out detector/SAM weights packaged on 2026-09-29. Do not silently replace them with later v5 weights or compare v4 preprocessing changes against a v5 baseline.

## What is implemented

1. `tools/preprocess_study.py`: raw, mean 3x3, Gaussian 5x5 sigma 0.8, Gaussian 9x9 sigma 1.2, separable SG window 5/7 degree 2, and bilateral strength 12. RGB processing acts on Lab L before converting back to RGB; no-op raw preserves original pixels.
2. Tone variants: none, gamma 0.85, gamma 1.15, Lab-L CLAHE 1.5 with 8x8 tiles. Gamma and CLAHE are separate conditions, not stacked. Exposure is fixed at 0 EV in the current quantitative comparison.
3. Scalar diagnostics: linear-RGB luminance plus R/(R+G+B), G/(R+G+B), B/(R+G+B) from original stored RGB. Calculate ratios before smoothing; retain numeric SG overshoot and clip display only. Use common valid mask support and exclude insufficient filter neighbourhoods.
4. Existing `leaf_preprocess_lab` UI: smoothing/tone settings, original/processed/difference/scalar views, full-image or selected leaflet display, explicit derived saves, source/provenance hashes and existing coordinate mapping.
5. `tools/preprocess_compare.py`: fixed inference settings, per-photo/class detector metrics, per-observation SAM mask metrics, review flags, timing, source audit and resumable caches.
6. `tools/preprocess_colab.py`: frozen inputs, GPU notebook and strict complete-result import.

## Observed results; do not promote the pilot alone

The four-photo pilot used 71 reviewed masks per condition. The expanded comparison used 14 photos and 268 reviewed mask observations per condition, seven conditions, one plant. These are photo observations, not 268 physical leaves or 14 independent plants.

The expanded result is recovered from saved Colab stdout, with 98 per-photo records reconciled against denominators. Runtime: 1,678.24 s. Its original artifact ZIP was not recovered from the expired session. Treat this as recovered numerical evidence until the rerun archive is downloaded and audited.

| Condition | Production AP50 | Mean mask IoU | Mean mask Dice |
|---|---:|---:|---:|
| Raw | 0.378258 | 0.840080 | 0.901007 |
| Mean 3x3 | 0.424784 | 0.834666 | 0.897156 |
| Gaussian 5x5 | 0.420356 | 0.836319 | 0.898054 |
| Gaussian 9x9 | 0.446407 | 0.832307 | 0.896076 |
| SG-5 | 0.410737 | 0.836960 | 0.899317 |
| SG-7 | 0.421122 | 0.830594 | 0.894187 |
| Bilateral 12 | 0.385873 | 0.832526 | 0.895838 |

Raw gives the best mask IoU/Dice; Gaussian 9x9 gives the best detection score. SG-5's pilot-only mask gain does not persist. The prespecified tone candidate selection is therefore raw plus Gaussian 9x9, subject to checking the regenerated full results. No default is changed.

AP50 is evaluated after existing production confidence filtering (>=0.25), not a conventional low-confidence training-report AP. References are human-accepted, model-assisted masks. Parameter selection on dwt_01 is exploratory even though the model excluded that plant in training. Merge flags are review heuristics, not established anatomical mistakes.

## User-proposed midrib branch: proposed ablation, not established improvement

```text
Original RGB
  +--> SG on Lab L --> fixed detector/SAM --> proposed leaflet mask
  |                                         |
  +--> raw detector/SAM baseline ------------+--> reviewed/chosen mask
  |                                               |
  +--> original-pixel RGB + that mask as ROI <------+
        +--> unchanged RGB/luminance
        +--> separate gamma / contrast variants
        +--> original stored-RGB fraction maps
                    |
          controlled Gaussian / ridge candidates
                    |
          visible base-tip path and human review
                    |
          cross-view physical-landmark confirmation
```

- SG is an image preprocessing filter, not an annotation algorithm. Compare SG-generated masks with raw-generated masks; current expanded evidence does not justify preferring SG.
- Transfer the selected mask through the established inverse crop/resize transform. Smoothing itself does not move pixels. Keep the full-resolution coordinate system, source observation ID, mask revision, model hash, candidate and threshold/sensitivity provenance.
- Start feature analysis from original RGB, not the SG-filtered image. The same chosen mask must be held fixed across tone/ridge comparisons. Do not black out the exterior before convolution; process original context and restrict evaluation to interior pixels with valid neighbourhood support.
- Keep stored-RGB fraction maps independent of nonlinear gamma/CLAHE changes. Ratios can reduce a common multiplicative brightness factor, but are not invariant to clipping, shadows, white-balance or nonlinear tone processing.
- Record the existing ridge operator's Gaussian widths (1, 2, 3) and any extra smoothing separately. Do not silently apply Gaussian twice and attribute changes to only one filter.
- Bright/dark ridges may be veins, folds, shadows, leaf edges or noise. A mask skeleton/major axis is a geometric centreline proposal, not a measured midrib.
- Confirm a midrib through a visible base/tip, continuous internal path, human correction and physical point IDs across views. Different tone variants of one photo are correlated transformations, not independent viewpoints or new depth evidence.
- Exposure variants beyond current fixed 0 EV are proposed only; distinguish them from already executed gamma/CLAHE conditions.

## Still unavailable

Independent anatomical midrib accuracy, true 3D leaf curvature, 3D reconstruction improvement and human correction time have no supporting reference measurements. Report them as unavailable. The comparison does not validate PPFD-ready surfaces.

## Recovery and delivery

Preserved evidence: `build/preprocess_colab_recovery_20260930/` (remote/local notebook diff text, full-precision recovered CSV, per-photo records, provenance JSON).
Recovery notebook: `Tomato_Preprocessing_Recovery_20260930.ipynb` in that directory. It uses the exact same input archive (SHA-256 `fe3b5ed5dc0aeb5e465839c6e46f5fe7acdf84ab09bc37c4fecc482bec8f1c6c`) and downloads phase checkpoints. A partial checkpoint is not a completed four-run delivery.

After all four phases finish:

```powershell
python -m tools.preprocess_colab --import-results <downloaded_zip> --out build/preprocess_colab_return_<fresh_timestamp>
```

Verify completion/source-audit records, frozen input hashes, per-condition photo/mask denominators, error rows and CSV/manifest compatibility. Compare rerun metrics against the recovered stdout; report differences rather than mixing runs. Then append the actual archive location, hashes, timings, tone/scalar outcomes and limitations to this handoff. Until then, do not claim the full download or final comparison is complete.

### Input integrity recheck

On 2026-09-30, the frozen ZIP hash and all 345 payload hashes were reverified locally. Every bundled photo, accepted-reference mask and weight file still matches the corresponding local source. Three support-code/test files differ from their later local versions (`leaf_preprocess_lab.py`, `preprocess_colab.py`, `test_preprocess_study.py`); the derived portable config and empty package marker exist only in the bundle. Recovery executes the frozen bundle rather than mixing these versions. Audit: `build/preprocess_colab_recovery_20260930/input_bundle_recheck.json`.

Recovery notebook uploaded separately: https://colab.research.google.com/drive/1Yw9VgtsTi_7JnaC3nb7LVhq_B_q09RfQ . Original notebook/tab preserved. Only the fresh, empty replacement runtime attached to the original notebook was released after the Files panel showed `sample_data` and no result files. No existing inference job was stopped.

### Recovery execution started

At approximately 11:55 KST, 2026-09-30, the separate recovery notebook passed the ZIP hash and all 345 payload checks on Tesla T4. Setup and software-test cell finished and the four-photo pilot printed per-photo inference progress. Run All was invoked once; expanded, tone, scalar, display and download stages follow in order. No recovery result ZIP has yet been verified locally. Proof: `build/preprocess_colab_recovery_20260930/recovery_gpu_running.png`. The existing 10-minute follow-up now watches this recovery notebook and will finalize this handoff only after actual download/import/audit. A browser-control timeout did not stop the visible GPU run.


### First recovery checkpoint downloaded and audited (2026-09-30 12:10 KST)

The pilot ZIP is now saved locally: `build/preprocess_colab_recovery_20260930/preprocess_checkpoint_pilot.zip` (264,103,788 bytes; SHA-256 `59dba6c4e0b14bad11b53cc3d8cc752be8a7f296372e623f481ef68ea1ae5405`). This is a partial pilot checkpoint, not a four-run completion. Its 1,085 ZIP entries pass CRC verification. All 83 source hashes match the frozen input bundle and all 83 recorded source-audit entries are unchanged. `masks.csv` contains 497 rows, exactly 71 per condition across seven conditions; completion metadata reports four photos. Mask statuses: {'success': 497}. Summed measured detector time is 53.497 s and SAM time is 210.707 s; these are component timings, not total wall time.

The browser download event timed out, but the actual Downloads file appeared and was copied into the project and validated; no inference was rerun to obtain it. Audit report: `pilot_checkpoint_audit.json`; numerical summary: `pilot_summary_downloaded.csv` in the same folder. Expanded inference is running. Tone, scalar and final complete-result import remain pending. The original notebook tab is no longer present in the current browser session; do not recreate or overwrite it merely to monitor the recovery notebook.

### Recovery follow-up: completed expanded stdout, unavailable runtime (2026-09-30 18:23 KST)

This status supersedes earlier statements that recovery inference is still running. The recovery notebook's saved cell 10 output now contains all seven completed 14-photo summaries (268 reviewed mask observations per condition) and a checkpoint-ready record. Expanded wall time was **1,876.94 seconds** (31.28 minutes), distinct from the original run's 1,678.24 seconds. Recovered AP50, IoU and Dice match the earlier saved summary exactly at the stored precision; timings differ and are not pooled.

The notebook reports `/content/preprocess_checkpoint_expanded.zip`, 1,175,273,797 bytes, SHA-256 `fc145626648a64442e9ba2c844a6b1125db7bdf45b08e8ba8ea0bc84f06cd5c2`. This is evidence of remote creation, **not a verified local download**. The local Downloads check found only the already-audited pilot checkpoint. Colab's session manager explicitly reports no active sessions and a disconnected runtime. Tone/scalar/display/final-download cells have no saved result output. No active job was restarted, no new runtime was allocated, and the complete-result importer was not run.

Saved evidence under `build/preprocess_colab_recovery_20260930/`:
- `browser_state_1823.txt`: visible notebook output and no-active-session dialog.
- `no_active_session_1823.png`: session-manager screenshot.
- `recovery_expanded_stdout_summary.csv`: seven rows extracted from the recovery notebook's saved stdout.
- `recovery_followup_1823.json`: availability, runtime, remote checkpoint metadata and per-condition differences against the original recovered summary.

Delivery remains partial: the pilot masks/artifacts are downloaded and audited; expanded numerical summaries are preserved, but expanded mask artifacts and full audit files are unavailable locally. Brightness/contrast comparison and scalar/ridge outputs remain unavailable. Raw still has the strongest expanded mask IoU/Dice, Gaussian9 the strongest production-filtered detector AP50. Do not promote SG or Gaussian to a universal default.

Resume with durable per-stage storage and verify each download before progressing. If no external copy of the expanded checkpoint exists, its artifacts require a new frozen-input Colab execution; do not rerun the completed pilot unnecessarily. Keep rerun output separate from recovered stdout. Continue the proposed SG-mask -> original-RGB -> controlled Gaussian/ridge branch as an ablation, not a validated midrib extractor. Independent anatomical midrib accuracy, 3D curvature/accuracy and correction time remain unavailable.

Local shell access recovered, but this host currently resolves no usable Python interpreter (`python` missing; Windows `py` reports no installed Python), which must be addressed before the Python result importer can run. No model execution moved to CPU. The obsolete live-job monitor could not be removed: the automation tool rejected both access and deletion because tool approval is required while the current approval policy is never. Do not claim the monitor was paused or removed.

### User-authorized Colab rerun (2026-09-30)

The user explicitly requested a Colab rerun after the runtime-loss report. Inspect the newly visible T4 session first: cell 2 currently reports a missing input ZIP. Re-upload the unchanged frozen input bundle, verify every payload, and restore the verified pilot checkpoint if practical rather than redoing its inference. Execute missing expanded/tone/scalar phases on GPU only, retaining the original model and thresholds. Download and verify each stage before continuing; no training or new default selection. Keep this run separate from saved historical stdout and append actual completion evidence.

### Rerun upload blocked by browser permission

The existing recovery notebook now has a connected GPU session. Its current cell 2 output identifies Tesla T4 but fails because `/content/preprocess_inputs.zip` is absent; the Files panel contains only sample_data. Attempted the supported file-chooser upload of the frozen input ZIP and verified pilot checkpoint. Browser security explicitly rejected the upload as user-denied. No alternate upload path, hidden API or indirect execution was attempted. User must upload those files in Colab or explicitly resolve the browser upload permission before execution can continue. Inference has not restarted. Preserve this runtime and notebook; do not mark the comparison complete.
