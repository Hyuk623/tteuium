# Multiview completion implementation and execution

Date: 2026-10-03. User explicitly requested actual code implementation and a model trial while preserving the existing program; the follow-up scope answer confirms implementation and trial execution.

## Inspected current state

The specification is CODEX_MULTIVIEW_DIFFUSION_INTEGRATION_SPEC_2026-10-03.md. No tools/multiview_completion.py exists. Existing detection-only ratios, observed surface comparison, fixed-camera projection and optical gates remain reusable. A historical p002_diffusion_comparison.zip contains an unexecuted Marigold single-image depth experiment, not an executed multiview completion backend. Do not substitute it for this objective.

The current PC reports Intel Iris Xe, no nvidia-smi, about 2.3 GiB free RAM of 15.6 GiB, Python 3.13, torch installed but no diffusers. No applicable diffusion checkpoint was identified in the scoped project filename inventory. The master handoff's no-base/untuned-model policy and Kaggle/Colab ownership require clarification for the proposed public-model cloud trial. Questions sent; no implied permission from elapsed time.

## Implementation scope

Create an optional Codex-owned adapter and tests: immutable source request audit, allowed-view dependency closure, frozen preparation, externally produced candidate bundle validation, image/geometry hypothesis evaluation and review output. Add an explicit bounded execution boundary for a verified model backend once compatibility and execution destination are resolved. Preserve raw photos, mask caches, source labels, tuned weights, camera calibration, pipeline defaults, human config and optical gates. First-label mask ratios remain source-linked and dimensionless. Write new artifacts only under fresh build directories; no pipeline patch, global dependency install, training or push.

Validation will exercise positive and negative contract paths, top-only leakage, immutable originals, missing scale and identity, first-label ratios, corrupted artifacts, budget/seed provenance, original coordinate transforms and candidate-vs-observed separation. Then prepare a real saved-input trial, execute an eligible model with explicit budgets, inspect outputs and compare against permitted evidence. Synthetic checks alone do not complete the model-execution objective. Log actual trial or precise external blocker state; do not claim a model run from a successful adapter test.

## Implementation checkpoint

User explicitly approved public pretrained models for this comparison only. The execution-destination question remains unanswered; no upload or GPU job has been started. Existing Kaggle CLI authentication was verified with a read-only kernels listing.

Added tools/multiview_completion.py (audit, preparation, candidate import, availability evaluation and review), tools/completion_viewfusion.py (bounded CUDA ViewFusion/Zero123 runner), tools/completion_package.py (condition-only archive) and tests/documentation. Actual multi-input source discovered at zero123/generate_360_multi_view_autoregressive.py. Downloaded 65 official source/config/licence files at revision 61286dc572ae3b4e8924ab51c45ca0bbd53c58ea, verifying Git blob hashes and recording SHA256, with no weights or dependency installation.

Prepared actual T1 top+side and top-only packages from saved masks and photo evidence. Preserve per-photo first-leaf ratio CSV. Selected source poses fail the original quality gate and remain diagnostic; no failure was relabelled. Inputs and mask-cache hashes were unchanged. Current preparations: build/multiview_completion_20261003_01/multiview_prepared_02 and top_only_prepared_02. Separate execution archives are about 12.8 MB and 6.8 MB; evaluation image 13 and evaluator metadata are excluded. Seeds 42/43, 2 virtual targets, 50 steps, max 1800 s per mode are bounded pilot settings, not biological criteria.

Validation: initial 44 combined completion/detection/normalization tests passed in 2.94 s; after adding archive isolation coverage, 25 completion-specific tests passed in 2.59 s. Three CLI help checks passed. Collection naming and a Lanczos rounding expectation were corrected during testing. No synthetic result is presented as actual model output.

Still required for the user's complete objective: resolve execution destination; install/verify isolated runtime and official checkpoint; run the actual bounded model trials; collect and inspect actual generated images and status/provenance; import/review results; report model behavior and real limits. Runtime dependency compatibility, checkpoint loading and practical VRAM are not yet verified. RGB-only candidate import intentionally does not claim metric candidate-mesh or hidden-anatomy completion. Goal remains active; do not mark it complete from this checkpoint.

### Checkpoint and package update

Official Hugging Face metadata for cvlab/zero123-weights/105000.ckpt reports 15,465,973,531 bytes and LFS SHA256 f0fee4e7c1d81c70af5a5f7bb6185fd03d75f0764f8fb9a2efaf729c69679855. An 8-byte HTTP range request confirmed ZIP-based serialization; no weight download occurred. Updated the runner to use weights_only=True and mmap=True rather than allocate the complete training checkpoint in RAM. Actual GPU loading remains untested.

Latest artifacts supersede the earlier preparation paths: multiview_prepared_03, top_only_prepared_03, multiview_execution_package_02 and top_only_execution_package_02 under build/multiview_completion_20261003_01. The source request revisions pin the checkpoint hash/size. implementation_status.json explicitly lists the still-unexecuted model/GPU steps; goal_complete=false. Existing source code hashes were checked against the previous detection calculation's audit and remained unchanged. Execution destination is still pending; no remote write or model execution.

### Read-only runtime readiness follow-up

The local Python is 3.13.3. Distribution metadata reports torch 2.13.0, torchvision 0.28.0, numpy 2.2.4, transformers 5.14.1 and omegaconf 2.3.1. pytorch-lightning, torchmetrics, kornia, einops, carvekit-colab, clip and taming-transformers distribution metadata are absent. This metadata check does not prove import or checkpoint compatibility. No dependencies were installed or changed.

Source inspection confirms unconditional CarveKit import in zero123/ldm/util.py, the legacy pytorch_lightning.utilities.distributed import in ddpm_swap_att.py, taming VectorQuantizer2 in autoencoder.py, and OpenAI CLIP/Kornia imports in the encoder. Saved masks do not eliminate those import requirements. A dedicated compatible runtime still needs import and GPU smoke tests. Do not treat the archives as a verified turnkey environment; no speculative dependency pins or vendor patches were applied.

The execution-destination question remains unanswered. The public-model exception is approved, but it does not select a GPU host or authorize the proposed private-photo upload. No model inference, remote write, checkpoint download or further code change occurred in this follow-up. Existing test evidence is unchanged, not rerun. The actual trial remains pending.
