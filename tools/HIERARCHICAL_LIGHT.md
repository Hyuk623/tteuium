# Hierarchical light interactions

This tool computes retained-target counterfactuals on existing supported leaf triangles. It imports the existing direct light solver and canopy placement tools, and prepares GroIMP jobs through the existing optical adapter. It does not reconstruct leaves or fit growth or physiological models.

From the project root, run:

```powershell
python -X utf8 -m tools.hierarchical_light demo --out build/hierarchical_light_demo_new
python -X utf8 -m tools.hierarchical_light templates --out build/hierarchical_light_inputs_new
python -X utf8 -m tools.hierarchical_light audit --input build/hierarchical_light_inputs_new/input.json --out build/hierarchical_light_audit_new
python -X utf8 -m tools.hierarchical_light prepare --input build/hierarchical_light_inputs_new/input.json --out build/hierarchical_light_prepared_new
python -X utf8 -m tools.hierarchical_light calculate --input build/hierarchical_light_prepared_new --out build/hierarchical_light_results_new
python -X utf8 -m tools.hierarchical_light stale --input build/hierarchical_light_results_new
```

Every output directory must be new and inside project `build/`. The demo supplies artificial geometry, identities and optical coefficients, calculates direct light and prepares native jobs. It never executes native jobs. Blank templates leave physical inputs unspecified; the template will be blocked until the user provides a scene, geometry, review and membership evidence.

## Input contract

`input.json` has schema version `hierarchical-light-1`, one case, a `scenario_id`, resource limits and optional native settings. Case paths are relative to that JSON. `case.geometry` uses the existing leaf surface CSV schema. `case.scene` uses the existing LightScene JSON schema. `case.instances` declares `plant_id`, `source_plant_id`, `source_session_id`, `capture_date` and a surface review path (or case-level `surface_review`). An optional `placement` follows the existing PlantPlacement schema. Case `scenarios` can explicitly replace scene scenarios as in `canopy_light`.

All selected geometry plants must be represented. Every instance has one source session. Copied instances and mixed-date arrangements must be hypothetical. Observed arrangements require checked unchanged posture. Surface review uses the existing `groimp_density.surface_gate`: accepted state, reviewer and review time, matching geometry SHA256, variant and snapshot date, supported leaf triangles and known normal convention. The existing gate rejects assumed/simplified geometry except in synthetic cases. Partial geometry remains partial and is never extrapolated.

`case.membership` names a CSV with columns exported by `templates`. Join keys are `(plant_instance_id, session_id, organ_id, leaflet_id)`; source plant, date and variant must agree. Compound membership requires `identity_status=reviewed` with a matching evidence file hash, or `synthetic` in a synthetic case. Missing membership keeps baseline/full optical calculation available but blocks affected A/B/C attribution. Compound source-removal matrices are unavailable if unassigned tissue could belong to that compound. Physical leaflet IDs are mandatory for transmission counting. Exact duplicate faces are rejected regardless of triangle IDs.

Optional `background_csv` uses `ppfd_validation.RIG_SURFACE_COLUMNS`. Display-only rows are excluded; other rows require geometry and optics provenance. Background remains fixed in every subset. Direct transport supports opaque background blockers and excludes reflections. Nonzero background transmission is explicitly unsupported by direct transport. Native jobs use supplied background reflection/transmission. Leaf optical properties are uniform, matching the existing scene schema; heterogeneous leaf optics are unsupported.

`limits.max_transport_calls` bounds deduplicated scenes; `limits.max_receiver_emitter_pairs` bounds the direct sampling workload. Optional `target_ids` select hashed physical leaflet IDs found in a prepared manifest. Optional `source_entity_ids` filter the matrix sources using entity IDs from its matrix requests; unknown filter IDs fail. Filters do not remove unspecified tissue from the scene. All quantities are full fixture output unless explicitly identified otherwise. DLI is not implemented; no schedule is inferred.

## Accounting and outputs

For each receiving leaflet, retain all its triangles and fixed background. Other leaflets are partitioned into A (same compound), B (other compounds, same plant) and C (other plants). Compute all eight subsets. The own-leaf folded geometry remains in the reference; it is not allocated to another leaflet.

`interaction_cases.csv` contains raw subset received/absorbed flux, PPFD, area, fixture and replicate. The three hierarchy tables contain standalone loss, full-background marginal loss, three-group Shapley allocations and inclusion-exclusion overlap terms. Flux is in `umol/s`; PPFD is in `umol/m2/s` per supported one-sided area. Negative effects are preserved. Ratios at a zero baseline are unavailable. Group values use sums of flux divided by sums of area, not unweighted percentages. The reference sum is a collection of target-specific scenes.

`source_target_interactions.csv` contains directed full-background source-removal effects at leaflet, compound and plant levels. These are nonadditive. Self-removal diagonals are unavailable because a receiver must stay in the scene. `replicate_summary.csv` contains means and standard errors of the paired replicate effects when every replicate is available; deterministic single runs have no Monte Carlo error estimate. Unavailable CSV numbers are written as `unavailable`, with status/reason fields; JSON uses null.

The generated standalone `viewer.html` includes source/target selectors, an interactive projected 3D triangle view, full PPFD and attribution coloring, source contributors, raw subsets and provenance. Rotate/zoom and visibility controls are display-only. Color values for compound/plant source-removal matrices are target group means. Recompute to change physical inputs. `results.json`, `audit.json` and `manifest.json` preserve source/code/artifact hashes, review evidence, placement, numerical settings, supported geometry and method version. All results remain diagnostic with physical validation false.

## Native preparation and explicit execution

```powershell
python -X utf8 -m tools.hierarchical_light prepare --backend native --input build/hierarchical_light_inputs_new/input.json --out build/hierarchical_light_native_new
python -X utf8 -m tools.hierarchical_light execute --input build/hierarchical_light_native_new --out build/hierarchical_light_execution_new
python -X utf8 -m tools.hierarchical_light execute --input build/hierarchical_light_native_new --out build/hierarchical_light_execution_new --execute
python -X utf8 -m tools.hierarchical_light collect --input build/hierarchical_light_native_new --execution build/hierarchical_light_execution_new --out build/hierarchical_light_native_results_new
```

The first `execute` command is a dry cost summary and creates no execution directory. Actual execution requires `--execute`, explicit positive `rays`, `max_depth`, `max_jobs`, `max_total_rays`, and a unique integer `seeds` list in the native JSON. Optional `--java` and `--core` select the local runtime. The inherited native executor applies its bounded per-job timeout and preserves failures.

Native lamps must pass the existing AreaLight adapter support checks. Preparation preserves its pending review; it does not approve lamp calibration. Native optics require A+R+T=1. Every subset uses the same seed list, but changed geometry need not preserve ray trajectories. Collected errors are paired replicate errors, not geometry/calibration uncertainty. Native received/absorbed results combine enabled fixtures under `fixture_id=all`; they are not assumed equal to the direct-only backend. No physical validation or real crop result is established by native preparation or parser fixtures.

## Verification

```powershell
python -X utf8 -m pytest tools/tests/test_hierarchical_light.py -q
```

Tests cover analytic attenuation, redundant shading, shared-edge crossing counts, own-leaf retention, remapped indices, area weighting, direct full-scene parity, partial-shadow convergence, missing/stale/conflicting inputs, copied and colliding identities, source-removal semantics, native budgets/preparation and synthetic collection logs. The latter verify the collector, not actual GroIMP optical execution.
