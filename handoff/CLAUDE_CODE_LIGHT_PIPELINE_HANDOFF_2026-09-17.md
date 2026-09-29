# Claude Code -> Codex: leaf light-use pipeline implemented

Date: 2026-09-17
Replies to: `handoff/CLAUDE_BRIEF_3D_LEAF_LIGHT_CALCULATOR_2026-09-17.md`
Status: **implemented and tested. Not validated on real plants or real lamps.**

## What the user asked

After the brief, the user explicitly asked Claude Code to implement the basic flow and the
environment variables (photograph -> 3D leaves -> light distribution -> sensor comparison ->
LED arrangement comparison). That instruction overrides the brief's design-review-first request.
The brief's schedule, person-hours and numeric acceptance criteria were **not** produced.

Research questions as the user stated them:

1. How accurately does a 3D model built from photographs predict the light distribution around
   leaves?
2. How far can the 41 views be reduced, and does question 1's accuracy hold?

## What exists now

`tomato3d/light/` + `python -m tomato3d.cli.run_light`. README section "Leaf light-use under the
LEDs" is the user-facing description. Every input value carries `value`/`status`/`source`;
`unavailable` propagates to outputs and is never 0.

| step | code | reads / writes |
| --- | --- | --- |
| environment variables | `light/scene.py`, `io/schemas.py::LightScene` | `light_scene.json`: lamps (centre, tilt, azimuth, size, emitter grid, PPF, cos^m beam + cutoff, watts, schedule), plant placement (board origin + yaw in grow frame), leaf optics, scenarios |
| leaf geometry | `light/geometry.py` | `leaf_surfaces.csv` (triangles, board frame) or `leaf_patches.csv` (centroid, area, normal tilt/azimuth); grouped by `geometry_variant_id` |
| light distribution | `light/raytrace.py` | direct PPFD per leaf sample; non-leaf surfaces opaque; leaf transmittance once per leaf crossed |
| budgets | `light/budget.py` | `leaf_triangle_light.csv`, `leaf_light.csv`, `plant_light.csv`, `scenario_summary.csv` (mol/day emitted/intercepted/absorbed, kWh/day, absorbed umol/J, deltas vs `as_built`) |
| sensor comparison | `light/validate.py` | `ppfd_readings.csv` -> `sensor_predictions.csv`, `validation.csv`; one lamp factor per scenario fitted on `calibration` readings against `no_plants`, applied to every variant; `evaluation` readings are held out |
| question 2 | `light/compare.py` | `geometry_variant_comparison.csv`: each variant vs a reference variant, per plant, matched leaves by `organ_id` |

Always-on baseline: geometry variant `no_plants` (the empty light field).

Tests: `tests/test_light_raytrace.py`, `tests/test_light_inputs.py`, `tests/test_light_pipeline.py`.
Full suite **183 passed** (116 before). Six injected defects each fail a test (per-triangle leaf
counting, missing `(m+1)` normalisation, missing mm2->m2, calibrating on evaluation readings,
forgotten absorptance, linear dimmed power). Photon conservation is tested: a floor under a lamp
recovers the emitted PPF within 0.5 %.

Example inputs: `tests/fixtures/light/` - placeholders and **synthetic** readings only.

## Ownership notes

- `config/` was not written. `config/light_scene.json` does not exist; the human creates it from
  `tests/fixtures/light/light_scene.example.json`.
- `CONVENTIONS.md` was not edited. Proposal: record the **grow frame** (mm, +Z up, origin described
  in the scene) and that `tomato3d/light/frames.py::board_to_grow_mm` is the only board->grow map.
- View-subset selection was **not** implemented, to avoid duplicating Codex T6. When T6 runs, it
  can emit one `leaf_surfaces.csv` geometry variant per subset; question 2 is then read from
  `validation.csv` and `geometry_variant_comparison.csv` with no new pipeline code.
- Stage 2/3 reconstruction remains stubbed. `leaf_surfaces.csv` is the table it should write.

## Assumptions to review

1. Plant placement = pose of the capture board lying flat under the pot on the shelf (yaw +
   translation; z = pot base).
2. A ray is attenuated once per (plant, organ, leaflet) surface crossed - avoids double counting at
   shared triangle edges, under-counts a rolled leaf crossed twice.
3. Direct light only; reflection not traced (predictions low where reflection matters);
   transmitted light keeps its direction.
4. Readings supported only with every enabled lamp at full output.
5. Dimmed-segment electrical power is unavailable unless measured; never scaled linearly.
6. One leaf optics set for all leaves; leaf area counted once for two-sided leaves.

## Open, not guessed

- Numeric PPFD acceptance criteria and which positions are calibration vs evaluation.
- Whether tomato leaflets need separate surfaces/identities.
- How plant pose under the LEDs will be measured after moving from the capture rig.
- LED model, PPF, beam angle, actual watts; quantum-sensor availability.
- The referenced session `cse_01AjdpW4NnEftAXbs8KfLQUx` was not reachable from Claude Code.
  `non-competitive/light-sim` and `alocasia-farm` were read as reference only.

## Requested from Codex

Review the assumptions above and the physics tests; report problems in `handoff/LOG.md` rather than
editing `tomato3d/` or `tests/`.
