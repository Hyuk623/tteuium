# Implementation prompt: measured leaf area and existing-leaf 3D surfaces

## Objective

Improve the calculation of CURRENT leaf area and the reconstruction of CURRENT leaf surfaces in 3D. Start from existing photographs, masks, camera calibration, board poses and reviewed observations. Deliver executable improvements and a source-linked comparison of the old and new calculations.

Future leaf occurrence, CompoundLeaf spatial distributions and growth-direction forecasting belong to another session. Do not modify that work. CompoundLeaf here is an aggregation unit for existing tissue, not a solid envelope that fills the gaps between its leaflets.

The practical endpoint is whole-plant one-sided leaf area and usable spatial geometry with minimal human review. Partial supported surfaces remain useful, but must not be called complete plant reconstruction. Keep a calibrated whole-plant proxy available while measured 3D coverage is incomplete.

## Start and ownership

Read the parent `공통규약.md`, this project's `AGENTS.md` and `CONVENTIONS.md`, the last five lines of `handoff/LOG.md`, and `handoff/TODO.md`. Inspect the current files; historical delivery claims are not current validation.

Codex owns `tools/` and `tools/tests/`. Respect `tomato3d/`, `tests/`, `docs/`, human configuration and source-observation ownership. Claude owns design/specification and agronomic decisions. Do not edit `config/` or human measurements. A prompt does not transfer ownership. Record cross-owner or unresolved specification needs in the English handoff and continue independent permitted work. Check for concurrent edits before touching shared files; preserve unrelated changes.

Write an English execution brief in `handoff/` before implementation and append results afterward. Generated outputs go into fresh `build/` directories. Conversation is Korean; code, comments and handoff are English. Tables are CSV; metadata, policies and audit results are JSON. Do not start training, neural inference, remote jobs, uploads, Git pushes or native light simulation under this task. Saved masks and predictions may be read.

## Required context and reusable code

Read `handoff/CODEX_LEAF_AREA_METHODS_2026-10-03.md`. Its reproducible experiment is `build/leaf_area_methods_20261003/experiment.py`; original results are in `build/leaf_area_methods_20261003/results/`.

Reuse and extend existing code rather than creating a second pipeline:

- `tools/plant_traits.py`: photo mask union, depth-based projected proxy, date/session matching and grouped calibration.
- `tools/plant_structure.py::Cameras`: camera projection/depth using the capture intrinsics and poses.
- `tools/leaf_light/reconstruction.py`: fixed-pose DLT, distortion handling, parallax/cheirality/reprojection checks and mesh baseline.
- `tools/compound_surface.py`: explicit local patches/boundaries/holes, face support, duplicate/intersection reporting and partial area.
- `tools/vein_surface_bridge.py` and `tools/visible_leaf_patch.py`: existing observation/visibility and projected-mask support mechanisms.
- `tomato3d/light/geometry.py::triangle_areas_mm2`: import the existing one-sided cross-product area calculation; do not edit it or duplicate it.
- `tools/plant_light_bridge.py`: retain its independent optical eligibility gates.
- `build/dwt_test_fill_20261003/regroup_traits.py`: reference for measured elevation only; its centre and threshold are capture-specific.

Known issues to verify against current code:

1. `photo_area` currently uses one hull-depth percentile per mask and sums Z^2/fx^2 on image pixels. This ignores unequal focal lengths and local distortion area scaling. It remains a projected proxy even after these are corrected.
2. In saved T1/T2/T3 intrinsics, fy/fx-1 is about +1.8829%; nonzero distortion is also present. This is not a measured total leaf-area error.
3. A 5% depth error produces about 10% projected-area error. A synthetic 60-degree tilted rectangle appears at about half its actual area.
4. Subdividing an existing mesh does not add measured curvature. Noisy dense meshes can inflate area.
5. Low reprojection residual does not prove metric accuracy; a wrong stereo baseline scale can give zero residual and wrong depth.
6. Code-prefix view groups can mix top/ring photographs in dwt_test. T3 has incompatible motion groups. Do not combine them silently.

## Work package 1: versioned, distortion-aware image-area proxy

Implement a reusable numeric helper in Codex-owned tooling and integrate it into `plant_traits` through an explicit estimator version. Preserve reproducible legacy results and expose side-by-side output. Do not overwrite saved historical runs or silently relabel old fields.

Inputs: original-image mask pixels/crop origin, calibrated camera matrix and distortion coefficients, compatible image dimensions, and depth in millimetres from the existing documented source. Resolve coordinate scaling explicitly if masks are resized. Camera/image incompatibility must be reported rather than guessed.

For each supported visible pixel, map its corners through the camera's distortion inverse into normalized camera rays. Calculate the footprint on the frontoparallel plane at the selected camera-Z depth. Under zero distortion this reduces to `pixel_count * depth_mm**2 / (fx_px * fy_px)` in mm2. For distorted pixels, use converged footprint integration or controlled subdivision with explicit numerical settings; a four-corner polygon is an approximation to curved distorted pixel edges. Document pixel-centre/corner conventions and validate the inverse mapping.

Preserve the current union/nearest-depth semantics so overlap within one photograph is counted once. Keep mask review provenance and accepted-only coverage separate. Validate finite positive depth/focal values, inverse-map failures and partial coverage. Distinguish a valid empty mask from missing depth or invalid calibration; unavailable observations are not measured zero. Stream/chunk calculations to control memory, and cache only under complete intrinsics/resolution/coordinate-transform keys.

Record `area_method`, method version, calibration identity and hash, depth method, original/used pixel counts, missing reasons and units. Keep the label projected proxy. Preserve existing consumers through an explicit compatibility path; do not silently reinterpret `leaf_area_cm2` as surface area.

Calibration k must be tied to estimator version and compatible capture style. Reject reuse across changed estimator/calibration contracts; re-fit only from existing independent measurement rows. Keep plant-grouped validation and date/session joins. No invented reference values or physical accuracy flags.

## Work package 2: measured view geometry and movement provenance

Expose per-photo measured elevation, camera centre, grouping source and availability from existing board poses. Group against explicitly supplied board-frame reference geometry and group policy. Reuse approved metadata/configuration values; if none are supplied, report elevation/grouping unavailable or retain explicitly labelled legacy grouping. Never turn the dwt_test reference script's 70 degrees or centre into a universal default.

Keep view sets, capture styles and movement groups visible in summaries. Do not use photograph order or nominal turntable angle as measured pose. Preserve T3's existing A+B1 versus B2 disposition and registration provenance. Detection of new motion or estimating registration requires a reviewed contract; an audit of supplied groups must not be presented as automatic motion detection.

## Work package 3: supported local surface reconstruction and comparison

Implement a comparison using the SAME supplied physical observations and the existing fixed camera poses:

1. Baseline: current triangulation and supported piecewise-linear mesh.
2. Nearly planar local patch: fit a plane to supported 3D observations, then intersect observed rays/boundaries with it. A known plane in a synthetic fixture is not evidence of a real leaf's normal.
3. Curved local patch: an explicitly configured regularized local polynomial or spline candidate constrained by measured boundary and interior points. Use an existing reviewed fitting contract if present; otherwise ask Claude through handoff to specify the model/selection contract. Do not choose a biological shape or fabricate curvature to fill absent observations. Implement generic comparison/audit plumbing and the defined baselines while that contract is unresolved.

Optional geometric point refinement may minimize image reprojection error with the SAME fixed camera calibration/poses, keeping the DLT baseline and failure diagnostics. Define the loss/weights/selection in the execution brief; these are numerical algorithm settings, not agronomic parameters. Do not discard observations merely to improve reported error. Evaluate on withheld observations where enough independent views exist; two-view-only reconstructions have no independent third-view check.

Boundary identity, interior landmark identity, leaf identity and visibility are separate evidence. A silhouette endpoint in two images is not automatically the same tissue point. Reuse existing reviewed data and proposals; request only missing discriminating evidence when needed. Do not require names for every leaflet before improving whole-plant proxy calculations.

Keep all patches in their recorded frame, in mm. Partition folded/disconnected tissue into supported local charts. Preserve serrations, holes and gaps with existing whole-face visibility/topology checks; do not stretch surfaces across different leaflets or use a convex hull as tissue. Smoothness is not an accuracy measure. Select numerical resolution by convergence and retained evidence, not by visual density alone.

Preserve surface/triangle identity and sum one-sided physical tissue once. Different views support the same tissue; distinct leaves overlapping in an image still have separate physical areas. Ambiguous coincident surfaces require review, not unconditional merging. Report measured-support, interpolated and inferred provenance. Partial supported area is not automatically a certified lower bound when scale/topology remain uncertain. Whole-plant total stays unavailable unless completeness or an independently calibrated estimator supports it.

Do not promote any reconstructed candidate to optical-ready or physically validated simply because area exists or tests pass. Preserve existing bridge review, normal, completeness, motion and source-freshness gates. Growth envelopes never enter the tissue-area sum.

## Output and review contract

Prefer extending the existing viewer/site. Show source photographs/masks, reconstructed patches and reprojections with old/new toggles and visible missing/partial states. Include separate plant/session/date/compound summaries for:

- legacy projected proxy and corrected projected proxy, with estimator versions;
- supported one-sided 3D area and covered patch inventory;
- calibrated whole-plant estimate, only when compatible reference measurements exist;
- unavailable/occluded/ambiguous tissue and unvalidated scale/pose status;
- surface normals/directions and geometry provenance, where supported.

Do not add a whole-plant calibrated estimate to a partial 3D area. Do not sum per-photo areas as total tissue. Retain original source links and review decisions. Deliver new CSV results, JSON provenance/policy/metrics and a viewer with reproducible CLI commands and `--help`. Write every added support-tool test under `tools/tests/`.

## Verification

Use independently known geometry, not fixtures that merely repeat the implementation:

- No distortion and unequal fx/fy: exact frontoparallel physical area; compare the legacy bias.
- Radial/tangential distortion, off-axis placement, crop/resize mapping: independently projected references, boundary integration convergence and inverse mapping checks.
- Tilted known plane: recover its physical area only in the plane-supported route; preserve reduced projected area in the proxy.
- Curved analytical cylinder: actual additional samples improve area; subdividing old chords does not.
- Flat and curved noisy surfaces: show both roughness inflation and over-smoothing bias; retain held-out error and parameter sensitivity.
- Holes, disconnected tissue, folds, duplicate/reversed faces and overlapping leaves: correct topology and one-sided accounting.
- Empty versus unsupported masks, missing depths, incompatible calibration, near-parallel rays and failed poses: explicit statuses rather than false zero/validity.
- Calibration version/capture-style mismatch and repeated dates: prevent stale k reuse and plant leakage.
- View regrouping and supplied movement groups: no order-derived geometry and no silent incompatible fusion.
- Source hashes: originals, masks, observations and configuration remain unchanged.

Run focused new and affected existing tests. Run read-only saved T1/T2/T3 comparisons where inputs exist, recording views used, exclusions, runtime and input hashes. Save new outputs under fresh build directories. If real reviewed correspondences or physical references are absent, report the precise missing evidence; do not manufacture it or claim plant accuracy from synthetic checks. Compare real accuracy only against independent measured targets, by held-out plant/capture style and with reference uncertainty acknowledged.

Numerical test tolerances must be justified by analytical precision/convergence. Physical acceptance thresholds, new rig policies and fitting-contract gaps require Claude's specification; never relax existing gates just to obtain a result.

## Completion report

Deliver implementation files, an executable CLI, focused verification results, real saved-data comparison or exact blockers, a source-linked viewer and English handoff updates. Explain in Korean which arithmetic/geometric behavior improved and which physical accuracy claims remain unverified. Separate software completion, real input availability and physical validation. Unresolved curved-surface specifications or missing measurements must remain explicitly open, not hidden by a passing proxy test. Do not mark the full surface/accuracy objective complete from the image-area correction alone.

## Scope of this artifact

This file is a prepared prompt. Its creation did not execute the implementation, change estimator behavior or send instructions to another chat. Start implementation only when the user invokes this prompt for execution in the receiving session.
