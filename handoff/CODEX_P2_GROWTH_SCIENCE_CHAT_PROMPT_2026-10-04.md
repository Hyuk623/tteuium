# P2 prompt for reference DLI and light provenance

Recipient: existing P2 light simulator chat. Date: 2026-10-04.

Apply the accepted light-input clarification from the growth Science review within P2's existing interface and validation. Preserve delivered directional transport. Do not build a P3/P4 adapter or a new physiological response model.

## Read first

Read the repository rules, LOG tail and TODO, then:

- [Science review](CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md), L01/L02 and section 4.
- [User decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), including the new growth Science addendum.
- [Prompt ownership](CODEX_GROWTH_SCIENCE_CHAT_PROMPTS_INDEX_2026-10-04.md).
- [P2 delivery](CODEX_P2_DIRECTIONAL_DELIVERY_2026-10-04.md).
- [Light interface](../tools/LIGHT_GROWTH_BRIDGE.md), [directional contract](../tools/DIRECT_ANGULAR_CONTRACT.md), current exporter/schema and independent consumer.

## User decisions

Question 1 is adopted: P3 uses **incident** DLI, in mol photon m-2 day-1, at **one declared reference position and sensor plane**, integrated over a **complete local day**, with whole-plant model scope and a declared applicability interval. The reference basis must not equal a P2 tissue `area_basis_id`. Whole-plant scope describes where P3 applies the value; it does not mean average light over plant surfaces.

Question 3 is adopted: P3 owns separate c_DLI declarations by growth_curve; P2 supplies light and provenance, not growth coefficients. Question 2 remains undecided: do not enforce incident/before_mito/adaxial-only as a P4 policy or change current physical transport to match that unselected package. Optional G03/G06/G07 proposals remain unadopted.

## Work

1. Write a brief and inspect current `integrate_light_schedule`, `export_spatial_light`, `export_compound_light_features`, `build_package`, schema and consumer. Reuse existing functionality; add only missing validation/metadata within P2 ownership.
2. Document reference DLI separately from leaf/tissue PPFD, incident/absorbed flux, dose and area bases. If the current P2 package has no supported reference-position record, report it explicitly and define the required input fields in the handoff. Do not fabricate a sensor, derive reference DLI from tissue means, or add a new sampling subsystem under this clarification.
3. For an existing supported reference channel, preserve position, plane orientation, coordinate frame, timezone/local-day interval, coverage status, source evidence and basis ID. Enforce `DLI=1e-6*sum(PPFD*seconds)` only for complete coverage. Missing light/time intervals remain unavailable rather than zero. Do not choose an actual reference position or numeric applicability bounds without evidence; P3 enforces its declared model interval.
4. Preserve L02 moment meanings and the receiver-to-emitter direction convention. Light direction is not plant growth direction. Document that P3 must reject binding these outputs directly as orientation parameters; P3 owns the binding guard.
5. Preserve per-instance IDs, full canopy occlusion context, source hashes and area/flux distinctions when splitting existing canopy packages. No isolated re-trace may replace a canopy-preserving split without an explicitly different result scope.
6. Keep source data usable for future P4 review: simultaneous fixture contributions belong at the same patch/time and are summed before nonlinear leaf exchange; do not sum per-fixture photosynthesis, apply absorptance twice or impose the undecided face policy.

The real lamp draft already records three REF-30-40 fixtures operating 16 hours/day at 100%. Preserve those facts. PPF, actual clock windows and other missing physical inputs remain missing; do not convert lumens to an adopted PPF or invent a clock schedule.

## Validation and delivery

Use focused synthetic checks for any changed semantics: complete-day integration, incomplete coverage, reference-versus-tissue basis rejection at the interface that owns it, units, unknown versus zero, and canopy-preserving splits if affected. Keep existing scalar/angular parity. Run core and tools suites separately if their conftest imports conflict. If the existing code already satisfies an item, cite it and avoid redundant changes.

Save `handoff/CODEX_P2_GROWTH_SCIENCE_EXECUTION_2026-10-04.md`: implemented versus documented items, exact fields/units/producers, tests and fresh hashes, unsupported reference-channel needs and unresolved physical evidence. No real accuracy claim follows from synthetic checks. Append LOG/TODO. Do not edit P3/calibration/P4 files or start cross-project linking, fitting or phototropism work.
