# Reviewed partial leaf surface and observation records

Implement the user-approved plan in the existing lab: optional boundary landmarks and explicit visible-boundary confirmation, original-pixel review, immutable point/surface outputs, existing triangulation and surface bridge, rotatable diagnostic geometry and image reprojections. Start with dwt_01 annotations 127/167; retain xv_001/xv_002 for three-view review. Never fabricate human point decisions. Preserve the original camera capture; do not import rescued poses automatically.

Prepare a fresh derived snapshot with verified original data and a new context. Preserve earlier results and review histories. Reports must distinguish unavailable points, points-only results and interpolated partial surfaces. No training, PPFD readiness, measured area or true curvature claim is authorized.

Reuse existing flowering/light CSV contracts; add capture and lighting schedule records, Korean instructions and a non-mutating validator. PPFD is unmeasured because no sensor is available. Separate historical geometry from prospective observations. Leave unknown values blank and do not derive measured DLI from dimmer settings.

Validation covers boundary identity/order conflicts, original coordinates, holes/components, missing/failed geometry, stale results, source preservation, CSV IDs/dates/units/duplicates/photos and censored flowering. Real pilot completion may be a precise unavailable result if no human-confirmed physical landmarks exist. Actual results will be appended after testing.

## Delivery — 2026-10-02

The existing lab at http://127.0.0.1:8834/?annotation=127 serves `build/leaf_surface_pilot_20261001`. Select annotation 167 as the comparison and open the pair. No separate annotation application was introduced.

### Implemented

- Independent outer-boundary proposals, interior/boundary point kinds, original-pixel coordinates, physical point IDs and persistent boundary order. Boundary acceptance explicitly requires confirmation of an actual visible leaf edge. Hole contours are excluded from proposals; possible occlusion edges remain for human review. Contour vertex IDs never establish correspondence.
- Existing move, pending, reject, delete, undo and explicit-save controls preserve history. Older records default to interior points. Duplicate boundary orders and conflicting point roles across views are rejected.
- Authenticated local APIs `POST /api/vein/surface` and `/api/vein/surface-results` reuse the existing token, lock, triangulation and surface bridge. Each calculation creates a new export and surface run.
- At least three noncollinear triangulated boundary points, continuous boundary order, a triangulated interior point and two eligible visible-mask observations are required. Crossed/repeated boundaries and disconnected evidence are rejected. Full projected triangle footprints must stay inside the visible masks; holes remain excluded and removal reasons are retained.
- Rotatable 3D points/triangles and full-photo reprojections appear in the same page. Interpolated faces and observed-point evidence have different colours. Unused identity-confirmed views show held-out reprojections, without an error claim if independent clicks are missing. Adding a third view creates a separate result.
- Source/settings/review changes mark dependent runs stale. Saved history remains viewable when changed inputs prevent recomputation. All surfaces retain `validated_metric=false` and `suitable_for_ppfd=false`.

Files: `tools/vein_boundary.py`, `tools/leaf_surface_review.py`, `tools/leaf_surface_review.js`, `tools/vein_correspondence.py`, `tools/vein_review.js`, `tools/vein_surface_bridge.py`, `tools/leaf_preprocess_lab.py`, `tools/leaf_preprocess_lab.html`, `tools/observation_records.py`; new tests `tools/tests/test_leaf_surface_review.py`, `tools/tests/test_observation_records.py` and extended `tools/tests/test_vein_landmarks.py`.

### Real pilot status

`build/leaf_surface_pilot_20261001/readiness.json` records:

| Leaflet | Annotation IDs | Actual result |
|---|---|---|
| xv_004 | 127 / 167 | no_human_confirmed_points; 0 points, 0 faces |
| xv_001 | 99 / 121 / 172 | no_human_confirmed_points; 0 points, 0 faces |
| xv_002 | 88 / 113 / 181 | no_human_confirmed_points; 0 points, 0 faces |

Physical leaflet identity is available; physical landmark confirmation is not. Codex saved no real human review or fabricated point. The first pair's original poses still fail the pose gate. Start human review with 3–5 clear vein landmarks and visible boundary features. Use boundary order 0,1,... consistently across views; never invent hidden observations. Save the review before supplying the reviewer and mask attestation for surface calculation.

`source_preservation_audit.json` verifies 317 context hashes, 284 dataset hashes, all 268 loaded observations and 536 unchanged crop/mask files. Dataset JSON is unchanged. Snapshot preparation recorded a changed `tools/plant_pipeline_plants.json` dependency but preserved the original capture exactly: SHA-256 `a165d5914a98b61aec787d6d34bc4e6688ca76da749a495b10cd0510a22af2c3`. No rescued-marker poses were imported. Earlier context/history is archived without re-attestation; the prior vein gallery was copied for viewing.

### Observation CSVs

Blank templates: `build/observation_records_20261001/`; Korean guide: `작성안내.txt`. Read-only initial audit: `build/observation_records_audit_20261001/validation.json` and `issues.csv`.

Nine header-only CSVs: plants, captures, lighting, growth, flower_visits, light_timeseries, sensors, ppfd_readings and area_evidence. They reuse existing flowering/sensor contracts. Initial validation is valid with warnings for no actual observations and unmeasured PPFD. Measured DLI remains unavailable.

`leaf_count` means compound leaves. Dimmer percentage, measured W and PPFD are distinct. Diagnostic area is not independent leaf-area measurement. Validation reports ID/date/unit/duplicate/photo errors and flowering contradictions, including missed visits, interval/right censoring and already-open plants, without changing any user record.

### Validation and use

83 targeted regression tests passed in 13.78 s. One additional third-view/history test passed in 2.31 s after correcting its Windows UTF-8 file read. Node syntax checks passed. Browser testing caught and fixed a missing point-kind control. The final UI loads boundary mode and real unavailable records; a synthetic fixture displayed five points, four triangles, rotation and reprojection without console errors. Exclude `build/leaf_surface_ui_fixture_20261002/` from all research; its temporary server was stopped. The real review UI remains open. Screenshot: `build/leaf_surface_pilot_20261001/review_ui.jpg`.

```powershell
python -m tools.leaf_preprocess_lab serve --run build/leaf_surface_pilot_20261001 --port 8834
python -m tools.observation_records --input build/observation_records_20261001 --out build/observation_records_audit_NEW
python -m tools.observation_records --templates --out build/observation_records_NEW
python -m tools.leaf_surface_review --snapshot-from build/leaf_veins_dwt01_20260930 --out build/leaf_surface_pilot_NEW
python -m pytest tools/tests/test_leaf_surface_review.py tools/tests/test_observation_records.py tools/tests/test_vein_landmarks.py tools/tests/test_leaf_preprocess_lab.py tools/tests/test_midrib_review.py tools/tests/test_leaf_vein_batch.py -q
```

Use fresh output paths. Do not overwrite snapshots or CSV records. No training, real leaf surface, validated dimensions, PPFD readiness, density optimum or flowering-prediction accuracy is claimed. Remaining work is human correspondence review, independent geometric validation and prospective measurements.

### Completion audit continuation
The requirement audit adds direct end-to-end regression evidence for collinear boundaries and disconnected masks, complementing the existing helper/hole tests. No real point review or camera setting will be changed.

Completion audit passed on 2026-10-02. Added end-to-end collinear-boundary and disconnected-mask tests; all 16 surface tests passed in 6.17 s (XML in the pilot directory). Requirement/evidence matrix: build/leaf_surface_pilot_20261001/completion_audit_20261002.json. All three real unavailable runs are current; no confirmed points or CSV observations were invented. The plan's explicit result-or-unavailable completion condition is satisfied; actual biological/metric validation remains pending human observation.

## User-requested assistant correspondence search — 2026-10-02
Inspect original crops and accepted masks for 127/167, then clearer already-linked pilot views if necessary. Save assistant-selected physical landmark hypotheses as pending with explicit assistant provenance, never as human confirmations. Preserve existing reviews; inspect geometric diagnostics only as supporting evidence, without changing quality gates or generating a confirmed surface.


Assistant search delivered seven pending pairs (127/167: four; 99/121: three), zero confirmed points and no new surface. Method, exact coordinates, source integrity and limitations are recorded in CLAUDE_ASSISTANT_LANDMARK_SEARCH_METHOD_2026-10-02.md and build/leaf_surface_pilot_20261001/assistant_search_20261002. Existing workflow readback passed; final browser row display remains unverified after a tab-binding interruption.
