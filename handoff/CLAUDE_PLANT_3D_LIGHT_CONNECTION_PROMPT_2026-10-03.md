# Connect reconstructed tomato plants to the existing light simulator

Implement the connection between the existing plant reconstruction outputs and the existing GroIMP light workflow. This is the prerequisite to later growth-simulator integration. First make plant geometry, lighting and calculated light results traceable in one workflow. Do not implement growth laws or claim flowering, biomass, yield or optimum-density predictions in this task.

## Read the current implementation before editing

Work inside `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.

Read `CONVENTIONS.md`, agent-specific instructions, the latest `handoff/LOG.md` and `handoff/TODO.md`, followed by:

- `handoff/CLAUDE_TO_CODEX_MASTER_HANDOFF_2026-10-03.md`
- `handoff/CLAUDE_PPFD_VALIDATION_COMPLETION_2026-10-02.md`
- `handoff/CODEX_GROWTH_CONNECTION_FIX_2026-10-03.md`
- Existing `tools/plant_pipeline.py`, `tools/plant_traits.py`, `tools/groimp_structure_export.py`, `tools/vein_surface_bridge.py`, `tools/groimp_density.py` and `tools/ppfd_validation.py`.
- Existing `tomato3d.light` geometry, placement and light-table contracts.

Reuse those contracts and functions. Do not build another annotation application or another photon-transport engine. Respect the existing freeze on `groimp_structure_export.py`, `groimp_static_verify.py` and `groimp_bridge.py`: import them unchanged, and document owner-side changes if necessary. Preserve photos, labels, masks, reviewed identities, calibrations, model weights and historical results. Do not edit human-owned `config/` or human measurement records.

No new training or remote upload is authorized by this prompt. Use existing results first. Heavy inference, if subsequently needed and authorized, belongs on Colab/Kaggle. Do not push GitHub changes.

## Objective and practical scope

The current primary research scope is whole-plant leaf area, PPFD/DLI and plant-intercepted light, with minimal human effort. Per-leaflet identity, landmarks and exact reconstruction are optional refinement routes, not a mandatory full-dataset labeling requirement.

Implement this sequence:

```text
Existing plant run and its source snapshots
  -> geometry and input audit
  -> explicit optical-scene eligibility
  -> existing GroIMP scene preparation and execution
  -> sensor and plant light tables
  -> linked 3D result view and provenance
  -> later, separately calibrated growth-model input
```

Start with one existing plant/session with the strongest usable evidence, preferably dwt_01 if the audit supports it. Then exercise other plants as supported inputs and explicit missing-input cases. Do not silently choose the newest file from unrelated runs or combine sessions merely because plant IDs match.

The October 2 PPFD handoff reported no reviewed real leaf surfaces or physical PPFD measurements. Re-audit current artifacts; that historical statement is not evidence that newer geometry exists or does not exist. Native synthetic checks have been reported, but they do not validate the real plant or lamp setup.

## 1 Audit and freeze the inputs

Create an adapter, preferably `tools/plant_light_bridge.py`, integrated with the existing job/result flow. Its preparation interface should accept an explicit plant run, plant ID, session ID, optional geometry/variant, optical study inputs and a new output directory under `build/`. Provide `--help`; use exact existing schemas rather than parallel ad hoc formats.

Produce an immutable manifest containing:

- Plant ID, session ID, capture date, run ID and input file hashes.
- Camera/board frame, length units, quality status and pose provenance.
- Mask review status and geometry source; distinguish manual review from model acceptance.
- Geometry counts by kind and source, usable surface area and completeness evidence.
- Light-scene, lamp-adapter, placement, optics, sensor, solver and review hashes.
- Each unavailable input and what operation it blocks.

Read dates from explicit source metadata or an explicitly supplied mapping with provenance. Never manufacture capture dates from file modification time. Conflicting dates or source hashes must produce a clear failure. If a legacy run lacks a capture date, preserve it as unavailable and block date-dependent joins.

Integrate or explicitly reuse the elevation-based view grouping documented in `build/dwt_test_fill_20261003/`. Do not infer top/side views solely from photograph numbers. Record measured elevation, grouping settings and coordinate centre; do not copy that scratch script's hardcoded centre into a generic pipeline.

For dwt_t3, preserve the established movement groups and failed alignment status. Do not merge the unaligned group into one rigid optical scene. If registration changes, preserve the original groups, transforms and supporting evidence.

## 2 Separate visible geometry from optical geometry

Inventory geometry before generating RGG:

| Existing evidence | Display use | Optical use |
|---|---|---|
| Confirmed or diagnostic positions | Position markers | Never leaf receivers or occluders |
| Bbox extents and plant hull | Extent inspection | Never silently substitute for leaf tissue |
| Display axes | Structural context | No optical participation without a separate physical geometry model |
| Leaf triangles reconstructed from image evidence | Source-labelled mesh | Subject to existing surface/normal/completeness gates |
| Inferred/interpolated triangles | Distinctly labelled mesh | Assumption-specific diagnostic route only; no promotion to measured surfaces |

Use existing surface reconstruction and `vein_surface_bridge` outputs when they are actually available. Preserve measured landmark evidence separately from interpolated surfaces. A closed watertight leaf solid is not required for the existing triangular receiver workflow; do not fill inter-leaf gaps to create a solid canopy.

Partial surfaces can produce partial-scene diagnostic light results only. Missing leaves can change shadows on retained leaves, so neither local nor whole-plant accuracy follows from a successful partial run. Report geometry completeness and excluded components. Do not extrapolate complete plant absorption from a few available leaf triangles.

If no usable surfaces exist, still implement and validate the connection using clearly separated synthetic fixtures and generate a real-input blocker report. Do not report that as real plant simulation success. If a simplified canopy model is proposed to reduce human work, specify its optical assumptions and validation plan separately before implementing it; never bypass the current real-surface gate or disguise a hull as reconstructed leaves.

## 3 Reuse GroIMP lighting and validation

Use `tools/ppfd_validation.py` for input auditing, light setup, empty-rig calibration, native execution and sensor comparison; use `tools/groimp_density.py` for existing surface/placement/result helpers where appropriate.

- Keep board geometry in mm at the pipeline boundary, place it through the existing grow-frame transform, and convert to metres exactly once through shared helpers.
- Reuse the documented directional emitter adapter. Verify the supported distribution and solver from code; do not silently replace it with an isotropic lamp.
- Keep emitting PPF in micromol/s, sensor incident PPFD in micromol/m2/s, and electrical power in W as different quantities. Follow the existing photon-valued GroIMP power convention; do not perform a second watt-to-photon conversion.
- Input leaf reflection/transmission and lamp parameters with their source/status. Missing values stay unavailable; explicit assumptions, if supported by an existing diagnostic route, must remain labelled and excluded from physical validation.
- Calibration uses designated empty-rig development measurements. Plant evaluation measurements must not fit lamp or geometry parameters. Preserve the existing frozen split and hashing checks.
- Preserve solver seed, ray count, bounce depth and convergence evidence. Python direct-light and GroIMP reflected/transmitted results are not automatically equivalent.
- Exclude display markers and annotation overlays from optical calculations. Preserve sensor position, sensing-face orientation and area averaging.

Use existing CLI commands after verifying their arguments:

```text
python -X utf8 -m tools.ppfd_validation audit --study <study.json> --out build/<fresh_audit>
python -X utf8 -m tools.ppfd_validation run --study <study.json> --out build/<fresh_prepared>
```

The second command prepares without native execution unless `--execute` is added. Actual run and comparison require eligible inputs; do not turn missing thresholds into silent defaults. For missing physical inputs, return an actionable audit while continuing independent software integration and synthetic tests.

## 4 Keep numerical meanings distinct

Export numerical tables as CSV and settings/provenance as JSON. Reuse existing output tables where possible and add a join table rather than changing their meaning.

Every result must resolve to plant/session/capture date, geometry revision, scene/placement, solver run and source surface or sensor. Keep these quantities distinct:

1. Sensor-plane incident PPFD, for comparison with the quantum sensor.
2. Incident irradiance/PPFD on leaf faces, with the existing front/back convention.
3. Absorbed photon flux per surface and summed over explicitly covered plant surfaces.
4. Whole-plant area-weighted light summaries; do not average triangle PPFD without area weights.
5. DLI, integrated over a known lighting schedule. Constant PPFD times photoperiod is valid only for a stated constant-light interval.
6. The older `plant_traits.intercepted_mmol_d`, a projected-area interception proxy. It is not GroIMP absorbed photons or photosynthesis.

Codex corrected `plant_traits.py` on October 3:
- Measurement joins now use plant/date/optional session. Ambiguous records fail instead of overwriting; unmatched inputs remain unavailable. Single undated legacy joins are explicitly identified.
- Calibration diagnostics hold out all dates of one plant together. Diagnostic errors do not set `validated_metric=true`.
- Absorbed-photon and photosynthesis outputs remain null; the legacy interception field is labelled as a proxy.

Do not undo these safeguards. Do not use a saved legacy summary's validation flag as evidence of physical accuracy. Carry source dates into new S8 results from explicit metadata rather than guessing them.

## 5 Connect the existing result viewer

Extend the current viewer/job pages with a light-results layer and a concise input/status panel:

- Original source image/mask, structural geometry, optical leaf surfaces and light heatmap.
- Clear labels for diagnostic, assumed, partial, unmeasured and validated states.
- Surface selection revealing plant/session/organ IDs, source photos, geometry origin, area and the exact light quantity shown.
- Sensor locations and predicted-versus-measured results where measurements exist.
- Missing-surface and missing-lamp/sensor input lists without fabricated zero values.

If automatic surface IDs exist without physical leaflet IDs, preserve that distinction. Do not manufacture cross-view identities merely to label a heatmap. Whole-plant aggregation remains possible for a justified optical representation without forcing individual human labels for every leaflet.

Light results depend on geometry, optics, placements, lamp settings and solver settings. Any changed dependency makes the previous result stale; recomputation writes a new run. Do not overwrite historical results or mutate reviewed source geometry.

## 6 Validation and delivery

Test at least:

- mm-to-m conversion and board-to-grow placement without double transforms.
- Plant/session/date isolation, duplicate records and input-hash mismatches.
- Visual markers excluded from transport; missing and partial surfaces reported correctly.
- Surface IDs and area-weighted aggregation preserved; mesh subdivision does not change an area-weighted mean solely by changing triangle count.
- Sensor normals and area averaging, opaque shadow and transmission using existing fixtures.
- Fixed-seed reproducibility and the existing convergence/energy checks.
- Missing PPFD, unknown schedule and absent optics stay unavailable.
- No validation success caused by a diagnostic metric merely existing.
- Stale detection after edits, and source-file hashes unchanged after running.

Deliver code, focused tests, reproducible CLI commands, a geometry/input audit, a prepared or executed scene with its true status, source-linked result tables/viewer and an English completion handoff. Report synthetic verification separately from actual plant/lamp validation. For real jobs, distinguish prepared, native execution completed, physical validation pending and blocked states.

Only after this connection is verified should a separate task feed dated plant states and light outputs into `tools/growth_simulator.py`. That simulator currently starts a procedural demo from development day zero; it is not an observed-plant growth model. Do not fit or introduce biological growth rules, CO2-dependent photosynthesis or first-flowering predictions in this task.
