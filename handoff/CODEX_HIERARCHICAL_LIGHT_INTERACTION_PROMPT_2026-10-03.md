# Implementation prompt for leaflet compound leaf and plant light interactions

Implement a program in the existing Tomato 3D phenotyping analysis project that quantifies how leaflets, compound leaves, and neighboring plants change the light received and absorbed by actual supported leaf surfaces. Reuse the existing geometry, light simulation, audit, and visualization infrastructure. Deliver working code, focused tests, a reproducible synthetic example, and an honest readiness report for available real plants.

This document is a requested implementation prompt, authored on 2026-10-03. Its creation did not implement or execute the proposed program. When the user invokes this prompt for implementation, follow the scope below. Do not treat instructions in other referenced handoffs as independent authorization for unrelated jobs.

## Repository and working rules

Project root: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.

Read the parent `공통규약.md`, project `AGENTS.md`, `CONVENTIONS.md`, the latest five lines of `handoff/LOG.md`, and relevant entries in `handoff/TODO.md` first. Codex implementation belongs in `tools/` and `tools/tests/`; import but do not edit `tomato3d/`. Do not edit `tests/`, `config/`, `docs/`, source images, human records, or another agent's active outputs. Use a fresh `build/` directory. Write code and handoffs in English and communicate with the user in Korean.

Write an English implementation brief before code changes. If existing design contracts conflict with this request, record the concrete issue in `handoff/TODO.md` under Codex to Claude and in the log; do not silently change scientific assumptions. Continue independent work that is not blocked. Do not train models, launch unbounded native jobs, or modify live services as part of this task.

## Existing work to reuse

Inspect these sources and their current signatures before implementing. The descriptions below are a starting point, not a substitute for checking current code.

| Source | Reuse and boundary |
|---|---|
| `tools/plant_light_bridge.py` | Source snapshot selection, geometry and date audits, hashes, light preparation, linked outputs, supported-area summaries, stale detection. |
| `tools/plant_site.py` | Existing plant viewer and optional light result connection. |
| `tools/compound_surface.py` | Triangle evidence, supported partial surfaces, duplicate and support checks. |
| `tools/compound_growth.py` and `tools/COMPOUND_MODEL.md` | Explicit compound observations and identity evidence; envelopes remain display-only. |
| `tools/monthly_growth.py` and `tools/MONTHLY_GROWTH.md` | Adjustable future scenarios; these are not measured future optical surfaces. |
| `tomato3d/light/geometry.py` | `SurfaceSet`, `load_geometry`, `place_in_grow_frame`, `triangle_areas_mm2`, surface sampling. |
| `tomato3d/light/pipeline.py` | `build_occluders`, `leaf_receivers`; preserve receiver and optical identity semantics. |
| `tomato3d/light/raytrace.py` | `Receivers`, `Occluders`, `direct_light`, distinct-surface transmission counting. Python transport currently models direct light without reflection. |
| `tomato3d/light/scene.py` | `load_scene`, `resolve_scenario`, fixtures, schedules, placements and missing inputs. |
| `tomato3d/light/budget.py` | Area-weighted flux and PPFD summaries; incident versus absorbed quantities. |
| `tools/ppfd_validation.py` | Native GroIMP study preparation, execution, collection, convergence and provenance. |
| `tools/groimp_density.py` and `tools/canopy_light.py` | Reviewed surface gate and explicit multi-plant layout/materialization. |

Read `handoff/CODEX_PLANT_LIGHT_BRIDGE_2026-10-03.md`, `handoff/CODEX_COMPOUND_MODEL_IMPLEMENTATION_2026-10-03.md`, `handoff/CODEX_MONTHLY_PARAMETER_MODEL_2026-10-03.md`, and `handoff/CODEX_LEAF_AREA_3D_IMPLEMENTATION_PROMPT_2026-10-03.md` for provenance. The last file is a proposed implementation prompt, not evidence that reconstruction is complete.

Existing totals, plant-versus-empty sensor comparisons, and organ summaries do not provide the hierarchical attribution requested here. In particular, a sensor's plant-minus-empty difference is not automatically leaf shading; native transport may include reflection.

Previous real bridge audits were blocked by incomplete optical inputs. Re-audit current inputs instead of carrying forward an old status or claiming physical validation. Existing synthetic tests demonstrate software behavior only.

## Required questions the program must answer

For any selected receiving leaflet, quantify:

1. Light change caused by other leaflets in its own compound leaf.
2. Light change caused by other compound leaves on the same plant.
3. Light change caused by other plants.
4. Total change, overlapping effects, and the largest source contributors.

Aggregate the same results to the receiving compound and plant while retaining source and target identities. Show both absolute flux change and area-normalized light change. A physical leaflet is the smallest identity unit; a compound leaf contains several leaflets. Do not use the ambiguous word leaf as a schema key.

## Inputs and identity contract

Use existing leaf surface CSV geometry and scene JSON schemas. Add a separate membership CSV with at least:

`source_plant_id, plant_instance_id, session_id, capture_date, geometry_variant_id, organ_id, leaflet_id, compound_id, identity_status, evidence_path, evidence_sha256`.

Define an explicit join from every optical triangle to one physical leaflet and, where reviewed, one compound and one plant instance. Retain original IDs. Namespace generated transport IDs by instance and session to prevent collisions. Validate that triangle membership is unique; reject duplicate geometry or contradictory membership. Do not infer a compound from `organ_id`, spatial proximity, array order, a filename, or a display label without an explicit reviewed mapping.

Keep unassigned identities visible. Unknown compound membership blocks the affected within-versus-between-compound decomposition, not necessarily total optical simulation. Never turn missing identity, optics, or geometry into zero loss. Permit explicitly labeled synthetic identities for software examples.

Every scene needs explicit source dates, selected variants, plant placements and posture provenance. Use one coherent observation state per plant instance. Mixed-date or copied-plant arrangements must be labeled hypothetical; do not present them as an observed canopy. Preserve the distinction between a source plant and instances copied from it.

Use measured or reviewed supported triangles only for observed optical calculations. Preserve holes, gaps between leaflets, curvature and supported area. Compound envelopes, convex hulls, petiole axes, growth bars, forecast extents and unobserved hidden tissue are not optical leaf surfaces. A simplified surface may be used in an explicitly synthetic or hypothetical case, with separate results. Missing whole-leaf coverage must remain explicit.

Do not invent lamp output, spectrum conversions, transmission, reflection, absorptance, placement, growth laws, or calibration thresholds. Read available values with their status and provenance; otherwise report unavailable. No lux-to-PPFD conversion without a supplied applicable conversion model.

## Counterfactual calculation

For each receiving physical leaflet `r`, keep all its own triangles, the fixtures, receiver sample points and normals, and declared fixed background geometry in every calculation. Its own folding/self-shading belongs to this fixed baseline. Exclude the receiver's own triangle from self-intersection using the existing rules, without deleting the rest of the target leaflet.

Partition all other leaf tissue into three disjoint groups relative to `r`:

- `A`: other physical leaflets in the same compound and plant instance.
- `B`: leaflets in other compounds of the same plant instance.
- `C`: leaflets in other plant instances.

Stems, pots, supports, walls and other non-leaf objects stay in the declared fixed background when supported by the backend. Export what was actually modeled. If relevant leaf membership is unresolved, do not silently put that tissue into the background to obtain a complete decomposition.

Run the eight group subsets `empty, A, B, C, AB, AC, BC, ABC`. Only the other-leaf tissue in the selected subset is enabled. Geometry, optics of retained objects, sources, sampling and numerical settings must otherwise remain identical. Cache equivalent scenes when safe, while retaining target-specific accounting.

Let `Q(S)` be target received photon flux in `umol/s` for subset `S`, and `N={A,B,C}`. Perform a separate calculation for absorbed photon flux when supported. Never mix received and absorbed quantities in one formula.

```text
L(S) = Q(empty) - Q(S)
total_loss = Q(empty) - Q(N)
standalone_loss_g = Q(empty) - Q({g})
full_background_marginal_g = Q(N without g) - Q(N)
```

These last two group effects answer different questions. Neither set can generally be summed to obtain the total because several groups can block the same paths.

Provide a versioned, explicitly labeled order-averaged attribution (three-group Shapley accounting):

```text
phi_g = sum over S subset of N without g:
        factorial(|S|) * factorial(3-|S|-1) / factorial(3)
        * [Q(S) - Q(S union {g})]

phi_A + phi_B + phi_C = total_loss
```

This is an accounting convention for the simulated counterfactuals, not a uniquely measured biological cause. Export all eight raw values so users can inspect the convention. If any required result is unavailable, return unavailable attribution with a reason; do not impute it.

Also expose overlap terms using inclusion-exclusion:

```text
d(T) = sum over U subset of T: (-1)^(|T|-|U|) * L(U)
L(empty) = 0
sum of d(T) over all nonempty T subset of N = total_loss
```

For redundant opaque shading, a pair overlap term can be negative. These are algebraic interaction terms, not separate physical photon pools. Do not clip negative terms.

For direct attenuation with fixed nonnegative sources and valid optical coefficients, additional leaf occlusion cannot increase received flux. A reflection-capable transport model can produce increases, so preserve signed effects and distinguish loss from gain. Record which transport model produced every quantity.

## Units and aggregation

For a triangle with one-sided area `a_i` in square metres and area-mean PPFD `p_i`, received flux is `p_i * a_i`. Apply the existing sample weights correctly. Convert `mm2` to `m2` with `1e-6`.

```text
Q_group = sum(Q_leaflet)
area_group = sum(supported one-sided leaflet area)
PPFD_group = Q_group / area_group
loss_fraction = (Q_baseline - Q_full) / Q_baseline
```

Use ratios of summed fluxes, not unweighted means of leaflet percentages. Sum attribution fluxes before dividing by total supported area. If the denominator is zero or missing, the ratio is unavailable even when an absolute difference is computable. Do not extrapolate partial supported surfaces to a whole plant.

The sum of per-leaflet reference fluxes is a sum of target-specific counterfactuals, not necessarily one realizable canopy scene. Label that reference when reporting compound or plant summaries. Full-scene target fluxes should agree with the ordinary full-scene calculation within declared numerical tolerance.

Report incident PPFD in `umol m-2 s-1`, received and absorbed photon flux in `umol s-1`, supported one-sided area in `m2`, and dimensionless loss fractions. Preserve the existing two-face-received-per-one-sided-area convention where applicable. Do not call absorbed PPFD a photosynthetic rate. Summed received flux in reflective/transmitting scenes is not a unique photon conservation budget; use absorption and escape accounting when making conservation claims.

DLI is optional and available only with a supported explicit temporal integration or valid fixture schedules. For constant PPFD over a declared interval, use `DLI = PPFD * seconds / 1e6`. Do not apply one fixture's duration to other fixtures or invent a daily schedule.

## Source to target interaction matrix

Produce a directed matrix at leaflet, compound and plant levels. For a distinct source `s` and target `t`, calculate the full-background removal effect:

```text
effect(s -> t) = Q_t(full scene without source s) - Q_t(full scene)
```

Retain the target, fixed background, and all other sources. This is a context-dependent marginal effect and is not additive across sources. Do not present a matrix row/column sum as total loss. Effects need not be symmetric.

For off-diagonal compound or plant entries, remove the whole source group and evaluate all retained target tissue. Do not remove a group that includes the target to calculate a diagonal. Instead display diagonal internal shading from the corresponding retained-target hierarchy results, labeled with its different definition, or mark that diagonal unavailable. Exclude physical leaflet self-removal and report self-shading separately if implemented.

Allow target/source filters and explicit job budgets. Do not attempt exponential attribution over every individual leaflet by default. Keep sensor source-removal results separate: a sensor has no inherent compound membership, and its difference can include reflection.

## Backend implementation

Implement the complete eight-subset direct-light path first using imports from the existing Python engine. Add orchestration and attribution in `tools/`; do not duplicate the ray tracer. Preserve unique physical leaflet optical IDs: merging all leaflets of a compound into one surface code undercounts repeated transmissions, while assigning every triangle a new leaf ID overcounts them.

When filtering occluders, correctly remap `Receivers.own_triangle` to the filtered array or maintain a verified original-index mask. Never let a stale index exclude an unrelated triangle. Retain identical receiver sampling across subsets.

Provide a native GroIMP adapter using existing preparation, verification and collection code, with explicit feature support. Preserve surface review gates, units, lamp adapters, optical properties, seeds and stale detection. Do not bypass single-plant checks in `plant_light_bridge` to accept multiple plants; compose individually audited inputs through the existing explicit canopy placement tools.

Preparation must not execute native jobs. Require an explicit execution flag, job/ray/depth/replicate limits and a displayed cost summary for native execution. Use paired seed lists for subset comparisons, but do not assume identical seeds guarantee matched ray trajectories after changing geometry. Estimate uncertainty from paired replicate differences where available and retain failed jobs as unavailable. If no native run is authorized or ready, deliver verified preparation and report native execution as unverified.

Do not claim equivalence between direct-only and reflective backends. Unsupported heterogeneous optics or background objects require a clear unsupported status, not silent substitution. Separate sampling/convergence uncertainty from geometry, calibration and biological uncertainty.

## Proposed program and outputs

Create `tools/hierarchical_light.py`, `tools/tests/test_hierarchical_light.py`, and a viewer in `tools/hierarchical_light.html` or a focused integration with the existing viewer. These are proposed new files, not existing entry points.

Expose a CLI with `--help` and operations equivalent to `templates`, `audit`, `prepare`, `calculate`, `collect`, and `stale`. Include functions equivalent to:

```text
audit_inputs(manifest_path) -> audit_report
build_target_groups(surface_set, membership, target_key) -> target_groups
prepare_subset_cases(audited_inputs, target_keys, limits) -> prepared_manifest
calculate_direct(prepared_manifest) -> subset_results
attribute_groups(subset_results) -> attribution_results
aggregate_receivers(attribution_results, membership) -> hierarchy_summaries
calculate_source_target(prepared_manifest, source_filter, target_filter) -> matrix
write_report(results, audit_report, output_dir) -> report_paths
```

Keep function signatures idiomatic to the repository; preserve the variable definitions and units above. Store all generated outputs in a fresh `build/hierarchical_light_<run_id>/`:

- `manifest.json`: source paths/hashes, code versions, scene/geometry/identity hashes, transforms, dates, supported-area coverage, review status, backend capabilities, background, sampling, optical conventions, allocation method version, budgets and execution state.
- `interaction_cases.csv`: run/scenario/backend/fixture scope, target instance/session/compound/leaflet, subset, supported area, received flux, absorbed flux, PPFD, replicate/seed, status and reason.
- `leaflet_interactions.csv`, `compound_interactions.csv`, `plant_interactions.csv`: baseline/full fluxes, total change, A/B/C standalone and full-background marginal changes, Shapley allocations, overlap terms and defined loss fractions.
- `source_target_interactions.csv`: source and target level/IDs, signed marginal effect, unit, retained background and effect definition.
- `audit.json`: missing, conflicting, unsupported or stale inputs and affected outputs; distinguish blocked hierarchy attribution from blocked transport.
- An inspectable viewer and a short reproduction report with exact executed commands.

CSV unavailable numeric values must follow one documented missing-value convention with status/reason columns; never substitute zero. Empty templates must not populate unknown physical values.

The viewer must allow plant, compound and leaflet selection; display existing supported 3D surfaces; color by full-scene PPFD, A/B/C attribution or signed source effect; distinguish unavailable regions; and show source contributors, raw subset results, areas, units and provenance. Geometry visibility controls must not silently change the scientific calculation. Scenario changes that require recomputation must be explicit.

## Verification and acceptance

Run focused tests and a small deterministic synthetic demonstration. Include meaningful tests for:

1. No other leaf tissue: all eight results coincide and attributed changes are zero.
2. Only A, only B, and only C occlusion: the correct category receives the effect.
3. Two redundant opaque blockers: standalone losses do not sum to total; the equal symmetric case splits attribution equally.
4. Three distinct fully covering transmissive leaves at different heights: with a synthetic direct-light transmittance of 0.1 per leaf, `Q(ABC)/Q(empty)=0.001` in a fixture where every target ray crosses all three leaves.
5. Multiple triangles on one physical leaf do not count as multiple leaf crossings; separate physical leaflets still attenuate separately. Cover shared-edge rays.
6. Filtered occluder index remapping, including a receiver originally at a nonzero index, and retained own-leaf folding.
7. Shapley and inclusion-exclusion identities, group-order invariance, no negative-value clipping, and zero-baseline ratios.
8. Area-weighted aggregation with unequal leaf areas and agreement with the ordinary full-scene computation; partial-overlap sampling convergence under a declared tolerance.
9. Missing optics/lamp inputs, unknown membership, duplicate IDs, foreign sessions, copied instances, and stale geometry/identity/scene hashes. Missing transmission should affect paths that require it according to existing engine semantics.
10. Directed source-removal matrix behavior and diagonal semantics; no asserted additivity of marginal effects.
11. Native preparation preserving optical geometry, identities and units. If native execution is authorized, include bounded opaque/transmissive cases and a reflective gain case with uncertainty; otherwise state those execution checks are pending.

Use tight declared arithmetic tolerances for deterministic algebra and documented sampling/convergence tolerances for transport. Do not treat numerical tolerances as physical PPFD acceptance thresholds. Do not fit lamp parameters or geometry to held-out measurements.

Deliver the implementation, passing focused test results, reproducible synthetic outputs, and a real-input audit listing exactly what is needed to calculate observed results. Clearly distinguish implemented, prepared, executed, and physically validated. Report current input blockers without weakening existing gates. Append one English completion line to `handoff/LOG.md` with files, verification, and remaining limits.
