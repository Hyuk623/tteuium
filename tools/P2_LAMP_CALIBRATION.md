# P2 native lamp calibration

`p2_lamp_calibration` adds a separate native fitting route. The existing direct-light fitter,
absolute blockers, measured reference-DLI routes, human records and growth model are unchanged.
Everything produced here is diagnostic/conditional. A small validation error does not establish
physical accuracy, especially for an unreconstructed canopy.

## Workflow and contracts

All output directories must be new children of project `build/`.

1. `python -m tools.p2_lamp_calibration audit --records data/records/env_20261013 --operating build/NEW/operating.json --out build/NEW/readiness`
2. Fill a separate `p2-native-lamp-plan-1` plan with explicit scene variants. Use the existing
   `ppfd_validation` scene, rig-surface, sensor, point and reading contracts. No input templates
   have runnable default lamp, beam, enclosure or sensor dimensions.
3. `python -m tools.p2_lamp_calibration freeze --plan build/INPUT/plan.json --out build/FROZEN`
4. `python -m tools.p2_lamp_calibration run --frozen build/FROZEN --out build/RUN`
5. `python -m tools.p2_lamp_controls --fit build/RUN/fit.json --out build/CONTROLS --emitter-grid 80 12 --sensor-samples 256 --atol 0.1 --rtol 0.02 --se-multiplier 6`
   These example numerical verification controls are explicit engineering choices, not measured inputs.
6. Export a reference field with an explicit frame/time contract:
   `python -m tools.p2_lamp_calibration export-reference --fit build/RUN/fit.json --variant ID --contract build/INPUT/reference_contract.json --out build/FIELD`
7. Consume a frozen point through the existing channel:
   `python -m tools.reference_dli simulate --position build/INPUT/reference_position.json --schedule build/INPUT/schedule.json --frozen-prediction build/FIELD/frozen_prediction.json --out build/DLI`
8. `python -m tools.reference_dli_consumer build/DLI/reference_dli.json`

The real input audit supports `daily_on_hours`, `output_fraction`, `source_kind=user_stated` and
`source_ref`. Daily duration is adequate for a stated constant-PPFD dose calculation, but does not
supply the dated clock intervals required by the reference-DLI channel.

## Fitting

Each plan variant has `variant_id`, `provenance`, `conditional_reasons`, paths `scene`,
`rig_surfaces`, `sensors`, `points`, `readings`, and explicit `fit_surface_ids`,
`enclosure_surface_ids`, `disc_segments`. Files and code are hashed at freeze. Native execution
saves a source snapshot and refuses finalization if code/input hashes change. Old packages are
never repaired by changing their hashes.

The fit grid varies `effective_reflectance_grey`, and optionally one declared lamp position
axis with `offset_grid_mm`. It solves a single common `photon_flux_scale` by bounded least squares:

`scale = clip(sum(q_i*y_i) / sum(q_i*q_i), lower, upper)`.

Here `q_i` is the seed-averaged coarse native prediction at declared normalization flux, and
`y_i` is the mean observed PPFD for a calibration point. Point weights are equal, including when
repeat counts differ. Only `split_role=calibration`, `stage=empty_rig` points enter the fit. Each
variant is fitted separately; no variant is selected using held-out readings. Flux/reflectance
bounds and offset-grid endpoints are reported when hit. Candidate residuals are exported;
statistical parameter intervals remain explicitly unavailable. No fourth beam parameter is fitted.

Coarse rays, final rays, at least two distinct seeds, maximum depth, timeout per job and maximum
job count are mandatory. Real plans require the specified 4.8M final rays. Job count is checked
before launch and again during execution. One probe per process avoids artificial probe-to-probe
interception. Supported input is full lamp output with ambient excluded and opaque static rig
surfaces. Reconstructed plants/transmissive rigs are not silently added to this calibration route.

Native geometry/optics reuse `ppfd_validation.make_job_rgg`, `rig_surface_triangles`, `sensing_mesh`
and `lamp_adapter`; there is no new ray tracer or object-geometry engine. The E4 native Phong model
and existing rectangular rig representation are reused. Arbitrary E4 imported object meshes are
not yet accepted by this wrapper. AreaLight adapter limitations still apply: positive rectangle
area, 90-degree cutoff and cosine exponent at least one. Unsupported beam models fail.

## Units, controls and uncertainty

Input/output positions are grow-frame millimetres, +Z upward. Native geometry converts to metres
once. The existing directional rectangular adapter preserves length/width, normal, orientation
and total source output. Source power is explicitly converted from umol/s to monochromatic W via
`fsp_extensions.photon_factor(wavelength_nm)`. Receiver absorbed W is multiplied by the same
factor and divided by the upward black probe's area in m2, producing incident umol/m2/s. The
intermediate adapter's numeric field names are historical; its saved power convention explicitly
marks W. The wavelength is a declared bookkeeping basis, not a measured spectrum. RGB fractions
are metadata; per-band predictions are unavailable. Electrical watts/lumens are not optical PPF.

Each selected fit is rerun with final rays and all seeds for:

- Full reflective enclosure.
- Identical opaque geometry with all reflectance set to zero (direct-only black-rig control).
- Declared enclosure surfaces removed (geometry-plus-reflection control).

Post-reflection PPFD is an **estimator**, full minus same-geometry black rig. This is not a native
path-history tag and is only supported for the stated reflection-only opaque static geometry.
Per-seed paired differences supply its standard error; negative estimates are retained, not
clamped. A fraction is unavailable for zero total or an estimate outside [0,total]. Neither
enclosure-free differences nor reflected wall power are called a sensor reflection fraction.
The independent direct solver validates the black-rig control under declared absolute/relative
and Monte Carlo tolerances. Complete terminal photon closure is still unavailable.

`conditional_predictions.csv` reports positions, observed and predicted PPFD, seed standard
errors, black-rig and enclosure-free PPFD, reflection estimate/error/fraction and ray count.
Fit reports give RMS and signed bias in umol/m2/s and percent of the observed mean. Percentage
metrics at zero mean are unavailable. Monte Carlo standard error does not include calibration,
beam, geometry, warm-up or model-form uncertainty. The analytic ~60% diffuse term is only a
model-dependent comparator and cannot make a run pass or fail.

## Frozen reference-DLI boundary

`frozen-reference-ppfd-1` includes a hashed CSV, fit and scene references, source hashes,
frame/height basis, upward normal, fixture IDs, full-photon-output basis, conditional reasons,
uncertainty and explicit timestamp support with hashed evidence. The export contract provides
`frame_id`, `coordinate_frame=grow_mm_z_up`, `height_basis`, and `time_support` containing
`start_at`, `end_at`, `source_ref={path,sha256}`.

The consumer requires an exact point and frame match. It does not interpolate or add the pot
rim height again. At present the field is an all-fixture aggregate: schedules with unequal
fixture fractions are refused, rather than redistributing the aggregate. Common dimming requires
explicit linear photon-response evidence. Daily doses integrate the actual dated schedule.

Plant association, coefficient-domain and fixed-horizon rules remain active. Only a single-plant
reference association is supported; a shared multi-plant association needs further spatial
evidence. Conditional predictions can supply auditable daily DLI but cannot supply a usable
whole-plant scalar. The independently recomputed consumer checks raw field hashes, coordinates,
support, schedule segments and dose, with absolute/relative tolerance 1e-12.

No `measured` provenance is assigned to a prediction. No P3/P4 integration, biological accuracy,
leaf-absorbed flux or completed physical calibration is implied.
