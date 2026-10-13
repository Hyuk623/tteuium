# P1 growth Science observation readiness

Date: 2026-10-04. Owner: Codex P1. Status at brief creation: audit in progress. Final outcome is appended below.

## Brief recorded before the audit

Request: audit current P1 observation outputs against the growth Science review and report field availability, measurement support, identity continuity, event definitions, and missing data. The active scope is read-only implementation inspection and documentation.

Current evidence to inspect: observed masks and per-photo area calculations, legacy compound-region geometry, compound-growth observation schemas, surface support exports, canopy source identity, and the latest r04 trial/mapping addenda. Earlier non-GPU and pending-mapping reports are historical where later evidence supersedes them.

Intended delivery: an evidence-backed field inventory and missing-data checklist here, with CSV/JSON audit artifacts under a fresh build directory. Explicitly distinguish observed, derived, synthetic/generated, and unavailable fields. Answer whether supported physical leaf area and longitudinal organ identity can be supplied now.

Restrictions: no production code, biological coefficients, human configuration/observations, docs, P3/calibration/P4 changes; no inference, training, remote upload, experiments, new adapter, or physiological-policy adoption. Q1 reference incident whole-day DLI and Q3 curve-family-specific coefficients remain accepted; Q2 and optional G03/G06/G07 proposals remain undecided.

Validation: inspect actual schemas, producer functions, current artifact contents, and local references; record hashes and counts. Do not rerun unrelated tests. Append findings and actual design questions to the shared handoff queue and one outcome to LOG.

## Final readiness decision

**P1 cannot currently supply an accepted real supported physical leaf area or confirmed longitudinal organ identity.** Both remain unavailable, not zero. P1 can supply saved image observations, per-photo dimensionless ratios, diagnostic projected areas, camera/quality provenance, and candidate geometry. The software also has explicit compound-state and supported-surface interfaces, demonstrated with synthetic inputs. Interface completeness is not observation completeness.

This audit made no production-code changes. Its audit artifacts are the [25-field inventory](../build/p1_growth_science_readiness_20261004_01/field_inventory.csv) and [evidence snapshot](../build/p1_growth_science_readiness_20261004_01/evidence.json). The latter records actual counts, function locators, 58 inspected-file hashes, root availability, and exact parent-versus-split comparisons. The [audit script](../build/p1_growth_science_readiness_20261004_01/audit_readiness.py) reads artifacts only.

## Evidence key and scope

All evidence below is local. Missing-data conclusions concern these delivered P1/P2 artifacts and the configured data roots, not an assertion that no records exist anywhere on the user's computer. The user already confirmed that independently measured leaf area and an accepted curved-surface specification are absent; this audit did not search for substitutes.

| Key | Stable artifact / source |
|---|---|
| E1 | [Current T1 detected ratios](../build/p1_r03_program_update_20261004_01/detected_areas/relative_detected_leaf_areas.csv) |
| E2 | [Current T1 projected-area audit](../build/p1_r03_program_update_20261004_01/projected_areas_final/audit.json) |
| E3 | [T1 pose capture](../build/plants_dwt_test_20261002/plants/dwt_t1/pose_session/edit_session/capture.json) and [legacy structure audit](../build/compound_model_20261003_02/real_t1_audit/audit.json) |
| E4 | [Current candidate-region review](../build/p1_r03_program_update_20261004_01/region_review.json) |
| E5 | [Synthetic compound input](../build/compound_model_20261003_02/synthetic_input/input.json) and [partial-surface example](../build/compound_model_20261003_02/surface_audit/audit.json) |
| E6 | [Current light package](../build/light_growth_science_20261004_01/package/package.json), [instance map](../build/light_growth_science_20261004_01/package/instance_map.csv), [sample table](../build/light_growth_science_20261004_01/package/light_samples.csv), [history](../build/light_growth_science_20261004_01/history.json) |
| E7 | Dated count records: [T1](../build/dwt_test_photos_20261002/dwt_t1/growth.json), [T2](../build/dwt_test_photos_20261002/dwt_t2/growth.json), [T3](../build/dwt_test_photos_20261002/dwt_t3/growth.json) |
| E8 | Empty record templates: [captures](../build/observation_records_20261001/captures.csv), [flower visits](../build/observation_records_20261001/flower_visits.csv), [lighting](../build/observation_records_20261001/lighting.csv), [growth](../build/observation_records_20261001/growth.csv), [area evidence](../build/observation_records_20261001/area_evidence.csv) |
| E9 | [Real lamp operating metadata](../build/lighting_REF_30_40_three_20261004_03/reference_metadata.json), [input readiness](../build/lighting_REF_30_40_three_20261004_03/input_readiness.json) |
| E10 | [Latest r04 contract](../build/multiview_completion_20261004_04/evaluation_contract.json) and [mapping comparison](../build/mapping_validation_20261004_02/comparison_note.md) |

Producer abbreviations in the table: CG = [compound_growth.py](../tools/compound_growth.py); CS = [compound_surface.py](../tools/compound_surface.py); DA = [detected_leaf_area.py](../tools/detected_leaf_area.py); AG = [leaf_area_geometry.py](../tools/leaf_area_geometry.py); AC = [leaf_area_compare.py](../tools/leaf_area_compare.py); PS = [plant_structure.py](../tools/plant_structure.py); CL = [canopy_light.py](../tools/canopy_light.py); LB = [light_growth_bridge.py](../tools/light_growth_bridge.py); OR = [observation_records.py](../tools/observation_records.py); FF = [first_flowering.py](../tools/first_flowering.py); IC = [import_organized_capture.py](../tools/import_organized_capture.py); MR = [marker_pose_rescue.py](../tools/marker_pose_rescue.py). Exact function lines are recorded in the evidence JSON rather than borrowed from older handoff line numbers.

## Field inventory

Support categories distinguish observed metadata/pixels, numerical derivation, synthetic examples, generative hypotheses and unavailable measurements. Date-only values do not supply a capture clock.

| Field | Producer file/function | Unit | Support | Identity | Time / frame | Evidence | Availability and limit |
|---|---|---|---|---|---|---|---|
| plant_id, session_id | CG.audit_legacy_structure | ID | Observed metadata | T1/capture | Date; board convention | E3 | Available capture IDs |
| plant_instance_id, source_plant_id | CL.materialize_case; LB | ID | Synthetic layout | P1 and P1_COPY share source P1 | Separate transforms | E6 | Synthetic provenance available; no real canopy association |
| compound_leaf_id, region_id | PS.compound_regions / reviewed_region_names | ID | Candidate partition | 12 run-local regions | Single session | E4 | Real physical compound mapping unconfirmed |
| label_id, source_annotation_id, view_id | DA.run | ID | Saved image annotation | Plant/session/view/label | Original image pixels | E1 | Available locally; no persistent leaf identity |
| organ_id, leaflet_id, triangle_id | CS.audit_surface | ID | Synthetic surface schema | Plant/session/variant/organ/leaflet/triangle | Board mm | E5/E6 | Export contract available; real reviewed patch association absent |
| observed_at, first_observed_at | CG.extract_compound_state | Zoned ISO time | Real unavailable | Plant/compound/session | Timezone required | E3/E5 | Real T1 time null; folder/date labels are insufficient |
| rachis_arc_length_mm | CG.axis_traits | mm | Polyline derivation | Whole compound axis | Board mm | E3/E5 | Real whole rachis absent; petiole segment is not a substitute |
| axis_stations, rachis_points_mm | CG._stations | 0..1; mm | Input contract, synthetic example | Compound/session | 0 attachment, 1 tip | E5 | Real complete observed axis absent |
| extent_stations, left/right_extent_mm | CG._stations / extract_compound_state | 0..1; mm | Input contract | Compound/session | Reviewed transverse axis | E5 | Real arrays absent; nonnegative extents, unique stations required |
| area_px2, reference_area_px2, relative_area | DA.pixel_area / run | px2; 1 | Mask-derived | Fixed first label per photo | Image plane; date only | E1 | 433 computed, two unavailable exclusions, 18 photos |
| supported_projected_area_cm2, projected_area_cm2 | AG.photo_area_v2 | cm2 projected | Pixel footprint plus hull depth | Selected mask union per photo | Camera/depth frame | E2 | Diagnostic available; not tissue surface area |
| supported_surface_area_cm2, total_tissue_area_cm2 | AC.run | cm2 tissue | Unavailable | Plant/session/coverage | Accepted metric frame needed | E2 | Both null in current T1 case |
| supported_area_cm2, area_basis_id | CS.audit_surface; CG.extract_compound_state | cm2; ID | Supported partial interpolation schema | Reviewed physical patch | Board mm and coverage basis | E5 | Synthetic example available; accepted real physical area unavailable |
| estimated_total_area_cm2 | CG.extract_compound_state | cm2 estimate | Separate estimate contract | Compound/session/basis | Same time and coverage provenance | E5 | Real estimate unavailable; never fill with partial area |
| attachment_xyz_mm, tip_xyz_mm, parent_stem_id | CG.axis_traits / extract_compound_state | mm; ID | Axis endpoints and reviewed attachment | Compound/parent | Board mm | E3 | Attachment and parent unconfirmed |
| direction_unit_xyz, azimuth_deg, elevation_deg | CG.axis_traits | 1; deg | Endpoint-chord derivation | Whole rachis | Signed elevation in board frame | E3/E5 | Petiole angles exist; whole-rachis direction absent |
| transverse_unit_xyz, frame_id, frame_evidence | CG.extract_compound_state | 1; ID | Explicit orthogonal frame | Compound/session | Stable board/local frame | E5/E6 | Synthetic available; real organ-frame evidence absent |
| rvec_rad, tvec_mm, intrinsics/board hashes | IC.import_capture; MR.rescue_session | rad; mm; hash | PnP-derived | Per image/capture | Board convention | E3 | Numerical poses available; real scale not confirmed |
| reprojection_error_px, passes_pose_gate, pose_source | IC.solve_pose; MR.marker_pose / rescue_session | px; flag | Residual/gate diagnostic | Per view | Camera/board | E3 | Available; not calibrated organ uncertainty |
| review, visibility, observation_status, ratio_status | DA.run | Category | Annotation/calculation provenance | Per image label | Image space | E1 | Available; not a measurement-error distribution |
| uncertainty and shared/organ covariance | CG.extract_compound_state | Status; variable-specific covariance units | Uncalibrated | Capture and organ errors not separated | Repeatability series needed | E3/E6 | No empirical covariance decomposition |
| captured_at plus photoperiod phase | OR; CG | Zoned time; phase duration | Empty real tables | Capture plus dated lamp schedule | Clock/phase reference absent | E8/E9 | Real phase unavailable; 16 h duration is insufficient |
| compound_leaf_count, growth_shoot_count, truss_count | Human run copies; PS.name_regions | Count | Dated snapshot | Plant; compound labels | 2026-10-02 | E7 | Available counts, not emergence times or cumulative ranks |
| flower_visits.state, first_open_date | FF.events | Category; date | First-open-flower contract | Plant/date/confirmation | Censoring interval | E8 | Empty template; no real dated event sequence |
| novel_view_rgb, metric/optical flags | Existing trial returns and mapping review | Pixels; flags | Generative | Request/seed/target | Canonical mapped pose | E10 | RGB hypotheses available; false metric/optical flags preserved |

The station parser enforces ordered unique values in [0,1] and axis endpoints 0/1. This alone does not declare normalized arc length, anatomical homology, or a repeatable station-placement procedure. Claude must define the observation convention before longitudinal extents can be treated as corresponding measurements.

## What the current numerical evidence means

E1 contains 435 T1 annotation rows: 433 computed ratios and two explicit exclusions. Each photograph retains its original first label as the reference. The ratio is visible mask pixels divided by first-label mask pixels; it has no area unit, no depth correction and no cross-date identity guarantee. The 435 rows are not 435 unique physical leaves.

E2 contains 18 photo calculations. For image 27, 124,520 selected pixels yield `supported_projected_area_cm2 = projected_area_cm2 = 11.29660018160603`, under the recorded distortion-aware pixel-footprint calculation and per-mask 20th-percentile hull depth with at least five hull points. This is a union projection, not a per-organ true lamina area. `passes_pose_gate`, `validated_metric` and `suitable_for_ppfd` are false. The case's supported surface, total tissue and calibrated whole-plant area are null.

E3's legacy audit has five candidates, zero confirmed compound IDs and null observation times. Fitted petiole endpoints/angles exist for four candidates; all five remain ineligible as observed whole compound states. E4 changes the cached partition from five to twelve candidate regions while retaining the coordinates. A region number, an assigned count label and a persistent biological identity must remain distinct. Do not transfer old names to this partition without review bound to its hash.

The camera capture stores intrinsics and board hashes, reprojection errors, solved/rejected pose information and the board-frame convention. Its recorded board-variant evidence has `confirmed_by_user=false` and no observed printed-caption evidence. Marker IDs and reprojection alone do not establish physical print scale. These are traceable diagnostics, not a physical-scale acceptance certificate or measured frame stability across dates.

CS.audit_surface requires confirmed physical patch identity, accepted topology with a review source, at least two visible support views under an explicit policy, and duplicate/intersection checks. Its example has 1 cm2 of partial supported interpolation from two retained faces, but it is synthetic evidence, not a real leaf measurement; total area is null and metric/PPFD flags remain false. A historical support label cannot override the current evidence gates.

The latest trial is r04: the execution handoff records 80 generated views and the mapping comparison now exists. Older blanket statements that no mapping comparison or GPU return exists are superseded. The object-centred mapping reproduces the hull camera crop at IoU 0.973; this is a mapping consistency diagnostic on the same hull. Under that mapping, r04 leaf-level IoU is about 0.264/0.258, near controls; filled-envelope IoU is about 0.493/0.464. The envelope metric and closing radius were selected post hoc, on one plant and one held-out view. This supports neither recovered leaf placement nor physical tissue area, normals, optical eligibility or longitudinal identity. No new generation or metric fitting was performed here.

## G08: uncertainty and repeatability

Available quality information includes camera reprojection residuals and gate outcomes, source-view membership, annotation review/visibility states, mask coverage, and numerical integration diagnostics. CG explicitly emits `uncertainty.status = uncalibrated`. E6 likewise labels geometry and optics uncalibrated; its numerical tolerances are precision settings, not biological confidence limits.

The inspected real data do not contain paired same-plant remounting replicates with matched organs, raw repeated lengths/extents/areas, paired pose/scale estimates and a declared error model. They therefore cannot separate shared camera/scale error from organ-specific annotation/reconstruction error, estimate cross-organ measurement covariance, or supply a calibrated measurement-noise matrix to P3. Do not convert segmentation scores, reprojection RMS or generative seed variation into such a covariance. Absence of off-diagonal estimates is not evidence of independence.

P3 owns G08/F11 likelihood/ESS reporting and the declared cross-organ-correlation limitation. P1's role here is to identify the missing observation inputs and preserve their eventual provenance. Optional G03 covariance-based reanchor weighting remains unadopted.

## G06: existing timing and photoperiod metadata

All nine CSVs in `build/observation_records_20261001` contain headers only. The configured data root resolves to this project's `data/`; `records/` and `tracks/` do not exist there at audit time. The actual T1 pose capture has no `captured_at`. Calendar dates in E7 do not establish within-day phase.

E9 preserves the user's confirmed 16 h/day at photon output fraction 1.0. Clock windows, schedule timezone and whether those hours form one continuous interval remain unset. The earlier 06:00-22:00 example is explicitly not adopted. E6's clocked schedule is labelled `synthetic_test_only` and cannot fill those real gaps. The lamp metadata is not evidence that each historical photo was taken under that schedule.

No real observation can currently be assigned to a reviewed photoperiod phase from these artifacts. No phase offsets, posture corrections, new clock windows or G06 model were fitted or selected.

## G07: actual event semantics and records

| Plant | Recorded date | Compound leaves | Unfolding compound leaves | Young shoots | Trusses |
|---|---|---|---|---|---|
| dwt_t1 | 2026-10-02 | 5 | 0 | 2 | 0 |
| dwt_t2 | 2026-10-02 | 4 | 0 | 2 | 0 |
| dwt_t3 | 2026-10-02 | 4 | 1 | 1 | 0 |

These are existing run-copy records; their notes preserve a prior user correction to unfolding flags. The input guide defines unfolding as a subset of total compound leaves, and young shoots as separate from leaflet totals. It explicitly says listed compound labels are not positions or coordinates. A truss count of zero means the record reports none observed; it does not establish a first-visible-bud threshold, flowering date, terminal state or lifetime node count. Retain these recorded zeros while leaving unknown event fields unavailable.

FF.events has a different, explicit first-open-flower endpoint: `not_open`, `bud_only`, `first_open`, `missed`; confirmed first-open records require an evidence photo. It distinguishes interval-censored, right-censored, already-flowered-at-entry, baseline-unknown and no-confirmed-observation cases. `bud_only` is a non-open observation in this contract. The delivered visits template has zero rows, so this software capability supplies no observed flowering endpoint here and does not choose G07's optional truss observable.

There is no delivered, reviewed first-visible leaf/truss sequence or termination follow-up in the inspected real record set. Forecast `events.csv` files and synthetic histories are model outputs/examples, not human event records. Visible counts cannot be equated with cumulative node rank; missed visits, lost leaves and unobserved organs would require explicit records and definitions.

## Identity through canopy representation and splitting

The current synthetic E6 package contains five instance-map rows and 1,344 light-sample rows. Source/instance pairs are P1/P1, P1_COPY/P1 and P2/P2. Samples retain organ, leaflet, triangle and sample IDs, session, geometry snapshot/variant, source plant, transform, frame, area basis and availability provenance. `compound_id` and `compound_leaf_id` are joined only through explicit reviewed associations; their names are not automatically interchangeable.

For both [P1 split](../build/light_growth_science_20261004_01/P1_in_canopy/package.json) and [P1_COPY split](../build/light_growth_science_20261004_01/P1_COPY_in_canopy/package.json), this audit compared all rows in five delivered tables to the exact parent selection. Both preserve 576 sample rows, unchanged common interval rows, full context geometry hashes and a matching parent-package hash. The split kind is `report_only_full_canopy_shading`. It preserves the original canopy's light context; it does not recalculate an isolated plant.

Thus existing representation/splitting preserves the synthetic identities supplied to it. It does not establish real identity, turn a template copy into an independently observed plant, or recover an omitted association. Compound aggregation cannot recover leaflet geometry from a mean; retain source sample/geometry files. Real P1 needs reviewed compound/leaflet/patch associations, persistent physical IDs, time/frame evidence and a supported area basis before any later adapter. No adapter or data merge was implemented.

## Proposed measurement plan: missing-data checklist only

This section translates Science section 6 into missing inputs. It is a proposal, not an adopted experimental protocol, a new experiment authorization or a request to fabricate records. Claude owns protocol/agronomic choices; the human owns acquisition and ground truth. Numerical sample-size suggestions below come from the Science handoff, not from demonstrated adequacy in this audit.

| Missing input | Proposed record/evidence checklist | Exact follow-up owner | Downstream limit until supplied |
|---|---|---|---|
| Persistent organ and patch identity | Same physical plant/compound/leaflet IDs across views/dates; attachment review; association evidence and partition hash; missing/occluded/lost state | Human acquisition/reviewer; Claude identity policy; P1 later export | No real longitudinal join or per-organ growth evidence |
| Metric scale and frame acceptance | Actual printed board/scale evidence, intrinsics/pose provenance and quality; remounting/frame evidence; no inferred scale from marker IDs | Human acquisition; Claude acceptance protocol; P1 diagnostic/export | Length/area numbers remain diagnostic |
| G08 repeatability covariance | Back-to-back captures of the same plant with remounting; replicate IDs, matched organs, raw measurements and shared camera/scale provenance; repeat enough under a reviewed estimation protocol | Claude repeatability/error-model design; human capture; P1 preserve inputs; P3 covariance consumer | Shared versus organ error and calibrated covariance unavailable |
| G06 phase metadata | Timezone-aware photo times; dated lamp on/off windows and phase reference; paired phases on at least three dates as proposed by Science | Human timing/capture; Claude phase protocol; P1 metadata; P3 only after optional-model decision | No separation of transient posture from growth |
| G02/G03 repeated geometry | Same-organ length, left/right extents and supported area at at least six time points; reviewed station correspondence and observed transverse frame | Claude station/coverage protocol; human observations; P1 geometry export; P3 calibration | No measured growth law or beta fit; optional reanchor unchanged |
| Independent leaf-area validation | Reviewed visible support/triangles, surface coverage and basis; independent area measurement with method, date, organ ID and evidence | Human measurements; Claude surface/validation specification; P1 later comparison | Neither total tissue area nor accepted real supported area ready |
| G07 dated events | First-visible leaf/truss observations plus missed visits, evidence and termination follow-up; explicitly choose observable and rank bookkeeping before use | Claude definition proposal; user decision for optional G07; human event log; P3 event consumer | No flowering/terminal timing or cumulative-rank inference |
| L01 reference DLI | Complete local-day incident PPFD with one declared reference plane/position and disjoint basis; timestamps, coverage, evidence and applicability; Science's >=3-position campaign may be proposed separately | Claude measurement protocol; human sensor data; P2 future authorized reference export; P3 model interval/coefficient use | Current tissue-light output is not accepted P3 reference DLI |
| C01-C04 physiology | Target-cultivar light-response/dark exchange; organ dry mass and structural/nonstructural split with identity, units, conditions | Claude physiology protocol; human measurements; P4 diagnostic/source review | P1 area or generated RGB cannot supply exchange/mass parameters |

Question 1's whole-plant model scope does not authorize averaging reconstructed leaf DLI or multiple sensor positions into the declared reference value. Question 3 requires growth-curve-family-specific coefficients and supplies no numeric coefficient. P4 question 2 remains undecided. P3 owns realized growth, P4 remains diagnostic, and cross-project linking remains deferred.

## Verification and completion

Executed only the new read-only audit script. It inspected schema meanings and source-function existence, checked the exact split contents, and verified all 58 inspected files were unchanged during its run. No inference, transport solve, fitting, production test suite, human-record edit or deployment occurred. The audit did not independently rerun r04 or its exploratory statistical analysis; it checked the current result artifacts and preserved their stated scope.

Reproduce from the project root: `python build/p1_growth_science_readiness_20261004_01/audit_readiness.py`.

All six P1 prompt work items are addressed above. Missing physical data limit downstream readiness but do not prevent completion of this read-only audit. Final local-link/source-hash checks and the requirement checklist are recorded in [completion_audit.json](../build/p1_growth_science_readiness_20261004_01/completion_audit.json). LOG/TODO receive separate appended outcome and design-question entries; no historical pending-GPU record is silently rewritten.
