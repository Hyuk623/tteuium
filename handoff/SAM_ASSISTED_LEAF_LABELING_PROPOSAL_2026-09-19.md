# SAM-assisted leaflet labeling: proposal for Claude review

The user asks how to make labeling easier using SAM. This is a reviewed-code feasibility proposal, not an implemented SAM integration. No models were installed or run and no speed/accuracy improvement has been measured. Real metric 3D remains dependent on the pending camera-calibration photos.

## Proposed user workflow

1. Open a reference photograph and select one **leaflet**, not an entire compound leaf. A positive click or a small box requests a mask from a pretrained model.
2. Show alternative mask candidates. Positive/negative clicks refine inclusion/exclusion; the user accepts the observed leaflet outline. Keep manual editing available.
3. Assign/reuse the existing organ_id. Open another photograph where the leaflet is visible, retain that identity, and request its mask with another click. Cross-view identity is explicitly reviewed.
4. Preserve named physical landmarks for triangulation: tip, base, recognizable boundary landmarks and interior/midrib features as required by the reconstruction. SAM prompt clicks are segmentation controls, not automatically triangulatable landmarks.
5. With accepted camera poses, show the existing epipolar guidance and reprojection checks. Offer correspondence candidates for human confirmation; do not manufacture missing points.

The baseline saves outline tracing. It does not yet eliminate the current reconstruction's landmark requirements. Do not promise that two tip/base clicks plus SAM produce a measured curved leaf surface.

## Model options

- Start with SAM 2.1 interactive image segmentation as a baseline. Its published pretrained checkpoints and image API accept point/box prompts; foreground/background points allow correction. Evaluate actual leaflet masks before considering task-specific fine-tuning.
- SAM 3 is an alternative for text/exemplar-based candidate discovery, followed by point/box review. A phrase such as "tomato leaflet" is a test prompt, not a promise of exhaustive individual-leaflet detection. Review errors where compound leaves merge or small overlapping leaflets disappear.
- SAM video tracking can propagate mask identities in video. Do not assume the current sparse multi-angle still photos, with view jumps and occlusion, behave like continuous video. If supplementary rotation video is later considered, keep it separate from the metric photograph subset study; no protocol change is made here.
- A stable whole-object tracking ID does not establish dense physical landmark correspondence. A silhouette vertex can move along a curved surface as the viewpoint changes.

## Existing integration points and gaps

- `tools/leaf_point_annotator.html` already stores per-view leaflet observations, shared organ IDs, masks represented as contour lists, separate boundary/interior points, identity split/relink and undo. It has no SAM inference endpoint or model integration.
- `autoContour()` currently constructs an outline from all named boundary points. Rendering, readiness counting and `buildExport()` use it. Simply putting a SAM polygon in `leaf.contours` is insufficient: the accepted contour must be explicitly consumed, persisted, displayed and exported.
- Keep `points.csv` physical point_id semantics unchanged. A SAM mask boundary's vertex_index is only a per-image contour ordering. Never uniformly sample separate contours and treat equal indices as corresponding 3D points.
- Preserve the existing plant/session/variant/image/organ scope, source image hashes, original upright pixel coordinates, model/checkpoint identity, prompts and human acceptance history. Cache image embeddings by source hash and model settings. Discard stale responses after image/organ/session switches.
- Prediction masks and reviewed masks must be distinguishable. An automatically generated confidence score is not verified quality. Undo, relabeling, split/relink, import/export and restart must preserve the accepted observation and provenance.
- Store binary mask artifacts losslessly in build, contour/landmark tables as CSV, metadata/provenance as JSON. Keep disjoint visible components and holes in the mask. Current polygon-only reconstruction cannot faithfully consume arbitrary occlusion masks: mark partial observations and keep them out of the full-outline constraint path until that contract is extended. Do not bridge occlusion gaps or fill hidden leaf tissue.
- `tools/leaf_light/reconstruction.py` requires each physical boundary point in at least two views and at least two full visible contours per leaflet. Calibrated poses, sufficient parallax and reprojection gates still apply. No relaxed gate, nominal camera pose or generated geometry should replace failed actual measurements.

## Two implementation stages

1. **Outline assistant:** connect a Python image predictor to the current local annotator; add include/exclude prompts, candidate masks, accept/edit actions and explicit reviewed-contour export. Reuse cross-view labels and existing landmarks. This image-only assistance can be developed before camera calibration succeeds.
2. **Reduced landmark workflow:** separately evaluate mask-constrained surface fitting plus sparse anatomical landmarks. This needs an actual new reconstruction method, model assumptions and validation; it is not a checkbox enabled by SAM. Preserve observable leaf curvature, gaps and uncertainty. Do not substitute a silhouette hull for leaf surfaces.

Keep flower/bud/truss bounding boxes separate; precise flower segmentation is not required for the initial leaf-surface milestone.

## Proposed development check

Use a small set of reviewed leaflets spanning isolated, touching and occluded cases in the supplied photographs. Compare manual labeling with SAM-assisted labeling on the same cases. Record total annotation/correction time, prompts, rejected masks, mask overlap/boundary error and cross-view ID mistakes. Following successful camera calibration, also check physical landmark reprojection, accepted surface coverage and geometric consistency. Fix the evaluation procedure before claiming a percentage time saving. Check local inference hardware before selecting a checkpoint; no installation or GPU performance is assumed here.

## Primary sources inspected

- [Meta SAM 2 repository](https://github.com/facebookresearch/sam2): pretrained SAM 2.1 checkpoints, interactive image segmentation and video mask propagation.
- [SAM 2 image predictor](https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py): foreground/background prompts, boxes, candidate masks and iterative mask refinement.
- [Meta SAM 3 repository](https://github.com/facebookresearch/sam3): concept-based segmentation and visual prompts; detector/tracker architecture.

The specific leaflet workflow, failure controls and staged integration above are engineering proposals based on the inspected local code, not published tomato-specific performance claims.
