# Ownership override, 2026-10-11 — Claude Code may fix Codex-column code directly

Date: 2026-10-11
Decided by: the user, in session
Recorded by: Claude Code
Changes: `CONVENTIONS.md` §1, `CLAUDE.md`, `AGENTS.md`

## The decision

`tools/`, `tools/tests/` and `phynotype2/` become **shared-owner** paths: Claude Code may edit, fix
and test code there, instead of filing a request in `handoff/LOG.md` and waiting for Codex.

This **adds an owner; it removes none.** Codex keeps exactly the write access it had.

## What is explicitly NOT changed

| Path | Still |
|---|---|
| `config/` | the human's, read-only for both agents |
| `data/records/` | the human's, read-only for both agents (written by people, never by the pipeline) |
| `docs/` | the human's / design agent's, read-only for both agents |
| `handoff/` | shared, **append-only** |
| `tomato3d/`, `tests/` | Claude Code's, with the 2026-10-04 light-core exception for Codex |

A config value that a fix appears to need is still a proposal in `handoff/LOG.md`, including when a
test would pass if it were changed. The 2026-10-04 light-core override stands unchanged.

## Why

Defects that Claude Code found in Codex-column code were being handed over as requests and left
unfixed in the queue. From `handoff/CROSS_STAGE_ISSUES_2026-10-11_KO.md`:

- **A11** `tools/plant_traits.py:120` — the legacy S8 path drops a posed top photo with zero leaflet
  masks and publishes the mean of the remaining photos as `top_leaf_area_cm2`, which the light
  summary then multiplies by DLI. The v2 path refuses the same case; the live config takes the legacy
  path.
- **CR-1** the 30-day horizon and `provided_axes` scope are enforced by one `if` in
  `tools/probabilistic_compound_growth.py:796-797`, so a horizon-length list needs a code change.
- **CR-3** the growth engine tags its forecast state `surface_role = 'compound_envelope'`, a form the
  light path forbids.
- **CR-4** `train_plant_ids` is read only for a disjointness check and never constrains fitting, so
  the frozen split does nothing; and `forecast()` leaves its input-snapshot field blank.

## The cost, and the rule that pays for it

Two owners now share three directories inside a OneDrive-synced folder. The failure mode is real and
has already happened in this repository: `handoff/LOG.md` was rewritten twice on 2026-09-16 (18:48 and
18:55) from a copy that predated entries appended in between, and two Claude Code entries were lost.

**Coordination rule, binding on both agents.** Before editing a file under `tools/`, `tools/tests/`
or `phynotype2/`:

1. Append one line to `handoff/LOG.md` naming the files you are about to touch.
2. Check that the other agent has not just claimed them.
3. After finishing, record what changed.
4. If both agents edited the same file in one day, say so explicitly rather than assuming the later
   write won.
5. Never revert a change you did not make. Ask in `handoff/LOG.md` first.

## Scope of this record

Permissions only. No code was changed and no fix was applied under this override at the time of
writing.
