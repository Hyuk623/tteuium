# P3 semantic binding guard verification

Request: inspect `build/p3_semantic_guard_20261004_01` and its current implementation.
Date: 2026-10-04, Asia/Seoul.

Plan: verify backed-up originals and current files against the recorded hashes;
inspect the exact code/test/documentation delta and before/after JUnit reports;
rerun the six recorded suites in the project's Windows environment. Preserve the
original delivery and all production code. Save new verification artifacts in a
fresh build directory and append results here. No biological model changes,
fitting, training or interproject integration are requested.

Initial finding: Claude added a meaning check before unit checks in explicit
constant/physical-location calibration bindings. An increment cannot become an
absolute width target merely because both use mm. Undeclared meanings are refused;
no conversion is introduced. Its Linux report explicitly retains two pre-existing
environment failures, requiring local confirmation rather than claiming all pass.


## Verified result

- All six pre/post hashes match: the three backups are original files and the
  three active tools files match Claude's recorded implementation exactly.
- Production delta is limited to ROLE_MEANING, COORDINATE_MEANING and
  _check_binding_meaning plus its call in the common constant/physical_location
  path. Both sides of absolute width targets are protected. Unsupported meanings
  fail explicitly; there is no automatic conversion or new biological law.
- Precision note: the guard runs before fitted-role-to-engine unit compatibility,
  while the destination coordinate/unit validity check still runs earlier.
- Five new test cases cover both width sides, rate-to-increment mismatch,
  undeclared semantics and accepted declared meanings. Existing bindings and
  D8-D10 behavior are covered by the regression suites.
- The Linux JUnit reports genuinely show 249/254 passes and the same two failures
  before/after. One is missing pandas; one is the exact legacy numerical hash.
  The guard did not introduce either recorded failure. Cross-platform exact-hash
  portability is not established by this review.
- **Windows verification: 256 passed in 24.60 seconds, zero failures/errors.**
  Both tests that failed in the isolated Linux environment pass here.
- Original delivery, production code, tests and biological parameters were not
  edited during this review; hashes were checked again after the test run.

Command:

```powershell
python -X utf8 -m pytest tools/tests/test_growth_calibration.py tools/tests/test_p3_growth_decisions.py tools/tests/test_probabilistic_compound_growth.py tools/tests/test_compound_growth.py tools/tests/test_monthly_growth.py tools/tests/test_fsp_carbon_diagnostic.py -q --junitxml=build/p3_semantic_guard_review_20261004_01/tests_windows.xml
```

Evidence: `build/p3_semantic_guard_review_20261004_01/verification.json`,
`tests_windows.xml`, `source_verification.json`, and three saved source diffs.
The earlier generic increment-to-absolute-width guard gap is closed. Correct
binding semantics do not establish calibration applicability or real forecast
accuracy; no cross-project integration was performed.
