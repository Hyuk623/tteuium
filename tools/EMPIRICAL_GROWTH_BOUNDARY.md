# Empirical leaf light boundary v1

The adapter consumes metric physical triangle snapshots from `assemble_canopy`, plus explicit canopy-metre to grow-millimetre registration. It does not infer a leaf from projected area, outlines, reference DLI, or physiology. Source schema is `empirical-growth-request-1`; result is `empirical-growth-boundary-1`.

```
python -m tools.empirical_growth_boundary --request build/NEW/request.json --out build/NEW/export
python -m tools.empirical_growth_consumer build/NEW/export/boundary.json --configuration CONFIG.json --context CONTEXT.json --required-basis absorbed
python -m tools.empirical_native_response --native PREPARED_NATIVE --boundary BOUNDARY.json --configuration CONFIG.json --context CONTEXT.json --interval 0 --diffuse-fraction 0.6 --out build/NEW/response --submit
```

All paths in source references are absolute with SHA256. Use fresh output directories. The last command is an opt-in submission to the native owner's live request; it does not launch or advance an engine. Its deadline must still be live. `--submit` omitted writes an unsubmitted response. It reuses `verify_prepared`, `read_request`, `submit_light`; no native source is replaced.

## Mandatory scientific interpretation

The input `transport_contract` explicitly selects interpretation `local_horizontal_environment_before_one_canopy_attenuation`, source_kind and source_ref; field_light_basis=incident; already_canopy_shaded=false; canopy_shading_passes=1; quadrature=triangle_centroid_area_weighted; local_field_approximation_acknowledged=true; canopy_scattering=not_modelled_transmission_only. There is no default. This declares a local empirical environmental illumination model, followed by one transmission/occlusion computation. It is not a conservative reconstruction of the room's radiance. The two acquisition planes had different plant-presence conditions; the user only confirmed no plants above the upper plane. Any real adoption of this local transport interpretation requires an explicit sourced scientific contract.

Each actual triangle contributes one centroid sample with its geometric one-sided area. All vertices and samples must lie inside supported field/tray bounds; a single unsupported tissue vertex rejects the export, even if its centroid is inside. The 150 mm observation does not authorize extrapolation to later taller tissue. No partial surface is expanded to a full leaf. The quadrature is an explicit approximation requiring refinement checks for spatially variable/shadowed surfaces.

Field direct/diffuse intensity weights each sum to one after projection onto the horizontal normal. At each point multiply these by local measured-field PPFD, then by the leaf-face cosine and existing canopy transmission exactly once. The input is incident; the output incident values already contain canopy occlusion. Native must not shade them again. Neither leaf reflection recirculation nor the room is re-traced. Fractions 0.5/0.6/0.7 remain separate assumed direction scenarios.

Absorption is optional and explicitly supplied per surface and geometric face with provenance. `absorbed_umol_s = normal_incident_umol_s * absorptance_normal + opposite_incident_umol_s * absorptance_opposite`. Missing absorptance yields unavailable absorbed fields, never `1-tau`. Supplied absorptance plus transmittance cannot exceed one. This interface does not choose a photosynthetic coefficient/basis mapping. Already absorbed inputs and second shading passes are rejected.

## Inputs and identities

- `field_ref`, `configuration_ref`: hashed field and current configuration; all original support/source/code checks remain active.
- `fixture_ids`, `diffuse_fractions`, `quadrature`, `leaf_transmittance` with provenance: explicit optical scenario. Field bar fixture IDs must match schedule membership.
- `intervals`: unique interval_id, timezone-aware start_at/end_at, snapshot_ref, registration_ref, expected_geometry_hash, absorptance_by_surface and explicit `segments`. Geometry is frozen only within that interval; the next interval supplies a new snapshot if the state changes.
- Snapshot: existing assemble_canopy output (`frame=canopy_m`, length_unit=m), canonical surface triangle hash, identity_map, placement_hash and one_sided_areas_m2. Every surface needs physical optical geometry evidence and face_convention=triangle_winding_geometric_normal. One surface per organ in this version. organ_id must equal plant_instance_id + `|` + producer_vertex_id; source IDs and external surface IDs are retained separately.
- Registration: from_frame=canopy_m, to_frame=grow_mm, proper 3x3 rotation, translation_mm, source_kind=fixture_truth/reviewed, source_ref (hashed for reviewed). Coordinates become `1000 * R * canopy_position_m + translation_mm`. Normals come from transformed winding; translation never enters a direction.
- Segment: explicit start_at/end_at, complete fixture_fractions mapping, source_kind/source_ref. Exact contiguous coverage is mandatory. The aggregate field currently supports all fixtures full output or all off; unequal fixture schedules or dimming require new data/contract. An absent window is never darkness. off_period_ambient=excluded_unmeasured records that environmental night light is not established.

## Exports and consumer

`leaf_segments.csv` carries each interval/scenario/surface/segment with plant/organ/surface IDs, geometry/namespace/configuration/registration/placement hashes, source kind, orientation variant, face convention, area (m2), incident normal/opposite/total and absorbed rates (umol/s), PPFD (umol/m2/s), and photon doses (umol and mol/m2). Both faces share one lamina area. Botanical upper/lower faces are not inferred. Geometry hash scheme is fsp_canopy_surface_triangles_m_v1, not a hash of arbitrary native CSV bytes; native geometry file hash is checked separately by the response adapter.

`leaf_intervals.csv` sums segment doses only within that frozen interval and scenario. Different interval areas are each integrated with that interval's flux; no cross-interval reference-area scaling. Missing incident/absorbed values remain null in JSON and unavailable in CSV. `transport_evidence.json` retains receiver area and face PPFD. `boundary.json` binds sources/code/artifacts and explicitly says native_consumption=unverified_hook_required. No fixture output is promoted to real accuracy.

The independent consumer checks area-weighted sums and segment integrals (atol=rtol=1e-10), identity coverage, current configuration, source/code/artifact hashes and expected live-state context. Context schema empirical-native-context-1 includes run_id, configuration_sha256 and interval records with interval_id/start_at/end_at/geometry_hash/namespace_hash/registration_sha256. It must be supplied from consuming state, not copied blindly from the export. `--required-basis absorbed` rejects missing absorbed values. `incident` is a diagnostic acceptance only; it is not permission to use incident values with absorbed-basis NRH coefficients.

## Native hook constraints

Owner API is fsp-native-boundary-1 / fsp-native-light-response-1. The response adapter compares every actual live native leaf triangle coordinate (canopy metres) exactly to the source snapshot, checks IDs and area (atol=1e-12, rtol=1e-10), and verifies interval/configuration/prepared input/engine lineage. A CSV row hash alone is insufficient. It selects exactly one direction scenario. Native receives on-period absorbed flux, not whole-day mean: the current NRH function is nonlinear. All on-segments must have identical rate and their duration must match native light_hours. Differing intensity requires native segment-wise physiology; no hidden averaging.

The current native contract permits growth only for fixture=true and nrh_basis=fixture_black_absorbed_equivalence; this adapter additionally enforces alpha_normal=alpha_opposite=1 and tau=0. Nonblack scenarios may use light_only plus disabled_diagnostic NRH. Nonfixture growth remains blocked. Missing geometry registration, actual lamp pose, source-basis science or live native integration cannot be fixed by relabelling a file. `submit_light` publishes ready last, uses request/deadline hashes, rejects changed retries and accepts identical retries once. Actual consumption still requires a fresh native completion/audit/flux comparison, performed jointly with its owner. Protocol fixture submission alone is not integration.

Validated delivery: `build/p2_empirical_growth_boundary_20261013_01/delivery_verification.json` records three completed actual native light-only runs (0.5/0.6/0.7 assumed diffuse scenarios, 45 engineering triangles each), external_once audit and exact supplied/native absorbed flux equality for 135 leaf-intervals. The source field uses the measured 46 points; geometry, registration, direction and black leaf optics are labelled fixture assumptions. This evidence does not establish growth-mode or real optical accuracy. Original export-stage manifests remain immutable; completed native validation is recorded separately.
