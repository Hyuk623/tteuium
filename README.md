# tomato3d — Stage 1: capture and calibration

Dwarf cherry tomato 3D phenotyping. A plant sits at the centre of a ChArUco board; the
board is mounted on a turntable and rotates **with** the plant while a single camera
stays put. Stage 1 turns a folder of those photographs into per-frame camera poses, plant
silhouettes and a session quality record.

Later stages (reconstruction, organ segmentation, phenotypes, the two-view product) exist
as importable stubs so the import graph is already fixed. They raise
`NotImplementedError`.

## Install

Python 3.11 or newer.

```bash
pip install -e ".[dev]"
```

`opencv-contrib-python`, not `opencv-python` — `cv2.aruco` lives in contrib.

## Configure

```bash
cp .env.example .env
```

| variable | meaning |
| --- | --- |
| `TOMATO3D_DATA_ROOT` | root of the data tree (`raw/`, `calib/`, `derived/`, …) |
| `TOMATO3D_CONFIG_DIR` | folder holding the three config JSON files |
| `TOMATO3D_CAMERA_ID` | default camera id |
| `TOMATO3D_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / … |
| `TOMATO3D_MAX_WORKERS` | worker threads for per-frame work |

These are read once, in `tomato3d/config.py`. Nothing else touches `os.environ`, and no
call site concatenates a path — every derived path is a property on `Settings`.

Configuration lives in `config/`:

- `board_spec.json` — the printed board
- `capture_config.json` — the rig geometry
- `quality_thresholds.json` — session gating

A `null` threshold means "not yet determined by the pilot". It is **loaded but inactive**:
it never gates `usable_for_training`, and no default is substituted for it.

## Calibrate the camera

Shoot at least 15 usable views of the board, filling the frame from varied angles and
distances, then:

```bash
python -m tomato3d.cli.calibrate_intrinsics --images data/calib/intrinsics_shots/ --board config/board_spec.json --camera-id cam_a
```

Writes `data/calib/intrinsics_cam_a.json`. Fewer than 15 usable views is a hard failure
with the count in the message — exit code 1.

## Run one session

A session folder looks like this:

```
data/raw/DT-001/DT-001_20260915_0900/
  images/side_000.jpg … side_035.jpg
  images/top_T0.jpg … top_T4.jpg
  session_manifest.json
```

`session_id` is `<plant_id>_<YYYYMMDD>_<HHMM>`, and `plant_id` must be its prefix.

```bash
python -m tomato3d.cli.run_stage1 --session data/raw/DT-001/DT-001_20260915_0900
```

Writes, under `data/derived/DT-001/DT-001_20260915_0900/`:

```
poses.csv
masks/side_000.png …
quality.json
```

and prints a one-screen summary: images total, poses solved, masks written, mean
reprojection error, silhouette area CV, `usable_for_training`.

The three outputs are published as one set: they are staged first and swapped into place
only when every file has been written. A rerun therefore never leaves an earlier run's
masks beside the new `quality.json`, and a present `quality.json` always describes the
`poses.csv` and `masks/` next to it. Only those three are replaced; other files in the
folder are left alone.

Exit codes: `0` success, `2` a hard failure (missing config, unreadable manifest,
intrinsics from the wrong camera, a `board_variant_id` that does not match the spec, a
mask that cannot be written). A **per-frame pose failure is not a hard failure** — it is
recorded and the run continues.

A frame is refused before pose estimation — recorded as failed, and the session gated —
when it cannot be decoded (`unreadable_image`) or when its pixel size differs from the
calibration's (`image_size_mismatch_with_intrinsics`). A resized frame solved with the
original camera matrix gives a pose at the wrong distance with a *small* residual, so no
reprojection threshold would catch it.

All image IO goes through `tomato3d/io/images.py`. On Windows `cv2.imread` and
`cv2.imwrite` silently fail on non-ASCII paths — including this project's own folder —
so neither is called anywhere else.

## Run the tests

```bash
python -m pytest
```

Every test renders its own synthetic ChArUco view. No real photograph is required.

---

## Design rules this code obeys

### Why there is no SfM

The camera and the background are both static while the board rotates. COLMAP, OpenSfM
and any feature-matching pose estimator conclude that the camera never moved, and fail.
Camera pose comes **only** from ChArUco PnP, solved independently per frame, and
`pyproject.toml` lists no SfM dependency. Do not add one.

### Why ChArUco, not `findChessboardCorners`

The plant occludes most of the board. A plain chessboard detector needs the whole grid.
ChArUco identifies each corner from the ArUco markers beside it, so any visible subset
solves. The suite covers this: on the 7×7 board with 70 % of the board area occluded,
8 of 36 corners survive and the pose still solves.

### Why the board is built only from `board_spec.json`

`build_charuco_board` sets the marker ids **and** the legacy-pattern flag explicitly from
the spec, never from OpenCV defaults. If either disagrees with the print, markers are
still detected but matched to the wrong object points: the pose is wrong while every count
looks healthy. (OpenCV's legacy flag only changes the layout on boards with an even row
count, so it is a no-op on the operational 7×7 board — the explicit call protects any
even-row board added later. Both facts are pinned by tests.)

### Why `board_variant_id` is checked, not trusted

Several printed boards exist (`charuco_7x7_190mm` operational, `charuco_5x5_190mm`
spare) and their marker ids overlap, so detected ids cannot tell them apart. Every session
manifest carries `board_variant_id`; `run_stage1` refuses — exit code 2, before any
output is written — a session whose id differs from `board_spec.json::variant_id`.

### Why the board is rejected geometrically, never by colour

The substrate is vermiculite — as bright and as uniform as parts of the board, so any
colour rule that removes the board also removes the pot. Instead the board rectangle is
projected from the solved pose and everything on the board plane within its measured
extent is discarded. `board_plane_mask` never reads a pixel; it takes an image *shape*,
not an image.

The cost is worth knowing: anything that projects *onto* the board quad, rather than
above it, is discarded with the board. From a side view that is the pot and lower stem.
From a top view it is **the whole plant** — a synthetic T0 view keeps 0 of ~60,000 plant
pixels — so top views get no silhouette at all (see Known limitations). That is the price
of rejecting the board by its 2D projection, and it is why `segment_plant_silhouette`
keeps a stable boundary — a segmenter that keeps foreground above the board can replace
its body without touching a caller.

### `nominal_angle_deg` is never geometry

It is the commanded turntable angle, bookkeeping only. `measured_angle_deg` in
`poses.csv` is authoritative, and it is fitted from the pose sequence. The turntable axis
itself is QC only: no downstream geometry may depend on it.

### `unavailable`, never `0`

A value that could not be measured is written as the string `unavailable`. A failed pose
row keeps `session_id`, `image_file`, `view_type`, `top_position` and `pose_status`, and
writes `unavailable` in **every** numeric column — including `n_corners_detected`, even
though a count was observed. Side rows also carry `unavailable` for `top_position`, which
is structurally absent rather than unmeasured; the project uses one sentinel rather than
two, so no reader has to distinguish an empty cell from a missing one.

A metric that is `unavailable` cannot pass an *active* gate — it fails with an explicit
reason rather than being imputed.

### CSV for measurements, JSON for everything else

`tomato3d/io/tables.py` is the only module that imports `pandas` or `csv`.
`tomato3d/io/schemas.py` is the only place a column order or a document schema is
defined.

## Coordinate frames

Two frames appear, and they are not the same.

**Sheet frame** — OpenCV's ChArUco object-point frame. Origin at the printed sheet's
`origin_corner`, `+X` right along a row, `+Y` down along a column, `+Z` into the board.
Every `*_position_mm` and `*_center_mm` value in `board_spec.json` is given here, and the
file says so with `"position_frame": "sheet"`. On the 7×7 / 190 mm board,
`scale_block_position_mm = [13.57, 13.57]` is the centre of corner cell A1, and
`board_center_mm = [95, 95]`.

**Board frame** — the pipeline frame, and the frame of every number in `poses.csv`.
Origin at the board's **origin inner corner** (ChArUco corner id 0), `+X` along the rows,
`+Y` along the columns, `+Z` up and away from the board surface. All lengths in
millimetres; angles are degrees in files and radians in code, with a `_rad` suffix.

The two differ by a 180° rotation about `+X` plus a translation of one square in `X` and
`Y`. `tomato3d/calib/board.py::sheet_to_board_mm` is the only implementation of that
map. On the 190 mm board (27.14 mm squares) the printed sheet therefore spans
`x ∈ [−27.14, 162.86]`, `y ∈ [−162.86, 27.14]` in the board frame.

Because the board rotates with the plant, this frame is identical in every session.
Cross-date comparison needs no registration step. Do not add one.

## Layout

```
tomato3d/
  config.py              Settings, get_settings()
  logging_setup.py       configure_logging(level), used by every entry point
  io/
    schemas.py           every schema, CSV column order, the unavailable sentinel
    manifest.py          session_manifest.json, session path resolution
    tables.py            the only module that touches csv/pandas
    quality.py           QualityRecord build + write, threshold gating
  calib/
    board.py             ChArUco board, corner detection, sheet <-> board frame
    intrinsics.py        intrinsic calibration
    pose.py              per-frame PnP, turntable axis, measured angle
  mask/
    silhouette.py        plant mask, board/chart/block rejection, area CV
  light/                 leaf light-use under the LEDs (see below)
    units.py             unit conversions
    frames.py            board frame -> grow frame, fixture axes
    scene.py             lighting environment, scenarios, emitters, schedule, energy
    geometry.py          leaf_surfaces.csv / leaf_patches.csv, sampling
    raytrace.py          direct PPFD with shading
    budget.py            triangle / leaf / plant / scenario light and energy
    validate.py          predictions vs quantum-sensor readings
    compare.py           geometry variants vs a reference variant
    pipeline.py          one run, end to end
  cli/
    calibrate_intrinsics.py
    run_stage1.py
    run_light.py
  recon/ organ/ fuse3d/ graph/ pheno/ track/ rules/ twoview/   later stages (stubs)
```

## Known limitations at this stage

- **No top-view silhouettes, so no session is currently training-usable.** Rejecting the
  projected board removes a plant seen from above, and an empty or partial top mask would
  carve the plant out of a visual hull, so top views are not masked
  (`SUPPORTED_VIEW_TYPES = ("side",)`). The operational top view T0 is required, so every
  session is gated with `operational_top_view_silhouette_unavailable` until the board
  rejection can keep foreground that stands above the board. That needs a design
  decision; widening `SUPPORTED_VIEW_TYPES` without one reintroduces the defect.
- A side view whose pose solved but whose silhouette is empty publishes no mask and gates
  the session with `side_view_silhouette_unavailable`.
- Segmentation is classical (excess-green Otsu inside the board prism, largest
  connected component). The function boundary is what matters; a learned segmenter
  replaces the body.
- **No silhouettes until the scale block is measured.** `scale_block_nominal_height_mm`
  is `null`, so the block cannot be excluded from the silhouette. `run_stage1` still
  solves every pose, logs the reason once, writes no masks, records
  `silhouette_area_cv: "unavailable"`, and gates the session out of training with
  `silhouette_area_cv_unavailable`. No placeholder height is ever substituted.
- **The colour chart is not excluded.** It stands beside the board
  (`color_chart_on_board: false`) and has no position in the spec. From an elevated side
  view a chart beyond the far board edge projects into the plant candidate region, where
  its green patches can enter the silhouette. The run logs a warning.
- The scale block footprint is `scale_block_footprint_mm` when set, otherwise one board
  square (27.14 mm on the 7×7 board). A physically wider block overhangs that box and
  leaks into the silhouette — set the footprint when the block is measured.
- `max_scale_block_height_error_mm` is `null` and therefore inactive until the pilot
  measures it.

---

# Leaf light-use under the LEDs (`tomato3d.light`)

Photographs -> leaf surfaces -> placed under the lamps -> direct PPFD on every leaf with
mutual shading -> per-leaf light, daily light integral, absorbed photons, electricity ->
compared with quantum-sensor readings -> compared across lamp arrangements and across
geometry variants (e.g. fewer photographs).

It answers two questions with its outputs:

| question | read it in |
| --- | --- |
| How well does geometry from photographs predict the light around the leaves? | `validation.csv`, `evaluation` rows: each geometry variant against the same held-out readings, including the `no_plants` baseline |
| How few photographs keep that accuracy? | the same rows for a reduced-view variant, plus `geometry_variant_comparison.csv` against the multi-view reference |

What it computes is light **arriving at and absorbed by leaves**. Photosynthesis, growth
and yield are not computed and need their own measurements.

## Run

```bash
python -m tomato3d.cli.run_light --scene config/light_scene.json --geometry leaf_surfaces.csv leaf_patches.csv --readings ppfd_readings.csv --reference-variant multiview_41 --run-id pilot_0920
```

A worked example runs as is:

```bash
python -m tomato3d.cli.run_light --scene tests/fixtures/light/light_scene.example.json --geometry tests/fixtures/light/leaf_patches.example.csv --readings tests/fixtures/light/ppfd_readings.example.csv --reference-variant multiview_41 --run-id example
```

Every physical value in the example is a placeholder and its readings are synthetic, so
its numbers say nothing about any real plant.

Writes `<data_root>/outputs/light/<run_id>/`; an existing run folder is never
overwritten. Exit codes: `0` success, `2` a hard failure.

## Inputs

### The lighting environment - `light_scene.json`

`config/light_scene.json` by default (`Settings.light_scene_path`). It does not exist
until the lamps are characterised; copy `tests/fixtures/light/light_scene.example.json`
and replace every value.

Every physical value is written with its provenance:

```json
"photon_flux_umol_s": {"value": 60.0, "status": "manufacturer_spec", "source": "datasheet rev. B"}
```

`status` is one of `measured`, `manufacturer_spec`, `reconstructed`, `manual`,
`assumed`, `scenario`, `unavailable`. `value` is null exactly when the status is
`unavailable`. Anything not measured on this rig is listed in `run_summary.json`, and an
unavailable input makes every output that needs it `unavailable` - never 0.

| block | variables |
| --- | --- |
| `fixtures[]` | emitting-face centre (grow frame), aim tilt from straight down, aim azimuth, long-side azimuth, emitting length and width, emitter grid, photon flux (PPF, umol/s), half-intensity half-angle and cutoff, electrical input (W) and its boundary, daily schedule segments with output fraction (and measured power for dimmed segments) |
| `plants[]` | grow-frame position of the board origin and board yaw - the pose the capture board would have lying under the pot on the shelf - and whether the posture was checked after moving |
| `leaf_optics` | PAR absorptance, transmittance, reflectance |
| `simulation` | triangle subdivisions, ray offset, chunk size |
| `validation` | PPFD bin edges for error by light level (`null` = inactive) |
| `scenarios[]` | alternative arrangements: per-fixture position, tilt, azimuth, flux, power or switched off; per-plant position or yaw |

### Plant surfaces - board frame, mm

- `leaf_surfaces.csv` - triangles (`LEAF_SURFACES_CSV_COLUMNS`). Vertex order
  counter-clockwise seen from the upper side when `normal_convention = adaxial_ccw`.
  This is the table a reconstruction stage writes.
- `leaf_patches.csv` - one flat rectangle per leaf from centroid, area, normal tilt and
  azimuth, length-to-width ratio (`LEAF_PATCHES_CSV_COLUMNS`). Measurable with a ruler
  and a protractor before automatic reconstruction exists.

Rows with the same `geometry_variant_id` form one variant ("all 41 views", "T0 + 12
sides", "hand-simplified"). `no_plants` is reserved and always included.

### Quantum-sensor readings - grow frame - `ppfd_readings.csv`

Position, sensor normal, PPFD and a `split_role` assigned before anything is fitted:
`calibration` readings fit one lamp factor per scenario against the calibration variant
(default `no_plants`), applied unchanged to every variant; `evaluation` readings are the
held-out accuracy. Only readings with every enabled fixture at full output are supported.

## Outputs

| file | content |
| --- | --- |
| `run_summary.json` | inputs with provenance, non-observed inputs, variants, calibration factors, model limits, warnings |
| `leaf_triangle_light.csv` | the leaf light map: PPFD with and without shading, occlusion loss, upper-side share, DLI |
| `leaf_light.csv` | per leaf: area, mean/min/max PPFD, occlusion loss, DLI, intercepted and absorbed photons |
| `plant_light.csv` | per plant: leaf area, intercepted and absorbed photons, leaf PPFD CV |
| `scenario_summary.csv` | per arrangement x variant: emitted, intercepted, absorbed mol/day and their fractions, kWh/day, absorbed umol/J, changes vs `as_built` |
| `sensor_predictions.csv` | per reading: measured, predicted, calibrated, errors |
| `validation.csv` | MAE, RMSE, bias per split role (and PPFD bin), raw and calibrated |
| `geometry_variant_comparison.csv` | per plant: leaf area and absorbed photons vs the reference, matched-leaf PPFD MAE/bias, unmatched leaf counts |

## The model, and what it leaves out

- Emission `I(theta) = I0 cos(theta)**m` with a hard cutoff; `I0` is normalised so the
  lamp emits exactly its PPF. Irradiance `E = I cos(beta) / d**2`.
- A ray from a leaf sample to an emitter point is stopped by any non-leaf surface and
  multiplied by the leaf transmittance once per leaf it crosses. With the transmittance
  unavailable, such a ray is unavailable.
- Absorbed = incident x absorptance. Leaf area is counted once; a leaf has two faces, not
  two areas.
- **Not modelled:** reflection from walls, shelves and leaves (predictions read low where
  it matters), diffuse transmission, measured goniometric lamp profiles, sensor
  displacement of leaves, ambient light, and anything physiological.

## Coordinate frame added

**Grow frame** - the growing space under the lamps, mm, `+Z` up; its origin and axes are
described by the human in `grow_frame_description`. Fixture positions, plant placements
and readings are in it. Plant geometry stays in the board frame on disk;
`tomato3d/light/frames.py::board_to_grow_mm` is the only board -> grow map.
