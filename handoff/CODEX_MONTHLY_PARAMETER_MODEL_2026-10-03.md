# User-configurable 30-day growth scenario

## Request and user clarification

The user clarified that the intended output is actual one-month growth prediction. When asked for cultivar, planting dates, temporal observations and future environment settings, the user answered that all are absent and asked for adjustable parameters to enter them later. Implement an editable 30-day calculation scenario now. Do not require historical measurements to run a user-assumed scenario, and do not label that scenario as a calibrated forecast.

## Inspected behavior

The existing compound model has persistence/recent-change baselines and an unavailable reviewed biological model. The procedural growth simulator starts at day zero with illustrative anatomy. Neither delivers a configurable monthly trajectory from an entered current state. The inspected T1/T2/T3 growth run copies all have capture_date 2026-10-02; they are different plants, not repeated dates. The current configured data root contains no crop parameters or measurement/environment records found by the present inventory. This is a scoped inventory, not a claim that no other user records exist.

## Implementation scope

Add tools/monthly_growth.py and its local form/viewer, with tests under tools/tests. Inputs are explicitly user assumptions unless later supported by evidence. Keep cultivar, start/sowing/transplant dates and environment metadata optional and null when absent. Make all numerical growth inputs explicit; ship blank production inputs, not adopted cultivar coefficients. Use a 30-calendar-day horizon requested by the user.

Provide a transparent arithmetic scenario: user-entered stem elongation and cap, per-compound initial attachment/orientation/length/width/one-sided area/unfolding fraction, user-entered dimension expansion rates and caps, bounded elevation change toward a user-entered target, and optional periodic new-compound appearance with explicitly supplied birth state. Effective development advances by a user-supplied daily multiplier. This multiplier is an assumption; it is not inferred from temperature, EC, pH or light. Environment values are editable and retained but have no unsupported automatic physiological response. The simple bounded linear rules are a calculation scenario chosen to expose the user's inputs, not a proposed biological law or fitted parameter set.

Existing attachments stay fixed while apical stem height extends; new attachments use stem height at event time. Document this assumption. Event times within a day are resolved before expansion; initial compounds have user-provided state rather than an invented age. No fixed leaflet count, surface mesh, carbon balance, flowering, senescence or yield claim. Schematic axes/extent bars are display-only, not ChArUco measurements or optical receivers. Parameter changes recalculate the complete scenario; results must become visibly stale after input edits.

Implement one Python engine for CLI and local browser API. Export JSON assumptions/provenance, daily/compound CSVs and a saved viewer into a new build directory. Hash input and code. Bind the server to localhost, limit API input size, and do not overwrite existing runs. Do not modify existing pipeline/demo/compound implementations, human data/config/docs, or shared frozen GroIMP helpers.

## Validation plan

Test day-zero preservation, 31 daily states, partial-day emergence and development, no emergence with a stopped developmental clock, bounded growth, downward orientation, invalid/missing/nonfinite inputs, chronology, optional unknown metadata, no mutation, and consistent export. Test browser parameter editing, calculation, day navigation, stale-result state and saving. Use synthetic coefficients only in tests, never as suggested crop values. Leave calibrated growth and uncertainty false/unavailable.

## Delivery

Pending implementation and verification. Actual calibrated monthly prediction remains a separate scientific/data requirement.


## Implemented extension and verified delivery

Delivered tools/monthly_growth.py, tools/monthly_growth.html, tools/MONTHLY_GROWTH.md and tools/tests/test_monthly_growth.py. The arithmetic scenario additionally supports user-supplied piecewise-linear response tables for temperature, RH, PPFD, photoperiod, EC, pH and CO2. Manual mode records environment only; table mode multiplies explicitly enabled factors with the daily clock. Missing required environment, duplicate/unsorted knots and out-of-domain values fail rather than silently extrapolate. This supersedes the opening brief's narrower environment-record-only plan. All response knots remain blank unless entered by the user; no crop coefficients were adopted.

Validation command: python -X utf8 -m pytest tools/tests/test_monthly_growth.py tools/tests/test_compound_growth.py tools/tests/test_compound_surface.py tools/tests/test_growth_simulator.py -q. Result: 84 passed in 8.17 seconds, including 30 monthly-model tests. CLI help/template/run succeeded. Browser checks covered blank-input rejection, JSON/form editing, 30-day calculation, day-zero navigation, stopped development, stale output/save blocking, unapplied common-environment blocking, entered temperature-response interpolation and save. No browser console errors.

Final blank setup: build/monthly_growth_setup_20261003_02/. Live local editor: http://127.0.0.1:8855/ ; hidden server PID recorded in that directory (17616 at delivery). Browser left with blank numerical inputs; no synthetic fixture is presented as the user's plant. Screenshot: editor_verified.jpg. Earlier setup _01 and browser test run 161543 are retained historical outputs preceding response-table support.

Final synthetic browser export: build/monthly_growth_20261003_162046_fb5e68f8/. CLI replay: build/monthly_growth_cli_check_20261003_01/. Exact result JSON equality and both input/output/code manifests verified. These coefficients are software fixtures only. Example test response at 20 C between user-entered knots (10,0) and (30,1) gives multiplier 0.5; this is an interpolation test, not a tomato temperature response claim.

No real observations, human configuration, docs, previous model code or GroIMP modules were modified. No training, real reconstruction or light execution. User-requested configurable monthly calculation is implemented; an accurate real monthly forecast still requires justified parameters and independent measurement-based evaluation.
