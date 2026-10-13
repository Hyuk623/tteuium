# Codex — P2: calibrate the light scene against the first real PPFD measurements (2026-10-13)

Implementer: **Codex** (owner of `tools/ppfd_validation.py`, `tools/reference_dli.py`, `tools/fsp_extensions.py`
— which already carries actual reflection/transmission and static objects — `tools/canopy_light.py`,
`tools/hierarchical_light.py`, `tools/groimp_bridge.py`). `tools/groimp_light_scene.py` is **Claude Code's**: do
not edit it; if the scene builder needs a hook, request it in LOG and work around it meanwhile.

**Why now:** until today every light number in this project was assumed. The user measured 46 points on two
planes, the lamp geometry and the spectrum. For the first time the light model has something to be **wrong
against**. That is the whole point of this task — not to make the model agree, but to find out by how much it
disagrees and why.

## 0. Read first
`data/records/env_20261013/README_KO.md` **and all five files there** (read-only, never write into
`data/records/`); `docs/정의집_토마토_2026-10-11.md` (the 2026-10-13 rows); `handoff/LOG.md` last 40 lines;
`CONVENTIONS.md`; `handoff/CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md`;
`handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md` (the assumed-PPFD rows this task can close).

## 1. The measurements (all `measured`, 2026-10-13)
- **Rim plane** — 7 cm above the board (= pot rim height, the `plant_local_mm` reference plane), **empty board,
  no plants**, 10:57. 6×5 = 30 points over the 60 × 40 cm board. Mean 181.358, min 119.811, max 256.560,
  Uo 0.661, DLI(14 h) 9.14.
- **Canopy plane** — 15 cm above the board, **plants in place**, 10:37. 4×4 = 16 points over the trays.
  Mean 295.889, min 203.528, max 367.416, Uo 0.688, DLI 14.91.
- **Spectrum** PAR 153.5 = R 64.3 + G 63.9 + B 25.3 → R:G:B = 41.9 : 41.6 : 16.5 %. `DLI = PPFD × 0.0504` at
  14 h confirmed against the meter.
- **Shaded point** 31.8 µmol under a leaf vs 153.5 exposed (same minute, among the plants).
- **Geometry** board 60 × 40 cm; trays 14 × 28 × 7 cm × 3, inset ≈7 cm from the edges, within 10 cm of the front;
  lamp = 3 linear LED bars with lenses, 5 cm apart, 30 cm above the board; enclosure walls and ceiling white.

## 2. What is NOT known — do not quietly invent it
- **Grid origin and orientation.** The x/y columns in `ppfd_grid_20261013.csv` are `inferred` (6 cells along the
  60 cm side → 10 × 8 cm cells), chosen because it fits better, **not stated by the user**. Treat the orientation
  as a declared variant and report results for both; if the two variants disagree about a conclusion, the
  conclusion is `unavailable`.
- **Lamp position / orientation / bar length relative to the board.**
- **Which board area the canopy 4×4 covered** (trays only).
- Meter model and calibration.
- **Warm-up:** the canopy grid is 7 min after lights-on, the rim grid 27 min. LED output falls as it heats, so the
  canopy plane may be biased HIGH. Carry this as a stated bias direction, never as a correction factor.

## 3. Work orders
**L1. Enclosure in the scene.** Add the white walls, ceiling and board as reflecting surfaces, and the 3 bars at
the measured geometry. Wall reflectance is a **fitted parameter** with `source_kind = fitted`, bounded to a
physically sensible range, with the fitted value and its interval reported. Static objects belong in
`fsp_extensions.py` where that machinery already exists.

**L2. Virtual sensors** at the 46 measured points, horizontal, upward-facing, at the two plane heights, with the
same ray budget discipline as the rest of P2 (declare it). The rim plane is an **empty scene** — no plants.

**L3. Fit on one plane, predict the other.** Free parameters: lamp flux, wall reflectance, and (if you must) a
lamp position offset — **no more than three**. Fit on the rim plane only. Then **predict the canopy plane and
report the held-out error**. A model fitted to both planes proves nothing; the held-out number is the result.
Report RMS and bias in % of the mean, per plane, per orientation variant.

**L4. Cross-check against the chat-side analytic fit** in `derived_summary_20261013.json`: 3 bars as finite line
sources at 23 cm gave RMS 16.5 % and ran to the search bounds; adding a uniform diffuse term gave RMS 5.7 % with
diffuse ≈ 112 µmol ≈ 60 % of the mean. Your scene computes the diffuse component from real geometry instead of
fitting a constant, so report **what fraction of the rim-plane irradiance arrives after at least one bounce**.
If that fraction is far from ~60 %, say so plainly — it means the enclosure model or the lamp beam is wrong.

**L5. Spectrum.** Decide and state whether the solver runs per band (R/G/B) or PAR-total. Per-band needs per-band
leaf optical properties; if those are not reviewed, run PAR-total, record the measured band fractions as scene
metadata, and mark per-band `unavailable` rather than inventing coefficients.

**L6. The shaded point is a sanity bound, not a validation.** 31.8 / 153.5 = 20.7 % reaching under a leaf, but the
real leaf arrangement at that moment is not reconstructed, so the model cannot be scored against it. Use it only
to check the model is not absurd (e.g. predicting 2 % or 60 % under a canopy), and label it that way.

**L7. Deliver a usable reference.** Once the held-out error is known, publish per-position PPFD/DLI at the rim
plane for the tray area so `reference_dli.py` can stop using an assumed reference, and state the uncertainty that
now rides on it. Update the pending-decisions register: which assumed-PPFD rows this closes, which stay open.

## 4. Acceptance
1. Held-out canopy-plane RMS and bias reported for both orientation variants, with the fitted parameters.
2. Bounce fraction at the rim plane reported and compared with the ~60 % analytic estimate.
3. An enclosure-free run reported alongside, to show how much the walls actually changed the answer.
4. Warm-up bias stated as a direction on the canopy comparison, with no correction applied.
5. Nothing written into `data/records/`; no `measured` label on any model output.
6. Existing P2/integration tests pass (report counts).

## 4b. Known backend limits from the eight-capability work — do not fight them
`handoff/CODEX_FSP_EIGHT_CAPABILITIES_EXECUTION_2026-10-11.md` already records what the native backend can and
cannot do. Read it before designing the acceptance, and reuse E2–E4 rather than rebuilding them.

1. **E4 is implemented and its only stated limit was "actual pot/shelf/non-target geometry still needs inputs".
   Those inputs arrived today** (`data/records/env_20261013/shelf_geometry_20261013.json`): board 60 × 40 cm,
   3 trays 14 × 28 × 7 cm, pots 60 mm across the flats × 70 mm deep, 3 lamp bars 5 cm apart 30 cm above the board,
   white enclosure. Instantiate the enclosure through the existing E4 scene-object table — new machinery is not needed.
   The other-variety plants in the same cabinet are a legitimate E4 non-target object (they shade, they do not grow);
   their geometry is still unmeasured, so declare them `unavailable` rather than inventing dimensions.
2. **E2 cannot close the photon budget.** Terminal escape / cutoff / estimator-residual categories are recorded as
   unavailable, and that report explicitly refuses to fabricate a remainder. So report the **bounce fraction** as
   first-hit versus post-reflection arrivals at the sensor plane, and state the unclosed remainder as `unavailable`.
   Do **not** manufacture a closure to compare against the ~60 % analytic diffuse estimate; compare what the tallies
   actually support and say what is missing.
3. **E3 is grey and monochromatic**, and E2 converts to watts at an assumed **550 nm**. Today's measurement gives the
   real band split (R 41.9 / G 41.6 / B 16.5 %), so that assumption is now knowably wrong — but fixing it is a
   separate spectral-calibration task. For this task: keep the declared monochromatic basis, record the measured band
   fractions as scene metadata, and **state plainly that any fitted wall reflectance absorbs the spectral error**.
   A reflectance fitted under a wrong spectral basis is an effective number, not a material property; name it
   `effective_reflectance_grey` so nobody later reads it as measured optics.
4. The nonblack-optics path for P4 growth stays blocked on the NRH fit-basis decision. This task is light-field
   calibration only; it must not enable nonblack growth as a side effect.

## 4c. Code-level findings that change this task (verified 2026-10-13)
From `handoff/FLOW_P2_LAMP_APPLICATION_REVIEW_2026-10-13.md`, re-verified against the sources. Treat these as part
of the work order.

1. **The existing fitter cannot do this fit.** `tools/ppfd_validation.py fit_empty_rig` enables only
   `photon_flux_scale` and `half_intensity_half_angle_deg`, its backend is "python direct light … no reflections",
   and it returns `blocked_reflective_rig_not_in_fit_backend` as soon as any rig surface has reflectance or
   transmittance above zero. So the wall-reflectance fit in §3 **must run through the native path**, and the direct
   solver stays as a control. Do not widen `fit_empty_rig` to smuggle reflections into a solver that has none, and do
   not quietly keep beam angle as a fourth free parameter — the three-parameter limit in §3 is the limit.
2. **Native fitting is expensive — stage it.** Each native evaluation is a GroIMP run. Do a coarse-ray search first,
   then re-run only the selected parameter set at the declared 4.8M rays, and report both. State the ray count beside
   every fitted number; a parameter fitted at low rays and reported beside a 4.8M validation must say so.
3. **The held-out canopy comparison is conditional, not definitive.** All 16 canopy points have `x/y = unavailable`
   and the plants were present and are not reconstructed. Freeze the spatial variants BEFORE looking at the errors,
   report RMS/bias per declared footprint variant, and keep the definitive matched score **`unavailable`**. Never use
   the canopy readings to choose their own footprint, the lamp placement or the grid orientation — that is fitting
   the test set.
   **UPDATED 2026-10-13 — the user stated the extent:** the canopy 4×4 covered the 3-tray block, **42 × 28 cm**,
   inset ≈7 cm from the board edges, so cells are 10.5 × 7 cm. The record's canopy x/y are now `derived` from a
   `user_stated` extent. What remains is only **which corner is (1,1) and which axis carries the 42 cm side** —
   declare those variants up front, report every one, and never select among them by looking at the readings.
   With the extent fixed the held-out comparison becomes a real score per declared variant: publish a definitive
   number only if the variants agree, and otherwise report the spread as the result.
4. **Lamp type matters and the obvious path throws it away.** `tools/groimp_light_scene.py lamps_from_scene` reduces
   directional emitters to isotropic `PointLight` (and blocks absolute validity for that reason); native V3 and
   `fsp_extensions_native.rgg` also emit PointLights. Reuse the directional
   `ppfd_validation.arealight_node` / `lamp_adapter` path within its documented support limits, and verify geometry,
   aim, beam and integrated flux survive the transfer. `groimp_light_scene.py` is Claude Code's file — request a hook
   in LOG rather than editing it.
5. **`reference_dli.py` is not a hard-coded constant to overwrite.** Its measured routes (`logged`, `spot_schedule`)
   work; the `simulated` route deliberately raises `simulation_execution_deferred`. Add a **versioned consumer for a
   frozen calibrated prediction** carrying scene/fit/source hashes, coordinates and frame, uncertainty, time support
   and provenance, and keep measured points distinct from fitted spatial predictions. An interpolated or simulated
   per-position value never becomes `measured`.
6. **Frames: do not apply the 7 cm twice.** The grids are recorded as heights above the board (70 mm and 150 mm)
   while `plant_local_mm` already references the pot rim. Carry explicit board→grow and plant→grow transforms, test
   their alignment, and remember that the tray placement (≈7 cm inset, within 10 cm of the front) is approximate and
   is not a sensor or pot mapping.
7. `absolute_blockers` will still refuse an absolute claim while rig optics and sensor positions are not measured.
   Keep those blockers; produce an explicit **conditional** comparison output instead of erasing them or relabelling
   the `inferred` coordinates as measured to force a score.

## 5. Deliverables
Code + tests under your claims; `handoff/P2_LAMP_CALIBRATION_EXECUTION_2026-10-13.md` (+ `_KO.md`) with commands,
exit codes, the fitted values, the held-out error, and every blocked item with its owner; `flow/flow_map.csv` rows
+ `check_flow.py --md`; LOG claim first, result last. If the held-out error is large, **report it as the result** —
a measured disagreement is the most valuable thing this task can produce.
