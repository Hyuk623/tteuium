# P1 Growth Pack V2 execution

Date: 2026-10-04. Owner: Codex P1. Status at brief creation: in progress.

## Brief before implementation

Request: execute the P1 V2 prompt together with technical-review section 6 and D21. Inspect only the changed consumer dependencies; preserve the historical readiness report and human observations.

Current behavior: compound_surface.audit_surface checks patch identity, topology and visible image support, but its partial-area eligibility does not validate the complete new scale/pose/time/one-sided-coverage evidence contract. All current real physical-area/longitudinal-identity findings remain unaccepted. Existing generated trial results are not new physical evidence.

Intended changes: add explicit downstream real-area evidence validation/reporting at the P1 surface boundary without altering geometry calculations; preserve explicit synthetic fixtures and report missing evidence as unavailable. Prepare the exact header-only D21 template and checklist plus a P3 field mapping. Record the V2 consumer evidence delta, biological face-evidence limits and downstream ownership.

Restrictions: no new reconstruction algorithm, GPU/inference/training, physiological code, covariance estimation, P3/P4/calibration edits, human-record/config/docs edits or integration adapter. D14 options and D21 recording are now approved; D15-D20 policies supersede the old undecided notes. No values, evidence or historical event definitions will be invented.

Validation: focused tests deleting each required evidence group and checking real-eligibility refusal, positive/negative synthetic-fixture checks, relevant existing surface/export regressions, exact CSV header/zero-row verification, source hashes and local reference checks. Output root: build/technical_review_fixes_20261004_01/P1/. Report section 6 and D21 completion separately; coordination retains ownership of shared final reports.

## Outcome

**Technical-review section 6: done. D21 P1 template/checklist/mapping: done.** The code now separates geometrically supported diagnostic area from an evidence-complete real-area claim. The approved blank Day-1 template is available immediately. Real supported physical area, longitudinal organ identity, trait covariance, phase offsets and biological leaf-face evidence remain unavailable in the inspected P1 records. No physical accuracy improvement is claimed.

Historical reports and observations were preserved. The [bounded evidence delta](../build/technical_review_fixes_20261004_01/P1/consumer_evidence_delta.json) compares nine relevant files to the prior readiness audit: all nine are unchanged. It also records the newer T1 regroup artifact and its partition hash. Regrouping is a candidate-identity change, not a new same-organ time series, scale calibration or area measurement. The previous full audit, reconstruction and generative trials were not rerun.

## Decisions changed since the earlier readiness report

- D14 approves opt-in reanchor weighting and observation-only posture offsets, with explicit truss-observable support. P3 owns the implementation; approval supplies no fitted offsets, variances or actual event observations.
- D21 fixes **visible_bud for new recording**, with early/late phases defined from actual lights-on/off. This supersedes the old unadopted/no-protocol wording. It does not relabel older ambiguous records.
- D15-D18 resolve the adopted dwarf-route P4 policy: absorbed light, before_mito and carbohydrate-equivalent maintenance; no 1.466 rescaling. D20 assigns per-patch illumination exposure to P2; P4 validates it. P1 cannot establish adaxial-only exposure alone.
- P3 still uses incident reference-position DLI, distinct from tissue area/light. No biological coefficients or P3/P4/calibration code were changed here. Implementation policy is separate from empirical source applicability or independent validation.

## Current field/evidence/gap table

| Consumer need | Actual P1 producer/function and fields | Units / provenance | Current evidence and missing values | Downstream owner |
|---|---|---|---|---|
| Matched same-organ reanchor observations | [compound_growth.extract_compound_state / load_history](../tools/compound_growth.py): plant_id, compound_leaf_id, session_id, identity_status, review_source, observed_at; axis/extent/area traits | mm, cm2, degrees; hashed source tables | Whole-rachis and temporal identity remain unconfirmed. The [legacy audit](../build/compound_model_20261003_02/real_t1_audit/audit.json) is not a matched longitudinal series | Human identity review; P1 export; P3 reanchor |
| Trait-specific uncertainty | compound_growth.extract_compound_state: uncertainty.status=uncalibrated | Trait-specific variance would need compatible squared units and named trait/basis | No measured state/measurement variance pair or shared-pose/scale decomposition. Scores, reprojection RMS and seed variation are not covariance | Claude measurement/error-model design; P3 opt-in weighting |
| Phase and time | [capture.json](../build/plants_dwt_test_20261002/plants/dwt_t1/pose_session/edit_session/capture.json); [observation_records CAPTURES/SCHEDULE](../tools/observation_records.py); new D21 captured_at/capture_phase | Aware timestamp, named phase, schedule-source reference | Historical T1 capture clock absent; [lamp metadata](../build/lighting_REF_30_40_three_20261004_03/reference_metadata.json) still has 16 h/day at 100% but unknown actual clock windows. Reference phase/offset values absent | Human recording; P3 read-only import and observation likelihood |
| Meaningful event observation | [first_flowering.events](../tools/first_flowering.py): state, first_open_date, censoring fields; [T1 count record](../build/dwt_test_photos_20261002/dwt_t1/growth.json): truss_count | Calendar date/count, human evidence | First-open flower is distinct from visible bud. Existing truss_count=0 retains its original meaning; no automatic conversion to dated visible-bud events or terminal events | Human D21 record; Claude counting rules; P3 G07 |
| Physical patch identity and area | [compound_surface.audit_surface / audit_area_evidence / audit_study](../tools/compound_surface.py): KEY, tissue_patch_id, partition/reviewer binding, area_basis_id, downstream_supported_area_cm2 | One-sided cm2; geometry digest; source-file and partition hashes | New gate exists; real four-group evidence absent. [Projected-area audit](../build/p1_r03_program_update_20261004_01/projected_areas_final/audit.json) remains diagnostic, with null tissue/supported-surface area | P1 boundary; human/Claude evidence; P2/P3 consume only eligible basis |
| Surface orientation and botanical face | [leaf_surface_compare.plane_points / chart_faces](../tools/leaf_surface_compare.py): unsigned_normal, normal_convention=unknown | Unit vector / geometric convention | No reviewed biological adaxial/abaxial association. Winding, +normal, upward orientation and visibility cannot fill it | Human/Claude face review; P1 provenance; P2 exposure; P4 exchange gate |
| New Day-0 node and visible-bud counts | Header-only D21 template below | Integer count plus counting-rule source; blanks unknown | No live records supplied. Visible leaves are not cumulative nodes; counts do not supply node_rank/parent-axis event identities | Human observation; P3 reviewed import/back-fill |
| Station correspondence | compound_growth._stations / extract_compound_state: station, transverse_unit_xyz | station in [0,1], mm; reviewed local frame needed | Range/order/endpoints do not establish same anatomical stations across dates; prior Claude specification question remains open | Claude correspondence rule; P1 preservation; P3 comparison |

The camera diagnostics and original image masks remain useful source evidence, but do not meet the new physical-area contract by themselves. Explicit synthetic schemas/fixtures can exercise software without supplying missing biological information.

## Section 6 implementation and interface

Changed [compound_surface.py](../tools/compound_surface.py) and [COMPOUND_MODEL.md](../tools/COMPOUND_MODEL.md); added [test_p1_area_evidence.py](../tools/tests/test_p1_area_evidence.py). No reconstruction physics changed. The existing `eligible_supported_area`/`supported_area_cm2` calculations retain diagnostic meaning and values, with `diagnostic_support_is_real_area_acceptance=false` explicitly reported.

`audit_surface` now calls `audit_area_evidence` and accepts optional keyword inputs `area_evidence` and `evidence_base`. A surface study may reference a hashed `p1-area-evidence-1` JSON through `area_evidence: {path, sha256}`. The [guide](../tools/COMPOUND_MODEL.md) specifies the complete field contract. Required patch groups are:

1. Physical scale: positive square_size_mm, nonnegative calibration_residual_mm and a hashed actual ChArUco scale-calibration source.
2. Pose: a declared max_reprojection_error_px and hashed source; every visible support frame must carry a finite residual within that threshold, solved pose and true passes_pose_gate.
3. Time/phase: aware captured_at, declared early_photoperiod or late_photoperiod, and hashed capture plus actual schedule evidence.
4. One-sided area: quantity=one_sided_physical_tissue, coverage_fraction in (0,1], occlusion_statement and hashed evidence. No coverage-based extrapolation to total area.

Identity is separately bound by plant/session/variant/organ/leaflet/patch, the exact verified partition hash and an explicit reviewer. Geometry content is bound by `geometry_digest=digest(rows(geometry_csv))`. Missing/changed geometry association cannot preserve a former accepted basis. Each patch coverage gets its own declared basis; the tool never invents an ID. If any patch face fails existing support/topology checks, that declared coverage cannot be issued as real area.

New outputs are `area_evidence` in audit JSON, per-face `eligible_real_area`, `area_basis_id`, `area_evidence_reasons`, and CLI tables:

| Output | Semantics |
|---|---|
| area_basis.csv | Declared ID separate from eligible ID; per-patch status/reasons and nullable downstream_supported_area_cm2 |
| downstream_leaf_surfaces.csv | Only faces whose complete patch passes the real-area evidence gate |
| supported_leaf_surfaces.csv | Existing diagnostic supported faces, explicitly not a real-area acceptance route |
| surface_review.json | Still pending/partial with false metric and PPFD flags; now references the area audit/table |

Unavailable real claims have null eligible ID/value in JSON and `unavailable` cells in CSV. The principal reasons are `area_evidence_undeclared`, `real_observation_evidence_unavailable`, `synthetic_not_real_area`, `area_geometry_binding_unavailable`, `partition_identity_review_unavailable`, `physical_scale_evidence_unavailable`, `pose_evidence_unavailable`, `pose_evidence_rejected`, `capture_time_phase_evidence_unavailable`, `one_sided_area_evidence_unavailable`, `area_basis_id_undeclared`, `physical_tissue_geometry_source_unavailable` and `patch_geometry_support_incomplete`.

Missing scientific evidence is an unavailable result. Hash mismatches and malformed/duplicate/orphan input claims remain integrity errors. Explicit synthetic declarations retain their supplied IDs as diagnostic declarations but cannot issue real-area eligibility, including when an attached manifest attempts to override a synthetic study. Projected/relative/unsupported total estimates, assumed geometry and unreviewed patches are refused at this boundary.

`evidence_complete` means the submitted evidence contract passes these checks. A hash cannot prove that a human calibration or review was scientifically correct. `validated_metric=false`, `suitable_for_ppfd=false` and pending optical review remain; this change does not replace independent validation or existing P2 optical gates. Existing historical exports do not retroactively become eligible. No cross-project adapter was added.

## D21 delivery and P3 mapping

The exact [day1_protocol.template.csv](../build/technical_review_fixes_20261004_01/P1/measurements/day1_protocol.template.csv) contains the required 11 columns and **zero data rows**. The [Korean user checklist](../build/technical_review_fixes_20261004_01/P1/measurements/DAY1_CHECKLIST.ko.md) is ready to use. [P3_MAPPING.md](../build/technical_review_fixes_20261004_01/P1/measurements/P3_MAPPING.md) documents source fields, units, missingness, required associations and hash preservation. P3 loaders were not edited.

- early_photoperiod is actual lights-on + 2 h; late_photoperiod is actual lights-off - 2 h. Record aware timestamps and actual schedule references; an unknown clock never becomes an inferred phase.
- New truss_observable is explicitly visible_bud. Anthesis/fruit set and old ambiguous truss records are not relabelled. Zero means observed zero; blank means unknown.
- Day-0 node_count needs a reviewed counting-rule source per plant. It is not automatically visible leaf count or cumulative event rank.
- Sowing/transplant dates remain blank when unknown. They do not establish absolute age of an existing organ.

The fixed header has no trait variance, lamp schedule, parent-axis or per-organ correspondence columns. Keep schedule/evidence references in notes and preserve referenced documents; P3 must request explicit associations rather than extract invented numerical evidence from prose. Capture_session_id is explicitly mapped to the consumer's session identifier; a count cannot automatically expand into ranked event records. Template preparation does not claim human measurements have occurred.

## Validation and remaining ownership

**60 focused tests passed** in [gate_tests_final.junit.xml](../build/technical_review_fixes_20261004_01/P1/gate_tests_final.junit.xml). Coverage includes each missing evidence group, naive timestamp, missing phase/schedule, invalid coverage, stale partition/geometry, each support-view pose gate, missing/tampered source, synthetic-versus-real distinction, disallowed area kinds, incomplete geometry support and CLI exports/source preservation. Existing compound-surface, surface-comparison and chart regressions remain passing.

The first run had two fixture hash failures because the test setup reused its capture-evidence filename for a camera file. That fixture collision was corrected; the hash-refusal code was retained. The earlier JUnit is preserved. One explicit CLI run on a clearly labelled [synthetic fixture](../build/technical_review_fixes_20261004_01/P1/synthetic_fixture/study.json) produced [synthetic_gate_demo/audit.json](../build/technical_review_fixes_20261004_01/P1/synthetic_gate_demo/audit.json): diagnostic area exists, real eligible ID/area do not. It is not a real reconstruction or accuracy experiment.

Run the changed-gate verification from the project root:

```powershell
python -X utf8 -m pytest tools/tests/test_p1_area_evidence.py tools/tests/test_compound_surface.py tools/tests/test_leaf_surface_compare.py tools/tests/test_leaf_surface_charts.py -q --junitxml=build/technical_review_fixes_20261004_01/P1/gate_tests_final.junit.xml
```

| Item | Status / exact owner |
|---|---|
| Section 6 geometry/topology/source support | Already present; P1 retained calculations |
| Section 6 complete real-area evidence gate / reporting | Done by P1, with focused tests and separate output |
| D21 blank template, checklist and field mapping | Done by P1; human recording may start now |
| D21 read-only G06/G07 import/back-fill | P3 owner; intentionally not edited here |
| Reanchor variance, offsets, same-organ identity, real scale/area evidence | Missing observations; human acquisition and Claude scientific protocol, P1 export when supplied |
| Station/anatomical correspondence specification | Claude owner; still open, no automatic mapping invented |
| Biological face identity and illuminated_faces | Human/Claude anatomical evidence; P1 preserve evidence; P2 exposure producer; P4 policy validator |
| Shared final technical/V2 reports and interproject linking | Coordination owner; no shared report overwrite or adapter in P1 |

Delivery hashes, exact header/zero-row assertions, local reference checks and source-preservation checks are saved in [verification.json](../build/technical_review_fixes_20261004_01/P1/verification.json). The only production implementation edit is the P1 compound-surface boundary; no P3/P4/calibration/light solver, human observations, configuration, biological coefficients or docs were changed.
