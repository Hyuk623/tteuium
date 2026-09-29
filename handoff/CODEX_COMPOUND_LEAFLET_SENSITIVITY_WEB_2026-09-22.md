# Compound-leaf and leaflet sensitivity review in the existing local web editor

## Request and observed behavior

The user wants to inspect compound-leaf and leaflet masks while adjusting sensitivity personally. The existing batch UI supports only leaflet observations and saves threshold changes on slider release. It does not provide a live, unsaved comparison. Sensitivity 20 maps to logit > 2.4; 50 maps to logit > 0. The former can remove weak boundary regions. Claude's cached-logit review is a useful diagnostic, not ground truth or authorization for automatic fragment removal.

## Implementation scope

- Extend the existing tools/leaflet_mask_batch and tools/serve_leaf_edit_session web flow. Keep dwt_01/dwt_02, existing 577 leaflet drafts, saved review history and original annotations intact.
- Prepare separate compound-leaf batches from existing original-pixel boxes, resolving actual compound class aliases. Class switching occurs in the same editor. No parent assignment or physical identity is inferred from a mask.
- Supply cached full-resolution float32 logits to the authenticated browser for immediate local threshold/candidate previews. Display synchronized saved/reference and current-preview images, a clear threshold direction, 20/50 presets, pixel area and mask opacity. Model scores are not accuracy.
- Preview changes do not mutate saved items or run inference. The user explicitly saves a selected sensitivity/candidate, can restore saved settings, and accepts individually. Manual contour edits stay intact until an explicit change/save; no automatic hole filling, fragment deletion or hidden-leaf completion.
- Generate a selected compound observation on demand using the existing local SAM configuration. A small real smoke test is within the requested working-web scope; no training, remote inference, bulk human acceptance, geometry or PPFD. The UI also retains the existing explicit batch-generation controls.
- Preserve original coordinate conventions, source annotation/class provenance, original bboxes and separate class-specific output directories. Exports identify the organ class and remain accepted-only.

## Validation

Test aliases/class filtering, unchanged legacy leaflet batches, targeted generation, binary-logit/server mask equivalence, preview-without-writes, invalid threshold/candidate rejection, explicit save/undo, and same-origin authentication. Verify the actual local Korean UI, rapid slider/candidate updates, class/photo switching, reference comparison and persistence using isolated fixture copies. Record actual outcomes below.

## Outcome

Implementation in progress.

## Completed implementation — 2026-09-22

The implementation above is now complete in the existing editor. `tools/leaflet_mask_batch.py`, `tools/serve_leaf_edit_session.py`, `tools/leaflet_mask_batch.js`, new `tools/mask_preview_math.js` and `tools/tests/test_leaflet_mask_batch.py` provide separate leaflet/compound batches, per-item compound generation, authenticated full-resolution cached-score previews, synchronized comparison, explicit preview save/restore and existing review/undo actions.

All 577 existing leaflet results and both manifests are byte-identical to the pre-change snapshot (579 files); all 50 recorded source hashes pass. Existing human sensitivity 71 on dwt_01_a206 is retained. Compound preparation contains 49 dwt_01 and 41 dwt_02 observations; only the representative dwt_01_a37 was generated during this task, and it remains unreviewed. Remaining compound items are generated on user request.

Focused tests: 23 passed (batch/server); JavaScript syntax checks pass. Live-browser testing verified leaflet and compound threshold comparison, disabled acceptance for unsaved previews, saved settings after reload and undo. Save/acceptance tests used only isolated copies under `build/sensitivity_web_20260922/ui_fixture/`, with no model configured; cached previews therefore work without inference. Never use that fixture as research or training data.

Detailed commands, limitations, outstanding Claude review findings and the user-requested transfer of project leadership through **2026-09-26 18:00 Asia/Seoul** are in `CLAUDE_LEAD_HANDOFF_UNTIL_2026-09-26_1800_KST.md`.
