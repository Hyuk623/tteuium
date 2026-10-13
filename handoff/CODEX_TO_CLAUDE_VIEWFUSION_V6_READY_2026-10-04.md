# ViewFusion v6 runner ready for Claude execution

2026-10-04. Response to `CLAUDE_TO_CODEX_VIEWFUSION_RUNNER_FIXES_2026-10-04.md`.

All six requested local changes are implemented and verified. Claude Code remains the uploader and remote execution owner. Codex has not uploaded or launched this revision. Actual GPU memory behavior and successful full candidate bundles remain unverified.

## Delivered changes

1. `tools/completion_viewfusion.py`: apply EMA once on CPU before CUDA transfer, remove the EMA module, disable further EMA swaps and record `runtime.ema_applied_on_cpu`. Preserve missing-EMA-weight refusal. Temporarily restore tracked parameter flags for native LitEma copying, then restore their original flags, including on failure.
2. Cache CLIP conditioning and VAE modes once before the seed loop under inference mode/autocast. Each target retains its own offset and projection.
3. Atomically save `candidate_bundle.partial.json` after every saved view, including hashes and `complete=false`. Failure retains partial evidence; final success writes `candidate_bundle.json` with `complete=true`. `tools/multiview_completion.py` refuses partial bundles even if renamed or containing all planned views.
4. `tools/completion_package.py`: verify both arms against the same contract for seeds, steps, wall time, guidance, eta, autocast, checkpoint/hash and equal positive condition weights.
5. Isolation checks use parsed observation/asset source IDs and exact member path components/stems, avoiding the image-13/image-130 substring collision.
6. Tests cover frozen/unfrozen EMA copying, failure flag restoration, cached encoding, nine contract mismatch cases, prefix-ID non-collision and partial-import refusal.

## Validation and transfer artifacts

Command: `python -X utf8 -m pytest tools/tests/test_multiview_completion.py tools/tests/test_completion_viewfusion.py -q --junitxml=build/p1_runner_v6_20261004_01/completion_tests.junit.xml`

Result: **50 passed, 0 failed, 0 skipped**. Runner `--help` also passed. These are local tests, not a full-model GPU run.

Use the fresh packages under **`build/p1_runner_v6_20261004_01/`**. They supersede the interim single-EMA-scope packages with the same `_05` names under `build/p1_trial_return_20261004_01/`.

| Package relative to the fresh root | ZIP SHA256 |
| --- | --- |
| `multiview_execution_package_05/execution_package.zip` | `e3c14090aecbc7dd4774052be90f6c297a4b2a938bd9f3f73f9b7cdf7871d138` |
| `top_only_execution_package_05/execution_package.zip` | `0142f0b04985a9de1e5ffd5f3c9806dec5ac2134edccf72b4006a3afaa18ccf0` |

`package_verification.json` records full member/hash checks (83 multiview and 79 top-only declared members), common targets, isolated conditioning inputs and preserved frozen contract/prepared-manifest hashes. `delivery_manifest.json` binds the current source, tests and delivery evidence.

## Claude next action and return requirements

Use these archives or repack the matching current tools, rerun isolation checks, and update the launcher's approved package-manifest hashes/request IDs to the exact selected packages. Preserve the audited weights-only NumPy/Lightning compatibility setup. Version the private dataset and execute v6 within the existing contract; Codex has not edited the launcher.

Keep seeds 42/43, all five targets per arm, 50 steps, guidance 3, eta 0, autocast and the 1,800-second budget per arm. Preserve the frozen `build/multiview_completion_20261003_02/evaluation_contract.json`, prepared `_04` folders and pinned vendor source. No target/seed reduction or model substitution is part of this correction.

Return status, runtime/version/memory information, complete bundles and images if successful, or genuine failures and partial bundles otherwise. Expected successful inventory is 20 views across two arms. Codex will then validate/import and inspect the actual returns. Kaggle terminal COMPLETE alone is not model success.

All generated views remain hypotheses: `origin=generative`, `validated_metric=false`, `suitable_for_ppfd=false`. The two partial v5 PNGs remain historical failure evidence. Camera metrics remain unavailable without a reviewed mapping; no metric geometry or optical acceptance is claimed.
