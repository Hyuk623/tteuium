# Implementation handoff: P2 reference-position DLI channel for P3 (D11)

Date: 2026-10-04, Asia/Seoul. From Claude to Codex (P2 light owner; P3 consumer check).
Authorization: decision D11 (`CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` section 8). Related: `CODEX_GROWTH_PACK_FIXES_IMPLEMENTATION_HANDOFF_V2_2026-10-04.md` row D11 (P3-side validation).
Status of real inputs: PPFD meter arrives around 2026-10-10. Reference position and lamp on/off clock times are **not yet known**. Implement and test with synthetic data now; leave real values blank.

## Goal

Fill the existing placeholder `reference_dli` in `tools/light_growth_bridge.py::_consumer_mapping` (currently `status='unavailable'`, reason `reference_position_channel_not_implemented`) with a real channel that produces the P3 DLI input defined by D11:

- quantity `incident`, model scope `whole_plant`, one declared reference position and horizontal sensor plane, unit `mol/m2/day`, time basis `complete_local_day`, explicit applicability interval.
- `basis_id` names the sensor plane/position (e.g. `incident_horizontal_canopy_top_center`) and must differ from every P2 tissue `area_basis_id`.

## Three source routes (implement A and C now; B as interface only)

| Route | `source_kind` | Input | DLI computation |
|---|---|---|---|
| A logged | `measured_logged` | CSV time series at the reference position | `DLI_d = 1e-6 · Σ_j PPFD_j · Δt_j` over each complete local day; trapezoid or declared step rule (declare which) |
| C spot × schedule | `measured_spot_schedule` | Spot PPFD readings at the reference position with lights on + declared on/off schedule | `DLI = mean(PPFD_spot) · Σ on-duration_s · 1e-6 · output_fraction`; valid only with `ambient_light='none'` and `output_constant=true` declared, else unavailable |
| B simulated | `simulated` | Virtual horizontal sensor at the reference position via existing `tools/ppfd_validation.python_point_ppfd` (empty rig, no plant occluders unless declared) + `integrate_light_schedule` | Interface and audit only now; returns unavailable `lamp_ppf_missing` until real PPF / fitted empty rig exists. Do not invent PPF. |

Reuse `integrate_light_schedule`, `ppfd_validation.python_point_ppfd`, `ppfd_validation.fit_empty_rig`, existing aware-time helpers. Do not create a second integrator.

## Input files (CSV + JSON)

`reference_position.json`
```json
{"schema_version": "reference-dli-1", "basis_id": null, "frame_id": "board_mm",
 "position_mm": [null, null, null], "sensor_normal": [0, 0, 1], "plane": "horizontal",
 "height_basis": "canopy_top|fixed_height", "timezone": "Asia/Seoul",
 "ambient_light": null, "output_constant": null, "output_fraction": 1.0,
 "applicability_interval_mol_m2_day": [null, null], "source_ref": null}
```
(`output_fraction=1.0` and 16 h/day are user-confirmed; on/off clock times are not.)

`schedule.json`: existing schedule schema (`start_hhmm`, `end_hhmm`, `output_fraction`, timezone). Leave times null in the template.

`reference_readings.csv` (routes A and C):
`reading_id,measured_at,ppfd_umol_m2_s,position_x_mm,position_y_mm,position_z_mm,sensor_model,sensor_serial,lights_state,notes`
- `measured_at`: timezone-aware ISO 8601.
- `ppfd_umol_m2_s` only; lux or W/m2 rejected (`non_photon_unit`), unless converted through existing `spectral_to_photon_umol` with a declared spectrum.
- Readings whose position differs from `reference_position.json` beyond a declared tolerance are excluded with reason.

Optional `spot_survey.csv` (same columns, other positions) is stored for later B calibration/validation; not used in the reference DLI value.

## Outputs (fresh `build/reference_dli_<date>_NN/`)

`reference_dli.csv`:
`basis_id,source_kind,local_date,dli_mol_m2_day,coverage_status,on_duration_s,n_readings,mean_ppfd_umol_m2_s,ambient_light,applicability_low,applicability_high,reason`
- `coverage_status` ∈ {complete, incomplete, schedule_missing}; incomplete days have empty `dli_mol_m2_day` and a reason. Missing intervals are never darkness.

`reference_dli.json`: the P3-ready block
```json
{"quantity": "incident", "model_scope": "whole_plant", "unit": "mol/m2/day",
 "basis_id": "...", "source_kind": "...", "time_basis": "complete_local_day",
 "value": null, "value_rule": "mean_of_complete_days|single_representative_day|declared_scenario",
 "days_used": [], "applicability_interval": [null, null], "fixed_over_horizon": true,
 "status": "available|unavailable", "reasons": [], "source_hashes": {}}
```
- `value_rule` must be declared; no silent averaging.
- Fill `_consumer_mapping()['growth']['reference_dli']` from this block (status/value/basis_id/applicability_interval), replacing the placeholder only when status is available.

## Rules

- `basis_id` equal to any P2 tissue `area_basis_id` → refused (`basis_collides_with_tissue_basis`).
- No PPF, absorptance or plant-tissue quantities enter this channel. Incident only.
- Route C requires declared `ambient_light='none'` and `output_constant=true`; otherwise unavailable (`spot_schedule_assumption_undeclared`).
- `mol/m2/day` ↔ `mol/m2/d` is notation only (no 86400 division).
- Value outside the declared applicability interval is still reported, with status `out_of_applicability` for P3 to refuse.
- Templates keep position, basis_id, times, applicability interval null. No defaults invented.

## CLI

```text
python -X utf8 -m tools.reference_dli templates --out build/reference_dli_template_new
python -X utf8 -m tools.reference_dli compute --position <reference_position.json> --schedule <schedule.json> --readings <reference_readings.csv> --route logged|spot_schedule --out build/reference_dli_new
python -X utf8 -m tools.reference_dli simulate --position <...> --schedule <...> --scene <scene.json> --out build/reference_dli_sim_new   # returns unavailable until PPF/fit exists
```
(New module `tools/reference_dli.py` or a subcommand of `light_growth_bridge`; Codex's choice, documented in `tools/LIGHT_GROWTH_BRIDGE.md`.)

## Tests (`tools/tests/`)

1. Logged route: synthetic constant 200 µmol/m²/s for 16 h → 11.52 mol/m²/day; trapezoid/step rule declared.
2. Gap in a day → incomplete, empty value; never treated as darkness.
3. Day boundary in declared timezone (lights crossing midnight).
4. Spot route: mean of spot readings × on-duration; missing ambient/constant declarations → unavailable.
5. lux / W/m2 rejected.
6. `basis_id` colliding with a tissue basis → refused.
7. Out-of-interval value → `out_of_applicability`.
8. Simulated route without PPF → unavailable `lamp_ppf_missing`.
9. Consumer mapping placeholder replaced only when available; P3 `_validate_d9` accepts the block (synthetic) and refuses it when out of interval.

## Deliverables

- Code, docs, templates (blank real fields), tests with JUnit XML in a fresh build folder.
- `handoff/CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md`; one LOG line; TODO entry "fill reference position, on/off times, readings after meter arrives (~2026-10-10)".
- Korean summary for the user, including a one-page measurement checklist for the meter arrival day (position, horizontal sensor, 3–5 readings 30 s apart, record time/position/model, optional survey points).
