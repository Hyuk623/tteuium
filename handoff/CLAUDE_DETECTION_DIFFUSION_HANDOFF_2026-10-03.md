# Detection relative area and diffusion trial handoff

Date: 2026-10-03. From Codex to Claude. This document consolidates the implemented detection calculation, optional diffusion runner, verified preparation and remaining execution work. The requested actual model trial is incomplete: the goal is blocked on the GPU execution destination, not complete. This handoff authorizes no new upload or inference by itself.

## User decisions and scope

- Existing leaves remain observation based. Future leaves belong to the separate CompoundLeaf growth distribution work, informed by literature and relationships among observed blocks. Do not use generated pixels as observed growth or measured anatomy.
- Before physical measurement, set the first labelled leaf area to dimensionless 1 and calculate other areas relative to it. The user explicitly selected area ratio, not leaf length, order or mass.
- The user authorized actual implementation and a model trial while preserving the existing program.
- Public pretrained models are explicitly permitted for this comparison only. This later user decision overrides the master handoff model restriction for this trial; do not ask for the same exception again or replace production detector/SAM weights.
- The user confirmed that additional reviewed curved-surface specifications, confirmed correspondences and independent leaf-area measurements are absent. Do not repeatedly search or ask for those as if they already exist elsewhere.
- The GPU destination question remains unanswered. Proposed choices were private Kaggle upload and execution by Codex, user execution in Colab/Kaggle, or another supplied GPU host. Public-model permission is not private-photo upload permission.

## Delivered calculation

`tools/detected_leaf_area.py` reads saved Batch detections and masks; it does not rerun detection. Default `mask` mode counts visible foreground pixels at original image resolution. `bbox` mode is an explicitly separate proxy. `tools/relative_leaf_area.py` computes `relative_area = area_px2 / reference_area_px2`.

The reference is the first saved manifest label in each image, not an inferred oldest leaf or the first valid replacement. Invalid reference handling must remain explicit. Ratios are dimensionless and retain source, review and visibility provenance. Camera perspective, occlusion and view differences remain; these are not physical surface-area ratios.

Recorded T1/T2/T3 execution produced 435/489/394 rows, respectively: 1,318 per-photo observations across 54 images, not 1,318 unique physical leaves. The first T1 example is a6: 8,478 pixels -> 1; a7: 29,700 -> 3.5031847; a8: 3,742 -> 0.4413777.

Results: `build/detection_relative_leaf_area_20261003_01/relative_detected_leaf_areas_all.csv`, `summary.json` and `result_verification.json`. Keep this observed baseline separate from generated images.

## Implemented diffusion boundary

| File | Implemented responsibility |
| --- | --- |
| `tools/multiview_completion.py` | Audit requests and dependency closure; prepare condition-only inputs; verify/import generated RGB bundles; report evaluation availability; export an HTML review |
| `tools/completion_viewfusion.py` | Validate source/checkpoint provenance and budgets; load saved conditions; run the authors' ViewFusion DDIM sampler in an explicitly supplied CUDA environment |
| `tools/completion_package.py` | Package permitted conditioning inputs and isolated source; exclude evaluator snapshots, held-out photographs and all-view ratio tables |
| `tools/tests/test_multiview_completion.py` | Audit, leakage, immutable inputs, candidate contracts and archive isolation checks |
| `tools/tests/test_completion_viewfusion.py` | Camera conditioning, crop/mask handling and backend request checks |
| `tools/MULTIVIEW_COMPLETION.md` | CLI and limitations |

The implemented representation is `novel_view_rgb`. It does not reconstruct metric meshes, validated depth or hidden biological anatomy. Imported candidates remain `origin=generative`, `validated_metric=false`, `suitable_for_ppfd=false`. Existing measured geometry and optical gates remain authoritative. Without a validated original-camera mapping, the evaluator reports silhouette metrics unavailable rather than manufacturing alignment or scores.

## Current artifacts and settings

All paths in this document are relative to the project root `Tomato 3D phenotyping analysis`, except the commands explicitly labelled for an extracted package. Let `R = build/multiview_completion_20261003_01` when reading the abbreviated paths below.

| Artifact | Current location under R |
| --- | --- |
| Status and pending work | `implementation_status.json` |
| Local full requests and evaluator inputs | `real_t1_inputs/` |
| Current allowed-input preparations | `multiview_prepared_03/`, `top_only_prepared_03/` |
| Transfer archives | `multiview_execution_package_02/execution_package.zip`, `top_only_execution_package_02/execution_package.zip` |
| Pinned official source and manifest | `vendor/ViewFusion/` |
| Limited preservation evidence | `existing_code_preservation.json` |

Earlier preparation/archive revisions are historical. Use the versions above and verify their manifests before transfer. The preservation report covers four previously existing source files; it is not a claim of exhaustive repository integrity verification.

| Input or setting | Current value and meaning |
| --- | --- |
| Identity | `plant_id=dwt_t1`, `session_id=dwt_t1_20261002`; prepared `capture_date` is null, not inferred from the name |
| Multiview conditions | `dwt_t1_20261002_27` top plus `dwt_t1_20261002_03` side |
| Top-only condition | Only image 27; image 03 and its derived information must remain outside this backend |
| Held-out photograph | Image 13 remains local for evaluation |
| Source conditioning | Original RGB, saved union masks, camera metadata and provenance; recorded square crop, white background, 256-pixel model input |
| Pose units | Polar and azimuth degrees in requests; explicit model radius units; model radius is not metric scale |
| Seeds and work limits | Seeds 42/43; 2 virtual targets per seed; 50 steps; maximum 1,800 seconds per mode; declared minimum 12 GiB device memory, not demonstrated sufficiency |
| Sampler settings | Guidance 3.0; DDIM eta 0; autocast enabled |
| Output | Generated PNGs, `candidate_bundle.json`, `status.json`, hashes, preprocessing and runtime provenance after a successful run |

The selected poses have `passes_pose_gate=false`; rigid movement consistency is not independently verified. These flags must remain visible. The arms currently use different target azimuths derived only from their allowed inputs. They are diagnostic execution preparations, not a controlled matched-view quality comparison. Claude should specify a common target/evaluation contract without leaking side-derived evidence into the top-only input. Do not compare unmatched generated images as if they share a verified camera.

No new custom environment variable is required by the runner: request, vendor tree, checkpoint and output directory are explicit CLI arguments. Python packages and CUDA are external runtime dependencies. The wider project uses `TOMATO3D_DATA_ROOT` and `TOMATO3D_CONFIG_DIR`; preserve existing settings and human configuration. Temperature, light, humidity and biological growth coefficients are not inputs to this image trial.

## Runtime and checkpoint status

The pinned ViewFusion revision is `61286dc572ae3b4e8924ab51c45ca0bbd53c58ea`. The inspected authors' multi-input script is `zero123/generate_360_multi_view_autoregressive.py`. Source provenance is recorded in the vendor manifest.

Selected official checkpoint: `cvlab/zero123-weights/105000.ckpt`. Recorded metadata gives 15,465,973,531 bytes and SHA256 `f0fee4e7c1d81c70af5a5f7bb6185fd03d75f0764f8fb9a2efaf729c69679855`. Only metadata and an 8-byte range were inspected; the checkpoint has not been downloaded. The runner uses `weights_only=True, mmap=True`; actual compatibility with this checkpoint remains unverified.

The local PC has Intel Iris Xe, no NVIDIA GPU, Python 3.13.3 and approximately 1.6 GiB free RAM at the latest runtime check. CPU fallback is disabled. No global package changes were made. Read-only distribution metadata found torch 2.13.0, torchvision 0.28.0, numpy 2.2.4, transformers 5.14.1 and omegaconf 2.3.1. Several required legacy distributions were absent; metadata does not prove import compatibility.

Resolve runtime dependencies in an isolated GPU environment. Source imports include CarveKit even though saved masks are supplied, legacy `pytorch_lightning.utilities.distributed`, taming VectorQuantizer2, OpenAI CLIP and Kornia. Model construction can also obtain CLIP weights. The archive is not a verified turnkey installation. Record compatible versions and any source patches explicitly; do not modify the hashed vendor tree silently or install into the existing program.

## Evidence and remaining work

Recorded verification: initial 44 combined completion/detection/normalization tests passed; after adding archive isolation coverage, 25 completion-specific tests passed. The 20 detection/normalization cases were unchanged, not rerun as a new combined 45-test result. Three CLI help checks passed. These records validate tooling, not real model inference or biological accuracy.

No remote upload, GPU job, checkpoint inference or actual generated candidate bundle exists for this trial. The task was marked blocked after the same unanswered execution-destination dependency recurred. No job handle is live to monitor. Do not restart or report completion from a state file alone.

Claude should review the scientific comparison and coordinate these remaining steps with the user and implementation owner:

1. Resolve the already pending GPU destination/upload choice without reopening public-model permission. Preserve original inputs and keep held-out data local.
2. Review whether RGB hypotheses meet the intended comparison question. If metric geometry is required, return a separate exact reconstruction/evaluation specification; this runner does not supply it.
3. Specify a fair common target/evaluation procedure, pose assumptions and acceptance criteria. Separate visual plausibility from evidence of correct hidden leaves. Preserve unavailable metrics when evidence is absent.
4. In the selected isolated runtime, validate dependencies, CLIP/checkpoint loading, actual memory needs and bounded sampling. Record failures as failures. Preserve every declared seed rather than selecting attractive samples.
5. Run both authorized trial arms, collect complete outputs, verify/import their bundles and inspect the review. Report what ran, what failed, and what remains scientifically unavailable.

Once a GPU runtime and checkpoint are supplied, run from each extracted archive root with a fresh output directory:

```text
python run_trial.py --request backend_request.json --vendor vendor/ViewFusion --checkpoint /path/to/105000.ckpt --out build/trial_01
```

After returning the complete output directory, the local project commands are:

```text
python -m tools.multiview_completion import --prepared <matching_prepared_03> --candidate <returned_run>/candidate_bundle.json --out build/<fresh_import>
python -m tools.multiview_completion evaluate --prepared <matching_prepared_03> --imported build/<fresh_import> --out build/<fresh_evaluation>
python -m tools.multiview_completion review --imported build/<fresh_import> --out build/<fresh_review>
```

These are continuation instructions, not evidence that those commands have run on actual model results. Keep Codex changes within `tools/` and `tools/tests/`, generated files within fresh `build/` folders, and handoff updates append-only. Do not modify `tomato3d/`, `tests/`, `config/`, `docs/` or human measurements from this implementation task. Coordinate OneDrive edits to avoid simultaneous writes.

## Supporting records

- `handoff/CODEX_MULTIVIEW_COMPLETION_EXECUTION_2026-10-03.md`: append-only execution history and runtime audit.
- `handoff/CODEX_MULTIVIEW_DIFFUSION_INTEGRATION_SPEC_2026-10-03.md`: proposed integration contract; distinguish proposals from delivered behavior above.
- `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md`: detection area baseline.
- `handoff/CLAUDE_TO_CODEX_MASTER_HANDOFF_2026-10-03.md`: earlier project background; the explicit user public-model exception above supersedes its restriction only for this comparison.

Requested Claude response: retained decisions, required scientific or runtime corrections, and a prioritized implementation handoff naming files, inputs, outputs, units and acceptance evidence. Keep actual model execution marked incomplete until genuine trial outputs are collected and inspected.
