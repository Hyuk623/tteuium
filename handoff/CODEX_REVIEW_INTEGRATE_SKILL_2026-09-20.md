# Claude revision review, integration fix, and reusable skill

## Reviewed revision

Read `LEAFLET_SURFACE_REVIEW_INTEGRATION_2026-09-20.md` and inspected the surface attachment, freshness comparison, renderer filtering, export boundary tests, and editor server caller. Claude's changes are already in the shared workspace; no branch merge or historical file replacement was needed.

Finding: the CLI accepted `--patches`, but `EditService._run()` did not pass a patch directory to rebuild. Consequently the editor button could not retain the newly connected partial-surface review.

## Integration completed

- `tools/serve_leaf_edit_session.py`: optional `--patches` / `EditService(..., patches=...)`, passed through on each saved-backup rebuild; job status exposes attachment status/count. This reads existing outputs only and does not execute segmentation.
- `tools/leaf_rebuild_client.js`: reports current attached surfaces or the stale-surface hidden state.
- `tools/tests/test_serve_leaf_edit_session.py`: real HTTP submit/poll/result regression checks current attachment, changed correspondence -> stale surface hidden, and unchanged input backup.

## Verification executed now

- `python -m pytest -q tools/tests/test_serve_leaf_edit_session.py tools/tests/test_leaflet_surface_attachment.py`: **11 passed in 43.52 s**.
- Node syntax check passed for `tools/leaf_rebuild_client.js`.
- Server CLI help exposes the new option.
- Rebuilt the saved real user snapshot into `build/photos1_manual3d_20260919/codex_surface_integration_check_20260920/` with the existing `sam_auto_20260920/three_d` patch run: 89 observations, 6 current attached patches, 0 cuboids, 18 labeled-photo outputs, `input_files_changed=false`, no DL run. Depth CSV is byte-identical to the source run.
- Original snapshot SHA256 remains `96f1dc556145c3a6e65ed64fd83fd4ff778081cd63df1cf226cc1c0bd15c45e6`.
- Visually inspected `labels/photo_0003.jpg`: point labels and projected surfaces are present; one surface lands on the board, confirming the existing diagnostic geometry issue rather than demonstrating physical accuracy. No labels or geometry were silently repaired.
- This was a focused integration review, not a fresh exhaustive audit of every historical feature. Calibration and PPFD validity remain false; full plant geometry and automatic matching remain incomplete.

## Runtime activation

The existing server on port 8821 was not restarted and its browser was not reloaded. It still uses its previous startup settings. To enable saved-surface attachment, restart that server with its existing command plus:

```text
--patches build/photos1_manual3d_20260919/sam_auto_20260920/three_d
```

Keep port 8821 to retain the browser storage origin. Preserve/export current user edits before reloading. Keep `--segmenter unavailable`; attachment is not permission for inference. Changed point depths correctly hide the older surfaces; regeneration requiring inference remains separately authorized work.

## Reusable Codex skill

Created `.agents/skills/claude-review-integrate/SKILL.md` and `agents/openai.yaml`. Skill instructions are English; user-facing reports remain Korean. The official project-local skills location is used, keeping every write inside the project.

Invoke from a Codex task rooted in this project:

```text
$claude-review-integrate Check Claude Code's latest revision, integrate it with the current workflow, verify it, and record the handoff.
```

For a task rooted in the parent Homefarm folder, explicitly provide the skill's full SKILL.md path or open a task in this project. Do not assume discovery scans child projects. If the current task's skill catalog has not refreshed, an explicit file reference remains usable. No global skill was installed and fresh-session automatic discovery was not tested.

The skill covers handoff/code inspection, preservation, actual caller-to-consumer integration, tests, real snapshot verification, and English logging. It does not start a scheduled watcher, contact Claude, or grant training/inference permissions.

Validation: bundled `quick_validate.py` passed using Python313. The bundled dependency Python lacked PyYAML; no dependency installation was performed. Metadata and workflow were manually checked against this actual integration case.

Official location/invocation reference: https://learn.chatgpt.com/docs/build-skills
