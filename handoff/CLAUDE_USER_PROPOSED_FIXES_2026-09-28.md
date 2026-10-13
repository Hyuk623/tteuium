# User-proposed changes: problem → cause → fix → result (for Codex)

Written by Claude Code, 2026-09-28. Scope: this project (Tomato 3D phenotyping analysis) only. Each item started
from a user observation, idea or rule. Sources: `handoff/LOG.md` (line numbers given as `L<n>`) and this
session's work. Everything below stays diagnostic (`validated_metric=false`, `suitable_for_ppfd=false`) unless
stated otherwise.

## Standing rules set by the user (apply before anything else)

| Rule | Since |
|---|---|
| **No edits to anything XL-language related** (`tools/groimp_structure_export.py`, `tools/groimp_static_verify.py`, `tools/groimp_bridge.py`, XL/RGG outputs) **until Codex finishes its XL work.** Claude did not touch these files. | 09-28 |
| **Upload split:** Kaggle upload + result collection = Claude; Colab upload + result collection = Codex; either agent may read the other's results. | 09-28 |
| **ChArUco board pose is ground truth.** When the board is visible well enough to solve a pose, modelling uses that pose. SfM is advisory only, never overrides a board pose. | 09-28 |
| Compound-leaf naming is **bottom-up**: L01 = lowest, the unfolding leaf = highest / last ID (replaced the 09-22 top-down rule). | 09-25 |
| Claude's work and decisions to date are the accepted baseline (L234). | 09-27 |

## A. This session (2026-09-28)

### A1. dwt_04 had no main stem; the user saw L02 "continue down" and proposed it was the stem
- **Problem.** S3 of `pipeline_20260927_202748` reported for dwt_04 `stem: unavailable — no stretch of the axis
  is seen by two photos at a usable angle`, and 0 petioles. In the 3D view the L02 region reached down to the soil.
- **Cause (verified).**
  1. Only views 25/26/28 have a board pose. The main-stem polygon exists in view 26 (lower trunk) and view 28 (a
     short upper piece); view 25 has none. The ray fit itself converges (79 rays, all within 2 mm, ray angles
     34°/54°), but the two photos' intervals along the line never overlap (26: t 116.8–183.2; 28: t 205.1–221.1),
     so `consensus()` returns no two-photo stretch and `fit_stem` gives up.
  2. The trunk is still inside the visual hull. `compound_regions()` votes it into whichever compound box covers
     it: in the z 50–60 mm slab, 224 of 270 voxels were region 4 (L02). Projected onto photos 25 and 26 these
     voxels sit exactly on the root-covered trunk (checked visually). The user's observation was correct.
  3. Rejected alternative: joining the two disjoint polygon segments with one straight line. Checked against the
     unlabelled view 25, that line lies beside the trunk (38% of samples on plant pixels vs 51% for a control line
     shifted 20 mm). Not adopted.
- **Fix** (`tools/plant_structure.py`, owner Claude).
  - New `stem_from_hull(cams, views, dets, H)`: selects hull voxels that project inside any main-stem polygon, then
    traces them upward from the lowest 2 mm slice, keeping voxels within 12 mm of the previous slice centre;
    stops when a slice is empty or holds more than 3× the running median (canopy). Needs ≥ 5 slices. Slice
    centres are fitted by one straight line. Output: `status='fitted'`, `method='hull_trunk'`, `axis` (12 points,
    same format as before), `z_mm`, `tilt_deg`, `slice_centre_distance_mm`, `slices`, `trunk_voxels`,
    `trace_stop`, `diameter_mm=None` (the dilated hull is wider than the stem), `ray_line_distance_mm=None`,
    `ray_fit_unavailable=<original reason>`, `trunk_voxels_taken_from_regions`.
  - `build()`: runs the ray fit first (now tagged `method='ray_fit'`); **only if it fails** runs the hull trace;
    trunk voxels are set to region −1 **before** naming, so region heights describe leaves. Plants whose ray fit
    already worked (dwt_01/02/03) are unchanged. New parameters recorded in `structure.json → parameters`.
  - `tools/plant_site.py` / `plant_site.html`: stem distance read from either field; the stem box explains the
    hull-trace method and shows no diameter. `tools/plant_pipeline.py`: S3 status says
    `줄기 맞춤(아래 줄기, 외곽 추적)` for this method.
- **Result** (fresh run `build/stem_fix_20260928/dwt_04_structure/`, old run untouched).
  - Stem fitted: z 54.5–92.5 mm, tilt 10.3°, 20 slices, slice-centre distance median 2.3 mm / p90 5.4 mm; it
    projects onto the trunk in the independent view 25 (`overlays/dwt_04_20260920_25.jpg`).
  - 2,116 voxels moved from L02 to the stem; L02 median z 100.5 → 101.5 mm; names unchanged (L01–L04, L05
    unfolding has no region).
  - Petioles 0 → 1 fitted (region 4 / L02), because petiole fitting needs a stem.
  - Tests: `python -m pytest tools/tests/test_plant_pipeline_tools.py -q` → 17 passed (2 new:
    `test_trunk_is_traced_through_the_hull_when_one_photo_labels_the_stem`,
    `test_trunk_trace_reports_unavailable_without_stem_polygons`). Mutation-checked: removing the 12 mm radius
    and removing the canopy stop each make the new test fail.
  - **Not done:** the full pipeline was not rerun, so `pipeline_20260927_202748` and the 3D site still show the
    old dwt_04 stem. The next `python -X utf8 -m tools.plant_pipeline --all` picks the fix up. The XL export of
    that new run is Codex's step (XL freeze).
  - Limits: lower trunk only (inside the canopy the stem is not traced); straight-line model; poses still fail
    the 1 px gate.

### A2. Kaggle leaflet-detector members A/B collapsed
- **Problem.** `dolgfish/tomato-leaflet-member-a/-b` LOPO box mAP50 A 0.615/0.192/0.525/0.019,
  B 0.339/0.000/0.295/0.238 (held-out plants dwt_01..04); held-out predictions 150–600 per photo vs 8–30 labelled.
- **Cause (verified from the per-epoch val curve).** Val mAP50 stays ≈0 for epochs 2–30 before the model starts
  learning. With `patience=30`, folds dwt_02/dwt_04 stopped at epoch 33–40 and kept `best.pt` = epoch 1. Folds that
  ran all 150 epochs are normal (A dwt_01 0.626 and still rising at epoch 139). Labels were checked by overlay
  (`build/leaflet_detect_20260927/check/`): correct.
- **Fix.** `epochs=200, patience=0` in `kernel_A/B/C/train.py` and `kernel_template.py`. C v2 pushed 09-28 10:44;
  A and B queued by `build/leaflet_detect_20260927/push_queue.py` (detached; retries on "2 GPU sessions" and on
  intermittent `api.kaggle.com` DNS failures from this PC).
- **Result.** Pending. After A/B/C finish: download, then `python -X utf8 -m tools.leaflet_fusion --oof <dir>
  --dataset build/leaflet_detect_20260927/upload/dataset`. Caveat: `best.pt` is still chosen on the held-out
  plant's val (mild selection leak, same as organ v3).
- Also: on this PC run the Kaggle CLI with `PYTHONUTF8=1`; otherwise `kernels output` writes 0-byte `.log` files
  (cp949 console error).

### A3. Four-plant OBB and SAM (collected this session)
- `tomato-leaflets4-obb`: held-out mAP50 0.860 / 0.813 / 0.829 / 0.835, long-axis error median 9.1–12.6°,
  within 30° 81–88% (2-plant version was 0.78 / ~15°). Weights `build/leaflets4_20260927/kout_obb/leaflet_obb_4plants.pt`.
- `tomato-leaflets4-sam`: held-out IoU median base 0.855–0.885 → tuned 0.890–0.907; IoU ≥ 0.5 88–91% → 91–97%.
  Weights `build/leaflets4_20260927/kout_sam/sam2_tiny_decoder_tuned_4plants.pt`. Not yet wired into the pipeline.

### A4. SfM without board poses (user idea 09-27)
- **Problem / idea.** Too few photos have a board pose (dwt_04: 3 of 17); SfM might add cameras.
- **Result** (`dolgfish/tomato-sfm`, CPU pycolmap; `build/sfm_20260927/kout/sfm_results.json`). Registered
  10/18, 10/18, 13/18 (2 models), 12/17 (2 models). Alignment to the board frame failed for **all four** plants:
  camera-centre differences after a similarity fit 55–206 mm, leave-one-out 72–361 mm (dwt_02 one view 21 m);
  rotation differences 28–57° (dwt_01) and ~95–180° (dwt_02/03/04, possibly a rotation-convention error in the
  comparison — not investigated). dwt_04 new views land kilometres away.
- **Decision (user).** Board pose first; SfM is not used for modelling. Correction: an earlier chat summary in this
  session called dwt_01 "normal" — it was not.

## B. Earlier user-proposed changes (from LOG)

| Date | Problem / proposal | Cause / finding | Fix | Result |
|---|---|---|---|---|
| 09-22 (L181, L195) | Whole-plant shape wanted for dwt_02 | Labels give only per-photo boxes | Visual hull from posed oblique silhouettes, then 1 mm grid | dwt_02 60.8 cm³ envelope; became S3 hull |
| 09-22 → 09-25 (L205, memory) | Compound naming rule | User rule changed top-down → bottom-up | `name_regions` bottom-up; L01 lowest | In use |
| 09-24 (L215) | Small top region named L01 after growth JSON edit | Unfolding leaf was named by height | Unfolding leaves take the smallest regions | Test added |
| 09-24 (L217) | Human-only work should drive reruns | — | Review page → `human_checks_*.json` in Downloads; `human_check_watcher.py` reruns the pipeline | Running |
| 09-25 (L225) | User saw dwt_03 compound colours far from the plant | Few-view carving leaves detached blobs | `main_component`: keep largest 26-connected piece | 488–2,649 voxels removed per plant |
| 09-25 (L222) | Which SAM for dwt_03/04 drafts | User chose the leaflet-tuned SAM | Merged tuned checkpoint | 296 / 408 drafts |
| 09-25/27 (L223, L226, L227, L229) | Apply the dead-tree competition recipe to organ boxes | Heavy geometric aug made the dwt_01 fold degenerate (250–290 leaflets/photo) | v3 = baseline aug + 3 seeds + flip TTA + WBF | Leaflet AP50 0.679 → 0.691; final models `kout_v3/final_all_s{0,1,2}.pt` |
| 09-27 (L231) | Four rejection reasons (occluded, duplicate, box misses leaf, false positive) | — | Reasons/visibility in the mask editor; `reject_reasons.html` for 125 old rejections; S2 applies them | Occluded → accepted partial |
| 09-27 (L233) | Pose-free cross-view leaflet linking (after Alocasia dedupe) | Leaf surfaces give too few correspondences (SIFT 0 pairs, LightGlue 1–2, DINOv2 3/9 mutual) | Not adopted; appearance only ranks review questions | Linking needs geometry |
| 09-27 (L236) | Leaflet-only detector, each member its own model, weighted fusion ("all in") | — | Members A/B/C + `tools/leaflet_fusion.py` (nested-LOPO weights) | See A2 |

## C. Corrections to Claude's chat answers earlier on 09-28 (so they are not reused)

- "Connect the L01 and L02 centres to get the dwt_04 stem" — wrong: the two centres are 47 mm apart horizontally;
  compound centroids are not on the stem. Superseded by A1.
- Auto-mesh answer cited `build/pipeline_20260927_202748/dwt_01/surfaces/leaflet_surfaces.csv` and a
  `--variant full` option as existing S3 surfaces — not verified; no such file was checked. Per
  `CODEX_STATIC_XL_IMPLEMENTATION_2026-09-27.md`, real-data XL exports contain zero leaf meshes and `--geometry`
  needs an existing geometry CSV plus an existing variant.
- "The GroIMP GUI lets people edit the structure" / "Colab verification is available" — overstated: GUI visual
  inspection is unverified, and the Colab bridge is in progress (`CODEX_COLAB_XL_BRIDGE_2026-09-28.md`).

## D. Open items for Codex

1. After the next `plant_pipeline --all`, regenerate the static XL export for the new run (your call on timing;
   dwt_04 `MainStem` should become `fitted` with `method='hull_trunk'`, `diameter_mm=None`).
2. dwt_01 S6 guard (`Prepared import source changed; crop validation is required before reimport`) is still yours.
3. If a Colab runner is added for heavy steps, keep the upload split rule above.

## Codex readback — 2026-09-28

Requested scope: inspect this handoff. Read the current LOG/TODO, inspected the referenced hull-trunk implementation and its test definitions, and read the saved dwt_04 structure output. No pipeline rerun, training, inference, source-code edit or new XL export was performed during this readback. The stated 17-test result is Claude's reported result, not a new Codex test run.

- The saved stem agrees with A1: `method=hull_trunk`, z 54.5–92.5 mm, tilt 10.3 degrees, 20 slices, median slice residual 2.3 mm, diameter unavailable, and 2,116 region-4 voxels reassigned. The residual measures the fit to derived slice centres; it is not independently measured physical accuracy.
- Qualify the petiole result: the one `fitted` region-4 petiole lists **only view 25**, two polygons, `length_two_view_mm=null`, and `extent_any_view_mm=3.2`. Preserve this distinction when displaying/exporting it; do not describe it as a petiole segment verified in two photographs.
- Section C's Colab progress statement is superseded by `CODEX_COLAB_XL_BRIDGE_2026-09-28.md`: local roundtrip and actual hosted static export passed for four plants; hosted-result download/local import remains pending. No GroIMP execution or heavy reconstruction was added to Colab.
- Interpret board-pose precedence as the selected coordinate/pose authority, not independently validated ground truth. Existing failed 1-pixel gates and diagnostic flags remain authoritative for quality reporting.
- The new dwt_04 output is separate from `pipeline_20260927_202748`. Existing XL exports remain snapshots of that older run. A new pipeline snapshot is needed before regenerating XL with the hull-trunk result; do not silently replace the fixed input.

## E. Session-wide user problems and responses — Codex consolidation, 2026-09-28

The user requested adding the session-wide explanation to this same file in the existing problem → cause → fix → result format. This is a documentation-only consolidation of conversation history and recorded implementation evidence, not authorization to rerun models. Historical test counts below refer to their original work sessions; no tests or research computations were executed for this addition. Preserve the earlier entries as dated history.

### E1. Obtain depth and real scale from ordinary phone photographs
- **Problem.** RGB photographs do not directly provide leaflet depth, length or inclination.
- **Cause.** A pixel specifies a viewing direction; depth and metric scale need additional constraints.
- **Method.** Use camera calibration and session-specific ChArUco dimensions to solve measured poses, then triangulate observations of the same physical landmark. Keep original-pixel coordinates and the established board coordinate transformation.
- **Result / limit.** The capture/import and diagnostic reconstruction paths exist. Solving a pose is distinct from passing the 1-pixel quality gate; current failed gates remain visible. A board marker does not identify which point on a leaflet corresponds across images. See the importer and hybrid-side-pose handoffs and LOG entries dated 09-20.

### E2. Separate overlapping leaflets without tracing every outline manually
- **Problem.** Dense foliage makes full manual outline annotation expensive; a compound-leaf box contains several leaflets.
- **Cause.** Boxes locate an object but also contain background and overlapping organs.
- **Fix.** Prompt SAM with each existing leaflet bbox, preserve multiple mask candidates, and let the user correct and accept each observation. Compound boxes remain contextual regions, not a substitute for individual leaflet instances.
- **Result / limit.** The dwt_01/02 batch generated candidates for 577 photo-level observations across 30 photos. This is neither 577 unique physical leaflets nor proof that all masks were accepted. Later review states supersede the initial batch counts. Source: `CODEX_LEAFLET_MASK_BATCH_2026-09-22.md`.

### E3. Remove adjacent leaves from a petiole mask while preserving real small leaves
- **Problem.** The user highlighted regions around a petiole; some were additional leaves, not disposable noise.
- **Cause.** Nearby plant parts can share colour and touch the requested segmentation region.
- **Fix.** Use positive/negative prompts, sensitivity adjustment and manual boundary editing to isolate the intended organ. Keep separate leaflets as separate observations; do not erase them merely because they are small or near the petiole.
- **Result / limit.** These correction mechanisms are available. No claim is made that every circled region in the historical screenshot was individually corrected. Sources: `SAM_PETIOLE_SENSITIVITY_2026-09-19.md`, mask-review handoffs.

### E4. Compare sensitivity visually for compound leaves and leaflets
- **Problem.** The user could not tell which sensitivity setting produced a suitable mask.
- **Cause.** A single default threshold hides boundary changes and can include neighbours or omit small regions.
- **Fix.** Add class/photo selection, cached-logit sensitivity previews, candidate comparison, explicit save/restore and undo in the existing editor. Preserve the user's preferred initial value of 20 without treating it as a universal optimum.
- **Result / limit.** Implemented and browser-checked in the original work session. Sensitivity is a boundary setting, not an accuracy percentage. Source: `CODEX_COMPOUND_LEAFLET_SENSITIVITY_WEB_2026-09-22.md`.

### E5. Make incorrect annotations easy to repair
- **Problem.** Incorrect points, boxes or mask regions need direct correction rather than restarting annotation.
- **Fix.** Use the existing selection/edit/delete controls and history; extend mask editing with paint, erase, brush radius, explicit save and undo. Zoom/crop is for display while stored coordinates remain tied to the original image.
- **Result / limit.** Brush integration and save/restore/undo were verified during Document 06 work. Editing a mask does not confirm identity, depth or a 3D surface. Source: `CLAUDE_DOCUMENT_06_ONLY_COMPLETION_2026-09-22.md`.

### E6. Distinguish the same leaflet across photographs
- **Problem.** The detector's class label and per-photo annotation do not establish whether two views show the same leaflet.
- **Fix.** Keep source annotation ID, physical `leaflet_id`, optional parent `compound_leaf_id`, and physical landmark `point_id` separate. Use side-by-side review and explicit identity link/split controls; uncertain links stay unresolved.
- **Result / limit.** Identity review/import exists, with seven reviewed physical leaflet IDs in the fixed dwt_01 XL snapshot. Other plants retain proposals. Accepted masks do not automatically establish cross-view identity. Sources: LOG cross-view identity entries, static XL handoff.

### E7. Repair provenance left behind after identity splitting and ambiguous point matches
- **Problem.** Splitting a leaflet left feature candidates/source records under the old identity. Multiple reference points targeting the same comparison point were not marked ambiguous.
- **Cause.** Metadata migration did not follow the split/relink operation completely; ambiguity checks were directional.
- **Fix.** Migrate view metadata and assigned drafts with split/relink, preserve history/undo, and check correspondence ambiguity in both directions.
- **Result / limit.** Recorded as fixed on 09-20, with 65 distinct Node tests and 13 Python mask/server tests reported. This supersedes the preceding chat summary's statement that final verification was unknown. Enabling SAM then did not establish successful full-photo automatic generation: that trial timed out. Source: `CODEX_AUTO_DRAFT_FIX_2026-09-20.md`, LOG entries 115–117.

### E8. Reduce manual physical-landmark entry
- **Problem.** Entering every correspondence by hand is slow.
- **Fix.** Generate geometric landmark candidates and cross-view matching proposals with recorded provenance and geometric checks. Require acceptance before promoting a proposal into a physical `point_id`; keep ambiguous/rejected candidates separate.
- **Result / limit.** Candidate tooling is implemented. It does not guarantee matching physical points, and appearance-only experiments did not provide reliable enough links to replace review. Sources: `CLAUDE_AUTO_BBOX_LANDMARK_BRIEF_2026-09-20.md`, section B above.

### E9. Show a rough 3D location before reliable landmarks exist
- **Problem.** The user wanted XYZ annotations and a bounding cuboid for each leaflet before full surface reconstruction.
- **Method.** Intersect the viewing constraints of identity-confirmed boxes using known camera poses. Use fully visible observations for finite extent constraints; partial observations must not exclude hidden parts. Report insufficient or inconsistent evidence explicitly.
- **Result / limit.** The bbox-extent and diagnostic evidence workflows provide location guidance. A cuboid is not a measured leaf or a PPFD occluder. Do not delete annotated points merely because they fall outside an uncertain extent. Sources: three-route fusion and Document 06 handoffs.

### E10. Display whole-plant structure when leaf surfaces are missing
- **Problem.** Boxes and incomplete landmarks did not produce a recognizable whole plant.
- **Method.** Intersect silhouettes from posed photographs on a voxel grid to obtain a visual hull; show stem axes, leaflet evidence and compound-region proposals as separate layers.
- **Result / limit.** Whole-plant diagnostic views exist. The occupied envelope is not leaf tissue volume, and its exterior is not a validated collection of leaf surfaces. The separate S7 visibility/intersection concerns remain open in `CODEX_PIPELINE_REVIEW_2026-09-27.md`; do not assume all downstream geometry follows Document 06's occlusion rules.

### E11. Assign leaflets to compound leaves and use growth JSON
- **Problem.** Compound boxes overlap, and per-photo detections disagree with the user's organ counts.
- **Cause.** Repeated views count the same organ multiple times; occlusion and missed/duplicate detections affect counts. Box containment alone is not biological attachment.
- **Fix.** Read growth JSON as reference information, compare observed/confirmed/proposed counts separately, and use compound regions and connection evidence to propose membership for review. Preserve unresolved parentage. Use the user's bottom-up naming rule: L01 lowest, unfolding leaf last.
- **Result / limit.** JSON reference checks and hierarchy review exist. Counts never authorize inventing missing organs, forcing memberships, or silently changing user records. Global/vertical/circumferential routes reuse observations without counting the same photo as independent evidence twice. Sources: `CLAUDE_JSON_REFERENCE_FOR_THREE_ROUTE_3D_2026-09-20.md`, LOG and section B.

### E12. Recover information from side photographs without a solved board pose
- **Problem.** Side photos show useful organs but often lack enough visible board corners.
- **Method.** Keep the board-pose baseline and a separate diagnostic feature/landmark pose path, with frozen references and pose-source reporting. Do not invent camera locations from nominal turntable angles.
- **Result / limit.** Diagnostic feature poses support some identity proposals. They retain their uncertainty and do not silently become qualified ChArUco poses. SfM was also tested, but alignment failed for all four plants; it was not adopted for modelling. Sources: `CLAUDE_HYBRID_SIDE_POSE_BRIEF_2026-09-20.md`, section A4.

### E13. Remove detached spatial blobs far from the plant
- **Problem.** The user saw coloured compound regions detached from the plant.
- **Cause.** Few-view silhouette intersections can leave disconnected candidate volumes.
- **Fix.** Claude added largest-26-connected-component selection to the visual-hull workflow.
- **Result / limit.** Recorded removals were 488–2,649 voxels per plant. This is a geometric filtering heuristic, not proof that every removed piece was false; it can lose real disconnected visible organs. See section B and LOG dated 09-25.

### E14. Separate the dwt_04 lower trunk from L02
- **Problem / cause.** The lower trunk fell inside compound boxes and was assigned to L02; the original two-view stem fit had no overlapping observed interval.
- **Fix.** Follow hull voxels under main-stem labels upward in 2 mm slices, limit continuation to a 12 mm neighbourhood, stop at gaps/widening, fit a diagnostic line and remove identified trunk voxels from compound membership. See A1 for full details.
- **Updated result.** The latest Claude LOG now records **full rerun `pipeline_20260928_122948`**, which includes the hull-trunk fallback. This supersedes A1 and the earlier readback's statement that a pipeline rerun is still needed. XL exports still reference `pipeline_20260927_202748` and have **not** been regenerated. Whether the previously shared remote Claude Artifact has been republished is not verified.
- **Limit.** The one fitted petiole has only one listed view and no two-view length; preserve the readback qualification above.

### E15. Improve automatic organ/leaflet models without equating training with deployment
- **Problem.** Some leaflet detectors returned far too many boxes; better leaf orientation and mask drafts were also requested.
- **Fix.** Inspect training curves and labels, disable the problematic early stop and increase training duration for A/B/C; separately evaluate four-plant OBB and tuned SAM outputs. See A2/A3.
- **Result / limit.** A/B/C rerun results remain pending in the inspected records. Four-plant OBB/SAM assets were collected; the four-plant SAM is not yet wired into S2. S2 currently uses baseline SAM for dwt_01/02 and the earlier two-plant-tuned SAM for dwt_03/04. Held-out model-selection leakage remains a reporting qualification, not an independently unbiased performance claim. No new training/inference was launched for this consolidation.

### E16. Transfer existing reconstruction structure into XL/GroIMP
- **Problem.** Existing Python IDs, parent relationships and diagnostic positions needed to remain usable in GroIMP.
- **Fix.** Implement static XL/RGG export with scoped organ IDs, separate confirmed/proposed relationships, explicit missing geometry, source hashes and one mm-to-m conversion. Do not invent surfaces for position-only leaflets.
- **Result / limit.** All four fixed-run exports and a synthetic mesh case passed local GroIMP CLI compile/reset/save/reopen. Real exports contain zero leaf meshes; visual GUI verification remains separate. No L-system growth rules or PPFD simulation were added. Source: `CODEX_STATIC_XL_IMPLEMENTATION_2026-09-27.md`.

### E17. Use Colab when local compute is insufficient
- **Problem.** The user requested a Colab connection as a resource fallback.
- **Fix.** Implement an interactive portable input ZIP, pinned environment, guided notebook, static-export execution and verified local result importer. Use sidebar upload when the embedded upload chooser fails.
- **Result / limit.** Four plants passed the local roundtrip and actual hosted static export. Hosted download/import remains pending because no download was observable in the current browser. This is not automatic CPU failover and does not offload reconstruction, training or GroIMP execution. Source: `CODEX_COLAB_XL_BRIDGE_2026-09-28.md`.

### E18. Make capture/calibration imports trustworthy without discarding the user's work
- **Problem.** Calibration compatibility was checked too weakly, board-description provenance was hardcoded, and source changes could invalidate prepared inputs.
- **Fix.** Compare declared camera/lens evidence, report compatibility as unverified when evidence is absent, record supplied board-caption provenance, preserve raw values, and compare focal lengths using the user-confirmed truncation to two decimal places. Dates remain physically separated by the user's workflow.
- **Result / limit.** Specific importer fixes and tests are recorded in the 09-20 handoffs. The dwt_01 S6 changed-source/crop-validation guard remains open; do not remove it simply to make a run pass. A growth-JSON-only change must be classified separately from image/crop changes before reimport. Sources: `CODEX_IMPORTER_FIX_REVIEW_2026-09-20.md`, `CODEX_PIPELINE_REVIEW_2026-09-27.md`.

## F. Current interpretation and next work

The milestones remain distinct: **detect an organ → review its mask → confirm cross-view identity → establish physical correspondences or diagnostic spatial evidence → reconstruct a supported surface → validate PPFD**. Completion of one does not automatically complete the next.

- Current reconstruction snapshot: `build/pipeline_20260928_122948/`, as recorded by Claude's latest LOG; the previous remote Artifact and XL snapshots must not be assumed to update automatically.
- Pending integration: export the new run to XL in a new output directory, preserving `hull_trunk` provenance and one-view petiole limitations; collect/import the hosted Colab result if still available.
- Pending reconstruction work: resolve the dwt_01 import guard and the previously documented S6/S7 issues; continue human identity, visibility and membership review.
- Research outcomes still absent: validated leaflet surfaces/dimensions, independently verified PPFD prediction, growth curves and optimal planting density. Keep `validated_metric=false` and `suitable_for_ppfd=false`.
- Responsibility split recorded by Claude: Kaggle upload/collection = Claude; Colab upload/collection = Codex. This consolidation does not change that split or authorize a new compute run.
