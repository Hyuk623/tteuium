# P2 lamp calibration execution — 2026-10-13

## Outcome

Native fitting, conditional comparison, frozen spatial export and independent reference-DLI
consumption are implemented and exercised. **Real lamp calibration is incomplete.** Missing
physical geometry/beam/sensor inputs are reported, not replaced by example values. No usable
P3 growth reference or validated physical PPFD is claimed.

The user confirmed in this task: lamp height **300 mm above the board**, **14 h/day**, **100%**
output, lamp clearances **50 mm** (edge-to-edge per the earlier explicit arrangement). This
supersedes the older provisional 400 mm/16 h scenario for these measurements. Exact emitting
surface height and daily clock endpoints remain unspecified. The confirmation is in
`build/p2_lamp_calibration_20261013_01/operating.json`; human records were not edited.

## Files and callable contracts

- `tools/p2_lamp_calibration.py`: `audit(records, operating, out)`, `freeze(plan_path, out)`,
  `run(frozen, out, java, core)`, `export_reference(fit_path, variant_id, contract_path, out)`.
  Separate `p2-native-lamp-plan-1`/`p2-native-lamp-fit-1` contracts; existing direct fitter unchanged.
- `tools/p2_lamp_controls.py::check`: independently reconstructs native raw power-to-PPFD and
  paired reflection differences, compares same-geometry black-rig results to the existing direct solver.
- `tools/reference_dli_frozen.py`: `frozen-reference-ppfd-1`, exact coordinate/time/source binding,
  predicted daily integration and independent arithmetic validation.
- `tools/reference_dli.py`: optional `frozen_prediction` on `prepare_record`, CLI
  `simulate --frozen-prediction`; raw scene simulation remains deferred, measured routes unchanged.
- `tools/reference_dli_consumer.py`: dispatches the frozen-field route to independent checks.
- Three new tests: `test_p2_lamp_calibration.py`, `test_p2_lamp_controls.py`,
  `test_reference_dli_frozen.py` under `tools/tests/`.
- `tools/P2_LAMP_CALIBRATION.md`: input/output/unit/uncertainty/CLI contract.

Reuse: directional `ppfd_validation.lamp_adapter`, existing rectangular rig/Phong surfaces,
one-sided probes, `run_groimp`, direct transport and `fsp_extensions.photon_factor`.
No new ray tracer, growth advance, training/upload or human configuration changes.
`groimp_light_scene.py` was not changed. General E4 mesh import is not added to this wrapper.

## Frozen execution and scientific boundaries

Fit only calibration-labelled empty-rig readings; validation values never enter parameter or
variant selection. Flux is a single bounded scale, grey reflectance is an explicit grid and
an optional single-axis offset is a third parameter. Beam is fixed, never a fourth fitted parameter.
Each variant is frozen and reported separately. Inputs/code are hashed before execution, source
is snapshotted, and changed inputs/code prevent finalization. Job/seed/depth/ray/timeout budgets
are explicit. At least two final seeds and one probe per native job are required.

Coordinates are grow-frame mm, native geometry m. Flux conversion is explicitly
umol/s -> monochromatic W -> incident umol/m2/s, exactly once in each direction. Declared 550 nm
is not a measured spectrum. RGB is metadata. `effective_reflectance_grey` is not a material measurement.
The native internal scene carries radiometric numeric power; the exported fitted scene carries
photon flux and fitted provenance.

Reflection output is a **paired-seed estimator**: full received PPFD minus same-geometry,
zero-reflectance opaque rig PPFD. Opaque surfaces are required; transmission is refused.
This preserves blocking. The enclosure-free run is a separate geometry-plus-reflection control.
Negative estimates are retained; fractions outside [0,1] or with zero denominator are unavailable.
This is not native per-path bounce tagging and does not close terminal escape/cutoff accounting.

Per-position full/black/enclosure-free PPFD, seed standard errors, reflection estimate/fraction,
fit ray count, final ray count, bound hits and conditional reasons are exported. Statistical
parameter intervals and systematic uncertainty remain explicitly unavailable. No ~60% target
is imposed. A canopy geometry or meter mismatch cannot be resolved by agreement between variants.

The reference consumer supports exact sampled points, one plant association and common fixture
fractions. Unequal fixture schedules need per-fixture fields and are refused. Missing support,
hash/coordinate mismatches and missing domain/horizon evidence cannot yield a usable whole-plant
value. Conditional daily DLI remains inspectable but `value=null`, `status=unavailable`.

## Validation evidence

Fresh root: `build/p2_lamp_calibration_20261013_01/`.

| Check | Result |
|---|---|
| Focused P2/reference/integration suite | **225 passed**, exit 0, 217.34 s; `tests.xml` |
| Synthetic observation generation | Four native jobs at 4.8M rays, seed 987; `synthetic_truth/` |
| Frozen synthetic calibration | 42 native jobs; coarse 200,000 rays, final 4,800,000; seeds 123/456; max depth 8; budget 42; per-job timeout 120 s; exit 0 |
| Raw native power -> prediction/difference | Independent recomputation passed at absolute/relative tolerance 1e-12; `synthetic_controls_02/controls.json` |
| Native black rig vs existing direct solver | All four points passed `abs(error) <= 0.1 + 0.02*abs(direct) + 6*seed_SE` umol/m2/s; emitter grid 80x12, sensor sampling 32x32 |
| Native field -> export -> DLI -> independent consumer | Passed; `independent_consumer.json`; arithmetic tolerance absolute/relative 1e-12 |
| Real input integrity | All readiness source hashes unchanged |
| Current flow index | 146 rows, zero missing paths; existence check only |

Commands: `python -m tools.p2_lamp_calibration audit/freeze/run`,
`python -m tools.p2_lamp_controls`, and `python -m pytest` on the eleven scoped test modules.
Exact native acceptance and reference-export preparation scripts are retained as
`run_native_acceptance.py` and `finalize_reference.py` in the fresh root. Final native invocation:

```
python -X utf8 -m tools.p2_lamp_calibration run --frozen build/p2_lamp_calibration_20261013_01/synthetic_frozen_02 --out build/p2_lamp_calibration_20261013_01/synthetic_fit_02
```

An earlier development run (`synthetic_fit/`) was interrupted when code was being hardened.
It has no finalized fit, is marked `INTERRUPTED.json`, and is preserved. Its partial jobs are
not acceptance evidence. No old hash was replaced to make an old run appear current.

### Important negative result in the synthetic fit

This is a four-point software fixture, not any of the 46 physical readings. Synthetic truth
was generated at grey reflectance 0.4 and flux scale 1.2. The coarse search selected reflectance
**0.8 (upper bound)** and scale **1.1770675253**. Final calibration RMS was **1.1116%** of its
observed mean; the one held-out point error was **1.8647%**. Therefore the pipeline executed,
but reflectance was **not recovered/identified**. The boundary hit and unavailable parameter
interval are part of the result, not a reason to tune the fixture or quote a physical reflectance.

The exported synthetic center-point dose at an explicit synthetic 14 h schedule is
**17.0601290429 mol/m2/day**. Its independent consumer is valid while its usable-reference status
remains unavailable because the prediction is conditional and systematic uncertainty is unknown.
This value is not a prediction for the user's shelf.

## Real readiness and remaining work

The read-only real-data summary contains 30 rim and 16 canopy readings. At the user-confirmed
14 h duration, constant measured-output summaries are 9.14046 and 14.91279615 mol/m2/day.
These are measurement summaries, not fitted per-pot/leaf references.

Remaining inputs: emitting surface dimensions/centres/beam and provenance; full wall/ceiling
geometry; sensor footprint/calibration; declared grid origin/orientation variants and approximate
tray placement; canopy plant geometry; fit bounds and native budget; dated clock/time-transfer
evidence for downstream daily reference use. Housing dimensions are not silently optical dimensions.
Science/backend limits: grey model, missing parameter/systematic intervals, sensor reflection
estimator rather than path tags, no terminal closure, no per-band optics, aggregate-field schedule
restriction, no arbitrary E4 mesh import in this wrapper. Physical validation remains unperformed.

The active Claude Code F9 claim includes `flow/flow_map.csv`, so shared flow files were not edited.
Owner upsert rows are in `handoff/P2_LAMP_CALIBRATION_FLOW_ROWS_2026-10-13.csv`; current/proposed
status renderings generated with the existing checker are in the build root. The owner should
merge by path and run `python -X utf8 flow/check_flow.py --md`. No P3/P4 enablement is requested.
