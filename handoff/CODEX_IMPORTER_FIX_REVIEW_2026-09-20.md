# Claude importer fixes: independent review

Request: review Claude Code's latest changes. Review only; no application edits, model inference, training, calibration changes or session regeneration.

Latest handoff claims fixes for R1 camera compatibility, R3 sourced board captions, and R4 inactive null thresholds. R2 remains operationally handled by the user. Inspect current implementation and tests, run focused regressions, and inspect saved real-data artifacts and input preservation. Append findings after verification.

## Independent outcomes

Focused validation: `python -m pytest tools/tests/test_import_organized_capture.py -q`: **9 passed in 4.40 s**. Claude's 175-test suite is historical, not independently repeated here.

R3 sourced-caption behavior and R4 inactive-null importer handling pass the focused regressions. R1 now honestly reports unavailable calibration profile information, but is not fully closed:

### F1 / P1: explicit expectation overwrites contradictory calibration evidence

`tools/import_organized_capture.py:129-137` merges `{**declared, **contract}` before checking mismatches. A calibration declaring camera A plus photographs from camera B and an explicit expectation of B is accepted as `verified_against_declared_profile`. Reproduced directly with in-memory inputs. Compare observations independently against both sources and reject contradictory contracts; do not label overridden evidence verified. Add a conflict regression. Current delivered trial intrinsics declare no camera profile, so this is a conditional defect, not evidence that these photographs used different lenses.

### F2 / P2: numeric focal lengths compared as exact strings

`tools/import_organized_capture.py:131` rejects the current photographs' EXIF focal length `5.960000038146973` against CLI `--expect-focal-length-mm 5.96`. Reproduced using the delivered capture profile. Parse numeric fields and compare with a documented representation tolerance, while retaining strict textual camera/lens checks. Add a float-roundoff regression and a materially-different-focal refusal regression. Current delivered imports omitted the focal expectation, so they are not blocked by this defect.

## Saved real-data verification

- Both 18-photo sets: all 36 original source hashes, all 36 decoded PNG hashes, and all 36 prepared-editor image hashes match their captures.
- Prepared camera pose vectors match parent captures; all 14 solved poses' board-evidence residuals match reported solve errors within 0.01 px.
- dwt_01: 6/18 solved; dwt_02: 8/18 solved; zero pass the unchanged 1 px gate; all 16 side views remain unposed. Both captures remain `validated_metric=false`.
- Both captures now record `verified_against_explicit_contract`, with no calibration-declared EXIF profile, and session-specific caption sources attributed to Claude. No new independent visual caption reading was performed in this review.
- Growth JSON hashes remain the corrected known values: dwt_01 counts 8/9/9; dwt_02 7/7/5. No records were modified.
- Date isolation remains the user's operational responsibility. Do not reopen R2 as required implementation.

Evidence: `build/importer_fix_review_20260920/review.py`, `review.json`, `focal_precision.json`. Reproduce primary audit with `python build/importer_fix_review_20260920/review.py` from project root. Source hashes are recorded in review.json.

Review only: no application edits, session regeneration, server changes, inference, training or PPFD simulation. Remaining fixes are handed to Claude; current geometry is still diagnostic.

## User decision: F2 implementation

Compare focal lengths in millimetres after truncating to two decimal places (discard the third and later decimal digits; do not round). Apply the same comparison to within-session focal consistency and calibration/explicit expectations. Preserve raw EXIF and calibration values; do not alter camera matrices or saved captures. Camera/lens text and zoom behavior remain unchanged. F1 conflict precedence remains a separate open review item. Validate decimal boundaries, real EXIF noise, missing/invalid focal values and original metadata preservation; no inference or re-import.

F2 outcome: implemented decimal truncation to 0.01 mm for focal comparisons both within the photo set and against calibration/explicit expectations. Raw numeric values are retained. Missing values remain missing; malformed/nonpositive/nonfinite focal values are rejected. Focused importer suite: 20 passed in 1.83 s, including decimal boundaries and preservation. No capture regeneration, inference or calibration changes. F1 remains open.
