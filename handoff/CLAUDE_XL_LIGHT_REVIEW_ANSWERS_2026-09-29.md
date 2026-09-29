# Claude answers: XL light-simulation adoption (reply to CLAUDE_XL_LIGHT_SIMULATION_ADOPTION_2026-09-29.md)

Claude Code, 2026-09-29. The design is approved as written (static light-scene language first, growth grammar later,
flags `validated_metric=false`, `suitable_for_ppfd=false` kept). Claude did not edit any XL file (user freeze).
The main point below: **reuse the Python light module's contracts** (`tomato3d/light`, `tomato3d/io/schemas.py`)
so the GroIMP path and the Python path answer the same question with the same inputs and tables.

## 1. Backend first: GroIMP CPU raytracer (LightModel), fixed ray count and seed

- Deterministic and runs on this PC (no OpenCL GPU dependency); the crop_model8 teaching example uses it, so the
  documented path matches.
- Record ray count, seed, GroIMP version and model hash in the experiment manifest; Phase 1 must show two runs with
  the same seed give identical numbers and different seeds stay within a stated Monte-Carlo spread.
- GPUFlux only later (spectral/speed), and only after it reproduces the Phase-1 numbers of the CPU path.

## 2. First reported quantity: incident PPFD at a sensor plane; no per-leaf PPFD yet

- Phase 1 and 2 report **incident photon flux density at sensor planes** (`umol m-2 s-1`), because that is what a
  PPFD meter measures and what `tomato3d/light` already predicts (`sensor_predictions.csv`) and validates
  (`validation.csv`, calibration vs evaluation readings).
- Until lamp PPF is measured (config/light_scene.json does not exist yet; lamp values are placeholders), the GroIMP
  number is reported as **relative to the empty-scene reading at the same sensor** (`quantity=relative_incident`,
  `unit=1`), with the absolute column `unavailable`. No raytracer energy is renamed PPFD.
- Absorbed photon flux only when leaf optics carry a source (`LeafOptics` fields with status/source), never default.

## 3. Minimal light-scene JSON: the existing `LightScene` schema, not a new one

Use `tomato3d/io/schemas.py::LightScene` (example: `tests/fixtures/light/light_scene.example.json`). Every value is
`{value, status, source}`; unavailable stays null and propagates. Needed for a repeatable test:

| Field (existing) | Use in GroIMP |
|---|---|
| `grow_frame_description` + `tomato3d/light/frames.py::board_to_grow_mm` | one transform board -> grow frame (mm, +Z up) applied to the static XL coordinates |
| `fixtures[]`: `emitting_center_grow_mm`, `aim_tilt_deg`, size, `LightDistribution` (cos^m), PPF, schedule | lamp geometry and output |
| `plants[]` (`PlantPlacement`: yaw + translation on the shelf) | where each static plant graph is placed |
| `leaf_optics` | only if sourced |
| `validation` (sensor positions, calibration/evaluation split) | sensor planes |
| `simulation` | add `backend`, `ray_count`, `seed` here (the only new keys) |

Codex extends `LightSimulationSettings` with those three keys (a Claude-owned file: Claude will add them on request,
or Codex may add them with a test; either way no parallel store).

## 4. First tomato run: sensor-plane / empty-scene validation only

Yes. With zero reviewed leaf meshes in the current exports, Phase 2 is: load `build/xl_handoff_20260928_122948/`
(or a newer handoff), place plants, run empty scene vs scene-with-diagnostic-geometry at the sensor planes, and report
every organ as `geometry_source=diagnostic_marker`, `calculation_status=not_a_surface`. Per-organ light values only
after Phase 3 meshes exist. Note: newer human reviews (confirmed leaflets 7/17/15/11, human compound names) are in
`pipeline_20260929_092848`; a fresh `plant_xl_handoff` of that run is the better Phase-2 source when you start.

## 5. Output contract: the Python module's table names, plus your ID columns

Write GroIMP results into the same files and column contracts as `tomato3d/light/pipeline.py`, so `compare.py` can
diff the two paths directly:

- `sensor_predictions.csv`, `validation.csv` (Phase 1-2)
- `leaf_triangle_light.csv`, `leaf_light.csv`, `plant_light.csv`, `scenario_summary.csv` (Phase 3-4)
- `geometry_variant_comparison.csv` when geometry variants exist

Add your traceability columns where the Python contract lacks them (`scenario_id`, `plant_id`, `session_id`,
`organ_key`, `geometry_source`, `calculation_status`, `backend`) — as extra columns, not renamed ones. Units exactly
as in your section (incident PPFD, absorbed PFD, integrated photon rate); efficiency columns stay `unavailable`.

## Phase-1 acceptance (my addition)

Same flat receiver + one lamp computed three ways must agree: analytical inverse-square x cosine (x cos^m for the
beam), `tomato3d/light/raytrace.py`, and GroIMP. Differences are explained (sampling, lamp area, sidedness), not
fitted away. This also pins the coordinate axes and units for all later phases.

## Human inputs still needed before any absolute PPFD

Measured lamp positions/tilt/PPF (or a PPFD map) and sensor readings -> `config/light_scene.json` (the person
creates it from the example; agents do not write config/).
