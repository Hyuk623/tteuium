# Claude Code handoff: current labeling, real SAM inference and partial 3D

## Start here

Continue in `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis` only.
Read the project conventions, latest LOG/TODO entries and this handoff before editing.
The user asked Codex to review and integrate Claude's work, then authorized actual SAM inference
and requested 3D based on it. This document consolidates the resulting state. It is not a claim
that full automatic plant reconstruction or validated PPFD geometry is complete.

Preserve all original photos, browser work, backups, calibration and historical outputs.
Use new output directories under `build/`. Do not change `config/` or `docs/`.
Coordinate edits to shared tools; do not overwrite the additions listed below with older copies.
Dialogue/UI: Korean. Code/comments/handoff: English.

## User's intended workflow

The user wants to draw leaflet bboxes and assign the same leaflet ID across views, then have
the application propose segmentation, correspondences and 3D, asking for correction only
where uncertain. The delete action must be easy to find. Reconstructed leaves/points must
remain linked to the original labeled photos and actual detected ChArUco IDs.

Current implementation reaches interactive segmentation assistance and diagnostic 3D from
EXISTING point correspondences. Reliable automatic physical-point matching is still missing.

## Dataset and calibration

- 18 plant photos of ONE plant, not 18 plants.
- Originals: `C:/Users/sho36/Downloads/Photos-1-001/` (read only).
- Imported PNGs: `build/photos1_3d_20260919/images/IMG_7910.png` through `IMG_7927.png`.
- Original image resolution 3024 × 3024. Preview coordinates must never be saved as original pixels.
- User-confirmed ChArUco: 7 × 5 squares, 38 mm each. Read the actual board config.
- Trial calibration: `build/photo_audit_board_20260919/intrinsics.board_only.trial.json`.
- RMS approximately 9.0644 px; 17 raw solved poses, 0/18 pass the configured 1 px pose gate.
- IMG_7910 has no solved pose. Point-error gate remains 2 px; do not relax gates to claim success.
- User authorized diagnostic work despite calibration quality. All geometry remains unvalidated.
- No SfM or nominal camera angles. Poses come from actual ChArUco detections.
- XYZ uses the existing board frame in mm. Reuse the core sheet-to-board mapping; do not duplicate it.

## Important: two different input histories

### Historical assistant reference

`build/photos1_manual3d_20260919/edited_roundtrip06/` and `edited_roundtrip08/`:
23 physical points, 48 observations across 11 photos, three partial surfaces.
Reproduction uses `edit_session07/` (or the documented earlier prepared session),
`manual_candidates.review09.json`, and the EXPLICIT backup:
`third_view_review10/third_view_revised.backup.json`.
The prepared seed lacks the latest third-view observations. Do not replace the explicit backup with it.

Codex integration check output:
`build/photos1_manual3d_20260919/integrated_review_20260920/`.
All 48 depth CSV rows are identical to roundtrip08; three surfaces; inputs unchanged.

### Current user browser work — latest input for SAM/3D

The browser had additional edits, labels and boxes. These were preserved, NOT replaced by the reference seed.
After loading the photos, Codex clicked the existing rebuild button. Successful run:

`build/photos1_manual3d_20260919/editor_runs/run_20260920_001200_c0ff5c90/`

- Exact submitted snapshot: `editor.backup.json`.
- Snapshot SHA256: `96f1dc556145c3a6e65ed64fd83fd4ff778081cd63df1cf226cc1c0bd15c45e6`.
- Derived output: `result/`.
- 89 point observations, six diagnostic partial surfaces, five leaflet bboxes, zero cuboids.
- `input_files_changed=false`, metric/PPFD validation false.
- All five boxes have unknown visibility and unconfirmed identity review. One also uses unposed IMG_7910.
  Do not automatically mark them full/confirmed to make a cuboid appear.
- Six surfaces do not establish an improvement over the historical three: the input annotations differ.
- An older failed run `run_20260919_233608_d740fd49` has a blank plant ID. It is not the current result.

## Implemented features and Codex integration changes

Claude's completed implementation is documented in:
- `handoff/LEAFLET_BBOX_XYZ_IMPLEMENTATION_2026-09-19.md`
- `handoff/AI_ASSISTED_LEAFLET_LABELING_2026-09-20.md`

It includes leaflet bbox/ID linking and splitting, visibility/review fields, measured-pose cuboid
estimation, point meanings, original-pixel storage, proposal/correction/acceptance, geometry-only
cross-view suggestions, training export and an explicit local rebuild server.

Codex reviewed and integrated it; see `handoff/CODEX_CLAUDE_INTEGRATION_REVIEW_2026-09-20.md`:

1. `tools/leaf_point_annotator.html`
   - Visible one-shot `삭제할 표시 클릭` toolbar button, using existing deletion and undo.
   - Missed clicks do not create points; tool changes cancel deletion mode.
   - In AI outline edit mode, delete targets the draft vertex, never an accepted bbox underneath.
   - Deletion cannot reduce a ring below three vertices. Undo restores the draft.
2. `tools/editor_point_review.py`
   - Optional `accepted_regions` input renders saved 2D outlines in cyan, including hole boundaries.
   - Photo counts/legend distinguish outlines from observed points and 3D surfaces.
3. `tools/rebuild_leaf_edit_session.py`
   - Exports `accepted_regions.json` and passes saved regions to the existing photo gallery.
   - Region vertices never enter triangulation. Unaccepted proposals remain separate.
4. Related tests in `tools/tests/` cover deletion, no overwrite, undo, source coordinates,
   outline pixels, holes and unchanged depth values.

The localhost server was restarted with current source on port 8821, with model backend
`unavailable`. The editor therefore still shows model unavailable until restarted with SAM config.
Actual inference below was run through the same segmenter module in explicit batch commands,
not by silently enabling SAM or importing proposals into the user's browser.

## Real SAM inference: five existing user bboxes

User explicitly approved inference with “ㄱㄱ”. This supersedes the earlier inference prohibition
for the requested trial; training was not authorized or run.

Output: `build/photos1_manual3d_20260919/sam_auto_20260920/`

- `source.backup.json`: exact copy of the current user snapshot above.
- `sam2_config.json`: verified local SAM 2.1 Hiera Tiny, CPU.
- Checkpoint SHA256: `7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`.
- Existing repository/runtime/checkpoint under `build/sam_trial_20260919/`; no new weights downloaded.
- `proposal_00.json` through `proposal_04.json`: original-pixel candidates, prompts and provenance.
- Three candidates per bbox, 15 total; overlays `proposal_XX_candidate_N.jpg`.
- `manifest.json`, `visual_review.json`, `index.html` and the one-off replay script `run.py`.
- No training, upload or accepted-label changes. All candidates remain pending review.

Visual inspection of candidate index 0 for each prompt:

| Proposal | Target | Finding |
|---|---|---|
| 00 | leaf_001 / IMG_7911 | User bbox is on background; returned mask is not a leaf. Correct prompt before reuse. |
| 01 | leaf_002 / IMG_7910 | Approximate leaf outline; attachment/overlap needs review. Camera pose unavailable. |
| 02 | leaf_002 / IMG_7911 | Approximate leaf outline; holes/neighbor boundary need review. |
| 03 | leaf_002 / IMG_7912 | Approximate leaf outline; base needs review. |
| 04 | leaf_002 / IMG_7922 | Approximate side-view outline; base/petiole needs review. |

Model scores are not measured accuracy. The three candidates were retained; no human acceptance is implied.

## SAM-supported partial 3D: what actually happened

The initial four useful masks belong to `leaf_002|unavailable`. Its saved physical points exist
ONLY in IMG_7910, which has no solved pose. Thus these masks and the shared ID do not provide
point depths by themselves.

An exploratory non-learning matcher was tried inside candidate-0 masks:
- SIFT keypoints: 500 (IMG_7911), 293 (IMG_7912), 70 (IMG_7922).
- Mutual Lowe ratio 0.75 matches: 1 / 0 / 0 for the three pairs.
- The only match had maximum reprojection error 68.6086 px vs the unchanged 2 px point gate.
- Zero accepted matches, no new point labels, no camera pose estimation.
- Summary: `three_d/original_leaf002_matching_audit.json`.
This experiment does not implement a production automatic matcher. **leaf_002 remains unconstructed.**

To make supported progress, Codex ran ADDITIONAL SAM inference on the six identities that already
have multi-view point depths. These are not the same five original bbox proposals above.
Prompts are derived from the bounds of existing observed points in posed views. Candidate selection
prefers containment of saved points, then model score; this is heuristic and remains unreviewed.

New support CLI: `tools/sam_supported_leaf_patches.py`.
It reuses `tools/visible_leaf_patch.py` and the existing patch viewer:

1. Read current capture and depth CSV; verify photo hashes.
2. Require at least two posed views, each with at least three existing finite-depth point observations.
3. Run SAM, save every proposal and selected candidate with provenance.
4. Interpolate between EXISTING 3D landmarks, subdivide triangles, and retain only face footprints
   inside the selected masks in the used views. Mask holes remain holes.
5. Report unavailable identities; never invent missing points or depth.
6. Export separate per-leaf PLY/JSON/photo overlays and one combined board-frame viewer/PLY.
   Combining preserves separate components; it does not join leaves or construct a stem.

`tools/visible_leaf_patch.py` now accepts original-pixel mask rings, preserving holes via even-odd
rasterization. Legacy polygon inputs remain supported. Photo overlays draw all ring boundaries.

Output: `build/photos1_manual3d_20260919/sam_auto_20260920/three_d/`

| Identity | Status | Retained triangles |
|---|---|---:|
| compound_A_candidate / A2 | Diagnostic partial patch | 796 |
| compound_B_candidate / B1 | Diagnostic partial patch | 267 |
| compound_B_candidate / B2 | Diagnostic partial patch | 507 |
| compound_B_candidate / B3 | Diagnostic partial patch | 584 |
| compound_D_candidate / D1 | Diagnostic partial patch | 815 |
| leaf_001 / unavailable | Diagnostic partial patch from new point-bounded SAM prompts | 228 |
| leaf_002 / unavailable | Insufficient posed multi-view point observations | 0 |

Total: six separate components, 3,197 retained triangles out of 6,400 proposed triangles,
36 existing landmark candidates represented in the combined view. Triangle count is sampling
density, not measurement accuracy. Some legacy correspondences have unresolved identity/quality
issues; clipping to SAM masks does not validate them.

Key outputs:
- `report.json`: inputs, model and per-identity outcome.
- `proposal_<identity-index>_<view-index>.json`: additional SAM inference and selection evidence.
- `regions_<index>.json`: selected unreviewed mask regions.
- `leaf_0/` through `leaf_5/`: `patch.json`, `visible_patch_mm.ply`, photo overlays, existing viewer.
- `combined.html`, `combined_patch.json`, `combined_patch_mm.ply`.
- `index.html`: success/failure overview and links.

Source depth SHA256 remains `8c262c9ffcadf071d40c9963e3e93ad3c3cbb173f878f37568479237c0ace5fb`.
These new drafts have NOT been merged into accepted browser annotations or the production light model.

## Commands

Python used: `C:/Users/sho36/AppData/Local/Programs/Python/Python313/python.exe`.
Run from the project directory. Use a NEW output path for any repeat.

```powershell
# Existing editor; preserves origin/session browser storage on port 8821.
python -m tools.serve_leaf_edit_session --session build/photos1_manual3d_20260919/edit_session07 --context build/photos1_manual3d_20260919/manual_candidates.review09.json --runs build/photos1_manual3d_20260919/editor_runs --initial-backup build/photos1_manual3d_20260919/third_view_review10/third_view_revised.backup.json --segmenter unavailable

# To enable interactive SAM, replace the final backend argument with:
# --segmenter sam2 --segmenter-config build/photos1_manual3d_20260919/sam_auto_20260920/sam2_config.json
# Check active jobs before restarting the server; do not overwrite browser work.

# Reproduce SAM-supported patches; this RUNS inference, not training.
python -m tools.sam_supported_leaf_patches --result build/photos1_manual3d_20260919/editor_runs/run_20260920_001200_c0ff5c90/result --segmenter-config build/photos1_manual3d_20260919/sam_auto_20260920/sam2_config.json --out build/photos1_manual3d_20260919/sam_patches_NEW_RUN

# Static generated-result viewer (port 8830 was started for this directory).
python -m http.server 8830 --bind 127.0.0.1 --directory build/photos1_manual3d_20260919/sam_auto_20260920
```

URLs, while the corresponding servers run:
- Editor: `http://127.0.0.1:8821/`
- Initial SAM proposals: `http://127.0.0.1:8830/`
- 3D overview: `http://127.0.0.1:8830/three_d/index.html`
- Combined partial 3D: `http://127.0.0.1:8830/three_d/combined.html`

## Verification actually performed

- Integration stage support suite: 150 passed, 1 skipped.
- Subsequent accepted-outline pixel tests: `test_editor_point_review.py`, 5 passed.
- Latest SAM-patch changes: `test_sam_supported_leaf_patches.py` plus
  `test_visible_leaf_patch.py`, 8 passed. These tests mock inference; actual inference is evidenced
  separately by the real saved proposals/manifests above.
- Tested mask holes removing surface, no invented correspondences, missing-geometry reporting,
  observation-supported candidate selection, source preservation and legacy clipping behavior.
- Combined mesh indices/counts checked; depth hash unchanged.
- B1 reprojection overlay visually inspected: green retained surface, magenta SAM boundary,
  yellow observed landmarks remain distinguishable.
- Browser inspected the combined result page and counts. A subsequent screenshot call failed
  because that tab was no longer in the browser session; do not claim a completed interactive
  rotation/screenshot test from that call. The result URL was reopened through the app.
- Core suite was not rerun for the latest support-only patch changes; older Claude core-test counts
  are historical, not fresh evidence for this stage.

## Next work, in priority order

1. Inspect current browser/user labels before any import. Never replace them with the older assistant seed.
2. Review the five original bbox prompts, especially background-targeting leaf_001/IMG_7911.
3. Review same-leaf identity across leaf_002's views and obtain at least three well-separated physical
   correspondences in at least two photos with solved poses. Use ChArUco epipolar guidance to reduce
   search, but do not treat a bbox, centroid, contour index or epipolar line as a known physical point.
4. Improve the assisted point-matching workflow with explicit uncertain/reject states. The SIFT trial
   failed; do not report it as successful automatic reconstruction.
5. Integrate the new batch outputs into the editor as OPTIONAL drafts/review artifacts if requested;
   currently they are support-tool outputs using the existing viewer. Preserve manual acceptance,
   source snapshot and per-view provenance.
6. Inspect segmentation/landmark mismatches before accepting any of the six partial surfaces. These
   are clipped approximations, not measured full-leaf curvature, thickness, area or complete plant geometry.
7. Resolve calibration/pose accuracy before dimensional or PPFD validation. No cuboid is a leaf
   surface or optical occluder. Growth prediction/training remain outside the completed scope.

Do not claim that bbox + same ID alone currently produces reliable full 3D. The working result is
**SAM-constrained partial surfaces from existing, unvalidated multi-view landmark depths**.
