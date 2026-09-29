# AI-assisted leaflet labeling in the existing editor — Claude Code, 2026-09-20

Request: `자동라벨링.txt` (project root). Builds on `LEAFLET_BBOX_XYZ_IMPLEMENTATION_2026-09-19.md`.
Same ownership note: `tools/` is Codex's column; the user directed this work. No `config/`, `docs/`,
`tomato3d/`, `tests/` edits.

## Status: three separate claims

| | State |
|---|---|
| Integration, model interface, state machine, export | **Implemented and tested** |
| Proposal -> correction -> acceptance -> rebuild -> export | **Tested with mocked model output only** (Node fixtures, Python `MockSegmenter`/fixed masks, browser walkthrough with `--segmenter mock`) |
| Real SAM 2 inference inside the editor | **Not run, not tested.** No weights downloaded, no inference, no training, no upload in this task |
| Cross-view appearance matching | **Not implemented.** Suggestions use measured (diagnostic, unvalidated) camera geometry only; manual linking remains |

SAM is a prompted segmentation model, not a trained tomato organ detector. All outputs are unreviewed proposals.

## What was added

- `tools/leaflet_segmenter.py`: backend interface. `unavailable` (default; manual labeling unaffected),
  `sam2` (lazy load from JSON config, checkpoint sha256 verified before loading, nothing downloaded),
  `mock` (deterministic ellipse; provenance `is_mock=true`, UI says "모의 도형(모델 아님)").
  Prompt crop in original pixels, mask -> rings (RETR_CCOMP; holes kept; approxPolyDP 1.0 px); only
  components hit by an include click (or dominant in the prompt box) are kept, exclude clicks drop
  components; discarded component count reported.
- `tools/serve_leaf_edit_session.py`: `GET /api/segmenter`, `POST /api/segment` (token + same Origin,
  session photos only, hash-checked, serialized, writes nothing), `--segmenter`, `--segmenter-config`.
- `tools/leaf_point_annotator.html` (in `소엽 · bbox` panel):
  - prompt box (not a label), include/exclude clicks, request, candidate choice, vertex edit
    (drag / Alt delete / Shift insert), accept, reject; undo via existing history.
  - Drafts in `variants.<v>.proposals[id]` with states `proposed | edited | accepted | rejected`,
    model info, prompts, crop, all candidates (original model rings kept), history, `previous_proposal_id`
    (a new request supersedes the open draft -> `rejected`/`superseded`).
  - Accept writes only the existing leaflet record: `bboxes[photo]` (+`region_source`, `proposal_id`) and
    new `regions[photo]` = `{rings, fill_rule:'evenodd', model, prompts, user_edited, ...}`. Refused if that
    leaflet already has a box/region in that photo (no overwrite). Visibility/identity stay as recorded
    (`unknown/unconfirmed` by default). No point is created. `contours` is NOT used (it feeds the
    rebuild's unchanged-label check). Deleting the box deletes its region; link/split moves the region.
  - Stale responses (other session/photo/resolution) are discarded.
  - Cross-view candidates: project the leaflet's triangulated points (else epipolar curves) into the
    other pane's photo; rank other leaflets' boxes/points there by distance. Decisions `same`
    (moves that photo observation in via `moveLeafView`, review stays `unconfirmed`), `different`
    (excluded afterwards), `uncertain`; logged in `variants.<v>.identity_decisions`.
  - Remote-sync body now includes `proposals` and `identity_decisions`.
- `tools/rebuild_leaf_edit_session.py`: bbox rows carry `region_source`, `proposal_id`,
  `has_accepted_region`, `region_model`; report `ai_proposals_by_state`. Regions never enter point rows.
- `tools/export_leaflet_training.py` (new): saved leaflet boxes + accepted regions only; copied original
  photos (hash-verified); even-odd masks at original resolution; `leaflet_instances.csv`,
  `export_manifest.json` (excluded draft counts, provenance), `splits.json` (group by plant; one plant ->
  `insufficient_plants_for_held_out_split`; multi-plant requires explicit `--eval-plants`).

## Checks executed

- `python -m pytest tools/tests -q`: 150 passed, 1 skipped (+8 vs previous 142: `leaf_annotator_ai.test.cjs`
  11 Node tests, `test_leaflet_ai_workflow.py` 7). `python -m pytest tests -q`: 183 passed.
- Mutation checks detected: removed no-overwrite guard, removed stale-session guard, accept setting
  full/confirmed, `different` not excluding.
- Browser (port 8836, storage cleared after) on `edit_session07` with `--segmenter mock`: prompt box stored
  in original px without creating a label; mock proposal via server; undo of an accept; edit + accept via the
  real button handler (`ai_proposal_edited_accepted`, model vertex kept separately); rebuild: 48 observations,
  point XYZ identical to `edited_roundtrip08`; training export produced 1 instance/1 mask/1 photo.
  Artifacts: `build/photos1_manual3d_20260919/editor_runs_ai_mockcheck08/` (`EXAMPLE_PROVENANCE.json`: mock,
  not labels). A window resize during the session made one coordinate-based drag miss; the browser tool
  re-ran a timed-out script, which produced the extra unedited run `run_..._000003`.
- 246 protected inputs and `edit_session07` photos/seed hash-identical.

## Later authorized SAM 2 trial (not executed)

Existing local assets from the earlier authorized trial: `build/sam_trial_20260919/checkpoints/sam2.1_hiera_tiny.pt`
(recorded sha256 `7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`), `vendor/sam2`, `runtime`.
Dependencies: torch (CPU ok), the SAM 2 repository, opencv-contrib-python, numpy, Pillow, scipy.

```
python -m tools.leaflet_segmenter --write-sam2-config build/photos1_manual3d_20260919/sam2_editor.json
# set checkpoint_sha256 to the value above; relative paths resolve from the project root
python -m tools.serve_leaf_edit_session --session build/photos1_manual3d_20260919/edit_session07 --context build/photos1_manual3d_20260919/manual_candidates.review09.json --runs build/photos1_manual3d_20260919/editor_runs --initial-backup build/photos1_manual3d_20260919/third_view_review10/third_view_revised.backup.json --segmenter sam2 --segmenter-config build/photos1_manual3d_20260919/sam2_editor.json
python -m tools.export_leaflet_training --session build/photos1_manual3d_20260919/edit_session07 --backup <run>/editor.backup.json --out build/photos1_manual3d_20260919/training_export01
```
Relative config paths resolve from the project root. Untested risks: real mask quality on leaflets, image
embedding not cached (each request re-encodes the crop), CPU latency, `sam2` import path details.

## Limitations / open decisions

1. No appearance-based cross-view matching; geometry uses poses that fail the 1 px gate (flagged `diagnostic_geometry`).
2. Accept is one click (undo available). A confirmation step could be added if preferred.
3. Masks are stored as outline rings (tolerance 1 px), not raw model masks; raw masks/logits are not saved.
4. The training export is per session; combining plants and choosing eval plants is a later, explicit step.
5. One labeled plant does not establish generalization.
