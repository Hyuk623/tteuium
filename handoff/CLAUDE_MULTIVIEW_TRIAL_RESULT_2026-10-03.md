# ViewFusion multiview trial result (P1 `3d구현`, dwt_t1)

Started 2026-10-03, completed 2026-10-04. Claude Code, execution owner. Prompt: `handoff/CLAUDE_CODE_MULTIVIEW_TRIAL_PROMPT_2026-10-03.md`. User chose GPU destination B (private Kaggle dataset/kernel uploaded by Claude). Root of all paths below: `build/multiview_completion_20261003_02/` unless written from the project root.

## Outcome

Both arms ran on a Kaggle Tesla T4 and completed: 2 seeds x 5 targets = 10 views per arm, 20 in total, all retained. Imports, evaluations and reviews exist for both arms. Silhouette metrics are `unavailable` with reasons; no metric geometry, hidden anatomy or growth claim is made. Imported candidates keep `origin=generative`, `validated_metric=false`, `suitable_for_ppfd=false`.

## Contract (`evaluation_contract.json`, sha256 b98f0a02...)

- Arms: multiview = images 27 (top) + 03 (side); top_only = 27, with 03 forbidden. Held-out image 13 never left the machine.
- Targets, identical in both arms: `T_eval` = image-13 board-frame pose as three numbers (polar 61.689, azimuth 82.165 deg, radius 1.248 model units normalized by image 27); `T_ring_000/090/180/270` = polar 60 deg, radius 1.5, fixed board azimuths. No image-13 pixels, masks or side-derived geometry enter either package. `passes_pose_gate=false` for every row (all condition poses and the image-13 pose fail their gate).
- Seeds 42/43, one sample per target and seed, ViewFusion interpolated DDIM, 50 steps, eta 0, guidance 3.0, autocast, 256 px, equal condition weights, 1,800 s per arm, no CPU fallback.
- Metrics: silhouette IoU and boundary F-score for T_eval against the image-13 union mask, `unavailable` because there is no validated mapping from the canonical 256 px view to the original camera. Ring targets: visual review only.

## Packages and isolation

`build_contract.py` wrote `requests/*_request_04.json`, then `multiview_prepared_04` and `top_only_prepared_04`. The executed archives are Codex's v6 repack of the same prepared folders: `build/p1_runner_v6_20261004_01/{multiview,top_only}_execution_package_05/execution_package.zip` (e3c14090..., 0142f0b0...). `arm_isolation_report_05.json` (4feea764...): identical targets, sampler, seeds and checkpoint across arms; top_only holds no image-03 or 03-derived asset; no image 13, evaluator snapshot or ratio table in either; full member hashes verified. A content scan of non-vendor members found no forbidden IDs. The kernel refuses any package whose `package_manifest.json` hash or request_id differs from the approved ones, and any file not listed in the manifest. Earlier `_03`/`_04` packages remain as history.

## Runtime (`kaggle/out_v6/runtime_env.json`, d4d07c5f...)

- Kaggle kernel `dolgfish/tomato-viewfusion-trial-04` v6 (private), dataset `dolgfish/tomato-viewfusion-trial-04-inputs` (private, two package zips only). Tesla T4 14.56 GiB, Python 3.13, torch 2.11.0+cu128, CUDA 12.8, pytorch-lightning 2.6.6, kornia 0.8.3, clip-anytorch 2.6.0, transformers 5.16.1, numpy 2.1.3.
- Checkpoint `cvlab/zero123-weights/105000.ckpt` downloaded on the host in 81 s; 15,465,973,531 bytes, SHA256 f0fee4e7...679855 verified before loading and again by the runner. 1938 state keys including 688 `model_ema.*`.
- Wall time inside the runner: multiview 115 s, top_only 121 s. Peak allocated VRAM 5.09 / 5.02 GiB (reserved 5.11 / 5.06). EMA applied once on CPU.
- Vendor tree `vendor/ViewFusion` at 61286dc5 stayed byte-identical (the runner verifies it). There is no vendor patch file because nothing in the vendor tree was changed. Runtime adaptations live in the launcher `kaggle/out_v6/runtime_shims/launch_trial.py`: a `pytorch_lightning.utilities.distributed` alias, CarveKit and taming refusal stubs (masks are supplied; the config uses AutoencoderKL), and a weights-only allowlist limited to the audited globals `pytorch_lightning.callbacks.model_checkpoint.ModelCheckpoint`, `numpy.core.multiarray.scalar`, `numpy.dtype` and `numpy.dtypes.*DType`. Any other global fails closed.

## Failed attempts (preserved unchanged in `kaggle/out_v1` ... `out_v5`)

| Attempt | Failure | Resolution |
| --- | --- | --- |
| v1 | weights_only refused the Lightning callback class used as a dict key | allowlist after `get_unsafe_globals_in_checkpoint` audit |
| v2 | fail-closed: numpy scalar/dtype globals | audited exact names |
| v3 | numpy 2 `numpy._core` rename broke name matching | `(obj, recorded_name)` tuples plus DType classes, tested locally first |
| v4 | `requires_grad_(False)` made `LitEma.copy_to` assert | line removed |
| v5 | first sample per arm, then CUDA OOM from a per-target `ema_scope` clone | Codex: CPU EMA application, cached conditions, partial bundles (`handoff/CODEX_TO_CLAUDE_VIEWFUSION_V6_READY_2026-10-04.md`) |

## Results and files

| Item | Path | sha256 |
| --- | --- | --- |
| Multiview bundle | `kaggle/out_v6/trial_multiview_01/candidate_bundle.json` | 85bcf52d... |
| Top-only bundle | `kaggle/out_v6/trial_top_only_01/candidate_bundle.json` | 3297ddb4... |
| Imports / evaluations / reviews | `{arm}_import_01`, `{arm}_evaluation_01`, `{arm}_review_01/viewer.html` | - |
| Comparison (24 rows) | `comparison.csv` | edf24532... |
| Visual review | `visual_review_note.md`, `visual_review_sheet_v6.png` | d87e0719... (sheet) |
| Tests | `completion_tests_v6.junit.xml`: 50 passed | e1c78c8b... |

Visual summary (details in the note): both arms give leaf-like but disconnected leaf clouds without stem or pot, with large seed-to-seed variation. Multiview outputs are upright and textured like image 03; top-only outputs collapse into a low band with dark smears. Small floating fragments come from two non-plant objects inside the saved image-27 mask.

## Remaining scientifically unavailable

- A validated original-camera mapping and reviewed boundary tolerance, needed for any T_eval silhouette metric.
- Passing pose gates for the condition and target poses.
- Seed-stable, structurally coherent hypotheses. With two seeds per arm, no claim about which arm is better at hidden leaves is supported.
- The image-27 mask includes non-plant objects. Cleaning it would change the conditioning and needs a new contract revision, not a silent edit.

## Addendum 2026-10-04: earlier 3D records checked after the run

- Pose: `build/plants_dwt_test_20261002/plants/dwt_t1/pose_session/rescue.json` (marker PnP rescue; policy max 4 px RMS) accepts image 13 at 3.46 px, azimuth 81.3 deg, elevation 27.2 deg, within about 1 deg of T_eval (82.2 deg, elevation 28.3 deg). Conditions 03 and 27 (and 28) are rejected there (too few RANSAC inliers). The strict ChArUco gate is 1.0 px; no condition pose passes either policy.
- View groups: `build/plants_dwt_test_20261002/DWT_TEST_RESULTS.md` confirms by measured elevation that T1 top shots are 27 and 28 (83-89 deg) and 01/03 are low-ring; capture.json group labels follow input order, not measurement. Using 27 as top and 03 as side is correct. Image 28 is a second top view, unused so far.
- Masks: the condition masks are `saved_visible_leaflet_union`. `labels/original_pixel_labels.coco.json` also holds sub-stem labels for 03 and 27 (and main-stem plus sub-stems for 13), which were not included. Absent stems in outputs are therefore at least partly an input property (see CODEX_P1_V6_RESULT_REVIEW_2026-10-04.md).
- Candidate next revision (not started; needs user approval and a new contract revision, never edits of the saved _04 inputs): leaflet + stem masks with the two non-plant objects excluded, an optional 28 top condition, and more seeds before any arm comparison.

## Addendum 2026-10-04: contract revision r03 executed (kernel v7)

User approved the revision. Folder `build/multiview_completion_20261004_03/` holds `build_revision.py`, `evaluation_contract.json` (56ee0e48...), `requests/*_05`, `*_prepared_05`, `*_execution_package_06`, `arm_isolation_report_06.json` (513fe02e..., identical targets/sampler, content scan clean) and returns in `kaggle_out_v7/`.

- Change, pre-declared: masks = saved leaflet union minus visually confirmed non-plant items (image 27: a545/a549, the board notebook spiral binding) plus same-image stem annotations with score >= 0.5 (03: one sub-stem; 13: two sub-stems; 27: its only stem label is a 0.29 corner fragment, excluded). The crop rule is unchanged (square 1.2 x mask bbox, reproduces all _04 crops), so the 27 crop became 840 px instead of 1575. Seeds 42-49. Targets, sampler and checkpoint are unchanged. Saved _04 inputs are untouched.
- Run: both arms completed, 8 seeds x 5 targets = 40 views per arm (bundles 9dc22125... / a742a915...), 298 s / 236 s, peak 5.1 GiB on the T4. Imports, evaluations and reviews exist for both arms; `comparison.csv` has 96 rows, all metrics unavailable with reasons; tests 50 passed (`completion_tests_v7.junit.xml`).
- Findings (`visual_review_note.md`, `posthoc_seed_consistency.csv`): the binding fragments vanish at the same seeds. The r02 top-only collapse does not recur, so it was mainly an input-scale effect (r02 note corrected). Top-only stays very dark while multiview carries image-03-like texture. There is still no stem or connected structure. Post-hoc seed-pair silhouette IoU is moderate (0.29-0.43), not accuracy.
- Still unavailable: a validated camera mapping for T_eval metrics, passing condition pose gates, and fully connected (reviewed) plant masks.

## Addendum 2026-10-04: mapping validation against the 3D status artifact modelling

`build/mapping_validation_20261004_01/` (`validate_mapping.py`, `mapping_validation_note.md`). On the dwt_t1 visual hull, an object-centred look-at render (the artifact's `lookFrom` and the Zero123 convention) followed by the 1.2 x bbox crop reproduces the real image-13 camera crop at IoU 0.973, but only when centred on the plant (hull centroid). Aiming at the pose-definition point c0 = (95, -57, 0) gives 0.675; roll is negligible (-0.01 deg). All trial poses were computed about c0, which lies about 95 mm below the plant centroid: side views are polar 77-78 deg about the plant, not 61.6-61.7, so the top-only 27 -> T_eval offset was about 16 deg too overhead. Provisional silhouette IoU against the image-13 mask under this mapping: r03 T_eval 0.27 (multiview) / 0.28 (top-only), wrong-pose ring controls 0.24-0.25, copying photograph 03 gives 0.25. There is no evidence that either arm reproduces image 13. The hull-to-mask consistency is only 0.40 (the hull fills leaf gaps). Next revision would re-centre poses on the plant; the top-only centre definition needs a fairness decision.

## Addendum 2026-10-04: contract r04 (plant-centred poses) and comparison under the validated mapping

User chose the pose centre: centroid of a hull carved with tools.plant_structure (unchanged, read-only) from all posed photos except 03 and 13 = (98.3, -69.5, 96.0) mm, within 0.5 mm of the full-hull centroid. `build/multiview_completion_20261004_04/`: `build_revision.py`, `pose_centre.json`, `evaluation_contract.json` (r04, only the pose centre changed versus r03), `requests/*_06`, `*_prepared_06`, `*_execution_package_07`, `arm_isolation_report_07.json` (clean). New poses: 27 (6.7, -68.6, 1.5), 03 (77.3, -41.6, 1.381), T_eval (77.9, 83.1, 1.523). Kernel v8 completed both arms, 80 views, peak 5.2 GiB; imports, evaluations and reviews done; 50 tests passed (`completion_tests_v8.junit.xml`).

Comparison (`build/mapping_validation_20261004_02/comparison_note.md`, post-hoc, exploratory): leaf-level silhouette IoU against image 13 stays at control level (r04 0.26 / 0.26 versus rings 0.24-0.25 and copy-03 0.25). Filled-envelope IoU: r04 T_eval multiview 0.493, top-only 0.464; rings 0.42-0.44; copy-03 0.41; hull reference 0.57. T_eval beats the same seeds' ring targets (p = 0.003 / 0.010). r04 versus r03 and multiview versus top-only are not significant. Generated views capture a pose-specific plant envelope but not leaf placement.
