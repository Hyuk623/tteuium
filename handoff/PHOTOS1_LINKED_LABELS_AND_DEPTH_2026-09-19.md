# Photos-1 linked photo labels and depth records — 2026-09-19

## User scope

The user requested labeled photographs alongside reconstruction. Deep learning and Kaggle remain deferred. Work uses the existing 18 plant photographs, not 18 different plants. Source/core/config files are unchanged.

## Delivered

- Latest standalone viewer: `build/photos1_manual3d_20260919/preview05/index.html` (all images embedded; can open offline).
- Leaf selection links the partial 3D candidate and its manually labeled source photographs. The selected leaf uses an original-resolution crop; full-photo view and labeled JPEG links remain available. Full-size gallery retains all 18 frame statuses.
- Six partial leaf patches, 38 vertices, 26 triangles. A2/B1/B2 candidate landmarks were revised by independent visual inspection, not projection-error fitting. A1/B3/C1 retain explicit correspondence-revision warnings. Maximum leaf residuals remain 15.59–40.94 px; these are not validated meshes or PPFD-ready geometry.
- Four additional small-leaf visible regions on IMG_7924 are retained as C2_2D..C5_2D. Pink outlines identify them; cross-view identity and depth remain unavailable. Their polygon indices are not physical landmarks and never enter triangulation. Export is separate: `visible_fragments.candidate.csv`.
- The optional reference board uses the configured board and only the core `sheet_to_board_mm` conversion. Reference marker rectangles depict the configured layout, not claimed per-photo marker detections.
- New depth export: `build/photos1_manual3d_20260919/depth_records02/`. Contains 76 manual observations, 38 landmarks, all 18 frame statuses, and six vertex-height summaries. Board height, camera optical-axis depth and Euclidean camera range are separate. Failed pose/point gates and source hashes persist. Every result is metric-unvalidated; missing detector IDs remain unavailable.

## Code and validation

Root changes: `tools/manual_leaf_preview.py`, `tools/manual_leaf_preview.html`.
New exporter/tests: `tools/leaf_depth_records.py`, `tools/tests/test_leaf_depth_records.py`, `tools/tests/test_manual_leaf_preview_fragments.py`.

23 targeted tests passed with:

```powershell
python -m pytest -q tools/tests/test_manual_leaf_preview.py tools/tests/test_manual_leaf_preview_fragments.py tools/tests/test_leaf_depth_records.py
```

Actual preview and depth CLIs completed. Browser verified selected 2D leaf -> IMG_7924 with no depth, selected 3D leaf -> only its two labeled source images, full-resolution crop, and the optional board display. Original working-photo hashes verified by both builders. No learned model ran.

Reproduce:

```powershell
python -m tools.manual_leaf_preview --capture build/photos1_manual3d_20260919/capture.preview.json --annotations build/photos1_manual3d_20260919/manual_candidates.review02.json --out build/photos1_manual3d_20260919/preview_new
python -m tools.leaf_depth_records --capture build/photos1_manual3d_20260919/capture.preview.json --preview build/photos1_manual3d_20260919/preview_new/preview.json --points build/photos1_manual3d_20260919/preview_new/points.candidate.csv --out build/photos1_manual3d_20260919/depth_new
```

## Remaining work

Whole-plant leaf reconstruction, reliable cross-view physical correspondences, small-leaf depth, and metric validation remain incomplete. The viewer is a review artifact, not evidence of the full research goal being achieved. Current annotation candidates are assistant-proposed, not user-approved labels or training ground truth. No hidden leaf/stem/petiole geometry was invented. No configuration or operational gate was relaxed.
