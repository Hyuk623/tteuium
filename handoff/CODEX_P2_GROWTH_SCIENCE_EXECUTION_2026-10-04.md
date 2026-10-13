# P2 growth Science clarification execution

Date: 2026-10-04. Objective: CODEX_P2_GROWTH_SCIENCE_CHAT_PROMPT_2026-10-04.md.

## Brief before implementation

Inspected current rules, relevant LOG/TODO, Science L01/L02 and accepted decisions 1/3 (question 2 undecided), ownership index and delivered P2 code. The existing package exports supported tissue DLI, not a declared reference-position/sensor-plane channel. Probes are explicitly unimplemented. No new sampling subsystem, reference location, optical input, growth coefficient or applicability bounds may be fabricated.

The existing full-day integrator, strict missingness, actual angular transport and canopy splits already implement their physical accounting. Reuse them. A real metadata defect remains: consumer_mapping.growth.light_covariates still says arrival features are pending the core hook despite delivered direct-angular-1. Correct that statement, add an explicit unavailable reference-DLI capability/metadata declaration, and clarify tissue versus reference semantics in the existing schema conventions. The independent P2 consumer should reject false reference capability/numeric/basis claims; P3 remains owner of applicability/binding validation and rejecting illumination as growth orientation. This is provenance validation, not a P3 adapter.

Preserve original face/absorptance semantics. Document simultaneous fixture summation at one patch/time before future nonlinear physiology, without adopting the undecided incident/before_mito/adaxial_only policy. Preserve actual lamp metadata at 16 hours/day and 100%; missing clock windows/PPF stay missing. Only P2 tools/schema/tests/guides and this handoff/build evidence will change; no P3/calibration/P4 edits or cross-project runs.

Validate explicit unsupported reference claims, complete/incomplete days, unknown versus zero, units and existing angular/canopy invariants. Regenerate into fresh build paths after code/schema hashes change; preserve old outputs. Record implementation versus documentation, exact producer fields, tests, hashes and remaining physical/reference requirements below.

## Execution outcome

The bounded P2 clarification is complete. **No reference-position sampling or reference-DLI calculation channel was added.** This is the explicit unsupported-channel branch in prompt items 2/3, not a claim that the accepted P3 reference input can already be supplied. Existing full-day tissue integration, angular transport and canopy preservation were reused and verified without numerical changes.

Implemented changes:

- `tools/light_growth_bridge.py::_consumer_mapping`: corrected the obsolete pending-core-hook statement; added explicit unavailable `growth.reference_dli`, P3-owned orientation-binding guidance and simultaneous-fixture/nonlinear-use/undecided-face guidance. `build_package` adds `capabilities.reference_dli`.
- `tools/light_growth_schema.json::conventions`: added tissue/reference DLI, orientation and nonlinear-use meanings. No CSV columns, numeric units, primary keys, transport formulas, schedule rules or existing field meanings changed.
- `tools/light_growth_consumer.py::_check_reference_channel_unavailable`, called by `validate_package`: rejects falsely enabled reference capability, tissue area basis reuse, invented numeric values (including zero), other invented reference basis or applicability interval, and wrong required quantity/unit/spatial/time/model scope. It checks P2 provenance only. It does not implement P3 model input validation, coefficients or a reference importer.
- `tools/tests/test_light_reference_provenance.py`: 15 focused tests, including 10 rehashed bad-producer claims, four complete-day/coverage cases and a preserved angular/canopy split case.
- `tools/LIGHT_GROWTH_BRIDGE.md`: documents the accepted reference input and unsupported channel, required nonlinear accounting order, scope and owners. Removed wording suggesting a tissue DLI row could be selected for P3's clarified reference input.

Unchanged production functions inspected: `integrate_light_schedule`, `integrate_dose`, `export_spatial_light`, `export_compound_light_features`, `split_canopy_results`; core `direct_light` and DirectionCollector also remain unchanged. The new reference metadata does not change their computation.

## Exact implemented fields, units and producers

| Output | Producer and meaning |
|---|---|
| `light_samples.csv::received_ppfd_umol_m2_s` | `export_spatial_light` / `integrate_light_schedule`: incident two-face receipt per supported one-sided tissue area, umol photon m-2 s-1 |
| `absorbed_ppfd_umol_m2_s` | Same path with absorptance already applied once, umol photon m-2 s-1 |
| `quadrature_area_m2`, `area_basis_id` | Supported tissue quadrature weight and evidence identity; never a reference-position identifier |
| `compound_light_features.csv::received_umol_s`, `absorbed_umol_s` | Area-weighted supported tissue flux; sum photons before dividing by area |
| `light_dose.csv::incident_dose_mol_m2`, `absorbed_dose_mol_m2` | `integrate_dose`: covered requested-interval dose, mol photon m-2; missing full coverage makes complete dose unavailable |
| `light_dose.csv::dli_mol_m2_day` | Incident supported-tissue dose only for a complete declared local day, mol photon m-2 day-1 (`mol/m2/day`); it is not reference DLI |
| `start_at`, `end_at`, `timezone`, `requested_seconds`, `covered_seconds`, `complete_local_day` | Existing dose/interval clock and coverage provenance; actual DST-day length is preserved |
| Raw `arrival_flux_umol_s`, `arrival_M_*_umol_s`, `arrival_B_*_umol_s` | Actual direct paths -> collector -> bridge. Same F/M/B and grow receiver-to-emitter convention, all raw components umol/s; translated positions never translate vectors |
| `observed_rachis_*` | Reviewed full observed axis channel, separate from light moments/directions; no light-to-growth orientation law |
| `capabilities.json::reference_dli` | `build_package`: `unavailable_reference_position_channel_not_implemented` |
| `consumer_mapping.json::growth.reference_dli` | `_consumer_mapping`: unavailable capability description detailed below; no sensor observation or numeric reference measurement |

The reference metadata has `status="unavailable"`, `reason="reference_position_channel_not_implemented"`, and null `value`, `basis_id`, `applicability_interval`. Its requirement descriptors are `unit="mol/m2/day"`, `quantity="incident"`, `model_scope="whole_plant"`, `spatial_basis="declared_reference_position_and_sensor_plane"`, `time_basis="complete_local_day"`. Whole-plant scope is the P3 model application scope, not tissue-average geometry. Neither a physical position nor interval bounds are populated.

`growth.orientation_binding` documents P3's rejection requirement; **the actual P3 guard belongs to P3**, and was not edited or claimed verified here. `physiology.fixture_combination` documents summation at the same patch/time before nonlinear exchange. `physiology.face_policy` explicitly leaves P4 policy unselected. No shared c_DLI was added; declarations by growth_curve and applicability rejection remain P3's responsibility under decision 3.

## Required future reference-channel input (handoff only; not an implemented schema)

No current package table supports these reference records. The following proposed field names define the information a future separately authorized importer/producer must preserve; they are not accepted request keys or fabricated data in this delivery.

| Required input | Fields and units / owner |
|---|---|
| Identity and applicability target | `reference_id`, `basis_id`, `plant_instance_id`, `source_plant_id`, `run_id`, `scenario_id`; explicit association when one reference serves several plants. `basis_id` identifies the declared position/plane and must differ from all P2 tissue `area_basis_id` values. Human/reviewed source supplies association. |
| One physical reference location | `position_xyz_mm` (one 3-vector), `coordinate_frame`, `frame_id`, frame-transform evidence if needed. Do not choose a centroid, tissue mean or quadrature sample implicitly. |
| Sensor plane | `plane_unit_normal_xyz` in the same frame (unit vector), explicit receiving-side convention and sensor/virtual-receiver geometry evidence. This is a reference-plane declaration, not a botanical leaf-face policy. |
| Clock/day | `timezone` (IANA), `local_date`, timezone-aware `day_start_at`, `day_end_at`; complete local midnight-to-next-midnight day. |
| Incident light history | Nonoverlapping `interval_start_at`, `interval_end_at`, `incident_ppfd_umol_m2_s`, availability/reason per interval. Measurements need temporal support; isolated instantaneous readings do not establish a complete day. Known zero is distinct from missing. |
| Coverage | `coverage_status`, `requested_seconds`, `covered_seconds`, explicit gap intervals and reasons. Only complete valid coverage permits numeric DLI; do not interpolate or treat unlogged times as off. |
| Light state and provenance | Actual fixture IDs and their simultaneous states/fractions, `photon_band`, measurement/model `source_kind`, evidence paths + SHA256, sensor identity/calibration or transport backend/code/source hashes. Keep incident light separate from absorbed tissue output. |
| Scene context | Full canopy/occluder context hashes, geometry/snapshot validity, placement and ambient-light evidence; preserve shared-scene context if the reference is reported for one instance. |
| P3 numerical applicability | P3 supplies/reviews `applicability_interval` as a declared DLI range (bounds in mol/m2/day), source evidence and model scope, with coefficient binding per growth_curve. P3 enforces out-of-range refusal. No numeric bounds are chosen by P2. Record any temporal validity separately from this numerical DLI range. |

A future supported channel must compute `DLI = 1e-6 * sum(incident_ppfd_umol_m2_s * interval_seconds)` over the complete day after summing simultaneous fixture contributions at that same sensor plane. No area multiplication or absorbed-light substitution applies to reference incident PPFD. Multi-position records are distinct reference candidates, not an implicit average. This rule is documented, not newly executed on an invented reference sensor. Existing sensor PPFD validation utilities elsewhere do not constitute the missing daily channel in this package.

## Reused invariants and future P4 use

Current `integrate_light_schedule` retains patch/sample and per-fixture rows, then writes one `fixture_id=all` sum per patch/time. `integrate_dose` integrates actual interval PPFD and separate time-indexed flux; no final-area multiplication or double absorptance. Missing schedules, light or geometry remain unavailable. Supported subtotal fields do not imply complete-day DLI.

Future P4 processing should select direct time-resolved `fixture_id=all` samples once, or equivalently sum the real fixtures at the same patch/time once, **before** a nonlinear leaf-exchange response. Do not add `all` to fixture rows, sum per-fixture photosynthesis, or replace heterogeneous patch responses by a plant-mean response. Join one interval duration per run/scenario/snapshot/time/backend/replicate. Raw fixture contributions, IDs, area weights and hashes remain available for a later reviewed adapter. No nonlinear exchange is computed here; question 2 (before_mito/incident/adaxial_only) remains undecided, and the existing physical two-sided light transport is unchanged.

## Executed verification and fresh results

**181 tests passed: 84 core + 97 tools**, zero failures/errors. The tools suite includes all 15 new reference-provenance tests plus existing scalar/side/day/DST/unknown/area-change/angular/region/fixture/canopy tests. Core tests still include actual callback off/on and same-call scalar/normal parity, extended/opposed sources, rotations/inverse/translation, background/own-triangle handling and explicit beam-exclusion zeros. atol=1e-10, rtol=1e-9; direction cancellation policy remains 1e-12. No physical acceptance tolerance was invented.

Fresh demo path: `build/light_growth_science_20261004_01/`, with new inputs, preparation, hierarchy calculation, request, `package`, `P1_in_canopy`, `P1_COPY_in_canopy`, `consumer_checks.json`, `copy_roundtrip.json`. All three packages pass the independent consumer, including the new provenance guard. The main package has 1344 samples, 1080 feature rows, 14 interval rows and 48 dose rows.

Final audit: `build/p2_growth_science_20261004_01/verification.json`, with source/code/artifact and package-manifest hashes, before/current hash snapshots, test counts and every table comparison. Every value and row in all five tables of the main and split packages equals the previous directional delivery exactly. All historical artifacts under `build/light_growth_directional_20261004_01` still match their original hashes. Only metadata/code freshness changed; historical hash records were never patched. Core source, human configuration and all real-lamp draft files in the before/current snapshot are byte-identical. Split tables also equal parent canopy row selections exactly, including global receiver indices and context provenance.

The initial audit-only comparison used slash-form expected names against Windows backslash paths; normalized the audit's path spelling and reran successfully. No simulation or data repair was needed. Runtime tests passed on their first run for this clarification.

Commands (project root):

```powershell
python -X utf8 -m pytest tools/tests/test_light_reference_provenance.py tools/tests/test_light_growth_bridge.py tools/tests/test_light_angular_exports.py tools/tests/test_light_direction_diagnostics.py -q --basetemp=build/p2_growth_science_20261004_01/tools_tmp --junitxml=build/p2_growth_science_20261004_01/tools.junit.xml
python -X utf8 -m pytest tests/test_light_inputs.py tests/test_light_raytrace.py tests/test_light_pipeline.py tests/test_light_angular_transport.py -q --basetemp=build/p2_growth_science_20261004_01/core_tmp --junitxml=build/p2_growth_science_20261004_01/core.junit.xml
python -X utf8 -m tools.light_growth_demo --out build/light_growth_science_20261004_01
python -X utf8 -c "import runpy; runpy.run_path('build/p2_growth_science_20261004_01/verify_delivery.py',run_name='__main__')"
```

## Completion audit against this prompt

| Item | Evidence / status |
|---|---|
| 1 brief + inspect/reuse | Brief above; scoped metadata defect repaired, existing integration/export/math reused; complete |
| 2 reference versus tissue; unsupported channel and required fields | Explicit unavailable capability/record, independent rejection checks, future input table above; complete through the specified unsupported-channel branch |
| 3 existing supported reference channel | None exists in this package. No fabricated sensor/value; complete-day rule and provenance requirements documented for future work. Existing tissue full-day, gap, unknown and zero checks pass. Reference calculation deliberately unimplemented |
| 4 L02 and P3 binding owner | Core/schema convention unchanged, actual angular regressions pass, orientation guard responsibility documented; P3 implementation not claimed |
| 5 IDs/canopy/source/area preservation | Both split consumers pass and all split rows equal parent selections; all old/new CSV values identical; complete |
| 6 simultaneous contributions/nonlinear/absorptance/face policy | Existing per-fixture and all sample rows preserved, guidance explicit, undecided P4 policy untouched; complete |
| Lamp inputs | Entire _03 lamp draft unchanged: 16 h/day, 100%; unknown PPF, real clock windows, aperture/beam and other optical evidence remain unknown |
| Validation/hashes/delivery/LOG/TODO | Two passing JUnit reports, three passing packages, hash/value preservation audit, this execution report and current IO guide; complete |

Remaining work belongs to a future authorized reference-channel implementation and independently evidenced reference sensor/model inputs, P3's model guard/coefficient scope, and the existing physical/P4 science review. No P3, calibration, P4, human configuration or observations were edited. No cross-project linking, fitting, phototropism, Native execution, inference/training or upload was initiated. Software checks do not establish real PPFD or biological accuracy.
