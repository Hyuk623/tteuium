# Leaflet mask review: operation and integration

## Scope and inputs

This is an extension of `tools.serve_leaf_edit_session`, not a separate annotation application. It uses the prepared dwt_01/dwt_02 sessions and Claude's verified original-pixel human COCO labels. Only `leaflet` observations are processed. There are 292 observations in 14 photos for dwt_01, and 285 in 16 photos for dwt_02. All 577 observations retain source IDs and provenance; none represents an automatically confirmed physical leaflet identity.

## Launch

Run from the project root, replacing `<plant>` with `dwt_01` (port 8821) or `dwt_02` (port 8822):

```powershell
python -m tools.serve_leaf_edit_session --session build/new_captures_20260920/<plant>/edit_session --context build/new_captures_20260920/<plant>/edit_session/annotations.source.json --runs build/leaflet_mask_batch_20260922/<plant>/editor_runs --initial-backup build/dwt_01_02_3d_20260922/<plant>/labels/seed_with_imports.backup.json --segmenter sam2 --segmenter-config build/photos1_manual3d_20260919/sam_auto_20260920/sam2_config.json --mask-batch build/leaflet_mask_batch_20260922/<plant> --port <port>
```

The mask panel loads an enlarged source photograph and its original bbox automatically. The legacy identity/landmark editor remains available through the Korean expand button. It is initially collapsed to keep this task focused and avoid decoding all full-resolution photographs unnecessarily. Existing browser labels are never overwritten by batch review.

## Review workflow

1. Choose an observation in the risk-ranked queue. The default queue includes deferred items and excludes accepted/rejected ones. Other filters expose every status.
2. Review the original photograph, yellow source box, green raster mask, candidate score and sensitivity. Scores are model outputs, not measured accuracy. Review priorities describe the initial draft; the current mask area is shown separately.
3. Select another candidate or compare sensitivity 20 with 50. Existing crop-resolution logits are rethresholded; this does not run the model again. No small-region removal, hole filling, component merging or centre prompt is applied.
4. Open correction tools. Add positive clicks on the target and negative clicks on other leaves/background, then regenerate only this observation. Points remain in original image pixel coordinates. Alternatively move, insert or delete contour vertices and save the contour edit. The raster delta preserves tiny regions omitted by editable polygon simplification. Edits are restricted to the stored crop; prompts can expand the next crop when needed.
5. Accept and advance, defer, or reject each observation individually. Empty masks cannot be accepted. A saved mask/candidate/threshold edit clears acceptance. Undo restores the previous persisted observation state. Unsaved clicks/contour edits must be saved before moving or accepting.
6. Export accepted masks only. Each export is a new folder with `accepted.json` and full-original-resolution binary PNG masks. Original boxes are separate from mask-derived bounds. The PNG is authoritative for holes and tiny components; simplified rings are a convenience for editing and display.

Within the open page, Undo follows the last saved action even after accepting and advancing to the next observation. After reloading the page, select the affected observation to undo its persisted state. Unsaved local clicks/contour edits are cancelled first. Keyboard events in the mask panel do not trigger the legacy editor's annotation shortcuts.

No action here confirms cross-view identity, parent membership, physical landmarks, depth or PPFD suitability. These remain subsequent, separate reviews.

## Persistence and restart

All generated files stay in `build/leaflet_mask_batch_20260922/<plant>/`:

- `manifest.json`: read-only batch input snapshot, coordinate transform and source hashes.
- `items/<observation>.json`: generation and review states, immutable source annotation/bbox, prompt, selected candidate, sensitivity, contour edits, revision, audit history and undo snapshots.
- `cache/<key>/logits.npz`: complete float32 crop-resolution candidate arrays. `result.json` records scores, crop origin, model/checkpoint/config, prompts, hashes, generation time and review signals.
- `summary.json`, `audit.json`, `processing.csv`: generation/review accounting and timing. Audits are explicit snapshots; run `audit` after completion for the final state.
- `exports/accepted_<timestamp>/`: accepted-only snapshots; previous exports stay intact.

The cache key includes image hash, bbox/prompts, model configuration and crop settings. A changed prompt affects one observation; a changed model requires new drafts and fresh review. A changed source image/label is reported instead of silently reusing its old coordinate mapping. Prepare a new batch after changing source annotations.

Start/resume skips unchanged completed observations. Stop takes effect after the current bbox. A persisted stop request also reaches a CLI worker. An OS file lease prevents another process from writing the same batch concurrently. JSON replacement is atomic and retries brief OneDrive file locks. Revision checks reject stale browser edits.

```powershell
python -m tools.leaflet_mask_batch status --batch build/leaflet_mask_batch_20260922/dwt_01
python -m tools.leaflet_mask_batch run --batch build/leaflet_mask_batch_20260922/dwt_01 --segmenter-config build/photos1_manual3d_20260919/sam_auto_20260920/sam2_config.json
python -m tools.leaflet_mask_batch audit --batch build/leaflet_mask_batch_20260922/dwt_01
```

Use `run --pilot` for the first middle and side photo per plant; `--retry-failed` explicitly retries generation failures. Mapping errors require correcting/validating inputs and preparing a new batch. Existing results are not overwritten by `prepare`.

## API contract

All batch routes require the existing local session token. Writes also require the matching loopback Origin. Existing `/api/segment` and `/api/segment_automatic` remain compatible.

- GET `/api/mask-batch/status`, `/queue`, `/item/<id>`, `/mask/<id>`.
- POST `/api/mask-batch/start`: `{ "pilot": false, "retry_failed": false }`.
- POST `/api/mask-batch/stop`: `{}`.
- POST `/api/mask-batch/review`: `{ "id": "...", "revision": 2, "action": "accept" }`.
- Review actions: `accept`, `defer`, `reject`, `undo`, `select` (`candidate`, `sensitivity`), `refine` (`positive_px`, `negative_px`), `contour` (`rings`). Optional `active_seconds` records foreground review time, capped at 30 minutes per action.
- POST `/api/mask-batch/export`: `{}`; returns the new local output path and accepted count.

Review/edit time and unchanged-acceptance ratio require actual human actions. With zero accepted masks the ratio is unavailable, not 0%. Generation time is the sum of item processing wall times, including loading/compression and recorded failures; concurrent execution means that sum is not end-to-end elapsed time.

## Test data

`ui_test_fixture/` contains two isolated copies used for browser acceptance/hold/export tests. Those test acceptances are not part of dwt_01/dwt_02 research results. Do not merge its masks or review metrics into the actual batches.

## Superseding web interaction update — 2026-09-22

The current web interface supports both leaflet and compound-leaf batches. Sensitivity/candidate changes are now **unsaved browser previews**, not autosaved on slider release. Click `미리보기 저장` to persist; click `저장값 복원` to discard the preview. Acceptance is disabled until the displayed preview agrees with saved data. Unreviewed items initially preview sensitivity 50; edited/accepted/manual items retain their saved setting. This does not bulk-convert existing masks or remove fragments/holes.

Compound masks are prepared in `build/sensitivity_web_20260922/<plant>/compound/`; attach them with `--compound-mask-batch`. Choose class, photo and observation; if pending, click `선택한 잎 초안 생성`. Both classes reuse the existing SAM configuration. Cached threshold/candidate previews require no model execution. GET batch routes accept the `organ_class` query; POST bodies carry `organ_class`; the default remains `leaflet`.

Use `CLAUDE_LEAD_HANDOFF_UNTIL_2026-09-26_1800_KST.md` for current restart commands, verified state, testing and leadership transfer. The additional `build/sensitivity_web_20260922/ui_fixture/` is also test-only and must be excluded from all research/training exports.
