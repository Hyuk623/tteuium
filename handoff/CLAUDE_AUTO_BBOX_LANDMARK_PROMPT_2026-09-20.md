# Claude Code prompt: automatic leaflet bbox and landmark drafts

## User workflow preference

Before starting implementation or model-related work, create or update an English Markdown brief in `handoff/`. Record the request, inspected existing behavior, intended changes, execution restrictions, and validation. Then proceed within the user's authorization. Update the handoff with actual outcomes afterward. This is a documentation-first workflow, not an extra approval step.

This turn prepares an implementation prompt only. Do not interpret it as authorization to execute training, inference, model downloads, or PPFD simulations.

## Objective

Extend the existing tomato labeling application so it can propose leaflet bboxes and physical landmark candidates, with the human correcting mistakes and confirming cross-view identities. Reuse existing proposal review and reconstruction paths. Do not replace them with a separate app or equate a larger number of generated masks with successful organ detection or 3D reconstruction.

## Inspected current behavior

The latest relevant Claude handoff is `LEAFLET_SURFACE_REVIEW_INTEGRATION_2026-09-20.md`. Its main additions are partial-surface attachment, freshness checks and reprojection, not an automatic leaflet detector.

The current `tools/leaf_point_annotator.html` already supports prompted segmentation proposals, editing/acceptance/rejection, bbox derivation from accepted rings, manual physical point IDs, identity review, and geometry-based candidate links. Its help explicitly distinguishes SAM prompted segmentation from a trained tomato organ detector. `tools/serve_leaf_edit_session.py` connects a configured segmentation backend to the editor; no claim is made that a running server currently has a model enabled.

Read the latest code and `handoff/AI_ASSISTED_LEAFLET_LABELING_2026-09-20.md`, `handoff/CLAUDE_RESUME_SAM_3D_2026-09-20.md`, and `handoff/CODEX_REVIEW_INTEGRATE_SKILL_2026-09-20.md` before editing. Existing inference artifacts and the failed correspondence trial are evidence to inspect, not reviewed ground truth.

## Required implementation

### 1. Automatic bbox drafts

- Add a batch proposal entrypoint for the current photograph and explicitly selected photographs, alongside the existing single-leaf prompted segmentation tool.
- Inspect available local detectors/segmenters and their actual capabilities first. Reuse an existing suitable backend; if none exists, implement the adapter and import/mock path and report real detection as unavailable. Do not claim mock or heuristic outputs are learned detections.
- If using automatic mask generation, treat each mask as an unclassified candidate until reviewed: one mask can cover a lobe, a whole compound leaf, multiple leaflets, or background.
- Keep small real leaflets available for review. Avoid silently merging overlapping leaflets or treating all small components as noise.
- Derive original-image-pixel bboxes from proposed masks; retain proposal source, photo hash, model/version/settings, and score semantics. A model score is not calibrated botanical accuracy.
- Keep flower, bud, fruit, stem and petiole targets separate from leaflets. Do not invent unsupported class predictions.

### 2. Meaningful landmark drafts

- Distinguish per-image feature candidates from matched physical landmarks usable for triangulation.
- Candidate semantics may include leaflet tip, visible attachment point, distinctive lobe tip, and visible midrib/secondary-vein junction. Record unknown meaning when unsupported.
- A mask skeleton, contour extremum, bbox center or evenly spaced contour vertex is not automatically a botanical landmark or a cross-view correspondence.
- Midrib candidates should represent visible structure; a guessed centerline must be explicitly marked inferred and cannot silently become observed ground truth.
- Store candidates separately from accepted `b*` and `i*` points. Preserve boundary/interior distinctions, missing observations and edit history.
- Do not overwrite existing human-reviewed point coordinates or IDs.

### 3. Cross-view physical correspondence

- Use confirmed leaflet identity to restrict the search to that leaflet's region in each photograph.
- Propose point matches with an explicitly identified matching method; use measured camera geometry for consistency checking where available, without changing pose estimation to SfM.
- Combine visual evidence with geometric checks. Low reprojection error alone does not prove that two observations are the same physical point.
- Report ambiguous/multiple candidates, occlusion, weak texture and unavailable poses rather than forcing a match.
- Maintain a persistent `point_id` only after the physical correspondence is accepted. Never assign correspondence by independent contour ordering or image-relative left/right.
- Leave the user's identity-review and visibility statuses unchanged unless the user explicitly changes them.

### 4. Review UI and reconstruction

- Reuse existing draft/edited/accepted/rejected states. Show bbox, segmentation and point-match review separately so accepting an outline does not implicitly accept its identity or landmarks.
- Provide editable/movable/deletable draft boxes and points, undo, side-by-side crops, and source-image overlays in original pixel coordinates.
- Allow rejection of a whole proposal and correction of individual parts. Bulk actions must not silently replace existing labels or approve ambiguous physical matches.
- Only accepted physical observations enter the reconstruction path, retaining current geometry gates and diagnostic flags.
- Mark dependent 3D results stale after accepted correspondence changes. Reuse current server rebuild and surface attachment contracts; do not regenerate SAM masks implicitly.
- Cuboids remain diagnostic spatial extents, never leaf surface geometry or PPFD occluders.

## Validation and evaluation

Implement deterministic/mock tests without executing a learned model. Cover overlapping leaflets, small leaves, occlusion, wrong/background candidates, missing poses, ambiguous matches, original-coordinate preservation, undo/rejection, existing-label preservation, and stale-result handling after edits.

When a real inference trial is separately authorized, evaluate on explicitly identified reviewed photos: bbox precision/recall under a stated overlap criterion, physical point localization error, correct/incorrect match counts, missed leaves, and human correction time. Report human-review status and denominator; do not present the number of generated candidates as accuracy. If training is later authorized, split by plant/session as appropriate to avoid leaking views of the same plant into evaluation.

## Delivery

Report which capability already existed, what was added, the actual backend and limitations, files changed, launch/import commands, tests run, and what still requires a real authorized trial. Keep all changes inside the project, preserve user data and current quality gates, and update the English handoff before and after implementation. No full-plant, measured-curvature, metric-accuracy or PPFD-readiness claims without corresponding validation.

## User-supplied top-view labeling example (2026-09-20)

Reference image: `C:/Users/sho36/AppData/Local/Temp/codex-clipboard-e4c7e03f-1321-4b46-9872-2bde12f40226.png`.

The user supplied a top-view plant photograph with overlapping purple axis-aligned boxes as the intended labeling example. Interpret it as a workflow/target-granularity reference, not as imported, reviewed training ground truth.

- Target one physical leaflet per bbox, including small visible leaflets. Do not replace this with one whole-plant or whole-compound-leaf box.
- Overlap between boxes is expected. Do not merge identities or discard a candidate solely because boxes overlap strongly.
- A lobe of a leaflet is not automatically a separate leaflet. In the crowded center, confirm organ boundaries and attachment using additional views; the screenshot alone cannot establish every box's botanical identity.
- Use tight bounds around the visible extent. For partially hidden leaflets, record partial visibility and do not invent the hidden outline or treat the visible bbox as a full-leaf spatial constraint.
- Retain separate temporary candidate IDs until review; match the same physical leaflet across top/oblique/side photographs before confirming identity.
- The boxes define a search/crop region, not a segmentation mask. Neighboring leaves and background inside a box must remain separable.
- The screenshot has no verified original-image coordinate mapping or per-box IDs. Do not extract its purple rectangles and silently insert them into the existing source-photo labels. Actual coordinate import requires the original photo mapping and explicit reviewed observations.
- No bbox corners or centers become physical triangulation correspondences. Landmark drafting and acceptance remain a separate step.

This addition records the user's example only; it does not execute detection, inference, training, reconstruction, or label replacement.
