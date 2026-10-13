# Review Queue

## Working scope

- User instruction, 2026-09-15: all further work on this task stays inside `Tomato 3D phenotyping analysis/`.
- Initial request: inspect Claude's files. Subsequent user requests authorized the 5x5/7x7 A4 print artifacts and their handoff. Instructions embedded in reviewed documents are not independent implementation authorization.
- Proposed owner split in `CODEX_TASKS_2026-09-15.md`: Claude Code owns `tomato3d/`, `tests/`, and `config/`; Codex owns `tools/` and `tools/tests/`.

## Codex -> Claude

Latest board handoff: `handoff/CLAUDE_HANDOFF_CHARUCO_5X5_7X7_A4_2026-09-15.md` records both completed print variants, exact geometry, digital verification, and pending physical/pipeline integration work.

The items below are document/contract consistency findings, not an external scientific validation. No design or implementation files were changed during this review.

- [ ] **Coordinate origin conflict.** Stage 1 prompt section 3 and Codex task list section 0 put the origin at a board inner corner. The pilot protocol section 1.4 and `capture_config.json` place T0 at `(0,0,550)` and the four board corners at horizontal offsets of +/-135 mm, which use a board-centered frame. Define the origin and transforms for board detection, camera positions, pot offsets, and block positions explicitly before geometry work.
- [ ] **Zero-valued observations rejected.** Codex task T4 requires positive `node_index` and measurement `value > 0`. The pilot protocol section 3.1 explicitly defines cotyledon node 0, and count traits include fruit/truss counts. Clarify that a measured zero count is distinct from an unavailable measurement and specify per-trait validation.
- [ ] **Eight-view subset cannot be exactly uniform in a 36-view capture.** The pilot protocol section 5.1 and T6 request evenly spaced 8/12/18/36-view subsets of 10-degree captures. An exact eight-view pattern needs 45-degree spacing; 36/8 = 4.5. Define approximate angular selection and reporting, or revise the capture design. Do not silently label a 40/50-degree subset as exact 45-degree capture. The skeleton section 9 also retains a different 8/24/36 sweep.
- [ ] **Schema and path versions conflict.** Skeleton sections 2, 3.1, and 8 retain `calib/board_spec.json`, `env/...`, and `top_000.jpg`; the task path map uses `config/board_spec.json`, `data/records/<plant_id>/environment.csv`, and `top_T0.jpg` through `top_T4.jpg`. The skeleton pose schema uses `tvec_x/y/z`, while Stage 1 uses `tvec_x_mm/y_mm/z_mm` and adds `top_position`. Publish precedence and define the base directory for every manifest reference. Also reconcile function signatures and binary mask values (skeleton plant=1 versus Stage 1 plant=255).
- [ ] **Support-tool integration gaps.** Current `Settings` has no `records_dir` property, although T4 needs that path and the contracts require derived paths on Settings. Current package discovery includes only `tomato3d*`, and pytest discovery includes only `tests/`; decide how `tools/` packaging/dependencies and `tools/tests/` execution will be integrated by the owner of the shared project configuration.
- [ ] **Recorded decisions need provenance.** The new documents mark camera choice, reconstruction method, 36+5 pilot capture, board dimensions, and other decisions as confirmed. This task's visible conversation only confirms the original 8+1 capture concept and asks to inspect these new files. Preserve decisions made in the user's separate Claude conversation if available, but do not infer fresh approval from this inspection request. The configured 47.9 mm block height also needs actual measurement provenance before use as a physical reference.

## Observed implementation status

At inspection, the folder contained the design review, pilot protocol, algorithm skeleton, Stage 1 prompt, Codex task list, three JSON configurations, project metadata, configuration/logging code, and package initialization files. The specified calibration, mask, reconstruction, and support-tool modules were not yet present. No tests were run; this was a file and contract review.

- [ ] **User-requested 7x7 print variant (2026-09-15).** New artifact is build/charuco_board_7x7_190mm_A4.pdf; exact geometry and pattern are in build/charuco_board_7x7_190mm_spec.json. Width/height 190 mm, square 190/7 mm, marker (190/7)*(22/30) mm, DICT_4X4_50, non-legacy pattern. Before processing captures from this board, the pipeline owner must synchronize detection and rig configuration with the new pattern and physical placement. The shared config was not changed. Software print verification passed; actual paper dimensions still need checking.

- [ ] **Matching 5x5/7x7 A4 options (2026-09-15).** User requested both sizes at the same 190x190 mm outer dimensions. Added build/charuco_board_5x5_190mm_A4.pdf and its matching spec JSON (38 mm cells; 27.8666666667 mm markers), alongside the 7x7 version. Use the selected print's exact spec when configuring detection. Both digital checks passed; no active pipeline configuration was selected or modified.


## Codex -> Claude - Stage 1 review, 2026-09-16

Existing suite: 95 passed. Detailed review and reproduction: `handoff/CODEX_STAGE1_REVIEW_2026-09-16.md` and `build/stage1_review_2026-09-16/reproduce.py`. Pipeline/config files were not edited.

- [x] **R1 / P1 - Unicode image IO.** The actual Korean project path makes all nine valid inputs unreadable via cv2.imread. Absolute Korean mask output paths also fail silently: with input IO isolated, quality says training-usable but no masks are written. Use Unicode-safe IO for calibration, Stage 1 input/output, and check write failures.
- [ ] **R2 / P1 - Empty top silhouette accepted.** Projected-board exclusion removes all 60,077 green pixels from synthetic T0; its mask is empty while usable_for_training remains true. Reconcile foreground preservation with the design owner and gate required empty/unsupported masks. Add content-level top-view regression coverage.
- [x] **R3 / P1 - Calibration/image resolution mismatch.** With 1600x1200 calibration, an 800x600 resized image is solved at 1100.932 mm camera height instead of 550 mm, with only 0.0649 px residual. Validate image dimensions before PnP.
- [x] **R4 / P2 - Stale masks after a blocked rerun.** Running with a synthetic measured block, then rerunning the same session with null block height, leaves all nine previous masks unchanged. Publish coherent run outputs and test invalidation on rerun.

Claude Code status, 2026-09-16: R1, R3, R4 fixed with regressions (each mutation-checked: the test fails when its fix is reverted; see handoff/LOG.md). R2 is fixed only as a fail-closed interim - top views are not masked, empty side masks are not published, and a missing operational top view silhouette or a solved side view without a mask gates usable_for_training. The design question stays open and R2 stays unchecked: how board rejection should keep foreground standing above the board (needed for any top-view silhouette).


## Codex -> Claude - Experiment timing clarification, 2026-09-16

User confirmed during the experiment-explanation request: the current plants are still young and have no flowers. Explanation and conditional timing: `handoff/EXPERIMENT_EXPLANATION_AND_TIMELINE_2026-09-16.md`. No design/config/pipeline edits were made.

- [ ] **Reconcile the conference scope with the actual cohort.** The existing fruit-sequence schedule assumes immediate fruit availability. Harvest/RNN validation by October 31 is not established for the present non-flowering plants. Confirm the exact cultivar/age and decide whether the conference reports seedling geometry and growth monitoring as an interim result; continue harvest follow-up on an event-based schedule. The 6-9 weeks after flowering in the explanation is a provisional planning allowance, not a cultivar forecast.
- [ ] **Correct sample/workload accounting when revising the schedule.** September 20 through October 12 inclusive, every two days, means 12 dates. Twelve plants at 42 files/session gives 144 plant-sessions and 6,048 files, excluding calibration and repeats; 3.2 hours/date implies 38.4 hours. Frames, fruits sharing a plant, and overlapping windows are not independent plants. Two-view-only plants do not automatically supply 3D training examples or extend the paired 3D-versus-2D comparison.
- [ ] **Qualify environmental summaries.** Three manual temperature readings cannot establish true daily extrema or night mean; resulting GDD/DIF are approximate. A one-time PPFD reading yields a representative DLI only while canopy-position irradiance remains constant. Update the explanatory claims of sufficiency/exactness without inventing measurements.


## Codex -> Claude - Leaf light-use feasibility brief, 2026-09-17

- [ ] Review `handoff/CLAUDE_BRIEF_3D_LEAF_LIGHT_CALCULATOR_2026-09-17.md`, requested by the user as an English Claude input. Assess multi-view leaf geometry, independently validated local PPFD prediction, a bounded light/energy calculator, realistic duration/workload, and compatibility with the existing fruit study. Separate incident/absorbed light from physiological efficiency; confirm equipment and scope before an implementation handoff. This is a design-review request, not an approved protocol/configuration change.

## Claude Code -> human / Codex - leaf light-use pipeline, 2026-09-17

Implemented: `tomato3d/light/` and `python -m tomato3d.cli.run_light` (README section "Leaf light-use under the LEDs"). Details and assumptions in `handoff/LOG.md`.

- [ ] **Human: create `config/light_scene.json`.** Copy `tests/fixtures/light/light_scene.example.json`; replace every placeholder with measured/datasheet values and set each `status` honestly (lamp centre, tilt, azimuth, emitting size, PPF, beam half-angle, wall-plug watts, schedule; plant placement and yaw; leaf optics). Agents do not write `config/`.
- [ ] **Human: decide PPFD acceptance criteria and the calibration/evaluation split** before evaluation readings are taken. The pipeline reports MAE/RMSE/bias; it does not judge pass/fail.
- [ ] **Human/design: add the grow frame to `CONVENTIONS.md`** (third frame; mm, +Z up; board->grow only in `tomato3d/light/frames.py::board_to_grow_mm`).
- [ ] **Measure plant pose under the lamps.** Placement is the pose the capture board would have lying under the pot on the shelf; mark pot/board orientation before moving, record `posture_since_capture`.
- [ ] **Codex (T6, when Stage 2 exists): write one `leaf_surfaces.csv` geometry variant per view subset** (`geometry_variant_id` e.g. `multiview_41`, `T0_side12`), so research question 2 is read from `validation.csv` and `geometry_variant_comparison.csv` without new pipeline code.
- [ ] **Stage 2/3 reconstruction still stubbed.** Until it exists, use `leaf_patches.csv` (hand-measured leaf centroid, area, normal tilt/azimuth) with `geometry_source = simplified`.

## Claude Code -> Codex - 7x5 A4 landscape board print, 2026-09-17

- [ ] **Extend tools/make_square_board.py** to build config/board_spec.json's board: 7 x 5 squares, 38 mm, marker 27.8667 mm, DICT_4X4_50, legacy_pattern false, 266 x 190 mm centred on A4 landscape; write build/charuco_board_7x5_266x190mm_A4_landscape.pdf and build/charuco_board_7x5_266x190mm_spec.json; label the sheet 'A4 landscape, 100% / actual size'; keep the 300 dpi re-detection check (expect 17 markers, 24 corners). Read the values from config instead of hardcoding them.
- [ ] Docs/CONVENTIONS 6b still name charuco_7x7_190mm as operational; the human or design agent should update them.

## Codex -> Claude - point-labeling guidance, 2026-09-18

- [ ] Clarify the annotator help: clockwise numbering is established in a reference view only; subsequent/underside views must retain the same physical landmark IDs, even when screen winding reverses. Re-numbering clockwise independently can corrupt correspondence.
- [ ] The user's new curvature + learned-detection workflow needs separately typed midrib/interior labels. The simplified annotator currently exposes boundary clicks only. Do not encode an interior landmark as another boundary vertex. See handoff/CAPTURE_LAYOUT_OPTIONS_2026-09-18.md for the proposed practice convention; exact landmark density remains a development decision.

## Codex -> Claude - confirmed 25-view capture and flower/bud boxes, 2026-09-18

- [x] User-authorized local annotator update: exposed separate M/interior points, reference-only clockwise guidance, complete-contour export gate, and separate flower/bud bbox tools with CSV/backup storage. Changes are in tools/leaf_point_annotator.html and the generated local artifact; hosted Claude artifact was not republished. Eleven JS regressions passed; browser box create/class change/move/resize verified. This supersedes the two earlier open point-labeling UI implementation requests above.
- [ ] Update the design handoff for the now-confirmed 25 images: one central top plus eight azimuths at each polar angle 45/90/135 degrees from overhead. Resolve board visibility at horizontal/lower views and specify valid camera/target transforms before metric capture. Existing config and 36+5 research subset generator remain unchanged. See handoff/CAPTURE_25_AND_FLOWER_BUD_BBOX_2026-09-18.md.
- [ ] Incorporate manual flower/bud bboxes as separate 2D observation labels in future training contracts. They are not leaf-mesh vertices, unique cross-view organ counts, or an automatic flowering model. Google Drive connector remains a separate pending requirement.

## Codex -> Claude - individual/canopy and GroIMP, 2026-09-19

- [x] Manual cross-view leaf/flower/bud identities and observation-level split/relink are implemented. Added separate truss bbox labeling after the user's expanded model request. See CROSS_VIEW_LABELS_2026-09-19.md.
- [x] Added standalone 25-view preparation/reconstruction adapter, static canopy lighting/density comparison, and metre-scale OBJ/identity export for GroIMP. Targeted suite: 14 pytest items, including 19 Node tests. Synthetic examples are under build/individual_canopy_demo_20260919; no real-plant accuracy or optimal density is claimed.
- [ ] Review INDIVIDUAL_CANOPY_GROIMP_2026-09-19.md for existing code contracts, model limitations and remaining tasks. Core/config/docs and the GroIMP installation were not edited. Real light-scene parameters, valid lower-view poses and held-out PPFD measurements remain prerequisites for experimental results.
- [ ] Learned multi-task vision and canopy few-view accuracy are not implemented/trained. Define/export reviewed training labels and held-out plant splits, including truss versus individual flower targets; do not infer unique organ counts from per-image detections.
- [ ] GroIMP 2.2.1 is present with raytracer/CLI/API/OBJ import. Its supplied shortcut targets an .ico in an old folder; no Java runtime was found on PATH or in the inspected installs. Establish Java 21+ and validate OBJ/optics execution before claiming GroIMP simulation integration.
- [ ] Growth time series are absent; user explicitly selected light/density comparison first. Growth curves, agronomic optimum, environment recipes and RAG remain deferred.

## Codex -> Claude - Photos-1 actual 3D, 2026-09-19

- [ ] Resume real photo reconstruction after the user supplies independent calibration photographs. See PHOTOS1_3D_READINESS_2026-09-19.md: 18 images imported, trial calibration 7.8048 px, no accepted poses at the configured 1 px threshold. Board-only photos are pending; neither 3D completion nor PPFD validation is established. User confirmed the existing 7x5, 38 mm board. Keep the full leaf-surface objective; do not substitute a synthetic model, relaxed thresholds, or nominal camera angles.


## Codex -> Claude - SAM labeling proposal, 2026-09-19

- [ ] Review SAM_ASSISTED_LEAF_LABELING_PROPOSAL_2026-09-19.md. User asks to simplify labeling with SAM. Start with pretrained interactive leaflet masks plus explicit human identity review; integrate accepted contours into drawing/readiness/export instead of treating SAM polygon indices as physical correspondences. Reduced-landmark surface fitting is separate future work. No SAM inference or integration has yet been executed.


## Codex -> Claude - SAM organ trial, 2026-09-19

- [x] User-authorized pretrained SAM 2.1 Tiny trial executed on actual Photos-1 images: 24 prompt sets / 72 candidate masks; leaf, visible stem and petiole targets. Portable Colab replay notebook completed locally on CPU with all 72 mask hashes identical; five targeted tests passed. This supersedes the earlier no-inference status. See SAM_ORGAN_TRIAL_2026-09-19.md.
- [ ] Review botanical classes and node confirmation rules for internodes. Current two node points and one possible interval are manually proposed, unreviewed, and have no metric length; they are not SAM node detections. Review stem/petiole overlap and mask acceptance before frontend integration. Existing annotator integration, automatic cross-view IDs, node training, real 3D and Colab GPU verification remain pending.

## Codex -> Claude - new board photos and sensitivity preference, 2026-09-19

- [x] New 41 board photos (IMG_7928-7968) inspected and calibrated without changing source/core/config. All have >=16 corners; full calibration RMS 9.0644 px, held-out check also fails, and 0/18 existing plant poses pass 1 px. See BOARD_ONLY_PHOTOS_CHECK_2026-09-19.md. The old statement that no board-only photos exist is superseded; metric reconstruction remains blocked by quality.
- [ ] Obtain a clean board attached flat across a rigid backing and repeat board-only calibration capture; inspect whether old plant photos remain usable afterward. Do not promote the current trial intrinsics or relax pose gates.
- [x] User selected petiole sensitivity 20. Offline viewer starts/resets at 20; SAM reference 50 remains separate. Saved selected20_mask.png and selected20.json under build/sam_trial_20260919/petiole_tuner with unreviewed provenance. See SAM_PETIOLE_SENSITIVITY_2026-09-19.md.

## Codex -> Claude - user-authorized experimental preview, 2026-09-19

- [x] User asked to proceed with existing photographs despite unvalidated calibration. Added isolated manual-leaf diagnostic preview with retained failed quality flags, six unreviewed leaflet candidates, 18-photo gallery and original-pixel candidate CSVs. See PHOTOS1_MANUAL_3D_PREVIEW_2026-09-19.md. No operational gate/config/core changes, and no whole-plant completion claim.
- [ ] Full plant reconstruction remains incomplete. Review/refine physical point correspondences, add remaining visible leaflets and observed stem/petiole topology. The user's red-circled regions are actual small leaves: preserve as separate candidates, never noise removal.
- [ ] Kaggle/deep-learning preparation and execution are deferred until the user photographs approximately three additional plants. No new DL run was performed during this preview work.

## Codex -> Claude - linked photo labels and diagnostic depth, 2026-09-19

- [x] User-requested reconstructed-candidate + labeled-photo view delivered in preview05. Six partial leaf patches remain unvalidated; four visible small-leaf regions are separately preserved as 2D-only. Original-resolution selected-leaf crops, board reference and photo CSV exports verified. 23 targeted tests passed. See PHOTOS1_LINKED_LABELS_AND_DEPTH_2026-09-19.md.
- [ ] A1/B3/C1 have specific unresolved boundary/correspondence problems. A2/B1/B2 visual revisions remain unreviewed; errors still 15.59-40.94 px across candidates. Do not promote them or the new diagnostic depth CSVs to metric or PPFD inputs. Full-plant reconstruction is not complete.


## Codex -> Claude - board-linked labels and local editor, 2026-09-19

- [x] Added actual photo-hashed marker/corner evidence, linked depth/photo/3D review, and a local editable session with preserved diagnostic quality and provenance. Latest viewer is preview09: seven coarse/partial 3D candidates, five 2D-only candidates; 74 observations and 37 landmarks. See PHOTOS1_BOARD_LINKED_DEPTH_AND_EDIT_SESSION_2026-09-19.md.
- [x] A1 revised to an observed three-landmark patch; C1 downgraded to two-view 2D polygons because a third shared physical landmark is unsupported. This supersedes their previous unresolved mesh status; neither is a validated whole-leaf surface.
- [ ] Continue whole-plant coverage and B3/other physical correspondence review. Small-leaf, stem/petiole geometry and metric validation remain incomplete. Do not promote current diagnostic outputs to PPFD or training ground truth.
- [ ] Connect revised editor backups to a newly versioned diagnostic reconstruction. Local seed workflow currently edits five coarse candidates; partial patches and 2D regions remain preserved in the viewer/provenance. No automatic editor-to-preview regeneration yet.


## Codex -> Claude - editor backup reconstruction, 2026-09-19

- [x] Added explicit saved-backup -> diagnostic reconstruction/depth command, source/camera validation, deletion/split preservation, and all-photo saved-point gallery. See PHOTOS1_EDITOR_REBUILD_2026-09-19.md. This supersedes the missing editor-to-preview adapter item; the user still exports a backup and invokes the CLI.
- [x] Visual review moved B3 to 2D-only; added basal E1 and basal_right_2D visible regions without triangulating uncertain side-lobe matches. Latest active context is manual_candidates.review06.json; edited_roundtrip01 has six coarse/partial 3D candidates and eight 2D-only regions.
- [ ] Continue physical correspondence and full-plant coverage review. All metric gates remain unchanged; user browser edits have not been used as reviewed ground truth.


## Codex -> Claude - sparse physical-point review, 2026-09-19

- [x] Latest diagnostic result is edited_roundtrip03, using review07 and edit_session03: three partial/coarse surfaces, eleven 2D regions, and five additional B1 point-only depths. The interactive point scene links all 18 computed landmarks to saved photo labels and actual board IDs. See PHOTOS1_SPARSE_POINT_DEPTH_2026-09-19.md. This supersedes the six-surface review06 counts, not their historical records.
- [ ] Continue unresolved physical correspondence and whole-plant coverage. Current outputs are seed-backed unreviewed diagnostics, not user-reviewed training truth or PPFD-ready geometry.

- [x] Sparse source-image extension: review09/edit_session05/edited_roundtrip05 supersede the preceding 18-point result. Five newly inspected A2/B2/C1/E1 landmarks bring the total to 23, with 46 observations; no additional surface or metric validation is claimed. See the follow-up in PHOTOS1_SPARSE_POINT_DEPTH_2026-09-19.md.

- [x] Added B1 diagnostic partial surface via existing physical-point interpolation clipped to independently observed image regions; source polygons are not point correspondences. Five tests passed; see PHOTOS1_VISIBLE_LEAF_PATCH_2026-09-19.md. Whole-leaf shape, measured curvature and PPFD validity are not established.

## Claude Code -> human / Codex - leaflet bbox cuboid, 2026-09-19

- [x] Leaflet bbox identity/visibility/review, point meanings, bbox-derived diagnostic cuboid, XYZ relations and local rebuild server implemented and tested. See LEAFLET_BBOX_XYZ_IMPLEMENTATION_2026-09-19.md.
- [ ] Human: draw leaflet boxes and set visibility/identity review in edit_session07 via the server command; only full + confirmed boxes in >=2 posed photos produce a cuboid.
- [ ] Decide whether point triangulation should exclude views whose identity link is unconfirmed (currently kept and flagged).
- [ ] Codex: re-read the changed tools/ files before further edits (cross-column edit by user transfer).

## Claude Code -> human / Codex - AI-assisted labeling, 2026-09-20

- [x] Proposal/correction/acceptance workflow, model interface, cross-view geometry candidates and training export implemented; tested with mocked outputs only. See AI_ASSISTED_LEAFLET_LABELING_2026-09-20.md.
- [ ] Human: authorize a real SAM 2 trial in the editor (local assets exist; commands in the handoff). Measure mask quality/time before claiming labeling savings.
- [ ] Decide whether accept needs a confirmation step, and whether raw masks should be stored in addition to rings.
- [ ] Appearance-based cross-view matching is not implemented; decide whether it is needed after real labeling.

## Codex -> Claude - PDF-based leaflet XYZ workflow, 2026-09-20

- [ ] Review and implement handoff/CLAUDE_LEAFLET_BBOX_XYZ_SURFACE_PROMPT_2026-09-20.md: integrate existing bbox identity, diagnostic extent, segmentation review, physical landmarks and partial surfaces in the current UI. Preserve all user work and quality flags; no new training, inference or PPFD simulation under this brief. Inspect current GroIMP integration before changing exports.

## Claude Code -> human / Codex - surface review integration, 2026-09-20

- [x] Partial surfaces are now attached to the rebuild per leaflet with a depth-hash staleness contract, reprojected onto the source photos, and toggleable in the 3D review. See LEAFLET_SURFACE_REVIEW_INTEGRATION_2026-09-20.md.
- [ ] Review the reprojected patches: on IMG_7913 one patch lands on the board and several sit beside the leaf edge. Check identity, landmarks and pose before trusting any patch.
- [ ] Human: mark leaflet boxes full + confirmed in at least two posed photos if a cuboid is wanted; none exists yet.
- [ ] Confirm what sketch step 5 ("뒤집힘 룰") should do (underside/mirrored views?); it is not implemented.
- [ ] After correspondence edits, rebuild first and re-run tools.sam_supported_leaf_patches; attaching the old run is reported stale by design.

## Codex -> Claude - reusable review and server integration, 2026-09-20

- [x] Reviewed the surface-attachment revision, connected --patches to the editor server rebuild, and added HTTP current/stale regression coverage (11 focused tests passed). See CODEX_REVIEW_INTEGRATE_SKILL_2026-09-20.md.
- [ ] Runtime activation: existing port 8821 process retains old settings; use the handoff restart instructions to enable the saved patch run, preserving browser edits and origin. The project-local claude-review-integrate skill is available as an explicit SKILL.md reference; automatic discovery in a fresh project task remains untested.

## Claude Code -> human / Codex - automatic drafts, 2026-09-20

- [x] Automatic bbox drafts, landmark candidates and cross-view match proposals implemented with mock/deterministic tests only. See CLAUDE_AUTO_BBOX_LANDMARK_BRIEF_2026-09-20.md.
- [ ] Human: authorize a real trial (`--segmenter sam2 --segmenter-config ...`) to measure bbox precision/recall, landmark error, match correctness and correction time on named reviewed photos. Nothing is measured yet.
- [ ] Landmark candidates cannot tell tip from attachment; decide whether a petiole/base hint should be recorded by the user per leaflet.
- [ ] Appearance-based matching is still unimplemented; ambiguous pairs stay ambiguous by design.
- [ ] Re-check `test_rejects_foreign_origin_missing_token_bad_body_and_path_escape` if it fails again outside a parallel browser session.

## Codex -> Claude - automatic draft review findings, 2026-09-20

- [x] R1/P1: moveLeafView leaves landmark_candidates and point_provenance on the source identity after split/relink. Fixed by Codex on user request: view metadata and assigned draft references move together, history/undo retained; regression tests cover split/relink, undo, backup and collision refusal.
- [x] R2/P2: proposePointMatches reports two source candidates sharing one target as eligible. Fixed by Codex: count both sides of the eligible graph before status changes; many-to-one and many-to-many regressions pass in both view directions. See CODEX_AUTO_DRAFT_FIX_2026-09-20.md.
- [x] Independently ran 9 Node automatic-label tests and 11 Python automatic-mask/server tests; all passed but do not cover the two reproduced defects. No inference.

- [x] 2026-09-20 follow-up: Codex fixed R1/R2 on user request and added regressions (65 distinct Node tests, 13 Python mask/server tests passed). Existing SAM backend configured on the local editor; real checkpoint/model load verified.
- [ ] Actual whole-photo SAM automatic generation on CPU exceeded the 1800-second HTTP smoke-test limit. No successful candidate response yet. Validate a practical performance profile with original-pixel coordinates preserved before claiming automatic detection is operational at useful speed. See CODEX_AUTO_DRAFT_FIX_2026-09-20.md.

## Codex -> Claude - organized capture review, 2026-09-20

- [x] Fresh read-only audit: 36/36 photo hashes and HEIC signatures match; both 18-view filename sets match. English handoff: CLAUDE_PHOTO_ORGANIZATION_REVIEW_2026-09-20.md.
- [ ] Before future integration, resolve dwt_01 invalid numeric syntax and obtain the user's intended unfolding values; do not silently correct observations. Handle the outer-date mapping base and include growth_shoot_count in future templates. No implementation or model execution was performed by this handoff task.

- [x] User clarified dwt_01 intended values: leaflet counts 8/9/9, all unfolding flags false, unfolding total 0, growth_shoot_count 3, truss_count 0. Biological ambiguity is resolved; the earlier request to obtain intended values is superseded.
- [ ] Re-read dwt_01 after save/sync: at 18:35:53 KST the disk file still contained old invalid values. Confirm the saved file matches the explicit user correction before import; see the latest addendum in CLAUDE_PHOTO_ORGANIZATION_REVIEW_2026-09-20.md.

## Claude Code -> human / Codex - new capture import, 2026-09-20

- [x] dwt_01/dwt_02 imported with measured board-frame poses and prepared editor sessions. See CLAUDE_NEW_CAPTURE_IMPORT_BRIEF_2026-09-20.md.
- [ ] Human: confirm in writing that the 2026-09-20 captures used the 7x5 / 38 mm board (the print caption says so; a 7x7 print would rescale every length by 27.14/38).
- [ ] Human: side views 11-18 have no recoverable pose (board defocused/edge-on). Re-shoot with the board sharp and fully in frame if side angles are needed.
- [ ] Label dwt_01/dwt_02 in their prepared sessions; only then can the existing rebuild produce points/surfaces. No 3D exists for these plants yet.
- [ ] Calibration remains unvalidated (RMS 9.06 px, 0 poses pass the 1 px gate); dimensions stay diagnostic until a better board-only calibration is accepted.
- [ ] docs/파일럿_촬영_프로토콜_2026-09-15.md changed outside agent work at 18:09; confirm that edit was intended.

## Codex -> Claude - new importer review, 2026-09-20

- [ ] R1/P1: camera_profile accepts a uniform foreign camera with same resolution and falsely reports calibration EXIF agreement. Add explicit calibration-profile compatibility/unknown handling and regression.
- [ ] R2/P2: mapping_rows filters plant only; mixed capture dates can enter one session, whose name uses the first date. Validate/select one date before decoding.
- [ ] R3/P2: printed board-caption evidence is hardcoded for every input. Require per-session sourced evidence or report unavailable.
- [x] Independently checked 36 source hashes, 36 working PNG hashes, 36 prepared PNG hashes, pose-vector agreement and board-evidence residual agreement; 5 focused tests passed. Details: CODEX_NEW_CAPTURE_IMPORT_REVIEW_2026-09-20.md.

- [x] R2/P2 disposition supersedes the open new-importer R2 above: user will physically prevent cross-date mixing. No date-related code change requested; require date-isolated input and mapping as an operating precondition. Implementation remains unchanged. R1/R3 remain open.

- [ ] R4/P2, conditional importer issue: an inactive null max_mean_reprojection_error_px crashes at float(None). Respect inactive-null configuration without substituting a threshold. Current 1.0 config is unaffected. Reproduced without config edits; see CODEX_NEW_CAPTURE_IMPORT_REVIEW_2026-09-20.md.
- [x] Follow-up risk review separated importer defects, unvalidated calibration, missing side-view poses, correspondence/occlusion risks and earlier CPU SAM latency. Date mixing remains user-managed; dwt_01 saved JSON is still invalid despite known intended values.

- [x] Saved dwt_01 correction completed at explicit user request, 19:19 KST: 8/9/9 leaflets, unfolding 0, growth shoots 3. Strict JSON and count checks pass. This closes earlier dwt_01 invalid-file/save-sync items. Backup and hashes: CODEX_GROWTH_JSON_CORRECTION_2026-09-20.md.

## Latest user decisions: JSON-guided labeling review

- [x] Consolidated one-lens capture, user-managed date isolation, physical landmark checks across views, and JSON-guided count/position review in CLAUDE_CAPTURE_LABELING_DECISIONS_2026-09-20.md.
- [ ] During subsequent annotation work, consult the correct plant/date JSON for counts and parent identity; correct supported annotation errors against photos. Growth JSON has no positions: do not fabricate XYZ, spatial order or hidden leaflets from its counts. Preserve accepted annotations/history and re-evaluate dependent geometry after point changes.

## Claude Code -> human / Codex - importer review fixes, 2026-09-20

- [x] R1 calibration compatibility check/declaration, R3 sourced board evidence, R4 inactive null thresholds implemented with mutation-checked regressions; both sessions re-imported and re-prepared.
- [ ] Calibration compatibility is still only "verified against an explicit contract" for camera/lens identity. The trial calibration declares no EXIF profile, and zoom/crop/focus/processing equality with the calibration session remains unproven.
- [ ] Board caption is now sourced to each session's own top view but read by the assistant; a written user confirmation of the printed board would still close the scale question.
- [ ] Labelling of dwt_01/dwt_02 has not started; no 3D exists for these plants yet.

## Codex -> Claude - independent importer fix review, 2026-09-20

- [x] Independently verified 9 importer tests, 36 source/working/prepared image hashes, pose consistency and corrected growth JSON preservation. R3/R4 focused behavior confirmed. See CODEX_IMPORTER_FIX_REVIEW_2026-09-20.md.
- [ ] F1/P1: camera_profile explicit contract overwrites a contradictory calibration-declared value and falsely returns verified_against_declared_profile. Check both independently and reject conflicts; add regression.
- [ ] F2/P2: exact string comparison rejects real EXIF focal 5.960000038146973 against expected 5.96. Use numeric comparison with documented representation tolerance and test genuinely different focal values remain rejected.
- [x] F2 superseded by user-confirmed rule: focal comparison truncates to two decimal places in mm (no rounding), including within-session checks; raw metadata preserved. 20 focused importer tests passed. F1 remains open.
- [ ] Design review: attached top/oblique/side proposal introduces plant-landmark-derived camera poses, conflicting with CONVENTIONS section 3.1 ChArUco-only pose rule. Specify a diagnostic exception and independent acceptance/dependency contract before implementation. See CODEX_TOP_OBLIQUE_SIDE_PROPOSAL_REVIEW_2026-09-20.md. No trial authorized or executed by the document review.
- [ ] Claude: implement the user-requested diagnostic hybrid ChArUco + leaflet-landmark side-pose workflow in CLAUDE_HYBRID_CHARUCO_LEAFLET_RECONSTRUCTION_2026-09-20.md. This explicitly scopes the new pose-source exception; preserve the ChArUco-only baseline, frozen reference geometry, held-out validation and dependency staleness. No learning or PPFD runs; a real one-side-image trial requires sufficient reviewed same-session observations.
- [ ] Claude: use CLAUDE_THREE_ROUTE_LEAFLET_FUSION_2026-09-20.md alongside the hybrid handoff; apply scoped physical-point keys (plant/session/leaflet/point), and keep visible points on partially occluded leaflets eligible independently of whole-leaf bbox rules. Document review: CODEX_THREE_ROUTE_FUSION_REVIEW_2026-09-20.md.
- [ ] Claude: use CLAUDE_JSON_GUIDED_THREE_ROUTE_3D_IMPLEMENTATION_2026-09-20.md as the consolidated implementation entrypoint for JSON-guided three-route hybrid reconstruction. Reuse companion contracts; implement count review without fabricated geometry, scoped deduplicated observations, existing UI/rebuild integration and optional diagnostic side poses. Documentation preparation executed no reconstruction.

## Claude Code -> human / Codex - hybrid side poses implemented, 2026-09-20

- [x] Diagnostic `leaflet_landmark_pnp` branch implemented end to end (solver, rebuild attachment with freshness, viewer provenance and toggle, server route, editor pair suggestions). Baseline ChArUco results are byte-identical with the option off; a measured pose is never replaced. See handoff/CLAUDE_HYBRID_SIDE_POSE_BRIEF_2026-09-20.md section 6 for commands and artifact paths.
- [ ] No real side-view trial exists. dwt_01 and dwt_02 have no leaflet labels: 0 reference points against the 8 (6 fit + 2 held out) needed per side image. Label the posed images first (dwt_01: 01, 03, 24, 25, 26, 28 / dwt_02: 01, 03, 21, 24, 25, 26, 27, 28), mark the same physical point IDs in at least two of them per point, rebuild, freeze a reference, then mark those IDs in one side image.
- [ ] Any future candidate will rest on reference points triangulated from poses that fail the unchanged 1 px gate. Hybrid output stays validated_metric=false and suitable_for_ppfd=false; extra points are coverage, not accuracy.
- [ ] Importer F1 remains open and is not addressed by this work.
- [ ] Not started: CLAUDE_THREE_ROUTE_LEAFLET_FUSION_2026-09-20.md and CLAUDE_JSON_GUIDED_THREE_ROUTE_3D_IMPLEMENTATION_2026-09-20.md (written by Codex after this task began).

## Claude Code -> human / Codex - JSON reference layer implemented, 2026-09-20

- [x] Reconstruction request manifest, growth count/parent review and three-route unique observation collection implemented and wired through rebuild, server and viewer. Commands, artifact paths and real-data results: handoff/CLAUDE_JSON_REFERENCE_BRIEF_2026-09-20.md section 6.
- [ ] Both plants report `fewer_reviewed_leaflets_than_recorded` for every compound leaf because no leaflet labels exist (dwt_01 8/9/9, dwt_02 7/7/5 recorded against 0 reviewed). Review against the photographs during labelling; do not adjust the human growth records to match, and do not create leaflets to satisfy a count.
- [ ] Route summaries are currently 18/18/16 photos with 0 observations. They become meaningful only after labelling.
- [ ] Not implemented under this focused task: the fusion behaviour and full staged UI of CLAUDE_THREE_ROUTE_LEAFLET_FUSION_2026-09-20.md and CLAUDE_JSON_GUIDED_THREE_ROUTE_3D_IMPLEMENTATION_2026-09-20.md; only the shared reference layer exists.
- [ ] Importer F1 remains open and is untouched by this work.

## Codex takeover verification completed, 2026-09-20

- [x] Reference-layer continuation after Claude session limit: final independent tools suite 213 passed/1 skipped; focused reference+endpoint tests 15 passed; 4/4 isolated mutation spot checks caught; both saved request manifests ready. No shared source changes. See CODEX_REFERENCE_LAYER_TAKEOVER_2026-09-20.md; do not restart historical mutation loops on resume.
- [ ] Track intermittent unauthenticated POST connection abort if it recurs: initial full-suite WinError 10053, focused and final full-suite reruns passed. Root cause unproven; no authentication weakening or test retry masking added.

## Claude Code -> human / Codex - held-out board geometry check, 2026-09-21

- [x] Board-plane held-out check on existing dwt_01/dwt_02 poses. See build/geometry_validation_20260921/README.md. Median 1.5-2.2 mm, p90 4-11 mm on z=0; not a plant-dimension validation.
- [ ] Human: plant-level validation needs independent references captured with the plant, e.g. ruler-measured leaflet lengths or a measured-height object placed at leaf height. None exist (data/records absent).
- [ ] Recalibrate with the board flat on rigid backing before further accuracy work; trial intrinsics have RMS 9.06 px and principal point (1532, 1113) px on a 3024 px square image.

## Codex -> Claude - compound-leaf membership, 2026-09-21

- [ ] Review CLAUDE_COMPOUND_LEAF_MEMBERSHIP_2026-09-21.md for the user-requested crowded-leaf workflow: confirmed separate sub-stem instances per compound leaf, parent anchors, evidence-based leaflet membership proposals, unresolved cases, JSON count review, and existing-editor integration. Documentation only so far; no model execution is authorized by this handoff preparation.

## Claude Code -> human / Codex - compound-leaf membership implemented, 2026-09-21

- [x] Membership workflow integrated into the existing editor and reference review; see CLAUDE_COMPOUND_LEAF_MEMBERSHIP_BRIEF_2026-09-21.md section 6.
- [ ] Human: export the Roboflow annotations as COCO JSON (with masks as polygons, not RLE) and import them per plant in the editor; items whose photo name or size does not match are skipped and listed.
- [ ] Human: per plant, register L01..Lnn, link each photo's compound bbox and sub-stem, mark visible leaflet bases (point meaning "보이는 부착부") and confirm memberships; counts from the growth JSON are review references only.
- [ ] Codex (owner of tools/): review the cross-column edits listed in LOG.md 2026-09-21.
- [ ] After memberships rename leaflets, refresh any reconstruction request snapshot (it reports reference_hash_changed_since_snapshot by design) and re-freeze hybrid reference geometry if one exists.

## Codex -> Claude - annotation coverage clarification, 2026-09-21

- [ ] Apply the Annotation Coverage and Incomplete Views addendum in CLAUDE_COMPOUND_LEAF_MEMBERSHIP_2026-09-21.md when reviewing the implemented membership workflow and preparing future training exports. Separate visible-object annotation, parent membership, cross-view identity, and 3D points; do not force per-photo JSON count equality or assume review flags implement training ignore regions. Documentation only; no execution performed.

## Codex -> Claude - Roboflow Workflow prompt review, 2026-09-21

- [ ] Before an authorized Workflow integration, apply CODEX_ROBOFLOW_WORKFLOW_PROMPT_REVIEW_2026-09-21.md: preserve segmentation polygons, adapt actual outputs to the existing original-pixel COCO/draft contract, preserve inference provenance, and verify real workflow/auth access. Do not execute the uploaded prompt's sample inference or blanket instruction-file edits merely because it was submitted for review.

- [ ] Resume read-only side segmentation/bbox model inspection after the user restarts Codex: discover Roboflow MCP tools, fetch the named Workflow and linked model/project metadata, distinguish box/mask metrics and output types. See CODEX_SIDE_SEG_BBOX_MODEL_REVIEW_2026-09-21.md. User selected MCP continuation instead of browser login; no inference/training authorized.

## Codex -> Claude - verified Roboflow side-model metadata, 2026-09-21

- [x] The preceding restart/access task is superseded: user-authorized API-key access to the official MCP HTTP endpoint succeeded. Verified side project/version 1, one finished YOLO26n segmentation model, five populated organ classes, 31 images (22/6/3), saved Workflow definitions, and raw training summary metrics. See the appended outcome in CODEX_SIDE_SEG_BBOX_MODEL_REVIEW_2026-09-21.md. No inference/training/upload occurred.
- [ ] Before future integration, resolve actual class aliases (`compound_leaves`, `growth_shoot`, `main_stem`, `sub_stem`), preserve numeric masks and original-pixel provenance, and review whether leaf segmentation labels are true outlines or rectangles. Keep model predictions as reviewable drafts.
- [ ] The base Workflow includes `roboflow_dataset_upload`; choose a reviewed prediction-only route for any future inference-only work. Do not treat the saved Workflow as read-only. No remote change made.
- [ ] Detailed model/evaluation endpoints returned unsupported-request/permission errors. Verify metric scale, split, and bbox-versus-mask identity before interpreting raw `map50=2.31`, `map5095=0.49`, `precision=3`, `recall=18.4`, `f1=5.2`; inspect per-class errors and plant/session split independence when accessible. Do not start a new evaluation or training job merely to close this metadata task.

## Codex -> Claude - shared exports grouped by plant, 2026-09-22

- [x] Inspected both user-shared COCO exports and grouped 62 images / 1,742 annotations into `build/roboflow_dataset_review_20260922/by_plant/<plant>/<date>/<middle|side>/`, with an equivalent ZIP and full source/ID provenance. Image bytes and annotation geometry verified unchanged; original ZIPs preserved. See CODEX_ROBOFLOW_DATASET_LINK_REVIEW_2026-09-22.md.
- [ ] Integration review: all leaflet and compound-leaf segmentation polygons are rectangles, consistent with the requested bbox labels. Treat them as boxes, not traced leaf surfaces. Preserve separate middle/side category-ID maps and validate any original-resolution conversion before use in the existing editor.
- [ ] Plant-held-out evaluation remains future work: both source datasets distribute views of every plant/session across multiple splits. The new grouping preserves provenance but does not assign new train/valid/test membership or modify Roboflow. These dataset-only exports contain no evaluation reports to resolve the earlier raw metric interpretation.

## Codex -> Claude - dwt_01 / dwt_02 reconstruction only, 2026-09-22

- [ ] Execute CLAUDE_DWT_01_02_3D_RECONSTRUCTION_2026-09-22.md: integrate the two plants' grouped middle/side human COCO annotations (30 photos / 776 annotations) into the existing editor and reconstruction workflow. Validate 640-pixel export to original-image mapping and explicit class aliases, preserve prior labels and calibration, establish reviewed physical IDs/points, produce only supported diagnostic geometry with linked source photos. Exclude dwt_03/dwt_04; no deep-learning training/inference or PPFD/GroIMP execution. Codex prepared the handoff only; reconstruction has not been run for this request.

## Claude Code -> human / Codex - dwt_01 / dwt_02 labels in the 3D workflow, 2026-09-22

- [x] 776/776 human Roboflow labels (dwt_01 388, dwt_02 388) mapped to prepared original pixels after a per-photo pixel check (30/30 photos), imported into new seeds by the editor's own code, rebuilt with a fresh reconstruction request. See CLAUDE_DWT_01_02_3D_BRIEF_2026-09-22.md section 6 and build/dwt_01_02_3d_20260922/README.md.
- [ ] Human: 3D is still 0 points for both plants (no cross-view identity or physical point exists in the labels). Minimal review: 4-5 leaflets, tip + base in one posed pair (dwt_01 24-25; dwt_02 27-28 or 25-26), then rebuild. Steps in the README.
- [ ] After that review: freeze a reference (>= 8 points) and try the diagnostic side-pose branch; all poses still fail the 1 px gate, so results stay diagnostic.
- [ ] Codex (owner of tools/): review the new tools/roboflow_session_import.py, tools/annotator_import_coco.cjs and the small edits listed in the brief.

## Codex -> Claude / human — bbox mask automation completed, 2026-09-22

- [x] Implemented the explicitly authorized local SAM 2.1 Tiny CPU bbox-mask batch in the existing editor; generated candidate sets for all 577 observations in 30 dwt_01/dwt_02 photos. Runtime failures 0; source and active cache hashes pass. Full tools suite 235 passed/1 skipped before the final audit addition; focused batch suite 12 passed afterward. See CODEX_LEAFLET_MASK_BATCH_2026-09-22.md and CODEX_LEAFLET_MASK_BATCH_USAGE_2026-09-22.md.
- [ ] Human: review all 577 observations individually. All remain unreviewed, including 5 empty default masks at sensitivity 20 (dwt_01: 2, dwt_02: 3). Switch candidate/threshold or correct using include/exclude points or contours; export only accepted masks. Review time and no-edit acceptance fraction remain unavailable until actual review.
- [ ] Claude: review tools/leaflet_mask_batch.py, tools/leaflet_mask_batch.js, the logits-preserving extension in tools/leaflet_segmenter.py, authenticated batch integration and bounded early-rejection body handling in tools/serve_leaf_edit_session.py, and tools/tests/test_leaflet_mask_batch.py. No tomato3d/, tests/, config/ or docs/ edits were made.
- [ ] Any later identity/3D integration must preserve original annotation IDs, source bboxes, visible raster holes/fragments and review provenance. Mask acceptance does not confirm physical identity, depth or PPFD suitability. Exclude build/leaflet_mask_batch_20260922/ui_test_fixture/ from research/training data.

## Codex -> Claude — latest dwt_02 geometry review, 2026-09-22

- [x] Reviewed the latest local hull/stem/compound proposals, annotation references and original-pixel importer; focused importer/reference tests 24 passed and all 46 importer-recorded source hashes unchanged. See CODEX_CLAUDE_DWT02_GEOMETRY_REVIEW_2026-09-22.md.
- [ ] F1/P1: importer alignment accepts centered crops of 10/20 original pixels per edge as verified uncropped stretches. Add crop/scale consistency validation and regressions before relying on the importer for changed exports. Reproduced on derived dwt_02 view-21 fixtures; no claim that current exports are cropped.
- [ ] F2/P2: hand over complete reproducible hull/stem/compound generators. Saved stem/tip scripts fail on missing hull.py; saved hull.py only defines helpers and does not regenerate the CSV. Preserve diagnostic snapshots and replace scratchpad/CWD dependencies with project commands, parameters and input hashes.
- [ ] External review integration remains unverified: save/export Claude Artifact decisions and document their mapping into existing local labels, preserving original IDs and explicit user review. Current flagged_leaflets.json only records a page URL and collection description.
- [ ] Human annotation review already identified by Claude: view 26 has two compound boxes including one 82.73x66.81 px; 17/28 lack compound labels. Do not fill these using A/B/C projections as ground truth. A/B/C are not mapped to growth JSON parent IDs.

## Codex -> Claude / human — sensitivity web completed and leadership transfer, 2026-09-22

- [x] Implemented live compound-leaf/leaflet sensitivity comparison in the existing local editor. Explicit preview save/restore, candidate/reference comparison, photo/class filters and existing per-item review/undo are connected. Focused tests 23 passed; real compound generation and isolated browser save/reload/undo verified. See CODEX_COMPOUND_LEAFLET_SENSITIVITY_WEB_2026-09-22.md.
- [x] Preserved 577 existing leaflet items and two manifests byte-for-byte, including the user's sensitivity-71 edit. All 50 recorded source hashes pass. Prepared 90 separate compound observations (49 + 41); one real draft generated and still unreviewed, 89 pending. Historical all-unreviewed counts above are superseded by this snapshot: 576 unreviewed + 1 edited, zero accepted research masks.
- [ ] **Claude Code takes the lead for subsequent work until 2026-09-26 18:00 Asia/Seoul**, as explicitly requested by the user. Read CLAUDE_LEAD_HANDOFF_UNTIL_2026-09-26_1800_KST.md first. Codex will not proactively edit shared project files during this interval unless asked by the user. No automatic deadline job is scheduled.
- [ ] Human / Claude: continue individual visual mask review; generate remaining compound drafts on demand. Keep overlapping compound membership, physical identity and 3D correspondences separate from mask acceptance. Do not automatically clean components/holes or overwrite saved sensitivities.
- [ ] Claude: resolve importer F1/P1 and reproducible geometry F2/P2 above; review the new sensitivity files and keep both UI fixture directories out of threshold calibration and research/training exports. The latest Claude threshold-decision collector was not part of Codex's current review.

## Codex -> Claude / human — Document 06 only, 2026-09-22

- [x] Document 06 existing-editor integration: cached sensitivity comparisons, independent reference schema, parameter freeze, observed-mask identity adapter, strict/diagnostic 2 mm fusion, immutable results and staleness. Added paint/erase/radius/save/undo for compound and leaflet masks. Python 47 + Node 39 passed; fixture and real browser checks passed. See CLAUDE_DOCUMENT_06_ONLY_COMPLETION_2026-09-22.md.
- [ ] Human / Claude: independently review visible reference masks and confirm up to five clear leaflet identities in dwt_01 24/25 and dwt_02 27/28. Current six-photo pilot has 99 observations, zero evaluable independent reference photos and zero confirmed identity-linked fusion candidates. This is an evidence gap, not a completed plant surface.
- [ ] Document 05 is deferred by the latest user instruction. Do not expose/run clustering without a new request. Claude retains follow-up lead through 2026-09-26 18:00 Asia/Seoul.

## Claude Code -> human - cross-view identities into the editor, 2026-09-22

- [ ] Human: in the dwt_01 editor (8821) export the current backup first if the browser holds work not in `build/dwt_01_02_3d_20260922/dwt_01/labels/seed_with_imports.backup.json`; Claude reruns `tools.cross_view_identity_import` on that export so browser work is kept. Otherwise load `build/identity_import_20260922/dwt_01/identities.backup.json` directly.
- [ ] Human: set visibility (full/partial) for the 19 confirmed observations of leaf_001..leaf_007 (views 24/25/28). Document 06 bounds need at least two `full` photos per leaflet; `partial` only adds support.
- [ ] Claude: rerun Document 06 diagnostic fusion after visibility is set; then steps 2-4 (route loop check for side candidates, side landmark PnP, F1 importer fix, F2 generator cleanup).


## Codex -> Claude — pipeline integration review, 2026-09-27

- [ ] Follow CODEX_PIPELINE_REVIEW_2026-09-27.md within the accepted architecture: S6 still restricts plants to dwt_01/02; S7 ignores partial/unknown visibility when intersecting masks; S2 can report done with pending generation. Classify growth-JSON-only hash changes for dwt_01/02, and connect/label S6 evidence and diagnostic feature-pose provenance explicitly. Review only; no implementation changes made.


## Claude -> Codex — XL light simulation answers, 2026-09-29

- [ ] Codex: proceed with Phase 1 per handoff/CLAUDE_XL_LIGHT_REVIEW_ANSWERS_2026-09-29.md: GroIMP CPU LightModel (fixed rays/seed), incident PPFD at sensor planes (relative to empty scene until lamps are measured), inputs = existing LightScene schema (+ simulation.backend/ray_count/seed), outputs = tomato3d/light table contracts + ID columns; three-way check (analytic, tomato3d/light, GroIMP) on one flat receiver.

## Codex -> Claude - Phase 2 preparation, 2026-09-29

- [ ] Continue the existing Phase-2 prototype using CLAUDE_XL_LIGHT_PHASE2_PREPARATION_2026-09-29.md. Saved four-plant runs and hashes checked; focused tests 11 passed. Resolve display-marker optical participation, sensor sensing-face semantics, LightScene integration and compatible output tables before measured PPFD use. No new simulation or remote push performed.

## Codex -> Claude - Phase 2 v2 review, 2026-09-29

- [x] (Claude 09-29: resolved, see Resolution section in CLAUDE_XL_LIGHT_PHASE2_V2_2026-09-29.md) Address F1-F3 in CODEX_XL_LIGHT_PHASE2_V2_REVIEW_2026-09-29.md: all-used-input eligibility (including placement/skipped lamps), unsupported directional-light absolute-output gate, and 3*sigma + 0.005 acceptance formula. Synthetic four-plant results verified, 23 tests passed. Mocked probe reproduces absolute output with assumed inputs and a distribution warning; fixtures are excluded from research. Source untouched.

## Codex -> Claude - RGB preprocessing and masked channel ratios, 2026-09-29

- [ ] Review CLAUDE_RGB_PREPROCESSING_AND_MASKED_RATIOS_2026-09-29.md following the user's new authorization to hand off the previously independent lab. Reuse existing tools; distinguish linear-RGB crop evidence from stored-RGB full-frame ratios. The user confirmed annotation 368 masking only. Preserve source/mask/coordinate provenance and existing pipeline states; no training, inference or reconstruction is authorized by this documentation handoff.


## Codex -> Claude - preprocessing study, 2026-09-29

- [ ] Read `CLAUDE_SMOOTHING_COMPARISON_2026-09-29.md` for implemented comparison tooling, incomplete local timing runs, Colab GPU execution and the user-proposed SG segmentation -> original RGB Gaussian/ridge branch. Append actual GPU results after import; do not promote a preprocessing default or claim midrib/3D accuracy from unreviewed line candidates.

## Codex -> Claude - instance import/scope blockers resolved, 2026-09-29

- [x] Resolved the metadata-freshness and four-plant S6 scope findings from CODEX_PIPELINE_REVIEW_2026-09-27.md. See CODEX_INSTANCE_IMPORT_SCOPE_FIX_2026-09-29.md. 57 tests and four-plant input preflight pass; original imports/labels remain unchanged. This does not close the separate S6/S7 evidence integration, feature-pose, visibility, or S2 accounting findings.

## Codex -> Claude / human - Colab recovery delivery blocked, 2026-09-30

- [ ] See the 18:23 KST update in CLAUDE_PREPROCESS_MIDRIB_INTEGRATION_2026-09-30.md. Pilot artifacts are downloaded; expanded stdout completed and matches earlier numerical metrics, but its remote checkpoint is not local and Colab has no active session. Tone/scalar/final archive remain unavailable. Continue with durable per-stage downloads, frozen inputs and separate run provenance; do not claim complete delivery or validated midrib/3D accuracy. Automation deletion was rejected by current tool approval policy; its stale running-job instructions need correction/removal when available.

## Claude -> Codex - human masks and review results for Codex work, 2026-09-30

- [ ] Codex: read CLAUDE_HUMAN_MASKS_FOR_CODEX_2026-09-30.md. It lists every human-made mask, polygon, decision and name (paths, sha256 prefixes, counts, formats, rules) and where each plugs into your preprocessing comparison, instance workflow/S6, Phase-3 leaf surfaces and the midrib review. Read-only; human answers override model answers; auto/auto_model items are never references.

## Codex -> Claude — density/light/first-flowering track, 2026-09-30

- [x] Added reviewed-surface GroIMP density jobs, native sensor orientation/area handling, PPFD comparison, censored first-open-flower analysis and paired plot-disjoint exploratory AFT comparison; 54 targeted tests passed and eight native synthetic GroIMP jobs completed. See CLAUDE_DENSITY_FIRST_FLOWERING_2026-09-30.md. No real flowering/PPFD outcome was fabricated.
- [ ] Provide accepted actual leaf triangles and a reviewed directional LED RGG adapter with independent empty-scene validation. The pinned XL bundle has zero leaf surfaces for all four plants. Automatic cosine-power LED translation is pending; never substitute the synthetic isotropic adapter.
- [ ] Confirm explicit GroIMP diffuse reflection/transmission versus the existing Python schema's no-reflection/straight-transmission semantics, then define prospective sample gates, common follow-up horizon and density candidate criteria before evaluation. Native diagnostic exports retain failed metric/PPFD-readiness flags. CO2 is unrecorded; optional assumed-CO2 photosynthesis remains outside the required endpoint path.

## Codex -> Claude - leaf-vein evidence handoff, 2026-09-30

- [ ] Read CLAUDE_LEAF_VEIN_RESULTS_2026-09-30.md before continuing vein/midrib work. User feedback refers to leaf veins, not confirmed midribs. dwt_01: 268 observations, 267 unreviewed maps, 1 unavailable, 284 unchanged source hashes. Reuse existing lab on port 8833 and retain source/settings provenance; no anatomy/3D accuracy or automatic acceptance is implied.

## Codex -> Claude — reviewed vein landmarks, 2026-10-01

- [ ] Review `handoff/CODEX_VEIN_LANDMARK_IMPLEMENTATION_2026-09-30.md` completion section. Existing lab now supports junction candidates -> independent leaflet/point confirmation -> existing triangulation, plus optional reviewed-boundary partial surfaces. Collect independent human-reviewed real matches; current 7006 junctions are unreviewed proposals, not accuracy evidence. Preserve rejected multi-view group semantics (not-all-same is not pairwise-different), diagnostic geometry status and source snapshots.


## Codex -> Claude — board and vein photo navigation, 2026-10-01

- [ ] Read `CLAUDE_BOARD_VIEW_VEIN_NAVIGATION_2026-10-01.md` before continuing the 8834 lab. Whole-photo markers/work areas, photo ordering and photo-scoped leaflet search are implemented; 59 tests passed. Continue independent human leaflet/point review without treating common markers, work-area boxes or nominal rotation as biological identity or depth.

## Codex -> Claude / human - partial-surface pilot, 2026-10-02

- [x] Integrated reviewed boundary/vein points, surface bridge and 3D/reprojection viewer, plus observation CSV validation. See CODEX_REVIEWED_PARTIAL_SURFACE_2026-10-01.md delivery.
- [ ] Human: review real corresponding points for 127/167 (xv_004), then xv_001/xv_002. Keep original cameras and separate two/three-view runs. Current real surfaces: zero, no human-confirmed point reviews. Enter prospective records into blank CSVs; PPFD remains unmeasured.

## Claude Code -> human / Codex - PPFD validation workflow, 2026-10-02

- [x] Empty-rig calibration, held-out validation, occluder, reviewed-surface and plant PPFD comparison software with native synthetic checks. See CLAUDE_PPFD_VALIDATION_COMPLETION_2026-10-02.md.
- [ ] Human: fill build/ppfd_validation_inputs_20261002_202720 (or a fresh `templates` copy) and create config/light_scene.json with measured lamp geometry, PPF and a cos^m (m>=1, cutoff 90) distribution; declare solver, sampling and acceptance settings before any evaluation reading.
- [ ] Human: obtain a quantum sensor; record its sensing shape/dimensions and calibration; take empty-rig calibration/validation points (split frozen before evaluation), then the occluder plate, then plant points.
- [ ] Human: review lamp_adapter.json from a run and set review_state=accepted only after held-out empty-rig evidence.
- [ ] Verify natively whether the emitting AreaLight Parallelogram blocks/absorbs reflected light before relying on max_depth > 1 with reflective rig surfaces.
- [ ] Plant stage stays blocked: newest XL bundle has 0 leaf surfaces; reviewed-surface pilot has 0 confirmed points. Review JSONs need `geometry_completeness`.

## Codex -> Claude - growth simulation connection review, 2026-10-03

- [ ] Before connecting real plant trajectories, add an explicit observed initial-state adapter and a state-aware growth step. `growth_simulator.simulate` starts at development day zero and calls `response_model(environment, parameters)` without organ state; its fixed five-leaflet/three-flower topology and synthetic geometry are illustrative, not measured plant structure. Preserve confirmed relationships and source coordinate frames; missing geometry is not an observed leaf surface.
- [ ] Make trait/measurement joins session/date-aware before time-series use: `plant_traits.summarize` currently keys measurement/light records by plant_id only, so repeated dates overwrite one another. Carry capture dates from source manifests and integrate the existing elevation-based view regrouping before comparing capture sessions.
- [ ] Keep proxy area and DLI-times-projected-area interception separate from independently measured leaf area, GroIMP absorbed photons and photosynthesis. Do not treat `validated_metric` in the current trait summary as a passed accuracy gate: it is set when a leave-one-out error exists, without checking an acceptance threshold. Obtain Claude's specification for acceptance and missing environmental inputs before integration; no physiological parameters were fitted during this review.

## Codex delivery update 2026-10-03

- [x] Corrected trait measurement joins by date/session, grouped calibration diagnostics by plant, removed automatic metric validation on LOO availability, and labelled projected-area light interception separately from absorption/photosynthesis. Regression suites: 35 passed. Real saved T1/T2/T3 trait smoke test completed in build/trait_join_smoke_20261003_130655; source hashes unchanged.
- [ ] Per the user's latest ordering, observed-state growth initialization and state-aware growth rules are deferred until the 3D-to-light connection. Claude: execute handoff/CLAUDE_PLANT_3D_LIGHT_CONNECTION_PROMPT_2026-10-03.md, respecting optical-surface eligibility and current file ownership/freeze rules. Date enrichment of legacy inputs, elevation grouping, moving-plant handling and physical light validation remain open; no real light simulation was run by this fix.

## Codex -> Claude - compound growth and surface-area methods, 2026-10-03

- [ ] User requirement: growth prediction will use CompoundLeaf as its state/forecast unit and estimate where/how each compound leaf spreads. Also investigate improving triangle-based leaf area. This is a method investigation and implementation review, not authorization to invent biological coefficients or start model training.
  - Current behavior inspected: tools/leaf_light/reconstruction.py uses fixed-pose multi-view DLT, PCA-plane Delaunay and sampled contour gates. tools/vein_surface_bridge.py adds full visible-mask footprint checks for its partial-surface route. tomato3d/light/geometry.py::triangle_areas_mm2 already implements the correct cross-product area. tools/growth_simulator.py creates procedural geometry from development day zero rather than updating observed compounds. tools/plant_structure.py::fit_petioles exports elevation_deg from arcsin(abs(u[2])), which loses up/down sign; do not use that value as a signed directional-growth target.
  - Review scope: investigate evidence-constrained surfaces and compound-state forecasts; preserve existing masks, IDs, coordinate helpers and original source files. No docs/config/pipeline edits, no assumed growth rates, no inference/training, no push. Validate recommendations against primary literature and actual functions, then record findings below. Claude retains specification/agronomic decisions.
  - Investigation outcome / candidate implementation points for Claude review (not an approved biological model):
    1. Retain the triangle cross-product area formula. Improve measured geometry and topology instead: boundary/hole constraints, whole-face support where visibility is known, no triangles across leaflet gaps, duplicate-face/physical-surface checks, one-sided area accounting, and explicit missing/partial geometry. A single PCA chart can fail on folded leaves; use local patches or a boundary-constrained smooth surface only with supporting interior observations. Smoothing and adaptive meshing need held-out boundary/surface checks and sensitivity analysis; more triangles alone cannot recover curvature. Preserve observed-supported, interpolated and inferred areas separately; no automatic optical eligibility.
    2. CompoundLeaf is the forecast unit, with persistent plant/compound/session/date identity and parent attachment. Existing per-photo compound regions remain proposals until identity is resolved. Geometry may retain multiple disconnected tissue patches within a compound; a compound envelope is a spread/occupancy descriptor, not a solid optical leaf. Forecasting compounds does not require predicting every leaflet independently or fixing a leaflet count.
    3. Candidate state: attachment_xyz_mm, rachis control points/arc length, orientation unit vector (or wrap-safe azimuth plus signed elevation), left/right extent profiles, occupied leaf area and geometry uncertainty. Define board/plant-local axes explicitly and keep the measured plant-to-rig transform for light. Decompose attachment movement with the growing stem from leaf-local lengthening, bending, rotation and unfolding. A stem axis alone does not fix azimuth. New/missing compounds need explicit events and availability, not ID renumbering or zero geometry.
    4. Candidate forecast: next compound state = state transition conditioned on observed recent states, elapsed time, leaf rank/development evidence and available environment. Start comparisons with persistence, recent-velocity and low-parameter age/rank-conditioned expansion curves; consider GRU only after adequate independent trajectories exist. Forecast 3D tip/axis/extent distributions plus area, rather than directly extrapolating mesh vertices. Separate reversible pose changes from tissue growth; do not enforce monotone projected area or monotone leaf angles. Day/time relative to LED onset matters for observation consistency.
    5. Directional light is a candidate covariate, not a deterministic instruction to point toward maximum PPFD. A scalar DLI cannot identify a preferred direction. Measured lamp/rig geometry and supported directional incident light, neighbor geometry and missingness may be added when available; future environment is a declared scenario. Literature parameters and fixed phyllotaxis values cannot be adopted as this cultivar's measured trajectory.
    6. Train/evaluate using chronological forecasts and plant-disjoint groups, retaining all compounds/dates of a plant together for independent validation. Compare tip/axis position error (mm), orientation error (degrees), length/extent and area error, and prediction-region coverage at declared horizons. Separate matched compounds from tracking failures/missing surfaces and compare against persistence. Validate area independently with non-destructive flattened-leaf references where feasible; these references do not alone validate in-situ curvature or forecast direction. No acceptance thresholds or noise magnitudes specified here.
  - Evidence: https://doi.org/10.1093/insilicoplants/diaf024 (dwarf-tomato GroIMP FSP model; relevant architecture/light precedent, not proof of individual directional forecasting); https://academic.oup.com/insilicoplants/article/7/2/diaf022/8342854 (tomato digital-twin FSP, orientation represented with insertion/rachis/leaflet angles); https://doi.org/10.1371/journal.pone.0256340 (Pheno4D temporal organ identities/traits; external greenhouse data, not target-cultivar validation); https://arxiv.org/abs/2209.11526 (shape-assisted temporal plant-component matching); https://doi.org/10.1016/j.apm.2021.05.014 (thin-leaf surface reconstruction). Some publisher full-text requests failed; only retrieved content supports these findings, no unverified coefficients or performance metrics were copied.
  - Verification: current code inspected; synthetic calculation using triangle_areas_mm2 confirmed subdividing a flat triangle keeps 100 mm2 unchanged, and the current abs-elevation expression maps +30 and -30 degrees to +30. No real growth forecast or surface accuracy validated. Claude to specify state fields, angle convention, forecast horizons, measurement/uncertainty protocol and acceptance gates before implementing calibrated growth behavior.

## Codex delivery - plant-to-light bridge, 2026-10-03

- [x] Implemented the software connection requested from CODEX_GROWTH_CONNECTION_FIX_2026-10-03.md: explicit plant/session/date audit, immutable inputs, reviewed-surface gates, existing PPFD job preparation/collection, source-linked surface/sensor CSVs and viewer/site link. 146 targeted tests passed; four real snapshot audits preserve input hashes; synthetic scene prepared without native execution. See CODEX_PLANT_LIGHT_BRIDGE_2026-10-03.md. This supersedes the earlier request to implement the light adapter from scratch.
- [ ] Physical connection remains blocked on supplied reviewed optical leaf triangles, LightScene/plant cases and measured lamp/optics/placement/sensor inputs. No native execution, light accuracy or complete plant absorption is claimed. Source-pipeline regrouping/motion detection and observed-state growth rules remain separate pending work.

## Codex delivery update for compound calculation tools 2026-10-03

- [x] Implemented supported-surface area audit and local patch helper, explicit CSV compound states, signed directions, bounded persistence/recent-change forecasts, chronological grouped evaluation, provenance exports/viewer and delegation to the existing light preparation bridge. 102 tests passed; synthetic end-to-end preparation and read-only real T1 input audit completed. See CODEX_COMPOUND_MODEL_IMPLEMENTATION_2026-10-03.md and tools/COMPOUND_MODEL.md.
- [ ] Claude: provide the reviewed fitted biological transition specification, parameter identifiability/measurement requirements and prospective accuracy/uncertainty gates. Current reviewed_growth is explicitly unavailable, not a calibrated third model. No agronomic coefficients were guessed.
- [ ] Human/Claude: supply timestamped stable-frame whole-axis/attachment observations with confirmed persistent compound identities and independent later targets, comparable extent/area evidence and physical light inputs. Existing T1 petiole segments/proposed names do not satisfy this contract. Results: build/compound_model_20261003_02/real_t1_audit/audit.json. Synthetic verification is not real-plant validation.

## Codex -> Claude - existing-leaf area / 3D method investigation, 2026-10-03

- [x] Delivered source inspection, primary-source method comparison and eight reproducible diagnostic tables in CODEX_LEAF_AREA_METHODS_2026-10-03.md and build/leaf_area_methods_20261003/results. Existing area proxy, curve sampling, depth, overlap and noise limitations are demonstrated independently; no real accuracy claim.
- [ ] Review the candidate versioned distortion-aware proxy contract and surface-fitting validation plan. Current photo_area uses fx squared; saved T1/T2/T3 fx/fy imply +1.8829% bias under the undistorted frontoparallel approximation, plus unaccounted nonzero distortion. Old calibration k must not be reused silently after an estimator change. Keep observed partial surface, calibrated whole-plant area and hidden tissue distinct. Future leaf growth stays in the separate growth session.


## Codex delivery / Claude follow-up - adjustable 30-day scenario, 2026-10-03

- [x] User clarified all cultivar/date/history/environment inputs are absent and should be adjustable. Implemented a blank-parameter 30-day current-state scenario with stem/compound expansion, emergence, signed direction/spread, optional user-supplied environmental response tables, browser controls and CSV/JSON exports. 84 related tests passed; browser/CLI parity and provenance verified. See CODEX_MONTHLY_PARAMETER_MODEL_2026-10-03.md and tools/MONTHLY_GROWTH.md.
- [ ] Claude: evaluate biological model form, shared developmental-clock/product-response assumption, apical-only stem growth, fixed existing attachments, common leaf expansion caps and no-senescence limitation before adopting coefficients for real monthly prediction. User parameter adjustability is not calibration. Keep independent 7/14/21/30-day validation and uncertainty requirements open; do not promote synthetic scenario outputs to observed plants.


## Codex -> Claude - probabilistic CompoundLeaf architecture design, 2026-10-03

- [ ] Use CLAUDE_STOCHASTIC_COMPOUND_GROWTH_DESIGN_PROMPT_2026-10-03.md to design the measured-state-conditioned 30-day block forecast. Preserve existing measured leaves; assess stochastic L-system/RGG appearance/topology plus a bounded conditional Flow Matching extension, coherent trajectory uncertainty and observation updates. Deliver one English implementation specification with evidence and minimal interfaces. No new UI, tissue generator, model execution or training is requested by this prompt-authoring task.

## Codex -> Claude - current-leaf area and curved fitting contract, 2026-10-03

- [x] Versioned distortion-aware projected proxy, compatible calibration, supplied measured-group/motion provenance and mesh/observed-plane comparison checkpoint delivered. See CODEX_LEAF_AREA_3D_EXECUTION_2026-10-03.md. 101 focused tests passed; real T1/T2/T3 run completed with 54 photos and 4048 verified hashes in build/leaf_area_implementation_20261003/real_compare_04. Full surface/physical-accuracy objective is still open.
- [ ] Claude: supply the reviewed regularized curved local-patch contract: basis/chart, loss and weights, regularization/selection, identifiable boundary/interior requirements, convergence and independent validation/acceptance. CLAUDE_LEAF_SURFACE_OPTIONS_2026-09-29.md remains a proposal; no precise fitting contract was inferred from it. Current curved candidate is explicitly unavailable.
- [ ] Human/Claude: reuse the existing review lab to confirm physical correspondences and supply independent non-destructive area references plus metric scale/pose evidence. Current latest pair reviews contain 7 pending points and 0 human confirmations; measurements/leaf_area.csv is absent. No real curved surface, calibrated whole-plant estimate or physical accuracy is claimed.
- [x] Codex: richer local-patch/visibility adapter delivered with explicit boundary/hole point IDs, same-leaf multi-chart identity, hashed visible masks and global surface audit. Existing comparison viewer now supports patch-scoped observations, original/mask display and compound/date/patch CSVs. Hole/disconnected/fold synthetic runs and 111 focused tests pass; optical gates remain unchanged. See the local-chart completion appendix in CODEX_LEAF_AREA_3D_EXECUTION_2026-10-03.md. Automatic linking into historical plant sites is optional and was not enabled.

## Codex delivery / Claude scientific review - probabilistic CompoundLeaf specification, 2026-10-03

- [x] Executed the user-selected design prompt and delivered CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md. This is a Codex-authored proposed contract, not completed Claude review. It supplies measured-state preservation, stochastic graph events and correlated trajectories, an inactive conditional FM interface, one observation-update method, exact CSV/JSON interfaces and independent evaluation criteria. Document checks passed for 2 JSON examples and 11 local source references; no production code, training or model execution occurred.
- [ ] Claude: review the proposed waiting/stop law, joint latent dependence, remaining-growth decoder, fixed stem directions and provided-axes/no-loss applicability before adopting them as biological rules. Select numerical parameters only from explicit assumptions or suitable evidence; do not copy unrelated cultivar values.
- [ ] Real predictive calibration remains pending eligible repeated observations, event/visibility intervals, supported noise/association models and independent 7/14/21/30-day targets with practical acceptance criteria. Future implementation and FM activation are separate tasks; this design delivery does not authorize or claim either.

## Codex delivery and Claude review for detection relative area and diffusion specification 2026-10-03

- [x] User replaced missing-metric preliminary calculation with first-label area=1. Implemented saved-mask pixel ratios, separate explicit bbox proxy, immutable source audits and first-label reference preservation. 40 focused tests passed; T1/T2/T3 saved detections produced 1318 per-photo ratios over 54 images. See CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md.
- [x] Executed the review/specification scope of CLAUDE_MULTIVIEW_DIFFUSION_COMPLETION_PROMPT_2026-10-03.md. Delivered official-source feasibility assessment, current integration map, normalized-area link, proposed request/import/evaluation/viewer contracts, split/composition policy and future test plan in CODEX_MULTIVIEW_DIFFUSION_INTEGRATION_SPEC_2026-10-03.md. No diffusion implementation or execution.
- [ ] Claude: review proposed completion topology/composition and scientific evaluation decisions. No permitted execution-ready backend, justified metric conversion or optical hypothesis route is established; public pretrained checkpoint availability does not override the project model policy. First-leaf normalization does not provide metric scale or independent hidden anatomy.

## Codex delivery - growth calculator extension, 2026-10-03

- [x] Implemented CODEX_GROWTH_CALCULATOR_HANDOFF_2026-10-03.md through the existing compound_growth CLI, with the eight public functions, strict measured origin, stochastic event/continuous trajectories, explicit environment/light response contracts, CSV/JSON outputs, updates, evaluation and blank templates. Final 92 tests passed; six CLI operations and 41 output hashes verified on a labelled 16-trajectory synthetic run. See CODEX_GROWTH_CALCULATOR_EXECUTION_2026-10-03.md and tools/PROBABILISTIC_COMPOUND_GROWTH.md.
- [ ] Scientific dependencies remain: eligible repeated whole-compound/parent observations, appearance/visibility intervals, reviewed or explicitly assumed biological/response parameters, supported observation likelihoods and independent acceptance targets. The known T1 snapshot remains partial-only. No requests to search again for already-confirmed absent data; no fitted or validated real monthly forecast claimed. Flow Matching and automatic fitting remain outside this delivered handoff.

## Codex -> Claude - implemented growth calculator review, 2026-10-03

- [ ] Review CLAUDE_GROWTH_CALCULATOR_REVIEW_HANDOFF_2026-10-03.md against the current implementation. Return retain/revise/unresolved decisions, evidence/applicability, and a prioritized exact Codex change contract. Distinguish exercised software behavior from scientific acceptance; preserve measured geometry, optical boundaries and known missing-input status. This consolidates the earlier growth review requests around the now-delivered calculator.


## Codex -> Claude - light consumer interface review, 2026-10-03

- [ ] Review handoff/CODEX_LIGHT_GROWTH_READINESS_PROMPT_2026-10-03.md before future implementation. Current core direct_light calculates per-emitter direction and attenuated contributions but exposes only scalar/side receiver arrays; a backward-compatible angular diagnostic hook requires core-owner work. Preserve existing transport and unit/frame semantics; native angular/side channels remain unsupported. This entry records a prompt-review dependency, not authorization to start implementation or native jobs. Growth-direction work must consume explicit light covariates, not assume a maximum-light biological response.

## Codex -> Claude - active light readiness core dependency, 2026-10-03

- [ ] Implementation is now explicitly invoked. Add an optional keyword-only diagnostic callback/return to tomato3d/light/raytrace.py::direct_light without changing default DirectLight arrays. Required chunk payload: fixture_id; global receiver indices; stable emitter/path indices; attenuated, receiver-cosine-weighted incident contributions in umol/m2/s; unit arrival vectors in grow frame pointing receiver -> emitter/last path origin; completeness/unknown status. Contributions must include zero paths and preserve unknown paths (no dropping NaNs). Chunk metadata must allow duplicate/omission checks. Sum contributions per receiver must reproduce existing ppfd and positive-normal contributions must reproduce upper_side_ppfd at declared numerical tolerance. Keep existing crossing/own-triangle/background behavior and budgets. Tools must not implement another tracer or infer angular moments from lamp centers. Please provide callback contract and parity tests in protected core; native angular/side diagnostics remain a separate unsupported capability. Independent owned spatial/time/transform work continues. No cross-chat message sent.

## Codex to Claude detection and diffusion trial handoff 2026-10-03

- [ ] Review CLAUDE_DETECTION_DIFFUSION_HANDOFF_2026-10-03.md for the implemented detection ratios, isolated ViewFusion runner and still-unexecuted trial. The user approved public models for this comparison; GPU destination/private-photo upload remains unanswered. Review common target/evaluation fairness and RGB-only limits, then return exact corrections and acceptance evidence. This updates the earlier no-backend/model-policy status without claiming an executed model or metric/optical completion.

## Codex -> Claude - growth calibration and physiology contract, 2026-10-03

- [x] Delivered additive growth calibration (93 combined regression tests; explicit blank audit, synthetic fit, independent synthetic validation and forecast; hashes verified). See CODEX_GROWTH_CALIBRATION_EXECUTION_2026-10-03.md. Real calibration/acceptance remain unavailable.
- [x] Delivered proposed CLAUDE_FSP_PHYSIOLOGY_CONTRACT_2026-10-03.md and build/fsp_physiology_spec_20261003_01 evidence pack: 28 equations, 64 parameter records, 16 synthetic accounting checks, 89 delivery checks. No production physiology or cross-project linking.
- [ ] Review the contract's explicit source conflicts: dwarf paper eq15-16 versus official ASR division; CH2O versus CSV CO2 comments; root/fruit ASR ordering; structural versus total/minimum-pool mass; NRH incident/absorbed and net/before-mito basis. Heuvelink thesis Table1 printed p109 supports CH2O and paper root/fruit ordering but does not settle target applicability. Do not install defaults before review.
- [ ] Apply coordination D1-D4 through contract section10: P3 owns realized increments; P4 computes diagnostics only. Potential/form equations are counterfactual; no multiplier or state overwrite. Carbon sufficiency requires compatible mass inversion, roots, reserves and respiration. Future synthetic conversion/linking pass is separate and not yet executed.

## Codex -> Claude - integration decision review, 2026-10-03

- [ ] Review CODEX_FOUR_PROJECT_INTEGRATION_DECISIONS_REVIEW_2026-10-03.md before the deferred final integration prompt. D1-D4 are compatible with a read-only P4 runtime diagnostic; explicitly distinguish the existing offline calibration-to-P3 adapter. Latest physiology contract section 10 already defines the diagnostic, but integration_map.json still omits compute_carbon_sufficiency and retains earlier trajectory wording; synchronize the final machine contract under section 10 precedence. Define reversible interchange versus non-invertible reductions and retain complete source shapes/samples. P3 environment_used/light_used flags describe clock coupling only and cannot audit all family/stop-logit dependencies. This is review-only; no active code or integration changes requested now.

## Codex delivery - light growth readiness, 2026-10-03

- [x] Delivered independent owned spatial/side/area/time/transform/consumer work in tools/light_growth_bridge.py, light_growth_consumer.py, light_growth_schema.json, light_growth_demo.py and LIGHT_GROWTH_BRIDGE.md. Related 266 regressions and final 24 focused checks passed. Fresh verified package and two same-source canopy splits: build/light_growth_readiness_20261003_03. Read CODEX_LIGHT_GROWTH_READINESS_EXECUTION_2026-10-03.md and its requirement audit; this does not close the full objective.
- [ ] Claude core owner: the per-path direct_light diagnostic contract requested above remains absent. After owner delivery, Codex must connect actual contributions into spatial/time/frame directional exports and prove scalar/side/angular parity. No second tracer or lamp-center estimate is authorized as a substitute. Future growth-direction implementation prerequisites remain incomplete.
- [ ] Real-input readiness: the four supplied snapshots still lack scene/accepted optical surfaces; reviewed time/compound/axis/area associations and independent physical calibration remain required. Preserve known missing-data status without repeating global searches or promoting synthetic evidence.

## Codex -> Claude - consolidated light readiness handoff, 2026-10-03

- [ ] Read CLAUDE_LIGHT_GROWTH_READINESS_HANDOFF_2026-10-03.md for the current _04 delivery, implemented interfaces, exact core diagnostic semantics/acceptance requirements and the required return to Codex. This consolidates the existing angular-hook request; no duplicate tracer, P3/P4 linking or native execution is requested. The light implementation goal remains blocked until the core-owner interface and subsequent owned integration/parity are delivered.

## Coordination update D5-D7, 2026-10-03

- [x] Follow-up decisions in CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md section 6 settle the earlier review questions: include explicit frozen calibration-pack application before P3; numeric P4 is optional for the first pass and may be unavailable with reasons; round trips apply to reversible representations only. Reflected in CODEX_FOUR_PROJECT_CHANGE_PLAN_2026-10-03.md. This closes those decision questions, not the pending P1 trial/P2 angular work or any integration implementation. Preserve D3 deferral.


## Codex -> Claude - exact angular callback return request, 2026-10-03

- [ ] Existing core dependency remains open. Review/implement CLAUDE_DIRECT_LIGHT_CALLBACK_CONTRACT_2026-10-03.md: proposed optional keyword-only callback, complete global path inventory, explicit unknown-fixture event, read-only buffer lifetime, bounded chunks and real scalar/normal-side off/on parity. The passive tools collector is prepared and tested but deliberately not wired to a guessed API. Return the adopted signature and actual core validation to Codex before final fixture/time/frame exports and fresh angular package generation. See CODEX_ANGULAR_CALLBACK_EXECUTION_2026-10-03.md; no protected edits or cross-chat messages were made.

## Codex to Claude current FSP handoff consolidation 2026-10-03

- [ ] Use CLAUDE_FSP_CURRENT_HANDOFF_2026-10-03.md as the current review entry point. D5 includes explicit frozen calibration before P3; D8-D10 are settled. Return retain/revise/unresolved decisions for physiological accounting and an exact implementation contract. The latest P4 draft still has pending delivery verification; this 23-reference documentation check does not close it or adopt biology. Preserve earlier evidence and deferred integration.


## P4 diagnostic specification delivery 2026-10-04

- [x] Codex: completed CODEX_P4_FSP_CHAT_PROMPT_2026-10-03.md review/specification scope. New continuation report and exact diagnostic contract separate D5 preparation from runtime P4, classify all 28 equations, preserve D9 provenance and D10 scope, and specify eight environment fields. 227 delivery checks passed, including five valid and 34 invalid schema fixtures; 17 requirements verified at specification scope. See CODEX_P4_CONTINUATION_REVIEW_2026-10-03.md and build/p4_diagnostic_contract_20261003_01/verification.json. No production physiology or linking.
- [ ] Claude: review the 14 equation/accounting decision groups against preserved source locators and return retain/revise/unresolved plus exact adopted formula/unit/domain/parameter IDs. This supersedes the earlier pending-delivery-check status, not the unresolved scientific review. Preserve diagnostic-only P4, explicit frozen pre-run calibration, unavailable/hypothetical missing inputs and deferred integration. Implementation remains a separately invoked stage.


## P1 continuation delivery and execution owner update

- [x] P1 baseline and package continuation delivered in CODEX_P1_CONTINUATION_2026-10-03.md: 1318 per-photo observations, 54 first-reference checks, 4021 source hashes; exact archive integrity and target pose/gate provenance checks; 55 focused tests and 2 existing synthetic transform/split tests passed. Inventory covers 13 geometry fields/groups; no cross-project adapter or accepted real geometry produced.
- [x] The common target concern is resolved for Claude's build/multiview_completion_20261003_02/evaluation_contract.json and prepared_04 inputs. Both archives verified. User explicitly selected Claude Code as uploader; the previous destination question is superseded, not a reason to ask again.
- [ ] Claude Code execution owner: inspect the P1 report and build/p1_continuation_20261003_01/numpy_alias_diagnostic.json. Retrieved Kaggle version 3 is terminal COMPLETE but both arms failed loading numpy.core.multiarray.scalar; zero candidates. Correct the launcher/probe's explicit serialized-name mapping while retaining weights_only=True, verify exact dtype/callback compatibility, and retry within frozen budgets. Updated source archives are under the same evidence root in *_execution_package_04. Preserve failure logs and record shim diffs; no remote launch was made by this Codex continuation.
- [ ] P1 Codex after genuine successful returns: import, inspect and review all seeds/targets; preserve unavailable camera metrics until a reviewed mapping exists. Real frame/time/identity/supported-surface/normal/optical gates remain open. Full trial and integration readiness are not complete.


## Codex delivery / Claude follow-up — P3 D8–D10, 2026-10-04

- [x] Applied CODEX_P3_GROWTH_DECISIONS_IMPLEMENTATION_HANDOFF_2026-10-03.md and CODEX_P3_GROWTH_CHAT_PROMPT_2026-10-03.md within the existing calculator. User resolved compatibility as unchanged calculations plus mandatory new fields. Beta newborns, restricted temperature/DLI entry and full dependency audit, persistent node budgets, truss/terminal events, finite-bank updates, unavailable post-terminal whole-plant scope and retention flag are implemented. Final 142 tests pass; 16 valid synthetic trajectories and 20 final output hashes verified. See CODEX_P3_GROWTH_DECISIONS_EXECUTION_2026-10-03.md and build/p3_d8_d10_20261003_01/verification_final.json.
- [ ] Claude: review assumption-only coefficient/basis applicability, normalized fixed-setpoint calibration evidence and dated node/truss measurements before real use. Configured records directory is absent; known missing repeat captures remain missing. No P1/P2/P4 linking, real fitting, biological validation or unselected Science structural changes were performed. A scalar fitted width increment still requires an explicit reviewed conversion before binding to an absolute side target; the generic adapter's unit check does not supply that conversion.

## P1 v5 GPU return and EMA memory correction

- [x] Retrieved and inspected actual v5 terminal outputs, including both failures and two partial images. Checkpoint alias loading succeeded; both arms then OOM in the second LitEma.store call. No complete candidate bundles exist. See CODEX_P1_TRIAL_RETURN_2026-10-04.md; this supersedes the earlier checkpoint-load blocker.
- [x] Corrected owned runner to retain a single EMA scope across all seed/target inference. 35 completion tests pass; pinned-EMA tiny CPU evidence proves 10 exact matching outputs, parameter restoration and snapshots reduced 10 to 1. Fresh *_execution_package_05 archives under build/p1_trial_return_20261004_01 pass full hash/isolation checks.
- [ ] Claude Code upload/execution owner: retry these archives with the existing verified alias/runtime setup and frozen budgets. Actual T4 memory correction is unverified until a new run. Return complete bundles/status/runtime; Codex will inspect/import successful outputs. Do not treat the two partial v5 images as a completed trial or optical geometry.

## Claude Code -> Codex - ViewFusion runner fixes before Kaggle v6, 2026-10-04

- [x] Apply handoff/CLAUDE_TO_CODEX_VIEWFUSION_RUNNER_FIXES_2026-10-04.md in tools/ (EMA applied once on CPU and EMA module dropped, condition encodings computed once, partial bundle per view, sampler/seed equality and parsed-ID leak checks in verify_arm_isolation, tests). Append a LOG line when done; Claude Code then repacks *_execution_package_05, re-verifies isolation, versions the private dataset and pushes kernel v6. Evidence: build/multiview_completion_20261003_02/kaggle/out_v1..out_v5. Trial remains incomplete: no successful candidate bundle yet.

## User decision: light core ownership restriction revoked, 2026-10-04

- [x] Recorded the user's revocation of Claude-only light-core ownership in parent/project rules and both agent entry points. Prior TODO requests requiring an exclusive Claude producer delivery are superseded as ownership dependencies; their technical acceptance requirements remain applicable.
- [x] P2 Codex: follow CODEX_P2_LIGHT_CHAT_PROMPT_2026-10-04.md to implement the actual-path callback directly in tomato3d/light/, validate relevant core tests, connect actual angular exports, and deliver a fresh verified package. Include the clarified three-lamp REF-30-40 draft; missing PPF/beam/schedule remain physical input gaps. Coordination originally changed no code or goal status; implemented and verified in CODEX_P2_DIRECTIONAL_DELIVERY_2026-10-04.md (240 tests, three validated packages).

## P4 isolated diagnostic implementation delivery 2026-10-04

- [x] Codex: user-invoked code/model implementation completed against CLAUDE_FSP_CURRENT_HANDOFF_2026-10-03.md. Eight diagnostic APIs, templates/audit/diagnose CLI, hashed CSV/JSON IO, hypothetical fixture generator and runtime schema/guide delivered. 78 tests, 11 CLI commands/nine cases, and 196 delivery checks across 24 software requirement groups passed. See CODEX_P4_IMPLEMENTATION_HANDOFF_2026-10-04.md and build/p4_implementation_20261004_01/final_03. P3 state remains immutable; no fitting, light solving or integration.
- [ ] Claude: existing physiological review remains open. Review incident/absorbed and net/respiration ownership, ASR/source-unit/mass basis, organ mappings and initial pools before target use. Runtime serialization refinements and explicit unavailable/hypothetical behavior are documented in tools/FSP_CARBON_DIAGNOSTIC.md. No test result adopts biological coefficients. Deferred adapters must preserve native geometry hashes separately from the isolated interval-state hashes.



## ViewFusion v6 local delivery, 2026-10-04

- [x] Completed all six requests in CLAUDE_TO_CODEX_VIEWFUSION_RUNNER_FIXES_2026-10-04.md; this closes its earlier unchecked implementation item. CPU EMA and one-time encoding, atomic partial bundles with import refusal, strict shared-contract and exact-ID isolation checks are implemented. 50 focused tests passed. See CODEX_TO_CLAUDE_VIEWFUSION_V6_READY_2026-10-04.md and build/p1_runner_v6_20261004_01/delivery_manifest.json.
- [ ] Claude execution owner: upload the fresh packages from build/p1_runner_v6_20261004_01 (superseding interim package_05 archives under p1_trial_return_20261004_01), update launcher pins, reverify and run v6 under the frozen budgets; return actual complete/partial outputs and statuses. Codex actual-output import/review remains pending. No successful GPU trial or metric/optical acceptance is claimed.

- [x] Final P4 implementation verification refinement: 79 tests now pass, including explicit parameter-pack scope mismatch. Use build/p4_implementation_20261004_01/final_04 and its current manifest; the earlier 78-test/final_03 references are historical. The 24 software requirement groups and 196 delivery checks remain complete; scientific review remains open.



## P1 execution dependency update, 2026-10-04

- [ ] Claude: retry the already verified v6 packages when Kaggle GPU batch capacity is available. The 13:08 push was rejected with maximum batch GPU session count 2 reached. Return actual statuses/bundles for Codex validation; do not treat the old terminal COMPLETE status as v6 success. Local runner implementation is delivered; full P1 goal is blocked on this external execution dependency.

## P2 actual directional delivery, 2026-10-04

- [x] Completed the CODEX_P2_LIGHT_CHAT_PROMPT_2026-10-04.md software objective after the user's light-core ownership override: actual direct-angular-1 callback, bounded collector, real F/M/B fixture/time/frame/region exports and independent consumer. 240 tests pass; fresh main package and two canopy-preserving splits validate. See CODEX_P2_DIRECTIONAL_DELIVERY_2026-10-04.md and build/p2_angular_20261004_01/delivery_verification.json. Historical core-owner wait requests above are superseded.
- [ ] Physical readiness remains open: supply actual PPF, aperture/center/height evidence, beam parameters, relevant leaf/surface optics, eligible metric optical surfaces, clock windows and independent PPFD calibration/evaluation measurements. Fresh draft build/lighting_REF_30_40_three_20261004_03 preserves confirmed 16 hours/day at 100% with no fabricated schedule. This is not a software blocker or a claim of real PPFD accuracy; cross-project linking remains deferred.

## Four project delivery review, 2026-10-04

- [x] Reviewed the four requested P1/P2/P3/P4 delivery handoffs; checked 291 recorded hashes and final P2/P3/P4 JUnit evidence without rerunning tests or models. See CODEX_FOUR_PROJECT_DELIVERY_REVIEW_2026-10-04.md and build/four_project_delivery_review_20261004_01/review_evidence.json. P2 directional and isolated P4 implementation are delivered; earlier wait/specification-only entries are historical.
- [ ] Codex -> Claude/P3 calibration owner: review the generic apply_parameter_set semantic guard gap documented in section C. Same-unit increment-to-absolute-width bindings need explicit rejection unless a reviewed conversion exists; no invalid delivered forecast was reproduced and no code was changed in this review.
- [ ] Codex -> Claude coordination: define P2 supported-tissue DLI versus P3 whole-plant fixed DLI, native geometry versus P4 endpoint-state hash association, and organ mass/respiration scope before deferred adapters. Explicitly classify light-driven direction, future optical geometry and reserve propagation as pending extensions rather than existing capabilities. Continue the established physical input/scientific review queues; do not reopen completed software or the confirmed 16 h/full-output lamp metadata.

## Claude Code - ViewFusion trial result, 2026-10-04

- [x] v6 ran both arms on Kaggle T4; 20/20 views imported, evaluated (metrics unavailable with reasons) and reviewed. See handoff/CLAUDE_MULTIVIEW_TRIAL_RESULT_2026-10-03.md.
- [x] Contract r03 executed (cleaned 27 mask, stems >= 0.5, seeds 42-49); see the result handoff addendum.
- [ ] Human/design decision: whether to pursue this route further. Open items: validated original-camera mapping for T_eval metrics, passing condition pose gates, reviewed fully connected plant masks (stem detections are sparse).


## P1 actual v6 return review completed, 2026-10-04

- [x] Claude executed v6 successfully; Codex independently imported/validated all 20 views, checked 24 comparison rows and visually reviewed the sheet/local references. The earlier GPU retry and actual-output review items are closed. All 4021 baseline hashes match. See CODEX_P1_V6_RESULT_REVIEW_2026-10-04.md and build/p1_v6_result_review_20261004_01/completion_audit.json.
- [ ] Scientific follow-up remains separate: camera mapping/pose gates, conditioning-mask policy and real identity/area/normal/optical evidence. Fragment provenance is a hypothesis; masked inputs already omit connecting plant structure. No metric/optical acceptance or interproject integration is claimed.


## P3 semantic guard verification, 2026-10-04

- [x] The four-project review section C / P3 increment-to-absolute-width binding guard item is closed. Claude implemented the runtime meaning check; Codex verified all six backup/current hashes, inspected the exact delta and reran the six suites on Windows: 256 passed, no failures. This supersedes the earlier open generic-guard item. See CODEX_P3_SEMANTIC_GUARD_REVIEW_2026-10-04.md and build/p3_semantic_guard_review_20261004_01/verification.json. No production changes during review; no automatic semantic conversion or biological applicability claim.

## Codex -> Claude: growth equation review pack, 2026-10-04

- [x] Codex: compiled current P2 supporting light, P3 growth/development, P4 carbon and calibration equations in CLAUDE_GROWTH_EQUATION_REVIEW_PACK_2026-10-04.md. Verified 18 equation groups, 15 local links and 18 source-function references; no model changes or runs.
- [ ] Claude: return retain/revise/unresolved decisions for the 18 equation groups using the pack's response table. Prioritize light/area/respiration basis, calendar versus development time, increment versus absolute target binding, mass/form scope and non-propagated reserve accounting. This consolidates existing scientific review requests; it does not adopt candidate coefficients, authorize implementation or reopen completed software delivery.

## Growth Science review prompt preparation and user answers 2026-10-04

- [x] Claude Science response received in CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md; this closes the earlier request for an initial equation review, not the remaining physiological/source questions.
- [x] Codex: recorded section 4 question 1 and question 3 as accepted recommendations, question 2 as undecided; prepared four separate prompts and index in CODEX_GROWTH_SCIENCE_CHAT_PROMPTS_INDEX_2026-10-04.md. All F1-F11 have an owner; reference/coverage checks passed. No implementation or cross-chat dispatch in this preparation.
- [ ] Recipient chats, when the user submits the respective prompt: follow its bounded scope and write separate execution/readiness reports. P3 alone edits calibration; P4 owns the new equation registry. Question 2 and optional G03/G06/G07 selections remain open; source reading is separate from choosing physiological policy. Cross-project integration remains deferred.

## P2 Growth Science clarification, 2026-10-04

- [x] P2 recipient completed CODEX_P2_GROWTH_SCIENCE_CHAT_PROMPT_2026-10-04.md within its unsupported-reference-channel branch: corrected stale direction metadata, explicit unavailable reference-DLI provenance and independent false-claim/basis checks, documented future inputs and P3/P4 ownership. 181 tests and three fresh package validations pass; old/new CSV values are identical. See CODEX_P2_GROWTH_SCIENCE_EXECUTION_2026-10-04.md and build/p2_growth_science_20261004_01/verification.json.
- [ ] Future separately authorized reference channel needs declared reference position/plane, disjoint basis, complete-day incident PPFD history, clock/coverage/evidence and canopy context. No sampling implementation was authorized by this clarification. P3 owns applicability interval, curve-specific c_DLI and rejecting light-direction bindings; P4 question 2 remains undecided. Existing physical-input/PPFD validation items remain open; 16 h/day and 100% are confirmed.


## P1 program corrections from r03, 2026-10-04

- [x] User-selected existing-leaf 3D/area improvement implemented and tested in owned program code. See CODEX_P1_R03_PROGRAM_UPDATE_2026-10-04.md; 117 tests and actual T1 calculations verified. No Claude deep-learning edit, new inference or source observation mutation.
- [ ] Claude/scientific review: inspect the 12 candidate regions after corrected measured-view grouping; do not transfer old region IDs/names. Physical surfaces, camera gates and independent leaf area remain unvalidated. Supply explicit grouping policy to new S3 runs and bind reviewed region names to the current partition hash.

## Claude - colour cue experiment, 2026-10-04
- [x] (2026-10-04 18:15, all numbers match; diagnostic grid rerun completed; see result handoff addendum) Check the rerun outputs in build/color_cues_20261004_01 (summary.json, arm_results.csv, diagnostic_grid.csv, dwt_test_shift.csv) after evaluate.err.log/diagnostic.err.log finish; update the result handoff if E/G differ.
- [ ] Human: add masks for leaflet boxes without a human mask (build/color_cues_20261004_01/leaflet_boxes_without_human_mask.csv; dwt_02 15) and re-score AL4 step_0 area.


## P3 Growth Science delivery / Codex -> Claude, 2026-10-04

- [x] Authorized P3 decisions 1/3 and F2/F3/F7/F8/F9/F11 implemented and verified: 174 tests, unchanged frozen baseline, original ensemble coverage retained, 37 export hashes verified. Read CODEX_P3_GROWTH_SCIENCE_EXECUTION_2026-10-04.md; original semantic-guard cases remain passing.
- [ ] P4 F1 owner: consume the equation-to-function map and final source hashes in that execution report for the registry. P3 did not edit the registry or P4 runtime.
- [ ] Claude scientific review: supply independently supported curve-specific DLI coefficient identities/evidence and inclusive applicability interval, incident reference plane and complete local-day coverage before real use. No defaults were invented. Missing repeated observations remain an external scientific limitation, not a software completion blocker.
- [ ] Deferred policy questions remain unchanged: select or reject reanchor_weight, transient-posture and truss_observable separately; decide P4 question 2 in its own scope. Cross-organ measurement correlation is explicitly unmodeled. Current narrowing evidence threshold is exactly target < min(observed stations); a broader threshold needs a separate decision.


## Codex -> Claude: P4 growth Science safety completed, 2026-10-04

- [x] P4 recipient completed F1/F4/F5/F6/F10. 105 tests, 12 CLI executions (one intended rejection), 10 synthetic cases and 256 checks pass. See CODEX_P4_GROWTH_SCIENCE_EXECUTION_2026-10-04.md and build/p4_growth_science_20261004_01/verification.json. This closes P4's implementation portion of the prompt-recipient item; other chats retain their own scope.
- [ ] Claude: resolve empirical NRH net/before-mito fitting and manuscript CH2O versus official CSV CO2 maintenance conflict using original preprocessing/author evidence. The source measurement conditions are documented, with cuvette versus leaf temperature and partial-pressure versus ppm distinctions. Q2 remains undecided; do not adopt source coefficients or treat software validation as cultivar validation.
- [ ] P4/P3 handoff refresh after P3 completion: equation_registry_v2.json uses a frozen in-progress P3 snapshot with exact locators; do not claim final synchronized producer mapping until the P3 owner completes. Cross-project adapters and reserve propagation remain deferred.


## Codex -> Claude: P1 Growth Science readiness, 2026-10-04

- [x] P1 completed the bounded read-only readiness audit. See handoff/CODEX_P1_GROWTH_SCIENCE_READINESS_2026-10-04.md and build/p1_growth_science_readiness_20261004_01/completion_audit.json: 25 fields, 58 unchanged source hashes, 41 local references and two exact existing canopy splits. No production edits, inference, experiments, new adapter or human-record mutation. Real supported physical area and longitudinal organ identity remain unavailable; this closes the audit, not scientific validation.
- [ ] Claude observation-specification owner: before future same-organ extent acquisition, define whether station in [0,1] represents normalized arc length or another declared correspondence, the station placement/reidentification procedure, and reviewed transverse-axis handedness. Current compound_growth._stations validates range/order/endpoints only; it does not establish anatomical correspondence. Preserve optional G03/G06/G07 as unadopted. This is a design question, not permission to change the model.
- [ ] Claude measurement-protocol owner: review the proposed G08 remounting replicate, G06 phase/timing, G07 dated-event and independent-area checklist in the readiness report. Human acquisition is separate; P1 exports reviewed evidence, P3 owns growth/calibration/covariance consumption, P2 owns future reference-light export, and P4 owns physiological diagnostics. No new acquisition campaign is authorized by this audit.

## Four Growth Science delivery consolidation 2026-10-04

- [x] Codex coordination: reviewed all four requested reports and saved evidence. See CODEX_FOUR_PROJECT_GROWTH_SCIENCE_SUMMARY_2026-10-04.md. The four bounded follow-up tasks are delivered; this does not declare original project goals, real-plant validation or integration complete.
- [ ] P4/coordination metadata follow-up: associate the versioned registry with P3's final completion report in a new version or addendum, preserving historical snapshots. All 31 code references already match current hashes/function lines; the only snapshot mismatch is the P3 report's appended completion sections. No algorithm repair is indicated by this finding.
- [ ] Existing readiness follow-ups remain: real P1 supported area and longitudinal identity; separately scoped P2 reference-position complete-day DLI channel/evidence; applicable P3 parameters; P4 Q2 and original-source convention reconciliation. Do not repeat completed F1-F11 work or treat tissue DLI as reference DLI. Integration remains deferred.

## Growth pack V2 prompt preparation 2026-10-04

- [x] Codex coordination: read V2 and recorded D11-D18, inspected current function/field vocabulary, and prepared four delta prompts in CODEX_GROWTH_PACK_V2_CHAT_PROMPTS_INDEX_2026-10-04.md. No production changes or dispatch. Historical Q2-undecided and optional-feature-unadopted entries are superseded by the newer decisions; no 1.466 maintenance rescaling is requested.
- [ ] Recipient chats on user submission: implement/review their scoped V2 delta and deliver separate CODEX_P1/P2/P3/P4_GROWTH_PACK_V2_EXECUTION_2026-10-04.md reports. P3 owns calibration; P4 owns physiology and registry; P1/P2 supply evidence/interface alignment. Keep reference-DLI production and integration outside this scope.
- [ ] Coordination after actual deliveries: consolidate the single CODEX_GROWTH_PACK_FIXES_EXECUTION_2026-10-04.md requested by V2, with fresh validation evidence. Do not claim completion of the runtime work from prompt preparation. Keep missing real measurements and biological applicability separate from resolved implementation policy.

## Claude Code -> Codex: S3/S8 measured grouping, 2026-10-04

- [x] Fixed by Claude on explicit user request (2026-10-04): new `plant_structure.region_assignment_digest` converts numpy values before `digest`; regression `test_region_assignment_digest_accepts_numpy_values_from_real_runs` (mutation-checked); 58 tests in the four plant_structure/pipeline suites pass; unwrapped S3 on dwt_t1-t3 gives the same assignment hashes as the wrapper run. Backup of the original: `build/plant3d_regroup_20261004_01/backup/plant_structure.py.orig`. Original item: `tools/plant_structure.py:655` fails on every real run with a view grouping: `digest(... regions=info)` gets numpy int64 -> `TypeError: Object of type int64 is not JSON serializable`. Convert numpy scalars to plain Python before hashing (pure-Python digests stay identical) and add a regression with numpy values. Claude's workaround (no tools/ edit): `build/plant3d_regroup_20261004_01/s3_safe.py` + `run_pipeline.py`.
- [ ] Codex: `tools/plant_traits.py` S8 means still use `view_group(code)` (photo number) although `view_geometry` is recorded per row; for dwt_test the "top" area averages ring photos 01/03. Use the measured grouping when supplied (unavailable otherwise), consistent with S3. Expected values: `build/dwt_test_fill_20261003/traits_by_elevation.csv`.
- [ ] Human: check the changed dwt_t2 (now L01-L04 + growing_leaf) and dwt_t3 regions in `build/plant3d_regroup_20261004_01/run2_<plant>/<plant>/hierarchy/viewer.html` before confirming names. See handoff/CLAUDE_PLANT3D_REGROUP_2026-10-04.md.

## P2 reference DLI prompt supplement 2026-10-04

- [x] Codex coordination: incorporated CODEX_REFERENCE_DLI_CHANNEL_HANDOFF_2026-10-04.md into the existing P2 V2 prompt. Prior no-reference-channel restrictions in the earlier prompt/index are superseded for this scoped recipient task. All nine handoff checks and P3 field-mapping limits are included; original source handoff preserved.
- [ ] P2 recipient on prompt submission: implement logged and spot-schedule measured routes, simulation interface/audit only, and independent package/consumer checks; report in CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md and cross-reference the V2 report. No P3/P4 runtime edits or full-system linking.
- [ ] Real inputs after meter arrival (expected around 2026-10-10, not confirmed): fill declared reference position/plane, actual clock schedule, PPFD readings and applicable model-domain evidence. Keep templates blank meanwhile. A multi-day reference reduction cannot silently masquerade as P3 single-day provenance; report any remaining consumer schema decision.

## Technical review prompt supplement 2026-10-04

- [x] Codex coordination: supplemented all four existing V2 chat prompts from CODEX_TECHNICAL_REVIEW_FIXES_HANDOFF_2026-10-04.md and D19-D21. Source handoff unchanged; earlier prompt versions backed up. This closes preparation only, not implementation.
- [ ] Recipient implementation ownership: P2 adds the single DLI_UNIT and owns reference-channel/face outputs; P3/P4 import it in their own files. P1 owns Day-1 template/checklist and area evidence gate; P3 owns read-only record back-fill. Never infer historical observations or rewrite human data.
- [ ] Apply each project's listed technical delta once with V2, record done/already present/deferred, and save separate tests/reports under technical_review_fixes_20261004_01 subdirectories. Coordination owns the later CODEX_TECHNICAL_REVIEW_FIXES_EXECUTION_2026-10-04.md. NRH empirical preprocessing and the source-listed missing physiological models remain unresolved/unimplemented; adopted policy is separate.


## Codex -> Claude / P3 / coordination: P1 V2 and technical-review delivery, 2026-10-04

- [x] P1 recipient completed technical-review section 6 and its D21 portion. See handoff/CODEX_P1_GROWTH_PACK_V2_EXECUTION_2026-10-04.md and build/technical_review_fixes_20261004_01/P1/verification.json. Added complete real-area evidence gating/reporting at compound_surface while preserving diagnostic geometry calculations; 60 focused tests passed and one explicitly synthetic CLI audit completed. Exact 11-column Day-1 template is header-only; Korean checklist and P3 mapping are delivered. Nine relevant prior evidence/source files remain unchanged; no improved physical accuracy, human measurement or longitudinal identity is claimed.
- [ ] P3 owner: consume the Day-1 template/mapping in build/technical_review_fixes_20261004_01/P1/measurements/ for your separately owned read-only back-fill/import. Preserve completed CSV/evidence hashes and row lineage, actual clock/schedule evidence and explicit visible_bud meaning; do not auto-expand counts into ranked events or infer existing-organ ages. No P3 loader was edited by P1.
- [ ] P2/P3 consumers and coordination: real-area claims from the new P1 boundary use area_basis.csv / downstream_leaf_surfaces.csv plus audit/source hashes. Existing supported_leaf_surfaces.csv and supported_area_cm2 remain diagnostic and pending optical review. Passing evidence completeness does not certify biological face, illumination, target accuracy or independent measurement. Read the exact contract in tools/COMPOUND_MODEL.md before any separately authorized adapter.
- [x] Policy-note update: old P1 "optional G03/G06/G07 unadopted / no recording protocol" notes are superseded by D14 and D21 for new work. The station-correspondence scientific specification and missing real covariance/area/face evidence remain open. New visible_bud protocol does not reinterpret older ambiguous observations. P2 owns illuminated-face exposure and P4 its policy gate.


## Codex -> Claude / coordination: P4 Growth Pack V2 delivery, 2026-10-04

- [x] P4 A1-A7, D19/D20, P4-a..f and F1/S3/technical section 3 delivered. 147 P4 tests plus 2 named Windows tests passed; 15 synthetic cases, 19 CLI commands (one intended rejection) and 554 delivery checks passed. See handoff/CODEX_P4_GROWTH_PACK_V2_EXECUTION_2026-10-04.md and build/technical_review_fixes_20261004_01/P4/verification.json. No P3/calibration/P2 producer or human-record edits by P4.
- [x] Supersedes earlier Q2-undecided / active maintenance-unit-conflict follow-ups for implementation policy: D15-D18 resolve absorbed dwarf input, before_mito, CH2O maintenance and face scope. New versioned registry preserves contrary historical records and coefficients without rescaling. P2 supplied DLI_UNIT; P4 imports it.
- [ ] Coordination/P3: after actual P3 V2 completion, refresh the frozen producer association in a new registry/addendum. V3 records the completed previous Science report and a V2 in-progress snapshot; its code advanced during P4 verification. Preserve both snapshot and final hashes. This pending metadata refresh does not block the bounded P4 delivery.
- [ ] Claude scientific review: original NRH empirical fit preprocessing and target applicability remain unresolved. Real area/biological-face, mass, reserve and domain/parameter evidence still require support. Buffer feedback, nonfoliar assimilation, reserve propagation, two-sided exchange, sympodial continuation, light-to-orientation response and FvCB remain deferred. Do not treat synthetic tests or conditional sufficiency interpretation as biological validation.


## P3 V2 and technical review delivery, 2026-10-04

- [x] P3 recipient task complete: D14a/b/c, D19/D21 and P3-a..f implemented or verified already present. Existing F2/F3/F7/F8/F9/F11 retained. See CODEX_P3_GROWTH_PACK_V2_EXECUTION_2026-10-04.md and technical_review_fixes_20261004_01/P3/completion_audit.json: 210 unique passing cases, both named Windows regressions, exact baseline, five real CLI commands and 47 verified export hashes. Day-1 loading is read-only; P1 template unchanged.
- [ ] Coordination/P4 registry owner: use P3's final hashes and equation/function map in the V2 report for the new registry and the shared V2/technical roll-ups. This task did not edit those shared artifacts or dispatch messages.
- [ ] Claude/scientific input follow-up: supply applicable real DLI coefficient-domain evidence, repeated same-organ measurements and identifiable within-trait variances/phase offsets before real use. No values were inferred. Intermediate orientation interpolation and cross-covariance remain explicitly unsupported under the adopted constraints; selecting new laws is separate from completed software.
- [ ] Day-1 acquisition owner: continue explicit visible_bud/aware-time/phase/sourced-node-count recording. P3 consumes exact P1 columns and existing-axis mapping; counts are not invented node ranks, dates are not organ ages, old records are not rewritten. Full-system integration remains separately scoped.

## P2 V2 and reference-channel final delivery, 2026-10-04

- [x] P2 recipient completed the revised V2/reference prompt, D19/D20 and P2-a..h. This closes P2's portions of the earlier recipient/reference/technical-review implementation items and supersedes their historical unimplemented-reference and Q2-undecided notes. See CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md and CODEX_P2_GROWTH_PACK_V2_EXECUTION_2026-10-04.md. Final audit: 435 checks, 175 unique passing tests, six independently validated packages and three reference-channel outputs; all five historical numeric tables and 21 protected hashes are unchanged. Evidence: build/technical_review_fixes_20261004_01/P2/completion_audit.json. No forecast, physiological exchange, Native execution or physical accuracy claim.
- [ ] Real measurement owner: after actual meter arrival (expected around 2026-10-10, not confirmed), supply reference position/height/frame, level and cosine evidence, dated on/off times, identified PPFD readings, ambient evidence, survey and supported positional/uniformity/horizon tolerances, plant association and P3 coefficient-domain evidence. Blank templates and the Korean checklist are in build/reference_dli_20261004_02/. Confirmed three lamps, 16 h/day and 100% output setting remain unchanged; clock windows remain unknown.
- [ ] Physical optical validation remains separate: actual PPF, emitting aperture/center/height and beam evidence, reviewed metric leaf surfaces/optics, and independent PPFD/calibration measurements. Measured routes A/C do not require lamp PPF. No lumens/CCT conversion or example optical values were adopted.
- [ ] Future P3 schema decision if multi-day/scenario consumption is requested: producer modes retain complete evidence, but the current mapper explicitly refuses p3_single_local_day_contract_cannot_represent_<value_rule>. Do not fabricate one local day. Route B execution and full-system integration remain separately scoped.
- [ ] Coordination: consume the two final P2 reports and current source hashes for your shared roll-ups. P2 did not edit the shared roll-up or dispatch messages; other owners retain their scopes.

## Codex -> Claude: plant area review corrections, 2026-10-04

- [ ] Reconcile the attached CLAUDE_PLANT3D_AREA_REVIEW_2026-10-04.md before implementation: G range does not match independent integration; area-only top views cannot resolve normal sign; A2 lacks the position/outline needed by A3; unknown occlusion does not yield a finite A1 interval; top/ring ratio does not uniquely determine mean inclination. Supply the missing synthetic reproducibility bundle and independent calibration/validation criteria. See handoff/CODEX_PLANT3D_AREA_REVIEW_RESPONSE_2026-10-04.md and build/plant3d_area_claim_check_20261004_01/projection_check.json. This is a review objection, not adoption of defaults, user decisions, or an implementation request.


## Four project area review prompts, 2026-10-05

- [x] Codex coordination prepared the user-requested four project chat prompts based on the attached Claude plant-area review and Codex corrections. See CODEX_FOUR_PROJECT_AREA_REVIEW_PROMPTS_INDEX_2026-10-05.md. This supersedes the mistaken top-view diffusion target assumption, not the earlier scientific objections.
- [ ] Recipient chats, when submitted by the user: inspect and apply only missing owned evidence/interface corrections, report already present versus design pending, and preserve completed V2 behavior. The new G/A1/A2/A3/matching/calibration choices are not adopted. Save separate project execution reports; no implementation or dispatch occurred during prompt preparation.

## P2 area-review alignment delivery, 2026-10-05

- [x] P2 recipient completed CODEX_P2_AREA_REVIEW_CHAT_PROMPT_2026-10-05.md: versioned geometric-computability/physical-eligibility audit, explicit unlocated-A2/proxy reasons, independent rehashed-claim rejection, unchanged transport/area/D20/reference semantics and canopy reporting verification. See CODEX_P2_AREA_REVIEW_EXECUTION_2026-10-05.md and build/area_review_alignment_20261005_01/P2/completion_audit.json: 80 unique passing tests, 16 overlapping current-dependency checks, 150 audit checks, three independent packages, exact five-table historical numerics and 23 unchanged protected files. This closes only P2's area-review software scope.
- [ ] Claude/P1: provide independently supported located receiving surfaces (vertices, or justified centroid/depth/outline/shape), board/grow identity, scale/pose calibration and one-sided area/support/coverage evidence. Geometric winding/upward orientation is not botanical face evidence; D20 still requires a separate reviewed mapping. No A2 tuple, projected proxy, hull or mean angle is accepted as certified optical tissue.
- [ ] Claude/user: keep area-review A1/A2 reporting priority, leaflet-matching method and calibration strategy open. Specify area-A3 camera visibility/located-surface dependencies before any future reconstruction adapter. Supply the missing companion simulation/CSV/SVG evidence before relying on reported synthetic accuracy; no G/lambda/tau/curvature/radius default was adopted.
- [ ] Physical-validation owner: real lamp/leaf optics and independent PPFD calibration/evaluation remain required. Supported measured reference DLI is independent of leaf optical eligibility; retain the existing P3 multi-day/scenario limitation and actual-reference-input TODO. Confirmed operation remains three lamps / 16 h per day / 100% output, with clocks still unknown.


## Codex -> Claude / P2: P1 area-review alignment delivery, 2026-10-05

- [x] P1 recipient completed the bounded area-review prompt: explicit S8 policy forwarding, separate grouping/integrator audits, unknown-view completeness, top-count fix and hash-bound trait provenance exports. Existing surface/face gates and diagnostic numerical baselines remain. See CODEX_P1_AREA_REVIEW_EXECUTION_2026-10-05.md and build/area_review_alignment_20261005_01/P1/verification.json: 119 unique tests and 27 delivery checks pass. This closes the P1 portion only and supersedes the historical missing-S8-caller item; the inspected real configuration still lacks an explicit area_policy/capture_style and was not changed.
- [x] P2 handoff inventory published: build/area_review_alignment_20261005_01/P1/P1_TO_P2_GEOMETRY_MANIFEST.json. Existing canopy transforms, exact source partitions and tissue accounting verified; current P2 optical-geometry-evidence-1 report reviewed read-only. No independently supported real optical surfaces can yet be supplied. No cross-chat dispatch or runtime adapter.
- [ ] Claude: supply a corrected executable area-review A1/A2/A3 contract with exact inputs/outputs/units, justified G and occlusion bounds or explicit unavailability, stable mask correspondence, pose/depth/view-coverage identifiability, antipodal normal convention, separately sourced located shape for A3, and convergence/failure/uncertainty/independent-validation criteria. Do not treat area plus two angles as a complete optical surface. Companion simulation/CSV/SVG evidence remains missing in the bounded locations checked.
- [ ] Claude/user: retain three open decisions (A1/A2 reporting priority, leaflet matcher, calibration strategy). Tau=.9, low-dilation depth priors, curvature factors and radius restrictions remain unadopted. Explicit v2 numerical policy/capture style is needed before enabling it in a real S8 configuration; no settings were silently chosen.
- [ ] Real evidence owners: scale, pose acceptance, one-sided lamina area/support, capture time/phase, reviewed tissue identity and botanical face evidence remain required. P1/P2 metadata gates and synthetic regressions are not physical validation. Do not infer measurements from templates or promote hull/projected/generated tissue.


## Codex -> Claude / coordination: P4 area-review delivery, 2026-10-05

- [x] P4 area-review prompt complete: physical one-sided area/source/partition gates, botanical-face evidence, endpoint SLA support, full-canopy provenance and per-plant accounting verified; exact synthetic baseline retained. 186 tests (147 retained + 39 new), 19 CLI commands on 18 cases and 306 delivery checks passed. See CODEX_P4_AREA_REVIEW_EXECUTION_2026-10-05.md and build/area_review_alignment_20261005_01/P4/verification.json. All eight items and six acceptance cases covered; no producer/runtime integration or biological validation.
- [x] P4 registry refresh records P3's now-final V2 report and separately freezes current owner code. Six of nine reported file hashes still match; three runtime files advanced. equation_registry_v4.json preserves v3 and does not falsely claim synchronized V2 source. Future changes require another versioned association.
- [ ] Claude/user: three area-review decisions remain open (A1/A2 reporting priority, leaflet matching, calibration). Corrected estimator/observability and independent validation contracts plus missing simulation/CSV/SVG evidence remain required. Namespaced area_review_A1..A7 are proposed/unvalidated, not adopted physiological A1-A7. Do not reopen D15-D18/Q2.
- [ ] P1/P2/P3 future adapter owners: P4 now documents p4-area-evidence-1 in tools/FSP_CARBON_DIAGNOSTIC.md. Bind physical area and source-row/partition hashes to exact plant/organ/patch/basis/geometry; retain full-canopy source and separately evidenced anatomical face/exposure. Endpoint area evidence belongs in P3 interval maps outside hashed organ states. Current P1 geometry manifest exports no supported real optical surfaces. No adapter or inferred real evidence was supplied by P4.


## Codex -> Claude / coordination: P3 area-review delivery, 2026-10-05

- [x] P3 recipient completed its bounded area-review interface corrections. See CODEX_P3_AREA_REVIEW_EXECUTION_2026-10-05.md and build/area_review_alignment_20261005_01/P3/completion_audit.json: 256 final passing tests, exact frozen states/weights, two actual CLI commands and 16 verified outputs. This closes P3 only in the four-project recipient item. No area estimator, biological coefficient fitting or other-project runtime change.
- [ ] Claude/P1: specify reviewed comparability for changed acquisition/method/calibration/pose/partition/phase/support hashes and any merged/split/canopy-placement identity transition before those observations enter one growth series. The new versioned P3 metadata retains them but returns unavailable without a supported mapping. P1 diagnostic supported_area_cm2 is not an automatic real-area input. Keep area-A1/A2 priority, leaflet matching and calibration strategy open; earlier physiological decisions remain adopted.
- [ ] Acquisition/scientific reviewer: supply independent same-organ area references with tissue/coverage, scale and source-row evidence, cross-date lineage, and trait-specific repeats/variance at documented capture phases. Repeatability/single-capture labels cannot certify growth dynamics. Provide multiple later same-organ observations across independent plants/units and coefficient-domain evidence before real calibration; no historical values or variance were inferred.
- [ ] Coordination/P2/P4: consume the final P3 report and source hashes for later integration while preserving incident-reference DLI versus tissue optics/face separation. No automatic P1 adapter, normal-to-trait conversion, area-to-shape equation, changed-method conversion or full-system validation is claimed. No messages were dispatched by this task.


## Codex -> Claude: nutrient FSP implementation, 2026-10-06

- [x] Implemented the independent fertilizer-label conversion, two-layer prescribed-flux water/element ledger, drainage/reuse and plant nutrient accounting, CLI/templates/scenario comparison and optional read-only P4 binding. 253 tests (67 new + 186 existing P4), eight actual CLI executions and 244 independent delivery checks pass. See CODEX_FSP_NUTRIENTS_EXECUTION_2026-10-06.md. This closes accounting/engineering only, not the full uptake-to-growth model.
- [ ] Claude scientific owner: provide the executable contracts requested in CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_REQUEST_2026-10-06.md (hydraulics, exchange, uptake, tissue demand/allocation, growth, salinity and joint carbon/nutrient controller). No source coefficients or growth laws were guessed. Predictive uptake and actual growth feedback remain unavailable.
- [ ] Real-input owner: supply fertilizer label/dose and final solution volume, source-water composition, confirmed internal filling dimensions, initial water/ion pools, water capacities, irrigation/drainage evidence and any independently measured uptake/plant nutrient state. Header-only templates are in build/fsp_nutrients_20261006_01/templates; never interpret EC/pH/photos or the synthetic demo as those measurements.

## Pointer for step 5 tracking (data/tracks/ planning, when reached) - 2026-10-08 literature intake

- [ ] Design to start from: board-pose-normalised 3-D position as the prior + growth-invariant appearance embedding for ambiguous cases; track **compound leaves**, leaflet identity inherited from `station_index`; plant 1 defoliation series = free matcher-rejection test; synthetic growth sequences can supply identity-labelled training data (LeafTrackNet). No content under data/ until that step opens (data/ is human-owned). See handoff/PRIOR_ART_DWARF_TOMATO_FSP_2026-10-08.md.

## Claude -> Codex: phynotype2 compound/terminal tracking, 2026-10-10

- [ ] Codex: implement work orders W0-W9 of handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md in phynotype2/ (generator and tools imported read-only; no data/ writes). Start with W0-W5; W6 (generator adapter) runs in the tomato_synth environment.
- [ ] Human: answer section 11 open items (pot orientation mark, pot rim inner diameter, lights-on time, top-view mask source, dwt_01-04 validation use, who writes manual_track_labels.csv). Also add phynotype2/ to CONVENTIONS.md section 1 and reconcile density_timeseries PROTOCOL.md section 4 (weekly) with the twice-daily capture decision.

## Phase 1 VTC/Python V2 execution, 2026-10-11

- [x] Codex (user one-task exception): delivered bounded native leaflet-subset mode, frozen Python bridge, carbon/geometry verification and native evidence. 234 tests pass; 16 successful three-day scenarios (48 intervals) plus intentional deficit/timeout failures. See PHASE1_GROIMP_PYTHON_EXECUTION_2026-10-11.md and build/vtc_python_phase1_20261011_acceptance/acceptance.json.
- [ ] Full original V2 remains INCOMPLETE: implement and test original-VTC determinate/truss/internode/rank-leaflet/rachis adaptation, 30-day seed spin-up, Stage-2/P1 input adapter and complete stem/root/fruit carbon pools. The delivered mode uses a VTC NRH fragment plus new native conservative accounting; it is not the complete developmental model. Do not mark the original prompt done.
- [ ] Scientific/real-input follow-up: independently review the constant-SLA and fixed-coefficient NRH assumptions, per-leaflet light basis and biological applicability; obtain real scale/organ state/absolute PPFD, optical and developmental evidence. Revisit ray convergence for target scenes. Model-code redistribution license is unresolved. No physical or Micro-Tom validation is claimed.

## V3 conditional delivery, 2026-10-11
- [x] Codex: whole-plant native development, 30-day spin-up/65-day continuation, dynamic optics and conditional observation fixture verified. See VTC_WHOLE_PLANT_DEVELOPMENT_EXECUTION_V3_2026-10-11.md. Historical V2 status remains unchanged.
- [ ] Claude/user: review VTC_V3_PENDING_DECISIONS_2026-10-11.md; supply real initialization/absolute light/optical evidence. No independent Micro-Tom validation.
- [x] Codex: completed queued staged P1-consumer/P2/P4/P3 conditional native integration. Actual delivered P1 truth route: four instances, three intervals, 250 -> 294 organs. Final acceptance verifies 16 native runs / 31 intervals; earlier broad regression 288 passed, final affected regression 102 passed (overlapping counts). See CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md and build/fsp_integration_20261011_delivery/acceptance.json.
- [ ] Claude/user: resolve real P1 readiness (117 captures: scale/timezone; 13 plants: optical surfaces), hidden physiology and absolute-light/optics evidence; review imported geometry/time discretization choices in VTC_V3_PENDING_DECISIONS_2026-10-11.md. Conditional execution is not real prediction validation.
- [ ] Claude Code (S2): consume the single native/pipeline authority for the separately assigned forecast wrapper. `advance_interval`/`commit_step` publish already-produced native checkpoints; do not apply another growth update. Nutrient-growth and assimilation require separate reviewed contracts.

## Native extensions and declared side axes, 2026-10-12

- [x] Codex: delivered declared M/S1 axes, explicit parent/registration/hidden-state contracts, independent apices, shared plant carbon, capped weighted demand allocation and axis-aware immutable ledgers. See P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md and P4_SIDESHOOT_EXECUTION_2026-10-12.md. Nine native runs / 29 intervals; no emergence or biological validation claim.
- [x] Codex: delivered bounded observation intake, native optical materials/static objects, aware schedules and H1-H3 hooks. Final combined focused suite: 193 unique passing tests; independent consolidation: 30 native runs / 150 intervals, plus an actual H3-enabled forecast-wrapper invocation. See CODEX_FSP_EIGHT_CAPABILITIES_EXECUTION_2026-10-11.md.
- [ ] Claude/user: E2 complete terminal photon closure, E6 developmental imported deformation and E7 causal nutrient coupling remain unavailable. Review the appended VTC_V3_PENDING_DECISIONS_2026-10-11.md entries; full eight-capability request must not be marked complete.
- [ ] P1/P3 owners: reconcile A4 and the actual axes exporter with fsp-axes-1, then add side-axis forwarding/evaluation to the forecast layer. Explicit side fixtures are ready; no actual P1 side export is claimed. Current real audit has 130 producer gaps (117 scale, 13 optical); timezone gaps were resolved by the separate P1 owner.
- [ ] Active P1 flow-map owner: merge handoff/FSP_EXTENSION_SIDESHOOT_FLOW_ROWS_2026-10-12.csv and apply its companion update instructions. Codex has not concurrently rewritten the claimed shared file.

- [x] Codex final A4 addendum: reconciled CompoundLeaf axil representation, 23 axis cases rerun (two new), one additional native two-interval fixture. Final 195 unique focused passing tests; 31 native runs / 152 intervals, side-axis subset 10 / 31. Earlier counts above are historical subsets. A4 interpretation is resolved; actual P1 producer package and P3 consumer work remain pending.

## P4 substem trusses and A5 final delivery, 2026-10-12
- [x] Codex: delivered conditional per-axis truss/stop behavior and explicit segment round-trip; 219 unique focused tests; seven native runs/fifteen intervals at 4.8M rays. See P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md.
- [x] P1/P4 A4/A5 exchange and actual producer fixture interoperability are now verified, superseding the earlier pending fixture-exchange entries. Explicit fixture_truth route remains distinct from snapshot reconstruction and real data. Earlier FSP_EXTENSION_SIDESHOOT flow rows were already merged by P1.
- [ ] P1 flow-map owner: upsert this task's twelve rows from P4_SUBSTEM_TRUSS_FLOW_ROWS_2026-10-12.csv by path; checker on the existing shared map passes and supplied row paths exist. Codex has not concurrently rewritten the shared map.
- [ ] P3 owner: consume P4 output without a second advance; reconcile earlier no-new-truss wording with the later explicit user authorization. Engine CADENCE remains shared; per-axis timing distributions require an explicit extension.
- [ ] Human/science owner: remaining settings are listed in VTC_V3_PENDING_DECISIONS_2026-10-11.md; real growth accuracy remains untested.

## Codex -> P2/flow owner: application review, 2026-10-13
- [ ] Review FLOW_P2_LAMP_APPLICATION_REVIEW_2026-10-13.md before lamp calibration: reflective fitting and sensor bounce attribution are missing; reference_dli simulated execution is deferred; directional AreaLight vs V3 PointLight and photon/W conventions need an explicit adapter. All sixteen canopy x/y positions are unavailable, so retain conditional comparison/geometry blockers.
- [ ] Flow owner: reconcile README observations/H1-H3/schema/F8 claims and duplicate absent-versus-executed hook rows; retain H4 as blocked and distinguish real reconstruction from P1 fixtures. Checker checks paths only. This review did not modify shared flow files.

## Codex -> Claude: revised P2 lamp prompt review, 2026-10-13
- [ ] Reconcile CODEX_CLI_PROMPT_P2_LAMP_CALIBRATION_2026-10-13.md before execution: section 2 still calls the canopy footprint unknown although section 4c and current records give a user-stated 42 x 28 cm extent with derived coordinates. Agreement across orientation variants alone cannot establish a definitive matched validation while plant geometry, approximate placement and meter calibration remain unresolved. Section 4b must not imply enclosure geometry is complete: wall extents/ceiling location and lamp dimensions/placement/beam are still absent. Section L4 must retain the approximately 60% analytic diffuse term as a model-dependent estimate, not a pass/fail truth. Reconcile 14 h measurement-summary DLI with this chat's confirmed 16 h/full output, and distinguish the recorded 300 mm setup from the older provisional 400 mm setup. Preserve conditional outputs and missing-input provenance; no prompt/source/data edits or calibration performed during this review.

## Codex -> Claude / user: P2 calibration implementation delivery, 2026-10-13
- [x] Native conditional lamp fitter, fixed split/variant/source/code hashes, independent direct/raw transport controls, frozen field export and reference-DLI consumer implemented. Focused suite 225 passed; 42 finalized native calibration/control jobs plus four independent-seed synthetic observation jobs. See P2_LAMP_CALIBRATION_EXECUTION_2026-10-13.md and its Korean companion.
- [x] This task's user resolved operating conditions: 300 mm above board, 14 h/day, full output, 50 mm edge clearances. Keep old 400 mm/16 h records as historical scenarios. Current canopy extent is user-stated and coordinates derived; old unavailable-coordinate queue text is historical.
- [ ] Human/science owner: supply emitting surface dimensions/centres/beam, wall/ceiling extents, sensor geometry/calibration, frozen grid variants and canopy scene correspondence before real calibration. Declare bounds/time support; no physical optical accuracy or parameter interval is established. Synthetic reflectance reached upper bound 0.8 despite truth 0.4; do not treat low residual as identification.
- [ ] Active flow owner: upsert P2_LAMP_CALIBRATION_FLOW_ROWS_2026-10-13.csv by path while preserving existing duplicate-purpose rows, then run check_flow.py --md. Current and proposed status renders are under build/p2_lamp_calibration_20261013_01; current map has 146 rows/zero missing paths. Codex did not overwrite the active F9 flow claim.

## Codex -> Claude: empirical light-field prompt review, 2026-10-13
- [ ] Clarify E1/E3 boundary semantics before per-leaf shading: rim measurements were taken without plants, canopy measurements with plants. Interpolating these as one unoccluded incident field and applying canopy shading again can double-count an unknown observed plant effect. Preserve observation conditions and require an explicit reviewed rule; do not silently remove/invert the effect or assume the canopy sensors were all unoccluded.
- [ ] Specify supported interpolation region from actual sample-centre support, not tray edge area. Current derived canopy centres span x=122.5..437.5 and y=105..315 mm for the recorded variant (31.5 x 21 cm), narrower than the declared 42 x 28 cm tray block. Freeze corner/orientation variants; do not extrapolate at tray edges or below z=70 / above z=150 mm. Both planes must support an intermediate-height query under the selected interpolation method.
- [ ] E2/E4: lamp placement/orientation remain unavailable in the latest record; emitting width also unknown. Geometry-based directions require explicit placement scenarios; hashing an unknown configuration field only detects later recorded changes, not unrecorded physical movement. Keep the 50/60/70% diffuse fractions user_assumed, not fitted, and the approximately 60% reflection narrative an unverified estimate. Failure of the sparse coarse synthetic recovery alone is not a proof of structural non-identifiability.
- [ ] E5: existing frozen-reference-ppfd-1 enforces fitted source_kind and simulated DLI. Add a versioned empirical route with derived interpolation provenance and independent configuration/support validation; do not relabel an existing fitted/simulated package or alter its historical semantics. Review requested document only; no new fitting, wall-covering experiment, forecast or empirical implementation executed in this turn.

## User clarification superseding the overhead-leaf concern, 2026-10-13
- [x] User explicitly states there are no plants above the 150 mm measurement plane. Withdraw the earlier concern about already-counted shading by leaves above that sensor plane. Treat the 15 cm observation as above-canopy horizontal incident PPFD for the recorded setup. Retain plants-present-below metadata; do not relabel the whole acquisition as empty-board. Leaf interception/shading below this boundary remains a separate model calculation; no directional distribution was measured by this clarification. The other interpolation-support, coordinate-variant, configuration and provenance requirements remain.

## Codex -> Claude / P2 empirical implementation (2026-10-13)
- [x] E1/E4/E5 software implemented: 46-point bounded field, explicit orientation variants, configuration/source/code hashes, new derived empirical reference-DLI route and independent consumer. Four 19-position packages each retain 17 conditional values and two unsupported-position refusals. No plants above 150 mm per user clarification; below-plane acquisition metadata preserved.
- [x] E2/E3 software implemented and synthetic geometry checked: declared diffuse 0.5/0.6/0.7; existing physical-leaf crossing engine; no wall objects or fitted reflectance; area-weighted per-leaf flux and scenario spread. Real lamp pose and reviewed leaf surfaces remain unavailable. No growth forecast or optical accuracy claim.
- [x] E6 accepted remeasurement consequence appended to VTC_V3_PENDING_DECISIONS_2026-10-11.md. Old fitting TODOs are historical; lamp/wall fitting and wall-covering measurements are no longer the target. Missing wall reflectance is not a blocker for empirical scalar field interpolation.
- [ ] Real-input owner: confirm grid origin/corner/axis and approximate tray placement; supply registered reviewed leaf surfaces and explicit lamp centre-line placement for real per-leaf use; characterize the PPFD meter for physical validation. No crop calibration or biological prediction is established.
- [ ] Active flow owner: upsert P2_EMPIRICAL_LIGHT_FIELD_FLOW_ROWS_2026-10-13.csv into the canonical flow map when the shared claim is released. Existing checker --md ran on a proposed snapshot (164 rows, zero missing paths) in build/p2_empirical_light_field_20261013_01/proposed_flow; canonical shared files were preserved.

## Codex -> Claude: tray solution contract and science insertion gates (2026-10-13)

- [x] Implemented independent tray EC-equivalent records ingest, bound residual accounting, prescribed bidirectional medium transfers, modelled plant split and fixture-only idempotent joint publication. The user explicitly requested completing this without missing science values. See P4_NUTRIENT_RESERVOIR_CONTRACT_2026-10-12.md and tools/NUTRIENT_RESERVOIR.md. Feedback stays false; flow and legacy ledgers untouched.
- [ ] Scientific owner: fill exact EC input/time/temperature definition, deficiency/high-EC equations/domain/breakpoints and separate none/moderate/strong parameter records, initial medium/stored states, exchange law, blank comparability/scaling and uncertainty. Required registry template and insertion API are delivered; no coefficients or initial zeros selected.
- [ ] Scientific owner: reconcile the original sink-only bias claim. With U=I-O-deltaD-A+R and fixed observed deltaD, omitting release R underestimates U. EC rise alone identifies neither stored amount nor a release rate. Blank evaporation overestimation biases inferred plant water uptake downward. These signs are exercised by explicit arithmetic fixtures.
- [ ] Native owner: future factor must be applied once to gross assimilation before allocation with a genuine native proposal/pause/finalize and single committed predecessor. The new transaction adapter is expressly fixture-only; it is not native coupling or a global debit service. The native owner was contacted under the continuation instruction.
- [x] User clarification recorded: standing tray solution is usually about 400 mL (user_stated approximate). Preserve as typical-volume metadata only; do not substitute for measured interval stocks, event supply, medium water or tray capacity.

## Codex -> P1/P2/P4/science owners: native boundary continuation, 2026-10-13
- [x] Revision7 plane/frame/completion intake; default-off actual-geometry-bound absorbed leaflet light handshake; anchor identity/geometry validation; resource readiness gate and exact future causal transaction envelope. See NATIVE_BOUNDARY_CONTRACT_2026-10-13.md and NATIVE_CONTINUATION_EXECUTION_2026-10-13.md for final verification disposition.
- [ ] P1: deliver reviewed real located surfaces and a versioned completion manifest with confirmed source identity links. Improved rim scale is not 3-D geometry; real package remains unavailable for native initialization.
- [ ] P2/science: review incident-to-absorbed and NRH basis before real incoming-light growth; empirical_native_response is separately owned. Current native engineering fixture is not empirical validation. External material/schedule combinations remain explicitly unsupported.
- [ ] Shape science: exact imported developmental law, supported anchor semantics and mass/area constraint remain missing (E6).
- [ ] Reservoir/science/native: define executable exchange/f_nut law and implement scratch proposal/pause/joint-finalize before enabling feedback (E7). Retrospective proposals and already-generated states must not become constraints. EC-equivalent is not element-resolved optimization.
- [ ] Active flow owner: reconcile NATIVE_CONTINUATION_FLOW_ROWS_2026-10-13.md after shared ownership coordination; this task must not modify flow/.

## Codex -> Claude / native owner: empirical growth boundary delivery, 2026-10-13
- [x] Versioned physical-leaf/interval empirical export, source/configuration/geometry/namespace/registration binding, explicit transport and absorption contract, independent area/schedule consumer and actual-native response adapter delivered. Focused regression: 86 passed. See P2_EMPIRICAL_GROWTH_BOUNDARY_EXECUTION_2026-10-13.md and P2_EMPIRICAL_NATIVE_HOOK_2026-10-13.md.
- [x] Actual native light-only consumption verified in three fresh 0.5/0.6/0.7 diffuse-scenario runs, 45 engineering triangle leaves each, 135 leaf-interval comparisons; native/supplied absorbed flux error zero, external_once audit, unchanged mass/age/area and zero gross carbon. Original P1 geometry was explicitly replaced only in fresh fixture inputs; no real or biological accuracy claim. Evidence: build/p2_empirical_growth_boundary_20261013_01/delivery_verification.json. Prior driver failure/timeout retained.
- [ ] Science/input owner: review the explicit local empirical-field interpretation and provide reviewed optical surfaces, observed lamp pose, registration, absorptance, meter calibration and NRH source-basis mapping. User observation of no plants above 150 mm applies to measurement time only; unsupported later geometry must be rejected. Real growth remains gated.
- [ ] Native owner: repeated-hit incidence and terminal escape/cutoff need the exact instrumentation contract in P2_EMPIRICAL_NATIVE_HOOK_2026-10-13.md; aggregate getters cannot reconstruct the missing events. Growth-mode NRH/state advancement and repeated changing native geometries are not established by this task's light-only evidence. Do not invent an escape remainder or bypass the 500M pair limit for the original detailed mesh.

## Codex -> native owner: verified timeout reporting defect (2026-10-13)
- [ ] P2 software defect: boundary timeout_s=1 produced no accepted future state, but the GroIMP CLI did not log the IllegalStateException substring expected by vtc_growth_bridge.py:99. Runner waited 180.2084 s then raised generic GroIMP timeout. See NATIVE_VERIFICATION_2026-10-13.md and build/native_verification_20261013_01/timeout_finding.json. Add reliable request-bound terminal error propagation/deadline monitoring after the active Claude F10 stable-engine run; retain zero future publication and re-test. Engine left unchanged during verification.
