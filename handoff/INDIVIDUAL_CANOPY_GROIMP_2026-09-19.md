# Individual plant and canopy implementation checkpoint

## Latest user priorities

1. Label leaves across ChArUco-board photographs, recover depth, calculate upper/lower
   leaf PPFD, and combine growth-related geometry with flower/truss observations.
2. Place plant geometry into denser arrangements; compare lamp height/angle and canopy
   PPFD. Develop fewer-view operation independently from the full reconstruction.
3. Later: environment prescriptions and RAG/LLM assistance.

The user explicitly said there are no growth time series yet and selected **light
distribution/density comparison first**. No growth curve, yield optimum or agronomic
planting-density recommendation is claimed. Ordinary smartphone RGB remains the input;
the pasted RealSense/FEM workflow is reference material, not a hardware-switch request.

## Implemented support tools

### `tools/leaf_point_annotator.html`

Manual cross-view identities, same/new subject selection, reference images, and
one-observation split/relink are complete. Details: `CROSS_VIEW_LABELS_2026-09-19.md`.
The subsequent request adds a separate `truss` bbox class alongside `flower` and `bud`.
A flower bbox is not automatically a truss; there is no automatic flower-to-truss grouping.
Nineteen JavaScript regression tests now cover the annotator. Source is copied to
`build/leaf_point_annotator/leaf_point_annotator.html`; the hosted Claude artifact is unchanged.

### `tools/multiview_plant.py`

New standalone adapter for the user-confirmed **top 1 + 45/90/135-degree rings of 8 = 25**.
It leaves the older frozen 41-view research protocol and core capture config untouched.

```text
python -m tools.multiview_plant init --out build/new_capture_template
python -m tools.multiview_plant prepare --plan CAPTURE_PLAN.json --intrinsics INTRINSICS.json --out build/new_capture
python -m tools.multiview_plant reconstruct --capture CAPTURE.json --points POINTS.csv --contours CONTOURS.csv --review REVIEW.json --out build/new_leaf_geometry
```

- `init` writes a draft photo inventory and independent annotation review template.
  Actual file paths, plant/session/camera IDs and physical measurements must be supplied.
- `prepare` imports the existing ChArUco detector/PnP and authoritative board settings;
  the polar/azimuth labels never generate camera poses. Resolution/identity mismatches,
  missing photos, failed poses and physical scale blockers are reported.
- The output `capture.json` can be opened in the annotator. Add explicitly chosen photo
  subsets in the capture plan. Each reconstruction requires its own selected-image-only
  CSVs and operator review record; excluded image rows are refused.
- Existing `reconstruct_variant` provides triangulation and surface fitting. Output is
  compatible `leaf_surfaces.csv` plus `leaf_geometry_features.csv` (area and board-frame
  height/centroid per labeled leaf) and `reconstruction.json` diagnostics/provenance.
- These geometry features are not physiological diagnoses or whole-plant stem height.
- A failed selected pose produces failed reconstruction rather than an invented depth.
- Physical print verification/scale-block fields are still incomplete in current config.
  Horizontal/lower-view board visibility remains a real-capture obstacle.

### `tools/canopy_light.py`

```text
python -m tools.canopy_light --plan CASES.json --out build/new_canopy_comparison
```

The plan (`schema_version: canopy-light-1`) lists cases with:
`case_id`, `data_kind`, `scene`, `geometry`, `geometry_variant_id`, `plot_area_m2`,
`height_split_board_mm`, and `instances` (`plant_id`, `source_plant_id`, optional
validated `placement`). Paths are relative to the plan file. Optional `scenarios`
use the existing LightScenario fixture/placement override schema.

- `observed_geometry`, `hypothetical_layout`, and `synthetic` remain distinct.
  Renamed template copies cannot masquerade as observed individual plants.
- Scene parameters and the existing direct-light engine are reused. Each arrangement
  retraces all plant triangles together with mutual shading; individual PPFD scalars
  are never pasted into a canopy.
- Outputs include leaf/triangle/plant/scenario light tables, height groups, CSV/HTML
  comparisons, source hashes and core-engine warnings.
- Height groups use each leaf's area-weighted **board-frame centroid** and a supplied
  split height. They mean canopy level, not adaxial versus abaxial leaf face.
- Density is plant count / explicit floor area. Floor bounds, pot collisions and
  inter-plant mesh collisions are not currently solved. Leaf posture is static.
- Raw direct-light predictions are not quantum-sensor validation. The separate existing
  `tools.light_study`/light validation routes remain available; this command does not fit
  calibration factors or estimate prediction accuracy.
- Both light criteria are optional: `minimum_lower_leaf_ppfd_umol_m2_s` and
  `maximum_upper_leaf_ppfd_umol_m2_s`. Both must be supplied, and upper/lower leaf values
  available, to classify a case by light feasibility. Missing inputs never imply pass.
  The bounds apply to min/max **leaf means**, not every surface sample.
- No criterion is silently supplied from a generic tomato recommendation. A case meeting
  light criteria is not an optimal growing density. Growth/optimum outputs are unavailable.

## GroIMP folder inspection

Read-only inspection of `C:/Users/sho36/OneDrive/작업물저장소/홈팜/groimp` found:

- GroIMP **2.2.1**, verified from Platform/Raytracer plugin metadata.
- `core.jar`; `Raytracer`, `GPUFlux`, `CLI`, and `API` plugins; **72 bundled .gsz files**.
- Useful bundled examples: `LightVisualization.gsz`, `LampDemo.gsz`, `leaf3dDemo.gsz`,
  `IndexedFaceSet.gsz`, `FSPM.gsz`, and `CarrotField.gsz`.
- DXF plugin declares a Wavefront OBJ **import** filter (`de.grogra.ext.obj.ImportFilter`).
- API plugin exposes an API application and an HTTP port default of 58081; existence
  does not establish that a local service is currently running.
- No tomato-specific model was identified in this folder inspection.
- `GroIMP.lnk` is broken: TargetPath is the old desktop folder's **groimp.ico**, and its
  WorkingDirectory is also that previous location, not this installation.
- Boot Main.class has class-file major version **65** (Java 21). No `java`/`javap` was
  found on the current shell PATH, and no Java runtime was found inside this folder or
  `C:/Program Files/GroIMP 2.2.1`. This is not proof that Java is absent everywhere.
- No installer was run, shortcut repaired, service opened, or GroIMP folder modified.

### `tools/groimp_bridge.py`

```text
python -m tools.groimp_bridge --geometry LEAF_SURFACES.csv --variant v25 --scene SCENE.json --out build/new_groimp_export
```

Exports `leaves_m.obj`, `identity_map.csv` and `export.json`. Omit `--scene` to keep
the board frame; with a scene it reuses the sole authoritative board-to-grow transform.
mm -> m conversion occurs once. Open leaf surfaces and identity metadata are preserved.
No watertightness filling is applied. GroIMP import/lighting execution is **not verified**
because the Java launch environment has not been established. RGB radiometric power
must not be relabeled PPFD; leaf optics and photon-band conversion need explicit review.

## Reference guide interpretation

The pasted guide's universal watertight-mesh requirement applies neither to our ray
intersection calculation nor automatically to every physics solver. Filling gaps
between leaves changes canopy transmission. RealSense alignment is relevant to a future
RGB-D input route, not required by the current smartphone route. A green/red dynamic
growth recipe remains a biological hypothesis, not implemented or validated guidance.

Primary references consulted:
- Open3D RaycastingScene: https://www.open3d.org/docs/latest/python_api/open3d.t.geometry.RaycastingScene.html
- GroIMP crop radiation tutorial: https://wiki.grogra.de/doku.php?id=tutorials%3Aradiation-model-in-crop_model

## Verification and examples

Targeted command:
`python -m pytest tools/tests/test_multiview_plant.py tools/tests/test_canopy_light.py tools/tests/test_groimp_bridge.py tools/tests/test_leaf_annotator.py -q`

Result: **14 pytest items passed**, including a wrapper running **19 Node regressions**.
Verified known-projection 25-view geometry/area/height recovery, two-view independent
reconstruction, excluded-view refusal, failed-pose handling, light height dependence,
area weighting, explicit density, unavailable growth, invalid cases, and OBJ unit/identity
transport. No new board renderer was created. Browser manual-label checks are recorded in
the cross-view handoff; real file chooser automation was inconclusive.

Generated examples (all synthetic, not experimental findings):

- `build/multiview25_20260919/capture_plan.draft.json`
- `build/individual_canopy_demo_20260919/synthetic_inputs/plan.json`
- `build/individual_canopy_demo_20260919/comparison/comparison.html`
- `build/individual_canopy_demo_20260919/reconstruction25/leaf_surfaces.csv`
- `build/individual_canopy_demo_20260919/groimp_export/leaves_m.obj`

## Remaining model work / Claude review

These are functioning support components, **not completion of all requested models**.

1. Multi-task learned vision (growth disorders, truss detection, cross-view automation)
   is not trained: reviewed real labels, split policy, training data and model validation
   are still needed. Manual truss labels are now collectible without confusing flowers.
2. Canopy fewer-view accuracy/minimum view count has not been established. Independently
   annotate/evaluate each selected layout; test on held-out plants and occlusion levels.
3. Review static geometry collisions and floor footprint, treatment of failed/incomplete
   leaf reconstructions, numerical sampling convergence, reflectance and calibrated PPFD
   before ranking canopy layouts as useful configurations.
4. Establish Java 21+ launch environment and review a GroIMP optical model before claiming
   GroIMP integration beyond geometric export. Existing Python engine remains available.
5. Growth curves, agronomic density optimum and RAG/environment prescriptions are deferred
   in line with the user's latest answer. No `tomato3d/`, `tests/`, `config/` or `docs/`
   files were edited.
