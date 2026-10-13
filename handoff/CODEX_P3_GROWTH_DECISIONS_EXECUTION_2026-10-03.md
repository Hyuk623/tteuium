# P3 D8–D10 execution brief and report

Date: 2026-10-03. Scope: existing tools calculator only.

## Contract and compatibility clarification

Implement CODEX_P3_GROWTH_DECISIONS_IMPLEMENTATION_HANDOFF_2026-10-03.md.
The user explicitly resolved its conflicting byte-identical/mandatory-new-fields clauses:
preserve existing calculation values and add the required audit fields/event columns.
File hashes necessarily change for changed schemas; compare legacy numerical payloads
and unchanged export files. No new UI, fitting family, training, P4 feedback or linking.
No edits to protected pipeline, config, docs or human observations.

## Source review before implementation

Line references below refer to the pre-change sources saved with the baseline.

| Review discrepancy | Verified behavior |
|---|---|
| 1 | Engine UNITS (35–42) uses development days; calibration apply_parameter_set (769) rejects non-calendar clocks. D9 requires an explicit normalized-setpoint exception. |
| 2 | _decode_block (639) uses a 3D rotation vector; calibration supports scalar azimuth_rotation. Initial direction/3D bending remain assumptions. |
| 3 | _decode_block (661) uses absolute side targets. A fitted increment is not an absolute width target; no automatic conversion is authorized. |
| 4 | apply_parameter_set (827–840) refuses unfitted conditional, shared, serial and cross-trait wait dependence. Retain those guards. |
| 5 | _trajectory (740–745) binds segment_families by material segment ID. Existing segment D/k remain unchanged. |
| 6 | validate_model_config (328) requires provided_axes. No unobserved lateral/sympodial initiation exists. |
| 7 | validate_model_config (383) requires no_loss_over_horizon. No abscission model exists. Add only the declared age flag. |
| 8 | _trajectory emits only leaf events; _decode_block keeps optional area independent. Add truss/terminal events without surfaces; no allometry. |
| 9 | tools/growth_calibration_evidence.json (18–26) records recovered full PDF and Heartbreakers F1 Twiggy Red. This supersedes the old inaccessible-full-text statement, not cultivar applicability. |

E1 cannot pass the old calendar-only adapter; normalization and declared calibration
setpoint evidence must be checked. A stop_logit is not a sampled persistent N_max state.
The old sample_forecast flags (829–832) inspect only the clock and miss family/stop
dependencies and frozen fitted responses. Whole-config provenance is required.

## Classification of the broader review (not blanket authorization)

- Existing expansion, fixed segment directions, calendar clock, independent area and
  lognormal waits: keep existing behavior.
- Beta newborn decoder, normalized clock helper/binding exception, size-only DLI,
  node budget/events/scope and retention flag: additive opt-in changes authorized here.
- Rank covariates and declared angle priors can use existing configuration fields;
  supplied coefficients still require evidence. No literature defaults installed.
- log-asymptote replacement, width sum/asymmetry, two-angle bending, shared stem-rank
  law, scalar vigour and factor covariance would change the current parameter contract:
  not adopted by D8, not implemented.
- Optional area allometry and transient observation-phase model require additional
  contracts. Logistic/Gompertz are not adopted. New rho bounds/defaults are not adopted.
- Manual repeat-count support will be reported from the configured records directory;
  prior user-confirmed absence of repeated captures is preserved, without a global search.

## Execution and validation plan

Freeze legacy fixture and outputs under build/p3_d8_d10_20261003_01 before edits.
Add explicit per-coordinate beta targets/times and rejection rather than clipping;
preserve day-zero measurements and deterministic legacy random streams. Add strict D9
auditing/guards and D10 persistent per-axis draws, event evidence and unavailable scope.
Use existing finite-bank updates with no resampling. Run focused new invariants plus
existing growth/calibration/observed regressions; save JUnit, synthetic outputs and
verified hashes. Record actual outcomes below after execution.


## Continuation prompt incorporated

The user subsequently selected CODEX_P3_GROWTH_CHAT_PROMPT_2026-10-03.md.
It retains D8–D10 and adds explicit DLI basis/scope, post-response validity,
indirect/alias entry checks and frozen calibration-time assumptions. These are
included. Reuse the user-resolved compatibility policy above. The calendar adapter
requires an evidence-bearing fixed_setpoint/calendar_day reference inside the hashed
fit plan; a mere mean of a fluctuating history is refused. No calibration defaults
or fitter changes are introduced. No cross-chat messages or cross-project runs.

The configured get_settings().data_root/records directory is absent. No eligible
repeated dated leaf/truss counts were found there; the prior missing-data status
stands. This was a scoped check, not a repeat global inventory.

Initial verification: all 93 existing growth/calibration/observed regressions pass.
The saved pre-change legacy fixture reproduces exact state arrays, original event
fields and original summary rows after changes; see legacy_parity.json. Added
metadata/columns and unavailable truss rows are intentionally excluded from that
numerical parity comparison under the explicit user clarification.


## Delivery — 2026-10-04 Asia/Seoul

Implemented within the existing calculator. `tools/compound_growth.py` delegation
already works and needed no edit. Changed files:

- `tools/probabilistic_compound_growth.py`: beta_shape/_beta_value, clock helper and
  calibration guard, environment_audit/_validate_d9, history event adapter,
  validation, _trajectory, analytic decoding/remaining-growth updates, summaries,
  finite-bank event likelihoods, evaluation, export and blank reference templates.
- `tools/growth_calibration.py::apply_parameter_set`: normalized-clock exception
  from a frozen fit-plan reference, refusal of beta/stop-budget incompatible
  bindings, preserved fitted feature provenance and pack digest. No fitter changed.
- `tools/tests/test_p3_growth_decisions.py`: 49 new checks including the frozen
  pre-change numerical-payload checksum. Existing tests were not weakened.
- `tools/PROBABILISTIC_COMPOUND_GROWTH.md`, `tools/GROWTH_CALIBRATION.md`: actual
  inputs, units, output additions, supported scope and refusal reasons.

### New contract summary

| Location | Added fields and meaning |
|---|---|
| Newborn family | growth_curve=determinate_beta; per length/left/right/segment/area x_max in mm or cm2, a_m/a_e in development days or dimensionless a_m_over_a_e; explicit transforms/covariance |
| Model | environment_profile=d9; optional light_response with DLI mol/m2/d, whole_plant scope and basis_id, center/scale, dimensionless c_DLI and provenance |
| Clock | normalization contains t_base_c, t_ref_c, upper_knot_c (degrees C) and dimensionless m_max; helper preserves no-extrapolation |
| Frozen fit plan | calibration_clock_reference: fixed_setpoint, calendar_day, temperature_c, source_kind/source_ref; missing or fluctuating-history reference refused for non-calendar conversion |
| Reviewed structure axis | observed_node_count plus node_count_source_ref; never inferred from visible block or polyline count |
| Axis parameters | node_budget.pmf [{n,p}], optional truss_rule.first_truss_rank_pmf and interval_leaves, each with provenance |
| Trajectory | persistent n_max_drawn axis map; first truss rank in axis state; separate stable RNG streams |
| Events | event_kind, node_rank; null geometry/IDs for truss and terminal; no optical surface |
| Event observations | hashed optional event_observations CSV; plant/parent, kind, rank, aware observed_at, visibility, source_ref |
| Retention | optional max_leaf_age_dev_days and leaf_age_evidence; known-age predicted block flag only |
| Run/manifest | p3_light_coupling, p3_environment_paths {path,metric,target}, derived environment/light-used flags and audit availability |
| Summaries | main_axis_new_leaf_count; new_truss_count or unavailable; post_termination_scope unavailable with sympodial_continuation_not_modeled |

Output schema remains probabilistic-compound-1 with additive fields, under the
user's explicit compatibility resolution. Angle parameters remain radians; parent
coordinates remain board-frame mm; area remains cm2 with its own basis. JSON null
and empty CSV cells represent missingness. A CSV n_max_drawn cell is a JSON map.
No biological number is installed by the blank reference template.

### Verification

Final command:

```powershell
python -X utf8 -m pytest tools/tests/test_p3_growth_decisions.py tools/tests/test_probabilistic_compound_growth.py tools/tests/test_growth_calibration.py tools/tests/test_compound_growth.py -q --junitxml=build/p3_d8_d10_20261003_01/tests_delivery.xml
```

Result: **142 passed** (49 new + 93 existing), 16.84 seconds. Final JUnit has no
failures. The initial cross-directory golden test exposed absolute provenance-path
keys, not numerical differences; the final test normalizes only that directory
while retaining filenames and source hashes. Same-input-path state/event/summary
comparison is exact without any path normalization (`legacy_parity.json`).

Pre-change numerical payload SHA256:
`9e228f9d3207d1196b507c1b7779b9bfddeb5595402d9bc27c717fb3d4e01e7d`.
Portable golden (only provenance directory normalized):
`e4a861974b972e11fe278cff039e9ab56c9ba7a127cc413d3fab1eaa872b616a`.
The baseline manifest saves the original code hashes; pre-change source text was
not separately copied. This clarifies the earlier baseline wording.

Fresh reproducible bundles under `build/p3_d8_d10_20261003_01/`:

- `legacy_inputs`, `legacy_before`, `legacy_after`, `legacy_values.json`,
  `legacy_parity.json`: pre/post evidence and compatibility policy.
- `d8_d10_inputs`: synthetic observation/structure/model/summary inputs.
- `forecast_final`: existing CLI forecast with D8 + D9 + D10. All 16 trajectories
  valid; 34 leaf, 9 truss and 16 terminal events. These counts span samples, not
  one actual plant.
- `event_update_inputs`: synthetic held-out confirmed truss, explicit likelihood,
  associations and evaluation plan.
- `update_final`: finite-bank reweighted continuation; 9 positive-weight samples,
  ESS approximately 9; original trajectory IDs and N_max draws preserved.
- `evaluation_final`: confirmed truss presence score, evaluated_unaccepted; no
  biological acceptance claim.
- `blank_templates`: blank new biological fields and event-observation CSV.
- `verification_final.json`: 20 final forecast/update/evaluation output hashes,
  code-hash verification and sample/update invariants.

The actual CLI entry remained `python -X utf8 -m tools.compound_growth probabilistic`.
Forecast used `--history d8_d10_inputs/observations --structure d8_d10_inputs/structure.json
--origin d8_d10_inputs/origin.json --model d8_d10_inputs/model.json --summary-config
d8_d10_inputs/summary_config.json`; all paths above are beneath the build root.
Update/evaluate used the frozen forecast and event_update_inputs. Export destinations
must be fresh. Final manifests match current production code hashes.

### Refusals, limitations and scientific dependencies

- No training, new fit family, real calibration, private upload, UI work,
  protected-core/config/docs edits, cross-chat messages or P1/P2/P4 linking.
- Missing repeated captures/dates, event records and independent targets remain
  missing; all rates, targets, timing ratios, DLI response, thermal parameters,
  node budget and truss placement remain supplied assumptions.
- Existing leaves stay measured at day zero and exponential thereafter. Known-age
  beta continuations retain their age and residual curve after re-anchoring.
- Empty budget support, absent reviewed origin count and contradictory observed
  stopped-apex/budget combinations report unavailable. Invalid beta targets/times
  and incompatible entry/binding contracts are refused, never clipped/replaced.
- No sympodial initiation or abscission. Whole-plant counts become unavailable
  after positive-weight termination, while supported main-axis counts remain.
- Only whole-plant fixed DLI scope is supported. No inferred per-leaf exposure or
  feedback from a light solver. A daily-dose basis must be named explicitly.
- The fit-plan fixed-setpoint declaration is explicit evidence/assumption, not a
  reconstruction or validation of missing temperature histories. Unknown/variable
  histories are not promoted through a period-mean normalization.
- Review discrepancy 3 is a documented binding restriction, not an automatic
  width conversion: the current generic calibration adapter checks role units;
  it must not be used to bind scalar increments directly to absolute side targets.
  No such conversion was added in this narrow D8–D10 binding task.
- Legacy calibrated packs missing response provenance have audit status unavailable
  and cannot claim D9 compliance. In legacy mode, p3_light_coupling=none alone
  does not imply light_used=false: dependency paths and availability must be read.

Software scope is delivered. Real monthly predictive accuracy and coefficient
applicability remain unvalidated and need the existing measurement/review plan.

### Final key hashes

- `forecast_final/trajectory_parameters.json`: `b5c8972b0413a4c8e9cd30df321ca75a0b6533b60c923803d8f4553251e29786`
- `verification_final.json`: `b775b2ce1594c3873698fe9295c815abd506bc7be83c41c143ce548360d9ad8b`
- `tests_delivery.xml`: `ae26fdfb235e35d0c54021883d9a961ec2c146c58fe314fbc5b34de2163462d0`
