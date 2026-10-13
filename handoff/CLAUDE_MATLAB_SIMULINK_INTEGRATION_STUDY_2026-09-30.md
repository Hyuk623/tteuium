# MATLAB and Simulink integration study for tomato light and flowering analysis

Date: 2026-09-30
Author: Codex
Status: researched integration proposal, not an implemented or executed MATLAB model.

## Purpose and recommendation

The user asked how to connect and run MATLAB and Simulink with the existing project and use their tools effectively. Keep Python for annotations, reviewed identities and reconstruction; keep GroIMP for optical transport. Use MATLAB for numerical inspection and parameter studies, and Simulink for time-dependent lighting schedules, light accumulation and eventually measured control dynamics.

Start with a CSV/JSON bridge and one fixed geometry snapshot. Precompute optical responses in GroIMP outside Simulink's time-step loop. Introduce direct Python calls only when a specific need justifies the additional runtime coupling. This is an engineering recommendation based on the current interfaces, not a measured performance result.

This document does not change the approved six-week research endpoint: light distribution and first open flower. CO2 is not measured. Photosynthesis under assumed CO2 remains a separate optional model, not required input to flowering analysis. No agronomic PPFD targets or optimum density are established here.

## Verified project starting point

Read project AGENTS.md and CONVENTIONS.md, recent LOG/TODO, the density/flowering handoff, tools/groimp_density.py and saved CSV headers.

- Existing light support: tools/groimp_density.py prepares and executes native GroIMP jobs and collects leaf, sensor and density tables.
- Existing endpoint support: tools/first_flowering.py handles interval/right-censored flowering observations; tools/density_flowering_report.py joins results. Reuse these definitions rather than adding an inconsistent flowering threshold in Simulink.
- Source bundle build/xl_handoff_20260929_092848 has zero optical leaf surfaces for each of dwt_01 through dwt_04, as recorded in build/density_flowering_inputs_20260930/current_readiness/readiness.json. This statement is about that pinned bundle, not every newer intermediate.
- Native synthetic optical checks exist. They validate software behavior, not plant-specific absolute PPFD.
- A reviewed real directional LED adapter, accepted actual leaf triangles and independent PPFD measurements are still required for real light validation.
- Current collection represents all lamps at full output. Individual-lamp response tables and time schedules are proposed extensions, not existing functionality.
- No matlab executable was found on PATH, and C:/Program Files/MATLAB was absent. This limited check does not exclude a custom installation or MATLAB Online. License, release and installed toolboxes remain unverified.
- No existing .m or .slx file was found in the inspected tools/handoff search. No MATLAB installation, toolbox purchase, inference, training or hardware actuation was performed.

All diagnostic flags remain validated_metric=false and suitable_for_ppfd=false.

## Connection routes

| Route | Implementation approach | Appropriate use | Main boundary |
| --- | --- | --- | --- |
| CSV/JSON offline bridge | MATLAB readtable/jsondecode; construct workspace signals; run Simulink | First prototype, reproducible comparison, independent program versions | New converter/model must still be implemented |
| Python orchestrates MATLAB | MATLAB Engine API calls a MATLAB wrapper that runs sim | Existing Python job runner needs one controlled MATLAB run | MATLAB installation and a release-compatible engine/Python combination required |
| Python inside Simulink | Python Code block, or MATLAB Function/MATLAB System integration | Small validated calculations that genuinely need to execute during simulation | Version, execution mode and deployment limitations must be checked |
| GroIMP on every time step | External process from a block | Not recommended for this initial study | Repeated startup/ray tracing, solver calls and stochastic noise are unnecessary for fixed geometry |
| Future hardware connection | Add measured sensor/device interfaces after simulation validation | Closed-loop LED/fan operation | Hardware protocol, device constraints and real dynamics are not yet specified |

Python Code is documented since R2025a and requires InProcess Python execution. MATLAB Function/Python integration has simulation/code-generation constraints; do not assume a Python-enabled model is automatically deployable. Use the installed release's documentation before selecting this route. [Python Code block](https://www.mathworks.com/help/simulink/ref_extras/pythoncode.html), [Python integration overview](https://www.mathworks.com/help/simulink/ug/overview-of-integrating-python-code-with-simulink.html).

The MATLAB Engine package must match the MATLAB release. The project uses Python 3.13 locally; verify compatibility rather than installing the latest matlabengine package blindly. [Engine installation](https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html), [Python compatibility](https://www.mathworks.com/support/requirements/python-compatibility.html).

## First executable model to build

Proposed first deliverable: a one-day lighting replay for one fixed snapshot, with no growth update.

1. Read a completed optical run and its provenance.
2. Select one sensor or a documented leaf-light quantity.
3. Load the on/off or dimming schedule.
4. Compute the light time series using a calibrated dimming response, or explicitly label ideal proportional scaling as a synthetic assumption.
5. Integrate the light quantity and separately integrate measured/modelled electrical power.
6. Compare against an independent Python calculation and display the time series.

Proposed block arrangement:

```text
From Workspace: lamp schedule
  -> dimming response / saturation
  -> fixed snapshot optical response
  -> light signal --------------------------------------> Scope / logged results
       -> gain 1e-6 -> accumulation over seconds --------> daily light integral

From Workspace: electrical power schedule
  -> gain 1/3600 -> accumulation over seconds ----------> Wh
```

Use From Workspace for time signals and Constant/Gain or matrix operations for fixed responses. An n-D Lookup Table can interpolate a validated regular grid of height/angle responses; a discrete case selector is preferable for different plant counts/layouts. These blocks are documented interfaces, not evidence that a tomato model already exists. [From Workspace](https://www.mathworks.com/help/simulink/slref/fromworkspace.html), [n-D Lookup Table](https://www.mathworks.com/help/simulink/slref/ndlookuptable.html).

Simulation time is seconds. Explicitly configure schedule transitions and zero-order hold for on/off commands; do not allow default linear interpolation to invent a gradual sunrise. Choose an integration step that resolves the specified changes and test a smaller step. Stop at the declared schedule endpoint; do not silently extrapolate missing records.

For front-face sensor PPFD P(t), the daily integral is:
DLI = 1e-6 * integral(P(t) dt), in mol m^-2 day^-1 over a complete day.
For electrical power W(t), energy_Wh = integral(W(t) dt) / 3600.

A pure arithmetic test is 200 umol m^-2 s^-1 for 16 hours and zero for the rest: 11.52 mol m^-2 day^-1. This is a synthetic test value, not a recommended tomato setpoint. At 50 W for 16 hours, energy is 800 Wh; this is also a test fixture. A partial day is a cumulative interval dose, not a completed daily total.

Readiness is deliberately split: the time-integration model can be verified with synthetic or measured sensor signals now; biologically credible canopy outcomes still require reviewed optical inputs.

## Efficient optical response representation

For fixed geometry and optical properties, propose separate per-lamp responses:

P_i(t) = sum_j H_ij * u_j(t)

Here H_ij is the simulated quantity at receiver i with lamp j alone at its reference photon output, and u_j is a dimensionless photon-output fraction. This linear transport formulation is a proposed acceleration method. Validate superposition and Monte Carlo convergence before adoption. Electrical dimming percentage need not equal photon-output fraction; measure or calibrate that relationship. Changes in lamp spectrum, beam shape or geometry invalidate a simple shared scaling assumption.

Keep independent H tables for:
- front-face sensor incident PPFD;
- leaf incident flux density, explicitly retaining face semantics;
- absorbed leaf photon flux.

The current all-lamps-on result cannot uniquely determine each H column. Add individual-lamp runs rather than inventing contributions. Hash each geometry, placement, lamp configuration and optical coefficient set.

A single dimming channel scales all receivers together in the ideal fixed-geometry model. It cannot independently correct lower/upper light ratio or spatial coefficient of variation. More controllable channels, different lamp positions/angles, changed spacing, or reviewed structural changes are needed to alter the distribution. Test feasible ranges before controller tuning.

For height and angle sweeps, start with a small explicit grid and compare interpolated predictions to omitted GroIMP cases. Shadow boundaries can make interpolation inaccurate. Reject out-of-domain queries rather than presenting extrapolation as validated light. Plant count/layout is a discrete scenario; do not interpolate across identities or different leaf vector lengths.

New geometry snapshots require new response tables. Holding a snapshot over a date interval is an explicit scenario assumption, not measured continuous plant growth.

## Existing data contracts to preserve

| Existing artifact | Fields inspected | Proposed consumer |
| --- | --- | --- |
| sensor_predictions.csv | case_id, sensor_id, height_group, snapshot_date, predicted_ppfd_umol_m2_s, scene_sha256, sensor_spec_sha256 | Sensor replay and independent measured comparison |
| leaf_light.csv | case_id, plant_id, session_id, organ_id, leaflet_id, n_triangles, area_mm2, incident_both_faces_umol_m2_s, absorbed_umol_s | Leaf-light visualization and separately named accumulations |
| density_comparison.csv | case_id, density_id, snapshot_date, plants_per_m2, n_plants, lower/upper incident_both_faces, plant_mean_cv, status | Discrete case comparison |
| results.json / readiness.json | Source hashes, status, quality flags, missing reasons | Import eligibility and provenance |
| Existing flowering CSVs | Plant/plot identity, visits and interval endpoints | Python endpoint analysis retained |

Never compare leaf incident_both_faces directly with a one-sided sensor reading as though they were the same observable. absorbed_umol_s is photon flux, not PPFD and not CO2 assimilation. Electrical watts are not photon flux without appropriate spectral information/calibration.

Add proposed schedules and adapter settings only as derived CSV/JSON under a new build directory. Record receiver ordering explicitly because matrix dimensions alone cannot preserve biological IDs. Preserve plant/session/organ IDs as text. Treat unavailable values with validity flags; never turn missing light into zero. Where a Simulink release disallows nonfinite signal values, fail or exclude a declared interval and report coverage instead of silently filling it.

Keep CSV/JSON as authoritative exchanged data. A generated .slx is a model artifact, not a replacement data format. Internal workspace structures and optional caches are disposable.

## Effective MATLAB use for preprocessing and midrib review

Use MATLAB as a small, reproducible numerical comparison environment; preserve the existing annotation web UI and pretrained Python/SAM workflow.

Proposed flow:

```text
Original image
  -> optional separable SG on Lab L for a segmentation experiment
  -> existing Python/SAM mask draft and human review
  -> accepted mask in ORIGINAL image coordinates
  -> original RGB / Lab L / separately computed R,G,B fractions
  -> controlled Gaussian or Hessian ridge enhancement
  -> tip/base constrained path proposal
  -> human and cross-view verification
```

Useful functions:
- Signal Processing Toolbox sgolayfilt with explicit dimension: apply along rows and columns separately for separable SG. It is not a full 2D polynomial fit. [sgolayfilt](https://www.mathworks.com/help/signal/ref/sgolayfilt.html).
- Image Processing Toolbox imgaussfilt for controlled sigma, filter size and border settings. Match Python precision, channel ranges and padding before attributing differences to an algorithm. [imgaussfilt](https://www.mathworks.com/help/images/ref/imgaussfilt.html).
- Image Processing Toolbox fibermetric for multiscale Hessian/Frangi ridge enhancement with bright/dark polarity. It enhances elongated structures; it neither identifies a anatomical midrib nor performs segmentation by itself. It includes scale-dependent smoothing, so additional Gaussian blur must be recorded as a separate experimental factor. [fibermetric](https://www.mathworks.com/help/images/ref/fibermetric.html).

Retain the unprocessed condition. Existing SG trials did not establish a universal segmentation gain. Do not force SG as the production default because it is available in MATLAB.

Filter unmasked image neighborhoods, then score only valid leaf-interior pixels. Do not convolve a black-filled mask boundary. Account for the complete filter support and holes/invalid pixels; compare methods on common valid support. Record clipped/overshooting SG values separately from display clipping.

OpenCV/original annotation coordinates use x=column, y=row with zero-based pixel centres. MATLAB arrays are indexed row,column from one. Any coordinate conversion must be explicit and round-trip tested. MATLAB Lab ranges also differ from common uint8 OpenCV encodings; do not mix them.

A visible ridge may be a vein, fold, hair or shadow. Human-confirmed tip/base landmarks and cross-view evidence are still necessary. The existing 51/71 proposals are not a measured midrib accuracy. Two-dimensional ridge curvature does not establish 3D surface curvature.

## Tool priorities

| Priority | Product or facility | Value for this project | Condition |
| --- | --- | --- | --- |
| First | MATLAB + Simulink | CSV/JSON import, numerical checks, lighting replay, basic blocks, scenario logging | Installation/license still unverified |
| First for image research | Image Processing Toolbox | Gaussian, Lab processing and ridge-enhancement comparison | Needed only for this MATLAB image branch |
| Optional for SG comparison | Signal Processing Toolbox | Documented SG filtering and signal inspection | Existing Python SG remains usable |
| After measured calibration data | Simulink Design Optimization | Parameter Estimator and sensitivity analysis | Bounds and identifiable parameters needed; held-out evaluation |
| After actuator data | System Identification Toolbox | Fit LED/sensor/fan dynamic response from measured inputs/outputs | Does not supply a tomato flowering mechanism |
| After controllability checks | Simulink Control Design | PID tuning against a dynamic model | Targets, delays and saturation must be defined |
| When batch jobs justify it | Parallel Computing Toolbox | Parallel Simulink scenario runs | Serial runs are sufficient for first model |
| Later physical environment study | Simscape and relevant libraries | Thermal/moist-air component modeling | Requires physical parameters and measured validation |

Simulation Data Inspector is useful for comparing measured and simulated time series with declared tolerances. SimulationInput keeps scenario overrides separate from the base model. parsim enables parameter sweeps and falls back to serial execution without a Parallel Computing Toolbox license. Do not assume a Colab T4 accelerates GroIMP Java or arbitrary Simulink blocks. [Data Inspector](https://www.mathworks.com/help/simulink/slref/simulationdatainspector.html), [SimulationInput](https://www.mathworks.com/help/simulink/slref/simulink.simulationinput.html), [multiple simulations](https://www.mathworks.com/help/simulink/ug/run-multiple-simulations.html).

For parameter estimation, use empty-scene measurements to fit lamp behavior before canopy validation. Do not jointly absorb camera errors, wrong leaf normals and lamp power errors into an unconstrained fitted coefficient. Sensitivity analysis can prioritize uncertain geometry/optics, but parameter ranges must have evidence. [Sensitivity analysis](https://www.mathworks.com/help/sldo/sensitivity-analysis.html), [Design Optimization](https://www.mathworks.com/help/sldo/getting-started-with-simulink-design-optimization.html).

Use system identification and PID tools for measured engineering dynamics. Simscape moist-air components can support a later enclosure model; they do not infer plant transpiration or nutrition from a photograph. [System identification](https://www.mathworks.com/help/ident/gs/about-system-identification.html), [PID tuning](https://www.mathworks.com/help/slcontrol/ug/introduction-to-automatic-pid-tuning.html), [moist air modeling](https://www.mathworks.com/help/simscape/ug/modeling-moist-air-systems.html).

Do not acquire every toolbox up front. Confirm institutional entitlements and actual required products; pricing and entitlements were not audited.

## Proposed implementation and run procedure

All filenames below are proposals, not files created by this research task.

1. In the user's MATLAB environment, inspect version, ver and which('sim'). Record release and toolbox availability. For Python integration, also inspect pyenv and the release compatibility table.
2. Add tools/matlab_bridge.py to freeze a completed run into build/matlab_bridge_<timestamp>/ with exact source hashes, IDs, units and eligibility. Its tests should reject missing/ambiguous quantities.
3. Add tools/matlab/build_light_replay.m to create build/.../tomato_light_replay.slx programmatically or provide an equivalent reviewed graphical model.
4. Add tools/matlab/run_light_replay.m to read CSV/JSON, configure SimulationInput, execute sim and write new CSV/JSON output. Keep cache/code-generation folders under build.
5. Run the synthetic arithmetic fixture, then a saved synthetic GroIMP case, then real sensor replay. Record these evidence levels separately.
6. Only after that succeeds, add per-lamp response generation, density/height/angle case selection and measured controller dynamics.
7. Feed prospective light summaries into the existing Python flowering analysis only when the timing and geometry are justified; no future observations enter prediction.

Illustrative API sequence, requiring the proposed model to exist first:

```matlab
% Example wiring only; not executed and not a complete loader.
% The loader must validate source hashes, IDs, units and quality first.
schedule = readtable(scheduleCsv);
s = timeseries(schedule.photon_fraction, schedule.time_s);
s = setinterpmethod(s, 'zoh');
in = Simulink.SimulationInput('tomato_light_replay');
in = setVariable(in, 'lamp_schedule', s);
in = setVariable(in, 'H_sensor', reviewedSensorResponse);
out = sim(in);
```

The model's From Workspace block must also disable linear interpolation and use the declared stop time. The example assumes an already-reviewed response; it does not derive H from all-lamps-on observations.

## Validation and delivery gates

- Input round trip: IDs, dates, hashes, coordinate units, leaf/sensor semantics, missing states and row order preserved.
- Timing: exact step transitions; seconds/hours conversion; full-day versus partial-day dose; synthetic 11.52 DLI and 800 Wh reference; Python/MATLAB agreement within a declared numerical tolerance.
- Optical approximation: exact table-node agreement; withheld GroIMP cases; superposition and ray-count/seed convergence; no extrapolated claim.
- Preprocessing: original pixels unchanged; row/column coordinate round trip; matched Lab ranges, border modes and finite support; human-only reference masks.
- Controller: bounded output, measured delay/dynamics, feasible independent receiver targets. One input must not be presented as independent control of many leaf targets.
- Research: separate lamp calibration from canopy evaluation; preserve quality gates; distinguish model uncertainty from Monte Carlo variation.
- First flower: interval/right censoring and plot-level separation preserved; no assumed PPFD dose threshold that declares flowering without observed validation.
- Output: model/scripts, CSV comparisons and JSON manifests under new build outputs, plus an English completion handoff with actual MATLAB release and execution logs.

## Research task outcome

The existing interfaces and primary MathWorks documentation were inspected. This English proposal was saved; no .m/.slx implementation or MATLAB simulation was run. Sources, labels, calibration, model weights and the current Python/GroIMP pipeline were preserved. Immediate recommended prototype: one-day light replay and accumulation. Highest-value image experiment: controlled original-image ridge analysis within reviewed masks. Real density/flowering conclusions remain dependent on physical validation and observations.

## Follow up on integration and performance comparison

The user requested a comparison with the existing tools. This section defines an executable comparison protocol for subsequent implementation; it contains no measured MATLAB speed or accuracy claim. A fresh PATH/default-install-directory check still did not locate MATLAB. Custom installations, MATLAB Online and licenses remain unverified.

### Integration without model conversion

Recommended first connection: preserve YOLO/SAM inference in its current Python environment, exchange original-resolution masks as lossless raster files with CSV/JSON identity and provenance, and use MATLAB for selected numerical analysis. Pass GroIMP CSV/JSON outputs into MATLAB/Simulink separately. Heavy inference remains on authorized Colab workflows, not local MATLAB.

If direct orchestration is later required, keep one MATLAB Engine session alive for a batch and time data transfer separately. The Engine converts Python/MATLAB data types; verify shape, dtype and ID preservation. Do not transfer images one pixel at a time. [Engine data exchange](https://www.mathworks.com/help/matlab/matlab_external/pass-data-between-matlab-and-python-from-python.html).

MATLAB can import certain exported/traced PyTorch networks using Deep Learning Toolbox and its converter support package. This does not establish compatibility with this project's exact YOLO/SAM checkpoints, prompt encoders, postprocessing or custom operators. No project model was imported or tested. Native-model conversion is a separate experiment with numerical equivalence checks, not a prerequisite for the bridge. [PyTorch import](https://www.mathworks.com/help/deeplearning/ref/importnetworkfrompytorch.html).

### Three comparisons that must stay separate

1. **Implementation equivalence:** same mathematical filter, dtype, kernel support, border rule and input. Measure pixel differences and elapsed time. This tests implementation behavior, not which biological model is better.
2. **Algorithm quality:** existing Python Hessian/path method versus a MATLAB ridge proposal. Different algorithms may return different paths. Compare against independently human-reviewed references; do not label differences as a programming-language effect.
3. **Workflow cost:** Python-only versus Python-to-MATLAB-to-Python. Include conversion, disk I/O, process startup, manual effort and maintenance. A faster kernel may still yield a slower total workflow.

| Task | Existing route | Candidate MATLAB route | Fair comparison |
| --- | --- | --- | --- |
| SG/Gaussian preprocessing | SciPy/OpenCV | sgolayfilt/imgaussfilt | Equivalent settings, max/mean pixel error, latency and memory |
| Mask inference | Frozen Python YOLO/SAM models | Initially call/reuse Python outputs | Same outputs establish bridge correctness, not a new accuracy improvement |
| Midrib candidates | Existing ridge/path proposal | Controlled fibermetric/path alternative | Reviewed path error, availability and human correction time |
| Geometric reconstruction | Existing calibrated Python helpers | Optional independent numerical check | Same measured poses/landmarks, reprojection error and independent dimension checks |
| Optical calculation | Native GroIMP | GroIMP retained | Identical run hashes; MATLAB visualization is not another optical solver |
| Daily light accumulation | Independent Python integration | Simulink replay | Same schedule and observable; numerical error, total runtime |
| Dynamic control studies | Would require additional Python implementation | Simulink block model and logging | Same equations/dynamics, constraints and disturbances; assess development effort separately |

For optics, distinguish full GroIMP ray tracing from a Simulink response-table approximation: compare both lookup error on withheld cases and runtime. A lookup speedup is an approximation/caching benefit, not evidence that MATLAB ray tracing is faster.

### Proposed small comparison dataset and measurements

Reuse the existing dwt_01 views 11, 18, 24 and 25 as a development pilot, with the exact frozen original image and human-reviewed mask hashes. Do not assume an export contains all 71 former observations without checking IDs. Full-image processing and individual crops must be reported separately. Subsequent independent evaluation requires a predeclared plant/plot split appropriate to the experiment; do not reuse parameter-selection images as independent validation.

Proposed benchmark procedure:

- Compare CPU implementations on the same host with recorded thread counts, processor, RAM, operating system, library versions and precision. Compare GPU implementations only on matched GPU/runtime conditions. Local MATLAB CPU versus Colab T4 is a deployment comparison, not a language benchmark.
- Load inputs once for compute-only timing. Separately measure complete input-to-saved-result elapsed time. Report cold startup apart from warm execution.
- Use a declared warm-up, then at least 10 timed repetitions for the small deterministic preprocessing pilot; retain individual times and summarize median and interquartile range. This is a proposed measurement setting, not completed testing.
- Use MATLAB timeit for CPU function timing and gputimeit for supported GPU computations. Synchronize asynchronous GPU work when using other timers; otherwise the measurement may only reflect dispatch. [timeit](https://www.mathworks.com/help/matlab/ref/timeit.html), [gputimeit](https://www.mathworks.com/help/parallel-computing/gputimeit.html).
- Hold model weights, prompts, candidate selection, thresholds, resizing and postprocessing fixed when evaluating preprocessing. Label any changed algorithm as a separate condition.
- Preserve RGB/BGR conventions, Lab encoding, original coordinates, row/column order and zero/one-based indexing. Match SG edge behavior and Gaussian border handling before interpreting discrepancies.
- Record model-quality metrics only against human-reviewed references. Mask IoU/Dice is available only with paired masks; midrib distance/error and correction time remain unavailable until separately observed. Better ridge contrast is not anatomical accuracy or recovered 3D curvature.

Proposed derived outputs: benchmark_runs.csv for per-run timing/environment, numerical_equivalence.csv, quality_metrics.csv with denominators/exclusions, and benchmark_manifest.json with source hashes and full settings. MATLAB measurements remain unavailable until MATLAB actually runs.

### Decision rule

Retain the current Python/SAM/GroIMP execution path by default. Adopt a MATLAB component only if it provides measured numerical/quality benefits or a useful inspection/control workflow at acceptable total time and maintenance cost. No speed multiplier, accuracy gain, model-conversion success or executed connection was established by this documentation task.



## Environment verification update 2026-10-01

The previous absence finding is superseded: MATLAB R2026b is now installed at `C:/Program Files/MATLAB/R2026b/bin/matlab.exe`, although it was not found on PATH. A background MATLAB batch process completed and reported version `26.2.0.3386108 (R2026b)`. `ver` listed MATLAB, MATLAB Copilot, Simulink and Simulink Copilot; no additional analysis toolboxes were listed. `license('test','Simulink')` returned 1, `which('sim')` resolved to the built-in Simulink engine, and `load_system('simulink')` succeeded. The library was closed and the batch process exited. Evidence: `build/simulink_check_20261001/readiness.json` and adjacent stdout/stderr logs. The startup emitted an unrecognized `nosplash` warning; omit that option in subsequent batch calls.

This confirms installed environment and library availability, not execution of a tomato simulation. No existing project `.m`/`.slx`/`.mdl` model was found by the project file search, and no model, bridge, training, inference or control action was implemented or executed during this check. The proposed CSV/JSON -> daily light replay connection remains to be implemented.
