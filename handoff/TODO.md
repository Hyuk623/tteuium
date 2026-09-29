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
