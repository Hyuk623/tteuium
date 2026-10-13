# Claude prompt for tomato multiview diffusion completion

Revision: 2026-10-03, reviewed against the current 3D program at the user's request. This revision changes the prompt only. No adapter, notebook, inference, reconstruction, training or optical calculation has been implemented or executed. Source-review findings are recorded in `handoff/CODEX_MULTIVIEW_COMPLETION_PROMPT_REVIEW_2026-10-03.md`.

## Task and scope

Prepare an integration specification for an evidence-constrained diffusion pilot that connects top and side photographs of the same tomato plant, then proposes geometry for occluded regions. Place it as an optional candidate branch alongside the existing 3D reconstruction program. The purpose is to test whether generative completion helps recover structure relevant to leaf area and light distribution, not merely to generate convincing pictures.

Distinguish two deployment questions:

1. **Multiview completion:** top plus selected real side/oblique images are available at inference. Use all of those observations as conditions.
2. **Top-only inference:** side images are available during development or as withheld evaluation targets, but not at inference. Learn/propose likely side and hidden structures from the top image. This is a harder, separate experiment and cannot borrow target side images, their masks, landmarks or derived geometry.

Current scope is document review and specification only: deliver a technical feasibility assessment, the existing-code integration map, proposed adapter/evaluation contracts and a future test plan. Do not create code or notebooks, install dependencies, download weights, run models, reconstruct plants, train, upload, launch remote jobs or execute light calculations under this review instruction. The later-stage implementation deliverables below are a plan, not authorization to execute them now. A separate user instruction to implement may activate the bounded adapter work; model execution/training still needs its stated scope and budgets.

## Read and reuse current work

Project: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.

Read working agreements, latest LOG/TODO and these handoffs before editing:

- `handoff/CLAUDE_TO_CODEX_MASTER_HANDOFF_2026-10-03.md`
- `handoff/CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md`
- `handoff/CODEX_LEAF_AREA_3D_EXECUTION_2026-10-03.md`
- `handoff/CODEX_LIGHT_IO_SUMMARY_2026-10-03.md`
- `handoff/CLAUDE_PLANT_3D_LIGHT_CONNECTION_PROMPT_2026-10-03.md`
- `handoff/CODEX_INTEGRATED_TOMATO_SIMULATOR_PROMPT_2026-10-03.md`

Later source files may supersede older handoff descriptions. Inspect current interfaces before proposing another module. Reuse masks, physical identity review, fixed camera projection, local surface charts, geometry comparison viewers, optical eligibility and light adapters. In particular, inspect `tools/leaf_surface_compare.py`, `tools/leaf_area_geometry.py`, `tools/compound_surface.py`, `tools/plant_light_bridge.py` and `tools/hierarchical_light.py` when present.

The latest leaf-area handoff reports a local-patch representation preserving holes, disconnected tissue and folds, but no reviewed curved-fitting contract, confirmed pilot correspondences or independent area references. Do not replace these missing inputs with generated evidence or repeat broad searches for already-confirmed absences.

Preserve source images, human labels, original-pixel coordinates, identities, masks, cameras, weights and historical runs. Follow file ownership and active work boundaries; no concurrent edits or GitHub push. English handoff/code, Korean UI and user explanation. New outputs belong to fresh `build/` folders. Keep existing tuned detectors/SAM intact; a generative candidate is a separate research component, not a replacement for them.

## Connection to the current 3D program

The code inspected for this revision establishes the following integration points. Recheck them before any future implementation; they are not claims that diffusion is already connected.

| Existing component | Current behavior | Proposed connection |
|---|---|---|
| `tools/plant_auto.py` and `tools/plant_pipeline.py` | Photo/mask workflow and S0-S8 orchestration; S3 calls `tools.plant_structure`; S8 calls existing traits | Consume an explicitly selected saved run through a separate optional branch. Do not insert generated views into S0/S1/S2 or replace S3/S8 defaults. |
| `tools/plant_structure.py::Cameras` and `build` | Board-pose projection, structure/hull and axis/region estimates | Reuse selected capture metadata and supported existing structure as read-only context, subject to the inference-view split. A hull/compound region is not leaf tissue. |
| `tools/leaf_area_geometry.py::photo_area_v2` and `tools/leaf_area_compare.py::run` | Versioned projected-area calculations on real saved masks and hull depth | Keep measured/proxy comparison outputs unchanged. Generated masks or candidate depth must not enter the calibrated area route. |
| `tools/leaf_surface_compare.py::run` / `compare_patch` | Fixed-camera reconstruction from confirmed physical point IDs with at least two fit views; mesh/plane comparison and local charts | Reuse the observed baseline and its artifacts. This entry point is not a generic generated-mesh importer and cannot serve a top-only reconstruction by inventing a second observed view. |
| `tools/compound_surface.py::audit_surface` | Supported partial-area audit requiring reviewed identity/topology and observed support | Preserve this audit for observed surfaces. Generated candidates require a distinct hypothesis-validation report; they must not gain observed-support eligibility. |
| `tools/leaf_surface_compare.html` | Embedded report-driven surface viewer | Propose a separate versioned candidate payload/layer and an explicit viewer adapter. Dropping an extra CSV next to the viewer does not integrate it. |
| `tools/plant_light_bridge.py::audit` | Snapshot/date/identity and accepted-surface/light-case checks | Keep downstream optical eligibility blocked until an explicit compatible diagnostic contract exists. Do not toggle review flags to force import. |

Proposed flow:

```text
Saved real capture, reviewed masks and identities
    -> allowed-view and movement audit
    -> existing observed 3D baseline, when eligible
    -> separate completion request
    -> unexecuted backend boundary during this review
    -> future imported hypothesis bundle
    -> candidate geometry/constraint checks and viewer layer
    -> frozen held-out evaluation
    -> optional separately eligible optical diagnostic export
```

A missing observed 3D baseline does not prevent writing the request/audit contract, but it must not become a fabricated anchor. Preserve the existing pipeline as usable independently. Future selection of this branch must be explicit, default off, and a blocked candidate must not mark the measured pipeline complete or failed incorrectly. The source code's `stem_completion` proposals are a different feature, not a diffusion backend.

The master handoff records a no-base/untuned-model restriction. Listing a public pretrained diffusion model does not establish an exception. Report model-policy compatibility explicitly; where no permitted backend exists, the result is an interface specification with backend execution unavailable, not an implicit plan to use an unapproved checkpoint.

## Scientific boundary

Label three distinct cases:

- Visible in the top and/or a real side image: observed image evidence is available.
- Occluded in one image but visible in another: multiview reconstruction can use that real observation.
- Hidden in every available image: geometry is prior-conditioned completion, not a measurement or uniquely recovered truth.

Diffusion does not automatically establish physical leaflet identity. Camera calibration supplies projection relationships and scale evidence, not organ identity. Generated images, predicted depth, masks extracted from generated images and surfaces fitted to them share generative provenance. They must never become independent camera observations, ground truth or extra triangulation support votes.

A model can generate mutually consistent views of the wrong plant. Reprojection agreement is necessary evidence, not proof of correct hidden geometry. Failed camera-quality gates and unknown absolute scale remain failures even if the generated images look good.

## Reference architectures to assess

Use primary references and inspect available official code, checkpoint licences, supported input views/poses, camera convention, output representation and practical memory requirements before selecting a backend.

- CAT3D: multiple observed images with camera conditions and novel-view generation. Research architecture reference; do not assume a downloadable, usable checkpoint exists. https://cat3d.github.io/
- MVD-Fusion: single-input RGB to consistent multiview RGB-D generation. It is not automatically a multiview-input model. https://openaccess.thecvf.com/content/CVPR2024/html/Hu_MVD-Fusion_Single-view_3D_via_Depth-consistent_Multi-view_Generation_CVPR_2024_paper.html
- Wonder3D: RGB/normal multiview generation. Its paper explicitly discusses thin-structure and severe-occlusion limitations. https://openaccess.thecvf.com/content/CVPR2024/papers/Long_Wonder3D_Single_Image_to_3D_using_Cross-Domain_Diffusion_CVPR_2024_paper.pdf
- ViewFusion: extending single-view-conditioned generation to multiple-view conditioning without additional fine-tuning. Assess implementation compatibility, rather than assuming it is a drop-in adapter. https://openaccess.thecvf.com/content/CVPR2024/html/Yang_ViewFusion_Towards_Multi-View_Consistency_via_Interpolated_Denoising_CVPR_2024_paper.html

These references support architectural possibilities, not demonstrated dwarf-tomato reconstruction accuracy. Do not invent a benchmark result or GPU/runtime estimate. If available models cannot consume the required observations or meet the standing model-use restrictions, report that and prepare the interface; do not silently discard side views or claim a backend is integrated.

The present integration review does not revalidate checkpoint availability, licences or hardware requirements. A future model-feasibility assessment must verify them from official sources and mark uninspected items unknown. Separate conceptual suitability, downloadable assets, supported conditioning and permission to use the model.

## Proposed pilot workflow for later implementation

### 1 Freeze observations and splits

Select existing plants/sessions with top and side images from one unchanged plant configuration. Exclude incompatible movement groups; dwt_t3 has known movement and failed alignment cases. Use measured poses and explicitly supplied view grouping, not image numbers or nominal angles.

Prepare manifests containing plant/session/date, real image and mask hashes, camera intrinsics/distortion/pose, original-pixel transform, visibility, available confirmed identities and reference counts. Do not force uncertain membership or create organs to match a count JSON.

Separate model development, fitting views, withheld real views and independent geometry references. Freeze these before candidate selection. Hold out entire plants, including all their dates, for final evaluation. Same-plant withheld views are reconstruction checks, not unseen-plant generalization evidence.

Any input derived from photographs must be computed only from that condition's allowed input views. A top-only condition cannot use an all-view hull, side-derived pose alignment, segmentation, count corrections or geometry. Declare separately any common measured rig calibration and user-supplied count information legitimately available at deployment.

Enforce this on the dependency closure, not just the final image list: the selected `structure.json`, masks, depth anchors, memberships, labels, learned checkpoint and any preprocessing statistics must have eligible provenance. A cached all-view structure is ineligible for top-only conditioning. Existing artifacts with unknown conditioning dependencies cannot silently pass this check.

Use the actual per-frame pose source and quality. `Cameras` currently recognizes `solved` and `solved_marker_corners`, while `leaf_surface_compare.compare_patch` checks `solved`. Document that compatibility gap and retain original status; do not relabel a pose to satisfy a consumer. No generated view provides a board pose or rescues failed calibration. Evaluation-camera poses obtained from withheld photographs remain evaluator-only and cannot inform candidate alignment or selection. A deployment-known virtual target pose is a separate declared input.

### 2 Reconstruct and preserve observable structure

Use the existing image masks and eligible geometry as an observation anchor. Carry unknown-depth and visibility masks explicitly. A valid foreground mask does not mean depth is known. Do not use black-filled missing areas as if they were observed empty space.

Match candidate leaflets using existing reviewed links and available appearance/vein/attachment evidence. Keep leaflet identity and physical landmark identity separate. Preserve unresolved links. Treat masks derived from unreviewed automatic predictions as uncertain conditions.

Preserve confirmed 3D points, accepted local patches, boundary/hole topology and source IDs. Generated geometry must not overwrite them. If a candidate cannot satisfy observed constraints, mark it inconsistent instead of changing the observations. Distinguish observation uncertainty from a hard constraint rather than freezing every noisy mask as exact truth.

### 3 Generate completion hypotheses

Define a backend-neutral request that includes only supported conditions: RGB views, camera information and, where implemented, masks, depth/normal evidence and structural references. Record unsupported conditions explicitly. Do not claim a generic pretrained model accepts a new depth/graph channel without a real adapter or training.

Produce multiple seeded completion hypotheses with an explicit configured sample budget. Prefer outputs that expose depth or surface normals in addition to RGB. Pure novel-view pictures or Gaussian-splat appearance are not yet physical triangular leaf surfaces.

Use a shared 3D or multiview-consistent representation; independently inpainting each photograph is not sufficient. Keep the camera/board background out of biological completion, while retaining the original calibration metadata. Correct resizing/cropping intrinsics and invert coordinate transforms on export.

Specify conversion to the candidate triangle representation below only when the backend provides sufficient geometry; this is not conversion into the observed-point/local-chart evidence schema. Preserve thin surfaces, holes, separate leaflets and folds; do not create a watertight canopy blob. Preserve inferred attachment relations as proposals. If metric scale is not identifiable, do not silently normalize the candidate to an assumed real plant size.

Specify the backend-to-board mapping explicitly: camera-to-world versus world-to-camera, axes/handedness, projection type, distortion handling, crop/resize mapping, depth meaning (camera Z versus ray distance), unit/scale and any normal transformation. Normal maps and novel-view RGB alone do not supply metric vertices. If a backend requires undistorted pinhole inputs, undistortion and inverse mappings are derived preprocessing with recorded hashes; do not alter the calibrated originals. Validate conversion against known measured projection anchors without using withheld targets to fit scale or alignment.

### 4 Score and review candidates

Reproject candidates to the actual fitting views and report foreground support, contradictions, unmatched structures and excluded pixels. Use visibility-aware rendering: hidden surfaces must not be required to reproduce a mask where another leaf occludes them.

Use fitting views for candidate ranking. Do not select the best sample using withheld target images or PPFD evaluation readings. Freeze the chosen sample rule or retain the full candidate set before evaluation. Save rejected candidates and reasons rather than deleting them.

Reuse the existing viewer for real photographs, actual masks, observed surfaces, generated surfaces and differences. Show candidate provenance and unresolved identity. Never mark a generated completion as human-confirmed merely because it was displayed or saved.

Classify each image region as observed visible tissue, confirmed visible background, occluded, or unknown. Unknown is not empty space. Render a complete frozen candidate scene with depth/occlusion when scoring silhouettes; the existing full-triangle support test is not a general visibility renderer for hidden hypotheses. Preserve legitimate front/back occlusion while reporting visible contradictions.

## Interfaces and provenance

Specify a separate candidate adapter only if no equivalent exists, for example a future `tools/multiview_completion.py`. Proposed logical functions are `audit_request(request_path)`, `prepare_request(request_path, out)`, `import_candidate_bundle(request_path, candidate_path, out)`, `evaluate_candidates(prepared_path, candidate_refs, evaluation_plan, out)`, and `export_review_bundle(result, out)`. These do not exist by virtue of this prompt. All paths resolve from the declared manifest, all outputs use fresh `build/` directories, and no function invokes inference, training or optical transport implicitly. Actual implementation is deferred under the current review-only request.

Numerical tables: CSV. Settings, hashes and relationships: JSON. Images and arrays use existing formats. Proposed additions, adapted to existing schemas rather than duplicating them:

- `completion_request.json`: proposed schema `multiview-completion-request-1`; plant/session/date, deployment mode, immutable source references/hashes, allowed fit/ranking/evaluation sets, movement-group evidence, model-use eligibility, declared conditions, anchor provenance, numerical policies and explicit sample/resource budgets. Null scientific thresholds stay unset.
- `completion_manifest.json`: backend/checkpoint hash, code/environment version, licence, seeds, conditioning inputs and their dependency closure, preprocessing, frozen sample-selection rule, view split, camera transforms, metric-scale provenance and per-stage statuses.
- `candidate_surfaces.csv`: exact existing `LEAF_SURFACES_CSV_COLUMNS` when board-frame mm and triangle geometry are supported. Join provenance by the existing full face key, not a newly invented unscoped surface ID. These files stay in candidate-specific folders and are not canonical optical inputs.
- `candidate_provenance.json`: `candidate_id`, plant/session/date, full face keys, source observations, observed/derived/generative origin, proposed versus confirmed identity, coordinate/scale evidence, unknown regions and model assumptions. Include candidate topology/semantic availability independently of geometric availability.
- `candidate_audit.json`: backend output/metric-frame availability, measured-anchor differences, dependency leakage, topology/identity issues, fit contradictions, staleness and optical blockers. Numerical mesh validity is separate from biological or optical acceptance.
- `area_hypotheses.csv`: candidate-specific area components with units, coverage and provenance; keep observed supported tissue and prior-conditioned completion separate. A scenario total is allowed only under an explicit disjoint-union policy and remains a hypothesis, never calibrated whole-plant area.
- `view_metrics.csv`: candidate, split, image, metric, value, denominator, exclusions and failure reason.
- `light_sensitivity.csv`: only when downstream calculation is separately eligible, candidate-specific light results and geometry coverage.

Keep `validated_metric=false` and `suitable_for_ppfd=false` for unqualified completion candidates. Preserve candidates separately from existing source surfaces. Hash changes in masks, cameras, identities, parameters or weights mark dependent results stale.

The actual triangle schema is `plant_id, session_id, geometry_variant_id, geometry_source, organ_class, organ_id, leaflet_id, triangle_id`, nine `v0/v1/v2_x/y/z_mm` fields, and `normal_convention`. The full face key is `(plant_id, session_id, geometry_variant_id, organ_id, leaflet_id, triangle_id)`. Use a unique variant per candidate/condition and retain a separate mapping to immutable observed anchors; temporary proposed IDs never become confirmed biological IDs.

Current `GEOMETRY_SOURCES` accepts only `reconstructed`, `manual`, `simplified`, `assumed`. Do not add `generated` to a protected schema or label generative vertices as observed reconstruction. If future candidate export uses this existing format, use `assumed` for generative faces with mandatory detailed sidecar provenance; retain original observed rows separately with their original provenance. Current `NORMAL_CONVENTIONS` accepts `adaxial_ccw` and `unknown`; geometric winding alone does not establish the biological adaxial side.

Sidecar provenance and eligibility must be required by the proposed candidate consumer. Reject absent, mismatched or incomplete sidecars; a CSV being parseable by the light geometry loader does not authorize feeding it to light simulation. Unknown scale stays in the backend's explicitly labelled nonmetric representation, with metric export unavailable; do not put normalized coordinates in `_mm` fields.

`compound_surface.audit_surface` accepts observed-support kinds `observed_supported` and `landmark_interpolated`, confirmed physical patch identity, reviewed topology and a policy requiring at least two real visible-support views. A generated hypothesis cannot satisfy these by relabelling support or by counting synthesized views. Existing `local_chart.point_ids`, boundary/hole rings and `visible_support` refer to real evidence; do not write generated landmarks into `points.csv`/`contours.csv` or use them to unlock `leaf_surface_compare`.

Keep immutable observed faces and candidate completion separate. Any future composition rule must specify anchor reuse, seam correspondence, overlapping/duplicate faces and candidate full-surface versus completion-only semantics. Never sum a full generated plant with the observed plant. No destructive clipping, refitting or movement of observed anchors is implicit; if a hypothesis cannot meet the declared composition contract, leave assembly unavailable and show it as an alternative hypothesis.

Proposed stage statuses include `prepared`, `backend_unavailable`, `not_executed`, `candidate_imported`, `constraints_checked`, `evaluation_unavailable` and `optical_export_blocked`. Keep scientific validation as a separate status; missing real references or a passing fit score never promotes it. Missing numeric values remain null/explicitly unavailable rather than fabricated zero.

## Evaluation design

Prepare these comparisons using identical permitted input sets and frozen policies:

| Condition | Purpose |
|---|---|
| Existing reconstruction from top plus selected sides, no diffusion | Main geometric baseline |
| Top-only observed measurements or an explicitly labelled fixed prior, no diffusion | Same-input baseline; unsupported depth/3D remains unavailable |
| Top-only generation | Compare against the top-only baseline without borrowing side-derived inputs |
| Top plus selected sides, with completion | Compare with the main baseline using exactly the same real conditioning images |
| Additional real views, where available | Separate increased-evidence comparison; not an isolated measure of diffusion benefit |

Report mask/silhouette overlap, organ merge/split or missing/excess candidates, confirmed landmark reprojection error and coverage on withheld actual photographs. Report depth, surface-distance or area error only with independent matching references. Missing anatomy hidden from every evaluation view remains unverified. Image realism scores alone do not establish 3D correctness.

Separate low-level software correctness, same-plant reconstruction consistency and unseen-plant generalization. With the current small number of plants, describe results as a feasibility pilot. No claim that training a specialized diffusion model is supported by the current sample size. Synthetic GroIMP plants may later supplement training, but their morphology/lighting assumptions and simulation-to-real gap require separate validation.

A shared detector/SAM checkpoint that saw a held-out plant makes its masks an additional evaluation dependency. Record each upstream training split; when unknown or contaminated, do not claim plant-disjoint generalization. Do not run retraining to repair this during prompt review. Freeze model/sample selection using development evidence, then score final evaluation data once; all-view geometry derived from final evaluation images is an evaluation reference, not a fitting anchor.

## Connection to light simulation

Keep generated completion as a diagnostic scenario branch. It must not bypass `plant_light_bridge` or existing optical review gates. Before any candidate photon calculation, require an explicitly supported diagnostic path with labelled assumed geometry and optics; if none exists, deliver a blocked optical export rather than turning candidate acceptance flags on.

For an authorized diagnostic experiment, compare the same lamps, sensor planes, solver settings and real-observation geometry across candidate completions. Report how lower/upper PPFD and explicitly covered plant photon interception vary with hidden geometry. Missing foliage can alter shadows on observed leaves too.

The spread across generative seeds is model-conditioned sensitivity, not a calibrated confidence interval, a coverage guarantee or the full uncertainty of the physical plant. Do not average triangle vertices from unrelated candidates into a fictitious mean leaf. Preserve each candidate geometry and its light results separately. Real sensor readings are reserved for independent validation, not for choosing the completion that looks best.

No growth simulator, biological response law or future-leaf generation is part of this pilot. This task concerns the current plant's hidden structure only.

## Software checks and completion report

Specify future tests for original-pixel/crop/pose/depth transforms; pose-status incompatibility; plant/session/movement isolation; withheld-view exclusion from the full dependency closure; generated views not counted as independent observations; immutable observed geometry/IDs; unknown-depth and occlusion masks; holes/disconnected patches; absent scale; full face keys and variant isolation; exact CSV enum compatibility; missing/tampered provenance rejection; full-surface/observed-face double counting; deterministic preparation; stale dependencies; seed retention; and optical gate preservation. Synthetic fixtures must remain excluded from research metrics. Do not run or write these tests during the present prompt-only review.

Deliver for the current specification task:

1. A feasibility table separating source-inspected facts, research candidates and unresolved model-use compatibility.
2. The existing-code integration map, proposed functions, input/output contracts and required owner changes.
3. A manifest/split/composition specification and planned evaluator/viewer adaptation, with unresolved scientific decisions explicit.
4. A future implementation/test plan and real-data blockers; no invented test results or executable notebook delivery claim.
5. An English review handoff stating exactly which prompt changes were made and that no implementation or model execution occurred.

If later separately instructed to implement, use this specification to build only the agreed local adapter, imported-candidate evaluator and viewer integration with bounded synthetic tests. Prepare cloud notebook/commands only if that deliverable is requested. Remote submission, checkpoint execution and optical simulation remain separately scoped actions; none is hidden in prepare/audit/evaluate.

Do not claim that all hidden tomato leaves were recovered. Success at preparation is a reproducible, source-preserving experiment that can test whether diffusion helps; biological and optical usefulness must be established by the subsequent evidence.
