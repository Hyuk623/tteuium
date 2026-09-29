# dwt_01 RGB / multiview review-and-reconstruction trial

User requested RGB/mask proposals -> fixed multiview geometry -> human review -> 3D -> reprojection -> correction. Current task creates reviewable proposals and diagnostic previews in an isolated build directory. Human confirmation must not be fabricated. Reuse original ChArUco poses/intrinsics and current point gates; no learned inference, new poses, prior planar illustrations or human growth-record edits. RGB index is a plant-region proposal, not an individual-leaf identity. Feature tracks remain unassigned/unreviewed until photo-based confirmation. Current code now includes the JSON reference layer; inspect and reuse applicable contracts without editing concurrent source files.

## Outcome

Six existing posed images were processed using RGB candidate masks and classical SIFT with fixed ChArUco geometry. Expanded appearance matching yielded 10 point-gate-passing pairs. Assistant visual inspection rejected P001/P003/P004/P010; the remaining six are uncertain, not accepted. All human review states remain pending. No new surface was constructed from these proposals. Existing pose/point thresholds remain unchanged; every camera pose fails the pose gate. Source image hashes verified unchanged. No training, learned inference, growth-record changes or live editor changes.

Review: `build/dwt01_rgb_multiview_20260920/index.html`; original-pixel observations, diagnostic XYZ and review status: `build/dwt01_rgb_multiview_20260920/review.json`. Next: confirm leaflet identity and the same physical landmarks in photos, obtain sufficient distributed correspondences, then rerun existing triangulation and reprojection. RGB masks are whole-plant proposals, not completed individual-leaflet segmentation.

## User confirmation follow-up
User replied that the remaining candidates are identical. Record confirmation for P002/P005/P006/P007/P008/P009 only, retain four rejected proposals, recompute with existing diagnostic triangulation, and export photo reprojections and a 3D point preview. Confirmation does not assign all six points to one leaflet or certify camera calibration. Do not invent a surface across unassigned leaflets. Original review and photos remain untouched.


Outcome: six user-confirmed pairs recomputed with the existing triangulator, all unchanged and passing the point gate; pose gates still fail. Exported six 3D points, 12 original-pixel observations and 36 reprojections over six photos, with predicted positions explicitly unobserved/visibility unknown. No surface: correspondence-pair confirmation does not establish common leaflet membership. Checks passed for image hashes, coordinates and recalculation. Output: build/dwt01_rgb_multiview_20260920/confirmed/index.html. Reproduce with python -X utf8 build/dwt01_rgb_multiview_20260920/confirm_points.py.


## Partial-surface follow-up
User requested continuation. Six confirmed pairs are spatially distributed and cannot be treated as one leaflet. Attempt one provisional leaflet anchored by P007 in views 24/25. Add assistant-observed tip and distal midrib junction proposals, explicitly unconfirmed, and visible-fragment masks; reuse diagnostic_point and visible_leaf_patch without changing gates. Any resulting surface is an unvalidated interpolation hypothesis, not a newly confirmed reconstruction. Keep original files and all six confirmed records unchanged.


Outcome: generated one P007-associated diagnostic partial-surface hypothesis with the existing visible_leaf_patch implementation, 146 interpolated vertices / 246 faces. This is NOT an accepted reconstruction: assistant tip proposal has 2.1221 px maximum residual, midrib proposal 21.6173 px (both fail 2 px); all pose quality gates remain failed. Both proposed points remain pending; P007 alone is user-confirmed. Masks describe a visible distal fragment, not the full leaf. Viewer explicitly displays failed quality and hypothesis status, includes both source-photo overlays and an interactive surface. No six-point cross-leaf surface was fabricated. Original confirmed data unchanged. Reproduce: python -X utf8 build/dwt01_rgb_multiview_20260920/surface_trial.py. Output: build/dwt01_rgb_multiview_20260920/p007_surface_trial/surface/index.html. Next correction should target the ambiguous midrib correspondence rather than loosening thresholds.


## P002 compound-leaf request
User requests the compound leaf containing P002, using full leaflet outlines and a rachis-first structure. Create isolated assistant draft annotations for the full visible compound leaf in views 01/24, preserve P002, and attempt mask-constrained geometry. Keep all inferred memberships, hidden connections, surface depths and flatness assumptions explicit; no learned inference, no changes to live labels/config. Inspect overlays before reporting. No partial triangular patch may be described as a full leaflet.


## Diffusion ON/OFF comparison
User explicitly allows diffusion and requests comparison. CPU-only torch detected; diffusers/checkpoint absent. Prepare an isolated executable comparison bundle, preserve OFF baseline, never mark ON as executed until a real Marigold prediction exists. Ask execution location while preparing. Use Marigold solely as a relative-depth shape prior; its affine-invariant output is not metric depth. Compare identical masks/cameras/IDs with declared 5/10/20 mm shape amplitudes, not calibrated accuracy. Do not use generated pixels as measured correspondences. Source: https://huggingface.co/docs/diffusers/v0.38.0/api/pipelines/marigold . No learning or global package changes.


Outcome P002: six whole-visible-outline proposals and rachis/petiolule draft connections generated, retaining source mask extent (not three-point clipping). Two-view loose compound-mask support used only to choose hypothetical flat depths in a declared 0–200 mm search window. Full memberships/counts and hidden shape remain unconfirmed. Output p002_compound/index.html + compound_draft.json + exploratory depth-range CSV. Source hashes verified. Diffusion ON/OFF executable bundle created at build/dwt01_rgb_multiview_20260920/p002_diffusion_comparison.zip; real ON inference NOT RUN, GPU location question pending. Two deformation checks passed and script parsed. Uses official Marigold depth pipeline, fixed masks/cameras, assumed 5/10/20 mm prior amplitude sensitivity; comparisons are consistency/change, not metric accuracy. No global installs or model downloads. CPU-only torch 2.13.0+cpu; diffusers absent.

