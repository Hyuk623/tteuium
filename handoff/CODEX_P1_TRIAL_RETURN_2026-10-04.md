# P1 GPU trial return and memory correction

English execution brief, 2026-10-04. Continue CODEX_P1_3D_CHAT_PROMPT_2026-10-03.md and the previous P1 report. User selected Claude Code as uploader. This task only observes/retrieves the existing remote job and prepares local corrections; no upload or new remote job is authorized for Codex here.

## Observed v5 evidence and intended correction

Read-only Kaggle status confirmed version 5 running and later terminal COMPLETE. Returned files under build/p1_trial_return_20261004_01/returned_v5 show both arms failed with CUDA OOM at the second entry into model.ema_scope, specifically LitEma.store cloning parameters. Each arm saved seed 42 T_eval.png after one complete sampling pass, but no candidate_bundle.json exists. Partial PNGs are evidence of partial execution, not successful candidate bundles.

The pinned LitEma.restore copies weights back but retains collected_params. A later store builds a new cloned list while the old one is still live. The error stack identifies this allocation, not a proved inability to run a single view on T4. Maintain the authors' EMA weights once around the entire inference-only seed/target loop instead of repeatedly entering its context for each view. Preserve inference_mode, per-view autocast, seed reset, targets, conditioning and budgets. Leave the pinned vendor tree and Claude's remote launcher unchanged.

Validation: inspect the small diff, run existing completion checks, exercise numerical EMA equivalence and snapshot lifetime using the actual pinned LitEma with a tiny CPU model, then pack fresh archives for the selected execution owner. Neither a tiny diagnostic nor successful packaging proves the full checkpoint GPU retry. Preserve real failure files and report actual partial-image inspection separately from metrics.

## Delivered correction and actual verification

Changed only the existing owned runner `tools/completion_viewfusion.py`: one `torch.inference_mode(), model.ema_scope()` now encloses every declared seed/target, with autocast retained per view. EMA and source weights are still checked and restored through the authors' existing context. No parameter freezing, checkpoint selection, seed, target, budget, image preprocessing or vendor source changed. `build/p1_trial_return_20261004_01/runner_ema_scope.patch` records the difference from the actual v5 packaged runner.

Commands executed:

```text
python -X utf8 build/p1_trial_return_20261004_01/check_ema_lifetime.py
python -X utf8 -m pytest tools/tests/test_multiview_completion.py tools/tests/test_completion_viewfusion.py -q --junitxml=build/p1_trial_return_20261004_01/completion_tests.junit.xml
python -X utf8 build/p1_trial_return_20261004_01/inspect_returns.py
```

Results: 35 completion tests passed. The independent tiny CPU diagnostic used the pinned LitEma and its actual ema_scope function: 10 predictions exactly matched between repeated and single-scope evaluation, original model parameters were restored, and store calls fell from 10 to 1. The old context retained two backup tensors before each later store; the new context took one snapshot only. This supports numerical equivalence and removal of the observed repeated-backup allocation. It is not a full-model memory benchmark or successful GPU retry.

## Verified remote output and partial visual review

Kaggle version 5 was observed live and then terminal COMPLETE. Output retrieval used the UTF-8 Python CLI entry point after the executable's default file encoding failed on a Unicode log. Retrying the same read-only download completed with exit code 0; the GPU job was not restarted.

The returned runtime records successful checkpoint size/hash verification, a Tesla T4 with 14.562 GiB and peak observed usage of 14.556 GiB in each failed arm. Actual OOM occurred in the second EMA backup allocation after one completed 50-step generation. This supersedes the earlier checkpoint-load blocker; the new blocker is repeated EMA snapshot memory and the unverified corrected retry.

`result_audit.json` preserves terminal failure statuses, runtime/version information and hashes. `comparison.csv` contains 20 failed planned-sample rows with blank scores; it does not represent 20 outputs. There are two partial PNGs and zero complete candidate bundles. No import/evaluation success was fabricated. Both partial images were inspected; `partial_visual_review.md` records their disconnected leaf-like fragments, large white gaps and differing dark/green appearance without anatomical or accuracy claims. Target pose gates remain false; IoU/F-score are unavailable without a validated camera mapping.

## Ready for the selected execution owner

Fresh immutable transfer archives:

- `build/p1_trial_return_20261004_01/multiview_execution_package_05/execution_package.zip`
- `build/p1_trial_return_20261004_01/top_only_execution_package_05/execution_package.zip`

`retry_packages.json` verifies every declared member (83 multiview, 79 top-only), exact conditions and common targets. These packages reuse `build/multiview_completion_20261003_02/{arm}_prepared_04` and the frozen evaluation contract. They were not uploaded by Codex. The existing Claude runtime shim that solved old NumPy aliases is still needed; the new archives do not silently install dependencies or alter that shim.

Claude Code should replace its transfer archives with these versions, preserve the existing audited checkpoint/runtime configuration, and rerun both arms within the same budgets. Do not drop seeds/targets, change the checkpoint, lower image resolution or relabel a failed arm to make the job pass. Return complete outputs, runtime information and genuine failures. P1 Codex can then import/evaluate/review complete successful bundles. The current full objective remains incomplete until that retry and its returned-output checks establish the requested end state. Real metric/optical acceptance and interproject linking remain separate unavailable/deferred work under the original P1 contract.

## Claude return contract for v6

Read CLAUDE_TO_CODEX_VIEWFUSION_RUNNER_FIXES_2026-10-04.md. Claude has stopped editing tools and requests six bounded owned changes before its v6 upload: CPU EMA application and removal, one-time condition encoding, partial bundle persistence and final-only import, strict shared sampler/seed/checkpoint/equal-weight checks, parsed exact ID/path isolation, and targeted regression tests. This supersedes the single-scope interim memory fix with lower weight residency. Preserve the frozen _04 preparations/evaluation contract, recorded failures, source images and vendor. Implement and test locally, then return fresh archives and one LOG entry for Claude to execute. No remote upload/push by Codex.
