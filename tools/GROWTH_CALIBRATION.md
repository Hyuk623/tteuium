# Growth response evidence and calibration

This adds explicit calibration to the existing probabilistic CompoundLeaf engine.
The proposed equations come from the growth handoff, not from transferred crop
coefficients. `growth_calibration.py` reads immutable observations, audits the fit
plan, fits eligible targets and exports a versioned parameter ensemble. It never
starts fitting from a forecast or executes images, light, neural training or UI.
The base calculator remains `tools.probabilistic_compound_growth`.

## Commands

Run from the project root with Python 3.11+ and installed NumPy/SciPy. Every output
must be a fresh subdirectory of project `build/`.

```powershell
python -X utf8 -m tools.growth_calibration --help
python -X utf8 -m tools.growth_calibration templates --out build/calibration_blank
python -X utf8 -m tools.growth_calibration audit --observations build/calibration_blank/observations.json --treatments build/calibration_blank/treatments.json --plan build/calibration_blank/fit_plan.json --out build/calibration_blank_audit
python -X utf8 -m tools.growth_calibration demo --out build/calibration_demo
python -X utf8 -m tools.growth_calibration fit --observations build/calibration_demo/inputs/observations.json --treatments build/calibration_demo/inputs/treatments.json --plan build/calibration_demo/inputs/fit_plan.json --evidence build/calibration_demo/inputs/evidence_registry.json --out build/calibration_explicit_fit
python -X utf8 -m tools.growth_calibration validate --parameters build/calibration_explicit_fit/parameter_set.json --observations build/calibration_demo/inputs/observations.json --plan build/calibration_demo/inputs/evaluation_plan.json --out build/calibration_validation
python -X utf8 -m pytest tools/tests/test_growth_calibration.py -q
```

Templates have no cultivar, biological coefficient, uncertainty scale or acceptance
threshold. `literature_candidates.json` is a separate discovery register, never
loaded as forecast defaults. The demo alone supplies clearly marked synthetic
assumptions. CLI `status=written` means artifacts were saved; inspect manifest and
audit status before using them. Scientific unavailability is a normal auditable
result; malformed inputs exit with code 2.

## Inputs

`observations.json` has `schema_version=growth-calibration-1`,
`data_kind=observed|synthetic`, `observations={path,sha256}` and optional original
`source_hashes`. Relative CSV paths resolve against this manifest. In-memory
manifests require `base_dir` for relative paths. `feature_units` maps environmental
CSV columns to exact declared units. Angular targets require
`target_metadata.<target_id>.angle_reference`; spectral/directional features also
need `feature_provenance` references. Missing values use empty CSV cells and JSON
null. Source files and previous results are never rewritten.

The observation CSV columns are exported by `templates` and declared in `COLUMNS`.
Each row identifies one organ state or one event endpoint, a true treatment
assignment `unit_id`, plant/organ/target identity, confirmed frame, origin and
measurement timestamps, elapsed calendar days, units, support/age basis and
capture phase relative to lighting. Continuous observations retain their measured
origin (`initial_value`) and measurement SD. A series cannot change its origin,
frame or area basis. An appearance event has one `interval` or `right` endpoint;
multiple successive censoring records are not independent events. `lower_day` is
last confirmed absence; `upper_day` is first confirmed appearance. Right censoring
has an empty upper bound and confirmed visibility. Occlusion is not absence.

`treatments.json` contains `units=[{unit_id,treatment_id,run_id,source_ref}]`.
Leaves/plants do not replace independently assigned plots/chambers/runs. Every
treatment requires the fit-plan minimum independent units for resampling.
Experimental causal interpretations additionally require design references for
randomization, blocking and controlled conditions. Other fits remain explicitly
observational associations or synthetic assumptions.

The frozen `fit_plan.json` declares target equations, parameters, known measurement
error, applicable domain, review, train/validation plant and unit sets, optimization
controls, uncertainty and model-selection freeze. Real data require a reviewed
plan with reviewer/source; a synthetic assumption review is sufficient only for
synthetic input. Failed scientific gates affect eligible components independently.
No future information from validation is used by the optimizer. Environmental
training exposures must be labelled `observed_history`.

## Supported explicit equations and fitting

| Family | Formula and roles | Likelihood |
| --- | --- | --- |
| `anchored_expansion` | `y0 + D*(1-exp(-k*a))`; `D` has target units, `k` is 1/calendar_day | Gaussian with measured SD and declared within-series exchangeable correlation |
| `azimuth_rotation` | `wrap(alpha0 + D*(1-exp(-k*a)))`; radians, named parent-local reference | von Mises with explicitly supplied concentration |
| `lognormal_wait` | `reference_day*exp(N(mu,sigma))`, plus explicit stop probability; residual versus inter-event endpoint is named | Exact interval probability or right-survival probability including stopped mass |

These are bounded supported fit families, not automated biological-law selection.
Full 3D rotation, initial-direction distributions and other response laws need a
reviewed fitting contract before adding a fitter. The base engine can still use
explicit assumption parameters for these quantities. Stem length and comparable
supported area can use `anchored_expansion` with their own units/evidence; envelope
width is not tissue area. Calendar coefficients cannot be passed to a different
development clock silently.

Parameters are either `fit` (initial value, finite bounds, bound source) or `fixed`
(explicit value); every parameter includes unit, evidence ID and identity/log
transform. Unknown is not fixed zero. All-fixed plans report assumptions, not a
successful calibration. No missing scientific field receives a hidden default.

Each feature has column/unit, affected role, identity/log link, coefficient ID,
center/scale, domain, basis and source. The current fit interface supports declared
constant exposure within a trajectory: standardized feature terms modify a role
additively or on its log scale. Varying histories are reported unavailable until a
reviewed integrated response is supplied. Collinear inputs (e.g. PPFD and DLI at
fixed photoperiod), constant inputs and endpoint-only data cannot identify dynamic
responses. Spectral and directional effects require their own evidence; scalar
PPFD does not identify a direction.

Bounded L-BFGS-B operates in scaled transformed parameter coordinates. Successful
optimization is followed by boundary and numerical local-curvature checks. Failed,
boundary-constrained or locally unidentified solutions are not parameter sets.
Whole assignment units are resampled within treatment strata, identically across
all targets. Joint bootstrap particles preserve parameter covariance. The number
of replicates, success fraction and all numerical tolerances come from the plan.
Local Hessian checks are diagnostics, not proof of global identifiability.

Bootstrap uncertainty is parameter uncertainty, not a Bayesian posterior or an
estimated complete process/noise model. Failed bootstrap replicates are reported;
an insufficient success fraction invalidates the uncertainty output. Residuals
remain inspectable in `residuals.csv`. Independent validation remains required.

## Validation

`evaluation_plan.json` names the exact fit-plan hash, frozen time, interval levels,
horizons and whether future environment is known, forecast or assumed. Forecast
origins cannot precede training information. Evaluation plant and assignment units
must be disjoint from fitting; repeated observations stay linked to their unit.
Scores are at the actual elapsed time. Missing 7/14/21/30-day targets generate
requirements instead of being relabelled to a convenient horizon.

Outputs include absolute/angular errors, scalar ensemble CRPS, event interval log
loss and occurrence Brier score. Parameter-only intervals are labelled separately
from observation-predictive intervals (Gaussian mixture with measurement error).
An angular likelihood uses the circular density; angular parameter intervals are
labelled as such. No unestimated biological process noise is fabricated.
Persistence is computed from the measured origin; recent-change needs separately
supplied, source-linked pre-origin history. Its absence is recorded. Target,
plant/unit and failed/unavailable denominators remain in the validation record.
No coefficient set is automatically promoted to `accepted_for_domain`.

## Connecting to the existing engine

`apply_parameter_set(parameter_set, model_config, scenario)` returns a new model
config. The fit plan must contain explicit `engine_bindings`; no guessed parameter
names or covariance transforms. Bindings use `constant`, `physical_location`,
`wait_distribution`, or `axis_stop` with target ID, role, family/axis, coordinate and
unit. `physical_location` applies the existing coordinate's inverse transform and
retains supplied process covariance. Every bootstrap particle updates all bound
families together. Unbound model assumptions and their provenance are retained.

A lognormal wait binding requires an existing exponential waiting coordinate and
rejects unfitted conditional/shared/serial or cross-trait dependence. A scalar
width increment must not be bound directly to an absolute target width; supply a
reviewed conversion when that interface is needed.

Runtime meaning guard (2026-10-04): `constant` and `physical_location` bindings
compare the fitted role's meaning (`ROLE_MEANING`) with the calculator coordinate's
meaning (`COORDINATE_MEANING`) before the unit check. Equal units are not enough:
`anchored_expansion.D` (remaining increment, mm) bound to `left_target_mm` or
`right_target_mm` (absolute target, mm) is refused with `Binding meaning mismatch`.
Undeclared roles or coordinates (including beta coordinates) are refused. No
conversion between meanings is implemented. Bindings are explicit model
interface contracts, not evidence of applicability to a new organ or cultivar.

```powershell
python -X utf8 -m tools.growth_calibration forecast --parameters <parameter_set.json> --history <observations.json> --origin <origin.json> --structure <structure.json> --model <model.json> --out build/calibrated_forecast_new
```

The model's scenario must match the adapter scenario, be within the declared
response domain and use a calendar clock or the explicitly supported normalized
temperature-clock exception below. The forecast CLI invokes only the
existing origin adapter, sampler and exporter. It never invokes fitting or light.
Future blocks retain the engine's optical-ineligible flags and shape protections.

## Artifacts and evidence limits

Every run exports `evidence_registry.json`, `data_audit.json`, `fit_plan.json`,
`parameter_set.json` (null if unavailable), `fit_diagnostics.csv`, `validation.csv`,
`requirements.csv`, and `manifest.json`. The manifest retains source/code/artifact
hashes, command, versions and seed. Empty CSV cells remain unavailable; zero is a
real numeric value. For in-memory configs the frozen JSON and hashes preserve the
exact supplied configuration even without a source filename.

`growth_calibration_evidence.json` records primary-source access and locators.
The WUR dwarf FSP full institutional PDF was recovered by direct HTTP after the
web tool failed. Equations and cultivar/experimental conditions were inspected;
supplement coefficients remain unadopted. No coefficients were taken from search
snippets. The two Frontiers articles
provide endpoint angle and spectral-treatment context; their static architecture
assumptions are not dynamic response parameters. No foreign cultivar coefficient
is installed as a dwarf tomato default. User plants still need confirmed repeated
observations, actual exposure/treatment-unit histories, reviewed fitting plans and
independent future targets. Code tests and synthetic recovery do not supply them.

## D8–D10 binding restrictions

`determinate_beta` has no fit family in this adapter. Bindings to its x_max,
a_m/a_e or ratio coordinates are refused explicitly, as are exponential expansion
bindings into a beta family. Do not relabel fitted exponential coefficients as
beta parameters. A fitted free stop probability cannot overwrite a node budget.
Existing process covariance and independent-wait guards remain unchanged.

The calendar-fitted pack may use a temperature development clock only when its
**hashed fit plan** contains `calibration_clock_reference` with:

```json
{
  "kind": "fixed_setpoint",
  "time_basis": "calendar_day",
  "temperature_c": null,
  "source_kind": null,
  "source_ref": null
}
```

Fill this with explicit calibration-period evidence/assumptions before freezing
the pack. A new model-config field cannot retroactively supply a missing fit-plan
reference. The adapter checks a temperature piecewise-linear clock, no
extrapolation, and m(T_ref)=1 at the declared calibration setpoint using the
model's numeric tolerance. A fluctuating-history mean or other time basis is
refused; normalization at one point does not establish equivalence for arbitrary
training temperature histories. Existing packs lacking this reference still work
with calendar time. None are silently upgraded or refitted.

Applied response features, exact bindings and source parameter-set identity are
frozen under `config.calibration.applied_features`; the full pack digest and
calibration reference are also recorded. P3's audit uses this provenance even
after the feature effect has been baked into a family constant/location. D9
rejects incompatible fitted drivers (including legacy PPFD or temperature size
responses), not merely live family coefficients. The new DLI response is a
separate explicit size-only contract; it is not applied twice through this
adapter. The engine's `none` light-coupling enum alone is not proof that a legacy
pack has no light dependence: also inspect the dependency paths, legacy flags and
audit availability.

## Accepted Science semantic guards (2026-10-04)

`ROLE_MEANING` and `COORDINATE_MEANING` distinguish remaining increment,
`absolute_extent_target_at_reference_DLI`, absolute potential maximum, birth value,
rate, angular offset, angular amplitude, positive wait, beta timing and
dimensionless ratio. Lognormal location/scale and stop probability keep their
separate meanings. Matching units alone never permits a cross-meaning binding;
no conversion or beta fitter was added. Width targets are reference-DLI extents:
their realized station asymptote is `w0+f_DLI*(target-w0)`.

Clock compatibility is checked before any binding. The accepted fixed-setpoint
rule above is unchanged, including rejection of fluctuating-history means. A
fitted free stop probability is refused when the destination axis has a node
budget. L02 directional-light descriptors in binding/parameter/source provenance
are refused for angular offsets, rotation amplitudes and rotation rates: no
light-to-direction response law has been adopted. Missing or falsely labelled
provenance cannot be scientifically authenticated by this software guard.

P3's reference-DLI contract requires separate coefficient identities and roles
for exponential increments and beta maxima, incident reference-plane provenance,
a complete local day and explicit applicability bounds. Independently supported
coefficients can have equal values. None is fit, copied between curves or inferred
by the adapter. Frozen fit-plan/parameter hashes and pre-run-only application
remain unchanged. See `PROBABILISTIC_COMPOUND_GROWTH.md` for input/output fields.


## V2 canonical DLI failure result

The adapter delegates DLI validation to P3, which imports the single shared
`DLI_UNIT` (`mol/m2/day`). Missing/legacy scientific input returns
`status="unavailable"`, `calibration_applied=false`, the frozen parameter-set ID
and structured field diagnostics. The forecast CLI exports `unavailable.json`
and a manifest in this case. Malformed bindings, unit/meaning conflicts, hashes,
clock incompatibility and stop-budget conflicts remain refused. No fitting or
legacy-unit conversion occurs. Existing five meaning-guard cases are retained.
