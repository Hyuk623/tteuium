# Stage 1 — Capture and calibration: implementation result and conformance report

Date: 2026-10-11
Author: Claude Code
Status: **Implemented and running. Conformance measured, not asserted.**
Implements: `handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md`
Korean companion: `handoff/STAGE1_IMPLEMENTATION_RESULT_2026-10-11_KO.md`
Downstream: `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` (Stage 2) →
`handoff/CODEX_FORECAST_SPEC_2026-10-10.md` (Stage 3)

---

## 0. Verdict first

Stage 1 is implemented and its five definition-of-done items are met, measured directly rather than
claimed. Scored against the brief as it stands today, **96 requirements: 77 met, 11 partial, 3 not
met, 5 superseded** by later recorded human decisions.

**But Stage 1 currently emits no plant silhouette and no physical-unit value**, and that is correct
behaviour, not a defect:

| Blocked output | Cause | Unblocked by |
|---|---|---|
| every plant silhouette | `scale_block_nominal_height_mm` is `null`, so the scale block cannot be excluded | caliper-measuring the block |
| `silhouette_area_cv` | follows from the above | the same |
| `usable_for_training` for every session | gated by `silhouette_area_cv_unavailable` + `operational_top_view_silhouette_unavailable` | the above, plus the top-view design decision (§6) |
| any millimetre value downstream | no `pot_rim_inner_diameter_mm` ever measured (board-free capture) | measuring it; see Stage 2 §3 |

Per-frame pose solving works: on a 41-image synthetic session, 41/41 poses solved at **0.22 px** mean
reprojection error.

---

## 1. Files read, and files that do not exist

Read: `handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md` (397 lines, the contract) ·
`handoff/TOMATO_3D_PHENOTYPING_ALGORITHM_SKELETON_2026-09-15.md` · `CONVENTIONS.md` · `CLAUDE.md` ·
`AGENTS.md` · `../공통규약.md` (7,511 B, exists) · `handoff/LOG.md` ·
`handoff/CLAUDE_CODE_FIX_BOARDSPEC_2026-09-16.md` · `handoff/CODEX_STAGE1_REVIEW_2026-09-16.md` ·
`config/{board_spec,capture_config,quality_thresholds}.json` · `tools/make_square_board.py` ·
`build/charuco_board_7x7_190mm_{spec,validation}.json`.

| Named in the brief but absent | Consequence |
|---|---|
| `.gitignore` (brief §6 tree, line 200) | **not met** — §3. Root file, outside Claude Code's column |
| `data/records/<plant_id>/{manual_events,manual_measurements,environment,organ_label_map}.csv` | **not met** — human-written ground truth the pipeline never writes; the layout is simply not present yet |
| `data/calib/intrinsics_shots/` | **partial** — named only in a docstring usage example; no `Settings` property creates or resolves it |
| `cv2.aruco.estimatePoseCharucoBoard` (brief §9) | **the symbol does not exist in OpenCV 4.13** — see §7 |

---

## 2. What was built

```
tomato3d/                      16 Stage-1 modules
  config.py                    frozen Settings, get_settings() lru_cached, derived paths as properties
  logging_setup.py             the one configure_logging() every entry point calls
  io/schemas.py                every schema, the poses.csv column order, the "unavailable" sentinel
  io/manifest.py               session_manifest.json, SessionPaths resolution
  io/tables.py                 the only module importing pandas/csv
  io/quality.py                QualityRecord, threshold gating, validity failures
  io/images.py                 Unicode-safe image IO (added after review R1)
  calib/board.py               ChArUco board, corner detection, sheet <-> board frame map
  calib/intrinsics.py          intrinsic calibration (>= 15 usable views or CalibrationError)
  calib/pose.py                per-frame PnP, turntable axis, measured_angle_deg
  mask/silhouette.py           geometric board rejection, plant mask, area CV
  cli/calibrate_intrinsics.py  camera calibration entry point
  cli/run_stage1.py            one session -> poses.csv, masks/, quality.json
  recon/ organ/ fuse3d/ graph/ pheno/ track/ rules/ twoview/   29 later-stage stub files
tests/                         7 Stage-1 test files within a 262-test suite
```

Outputs per session, published as one coherent set (staged, then swapped in):
`data/derived/<plant_id>/<session_id>/{poses.csv, masks/, quality.json}`.

Operational board today: **`charuco_7x5_266x190mm`** (7×5 squares, 266×190 mm, A4 landscape),
`physical_print_verified: false`, `scale_block_nominal_height_mm: null`.

---

## 3. Conformance with the brief

Scored by an adversarial audit in which every "met" claim had to survive a challenger that opened the
cited `file:line` itself; four claims were downgraded that way.

| Status | Count |
|---|---|
| met | 77 |
| partial | 11 |
| not met | 3 |
| superseded by a recorded decision | 5 |

### Not met (3)

| Brief | Requirement | State |
|---|---|---|
| §6 | `.gitignore` including `build/` and `data/` | file absent; `CONVENTIONS.md` §7 also unsatisfied. Added to the brief *after* implementation |
| §7 | `data/records/<plant_id>/` with its four CSVs | none exists; human-owned ground truth, not a pipeline deliverable |
| §9 | `solve_pose` uses `cv2.aruco.estimatePoseCharucoBoard` | the API does not exist in OpenCV 4.13 — §7 below |

### Partial (11)

1. §12.3 type hints — `tomato3d/` has zero misses; the brief's own `tests/` modules have 87.
2. §12.4 unit-suffixed names — a bare `radius` at `calib/pose.py:137` and two rebinds at
   `calib/board.py:148,154`.
3. §12.5 magic numbers — hoisted to named module constants, but **none comes from a config JSON**, as
   the second sentence of the bullet requires; plus a bare `4` (the PnP minimum) in two places.
4. §4 `Settings` "exactly the listed fields" — a sixth field `synth_path_map` was added by another
   session (recorded in `handoff/LOG.md`).
5. §5 `quality_thresholds.json` — the brief's `_note_board` key is not in the file.
6. §7 `intrinsics_shots/` — docstring only.
7. §7 `environment_log_ref` — never resolved or validated; no `records_dir` property exists.
8. §9 colour chart exclusion — not excluded at all; see §6.
9. §9 `segment_plant_silhouette` — raises unconditionally today; the brief specifies no raise.
10. §11 `test_schema_roundtrip` — split into four named tests; content stronger, name different.
11. §13.1 `pytest` passes — the audit was forbidden to run it; measured separately in §4.

### Superseded (5)

| Brief | Replaced by |
|---|---|
| §5 board listing (7×7, 190 mm) | human instruction 2026-09-17 → `charuco_7x5_266x190mm` |
| §2.1 "no feature-matching pose estimation anywhere" | human choice 2026-09-24 → feature-pose candidates allowed as diagnostic S4 views only |
| §6 import `tools.charuco_render.render_charuco_view` | `CLAUDE.md` → `tests/conftest.py::render_charuco_view` is the single renderer |
| §6 `build/` owned by the second agent | `CONVENTIONS.md` §1 → `build/` is shared |
| §7 one session grammar | a second grammar `<plant_id>_gen_<YYYYMMDD>` for synthetic sessions |

---

## 4. Definition of done — measured

| # | Item | Result |
|---|---|---|
| 1 | `pytest` passes | **261 passed, 1 skipped** (the skip is a missing optional dependency, `openalea.lpy`) |
| 2 | `run_stage1 --help` works | exit 0; `calibrate_intrinsics --help` exit 0 |
| 3 | README shows install, `.env`, calibration, running one session | all four headings present |
| 4 | later-stage packages import and raise `NotImplementedError` | **21 entry points**, 0 wrong exception |
| 5 | no SfM dependency in `pyproject.toml` | none; the only match is a comment explaining why |

---

## 5. Review findings and their fixes

### Codex review `handoff/CODEX_STAGE1_REVIEW_2026-09-16.md` (R1–R4)

All four reproduced before fixing; each regression test was then **mutation-checked** — reverting the
fix in-process makes its test fail (`build/mutation_check_stage1.py`).

| | Finding | Fix |
|---|---|---|
| R1 | On Windows `cv2.imread`/`imwrite` fail silently on this project's own Korean path: every input unreadable, masks written nowhere while quality said "usable" | all image IO through `tomato3d/io/images.py`; a write failure raises and is a hard failure; the whole CLI suite now runs under a Korean data root |
| R2 | The projected board rectangle erased the **entire** T0 plant silhouette (0 of 60,077 plant pixels) while the session was still marked usable | top views are not masked (`SUPPORTED_VIEW_TYPES = ("side",)`); empty masks are not published; new validity codes gate `usable_for_training`. Fail-closed interim — the design question is open (§6) |
| R3 | A frame resized to 800×600 solved with the 1600×1200 camera matrix at **1413 mm instead of 713 mm**, with a residual small enough to pass the 1 px session gate | image size is compared with `Intrinsics.image_shape` before detection; a mismatch is a recorded failure and a validity code |
| R4 | A rerun left the previous run's masks beside the new `quality.json` | outputs are staged and swapped as one set; `quality.json` leaves first and returns last; only Stage 1's own three artifacts are replaced |

Response document: `handoff/CLAUDE_CODE_STAGE1_REVIEW_RESPONSE_2026-09-16.md`.

### BoardSpec fix `handoff/CLAUDE_CODE_FIX_BOARDSPEC_2026-09-16.md`

`config/board_spec.json` had been rewritten and no longer validated — 17 keys the strict model
forbade, and `scale_block_nominal_height_mm: null` against `Field(gt=0)`. Nothing ran. Fixed by
extending the schema, not the config: the new typed fields with `extra="forbid"` kept, `_`-prefixed
human notes carried verbatim and never read, marker/corner cross-checks, a nullable block height, and
an optional `scale_block_footprint_mm`. `build_charuco_board` now sets the legacy flag **and**
`marker_ids` explicitly; `board_variant_id` is required in every manifest and a mismatch exits 2
before any output is written.

**Spec correction, verified on OpenCV 4.13:** `legacy_pattern` changes the layout **only when
`squares_y` is even**. On 7×7, 5×5 and 6×7 both settings render identically, so the "silent wrong-ID
risk" does not apply to any board this project has used. The explicit call is still correct — it
protects an even-row board added later — and both facts are pinned by tests.

---

## 6. Known limitations — what Stage 1 cannot emit today

1. **No silhouettes at all.** The scale block is unmeasured, so it cannot be excluded; no placeholder
   height is substituted. Poses still solve, the reason is logged once per run, masks are not written,
   and the session is gated out of training.
2. **No top-view silhouette, by design.** Seen from above the whole plant projects inside the board
   quad, so geometric board rejection removes it. An empty or partial top mask would carve the plant
   out of a visual hull, so none is produced. **The operational top view T0 is required, so every
   session is gated.** Resolving this needs a design decision: compare against the rendered board
   pattern, allow greenness classification inside the quad (arguably against hard constraint 3), or
   defer top-view silhouettes to Stage 2 multi-view consistency.
3. **The colour chart is not excluded.** `color_chart_on_board: false` — it stands beside the board and
   has no position in the spec, so from an elevated side view it can enter the plant candidate region.
4. **Side-view silhouettes lose the pot and lower stem**, which project onto the board quad.
5. **Scale block footprint** falls back to one board square when `scale_block_footprint_mm` is null; a
   physically wider block overhangs that box.
6. **`physical_print_verified: false`** — no printed sheet has been measured.

---

## 7. Contract corrections

| # | Correction | Evidence |
|---|---|---|
| 1 | **`cv2.aruco.estimatePoseCharucoBoard` does not exist in OpenCV 4.13.** `solve_pose` uses `CharucoBoard.matchImagePoints` + `cv2.solvePnP`, the documented replacement in the new ArUco API; accuracy is pinned at < 0.5 px reprojection by test. **This substitution was recorded in `handoff/LOG.md` on 2026-09-16 and lost when that file was rewritten twice from a stale copy; this document restores the record.** | `hasattr(cv2.aruco, 'estimatePoseCharucoBoard') == False` on 4.13.0 |
| 2 | `legacy_pattern` is a no-op on odd row counts (§5) | rendered both ways on 7×7, 5×5, 6×7 |
| 3 | A failed `poses.csv` row writes `unavailable` for **every** numeric column including `n_corners_detected`, following the brief literally even though a count was observed | brief §8 |
| 4 | Side rows carry `unavailable` for `top_position`, which is structurally absent rather than unmeasured — one sentinel, so no reader must distinguish an empty cell from a missing one | — |
| 5 | `SessionManifest.scale_reference_block_mm` was made nullable: a required float forced every manifest shot before the block is measured to invent a number | project rule: never impute |

### Change requests (not applied; outside Claude Code's column)

| CR | Request | Owner |
|---|---|---|
| S1-CR-1 | Create `.gitignore` with at least `__pycache__/`, `*.pyc`, `.pytest_cache/`, `build/`, `data/`, `.env` | human (root file) |
| S1-CR-2 | Decide whether `data/records/<plant_id>/` and its four CSVs will exist, and their columns | human |
| S1-CR-3 | Move the segmentation constants into a config JSON, or amend brief §12.5 | human (`config/` is theirs) |
| S1-CR-4 | State the meaning of `board_center_mm` (board centre vs turntable axis) — currently duplicates width/2 and is not cross-validated | human |
| S1-CR-5 | Measure `scale_block_nominal_height_mm` and `scale_block_footprint_mm`; set `physical_print_verified` only from a measured sheet | human |

---

## 8. Human decisions this stage waits on

1. Measure the scale block → unblocks every silhouette.
2. The top-view silhouette design decision (§6.2) → unblocks `usable_for_training`.
3. A colour chart position, or an explicit decision to accept the contamination risk.
4. `pot_rim_inner_diameter_mm` → unblocks every millimetre value in Stages 2 and 3.
5. `.gitignore` (S1-CR-1) and the `data/records/` layout (S1-CR-2).

---

## 9. Handover to Stage 2

Stage 2 consumes `poses.csv`, `masks/` and `quality.json` and must honour: the two coordinate frames
(sheet vs board) with `calib/board.py::sheet_to_board_mm` as the only converter; `unavailable` never
0; CSV for tables and JSON for configuration; `board_variant_id` checked, not trusted; and the fact
that **no mask and no millimetre value exists today**. The Stage-2 contract already encodes all of
this — see `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` §2–§4.

Out of scope for Stage 1: reconstruction, organ segmentation, phenotypes, the two-view product — all
present as stub packages that raise `NotImplementedError`.
