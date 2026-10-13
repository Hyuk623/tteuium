# Optional multiview completion trial

This feature lives beside the existing pipeline. It reads saved inputs and writes fresh build directories. No command modifies source photographs, masks, labels, calibrations, weights, human configuration or the normal reconstruction pipeline. The current backend generates novel-view RGB hypotheses. It does not deliver metric leaf meshes, recover verified hidden anatomy or make an optical scene eligible.

## Entry points

```powershell
python -X utf8 -m tools.multiview_completion audit --request build/multiview_completion_20261003_01/real_t1_inputs/multiview_request.json --out build/fresh_completion_audit
python -X utf8 -m tools.multiview_completion prepare --request build/multiview_completion_20261003_01/real_t1_inputs/multiview_request.json --out build/fresh_completion_prepared
python -X utf8 -m tools.completion_package --prepared build/fresh_completion_prepared --vendor build/multiview_completion_20261003_01/vendor/ViewFusion --out build/fresh_completion_package
```

A request declares plant/session, condition/evaluation images, source hashes and dependency graph, movement evidence, model policy, backend revision, seeds, sample/view/step/time budgets, virtual targets and preprocessing. Audit follows the conditioning dependency closure; unknown provenance, top-only side dependencies and mismatched sources are blockers. Preparation retains a local evaluator snapshot but puts only allowed conditioning assets into backend_request.json/inputs. Packing excludes evaluator snapshots, evaluation photographs and all-view ratio tables. Upload is not implicit.

The first-label observed-area calculation remains in `tools/detected_leaf_area.py`. The real trial has a separate `relative_observed_areas.csv`; it is not copied as a whole into the top-only backend. Each photo's first saved label is the reference, with missing/zero semantics preserved. These dimensionless observed ratios are not generated surface-area ratios.

## Isolated model execution

`tools/completion_viewfusion.py` accepts the condition-only backend request, a separately installed CUDA runtime, the pinned ViewFusion vendor tree and an explicitly supplied official Zero123 checkpoint. It runs the authors' DDIM interpolation sampler with every declared real condition. No model training, package installation or checkpoint download occurs on module import or preparation.

```text
python -m tools.completion_viewfusion --request <prepared>/backend_request.json --vendor <vendor>/ViewFusion --checkpoint <official-105000.ckpt> --out build/<fresh-model-run>
```

The runner checks source hashes, checkpoint hash when pinned, CUDA availability, minimum declared VRAM, seeds and candidate/target limits. It uses a bounded wall-time alarm on Linux, writes live status.json, preserves every declared seed and reports runtime versions, GPU, peak allocated VRAM, preprocessing and checkpoint SHA256. CPU fallback is disabled. The current runtime dependency installation and actual checkpoint execution remain unverified until a GPU trial succeeds; successful unit tests do not establish model compatibility.

Request angles are polar/azimuth degrees; the runner converts differences to the authors' polar/sin-azimuth/cos-azimuth/radius conditioning. Radius uses explicit model units. Original-pixel square crops and saved mask compositing are recorded. No canonical camera direction or radius becomes a board-frame measurement. The supplied real T1 trial retains failed camera quality gates and unknown independent rigid-group verification; its conditions are diagnostic assumptions and its output remains an image hypothesis.

The pinned source is [ViewFusion](https://github.com/Wi-sc/ViewFusion) revision `61286dc572ae3b4e8924ab51c45ca0bbd53c58ea`. The actual multi-input script is `zero123/generate_360_multi_view_autoregressive.py`, not the stale README path under 3drec/data. Vendor source files and the Apache licence are saved separately under build with Git-blob verification and SHA256 manifest. Public-model use for this comparison was explicitly permitted by the user; it does not change the tuned detector/SAM selection.

## Import and inspect

Return the entire model output directory, including generated images, candidate_bundle.json and status.json. Import verifies the original request hash, backend provenance, conditioning closure, every declared seed/target, image dimensions/hashes and false physical/optical flags.

```text
python -m tools.multiview_completion import --prepared <prepared> --candidate <result>/candidate_bundle.json --out build/<fresh-import>
python -m tools.multiview_completion evaluate --prepared <prepared> --imported build/<fresh-import> --out build/<fresh-evaluation>
python -m tools.multiview_completion review --imported build/<fresh-import> --out build/<fresh-review>
```

Review exports a Korean HTML image/provenance viewer. Evaluation currently reports real-camera silhouette metrics unavailable for canonical RGB without a validated mapping. The standalone silhouette helper handles explicit known/unknown regions; it is not used to fabricate alignment or generated masks. Metric candidate-mesh import, depth reconstruction and a calibrated hypothesis renderer remain future work, not delivered by the RGB backend. Existing optical gates remain unchanged.

## Current artifacts and verification

`build/multiview_completion_20261003_01/` contains real T1 selected-input snapshots, current `multiview_prepared_03` and `top_only_prepared_03`, pinned vendor sources and separate execution archives. Earlier prepared directories are historical; use the _03 preparations with the restricted package field whitelist and pinned official checkpoint SHA256. The corresponding archives are in multiview_execution_package_02 and top_only_execution_package_02.

Selected condition images: 27 top plus 03 side for multiview; only 27 for top-only. Selection uses the previously calculated measured elevation grouping, not photo number. Image 13 is retained locally for evaluation. Two seeds (42, 43), two declared virtual targets, 50 steps and at most 1800 seconds per mode are trial settings, not scientific acceptance thresholds. Each archive contains only that condition's actual allowed input images. Original masks/sources were hash-checked unchanged.

Initial combined adapter/backend-preprocessing/detection/normalization tests: 44 passed. After adding archive isolation coverage, 25 completion-specific tests passed; the 20 detection/normalization cases from the combined run were unchanged. All three CLI help commands passed. No actual checkpoint inference, remote upload, geometry reconstruction or optical execution has occurred at this checkpoint.

The official checkpoint metadata reports 15,465,973,531 bytes; the runner uses tensor-only, memory-mapped loading. Only the HTTP range header/ZIP signature and repository metadata were inspected locally; weights were not downloaded. GPU runtime verification remains pending.

## P1 continuation and runtime evidence

Read `handoff/CODEX_P1_CONTINUATION_2026-10-03.md` for the current state. The user assigned uploads to Claude Code. Its common target contract and `_prepared_04` inputs exist under `build/multiview_completion_20261003_02/`; the previous unmatched targets and pending uploader selection are superseded for that revision. Retrieved Kaggle version 3 completed as a kernel but both arms failed checkpoint loading at the old NumPy scalar global name. No generated candidates exist in those returned outputs. Full GPU/checkpoint compatibility and inference remain unverified.

`build/p1_continuation_20261003_01/` contains a fresh baseline audit, actual failure comparison, a synthetic serialization diagnosis and updated `multiview_execution_package_04` / `top_only_execution_package_04` archives. They retain the existing common targets and add exact archive integrity checking and target pose/gate provenance retention. Candidate import rejects changed or missing declared target metadata. `completion_package.verify_archive` verifies member hashes and the exact declared input inventory without extraction. Focused P1 tests: 55 passed; separate existing synthetic transform/split tests: 2 passed. These packages were not uploaded by this task. Use the continuation report for the exact execution-owner follow-up and scientific limits.
