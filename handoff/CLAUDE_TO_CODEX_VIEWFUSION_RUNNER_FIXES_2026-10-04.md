# ViewFusion runner fixes required before Kaggle attempt v6

Date: 2026-10-04. From Claude Code (execution owner, P1 trial) to Codex (owner of `tools/`).
Claude Code stopped editing `tools/` after observing a concurrent edit of `tools/completion_viewfusion.py` at 2026-10-04 12:44:19. Please apply the changes below, run the focused tests, and append one LOG line when done; Claude Code will then repack `*_execution_package_05`, re-run `verify_arm_isolation`, version the private dataset and push kernel v6.

## Evidence from actual Kaggle T4 attempts (kernel `dolgfish/tomato-viewfusion-trial-04`)

All returned outputs are preserved unchanged under `build/multiview_completion_20261003_02/kaggle/out_v1` ... `out_v5`.

| Attempt | Result | Cause |
| --- | --- | --- |
| v1 | both arms failed at `torch.load` | weights_only: `pytorch_lightning.callbacks.model_checkpoint.ModelCheckpoint` (callback class used as dict key) |
| v2 | stopped before arms (fail-closed audit) | checkpoint also references `numpy.core.multiarray.scalar`, `numpy.dtype` |
| v3 | both arms failed at `torch.load` | numpy 2 renamed `numpy.core` -> `numpy._core`; allowlist needs `(obj, recorded_name)` tuples |
| v4 | both arms failed entering `ema_scope()` | `model.requires_grad_(False)` makes `LitEma.copy_to` assert; Claude removed that line on 2026-10-04 (inference_mode already disables autograd) |
| v5 | first sample written (`seed_42/T_eval.png`, both arms), then CUDA OOM at 14.23 GiB | `ema_scope()` per target: `LitEma.store` clones the UNet while the previous clone is still alive |

Runtime facts: Tesla T4 14.56 GiB, Python 3.13, torch 2.11.0+cu128, pytorch-lightning 2.6.6, kornia 0.8.3, clip-anytorch 2.6.0. Checkpoint size and SHA256 verified (`f0fee4e7...679855`), 1938 state keys, 688 `model_ema.*`, 686 UNet keys, `cc_projection` present. Weights-only allowlist and import shims (Lightning `utilities.distributed`, CarveKit and taming refusal stubs) live in the kernel launcher, not in the vendor tree; see `kaggle/kernel/viewfusion_trial.py`.

The current single `ema_scope()` around all seeds (present in the file at 12:44) addresses the double clone but still keeps UNet + EMA buffers + one clone resident (about 10-11 GB of weights on a 14.56 GiB device).

## Required changes

1. `tools/completion_viewfusion.py::run` - apply EMA once on CPU before `.to('cuda')`: after the missing-key checks, if `model.use_ema`: `model.model_ema.copy_to(model.model)`; `del model.model_ema`; `model.use_ema = False`. Record `ema_applied_on_cpu=true` in `runtime`. This removes per-sample swaps and about 7 GB of GPU residency without editing the vendor tree. Keep the existing `model_ema.*` missing-key refusal.
2. Same function - compute `model.get_learned_conditioning(cond_images)` and `model.encode_first_stage(cond_images).mode()` once before the seed loop (under inference_mode/autocast); per target only build the offset, `cc_projection`, cond/uncond dicts and sample.
3. Same function - salvage partial results: after each saved view, write `candidate_bundle.partial.json` (same schema fields as the final bundle, candidates so far with hashes, `complete=false`). The final `candidate_bundle.json` stays the only importable bundle; a failed run must keep its partial file and the failure status.
4. `tools/completion_package.py::verify_arm_isolation` - also require, for every arm, equality with the contract and across arms of: `budgets.seeds`, `budgets.steps`, `budgets.max_wall_time_s`, `backend.parameters` (guidance_scale, ddim_eta, autocast), `backend.checkpoint`, `backend.checkpoint_sha256`, and per-target `condition_weights` equal to the contract's `equal` rule. Contract fields: `seeds`, `sampler.{steps,ddim_eta,guidance_scale,autocast,checkpoint,checkpoint_sha256,max_wall_time_s_per_arm}`.
5. Same function - replace substring leak checks (`i in request_text`, `i in n`) with parsed fields: observation `image_id`, asset `source_image_ids`/`asset_id`, and member path components/stems. Avoids false refusals such as `..._130` versus forbidden `..._13`.
6. Tests in `tools/tests/`: EMA application with a small fake LitEma-shaped model (frozen parameters must not assert; EMA values must land in the module); sampler/seed mismatch refused by `verify_arm_isolation`; prefix-ID non-collision.

Keep `origin=generative`, `validated_metric=false`, `suitable_for_ppfd=false`, all declared seeds/targets, and the 1,800 s budget. Do not change the contract `build/multiview_completion_20261003_02/evaluation_contract.json` or the prepared `_04` folders.

## Claude Code side already done (build/ only)

Kernel: pinned approved package manifest hash and request_id per arm, refusal of files not in the manifest, `nvidia-smi` monitor without a shell (terminated and waited), `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, non-zero exit when any arm fails. `make_comparison.py` takes `--returned` and reports failed/pending/unavailable rows separately.
