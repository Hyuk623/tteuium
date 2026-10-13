# P4 growth Science execution

Date: 2026-10-04. Status: implementation started; outcomes appended below.

## Brief

Implement the authorized P4 prompt F1/F4/F5/F6/F10. Inspected the current runtime including export/CLI, tests, schema, guide, implementation handoff, Science review and prompt ownership. Current single-interval implementation has no table validator; RGR5 reads organ-local history; multiple inverses select the first; the hypothetical ledger has no originating-diagnostic association. Negative-budget status already exists and must be preserved.

Add explicit independent-interval metadata and a public table validation/export entry point; require complete plant-scoped RGR5 evidence, flag zero activity and reject floating saturation; select explicitly named inverse when multiple inverses exist; verify ledger pack and quantities against an originating diagnostic. Create a new equation registry with source snapshots and implementation/biological status separated. Inspect cached primary sources for the three source questions.

Only P4 runtime/schema/tests/guide and new build evidence are edited. P3/calibration remain read-only. No coefficient adoption, fitting, integration, reserve propagation or geometry feedback. Q2 stays undecided; Q1/Q3 remain P3-owned. Tests will cover guard failures, existing accounting regression, actual JSON/CSV and CLI exports. Historical registries and evidence are preserved.

## Final outcome: completed software safety

F1/F4/F5/F6/F10 are implemented and verified. This supersedes the earlier P4 implementation delivery for current code/schema hashes; historical reports, tests and registries remain unchanged. Scientific acceptance is separate and still false in every result. Q2 remains undecided.

| Item | Implemented behavior and precise location | Verification |
|---|---|---|
| F1 | `build/p4_growth_science_20261004_01/equation_registry_v2.json` maps all 28 historical equations: 11 implemented, 8 partial, 9 deferred. Each row has exact function/file/line range and a frozen source hash; partial formulae have implemented=false. NRH uses the stable nonnegative-term discriminant. | Historical registry hash unchanged; all function locators and snapshots verified. P3 normalized-clock/beta counterparts are identified without claiming a P4 mass-growth engine. |
| F4 | `tools/fsp_carbon_diagnostic.py::compute_carbon_sufficiency` adds reserve_propagation=none, interval_independence=independent_single_interval and reserve_reuse_assumption. `validate_diagnostic_table`, `export_diagnostic_table` and CLI `validate-table` compare contiguous supplied intervals. | Unordered contiguous equal-reserve rows without later-row assumption fail. Other plants/trajectories/draws/boundaries and noncontiguous intervals do not spuriously fail. Run labels cannot bypass the guard. Valid assumptions survive actual CSV/JSON. U<0 remains maintenance_deficit with null growth budget/ratio/deficit. |
| F5 | `compute_respiration` requires organ parameter rgr5_scope=plant and separate carbon_state.plant_rgr5_history with complete plant coverage, identity, structural mass basis, positive endpoint masses, source and dated five-day span. | Per-organ history is not used as plant history. Missing/wrong scope, incomplete coverage, wrong identity/date and negative growth are unavailable. Activity [0,1) enforced; floating saturation at 1 is unavailable. Zero activity is flagged. Constant mode remains valid without RGR5. |
| F6 | `infer_structural_demand` requires unique inverse_id and primary_inverse when multiple inverses are supplied. Component rows preserve the selected primary. | Agreeing inverses without primary fail; second inverse can be selected even when numerically distinct within tolerance; disagreement beyond tolerance fails. No averaging. |
| F10 | `audit_carbon_balance(ledger, originating_diagnostic)` uses `_verify_originating_diagnostic` to recompute retained C04 inputs, verify the result and require matching pack_id and originating amounts. | Missing/wrong pack, missing origin, changed amounts and tampered origin rejected/unavailable. Correctly associated hypothetical ledger balances. Echoed ID alone is insufficient. |

The table comparison key is plant, trajectory, parameter draw/pack and accounting boundary (scope, subset membership and boundary policy). Whole-plant organ inventory may evolve without changing its boundary. The validator sees only rows supplied to it; single-row calls cannot detect unseen history. Different reserve values are not proof of dynamic stock consistency. No reserve engine or next reserve state exists.

RGR5 is a supplied whole-plant structural-DM history, not a sum inferred from an incomplete inventory. Its activity is held over each declared validity interval and aligned with organ-mass/environment boundaries. `mass_at_now` equals the activity record start; the other endpoint is exactly five elapsed days earlier. The provider remains responsible for real evidence authenticity. Fields and units are specified in `tools/FSP_CARBON_DIAGNOSTIC.md`: structural mass g DM, carbon g C, activity dimensionless, activity_f days, five-day RGR per day; maintenance remains explicitly g CH2O/g structural DM/day. No basal floor, new activity law or biological number was adopted.

The input schema remains p4-carbon-diagnostic-2 with a dated safety revision. Required output metadata and optional-path evidence are stricter. Historical result objects must be regenerated for new export validation; historical archives must not be edited. Legacy unassociated ledgers and ambiguous RGR5/multiple-inverse inputs intentionally no longer pass. New schema and CSV fields are documented and exercised.

## Executed tests and evidence

- `tools/tests/test_fsp_carbon_diagnostic.py` and `tools/tests/test_fsp_growth_science.py`: **105 passed**; JUnit `build/p4_growth_science_20261004_01/tests_final.xml`.
- `build/p4_growth_science_20261004_01/delivery/`: **12 actual CLI executions**, 10 explicitly synthetic cases, one expected table rejection and one accepted two-row table. Includes signed night exchange, maintenance deficit, zero/saturated RGR5, absent/selected primary, unreviewed pack and balance association.
- `build/p4_growth_science_20261004_01/verification.json`: **256 checks passed**, including saved artifact hashes, historical registry preservation, exact function locators and CSV/JSON association.
- Existing regression coverage preserves exclusive maintenance ownership, growth cost already included in ASR, negative night supply, unavailable components, source hashes and immutable P3 inputs. No P3 model was executed or imported.
- `source_snapshot.json` and `source_snapshot/` freeze the exact inspected source. P3 is concurrently changing under its own owner: its execution handoff remains a planned/in-progress brief at inspection. This is a snapshot, not a final synchronized P3 mapping; refresh when its owner completes. P4 did not edit P3 or calibration.

Run from project root:

```powershell
python -X utf8 -m pytest tools/tests/test_fsp_carbon_diagnostic.py tools/tests/test_fsp_growth_science.py -q
python -X utf8 build/p4_growth_science_20261004_01/verify_delivery.py
```

The delivery generator intentionally requires a fresh output directory. It is preserved with the evidence for inspection, not for overwriting the delivered package. Old P4 verifiers pin historical code and must not be used as current-code acceptance after this revision.

## Primary-source answers (evidence, not policy selection)

Exact locators, original URLs, pinned commit, cached access/retrieval status and content hashes are in `build/p4_growth_science_20261004_01/source_checks.json`.

1. **NRH empirical fit: unresolved.** Butturini p6 eq5 and p7 eq8-10 use the NRH before downstream maintenance. The p10 fitting description does not establish whether measured net exchange was corrected for respiration before fitting. Pinned photosynthesis.rgg implements NRH without Rd; this and H(0)=0 establish the model algebra, not the empirical fitting convention. CSV lines105-107 label ASAT an educated assumption and alpha/convexity as mid/highest-rank data, differing from the paper's rank-3 methods description. No fitting script or raw light-response measurements was identified in the complete 37-entry repository tree at commit 2d727a3364f87392b3f8b74d8ff7127cc5090c3a. Original fitting preprocessing or author clarification is still needed.
2. **Maintenance units: conflicting.** Butturini p5 Table1/p7 eq7 and Heuvelink thesis PDF p114 (printed p109, Table1) specify CH2O equivalents. The pinned dynamic parameter CSV lines93-96 labels the same numbers CO2. Visual table inspection confirmed the units. Conversion is 12.011/30.026 gC/gCH2O versus 12.011/44.009 gC/gCO2; equal numeric rates differ by about 1.466. The source implementation also mixes structural-plus-minimum-pool versus total-mass conventions. No coefficient correction or mass-basis adoption follows from this conflict.
3. **Recorded measurement conditions: verified, with light-basis limit.** Butturini p10 reports three plants, mature fully expanded rank-3 leaf at six weeks, approximately 23 C cuvette temperature, 798 microbar CO2 partial pressure, 50:50 red:blue illumination and cuvette light steps 0-2000 umol/m2/s. These are applied-light setpoints; their interpretation as incident measurement light does not establish the coefficient preprocessing/basis, while eq5 explicitly calls I absorbed PAR. Cuvette temperature is not asserted to be measured leaf temperature; 798 microbar is not silently converted to ppm. The full cultivar name appears on p9. None of this establishes target-cultivar applicability.

Primary materials: cached [Butturini full text](../build/growth_calibration_20261003_01/dwarf_fsp_source.pdf), [Heuvelink thesis](../build/fsp_physiology_spec_20261003_01/sources/heuvelink_thesis.pdf), and the pinned official repository files listed in source_checks.json. Web-reader access to the publisher redirect failed; the already cached full text was inspected. GitHub's complete pinned tree was retrieved through its official API and saved; no secondary paraphrase substituted for primary evidence.

## Remaining decisions and limits

Q2 remains undecided: before_mito versus net_leaf, adopted PPFD basis and illumination-face policy were not selected. Both existing explicit respiration modes remain; unknown evidence remains unavailable. Accepted Q1/Q3 are P3-owned. Optional reanchor weighting, posture correction and truss observables remain unadopted. Source findings do not supply missing root/reproductive masses, reserves or target allometry. No borrowed temperature, root fraction or ASR became a default. No fitting, training, cross-project adapters, whole-system integration or physiological feedback was performed.

## Final file hashes

| File | SHA256 |
|---|---|
| tools/fsp_carbon_diagnostic.py | eb7d02df906c0bbdf95b10eeefac0ece37348f4be61be5c64d244a2fd5a7d02a |
| tools/fsp_carbon_diagnostic_schema.json | be5a7da8999585db8ca986b9a210b3d60155fe2b7cf6fadcf6c5ffc202f028e8 |
| tools/FSP_CARBON_DIAGNOSTIC.md | cc7ef5a6ef94d7c63f5dc1e124af985c6a990fc8cd997196a3dc61cb515bb8e5 |
| tools/tests/test_fsp_carbon_diagnostic.py | 852daa90e68dd93f6dfaaff22c0576fee35b041e5ca65a2ac1411d1fcf0f7fb7 |
| tools/tests/test_fsp_growth_science.py | b440d158f7eae44f7c9ac082d325a61d2f56fb14542fae027c187d1126a1c402 |
| build/p4_growth_science_20261004_01/equation_registry_v2.json | 984ba8d8d221dd3b26a6201d3b70e6aa4f1ff9674fa3f86dfc5ece65b382ad8e |
| build/p4_growth_science_20261004_01/source_checks.json | acb70a23dbc6dbe966b76d191762efc5c37719bad29df804adad8d50bee12888 |
| build/p4_growth_science_20261004_01/tests_final.xml | bfbdac5e222b05c043b138f733bb95b5d93a947d08c65cbd16aa012382b5470a |
| build/p4_growth_science_20261004_01/verification.json | 3a833a666cf942cbf1045007cb465a2d2485c897c1da444fe001de6ae6538942 |
