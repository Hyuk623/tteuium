# P3 Growth Pack V2 execution

Date: 2026-10-04. Brief written before implementation. Scope: invoked P3 V2
prompt plus D19/D21 and technical P3-a through P3-f. Supersedes older optional
feature deferrals only within this authorized scope. No P4/registry/common module
edits, real fitting, new biological coefficients, human-record edits or integration.

Inspected existing validation, likelihood, reanchoring, event generation and
summaries. Prior F2/F3/F7/F8/F9/F11 implementation exists. Remaining work is opt-in
weighted anchors and observation-only posture, explicit truss meaning, scientific
unavailability classification, split support masses, hard-admissibility reporting,
canonical DLI validation and read-only Day-1 ingestion. Freeze current valid
baseline before changes; preserve default equations and weights. Legacy truss
meaning and underspecified/legacy-unit DLI intentionally change availability.

Evidence: build/growth_pack_fixes_20261004_01/P3 and
build/technical_review_fixes_20261004_01/P3. P2's shared DLI_UNIT was absent at
initial inspection; work on independent P3 changes first and recheck the dependency.

Verification plan: focused synthetic options/failure/CLI tests, original calibration
and growth suites including the named Windows regressions, consecutive updates,
input immutability and output hashes. Document exact APIs, limitations, equation
locators and all actual outcomes below. No new covariance law, multivariate Kalman
update, posture geometry law, anthesis model or full-system adapter is introduced.


## Completed V2 delivery

All authorized P3 V2 and technical-review deltas are implemented and verified.
This is software completion, not target-cultivar validation or a four-project run.
The initial DLI_UNIT dependency was resolved by P2's published common-module
change; P3 imports it and did not edit the common module.

### Requirement audit

| Item | Status | Authoritative evidence |
|---|---|---|
| D14a manual weights | Implemented | Actual update tests at 0, 0.25 and 1; default 1 equals the prior measured-anchor output; geometry-length consistency; beta remaining endpoint displacement |
| D14a covariance mode | Implemented, opt-in only | Declared marginal variances and squared units; 3/(3+1)=0.75; missing/invalid source, zero denominator, negative variance, incompatible unit, non-identifiability and cross-covariance return reasons, no fallback certainty |
| D14a cumulative correction | Implemented | Two actual consecutive updates yield 2+3=5 mm correction per trajectory/organ/trait; previous ledger retained; same-input replay deterministic; duplicate timestamp refused; units/components separate |
| D14b posture | Implemented, likelihood only | Disabled and exactly-zero offsets preserve weights; phase offset changes likelihood/weights; wrapped offsets agree; matched trajectory block states unchanged by the posture term; missing evidence/time/phase and nonzero reference offset disable reweighting with reasons |
| D14c truss observable | Implemented, intentional availability change | Missing rule meaning preserves leaf/terminal events, blocks and weights; truss only unavailable. Explicit visible_bud exported; first_open_flower mismatch cannot condition a visible_bud rule |
| D19 canonical DLI | Implemented | P2-owned DLI_UNIT imported; canonical fixture passes; legacy unit CLI returns legacy_dli_unit_spelling with 41 missing/different-field diagnostics; no conversion |
| P3-a support masses | Implemented | Original-weight existence/computability/intersection sums; not-yet-present vs low-DLI failure; terminated plant scope versus retained existing leaves; failed draw has unknown existence, not biological absence |
| P3-b hard admissibility | Implemented | Stage label, raw rejected count and prior-weight rejected mass; geometry likelihood times Boolean indicator once; fixed multiplication order invariant; ESS stages order-dependent; all-zero support remains incompatible |
| P3-c meanings | Already satisfied; regression retained/extended | Existing taxonomy unchanged; remaining increment cannot bind extent target or beta potential maximum; DLI role mismatch rejected; original five guard cases pass |
| P3-d lower temperature knot | Already satisfied; full-path test added | Helper-generated lower zero knot passes validate_model_config/_validate_d9 and pauses development; changed normalization rejected; no extrapolation or relaxed calibration clock rule |
| P3-e legacy science failure | Implemented | Complete missing/different-field collection, public structured unavailable result, real CLI/JSON output; malformed arrays, hashes and conflicting duplicate intervals remain errors |
| P3-f reverse basis check | Implemented | Hashed P2 tissue manifest checked independently; falsely labelled valid collision refused; distinct reference passes; provenance from selected coefficient domain checked |
| D21 Day-1 loader | Implemented | P1's exact header-only template consumed read-only; explicit rows retain hash/row/time/phase/zero/blank; missing timestamps/source/meaning and incompatible truss meaning tested; matching sourced node count reaches N_max lower truncation |
| Prior F2/F3/F7/F8/F9/F11, D11/D13 | Retained with prescribed refinements | Full regression suites and pre-V2 baseline comparison; original curve availability, width meaning, beta restrictions, semantic/clock/stop guards and fixed DLI remain |

### Changed APIs, files and fields

Runtime changes:

- `tools/probabilistic_compound_growth.py`: integrates optional observation helpers,
  imports canonical DLI_UNIT, audits scientific missing fields, validates independent
  P2 basis/domain references, imports Day-1 records, requires explicit truss semantics,
  adds summary support and hard-admissibility diagnostics, extends templates/exports.
- `tools/growth_observation_options.py`: manual/declared-variance weighted anchors,
  unit-separated correction ledger, phase-offset validation and wrapped residuals.
- `tools/growth_day1.py`: read-only loader/back-fill and CLI. No P1 template edits.
- `tools/growth_calibration.py`: structured scientific-unavailable outcome before
  applying frozen bindings, including CLI export. Existing meaning taxonomy, fit
  equations, clock-first order, stop-budget and L02 guards are retained.
- Two guides and three P3 test files updated/added. No P4 runtime/registry, common
  module, human record, configuration, photograph or source-specification edits.

Association JSON accepts `reanchor_weight` (dimensionless [0,1], default 1), or
exclusive `reanchor_covariance={mode:"diagonal_variance",cross_covariance:null,
traits:{...}}`. Trait records have variance_state, variance_measurement, unit
(`mm^2`, `cm2^2`, `rad^2`), identifiable, source_kind and source_ref. Vector/profile
records declare a common marginal variance per component; no covariance is
estimated and no multivariate Kalman update is introduced. Unsupported intermediate
rotation/profile correspondence is explicitly reported. Supported scalar geometry
uses the existing axis dilation/attachment translation. Weight 1 retains the exact
measured geometry path; weighted anchors are labelled separately from measurements.

`observation_model.posture_offset` is optional, null/disabled by default. Enabled
records declare reference_phase, source_kind/ref, observed_at,
time_reference=declared_capture_phase and phase-keyed offsets. Each offset has
rad units, source_ref and values on the existing observed-direction tangent
likelihood coordinates. Reference offsets are zero. The residual is
wrap(state minus observation plus offset); structural geometry receives no offset.
Association capture_phase or a matching explicitly recorded Day-1 phase is used.

`reanchor_corrections` and `reanchor_cumulative` are exported in update.json; the
bank carries the ledger through continuation. Each row identifies trajectory,
organ, trait, component/station, unit and update IDs. Accumulation is sum of
absolute applied displacement within that identity only. No cross-unit total.
Missing variance is a reason, not an invented 0/1 weight.

Truss rules/evidence and event/summary outputs carry `truss_observable`. New D21
records use visible_bud explicitly; no legacy label is inferred. Unknown truss
meaning/evidence does not remove trajectory existence or leaf/terminal predictions.
Mixed observable summaries are unavailable. The event stage is named
`hard_admissibility`; its unique valid positive-prior-weight rejected count is
separate from `event_rejected_prior_mass`. Stage ESS loss is signed and ordered,
not a causal decomposition. Cross-organ measurement correlation remains unmodeled.

Every summary adds existence_mass, computable_mass, available_mass (intersection),
ensemble_weight, not_present_mass, existence_unknown_mass,
computational_unavailable_mass, support_denominator and computational_reasons.
Masses sum original normalized bank weights. Failed draws have unknown existence;
biological nonappearance does not imply failed parameters. Conditional quantiles
use available_mass. Occurrence probability includes present and absent trials;
legacy available_weight is retained as its original statistic-specific support.
Terminated whole-plant continuation is unavailable, but existing leaves remain.

DLI's canonical interval remains light_response.applicability_interval. The V2
name dli_applicability_interval is an explicit top-level or nested alias copied
into the canonical field; conflicting duplicates raise. No bounds are inferred.
Time basis is complete_local_day, unit comes from the shared DLI_UNIT. A domain's
applicability_source_ref must match each selected curve coefficient's domain
reference. Structured references require a verified path/hash/JSON pointer to a
matching min/max/unit object; arbitrary sensor metadata cannot fill that role.
Legacy scientific omissions yield named reasons and the complete field list.

Optional observation-manifest day1_protocol={path,sha256} is consumed read-only.
P1's exact eleven columns are preserved, including row identity, declared aware
captured_at and capture_phase. early_photoperiod means 2 h after actual lights-on;
late_photoperiod means 2 h before actual lights-off; no retrospective phase inference.
Explicit origin day1_axis_id maps the same capture's sourced node count to an
existing axis and unchanged N_max truncation. A visible-bud count is retained as
count evidence, not converted into invented node ranks or emergence timestamps.
Sowing/transplant dates never assign existing organ ages. No environment variable
is added; CLI paths remain explicit.

### Failure classification

Scientific missing evidence: structured unavailable with reason and field/trait
context. Examples: legacy_light_response_underspecified, legacy_dli_unit_spelling,
dli_complete_local_day_unavailable, dli_outside_applicability_interval,
dli_applicability_coefficient_domain_mismatch, dli_applicability_source_domain_mismatch,
basis_collides_with_tissue_basis, truss_observable_undeclared,
truss_evidence_observable_undeclared, truss_observable_mismatch,
reanchor_variance_evidence_missing, reanchor_zero_variance_denominator,
reanchor_cross_covariance_unsupported, posture_reference_offset_nonzero and
Day-1 per-field missing reasons. F3's two curve reasons are unchanged.

Malformed numeric values, invalid manual weight, wrong array shape, hash failure,
conflicting interval aliases, incompatible binding semantics and invalid clock
normalization remain explicit input errors. Public configuration validation catches
ScienceUnavailable; low-level _validate_d9 retains a typed refusal with structured
details. Calibration returns calibration_applied=false and exports unavailable.json
when scientific DLI declarations are missing. No broad programming-error swallowing.

### Verification and compatibility

Evidence roots:

- `build/growth_pack_fixes_20261004_01/P3`: frozen before sources/hashes, baseline
  inputs/bank/values and comparison, final JUnit copies, `demo_verified` weighted
  CLI update plus consecutive update and blank option templates.
- `build/technical_review_fixes_20261004_01/P3`: final JUnit, requirement function
  map, completion audit, delivery verification, `demo_verified` valid/low-DLI/
  legacy-unavailable CLI forecasts, Day-1 import and P1 template read-only audit.

**209 full regression cases passed in 78.24 seconds.** A final evidence-kind
validation refinement was then verified with all **36 V2 option/boundary cases**
in 29.36 seconds. These reports cover **210 unique passing cases** (35 overlap),
with zero failures/errors/skips in the final selected reports. Both named Windows
regressions pass: test_legacy_golden_numerical_payload and
test_prepare_light_delegates_existing_bridge. All five original semantic cases
remain. JUnit copies exist in both required P3 roots.

Five actual CLI commands passed: valid DLI forecast, low-DLI forecast,
legacy-unavailable forecast, weighted observation update and Day-1 import.
Forty-seven manifest-referenced output files and all recorded artifact hashes
were verified. The real P1 header-only template was read and hash-checked unchanged.
The synthetic P2 producer returned 11.52 mol/m2/day; its actual reference_dli.json
was explicitly mapped into _validate_d9 with identical domain provenance and
validated, including out-of-domain refusal. That boundary test performs no P3
forecast, light-to-growth integration or full-system run.

Pre-V2 decoded states, all pre-existing summary fields, weights and events match
exactly. AST comparison also proves no changes to _remaining, beta_shape,
_beta_value, normalized_temperature_clock, _draw, _size_response or the accepted
validate_calibration_clock policy. Opt-in behavior and required truss availability
are intentional changes. Additive fields change output bytes/hashes, as authorized.
The historical numerical golden is checked with only additive report fields removed.
No calibration refit or biological coefficient was introduced.

Intermediate evidence is retained: old missing-science assertions were updated to
the requested unavailable result; a delivery assertion now uses 1e-12 tolerance
for 4.999999999999999 mm versus 5 mm; one test was corrected to mutate the copied
canonical interval rather than a detached pre-validation dictionary. These were
contract/test-harness corrections, not hidden scientific parameter changes. Use
only the final selected reports and demo_verified directories for acceptance.

Commands from project root:

```powershell
python -X utf8 -m pytest tools/tests/test_p3_growth_pack_v2.py tools/tests/test_growth_calibration.py tools/tests/test_p3_growth_decisions.py tools/tests/test_p3_growth_science.py tools/tests/test_probabilistic_compound_growth.py tools/tests/test_compound_growth.py -q --junitxml=build/technical_review_fixes_20261004_01/P3/regression_final_02.xml
python -X utf8 -m pytest tools/tests/test_p3_growth_pack_v2.py -q --junitxml=build/technical_review_fixes_20261004_01/P3/options_verified.xml
$env:PYTHONPATH='.'
python -X utf8 build/technical_review_fixes_20261004_01/P3/verify_delivery.py
python -X utf8 -m tools.growth_day1 --records <record.csv> --out build/day1_import_new
```

The delivery script uses fresh destinations; choose new directory names for a
rerun instead of overwriting recorded evidence. Exact command arguments/source and
artifact hashes are in delivery_verification.json. Runtime schemas/templates are
updated in place; no second schema source or UI was added.

### Equation map for P4 registry owner

The live locators below are recorded in requirement_function_map.json. P4 owns
registry updates; this chat did not edit it or the shared roll-up reports.

| Scope | Current implementation |
|---|---|
| D14a | `tools/growth_observation_options.py:42 weighted_anchor`; `tools/growth_observation_options.py:94 accumulate_corrections`; `tools/probabilistic_compound_growth.py:1664 _remaining` |
| D14b | `tools/growth_observation_options.py:112 posture_offsets`; `tools/growth_observation_options.py:145 adjust_posture_residual` |
| D14c | `tools/probabilistic_compound_growth.py:466 _truss_rule_reason`; `tools/probabilistic_compound_growth.py:457 _truss_evidence_reason`; `tools/probabilistic_compound_growth.py:422 _event_likelihood` |
| D19/P3-e | `tools/probabilistic_compound_growth.py:183 _light_contract_issues`; `tools/probabilistic_compound_growth.py:296 _validate_d9` |
| P3-a | `tools/probabilistic_compound_growth.py:1576 _summary_support` |
| P3-b | `tools/probabilistic_compound_growth.py:1698 _conditioning_diagnostics`; `tools/probabilistic_compound_growth.py:1720 update_forecast` |
| P3-c | `tools/growth_calibration.py:81 _check_binding_meaning` |
| P3-d | `tools/probabilistic_compound_growth.py:94 normalized_temperature_clock` |
| P3-f | `tools/probabilistic_compound_growth.py:221 _validate_reference_dli` |
| D21 | `tools/growth_day1.py:19 load_day1_protocol`; `tools/growth_day1.py:57 backfill_origin` |

G01 clock, G02 exponential, G03 beta and G05 stochastic equations remain as in the
previous Science report. G03/G08 add weighted observed displacement while keeping
the same remaining increment. G06 posture is observation-only. G07 adds declared
truss observable and read-only Day-1 count provenance. G08 reports hard event
admissibility, ordered ESS and cumulative unit-separated correction. G04/D19
refines units, domain and input failure semantics without changing f_DLI. K01 fit
equations and K02 taxonomy remain unchanged; K02 now returns structured missing-DLI
science outcomes before binding. No L02 growth-direction response is implemented.

### Remaining scientific limits / coordination

No P3 software requirement is deferred. Applicable real coefficient/domain
provenance, repeated same-organ observations and covariance/phase-offset evidence
remain scientific inputs, not inferred by these fixtures. Intermediate direction
interpolation and multivariate cross-covariance stay explicitly unsupported under
the authorized no-new-shape/no-Kalman constraints. D21 recording need not wait for
software; this work imported no real human observations.

P4 owns its D15-D18/D20 policy, registry and physiology; P2 owns reference-light
production; P1 owns acquisition/area evidence and the Day-1 template. Full-system
integration, new fitting, new coefficients, senescence, sympodial continuation,
anthesis timing and reproductive biomass are outside this task. Coordination may
consume this report for its two requested final roll-ups; neither was edited here.

### Verified source hashes

| File | SHA256 |
|---|---|
| `tools/probabilistic_compound_growth.py` | `1905dcade519bbf4d5c661178ce22420d4da00f6ccd887120c92afc275dd65ae` |
| `tools/growth_calibration.py` | `f28a2e5ca93fce3caf1cde67b5b489e24db63f56a4c5553dfbc9ad7c1998df3b` |
| `tools/growth_observation_options.py` | `cf28b51e94b1f1c5d8a4c33479383c981f8ecf0763d396a2701ff52171c5463a` |
| `tools/growth_day1.py` | `5b2270a7d753fedefaf3f41a14852b35aab59751638755d1db9a366be83dcc25` |
| `tools/PROBABILISTIC_COMPOUND_GROWTH.md` | `adc72f84215b95b3fd4dca442905e7be61c099d205ca37acbfb97c1b28d0881d` |
| `tools/GROWTH_CALIBRATION.md` | `963c709f3b557f01bcb814a92b89bd1436f24c6aa7da6f2b02bdd5082c1a8706` |
| `tools/tests/test_p3_growth_decisions.py` | `a208c15a7e601cfcf25e2c0c1e89b6a1d6c903f73ae3d9be233e2cd81635a2ed` |
| `tools/tests/test_p3_growth_science.py` | `42243256cf387188bd75ce35466d54c316262e942b4f9817639ee57dc25ec2ae` |
| `tools/tests/test_p3_growth_pack_v2.py` | `1b29067249a5e78ae5bbcccf32e7acfa81ff5a643a1458e3964f5e76a9b6b1e8` |

Completion audit SHA256: `bc6e3703e469fe587f94091a302df5a12ebc2ad256be3309392c07a4c7d9a372`.
