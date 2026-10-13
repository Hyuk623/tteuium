# CONVENTIONS — binding rules for every agent working in this repository

Two agents work in this folder: **Claude Code** and **Codex**. A human owns the design decisions.
This file is binding for both. Read it before your first edit in a session.

Last updated: 2026-10-11

---

## 1. Ownership map — never edit outside your own column

| Path | Owner | Others may |
|---|---|---|
| `tomato3d/` | Claude Code | read, import |
| `tests/` | Claude Code | read |
| `tools/` | Codex **and Claude Code** (2026-10-11) | read, import |
| `tools/tests/` | Codex **and Claude Code** (2026-10-11) | read |
| `phynotype2/` | Codex **and Claude Code** (2026-10-11) | read, import |
| `config/` | **the human** | read only |
| `docs/` | **the human / design agent** | read only |
| `handoff/` | shared, append-only per §5 | read, append |
| `build/` | generated output, either agent | overwrite own outputs |
| `data/` | see §4 | see §4 |

**User override, 2026-10-04 — light calculation core:** the Claude-only restriction is revoked
for `tomato3d/light/` and relevant light tests under `tests/`. Both Codex and Claude Code may
implement and validate this scope, coordinating edits so only one works on a file at a time.
Codex may complete the actual-path callback and tools integration without waiting for a separate
core-owner delivery or ownership approval. This exception takes precedence over older protected-core
instructions in handoffs. Other ownership rules remain unchanged. Decision record:
`handoff/CODEX_LIGHT_CORE_RULE_UPDATE_2026-10-04.md`.

**User override, 2026-10-11 — Claude Code may fix Codex-column code directly:** the Codex-only
write restriction is revoked for `tools/`, `tools/tests/` and `phynotype2/`. Claude Code may edit,
fix and test that code itself instead of filing a request and waiting for Codex. Codex keeps full
write access to the same paths — this adds an owner, it does not remove one. The reason is
throughput: defects found by Claude Code in those paths were being handed over as requests
(`handoff/CROSS_STAGE_ISSUES_2026-10-11_KO.md` item A11 and change requests CR-1, CR-3, CR-4), which
left real errors unfixed in the queue.

The unchanged parts, stated so nothing is read into this override: `config/`, `data/records/` and
`docs/` remain the human's and stay read-only for both agents — this override says nothing about
them. `handoff/` stays append-only (§5). The no-concurrent-edit rule below becomes **more**
important, not less: two owners now share three directories on a OneDrive folder.

**Coordination rule for a shared-owner path.** Before editing a file under `tools/`, `tools/tests/`
or `phynotype2/`, append one line to `handoff/LOG.md` naming the files you are about to touch, and
check that the other agent has not just claimed them. After finishing, record what changed. If both
agents have edited the same file in one day, say so explicitly in the log rather than assuming the
later write won. Decision record: `handoff/OWNERSHIP_OVERRIDE_2026-10-11.md`.

Outside the explicit exceptions above, if a task needs a change outside your column, **stop and write it in `handoff/LOG.md`**
instead of making the change. Do not "just fix" someone else's file. A silent cross-column edit is
the single most expensive failure mode in this repo, because the other agent will not know its
assumptions changed.

`config/` is the human's. Neither agent changes a value there on its own initiative — not to make a
test pass, not to match a file it just generated. Propose it in `handoff/LOG.md` and wait.

---

## 2. Board specification — one source of truth

`config/board_spec.json` is **the** board the pipeline assumes. Nothing else is.

`build/*_spec.json` files are **printed-pattern metadata only**. They describe what a particular PDF
contains. They are not a pipeline configuration, they omit rig fields (pot, scale block, colour
chart, origin convention), and they must never be copied over `config/board_spec.json`.

Several board variants exist as print artifacts. **Marker IDs overlap between variants**, so the
board model can never be inferred from detected IDs. Every capture session records which board it
used, in its `session_manifest.json`. A session captured on one board and processed with another
board's spec produces confident, wrong numbers — and nothing in the pipeline will flag it.

---

## 3. Hard constraints — violating any of these breaks the design

1. **No SfM.** No COLMAP, no OpenSfM, no feature-matching pose estimation. The camera and the
   background are both static while the board rotates; SfM concludes the camera never moved. Camera
   pose comes only from ChArUco PnP, solved independently per frame.
2. **No `cv2.findChessboardCorners`.** The board is ChArUco. Use `cv2.aruco.CharucoDetector` so pose
   still solves when the plant occludes most of the board.
3. **Never reject the board by colour.** The substrate is vermiculite — bright and uniform, like
   parts of the board. Reject the board geometrically: points on the board plane within its measured
   extent.
4. **`board_variant_id` is mandatory in every session manifest** and must match
   `config/board_spec.json::variant_id`. See §6b.
5. **Never use `nominal_angle_deg` for geometry.** It is the commanded turntable angle. The measured
   pose in `poses.csv` is authoritative.
6. **A value that cannot be measured is `unavailable`** — never `0`, never an imputed number, never
   a silently dropped row.
7. **A null threshold in a config is loaded but inactive.** Never substitute a default for a value
   the pilot has not yet determined.
8. Tabular data is CSV. Configuration, knowledge and metadata are JSON. No other formats.

---

## 4. Data directories

```
data/raw/<plant_id>/<session_id>/      capture input + session_manifest.json
data/calib/                            intrinsics_shots/, intrinsics_<camera_id>.json
data/records/<plant_id>/               HUMAN-WRITTEN GROUND TRUTH - read only for both agents
data/derived/<plant_id>/<session_id>/  pipeline output
data/tracks/<plant_id>/                pipeline output
data/outputs/<plant_id>/<session_id>/  pipeline output
data/knowledge/                        crop pack JSON
```

`data/records/` holds `manual_events.csv`, `manual_measurements.csv`, `environment.csv` and
`organ_label_map.csv`. People write these by hand; they are the evaluation ground truth. **No agent
writes to them, and no agent "repairs" a malformed row.** A validator reports problems and exits.

Resolve `data/` from `TOMATO3D_DATA_ROOT` and `config/` from `TOMATO3D_CONFIG_DIR`, both via
`tomato3d.config.get_settings()`. Never hardcode `./data`, never concatenate paths at call sites.

---

## 5. Handoff protocol

- `handoff/LOG.md` — append one dated entry per work session: what changed, what you could not do,
  and every assumption you had to make. Append; do not rewrite history.
- `handoff/TODO.md` — open items. Move an item to done rather than deleting it.
- Specification documents in `handoff/` are written for an agent to execute. If one turns out to be
  wrong, underspecified or self-contradicting, **report it — do not fix it by guessing.** A guess
  that happens to work is worse than a stop, because it silently becomes the spec.

### Language

- `docs/` — Korean. Design reviews and protocols the human reads.
- `handoff/`, code, comments, commit messages, config — **English**.

---

## 6. Code conventions

- Python 3.11+, type hints everywhere, `pathlib.Path` for every path.
- `opencv-contrib-python` (not `opencv-python`) — `cv2.aruco` lives in contrib.
- **Every length variable carries its unit in the name**: `square_size_mm`, `height_mm`,
  `radius_mm`. Angles are `_deg` or `_rad`. No bare `size`, `height`, `angle`.
- Angles are degrees in files, radians in code.
- No magic numbers in function bodies. Every constant comes from a config JSON.
- Logging via `tomato3d.logging_setup.configure_logging`, never `print`, except a CLI summary.
### Coordinate frames — there are two, and they are not the same

- **Sheet frame** — OpenCV's ChArUco object-point frame. Origin at the printed sheet's
  `origin_corner`, `+X` right along a row, `+Y` down along a column, **`+Z` into the board**.
  The `*_position_mm` values in `board_spec.json` are expressed here.
- **Board frame** — the pipeline frame, and the frame of every number in `poses.csv`. Origin at the
  board's **origin inner corner** (ChArUco corner id 0), `+X`/`+Y` along rows/columns,
  **`+Z` up, away from the board surface**.

The two differ by a 180° rotation about `+X` plus a one-square translation in `X` and `Y`.
`tomato3d/calib/board.py::sheet_to_board_mm` is the **only** implementation of that map. Do not
write a second conversion anywhere, and state which frame you mean whenever you write a coordinate.

All lengths in millimetres; angles are degrees in files, radians in code with a `_rad` suffix.

The board frame is identical in every session because the board rotates with the plant — cross-date
comparison needs no registration step, and none should be added.

> **Resolved 2026-09-15.** The ambiguity Claude Code flagged in `scale_block_position_mm` is closed:
> **every `*_position_mm` and `*_center_mm` value in `config/board_spec.json` is in the SHEET frame**,
> and the file now carries `"position_frame": "sheet"` to say so. Nothing in the code changes —
> keeping the two frames distinct was the right call. State the frame whenever you add a new
> coordinate field.

---

## 6b. The operational board

`charuco_7x7_190mm` — 7x7 squares, 190/7 mm each, 19.905 mm markers, 190x190 mm, A4,
36 inner corners, 24 markers, `DICT_4X4_50`, `legacy_pattern: false`.
Print: `build/charuco_board_7x7_190mm_A4.pdf`.

`build/charuco_board_5x5_190mm_A4.pdf` is a **built spare, not the operational board.**

**Marker IDs overlap between the two variants.** A session's board can never be inferred from
detected IDs — only from `board_variant_id` in its `session_manifest.json`. Get that field wrong and
detection looks perfectly healthy while every measured dimension is wrong. Nothing downstream will
catch it.

`physical_print_verified` is `false` until a printed sheet has actually been measured. Do not flip it
from a digital check.

---

## 7. Repository hygiene

`.gitignore` must contain at least:

```
__pycache__/
*.pyc
.pytest_cache/
build/
data/
.env
```

This folder lives in OneDrive. Cache directories that sync are noise for the human and a source of
spurious conflicts — do not commit them, and do not create scratch files outside `build/`.
