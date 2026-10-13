# Claude Code — Micro-Tom forecast layer code fixes (2026-10-11)

Implementer: Claude Code (forecast session). Code changes only — no measurements invented, no training, no uploads.

## 0. Read first (list files read in the report)
`CONVENTIONS.md`, `CLAUDE.md`, last 40 lines of `handoff/LOG.md`, `handoff/MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md`,
`handoff/MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md`, `handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md`,
`tools/TOMATO_FSP_PIPELINE.md`, `handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md`, `handoff/MTG_CONVENTION_2026-10-10.md` (A1, A2, §13).
Another Claude Code session works on `tomato3d/state/`, `tomato3d/cli/run_p1.py`, `tests/` at the same time — do not
edit those files; read P1 packages only.

## 1. Binding rules
- Ownership: `tomato3d/`, `tests/` yours; `tools/` shared — append a LOG claim before editing. Never edit
  Codex-claimed files: `tools/vtc_development*`, `tools/vtc_growth_bridge.py`, `tools/tomato_fsp_*`,
  `tools/TOMATO_FSP_PIPELINE.md`, `tools/tests/test_tomato_fsp_pipeline.py`. Missing hook → LOG request + fixture.
- `config/`, `data/records/`, `docs/`, original `Downloads/vtc-main`: read-only. LOG append-only.
- Never overwrite earlier outputs: new runs get new `build/…_<nn>` folders; issued forecasts stay immutable.
- MTG §13: area_basis `full_outline`; blade curl and θ flat/bent thresholds on hold — no field, no threshold.
- Every value keeps its `source_kind`; nothing becomes `measured` without a human record.

## Part B — Forecast layer (`tools/microtom_*`, `tools/tests/test_microtom_*.py`)

**B1. Route through the pipeline.** `tools/microtom_forecast.py` calls V3 directly, so forecasts are single-plant
with no canopy shading and no P1 input. Codex's report names `tools/tomato_fsp_pipeline.py` the single
state-advance authority.
- Add a route `--engine pipeline` that builds ensemble members as pipeline runs (prepare → run → collect) from a
  P1 package or fixture, multiple instances, canopy placement included.
- Read results only from committed checkpoints. Never call `advance_interval` on an already produced checkpoint.
- Keep `--engine v3_direct` for single-plant scenarios, labelled as such in the manifest.
- If the pipeline lacks an entry you need (e.g. a parameter-registry override per member), request it in LOG and
  stop that part.

Tests:
- pipeline-route manifest records instance IDs and checkpoint hashes;
- no double advance;
- the v3_direct route still works.

**B2. Ray count for issued forecasts.** Issued forecasts used 300k rays. Make 4.8M the default for `issue`;
allow lower only with `--rays N --diagnostic`, which marks the forecast
`quantitative_light_sampling = false` and `issue_class = diagnostic`. Re-issue the seed-route forecast at 4.8M as a
new folder; leave `_01`/`_02` untouched.

**B3. Ensemble that actually varies.**
- The fixture ensemble had zero spread: `FIRST_LEAVES` is inert once ≥ 9 leaves exist, and the middle ramp is
  inert for 2-pair compounds.
- Before issuing, compute per-member parameter sensitivity eligibility from the input state and draw only
  parameters that can act on it. Candidates include `NR_LEAFLET_PAIRS_BY_RANK` for future compounds, truss
  cadence, phyllochron and others in the registry with declared uncertainty.
- If no eligible parameter has declared uncertainty, issue with `ensemble_spread = none` and say why. Never
  invent a range.

Test: inert parameters are excluded and named in the manifest.

**B4. Separate rule outputs from scenario spread.**
- In event tables, add a `probability_basis` column:
  - `rule_deterministic`: every member shares the rule that produces the event, e.g. apex stop from
    `SP_STOP_RULE`.
  - `scenario_fraction`: members differ.
  - `unavailable`.
- Rename nothing else.

Test: apex stop under one shared rule is `rule_deterministic`.

**B5. Sowing date input.**
- The seed route assumed sowing 2026-09-11 06:00 +09:00.
- Add `--sowing-datetime` (aware ISO), recorded as `sowing_datetime` + `sowing_source`. Values:
  - `user_stated` when given;
  - `assumed_issue_minus_days_at_start` when defaulted.
- Default behaviour unchanged but labelled. Also read an optional per-plant sowing column if the plant registry
  gains one (read-only); absent → default with label.

**B6. Activate H1–H3 when they exist.**
- `CURVE_RATIO`, `BENT_FRACTION` and `AREA_CORRECTION` are `inactive_in_engine`.
- Add a capability check that reads V3's parameter list at runtime. When a hook appears, switch the row to
  `active` automatically and record the V3 version. Until then, stay inactive.
- `AREA_CORRECTION` is accounting-only and never applied to optical geometry.

Test with a fixture V3 parameter list that has and lacks each hook.

## Deliverables
- Code + tests; full `tools/tests/` suite passes (report counts).
- New outputs: re-issued 4.8M forecast (B2), one pipeline-route forecast on `build/p1_state_20261011_01` (B1).
  Earlier `build/forecast_20261011_01/_02` untouched.
- Report `handoff/FORECAST_FIXES_EXECUTION_2026-10-11.md` + `_KO.md`: per item done / blocked (why) / unchanged, commands
  and exit codes, LOG hook requests.
- Update the forecast rows' notes in `flow/flow_map.csv` and rerun `python -X utf8 flow/check_flow.py --md`.
- LOG: claim line first, result line last.

## Out of scope
Codex-owned pipeline/V3 internals, new measurements or thresholds, Q2 board-free 3D, detector training,
nutrient-growth coupling, any claim of real-photo reconstruction or validated growth.
