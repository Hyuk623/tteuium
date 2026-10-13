# Observed plant to growth scaffold connection

User authorization: correct the integration gaps identified in the preceding review.

Implementation scope:
- Add an observed initial-state adapter to the existing growth simulator. Preserve plant/session/date, explicit compound IDs, reference counts, diagnostic traits and input hashes. Counts alone never create leaflet meshes or positions.
- Accept explicit state-aware transition callbacks for future models. Do not silently apply the synthetic five-leaflet topology to observed plants. Without a transition model, export the observed initial frame with an explicit pending status.
- Match trait measurement/light rows by plant, date and optional session, reporting missing or ambiguous joins. Preserve the single undated legacy case only when unambiguous. Keep all dates of a held-out plant together in calibration diagnostics.
- Separate calibration diagnostics from metric validation. Retain the legacy intercepted-light field as an explicitly labelled projected-area proxy; absorbed photons and photosynthesis remain unavailable.
- Preserve existing demo behavior. Add regression tests for dated joins, missing values, identity/state preservation and safe exports.

No training, heavy inference, GroIMP light run, biological coefficient fitting or source-data edits. Missing environmental measurements are not imputed. Existing elevation-regrouped results remain separate; capture geometry is not recalculated by this work. New growth laws and accuracy acceptance criteria still require the design agent's specification.

## User steering and delivered scope

The user subsequently requested the plant 3D to light-simulation connection **before** growth-simulator integration, plus a Claude coding prompt. Consequently, observed-state initialization and state-aware growth callbacks above are deferred, not implemented. `growth_simulator.py` remains unchanged.

Implemented in `tools/plant_traits.py`:
- Date/session-aware measurement joins with explicit match status. Different dates do not overwrite each other. Ambiguous duplicates and session joins fail explicitly. Single undated legacy observations remain compatible; undated records do not substitute for dated observations.
- New S8 traits preserve capture metadata when provided. Missing dates stay missing; dates are not guessed from filenames or session IDs.
- All dates of a held-out plant are excluded together in calibration diagnostics. Report unique plants separately from observations.
- Calibration error availability no longer sets `validated_metric=true`. No new accuracy threshold was invented.
- `intercepted_mmol_d` is retained for compatibility but labelled projected-area interception proxy, not absorption. Absorbed photons and photosynthesis stay null. Missing photoperiod stays null; invalid numerical inputs are rejected. An observed zero top-area is not replaced by hull area.

Validation: `python -X utf8 -m pytest tools/tests/test_plant_traits.py tools/tests/test_growth_simulator.py -q` — 35 passed. These verify software contracts, not biological accuracy. Sources, historical build outputs and human measurements were not modified.

Follow-up prompt: `handoff/CLAUDE_PLANT_3D_LIGHT_CONNECTION_PROMPT_2026-10-03.md`. Elevation regrouping, source-date enrichment of legacy runs, moving-plant handling and biological models remain follow-up work. The adapter must report unavailable date/session links rather than silently consuming old unscoped summaries.

Real-data smoke check: existing T1/T2/T3 trait JSONs read without inference or recomputation; fresh output at build/trait_join_smoke_20261003_130655. Three plants/observations exported, metric validation false, absorption/photosynthesis unavailable, all three source hashes unchanged. Historical view grouping was intentionally not promoted to a newly corrected geometry result.
