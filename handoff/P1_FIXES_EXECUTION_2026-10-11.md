# P1 fixes A1–A5 — execution report (run 2026-10-12)

Author: Claude Code. Implements `handoff/CLAUDE_CODE_CLI_PROMPT_P1_FIXES_2026-10-11.md`. Korean companion:
`handoff/P1_FIXES_EXECUTION_2026-10-11_KO.md`. Command log: `build/p1_fixes_cli_log_20261012.txt`.

## 0. Files read
`CONVENTIONS.md`, `CLAUDE.md`, last 40 lines of `handoff/LOG.md` (re-read before each LOG write),
`handoff/P1_EXECUTION_2026-10-11.md`, `handoff/P1_INVENTORY_2026-10-11.md`, `handoff/MTG_CONVENTION_2026-10-10.md`
(A1, A2, §13), `handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md` (consumer side), consumer code
read-only (`tools/tomato_fsp_io.py`, `tools/tomato_fsp_acceptance.py`, `tools/tests/test_tomato_fsp_pipeline.py`),
`flow/flow_map.csv`, `flow/check_flow.py`, `tomato3d/synth/compound_leaf.py` + `.lpy`,
`build/sideprop_20261009_01/kaggle/klog/render_steps.log`.

## 1. Per item

| Item | Result |
|---|---|
| **A1 capture timezone** | **Done.** `prepare --capture-tz <IANA> --capture-tz-ref "<user statement>"` (real mode only; invalid zone, missing ref or fixture mode → exit 2). `captures.csv` gains `capture_tz`, `capture_tz_source` (`user_stated` when given, `assumed` for the fixture's declared clock, else `unavailable`). Times become aware only with a stated zone; DST-gap or ambiguous local times are errors, never guesses; a real row with an offset but no stated zone is rejected ("no implicit offset"). **User confirmation received in chat 2026-10-12: "Asia/Seoul"** → new real audit `build/p1_state_20261011_03` (`_02` untouched). Codex `audit_p1_package` on `_03`: no timestamp gap (gaps 247 → 130: only `scale_unavailable` ×117 and `optical_surface_unavailable` ×13). |
| **A2 side-view rule → MTG** | **Done.** `handoff/MTG_CONVENTION_2026-10-10.md` §14 *Amendment A3* appended (rule, recording field, evidence, synthetic-only caveat) + §14.5 correction (below). `sidegeom.select_views` is the single implementation; `side_geometry.csv` carries `selected_for_mtg` + `view_selection_rule` (`MTG_A3_v1:…`); `structure_state.csv` `evidence_ref` names the selected view. |
| **A3 full R.1 revalidation** | **Done.** Batch c was finalized on disk at 15:44 by the render pipeline (600/600 views with `rgb.png`; I started no render). `build/p1_side_validation_20261012_01` (150 scenes, 4,152 compound-views). Table §2. |
| **A4 occlusion-completion candidates** | **Done, improved 5/14 → 10/14 on the same fixture at the unchanged 0.98 threshold.** L-Py check: `python -m pip index versions openalea.lpy` → "versions: none"; `pip install --dry-run --no-deps openalea.lpy` → "No matching distribution found" (conda-only; project env is CPython 3.13). So the generator runs through a new **numpy backend** (§3). Details §2. |
| **A5 `fixed=` decision** | **Needed by A4 → added.** A4 conditions candidates on the observed terminal leaflet (phynotype2 §6.4: choose the terminal contour by the observed outline), which requires pinning interior draws. Whitelist `terminal_rel_length`, `contour_index.T`, `width_scale.T` (the generator's `width_scale` is per leaflet; the pin applies to the terminal leaflet, matching `contour_index.T`). Applied after the normal draw (RNG stream unchanged); `fixed=None` bit-identical (regression §3). The tracker does not use it. |

## 2. Results

**A3 — side-view geometry vs R.1 truth (synthetic projection error, not real-photo accuracy)**

| Scenes | compounds with a side-on view | A3 median / p90 | first view median / p90 | no side-on view | quadrant |
|---|---|---|---|---|---|
| a 0–49 (64 spp) | 308 | 6.1° / 13.8° | 14.5° / 48.6° | 40 | exact 1073/1073 |
| b 50–99 (64 spp) | 279 | 6.0° / 13.6° | 13.5° / 52.7° | 67 | exact 1024/1024 |
| c 100–149 (16 spp) | 283 | 5.5° / 13.7° | 15.9° / 56.0° | 61 | exact 1021/1021 |
| **all 150** | **870** | **5.9° / 13.7°** | 14.5° / 52.9° | 168 (16 %) | exact 3118/3118 |

Per-class medians (all 150): `cl_left` 5.4°, `cl_right` 5.6°, `cl_toward` 25.7°, `cl_away` 40.7°, `unclear` 17.0°.
θ: A3 1.4° / 3.4° vs first view 2.7° / 16.0°; Σα: 2.1° / 4.8° vs 4.4° / 24.3°. Render spp does not matter here (geometry
only). **Correction:** the 7.0° / 15.6° I reported on 2026-10-11 (and wrote into §14.3) silently fell back to the first
view for the 40 batch-a compounds with no side-on view; A3 has no fallback. Recorded as MTG §14.5, append-only.

**A4 — conditional completion, same fixture (the 14 occlusion-touching compounds of the P1.10 request), threshold 0.98**

| Adapter | compounds with ≥ 1 kept candidate |
|---|---|
| before: pool donors, rotate + scale (`build/p1_state_20261011_01`) | 5 / 14 |
| after: pool donors (unchanged) | 5 / 14 |
| after: generator, numpy backend + terminal pins + bounded fit | **8 / 14** |
| after: either adapter (`build/p1_state_20261012_02`) | **10 / 14** |

Generator adapter (`tomato3d/state/optical.py::generate_candidates`): 48 seeds per compound; compound dict from the
observation (azimuth, distal radius, lateral reach × 1.5); elevation and all other interior values from the declared
generator ranges (`user_assumed`); terminal pins from the observed terminal mask, each kept only inside its generator
range; distal alignment then a bounded local fit (rotation −10…+10°, uniform scale 0.95…1.10, 8 best samples); fit
parameters are `fixture_declared` in `p1_config.json`. **Not hidden:** background violation of kept generator candidates
is 0.09–0.53 (fraction of candidate pixels on non-plant background), reported per row in `completion_report.csv`;
phynotype2 has no violation threshold (null → report only). Per-pair sizes come from the generator's extent contract,
not from a post-hoc rescale. Two compounds failed every sample on the generator contract (48/48 rejected): these are
kept by the pool adapter. Every candidate is `generated_candidate` in a separate sub-MTG and `conditional_completion`
in the optical manifest; `mtg_vertices.csv` holds 0 candidate rows.

## 3. Generator change (`tomato3d/synth/compound_leaf.py`, my column)
- `build_compound(..., fixed=None, backend="lpy")`: default unchanged. `backend="numpy"` = `derive_modules` (same production
  as `compound_leaf.lpy`) + `interpret_numpy` (PlantGL turtle subset: f, down, left, right, push, pop).
- Equivalence: numpy backend vs the **105 stored O-mature compounds** (made by L-Py + PlantGL, incl. redraw attempts):
  max |diff| 5.9e-11 mm, every `attempt` and `contour_index` equal. In the `tomato_synth` env: L-Py default vs stored
  **bit-identical 34/34**, L-Py vs numpy 4.4e-11 mm, `fixed=` applied with all other draws unchanged 32/34 (2 pinned
  samples fail the generator's own contract, as they should).

## 4. Commands and exit codes (`build/p1_fixes_cli_log_20261012.txt`)
```
python -m pip index versions openalea.lpy                                      no versions
python -m pip install --dry-run --no-deps openalea.lpy                         No matching distribution
python -X utf8 -m pytest -q                                                     see §5
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode fixture --out build/p1_state_20261012_01    0
python -X utf8 -m tomato3d.cli.run_p1 run --package build/p1_state_20261012_01                   0
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261012_01                0
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode fixture --out build/p1_state_20261012_02    0
python -X utf8 -m tomato3d.cli.run_p1 run --package build/p1_state_20261012_02                   0
python -X utf8 -m tomato3d.cli.run_p1 compare-observation --package build/p1_state_20261012_02   0
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261012_02                0 (93/93 identical)
python -X utf8 -m tomato3d.cli.run_p1 side-validate --out build/p1_side_validation_20261012_01   0
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode real --out build/p1_state_20261011_03 --capture-tz Asia/Seoul --capture-tz-ref '…"Asia/Seoul"'   0
python -X utf8 -m tomato3d.cli.run_p1 run --package build/p1_state_20261011_03                   3 (valid, partial)
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261011_03                0 (13/13 identical)
python -X utf8 -m pytest -q tools/tests/test_tomato_fsp_pipeline.py                             28 passed (read-only consumer check)
python -X utf8 flow/check_flow.py --md                                                           0
```
`build/p1_state_20261012_01` is **superseded**: it marked every side-on view selected because `validate_scene` wrote the
view name into `capture_id` (one R.1 scene = one side capture). Fixed (`validate_scene(capture_id=...)`, a test, and a
package guard that refuses more than one selected view per compound) and republished as `_02`; `_01` kept as the record.

## 5. Tests and consumer
Full `tests/` suite: **350 passed, 1 skipped** (`build/p1_fixes_pytest_20261012.txt`; before
this session 331 passed, 1 skipped). New: `tests/test_synth_numpy_backend.py` (6, one skips without the O-mature build),
`tests/test_state_p1_fixes.py` (13). Codex consumer `tools/tests/test_tomato_fsp_pipeline.py`: 28 passed;
`audit_p1_package`: `_20261011_01` fixture_ready (revision-1 headers still accepted), `_20261012_02` fixture_ready,
`_20261011_03` real_ready false with 130 named gaps (no timestamp gap).

## 6. Schema
`p1_state_v1`, **`schema_revision = 2`** (additive): `captures.csv` + `capture_tz`, `capture_tz_source`;
`side_geometry.csv` + `selected_for_mtg`, `view_selection_rule`. Validators accept revision-1 capture headers, so Codex's
reader and earlier packages keep working; the version string is unchanged because Codex compares it for equality. Code
version of the new packages: `p1code-dbc3c1aa596e2c3e`. Earlier packages now report themselves **stale** in `collect`
(code hashes changed) — by design; they remain valid records of their own code version.

## 7. Unchanged / not done
No threshold lowered or added; no measurement invented; nothing marked `measured`. No render started. No edit to
`tools/`, `config/`, `data/records/`, `docs/`, or Codex-claimed / `tools/microtom_*` files. Real P1 still blocked by
scale, top masks, plant↔slot, lights-on time and Q2 (unchanged from `P1_EXECUTION_2026-10-11.md` §9; the timezone is
now resolved).
