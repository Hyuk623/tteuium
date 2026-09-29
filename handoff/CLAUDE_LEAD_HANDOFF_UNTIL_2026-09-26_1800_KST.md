# Handoff to Claude Code: sensitivity review and continued tomato work

## User instruction and leadership period

The user explicitly requested that, after Codex completes the current sensitivity-review web implementation, the completed work and remaining work be documented and **Claude Code take the lead until 2026-09-26 18:00 Asia/Seoul (UTC+09:00)**.

This file records that transfer. Claude Code is the primary coordinator for follow-up implementation and review during that interval. Codex will not independently continue editing these shared project files during the interval unless the user asks. This is a file-based handoff, not evidence that a message was delivered to a running Claude session. There is no scheduled job or automatic execution at the deadline. Avoid simultaneous editing in this OneDrive directory and record which files are being changed.

## Scope completed so far

1. Human Roboflow exports were grouped by plant and retained with source provenance. The current reconstruction/mask scope is dwt_01 and dwt_02 only. Claude imported 776 human organ annotations in 30 middle/side photos into the existing original-pixel editor flow. Leaf and compound segmentation polygons in those exports are rectangles; they are bbox labels, not measured leaf outlines.
2. Codex implemented and ran the authorized local SAM 2.1 Hiera Tiny CPU bbox-mask pipeline for **577 leaflet observations**, not 577 distinct physical leaflets. All 577 have generated candidate sets. The original preparation, source images, boxes and previous geometry were preserved.
3. Codex reviewed Claude's latest dwt_02 geometry and importer. Reproducibility/import-validation findings remain open; see the references below. Existing geometry remains diagnostic and is not PPFD-ready.
4. The existing local editor now supports **compound-leaf and leaflet sensitivity comparison**, with separate class-specific batches, cached-logit previews and explicit saving. No separate application or parallel annotation database was introduced.

## Current web implementation

Open the running local editors:

- dwt_01: http://127.0.0.1:8821/
- dwt_02: http://127.0.0.1:8822/

The Korean interface provides class, photograph and observation selectors; synchronized reference/preview canvases; sensitivity slider and numeric input; 20/50 presets; candidate selection; opacity/mask visibility; shared zoom/pan; include/exclude points; manual contour editing; explicit preview save; restore; accept/defer/reject; and undo.

Suggested user flow: select the organ class, photo and observation; generate a draft if pending; compare sensitivity/candidates; save the preview; inspect and explicitly accept if appropriate. Include/exclude points or contour editing are needed when threshold changes alone cannot separate overlapping organs.

Sensitivity is **not an accuracy score**. The threshold is `(50 - sensitivity) * 0.08` on cached SAM logits. A lower setting is stricter and generally shrinks the mask. Sensitivity 20 means logit > 2.4; 50 means logit > 0. Existing saved items were not reset. Unreviewed leaflet items initially display an **unsaved** preview at 50; reviewed/edited items open at their saved setting. The user's existing dwt_01_a206 edit at sensitivity 71 was preserved.

Moving the slider or selecting another candidate is an in-browser preview: no inference and no disk mutation. Use `미리보기 저장` to persist the settings. This marks the item edited/unconfirmed, not accepted. `저장값 복원` discards the unsaved sensitivity/candidate choice; `되돌리기` restores the preceding saved review state. Saving a changed threshold/candidate replaces any existing manual contour for that item, with a visible warning and an undo snapshot.

No fragment deletion, hole filling, hidden-leaf completion, parent assignment, cross-view identity confirmation or 3D reconstruction is performed by these controls. Compound boxes can include leaves from another compound leaf; SAM and sensitivity alone cannot resolve biological membership.

## Data state at handoff

| Plant | Leaflet observations ready | Leaflet review state | Compound observations prepared | Compound drafts ready |
| --- | ---: | --- | ---: | ---: |
| dwt_01 | 292/292 | 291 unreviewed, 1 edited | 49 | 1 |
| dwt_02 | 285/285 | 285 unreviewed | 41 | 0 |

The real compound smoke test generated `dwt_01_a37` from view 21. At sensitivity 50 its selected candidate covers 273,017 original-crop pixels; at 20 it covers 206,698. These numbers demonstrate threshold behavior, not segmentation accuracy. It remains unreviewed. The other **89 compound observations** remain pending and can be generated individually using `선택한 잎 초안 생성`, or through the explicitly selected current-class batch action.

Output locations:

- Existing leaflet batches: `build/leaflet_mask_batch_20260922/<plant>/`.
- New compound batches: `build/sensitivity_web_20260922/<plant>/compound/`.
- Verification artifacts: `build/sensitivity_web_20260922/`.
- UI-only fixture: `build/sensitivity_web_20260922/ui_fixture/`. **Exclude this and the older `build/leaflet_mask_batch_20260922/ui_test_fixture/` from research/training data.** Fixture edits and acceptance tests are not human annotation decisions.

Masks remain linked to original photo-level annotation IDs. `leaflet_id`, compound parent identity and physical point correspondence are separate concepts. Accepted exports remain separate from original bboxes and include organ class. A mask accepted in one photo does not certify cross-view identity, depth or PPFD suitability.

## Files and interfaces changed by Codex

- `tools/leaflet_mask_batch.py`: organ aliases, separate class preparation/defaults, selected-observation generation, class-aware exports, read-only binary logits.
- `tools/serve_leaf_edit_session.py`: optional `--compound-mask-batch`, class routing on batch endpoints, authenticated logits delivery, preview math script injection. Existing single-observation segmentation and editor routes remain.
- `tools/leaflet_mask_batch.js`: integrated Korean comparison/review interface.
- `tools/mask_preview_math.js`: float32-compatible browser thresholding without cleanup.
- `tools/tests/test_leaflet_mask_batch.py`: class isolation, preview equivalence, float32 boundary and authenticated HTTP routing regressions.

GET batch endpoints accept `organ_class=leaflet|compoundleaves`. POST batch requests carry the same field. Omitting it retains legacy leaflet routing. `POST /api/mask-batch/start` accepts an optional original observation `id` to generate only that observation. All model work uses the existing local configuration and shared per-server model lock.

`GET /api/mask-batch/logits/<observation_id>` returns four little-endian uint32 values (candidate count, crop height, crop width, item revision), followed by candidate-major float32 logits at original crop resolution. It requires the existing local token and verifies the cached file hash. Browser comparison uses a float32 threshold (`Math.fround`) to match NumPy's float32 boundary behavior. Masks retain disconnected components and holes; display zoom never changes saved original-image coordinates.

No changes were made by this task to `tomato3d/`, `tests/`, `config/` or `docs/`. No new training, remote inference, 3D reconstruction or PPFD calculation ran.

## Restart commands

Run from the project root. If the port is already serving the correct editor, keep it; do not start duplicate servers. Launch dwt_02 separately with `$plant = 'dwt_02'` and `$port = 8822`.

```powershell
$plant = 'dwt_01'
$port = 8821
python -X utf8 -m tools.serve_leaf_edit_session `
  --session "build/new_captures_20260920/$plant/edit_session" `
  --context "build/new_captures_20260920/$plant/edit_session/annotations.source.json" `
  --runs "build/leaflet_mask_batch_20260922/$plant/editor_runs" `
  --initial-backup "build/dwt_01_02_3d_20260922/$plant/labels/seed_with_imports.backup.json" `
  --segmenter sam2 `
  --segmenter-config build/photos1_manual3d_20260919/sam_auto_20260920/sam2_config.json `
  --mask-batch "build/leaflet_mask_batch_20260922/$plant" `
  --compound-mask-batch "build/sensitivity_web_20260922/$plant/compound" `
  --port $port
```

SAM checkpoint SHA-256: `7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`.
The configuration uses CPU with four threads. Initial model loading/generation may be slow on this host; cached sensitivity previews remain independent of model execution. There is no model download step in this task.

## Verification

- Focused batch/server suite: **23 passed**. Log: `build/sensitivity_web_20260922/pytest_final.txt`. Both changed JavaScript files pass `node --check`.
- Regression coverage includes aliases, separate compound preparation, one-item generation, original-pixel crop reconstruction, small components/holes, candidate changes, manual contour preservation, undo, acceptance gating, cache/source integrity, class-isolated routing and local token/origin enforcement.
- Live browser checks verified real saved sensitivity 71 survives preview comparisons and class changes; 20/50 previews alter area without saving; acceptance is disabled while the preview differs; and a real compound draft can be generated and previewed.
- Preservation audit: **579 existing leaflet files unchanged** (577 items plus two manifests), **50 recorded source files unchanged**. See `build/sensitivity_web_20260922/preservation_report.json`. This preserves the user's existing edited state rather than resetting everything to unreviewed.
- Additional fixture UI results are appended below after the final save/reload/undo checks.

## Claude follow-up priorities

1. Review the sensitivity UI and cached-score semantics, then support the user's individual review. Do not silently overwrite saved sensitivities, accept masks, or remove fragments as a default quality fix. The initial candidate-disagreement score is nearly saturated in this dataset and is not reliable evidence of correctness.
2. Generate further compound drafts only as needed for review. Resolve overlapping compound membership using visible evidence and reviewed sub-stem/attachment information, not threshold alone or JSON count quotas.
3. Fix/import-review finding F1/P1: centered-crop fixtures with 10/20-pixel borders were falsely accepted as verified uncropped stretches. Current 30 exports were not demonstrated to be cropped. Add crop/scale consistency validation before trusting changed exports.
4. Resolve geometry finding F2/P2: hand over complete executable hull/stem/compound generators; saved stem/tip scripts depend on missing `hull.py`, while the saved hull file only contains helpers. Preserve existing diagnostic artifacts and provenance.
5. Continue reviewed physical identity and correspondence only after the user has suitable labels. Maintain the 1-pixel calibration quality gate and current unverified/diagnostic status; do not call current outputs complete plant surfaces or PPFD-ready.
6. Claude's latest threshold-decision collector and compound-membership changes were noted in LOG.md, but **were not reviewed as part of this sensitivity UI task**. Keep synthetic fixture decisions out of any calibration/threshold fitting.

References: `CODEX_LEAFLET_MASK_BATCH_2026-09-22.md`, `CODEX_LEAFLET_MASK_BATCH_USAGE_2026-09-22.md`, `CODEX_COMPOUND_LEAFLET_SENSITIVITY_WEB_2026-09-22.md`, `CODEX_CLAUDE_DWT02_GEOMETRY_REVIEW_2026-09-22.md`, and the latest `LOG.md`/`TODO.md` entries. Earlier dated counts remain historical snapshots; use current manifests for current state.

## Final fixture UI verification

The isolated port-8823 fixture was launched **without a segmentation model**. Cached previews and edits remained functional: sensitivity 71 -> unsaved 65 -> explicit save -> reload retained 65 -> undo restored 71 and 21,065 pixels. Switching the candidate produced a different area and disabled acceptance until saved/restored. Explicit acceptance of the fixture observation moved to the next item. None of these fixture actions was applied to the real research items.

The live browser comparison at the actual dwt_01_a206 item showed 0 pixels at sensitivity 20, 5,605 at 50 and the saved 21,065 at 71; restoring the saved setting did not write the item. This is an example of why the user should choose the boundary visually rather than interpret a preset as universally correct.

Undo after fixture acceptance returned to the preceding observation with zero accepted items. The actual dwt_02 page was checked: 285 leaflet drafts are ready, its separate 41-compound queue is pending, and the pending view explicitly asks for draft generation. The test-only port-8823 server was stopped; the real 8821/8822 editors remain running. The dwt_01 editor is left open for the user. Machine-readable browser evidence: `build/sensitivity_web_20260922/browser_verification.json`.
