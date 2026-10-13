# Claude feature review and integration — 2026-09-20

## Scope and findings

Reviewed `AI_ASSISTED_LEAFLET_LABELING_2026-09-20.md` and current editor, segmenter,
rebuild, export and server code. Claude's proposal state machine, separate accepted
regions, geometry-based identity suggestions and training export already use the
existing application. No replacement app was created.

Two remaining integration gaps were fixed:

1. Codex's click-to-delete toolbar now handles AI draft outline vertices while in
   draft-edit mode. It cannot delete an accepted bbox underneath that draft.
   Minimum three vertices and undo remain enforced. Point/bbox deletion still
   uses the existing photo-local operations.
2. Rebuilt labeled-photo galleries now show saved accepted 2D region outlines in
   cyan, including hole boundaries, with per-photo counts. These are explicitly
   separate from correspondence points and 3D surfaces. `accepted_regions.json`
   preserves their identities, source image hashes and proposal provenance.
   Drafts are not drawn or triangulated. Existing point calculations are unchanged.

Files changed: `tools/leaf_point_annotator.html`, `tools/editor_point_review.py`,
`tools/rebuild_leaf_edit_session.py`, and related tests under `tools/tests/`.

## Verification

- Full support suite after integration: 150 passed, 1 skipped.
- Added a further direct rendered-pixel regression for cyan outer/hole outlines
  and unchanged hole interiors: `test_editor_point_review.py`, 5 passed.
- Node regression covers draft vertex deletion, protection of existing boxes,
  rejection of deletion below three vertices, missed clicks and undo.
- Mock AI integration test verifies exactly one accepted region reaches the
  gallery/JSON and existing point-depth values remain unchanged.
- Real historical backup rebuild: `build/photos1_manual3d_20260919/integrated_review_20260920/`.
  Its 48 depth CSV rows are identical to `edited_roundtrip08`; three partial
  surfaces remain, protected inputs unchanged, metric/PPFD validation false.
- Restarted the known localhost editor process on the same port 8821 with the
  current server code, explicitly `--segmenter unavailable`. No model was run.
- Browser load verified 18 photos and the user's persisted work were preserved,
  rather than replaced with the assistant seed. The deletion control and model
  unavailable state are visible together.
- Clicked the existing rebuild button on the preserved browser work. Run:
  `build/photos1_manual3d_20260919/editor_runs/run_20260920_001200_c0ff5c90/`.
  It completed with 89 point observations, six diagnostic partial surfaces,
  five leaflet boxes, zero cuboids; `input_files_changed=false` and
  `deep_learning_run=false`. The result page was inspected in the browser.

## Current interpretation and limitations

The historical assistant backup and the live browser work are DIFFERENT inputs.
Do not overwrite the user's current work to force the historical 23-point result.
The live backup is preserved in the new run. Its six surfaces are unvalidated,
not six verified complete leaves or an improvement in reconstruction accuracy.

All five live boxes have unknown visibility and unconfirmed identity review;
one is also on IMG_7910 without a solved pose. Therefore none constrain a cuboid.
Do not automatically mark them full/confirmed to produce a box.

Real SAM inference and appearance-based cross-view matching remain untested/not
implemented respectively, as documented by Claude. Automatic physical-point
matching and bbox/ID-only full surface reconstruction are not claimed. Existing
calibration gates remain unchanged. No DL training/inference, uploads, core,
config or design-document edits occurred.

## Use

Open `http://127.0.0.1:8821/`. Load the prepared photos to restore the browser's
existing labels. The same editor provides manual points/bboxes, delete/undo,
AI proposal controls (disabled without a configured model), and explicit rebuild.
The new result is linked from the completed rebuild message.
