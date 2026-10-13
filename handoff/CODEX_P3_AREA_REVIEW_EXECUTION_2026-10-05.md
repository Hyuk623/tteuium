# P3 area review alignment execution

## Implementation brief

Request: execute the bounded P3 area-review prompt. Inspect existing V2 observation,
reanchoring and calibration boundaries; add missing evidence checks only.

Inspected gaps: the observation loader retains area basis but drops method and
quantity provenance; exact reanchoring can apply an incompatible area despite an
audit warning. Calibration checks units/coverage and repeated times but not area
method continuity. Variance sources do not distinguish empirical covariance from
mask confidence or synthetic MAE. Existing identity/session and frozen split checks
will be retained and extended for explicit lineage and source-row reuse.

Plan: add versioned optional observation metadata, retaining raw evidence and
source hashes; gate real area and explicitly unsupported direction per trait;
check comparability before updates/increments/fitting; preserve valid synthetic
numerics and legacy measured-axis geometry. Unsupported comparisons remain
unavailable; no conversion, new growth equation or area estimator is authorized.

Validation: freeze a synthetic baseline and source copies, test the changed import,
update and calibration boundaries plus CLI/export, then relevant V2 regressions.
Evidence root: build/area_review_alignment_20261005_01/P3/.

Restrictions: no edits to P1/P2/P4 runtime, docs, config or human data; no real
fitting, training, new acquisition or physical-accuracy claim. area-A1/A2 priority,
leaflet matching and calibration strategy remain Claude/user decisions. The
source companion simulation bundle remains unavailable as recorded in the prior
review; its claimed accuracy is not reproduced or adopted.

## Final outcome

Implemented the missing P3 evidence boundaries. No area estimator, coefficient,
shape law, flow model or biological face mapping was adopted. Eight owned source,
contract and test files changed; their hashes and function locations are in
`completion_audit.json` and `function_map.json` under the evidence root.

| Prompt item | Status | Current implementation and evidence |
| --- | --- | --- |
| 1: V2 inspection/preservation | Implemented / already present | `compound_growth.load_history`, `probabilistic_compound_growth.update_forecast`, calibration audit/fit/validate and observation options inspected. Existing Day-1, DLI, D14 and D19/D21 retained; acceptance suite and AST checks pass. |
| 2: area/orientation contract | Implemented | New `growth_observation_evidence.load_evidence`, `attach_evidence`, `audit_state`; integrated loader plus prepared-origin API. Source hashes, source CSV line and declared method/quantity/support are preserved. Real legacy diagnostic area without evidence becomes unavailable while measured axis geometry remains. |
| 3: continuity | Implemented; mapping design pending | `comparison_reason` gates kinematic rates, reanchor, likelihood, calibration audit and independent validation (including recent-change baseline). Changed method/version/calibration/pose/partition/support/phase/placement is unavailable; no history rescaling. |
| 4: identity/canopy | Implemented; merge/split/placement mapping unavailable | Exact plant/organ/session or calibration-row joins; source-row reuse refused. Within-ring-only associations cannot update the bank; explicit rename lineage required. Duplicate predicted aliases refused. Other-plant-only batches leave the origin unchanged. |
| 5: orientation | Implemented | Directed whole-rachis vector/angle remains distinct from normal axis, botanical face, leaflet scope and top/ring ratio. Unsupported direction is null with retained raw evidence. Length/area observations and supported likelihood coordinates remain usable; no new shape or light-response equation. |
| 6: covariance/repeats | Implemented / already present | `variance_reason` and `_weight` reject diagnostic substitutions and require repeat evidence for real measured/fitted covariance. Existing assumed/literature policy, zero-denominator and missing-variance behavior remain. Repeatability/single-capture tags cannot enter dynamic fitting; existing temporal identifiability gates remain. |
| 7: light/science | Already present; scientific evidence unavailable | Incident complete-local-day DLI, coefficient-domain checks, tissue separation and no-L02 response remain unchanged. No real dataset, coefficient fitting or integration claim. |

## Exact interface and behavior

The full versioned contract, fields/units and reasons are in
`tools/GROWTH_OBSERVATION_EVIDENCE.md`. No new environment variable or CLI is added.
Original CSV columns and outer schemas remain accepted. Metadata is JSON in
`observation_evidence`, schema `p3-observation-evidence-1`, with source refs and
exact row joins. Area is cm2 of one-sided physical tissue at compound-leaf scope;
orientation is an existing directed whole-rachis unit vector, or the declared
calibration angle in rad with its angle reference. No area-to-length/width mapping
exists or was invented. Historical P1 diagnostic area does not satisfy this gate.

Raw unsupported values and geometry are retained under `raw_observation_traits`;
per-trait nulls/reasons do not change unrelated measurements. Blocked reanchors
retain eligible prior predictions and prior trait provenance, explicitly labelled
`weighted_observation_anchor` / `retained_prediction_traits`; they are not new
measurements and their correction is unavailable rather than zero. A first
observation of a previously generated block can anchor it without pretending a
previous generated state was measured. Real zero remains zero.

`trait_diagnostics`, `trait_unavailable`, `trait_update_unavailable`, state metadata,
trajectory/update JSON, calibration audit metadata and validation evidence JSON
preserve the reasons and evidence. Source hashes and new helper code hashes are
included in export manifests. Missing science remains unavailable; malformed
schema, conflicting phases, duplicate joins/rows and changed hashes are errors.

Explicit metadata tightens the old real-area boundary intentionally: a basis ID
and cm2 alone were diagnostic, not proof of physical tissue support. Legacy
synthetic fixtures and valid measured-axis behavior retain their numerical values.
No existing real area is silently promoted. Changed capture hashes currently need
an approved comparability contract; this implementation deliberately cannot assume
that a changed pose/partition file is either equivalent or a biological increment.

## Verification

Final full relevant regression: **256 passed in 28.17 seconds**, zero errors,
failures or skips (`acceptance.xml`). Includes the original five semantic guards,
the exact legacy numerical golden, Windows light-bridge regression, D14/posture,
D19/D21 and the new area/identity/variance API/CLI boundaries. The golden excludes
only the new additive `source_row` field; its historical expected digest is intact.
A separately frozen pre-change bank's full decoded states at days 0/7/30 and
weights match exactly (`baseline_comparison.json`).

Two actual final CLI executions passed: unsupported-proxy observation update and
changed-method calibration audit. Both retain structured reasons and raw source
lineage. All **16 output artifact hashes**, source hashes and code hashes verified.
Use `demo_final/`, `delivery_verification.json` and `cli_commands.json`. Earlier
`cli_demo/` and `demo_verified/` are retained historical intermediate runs. The
first delivery verifier expected the forecast manifest's `output_hashes` key for
a calibration manifest, which uses `artifact_hashes`; the verifier was corrected,
not either runtime schema.

AST checks prove `_remaining`, beta equations, clock, joint sampling, size response,
reference-DLI gates, calibration prediction/loss/optimizer, posture residual and
cumulative-correction equations unchanged. The new gates control admissible inputs;
they do not fit biological coefficients. Tests use explicit synthetic fixtures.
Initial test failures were a reason-precedence bug (fixed), a test reusing an old
manifest hash after editing its fixture (fixed), and the new additive source-row
field in the historical golden (excluded explicitly, values preserved).

Commands from project root:

```powershell
python -X utf8 -m pytest tools/tests/test_p3_area_review.py tools/tests/test_p3_growth_pack_v2.py tools/tests/test_growth_calibration.py tools/tests/test_p3_growth_decisions.py tools/tests/test_p3_growth_science.py tools/tests/test_probabilistic_compound_growth.py tools/tests/test_compound_growth.py -q --junitxml=build/area_review_alignment_20261005_01/P3/acceptance.xml
$env:PYTHONPATH='.'
python -X utf8 build/area_review_alignment_20261005_01/P3/verify_delivery.py demo_final
```

Use fresh output names to rerun; do not overwrite the evidence. The directory is
not a Git checkout; source-before copies and explicit diffs are saved instead.

## Downstream owners and unresolved science

Claude/design: keep **area-A1/A2 reporting priority**, **leaflet matching** and
**calibration strategy** open. These are unrelated to the adopted physiological
A1-A7 and D11-D21. Supply approved changed-method/pose/partition/phase comparability
rules and any merge/split/placement state mapping; until then those comparisons
are unavailable. Supply a corrected, identifiable area-A2-to-trait contract before
using a normal or leaflet estimate as a compound observation. No botanical face or
light-to-direction law follows from those outputs.

P1/acquisition: provide independently referenced same-organ area measurements,
reviewed tissue inclusion/coverage, calibrated scale, source rows/hashes and
cross-date identity/lineage; validate magnitude against independent area references.
Retain within-session correspondence separately. Real supported data may use the
explicit contract after review; automatic P1 producer adaptation is not implemented.
Provide repeated measurements of the same trait under specified posture/capture
phase to quantify measurement variance, separately from dated growth observations.
Supply enough independent plants/assignment units and multiple later observations
per organ for dynamics; neither one capture nor repeatability alone is that data.

P2/P4/coordination: continue to keep reference incident DLI, tissue area, optical
surface support and biological face distinct. Consume this report/contract and
final hashes for later integration; this task dispatched no messages and changed
no other project's runtime. No whole-plant allocation, curvature default, G=0.5,
quantile estimator, hull-to-tissue conversion or synthetic MAE calibration was added.

The independent G audit remains sensitivity evidence only (about 0.472-0.550 over
its cases). Unknown occlusion does not yield a finite true-area interval; top views
do not remove normal sign ambiguity; area and normal do not provide located ray
surfaces. The source's companion simulations/CSV/SVGs remain unavailable as reported
in the prior review, and their claimed synthetic accuracy remains unreplicated.
No physical accuracy or successful real one-month forecast is claimed.
