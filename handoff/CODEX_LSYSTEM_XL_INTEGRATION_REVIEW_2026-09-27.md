# L-system and XL integration assessment — 2026-09-27

## Purpose

Assess how GroIMP's XL/RGG modelling can enter the accepted tomato pipeline without replacing measured image evidence or overstating the present geometry quality.

## Recommended separation of roles

1. **Observation layer (existing Python pipeline):** photos, ChArUco/diagnostic poses, reviewed masks and identities, organ hierarchy, optional reviewed surfaces, environment and PPFD measurements.
2. **Plant grammar layer (new XL/RGG model):** explicit modules for Plant, MainStem, Internode, CompoundLeaf, Petiole/SubStem, Leaflet, GrowthShoot, Truss, Flower and Fruit. Rewriting rules create topology and change organ state over time.
3. **Radiation layer (GroIMP Raytracer/GPUFlux):** calculate incident/absorbed radiation for a specified geometry, spectrum, optics and lighting scene.
4. **Experiment controller (Python + GroLink/GroPy):** write parameter/input files, run the RGG functions, collect CSV outputs and compare scenarios or measurements.

An L-system/RGG is a generator of architecture and temporal state. It is not a 3D reconstruction algorithm and does not infer hidden leaves from one image. XL is the Java-based language GroIMP uses to define modules, graph queries, turtle geometry and relational rewriting rules.

## Two geometry modes

- **Observed snapshot:** import only reviewed triangle surfaces and identities. Use the current `tools.groimp_bridge` OBJ plus identity map as the starting transport. Do not apply growth rules to claim the observed geometry is complete.
- **Parametric digital plant:** instantiate an XL/RGG plant from measured topology and fitted distributions. Missing organs may be generated only as simulated organs with separate provenance. This mode supports density, future-growth and architecture experiments, but it is not an observation.

Never merge these modes into one unlabeled mesh. Every organ needs `geometry_source = observed | fitted | simulated` and a stable plant/compound-leaf/leaflet identity.

## Proposed data contract

Python should export a versioned package with:

- `plant_graph.json`: organ nodes, parent links, stable IDs, developmental state and source provenance.
- `organ_parameters.csv`: board/grow-frame position, orientation, dimensions and availability/quality flags.
- `leaf_meshes.obj` plus `identity_map.csv`: reviewed surfaces only.
- `environment.csv`: timestamped temperature, humidity, CO2 and solution/environment variables when available.
- `light_scene.json`: lamp geometry, spectrum/PPF, schedule and leaf optical properties with sources.
- `growth_parameters.json`: fitted phyllochron, internode/leaf expansion and senescence parameters, initially unavailable until time-series evidence exists.

GroIMP should return CSV tables keyed by the same identities: time step, organ state, area, position/orientation, incident/absorbed PPFD or photon flux, biomass/carbon variables if a physiological model is explicitly added, and scenario ID. Metadata must record XL model hash, GroIMP version, parameter hash and whether each geometry was observed or simulated.

## Implementation phases

### Phase A — static integration check

Create one minimal RGG project, import a small synthetic/reviewed leaf mesh, preserve identities, add one measured lamp scene and export per-organ radiation. Compare units, coordinate axes, surface sidedness and photon conservation against the existing Python direct-light engine. This is software validation, not biological validation.

### Phase B — static canopy scenarios

Clone an observed/fitted plant graph into layouts with explicit spacing and rotation. Sweep plant density and lamp height/angle through Python/GroPy. Compare upper/lower leaf light distribution, uniformity, interception and electrical input. Report light-feasible tested scenarios; do not call them optimal density without growth/yield outcomes.

### Phase C — calibrated dwarf-tomato grammar

Use repeated-date observations to estimate organ appearance order, thermal-time or time-step phyllochron, internode extension, compound-leaf/leaflet expansion, angles, flowering, fruit growth and senescence. Keep plant-level train/calibration and held-out evaluation splits. Rules must retain stochastic variation rather than reproduce only one plant.

### Phase D — functional-structural feedback

Add a reviewed photosynthesis/carbon-allocation model only after light and growth components are separately validated. Radiation may drive organ carbon input; temperature/CO2 and organ age may modify physiology; carbon availability may affect expansion and fruit growth. PPFD alone cannot establish growth or yield.

## Immediate value and limits

XL/RGG is highly suitable for the project's Stage 2 questions: generating many plants consistently, changing architecture/density, retaining organ relationships and advancing time. It also gives a clean graph for the later dashboard/RAG layer.

It adds little to the current Stage 1 identity and reconstruction bottleneck. Current hierarchy regions, bbox cuboids and diagnostic hull intersections are not leaf surfaces. Existing outputs remain `validated_metric=false` and `suitable_for_ppfd=false`; importing them into GroIMP does not promote their validity.

## Local readiness

- Local GroIMP 2.2.1 is present with RGG, API, GPUFlux and Raytracer plugins.
- Java 21 is currently available on PATH (`OpenJDK 21.0.12.1`).
- `tools/groimp_bridge.py` already transports reviewed triangle geometry to metre-scale OBJ with an identity map, but GroIMP import/light execution has not been verified.
- The first useful implementation is therefore a small static round-trip and unit/identity check, followed by a Python/GroPy batch controller. Do not begin with a complete growth grammar.

## Acceptance gates

1. Coordinate/unit/identity round-trip verified on synthetic geometry.
2. Per-organ radiation output reproducible and reconciled with a simple analytical/Python case.
3. Empty-scene and quantum-sensor validation completed before real PPFD claims.
4. Repeated-date plant measurements available before fitting growth rules.
5. Held-out plants/dates used before claiming predictive growth or density performance.

Document 05 clustering remains deferred and is unrelated to this integration decision.

## Verification addendum — review of the preceding Sol-authored assessment

The integration direction is reasonable, but the preceding text is an architectural proposal, not a tested implementation contract. Apply these qualifications when handing it to Claude:

1. **Static XL is useful before growth data exist.** Use a fixed graph and static geometry for organ queries, layout generation and light experiments. L-system growth rewriting is optional in this phase. RGG extends the modelling approach; it is not an alternative unrelated to L-systems. The observation -> XL -> radiation diagram is a proposed route, not a mandatory dependency of all PPFD calculations.
2. **The bridge does not enforce human review.** `tools/groimp_bridge.export` loads a geometry variant and exports its triangles; it does not inspect a human-acceptance manifest. Its ID map also omits `geometry_sources` and `surface_classes`, although `SurfaceSet` carries these fields. Therefore the earlier description of it as transporting only reviewed leaf geometry overstates its current guarantees. Add a reviewed-input contract and preserve provenance before relying on that property. OBJ export alone does not create XL organ nodes or reconstruct parent-child relations. The actual current filename is `leaves_m.obj`; `leaf_meshes.obj` above is only a proposed name.
3. **Reuse the existing schemas.** The proposed JSON/CSV names are suggestions, not new mandatory parallel stores. Adapt the existing hierarchy, geometry tables and light scene; preserve actual annotation class aliases and nullable/unconfirmed parents. A single `sub_stem` class cannot by itself distinguish petiole, rachis and petiolule anatomy. Preserve it unless a reviewed mapping defines the finer anatomy.
4. **Keep optical comparison like-for-like.** Compare GroIMP with the current Python direct-light engine under the same source, receiving area/normal, wavelength/photon convention and reflection/transmission assumptions first. Differences from adding scattering/reflection are not automatically bugs. Explicitly distinguish incident PPFD (micromol m^-2 s^-1), absorbed photon flux density, and integrated photon rate (micromol s^-1). Display colour or generic raytracer energy must not be renamed PPFD; sensor comparison uses the actual sensor plane/area, not automatically the leaf plane. Plugin presence does not prove OpenCL/GPU availability or a working radiation run.
5. **The cited crop example is a teaching model.** The official page explicitly says it is not based on real-plant measurements. Its growth, yield and density parameters are not validated dwarf-tomato parameters. The previous chat response also misspelled its URL; use the correct source below.
6. **Availability is not completion.** The new adapter, RGG modules, importer, optical configuration and GroPy controller remain proposed. Java/plugin checks establish prerequisites only. No running service, real model import or light computation was verified in this review. Deterministic baseline growth rules are also permissible; stochastic variation is an optional modelling choice rather than a mandatory first-stage requirement.
7. **Geometry priors may help later.** A fitted grammar can propose missing topology/shape for human review or constrain a reconstruction fit. It cannot establish hidden organs or depths as observations. Keep fitted/simulated candidates separate from measured evidence and validate any claimed reconstruction benefit independently.

Verified primary references:

- XL/RGG language: https://wiki.grogra.de/doku.php?id=groimp-platform:xl-language
- Python integration: https://wiki.grogra.de/doku.php?id=tutorials:getting-started-with-grolink-and-gropy
- Crop radiation teaching example (correct URL): https://wiki.grogra.de/doku.php?id=tutorials:radiation-model-in-crop_model8

Review outcome: retain the staged adoption proposal, start with a static graph/geometry import and controlled optical check, and defer calibrated growth prediction until suitable repeated-date data exist. This addendum changes documentation only.
