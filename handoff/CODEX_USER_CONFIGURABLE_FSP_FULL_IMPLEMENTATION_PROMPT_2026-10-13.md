# Implement a user-configurable tomato FSP application with active growth responses

Date: 2026-10-13
Primary implementer: Codex application/integration owner
Scientific contracts: Claude scientific reviewer
Producer/forecast dependencies: existing Claude Code P1 and Micro-Tom forecast owners
Root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

## 1. User objective and completion standard

Build a usable local application in which the user enters plant count, temperature, relative humidity, light, irrigation and nutrient conditions, starts a simulation, and sees their effects on per-plant and per-organ growth. Include presets, schedules, save/load, scenario comparisons, native 3D output, progress and explicit failures.

This is a request for a complete working calculation path, not only a settings form, JSON exporter, recorded-only climate columns or prerecorded animation. Every advertised active control must reach an executable model and its causal outputs. Preserve scientific honesty: complete software integration does not mean measured Micro-Tom accuracy. Do not remove assumption labels to make a run look complete.

Support both an observation-initialized route and an explicitly selected generated-plant route. Generated plants make user-defined scenarios executable without pretending that missing photo reconstruction exists. Real reconstruction cannot be claimed until P1 supplies supported geometry and identity. Missing reviewed response laws are unfinished scope, not satisfied by an inactive checkbox or an arbitrary multiplier.

No implementation is executed by creation of this prompt. When this prompt is assigned for implementation, carry out the authorized work through actual UI, CLI and native acceptance.

## 2. Recommended implementation environment

Use Windows local execution, the project's verified Python environment (requires Python >=3.11; inspect and retain a working interpreter), GroIMP 2.2.1 and the working Java 21 runtime. Freeze exact tested versions. Do not replace the environment or upgrade the native engine as part of UI work without a demonstrated need.

Add a **Streamlit local browser UI** over a UI-independent Python service and the existing native pipeline. Keep Python adapters, validation and worker lifecycle outside the UI script. GroIMP remains the authority for native plant physiology/allocation/development; Python owns input preparation, selected external light adapters, resource bookkeeping and verification.

Launch from the Codex PowerShell terminal, bind the web UI to `127.0.0.1`, and open it in the user's browser. This is a local desktop workflow; hosting, authentication, cloud deployment, CUDA and model training are not prerequisites for the input application. Do not imply that Streamlit accelerates native computation. Retain headless GroIMP and avoid unexpected console windows for background helpers.

Use forms to submit related settings together, explicit Run/Cancel actions, and session state for UI convenience only. Durable settings, job state and checkpoints must survive browser refresh independently of Streamlit session state. A widget change or page rerun must never launch another GroIMP process.

Official implementation references, checked 2026-10-13:

- [Streamlit local run](https://docs.streamlit.io/develop/concepts/architecture/run-your-app)
- [Streamlit forms and reruns](https://docs.streamlit.io/develop/concepts/architecture/forms)
- [Streamlit session state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
- [GroIMP command-line/headless mode](https://wiki.grogra.de/doku.php?id=user-guide%3Acommand-line-arguments)

These sources support application mechanics, not plant biology. A separate frontend/API stack may be considered later for multi-user service; it is not required for this local implementation.

## 3. Read first and coordinate current work

Read parent/project rules, LOG/TODO and current claims. Inspect:

- `tools/TOMATO_FSP_PIPELINE.md`, `tools/MICROTOM_FORECAST.md` and actual public APIs.
- `handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md`.
- `handoff/CODEX_FSP_EIGHT_CAPABILITIES_EXECUTION_2026-10-11.md`.
- `handoff/CLAUDE_FOUR_PROJECT_SCIENCE_EQUATION_PARAMETER_REVIEW_2026-10-11.md`.
- Latest P1 revision-7 execution/package and MTG conventions/decisions.
- `handoff/NATIVE_BOUNDARY_CONTRACT_2026-10-13.md` and its latest execution report.
- Empirical light-field/growth-boundary contracts and reports; `tools/EMPIRICAL_LIGHT_FIELD.md`.
- `handoff/PROMPT_CODEX_NUTRIENT_RESERVOIR_CONTINUATION_2026-10-13.md`, its source contract and later decisions.
- S2 ownership amendments, VTC decisions and latest forecast/axis execution reports.

At prompt preparation, native boundary and empirical growth-boundary implementations have active claims. Do not overwrite their files or assume that a contract already has delivered runtime evidence. Reuse their public requests/responses after verification and coordinate exact missing hooks through LOG. Claude Code retains P1 and forecast-wrapper ownership. Claim new shared files before editing.

Keep human records/config/docs and original VTC read-only. Save user-created application scenarios separately under generated workspace output, never by silently rewriting experimental records. Do not revert another owner's concurrent changes. No automatic cross-chat dispatch, external uploads or remote jobs.

## 4. Input contract: one source for UI and CLI

Implement a versioned validated `fsp-user-scenario` model. The UI and CLI must call the same validator, resolver and compiler. Every value needs units, scope, origin, source/assumption metadata and model activity. Separate input acquisition (`user_entered`, imported record) from biological evidence (measured, literature, scenario assumption); map to existing source-kind enums explicitly.

| Group | Required user controls | Scope/behavior |
| --- | --- | --- |
| Plants | Count, cultivar/model, source mode, per-plant ID, initial stage/age or observed package, geometry template, initial physiological supplement | Count must equal explicit instance records; generated copies are labelled instances, never separate measured plants |
| Placement | Pot/tray/zone membership, XYZ, rotation, spacing, shelf layout, optional non-target occluders | Preview and validate transforms once; occupied geometry affects shading |
| Climate | Temperature in C, RH in %, CO2 in ppm where required, optional pressure/airflow/leaf-temperature inputs required by the selected model | Constant, day/night, or timestamped table; common defaults with explicit zone/plant overrides |
| Light | Native lamps or registered empirical field, source positions/orientation/output/spectrum where supported, on/off schedule and supported dimming | One light authority per interval; preserve incident/absorbed and horizontal/per-leaf bases |
| Irrigation/media | Medium layers, geometry, initial water, water capacity, irrigation events/volume, drainage and reuse | Pot-level or declared shared reservoir/tray topology; geometry is not water capacity |
| Nutrients | Product composition/basis, dose, dilution volume, source-water contribution, application events; EC/pH records where available | Element-resolved mode and EC-equivalent mode remain distinct; neither inferred from the other |
| Initial plant resources | Organ dry mass, reserves, roots, stored nutrients where required | Sourced estimates permitted with visible provenance; photos do not measure these quantities |
| Execution | Start timestamp/timezone, duration, output interval, solver/substep settings, seed, ray budget, selected response models | Distinguish numerical settings from biological parameters; record all resolved values |

Show easy common settings first and advanced per-instance/zone overrides second. Resolve precedence deterministically: explicit instance/zone overrides over scenario defaults; ambiguous overlapping zone assignments fail. Include a final resolved-input preview with origin and units before Run. Do not hide missing mandatory fields behind zeros.

Schedules require aware timestamps, complete coverage and a declared interpolation rule. Split at changes and events. Reject overlaps/gaps unless explicitly modelled. A fixed 14-hour or 16-hour historical setup must not become a universal default. Retain presets as named, versioned scenarios with their original source and date.

Plant count changes in the editor create a new initial scenario. Mid-run adding/removing plants requires explicit events and source/sink bookkeeping, not changing a counter in a live run. Separate biological limits from machine-resource limits; do not impose an unexplained fixed 24-plant model limit.

## 5. Scientific contracts that must become executable

Before adding new physiological responses, Claude must provide `handoff/USER_CONFIGURABLE_FSP_SCIENCE_CONTRACT_2026-10-13.md` or a verified later equivalent. For every equation specify input/output units, light/area basis, timestep, temperature/CO2/VPD domain, coefficient provenance, uncertainty, organ/cultivar dependence and failure behavior. Register exact model versions, parameter schemas and response ownership.

Implement independent application/adapter work while science is pending. Do not mark the full requested feature set complete until temperature, RH, light and the selected nutrient model have real causal native integration. Do not hardcode invented coefficients merely to produce responsive plots.

### Temperature and humidity

Temperature must affect the selected development clock, photosynthetic capacity/kinetics and respiration where the reviewed model specifies these processes. The existing fixed-NRH model cannot become temperature-responsive merely by storing temperature columns.

RH must enter a reviewed humidity/VPD -> stomatal conductance/transpiration -> carbon/water response. State whether VPD uses measured/modelled leaf temperature or an explicitly assumed leaf-air equality. Air-temperature/RH-derived VPD is not a complete leaf energy-balance model. Implement required water availability and hydraulic limits consistently. Humidity does not become active by changing only a reported VPD column.

Specify any pressure, boundary-layer conductance, airflow and CO2 inputs required by the selected law. Handle saturation/condensation/out-of-domain cases explicitly. Do not force higher temperature or RH always to increase growth. Distinguish an imposed climate scenario from modelling greenhouse HVAC or a canopy microclimate.

### Light

Native lamp transport: integrate the actual time schedule on the current canopy; reuse implemented optics and scene objects where supported. Empirical mode: freeze measured field/configuration hashes, spatial/time support and registered geometry, and reuse the new growth-boundary adapter when delivered. Never double shade an already intercepted field or send horizontal reference DLI directly as per-leaf absorbed flux.

Empirical output does not authorize extrapolation beyond its sampled region, unsupported dimming, new lamp placement or a new enclosure. Changes that invalidate its configuration require another measured field or an explicitly selected native-model scenario. Never silently swap engines. Incident/absorbed-to-NRH mapping must be reviewed before active real growth is claimed.

### Nutrients and water

Provide visibly separate capabilities:

1. Element-resolved composition and water/element accounting, with uptake/growth effects only under its complete reviewed contract.
2. Existing EC-equivalent reservoir response, if selected and fully defined, with its actual supported coupling site and limitations. It is not N/P/K-resolved uptake or a fertilizer-composition predictor.

If the UI promises composition-dependent growth, the element-resolved uptake/internal-state/demand/allocation law is mandatory; an EC-only curve does not satisfy it. Define medium exchange/release, root basis, internal stores, shortage/excess and salinity response where in scope. User-entered pH is recorded-only unless a reviewed pH response is implemented; show this before execution.

Respect the selected nutrient law's causal location. If EC affects gross assimilation, apply it there once; do not also impose an unrelated growth penalty. For element-limited growth use actual demand/availability/finalization. Do not infer missing ions, root mass or measured absorption from EC or images.

## 6. Single runtime loop and joint commitment

Implement the shared service around existing APIs; no UI-owned biology and no second engine in Python:

```text
validated UI/CLI scenario -> immutable resolved snapshot
-> P1 supported geometry OR explicit generated initialization
-> instances + canopy + resource topology
-> interval boundary and active environment
-> current-geometry native/empirical light (one authority)
-> reviewed temperature/RH/water/nutrient responses
-> provisional carbon exchange, development and resource demands
-> resource availability / native finalize handshake as the selected law requires
-> actual funded mass + organ development + morphology
-> independent carbon/water/nutrient checks
-> one atomic committed state -> new geometry -> next interval
```

Use the native continuation contract's predecessor, geometry, interval and source hashes. The old `advance_interval` publishes already-produced checkpoints; it must not be used as a second growth invocation or a retrospective nutrient limiter. Await causal boundaries before dependent native mutations.

Preserve one carbon pool per plant with current declared-axis rules; shared trays/reservoirs are explicit topology and cannot give each plant the entire reservoir stock. Coordinate transpiration and uptake with water storage; neither native nor Python may remove the same water twice. Reject negative stocks, stale responses, duplicate births and unsupported resource overdrafts. Log starvation/deficits under the reviewed policy.

One final allocation must agree with geometry, structural mass, reserve change and all resource ledgers. New organs cannot photosynthesize before birth. Frozen-geometry/substep conventions must be declared and tested. Keep developmental orientation distinct from phototropism; this request does not authorize an invented direction law.

## 7. Application and worker implementation

Proposed files (reuse equivalents if present):

- `tools/fsp_app.py`: Korean UI, forms, scenario editor, result display.
- `tools/fsp_user_scenario.py`: typed schema, validation and override resolution.
- `tools/fsp_scenario_service.py`: compile scenario to existing producer/native/resource inputs; activity map.
- `tools/fsp_job_runner.py`: durable job lifecycle and CLI shared by the UI.
- `tools/FSP_USER_APP.md`, isolated dependency file and focused tests.

Required functions: `validate_scenario`, `resolve_scenario`, `compile_run_inputs`, `submit_run`, `get_run_status`, `cancel_run`, `load_results`, `compare_runs`; map these to actual files and engine calls. Do not require those exact function names when an existing public equivalent is suitable.

UI flow: **개체·배치 -> 환경·조명 -> 관수·양분 -> 입력 확인 -> 실행 -> 결과 비교**. Offer JSON save/load and CSV schedules/imports with validation preview. Labels carry units. Model details/provenance belong in an expandable panel rather than distracting the normal input flow. For every control show `계산 반영`, `기록만`, or `미지원` based on actual capability, not manual marketing labels. A full-mode run must refuse recorded-only required growth drivers.

Job lifecycle: draft -> validated -> queued -> running -> completed/failed/cancelled. Freeze a unique request and job ID; explicit submission is idempotent. Do not launch long native jobs in a widget callback tied to reruns. Default to one active native job and a bounded queue; independently benchmark any concurrency increase.

Persist a manifest/status JSON, logs and immutable input snapshot per job; poll progress without holding a UI session open. Report native phase and committed simulation time, not invented overall percentages. Cancellation stops only that job's owned worker/native process tree, retains verified checkpoints and labels the attempt cancelled. Resume only by supported semantics; do not pretend native in-place resume exists if only fresh replay is supported.

Use local filesystem-safe APIs and argument lists for paths with Korean characters/spaces. Avoid shell interpolation of user values. Restrict generated outputs to fresh run directories. Write manifests atomically; handle OneDrive locks with bounded retry and explicit failure. Never delete old failed/successful runs to recover. An optional user-selected nonsynced output root is a future explicit setting, not a silent project move.

Target commands to implement and verify (not claims that these files already exist):

```powershell
python -m streamlit run tools/fsp_app.py --server.address 127.0.0.1
python -m tools.fsp_job_runner validate --scenario build/user_scenarios/example.json
python -m tools.fsp_job_runner run --scenario build/user_scenarios/example.json --out build/user_fsp_run_001
```

## 8. Results and observability

Display committed simulation time, plant count/identity, per-plant leaf area/dry mass/height/organ counts, carbon assimilation/respiration/reserves, water state/transpiration and the selected nutrient model's legitimate outputs. Show photosynthesis and allocation changes so a growth difference is explainable. Avoid reporting unimplemented fruit yield or predicted elemental uptake.

Render returned native geometry with time controls and plant selection. Show imported versus generated organs, light map and quantities/units. Viewer state must come from the committed model. Support side-by-side scenarios, absolute and relative differences, and min/max scenario spread clearly separated from calibrated confidence intervals.

Export `resolved_scenario.json`, `parameter_activity.csv`, `environment_consumed.csv`, plant/organ/light/resource time series, checkpoint lineage, model versions, code/source hashes and validation reports. `parameter_activity.csv` must trace each editable field to a consumed field, actual function/model and affected output, or an explicit inactive reason. Logs alone do not prove causal effect.

## 9. Acceptance: demonstrate active inputs, not merely editable controls

Use independent expected relations/limits and reviewed test domains. A different result is not universally required if a model saturates; include a responsive case and a saturation case with explanation. Compare numerical effects against stochastic light noise. Tests must cover:

1. UI save/load and CLI resolution produce identical effective inputs; editing widgets does not start jobs; double-submit does not duplicate execution; refresh retains job identity.
2. Counts 1, 4 and 24 yield correct unique plant instances/pools, no duplicated geometry or resources; a synthetic count test is not actual 24-plant reconstruction. Benchmark time/memory rather than promise instant results.
3. Temperature changes alter documented physiology/development paths within the approved domain; storing temperature is not sufficient. RH changes affect the reviewed transpiration/stomatal path and, in a responsive test, carbon or growth.
4. Light changes affect actual photon and carbon inputs; schedule integration matches analytic cases; geometry feedback is consumed at the next boundary. Verify native and empirical routes separately and reject unsupported empirical configuration changes.
5. Water-only addition dilutes concentration without adding nutrient mass. Same fertilizer ratio at different total concentration and different ratios at a declared equal-concentration basis remain distinguishable.
6. Nutrient supply changes the selected active growth response in a reviewed limitation case; element-resolved claims require elemental tests. EC-only mode must refuse an element-resolved completion claim. Verify enough-resource and oversupply domains separately.
7. Carbon, water and selected nutrient balances close; consumption follows actual growth; no duplicate stress/respiration deduction, no cross-plant carbon transfer, no duplicate reservoir withdrawal.
8. Job timeout/cancel/retry, native crash, stale boundary response, schema mismatch, invalid schedule and OneDrive write failure cannot publish a successful future state.
9. Legacy disabled-feature modes preserve prior results; existing P1 and forecast wrappers remain compatible under versioned contracts. Do not rerun every expensive historical scenario without a relevant reason.
10. A native multi-interval run launched from the UI completes with actively consumed temperature, RH, light and the selected nutrient law. Repeat from CLI with the same frozen scenario and compare within declared tolerances. Show later growth and 3D state, not only initial setup.

Validate the UI by actual interaction with submit, progress, results and error cases; unit tests alone do not prove usable UI behavior. Validate real-input readiness separately. A real P1 route with missing geometry must remain blocked; generated-route success is still a useful implemented simulation, not a measurement.

## 10. Work packages and final delivery

W0 inventory/claims and input-to-model gap map. W1 shared scenario schema and Korean UI. W2 job runner and existing native loop. W3 plant count/placement and light modes. W4 reviewed temperature/RH/water physiology. W5 reviewed nutrient model plus causal native transaction. W6 result/forecast integration. W7 UI/CLI/native causality tests and delivery. These are dependency milestones, not repeated user permission gates.

If a scientific contract is absent, finish independent W1–W3 and the relevant transaction mechanics, send the exact unresolved equation/parameter questions to the documented handoff, and keep W4/W5 and overall full-response completion open. Do not silently reduce the request to a dashboard. Continue remaining authorized work while awaiting the required science.

Deliver `handoff/USER_CONFIGURABLE_FSP_IMPLEMENTATION_EXECUTION_2026-10-13.md`, a Korean quick-start under the app's permitted documentation/output area, exact launch commands, dependency versions, field-to-function map, real execution artifacts and acceptance JSON. Document which response models are active, which are conditional parameterizations and which remain unimplemented. Distinguish complete software integration from independently validated Micro-Tom prediction.

Update flow only after coordinating its owner; append LOG with claims and results. Do not mark this objective complete solely because the UI can save every requested parameter.
