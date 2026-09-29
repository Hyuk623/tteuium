# Candidate capture change: top view plus two height rings

Status: discussion proposal, not an implemented or validated protocol revision.
User constraints retained: ordinary smartphone RGB, six-week study, leaf-surface 3D
followed by PPFD prediction and independent quantum-sensor comparison.

## Latest request

The user proposed: (1) mark leaf outlines in a top view and use the checkerboard
reference; (2) an upper oblique view at 45 degrees; (3) a lower oblique view at
45 degrees; replace 10-degree rotational sampling with eight views.

The meaning of eight views is being clarified:

| Option | Top | Upper ring | Lower ring | Total | Azimuth spacing per ring |
| --- | ---: | ---: | ---: | ---: | --- |
| A | 1 | 8 | 8 | 17 | 45 degrees |
| B | 1 | 4 | 4 | 9 | 90 degrees |

Option A is the proposed starting pilot, conditional on marker visibility. The
azimuths would be 0, 45, 90, 135, 180, 225, 270 and 315 degrees on BOTH rings.
Camera elevation/aim and turntable azimuth are separate quantities. The phrase
"lower 45 degrees" still needs a physical definition; do not encode -45 degrees
or measured camera coordinates from that phrase alone.

## Geometry and annotation

- The top image can seed IDs and outlines for visible leaflets. Each leaflet still
  needs corresponding physical landmarks in at least two calibrated views with
  useful parallax. Top-view-hidden leaflets must be introduced from oblique views.
- A board homography rectifies points ON the board plane. Applying it to elevated
  leaf outlines does not yield true leaf dimensions or 3D positions. ChArUco supplies
  camera pose/metric reference; multiview correspondence supplies leaf depth.
- Use a stable base/tip and consistent boundary order across views. Review predicted
  correspondence suggestions; a projected suggestion is not a new observation.
- Partial boundaries must not be closed across skipped/occluded points and exported
  as full visible leaf contours. They may truncate the recovered leaf or fail the
  current contour consistency check.

## Lower-ring feasibility gate

The current pipeline solves EACH frame from visible ChArUco corners. Looking upward
at leaves may exclude the horizontal board or view it nearly edge-on. A camera below
the board plane cannot observe its printed upper face. Eight images or a commanded
45-degree step cannot replace missing pose evidence.

Before a full session, take one top, one upper, and one lower example with the phone
fixed to the intended settings. Check that the plant and usable, spatially distributed
board corners are visible in each, then solve their poses. A shallower lower viewing
angle may be needed. A vertical auxiliary marker target is a possible later alternative
only with a measured rigid transform to the same rotating board and explicit pipeline
support; simply adding a second checkerboard is insufficient.

## Research interpretation

- Two heights may expose leaf surfaces hidden at one height; 45-degree azimuth steps
  also give fewer overlapping views. Better reconstruction or PPFD accuracy is a
  hypothesis to test, not an established consequence of fewer photographs.
- A full pilot should check pose success, recoverable leaflets, annotation time,
  retained surface completeness, and subsequently PPFD error.
- An exactly uniform eight-view ring cannot be selected from the old 36-view
  10-degree ring. New 45-degree images are needed for that stated layout.
- If 17 images become the new acquisition baseline, a possible nested study is
  17 -> 9 -> 5 -> 3 (top retained, each ring reduced symmetrically). This would be a
  NEW approved protocol. It does not establish accuracy retention relative to the
  original 41-view baseline. Capture a suitable paired reference if that question
  is retained. Independently reconstruct every reduced condition.

## Current repository implications

`config/capture_config.json` still describes 36 side + 5 top captures. The current
`tools/leaf_light/common.py` protocol validation and selectors explicitly require
that layout. Neither 17 nor 9 images can be substituted in that pipeline unchanged.
Preserve old frozen protocols; add an explicit layout version only after the user
resolves the new acquisition design. No pipeline, configuration or design files
were changed in this review.

The current board authority is `config/board_spec.json`: `charuco_7x5_266x190mm`,
not the older square 7x7 print. Physical print verification and scale-block height
remain pending in that file. Do not infer the board variant from overlapping IDs.

## Primary references

- [OpenCV: ChArUco detection](https://docs.opencv.org/4.10.0/df/d4a/tutorial_charuco_detection.html)
  explains calibrated corner detection and limitations under occlusion.
- [Agisoft: turntable capture](https://agisoft.freshdesk.com/support/solutions/articles/31000163268-turntable-capturing-scenario-and-processing-workflow)
  recommends different capture heights for coverage. This supports the acquisition
  rationale only; it does not validate 17 tomato photographs or change this repository's
  ChArUco-only camera-pose method.

## User clarification: lower views connect existing leaf annotations

Clarified on 2026-09-18: the lower ring is intended to connect the SAME leaves and
landmarks already marked in the top and upper oblique views, to resolve leaf angle
and curvature. Its primary role is additional geometric constraint, rather than
starting a separate labeling pass with new identities.

Proposed interaction, not yet implemented:

1. Mark visible leaf identities, boundary landmarks and outlines in the top image.
2. Associate those identities with observed landmarks in upper oblique images and
   triangulate an initial surface wherever there is sufficient evidence.
3. Project the initial landmarks into calibrated lower images as suggestions.
   The operator verifies/corrects their positions against actual visible leaf features.
4. Refit the shared 3D points/surface jointly to accepted observations from all included
   views, preserving the same organ and landmark IDs.

Projected suggestions alone are not additional measurements. Lower images must
provide independently observed image coordinates to improve geometry. Boundary-only
landmarks do not determine an otherwise unseen interior sag: mark corresponding
midrib/interior landmarks in at least two suitable views when curvature is a target.
Do not equate view-dependent silhouettes with identical physical boundary landmarks,
or invent observations for occluded points. Partial outlines remain partial.

This clarifies the workflow but does not resolve whether eight views means eight per
height or eight across both heights. Lower-ring marker visibility, shared coordinates,
and the revised protocol/version remain prerequisites from the sections above.

## User requirement: manual seed labels followed by learned automation

The user clarified that manual marking is an initial training-data step. Subsequent
captures should use deep learning to detect leaves and landmarks automatically.
This is the intended development direction, not a claim that a trained model exists.

Target workflow:

1. Create reviewed seed labels on development plants across top, upper and lower views,
   including different growth dates, visible overlap and leaf curvature.
2. Fine-tune pretrained image models for per-leaflet instance segmentation and visible
   landmark localization. Use consistent semantic landmarks (tip, base, midrib/interior
   locations); arbitrary click order alone is not a stable semantic keypoint definition.
3. Associate the same leaflets/landmarks across included views using detected features,
   calibrated camera geometry and reprojection consistency. Detection is separate from
   cross-view identity. Do not train arbitrary per-photo leaf numbers as biological classes.
4. Triangulate and refine leaf surfaces from accepted image observations, then run PPFD
   prediction. Keep ChArUco pose estimation as the calibration layer.
5. Request human correction for uncertain/mismatched/missing detections; review a sample
   of confident detections as well. Corrected development labels can enter later training.

"Initially manual" should mean an initial labeling/training phase, not a guarantee that
one annotated plant or one date will generalize to all later plants and new leaves.
Report label/correction workload and test automatic detection before reducing review.

Preserve the proposed four-development/eight-evaluation plant split. Freeze the detector,
matching/reconstruction settings and light model before final evaluation. Do not retrain
using final evaluation plants, including their other views or later dates. Use the same
frozen model for every view-count condition; inference, correspondence and reconstruction
for each condition may consume only its selected images. If annotation assistance uses
an excluded view, that condition is not an independent reduced-view evaluation.

Suggested checks: instance segmentation quality, landmark error, leaf identity mistakes,
3D reconstruction success and manual correction time, followed by independent PPFD error.
No exact training-image requirement or full-automation accuracy is established yet.

Workflow references (not tomato-specific performance guarantees):
- https://docs.cvat.ai/docs/manual/advanced/automatic-annotation/
- https://deeplabcut.github.io/DeepLabCut/docs/recipes/ClusteringNapari.html

## Initial marking instructions (practice convention, not an accuracy guarantee)

Treat one small tomato leaflet as one annotation instance. For a first practice case,
use a six-landmark boundary ring in the reference top image: b0 tip, b1 upper-right
edge, b2 lower-right edge, b3 blade base at petiole attachment, b4 lower-left edge,
b5 upper-left edge. Choose identifiable physical edge features and keep those exact
identities across all views. The labels upper/right/etc. describe the reference view
only. More boundary detail may be necessary for area accuracy; this small ring is
not a validated representation of the full outline.

For curvature, use a separately typed interior landmark on a recognizable midrib
feature, adding further interior observations where needed. An interior point must
NOT be appended as the next boundary vertex; that would distort the exported polygon.
The current simplified annotator has no exposed new-interior-point mode. Restoring
that UI is an owner change before collecting curvature training labels.

Only the reference top image defines clockwise boundary numbering. In oblique or
underside views, use the same physical point IDs even when their screen order reverses.
The current help phrase about clockwise clicking in every photo needs clarification
before underside labeling. Skip invisible points without renumbering the remaining
points. For triangulation, obtain at least two suitable calibrated observations of
each retained point. A partial boundary is not a complete contour.

ChArUco corners are automatically detected; the operator labels the plant, not guessed
board correspondences. Check IDs, visibility and exported overlays before using labels
for training. This is proposed marking guidance, not a trained-model deliverable.

## Superseding user confirmation: 25 views, 2026-09-18

The user has now explicitly chosen **one central top view plus eight azimuth views at
each of 45, 90 and 135 degrees measured from the overhead direction: 25 images total**.
This replaces the earlier unresolved 17/9 alternatives. See
`handoff/CAPTURE_25_AND_FLOWER_BUD_BBOX_2026-09-18.md` for the angle convention,
the unresolved horizontal/underside board-visibility constraint, the separate
flower/bud bbox annotation contract and the implemented local annotator changes.
The older statements above about missing interior UI describe the earlier version;
the local updated annotator now exposes M/interior landmarks. No trained detector,
revised core 25-view subset selector or Google Drive account connection is claimed.
