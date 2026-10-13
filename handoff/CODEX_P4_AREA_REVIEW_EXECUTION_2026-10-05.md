# P4 area review execution — 2026-10-05

## Implementation brief (before changes)

Scope: the eight P4 area-review items and six acceptance cases, preserving D15-D21 and V2 numerical behavior. Inspected rules, LOG/TODO, V2 report, current runtime/schema/guide and registry, the supplied Downloads review, Codex response and projection_check.json. The companion CSV/SVG/simulation bundle is not present in the inspected Downloads location; its numerical claims remain unreplicated.

Already present: single-plant/organ/patch context joins, m2 supply weights, cm2-to-m2 SLA inversion, simultaneous fixture summation before NRH, one-sided sample flag, D20 face/exposure gates, exclusive respiration ownership, compatible structural DM/SLA, reserve lineage and reuse guards, unconditional accepted_for_domain=false. Missing: independently traceable area evidence for measured_tissue, partition provenance/duplicate detection beyond patch IDs, explicit non-geometric biological-face evidence, and downstream supply-row source/canopy provenance.

Implement additive area-evidence contract p4-area-evidence-1 for supplied evidence; measured tissue requires quantity=physical_one_sided_lamina, supported status, plant/organ/patch/basis/geometry association, source hash/row, tissue partition and partition-review provenance. Preserve legacy hypothetical fixtures as explicitly hypothetical arithmetic, never physical eligibility. A declared unsupported area fails even in diagnostic use; missing real evidence is unavailable, not zero. The area-based inverse requires the corresponding supported endpoint evidence unless the whole parameter pack is explicitly hypothetical; supplied contradictory evidence is always checked. Supply inputs remain m2 only, inverse inputs cm2 only; refuse alternative units rather than guess.

Retain D20 gates and add a measured-tissue biological-face evidence record; normal/winding/top projection cannot qualify it. Optional canopy-scoped provenance must explicitly retain full-canopy source hashes and selected plant association, while P4 still consumes one exact plant slice. Do not implement a canopy adapter. Add source/basis/partition/fixture lineage to exports and an area eligibility disclosure distinct from biological validation. Build a versioned registry addendum, preserving historical records and namespacing proposals area_review_A1..A7. Verify current P3 final report association read-only.

Evidence root: build/area_review_alignment_20261005_01/P4/. Baseline request/result and source copies/hashes captured before edits. Test new boundaries via API and real CLI/JSON/CSV exports, then run relevant 147-case P4 regression set. No new estimator, G/lambda/curvature default, physiological law, coefficient fitting, inference, integration or human evidence modification. Three area-estimator/matching/calibration decisions remain open for Claude/user.


## Verified completion — 2026-10-05

The bounded P4 area-review engineering task is complete. 186 tests passed (147 retained V2/Science regressions and 39 new boundary cases), 19 actual CLI commands passed on 18 explicitly synthetic cases, and 306 delivery checks passed. All pre-existing baseline diagnostic fields and numerical component/flux values are exactly preserved. No estimator, biological coefficient, law, physical validation or four-project integration was introduced.

### Requirement-by-requirement disposition

| P4 item | Disposition | Authoritative evidence |
|---|---|---|
| 1: adopted physiological policy | Already present, retained | D15-D18 and NRH/respiration code unchanged; original regression suite passes; v4 retains implemented/partial/deferred distinctions and unresolved raw NRH fit preprocessing. inspect_p3_coupling stays read-only. |
| 2: area factors, units and provenance | Implemented missing checks | _area_evidence and _physical_light_support validate measured one-sided lamina, spatial support, source row/hash, exact plant/organ/patch/geometry/basis and disjoint partition declaration. Supply multiplies rate by m2 once; cm2 is only converted once in the area inverse. Supply and demand rows carry source evidence into CSV/JSON. |
| 3: no unsupported real eligibility | Implemented | Proxy, hull, whole-plant A1, unvalidated A2 and missing real support are unavailable. Legacy hypothetical arithmetic remains explicitly hypothetical. Every result retains accepted_for_domain=false and adds physical_area_validated=false; a supported declaration is not validated accuracy. |
| 4: botanical face vs normal | Implemented missing evidence gate; D20 retained | _physical_light_support requires anatomical mapping for measured tissue; unsigned_normal/winding/top_projection and absent evidence fail. _face/_combined_face retain both-face refusal and explicit exposure; no relabelling or halving. |
| 5: absorption, fixtures and respiration | Already present, verified | Exact pre-existing baseline, same-patch canopy fixture combination equivalence and unchanged maintenance; G/imaging lambda/curvature metadata have no numerical effect. Pack/sample light basis and downstream respiration ownership remain explicit. |
| 6: area -> structural mass/demand | Implemented missing area support checks; existing mass/SLA guards retained | infer_structural_demand requires compatible supported endpoint evidence for real area inverses. Unsupported inverse CLI remains unavailable with null demand. Structural blade DM, positive m2/g_structural_blade_DM SLA, primary inverse agreement, ASR, reserve provenance and reuse tests pass. |
| 7: canopy light, individual accounting | Implemented missing metadata checks; single-plant arithmetic retained | Exact context joins; duplicate partition/source rows refused; canopy provenance and every fixture/sample hash retained. Two-plant CLI/table preserves distinct reserve chains, separate supply and maintenance. Orphan canopy tags cannot silently discard canopy scope. |
| 8: registry and review corrections | Implemented metadata; estimator design pending | equation_registry_v4.json, area_review_addendum.json and boundary_function_map.json preserve v3 and namespace all seven proposed/unvalidated estimators area_review_A1..A7. No A2/A3 or full integration completion is claimed. |

Machine-readable coverage: requirement_coverage.json. Exact current function lines and SHA256s: boundary_function_map.json and source_snapshot.json. The changed files are tools/fsp_carbon_diagnostic.py, tools/fsp_carbon_diagnostic_schema.json, tools/FSP_CARBON_DIAGNOSTIC.md and new tools/tests/test_fsp_area_review.py. Demo and all three previous P4 test files remain byte-identical. P1/P2/P3/calibration runtime, docs, config, raw photos and human records were not edited by P4.

### Additive contract and failure behavior

The request version remains p4-carbon-diagnostic-2; x-area-evidence-revision is p4-area-evidence-1. The guide's new Area review boundary revision section documents the full representation. Scientifically missing/unsupported values return structured unavailable with reason codes, while malformed values/hashes, contradictory patch contexts or tampered result provenance remain errors.

- Measured patch area_evidence: schema_version, quantity=physical_one_sided_lamina, status=supported, spatial_support=located_tissue_partition, value and unit=m2; exact plant_instance_id/organ_id/patch_id/area_basis_id/geometry_hash; source_ref/source_sha256/source_row_id/support_source_ref; tissue_partition_id/partition_source_ref/partition_sha256. A source row is a disjoint physical partition, not a second optical face. Missingness: physical_area_evidence_missing or tissue_partition_evidence_missing. Incompatibility: physical_area_unsupported, area_identity_mismatch, area_unit_incompatible, duplicate_tissue_partition.
- Supply inputs remain area_weight_m2, in m2, on each patch and sample. area_weight_cm2 or an incompatible area_unit is refused, not converted implicitly. Exchange is umolCO2/m2/s times m2 times seconds times 12.011e-6 gC/umolCO2. Summation is over non-overlapping patch/time fluxes; fixtures contribute irradiance before NRH. _scope_supply still checks patch-area sum against each scoped leaf's supported_area_m2.
- Area inverse inputs remain supported_area_cm2; CM2_TO_M2=1e-4 is used once. Independent real endpoint evidence maps are p3_interval.area_evidence_start[organ_id] and area_evidence_end[organ_id], unit=cm2, spatial_support=organ_lamina and the corresponding endpoint geometry hash. These maps deliberately sit outside organ_states_start/end, whose complete contents are hashed; placing their own hash inside them would be circular. The initial test exposed that representational issue and it was corrected before delivery. This refines the brief's endpoint-evidence location, not the geometry hashing contract. Missing real endpoint evidence or an unvalidated area method cannot generate empirical mass. Existing explicitly hypothetical inverses remain conditional diagnostics.
- Measured tissue biological_face_evidence: kind=observed_anatomical_mapping or reviewed_anatomical_mapping, face=adaxial, exact plant/organ, source_ref matching face_source_ref and source_sha256. Missing or geometric-only evidence reuses illuminated_faces_evidence_missing. Existing illuminated_faces_undeclared, two_sided_exchange_unavailable and abaxial_exchange_unavailable remain in force. P1 supplies botanical identity; P2 supplies exposure; P4 checks both at its boundary.
- light_scope=canopy requires canopy_provenance with canopy_id, unique plant_instance_ids, full-canopy geometry_hash, source_ref and source_sha256; every selected sample retains canopy_id and canopy_geometry_hash. Missing evidence gives canopy_provenance_missing; wrong membership/geometry gives canopy_identity_mismatch. P4 consumes an exact identified one-plant slice, not a merged biological pool. No canopy adapter or transport was implemented.
- Supply rows now contain plant_instance_id, geometry_hash, area_basis_id, area_unit, tissue_partition_id, area_support, canopy_provenance and light_sources (fixture ID, source reference, sample hash). Demand rows record used endpoint area_support; direct-mass demand uses an empty list. JSON retains all inputs and hashes; compound CSV cells use JSON strings.
- Every sufficiency row includes area_evidence_contract, area_evidence_status=hypothetical/supported_declaration/unavailable, physical_area_validated=false, area_support_json and canopy_provenance_json. Existing status, ratio, reason codes, biological interpretation and reserve lineage remain intact. Missing dependencies produce unavailable and null dependent values, never a manufactured zero or a biological-shortage conclusion.

A valid declaration establishes internal traceability only. Scalar metadata cannot discover overlap hidden behind fabricated partition IDs or authenticate a source file that was not supplied for independent review. P1 must establish actual disjoint geometry, physical area and anatomical evidence. P4 deliberately does not promote such declarations to physical_area_validated=true.

### Source review and producer association

The supplied Downloads Markdown, Codex response and projection_check.json were inspected and hashed. companion_inventory.json records the five named companion CSV/SVG files as absent from the inspected Downloads and proposed project-bundle locations. No simulation code, synthetic MAE, figure contents or global absence claim was invented.

The addendum records the independently calculated six-family selected-zenith G range approximately 0.472–0.550 as sensitivity only. G=0.50 remains unadopted. Unknown occlusion does not identify absolute area or finite upper bounds without justified restrictions. abs(n dot v) is unchanged by normal reversal, including top views. Area plus two angles lacks centroid/depth/outline/curvature for located ray-casting surfaces. Top/ring ratios do not identify an unrestricted angle distribution or mean inclination. Quantile tau=0.9, curvature and low-dilation depth remain proposed; restricted image radius alone does not validate calibration.

The new registry has 28 equations with the previous 11 implemented / 8 partial / 9 deferred statuses, current exact function locators and frozen hashes. Older registries/source policies are unchanged. P3's V2 final report now exists: six of its nine listed file hashes still match, while probabilistic_compound_growth.py, growth_calibration.py and growth_observation_options.py have advanced under their owner. The addendum records both reported and current hashes, and v4 freezes the actual code association separately. This does not claim that current P3 is byte-identical to its V2 delivery. Further producer changes require a new association snapshot, not mutation of these historical records.

### Commands, artifacts and limits

```powershell
python -X utf8 -m pytest tools/tests/test_fsp_area_review.py tools/tests/test_fsp_carbon_diagnostic.py tools/tests/test_fsp_growth_science.py tools/tests/test_fsp_growth_pack_v2.py -q
python -X utf8 build/area_review_alignment_20261005_01/P4/verify_delivery.py
```

Evidence root: build/area_review_alignment_20261005_01/P4/. tests_final.xml records 186 passing tests. delivery_final/commands.json records the exact 19 executed CLI commands; delivery_final/cases.json records 18 cases and their reasons. These cover original/supported baseline, missing area, projected/hull/A1/A2, duplicate tissue, unsigned normal, both faces, wrong unit, missing mass, two canopy plants, missing canopy source/orphan tags, supported and unsupported SLA inversion, plus a two-plant table. delivery_final/manifest.json seals the exports. baseline_comparison.json proves exact previous output fields and numbers. verification.json records 306 checks. Earlier failed/intermediate test files and delivery/ are retained as history; only tests_final.xml and delivery_final/ are the final evidence.

run_delivery_final.py is the final generation recipe; use a new output directory before repeating it. finalize_evidence.py freezes current source associations; do not rerun it over a historical snapshot after final sealing. verify_delivery.py rechecks evidence and current P4 hashes; later intentional code changes require a new version rather than retroactively changing this delivery. No unrelated campaigns, GPU work, fitting or real acquisition was run.

### Design pending / downstream handoff

- Claude/user: keep area_review_A1/A2 reporting priority, leaflet correspondence method and calibration strategy open. Supply a corrected observability/estimator contract and the missing reproducibility bundle before estimator implementation. Earlier resolved D15-D18/Q2 are not reopened.
- P1: independently support one-sided physical lamina, position/outline/curvature as needed, exact plant/organ/partition identity, disjointness, anatomical face and optical geometry. Whole-plant area alone is not spatial patch support.
- P2: preserve the full canopy transport source and exact selected plant/organ/patch/basis/exposure when providing a P4 slice. Geometric transport is not proof of botanical face.
- P3: supply compatible endpoint-area evidence outside hashed organ states and independently supported mass/form relations. Keep current producer association versioned as code advances. P4 made no producer edits.
- Unavailable scientific quantities: validated real leaf area, optical/anatomical applicability, original NRH empirical preprocessing, independently supported target coefficients and any area-only estimate of total DM/roots/reserves/future demand. Diagnostic arithmetic remains conditional. Reserve propagation, new physiology, curvature, phototropism and feedback remain deferred.

### Final evidence hashes

| Artifact | SHA256 |
|---|---|
| tests_final.xml | 1cb58bad48eb6a1f1fb29665c6a5702887cbff76364399c20cd501e22311adc2 |
| baseline_comparison.json | 0934d69bad9b6673661eb56335604ac96265105d4dfe487962bb3f78e238c5ab |
| equation_registry_v4.json | dc12c81e22f19437b7c5b187475143ff78168b2afe3574184f72bb5c7afded98 |
| area_review_addendum.json | 4e5d65ac8666231dba1d37fe355793ce85045380e903b4b2d40e969f80d9d8b4 |
| verification.json | a93895497640ab6a90869b3e73f3b1c19f942e8f067d2800f3e8cc882aa6eec6 |
| source_snapshot.json | c41e712474a3a69a0884cbdf580f74bb5f12cc62a7157a3840f10ae42382135f |

### Owner deliveries available at closure

Read-only inspection of the newly published P1_TO_P2_GEOMETRY_MANIFEST.json confirms independently_supported_real_optical_surfaces=[] and real_area_basis_id=null, with missing scale/accepted pose/one-sided area/capture phase/partition/biological-face evidence. P2's area-review report separates geometric computability from real PPFD eligibility using optical-geometry-evidence-1. These owner artifacts are frozen in downstream_owner_snapshot.json. P4's p4-area-evidence-1 is an additive consumer contract, not an implemented adapter from those tables. Mapping P1 tissue_patch_id and compound identities into P4 plant/organ/patch identities requires a separately scoped, source-preserving adapter; no physical input was inferred or integration claimed.
