# Claude Code — P1 code fixes (2026-10-11)

Implementer: Claude Code (P1 session). Code changes only — no measurements invented, no training, no uploads.

## 0. Read first (list files read in the report)
`CONVENTIONS.md`, `CLAUDE.md`, last 40 lines of `handoff/LOG.md`, `handoff/P1_EXECUTION_2026-10-11.md`,
`handoff/P1_INVENTORY_2026-10-11.md`, `handoff/MTG_CONVENTION_2026-10-10.md` (A1, A2, §13),
`handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md` (consumer side of the P1 package only).
Another Claude Code session works on `tools/microtom_*` at the same time — do not edit those files.

## 1. Binding rules
- Ownership: `tomato3d/`, `tests/` yours; `tools/` shared — append a LOG claim before editing. Never edit
  Codex-claimed files: `tools/vtc_development*`, `tools/vtc_growth_bridge.py`, `tools/tomato_fsp_*`,
  `tools/TOMATO_FSP_PIPELINE.md`, `tools/tests/test_tomato_fsp_pipeline.py`. Missing hook → LOG request + fixture.
- `config/`, `data/records/`, `docs/`, original `Downloads/vtc-main`: read-only. LOG append-only.
- Never overwrite earlier outputs: new runs get new `build/…_<nn>` folders; issued forecasts stay immutable.
- MTG §13: area_basis `full_outline`; blade curl and θ flat/bent thresholds on hold — no field, no threshold.
- Every value keeps its `source_kind`; nothing becomes `measured` without a human record.

## Part A — P1 (`tomato3d/state/`, `tomato3d/cli/run_p1.py`, `tests/`)

**A1. Capture timezone.** Real captures carry device-clock times without a UTC offset. Add an explicit capture
timezone input (`--capture-tz`, IANA name, default none) recorded in `captures.csv` as `capture_tz` +
`capture_tz_source` (`user_stated` when given, else `unavailable`). With it, emit timezone-aware ISO times;
without it, keep times naive and the segment `unavailable` (never guess). The capture timezone is NOT yet confirmed by the user. Ask the user in chat; only after an explicit
confirmation (e.g. "Asia/Seoul"), re-export the real audit as a NEW package `build/p1_state_20261011_03` with
that `--capture-tz` (`capture_tz_source = user_stated`, quote the confirmation in LOG). No confirmation → implement
the flag and stop this item. Leave `_02` untouched. Check that Codex's `tools/tomato_fsp_io.py::audit_p1_package`
no longer lists the timestamp gap for `_03` (read-only call).
Tests: aware vs naive, invalid tz rejected, no implicit offset.

**A2. Side-view rule into the MTG convention.** The rule "side-view compound angles are taken only from views
whose direction label is `cl_left`/`cl_right`" lives only in code. Append to `handoff/MTG_CONVENTION_2026-10-10.md`
a new section `## 14. Amendment A3 — side-view measurement source (Claude Code)`: the rule, the evidence (R.1
synthetic: per-compound median 7.0°, p90 15.6° vs first-view 14.6° / 49.5°; toward/away views 25–41°), the
field that records which view was used, and that the error figures are synthetic-truth projection error, not
real-photo accuracy. Append-only; no earlier section edited. Make `sidegeom.py` write the chosen view and the
rule version into its output.

**A3. Re-validate on the full R.1 set.** When render batches b/c are finalized
(`build/sideprop_20261009_01/kaggle/klog/render_steps.log`, finalized views on disk), rerun side-geometry
validation on all finalized scenes into a new output folder; report per-class errors for 50 vs all scenes. If
b/c are not finalized, report the count present and stop this item (do not start renders).

**A4. Occlusion-completion candidates.** Only 5/14 occluded compounds passed coverage ≥ 0.98 because candidates
are pre-built compounds only rotated/scaled (no L-Py). Improve candidate generation without lowering the
threshold:
- First check whether `openalea.lpy` can be installed in the project env (report the command and result; do not
  change the env file).
- If not, generate candidates from `tomato3d/synth/compound_leaf.py` with sampled rachis length, pair count,
  leaflet sizes and bend within the declared generator ranges (`user_assumed`), fitted to the observed 2-D mask
  (rotation, scale, per-pair size).
- Every candidate stays `conditional_completion` in a separate sub-MTG.

Report pass count before/after on the same fixture. Tests: threshold unchanged, provenance kept, no candidate
promoted to observed.

**A5. Generator `fixed=` decision.** The prompt assumed `build_compound(fixed=…)`; it does not exist. Decide from
current callers whether A4 or the tracker needs it. If yes, add a narrow `fixed=` whitelist
(`terminal_rel_length`, `contour_index.T`, `width_scale`):
- apply it after the normal draw so the RNG stream is unchanged;
- `fixed=None` stays bit-identical (regression test).

If not needed, record the decision in the report and change nothing.

## Deliverables
- Code + tests; full `tests/` suite passes (report counts; also run `tools/tests/test_tomato_fsp_pipeline.py` read-only to
  confirm the consumer still accepts the packages).
- New outputs: `build/p1_state_20261011_03` (A1, only after the user's timezone confirmation), side-geometry
  revalidation folder (A3, if batches are ready).
- Report `handoff/P1_FIXES_EXECUTION_2026-10-11.md` + `_KO.md`: per item done / blocked (why) / unchanged, commands and exit codes.
- Update the P1 rows' notes in `flow/flow_map.csv` and rerun `python -X utf8 flow/check_flow.py --md`.
- LOG: claim line first, result line last.

## Out of scope
Codex-owned pipeline/V3 internals, new measurements or thresholds, Q2 board-free 3D, detector training,
nutrient-growth coupling, any claim of real-photo reconstruction or validated growth.
