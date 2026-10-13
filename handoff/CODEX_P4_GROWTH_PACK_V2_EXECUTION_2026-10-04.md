# P4 Growth Pack V2 execution

Date: 2026-10-04. Brief before implementation; outcomes appended after validation.

## Scope and current state

Implement P4 A1-A7, F1/S3 refresh, D19/D20, P4-a..f and technical section 3 metadata. Retain the delivered F4/F5/F6/F10 protections. Inspected current runtime including CLI/export/table semantics, schemas, tests and previous source evidence. Q2 is resolved by D15-D18; empirical fitting preprocessing is still unresolved. P3/calibration, P2 transport, human records and historical evidence stay read-only.

The current P4 lacks source-family, measured-basis, face, reserve-lineage and full interpretation disclosures. A shared plant RGR5 history exists, but retained organ-local declarations need consistency checking. Strict SLA units already exist; add a named refusal in that same check. Current DLI audit still spells mol/m2/d. DLI_UNIT is not present in common.py at inspection; the user confirmed P2 will add it and instructed P4 to continue independent work. Do not edit that shared file or define a duplicate.

## Concrete representation

- Source discriminator: explicit source_family in pack/parameter evidence, with reporting values documented separately. Adopt butturini_dwarf, non_dwarf or hypothetical; no substring inference. Parameter evidence can override pack family. Missing provenance blocks the affected physiological path. Synthetic fixtures are explicitly hypothetical and may model a labelled non-dwarf Rd evidence scenario without claiming real coefficients.
- Keep photosynthesis.Pmax as the saturation-role ID; P_sat is an alias to the same parameter, not a second coefficient. Conflicting aliases are malformed. Require measured_light_basis on alpha/Pmax/theta evidence and propagate nonfatal conflicts to every supply flux and top-level CSV/JSON diagnostics.
- Patch biological face declaration plus evidence is mandatory. For multiple fixtures, require explicit contribution-face provenance so opposite surfaces cannot be hidden by a patch label; same-face contributions are summed once before NRH. No P2 adapter or physics change.
- Reserve evidence is carbon_state.reserve_evidence with source_ref and lineage_id. Output chain identity derives from supplied lineage and accounting boundary, independent of run/time. An evidence hash also binds the supplied source and stock observation; missing evidence leaves budget unavailable. Existing table validation compares actual supplied records, never unseen calls or dynamic reserves.
- Reporting fields use undeclared/not_applicable/unsupported statuses when model evidence is absent. Never fill missing physiology with a default. RGR5 source-mass deviation and total-DM caveat are disclosures only; no change in f, mass basis or 0.9 conversion.

Outputs will be saved in fresh build/technical_review_fixes_20261004_01/P4/. Run focused/new plus retained P4 regressions, Windows named compatibility checks when their prerequisites exist, and actual synthetic CLI/CSV/JSON/table exports. Freeze current functions/source hashes in a new registry version, classify P3 association from the actual available report, and preserve previous registries and source checks. No biological fit, coefficient adoption, cross-project run or reserve/growth feedback.

## Verified delivery — 2026-10-04

P4's bounded V2 implementation is complete. This supersedes the earlier Q2-undecided and active maintenance-unit-conflict notes for new model-policy work. Historical source records and registries were preserved. Empirical NRH fitting preprocessing remains unresolved; no target-cultivar validation or four-project integration is claimed.

Changed files: tools/fsp_carbon_diagnostic.py, tools/fsp_carbon_diagnostic_demo.py, tools/fsp_carbon_diagnostic_schema.json, tools/FSP_CARBON_DIAGNOSTIC.md, tools/tests/test_fsp_carbon_diagnostic.py (canonical DLI fixture), and new tools/tests/test_fsp_growth_pack_v2.py. Existing test_fsp_growth_science.py was retained byte-for-byte. P2 published DLI_UNIT during this work; P4 imports it without editing common.py. P3/calibration, docs, config and human observations were not edited by P4.

### Requirement disposition

| Item | Status and implementation | Evidence / failure behavior |
|---|---|---|
| A1 / D16 / P4-b | Done in _net_leaf_evidence and existing _ownership. before_mito remains the dwarf convention; alternate net_leaf needs evidenced non-dwarf Rd_day AND Rd_night. | net_leaf_requires_rd_bearing_source for missing/unsupported evidence; supported synthetic alternate, signed night exchange and single-charge maintenance tested. |
| A2 / D15 / P4-a | Done in _source_family, _saturation_id, _photo_evidence_issues and compute_leaf_exchange. Pack provenance is explicit; individual parameter provenance can override it. Pmax/P_sat refer to the same saturation record. | Missing source/basis gives source_family_undeclared or measured_light_basis_missing. Dwarf pack or NRH source requires absorbed input (dwarf_source_requires_absorbed_light). Mismatch emits alpha_calibration_basis_conflict with parameter ID, role, both bases and source on every supply flux and top-level CSV/JSON; values are unchanged. |
| A3 / D18 / D20 | Done in _face and _combined_face before summation/evaluation. Accept evidenced adaxial_only. Each multiple-fixture contribution must declare its biological face and face_source_ref. | illuminated_faces_undeclared, illuminated_faces_evidence_missing, two_sided_exchange_unavailable, abaxial_exchange_unavailable. Opposite faces unavailable; same-face intensity still math.fsum followed by one NRH evaluation. |
| A4 / D17 | Retained maintenance equation and 12.011/30.026 gC/gCH2O; source-specific Tref check added to compute_respiration. | Evidenced dwarf Tref must be 25 C (dwarf_maintenance_tref_conflict). No global default, coefficient change or 1.466 rescaling. Source Q10=2 recorded only as source metadata. |
| A5 / F5 | Canonical plant_rgr5_history and activity limits already present; _rgr5_consistency now checks retained included-organ/spec/history payloads semantically, including provenance. | rgr5_scope_inconsistent on conflicts; missing scope/history remains unavailable. Constant activity needs no fabricated history. Zero-activity reporting, [0,1) and no basal floor retained. |
| A6 | Existing _parameter SLA unit guard retained with named missing-evidence reason. | sla_unit_incompatible; required m2/g_structural_blade_DM. No m2/mg conversion. |
| A7 / P4-c | Done in _disclosures, compute_carbon_sufficiency, _csv and result semantic validation. | All available, deficit and unavailable exports contain the disclosure set; nested CSV metadata uses JSON. Numeric status/ratio remains unchanged by interpretation notes. |
| D19 | Done in inspect_p3_coupling using P2's DLI_UNIT. | mol/m2/day accepted; mol/m2/d yields legacy_dli_unit_spelling with field/actual/expected for both response unit and applicability-interval unit. No repair or division by 86400. |
| P4-d / F4 | _reserve_provenance and _reserve_boundary require reserve_evidence.source_ref and lineage_id. Existing table guard reused. | reserve_source_missing / reserve_lineage_missing; chain ID stable across separate exports with the same supplied lineage/boundary. Evidence hash changes with stock/source evidence. Table audit exposes both chain IDs and same_reserve_lineage. Changed IDs do not bypass repeated-stock rejection. |
| P4-e | Done as rgr5_mass_basis_deviation_from_source disclosure for borrowed dwarf activity_f meaning. | Source total DM includes roots/buffer; P4 remains structural_dm_excluding_reserve. Exact updateBiomass variable/line locators recorded; f unchanged. |
| P4-f | Done as total_dm_substitute_caveat only for an explicitly supplied assumption. | Source static-branch 90-percent structural / approximately 10-percent buffer note disclosed; no 0.9 multiplication and no newly accepted total-mass input path. |
| F1 / S3 / technical section 3 | New equation_registry_v3.json and source_policy_v2.json; frozen source hashes and exact function lines. | 28 equations: 11 implemented, 8 partial, 9 deferred. Primary model policy resolved, raw fit unresolved; calibration-domain conditions rechecked. |

Pack source_family values are butturini_dwarf, non_dwarf, hypothetical; classification never uses a name substring. Scientific missingness returns structured unavailable through API/CLI/schema paths; malformed representations may raise. The synthetic demo's non-dwarf Rd branch is explicitly assumed evidence for software testing, not an actual measured parameter source. No new biological coefficient values were installed.

### Export and model interpretation contract

Every sufficiency row exposes actual respiration_accounting and light_basis; applicable rgr5_scope; source_buffer_feedback=not_modelled; nonfoliar_assimilation=not_modelled; maintenance_temperature_integration=sub_daily; diagnostic_interpretation=cross_cultivar_consistency_check. Missing declarations report undeclared, constant activity not_applicable, and unsupported/inconsistent RGR5 has declared-scope reasons. Reporting statuses are separate from valid model-input enums. issue_codes and calibration_basis_issues_json preserve nonfatal coefficient conflicts in CSV; every supply flux preserves the same issue objects.

Reserve units remain gC; structural mass is g DM excluding reserve. reserve_provenance_chain_id hashes supplied lineage plus accounting boundary (plant, scope, subset membership and boundary policy), without run/time. reserve_evidence_hash separately binds the source payload, stock_at and reserve_gC. These identify supplied evidence and do not authenticate observations. Independent single calls cannot detect unseen reuse; validate-table operates on supplied rows only. Existing explicit independent-interval metadata, primary inverse selection and originating-demand C04 ledger verification are retained (F4/F6/F10).

Buffer-feedback omission can overpredict supply under sink limitation; it is not a universal validated bias. Sub-daily Q10 differs from daily-mean-temperature evaluation; the cited approximately 0.4-percent example is conditional and is never applied as a correction. nrh_interpretation_note is also conditional: if an origin-passing three-parameter fit used net data without correction, alpha/saturation and supply may be underestimated and respiration counted again. Only under that specified conservative-bias interpretation is ratio >= 1 credible while ratio < 1 alone is not proof of shortage. This is not an adequacy guarantee; light, domain, mass, reserve and omitted processes remain independent limitations.

### Source decisions and frozen producer association

source_policy_v2.json records six re-inspected cached primary sources, their hashes and exact locators. calcSourceStrength lines 147/160 convert CO2 to carbohydrate and lines 156/167 subtract maintenance_demand_mg. With paper eq7/p7 and Table1/p5, this supports D17 gCH2O model units; the historical CSV CO2 label is retained as a label error. D16 before_mito is linked to eq5, eq8, Table2 and Thornley.calc; it does not establish empirical fit preprocessing.

The source experiment used n=3, mature fully expanded rank-3 leaves, approximately 23 C cuvette temperature, 798 microbar CO2 partial pressure, 50:50 red:blue and applied PPFD 0–2000 umol/m2/s (paper p10; cultivar p9). Applied incident cuvette-light meaning is inferred from the reported setpoints; fit-basis conversion is undocumented. No ppm conversion or ambient-400-ppm target validation was performed. The adopted absorbed model input remains distinct from measurement conditions.

The registry links the completed previous P3 Science report and a frozen current P3 V2 in-progress report. P3 V2 had no completion section at final inspection. Its owner advanced probabilistic_compound_growth.py after the snapshot; verification.json records both hashes explicitly. P4's own current code and all frozen equation locators match their recorded hashes. This is a valid versioned association, not a synchronized final P3 claim. Coordination/P3 must refresh that association after the actual V2 delivery; P4 did not edit P3.

### Validation and reproduction

Evidence root: build/technical_review_fixes_20261004_01/P4/.

- 147 P4 tests passed: 105 retained regressions plus 42 new V2 cases. JUnit: tests_final.xml.
- Two named Windows compatibility tests passed: test_legacy_golden_numerical_payload and test_prepare_light_delegates_existing_bridge. JUnit: tests_windows_compatibility.xml. These bounded tests are not a cross-project model run.
- delivery/ contains 15 synthetic cases, 19 CLI commands (18 successes and one intended exit-2 table rejection), actual result JSON/CSV, two accepted table rows, preserved input hashes and a verified balanced originating-demand ledger. The rejected table directory was not created.
- verify_delivery.py passed 554 checks covering frozen/current P4 hashes, historical preservation, 28 equation function locators, source evidence, JUnit results, every export hash, disclosure round trips, input immutability and requirement coverage. requirement_coverage.json is the machine-readable item map.

```powershell
python -X utf8 -m pytest tools/tests/test_fsp_carbon_diagnostic.py tools/tests/test_fsp_growth_science.py tools/tests/test_fsp_growth_pack_v2.py -q
python -X utf8 -m pytest tools/tests/test_p3_growth_decisions.py::test_legacy_golden_numerical_payload tools/tests/test_compound_growth.py::test_prepare_light_delegates_existing_bridge -q
python -X utf8 build/technical_review_fixes_20261004_01/P4/verify_delivery.py
python -X utf8 -m tools.fsp_carbon_diagnostic --help
```

run_delivery.py and build_evidence.py are retained generation recipes that require fresh output locations; do not rerun them over frozen evidence. delivery/commands.json contains exact executed CLI arguments. Use a fresh build output directory when repeating individual commands.

| Artifact | SHA256 |
|---|---|
| tests_final.xml | e2466465fc3348f03c4ca7319391de167d078d93b7323771fd50c1983a750b91 |
| tests_windows_compatibility.xml | 27cbdefb4c1254e56609dd76919660da5e7fb321c0173a2220472b1bdd78e81e |
| equation_registry_v3.json | 907d2eb4a1266d1c7633a5aff67b49023a60a503b8464a18bea384771ec446e2 |
| source_policy_v2.json | b07773471be5da3b7fd206c426d89557bbb2517c130c5600fc5b7a9aa0f62d2f |

source_snapshot.json contains exact P4/P3/common and primary-handoff hashes; final_manifest.json additionally seals delivery scripts, coverage, validation and this execution report. Historical equation_registry.json, equation_registry_v2.json and source_checks.json remain unchanged.

### Remaining work outside this delivery

Deferred: buffer feedback, nonfoliar assimilation, reserve propagation, two-sided exchange, sympodial continuation, light-to-orientation response and FvCB. These retain explicit not_modelled/none disclosures and registry distinctions. Also pending: original NRH fit preprocessing, independently supported target parameter/domain evidence, real face/area/mass/reserve observations, and final P3 V2 association refresh. No four-project adapter, allocation feedback, new experiment, coefficient fitting or shared coordination roll-up was performed.
