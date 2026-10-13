# Reference DLI channel execution

Date: 2026-10-04. Active objective: CODEX_P2_GROWTH_PACK_V2_CHAT_PROMPT_2026-10-04.md, including D19/D20 and P2-a through P2-h.

## Implementation brief before edits

Current P2 reports reference DLI as unimplemented and has no reference_dli.py. The actual direct-angular-1 transport is delivered and must remain unchanged. Reuse schedule boundary evaluation and photon-dose arithmetic from the existing bridge; introduce an explicit measured-interval adapter, not a new tracer or an unrelated time engine. Implement logged and spot/schedule routes with declared sampling, transition, gap, timezone/DST, dimming, evidence and value-selection policies. Simulated route remains audit/interface only, even with known PPF.

Inputs will preserve the handoff CSV/JSON fields, extending only explicit metadata for date selection, sample support, sensor cosine/level evidence, ambient evidence, survey-derived positional tolerance, plant association/uniformity, model-domain source and fixed-horizon spread tolerance. Unknown real position/clock/readings/domain stay blank; confirmed 3 lamps, 16 h/day and 100% remain operating metadata. No new physical or biological coefficients.

P2 alone adds shared DLI_UNIT to tools/leaf_light/common.py and imports it in P2 modules. Add per-patch illuminated_faces using existing actual normal/opposite-side PPFD plus a separately reviewed, hashed biological face mapping. Unknown mapping, zero exposure or unknown contributions stay unavailable. Sum fixture exposure at the same patch/time; preserve two-face physical sums and all existing scalar/moment values.

Integrate hashed reference results into the package while retaining failed/out-of-domain evidence. Extend independent validation to check real daily support, reference/tissue basis separation, metadata/source hashes and face classifications; rehashed invented values cannot pass. Publish blank templates, synthetic route CLI runs, focused tests/JUnit, fresh packages and per-item audits. No P3/P4/calibration edits, fitting, remote execution, acquisition, forecast, physiological model or full-system integration.

Initial read-only P3 inspection: _validate_d9 and _validate_reference_dli still require legacy mol/m2/d. This conflicts with D19. Do not translate canonical results or patch P3. Finish independent P2 work, re-inspect the current owner contract for the bounded single-day acceptance check, and report the exact incompatibility if it remains. Multi-day/scenario selection must not fabricate one local-day record.

Technical evidence will be isolated under build/technical_review_fixes_20261004_01/P2; channel outputs under fresh build/reference_dli_20261004_* paths. Coordination owns the shared technical report; this chat will write only its two named P2 reports and append LOG/TODO.

## Interim implementation stage 02 (not final completion)

The previous parameter-acknowledgement turn made no implementation progress. This continuation re-read the authoritative prompt/rules and implemented the measured channel. Current files: `tools/reference_dli.py`, `reference_dli_contract.py`, `reference_dli_intervals.py`, `reference_dli_policy.py`, `reference_dli_consumer.py`, `reference_dli_demo.py`, `light_time.py`, their three test modules and `tools/REFERENCE_DLI.md`. Existing bridge schedule/dose helpers were extracted unchanged into `light_time.py`; bridge imports preserve their old names. Its package code hashes now include the shared helper. No light-core numerical code was changed.

Implemented producer behavior: explicit instantaneous versus interval-mean support; supported transition holds rather than artificial ramps; excluded samples as reconstruction barriers; complete-day/night coverage; elapsed DST day lengths or explicit refusal; measured versus asserted ambient evidence; target-output normalization once; survey-gradient-derived finite position tolerance and supported plant association; evidence-bound P3 domain; selected-day spread and reduction rules; canonical units; simulation readiness without tracing/fitting. Supported interval means can be integrated without lamp clock windows, with unknown on-duration retained. Their per-day split across midnight needs separate support evidence.

The standalone consumer verifies hashed source data, daily CSV/JSON/audit consistency, geometry/evidence policy, and independently computes daily doses from original readings. It does not call the producer, the producer day adapters, or its photon integrator. Arithmetic tolerances are absolute 1e-12 and relative 1e-12. Rehashed forged numeric output is rejected. This is not yet a claim that the existing tissue package consumer accepts a channel result.

Commands executed include the CLI `--help`, synthetic input generation, both `compute` routes, blank `templates`, `simulate` using the preserved actual lamp draft, and standalone consumer verification. Fresh artifacts:

- `build/reference_dli_20261004_01/`: synthetic spot inputs/result, 11.52 mol/m2/day, independent consumer valid.
- `build/reference_dli_20261004_02/`: blank real templates and Korean measurement checklist; confirmed three lamps / 16 h / 100%, clocks unknown.
- `build/reference_dli_20261004_03/`: synthetic logged inputs/result, 11.52 mol/m2/day, independent consumer valid.
- `build/reference_dli_20261004_04/`: simulation readiness, unavailable with lamp_ppf_missing and reference_basis_missing; independent consumer valid as unavailable.

Latest test command: `python -X utf8 -m pytest tools/tests/test_reference_dli_channel.py tools/tests/test_reference_dli_intervals.py tools/tests/test_reference_dli_consumer.py tools/tests/test_light_growth_bridge.py -q --junitxml=build/technical_review_fixes_20261004_01/P2/reference_stage_02.xml`.

Outcome: 105 passed, no failures/errors/skips. `reference_stage_02_verification.json` records current code hashes, JUnit hash, three consumer checks and all 21 protected source/config/real-lamp hashes unchanged. Earlier stage JUnit files are preserved. These stage outputs must be regenerated into fresh paths after relevant code changes, not rehashed in place.

Current P3 read-only inspection supersedes the initial legacy-only finding: the owner has now adopted DLI_UNIT and explicit reference/domain/basis validation. The acceptance round trip has not yet been executed. Its evidence enum is measured/user_assumed/literature_informed/fitted, so the mapping must preserve the detailed P2 route separately while explicitly mapping evidence classification; no route or model coefficients may be invented.

Outstanding software work remains: bridge hashed-channel request/mapping, schema/capabilities and existing package independent consumer; D20 reviewed biological faces on actual transport and simultaneous fixture combinations; bounded P3 acceptance/refusal and multi-day limitations; fresh full package/splits and numeric preservation; full acceptance audit and final reports. Keep the active goal open. Actual reference position, clock windows, reviewed model-domain evidence and measurements remain missing physical inputs, not reasons to postpone synthetic software work.

## Final bounded software delivery, 2026-10-04

This section supersedes the initial/interim in-progress statuses above. The scoped P2 V2 reference producer, package integration, D20 output and bounded compatibility work are complete. The approved B execution deferral, P3 multi-day schema limitation and missing real physical evidence remain explicit; no full-system integration is claimed.

### Exact code and input/output contract

- `tools/reference_dli.py`: `prepare_record`, `save_result`, `templates`, `simulation_reason`, CLI compute/templates/simulate.
- `tools/reference_dli_contract.py`: strict photon reading/evidence/geometry, canonical-unit checks, surveyed support and plant association.
- `tools/reference_dli_intervals.py`: measured interval adapters, dated schedule, supported means without lamp clocks, and single-application output scaling. `tools/light_time.py` contains the extracted existing schedule/dose functions; bridge public names remain import-compatible.
- `tools/reference_dli_policy.py`: sensor/ambient evidence, hashed domain pointer and explicit daily reduction/spread policy.
- `tools/reference_dli_consumer.py`: independent original-reading arithmetic, source/code/artifact hashes and semantic checks. It never calls producer day integration. Numeric comparisons, including nested provenance values, use abs=1e-12 / rel=1e-12.
- `tools/light_reference_channel.py`: hashed package attachment, usable mapping only when available, original-request/plant-inventory binding, and retention of unavailable/out-of-domain evidence.
- `tools/reference_dli_p3.py::map_single_day`: verified producer representation mapped into an already declared model block. Evidence classification is an explicit argument in P3's vocabulary; original detailed route is retained. kind/center/scale/coefficients/domain bindings are preserved, never inferred or rebound.
- Existing `light_growth_bridge.py`, `light_growth_consumer.py`, `light_growth_schema.json`: optional reference/face request extensions, required evidence JSON, current capabilities/policy and independent checks. D20 details are in the V2 report.
- Guides: `tools/REFERENCE_DLI.md`, `tools/LIGHT_GROWTH_BRIDGE.md`. Synthetic/reproduction CLIs: `tools/reference_dli_demo.py`, `tools/light_growth_v2_demo.py`. No P3/P4 runtime, calibration, config, docs, human data or light-core numerical code was edited.

Required physical fields remain the handoff CSV/JSON contract. Additional explicit policy fields, exact enum values, evidence shapes, temporal reconstruction, survey-derived tolerance, missingness and CLI arguments are documented in REFERENCE_DLI.md. Evidence is `{path,sha256}`; applicability additionally uses `json_pointer` to a declared P3 `{min,max,unit}` domain. Real templates supply no position, clocks, scientific tolerances, sensor identity, domain or measurements. Unit is incident umol/m2/s at the sensor and DLI_UNIT mol/m2/day; no tissue area/absorptance or lumens/CCT conversion enters this channel. Unknown daily values are empty CSV cells, never zero. Complete out-of-range daily values remain numeric audit data; usable value is null.

Package request `reference_dli={path,sha256}` copies the producer JSON/CSV/audit byte-for-byte into `reference_dli/`, records `reference_channel.json`, and tracks original source hashes. Available mapping names only explicitly associated plant instances. Original-request and full-canopy instance inventory are independently checked; splits preserve that scope rather than relabelling a reference as the copied instance. Missing input uses `reference_inputs_not_supplied`; implemented capability is separate from measurement availability. A failed or out-of-domain result remains attached with no usable mapping value/basis/domain. Native direction/side channels remain unavailable.

### All nine source acceptance checks

| Check | Verified outcome / evidence |
|---|---|
| 1 Logged 200 x 16 h + supported night | 11.52 mol/m2/day, current CLI `_06/result`, semantics/support tests |
| 2 Missing support | Endpoint, disallowed gap, unknown or excluded sample -> incomplete/empty DLI; no darkness substitution |
| 3 Day/timezone | Midnight-crossing windows and actual 23/25-hour DST days; explicit transition refusal also tested |
| 4 Spot/schedule | `_05/result` 11.52; ambient/constant/output/schedule declarations required; no double dimming |
| 5 Non-photon | Lux/W/m2 direct data refused by name; this CLI performs no spectral conversion |
| 6 Basis collision | Producer and independent consumer refuse tissue reuse; current P3 reverse guard also tested |
| 7 Domain | Numeric 57.6 audit retained out of domain; no usable reference; frozen model/domain conflicts refused |
| 8 Simulation | `_07` returns lamp_ppf_missing plus missing reference identity; known-PPF test still returns simulation_execution_deferred; no fit/trace |
| 9 Mapping/consumer/P3 | Available package and two splits pass; rehashed false claims fail; actual producer -> current P3 validator passes, out-of-domain input fails |

P2-a..h additions are covered by discriminating tests: transition strictly inside a sampling interval for both semantics; cosine false versus unknown and level evidence; asserted versus measured daytime ambient; local-gradient finite radius and underdetermined/flat/outside support refusal; all associated plants within declared uniformity; variable days_used failing fixed-horizon tolerance; explicit DST policy; two-way basis separation. A two-day mean also passes the independent consumer while retaining both dates. The declared-scenario producer mode retains scenario evidence. Neither multi-day nor scenario is collapsed to a fake P3 date: the current P3 mapping explicitly refuses these modes with `p3_single_local_day_contract_cannot_represent_<value_rule>`. This is the exact permitted consumer-schema limitation, not an unimplemented producer mode.

### Current artifacts, tests and reproducibility

- Fresh full run: `build/light_growth_v2_20261004_02/`. Deliver `v2_package/`, `v2_P1_in_canopy/`, `v2_P1_COPY_in_canopy/`, `reference_result/`, `predeclared_p3_validator_config.json`, `p3_validator_input.json`, and `v2_verification.json`.
- Standalone current CLI results: `build/reference_dli_20261004_05/result/` (spot), `_06/result/` (logged), `_07/` (simulation refusal). Both constant measured fixtures produce 11.52. The full package's explicitly different two-fixture synthetic schedule produces 9.72 and is not the real REF-30-40 configuration.
- Blank real templates and Korean one-page checklist: `build/reference_dli_20261004_02/`, including `측정_체크리스트.md`. Confirmed three lamps / 16 h/day / output setting 100% are preserved; actual clocks are blank.
- Current software evidence: `build/technical_review_fixes_20261004_01/P2/completion_audit.json`, `delivery_checks.json`, `verify_delivery.py` and four final JUnit files. 175 unique passing cases are covered by the 171-case regression, 70-case attachment follow-up, one current Windows prepare-light delegation check and one multi-day independent-consumer check (overlaps are not double-counted).
- Read-only final audit: `python -X utf8 build/technical_review_fixes_20261004_01/P2/verify_delivery.py`. It verifies test coverage, current sources, six packages, three standalone channels, artifact hashes, historical numeric parity, exact source protection and bounded P3/P4 gate evidence.
- The two named Windows tests are confirmed in P3 owner's current-source final JUnit. The prepare-light delegation test was also rerun here. `test_legacy_golden_numerical_payload` calls sample_forecast, so P2 inspected the owner's passing result and matching current P3/calibration hashes instead of violating the no-forecast instruction. Other-owner P3/P4/calibration suites were not rerun in this task; their current delivery evidence is reviewed. P2 directly exercised only the authorized P3 validator and P4 face metadata gate.

Commands run include both reference CLI compute routes, templates, simulate and standalone consumer; `python -X utf8 -m tools.light_growth_v2_demo --out build/light_growth_v2_20261004_02`; focused tests and the audit command above. Final regression selection is recorded in JUnit and the prior stage command plus `test_reference_dli_p3.py`, `test_light_reference_faces.py`, `test_light_reference_provenance.py`, `test_light_direction_diagnostics.py`. Intermediate failures exposed a nested-float comparison issue and an incomplete synthetic P3 clock fixture; both were fixed and verified. Historical failed/passing stage reports and old numerical artifacts are preserved. No old hash was changed to force acceptance.

All numeric columns in all five tables match the historical `build/light_growth_science_20261004_01/package` exactly: 5 instance rows, 1,344 light samples, 1,080 features, 14 intervals, 48 doses. The fresh unannotated versus annotated package comparison is also exact. All 21 protected core/config/real-lamp files match the pre-work hashes. Transport remains one call per snapshot with 56 receivers, two fixtures x four emitters, 224/224 paths per fixture, chunks <=127 and 10,752 accumulator array bytes. Existing pair/chunk/minute resource guards pass. Package numerical comparisons retain abs=1e-10 / rel=1e-9; direction degeneracy remains 1e-12. These are numerical verification tolerances, not physical accuracy thresholds.

### Remaining real inputs and explicitly deferred scope

The meter is expected around 2026-10-10; arrival and measurement are not established. Supply an actual reference position/height/frame and level/cosine evidence, actual dated on/off clocks for route C, identified PPFD observations/support, ambient evidence, survey and scientifically declared positional/uniformity/horizon tolerances, plant association and the P3 coefficient-domain record. Complete logged interval means can establish a daily integral independently of unknown lamp clocks, but must not invent an on-duration. Real reference inputs stay blank until provided.

Real optical simulation/PPFD validation additionally needs actual PPF, emitting aperture/center/height and beam evidence, reviewed optical leaf geometry/optics and independent sensor/calibration/evaluation measurements. The measured A/C channel does not require lamp PPF. B execution, full P1-P2-P3-P4 integration, growth/physiology predictions, future optical geometry, fitting, acquisition and remote execution remain outside this task. No real PPFD accuracy, biological applicability or validated physical leaf-face claim is made.
