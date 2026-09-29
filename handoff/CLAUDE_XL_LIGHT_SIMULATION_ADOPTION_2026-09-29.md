# Claude handoff: XL language adoption for GroIMP light simulation

## Purpose

The user wants to introduce GroIMP's XL/RGG language primarily for **light simulation**, not for immediate biological growth prediction. Treat XL as the bridge from the existing tomato image-derived structure into a GroIMP scene that can later run radiation/light-distribution experiments.

This handoff is for Claude Code planning and follow-up implementation review. It does not authorize retraining, new reconstruction, PPFD claims, growth-rule simulation, GitHub publication, or edits outside the current project scope.

## Current starting point

Relevant completed work:

- `tools/groimp_structure_export.py` exports static `Model.rgg` projects from existing pipeline snapshots.
- `tools/plant_xl_handoff.py` connects an existing S0-S7 run to static XL export and optional GroIMP CLI verification.
- `build/xl_handoff_20260928_122948/` is the newest locally verified static XL handoff for four plants.
- `build/colab_xl_hosted_return_20260928/` is the recovered hosted Colab static XL result for the older `pipeline_20260927_202748` snapshot.
- Local GroIMP CLI compile/reset/save/reopen has been verified for the newer static XL handoff.
- Real exports currently contain diagnostic organ nodes, stem/sub-stem axes and leaflet position markers; they do **not** contain validated complete leaf surfaces.

Status flags must remain:

- `validated_metric=false`
- `suitable_for_ppfd=false`

These flags mean the current XL outputs are good enough for structure transfer and software checks, but not yet validated as biological geometry or PPFD-ready leaf surfaces.

## Intended role of XL

Use XL/RGG in GroIMP for three light-simulation roles:

1. **Static scene construction**
   - Build a selectable plant graph from Python-exported organs.
   - Preserve plant/session/organ IDs, proposed versus confirmed relationships, and missing-geometry reasons.
   - Place only available diagnostic geometry: position markers, axes and reviewed meshes when available.

2. **Radiation experiment wrapper**
   - Define lamps, board/grow-frame coordinates, optional canopy layout and organ optical properties inside a reproducible GroIMP scene.
   - Run light/radiation calculations only after a minimal optical validation scene passes.
   - Output per-organ or per-sensor-plane light tables keyed by the original organ IDs.

3. **Scenario generator for later canopy tests**
   - Clone the static plant graph into density/spacing/rotation layouts.
   - Keep cloned organs marked as scenario copies, not new observations.
   - Use this for light-distribution comparison first. Do not add growth curves until time-series growth data exist.

## What XL should not do yet

- Do not infer hidden leaves or hidden depths from one view.
- Do not convert S7 diagnostic centres into validated leaf surfaces.
- Do not generate missing leaflets to satisfy growth JSON counts.
- Do not treat `compound_leaf` region proposals as confirmed biological parents.
- Do not rename display colour, raytracer energy or arbitrary surface irradiance as PPFD without unit reconciliation.
- Do not claim optimal planting density from light results alone.
- Do not add L-system growth rewriting as the first implementation step.

## Required data contract for a light-ready XL package

Reuse the existing static XL export and add only the minimum light-scene inputs. Prefer extending existing manifests over creating parallel stores.

### Inputs

- Static plant XL package:
  - `Model.rgg`
  - `organs.csv`
  - `relationships.csv`
  - `coordinates.csv`
  - `structure_snapshot.json`
  - `export.json`
- Optional reviewed geometry:
  - leaf mesh or triangle table, only when source and review status are explicit
  - identity map from mesh pieces to `plant_id/session_id/organ_key`
- Light scene:
  - lamp position, size, direction, spectrum or PPF
  - board-to-grow or board-to-lamp transform
  - sensor-plane location, area and normal if comparing against a PPFD sensor
  - leaf reflectance/transmittance/absorptance assumptions, with source or placeholder status
- Experiment manifest:
  - scenario ID
  - source run path and hashes
  - GroIMP version
  - XL model hash
  - whether geometry is observed, diagnostic, fitted or simulated

### Outputs

GroIMP/XL light outputs must be machine-readable CSV/JSON and keyed by original IDs:

- `scenario_id`
- `plant_id`
- `session_id`
- `organ_key`
- `geometry_source`
- `quantity`
- `unit`
- `value`
- `surface_or_sensor_plane`
- `calculation_status`
- `notes`

Required unit distinction:

- Incident PPFD: `umol m-2 s-1`
- Absorbed photon flux density: `umol m-2 s-1`, with optics specified
- Integrated photon rate: `umol s-1`
- Electrical efficiency or light-use efficiency must remain unavailable unless measured inputs exist.

## Recommended implementation sequence

### Phase 1: simple optical sanity scene

Create a tiny XL/RGG project independent of real plants:

- one flat square receiver
- one simple light source
- known distance and angle
- optional sensor plane matching the Python direct-light calculation

Goal: prove GroIMP output units, coordinate direction, surface sidedness and light-source assumptions. Compare this against the existing Python light module or an analytical inverse-square/cosine case.

Completion gate:

- same scene gives reproducible output
- units are recorded
- coordinate axes are documented
- differences from Python are explained by model assumptions, not hidden conversions

### Phase 2: static tomato snapshot light scene

Use `build/xl_handoff_20260928_122948/` as the first current-run source.

- Load existing organ graph.
- Display current positions/axes as diagnostic structure.
- Include reviewed leaf meshes only if an explicit reviewed mesh source exists.
- If no leaf surfaces exist, run only structure/scene checks and sensor-plane tests, not per-leaf PPFD claims.

Completion gate:

- every output row traces back to a source organ or sensor plane
- missing geometry is reported instead of skipped silently
- `validated_metric=false` and `suitable_for_ppfd=false` remain in the output manifest

### Phase 3: leaf-surface light pilot

After reviewed leaf surfaces become available:

- attach meshes to `Leaflet` nodes
- calculate incident and, if optics are supplied, absorbed light per surface
- compare a simple empty-scene/sensor reading before evaluating plant shading

Completion gate:

- source mesh provenance is explicit
- mesh normals/sidedness are verified
- sensor comparison is done at the sensor plane, not automatically at the leaf plane
- errors are reported as model error, not leaf physiological efficiency

### Phase 4: density and canopy scenarios

After Phase 1-3 pass:

- clone the static plant into spacing/rotation scenarios
- vary lamp height/angle
- compare upper/lower light distribution and uniformity

Completion gate:

- results are described as tested light-distribution scenarios
- no growth/yield optimum is claimed without growth or harvest data

## Claude review questions

Claude should review and decide these before implementation:

1. Which GroIMP radiation backend should be used first: CPU raytracer, GPUFlux or a minimal built-in radiation example?
2. What exact light quantity will be reported in the first version: incident PPFD, absorbed photon flux density or relative light score?
3. What minimal light-scene JSON fields are required for a repeatable test?
4. Should the first tomato run use only sensor-plane/empty-scene validation until reviewed leaf surfaces exist?
5. Which output table names and units should become the contract for later dashboard/RAG use?

## Codex implementation contract if approved later

If Claude approves the design, Codex can implement a narrow tool-first path:

- Add a light-scene adapter that consumes existing static XL exports and a light-scene JSON.
- Add a minimal GroIMP/XL radiation test project and verifier.
- Add parser/importer for GroIMP light outputs.
- Add tests for unit conversion, source hashes, missing geometry, organ ID traceability and stale inputs.
- Keep all outputs under a fresh `build/` directory.

Do not modify `docs/` from Codex. Do not mutate existing labels, masks, source photos or historical exports. Do not overwrite previous XL handoffs.

## References and local entry points

- `handoff/CODEX_LSYSTEM_XL_INTEGRATION_REVIEW_2026-09-27.md`
- `handoff/CODEX_STATIC_XL_IMPLEMENTATION_2026-09-27.md`
- `handoff/CODEX_PIPELINE_TO_XL_2026-09-28.md`
- `handoff/CODEX_COLAB_XL_BRIDGE_2026-09-28.md`
- `build/PIPELINE_FLOW_2026-09-28.md`
- `build/xl_handoff_20260928_122948/`
- `tools/groimp_structure_export.py`
- `tools/plant_xl_handoff.py`
- `tools/groimp_static_verify.py`
- `tomato3d/light/`

Primary GroIMP references already checked in prior review:

- XL/RGG language: https://wiki.grogra.de/doku.php?id=groimp-platform:xl-language
- Python integration through GroLink/GroPy: https://wiki.grogra.de/doku.php?id=tutorials:getting-started-with-grolink-and-gropy
- Crop radiation teaching example: https://wiki.grogra.de/doku.php?id=tutorials:radiation-model-in-crop_model8

## Bottom line

Introduce XL first as a **static light-simulation scene language** around the existing plant graph. Growth grammar comes later. The next useful milestone is not "tomato growth in GroIMP"; it is "a simple light scene with traceable units, then the current tomato graph with honest missing-geometry states."
