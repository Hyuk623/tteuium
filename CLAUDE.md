# CLAUDE.md — Claude Code working agreement

**Read `CONVENTIONS.md` first. It is binding and covers both agents.** This file only adds what is
specific to you.

## Your scope

You own `tomato3d/` and `tests/`. You implement the pipeline.

**You do not own `tools/`, `tools/tests/`, `config/` or `docs/`.** `tools/` belongs to Codex — it
holds the board print generator, session organiser, record validators, mask contact sheet and pilot
sweep runner. Do not create, edit or delete anything there, and do not reimplement a tool that
belongs there because it is missing; note it in `handoff/LOG.md` and carry on.

## Synthetic board renderer — you own it

`tests/conftest.py::render_charuco_view` is the project's synthetic ChArUco renderer. You wrote it,
its tests pass, and it stays where it is. Codex's task T2 (a second renderer under `tools/`) has
been **cancelled** so there is only one implementation. Do not move it, do not duplicate it, and if
a Codex tool ever needs it, say so in `handoff/LOG.md` rather than copying it across columns.

## Specifications you work from

- `handoff/TOMATO_3D_PHENOTYPING_ALGORITHM_SKELETON_2026-09-15.md` — module boundaries, function
  signatures, file names, schemas. Authoritative for structure.
- `handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md` — the Stage 1 brief.
- `docs/파일럿_촬영_프로토콜_2026-09-15.md` — the confirmed capture spec.

Where a spec and `config/board_spec.json` disagree, **neither one wins by default** — stop and
report the conflict in `handoff/LOG.md`. Do not edit the config to resolve it.

## Build order

Stage 1 `io`, `calib`, `mask` → 2 `recon` → 3 `organ`, `fuse3d` → 4 `graph`, `pheno` →
5 `track`, `rules` → 6 `twoview`. Later-stage packages exist as stubs that raise
`NotImplementedError`; leave them that way until their stage is opened.

## Before you finish a session

Append to `handoff/LOG.md`: what you changed, what you could not do, every assumption you made, and
every place the specification was unclear.
