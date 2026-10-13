# Growth response calibration execution

Started 2026-10-03. Authorized by the user's invocation of
`CODEX_GROWTH_RESPONSE_CALIBRATION_HANDOFF_2026-10-03.md`.

## Inspected state and ownership

The separate active chat `생장방향` is implementing the base calculator in
`tools/probabilistic_compound_growth.py` from the base handoff. Do not edit its
files concurrently. This session owns the additive `tools/growth_calibration.py`,
`tools/tests/test_growth_calibration.py`, `tools/GROWTH_CALIBRATION.md`, and this
brief. Read/import the base engine after its interface becomes available; verify
integration rather than write a duplicate engine. No cross-chat messages sent.

## Requirement map and implementation contract

1. Evidence registry: exact source/version/locator, cultivar and conditions,
   evidence kind, units/angle reference, uncertainty meaning, experimental unit,
   applicability/review. Literature candidates never become target-cultivar truth.
2. Read-only calibration audit: hashed observation CSV and treatment JSON;
   timestamps, confirmed IDs/frame, comparable support, birth/visibility intervals,
   actual historical exposure, assignment units, split leakage, replication,
   confounding/collinearity and per-target missingness. Known missing real data
   are reported, not searched for again.
3. Frozen explicit fit plan: only specified anchored expansion, local azimuth
   rotation and interval/right-censored lognormal event waits. These implement
   the proposed contract; they are not fitted literature physiology. No automatic
   family selection. Real fits require reviewed scientific plans; synthetic
   assumption plans exercise the implementation only.
4. Parameters: fitted/fixed with units, transform, finite bounds/source, explicit
   feature scaling/domain and linked response coefficients. Continuous targets use
   declared Gaussian observation covariance; angular targets use a declared
   circular likelihood; event targets preserve censoring. Dependence/uncertainty
   uses whole assignment-unit resampling shared across targets. Reject failed,
   boundary-constrained or locally unidentifiable optima as calibrated output.
5. Separate validation on held-out plants and assignment units, chronological
   targets, supported horizons, errors, predictive intervals/proper scores and
   persistence/recent-change comparisons. No automatic domain acceptance.
6. Explicit adapter from parameter particles to base model families, preserving
   units, provenance and joint uncertainty. Forecast never fits or runs light.
7. Standalone audit/fit/validate/forecast/templates/demo CLI, English documentation,
   blank templates, bounded synthetic demonstration, focused negative/regression
   tests and requirement-by-requirement completion audit.

## Additional schemas (version growth-calibration-1)

Observation manifest: `schema_version`, `data_kind`, `observations` containing
`path,sha256`, and optional original `source_hashes`. Observation CSV rows:
`record_id,plant_id,organ_id,target_id,unit_id,observed_at,origin_at,elapsed_days,
value,initial_value,unit,frame_id,identity_status,coverage_basis,age_basis,
measurement_sd,lower_day,upper_day,censoring,visibility_status,split`, plus
declared response-feature columns. Empty cells mean unavailable. Event endpoint
rows use `censoring=interval|right`; right censoring needs confirmed visibility.
Rows retain explicit capture timing relative to light via `capture_phase`.

Treatment manifest: assignment-unit records with `unit_id,treatment_id,run_id,
source_ref`; all plants map to a true assignment unit. The fit plan freezes
train/validation plant and unit lists, eligible target IDs, parameter definitions,
target-to-parameter maps, feature definitions, observation-error structure,
cluster resampling settings, optimization tolerances and review metadata.

Units: mm for lengths, cm2 for supported area, rad for angular observations,
calendar_day for event times (development clocks require explicit conversion
before fitting), inverse calendar days for rates. The adapter allows calendar
clock only unless an explicit compatible development mapping is supplied.
Biological values are null in templates. All generated data go to fresh build/.

Outputs: evidence_registry.json, data_audit.json, fit_plan.json,
parameter_set.json, fit_diagnostics.csv, validation.csv, requirements.csv and
manifest.json with source/code/artifact hashes and computation provenance.
Parameter evidence and independent-validation status are separate fields.

## Restrictions and validation

No core/config/docs/source edits, no new UI, optics, photosynthesis/carbon
allocation, roots/yield, remote jobs, neural training, FM, deployment or outreach.
Test missing/unit/angle mismatch, endpoint-only rates, pseudoreplication,
collinearity, censoring, angular wrap, leaks, optimization failure, joint uncertainty,
immutable export and refusal of automatic scientific promotion. Synthetic recovery
does not validate real 30-day growth. Scientific gaps remain available per component.

## Outcome

Completed the scoped software foundation on 2026-10-03. Added
tools/growth_calibration.py, tools/tests/test_growth_calibration.py,
tools/GROWTH_CALIBRATION.md and tools/growth_calibration_evidence.json.

Final combined regression command:
`python -X utf8 -m pytest tools/tests/test_growth_calibration.py tools/tests/test_probabilistic_compound_growth.py tools/tests/test_compound_growth.py -q --junitxml=build/growth_calibration_20261003_02/final_tests.xml`.
Result: **93 passed**. The existing engine is reused, not rewritten in this task.

Verified operating cases:

- Blank templates: build/growth_calibration_blank_20261003_02; explicit audit:
  build/growth_calibration_missing_audit_20261003_02. Missing coefficients,
  observations and review produce unavailable output, not invented parameters.
- Integrated synthetic demo: build/growth_calibration_20261003_02. Eight training
  assignment units, four independent validation units, 60 synthetic observations.
- Explicit fit: build/growth_calibration_explicit_fit_20261003_01. Recovered
  D=24.0627626396 mm, k=0.1202885048 per calendar day, light_beta=0.2461351595
  against synthetic truths 24, 0.12, 0.25. These are not plant coefficients.
- Explicit validation: build/growth_calibration_validation_20261003_01.
- Explicit base-engine forecast: build/growth_calibration_forecast_20261003_01.
  No fit/light execution is triggered by the forecast operation.
- Source/code/artifact hashes for all four explicit operations were verified in
  build/fsp_physiology_spec_20261003_01/verification.json. Earlier audit attempt
  *_01 failed on null uncertainty export; the bug and regression were corrected,
  and successful *_02 is the delivered blank audit. Do not reuse failed output.

Known T1 audit is partial-only with unconfirmed temporal identity, whole rachis,
attachment, extent, tissue area, stable frame and capture time. It is recorded
with source hash in build/fsp_physiology_spec_20261003_01/known_real_input_audit.json.
No repeated-data search, real fit, real predictive validation or automatic
acceptance took place. All parameter sets retain accepted_for_domain=false.

Literature recovery now includes the complete dwarf-FSP paper and pinned official
code/input; mature spectral-treatment angles remain endpoint evidence, not fitted
rotation dynamics. The subsequent user-selected physiology task delivers a
separate proposed scientific contract and evidence pack, not a modification to
these fitting families. See CODEX_FSP_PHYSIOLOGY_EXECUTION_2026-10-03.md.

Requirement audit for both stages:
build/fsp_physiology_spec_20261003_01/requirement_audit.csv.
