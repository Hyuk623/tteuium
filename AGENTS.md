# AGENTS.md — Codex working agreement

## User preference — documentation first (2026-09-20)

For implementation, Claude-review/integration, and automatic-labeling work, first create or update an English Markdown brief in `handoff/` describing the request, inspected current behavior, intended changes, execution restrictions and validation. Then proceed within the user's authorized scope; this does not introduce another approval step. Record actual outcomes afterward. Preparing a prompt alone does not authorize training or inference.

**Read `CONVENTIONS.md` first. It is binding and covers both agents.** This file only adds what is
specific to you.

## Your scope

You own `tools/` and `tools/tests/`. You build support tooling.

**User override, 2026-10-11 — `tools/`, `tools/tests/` and `phynotype2/` are now SHARED with Claude
Code.** Your write access is unchanged and nothing is taken away from you, but you are no longer the
only writer: Claude Code may fix and test code in those three paths directly instead of filing a
request. Do not assume a file there is untouched since your last session, and do not revert a change
you did not make — read `handoff/LOG.md` first and ask there if it looks wrong.

**Before editing a file under those three paths**, append one line to `handoff/LOG.md` naming the
files you are about to touch, and check Claude Code has not just claimed them. Record what changed
when you finish. This folder is on OneDrive: a simultaneous edit produces a conflict copy, and
`handoff/LOG.md` itself was overwritten twice on 2026-09-16, losing entries — append, never rewrite.
See `handoff/OWNERSHIP_OVERRIDE_2026-10-11.md`.

**User override, 2026-10-04:** the Claude-only ownership restriction for the light calculation
core is revoked. Codex may directly implement, edit and validate `tomato3d/light/` and the relevant
light tests under `tests/`, including the actual-path diagnostic callback and its integration.
Do not wait for a separate Claude core-owner delivery or ownership approval for this scope.
See `handoff/CODEX_LIGHT_CORE_RULE_UPDATE_2026-10-04.md`.

Outside that exception, `tomato3d/` and `tests/` remain Claude Code's scope; `config/` and `docs/`
remain outside Codex's write scope. Report unrelated cross-scope changes in `handoff/LOG.md`.
Coordinate active edits; the shared OneDrive no-concurrent-edit rule still applies.

`config/` is the human's. Read it; never write it. In particular, generating a board PDF does **not**
authorise updating `config/board_spec.json` to match — a generated `build/*_spec.json` is printed
pattern metadata, not a pipeline configuration. See `CONVENTIONS.md` §2.

## Your task list

`handoff/CODEX_TASKS_2026-09-15.md`. Priority order is stated there; T1 blocks all capture.

## Cancelled work — do not start T2

Task **T2 (synthetic ChArUco renderer) is cancelled.** Claude Code already implemented
`tests/conftest.py::render_charuco_view` and its tests pass. A second renderer under `tools/` would
be duplicate work and a second source of truth. Do not create `tools/charuco_render.py`.

## Standards for every tool

- A standalone CLI runnable as `python -m tools.<name>` with `--help`.
- Reads values from `config/*.json` — never hardcodes one that exists there.
- Writes generated artifacts only to `build/`.
- Ships a test under `tools/tests/`.
- Reports rather than repairs: a validator never modifies the file it validates.

## Before you finish a task

Append to `handoff/LOG.md`: files added, how to run them, and anything in the brief that turned out
to be wrong or underspecified. **Do not fix a specification problem by guessing.**
