# Technical fix review of the four-project growth deliveries (2026-10-04)

I need a technical review that lists what must still be changed in my dwarf tomato project, based on Codex's delivery summary. Review only: do not write code and do not install literature coefficients.

## Inputs

Primary document (attached; also in the project):
`handoff/CODEX_FOUR_PROJECT_GROWTH_SCIENCE_SUMMARY_2026-10-04.md`
Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`
Do not list the whole OneDrive tree; open named files directly. If you cannot read a file, say so and do not make claims about it.

Read as needed:
- Delivery reports: `handoff/CODEX_P1_GROWTH_SCIENCE_READINESS_2026-10-04.md`, `CODEX_P2_GROWTH_SCIENCE_EXECUTION_2026-10-04.md`, `CODEX_P3_GROWTH_SCIENCE_EXECUTION_2026-10-04.md`, `CODEX_P4_GROWTH_SCIENCE_EXECUTION_2026-10-04.md` (final-outcome sections)
- Decisions: `handoff/CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` sections 7–9 (D8–D18)
- Pending implementation: `handoff/CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md`, `handoff/CODEX_REFERENCE_DLI_CHANNEL_HANDOFF_2026-10-04.md`
- Evidence: `build/p4_growth_science_20261004_01/source_checks.json`, the new versioned equation registry, `build/fsp_physiology_spec_20261003_01/sources/` (dwarf model RGG/CSV, Butturini PDF, Heuvelink thesis), `build/four_project_growth_science_review_20261004_01/review_evidence.json`
- Code: `tools/probabilistic_compound_growth.py`, `tools/growth_calibration.py`, `tools/fsp_carbon_diagnostic.py`, `tools/light_growth_bridge.py`

## Known conflicts to resolve first

The delivery summary and my recorded decisions disagree. Check each against the sources and code and tell me which is correct and what must change:

1. **Question 2 status.** Summary says "still undecided". Decisions D15–D18 (2026-10-04 17:41) record: P4 `light_basis='absorbed'` with `measured_light_basis` mismatch issue; `before_mito` only (net_leaf needs a non-dwarf Rd source); `illuminated_faces='both'` unavailable; `rgr5_scope='plant'`. My check found none of these (e.g. `alpha_calibration_basis_conflict`, `two_sided_exchange_unavailable`, `net_leaf_requires_rd_bearing_source`, SLA `m2/mg` guard) in the code yet; v2 handoff is pending. Confirm the gap and whether D15–D18 are technically sound.
2. **Maintenance units.** D17 says source MAINT is g CH2O g⁻¹ DM_str d⁻¹ (Butturini eq 7 p.7) and the current 12.011/30.026 factor is correct. P4's source check says the pinned parameter CSV labels the same numbers as CO2 (≈1.466× carbon difference). Determine which unit the dwarf model's code actually applies to those numbers (read the RGG where the rate is used), whether the CSV label is a comment error, and what the project should record. Do not tell me to rescale coefficients without that evidence.
3. **NRH fit convention.** Model algebra is before-maintenance (eq 5, eq 8, `Thornley.calc()` with no Rd). Open question: were the measured net exchange data corrected to before-mito before fitting α/Pmax/θ? If original preprocessing is not available, state what the project must label and what bias direction an uncorrected net fit implies.
4. **Opt-in fields.** Summary says reanchor weight, transient posture and truss observable are "unadopted". D14 approved them as opt-in (defaults preserve current behaviour). Confirm whether they belong in the pending v2 work or should stay out, with reasons.
5. **Registry metadata.** P4 registry carries `P3_in_progress_pending_final_refresh`; summary says code references match current source. Confirm the required metadata fix only.

## Technical review requested

For each project (P1 3D/observation, P2 light, P3 growth, P4 carbon) and for cross-project interfaces, list what must be modified. Cover at least:

- **P3:** conditional quantiles (now report coverage of the original ensemble) — is that the right semantics or should summaries be split differently; ordered ESS stages (prior, after geometry, after events) — any misleading interpretation; width asymptote `w0 + f_DLI·(target − w0)` naming; sub-base zero knot; strict reference-DLI input rejecting older configs — migration handling.
- **P2:** reference-DLI channel absent (handoff pending; PPFD meter arrives ~2026-10-10). Review the pending handoff design (logged route, spot × schedule route, simulated route blocked on PPF) for technical gaps: timezone/midnight, trapezoid vs step integration, ambient light, sensor cosine response, position tolerance, applicability interval, multiple plants sharing one reference.
- **P4:** single-interval independence and identical-reserve validator (only sees supplied rows) — sufficient?; RGR5 plant-history requirement; primary inverse; pack association in balance audit; disclosure fields still missing from v2 A7.
- **P1:** what minimum evidence makes real tissue area and persistent organ identity acceptable (scale, pose, timestamp, association bound to partition hash); which P1 outputs must never feed P2/P3.
- **Interfaces:** `mol/m2/day` vs `mol/m2/d` spelling mapping, tissue DLI vs reference DLI separation, P2→P4 two-face output vs adaxial-only policy, schema version vs content hash pinning, regeneration instead of editing archives.

## Output format

1. Conflict table (items 1–5): which document is correct, evidence locator, required change, owner.
2. Per-project fix list:

| ID | Project | Severity (blocker / correctness / safety / clarity) | Problem | Evidence (file:function/line or source page) | Required change | Acceptance test | Needs user decision? |
|---|---|---|---|---|---|---|---|

3. Items that are correct as delivered and should not be changed.
4. At most 3 decisions I must make before the next Codex round.

Label statements **verified source fact**, **design proposal**, or **open assumption**. Keep software correctness separate from biological accuracy. After we agree, the agreed items will be written as an English Codex handoff with file/function/unit references.
