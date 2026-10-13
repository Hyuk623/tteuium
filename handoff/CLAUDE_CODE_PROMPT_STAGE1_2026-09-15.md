# Claude Code Prompt — Stage 1 Scaffold + Capture/Calibration

Paste everything between the `--- BEGIN PROMPT ---` and `--- END PROMPT ---` lines into Claude Code.

---

--- BEGIN PROMPT ---

You are implementing the capture and calibration stage of a tomato 3D phenotyping pipeline.
Read this whole brief before writing any code. Do not deviate from the file names, variable names,
units, or schemas given here — downstream stages depend on them exactly as written.

## 1. What the system does

A dwarf cherry tomato plant sits in the centre of a ChArUco board. The board is mounted on a
turntable and rotates together with the plant. A single camera stays in a fixed position and
photographs the plant at many rotation angles, then is moved to an overhead jig for 5 top views.
From those images the pipeline reconstructs 3D geometry, extracts organ keypoints, and measures
phenotypes.

**Stage 1 (this task)** covers: project scaffold, configuration, session manifests, camera
intrinsic calibration, per-frame camera pose from the board, and plant silhouette masking.

## 2. Hard constraints — violating any of these breaks the design

1. **Do NOT use SfM (COLMAP, OpenSfM, feature-matching pose estimation).** The camera and the
   background are both static while the board rotates; SfM concludes the camera never moved and
   fails. Camera pose comes **only** from ChArUco PnP, solved independently per frame.
2. **Do NOT use `cv2.findChessboardCorners`.** The board is ChArUco. Use
   `cv2.aruco.CharucoDetector` (OpenCV >= 4.8) so that pose still solves when the plant occludes
   most of the board.
3. **Do NOT reject the board by colour thresholding.** The substrate is vermiculite — bright and
   uniform, like parts of the board. Reject the board **geometrically**: points lying on the board
   plane within its measured extent.
4. **`board_variant_id` is mandatory in every manifest, and must match
   `config/board_spec.json::variant_id`.** Several printed board variants exist and their marker IDs
   overlap, so the board can never be inferred from detected IDs. Refuse to process a session on a
   mismatch — it yields healthy-looking detection and wrong dimensions, and nothing catches it.
5. **Never use `nominal_angle_deg` for geometry.** It is the commanded turntable angle. The
   measured pose in `poses.csv` is authoritative.
6. **A value that cannot be measured is written as `unavailable`, never as `0` or an imputed
   number.**
7. Tabular data is CSV. Configuration, knowledge and metadata are JSON. No other formats.

## 3. Coordinate frame

Origin at the board's origin inner corner. `+X` and `+Y` along the board rows and columns,
`+Z` up, away from the board surface. All lengths in **millimetres**. All angles in **degrees**
in files, **radians** inside code (name radian variables with a `_rad` suffix).

Because the board rotates with the plant, this frame is identical in every session. Cross-date
comparison therefore needs no registration step. Do not add one.

## 4. Environment variables

Create `.env.example` and load it with `python-dotenv`. All are read once in
`tomato3d/config.py`, never with `os.environ` scattered through the code.

```
TOMATO3D_DATA_ROOT=./data
TOMATO3D_CONFIG_DIR=./config
TOMATO3D_CAMERA_ID=cam_a
TOMATO3D_LOG_LEVEL=INFO
TOMATO3D_MAX_WORKERS=4
```

`tomato3d/config.py` exposes a frozen dataclass `Settings` with fields
`data_root: Path`, `config_dir: Path`, `camera_id: str`, `log_level: str`, `max_workers: int`,
and a module-level `get_settings()` that caches with `functools.lru_cache`.

Derived paths are **properties on `Settings`**, never string-concatenated at call sites:
`raw_dir`, `calib_dir`, `derived_dir`, `outputs_dir`, `knowledge_dir`, `tracks_dir`.

## 5. Configuration files (JSON, in `TOMATO3D_CONFIG_DIR`)

### `config/board_spec.json`

```json
{
  "schema_version": "1.1",
  "variant_id": "charuco_7x7_190mm",
  "pattern": "charuco",
  "aruco_dict": "DICT_4X4_50",
  "legacy_pattern": false,
  "squares_x": 7,
  "squares_y": 7,
  "square_size_mm": 27.142857142857142,
  "marker_size_mm": 19.904761904761905,
  "board_width_mm": 190.0,
  "board_height_mm": 190.0,
  "marker_ids": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
                 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
  "expected_marker_count": 24,
  "expected_inner_corner_count": 36,
  "origin_corner": "top_left",
  "position_frame": "sheet",
  "mounted_on_turntable": true,
  "surface_finish": "matte",
  "print_page_size": "A4",
  "print_pdf_ref": "build/charuco_board_7x7_190mm_A4.pdf",
  "pattern_spec_ref": "build/charuco_board_7x7_190mm_spec.json",
  "board_center_mm": [95.0, 95.0],
  "pot_center_offset_mm": [0.0, 0.0],
  "scale_block_position_mm": [13.571428571428571, 13.571428571428571],
  "scale_block_cell_code": "A1",
  "scale_block_nominal_height_mm": null,
  "color_chart_on_board": false,
  "physical_print_verified": false,
  "_position_frame_note": "Every *_position_mm and *_center_mm value in this file is in the SHEET frame: origin at the printed sheet's origin_corner, +X right along a row, +Y down along a column, +Z into the board. The pipeline's board frame is a different frame; tomato3d/calib/board.py::sheet_to_board_mm is the only conversion.",
  "_scale_block_note": "Cell A1 is a marker-free (black) square on this board - all four corner cells are - so the block covers no marker. scale_block_nominal_height_mm stays null until the physical block is measured with a caliper.",
  "_color_chart_note": "The colour chart sits on the turntable beside the board, not on it, so it cannot occlude markers. Its pose is not solved; it is used for colour correction only.",
  "_spare_variant_note": "build/charuco_board_5x5_190mm_A4.pdf is a built spare (5x5, 38 mm cells, 12 markers, 16 corners). It is NOT the operational board. Marker IDs overlap between variants, so a session's board is known only from its manifest."
}
```

### `config/capture_config.json`

```json
{
  "schema_version": "1.0",
  "side_camera_radius_mm": 550.0,
  "side_camera_height_mm": 300.0,
  "side_camera_elevation_deg": 28.6,
  "side_aim_point_mm": [0.0, 0.0, 110.0],
  "side_view_count_pilot": 36,
  "side_view_step_deg": 10.0,
  "top_camera_height_mm": 550.0,
  "top_view_positions_mm": {
    "T0": [0.0, 0.0, 550.0],
    "T1": [135.0, 135.0, 550.0],
    "T2": [-135.0, 135.0, 550.0],
    "T3": [-135.0, -135.0, 550.0],
    "T4": [135.0, -135.0, 550.0]
  },
  "operational_top_view": "T0",
  "settle_seconds_after_rotation": 5.0
}
```

`operational_top_view` matters: the final product infers from one top view plus one side view, and
that top view is always `T0`. `T1`–`T4` exist only to build training references.

### `config/quality_thresholds.json`

```json
{
  "schema_version": "1.0",
  "min_pose_solved_ratio": 0.95,
  "max_mean_reprojection_error_px": 1.0,
  "max_silhouette_area_cv": 0.15,
  "max_scale_block_height_error_mm": null,
  "min_charuco_corners_for_pose": 6,
  "_note_board": "charuco_7x7_190mm. 36 inner corners, 24 markers. Every *_position_mm in board_spec.json is SHEET frame."
}
```

`null` means "not yet determined by the pilot". A null threshold is **loaded but inactive** — never
substitute a default.

## 6. Repository layout to create

```
tomato3d/
  __init__.py
  config.py              Settings, get_settings()
  logging_setup.py       one configure_logging(level) used by every entry point
  io/
    __init__.py
    schemas.py           every dataclass + JSON Schema, and CSV column orders
    manifest.py          read/write session_manifest.json, resolve session paths
    tables.py            typed CSV read/write helpers (single place that touches csv/pandas)
    quality.py           QualityRecord build + write
  calib/
    __init__.py
    board.py             ChArUco board construction + corner detection
    intrinsics.py        intrinsic calibration
    pose.py              per-frame PnP, turntable axis estimation
  mask/
    __init__.py
    silhouette.py        plant mask, board/chart/block rejection, consistency metric
  cli/
    __init__.py
    calibrate_intrinsics.py
    run_stage1.py
tests/
  conftest.py
  test_config.py
  test_schemas.py
  test_board_pose_synthetic.py
  test_manifest.py
  test_mask_geometry.py
config/
  board_spec.json
  capture_config.json
  quality_thresholds.json
data/
  .gitkeep
pyproject.toml
.env.example
.gitignore            must include build/ and data/
README.md
```

**`tools/` and `build/` are owned by a second agent working in this repo. Do not create, edit or
delete anything under either.** `tools/` holds support tooling (board print generator, session
organiser, record validators); `build/` holds generated artefacts. Your test fixtures import
`tools.charuco_render.render_charuco_view` for synthetic board rendering — import it, do not
reimplement it, and if it is not present yet, write the test with a skip marker naming that module
rather than writing your own renderer.

Create **stub modules with docstrings and `raise NotImplementedError`** for later stages so the
import graph is fixed now: `tomato3d/recon/`, `tomato3d/organ/`, `tomato3d/fuse3d/`,
`tomato3d/graph/`, `tomato3d/pheno/`, `tomato3d/track/`, `tomato3d/rules/`, `tomato3d/twoview/`.
Do not implement them.

## 7. Data layout produced

```
data/raw/<plant_id>/<session_id>/
  images/side_000.jpg ... side_035.jpg
  images/top_T0.jpg ... top_T4.jpg
  session_manifest.json
data/calib/
  intrinsics_shots/                  raw board-only shots used for intrinsic calibration
  intrinsics_<camera_id>.json
data/records/<plant_id>/             human-recorded ground truth - READ ONLY for the pipeline
  manual_events.csv
  manual_measurements.csv
  environment.csv
  organ_label_map.csv
data/derived/<plant_id>/<session_id>/
  poses.csv
  masks/side_000.png ...
  quality.json
```

`data/records/` is written by people, never by this pipeline. The manifest's `environment_log_ref`
points at `data/records/<plant_id>/environment.csv`. Reading those files is fine; writing to them,
or "repairing" a malformed row, is not.

`session_id` format: `<plant_id>_<YYYYMMDD>_<HHMM>`.

## 8. Schemas to implement in `io/schemas.py`

### `session_manifest.json`

Fields: `schema_version, plant_id, session_id, captured_at (ISO8601 with offset), camera_id,
board_variant_id, board_spec_ref, intrinsics_ref, rotation_mode, side_view_count, side_view_step_deg, top_view_count,
top_view_method, top_view_positions_mm, operational_top_view, side_camera_radius_mm,
side_camera_height_mm, color_chart_in_frame, scale_reference_block_mm, environment_log_ref,
images[], notes`.

Each entry of `images[]`: `{file, view_type, top_position, nominal_angle_deg}` where
`view_type` is `side` or `top`, `top_position` is `T0`–`T4` or null, and `nominal_angle_deg` is
null for top views.

### `intrinsics_<camera_id>.json`

`schema_version, camera_id, image_width_px, image_height_px, camera_matrix (3x3 row-major),
dist_coeffs (list), rms_reprojection_error_px, n_calibration_images, calibrated_at,
distortion_model ("opencv_pinhole")`.

### `poses.csv` — column order is fixed

```
session_id, image_file, view_type, top_position, pose_status, n_corners_detected,
reprojection_error_px, rvec_x, rvec_y, rvec_z, tvec_x_mm, tvec_y_mm, tvec_z_mm, measured_angle_deg
```

`pose_status` is `solved` or `failed`. `rvec_*` are Rodrigues components in radians mapping the
board frame to the camera frame. A failed row keeps the image_file and writes `unavailable` for
every numeric field.

### `quality.json`

`session_id, pose_solved_ratio, mean_reprojection_error_px, silhouette_area_cv,
n_images_total, n_images_solved, usable_for_training, failure_reasons[]`.

`usable_for_training` is computed from `config/quality_thresholds.json`, skipping any null
threshold. Later stages add `scale_block_height_error_mm`, `hull_voxel_count`,
`depth_scale_fit_rmse_mm` — leave those keys absent, not null, at this stage.

## 9. Function signatures — implement exactly these

`tomato3d/calib/board.py`

```python
def build_charuco_board(spec: BoardSpec) -> cv2.aruco.CharucoBoard: ...

def detect_board_corners(image: np.ndarray, board: cv2.aruco.CharucoBoard) -> BoardDetection:
    """Subpixel ChArUco corners. BoardDetection carries corners (N,2) float32,
    ids (N,) int32, and n_corners_detected."""
```

`tomato3d/calib/intrinsics.py`

```python
def calibrate_intrinsics(image_paths: list[Path], spec: BoardSpec, camera_id: str) -> Intrinsics:
    """Requires >= 15 usable views. Raises CalibrationError with the count if fewer.
    Writes nothing; the caller writes the JSON."""
```

`tomato3d/calib/pose.py`

```python
def solve_pose(detection: BoardDetection, intrinsics: Intrinsics, board: cv2.aruco.CharucoBoard,
               min_corners: int) -> Pose:
    """cv2.aruco.estimatePoseCharucoBoard. Returns Pose with pose_status='failed' when fewer
    than min_corners corners were detected or the solver fails. Never raises for a bad frame."""

def estimate_turntable_axis(poses: list[Pose]) -> TurntableAxis:
    """Fit the rotation axis from the side-view pose sequence. Used for QC and to fill
    measured_angle_deg only. No downstream geometry may depend on it."""

def measured_angle_deg(pose: Pose, axis: TurntableAxis) -> float: ...
```

`tomato3d/mask/silhouette.py`

```python
def board_plane_mask(pose: Pose, intrinsics: Intrinsics, spec: BoardSpec,
                     image_shape: tuple[int, int]) -> np.ndarray:
    """Project the board rectangle into the image. Returns a binary mask of the board region.
    Purely geometric - no pixel colour is read."""

def segment_plant_silhouette(image: np.ndarray, pose: Pose, intrinsics: Intrinsics,
                             spec: BoardSpec) -> np.ndarray:
    """Binary uint8 mask, plant=255. Exclude the board region, the colour chart and the scale
    block using board_plane_mask and the known scale_block_position_mm. Everything above the
    board plane inside the board footprint is a plant candidate."""

def silhouette_area_cv(masks: list[np.ndarray]) -> float:
    """Coefficient of variation of silhouette pixel area across side views.
    A high value means the plant moved during rotation or masking failed."""
```

For this stage a classical segmentation (board rejection + GrabCut or Otsu on the non-board region,
plus largest-connected-component cleanup) is sufficient. Keep the function boundary stable so a
learned segmenter can replace the body later without touching callers.

## 10. CLI contracts

```
python -m tomato3d.cli.calibrate_intrinsics --images data/calib/intrinsics_shots/ \
                                            --board config/board_spec.json \
                                            --camera-id cam_a

python -m tomato3d.cli.run_stage1 --session data/raw/DT-001/DT-001_20260915_0900
```

`run_stage1` writes `poses.csv`, `masks/`, and `quality.json`, then prints a one-screen summary:
images total, poses solved, mean reprojection error, silhouette area CV, `usable_for_training`.

Both exit non-zero on a hard failure (missing config, unreadable manifest, too few calibration
images). A per-frame pose failure is **not** a hard failure — it is recorded and the run continues.

## 11. Tests — write these first and make them pass

| test | asserts |
|---|---|
| `test_config_paths` | every derived path property resolves under `TOMATO3D_DATA_ROOT` |
| `test_settings_cached` | `get_settings()` returns the same object twice |
| `test_schema_roundtrip` | every JSON schema and CSV writes and reads back identically, column order preserved |
| `test_manifest_validation` | a manifest missing a required field is rejected with the field named |
| `test_board_pose_synthetic` | render a synthetic ChArUco view with a known pose; recovered rvec/tvec within 0.5 px reprojection |
| `test_pose_partial_occlusion` | occlude 70% of the synthetic board; pose still solves |
| `test_pose_below_min_corners` | fewer than `min_charuco_corners_for_pose` corners yields `pose_status='failed'`, no exception |
| `test_mask_geometry_only` | `board_plane_mask` output is unchanged when the input image's colours are randomised |
| `test_unavailable_not_zero` | a failed pose row serialises numeric fields as `unavailable`, not `0` |
| `test_null_threshold_inactive` | a null threshold in `quality_thresholds.json` does not gate `usable_for_training` |

Use `pytest`. Synthetic board renders go in `tests/conftest.py` as fixtures — do not require real
photographs for any test.

## 12. Style

- Python 3.11+, `pyproject.toml`, dependencies: `opencv-contrib-python`, `numpy`, `pandas`,
  `python-dotenv`, `pydantic` (schema validation), `pytest`.
- `opencv-contrib-python`, not `opencv-python` — `cv2.aruco` lives in contrib.
- Type hints everywhere. `pathlib.Path` for every path.
- Every length variable carries its unit in the name: `square_size_mm`, `height_mm`, `radius_mm`.
  Angle variables are `_deg` or `_rad`. No bare `size`, `height`, `angle`.
- No magic numbers in function bodies. Every constant comes from a config JSON.
- Logging via `logging_setup.configure_logging`, never `print`, except the CLI summary.

## 13. Definition of done

1. `pytest` passes.
2. `python -m tomato3d.cli.run_stage1 --help` works.
3. A `README.md` that shows: install, `.env` setup, intrinsic calibration, running one session.
4. Later-stage packages import cleanly and raise `NotImplementedError` when called.
5. No SfM dependency anywhere in `pyproject.toml`.

Implement it now. Start with `config.py`, `io/schemas.py` and the tests, then the calibration and
mask modules.

--- END PROMPT ---
