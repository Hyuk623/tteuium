# Codex — P2: use the measured light field directly; stop fitting the lamp and the walls (2026-10-13)

Implementer: **Codex**. Replaces the fitting goal of `CODEX_CLI_PROMPT_P2_LAMP_CALIBRATION_2026-10-13.md`; the code
that task delivered is **kept and reused** (native scene objects, the paired-seed reflection estimator, the frozen
export package, the versioned `reference_dli` consumer, the conditional-comparison outputs). What is dropped is the
attempt to fit wall reflectance and lamp parameters.

## 1. User decision (2026-10-13) and the evidence behind it
**Skip the wall reflectance. No wall-covering measurement. Do not fit the lamp.** Two independent results say the
fit cannot work with the data that exists:
- Your synthetic check: truth reflectance **0.4**, the fit chose **0.8 at the upper bound** while calibration RMS was
  **1.11 %** and the held-out point **1.86 %**. A good RMS was not evidence about the parameter.
- The chat-side analytic check with the lamp **fixed at its real geometry** (3 bars, 50 cm emitting length, 5 cm
  apart, 30 cm above the board to the emitting surface) and only [flux, diffuse] free: rim-plane RMS 9–19 % and the
  canopy plane underpredicted by **20–58 %** in every lamp-position variant tried.

The reason is structural: about **60 % of the light arrives after reflection** from a white ceiling that sits right
beside the lamp, so the reflected part **grows with height** and a height-independent diffuse constant cannot
represent it. Reflection is the dominant term, not scene furniture.

## 2. What to build instead — `empirical_light_field`
**E1. Interpolate the measurement, do not simulate the room.** Build an incident-irradiance field over the tray
volume from the 46 measured points in `data/records/env_20261013/ppfd_grid_20261013.csv`: the rim plane (7 cm, 30
points over the 60 × 40 cm board) and the canopy plane (15 cm, 16 points over the 42 × 28 cm tray block). State the
interpolation method. **Refuse extrapolation**: outside the measured footprint, and above 15 cm, the field is
`unavailable` — plants already reach about that height, so this limit will bite and must fail loudly rather than
quietly extend a surface.

**E2. Direction is not measured — carry it as a scenario set, never as a fitted truth.** A horizontal sensor gives
plane irradiance, not where the light comes from, and a tilted leaf intercepts differently. Declare the direct
fraction from the bar geometry and the remainder as a diffuse dome, and run the per-leaf interception under a
declared set (e.g. diffuse 0.5 / 0.6 / 0.7, `user_assumed`), reporting the spread per leaf. One forecast per value,
reported side by side, never pooled — the same rule as `SUBSTEM_SINK_SCALE`.

**E3. The engine computes canopy self-shading only.** No wall surfaces in the prediction path, no lamp fitting. The
`effective_reflectance_grey` work stays in the repository as a record; it must not feed any published number.

**E4. Bind the field to this exact configuration, mechanically.** Hash the board, tray block, lamp position, height,
emitting length and spacing, and the enclosure description into the field package. If any of them changes, the field
is **invalid** and consumers refuse it — a new configuration requires new measurements, never extrapolation. Make
this a test, in the style of the `reuse_as_prediction = forbidden` enforcement.

**E5. Feed `reference_dli` through the consumer you already built.** Per-position DLI comes from the measured field
with the declared lighting hours. Label every value `empirical_light_field`; an interpolated point is `derived`,
never `measured`, and never `simulated`.

**E6. Write down what this costs.** With no lamp model, **"what happens if the lamp moves" can no longer be
answered by prediction** — it becomes a re-measurement experiment. Record that in the pending-decisions register as
an accepted consequence of the 2026-10-13 decision, not as an open task.

## 3. Acceptance
Extrapolation above 15 cm or outside the tray block is refused (tested); the configuration hash invalidates the
field when any geometry field changes (tested); per-leaf interception is reported for every declared direction
split with its spread; no published number depends on a fitted reflectance; `reference_dli` yields per-position DLI
with provenance; existing P2/DLI/integration suites pass with counts.

## 4. Deliverables
Code + tests, `handoff/P2_EMPIRICAL_LIGHT_FIELD_EXECUTION_2026-10-13.md` (+ `_KO.md`), the field package under
`build/`, pending-decisions update, flow rows + `check_flow.py --md`, LOG claim first and result last.
