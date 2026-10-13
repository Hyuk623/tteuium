# Build a compound leaf growth calculation model

You are Claude, responsible for reviewing the scientific specification and coordinating implementation in the existing Tomato 3D phenotyping project. Build toward a calculation model that starts from an observed plant and predicts where each compound leaf will extend, rotate, bend and unfold over time. Improve the surface reconstruction used for leaf area at the same time. The forecast unit is CompoundLeaf; predicting every leaflet independently is not required.

This is a task prompt for a future implementation session. Its creation did not execute or authorize remote training, uploads or inference. It does not claim that a calibrated growth model, complete leaf surfaces or measured light inputs already exist.

## Read the current project before changing it

Workspace: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.

Read the parent `공통규약.md`, project `AGENTS.md`, `CLAUDE.md`, `CONVENTIONS.md`, the latest five LOG entries and relevant TODO entries. Then read:

- `handoff/CODEX_NEW_CHAT_HANDOFF_2026-10-03.md`
- `handoff/CLAUDE_TO_CODEX_MASTER_HANDOFF_2026-10-03.md`
- `handoff/CLAUDE_PLANT_3D_LIGHT_CONNECTION_PROMPT_2026-10-03.md`
- The compound growth and surface-area investigation in `handoff/TODO.md`.

Inspect newer work before implementing; reuse any completed adapter. Keep the accepted sequence: observed reconstruction and optical-surface eligibility, existing GroIMP light integration, then observed-state growth integration. State extraction and software tests can proceed without physical light validation, but must not imply it has passed.

Write an English implementation brief before coding and append actual results afterward. Conversation is Korean; code and handoff are English. Honor current file ownership and freezes. This prompt does not grant cross-owner editing permission. If an essential edit is outside your ownership, provide a concrete patch proposal and handoff while continuing allowed work. Preserve source photographs, masks, human records, review history and unrelated changes. Do not edit human `config/`, invent observations, push to GitHub or launch heavy jobs. Generated artifacts belong in a new `build/` directory.

## Required outcomes

1. Compute supported leaf tissue area from reconstructed surfaces without filling gaps between leaflets or counting the same tissue twice.
2. Extract an observed state for each persistent compound leaf, with traceable geometry and missingness.
3. Predict future compound direction, axis shape, spatial extent and tissue area from recent observed states using explicit, comparable calculation models.
4. Separate observed reconstruction, interpolation, forecast geometry and independently validated results in every export and viewer.
5. Connect eligible geometry to the existing light workflow through its current contracts. Do not implement a second renderer or photon solver.

Claude must resolve scientific choices and record their evidence. The computational interfaces below are proposed contracts to review before implementation; they are not established biological laws. Do not stop at a conceptual description when permitted software work is possible. If data are insufficient, deliver runnable software and an exact input-gap report rather than fabricated calibration.

## Reuse these components

| Existing component | Role and limitation found during review |
| --- | --- |
| `tomato3d/light/geometry.py::triangle_areas_mm2` | Correct triangle cross-product area; reuse it |
| `tools/leaf_light/reconstruction.py` | Fixed ChArUco poses, multi-view DLT, PCA-plane Delaunay, contour checks; hidden surfaces are absent |
| `tools/vein_surface_bridge.py` | Reviewed interior/boundary points and full visible-mask footprint checks for partial surfaces |
| `tools/plant_structure.py::compound_regions` | Compound region proposals; a region is not automatically a confirmed biological identity |
| `tools/plant_structure.py::fit_petioles` | Existing axis evidence; its `arcsin(abs(u[2]))` elevation loses up/down sign |
| `tools/plant_traits.py` | Session/date-aware proxy traits; preserve completed join and validation fixes |
| `tools/growth_simulator.py` | Procedural demonstration from development day zero, fixed five-leaflet display topology; not an observed-state growth model |
| `tools/groimp_bridge.py`, `tools/groimp_density.py`, `tools/ppfd_validation.py` | Coordinate/unit helpers and current optical/validation workflows |

Recheck these findings against current files. Preserve the existing freezes on `groimp_structure_export.py`, `groimp_static_verify.py` and `groimp_bridge.py`.

## Improve the surface used for area

Keep `A_triangle_mm2 = 0.5 * norm(cross(v1 - v0, v2 - v0))`. Sum eligible, nonduplicated faces; convert mm2 to cm2 by dividing by 100. The area definition is one-sided leaf blade tissue area, excluding petiole/rachis cylinders and artificial back faces. Document any departure before using it.

Improve topology and evidence, not merely triangle count:

- Preserve boundaries, holes and disconnected tissue patches within each compound. Never use a bounding box or a filled compound hull as its physical leaf surface.
- Require appropriate visible-image support for full triangle footprints, not only vertices and centroids. An occluded view is unavailable evidence, not automatically a contradictory mask. Reuse existing visibility contracts.
- Detect duplicate/reversed faces, degeneracy, self-intersections and unsupported connections. Report ambiguity instead of deleting genuine overlapping leaves. Resolve cross-view observations of the same physical patch before aggregating it.
- A single PCA chart is insufficient for some folded leaves. Support local charts/patches, or a boundary-constrained smooth surface when interior observations support the curvature. Do not silently replace folded geometry with a convex hull.
- Use edge/curvature adaptation and denoising only with explicit settings, evidence and sensitivity checks. Subdividing a flat triangle without new geometry leaves its area unchanged.
- Export supported partial area separately from inferred completion. A total area is unavailable when completeness cannot be established. Smoothing, triangulation success and a finite area do not make a surface optically validated.

## Define the compound state

Use a persistent key containing `plant_id`, `compound_leaf_id`, `session_id` and an observed timestamp with timezone. Retain source image/review IDs and hashes. A name based on height order alone must not silently become a cross-date identity. Unresolved region-to-compound mappings stay unresolved.

Proposed state fields, to be finalized in an English schema:

| Field | Meaning |
| --- | --- |
| `attachment_xyz_mm`, `parent_stem_id` | Observed attachment and its parent |
| `rachis_points_mm`, `rachis_arc_length_mm` | Ordered leaf-axis geometry and length |
| `direction_unit_xyz` | Directed attachment-to-tip orientation, when identifiable |
| `azimuth_deg`, `elevation_deg` | Wrap-safe horizontal direction and signed vertical inclination |
| `left_extent_mm`, `right_extent_mm` | Extent profiles at documented normalized positions along the axis |
| `tip_xyz_mm` | Distal endpoint when observed or explicitly predicted |
| `supported_area_cm2`, `estimated_total_area_cm2` | Supported tissue area and separately qualified total estimate |
| `development_state`, `first_observed_at` | Observed development evidence; first seen is not necessarily biological emergence |
| `geometry_status`, `identity_status`, `qc_flags`, `uncertainty` | Availability, evidence and uncertainty per field |

Store tabular observations/features in CSV and metadata/settings in JSON. Use child CSV tables for ordered axis/extent samples. Missing measurements remain unavailable with a reason, not zero. Keep derived tables separate from originals.

Define coordinate frames and handedness explicitly. Reuse ChArUco board-frame helpers and measured poses. Do not use nominal turntable angles or SfM as replacement poses. A stem axis alone does not determine azimuth: retain an observed transverse reference. Keep plant-local orientation and the measured plant-to-rig transform separate so moving a pot cannot look like leaf growth or change the light frame silently.

Orient axes from attachment to tip. Use signed elevation, for example `atan2(dz, hypot(dx, dy))` in the declared frame, and wrap-safe azimuth. At vertical orientations azimuth is undefined; when the axis collapses direction is unavailable. Do not change legacy angle semantics silently: version the new state and preserve provenance.

Decompose parent-stem/attachment motion from compound-local elongation, rotation, curvature and unfolding. Maintain spatial consistency between the axis, tip and width profiles. Treat tissue-area increase separately from an increase in projected width caused by unfolding. New leaves, occlusion, senescence and identity changes need explicit events; missing geometry does not mean disappearance.

## Implement comparable forecast models

The transition must receive the current observed state and history, not only environment and global parameters:

`forecast(history, horizons_days, environment_scenario, model_parameters) -> compound_forecast`

All horizons are caller-supplied positive durations. Use actual time intervals. Parameter provenance and model applicability must be exported.

Implement these in order:

1. **Persistence:** retain the last eligible compound state. Identify any separate parent-motion assumption.
2. **Recent change:** estimate translation, angular motion, length and extent change from timestamped history. Use wrap-safe orientation operations, explicit applicability limits and physical constraints. Do not invent a velocity with only one observation or extrapolate unbounded growth indefinitely.
3. **Low-parameter growth candidate:** compare measured length/area expansion curves conditioned on observed development stage or leaf rank, with separately fitted orientation/curvature dynamics. Claude must choose and document the model form, fitting domain, required observations and identifiable parameters. Unsupported asymptotes, growth rates and physiological response coefficients remain unavailable.

A GRU or graph model is a later comparison only if data volume and independent validation support it. Do not add neural training as a prerequisite for these calculation models. Many compounds on one plant do not constitute many independent plants.

Forecast state variables rather than arbitrary independent mesh-vertex displacements. Reconstruct predicted geometry from that state while preserving tissue gaps and topology where supported. When detailed tissue allocation is unknown, export a predicted extent envelope separately; it is not an optical receiver. Do not fix every compound to five leaflets or assign measured-looking surfaces from counts alone.

Supply forecast distributions/intervals only when the noise/residual model has evidence. Otherwise report uncertainty as uncalibrated or unavailable. Distinguish measurement uncertainty, forecast uncertainty and future-environment scenarios. Do not force projected area, leaf angle or every biological stage to be monotone.

## Use light as a supported input

A scalar PPFD or DLI cannot specify the direction of future movement. Directional features require a measured light scene, explicit frames and the existing solver's eligible geometry. Where available, consider directional incident light, neighbor geometry and shading alongside development and recent motion. These are candidate predictors, not proof of causation.

Do not implement “always grow toward maximum PPFD” as a biological law. If directional light is unavailable, keep the observation-based models usable and mark light-conditioned forecasts unavailable. Any held-constant future environment must be labeled as a scenario. Do not use future measured light or geometry during retrospective forecasts.

Keep incident PPFD, absorbed photons, DLI, projected interception and photosynthesis distinct. Never infer photosynthesis without its physiological inputs. Forecast geometry may be used for a clearly labeled optical scenario only after the relevant eligibility checks; that does not validate predicted biology.

## Suggested implementation boundaries

First map these responsibilities onto existing code. Add narrowly scoped modules only where no equivalent exists:

- Surface audit and area aggregation: `audit_surface` and `summarize_area`.
- Observed compound adapter: `extract_compound_state` and `validate_history`.
- Forecast engines: `forecast_persistence`, `forecast_recent_change`, and a reviewed fitted candidate.
- Evaluation: `evaluate_compound_forecasts` with a frozen split/forecast-origin manifest.

Offer standalone CLIs for audit, state extraction, forecasting and evaluation, with `--help`, explicit inputs and a new output directory. Keep computation functions importable. Placement must follow current ownership; proposed names do not authorize editing another agent's files.

A run should contain state/forecast/metric CSV tables, a JSON schema/manifest with hashes, model parameters and availability reasons, and the existing viewer extended where feasible. Show current geometry, predicted geometry and uncertainty distinctly. Keep display envelopes distinguishable from tissue surfaces. The report must separate software readiness, real-data evaluation, physical-light validation and growth validation.

## Tests and evaluation

Require tests that expose meaningful failure modes:

- Known planar and curved synthetic surfaces, rigid-transform area invariance, mm2/cm2 conversion, and area convergence against an independent reference. Flat subdivision alone must not change area.
- Holes, gaps between disconnected leaflets, unsupported faces, duplicates, thin degenerate faces and folded surfaces. No automatic completion of hidden tissue.
- Upward versus downward axes, azimuth wraparound, vertical/zero-length axes, global rigid motion, and parent motion separated from local expansion.
- Stable IDs across dates, ambiguous matches, duplicate observations, unequal intervals, missing data, negative/zero horizons and insufficient history.
- Persistence identity, known synthetic expansion/rotation, consistent tip/axis geometry, no future-data leakage and deterministic replay.

Use chronological forecast origins and plant-disjoint evaluation, with all compounds/dates of each plant kept together for independent holdout. Fit preprocessing and parameters on training data only. Report tracking failures and missing-target coverage alongside errors, rather than evaluating only easy matches without disclosure.

Report horizon-specific tip/axis position errors in mm, directional angular error in degrees, length/extent errors, area errors and interval coverage where calibrated. Compare every fitted model against persistence and recent change. Report sample counts by plants, compounds and forecast origins; avoid treating repeated observations as independent confidence samples.

Independent non-destructive flattened-leaf area references can support area checks but do not by themselves validate in-situ curvature or future direction. Keep observed and model-generated references separate. Do not invent accuracy thresholds: Claude must propose and justify prospective gates, leaving unspecified gates inactive and validation unclaimed.

If real temporal data are insufficient, complete the software tests, exercise any eligible real extraction read-only, and list exactly which states, dates, identities or reference measurements are missing. Do not claim real predictive accuracy from synthetic success.

## Research references to verify

These are starting points, not transferable cultivar coefficients or proof of this model's accuracy:

- [Dwarf tomato functional structural model using GroIMP](https://doi.org/10.1093/insilicoplants/diaf024): relevant structure/light precedent; verify which orientation variables are fixed versus dynamic.
- [Tomato functional structural model for digital twins](https://academic.oup.com/insilicoplants/article/7/2/diaf022/8342854): organ orientation and growth representation.
- [Pheno4D](https://doi.org/10.1371/journal.pone.0256340): temporal plant geometry and organ identity; verify the annotation unit before mapping to compound leaves.
- [Temporal registration using statistical plant shapes](https://arxiv.org/abs/2209.11526): matching components across dates.
- [Thin leaf surface reconstruction](https://doi.org/10.1016/j.apm.2021.05.014): surface representation under noise and missing data.

Some full texts were inaccessible during the preceding investigation. Check original methods before adopting a formula; do not fill gaps from search snippets.

## Delivery

Return a Korean explanation of what was implemented, actual commands/results, example compound forecasts if supported, and remaining evidence gaps. Save the English specification, execution notes and model applicability in handoff. Append one LOG entry and update relevant TODOs without deleting history.

Success means a reproducible observed-compound calculation workflow with explicit surface-area semantics, comparable direction/spread forecasts, tests and honest real-data evaluation status. A growing procedural plant animation alone does not satisfy this task.
