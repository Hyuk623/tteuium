# CLAUDE.md — Claude Code working agreement

**Read `CONVENTIONS.md` first. It is binding and covers both agents.** This file only adds what is
specific to you.

## Your scope

You own `tomato3d/` and `tests/`. You implement the pipeline.

**User override, 2026-10-04:** `tomato3d/light/` and the relevant light tests under `tests/`
are also writable by Codex. The former Claude-only light-core restriction is revoked; Codex
does not need a separate core-owner delivery or ownership approval to implement the callback.
Coordinate before editing the same files. See `handoff/CODEX_LIGHT_CORE_RULE_UPDATE_2026-10-04.md`.

**User override, 2026-10-11 — you may now fix Codex-column code yourself.** `tools/`,
`tools/tests/` and `phynotype2/` are writable by you as well as by Codex. When you find a defect
there, **fix it and test it** instead of filing a request and waiting. This adds an owner rather than
removing one: Codex keeps the same access, so the coordination rule below is now binding on you.
See `handoff/OWNERSHIP_OVERRIDE_2026-10-11.md`.

Before editing a file under those three paths, append one line to `handoff/LOG.md` naming the files
you are about to touch, and check the other agent has not just claimed them. Record what changed when
you finish. This folder is on OneDrive and two owners now share three directories — a silent
simultaneous edit produces a conflict copy, and `handoff/LOG.md` has already been overwritten twice
that way (2026-09-16), losing entries.

**You still do not own `config/`, `data/records/` or `docs/`.** They are the human's and stay
read-only for you. The override above says nothing about them: a config value you need changed still
goes to `handoff/LOG.md` as a proposal, including when a test would pass if you changed it.

What `tools/` holds, so you know what you are touching: the board print generator, session organiser,
record validators, mask contact sheet, pilot sweep runner, and the growth and light calculators.
Before adding a new tool, check whether one already exists — a second source of truth is worse than a
missing feature.

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
