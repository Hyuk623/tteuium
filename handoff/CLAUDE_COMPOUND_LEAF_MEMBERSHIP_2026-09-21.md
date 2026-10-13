# Claude Handoff: Compound-Leaf Membership in Crowded Tomato Images

Date: 2026-09-21
Status: implementation brief prepared; no implementation, training, inference, or reconstruction performed for this handoff.

## 1. Objective and confirmed user decisions

Extend the existing annotation workflow so that leaflets detected in crowded, overlapping tomato photographs can be associated with their parent compound leaves. Use the matching plant/session growth JSON to review counts, while keeping observed evidence and biological reference counts separate.

The user confirmed that each compound leaf's `sub-stem` is annotated as a separate object. This is the starting point for grouping. Do not require the user to redraw all existing labels or create separate detector classes for individual leaf IDs.

Preserve the user's five exact class names and annotation types:

| Class | Current annotation | Role in this workflow |
| --- | --- | --- |
| `compoundleaves` | bbox | Parent compound-leaf instance |
| `leaflet` | bbox | Individual leaflet instance |
| `sub-stem` | mask, separate object per compound leaf | Visible petiole/rachis evidence associated with a parent |
| `main-stem` | mask | Main axis and visible attachment context |
| `growth-shoot` | bbox and mask | Separate organ; do not count as a leaflet |

The current Roboflow task detects these classes in individual photographs. It does not inherently provide botanical parent membership, cross-view physical identities, or 3D landmark correspondences. Do not assume an API or export has already been supplied or inspected.

## 2. Existing functionality to reuse

The inspected `tools/leaf_point_annotator.html` stores leaflet records with `organ_id` and `leaflet_id`; in this leaflet context, `organ_id` denotes the parent compound leaf. It also distinguishes photo-specific `annotation_id` from physical identity and stores original-image pixel coordinates.

`tools/reconstruction_request.py::review_counts` already compares distinct confirmed leaflet identities grouped by `organ_id` against the growth JSON's `compound_leaf_id` and `leaflet_count`. Unconfirmed identities are listed separately. This function reviews membership that has already been supplied; it does not infer botanical membership from images.

The inspected growth record `tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json` contains L01=8, L02=9, L03=9. It contains no spatial positions or image-to-parent assignments. These values are an example from that session, not defaults for other plants or dates.

Re-read the relevant files and recent handoffs before implementing, particularly `CLAUDE_JSON_REFERENCE_BRIEF_2026-09-20.md`. Integrate with the existing editor, reference layer, and review views; do not build a separate labeling application. Coordinate shared-file ownership before edits, and preserve other ongoing work.

## 3. Proposed annotation and relationship workflow

### A. Establish parent anchors

1. Load the photographs, available detector annotations, and correct plant/session growth JSON.
2. Let the user select a compound-leaf bbox and assign or confirm its parent ID, such as L01.
3. Let the user associate the corresponding separately annotated `sub-stem` object with that parent.
4. Store this as an explicit reviewed relationship. A class label alone is not a relationship.

Illustrative identity structure, not new detector classes:

```text
compoundleaves L01
  sub-stem S01
  leaflet F001
  leaflet F002

compoundleaves L02
  sub-stem S02
  leaflet F003
```

Parent membership and cross-view identity are separate decisions: knowing that two observations belong to L01 does not prove they depict the same leaflet.

### B. Propose leaflet membership

Use a relationship graph: compound leaves are parents, sub-stems provide attachment evidence, and leaflets are children. A parent may have many leaflets; a confirmed physical leaflet has one parent within the session. Ambiguous observations may retain multiple candidate parents without a confirmed assignment.

For each leaflet, combine these evidence sources:

- A visible leaflet base or petiolule connection to the associated sub-stem.
- The visible sub-stem mask and a derived centerline, if usable.
- Compound-leaf bbox overlap as supporting evidence only.
- Reviewed observations of the same organ in other views.

The nearest stem in image pixels is not necessarily the attached stem. Mask crossings, overlapping bboxes, and connected foreground regions must not automatically establish physical connections. Do not use a leaflet bbox center as its anatomical attachment point.

When the connection is unclear, show candidate parents and allow the user to select one or keep it unresolved. A manually marked, actually visible leaflet base can provide additional evidence. If that base is hidden, inspect another view instead of inventing it. Candidate scores are heuristic review aids, not calibrated probabilities or acceptance evidence.

If geometric cross-view checks are used, apply existing pose availability and quality rules. Nominal view angles, board IDs, or a growth count must never supply missing XYZ coordinates. ChArUco provides a coordinate reference, not biological identity.

### C. Separate outline refinement from parent membership

Existing leaflet bboxes remain valid annotations. A bbox does not describe the precise leaf boundary and may include other leaves or background.

Allow optional instance-mask refinement when boundary separation is needed. Preserve the original bbox and record mask provenance and review state. For an occluded leaflet, distinguish visible fragments from inferred hidden shape; do not fill hidden regions as observed ground truth. If several visible fragments are confirmed to belong to one leaflet, retain one physical identity with separate visible components.

Do not make mask generation a prerequisite for manually confirming membership. Any learned mask generation is a separate, explicitly authorized execution step; preparing this handoff does not authorize model inference or training.

### D. Make dense scenes easy to review

- Selecting L01 highlights its compound bbox, linked sub-stem, and confirmed leaflets; other objects are faded or hidden.
- Show unresolved membership candidates separately with their supporting evidence.
- Offer side-by-side views for checking hidden attachment regions and cross-view identity.
- Provide assign, unassign, reparent, split, and undo actions without deleting original observations.
- Preserve original-image coordinates through zoom and crop display.
- Display per-parent reference count, confirmed unique count, and unresolved candidates separately.

## 4. JSON and identity contracts

Keep the human growth JSON read-only during automated review. It supplies biological count references, not missing detections, spatial order, or geometry. A discrepancy may reflect occlusion, missed detection, duplicate identity, incorrect membership, or an incorrect reference record; report it for photo-based review.

Examples:

- JSON says L01 has eight leaflets, but one image shows five: this alone is not a labeling error.
- The same leaflet appears in four photographs: count it once after identity confirmation.
- Ten distinct confirmed leaflet IDs are assigned to L01: flag a mismatch; do not delete two labels automatically.
- Two parents both have nine leaflets: their counts cannot distinguish which parent owns a particular leaflet.

Count after cross-view identity review, not by summing detections across images. Where identity remains uncertain, show the unresolved observations without claiming an exact unique total. Count deficits must not force a parent assignment or create a hidden organ.

Reuse existing `organ_id` as the confirmed parent field for leaflet records rather than adding a competing parent field with different semantics. Represent new sub-stem relationships and candidate membership with explicit evidence and review state, using the existing session metadata conventions where possible. Keep unresolved proposals separate from confirmed records; do not invent a parent solely to satisfy an existing storage key.

Retain plant/session scope, image and observation IDs, physical leaflet identity, candidate/confirmed parent, source method, review state, and edit history. A proposal must not silently become confirmed. Bbox and mask annotations for the same growth-shoot observation should link to one object rather than inflate counts.

Reparenting must preserve coordinates and physical-point meaning. Because the existing editor uses parent/leaflet keys, update all dependent references atomically if a key changes, including candidates, provenance, history, and cross-view links. Preserve a traceable mapping; never leave evidence under the old key. Recompute count review and invalidate or revalidate affected reconstruction dependencies through the existing mechanism.

Membership does not create 3D point correspondences. Triangulation still requires the same observed physical landmark across valid views. Bboxes, mask vertex indices, and an inferred stem centerline are not automatically corresponding physical points. Existing calibration quality gates and diagnostic/PPFD restrictions remain unchanged.

## 5. Acceptance scenarios and delivery

Use deterministic fixtures or mocked detections for implementation tests; no trained-model run is needed.

1. Overlapping compound bboxes: containment alone cannot confirm membership; visible attachment evidence or human confirmation resolves it.
2. Crossing/occluded sub-stems: ambiguous leaflets remain unresolved; hidden connections are not invented.
3. Multiple leaflets can belong to one parent, while one confirmed leaflet cannot simultaneously belong to two parents.
4. Same leaflet in multiple views counts once; uncertain cross-view identities are reported separately.
5. JSON count mismatch flags a review item without modifying growth JSON, inventing labels, or forcing assignments.
6. Equal counts for L02/L03 do not resolve parent ambiguity.
7. Assign/unassign/reparent/split/undo preserve observations, provenance, candidate ownership, history, and original pixel coordinates.
8. Old backups without sub-stem membership metadata still load; their missing relationships remain unresolved.
9. Bbox-only observations remain usable without segmentation; growth-shoot bbox/mask pairs do not count twice or enter leaflet counts.
10. No membership action silently changes measured coordinates, promotes failed calibration, or marks a model PPFD-ready.

Expected implementation delivery: integrated parent-selection/review controls, documented relationship metadata and compatibility behavior, focused regression tests, and an updated English handoff distinguishing implemented behavior from proposals and unverified model performance.

Current delivery: this document only. No application code, photographs, labels, growth JSON, calibration, or reconstruction outputs were changed.

## Reference

Roboflow's overview describes instance segmentation as separating individual object masks: https://blog.roboflow.com/instance-segmentation/. This supports the boundary-representation distinction; the botanical membership workflow above is a proposed integration design, not a claim of validated performance on these plants.

## Addendum: Annotation Coverage and Incomplete Views (2026-09-21)

### Request and current implementation context

The user asked whether every labeled photograph must contain annotations for every physical leaflet, then requested this clarification as a Claude handoff.

Claude's completion report in `CLAUDE_COMPOUND_LEAF_MEMBERSHIP_BRIEF_2026-09-21.md` section 6 and the latest LOG report that parent anchors, membership proposals/actions, COCO import, and count review have been implemented. The original document's delivery status above describes its initial preparation. This addendum does not re-request that implementation from scratch, and Codex has not independently verified the reported code changes in this documentation task.

### Coverage rule

A photograph does not need to show or label every leaflet physically present on the plant. It also need not contain all five classes. However, in an image selected for ordinary supervised detector training, annotate every identifiable, in-scope visible object consistently. Do not arbitrarily omit clearly visible leaflets simply to reduce annotation effort.

| Observation in a photograph | Annotation action |
| --- | --- |
| Clearly identifiable leaflet | Create its individual annotation. |
| Partly occluded but identifiable as a separate leaflet | Annotate the observed extent and record partial visibility. |
| Clearly identifiable leaflet, parent compound leaf uncertain | Keep the valid leaflet annotation; leave parent membership unresolved. |
| Leaflet recognizable, but cross-view identity uncertain | Keep the 2D observation; leave the physical identity link unconfirmed. |
| Too blurred or occluded to identify reliably | Keep a review draft or uncertainty record; do not export a guessed confirmed target. |
| Entirely hidden or outside the image | Do not create a photo annotation from a count reference. |

For this observed-geometry workflow, masks describe visible tissue. Do not complete a hidden boundary and present it as an observed mask. A bbox encloses the selected observed object extent and can include background or an occluder; this does not make those enclosed pixels part of the leaflet. Keep the extent convention consistent and preserve existing annotations if their convention needs review.

### Keep four kinds of completeness separate

1. **2D detection annotation:** whether identifiable target objects in a selected image have been labeled.
2. **Parent membership:** whether a leaflet's compound-leaf parent is confirmed.
3. **Cross-view identity:** whether observations in different photographs depict the same physical leaflet.
4. **3D correspondence:** whether observations identify the same physical point under the existing reconstruction rules.

An incomplete parent assignment or absent 3D point is not a reason to discard an otherwise valid detector annotation. Conversely, a complete set of bboxes does not imply complete identity links or a reconstructed plant. Preserve existing review states instead of coupling all four tasks into one mandatory completion flag.

### JSON count review

Example: the growth JSON records nine leaflets for L01, but only five are identifiable in a particular photo. Label those five; do not force four extra boxes or report a per-photo count deficit as proof of a labeling error.

Across views, count confirmed physical leaflet identities once and list unresolved identities separately. A discrepancy against the JSON remains a review finding, with possible causes including visibility, missed labels/detections, duplicate identities, incorrect parent membership, or an inaccurate manual count. JSON must not synthesize hidden organs, assign parents, or change image coordinates.

### Training preparation

- Prefer a smaller, well-reviewed image subset over a larger set with arbitrary omissions of identifiable target objects.
- Keep incomplete annotation drafts available for continued labeling; do not silently treat them as fully annotated training images.
- A custom `uncertain`, `partial`, or review flag does not automatically make the training loss ignore a region. Verify the actual export format and selected trainer before relying on ignore-region behavior.
- If an image contains unresolved target-like regions and the chosen training path cannot represent the intended ignore policy, defer that image from ordinary supervised training until reviewed, or prepare a fully reviewed crop with correctly transformed labels. Do not just remove uncertain boxes and assume the remaining unlabeled regions are harmless background.
- Parent IDs need not be included as detector classes. Preserve the five existing class names; membership is a separate relationship task.
- These are preparation requirements only. No training, inference, or data-export execution is authorized by this documentation request.

### Reconstruction and PPFD implications

Partial labeling can support a partial reconstruction trial. State which observed leaflets and surfaces are represented and which remain unresolved; do not describe it as complete plant reconstruction.

Missing leaf surfaces can omit occlusion in a subsequent light simulation and bias the predicted light distribution. Neither a JSON count match nor complete bbox coverage establishes sufficient surface geometry or PPFD validity. Existing calibration and reconstruction quality gates remain unchanged.

### Follow-up checks

- Nine recorded leaflets and five visible annotations in one image must not trigger automatic completion or deletion.
- A valid leaflet bbox with unresolved parent membership remains available as a 2D annotation.
- One physical leaflet seen in multiple views is counted once only after identity confirmation.
- Blurred/uncertain draft regions are not silently converted into confirmed targets or assumed to be ignored by a trainer.
- Partial reconstruction and full-plant coverage are displayed separately; count reconciliation cannot promote PPFD readiness.

Reference: [Roboflow image-labeling guidance](https://blog.roboflow.com/tips-for-how-to-label-images/) explains why omitting identifiable target instances can introduce false negatives during detector training. The project-specific coverage and membership rules above supplement that general guidance.

Addendum delivery: English documentation only; no source code, labels, growth JSON, calibration, model execution, or reconstruction outputs changed.
