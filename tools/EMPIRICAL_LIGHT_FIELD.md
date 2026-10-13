# Empirical light field, version 1

`python -m tools.empirical_light_field freeze --grid RAW.csv --configuration CONFIG.json --out build/NEW/field`

`python -m tools.empirical_light_field query --field build/NEW/field/field.json --configuration CONFIG.json --position-mm 280 210 110`

`python -m tools.reference_dli empirical --field FIELD.json --configuration CURRENT.json --positions POSITIONS.csv --operation OPERATION.json --out build/NEW/dli`

`python -m tools.reference_dli_consumer build/NEW/dli/reference_dli.json --current-configuration CURRENT.json`

`python -m tools.empirical_canopy --field FIELD.json --configuration CURRENT.json --scene CANOPY.json --out build/NEW/canopy`

Use new output directories. No raw data, human config, old fitted packages or old hashes are rewritten. Configuration and source paths in packages are absolute, locally auditable references; copying a package alone is not a portable archive.

## Field and support

Input is the existing PPFD grid CSV in cm / umol/m2/s. Both complete rectangular planes, z=70 and 150 mm, are required. IDs are plane:row:column; missing, duplicate, negative and nonfinite samples fail. `samples.csv` retains all observations, including those outside the query region. Outputs are always `method=empirical_light_field`, `source_kind=derived`, including queries exactly at a measured sample. The original raw CSV remains the measurement source.

Interpolation is bilinear within each XY plane followed by linear Z interpolation. It uses only nonnegative weights summing to one. Exact-plane queries need that plane alone; intermediate queries need both planes. The intersection with the declared tray block is enforced. No cell-edge padding, nearest-neighbor fallback or extrapolation occurs. Scalar query errors are explicit; batched DLI exports preserve unsupported positions as unavailable with a reason. No averaging of the two plane means is used to evaluate a position.

Configuration copies the board/tray/lamp/enclosure/canopy-grid source metadata and adds `empirical_contract`: grow frame, shelf-floor height basis, `tray_bounds_xy_mm=[xmin,xmax,ymin,ymax]`, `coordinate_variant`, `plants_above_150_mm=false`, explicit source refs with SHA256, conditional reasons, and source kind `user_assumed` or `fixture_truth`. Orientation options are as_recorded, reverse_x, reverse_y, reverse_xy, reversing the sample assignment within each plane. These are declared variants, never selected by fit quality; axis interchange is not silently inferred. Current recorded centres use a conditional XY mapping, not surveyed absolute coordinates.

SHA256 of the entire configuration plus hashes of raw records/clarifications bind the field. Consumers require a separately supplied current configuration and reject differences. Unknown recorded poses remain unknown: hashes detect recorded changes and cannot detect an unrecorded physical move. Field reuse after lamp/board/tray/enclosure movement requires remeasurement. No reflectance value participates in numerical evaluation; changing recorded enclosure metadata still invalidates reuse intentionally.

## Direction and canopy contract

`empirical-canopy-1` explicitly supplies grow-frame receivers (ID, leaf ID, position_mm, unit normal, own_triangle, supported_one_sided_area_m2), leaf-only triangles (surface_id, vertices_mm, role=leaf), transmittance plus provenance or null, configuration SHA256, quadrature/resource limits, and diffuse fractions. Real geometry requires source_kind=reviewed_optical_surface and a hashed source_ref; tests use fixture_truth. It is the caller's reviewed optical-surface contract, not an adapter for P1 area proxies or future outlines.

Field configuration must contain `direction_bars` with start_mm/stop_mm and `direction_source_kind=user_assumed`. Missing bar pose refuses leaf interception. Endpoints represent centre lines; the real emitting width and beam are unmeasured. Equal samples per bar have relative inverse-square intensity, normalized so their horizontal projection sums to one. A uniform-radiance upper dome uses midpoint quadrature in azimuth/cos(zenith), normalized the same way. For diffuse fraction f and observed horizontal Q, directional intensity weights are Q*((1-f)*direct, f*diffuse). Leaf contributions multiply by abs(n dot u); normal-side and opposite-side values remain separate. This is a declared sensitivity model, not recovered radiance or measured reflected fraction. No fitted PPF or wall reflectance enters it.

The existing `tomato3d.light.raytrace.count_crossings` computes canopy interception. Rays terminate just above z=150 mm. It preserves receiving-triangle exclusion and counts distinct physical leaf surface IDs once. Transmission is tau**crossings; unknown tau makes any affected positive contribution unavailable rather than zero. Zero incident light stays zero. There are no walls. Scene geometry above 150 mm is refused. Maximum pair work and chunk size are explicit; the fixed upper safety limits are 500 million total pairs, 1 million pairs/chunk, and 65536 directions per receiver. Receivers are processed sequentially; numeric geometry arrays are held in memory and no Native/GPU backend is used.

Leaf flux F=sum(area_i*PPFD_i) in umol/s precedes division by supported one-sided area in m2. Partial support is never promoted to a whole leaf or plant. Each diffuse scenario has a distinct row; spread=min/max difference across those rows, unavailable if any scenario is unknown. It is not a confidence interval. No growth forecast is produced. Scenario-specific light rows are available for a separately authorized future forecast caller.

## DLI consumer

New schema `reference-dli-empirical-result-1` preserves the old reference-DLI contracts unchanged. Positions CSV uses position_id,x_mm,y_mm,z_mm. Operation JSON explicitly supplies daily_on_hours, output_fraction=1, measurement_output_fraction=1, constant_during_on=true, source_kind=user_stated, source_ref. Dimming or nonconstant operation is refused; it cannot be inferred from an aggregate field.

Per-position DLI = Q * hours * 3600 / 1e6, in mol/m2/day. This is a conditional on-period daily dose assuming the sampled PPFD is constant. It is not a dated logger integral; clock times and off-period ambient light are unconfirmed. The package has value=null, model_scope=per_position_horizontal_reference and cannot silently become a whole-plant P3 input. The consumer independently evaluates tensor-product interpolation and duration integration, checks source/current-configuration/code/artifact hashes and interpolation evidence, and rejects promotion to measured/simulated/whole-plant provenance. Absolute and relative arithmetic tolerances are both 1e-12. Canopy normalization tests use atol=1e-10 and rtol=1e-12; dome angular convergence uses atol=.01 and rtol=.001.

Physical accuracy is unvalidated. Above-plane plants are absent per user clarification, while plants below were present during acquisition. Unknown meter calibration, approximate grid registration, environment/canopy dependence and assumed direction remain disclosed. A small interpolation residual at source nodes is not independent validation.
