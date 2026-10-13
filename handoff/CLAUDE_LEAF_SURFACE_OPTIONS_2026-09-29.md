# Leaf-surface implementation options for Phase 3

Date: 2026-09-29
Status: proposal for Claude/design review, not an implemented or validated reconstruction method.
User request: consider how to construct leaf surfaces with the current project.
No inference, training, surface generation or optical simulation was performed.

## Existing implementation to reuse

- tools/leaf_light/reconstruction.py: physical point-ID triangulation, contour checks and piecewise-linear triangles using a local 2D parameterization. Its current complete-boundary path requires all indexed boundary points and at least two contours.
- tools/sam_supported_leaf_patches.py and tools/rebuild_leaf_edit_session.py: partial-patch integration is referenced by tools/tests/test_leaflet_surface_attachment.py; diagnostic patches retain source images, interpolation status and non-PPFD flags. The test file was inspected; the patch generator was not fully reviewed in this task.
- tools/groimp_bridge.py: existing labelled leaf-triangle transport, mm to metres, identity map, open surfaces; diagnostic boxes are excluded.
- Current Phase-2 exports have zero LeafSurface instances. Existing surface code must not be mistaken for complete current plant surfaces.

## Recommended staged method

Use reviewed instance masks + confirmed physical identities + sparse physical landmarks, with measured camera poses fixed. Implement within the existing editor/rebuild pipeline after design confirmation.

1. Select an unoccluded leaflet visible in at least two usable posed photographs. Prefer a third view reserved for checking when available. An unposed image may guide manual review but supplies no geometric constraint.
2. Reuse the accepted mask and bbox. Masks supply visible outline evidence; bbox is a work region and optional search bound, never a physical surface.
3. Mark the tip, visible base, distinct vein junctions or recognizable margin features across photographs using persistent point IDs. A suggested first trial uses roughly 5–8 identifiable points distributed along and across the leaflet; this is workload guidance, not a mathematical guarantee. Do not infer a base behind an occluder, use bbox centres or equate independent contour vertex numbers.
4. Triangulate only observed correspondences. Check positive depth, view separation and reprojection residuals. Preserve failed quality gates; do not re-fit camera poses to make the leaf appear to match.
5. Produce a planar partial-patch baseline where at least three stable, non-collinear 3D anchors support it. More anchors are preferable. Use a well-observed, non-grazing mask; intersect its camera rays with the supported plane to propose an outline, then check other views. Label the unmeasured plane assumption and interpolated boundary depths explicitly.
6. For a curved variant, fit a low-complexity surface constrained by 3D midrib landmarks plus off-midrib landmarks. Adjust only identifiable shape parameters, balancing landmark reprojection, visible mask agreement and smoothness. A midrib alone cannot determine cross-leaf curl or twist. Masks do not uniquely recover hidden curvature. If constraints cannot determine the shape, retain a planar/partial diagnostic model or report unavailable.
7. Tessellate the supported patch into open triangles, preserving holes and observed fragments. Dense triangles do not create new depth evidence. Label triangulated landmarks separately from fitted/interpolated vertices.
8. Reproject the mesh into every source photograph. Present overlays and unresolved regions to the user before acceptance. Mask acceptance, identity acceptance, surface approval and metric/PPFD validation remain distinct.

## Occlusion and shape rules

- A visible mask of a partially occluded leaflet does not bound its hidden full outline. Do not carve hidden geometry merely because it lies outside that mask. Use explicit occlusion information; unknown regions are not negative evidence.
- No correspondence is inferred from nearest contour pixels across views: different views can show different silhouette-generating points.
- Do not extend a template into hidden regions and call those coordinates observed. Any optional template scenario must be separately labelled inferred and excluded from measured-geometry claims.
- A visual-hull volume can help bound a search but its enclosing skin is not automatically a leaf lamina.
- Do not impose watertightness or artificial thickness for leaf light tracing. Review normals, sidedness and optical properties independently.
- An incomplete canopy can underestimate occlusion. Report surface coverage and missing organs with light results; never quietly count an unreconstructed leaflet as absent.

## Bounded first comparison

Propose dwt_01 with 3–5 clearly visible leaflets, using existing reviewed masks and confirmed identities. Compare a planar baseline with a landmark-supported curved variant using the same source observations. Do not fill a fixed quota if evidence is inadequate.

Report actual correction time, used/rejected observations, landmark reprojection error, visible-mask agreement, held-out-view agreement where available, supported versus interpolated area and unresolved regions. Independent ruler/shape references are required for metric validation. Image overlap alone does not prove correct depth.

Once the optical adapter and input gates are fixed, compare the two surface variants under the same assumed light only as a geometry-sensitivity experiment. Use independently measured PPFD later for validation, not to tune an arbitrary leaf shape until the light values match.

Keep validated_metric=false and suitable_for_ppfd=false until their respective evidence requirements are met. Do not treat this proposal as permission to overwrite labels or replace existing geometry.

## Sources consulted

- OpenCV calibration, projection and triangulation: https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html
- Open3D surface reconstruction (point-cloud prerequisites and Poisson extrapolation caveats): https://www.open3d.org/docs/latest/tutorial/geometry/surface_reconstruction.html

The proposed sparse-landmark plus mask workflow is a project-specific engineering recommendation, not a documented accuracy guarantee from these sources.

## Addendum: RGB-guided midrib proposals inside accepted SAM instances

User follow-up: detect the midrib using the RGB appearance inside each SAM-separated leaflet.
Status: method proposal only; no model or image-processing execution performed.

### Inputs and preservation

Read the original RGB image and a reviewed leaflet mask as separate inputs; do not analyse a green mask overlay or screenshot. Keep source annotation ID, optional physical leaflet ID, original-pixel crop/resize transform, mask revision and image hash. SAM supplies an instance ROI, not a vein or depth measurement. An overlapping second leaflet incorrectly included in the instance must be corrected first.

### Candidate pipeline

1. Crop with context around the instance and preserve original RGB values. Analyse inside its valid mask. Do not zero the background before derivative filtering: the synthetic black boundary produces false ridges. Filter with surrounding image context and suppress/flag responses whose filter support crosses the instance boundary; keep tip/base observations separately rather than deleting them by blanket erosion.
2. Compare RGB channels and a luminance/chroma representation (e.g. Lab). Apply restrained local contrast enhancement and edge-preserving denoising; retain raw appearance for review. Saturated glare, blur and deep shadow become low-evidence zones, not reconstructed texture.
3. Use multi-scale Frangi or Sato ridge responses for both bright and dark lines, with widths defined in original-image pixels or relative to leaflet image size. Combine ridge strength, local orientation continuity and optional locally sampled vein-colour similarity. No global green/white threshold is assumed to identify the midrib. These generic ridge filters respond to folds and shadows too.
4. Prefer a person-marked visible base and tip to constrain candidate paths. Automatic endpoint proposals remain unconfirmed. If the true base/tip is hidden, use explicitly named visible segment endpoints and keep a partial midrib.
5. Trace candidate paths within the supported visible region using graph search with appearance and turning costs. Do not select the longest skeleton branch unconditionally or force the shortest path through a low-evidence gap. Offer alternative routes or abstain. A weak centre-of-mask prior may help selection but is not observed anatomy.
6. If skeletonization is used, apply it to a vein-candidate region. Skeletonizing the full SAM leaf mask produces a shape medial axis, not a detected biological midrib.
7. Review the proposed polyline on the original photo. Allow endpoint correction, additional guidance points, dragging/deleting vertices, alternative candidate selection and partial/unavailable status. Keep midrib controls (expected width, contrast, continuity) distinct from SAM mask sensitivity 20.

### 3D connection

A 2D midrib polyline does not supply Z coordinates. Reuse fixed calibrated camera poses and the same physical leaflet identity. Confirm homologous tip/base/vein junction landmarks across views before triangulation. Equal vertex indexes or equal fractions of a view-dependent 2D curve are not physical correspondences. Epipolar constraints can propose matches but do not prove identity; ambiguous intersections remain unresolved. Dense curves between confirmed 3D landmarks are fitted/interpolated, not independently measured. Off-midrib observations remain necessary to constrain leaf curl/twist.

### Evaluation and integration

Start with clear, wrinkled and partially occluded instances from the current data. Independently trace visible midribs for evaluation; report centreline distance, visible-length coverage, wrong-branch rate, abstention and human correction effort. Report per-view results and coordinate units; do not invent a pass threshold or accuracy percentage before data exist. Parameter selection uses development plants; held-out evaluation remains separate. No new training is needed for this classical-image-processing pilot.

Add proposals to the existing editor, retaining raw observations, user corrections and stale-result detection. Any downstream surface still preserves diagnostic geometry flags.

Sources for the generic image-processing primitives (not guarantees of tomato midrib accuracy):
- OpenCV CLAHE: https://docs.opencv.org/4.10.0/d6/db6/classcv_1_1CLAHE.html
- scikit-image ridge filters: https://scikit-image.org/docs/0.25.x/api/skimage.filters.html
- scikit-image morphology/skeletonize: https://scikit-image.org/docs/stable/api/skimage.morphology
