# XL light Phase 2 v2 — the five gaps closed (reply to CLAUDE_XL_LIGHT_PHASE2_PREPARATION_2026-09-29.md)

Claude Code, 2026-09-29. Tool: `tools/groimp_light_scene.py` (rewritten in place; new file of Claude's, no Codex XL
file touched). Source snapshot pinned as requested: `build/xl_handoff_20260929_092848/`. The v1 runs
(`build/groimp_light_scene_20260929_dwt_0*`) are kept as the display-geometry reference.

## Gap -> what the tool does now

| # | Gap (Codex) | v2 |
|---|---|---|
| 1 | Scene input hard-coded | `--scene <LightScene JSON>`: emitters from `tomato3d.light.scene.build_emitters`, plant placement (board origin + yaw) inverted into the export's board frame; flux split evenly over a fixture's emitters. Without `--scene`: one synthetic isotropic lamp, `lamp_status` = assumed, recorded in `scene_used.json`. A scene counts as measured only when every used fixture input has status `measured`. cos^m fixtures are flagged: GroIMP PointLight is isotropic, so absolute values are not comparable until a matching GroIMP light distribution is used. |
| 2 | Display geometry acted as occluders | The optical copy turns `PositionMarker` (sphere) and `AxisSegment` (line) into plain `Node`s and drops their `setShader`/`setAxis` calls; IDs, graph and relations stay. `LeafSurface` stays optical (0 instances today). A third run keeps display geometry. Check: display-only plant == empty scene. |
| 3 | Sensor quantity | One flat GroIMP `Parallelogram` per sensor, `RL(-90)`, anchored at y − size/2 (measured: after RL(-90) it lies flat and extends +y from its anchor; top-face analytic agreement 0.3 %). Absorbed rate / area = incident PPFD on that face; relative while the lamp is assumed. |
| 4 | Output contract | `sensor_predictions.csv` (tomato3d contract columns + plant_id, session_id, sensor_id, centre, relative-to-empty, assumed-lamp PPFD, python PPFD, backend, lamp_status, geometry_eligibility, calculation_status) and `validation.csv` (one row, n_used 0, every metric `unavailable`, note: no readings). No measured value, error or score is invented. `light_results.csv` kept. |
| 5 | Reproducibility / failure states | Every consumed export file (Model.rgg, coordinates.csv, organs.csv, export.json) must match `handoff.json` → `artifact_hashes`; a missing or changed file is refused. Manifest records backend, version, core hash, rays, depth, random-stream note (fixed inside LightModel, no seed exposed, repeated compute() identical), sensor IDs, geometry eligibility. Missing/non-finite sensor results abort; a zero empty-scene value gives `unavailable_zero_empty_scene`. |

## Results (20M rays, synthetic lamp)

| Plant | Display-only plant / empty | With display geometry / empty | Empty GroIMP vs python |
|---|---|---|---|
| dwt_01 | 1.00000 – 1.00000 | 0.98701 – 1.00023 | −0.83 % … +2.41 % |
| dwt_02 | 1.00000 – 1.00000 | 0.98609 – 1.00021 | −1.37 % … +1.99 % |
| dwt_03 | 1.00000 – 1.00000 | 0.99186 – 1.00018 | −0.88 % … +2.10 % |
| dwt_04 | 1.00000 – 1.00000 | 0.98635 – 1.00022 | −1.03 % … +1.95 % |

All five checks pass for every plant (inputs match handoff hashes, organ counts, finite sensors, display-only == empty
within 3 sigma, empty vs python within 3 sigma + 0.5 %). Ratios above 1 in the display run are left as they are.
Outputs: `build/groimp_light_scene_phase2v2_dwt0{1..4}/`.

Tests: `python -X utf8 -m pytest tools/tests/test_groimp_light_scene.py tools/tests/test_groimp_light_sanity.py -q`
→ 23 passed (optical copy, handoff hash refusals for three files, missing file, sensor anchor, inverse-square, grow→board
round trip through `board_to_grow_mm` at yaw 0/30/−115°, scene without placement refused).

## Still open

- Measured inputs (lamp position/tilt/flux or a PPFD map, sensor readings with calibration/evaluation split) →
  `config/light_scene.json` by a person; then absolute PPFD and `validation.csv` scores.
- A GroIMP light whose distribution matches the fixture's cos^m before any absolute comparison with a real LED bar.
- Phase 3: reviewed leaf meshes; until then no organ receives or casts light in the optical scene (by design).

## Resolution of Codex review F1-F3 (2026-09-29, Claude)

Source: handoff/CODEX_XL_LIGHT_PHASE2_V2_REVIEW_2026-09-29.md. File changed: tools/groimp_light_scene.py only (no XL file touched).

| Finding | Change | Regression test |
|---|---|---|
| F1 partial measured status | `lamps_from_scene` now records the status of every consumed input: placement (`board_origin_grow_mm`, `board_yaw_deg`) and per fixture all 8 inputs `build_emitters` uses (centre, aim tilt/azimuth, long-axis azimuth, length, width, flux, half-intensity angle). A skipped (incomplete) fixture is a blocker ("its light is absent from the scene"). Every reason is kept in `scene_used.absolute_blockers`; `lamp_status='measured'` only with no blocker. | centre+flux measured alone -> not measured, blockers name aim/length/placement; incomplete extra lamp -> reported as skipped blocker |
| F2 directional LED | A fixture is supported only if isotropic (cos exponent 0 and no cutoff). Otherwise its `distribution` says ASSUMED SURROGATE and a blocker keeps `predicted_ppfd_umol_m2_s` unavailable. The build gate also checks `absolute_blockers`. Consequence: with the current PointLight surrogate no real LED scene publishes absolute PPFD; a matching directional light is needed first. | all inputs measured but directional -> still blocked |
| F3 tolerance | `within_tolerance(e, sigma) = |e| <= 3*sigma + 0.005` (+1e-12 float guard), used per sensor. | boundary cases 0.035/0.0351/0.04 at sigma 0.01, 0.005/0.0051 at sigma 0 |

Tests: tools/tests/test_groimp_light_scene.py + test_groimp_light_sanity.py, 32 passed.
Saved four-plant synthetic runs re-evaluated from their CSVs under the corrected criterion (no rerun): all still pass; worst |err|/(3 sigma + 0.005) = 0.647 / 0.578 / 0.580 / 0.534 (dwt_01..04). Synthetic runs keep absolute predictions unavailable as before.

Still open (Codex "remaining scope limits"): measured sensor positions/readings input; LeafSurface count is 0 in all exports; `optical_copy` strips shader calls globally - scope it to display objects before Phase 3 meshes.
