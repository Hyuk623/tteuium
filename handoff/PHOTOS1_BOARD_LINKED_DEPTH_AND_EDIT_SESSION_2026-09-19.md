# Photos-1 board-linked depth and local label editing — 2026-09-19

## Scope and current result

Continue the existing 18 photographs of one plant. Deep learning/Kaggle remain deferred. The user asked to see labeled photographs alongside reconstruction and asked whether the work was finished. Whole-plant reconstruction is **not finished**. The outputs below are assistant-proposed, unreviewed diagnostic candidates, not training ground truth or validated PPFD inputs.

Latest outputs:

- `build/photos1_manual3d_20260919/preview09/index.html`: self-contained 3D candidate/photo-label viewer.
- `build/photos1_manual3d_20260919/manual_candidates.review05.json`: current annotation candidates.
- `build/photos1_manual3d_20260919/depth_records05/`: 74 manual observations, 37 landmarks, 18 frame records, seven leaf records.
- `build/photos1_manual3d_20260919/board_evidence01/`: actual per-photo detections and enriched capture.
- `build/photos1_manual3d_20260919/edit_session01/`: local editor, all 18 original-resolution working PNGs, and five editable coarse leaf candidates.

Seven coarse/partial 3D candidates remain: A1, A2, B1, B2, B3, D1, D2. Five candidates have only 2D labels: C1 and C2_2D through C5_2D. A1 is now a three-landmark observed patch; D2 is also explicitly partial. C1's former mesh is no longer supported by visual review: its independent polygons in IMG_7916/7924 remain visible, but do not enter physical-point triangulation. Old source versions are preserved. The final A1 candidate uses IMG_7919 pixels (402,655), (444,642), (428,683) and IMG_7927 pixels (330,585), (392,558), (364,606) on the 1500-pixel labeling images; CSVs scale these to the original 3024-pixel photographs.

All metric validity flags remain false. Seventeen raw camera poses exist, zero pass the existing pose gate, and IMG_7910 remains failed. No calibration, pose, quality threshold, core, config, or design file was changed. Lower fit residuals on individual patches do not validate scale or shape.

## Actual board evidence and depth records

`tools/charuco_capture_evidence.py` uses the existing ChArUco detector and board conversion. It records 181 marker observations (724 marker vertices) and 166 inner-corner observations across all 18 photos. It adds evidence without re-estimating poses or intrinsics. Original capture fields and quality flags were independently compared and preserved; small residual differences are numerical recomputation only.

`tools/leaf_depth_records.py` joins actual detected IDs to the exact photograph by hash, checks board-spec provenance, distinguishes unavailable evidence from a detected empty set, and retains partial-outline and correspondence status. Board XYZ, camera optical-axis Z, and Euclidean camera range are separate fields. They are not interchangeable with leaf length.

The viewer shows actual detected marker/corner overlays, selected-leaf original-resolution crops, physical landmark numbers, source-photo choices, and depth-table/3D-point linking. Multi-view 2D polygons may have different vertex counts and never become physical correspondences. Partial observed patches have a separate boundary export rather than a complete-contour export.

## Editable local session

`tools/leaf_point_annotator.html` now preserves diagnostic capture quality, hashes, board evidence and annotation provenance through backup/restore and identity edits. Raw failed-quality poses can supply diagnostic guides but cannot make labels metric-ready or green/validated. Partial patches cannot be silently exported as complete contours. Desktop photo stages keep a 420-pixel minimum; a bounded workspace and internally scrolling sidebar prevent both collapsed images and excessive blank canvas height.

`tools/prepare_leaf_edit_session.py` copies verified working images and prepares a local-only editor. Loading requires the visible button; existing browser work is never replaced by seed labels. Prepared HTML disables the Claude cloud initialization hook and restricts network connections to its own origin. No model or external upload runs.

The five editable seeds are A2, B1, B2, B3 and D1. The bundle was generated from review04; exact comparison confirms these five candidates are unchanged in review05. A1/D2 partial patches and 2D-only regions are preserved in provenance, but are not loaded into the complete-outline editing workflow. The viewer remains their inspection surface. Two HTML-only layout refreshes are recorded in `session_report.json`; copied images and the seed hash were unchanged. Existing browser edits were preserved during reload testing. The editor does not yet automatically rebuild preview09 after a user edit.

## Verification

44 targeted pytest items passed, including the annotator's 26 Node regression cases and the prepared-session bootstrap checks:

```powershell
python -m pytest -q tools/tests/test_manual_leaf_preview.py tools/tests/test_manual_leaf_preview_fragments.py tools/tests/test_manual_leaf_preview_partial.py tools/tests/test_leaf_depth_records.py tools/tests/test_charuco_capture_evidence.py tools/tests/test_leaf_annotator.py tools/tests/test_prepare_leaf_edit_session.py
```

Actual builders completed. An independent artifact audit verified all 74 original-pixel observations against review05, 37 PLY vertices, all 18 labeled JPEGs, actual board-ID joins, C1's exclusion from geometry, and unchanged editable seeds. Browser inspection verified latest 7/5 counts, A1 partial labeling/depth, C1's two selectable photos with no depth, board overlays, and the editor's 18-photo loading/preserved edits. Source CSS changed after the tests; no JavaScript changed in those final layout edits.

Reproduction from the project root (choose unused output folders):

```powershell
python -m tools.charuco_capture_evidence --capture build/photos1_manual3d_20260919/capture.preview.json --out build/photos1_manual3d_20260919/board_evidence_new --overlays
python -m tools.manual_leaf_preview --capture build/photos1_manual3d_20260919/board_evidence01/capture.board_evidence.json --annotations build/photos1_manual3d_20260919/manual_candidates.review05.json --out build/photos1_manual3d_20260919/preview_new
python -m tools.leaf_depth_records --capture build/photos1_manual3d_20260919/board_evidence01/capture.board_evidence.json --preview build/photos1_manual3d_20260919/preview_new/preview.json --points build/photos1_manual3d_20260919/preview_new/points.candidate.csv --out build/photos1_manual3d_20260919/depth_new
python -m tools.prepare_leaf_edit_session --capture build/photos1_manual3d_20260919/board_evidence01/capture.board_evidence.json --annotations build/photos1_manual3d_20260919/manual_candidates.review05.json --out build/photos1_manual3d_20260919/edit_session_new
python -m http.server 8821 --bind 127.0.0.1 --directory build/photos1_manual3d_20260919/edit_session01
```

## Remaining work

Review B3's ambiguous boundaries and all candidate physical identities. Label remaining visible leaflets and observed stem/petiole topology; do not fabricate hidden surfaces. Determine additional supported correspondences for 2D-only regions. Connect edited backups to a new explicitly versioned diagnostic reconstruction. Whole-plant coverage and metric validation remain incomplete. The D2 unresolved-observation entry includes its historical pre-reconstruction depth note; current numeric candidate depth is in the unvalidated geometry/depth tables, not a validated measurement.

Final desktop DOM check at 1270x708 measured both photo stages at 440.21 pixels high (458.5 pixels wide), replacing the original approximately 65-pixel collapse. Existing five candidate identities and a previously saved extra point survived reloads.
