# Existing-leaf area and 3D reconstruction method investigation

## Request and scope

This chat investigates better calculation of existing leaf area and representation in 3D. Future CompoundLeaf occurrence/directional growth belongs to the separate growth session. Existing leaves retain measured evidence. This is a method investigation with reproducible diagnostic experiments, not authorization to invent observations, replace source reconstructions, train models or run remote jobs.

## Inspected current behavior

- tools/plant_traits.py::photo_area merges visible masks and uses one hull-depth percentile per mask, then sums Z^2/fx^2. This is a projected proxy; it is not a complete one-sided leaf surface area. Cameras.project includes distortion, whereas the area conversion has no distortion Jacobian. Anisotropic intrinsics need fx*fy in the undistorted frontoparallel case.
- tools/leaf_light/reconstruction.py::triangulate already undistorts observations, solves fixed-camera multi-view DLT, checks parallax, cheirality and per-view reprojection. Surface connectivity uses a PCA chart and Delaunay with sampled contour checks.
- tools/compound_surface.py already offers local charts with explicit boundaries/holes, full projected mask support, duplicates/intersections and partial-area accounting. Do not duplicate these controls or claim a new cross-product formula is needed.
- Latest saved T1 audit is partial_observation_only; no confirmed complete compound state or optical-ready surface is established. No new real-data validation is inferred from historical tests.

## Work and restrictions

Create a separate build-only diagnostic experiment comparing projected area versus known-plane ray intersections, focal anisotropy, depth sensitivity, observed curvature versus subdivision, occlusion and noise inflation. Read representative saved capture intrinsics and report source hashes. Synthetic dimensions and noise are experiment settings only, never target-plant parameters. Keep tables in CSV and metadata/audits in JSON. Preserve source, measurements, config, docs, existing tools and model assets.

## Validation and decisions

Use analytically known rectangles/cylinders and an independent polygon formula to check geometry, distinguish new observations from interpolated mesh vertices, and verify input hashes. Inspect primary sources for method applicability. Record candidate improvements and physical validation requirements here after execution. Claude retains design/acceptance and agronomic decisions; no arbitrary physical pass thresholds will be adopted.

## Primary sources inspected

- OpenCV 4.13 calibration model and undistortion: https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html
- Whebell et al., thin-leaf implicit reconstruction from dense scanned clouds (not sparse RGB landmarks): https://arxiv.org/abs/2009.10286
- Ahmed and Maini, 2026 comparative preprint, nine surface methods on leaf point clouds: https://arxiv.org/html/2604.03328v1 . Its point-cloud comparisons do not validate this project's geometry or justify filling unseen tissue.

## Executed evidence

Script: `build/leaf_area_methods_20261003/experiment.py`. Outputs: `build/leaf_area_methods_20261003/results/`, eight CSV tables and `audit.json`. Rerun with `python -X utf8 build/leaf_area_methods_20261003/experiment.py --out build/<fresh-directory>`; output refuses existing directories. All checks passed; seven inspected source files/captures were unchanged.

1. An analytical 800 mm2 rectangle tilted 60 degrees produces 400.962 mm2 with the centre-depth fx*fy projected approximation. Ray intersection with its explicitly known plane recovers 800 mm2. At 80 degrees the proxy falls to 139.351 mm2. The plane is oracle synthetic evidence; this is NOT a way to recover an unknown normal from one mask.
2. The actual `photo_area` function gives 12.8 cm2 for a frontoparallel 16 cm2 fixture with fx=100, fy=80. Saved T1/T2/T3 intrinsics all have fx=3216.1098, fy=3276.6649; using fx squared instead of fx*fy introduces +1.8829% bias under the undistorted frontoparallel approximation. All three captures have nonzero distortion, so focal correction alone is incomplete. No revised real-plant area is claimed.
3. A +5% depth error implies +10.25% projected-area error; -5% implies -9.75%. This follows the quadratic scale relationship, not a measured error distribution.
4. A half-cylinder has analytical area 628.319 mm2. Four observed arc segments give 612.293; 64 new arc segments give 628.255. Subdividing the original chords into 64 segments stays 612.293. More observations can improve curvature; more triangles alone cannot.
5. On an independently known 400 mm2 flat square with synthetic independent z noise SD=0.5 mm, raw mesh means grow from 407.598 to 708.900 mm2 as grids increase from 5x5 to 33x33. A plane fit gives about 400 mm2. This proves a noise failure mode, not that real curved leaves should be flattened or that this noise magnitude describes our data.
6. A synthetic stereo baseline scale error of +2% reconstructs true depth 500 mm as 510 mm with zero reprojection error. Low reprojection residual alone does not establish physical accuracy.
7. One and two perfectly overlapping 800 mm2 leaf layers have the same 800 mm2 image union, but physical tissue totals differ. A single mask cannot identify hidden tissue area; summing masks across views can also double-count the same tissue.

## Method priorities for Claude review

### A. Correct camera geometry and capture comparability first

Carry board variant/physical scale and capture identity explicitly. Keep the plant fixed relative to the board; separate motion groups rather than fitting one inconsistent hull. Reuse measured elevation for grouping, with the capture centre/threshold supplied by the contract; the existing diagnostic script's centre and 70-degree threshold are not universal defaults. Compare like capture styles. Keep point matching and scale quality separate from reprojection residual.

For the existing proxy, an implementation can use undistorted pixel-corner rays and their area on a frontoparallel plane at the current mask depth. This incorporates fx, fy and lens distortion while preserving the proxy definition. In the no-distortion case the conversion is pixel_count * Z^2/(fx*fy). It still cannot repair wrong hull depth, leaf tilt or occlusion. Version outputs and re-fit calibration after changing the proxy; do not silently apply an old fitted k.

### B. Recover local leaf surfaces where observations support them

Keep current measured ChArUco poses fixed. Establish multi-view physical correspondences using visible interior texture/vein junctions plus true tissue boundary points; silhouette extrema are not automatically the same physical points across views. Confirm surface/identity evidence without requiring global names for every leaflet. Existing reviewed correspondences remain authoritative.

Use the existing DLT as baseline. A candidate refinement minimizes distorted-image reprojection residuals for the same 3D point with fixed cameras; evaluate on withheld observations, retain outliers and failure counts, and do not optimize cameras against their own reconstructed leaves as independent validation. Uncertain camera calibration needs separate perturbation/sensitivity analysis rather than confidence intervals computed from image-point noise alone.

Nearly planar local patches: fit a supported local plane and intersect undistorted rays with it. Curved patches: compare bounded local smooth surfaces (e.g. regularized spline or local polynomial) against the existing piecewise-linear mesh, using interior observations and retained boundary/hole constraints. Split folded leaves into locally representable patches; a global PCA height function cannot represent every fold. Never divide image area by a guessed cosine; grazing-angle geometry is particularly unstable.

### C. Mesh and aggregate physical tissue once

Reuse `compound_surface` for gap/hole preservation, face support, duplicate/intersection reporting and partial completeness. Sum the one-sided 3D triangle areas, not 2D camera unions, for reconstructed tissue. Multiple views contribute evidence to the SAME surface; they are not additional leaves. Distinct overlapping leaves still count separately in tissue area even when only one is visible in a photo. CompoundLeaf is an aggregation/organization unit; its convex envelope and spaces between leaflets are not leaf tissue.

Choose mesh resolution by stable area/shape under refinement AND independent image/point support. Smoothing needs validation: excess roughness inflates area, while over-smoothing removes real curvature and serrations. Maintain observed/interpolated/inferred provenance; supported partial area is not a certified lower bound when camera scale or topology is uncertain. Unknown total area remains unavailable, rather than zero or a forced completed mesh.

### D. Keep an operational whole-plant estimate in parallel

Whole-plant non-destructive area references and same-style image-proxy calibration remain useful even when complete 3D tissue coverage is absent. Fit and evaluate by held-out plant, preserving date/session and capture style. A reference estimated as k*length*width has its own calibration uncertainty; it is not exact ground truth. Flattened-leaf images with a coplanar scale can check one-sided area, but cannot validate the original in-situ curvature or position.

Report separately: projected proxy, supported reconstructed area, whole-plant calibrated estimate, missing surface/visibility status, and validation evidence. Do not sum partial 3D area with a calibrated whole-plant estimate. If a hybrid visible-plus-unseen estimator is later specified, deduplicate physical tissue and validate it independently.

## Literature interpretation and selection limits

Whebell et al. fit smooth thin surfaces to scanned capsicum/tomato point clouds using localized implicit interpolation. This makes smooth thin-surface fitting a relevant candidate once adequate 3D samples exist; it does not supply missing depth from our silhouettes.

The 2026 comparison evaluates nine methods, but parts of its area comparison use Poisson as the reference, not independently measured leaf area; its D2 implementation also substitutes a thin-plate-spline approximation and empirical smoothing. Therefore its ranking is not an accuracy guarantee. It also reports that sparse/noisy inputs and concave leaflet clusters can produce incorrect bridging or area inflation. No new Poisson, SOM or neural pipeline is selected merely from that ranking. These are dense-point-cloud candidates, with tuning and independent validation still necessary.

## Concrete next implementation and validation contract proposal

1. Implement a separately versioned distortion-aware projected-area calculation within Codex-owned tooling, preserving the current proxy baseline. Test anisotropic K, distorted/off-axis planar references, crop/resize coordinate consistency, invalid rays, holes/overlap, unavailable depth and source preservation. Record formula and calibration version. This is numeric correction, not physical calibration.
2. Integrate measured-elevation diagnostics with caller-supplied geometry metadata; keep missing/moving views explicit. Do not choose new rig thresholds or repair config from this research brief.
3. Compare current mesh, known/supported local planes and regularized curved patches on identical observed point sets. Evaluate physical-area error, held-out reprojection/3D error, topology, coverage and sensitivity. Do not rank methods solely by training residual or total area agreement, which can hide cancelling local errors.
4. Physical validation needs independently measured leaf/board dimensions and multi-view surface evidence; tolerances and smoothing selection belong in the reviewed contract. Existing capture audits and these synthetic experiments do not close that gate.

Method investigation is delivered. Production estimator changes, new physical observations, model execution and real accuracy improvement were not performed or claimed in this investigation.
