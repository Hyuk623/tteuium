# AGENTS.md — Codex working agreement

## User preference — documentation first (2026-09-20)

For implementation, Claude-review/integration, and automatic-labeling work, first create or update an English Markdown brief in `handoff/` describing the request, inspected current behavior, intended changes, execution restrictions and validation. Then proceed within the user's authorized scope; this does not introduce another approval step. Record actual outcomes afterward. Preparing a prompt alone does not authorize training or inference.

**Read `CONVENTIONS.md` first. It is binding and covers both agents.** This file only adds what is
specific to you.

## Your scope

You own `tools/` and `tools/tests/`. You build support tooling.

**You do not own `tomato3d/`, `tests/`, `config/` or `docs/`.** `tomato3d/` and `tests/` belong to
Claude Code. Do not create, edit or delete anything there. If a task appears to need a change in the
pipeline, stop and write it in `handoff/LOG.md`.

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
