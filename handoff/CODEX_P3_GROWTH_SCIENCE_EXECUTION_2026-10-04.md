# P3 accepted growth Science fixes — execution brief

Date: 2026-10-04 (Asia/Seoul). Source: CODEX_P3_GROWTH_SCIENCE_CHAT_PROMPT_2026-10-04.md.

## Scope and inspected state

Implement accepted decisions 1/3 and F2/F3/F7/F8/F9/F11 in the existing P3
calculator and its calibration adapter. P3 alone owns these edits; no P4 runtime
or equation-registry edits, cross-project linking, training or real fitting.
Read the Science disclosure, decision addendum, prompt index, D8–D10 delivery,
semantic-guard verification and actual current functions. The last completed
task was verified progress: 256 Windows tests and six semantic-guard hashes.
This is the first turn on this new goal, with no blocking dependency established.

Current code confirms the reported gaps: the temperature helper starts at T_base;
one c_DLI scales both curve families; DLI provenance has no local-day/domain
contract; DLI-induced invalid targets fail entire samples. Side target meaning
is generic absolute_target. The closed calibration guard already checks meanings,
clock compatibility and stop-budget mismatch. It needs finer taxonomy and L02
directional-source refusal, not replacement. update_forecast currently accumulates
geometry and then event evidence into the same log weights and only reports final
ESS. _remaining preserves residual beta increments (its final endpoint shifts
with the observed anchor); no new reanchor policy is authorized.

## Planned implementation and verification

- Explicit incident reference-position/plane, complete local-day provenance,
  applicability interval, and distinct per-curve coefficient identities/roles.
  Reject old underspecified light contracts rather than fabricate migration data.
- Optional declared lower temperature knot; preserve fixed-setpoint calibration.
- Trait/curve unavailability within persistent weighted trajectories, original
  ensemble coverage and structured reason exports; no zero-growth substitution.
- Exact reviewed narrowing threshold target < min(observed stations), with
  explicit narrowing_assumption evidence; no broadened threshold.
- Extend binding meanings/L02 refusal and ESS stage diagnostics without changing
  accepted numeric laws or final posterior weights.
- Freeze current valid fixtures/code hashes, add focused checks, run relevant
  P3/calibration regressions, verify exports/hashes, and publish equation-function
  locators for P4 through this handoff. Append actual results after verification.

Deferred: P4 question 2, optional reanchor_weight, transient posture, truss_observable,
new coefficients, biological validation and interproject adapters.


## Completed implementation and acceptance

Status: **all authorized P3 software requirements verified**, 2026-10-04. This
extends the previously reviewed semantic guard, rather than replacing its five
cases. Original `build/p3_semantic_guard_20261004_01` remains historical evidence.
The current evidence root is `build/p3_growth_science_20261004_01`.

| Requirement | Implemented behavior | Verification |
|---|---|---|
| Decisions 1/3 | Incident reference position/plane, whole-plant fixed scope, disjoint tissue basis, complete local day, explicit inclusive domain; separate curve coefficient identity/role | 14 refusal cases, equal-valued distinct bindings accepted, complete 23-hour DST local day accepted, curve-specific scaling checked |
| F2 | Optional explicit lower zero knot below T_base; no extrapolation | Sub-base pause, out-of-domain refusal, reference multiplier 1; default clock unchanged |
| F3 | Two DLI failure modes mark affected traits unavailable while retaining trajectories and weights | Mixed finite ensemble retains 32 IDs and mass 1; conditional quantile coverage/reason mass verified; negative widths remain null; birth geometry preserved; unrelated invalid reference beta fails |
| F7 | Reference-DLI side-target meaning and exact narrowing evidence threshold | Target between station min/max and equality allowed; below minimum requires evidence; nonunit-factor asymptote checked |
| F8 | Existing blocks and segments hard-refuse beta | Existing block regression retained; added segment refusal; guide corrected |
| F9 | Complete coordinate meaning taxonomy; L02 direction refusal; prior clock and stop-budget checks retained | Five original guard cases retained; all engine coordinates catalogued; actual synthetic frozen packs reject L02 and stop-budget; clock fails before binding |
| F11 | Prior -> geometry -> geometry+events ESS diagnostics; covariance limitation disclosed | Independent single-application likelihood calculation matches final weights; all-zero support stays incompatible; no-model stages unavailable; source bank immutable |
| Deferred G03 behavior | Remaining beta increment preserved with endpoint displacement | Observed +3 mm anchor shifts endpoint from 8 to 11 mm; no new reanchoring policy |

### Changed files and runtime schema

- `tools/probabilistic_compound_growth.py`: clock helper, reference-DLI validation,
  per-curve size response, narrowing/curve availability, state and summary audits,
  ordered update diagnostics, CSV/manifest fields and blank templates.
- `tools/growth_calibration.py`: semantic catalog and source-provenance rejection
  in the existing adapter. Fit equations, clock policy and frozen-pack hash checks
  are unchanged.
- `tools/PROBABILISTIC_COMPOUND_GROWTH.md`, `tools/GROWTH_CALIBRATION.md`: actual
  contracts, compatibility, equations and limitations.
- `tools/tests/test_p3_growth_decisions.py`: explicit synthetic DLI fixture migrated
  to the accepted contract; old sample-failure expectation updated for F3.
- `tools/tests/test_p3_growth_science.py`: 27 focused synthetic cases.

There is no separate P3 JSON-schema artifact to update: runtime validation and
`templates/d8_d10_parameters.json` define the existing input contract. The outer
`probabilistic-compound-1` schema and `stochastic-grammar-proposal-1` model IDs are
retained. The refined optional DLI block is a deliberate validation tightening;
old underspecified DLI configs are refused with migration reasons. No inferred
migration, coefficient cloning, default domain or fabricated plane/day is supplied.

New/refined inputs under `light_response`:

| Field | Unit / meaning |
|---|---|
| `light_basis`, `basis_id`, `scope` | incident; reference identity; whole_plant |
| `reference.position_mm`, `normal_unit_xyz`, `frame_id`, `coordinate_frame` | mm; unit normal; declared common frame |
| `local_day.start_at/end_at/timezone/coverage` | aware timestamps, IANA zone, complete next-midnight local day |
| `applicability_interval.min/max/unit` | inclusive mol/m2/d domain |
| `coefficients.<growth_curve>.coefficient_id/role/c_DLI` | unique binding identity; increment or potential maximum; dimensionless standardized-DLI coefficient |
| `center`, `scale`, `value` | mol/m2/d; scale positive; value fixed across horizon |
| `source_kind/source_ref` | required on response, reference, day, domain and each coefficient |

Other input additions are optional `lower_knot_c` (degrees C) to the temperature
helper and family `narrowing_assumption` evidence when target < min(stations).
No new environment variables. CLI input paths remain explicit; IANA timezone data
must be installed for reference-DLI local-day validation (available on this host).

Outputs retain JSON null / empty numeric CSV cells for unavailable values:

- Draws: `reference_size_targets`, `size_target_factor`, `dli_binding`.
- Trajectory availability: component/quantity/reason/coefficient identity;
  decoded states and `block_states.csv`: `growth_unavailable`.
- DLI summaries and `summary.csv`: original `ensemble_weight`,
  `available_fraction_of_ensemble`, `unavailable_weight`, `unavailable_reasons`.
  Each reason has weight and probability_of_ensemble. Quantiles remain conditional
  on available curves; counts/existence are not removed with unavailable traits.
- `update.json`: `conditioning_diagnostics` with ordered stage ESS, signed losses,
  rejection IDs, stage status, weight-update flag and covariance disclosure.
- Every export manifest: `cross_organ_measurement_correlation="not_modeled"`.

### Numerical compatibility and verification

The frozen pre-edit states at 0/7/14/21/30 days and all baseline summaries match
exactly. Baseline weights and events also match exactly. The earlier portable
legacy numerical golden regression still passes. Additional fields intentionally
change new file bytes/hashes, as the user authorized. Conditional DLI failures
change from whole-sample failure to trait unavailability by explicit F3 decision.

- Final Windows regression: **174 passed in 32.89 s**, zero failures/errors.
  Includes 147 existing cases and 27 new cases, including all five semantic guards.
- Three actual forecast CLI runs: valid two-curve DLI, low DLI and mixed targets.
  All preserve 32 valid trajectories and original total weight 1.
- Joint geometry/event update exported; 37 manifest-referenced output hashes
  verified across forecasts and update artifacts.
- ESS example: prior 32; after geometry 26.12794010802128; after events
  13.22354523441057. Signed stage losses 5.872059891978719 and
  12.90439487361071. These are ordered diagnostics, not a causal decomposition.
- An initial new test used the internal JSON name instead of the existing CSV
  column `axis_length_mm`; corrected that test assertion. No production defect
  was concealed and its failing JUnit remains in the evidence directory.
- `before/`, `before_hashes.json` and source diffs preserve the pre-edit code.
  `verification.json` records final source/artifact hashes and exact CLI arguments.

Commands (project root):

```powershell
python -X utf8 -m pytest tools/tests/test_growth_calibration.py tools/tests/test_p3_growth_decisions.py tools/tests/test_probabilistic_compound_growth.py tools/tests/test_compound_growth.py tools/tests/test_p3_growth_science.py -q --junitxml=build/p3_growth_science_20261004_01/regression_final.xml
$env:PYTHONPATH='.'
python -X utf8 build/p3_growth_science_20261004_01/verify_delivery.py
```

The delivery script requires a fresh `delivery/` destination; use a new evidence
root when reproducing instead of overwriting this recorded run. Fixtures and
calibration runs are synthetic only. Exact hashes are host-run evidence; the
previous Linux/Windows floating-point portability limitation is unchanged.

### Equation-to-function map for P4 F1 owner

Paths/lines below describe the verified source hashes in the next section.
P4 may use this map for its registry; no registry or P4 runtime was edited.

| ID | Current function locator | Meaning / boundary |
|---|---|---|
| G01 | `tools/probabilistic_compound_growth.py:91 normalized_temperature_clock`; `:846 _clock` | Integrate declared multiplier over calendar intervals; optional sub-base zero interval; no extrapolation |
| G02 | same file `:959 _h`, `:1002 _decode_block`, `:292 _check_narrowing` | Exponential remaining increments; station asymptote w0+f*(target-w0); reference extent semantics |
| G03 | same file `:58 beta_shape`, `:68 _beta_value`, `:1476 _remaining` | Newborn beta only; original birth and shape age retained; observation shifts future endpoint |
| G04 | same file `:180 _validate_reference_dli`, `:275 _size_response`, `:300 _check_curve_availability` | Incident reference DLI, per-curve factor exp(c*(value-center)/scale), explicit domain; trait unavailability |
| G05 | same file `:907 _draw`, `:1147 _trajectory` | Existing joint plant/process randomness; no covariance-law changes |
| G06 | same file `:1100 _new_block`, `:1002 _decode_block` | Existing parent-local birth direction/rotation; no L02 response or posture term |
| G07 | same file `:1147 _trajectory`, `:355 _event_likelihood` | Existing appearance, persistent budget, event support; no truss_observable selection |
| G08 | same file `:1531 update_forecast`, `:1510 _conditioning_diagnostics`, `:1476 _remaining` | Once-only geometry then event conditioning; finite bank; unmodeled cross-organ measurement correlation |
| K01 | `tools/growth_calibration.py:471 _prediction`, `:477 _event_log_probability`, `:491 _loss` | Existing three calibration families unchanged; no beta fitter |
| K02 | same file `:81 _check_binding_meaning`, `:811 apply_parameter_set`; P3 `:115 validate_calibration_clock` | Clock first, semantic equality, stop-budget incompatibility, L02 provenance refusal |
| L01/L02 | P2 ownership unchanged | P3 consumes declared reference DLI only and rejects L02 direction bindings; no light integration or moment implementation changed |

### Deferred scientific decisions and limitations

Question 2 (P4 respiration/light-basis/face policy), reanchor_weight, transient
posture, truss_observable, cross-organ covariance model, new biological coefficients
and P1/P2/P4 adapters remain unselected or deferred. Complete local-day coverage
and coefficient identities are checked as declared provenance; this is not an
independent verification of measurements or coefficient applicability. Narrowing
evidence deliberately uses only target < minimum, not every decreasing station.
Future envelopes remain optical-ineligible. Real repeated observations and
reviewed calibration evidence are still missing; no real one-month accuracy or
biological validation is claimed. No additional implementation approval is needed
for the completed bounded scope.

### Final code and evidence hashes

| File | SHA256 |
|---|---|
| `tools/probabilistic_compound_growth.py` | `e0679d46851296f8b4fc1d675c833bde8c8acd93710b3bc31bca8dd546423a3a` |
| `tools/growth_calibration.py` | `1997db479cde7c2116e7d5cc6757b9be90dd130b872cee80de620c9f592e5075` |
| `tools/PROBABILISTIC_COMPOUND_GROWTH.md` | `b924eb4f4b8f5781fbf5b0eebb6eb281f5074ede2a2d82b3e43f094250dee805` |
| `tools/GROWTH_CALIBRATION.md` | `03f750ac9bd6291d513f9601880a816876cc99b18d2f17b7dfd10066adffac6c` |
| `tools/tests/test_p3_growth_decisions.py` | `d4fa998e8756a3c28df4c5c921a5edd11ed16a572ca5e0d30fe2fa2c3f4e9483` |
| `tools/tests/test_p3_growth_science.py` | `a5fe44ed046d765386a0b48b06444c885300c4f810eefa28826182e3fc906e16` |
| `regression_final.xml` | `a997ff5435748e972990010ff655e9016723e75575d60d31dd9d1ad58c1a6af3` |

Baseline numerical payload SHA256: `15766237398ce478e6daef4c57fdfe18c5b278792dedbf4bd273e724d776c3fb`.
