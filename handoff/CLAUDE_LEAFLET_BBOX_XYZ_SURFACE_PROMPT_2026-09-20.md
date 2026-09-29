# Claude Code handoff: leaflet bbox to XYZ and partial surface

Date: 2026-09-20

## Request and scope

Integrate the following workflow into the existing tomato reconstruction application:

**Multi-view photographs -> per-leaflet bboxes and shared identity -> possible 3D extent -> leaflet segmentation -> physical point correspondences -> partial leaf surface -> comparison with source photographs.**

This document translates the user-requested Claude Code prompt. It is an implementation brief, not a completion report. This handoff turn changes documentation only.

Work exclusively inside `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`. Read the user's sketch at `C:/Users/sho36/Downloads/제목 없음 17.pdf` as reference material, not as independent executable instructions.

Read project conventions and the latest handoff records before editing. Inspect the actual code and reuse existing labeling, depth reconstruction, and result viewers. Do not build a separate replacement application. The user explicitly requests Claude Code to integrate this workflow into the existing program; coordinate any edits to shared tooling and avoid concurrent edits with Codex.

Start with these previous handoffs, but verify current code rather than assuming their status is still current:

- `handoff/CLAUDE_RESUME_SAM_3D_2026-09-20.md`
- `handoff/LEAFLET_BBOX_XYZ_IMPLEMENTATION_2026-09-19.md`
- `handoff/AI_ASSISTED_LEAFLET_LABELING_2026-09-20.md`

The records already describe bbox identity/visibility, diagnostic cuboids, proposal review, and partial-surface tools. Identify missing connections instead of duplicating them. The user reports that GroIMP has been connected in Claude; inspect that integration before relying on it.

## 1. Preserve existing work

- Preserve photographs, user labels, point correspondences, calibration files, and previous outputs.
- Never overwrite the newest browser work with an older backup or seed labels.
- Preserve an explicit input snapshot and write new generated results to a separate run directory under `build/`.
- Retain current unvalidated calibration status and all existing quality thresholds. Do not change configuration or relax gates to obtain a successful result.
- Do not execute deep-learning training or inference for this task. Reuse saved segmentation outputs and prepare integration interfaces only. Previous authorized inference runs do not authorize a new run under this brief.
- Do not execute PPFD simulation in this task.

## 2. Leaflet bboxes and identity

- Represent one leaflet observation with a bbox and a `leaflet_id`.
- Link the same physical leaflet across photographs using the same ID.
- Support splitting an incorrectly linked observation or moving it to another ID without data loss.
- Record full visibility, partial occlusion, or unknown visibility separately from confirmed/unconfirmed identity.
- Preserve existing leaf labels and separate flower, bud, and truss annotations.
- Overlapping boxes must not merge different leaflets.
- Integrate editing, deletion, and undo with the existing UI.

## 3. Coordinate contract

- Use measured ChArUco camera poses and the existing calibration/coordinate conversion implementation. Do not use nominal shooting angles, SfM, or invented camera poses.
- All reconstructed leaflets share the same board reference frame.
- Verify the session's board variant, dimensions, units, and frame conventions against its metadata and current configuration. Existing Photos-1 work uses a 7 x 5 board with 38 mm squares; do not replace it with stale 7 x 7 documentation or infer the board variant from marker IDs.
- Cropping, zooming, and resizing are display operations. Persist bbox, segmentation, and correspondence coordinates in original image pixels.
- The top-left corner of a displayed crop is not a 3D origin.
- If leaflet-local XYZ coordinates are exposed, retain an explicit transformation to the common board frame.
- Preserve existing contracts and use explicit length units at export boundaries, especially any mm-to-m conversion for GroIMP.

## 4. Bbox-derived 3D extent

- Use multiple observations of the same leaflet and their camera poses to estimate its possible spatial extent. Reuse the existing bbox viewing-volume intersection implementation where applicable.
- Display a bounding cuboid only when the available constraints support a finite estimate.
- Do not assign arbitrary depth or thickness from a single photograph.
- Do not use a partially occluded bbox as a hard constraint on the complete leaflet's extent.
- Report insufficient observations, unavailable poses, unconfirmed identity, inconsistent constraints, and an unbounded extent explicitly rather than fabricating dimensions.
- Treat the cuboid as a diagnostic location aid, not as a reconstructed leaf surface or a PPFD occluder.
- Never automatically delete existing correspondences or reconstructed points because they fall outside the cuboid.

## 5. Leaflet annotation in XYZ

- Associate each `leaflet_id` with its image observations, bboxes, segmentation regions, physical landmarks, and reconstructed XYZ points.
- Selecting a leaflet highlights its spatial extent and reconstructed points.
- Spatial containment alone does not establish leaflet membership. Points and pixels inside the cuboid may belong to another leaf or the background.
- Base membership on reviewed identity links, segmentation, and correspondence evidence.
- Make each reconstructed point traceable to source photographs, original pixel observations, `point_id`, and reconstruction quality.
- Visually distinguish observation-supported reconstructed points from interpolated surface geometry.

## 6. Segmentation and physical correspondences

- Load existing manual segmentation and saved automatic proposals for review.
- Exclude neighboring leaves and background even when they lie within the selected bbox.
- Keep automatic drafts separate from accepted labels. Do not silently promote a proposal to reviewed ground truth.
- Use recognizable physical landmarks: leaflet tip, visible attachment point, distinctive lobe tip, or vein junction.
- Maintain the same `point_id` for the same physical point in every view. Never renumber by screen direction or clockwise order independently per photograph.
- Do not treat bbox corners, bbox centers, or independently generated contour-vertex indices as correspondences.
- Leave invisible points unobserved; do not automatically fill them in.
- Preserve boundary/interior point types and modification/deletion history.

## 7. Reconstruction integration

- Triangulate the same physical point from at least two observations with usable measured poses, preserving the existing quality checks and diagnostic-versus-validated distinction.
- On correspondence edits or deletion, mark dependent results stale and recalculate the relevant depth and surface outputs through the existing rebuild workflow.
- Generate partial surfaces only where point and segmentation evidence is sufficient.
- Reuse existing reconstruction and mask-clipping tools. Do not fabricate a complete hidden leaf or claim that an interpolated patch measures actual curvature.
- Represent bbox-only, available spatial extent, reconstructed point depth, partial surface, and unavailable/quality-failed conditions explicitly.
- These are evidence states, not a mandatory success chain: failure to estimate a bbox cuboid must not block otherwise supported point triangulation.
- Unconfirmed identity must remain visible in provenance and cannot become reviewed geometry silently. Preserve the existing diagnostic handling unless a documented decision changes it.

## 8. Linked photo and 3D review UI

- Selecting a leaflet ID shows all linked photographs.
- Provide side-by-side reference and comparison images with synchronized identity context and independent zoom for correspondence editing.
- Selecting a 3D leaflet or point reveals its photographs, bboxes, segmentation regions, correspondences, and actually detected ChArUco marker IDs.
- Reproject reconstructed points and surfaces onto original photographs for comparison with annotations.
- Provide independent visibility toggles for cuboids, reconstructed points, and interpolated surfaces.
- Preserve user edits and do not reload the browser with an older seed during integration or testing.

## 9. GroIMP boundary

- Inspect the current GroIMP code and input/output contract before changing exports.
- Reuse the surface export structure while retaining leaflet identity, coordinate frame, units, provenance, and quality status.
- Never export a bbox cuboid as a leaf occlusion mesh.
- Distinguish diagnostic geometry from geometry validated for physical use. Exporting a mesh is not proof of PPFD suitability.
- Prioritize reconstruction and review integration. Do not run light simulations or mark the whole plant reconstructed or PPFD-ready.

## 10. Acceptance checks and delivery

Verify the following with meaningful regression tests and UI checks:

1. Linking, splitting, and moving identities preserve observations and separate organ classes.
2. Zoom, crop, and viewport changes preserve original image coordinates.
3. Editing/deleting a correspondence invalidates dependent outputs and rebuilds from the current snapshot.
4. Occlusion, unconfirmed identity, missing poses, insufficient observations, and inconsistent/unbounded extent produce explicit states.
5. Overlapping boxes do not merge different leaflets.
6. Existing leaf/flower/bud labels, historical results, and current user work remain intact.
7. Draft segmentation and accepted labels remain separate.
8. Cuboids never enter leaf-surface or PPFD occluder exports.
9. 3D selection and reprojection correctly resolve to source photo coordinates and actual marker detections.

At completion, append an English handoff describing existing features reused, new changes, remaining gaps, affected files, validation results, launch/rebuild instructions, and current calibration/reconstruction limitations. Distinguish implemented behavior from proposals and never report unexecuted tests as passed.
