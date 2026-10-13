# Review the dwarf tomato growth and carbon equations (review pack 2026-10-04)

I want a scientific review of the growth, development and carbon-diagnostic equations now implemented in my dwarf tomato project. This is review only: do not write code and do not install literature coefficients as defaults.

## Inputs

Primary document (attached; also at the project path below):
`handoff/CLAUDE_GROWTH_EQUATION_REVIEW_PACK_2026-10-04.md`
Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`

If you can read the project, check the pack against the cited source functions before reviewing, and report any mismatch first:
- `tools/probabilistic_compound_growth.py` (`beta_shape`, `normalized_temperature_clock`, `_size_response`, `_draw`, `_decode_block`, `_trajectory`, `_remaining`, `update_forecast`)
- `tools/growth_calibration.py` (`_prediction`, `_event_log_probability`, `_loss`, `apply_parameter_set`)
- `tools/fsp_carbon_diagnostic.py` (`compute_leaf_exchange`, `compute_respiration`, `infer_structural_demand`, `_budget`, `compute_carbon_sufficiency`, `audit_carbon_balance`)
- Evidence: `tools/growth_calibration_evidence.json`, `build/fsp_physiology_spec_20261003_01/` (source/equation/parameter registries; cached Butturini 2026 PDF, Heuvelink thesis, Farquhar 1980)
Do not list the whole OneDrive tree (it timed out last time); open the named files directly. If you cannot read them, say so and work from the attached pack.

## Decisions already made (constraints, do not reopen)

- P3 (growth) is the only owner of realized growth, events and geometry. P4 (carbon) is a read-only diagnostic: it never scales growth, moves organs, rejects trajectories or changes probabilities.
- Frozen calibration packs are applied explicitly before a P3 run; no runtime fitting.
- Existing (age-unknown) organs keep the exponential remaining-increment curve; only newborn organs may use the beta curve. Remaining increment D is kept (no log x_inf reparameterization, no rank law, no scalar vigour factor).
- Temperature enters only the development clock (normalized to 1 at the calibration setpoint). Fixed whole-plant DLI enters only size targets. CO2, RH/VPD, EC, pH have no P3 response.
- Per-trajectory node budget N_max, truss/terminal events with null geometry, post-termination sympodial growth = unavailable.
- No light-direction → leaf-orientation law is adopted.
- Cross-project integration is deferred; first integration target is synthetic conversion correctness.

## Update since the pack was written

K02 is resolved in code (2026-10-04): `apply_parameter_set` now refuses a binding when the fitted role's meaning differs from the engine coordinate's meaning (e.g. fitted increment D in mm → absolute side target in mm), refuses undeclared meanings, and implements no conversion. Review whether the meaning categories are correct and complete; do not re-request the guard.

## What I need

Follow the pack's section 9 response format. In particular:

1. **Per equation group (L01–L02, G01–G08, C01–C06, K01–K02):** retain / revise / unresolved, exact equation and unit changes, source equation/table/page/version, required parameter evidence and domain, required observations, affected function and acceptance check. Distinguish "faithful transcription of a source" from "appropriate for my target dwarf cultivar".
2. **Resolve first (priority 1 in the pack):** the semantics that decide whether quantities can be combined at all:
   - L01: what DLI P3 should receive (incident vs absorbed; tissue-supported vs whole-plant; spatial reduction; full-day rule; basis_id).
   - C01: whether the NRH curve is before-mitochondrial or net exchange, how photorespiration is included, incident vs absorbed PPFD, one-sided area with two-face illumination.
   - C02–C04: respiration ownership, CH2O vs CO2 source units, ASR multiply/divide convention, root/fruit coefficient order, structural vs total dry mass.
3. **Respiratory-accounting table** assigning leaf exchange, leaf/stem/root/reproductive maintenance and growth respiration exactly once.
4. **Specific issues to judge:**
   - G03: beta re-anchoring keeps the original absolute asymptote after an observation shift — intended or not?
   - G04: the DLI multiplier acts on a remaining increment (existing organs) but on an absolute maximum (newborn beta); is that consistent, and how should low-DLI targets below birth size be handled?
   - G02: common absolute side target with possible narrowing — biologically and geometrically sound?
   - C02: RGR5 = 0 gives zero maintenance — acceptable or does it need a basal term (with evidence)?
   - C05: no reserve propagation between intervals — how should independent intervals be labelled so results are not read as a conserved trajectory?
   - G07: what observable a "truss event" should mean (visible bud, anthesis, fruit set).
5. **Parameter ledger** (measured / fitted / literature candidate / explicit assumption / unavailable) with cultivar, stage, environment and source locator; which parameters are jointly unidentifiable with current data (mostly single-time photos of 4+3 plants; no repeated captures, dry mass or gas exchange yet).
6. **Smallest defensible equation set for current data**, and a separate list of extensions that would need a new user decision (e.g. phototropism, FvCB/CO2, senescence, reserve propagation, sympodial growth).
7. **Checks**: software checks (units, boundaries, carbon/mass conservation, unavailable behaviour) separately from biological evaluation (held-out plants, times, treatments).

## Output

- First response: the per-group table, the respiratory-accounting table, and at most 3 decisions I must make first. Keep the rest for follow-ups.
- Label every statement **verified source fact**, **design proposal**, or **open assumption**. Do not present coefficients from sources you could not open as verified.
- After we agree, write only the agreed items as an English implementation handoff for Codex with file/function/input/output/unit references; leave unresolved items unresolved.
