# Tomato 3D Phenotyping — Algorithm Skeleton

- Date: 2026-09-15
- Status: **Design skeleton. Not an implementation authorization.**
- Companion: `docs/3D_표현체_설계리뷰_2026-09-15.md` (Korean design review; agronomic rationale lives there)
- Scope: dwarf (determinate) cherry tomato, indoor LED shelf, single fixed camera + rotating reference board

This document defines module boundaries, function signatures, file names, and data schemas.
It intentionally contains no algorithm tuning values. Every numeric threshold is a placeholder
resolved from `crop_pack_dwarf_tomato.json` or from pilot measurements.

---

## 0. Confirmed constraints that shape this skeleton

| ID | Constraint | Consequence in code |
|----|-----------|---------------------|
| C4 | One camera, fixed position | Views come from board rotation, not camera motion |
| D1 | Board rotates with the plant (recommended) | Camera pose is solved per-frame by PnP; **no SfM module exists in this design** |
| C5 | RGB reconstruction + monocular depth assist | Reconstruction = visual hull + scale-aligned monocular depth |
| C7 | Final target: 1 top + 1 side real image | Two-view module consumes labels distilled from the multi-view reference |
| C9 | Board = ChArUco `charuco_7x7_190mm`: **7x7 squares, 190/7 mm square, 19.905 mm marker**, DICT_4X4_50, **190x190 mm, A4** | 36 inner corners, 24 markers; pose survives heavy board occlusion |
| C10 | 5 top views T0..T4; **T0 only** is the operational top view | Two-view inference is always `T0 + one side`; T1..T4 are teacher-only |
| C11 | Pilot captures 36 side views at 10 deg | Operational side count is decided from the pilot sweep, not assumed |

**Critical:** standard SfM (COLMAP etc.) fails on a turntable rig because background and camera are both
static. This design avoids SfM entirely by solving pose from the rotating board. Do not substitute SfM.

---

## 1. Repository layout

```
tomato3d/
  io/
    manifest.py          session manifest read/write, path resolution
    schemas.py           dataclasses + JSON Schema validation for every artifact
    quality.py           per-session quality record
  calib/
    board.py             checkerboard corner detection
    intrinsics.py        camera intrinsic calibration
    pose.py              per-frame extrinsics via PnP, turntable axis estimation
  mask/
    silhouette.py        plant/background separation, rotation-consistency check
  recon/
    visual_hull.py       voxel carving from silhouettes
    monodepth.py         relative depth inference
    scale_align.py       affine (a, b) fit of relative depth to metric
    fuse.py              hull + depth -> oriented point cloud
  organ/
    segment2d.py         per-view organ instance segmentation
    classes.py           organ class enum and ontology
  fuse3d/
    lift.py              2D instance mask -> 3D point subset
    merge.py             cross-view instance merging, persistent organ IDs
  graph/
    skeleton.py          stem centerline extraction
    nodes.py             node (phytomer) detection and ordering
    keypoints.py         per-organ keypoint extraction
    connectivity.py      organ graph assembly
  pheno/
    measure.py           phenotype computation -> CSV
  track/
    link.py              cross-date organ linking
  rules/
    croppack.py          crop pack JSON loader + validator
    diagnose.py          disorder assessment
    actions.py           leaf-removal / fruit-culling suggestions
  twoview/
    render_labels.py     project multi-view 3D into 2-view label space
    dataset.py           paired dataset assembly + plant-level splits
    model.py             two-view network definition
    infer.py             two-view inference -> same CSV schema as pheno/
  cli/
    run_session.py       full multi-view pipeline for one session
    run_twoview.py       two-view inference for one capture
```

---

## 2. Data layout on disk

```
data/
  raw/<plant_id>/<session_id>/
    images/side_000.jpg ... side_NNN.jpg
    images/top_000.jpg
    session_manifest.json
  calib/
    intrinsics_<camera_id>.json
    board_spec.json
  derived/<plant_id>/<session_id>/
    poses.csv
    masks/side_000.png ...
    depth/side_000.npy ...
    pointcloud.ply
    organs.csv
    keypoints.csv
    connectivity.csv
    phenotypes.csv
    quality.json
  tracks/<plant_id>/tracks.csv
  outputs/<plant_id>/<session_id>/
    diagnoses.csv
    actions.csv
  knowledge/
    crop_pack_dwarf_tomato.json
```

Convention (project rule): **measurement tables = CSV, configuration/knowledge/metadata = JSON.**
Derived outputs are reproducible and never written back into raw observation tables.

---

## 3. Schemas

### 3.1 `session_manifest.json`

```json
{
  "schema_version": "1.0",
  "plant_id": "DT-001",
  "session_id": "DT-001_20260915_0900",
  "captured_at": "2026-09-15T09:00:00+09:00",
  "camera_id": "cam_a",
  "board_variant_id": "charuco_7x7_190mm",
  "board_spec_ref": "config/board_spec.json",
  "intrinsics_ref": "calib/intrinsics_cam_a.json",
  "rotation_mode": "board_with_plant",
  "side_view_count": 36,
  "side_view_step_deg": 10.0,
  "top_view_count": 5,
  "top_view_method": "camera_moved_to_overhead_jig",
  "top_view_positions_mm": {"T0": [0,0,550], "T1": [135,135,550], "T2": [-135,135,550], "T3": [-135,-135,550], "T4": [135,-135,550]},
  "operational_top_view": "T0",
  "side_camera_radius_mm": 550.0,
  "side_camera_height_mm": 300.0,
  "color_chart_in_frame": true,
  "scale_reference_block_mm": null,
  "environment_log_ref": "env/DT-001_20260915.csv",
  "images": [
    {"file": "images/side_000.jpg", "view_type": "side", "nominal_angle_deg": 0.0},
    {"file": "images/top_T0.jpg",   "view_type": "top",  "top_position": "T0", "nominal_angle_deg": null}
  ],
  "notes": ""
}
```

`nominal_angle_deg` is the commanded angle. The measured angle comes from `poses.csv` and is
authoritative. Never use the nominal angle for geometry.

**`board_variant_id` is mandatory and is checked, not trusted blindly.** Several printed board
variants exist (`charuco_7x7_190mm` operational, `charuco_5x5_190mm` spare) and **their marker IDs
overlap**, so the board can never be inferred from detected IDs. `run_stage1` must refuse a session
whose `board_variant_id` does not match `config/board_spec.json::variant_id`. A mismatch produces
healthy-looking detection with every dimension wrong, and no later stage can catch it.

### 3.2 `board_spec.json`

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

### 3.3 `poses.csv`

| column | type | unit | note |
|---|---|---|---|
| session_id | str | | |
| image_file | str | | relative to session dir |
| view_type | str | | `side` \| `top` |
| pose_status | str | | `solved` \| `failed` |
| n_corners_detected | int | count | |
| reprojection_error_px | float | px | RMS |
| rvec_x, rvec_y, rvec_z | float | rad | Rodrigues, board frame -> camera |
| tvec_x, tvec_y, tvec_z | float | mm | |
| measured_angle_deg | float | deg | about estimated turntable axis |

**Coordinate frame:** origin at board origin corner, `+Z` up (away from board surface),
`+X`/`+Y` along board rows/columns. This frame is identical across sessions, which is what makes
cross-date comparison possible without registration.

### 3.4 `organs.csv`

| column | type | unit | note |
|---|---|---|---|
| session_id | str | | |
| organ_id | str | | stable within session, e.g. `leaf_007` |
| organ_class | str | | see §4 |
| node_index | int | | 0 = cotyledon node; null if not attached to stem |
| parent_organ_id | str | | truss for a fruit, stem for a leaf |
| observation_status | str | | `observed` \| `inferred` \| `unknown` |
| n_views_observed | int | count | |
| centroid_x, centroid_y, centroid_z | float | mm | board frame |
| volume_mm3 | float | mm^3 | null for leaves |
| mean_L, mean_a, mean_b | float | CIELab | after color correction |
| confidence | float | 0-1 | |

### 3.5 `keypoints.csv`

| column | type | unit |
|---|---|---|
| session_id | str | |
| organ_id | str | |
| keypoint_name | str | see §5 |
| x, y, z | float | mm |
| source | str | `triangulated` \| `hull` \| `depth` \| `inferred` |
| confidence | float | 0-1 |

### 3.6 `connectivity.csv`

| column | type | note |
|---|---|---|
| session_id | str | |
| from_organ_id | str | |
| to_organ_id | str | |
| relation | str | `attached_to` \| `bears` \| `branches_from` |
| attachment_x, attachment_y, attachment_z | float (mm) | 3D attachment point |
| confidence | float | |

### 3.7 `phenotypes.csv`

One row per (session_id, trait, subject_id). Long format so multi-view and two-view outputs share a schema.

| column | type | note |
|---|---|---|
| session_id | str | |
| captured_at | ISO8601 | |
| subject_id | str | `plant` or an organ_id |
| trait | str | see §7 |
| value | float | |
| unit | str | |
| method | str | `multiview` \| `twoview` |
| observation_status | str | `observed` \| `inferred` \| `unavailable` |
| uncertainty | float | same unit as value; null if unavailable |

### 3.8 `quality.json`

```json
{
  "session_id": "DT-001_20260915_0900",
  "pose_solved_ratio": 0.96,
  "mean_reprojection_error_px": 0.41,
  "silhouette_area_cv": 0.08,
  "scale_block_height_error_mm": 1.2,
  "hull_voxel_count": 184203,
  "depth_scale_fit_rmse_mm": 2.8,
  "usable_for_training": true,
  "failure_reasons": []
}
```

`usable_for_training` gates a session out of the two-view training set. Thresholds come from the pilot.

### 3.8b Ground-truth and environment tables

These are **human-recorded**, never written by the pipeline. The pipeline reads them for evaluation
and for environment-dependent rules; it must never modify them.

`manual_events.csv`
`plant_id, observed_at, observer, event_type, truss_index, node_index, organ_label, count, note`

`event_type` in `{flowering_open, flower_bud, flower_spent, fruit_set, fruit_color_break,
fruit_harvest, leaf_removed, organ_lost, anomaly}`.

`manual_measurements.csv`
`plant_id, session_id, measured_at, trait, value, unit, method, observer`

`trait` in `{plant_height, stem_diameter_base, leaf_count, fruit_count, truss_count, canopy_width,
reference_block_height}`. `method` in `{ruler, caliper, visual_count}`.

`environment.csv`
`plant_id, timestamp, air_temp, rh, solution_ec, solution_ph, ppfd, photoperiod,
bottom_water_level, source, note`

Units: degC, %, dS/m, -, umol/m2/s, h. Substrate is vermiculite with constant bottom watering,
so EC/pH are measured in the bottom reservoir; the sampling point must not change between sessions.

`organ_label_map.csv`
`session_id, organ_label, organ_id, match_status, checked_by`

`match_status` in `{matched, unmatched_manual, unmatched_pipeline, ambiguous}`.
**`organ_label` (human) and `organ_id` (pipeline) are different namespaces and are never merged.**
Every evaluation metric that compares detection against ground truth joins through this table.

### 3.9 `crop_pack_dwarf_tomato.json` (extension contract)

> **Rule content, thresholds and agronomic judgment are supplied by the user.** The pipeline only
> loads, validates and enforces this schema; it must not invent thresholds or infer rules.

Extends the existing Crop Pack contract. Every rule carries `rule_id`, `basis`, `confidence`, `source`.

```json
{
  "schema_version": "1.0",
  "crop": "tomato",
  "type": "dwarf_determinate",
  "cultivar": "TBD",
  "rules": [
    {
      "rule_id": "LEAF_REMOVE_BELOW_FIRST_TRUSS",
      "kind": "leaf_removal",
      "condition": {"node_index_lt": "first_truss_node_index"},
      "output": {"reason": "airflow_and_splash_barrier"},
      "basis": "standard practice for determinate types",
      "confidence": "high",
      "source": "literature"
    },
    {
      "rule_id": "LEAF_REMOVE_SENESCENT",
      "kind": "leaf_removal",
      "condition": {"leaf_chlorosis_fraction_gt": null, "necrosis_fraction_gt": null},
      "output": {"reason": "senescent_or_lesioned"},
      "basis": "no net photosynthetic contribution; inoculum source",
      "confidence": "high",
      "source": "literature",
      "note": "thresholds TBD from pilot"
    },
    {
      "rule_id": "FRUIT_CULL_DEFECTIVE",
      "kind": "fruit_culling",
      "condition": {"defect_class_in": ["malformed", "cracked", "lesioned", "blossom_end_rot"]},
      "output": {"reason": "quality_loss_or_inoculum"},
      "confidence": "high",
      "source": "literature"
    },
    {
      "rule_id": "FRUIT_LOAD_WARNING",
      "kind": "load_warning",
      "condition": {"fruits_per_truss_gt": null, "leaf_area_per_fruit_lt": null},
      "output": {"reason": "source_sink_imbalance"},
      "confidence": "low",
      "source": "requires_homefarm_measurement",
      "note": "NOT resolvable from literature; cultivar- and DLI-dependent"
    },
    {
      "rule_id": "ETIOLATION_ASSESS",
      "kind": "disorder",
      "condition": {"internode_length_mm_gt": null, "height_per_leaf_mm_gt": null},
      "output": {"disorder": "excessive_elongation"},
      "requires_environment": ["dli", "night_temperature", "day_night_temp_diff"],
      "confidence": "medium",
      "source": "requires_homefarm_measurement"
    },
    {
      "rule_id": "DEFICIENCY_MOBILITY_TRIAGE",
      "kind": "disorder",
      "condition": {"symptom_node_position": "lower|upper"},
      "output": {
        "lower": {"mobility": "mobile", "candidates": ["N", "P", "K", "Mg"]},
        "upper": {"mobility": "immobile", "candidates": ["Ca", "Fe", "B", "S", "Mn"]}
      },
      "action": "verify_ec_ph_and_solution_composition",
      "confidence": "medium",
      "source": "literature",
      "note": "never emit a single element as a diagnosis from RGB alone"
    }
  ]
}
```

### 3.10 `actions.csv` / `diagnoses.csv`

`diagnoses.csv`: `session_id, disorder, affected_organ_ids, evidence_traits, node_range, confidence, rule_id, requires_environment_check`

`actions.csv`: `session_id, action_type, target_organ_id, parent_organ_id, attachment_x/y/z, reason, rule_id, priority, confidence`

`action_type` is one of `leaf_removal`, `fruit_culling`, `load_warning`, `recapture_requested`.
Measured observations, inferred conditions, and recommended actions stay in separate files by design.

---

## 4. Organ ontology (`organ/classes.py`)

```python
class OrganClass(str, Enum):
    STEM_SEGMENT = "stem_segment"
    LEAF         = "leaf"          # compound leaf as one instance
    LEAFLET      = "leaflet"       # optional finer level
    PETIOLE      = "petiole"
    TRUSS        = "truss"
    FLOWER_BUD   = "flower_bud"
    FLOWER_OPEN  = "flower_open"   # anthesis: corolla visible
    FLOWER_SPENT = "flower_spent"
    FRUIT        = "fruit"
    GROWING_TIP  = "growing_tip"
```

Flowering definition is fixed at `FLOWER_OPEN` = corolla reflexed and visible.
`first_observed_flowering_date` is an **observation date**, not anthesis date; capture interval is
recorded alongside it as the irreducible error.

---

## 5. Keypoint definitions (`graph/keypoints.py`)

| organ_class | keypoint_name | definition |
|---|---|---|
| STEM_SEGMENT | `stem_base` | centerline intersection with board plane |
| STEM_SEGMENT | `node_{i}` | centerline point at i-th phytomer |
| GROWING_TIP | `apex` | distal end of main centerline |
| LEAF | `petiole_attachment` | petiole/stem junction on centerline |
| LEAF | `blade_centroid` | area centroid of lifted leaf points |
| LEAF | `blade_tip` | point of max geodesic distance from attachment |
| TRUSS | `truss_attachment` | truss/stem junction |
| FLOWER_* | `flower_center` | corolla centroid |
| FLOWER_* | `flower_attachment` | pedicel/rachis junction |
| FRUIT | `fruit_centroid` | volumetric centroid |
| FRUIT | `pedicel_attachment` | pedicel/truss junction |

`attachment` keypoints are the deliverable for D12 ("location" = attachment point, not cutting trajectory).

---

## 6. Function signatures

Types below use `pathlib.Path`, `numpy.ndarray`, and the dataclasses from `io/schemas.py`.

### 6.1 `calib`

```python
def detect_board_corners(image: np.ndarray, spec: BoardSpec) -> BoardDetection:
    """Returns subpixel corner array (N,2) and detection status. N = inner_corners_x * inner_corners_y."""

def calibrate_intrinsics(images: list[Path], spec: BoardSpec) -> Intrinsics:
    """Writes calib/intrinsics_<camera_id>.json. Requires >= 15 board poses spanning the frame."""

def solve_pose(detection: BoardDetection, intrinsics: Intrinsics, spec: BoardSpec) -> Pose:
    """PnP. Returns rvec/tvec (board frame -> camera) and reprojection_error_px."""

def estimate_turntable_axis(poses: list[Pose]) -> TurntableAxis:
    """Fits the rotation axis from the pose sequence. Used only for QC and measured_angle_deg;
    geometry never depends on it."""

def write_poses_csv(poses: list[Pose], out: Path) -> None: ...
```

### 6.2 `mask`

```python
def segment_plant_silhouette(image: np.ndarray, pose: Pose, spec: BoardSpec) -> np.ndarray:
    """Binary mask, plant=1. Board plane and known board extent are used to reject the board,
    the color chart, and the scale block.
    Vermiculite substrate is bright and uniform, and so are parts of the board: reject the board
    GEOMETRICALLY (points on the board plane within its measured extent), never by a color threshold."""

def silhouette_consistency(masks: list[np.ndarray], poses: list[Pose]) -> float:
    """Coefficient of variation of silhouette area across views. High CV => plant moved during
    rotation, or masking failed. Feeds quality.json."""
```

### 6.3 `recon`

```python
def carve_visual_hull(masks: list[np.ndarray], poses: list[Pose], intrinsics: Intrinsics,
                      voxel_size_mm: float, bounds_mm: tuple) -> VoxelGrid:
    """Space carving in the board frame. voxel_size_mm from pilot; start at 1.0."""

def infer_relative_depth(image: np.ndarray) -> np.ndarray:
    """Monocular relative (affine-invariant) depth. Output is NOT metric."""

def fit_depth_scale(rel_depth: np.ndarray, mask: np.ndarray, pose: Pose,
                    intrinsics: Intrinsics, hull: VoxelGrid, spec: BoardSpec) -> DepthScale:
    """Least squares for (a, b) in d_metric = a * d_rel + b.
    Correspondences: (i) board-plane pixels with known 3D depth,
                     (ii) hull surface points projected into this view.
    Returns (a, b) and depth_scale_fit_rmse_mm."""

def fuse_to_pointcloud(hull: VoxelGrid, depths: list[MetricDepth], poses: list[Pose],
                       intrinsics: Intrinsics) -> PointCloud:
    """Hull provides the outer envelope; scale-aligned depth refines surface geometry inside it.
    Points outside the hull are rejected. Per-point source flag is preserved."""
```

### 6.4 `organ` / `fuse3d`

```python
def segment_organs_2d(image: np.ndarray, mask: np.ndarray) -> list[Instance2D]:
    """Instance segmentation over OrganClass. Reuses the existing SAM+YOLO assets;
    class set must be extended (decision D9)."""

def lift_instance(inst: Instance2D, depth: MetricDepth, pose: Pose,
                  intrinsics: Intrinsics, cloud: PointCloud) -> Instance3D: ...

def merge_instances(instances: list[Instance3D], poses: list[Pose]) -> list[Organ]:
    """Cross-view merging by 3D overlap + class agreement. Assigns organ_id.
    Records n_views_observed. An organ seen in one view only is flagged low confidence,
    not discarded."""
```

### 6.5 `graph`

```python
def extract_stem_centerline(cloud: PointCloud, organs: list[Organ]) -> Centerline: ...
def detect_nodes(centerline: Centerline, organs: list[Organ]) -> list[Node]:
    """Nodes are located where petiole/truss attachments cluster on the centerline.
    node_index is ordered from the base upward."""
def extract_keypoints(organs: list[Organ], centerline: Centerline, nodes: list[Node]) -> list[Keypoint]: ...
def build_connectivity(organs, nodes, keypoints) -> list[Edge]: ...
```

### 6.6 `pheno`

```python
def measure(organs, keypoints, edges, centerline, quality) -> list[PhenotypeRow]:
    """Every row carries observation_status and uncertainty. A trait that cannot be measured
    from the available observations is emitted as `unavailable`, never as 0 or an imputed value."""
```

### 6.7 `track`

```python
def link_sessions(prev: SessionResult, curr: SessionResult) -> list[TrackRow]:
    """Cross-date organ linking in the shared board frame.
    Must distinguish: newly emerged organ / previously occluded organ now visible /
    removed organ / tracking ambiguity. Each gets an explicit link_status."""
```

`tracks.csv` columns: `plant_id, track_id, session_id, organ_id, organ_class, link_status, confidence`
where `link_status` in `{new, continued, reappeared, removed, ambiguous}`.

### 6.8 `rules`

```python
def load_crop_pack(path: Path) -> CropPack:
    """Validates that every rule has rule_id, basis, confidence, source.
    A rule with a null threshold is loaded but marked inactive."""

def diagnose(pheno: list[PhenotypeRow], organs, tracks, pack: CropPack,
             env: EnvironmentLog | None) -> list[DiagnosisRow]:
    """Rules declaring requires_environment produce a diagnosis only when env is supplied;
    otherwise they emit requires_environment_check=True with no disorder claim."""

def suggest_actions(organs, edges, keypoints, diagnoses, pack: CropPack) -> list[ActionRow]:
    """Emits leaf_removal / fruit_culling / load_warning / recapture_requested.
    Never emits sucker removal for a determinate cultivar."""
```

### 6.9 `twoview`

```python
def render_two_view_labels(result: SessionResult, top_pose: Pose, side_pose: Pose) -> TwoViewLabels:
    """Projects the multi-view 3D result into the two chosen views.
    Labels include organs that are OCCLUDED in those two views - this is the whole point of the
    multi-view capture and the only reason it pays for itself."""

def build_dataset(sessions: list[SessionResult], split_by: str = "plant_id") -> Dataset:
    """split_by MUST be plant_id. All dates and all views of one plant land in the same split."""

def infer(top_image: np.ndarray, side_image: np.ndarray, intrinsics: Intrinsics,
          spec: BoardSpec, model: TwoViewModel) -> SessionResult:
    """Returns the same organs/keypoints/connectivity/phenotypes schema as the multi-view path,
    with method='twoview'. Occluded organs carry observation_status='inferred'.
    If aggregate uncertainty exceeds the pack threshold, emits a recapture_requested action
    instead of phenotype rows."""
```

Two-view model heads:
1. organ instance segmentation + 2D keypoints + node-index assignment (supervised by rendered labels)
2. monocular depth -> per-organ partial 3D, scaled by the board
3. phenotype regression with uncertainty (supervised by multi-view `phenotypes.csv`)

The two-view model does **not** attempt full 3D reconstruction. Two views cannot constrain a visual
hull; a reconstruction from them would be a learned prior, and measurements taken off that prior are
not traceable to observation.

---

## 7. Trait registry (`pheno/measure.py`)

| trait | unit | subject | required observations | notes |
|---|---|---|---|---|
| `plant_height` | mm | plant | stem_base, apex | along centerline, not straight line |
| `internode_length` | mm | node pair | consecutive nodes | primary etiolation indicator |
| `stem_diameter_base` | mm | plant | cloud near stem_base | |
| `height_per_leaf` | mm | plant | plant_height, leaf_count | cultivar-robust etiolation index |
| `leaf_count` | count | plant | merged LEAF organs | fully expanded leaves only |
| `leaf_area_projected` | mm^2 | leaf | top view mask | **not** surface area |
| `leaf_area_surface` | mm^2 | leaf | lifted leaf points | reconstruction-dependent; separate trait |
| `leaf_angle` | deg | leaf | petiole_attachment, blade_centroid | vs board plane |
| `canopy_width` | mm | plant | hull | max horizontal extent |
| `flower_count_open` | count | truss | FLOWER_OPEN organs | |
| `first_observed_flowering_date` | date | plant | tracks | observation date, not anthesis |
| `fruit_count` | count | truss | FRUIT organs | |
| `fruit_diameter` | mm | fruit | lifted fruit points | feeds existing diameter->mass module |
| `fruit_volume` | mm^3 | fruit | hull subset | |
| `leaf_chlorosis_fraction` | 0-1 | leaf | corrected Lab | requires color chart |
| `leaf_necrosis_fraction` | 0-1 | leaf | corrected Lab | |

`leaf_area_projected` and `leaf_area_surface` are deliberately separate traits and must never be
merged or silently substituted.

---

## 8. CLI contracts

```
python -m tomato3d.cli.run_session --session data/raw/DT-001/DT-001_20260915_0900 \
                                   --crop-pack data/knowledge/crop_pack_dwarf_tomato.json \
                                   [--env data/env/DT-001_20260915.csv]

python -m tomato3d.cli.run_twoview --top  path/top.jpg \
                                   --side path/side.jpg \
                                   --intrinsics calib/intrinsics_cam_a.json \
                                   --board calib/board_spec.json \
                                   --model models/twoview_v1.pt \
                                   --crop-pack data/knowledge/crop_pack_dwarf_tomato.json
```

Both write the same derived/outputs schema. A consumer cannot tell them apart except via the
`method` column, which is the intended property.

---

## 9. Tests to write before any pipeline code

| test | asserts |
|---|---|
| `test_board_pose_synthetic` | PnP recovers a known synthetic pose within 0.5 px reprojection |
| `test_scale_recovery` | scale block height recovered within tolerance from a synthetic hull |
| `test_depth_affine_fit` | known (a, b) recovered from synthetic relative depth |
| `test_hull_known_solid` | hull volume of a synthetic cylinder within N% at the chosen view count |
| `test_view_count_sweep` | hull volume error vs view count (8 / 24 / 36) - this test IS the D2 decision |
| `test_organ_merge_idempotent` | merging the same instance list twice yields identical organ_ids |
| `test_node_ordering` | node_index is monotonic along the centerline from base |
| `test_split_no_leakage` | no plant_id appears in more than one split |
| `test_schema_roundtrip` | every CSV/JSON writes and reads back identically |
| `test_unavailable_not_zero` | an unmeasurable trait emits `unavailable`, never 0.0 |

---

## 10. Build order

| Stage | Modules | Gate to proceed |
|---|---|---|
| 1 | `io`, `calib`, `mask` | pose solved on >= 95% of frames; reprojection RMS < 1 px |
| 2 | `recon` | scale block height error within pilot tolerance; **run `test_view_count_sweep` and settle D2 here** |
| 3 | `organ`, `fuse3d` | organ merge stable; per-class instance recall measured |
| 4 | `graph`, `pheno` | plant_height and leaf_count validated against manual measurement |
| 5 | `track`, `rules` | crop pack thresholds populated from pilot; rules loadable and inactive-flagged where null |
| 6 | `twoview` | validated on **real** two-view captures, not rendered views |

Stage 1 is the only stage that can start before decisions D1-D4 are made, and only if D1 is fixed.

---

## 11. Open decisions blocking this skeleton

Settled: D1 (board on turntable), D3 (5 top views, T0 operational), D4 (scale block), D6 (ChArUco 270 mm),
D10 (environment.csv is an input).

Open, resolved by the pilot: D2 side view count, D5 rim marker band, D7 capture interval,
D8 dataset size, D9 organ label set. D11 (rule thresholds) is the user's call, not the pipeline's.

See `docs/파일럿_촬영_프로토콜_2026-09-15.md` for the settled capture spec and the pilot design.
