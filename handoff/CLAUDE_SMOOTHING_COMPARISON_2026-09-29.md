# Preprocessing comparison: implementation brief

User authorization: implement the agreed smoothing / brightness / stored-RGB-ratio comparison, run comparisons, then consolidate the plan and actual outcomes here for Claude. No training, geometry changes, pyramid/tile-layout changes, or replacement of source labels.

## Protocol

- Extend `tools/leaf_preprocess_lab.*`; preserve legacy saved selections.
- Original-pixel smoothing: none, mean 3x3, Gaussian 5x5 sigma 0.8, Gaussian 9x9 sigma 1.2, separable SG windows 5/7 degree 2 (horizontal then vertical), bilateral diameter 5 strength 12 sigmaSpace 2.
- RGB model path: smooth Lab L, retain a/b, transform back to RGB; process the full frame before the existing fixed crops/resize. Exact original baseline bypasses Lab conversion.
- Tone phase: no smoothing and selected smoothing candidates, each with none / gamma 0.85 / gamma 1.15 / Lab CLAHE 1.5, grid 8x8. EV stays zero; gamma and CLAHE are mutually exclusive.
- Scalar path: original linear-sRGB luminance and original stored-RGB R/G/B fractions, followed by independent smoothing. Preserve numeric SG overshoot; clip display only. Exclude filter footprints crossing masks, holes, invalid pixels or image edges; compare common support and record coverage.
- Ridge internal Gaussian widths remain [1,2,3] pixels; record this additional filtering separately.
- Fixed dwt_01-held-out full/tiles detectors and held-out SAM 2.1 Tiny; weights, prompts, sensitivity and candidate rule remain fixed. The existing tile geometry remains unchanged. Preprocessing caches must include image bytes, recipe, model and prompts.
- Begin with dwt_01 views 11,18,24,25, then expand to reviewed dwt_01 photos. Use accepted_by_user masks only; source detector GT provenance must be audited before accuracy claims.
- No independent midrib/landmark references currently established. Human visibility, click repeatability and correction time remain unavailable until explicitly recorded. No 3D accuracy claim.

## Delivery and checks

New immutable build outputs: manifests, settings, images, numeric arrays, model predictions, CSV metrics, timing, hash audit and review artifacts. Test no-op pixels, SG computation, channel/coordinate order, invalid/boundary support, cache separation and source preservation. Final outcomes and commands will be appended after execution. Development results on dwt_01 are exploratory, not independent final validation.

## Execution steering: heavy computations on Colab

The user subsequently required complex calculations on Colab. The local pilot process was stopped; its partial files are retained, not interpreted as a completed comparison. Move repeated detector/SAM inference to a GPU-gated Colab notebook. Local work is limited to packaging, software checks and the review UI. Colab must rerun its original baseline so CPU/GPU results are not silently pooled. Preserve the exact held-out weight bytes, original-pixel input images and human-reviewed references in a private input bundle. No new training is authorized or required.

## User-proposed two-stage path: SG segmentation, original-image Gaussian/ridge analysis

The user proposed discussing this additional path, not declaring it superior before comparison:

1. Original RGB -> separable SG on Lab L (5/7 pixels, degree 2) -> existing detector/SAM -> proposed instance mask. SG is preprocessing, not an annotation model. Compare mask quality against unchanged-RGB inference.
2. Return the instance mask to the original pixel grid. Since these filters do not warp or resize, mask transfer is identity; any model resize/crop still needs the established inverse transform. Keep source annotation ID, mask revision, transform and recipe. Preserve separate prediction and human-reference masks.
3. Use the original RGB/context, not SG-smoothed RGB, for within-leaf feature analysis. Define the mask as an analysis ROI; do not zero the background before convolution. Exclude boundaries/holes whose neighbourhood is not fully supported.
4. Compare original, exposure/gamma and contrast variants from that same original. For each variant, apply a controlled Gaussian scale or fixed Gaussian-derivative/ridge operator; do not silently stack extra Gaussian layers. Original stored-RGB fractions stay a separate branch, because nonlinear tone/contrast adjustment changes those fractions.
5. Treat bright/dark line responses as vein/fold/shadow candidates. Multiple tone variants are correlated views of the SAME pixels, not independent observations or new depth evidence. Feature stability can rank candidates but cannot confirm anatomy.
6. Confirm a midrib using a visible base/tip and continuous internal path, with human correction and cross-view physical landmark checks. A mask skeleton or leaf major axis is only a geometric centreline proposal, not an observed midrib.
7. Distinguish 2D fold appearance/curved contours from metric 3D leaf curvature. Actual curvature requires multi-view depth/surface evidence; RGB contrast or Gaussian derivatives alone do not establish it.

Suggested fair ablation: original mask vs SG mask; hold the chosen mask fixed while comparing original/weak Gaussian/tone variants for line visibility. Where independent midrib labels or repeated human clicks are unavailable, report visibility-only and leave midrib/3D accuracy unavailable. This proposal does not supersede the agreed seven-condition segmentation comparison or activate a new default.

Primary implementation references: [SciPy Savitzky-Golay](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html), [SciPy Gaussian derivatives](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html), [scikit-image ridge operators](https://scikit-image.org/docs/stable/auto_examples/edges/plot_ridge_filter.html).

## Implementation and current execution record

- Added `tools/preprocess_study.py`: the seven smoothing recipes, Lab-L RGB processing, stored-RGB scalar-first maps, SG numeric overshoot preservation, explicit common support and fixed ridge parameters.
- Extended `tools/leaf_preprocess_lab.py/.html/.js`: Korean study controls, original/processed/difference/scalar displays, full-frame preprocessing before crop display, read-only model overlays when available, explicit derived saves and legacy compatibility. Local review UI is `http://127.0.0.1:8833/?annotation=368`.
- Added `tools/preprocess_compare.py`: fixed held-out full/tiles detector and held-out SAM, original-based crop layout, source hashing, per-condition model caches, resumable prediction records, per-photo/class and pooled production-threshold AP50, per-observation mask IoU/Dice, merge flags and timings. No training.
- Added `tools/preprocess_colab.py`: allowlisted source/weight/reference packaging, GPU-only notebook and safe result import. Local source and imported output directories stay separate.
- Software validation: 30 targeted tests passed (19 legacy + 11 new); notebook format validated and every code cell compiled locally. Notebook GPU execution is NOT validated by these tests.
- Existing annotation 368 SG-7 scalar example: 45,507 reviewed-mask pixels; common scalar support 39,177 pixels (86.09%); this G-ratio example has no SG values outside 0..1. This is coverage, not accuracy.
- Local source audit: 9 unique original-photo/mask/export files for the four UI observations match the prior snapshot hashes.
- Local inference was deliberately stopped after user steering to Colab. The preliminary timing run processed one raw photo and one mask. The interrupted comparison saved raw-condition masks for views 24 and 25 only. These files are incomplete and cannot establish a preprocessing winner. `build/preprocess_pilot_20260929/STOPPED_FOR_COLAB.json` records this.
- Colab input bundle: `build/preprocess_colab_20260929/preprocess_inputs.zip`, 307,032,461 bytes, 345 entries, 14 dwt_01 photos and 268 human-accepted leaflet observations. ZIP SHA-256: `fe3b5ed5dc0aeb5e465839c6e46f5fe7acdf84ab09bc37c4fecc482bec8f1c6c`.
- Uploaded notebook: https://colab.research.google.com/drive/1SjaiAa7r0GpPuvhBzIqlDcO6PVMVsIcs . At this record, the GPU runtime was allocating; no GPU comparison results were available. The input ZIP had not yet been uploaded to the runtime.
- The Colab archive freezes the code version at packaging. Later local additions only add result-import support / cross-platform viewer path matching / tests; the packaged preprocessing and comparison computation stays unchanged. Do not silently mix CPU and GPU results.

### Reproduce and return results

```powershell
python -m tools.leaf_preprocess_lab serve --run build/rgb_preprocess_study_ui_20260929 --port 8833 --experiment build/preprocess_pilot_20260929
python -m pytest tools/tests/test_preprocess_study.py tools/tests/test_leaf_preprocess_lab.py -q
python -m tools.preprocess_colab --import-results <downloaded_preprocess_colab_results.zip> --out build/preprocess_colab_return_<timestamp>
```

Open the uploaded Colab notebook, connect a GPU, upload the paired ZIP in its first cell, and execute the remaining cells in order. The notebook runs the 4-photo pilot with ALL accepted masks, expands the seven smoothing conditions to all 14 eligible photos, selects exploratory candidates separately by detector/mask metrics, compares tones, and exports scalar diagnostics. No automatic default selection is deployed.

The downloaded result folder can be passed to the existing review server with repeated `--experiment` arguments pointing to imported `build/colab_preprocess_*` directories. Inspect source hashes, completion records, coverage and logs before adding a final result section here. The initial CPU pilot is not a substitute.

### Remaining research outcomes

GPU comparison, performance ranking, independent new-plant confirmation, human midrib/landmark references, repeated-click/timing assessments, and the proposed SG-mask -> original-image Gaussian/ridge branch remain unvalidated. No measured 3D improvement, anatomical midrib correctness, physical leaf curvature or PPFD readiness is claimed.

## Colab transfer update

The paired input ZIP finished uploading through the Colab Files panel. The output-frame file picker was unavailable, so the first code cell was changed to read `/content/preprocess_inputs.zip`. The archive hash and all 345 payload file hashes passed in the extraction cell. The connected device is Tesla T4. Dependency installation completed successfully. GPU comparison results are still pending; local inference remains stopped. The notebook generator now also accepts an already uploaded ZIP, preserving the same hash check.

## First completed GPU pilot (2026-09-29)

The four-photo pilot completed successfully on Tesla T4 (process exit code 0 and completion record checked by the next cell). It evaluated 71 human-reviewed leaflet observations per condition, 497 mask comparisons in total. The following rounded values were read from the Colab result table; retain the downloaded CSV as the final numerical source when available.

| Smoothing | Production AP50 | Mean mask IoU | Mean mask Dice |
|---|---:|---:|---:|
| Original | 0.329734 | 0.843651 | 0.900906 |
| Mean 3x3 | 0.372309 | 0.839953 | 0.896728 |
| Gaussian 5x5, sigma 0.8 | 0.388431 | 0.840031 | 0.896692 |
| Gaussian 9x9, sigma 1.2 | 0.381180 | 0.836118 | 0.894582 |
| SG-5, degree 2 | 0.366619 | 0.849557 | 0.905388 |
| SG-7, degree 2 | 0.378626 | 0.837357 | 0.895058 |
| Bilateral 12 | 0.350110 | 0.829874 | 0.890132 |

All conditions returned nonempty masks. Merge-candidate review flags ranged from 17 to 19; these flags are not confirmed biological merges. SG-5 improved mean mask IoU by approximately 0.0059 in this small pilot, whereas weak Gaussian had the highest production-threshold detection AP50. This is not proof of a general improvement or midrib/3D benefit. Do not install a new preprocessing default from this pilot.

The 14-photo comparison is running. Tone comparison is queued with an explicit preceding-completion check. No training is running. Colab's inherited subprocess output did not appear live in the first pilot; subsequent runs now explicitly stream per-photo progress. The local notebook generator has the same streaming wrapper; its targeted tests passed (11/11). `build/preprocess_colab_20260929/colab_pilot_progress.png` records the pilot result / expanded-run screen.

## Completion follow-up

The user explicitly requested handoff preparation after completion. A thread follow-up named "토마토 전처리 결과 인계 준비" was created (automation ID `automation`, every 10 minutes). It must remain quiet on unchanged progress, finish result display/download/import and English handoff consolidation, and pause after delivery. At registration, the pilot was complete; expanded inference was running and tone/scalar cells were queued. Browser control subsequently timed out; do not interpret that as a compute failure or reload the active notebook. Final result display/download cells are not yet queued. The remaining comparisons and final handoff are therefore pending, not complete.

## Recovery brief (2026-09-30)

The original Colab session disconnected. Reconnection created a fresh runtime whose Files panel contains only `sample_data`; the original notebook also has a remote/local save conflict. Both displayed notebook versions were preserved as text under `build/preprocess_colab_recovery_20260930/`. Do not overwrite the remotely saved notebook with the stale local version.

The remotely saved stdout contains the completed 14-photo, seven-condition summary and 98 per-photo records. Preserve these as recovered evidence, not as an original result archive. Tone and scalar cells have no visible completion output. The original per-observation files, audit records and prediction masks have not been recovered.

Recovery action: generate a separate notebook using the SAME frozen 307,032,461-byte input ZIP and unchanged inference code; rerun on Colab GPU to regenerate auditable artifacts. Download checkpoints after each completed phase, then use the existing strict four-run importer for the final ZIP. This is a recovery rerun, not additional parameter search or model training. Keep the previous summary separate and compare it with the rerun. Do not update model defaults or use Claude's newer weights in this frozen comparison.

## Recovered expanded comparison (2026-09-30; partial delivery)

The remotely saved notebook stdout records completion of the 14-photo smoothing comparison in 1,678.24 seconds (27.97 minutes). The 98 per-photo log records reconcile to 14 distinct photos and 268 reviewed masks for each of seven conditions: 1,876 mask comparisons, not unique physical leaflets. All photos are from dwt_01. The local CSV below is a transcription of full-precision JSON stdout, not the original CSV downloaded from Colab.

| Condition | Production AP50 | Mean mask IoU | Mean mask Dice | Merge-review flags |
|---|---:|---:|---:|---:|
| none__none | 0.378258 | 0.840080 | 0.901007 | 56 |
| mean3__none | 0.424784 | 0.834666 | 0.897156 | 53 |
| gauss5__none | 0.420356 | 0.836319 | 0.898054 | 55 |
| gauss9__none | 0.446407 | 0.832307 | 0.896076 | 53 |
| sg5__none | 0.410737 | 0.836960 | 0.899317 | 55 |
| sg7__none | 0.421122 | 0.830594 | 0.894187 | 53 |
| bilateral12__none | 0.385873 | 0.832526 | 0.895838 | 52 |

Interpretation: raw RGB has the highest mean mask IoU and Dice. SG-5 falls from 0.840080 to 0.836960 compared with raw (-0.003119 IoU); the pilot-only SG gain did not persist. Gaussian 9x9 has the highest production-threshold detection AP50 (0.446407 vs raw 0.378258; +0.068149), but lower mask IoU (0.832307). The prespecified tone-candidate rule therefore selects `none` and `gauss9`. These are exploratory, task-dependent comparisons, not a deployed recommendation or new-plant validation. All empty-mask counts are zero; merge flags are review candidates, not confirmed errors.

Recovered artifacts: `build/preprocess_colab_recovery_20260930/{remote_notebook_diff.txt,unsaved_notebook_diff.txt,recovered_expanded_summary.csv,recovered_per_photo_log.csv,recovery_provenance.json}`. The source text SHA-256 is in the provenance JSON. The runner emits its final JSON only after its audit/completion code; this supports completion at that time, but the original audit file is unavailable for independent reinspection. Tone/scalar outputs, prediction masks and a complete result ZIP are still unavailable. No successful four-run import is claimed.

### Claude integration boundary

Keep detection, mask generation and within-mask feature analysis as separate selectable branches. Preserve raw RGB as the segmentation baseline. Do not automatically promote SG based on the earlier four-photo pilot. The user-proposed SG-mask -> original-RGB -> controlled Gaussian/ridge path remains an ablation to test. Returning a mask to unchanged original coordinates is supported by the existing transform contract; ridge responses remain generic 2D candidates until a visible base/tip, human-reviewed path and cross-view landmark identity verify the midrib. Tone variants do not provide new geometric views. Physical leaf curvature, independent midrib accuracy, 3D accuracy and human correction time remain unavailable.

A separate recovery notebook, `build/preprocess_colab_recovery_20260930/Tomato_Preprocessing_Recovery_20260930.ipynb`, passes notebook-schema validation and Python syntax parsing for every code cell. It preserves the fixed input ZIP and inference code, streams progress, and downloads cumulative checkpoints after each phase. A checkpoint is a partial archive until all four phases have completion records. Full delivery remains pending the recovery rerun and import.


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
