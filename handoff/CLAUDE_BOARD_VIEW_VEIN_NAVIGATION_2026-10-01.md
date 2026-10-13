# Board guided photo navigation and vein correspondence handoff

## Purpose and current state

For Claude Code, from Codex, 2026-10-01. The existing Python preprocessing lab now connects whole-photo board inspection to leaflet selection and the existing vein correspondence workflow. This is implemented functionality, not a request to build a separate application.

The user supplied `C:/Users/sho36/Downloads/제목 없음 17 (1).pdf`, a one-page diagram linking photographs 21/22/23 and 11/12/13 through marked board locations and leaves, with approximate 45-degree rotation notes. Codex interpreted it as navigation guidance. The user authorized direct implementation without a handoff first, then explicitly requested this handoff afterward.

Current flow:

```text
Choose a reference leaflet
  -> inspect its whole photo and detected board markers
  -> select a comparison photo by capture number or measured viewing direction
  -> inspect shared marker IDs and leaflet work areas
  -> search leaflet candidates within that photo
  -> open the existing side-by-side vein junction review
  -> confirm physical leaflet identity and physical point identity separately
  -> explicitly save and request existing strict or diagnostic triangulation
```

Board correspondence, physical leaflet identity and physical landmark identity remain distinct. This addition does not automatically establish any biological identity or depth.

## Files and interfaces

| File | Change |
|---|---|
| `tools/vein_view_guide.py` | Read-only photo guide, hash-matched board evidence, measured direction comparison and whole-photo previews. |
| `tools/vein_review.js` | Photo navigation, sorting, previous/next controls, full-photo previews, photo-scoped leaflet selection and candidate search. |
| `tools/vein_correspondence.py` | Optional `image_file` filter on `Workflow.candidates`; existing unfiltered callers remain compatible. |
| `tools/leaf_preprocess_lab.py` | Two additional authenticated routes using the existing workflow and lock. |
| `tools/tests/test_vein_landmarks.py` | Navigation, measured-angle, evidence-hash, source-preservation and HTTP integration checks. |

New POST routes use the existing local server token:

- `/api/vein/view-guide`, body `{ "a": "sample_094" }`: photo list, sample IDs, capture view labels, marker IDs, shared marker IDs, pose availability, quality state and nullable board-origin viewing angle.
- `/api/vein/photo-preview`, body `{ "a": "sample_094" }`: display image, source photo identity, original dimensions and display scale. It accepts an existing sample ID, not an arbitrary file path.
- `/api/vein/candidates` additionally accepts `image_file`; null retains all-photo search. The existing scoring and human-review rules are unchanged.

## Geometry and display semantics

Photo number ordering is natural filename ordering. It is not a measured rotation sequence. No nominal 45-degree rotation, filename-derived angle, SfM or new pose estimation is used.

When both measured poses exist, the guide calls the existing `Cameras.centre()` and calculates the angle between camera-centre vectors from the board origin:

```text
C = -R.T @ t
angle = acos(dot(Ca / norm(Ca), Cb / norm(Cb))) in degrees
```

This is the separation of observation directions about the board origin, not a recovered turntable rotation, leaf-point triangulation angle or leaf inclination. Missing poses yield null. Failed-quality poses remain explicitly diagnostic. The guide retains `validated_metric=false` and `suitable_for_ppfd=false`.

Detected marker IDs and marker polygons are displayed only when the board-evidence image hash matches the relevant source image hash. Missing or mismatched evidence is unavailable. Shared markers are an inspection aid; their count does not confirm leaf identity or camera-pose quality. IDs are interpreted within the existing capture and configured board context, not across arbitrary board variants.

Preview colors:

- Yellow: selected leaflet crop/work area.
- Purple: other leaflet crop/work areas.
- Cyan `M` labels: actually detected marker polygons and IDs.

The displayed rectangles come from `crop_xyxy_px`. They are work areas with possible padding, not exact leaf contours, newly generated annotation boxes, physical leaf extents or 3D surfaces. Previews are resized to a maximum dimension of 900 pixels for display; original pixels, masks, annotations and stored coordinates remain unchanged. Preview boxes cannot be used as correspondence points.

Capture frames without prepared leaflet observations remain visible with zero labels and cannot be selected for leaflet review. Frames with labels but no solved pose remain selectable for 2D review. Selecting a photo filters the leaflet selector; the existing `두 사진 열기` action opens the selected pair for point review. Navigating photos does not save or confirm observations automatically.

## Verified dataset and behavior

- Existing run: `build/leaf_veins_dwt01_20260930`.
- Dataset: dwt_01, 268 photo-level leaflet observations across 14 photographs. These are not 268 unique biological leaflets.
- All 317 frozen source hashes passed verification after implementation. Original photographs, masks, labels, calibration and weights were preserved.
- The guide lists the existing 18 capture frames, including those without prepared labels.
- Actual browser pilot: annotation 127 in photo 25 versus annotation 167 in photo 28. Common detected markers: 4, 7, 13, 16. Board-origin observation direction difference: approximately 68.5 degrees, diagnostic because pose quality fails the existing gate.
- Restricting search to photo 28 returned 25 candidate observations. Annotation 167 appeared first because the existing confirmed identity is prioritized. This is not evidence of automatic matching accuracy.
- Existing point-review rendering remained operational: 15 junction candidates on label 127 and 64 on label 167, with Otsu thresholds approximately 0.290 and 0.310. No candidate was accepted as anatomical truth by Codex.
- Browser verification covered photo filtering, measured-direction sorting, whole-photo previews, shared-marker text, scoped search and transition into the existing pair viewer. No browser console errors were returned.
- Zero new human vein-review records were saved during verification; no new real 3D point or surface result was claimed.

The earlier 7,006-candidate extraction remains a historical derived run described in `CODEX_VEIN_LANDMARK_IMPLEMENTATION_2026-09-30.md`. It was not rerun or overwritten for this navigation addition.

## Run and validation

Run from the existing project directory:

```powershell
python -m tools.leaf_preprocess_lab serve --run build/leaf_veins_dwt01_20260930 --port 8834
```

URL: `http://127.0.0.1:8834/`. At verification, this server was PID 35244; check the current process before any future restart. Other lab servers were preserved.

```powershell
python -m pytest tools/tests/test_vein_landmarks.py tools/tests/test_leaf_preprocess_lab.py tools/tests/test_midrib_review.py tools/tests/test_leaf_vein_batch.py -q
& 'C:/Program Files/nodejs/node.exe' --check tools/vein_review.js
```

Results: **59 tests passed in 8.23 seconds**; Node syntax check passed. New tests verify measured camera geometry rather than nominal angles, null angles for unposed photos, source-hash matching for markers, explicit unavailable-label frames, preview source preservation, changed-source rejection and authenticated photo-filtered API use.

## Continuation and limits

Reuse this photo guide before the existing human correspondence review. Start with the existing 127/167 identity or independently confirmed neighboring views. Shared marker appearance alone must not assign `leaflet_id` or `point_id`. Approximate rotation notes in the PDF must not become geometry inputs.

For the underlying immutable reviews, point-ID reuse, conflict handling, staleness, triangulation gates and optional independently reviewed boundary-to-surface adapter, read `CODEX_VEIN_LANDMARK_IMPLEMENTATION_2026-09-30.md`. Backend code revisions are part of graph/proposal provenance; previously saved point evidence may require review or regeneration after a code change. Do not force old results current or replace their recorded hashes.

No training or deep-learning inference was run. Independent leaflet matching accuracy, vein-point accuracy, true 3D curvature accuracy and PPFD readiness remain unverified. Real anatomical confirmations and independent geometry measurements are the next evidence needed; this navigation feature does not resolve the existing pose-quality failures.
