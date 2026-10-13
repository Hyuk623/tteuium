# Multiview diffusion completion feasibility and integration specification

Date: 2026-10-03. Author: Codex. Recipient: next implementation session and Claude scientific review.

## Request and execution brief

Execute the specification task in `handoff/CLAUDE_MULTIVIEW_DIFFUSION_COMPLETION_PROMPT_2026-10-03.md` after the user-requested first-label detection-area normalization. The source prompt explicitly scopes its present task to feasibility review and proposed integration contracts. This document is the deliverable for that scope; diffusion adapter implementation, checkpoint execution, training, remote jobs and optical calculations are future actions. The independently authorized detection-only ratio implementation is reported separately and must not be described as diffusion implementation.

Inspect current project interfaces and official architecture/code/weight sources. Preserve source files and observed/generated provenance. Define a backend-neutral interface, leakage-safe splits, normalized-area connection, candidate composition, evaluator/viewer contract and future checks. No protected schema or scientific threshold changes. Record unresolved choices rather than assert a permitted or validated backend.

## Feasibility decision

A reproducible detection-only relative-area baseline is available now. Diffusion can be specified as a separate hypothesis branch, but this review identifies no execution-ready backend satisfying the standing project restriction to user-data-tuned models. Public model availability is not project eligibility. The first-leaf convention fixes a dimensionless reference; it supplies neither metric depth nor hidden anatomy.

The following facts were inspected from official sources on 2026-10-03. Published capabilities and resource statements are not local performance measurements. Repository licences are reported as metadata, not as a conclusion that all dependent checkpoints have identical terms.

| Architecture | Inspected capability and assets | Integration assessment and unresolved items |
|---|---|---|
| CAT3D | The [official project](https://cat3d.github.io/) describes conditioning on multiple images and camera rays, followed by NeRF or Gaussian reconstruction. No official code/checkpoint download was identified on that page. | Conceptually suited to top-plus-side conditions. Usable checkpoint, licence and target-hardware memory remain unverified. Appearance reconstruction is not a leaf-triangle decomposition. No executable backend selected. |
| MVD-Fusion | [Official README](https://github.com/zhizdev/mvdfusion) describes single RGB input, multiview RGB-D outputs, and MVD/Zero123/CLIP weights. [Inference config](https://raw.githubusercontent.com/zhizdev/mvdfusion/main/configs/mvd_gso.yaml) sets input_batch_size to 1. Repository [licence](https://raw.githubusercontent.com/zhizdev/mvdfusion/main/LICENSE) is MIT. The [weight landing page](https://huggingface.co/zhizdev/mvd-fusion) has no model card. | A top-only research candidate, not a demonstrated multiview-input adapter. The [GSO loader](https://raw.githubusercontent.com/zhizdev/mvdfusion/main/dataset/gso_test.py) uses fixed synthetic cameras, PyTorch3D and normalized parameters; these cannot substitute for board poses. Full checkpoint terms, numerical depth meaning and target inference memory remain unresolved. The weight file listing could not be fetched in this review; no download was attempted. |
| Wonder3D | [Official code](https://github.com/xxlong0/Wonder3D) exposes single-image RGB/normal generation and separate reconstruction, using six orthographic views. The [configuration](https://raw.githubusercontent.com/xxlong0/Wonder3D/main/configs/mvdiffusion-joint-ortho-6views.yaml) specifies 256 by 256 inputs. [Code licence](https://raw.githubusercontent.com/xxlong0/Wonder3D/main/LICENSE) is MIT. | Its perspective/orthographic mismatch needs an explicit conversion assessment; normals alone are not metric vertices. Author guidance reports sensitivity to occlusion and facing direction. Precise target VRAM and full checkpoint/dependency terms are unverified; model-card raw retrieval failed. It does not directly consume this program's arbitrary top-plus-side photographs. |
| ViewFusion by Yang et al. | The [CVPR paper](https://openaccess.thecvf.com/content/CVPR2024/html/Yang_ViewFusion_Towards_Multi-View_Consistency_via_Interpolated_Denoising_CVPR_2024_paper.html) describes interpolated denoising for multiple conditions. [Official README](https://github.com/Wi-sc/ViewFusion) uses Zero123 and reports about 23 GB VRAM for its limited-window setup. [Code licence](https://raw.githubusercontent.com/Wi-sc/ViewFusion/main/LICENSE) is Apache 2.0; the [Zero123 card](https://huggingface.co/cvlab/zero123-weights) displays MIT metadata and use limitations. | A research candidate for multiview conditioning, with no demonstrated local integration. The README-linked real-image script path returned 404 during inspection, so exact camera adaptation remains unresolved. Author VRAM is not a guarantee for this workload. Reusing a public Zero123 checkpoint does not satisfy the project's tuned-model policy. |

Recommendation, as an engineering inference: retain a backend-neutral request/import boundary and the observed mask ratio baseline. Keep backend selection null until a compatible checkpoint, supported conditioning contract and camera/depth mapping are supplied. Do not obtain a nominal implementation by discarding side images or passing protected observations through an incompatible model. None of these sources demonstrates reconstruction accuracy for these dwarf tomato plants.

## Verified existing integration points

| Local source | Inspected behavior | Proposed use and owner |
|---|---|---|
| `tools/detected_leaf_area.py::run` | Reads saved masks or explicit boxes; outputs per-image pixel area ratios and hashes without geometry or model execution. | Codex: attach the ratio CSV/audit as an observed image-space baseline. This is the implemented part of the current user request. |
| `tools/plant_pipeline.py`, S3 and S8; `tools/plant_auto.py` | Existing photo/structure/traits stages; S3 also calls stem_completion. | Codex: future optional branch from an explicitly selected saved run. Leave default stage behavior intact. Stem completion is not diffusion. |
| `tools/plant_structure.py::Cameras` | OpenCV projection, inverse-distorted rays and camera centres; accepts solved and solved_marker_corners. | Reuse fixed real camera projection. Candidate adapter must explicitly declare which observed consumers support each pose status. |
| `tools/leaf_area_geometry.py::photo_area_v2`; `tools/leaf_area_compare.py` | Metric projected proxy depends on hull depth and calibration. | Preserve separately. Pixel normalization does not make this a detection-only formula or justify generated depth substitution. |
| `tools/leaf_surface_compare.py::compare_patch` | Requires at least two distinct real fit views, confirmed point/patch evidence and solved poses. | Reuse eligible observed mesh/plane results; baseline can remain unavailable. Never insert generated landmarks as observations or relabel rescued poses. |
| `tools/compound_surface.py::audit_surface` | Requires confirmed physical patches, accepted topology and at least two real support views; returns partial area and false physical/optical flags. | Keep for observed surfaces. A distinct hypothesis audit is needed for generated geometry. |
| `tools/leaf_surface_compare.html` | Reads embedded __SURFACE_DATA__ payload, patches, methods, source images and projections. | Future Codex viewer adapter must add a versioned candidate layer and explicit import. An adjacent candidate CSV alone cannot render it. |
| `tomato3d/io/schemas.py` | Exact triangle columns and source/normal enums. | Read/import unchanged; Claude owns core changes. No core change is required for candidate storage using existing assumed provenance plus mandatory sidecar. |
| `tools/plant_light_bridge.py`; `tools/groimp_density.py::surface_gate`; `tools/hierarchical_light.py` | Optical gate checks review/hash/variant/date, normal knowledge and receiver geometry. Non-synthetic assumed/simplified geometry is blocked. | Keep optical export blocked. A future real diagnostic hypothesis route needs its own explicit reviewed contract; labelling real hypotheses synthetic is not a workaround. |

No `tools/multiview_completion.py` exists at inspection. Proposed functions below are not delivered code. Core schema changes, if later needed, belong to Claude; configs remain human-owned. This review changes no pipeline, geometry viewer or optical gate.

## First leaf convention and comparison contract

For an image v and source label i, define P(i,v) as the saved visible-mask foreground count in original pixels. Fix r(1,v) = 1 when the first source label has positive available count, and calculate r(i,v) = P(i,v) / P(1,v). Keep P and the reference label/hash in the result. A zero/missing/rejected reference makes ratios unavailable; do not choose the next label. A new detector ordering creates a different reference revision and cannot be compared silently with the old revision.

This per-image reference does not identify the same physical leaf in another view. Persistent cross-view normalization requires an explicit physical-ID mapping, unavailable here. The reference is not inferred from an L01 height proposal. Unknown date remains null; date-dependent temporal comparisons remain unavailable. Mask changes invalidate ratios through source hashes.

For future candidate rendering, use the same real camera and source reference ID where a reviewed or explicitly proposed candidate-to-observation mapping exists. Compute candidate visible projected pixel ratios separately, then report signed and absolute differences from observed ratios; unmatched identities stay unmatched. Candidate r(1,v) also normalizes to 1 and is therefore not evidence of fit quality. Report raw silhouette fit and reference-mask fit alongside ratios. Do not optimize with held-out labels or renormalize against whichever candidate leaf happens to match best.

A hypothetical nonmetric surface may additionally report its own surface-area ratios, labelled `candidate_surface_relative` with its own reference face set and coordinate units. This is not the observed `detected_visible_mask` ratio. Do not compare projected ratios with surface-area ratios as though they measure the same quantity. No normalized coordinates enter `_mm` fields; no absolute cm2 is filled from the convention 1.

## Proposed function and output contracts

All paths resolve relative to the declaring JSON. Source manifests are immutable and content-hashed. Outputs are new directories below build. Missing numerical values are JSON null or CSV unavailable. Parsing/hashes/contracts may pass while scientific or backend availability remains false.

| Proposed function | Inputs | Outputs and behavior |
|---|---|---|
| audit_request(request_path: Path) -> dict | Versioned request, file references, split/dependency/model policies | Read-only statuses, blockers, verified references and conditioning closure. No checkpoint loading or network execution. |
| prepare_request(request_path: Path, out: Path) -> dict | Audited request | Frozen request/manifest, input registry and ratio references. May prepare a non-executable package with explicit blockers; must not produce a runnable backend job when blocked. |
| import_candidate_bundle(request_path: Path, candidate_path: Path, out: Path) -> dict | Frozen request plus externally produced candidate manifest, geometry and provenance | Structural/numerical checks and immutable candidate copy. Reject mismatched request hash, missing sidecar, inconsistent units/IDs or undeclared dependencies. Does not create observations. |
| evaluate_candidates(prepared_path: Path, candidate_refs: list[Path], evaluation_plan: Path, out: Path) -> dict | Frozen candidate set, selection rule and allowed evaluator inputs | view_metrics.csv, area_hypotheses.csv and evaluation audit. Unsupported alignment/visibility/identity yields unavailable metrics with reasons. No generation, candidate fitting or light transport. |
| export_review_bundle(result: Path, out: Path) -> dict | Frozen result and explicit image/candidate references | Versioned embedded viewer payload and exports, provenance labels and unavailable states. Display selection never alters scientific eligibility. |

These functions belong in a future Codex-owned `tools/multiview_completion.py`, using common file/CSV/output helpers and existing projection/schema contracts. CLI verbs should map directly to audit, prepare, import, evaluate and review. No command implies a backend run. Avoid duplicating the detector, SAM, photon solver or annotation application.

## Manifest and dependency specification

Proposed schema `multiview-completion-request-1` requires:

- Identity: request_id, plant_id, session_id, capture_date (nullable with provenance), deployment_mode (`top_only` or `multiview`), source_run path/hash and selected movement_group_id with evidence. Unknown rigid-group compatibility blocks geometric composition, not per-image mask ratios.
- Observation registry: each image_id, role, path/hash, original width/height, pixel transform, mask references/review/visibility, source annotation IDs, camera source/quality and dependencies. Measured top/side grouping must have source and thresholds; no grouping from photograph numbers.
- Asset dependency graph: asset_id, path/hash, kind, parent_asset_ids, source_image_ids, source_plant_ids, producer/version and provenance status. Include labels, corrections, hulls, depths, checkpoint training data and preprocessing statistics. Detect cycles and missing parents; unknown closure blocks leakage-sensitive use.
- Split: condition_image_ids, ranking_image_ids, evaluation_image_ids and final_evaluation_plant_ids. Ranking is confined to allowed fit observations and is disjoint from held-out views. Top-only conditioning contains only declared top evidence; side-derived structure, identities, masks or poses remain evaluator-only. Legitimately deployment-known rig calibration/virtual target poses need separate provenance.
- Backend: selected_backend (nullable), checkpoint path/hash (nullable), dependent checkpoints, licence evidence, trained_on_user_data evidence, training plant split and required/supported condition channels. No supported-channel claim from a generic tensor alone. Unknown or incompatible training split prevents a plant-disjoint claim.
- Geometry: native representation, coordinate frame, projection type, camera transform direction/axes, unit/scale provenance, depth meaning, normal mapping and original-to-model pixel transformation. Missing entries block the corresponding conversion rather than preparation of the report.
- Policies: fixed sample-selection rule, composition mode, independently supplied numerical tolerances and visibility semantics. Scientific acceptance thresholds remain null until reviewed. Budgets declare seeds, max_candidates, steps, VRAM, wall time and output limit before any later model execution; no defaults are invented here.

A shape-only request example, deliberately not execution-ready:

```json
{
  "schema": "multiview-completion-request-1",
  "request_id": "draft_detection_relative_baseline",
  "plant_id": null,
  "session_id": null,
  "capture_date": null,
  "deployment_mode": "multiview",
  "source_run": null,
  "movement_group_id": null,
  "observations": [],
  "assets": [],
  "split": {
    "condition_image_ids": [],
    "ranking_image_ids": [],
    "evaluation_image_ids": [],
    "final_evaluation_plant_ids": []
  },
  "relative_area": {
    "scope": "detected_visible_mask",
    "reference_rule": "first_manifest_label_per_image",
    "reference_value": 1,
    "units": "dimensionless",
    "source_csv": null,
    "source_audit": null
  },
  "backend": {
    "selected_backend": null,
    "checkpoint": null,
    "model_use_eligible": false,
    "execution_status": "backend_unavailable"
  },
  "geometry": {
    "frame": null,
    "units": null,
    "depth_meaning": null,
    "metric_scale_source": null
  },
  "policies": {
    "composition": "alternative_hypothesis_only",
    "sample_selection": "retain_all_declared_seeds",
    "scientific_acceptance": null
  },
  "budgets": {
    "max_candidates": null,
    "seeds": [],
    "steps": null,
    "max_vram_gb": null,
    "max_wall_time_s": null
  },
  "validated_metric": false,
  "suitable_for_ppfd": false
}
```

An audit of this example must report missing identity, observations, movement evidence, backend, scale and execution budgets. The nulls are not valid execution inputs. No real fit/held-out split is selected by this example.

## Geometry mapping and composition

The existing camera convention is X_camera_mm = R * X_board_mm + t_mm, with the row-array implementation X @ R.T + t. Camera centre is -R.T * t. Reuse inverse distortion for original-image rays. Future metric depth backprojection must distinguish camera-Z depth from distance along a unit ray, then apply the inverse real camera transform. Model resizing/cropping/undistortion is a derived transform with its inverse and hashes; source calibration stays unchanged. Validate against permitted measured anchors, never evaluator-only targets.

Backend canonical coordinates require an explicit axis/handedness map, rotation, translation and metric scale supported by allowed observations. Setting the first leaf area to 1 cannot determine this mapping. An orthographic model and a perspective calibrated photograph are not interchangeable by changing focal length. If conversion cannot be justified, keep native coordinates and block metric triangle export.

For metric candidate triangles reuse the exact `LEAF_SURFACES_CSV_COLUMNS`: plant_id, session_id, geometry_variant_id, geometry_source, organ_class, organ_id, leaflet_id, triangle_id, the nine v0/v1/v2_x/y/z_mm fields, normal_convention. The face key is (plant_id, session_id, geometry_variant_id, organ_id, leaflet_id, triangle_id). Give each condition/candidate a distinct variant. Generative faces use geometry_source=assumed with mandatory full-key sidecars; normal_convention=unknown unless biological orientation has independent evidence. A triangle's geometric winding does not establish the adaxial side.

Default proposed composition is `alternative_hypothesis_only`: preserve immutable observed surfaces and show each candidate separately. This avoids pretending a full generated plant is disjoint completion tissue. A future `completion_only_disjoint_union` requires explicit observed-face mappings, seam correspondences, overlap/intersection checks and supported scale; failed checks leave composition unavailable. No clipping, replacement, refitting, vertex averaging or area summation with observed tissue happens implicitly. Hidden topology and compound membership remain proposed.

Each candidate sidecar must contain candidate/request IDs and hashes, the full face keys, seed, backend/checkpoint/code versions, full conditioning closure, per-face observed/derived/generative origin, source links, physical identity status, scale provenance, unknown regions and composition state. Missing, extra or duplicate keys fail import. Observed anchors retain their original file bytes/IDs and a separate immutable mapping; generated faces never receive observed support votes.

## Evaluation and viewer adaptation

Compare four principal conditions: top-only observed baseline, top-only generation, selected top-plus-side observed baseline, and exactly the same multiview inputs with completion. Additional real views form a separate evidence condition. With no permitted backend, generated arms are not executed; with no confirmed points, metric observed reconstruction is unavailable. The implemented pixel baseline remains usable in either case.

Future fit and evaluation rasters must classify known visible tissue, confirmed visible background, occluded and unknown pixels. Automatic mask absence is not confirmed background. Render each complete frozen candidate scene with depth/occlusion. Compute silhouette IoU only over valid pixels E: |candidate intersect observed intersect E| / |(candidate union observed) intersect E|; empty denominator is unavailable. Report the denominator and excluded counts. Uncertain automatic masks can support an explicitly labelled detector-agreement metric, not independent anatomy accuracy. Partial geometry must not be scored as a full-scene renderer.

Landmark RMS uses confirmed held-out physical correspondences only; unlinked instance masks cannot create landmark matches. Report missing/excess/merged/split organs only where evaluation identities support these counts. Depth/surface/absolute-area error requires independent matching references. Dimensionless first-leaf ratio differences are image-space consistency metrics; view angle, hidden tissue and detection bias remain. Freeze all candidates and the fit-only selection rule before held-out scoring. Retaining all configured seeds is the default proposed reporting rule, not selecting the best held-out sample.

Proposed numerical tables:

| File | Required fields beyond plant/session/request identity |
|---|---|
| view_metrics.csv | candidate_id, condition_id, split, image_id, metric, value, units, denominator, excluded_pixels, reference_label_id, identity_status, status, reason |
| area_hypotheses.csv | candidate_id, component_id, origin, area_scope, coordinate_units, area_value, reference_component_id, relative_area, coverage_status, composition_status |
| candidate_audit.json | schema, source hashes, constraints, leakage status, scale/identity/topology availability, stage statuses, blockers, validated_metric=false, suitable_for_ppfd=false |
| completion_manifest.json | frozen request, backend and dependency evidence, seeds, sample rule, transforms, split hash, environment/code versions and stage outcomes |
| candidate_provenance.json | complete face-key joins and the evidence listed above |

Extend the existing embedded viewer through an explicit future `completion-view-1` payload containing request/audit references, observed-baseline reference, candidate list, per-candidate renderable geometry/frame/units, per-view projected layers and metrics. Validate the payload before rendering. Separate original photographs, observed masks/surfaces and proposed hidden geometry visually; retain unknown regions, failed candidates and proposed identity labels. Candidate selection must preserve the original reference leaf and units. A nonmetric candidate uses a separate panel/frame, never an overlay pretending to share board millimetres. Show the relative-area table even if 3D is unavailable. UI changes are not implemented in this specification task.

## Future implementation checks and remaining scientific decisions

First implement local request auditing/preparation, then imported-candidate validation, then a visibility-aware evaluator and the versioned viewer layer. Backend execution remains a separate scoped step. Keep existing geometry/light modules unchanged unless an explicit reviewed owner change is needed.

Planned checks, not executed diffusion tests:

1. Original-pixel crop/resize/undistortion and pose/depth conversion round trips; reject absent scale and incompatible projection. Exercise solved_marker_corners without changing its source status.
2. Plant/session/date/movement isolation; full dependency graph leakage through hulls, learned masks, checkpoint splits and cached geometry; top-only mode cannot read side-derived fitting inputs.
3. Missing/zero first leaf, mask/bbox scope separation, stable reference revisions and cross-view identity unavailability. Generated-image masks never become observed pixel baselines.
4. Immutable observed anchors and exact triangle face keys; reject missing/tampered/duplicate sidecars, variant collisions, unsupported enums and normalized coordinates presented as mm.
5. Holes, disconnected patches, folded thin tissue, occluded/unknown pixels, empty metric denominators and unsupported whole-scene rendering. Generated views contribute no observation-support votes.
6. Full-surface versus completion-only semantics, seam/duplicate/intersection failures and unavailable assembly. No double-counting or destructive anchor edits.
7. Deterministic preparation and stale-dependency detection; preserve all seeds and freeze candidate selection before evaluator access. Synthetic fixtures remain excluded from scientific metrics.
8. Viewer provenance/frame labels and unchanged optical gates; assumed real geometry remains blocked by current surface_gate. No implicit checkpoint, upload, training or light execution in any adapter command.

Claude review remains necessary for biological topology/composition, practical scientific acceptance thresholds and uncertainty interpretation. Backend compatibility, full weight/dependency terms, measured camera conversion and resource budgets remain unresolved. The user already confirmed the absence of extra correspondence/independent area files; do not repeat that search. Relative normalization completes the requested preliminary calculation without claiming these scientific gaps are resolved. Seed spread is model sensitivity, not a calibrated confidence interval. Existing future-growth work is outside this current-plant completion scope.

## Delivery status

Delivered the feasibility assessment, inspected integration map, proposed functions and I/O, manifest/split/composition specification, evaluator/viewer adaptation and future tests. The source prompt is unchanged; this companion specification adds the new first-leaf pixel-ratio decision and a current official-source feasibility assessment. This is a Codex-authored engineering proposal, not completed Claude scientific review.

No diffusion adapter, notebook, backend run, reconstruction, training, upload or optical calculation was created or executed for this specification task. The separate detection-ratio implementation and its focused tests are real delivered software, with outcomes recorded in the leaf-area execution handoff. A usable diffusion backend and demonstrated hidden-leaf/physical accuracy are not claimed.

Static delivery verification: the JSON shape example parses; 13 referenced local source files exist; 7 named source symbols were checked through AST inspection; the proposed diffusion adapter is absent as stated. This is document/source verification, not a diffusion test run. Official web sources were inspected without downloading weights. The companion detection calculation exported 1318 observations over 54 photographs with 54 reference ratios equal to 1; no generative result is included.
