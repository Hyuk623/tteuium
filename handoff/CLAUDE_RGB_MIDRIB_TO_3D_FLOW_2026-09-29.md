# Standalone handoff: RGB midrib detection for tomato 3D reconstruction

Date: 2026-09-29  
Status: proposed workflow for Claude review; documentation only.

## 1. Objective and scope

Use the original RGB appearance inside reviewed SAM leaflet instances to propose visible midribs, reduce manual tracing, and supply reviewable landmarks for the existing 3D pipeline.

```text
Original RGB + reviewed leaflet mask + original annotation ID
    -> image-quality and coordinate checks
    -> normalized RGB + local brightness contrast + ridge evidence
    -> visible endpoint-guided 2D midrib candidates
    -> human correction and acceptance per photo
    -> confirmed physical leaflet identity across views
    -> confirmed matching physical landmarks
    -> triangulated 3D landmarks with quality diagnostics
    -> supported 3D midrib segments + separately labelled interpolation
    -> mask and off-midrib constraints for a partial leaf surface
    -> reprojection review -> existing geometry export -> GroIMP
```

2D detection, cross-view identity, physical point matching, 3D reconstruction and light-model eligibility are separate decisions. This document does not authorize training or claim that midrib detection or these new controls already exist. No implementation, inference, reconstruction or simulation was run for this request.

## 2. Reuse the existing application

- Reuse original photos, accepted masks, bbox prompts, review history, physical leaflet IDs and original-pixel coordinate transforms.
- Reuse side-by-side review, point-ID editing, triangulation, partial-surface attachment and reprojection views.
- Relevant existing components: `tools/leaf_depth_records.py`, `tools/leaf_light/reconstruction.py`, `tools/rebuild_leaf_edit_session.py`, and `tools/groimp_bridge.py`.
- The existing complete-boundary reconstruction path has stronger input requirements than a partial midrib. Do not invent boundary points to satisfy it. Keep a midrib curve as its own derived result until a supported surface can be built.
- The latest inspected Phase-2 exports contain no LeafSurface instances. This workflow addresses an upstream evidence gap; it does not make the current exports PPFD-ready.

## 3. Input and quality checks

For each observation, preserve plant/session/image IDs, source annotation ID, optional confirmed leaflet ID, mask revision, original bbox, image hash and camera/pose references. Parent compound-leaf membership remains independently confirmed or unresolved.

Read the original image and mask separately. Never analyse an image with a coloured mask overlay. Preserve the crop/resize transform and save coordinates in original-image pixels. Store algorithm settings and image representation, including any colour conversion. Keep computational precision; formatting or truncation for display must not alter source coordinates.

Check blur, clipping/glare, deep shadow, mask contamination by neighbouring leaves, occlusion and disconnected visible regions. A confirmed mask does not imply a visible midrib. Keep unusable observations with reasons.

For 2D review, a photo does not need a solved pose. For 3D, it must have an eligible measured pose. Unposed images and nominal turntable angles do not contribute geometric measurements. Preserve the existing 1-pixel quality gate and strict/diagnostic distinction.

## 4. RGB and line-evidence extraction

### Colour ratios

For valid pixels, compute normalized channels:

```text
S = R + G + B
r = R / S; g = G / S; b = B / S
```

Reject or mark low-signal pixels before division; never turn a near-zero denominator into reliable evidence by adding epsilon alone. Record any numerical stabilizer. These ratios cancel a common multiplicative intensity change under the model `(R,G,B) -> k*(R,G,B)`. They do not remove specular glare, clipping, changed illumination colour, automatic white balance or arbitrary phone HDR processing.

For a physically motivated baseline, linearize a documented sRGB image before ratio analysis; retain the original for viewing. Unknown tone-mapped or HDR exports must not be assumed to be linear measurements. Compare representations empirically on the current images.

### Retain brightness information

A midrib may differ from the lamina mainly in brightness. Keep a separate local-contrast channel, for example `(I - local_background)/(local_background + epsilon)` on sufficiently exposed pixels. This is an appearance feature, not a reflectance or depth measurement. Local contrast enhancement must be bounded and recorded.

### Ridge candidates

- Compare colour-ratio contrast and multi-scale bright/dark ridge responses, using Frangi or Sato as candidate primitives.
- Express expected line width in original-image pixels or a recorded fraction of leaflet image size. Do not reuse a fixed resized-pixel width across all images.
- Combine line evidence, local direction continuity and optional user-sampled vein colour. Folds, secondary veins and shadows remain competing candidates.
- Filter RGB with surrounding context rather than blackening everything outside the mask first. Exclude or flag filter responses contaminated by mask boundaries; retain true endpoint observations separately.
- Skeletonization, if used, operates on the vein-candidate image. A skeleton of the whole leaf mask is a geometric medial axis, not observed midrib anatomy.

No universal weights or accuracy thresholds are set here. Tune on development references and record the selected settings before held-out evaluation.

## 5. Endpoint-guided 2D tracing and review

Start with two human-confirmed visible endpoints, ideally the visible leaflet base and tip. Automatic endpoint suggestions remain drafts. If an anatomical endpoint is hidden, label the visible segment endpoint honestly rather than assigning it the hidden base/tip identity.

Search for a path supported by ridge/colour evidence and consistent direction between endpoints. Avoid blindly selecting the longest skeleton branch. A weak preference for the mask interior can aid search but does not establish anatomy.

Return alternative paths, partial segments or `unavailable` when evidence is insufficient. Do not force a line through a shadow, occluder or disconnected mask component. Interpolated gaps, if shown as a visual guide, remain separate from observed segments.

Proposed existing-editor controls:

- Select leaflet; mark/correct endpoints; propose midrib.
- Compare original RGB, colour-ratio view and ridge-evidence view.
- Choose a candidate; add a guidance point; drag/delete points; undo.
- Accept a visible segment, defer or reject with a reason.

Keep midrib width/contrast/continuity controls separate from SAM segmentation sensitivity (the user's existing preference is 20). Algorithm scores are not correctness probabilities.

## 6. Cross-view physical correspondence

After accepting a 2D curve, confirm the same physical leaflet across usable views. Identify homologous visible features: tip, base where visible, distinctive vein junctions or persistent texture features on the midrib.

- Keep one physical `point_id` per feature across images; do not renumber by screen direction.
- Curve sample index, equal 2D arc-length fraction, bbox centre and independent contour vertices are not physical point correspondences.
- Known camera geometry can propose epipolar candidates. Compare local appearance, neighbouring junction order and all available views; an epipolar intersection alone is not confirmation.
- Weak baseline, several intersections or indistinct texture remain ambiguous. Preserve multiple candidates rather than choosing by expected count.
- Occluded features are unobserved. The growth JSON may help review organ identity/counts but cannot supply missing landmark coordinates.

Store photo-level observation IDs, physical leaflet IDs, parent membership and physical landmark IDs separately. Proposed cross-view links do not become confirmed because a 2D midrib was accepted.

## 7. 3D midrib construction

Triangulate only confirmed observations of the same point in at least two geometrically useful posed photographs. Reuse distortion handling, fixed camera poses and the established board coordinate frame in millimetres. Do not introduce SfM or silently optimize camera poses to force agreement.

Report positive-depth checks, view separation/triangulation stability, reprojection residuals and contributing photos. More views improve evidence only when identity and image quality support them. Failed calibration/pose gates remain visible in diagnostic output.

Fit a low-complexity polyline or smooth curve through supported 3D landmarks when the evidence allows it:

- Two 3D endpoints supply a chord; they do not measure curvature.
- Additional distributed landmarks constrain bending. Sparse anchors still cannot establish every wrinkle.
- Label fitted intermediate vertices as interpolated, and stop at the supported extent.
- Reproject the 3D curve onto source images; use an additional independent view for checking when available.

Image agreement is not independent metric validation. Keep `validated_metric=false` until independent physical checks support a change.

## 8. Leaf-surface and GroIMP connection

Use the 3D midrib as a longitudinal constraint. Reviewed masks constrain visible outlines; off-midrib landmarks constrain width direction, cross-leaf curl and twist. A midrib alone does not determine a surface.

Compare a supported planar partial patch with a low-complexity curved variant. Do not force mirror symmetry, fill hidden regions or create a full leaf from count metadata. The bbox cuboid remains a search/display aid and never becomes a leaf occluder.

Keep open triangle surfaces, explicit observed/interpolated provenance, holes and partial coverage. Surface review, material/sidedness review and PPFD eligibility remain separate. Export accepted eligible surface artifacts through the existing bridge and keep `suitable_for_ppfd=false` until the agreed requirements are met. The midrib guide itself is not a thick optical occluder.

## 9. Proposed outputs and change tracking

Adapt these proposed filenames to existing contracts instead of creating a parallel store:

| Artifact | Contents |
|---|---|
| `midrib_observations.csv` | Per-photo candidate/accepted curve samples, original x/y pixels, segment and sample IDs, evidence/review status; sample ID is not physical point ID |
| `midrib_correspondences.csv` | Physical point ID, source observation/image/leaflet IDs, original x/y pixels and confirmation state |
| `midrib_landmarks_3d.csv` | Triangulated board-frame XYZ in mm, source point IDs, view count, errors and quality state |
| `midrib_curve_3d.csv` | Derived curve samples with observed-anchor versus interpolation provenance; gaps remain explicit |
| `midrib_manifest.json` | Immutable source hashes/revisions, transforms, parameters, software versions, relationships, exclusions and diagnostic flags |
| Reprojection overlays | Source RGB plus reviewed masks, 2D curves, physical points and reprojected 3D evidence |

Use explicit states such as `draft_2d`, `reviewed_2d`, `correspondence_pending`, `triangulated_diagnostic`, `partial_3d` and `unavailable`, retaining existing compatible state fields. Mask, identity, point or pose changes mark dependent runs stale; recalculation writes a new derived run under `build/` and preserves history.

## 10. Pilot and verification

Begin with 3–5 identifiable dwt_01 leaflets, preferably with two or three usable views each. Record insufficient cases rather than filling a quota. First compare brightness-only, ratios-only and their combination with identical endpoints and ridge/path settings; use independently reviewed visible midribs as references.

Report centreline distance in original pixels, visible-length coverage, wrong-branch rate, abstentions and correction time. Include wrinkled, shadowed and partially occluded cases, reporting exclusions rather than hiding failures. Freeze development settings before evaluating another plant.

Verify original-coordinate round trips; rejection of dark/clipped evidence; partial endpoint semantics; no automatic point-ID matching by curve fraction; ambiguous epipolar candidates; synthetic 3D point/curve recovery; nearly degenerate views; stale detection; and preservation of existing labels and undo.

A successful pilot provides traceable reviewed 2D midribs and supported diagnostic 3D segments. It does not establish complete leaf surfaces, whole-plant reconstruction, measured curvature everywhere or PPFD accuracy.

## References

- OpenCV projection/triangulation: https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html
- OpenCV CLAHE: https://docs.opencv.org/4.10.0/d6/db6/classcv_1_1CLAHE.html
- scikit-image ridge filters: https://scikit-image.org/docs/0.25.x/api/skimage.filters.html
- scikit-image morphology: https://scikit-image.org/docs/stable/api/skimage.morphology
- Colour normalization assumptions and limitations: https://staff.science.uva.nl/th.gevers/pub/CIP06.pdf

These sources explain generic primitives and assumptions; the proposed tomato workflow still needs project-specific validation. Related local proposal: `handoff/CLAUDE_LEAF_SURFACE_OPTIONS_2026-09-29.md`.
