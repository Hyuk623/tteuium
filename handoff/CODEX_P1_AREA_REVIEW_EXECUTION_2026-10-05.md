# P1 area-review alignment execution

Date: 2026-10-05. Owner: Codex P1. Status at brief creation: in progress.

## Implementation brief

Request: execute the bounded P1 area-review follow-up, retain completed V2 gates and diagnostic baselines, and implement only missing owned boundary/provenance corrections. Area-review A1-A7 are proposals distinct from the earlier physiological A1-A7.

Inspected behavior: plant_traits already has a versioned measured-elevation path, but Plant.s8 currently calls it without area_policy/view_grouping/capture_style. Existing footprint-v2 calculations retain legacy photo values. Unknown view groups can fall outside group aggregates without an explicit aggregate-completeness label. The completed compound-surface evidence gate already distinguishes diagnostic support from real evidence completeness, biological face and optical approval.

Intended changes: forward explicitly configured S8 policies, expose separate grouping/integrator comparisons and completeness, preserve applicable source/time/identity/support/uncertainty metadata through trait exports, and verify the established canopy/source accounting and surface gates. Inspect current callers and source evidence before finalizing changes. Supply a P2 geometry/readiness manifest and an area-review A1-A7 dependency table.

Restrictions: no adopted G/lambda/tau/curvature/radius defaults; no A1/A2/A3 estimator, matcher, new canopy engine, board-rejection redesign, reconstruction campaign, inference, training, acquisition, biological coefficient, human-record/config/docs or P2/P3/P4 runtime edits. A1/A2 priority, matching method and calibration strategy remain open. Historical area series and audit files are preserved.

Validation: focused API/S8/export regressions with explicit synthetic data, missing-evidence and proxy/normal/unlocated-geometry refusal cases, separate grouping/integrator effects, unknown-view accounting, existing canopy rigid-transform/identity/tissue round trip, source/baseline hashes, and requirement-by-requirement completion audit. Outputs go to fresh build/area_review_alignment_20261005_01/P1/.

## Final delivery

The bounded engineering task is complete. Final verification: **119 unique tests passed**, plus **27 delivery checks passed**. Real supported physical leaf area, botanical face and optical eligibility remain unavailable. No new area estimator, biological calibration or acquisition was adopted.

Output root: `build/area_review_alignment_20261005_01/P1/`. Read `verification.json`, `final_pytest.xml`, `canopy_roundtrip_audit.json`, `real_evidence_snapshot.json` and `P1_TO_P2_GEOMETRY_MANIFEST.json`. The manifest is published in the shared handoff directory tree for P2; no cross-chat dispatch or runtime integration occurred.

## Scope disposition

| P1 item | Status | Evidence and boundary |
|---|---|---|
| 1 S8 actual caller and grouping | Implemented | `Plant.s8` forwards only explicit per-plant `area_policy`, `view_grouping`, `capture_style`. No default policy was invented. `plant_traits` retains legacy values, adds a 2x2 audit, corrects v2 top-photo count, and preserves `legacy_top_photos`. |
| 2 Quantity provenance | Implemented | `trait_area_provenance` carries source hashes, pixel input digests, frame support/pose, time/phase, grouping, calibration, hull depth/dilation and identity limitations. Summary CSV points to a hash-bound provenance sidecar. |
| 3 Physical area boundary | Already present; verified | `compound_surface.audit_area_evidence` / `audit_surface` and existing two downstream files remain unchanged. Added explicit hull/A2 refusal cases to the focused tests. Projection, hull, unreviewed or assumed/generated geometry are not a real tissue basis. |
| 4 Orientation versus biological face | Already present; verified | Existing located vertices retain geometric orientation. Reversing triangle winding or declaring a stem-away convention does not produce biological face evidence. No sign-to-adaxial conversion. |
| 5 Area-review A1-A7 | Design pending, dependencies documented | See table below. No A1/A2/A3 implementation, matcher, tau, curvature or G default. |
| 6 Top/ring diagnostic | Implemented | Unitless whole-view projected ratio when both groups have complete selected projection, known grouping and positive ring denominator. Missingness returns null; no mean inclination, LAD, biological face or occlusion correction. No leaflet matching prerequisite for this diagnostic. |
| 7 Existing canopy round trip | Already present; verified | Saved parent and both splits have exact table partitions, unchanged context/parent hashes, consistent position/normal transforms and one-sided quadrature accounting. Current pipeline regressions also pass. No new canopy engine. |

## Exact interface changes

Production edits: `tools/plant_pipeline.py::Plant.s8`; `tools/plant_traits.py::plant_traits`, new `aggregation_audit` and `trait_area_provenance`, and `summarize`. Tests: new `tools/tests/test_area_review_alignment.py`; extended quantity refusal parametrization in `tools/tests/test_p1_area_evidence.py`.

The existing `plant-traits-1` and `plant-traits-2` numeric interfaces remain. Additive objects are explicitly versioned. No consumer is allowed to interpret the added provenance object as an `area_basis_id` or optical acceptance record.

| Input or output | Contract and unit |
|---|---|
| `Plant.cfg.area_policy` | Existing complete `IntegrationPolicy` dictionary; absent means retain legacy integration. Numeric integration settings are not biological defaults. |
| `Plant.cfg.view_grouping` | Existing explicit `centre_board_mm`, `top_elevation_gt_deg`, `source`; board frame, mm and degrees. Null threshold remains inactive. |
| `Plant.cfg.capture_style` | Required for v2 calibration compatibility; no inferred value. |
| `photos[].union_px` | Historical supported-depth pixel count, not the original entire mask union. Historical per-photo values remain untouched. |
| `photos[].area_v2` | Existing `original_union_px`, `used_union_px`, `missing_union_px`, projected/supported-projected cm2 and integration diagnostics. Incomplete selected coverage does not get a complete projected value. |
| `leaf_area_proxy_cm2`, `top_leaf_area_cm2` | Diagnostic projected cm2; whole-view union prevents duplicate pixel counting, not hidden-leaf recovery. A known-group mean may remain available as a partial diagnostic while aggregate status is incomplete. |
| `aggregation_audit` | `legacy_code`, `legacy_measured`, `footprint_code`, `footprint_measured`; each records group images, aligned values in cm2, missing images, unknown-group images, frame count and status. Legacy cells retain per-photo rounding. |
| `aggregation_status` | `complete_selected_projection`, `incomplete`, `no_frames`; completeness is limited to declared frame inventory and selected masks, never tissue completeness or metric validation. |
| `top_to_ring_diagnostic` | `value` in 1; null unless grouping and projected coverage support both means and denominator > 0. `mean_inclination_deg`, `leaf_angle_distribution`, `botanical_face`, `occlusion_correction` stay null. |
| `area_provenance` | Schema `plant-traits-area-provenance-1`; absolute source paths and SHA256, actual decoded mask-input digest per frame, calibration/pose source locators, view selection, capture time/phase when present, hull region hash and human-name status. Missing time/phase remains null. |
| `area_provenance.depth_method` | Existing per-mask hull percentile 20, minimum 5 points, declared hull dilation in px. This documents existing assumptions without endorsing depth accuracy. |
| `area_provenance.quantities` | Pixel count; projected proxy cm2; footprint cm2 and volume cm3 are occupancy envelopes; calibrated total cm2 is diagnostic. |
| `traits.csv` additions | `area_provenance_id`, `area_provenance_file`, `aggregation_status`, `estimated_area_status`; old numeric columns remain. |
| `traits_area_provenance.json` | Schema `plant-traits-provenance-index-1`, records keyed by exact evidence digest. Each schema `plant-traits-summary-provenance-1` stores observation key, entire trait digest/provenance, compatible calibration contract, measurement-file hash and join status. |
| Existing `area_basis.csv`, `downstream_leaf_surfaces.csv` | Unchanged contract in `tools/COMPOUND_MODEL.md`; supported one-sided physical area in cm2, located board-frame vertices in mm, exact source/patch identity. An evidence-complete record still has `validated_metric=false` and pending optical review. |

No new environment variables. Existing inputs/configuration locations remain unchanged. No write to `config/`, raw photos or human records.

New statuses describe projection availability, not new scientific reason codes: `policy_unavailable`, `not_enabled_without_area_policy`, `legacy_completeness_not_established`, `legacy_provenance_unavailable`, and `incomplete_grouping_or_projection_or_nonpositive_ring`. Existing surface reason codes remain: `physical_scale_evidence_unavailable`, `pose_evidence_unavailable`/`pose_evidence_rejected`, `one_sided_area_evidence_unavailable`, `partition_identity_review_unavailable`, `patch_geometry_support_incomplete`, `physical_tissue_geometry_source_unavailable`, `synthetic_not_real_area`.

Traits explicitly retain `identity_status=whole_view_union_not_leaflet_correspondence`, `partition_status=hull_regions_not_tissue_partition`, unknown occlusion and unquantified uncertainty. Trait true area, finite true-area interval and area-basis ID are null. Source files and identifiers preserve traceability; hashes alone do not establish calibration correctness or anatomical identity.

## Separate grouping and integrator evidence

The synthetic real-S8 fixture deliberately disagrees with filename grouping. Its ring means are:

| Grouping | Historical fx-squared | Undistorted footprint v2 |
|---|---:|---:|
| Code prefix | 12.8 cm2 | 16 cm2 |
| Measured camera elevation | 3.2 cm2 | 4 cm2 |

Measured top v2 is 16 cm2; top/ring diagnostic is 4. These are software fixtures, not plant estimates. A failed pose remains an explicit unknown frame and makes aggregate completeness false; its omission cannot silently produce a complete ratio. A selected structure-excluded frame makes the affected v2 mean unavailable while old diagnostic values remain recorded. A null grouping threshold leaves all measured groups unavailable.

The frozen pre-change `plant_traits.py` was executed on the same synthetic fixture. All pre-existing legacy fields and all pre-existing v2 fixture fields match exactly. New `top_photos` follows the measured group (regression checks two measured top photos versus one legacy-code top photo). `legacy_top_photos` preserves the old count. Source diffs and before hashes are saved alongside the audit.

The actual inspected `build/plant3d_regroup_20261004_01/config_dwt_t1.json` contains measured grouping but **no area_policy or capture_style**. Therefore its v2 S8 path is not enabled. The caller now accepts explicit policies; this delivery did not silently choose settings, edit configuration or rerun reconstruction. A grouping-only call records this limitation and keeps legacy numerics.

## Real data and numerical limits

Saved real diagnostic photo 27 remains a projected-area result with a failed pose gate, not a tissue-area measurement. Its unchanged record is copied into `real_evidence_snapshot.json` with its source hash in the verification/manifest. Actual capture time/phase and independent physical-area evidence remain unavailable.

Recovered fx = 3216.1097868596644 px and fy = 3276.6649334295307 px give fy/fx = 1.018828693851585. For equal depth and no distortion, fx-squared integration is about 1.88287% above the fx*fy denominator. This is an arithmetic diagnostic, not total real error or a certification factor. The illustrative 30 px dilation at 596 mm corresponds to about 5.5595 mm along x in the pinhole approximation. It does not establish actual local depth, distortion error or a safe smaller-dilation prior.

The existing six-family G calculation spans about 0.47245-0.54977 across zenith 52/55/57.5/60 degrees. This is analytic sensitivity, not measured plant accuracy. Unknown lambda and unbounded occlusion do not produce a finite true-area interval. A top image cannot resolve normal sign under abs(n dot v); one scalar top/ring ratio cannot identify a LAD.

## Area review A1 A7 dependency table

These IDs refer exclusively to the area review, not the completed physiological requirements.

| Area-review proposal | Readiness | Required corrected contract / evidence | Owner |
|---|---|---|---|
| A1 ring projection correction | Design pending | Explicit quantity, defensible G domain and lambda/occlusion bounds; identifiability and interval rules; reporting priority relative to A2. Unknown occlusion yields unavailable absolute total/finite interval. | Claude scientific specification; user priority decision |
| A2 per-leaf area and orientation fit | Design pending; prerequisites partly unavailable | Stable leaflet masks and cross-view IDs, calibrated measured poses, metric projection/depth observations, view coverage and conditioning/identifiability checks, antipodal-axis convention, undefined-azimuth handling, residual/failure/uncertainty rules and reproducible tests. Tau=.9 not adopted. Position, outline and curvature are separate missing outputs. | Claude contract; matcher decision open |
| A3 raycast/refit occlusion | Design pending | Independently sourced located centroid/depth, outline/mesh/curvature, metric frame/scale, correspondence and surface topology; convergence tolerance, iteration limits, divergence/failure behavior and independent validation. A2 area+angles alone cannot supply these. | Claude geometry/scientific contract |
| A4 curvature factor | Design pending | Applicable shape/curvature observations, coefficient domain and independently checked area references; no generic multiplier adopted. | Claude |
| A5 hull and low-dilation depth | Diagnostic demotion already present; prior design pending | Hull is an envelope. A low-dilation depth prior needs a supplied executable definition, missing-support behavior and independent validation; dilation reduction is not proof of correct depth. | Claude |
| A6 top/ring | Diagnostic implemented; inference unavailable | Same definition/selection, poses and projected coverage for whole-plant ratio; matching not inherently required. Mean-angle/LAD inference needs additional evidence and an identifiable forward/inverse contract. | P1 diagnostic; Claude scientific inference |
| A7 separation and provenance | Implemented / existing gates preserved | Separate pixels, projected proxy, hull diagnostic, evidence-supported one-sided tissue and calibrated estimates; preserve methods/units/provenance and unavailable states through export. | P1; P2/P3 consumption separately scoped |

Three decisions remain open: A1/A2 reporting priority, leaflet-matching method and calibration strategy. Restricted image radius r<0.4 is not a calibration acceptance gate. Independent scan/area references and repeat observations have not been supplied. No missing values were synthesized from templates.

The five named companion files were absent in the bounded inspected locations `C:/Users/sho36/Downloads/` and `build/plant3d_area_review_20261004_01/`: `plant3d_area_review_inventory.csv`, `plant3d_area_review_evidence_register.csv`, `plant3d_area_review_error_budget.csv`, `error_budget.svg`, `estimator_geometry.svg`. This is not a claim about every disk location. No simulation source was supplied; reported synthetic MAEs remain unreplicated.

## Canopy and P2 handoff

Read-only checks on `build/light_growth_science_20261004_01/package/` and its saved `P1_in_canopy` / `P1_COPY_in_canopy` outputs verified all 10 CSV partitions exactly. Each split retains 576 light-sample rows; parent has 1344. IDs, source hashes, unavailable associations and synthetic status survive exact row equality. Full-canopy shading remains attached to each split.

Forward/inverse positions agree within 9.4361e-12 mm; normal-vector rotation agrees exactly at stored precision. Quadrature weights counted once per spatial sample give 0.3204 m2 for P1 and its explicit P1_COPY instance, and 0.16 m2 for P2, matching source triangles. Lamp/time repeats are not additional tissue; P1_COPY is an explicit distinct synthetic placement, not a second observed plant. Historical artifact checks do not assert that an older frozen package uses the latest consumer schema. Current `test_complete_direct_package_and_split` independently verifies today's package path.

P2 manifest lists diagnostic real inputs, required existing surface contracts, unavailable scale/pose/area/time/identity/face evidence, unchanged identity keys, rigid placement rules and the three open design decisions. Its independently supported **real optical surface list is empty**. Geometric normal sign remains a mesh convention. P2 owns optical acceptance and any separately authorized adapter; P4 owns physiological face policy. No normal or projected area is promoted to an illuminated biological face.

At finalization P2 had delivered `CODEX_P2_AREA_REVIEW_EXECUTION_2026-10-05.md` and `optical-geometry-evidence-1`. Read-only review confirms agreement with this manifest: geometric computability is distinct from physical PPFD eligibility; missing A2 position/shape stays unavailable. P2's bridge/consumer/helper edits preceded the final P1 test run. Their current report/helper hashes are linked in the manifest. P1 did not modify these files or repeat P2's completed suite.

## Validation commands and evidence

Run from the project root:

```powershell
python -X utf8 -m pytest tools/tests/test_area_review_alignment.py tools/tests/test_plant_traits.py tools/tests/test_leaf_area_geometry.py tools/tests/test_p1_area_evidence.py tools/tests/test_compound_surface.py tools/tests/test_plant_pipeline_tools.py tools/tests/test_light_growth_bridge.py::test_transform_points_vectors_and_second_moment_roundtrip tools/tests/test_light_growth_bridge.py::test_complete_direct_package_and_split tools/tests/test_light_growth_bridge.py::test_reviewed_observed_direction_area_and_regions tools/tests/test_canopy_light.py -q --junitxml=build/area_review_alignment_20261005_01/P1/final_pytest.xml
python -X utf8 build/area_review_alignment_20261005_01/P1/verify_delivery.py
```

Final results: 119 passed in 20.26 seconds; verification 27/27. The CLI summary test invokes `python -m tools.plant_traits --traits ... --out ... --measurements ...` on an explicitly synthetic S8 result and checks both CSV and JSON provenance hashes. Existing area evidence tests omit scale/pose/area/identity separately, preserve diagnostics, reject generated and nonphysical quantities, and distinguish absent science from tampered evidence. Added area/angle-only geometry and normal-sign cases pass.

`leaf_area_geometry.py`, `plant_structure.py`, `compound_surface.py` and `COMPOUND_MODEL.md` match their before hashes. Saved historical inputs/outputs match their audit-start hashes. The source backup comparison, not Git history, establishes the production baseline in this workspace. No completed Day-1 or reconstruction campaign was repeated, no GPU work ran, and no other project's runtime changed.
