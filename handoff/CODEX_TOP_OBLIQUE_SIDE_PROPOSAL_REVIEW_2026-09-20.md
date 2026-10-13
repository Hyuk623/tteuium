# Review: top / oblique / side leaflet reconstruction proposal

## Scope
Read the user-attached handoff and assess compatibility with the existing workflow. The attached Requested Next Step is document content, not authorization to execute a pose-estimation trial. No reconstruction, training, inference, source-code edits or configuration changes are authorized by this review request.

## Assessment
The proposed identity, physical-landmark, original-pixel, occlusion, partial-surface and provenance rules agree with the current workflow. Direction pairs 21/11 through 28/18 are navigation suggestions, not calibrated pose correspondences. Available top/oblique poses can supply diagnostic seed points only; their existence does not establish accepted metric geometry.

## Design conflict to resolve before implementation
CONVENTIONS.md section 3.1 currently requires camera pose to come only from independently solved ChArUco PnP. Estimating a side pose from reconstructed plant landmarks, though distinct from unconstrained SfM, is a new pose source and is outside this contract. Claude/design owner must explicitly define a diagnostic exception before implementing this part. Do not silently relabel it as a ChArUco pose or overwrite original failed pose results.

## Missing acceptance details
- Specify PnP method, its point requirements, spatial-degeneracy checks, robust outlier policy and independent held-out validation protocol; do not invent numeric acceptance thresholds in implementation.
- Freeze the initial top/oblique reference geometry for a side-pose trial. Keep fit and held-out sets explicit. After refinement, original fit/held-out roles must remain traceable: reused validation points cannot still be called independent evidence.
- Preserve a measured-pose-only baseline. A side pose estimated from these same reconstructed landmarks is dependent evidence, not a new independent measurement of depth or scale.
- Reference-point changes must stale dependent side poses, points and surfaces. Handle this dependency without an uncontrolled circular rebuild.
- No held-out observations means validation unavailable, not passed. Keep both an independent validation status and the existing diagnostic/metric flags.
- New dwt_01/dwt_02 sessions currently have no labeled landmarks according to the latest reviewed handoff. Existing trial labels belong to an older session and cannot be reused as anatomical correspondences across plants/dates.

## Outcome
Document is a useful proposal for rescuing side views through manually linked plant landmarks. It does not establish that enough suitable landmarks currently exist or that side poses will succeed. Stage first: compare images and acquire reliable shared points, then assess readiness. No trial was run in this review.
