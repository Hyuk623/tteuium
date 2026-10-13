# Three-lamp configuration draft

Date: 2026-10-04. Scope: user-confirmed REF-30-40 arrangement only.

## Brief before execution

Prepare a fresh build-only scene draft and readiness report from the supplied 600 x 400 x 400 mm shelf, front-left floor origin, +X right, +Y rear, +Z up. Derive rear-to-front lamp centers using the reported 47 mm width and 50 mm edge gaps. Keep the Y offset; do not recenter. Use the authoritative `fixture_axes` function to verify downward aim and the X-aligned long axis.

Current schema supports provenance-wrapped unknown PPF/emitting dimensions/half-intensity angle, but schedule, cutoff angle, emitter grid and electrical boundary have no unavailable representation. Omit those unresolved required fields in the draft and report the exact validation errors; never use empty schedules, zeros, sample beam settings or `model_construct` to pretend the scene is runnable. No production schema/source changes.

Reported product ratings will use existing `manufacturer_spec` provenance with a source explicitly saying user-reported and independently unverified. Confirmed orientation uses `manual` provenance. Center vectors use `assumed` provenance because they combine derived housing placement with provisional coincident emitting centers/height. Actual emitting length and width remain unavailable; use 517 x 47 mm only in separate reported-envelope/layout metadata. Keep CCT/lumens/lm-per-W/supply/shelf dimensions outside strict scene/fixture objects. PAR_400_700nm names the current schema's sole calculation band, not a measurement inferred from 4000 K.

Validation: check reported-envelope clearances, all three centers, unique IDs, core axes and scalar/vector wrappers; require expected incomplete-scene validation failure without unknown fields; verify artifacts round-trip as JSON and preserve current protected/input hashes. Report numerical-light prerequisites separately from daily operation and PPFD measurement validation. Do not execute light transport, growth, integration, inference or upload work. Existing human configuration and source files remain untouched.

User clarification during preparation: total daily lighting duration is 16 hours. Record that confirmed duration in reference metadata. The user has not confirmed start/end times, whether the duration is one uninterrupted window, or actual photon-output fraction/dimming response. Do not invent a ScheduleSegment or adopt the earlier example times/output.

## Subsequent clarification and final outcome

The user then confirmed **retain 100% output**. Final operating metadata therefore records 16 hours/day and `photon_output_fraction=1.0` as user-confirmed. Clock windows and single-versus-split operation remain unknown, so `schedule` is still omitted instead of fabricating 06:00-22:00. A dimming response is unnecessary for the declared full-output setting; it remains unavailable for possible future dimmed operation.

Final artifacts: `build/lighting_REF_30_40_three_20261004_02/`, including `light_scene.draft.json`, `reference_metadata.json`, `input_readiness.json`, `layout_checks.json`, `ppfd_readings.template.csv`, `verification.json`, a build-only preparation script and README. `_01` is preserved as an earlier incomplete draft: its final verification write failed on a relative-versus-absolute source-path bookkeeping issue. `_02` fixes that path and incorporates the subsequent user confirmation; no simulator source was changed.

Checked all three centers against the user handoff, 50 mm rear/inter-lamp gaps, 97 mm center spacing, 109 mm front clearance, 41.5 mm lateral clearances, depth closure and no Y recentering. Core `fixture_axes` confirms aim [0,0,-1], long axis [1,0,0], width axis [0,-1,0]. Absolute arithmetic/vector tolerance 1e-9, relative tolerance 0. This is reported-envelope plan-view verification; aperture dimensions, physical thickness, mounting and real pose accuracy are not validated.

All populated scalar/vector wrappers validate. Full LightScene validation deliberately reports exactly 16 missing fields: four per fixture (grid, cutoff, electrical boundary and schedule) plus ambient condition, plants, leaf optics and simulation settings. No extra fields were inserted into strict objects, no unknowns became zero, and no examples became operating inputs. PPF, emitting dimensions and half-intensity angle retain supported null/unavailable representations.

Protected core/configuration and the earlier intake hashes were unchanged through preparation. JSON round trips and empty measurement-template header checks passed. No transport, growth, integration, inference, upload or physical-validation claims. Lamp-draft work is fulfilled; a numerical scene still requires the specific inputs listed in `input_readiness.json`. This does not resolve or resume the separate blocked angular-output objective.
