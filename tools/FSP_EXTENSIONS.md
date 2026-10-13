# Native FSP optional extensions and declared axes

The single native V3 model owns light, physiology, allocation and state advance. Python prepares frozen inputs, validates native results and publishes checkpoints. Use `tools.tomato_fsp_pipeline.prepare_run`, `run`, `collect`, `replay`; `advance_interval` only publishes an existing native checkpoint. It never advances biology a second time.

Contracts: `handoff/FSP_EIGHT_CAPABILITIES_CONTRACT_2026-10-11.md` and `handoff/P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md`. All biological parameters remain conditional. Real-photo readiness and biological validation are separate from successful software tests.

## Observation routes

Scenario `observation_route`: `observed_metric`, `conditional_completion`, `observation_only`, or explicit `fixture_truth`. Omission preserves the prior consumer route. Main observed rows never silently fall back to fixture truth. `observation_only` writes evidence/readiness and does not launch GroIMP. Actual P1 v1 uses `plant_local_mm`; mm converts once to metres. A standalone m/mm conversion primitive is tested, but a full metre-based P1 producer schema is unavailable and is not advertised as supported.

Every simulated organ needs explicit mass, maximum mass, thermal age, true-order mapping, units and provenance in `organ_initialization`. Roots/reserves/apex clocks use `plant_initialization`; declared axes have their separate supplement. None becomes measured from a photo. Conditional completion additionally requires the exact hash-bound package entrypoint `completion_manifest.json`, schema `fsp-p1-completion-1`, producer version, observation links, scale/depth/posture assumptions, simulation identity mapping and hashes. This is a consumer interface contract, not a claim that a producer has delivered it.

```powershell
python -X utf8 -m tools.fsp_observation_intake --p1 build/p1_state_20261011_02 --route observation_only --out build/new_real_intake
python -X utf8 -m tools.tomato_fsp_pipeline prepare --p1 <package> --scenario <scenario.json> --out build/new_run
python -X utf8 -m tools.tomato_fsp_pipeline run --run-dir build/new_run --timeout 1200
```

Use fresh output paths. Failed or earlier issued artifacts are not overwritten.

## Optical materials, objects and photon units

Optional `extensions` object has `schema_version=fsp-extensions-1`, `wavelength_nm`, `materials`, `leaf_material`, `nonleaf_material`, `objects`, `max_depth`, and optional `schedule`. Each material declares absorptance/reflectance/transmittance, nonnegative and summing to one; `source_kind,source_ref,uncertainty,domain` are mandatory. The only supported scattering selection is `lambertian_reflection_straight_transmission`. This uses actual native Phong transport: diffuse reflection and straight/specular transmission, not diffuse leaf transmission. Grey optics have no calibrated wavelength, angle or botanical-face dependence.

Lamp inputs are umol photons/s. Extension mode explicitly converts to GroIMP watts using the declared monochromatic wavelength and exact SI constants, then records raw W and converted photon units separately. A chosen wavelength is a scenario hypothesis, not a measured LED spectrum. Legacy requests without extensions preserve the historical native numerical-power convention.

`optical_flux.csv` exports independent native first-hit received, absorbed, reflected and transmitted watts plus hit count. `scene_photon_budget.csv` records emitted W, leaf/nonleaf absorption, the conversion factor and checkpoint photon-unit columns. Escape, cutoff termination and estimator residual remain **unavailable**, because this GroIMP API does not expose terminal accounting. Received power suppresses repeated same-object hits along a path: total incident PPFD is therefore published only for black leaves, whose first hit absorbs/terminates. Nonblack leaves retain `received_first_hit_*` and an explicit unavailable total incident field. Never divide absorbed flux by absorptance. Reflection/transmission are internal transfers, not extra emitted photons or terminal sinks.

Near a perfect reflecting/transmitting limit, native float32 spectra can yield tiny negative raw absorption by subtraction. Raw values remain visible; validation permits only a relative float32 roundoff bound (32 epsilon times the received/reflected/transmitted scale). Physiology uses nonnegative absorption only within that bound. This is a numerical roundoff bound, not an empirical physical uncertainty or fabricated energy closure.

Nonblack leaf growth is blocked until the NRH incident/absorbed fit-basis decision is reviewed. Nonblack materials can be evaluated in light-only mode. Native two-sided interception divides by one physical full-outline lamina area, never two copies of the same tissue.

Objects have unique `scene:` IDs, role `pot|shelf|post|non_target_plant|optical_fixture`, static triangles in `object_local_m`, a proper 4x4 rigid transform, material and source evidence. The transform is applied once. Duplicate placed triangles are rejected. Objects participate in optics and the nonleaf absorption category, with no tissue mass, physiology, allocation or carbon pool. Example construction: `tools.fsp_extensions_acceptance.plate`; material example: `extension`. Do not adopt its dimensions or coefficients as measurements.

## Actual piecewise schedules

`extensions.schedule` contains aware `start,end`, `interpolation=piecewise_constant`, positive `max_step_s`, `lights` keyed by every lamp ID, and `environment`. Every lamp/environment row covers an exact `[start,end)` segment and names `source_kind`. Lamp rows have `fraction` in [0,1]; environment rows have `temp_c,co2_ppm`. Rows must cover the full horizon with no gap or overlap. Native intervals split at all boundaries and the maximum step. The current limit is 365 intervals.

Native source powers use each lamp's instantaneous fraction. Photosynthesis applies nonlinear NRH separately per interval; maintenance and thermal age use actual elapsed days. Midnight does not reset clocks. Geometry is frozen inside each interval; funded/new tissue changes the next light calculation. CO2 and temperature-dependent photosynthetic responses remain inactive; temperature still drives the conditional development clock. `time_boundaries.csv` and viewer elapsed-day labels use actual durations. `absorbed_dli_mol_m2` integrates instantaneous PPFD over the interval seconds. Equal DLI is not assumed to imply equal carbon gain.

## H1-H3 parameter hooks

Hooks are optional entries in the existing parameter registry with its required provenance fields. Membership in `vtc_development_io.PARAMS` alone is not sufficient to activate them.

| Hook | Required value and semantics |
|---|---|
| CURVE_RATIO | Nonnegative, positive-sum vector for its exact segment count. `by_segment_count` supplies other actual PAIRS counts, e.g. value `[2,1]`, map `{"1":[1]}`. Normalized per compound. No truncation/interpolation. Bend sign resides in the amplitude, downward-positive. |
| BENT_FRACTION | Numeric [0,1] with explicit `templates={flat_total_bend_deg,bent_total_bend_deg}`, or null/inactive. SHA256 of persistent organ ID and seed chooses once. Applies only to generated compounds; imported posture and observed labels remain unchanged. |
| AREA_CORRECTION | Positive factor plus `area_basis=summed_one_sided_full_outline_lamina_m2`. Produces `area_correction.csv`, including raw/corrected reporting area, source and uncertainty. Never changes optical triangles, SLA, mass or allocation. Missing omitted tissue remains unavailable. |

`parameter_activity.json` records activation. `posture_assignments.csv` records identity-stable draws. `area_correction.csv` is derived after native calculation for both seed and integrated runs. Current Claude forecast wrapper can activate H3 explicitly with `--enable-hooks`; its H1 vector lacks the per-count mapping and H2 fraction is unavailable, so these remain inactive with reasons. Wrapper-side axis forwarding and new optical/schedule controls require its own explicit interface support.

## Declared side axes

Opt in with `axis_contract=fsp-axes-1`, `topology_scope=provided_axes`, `topology_completeness=unavailable`, and a complete `axes` list including M for each selected plant. Exact per-axis request format, hidden state and science choices are in the resource contract, section 3. Producer `axis` maps explicitly to native logical `axis_id`, and `axis_state` to the accepted stage alias. No prime characters are identifiers. Axis state is never automatically promoted from axis_shoot to substem by a modeled age.

Each S axis requires an existing main-axis attachment node and matching parent_rank, two existing registration compounds, explicit physiological clocks/masses and provenance. Its graph parent is the declared node. Sympodial continuation retains the same logical axis; `developmental_axis_id` identifies the actual segment. No missing side axes are synthesized.

Each declared axis has `SUBSTEM_SINK_SCALE` and `APPLY_DETERMINATE_STOP` parameter records. Unity means no dominance. Allocation draws from one plant pool using capped weighted demand, and each tissue is charged once. The common root is attributed to M only to make diagnostics exhaustive. Stop=true selects the same conditional V3 program independently on that axis; false selects declaration-only initiation, with existing tissue expansion retained. Main stop never stops another axis. Actual substem truss behavior remains unresolved.

Native and committed `axis_flux.csv` gives absorbed light, gross assimilation, maintenance, demand, allocation, structural carbon and growth respiration per interval/plant/axis. It sums to organ/plant ledgers for growth runs. Light-only gross is explicitly an uncommitted diagnostic. States/events/meshes carry axis_id and parent_rank; commits include axis_inventory.csv and axis_parameter_registry.csv. An axis's assimilation need not equal its growth: its photosynthate joins the shared plant pool. Nutrients remain plant-level, growth feedback disabled.

## Deferred mechanics and failure semantics

Imported meshes retain exact initial posture and mass-funded isotropic expansion. `rigid_about_anchor` is a tested engineering primitive, not a runtime developmental bending law. `imported_deformation` is rejected without the missing reviewed age/anchor/mass-area contract. No phototropism, curl classifier or hidden pivot is supplied.

`fsp_nutrient_transaction.begin/finalize` is an explicitly marked protocol fixture only. It binds transaction, predecessor, model, parameters, interval and plant IDs, validates prescribed demand/availability/use, returns unused reservations, and atomically commits or rejects stale/timeout/cross-plant/conflicting responses. It does not pause native V3, implement nutrient-limited growth, solve uptake or provide a joint biological commit. `nutrient_coupling` remains rejected without the scientific contract.

## Field migration

| Previous interface | Optional addition / preserved behavior |
|---|---|
| Daily dt_s / light_hours | Existing inputs unchanged. Explicit schedule compiles aware variable intervals. |
| Black leaf absorbed flux only | Optional independent first-hit received/raw optical flux; black total incident, nonblack total incident unavailable. |
| No scene object ledger | Static object manifest plus nonleaf absorption; no object carbon. |
| Existing parameter registry | Base keys still sufficient; H1-H3 optional and provenance-bound. |
| One active controller per plant | Versioned axes list introduces independent declared-axis controllers, one shared reserve. |
| axis_id = graph segment | Unchanged in legacy mode. In fsp-axes-1, axis_id=M/S1 and developmental_axis_id preserves the segment ID. |
| State / event / mesh CSVs | Additive parent_rank/axis metadata; consumers must select columns by name. |
| Post-run prescribed nutrient ledger | Still diagnostic, not relabelled as causal feedback. |

Repeatable native acceptance commands (fresh paths):

```powershell
python -X utf8 -m tools.fsp_axes_acceptance --mode growth --out build/new_axis_growth --rays 4800000
python -X utf8 -m tools.fsp_axes_acceptance --mode shading --out build/new_axis_shading --rays 4800000
python -X utf8 -m tools.fsp_extensions_acceptance optics --out build/new_optics --rays 4800000
python -X utf8 -m tools.fsp_extensions_acceptance schedule --out build/new_schedule --rays 4800000
python -X utf8 -m tools.fsp_extensions_acceptance hooks --out build/new_hooks --rays 4800000
python -X utf8 -m tools.fsp_extensions_acceptance intake --out build/new_intake --rays 4800000
```

These commands use explicit synthetic fixtures and local GroIMP/VTC prerequisites. Original VTC source and redistribution-license status remain unchanged; local execution only.
