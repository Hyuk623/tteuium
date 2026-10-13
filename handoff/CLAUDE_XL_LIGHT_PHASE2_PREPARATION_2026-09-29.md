# Phase 2 preparation and existing implementation review

Date: 2026-09-29
User request: Prepare Phase 2 of the XL/GroIMP light workflow.

## Scope and execution record

Reuse Claude's existing Phase-2 implementation rather than create another scene exporter. This preparation inspected code, saved manifests, model hashes and GroIMP completion logs; it reran the focused Python tests. No new GroIMP simulation, model inference, training, configuration edit or remote push was performed. Existing source and result files are preserved.

References:
- handoff/CLAUDE_XL_LIGHT_SIMULATION_ADOPTION_2026-09-29.md
- handoff/CLAUDE_XL_LIGHT_REVIEW_ANSWERS_2026-09-29.md
- tools/groimp_light_scene.py
- tools/groimp_light_sanity.py

## Verified starting assets

Use the existing static snapshot `build/xl_handoff_20260929_092848/` for this continuation. Do not silently substitute a newer reconstruction.

Saved Phase-2 runs: `build/groimp_light_scene_20260929_dwt_01/` through `build/groimp_light_scene_20260929_dwt_04/`.

Each run contains `empty/Model.rgg`, `plant/Model.rgg`, the corresponding GroIMP logs, `light_results.csv` and `manifest.json`. Source Model.rgg hashes and both generated scene hashes match their manifests for all four plants. Both logs in each run contain SANITY_DONE. Manifests report matching organ counts, 25 sensor results and empty-scene agreement with Python within 5 percent.

| Plant | Saved plant/empty ratio range | Saved empty/Python relative error range |
|---|---|---|
| dwt_01 | 0.9870–1.0002 | -0.77% to +2.46% |
| dwt_02 | 0.9861–1.0002 | -1.20% to +2.11% |
| dwt_03 | 0.9919–1.0002 | -0.89% to +2.19% |
| dwt_04 | 0.9864–1.0002 | -0.97% to +1.88% |

These ratios describe diagnostic display geometry, not measured tomato shading. Ratios slightly above one must remain visible and must not be clamped or interpreted as a biological effect.

Focused verification: `python -X utf8 -m pytest tools/tests/test_groimp_light_sanity.py tools/tests/test_groimp_light_scene.py -q` -> 11 passed.

## What Phase 2 currently does

1. Read the exported static organ graph and coordinates.
2. Add an assumed isotropic point light above the diagnostic coordinates.
3. Add 25 black sensor boxes on the board plane.
4. Run the scene with and without the static organ display geometry.
5. Compare empty-scene photon rates with the existing Python light calculation.
6. Report relative sensor results and preserve organ IDs; organs remain `not_a_surface`.

This is an integration prototype with saved successful runs. It does not reconstruct additional leaf surfaces. Retain `validated_metric=false` and `suitable_for_ppfd=false`.

## Remaining contract gaps to resolve before calling Phase 2 complete

1. **Measured scene input:** the tool currently hardcodes flux, sensor geometry and lamp offset. It does not consume the approved LightScene contract or apply the board-to-grow placement through its existing helper. Connect that contract before any measured-rig comparison. Until then, label the entire scene as synthetic/assumed and retain board-frame coordinates.
2. **Diagnostic geometry must not become biological occluders:** current marker and axis display objects participate in ray tracing. Their display radii can therefore change the ratio. Preserve the current run as a display-geometry software check. Before interpreting sensor results, separate non-optical display objects from eligible physical surfaces, and verify a display-only plant gives the empty-scene result within sampling tolerance. Do not fabricate leaf surfaces to create shading.
3. **Sensor quantity:** the current black boxes collect absorbed photon rate over their surfaces, including side faces. This is not yet a calibrated, oriented sensor-plane PPFD measurement. Define and test the actual sensing face, area averaging and orientation; report absolute PPFD as unavailable while the physical inputs are missing.
4. **Output compatibility:** current results use `light_results.csv`. The approved contract requires compatible `sensor_predictions.csv` and `validation.csv` with additional traceability fields. Preserve raw outputs and add contract-compatible outputs without inventing measured values or validation scores.
5. **Reproducibility and failure states:** record actual backend/version and random-stream control (including unsupported seed control), all consumed input hashes, sensor IDs and geometry eligibility. Validate complete finite sensor results, missing files, zero denominators and changed coordinates/organ tables, not only the RGG hash. Current unit tests do not establish these behaviors.

These findings are preparation items for the existing implementation, not an instruction to change design silently. Claude owns the LightScene schema; keep schema work in the agreed ownership workflow.

## Execution order for continuation

- Start with dwt_01 using the pinned snapshot; keep other saved runs as references.
- Resolve display-versus-optical geometry and sensor-face semantics first.
- Wire the approved LightScene inputs and compatible output tables.
- Check synthetic placements/rotations and repeated initialization before any measured run.
- Expand the same verified adapter to dwt_02–04.
- When actual lamp and sensor data exist, record calibration/evaluation separation and compare predictions with independent readings.
- Reviewed leaf surfaces and their optical properties belong to Phase 3; do not equate the current static graph with completed tomato surface reconstruction.

## Existing reproduction command

Run from the project directory. Use a new output directory; this command executes GroIMP and was NOT run during this preparation:

```powershell
python -X utf8 -m tools.groimp_light_scene --handoff build/xl_handoff_20260929_092848 --plant dwt_01 --out build/groimp_light_scene_phase2_dwt01_followup --rays 20000000
```

The present command reproduces the prototype assumptions above. It is not a measured-light workflow yet.

## Human inputs for the measured-light stage

- Lamp position and direction relative to the plant/board, emitting dimensions and measured or sourced output/distribution (or a measured empty-scene PPFD map).
- Sensor sensing-area dimensions, position, direction and recorded PPFD, with calibration/evaluation designation.
- Plant placement and posture changes since photography.

These inputs are not required to inspect the existing static structure or synthetic integration outputs. Never replace unavailable physical values with apparent measurements.
