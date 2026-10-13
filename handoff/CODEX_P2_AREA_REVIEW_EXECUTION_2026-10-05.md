# P2 area-review alignment execution

Date: 2026-10-05. Status: implementation in progress.

## Brief before changes

Scope: CODEX_P2_AREA_REVIEW_CHAT_PROMPT_2026-10-05.md. Read the supplied Claude area review, Codex response, analytic projection audit, current P2 V2 report and repository rules. Area-review A1-A7 are proposals distinct from adopted P4 physiology decisions. No G, imaging occlusion, quantile, curvature, image-radius or calibration default is adopted.

Current inspection: hierarchical_light.audit_inputs uses the existing reviewed surface boundary and rejects exact duplicate faces regardless of winding/ID. Core load_geometry requires located triangle vertices or a complete rectangular patch (centroid, area, normal and aspect ratio); two patch triangles tile one one-sided area. Bridge uses actual quadrature weights and full-canopy transport, D20 requires separately hashed biological mapping, and measured reference DLI has independent evidence. Existing outputs correctly set physical validation false, but detailed geometric-computability versus physical-claim evidence is not exported, and the consumer does not independently refuse an edited positive physical-validation flag.

Planned bounded correction: add a read-only versioned optical-geometry evidence audit with specific missing-location/shape reasons, source hashes, geometry/area/frame/normal/support disclosures and explicit physical-eligibility limitations. Integrate it additively into bridge audit/package validation without changing transport or reference arithmetic. Retain legacy packages without the additive marker under their existing contract. Test real file/API/CLI/export boundaries, rehashed false physical claims, conventional-normal absence of biology, unit/duplicate handling, full-canopy split additivity and reference independence. Preserve baseline numerics and original review/artifacts; generate evidence in a fresh build/area_review_alignment_20261005_NN/P2 directory.

Restrictions: tools and tools/tests only unless a demonstrated core correction is necessary. No P1/P3/P4 runtime, human data, config/docs, new fitting/tracer, acquisition, inference or cross-chat dispatch. Real scale/pose/surface/face/optical validation and the three source design decisions remain open. Companion CSV/SVG/simulation claims require actual files and are not assumed verified.

## Final bounded delivery

Status: completed software alignment; real optical eligibility remains unavailable. Final evidence is build/area_review_alignment_20261005_01/P2/completion_audit.json (150 checks, 80 unique passing tests, plus 16 overlapping current-dependency checks). All seven P2 items and six acceptance cases have source/test/artifact evidence below. No area-estimation proposal was adopted.

### Requirement disposition and source trace

| P2 item | Disposition | Evidence and boundary |
|---|---|---|
| 1 Existing V2 | Already present, preserved | reference_dli A/C and B-readiness modules, light_face_evidence D20 and core sources unchanged; mapped same/opposite and unknown-face regressions pass |
| 2 Geometry versus real eligibility | Implemented additive audit; physical evidence unavailable | light_geometry_evidence.audit_surface/snapshot_evidence; bridge.audit_growth_light_inputs/build_package; prepared board-mm vertices, scene/placement and review hashes retained. A2 tuple and proxy cases cannot become receiving surfaces |
| 3 Geometric versus botanical side | Already present, verified | Core normals determine geometric sides. light_face_evidence.bind_face_mappings/classify_face independently require reviewed biological mapping. Positive conventional normals alone produce unavailable illuminated_faces, while numerical transport remains available |
| 4 Quantity/area basis | Already present, verified | geometry.triangle_areas_mm2 and patch_vertices_mm; hierarchical_light.load_context weights = triangle mm2 * 1e-6 / sample count; bridge.aggregate_samples sums umol/s then divides by corresponding one-sided m2. export_spatial_light applies absorptance once. No G, lambda or projected-area denominator added |
| 5 Camera versus lamp visibility | Already separate; area-A3 unavailable | raytrace.direct_light applies actual emitter-to-receiver visibility and abs(normal dot direction), with geometric self exclusion and physical leaf crossing codes. Camera-centre visibility could reuse intersection routines, but A2 does not supply located A3 surfaces/camera support; no imaging lambda used |
| 6 Canopy/instance accounting | Already present, verified | split_canopy_results filters existing rows only; test forbids transport during splitting, retains source indices/context, proves positive neighbor-C shading and additive area-weighted flux. Duplicate reversed faces are invalid, real fixture rows are not summed with all |
| 7 Missing evidence and reference independence | Implemented disclosures, existing reference retained | geometry audit states unavailable physical eligibility while supported measured reference remains available; A2 geometry failure does not invalidate standalone measured producer. Valid DLI never certifies tissue PPFD. P3 multi-day/scenario representation restriction unchanged |

### Exact additive contract and changed files

- New tools/light_geometry_evidence.py: audit_surface(path: Path, data_kind: str) -> dict; snapshot_evidence(prepared, snapshot, manifest) -> dict; check_package_evidence(folder, package) -> None; CLI documented below. CSV input uses existing LEAF_SURFACES_CSV_COLUMNS or LEAF_PATCHES_CSV_COLUMNS. An incomplete A2/proxy CSV can be audited, but is never converted to a core optical table.
- tools/light_growth_bridge.py: read-only input audit now adds optical_geometry; build_package records optical_geometry_contract and helper code hash. No sampling, scalar, side, moment, schedule, area, absorption or split arithmetic changed.
- tools/light_growth_consumer.py: validates the additional boundary evidence before numerical checks, verifies source bindings and independently reads current geometry/review/placement sources. It also refuses positive physical-validation claims in package/audit/capabilities. Geometry contract validation shares the read-only helper; existing independent photon/time arithmetic remains separate from exporter arithmetic.
- tools/tests/test_light_area_review.py: 14 discriminating boundary cases, including actual transport/export, CLI, malformed versus missing input, reversed duplicates, tampering, reference independence and canopy shadow preservation.
- tools/LIGHT_GROWTH_BRIDGE.md: versioned metadata/API/CLI/reason/compatibility documentation. tools/light_growth_schema.json and every CSV column remain byte-for-byte unchanged.

New package marker: optical_geometry_contract='optical-geometry-evidence-1'. New audit.json::optical_geometry contains one record per original geometry_snapshot_id. Each retains source_ref and scene_ref {path, sha256}, data_kind, board_frame_ids, grow_frame, existing resolved placements and surface_reviews (including their original declarations and hashes). geometric_computability is available/unavailable/invalid; diagnostic_transport is available or native_scalar_only. physical_ppfd_eligibility stays unavailable and physical_validation false. Actual independent validation is not inferred from review_state/validated_metric/suitable_for_ppfd labels.

Variant fields retain geometry_variant_id, plant_ids, session_ids, geometry_sources, triangle_count, receiver_triangle_count, one_sided_area_mm2, one_sided_area_m2, normal_convention, surface_support and shape_assumption. Vertices/centroids remain in their hashed source table rather than duplicated without provenance. A complete rectangle requires centroid xyz, normal tilt/azimuth, area and aspect ratio; it is an explicit flat-rectangle diagnostic assumption. A two-triangle rectangle has its original one-sided area, not twice that area. For example, 1,200 mm2 = 12 cm2 = 0.0012 m2. PPFD is umol/m2/s and area-integrated flux is umol/s. Existing explicit cm2 observations convert by 1e-4 only in their reviewed association boundary.

New reason codes: receiving_surface_position_unavailable, receiving_surface_shape_unavailable, receiving_surface_parameters_unavailable, projected_area_not_physical_receiving_surface, unsupported_geometry_table_schema, independent_geometry_scale_pose_area_and_optical_validation_required, synthetic_geometry_not_physical_evidence, unsupported_physical_ppfd_claim, unknown_optical_geometry_contract, missing_optical_geometry_contract, optical_geometry_source_binding_missing, optical_geometry_evidence_mismatch. Existing no_leaf_surfaces, duplicate_geometry_face and core malformed-number/degenerate-triangle messages are reused. Missing required scientific coordinates are unavailable; nonnumeric/degenerate/duplicate core geometry is invalid. Unknowns are never zero. normal_convention='geometric_winding_not_botanical_evidence' and biological_face_evidence='separate_reviewed_mapping_required' prevent a geometric convention being presented as botanical proof.

Compatibility: no new mandatory input, no CSV meaning change and no strict scene/schema modification. New package code hashes bind the marker; stripping only the marker is refused. Pre-extension outputs are not retroactively certified and remain subject to ordinary source/code freshness. Historical packages and all original reviews are preserved. Regenerating into fresh paths is necessary after dependency changes; hashes were not patched to force acceptance.

### Execution and acceptance evidence

Commands (project root):

```text
python -X utf8 -m tools.light_geometry_evidence --geometry <CSV> --data-kind synthetic|observed_geometry|hypothetical_layout --out <fresh build directory>
python -X utf8 -m pytest tools/tests/test_light_area_review.py tools/tests/test_light_reference_faces.py tools/tests/test_light_growth_bridge.py tools/tests/test_light_reference_provenance.py -q --junitxml=build/area_review_alignment_20261005_01/P2/regression_01.xml
python -X utf8 -m pytest tools/tests/test_light_area_review.py tools/tests/test_light_growth_bridge.py::test_reviewed_observed_direction_area_and_regions tools/tests/test_light_growth_bridge.py::test_complete_direct_package_and_split -q --junitxml=build/area_review_alignment_20261005_01/P2/current_dependency_02.xml
python -X utf8 -m tools.light_growth_bridge export --input build/area_review_alignment_20261005_01/P2/request_02.json --out build/area_review_alignment_20261005_01/P2/package_02
python -X utf8 -m tools.light_growth_bridge split --input build/area_review_alignment_20261005_01/P2/package_02 --instance P1 --out build/area_review_alignment_20261005_01/P2/P1_in_canopy_02
python -X utf8 -m tools.light_growth_bridge split --input build/area_review_alignment_20261005_01/P2/package_02 --instance P1_COPY --out build/area_review_alignment_20261005_01/P2/P1_COPY_in_canopy_02
python -X utf8 build/area_review_alignment_20261005_01/P2/verify_delivery.py
```

The reference compute CLI was rerun from the original synthetic build/light_growth_v2_20261004_02/reference_inputs position/schedule/readings/survey with route logged into reference_result_02. Value remains 9.72 mol/m2/day under that explicitly synthetic two-fixture schedule, not the real three-lamp configuration. Final request uses absolute source paths and the new result hash; existing physical inputs and human configuration were not changed.

The first attempt to reuse the old reference result was correctly refused with reference_dli_code_hashes_mismatch after the bridge change. A subsequent package became stale when the separately owned compound_growth.py dependency changed during this task. Its original artifacts are retained. The current _02 reference/package/splits were recomputed, and the 16 relevant current-dependency checks were rerun; no P3 code was modified here. Initial boundary_01.xml (10 cases before extending the tests), regression_01.xml (80 cases), and current_dependency_02.xml (16 overlapping cases) are retained. Do not add overlapping counts.

All six acceptance cases pass:
1. Valid synthetic fixtures retain every numeric column exactly; proxy-only and hull-labelled sources never acquire real optical eligibility.
2. Convention-only normals remain biologically unavailable. Existing mapped same-face/opposite-face fixtures still classify correctly.
3. Missing A2 position/shape has explicit reasons through the API and successful unavailable-status CLI export; malformed numeric geometry remains invalid.
4. Rectangular tessellation preserves the one-sided mm2/m2 basis; reversed duplicate faces are rejected. No additional G/lambda attenuation or second absorption multiplication occurs.
5. Reporting-only splits preserve exact parent sample rows, neighbor shading, receiver/fixture separation and additive flux. PPFD is not treated as an additive total.
6. Supported measured reference output validates despite unavailable real plant optical eligibility, and its standalone consumer is independent of unplaceable A2 input.

Three current packages pass independent consumption. All five tables exactly match the historical V2 numeric columns (5 instance rows, 1,344 samples, 1,080 features, 14 intervals, 48 doses). The audit checks 23 protected core/config/reference/face/hierarchy files unchanged and the unchanged strict schema. Numerical comparisons use abs=1e-10, rel=1e-9; baseline comparisons are exact. These are numerical tolerances, not physical acceptance criteria. Added audit work is linear in geometry rows (plus per-face vertex ordering); it performs no transport and does not change existing ray/chunk budgets.

### Scientific limitations and downstream owners

The supplied Markdown, response and analytic audit exist. The five named companion CSV/SVG files are still absent in the Downloads and project build locations checked; companion_inventory.json records exact paths. Their simulation seeds/code/results were not reconstructed or claimed verified. The existing analytic table spans about 0.472-0.550 over its six families and four zenith angles; this is sensitivity, not measured plant accuracy. Neither G=0.5 nor a finite true-area interval is adopted. abs(n dot v) is invariant under n -> -n, and top/ring ratios do not resolve botanical face or a full angle distribution.

P1 must supply reviewed located lamina vertices or an explicitly supported geometric model, centroid/depth/outline/curvature assumptions, scale and pose evidence with source hashes, support/coverage and stable plant/organ/patch identity. Independent calibration/area validation and botanical face evidence remain separate. Full optical validation additionally requires supported lamp PPF/beam/aperture/placement, leaf optical properties and independent PPFD evaluation. Current user-confirmed three lamps, 16 h/day and 100% output setting are retained; missing clock times and physical inputs are not invented.

Claude/user decisions remain open: area-review A1/A2 reporting priority, leaflet correspondence method and calibration strategy. Area-A3 requires located surfaces and a scientifically specified camera-visibility/reconstruction contract; reuse of intersection code alone does not complete it. P4 owns physiological eligibility/refusal, P3 owns model-domain and multi-day/scenario representation policy. No other runtime was edited and no other chat was contacted. No physical accuracy, biological validation, training/inference, fitting, Native run or full-system integration is claimed.

## Resubmitted prompt recheck brief, 2026-10-05

The user resubmitted the same area-review prompt. Current P2 implementation hashes still match the completed delivery; no repeated implementation is needed. Current independent consumption of package_02 is refused because the separately owned compound_growth.py dependency advanced after delivery. Preserve that historical result and regenerate the measured reference plus package/splits in a fresh build directory, then rerun the affected boundary/observed-association checks. P1's newly available P1_TO_P2_GEOMETRY_MANIFEST.json lists no independently supported real optical surfaces; no physical eligibility or adapter is inferred. No other runtime edit or cross-chat contact is authorized/needed.

## Resubmission recheck outcome

Completed without production edits. Fresh outputs: build/area_review_alignment_20261005_02/P2/reference_result, package, P1_in_canopy and P1_COPY_in_canopy. All three packages and the independently recomputed reference validate against current code; all five numeric tables exactly match the earlier area-review package and split rows remain exact parent partitions. 16 focused current-dependency tests pass in recheck.xml (the historical 80-case suite was not repeated). verification.json and verify_recheck.py record current hashes and reproducible evidence. P1's real optical surface inventory is still empty. Earlier package_02 and its validation history are preserved; they now have a stale P3 dependency hash and must not be presented as current-code packages. This refresh changes no physics, geometry evidence, human input or scientific decision.
