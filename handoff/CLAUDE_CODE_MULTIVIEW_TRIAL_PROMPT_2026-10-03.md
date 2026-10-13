# Claude Code prompt: finish the multiview diffusion trial (P1 `3d구현`)

Date: 2026-10-03. Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.
Talk to the user in Korean. Write code, handoffs and logs in English. Tables as CSV, settings/provenance as JSON.

## Goal

Complete the already authorized ViewFusion novel-view trial for `dwt_t1` with a fair, common evaluation contract, run both arms on a GPU, and import/evaluate/review the real outputs locally. The result is an RGB hypothesis comparison, not metric geometry, hidden anatomy or growth evidence.

## Read first

1. `handoff/CLAUDE_DETECTION_DIFFUSION_HANDOFF_2026-10-03.md` (current state, settings, commands)
2. `handoff/CODEX_MULTIVIEW_COMPLETION_EXECUTION_2026-10-03.md` (append-only history, runtime audit)
3. `handoff/CODEX_MULTIVIEW_DIFFUSION_INTEGRATION_SPEC_2026-10-03.md` (proposed contract; distinguish from delivered code)
4. `tools/MULTIVIEW_COMPLETION.md`, `tools/multiview_completion.py`, `tools/completion_viewfusion.py`, `tools/completion_package.py`
5. `build/multiview_completion_20261003_01/implementation_status.json` and `existing_code_preservation.json`
6. Parent `공통규약.md`, `AGENTS.md`, `CONVENTIONS.md`, latest `handoff/LOG.md` / `handoff/TODO.md`

Before editing any file under `tools/`, check LOG/TODO for an active Codex session on the same files. If one is active, stop and write the change as a requirement for Codex instead of editing.

## Fixed decisions (do not reopen)

- Public pretrained models are allowed for this comparison only. Do not replace production detector/SAM weights.
- Existing leaves stay observation based. Generated pixels never become observed growth, training ground truth, metric surfaces or optical tissue.
- First-leaf=1 relative areas stay dimensionless; never convert them to cm2.
- Absent: reviewed curved-surface spec, confirmed correspondences, independent leaf-area measurements. Do not search or ask for them again.

## Step 0 — GPU destination (ask the user once, then proceed)

Public-model permission is not permission to upload private photos. Ask the user with one question:
- A. User runs the packaged archive in Colab or Kaggle (recommended; Claude prepares a notebook/cell list and the user executes)
- B. Private Kaggle dataset/kernel upload executed by Claude (needs explicit upload approval)
- C. Another GPU host the user supplies

Whatever is chosen: held-out image 13 and evaluator inputs never leave the local machine. Only the two `execution_package.zip` contents (re-made in Step 1) may be uploaded.

## Step 1 — Common target and evaluation contract (fix before running)

Problem: the multiview arm (images 27 top + 03 side) and top-only arm (27 only) currently use different target azimuths, so outputs are not comparable.

1. Define one target pose list used identically by both arms. Targets are camera poses only, never image content:
   - T_eval: the measured pose of held-out image 13 (board frame, polar/azimuth deg, model radius), used only as a target pose.
   - T_ring: a small fixed set of board-frame poses declared in the contract file (e.g. 4 azimuths at the top-view-free side elevation), independent of either arm's inputs.
   Confirm that giving a target pose does not leak image-13 pixels, masks or side-derived geometry into the top-only arm. If the pose of 13 itself fails the pose gate, keep it as a target but carry `passes_pose_gate=false` into every result row.
2. Write `build/multiview_completion_20261003_02/evaluation_contract.json` with: target list and source of each pose, units, seeds (42, 43), samples per target, sampler settings (50 DDIM steps, eta 0, guidance 3.0, autocast), metrics, and which metrics are unavailable without a validated original-camera mapping.
3. Metrics: silhouette IoU and boundary F-score against the saved union mask of image 13 only when the camera mapping is validated; otherwise `unavailable` with the reason. Report visual-review notes separately from metrics. Visual plausibility is not evidence of correct hidden leaves.
4. Rebuild both preparations and archives from the contract into fresh folders (`multiview_prepared_04`, `top_only_prepared_04`, `*_execution_package_03`). Verify that the top-only package contains no image 03 data or anything derived from it, and that no package contains image 13, evaluator snapshots or all-view ratio tables. Add a regression test for this isolation and for identical target lists across arms.

## Step 2 — Isolated runtime

- Create a fresh isolated environment on the chosen GPU host. Never install into the project's local Python.
- Resolve: CarveKit import (masks are supplied; patch only the import path if needed), legacy `pytorch_lightning.utilities.distributed`, taming VectorQuantizer2, OpenAI CLIP, Kornia. Record exact versions in `runtime_env.json`. Record any vendor source patch as a separate diff file; do not silently edit the hashed `vendor/ViewFusion` tree (pinned `61286dc572ae3b4e8924ab51c45ca0bbd53c58ea`).
- Download checkpoint `cvlab/zero123-weights/105000.ckpt` on the GPU host; verify size 15,465,973,531 bytes and SHA256 `f0fee4e7c1d81c70af5a5f7bb6185fd03d75f0764f8fb9a2efaf729c69679855` before loading.
- Record GPU model, memory, and peak memory per arm. CPU fallback stays disabled. Respect the 1,800 s per arm budget; record a timeout as a failure.

## Step 3 — Run both arms

```text
python run_trial.py --request backend_request.json --vendor vendor/ViewFusion --checkpoint /path/to/105000.ckpt --out build/trial_<arm>_01
```

Run every declared seed and target. Keep all samples; no cherry-picking. Failures stay recorded as failures with error text. Bring back the complete output directories unchanged.

## Step 4 — Local import, evaluation, review

For each arm with its matching `*_prepared_04`, into fresh `build/` folders:

```text
python -m tools.multiview_completion import   --prepared <prepared_04> --candidate <returned_run>/candidate_bundle.json --out build/<fresh_import>
python -m tools.multiview_completion evaluate --prepared <prepared_04> --imported build/<fresh_import> --out build/<fresh_evaluation>
python -m tools.multiview_completion review   --imported build/<fresh_import> --out build/<fresh_review>
```

Then write `build/multiview_completion_20261003_02/comparison.csv` (arm, seed, target_id, metric, value, unit, availability, reason, passes_pose_gate) and open the review HTML to inspect it yourself.

## Constraints

- Do not modify `tomato3d/`, root `tests/`, `config/`, `docs/`, human measurements or original photos.
- All generated files go to fresh `build/` folders; earlier preparations/archives stay as history.
- Imported candidates keep `origin=generative`, `validated_metric=false`, `suitable_for_ppfd=false`.
- Do not report completion from a state file; only from inspected real outputs.

## Acceptance

1. `evaluation_contract.json` exists; both arms share an identical target list (test passes).
2. Isolation test passes for both new packages.
3. Both arms ran on the GPU, or each failure is recorded with cause; checkpoint hash verified.
4. Imports, evaluations and reviews exist for every successful arm; unavailable metrics carry reasons.
5. `comparison.csv` and a short visual review note exist.
6. Focused tests rerun: `python -X utf8 -m pytest tools/tests/test_multiview_completion.py tools/tests/test_completion_viewfusion.py -q` with the JUnit XML saved in the new build folder.

## Deliverables

- English handoff `handoff/CLAUDE_MULTIVIEW_TRIAL_RESULT_2026-10-03.md`: what ran, what failed, contract, metrics, runtime, file hashes, remaining unavailable science.
- One LOG.md line (append-only); TODO updates for anything left open.
- Korean summary to the user: results in 3–5 lines, plus any decision needed next.
