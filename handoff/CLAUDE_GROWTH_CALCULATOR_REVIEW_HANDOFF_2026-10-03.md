# Claude handoff: implemented CompoundLeaf growth calculator

Date: 2026-10-03. Prepared by Codex for scientific review and the next implementation specification.

## Purpose and status

The calculator projects measured tomato architecture over 30 days, producing joint distributions of existing-leaf growth and future CompoundLeaf appearance/placement. It is implemented as an extension of the existing `tools.compound_growth` CLI. It is **assumption-conditioned software**, not a fitted cultivar model or an independently validated real-plant forecast.

Claude's next responsibility is to review the scientific choices and identify precise corrections, parameter evidence and validation requirements. Do not infer biological acceptance from passing software tests. Do not rebuild the delivered calculator or repeat completed synthetic runs merely to establish activity.

Read the parent `공통규약.md`, project `AGENTS.md` / `CONVENTIONS.md`, latest LOG and relevant TODO entries. Respect shared OneDrive ownership: Codex owns `tools/` and `tools/tests/`; proposed changes to those files should be handed back as explicit requirements. Keep human observations/configuration unchanged.

## Read first

Paths below are relative to the project root, `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`.

1. `tools/PROBABILISTIC_COMPOUND_GROWTH.md` — implemented commands, parameter bindings, schemas and limitations.
2. `handoff/CODEX_GROWTH_CALCULATOR_EXECUTION_2026-10-03.md` — delivery record and requirement audit.
3. `handoff/CODEX_GROWTH_CALCULATOR_HANDOFF_2026-10-03.md` — authorized implementation scope.
4. `handoff/CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md` — proposed mathematics, literature/access limits and scientific assumptions; not completed Claude review.

## Delivered code and integration

| File | Responsibility |
| --- | --- |
| `tools/probabilistic_compound_growth.py` | Numerical calculator, validation, sampling/decoding, summaries, updates, evaluation, exports and CLI |
| `tools/compound_growth.py` | Existing observation/baseline implementation, extended with lazy `probabilistic` command delegation |
| `tools/tests/test_probabilistic_compound_growth.py` | New synthetic mathematical, state, update and integration tests |

Public functions: `prepare_origin`, `validate_model_config`, `sample_forecast`, `decode_trajectory`, `summarize_forecast`, `update_forecast`, `evaluate_forecasts`, `export_run`. Their argument contracts are in the original handoff and implementation documentation.

Reuse includes strict existing observation loading and persistence/recent-change baselines, plus shared IO/hashing helpers. Existing viewers and legacy commands remain in place. There is no new image pipeline, canopy assembly, light solver, UI or training system.

## What the implementation calculates

- **Measured origin:** existing full-axis points, bends, extents and attachment offsets are preserved exactly at day zero. Future states and generated IDs are separate from observed evidence.
- **Events:** distinct residual-to-next-event and subsequent inter-event distributions; stop probability or conditional logistic stop rule; multiple within-day events; trajectory-local future CompoundLeaf IDs.
- **Dependencies:** ordered transformed Gaussian variables, supplied cross-trait covariance, a shared plant effect and sequential AR residuals. Missing covariance is not inferred as zero.
- **Continuous change:** anchored remaining growth, `initial + D*(1-exp(-k*a))`, with explicit parameters. Widths approach nonnegative targets and can increase or decrease. Leaf-local rotation is separate from parent attachment translation.
- **Parent geometry:** measured material-segment elongation moves attachments. A previous terminal continues growing after a new node appears. Stem directions remain fixed; unobserved lateral-axis initiation is outside this version.
- **Environment:** calendar time, explicit piecewise developmental multipliers, or one declared piecewise-linear input response to the development clock. No automatic multiplication of environmental effects.
- **Light:** optional external metric/provenance and a declared fixed-light response. Incident PPFD and absorbed flux are distinct. Future shading is not recalculated.
- **Updates:** finite-bank likelihood reweighting with supported associations and observation errors. Confirmed, ambiguous, missed/occluded and unmatched observations have distinct behavior. No observation model means re-anchoring without a claimed parameter posterior.

The update output covers the **remaining original forecast horizon**. A fresh 30-day run needs explicit new-origin parameters and parent evidence. New compound observations do not make the old/predicted stem a newly measured stem; continuation-only configs cannot silently restart a full forecast.

## Inputs, outputs and boundaries

Inputs are the existing observation CSV bundle, `origin.json`, optional reviewed parent/attachment CSVs referenced by `structure.json`, and `model.json`. Biological parameter values, units, evidence, covariance and applicability are explicit. Blank templates contain no cultivar defaults or invented rates.

Optional cultivation fields: `temperature_c`, `relative_humidity_pct`, `ppfd_umol_m2_s`, `photoperiod_h`, `ec_ms_cm`, `ph`, `co2_ppm`. Without a declared response, they remain metadata and coupling is unavailable. Positions/lengths use mm, area cm2, directions unit vectors, and internal angular parameters radians. Time distinguishes calendar days from development days. `numeric_tolerances.absolute` is canonical; the documented scalar alias must not conflict.

Outputs include `events.csv`, `block_states.csv`, `trajectories.csv`, `trajectory_parameters.json`, `summary.csv`, `origin.json`, `model.json` and `manifest.json`. Applicable runs also export update/association or evaluation files. Samples preserve dependencies/modes; conditional geometry summaries are distinct from occurrence probabilities. Missing JSON values are null; missing CSV cells are empty.

**Optical boundary:** predicted envelopes are not occupied leaf tissue. They remain `optical_eligible=false` and `suitable_for_ppfd=false`; no opaque surfaces or leaflet meshes are generated. Supported partial area, estimated total area and dimensionless image-area ratios cannot be interchanged. Area growth requires its own comparable basis and parameters. Forecasts never become observed training ground truth.

## Verification evidence

These are recorded implementation results, not new tests run while authoring this handoff:

- `build/growth_calculator_20261003_02/tests_final.xml`: **92 passed**, covering the new calculator and existing compound/monthly tools.
- `build/growth_calculator_20261003_03/verification.json`: final-code 16-trajectory synthetic example; six successful CLI operations; 41 artifact hashes verified. Demo and blank-template commands also completed.
- `build/growth_calculator_20261003_03/completion_audit.json`: delivery evidence and file hashes.
- `build/growth_calculator_20261003_03/results/`: complete synthetic example outputs.
- `build/growth_calculator_20261003_03/update_cli/` and `evaluation_cli/`: exercised update/evaluation outputs. Their targets were generated for software verification and are explicitly **not independent validation**.
- `build/growth_calculator_20261003_03/real_t1_input_audit.json`: five known T1 candidates remain ineligible partial observations. No real monthly forecast was produced.

Tests cover origin preservation, moving attachments/event continuity, residual waits/stops, covariance/units, unavailable inputs, signed/wrapped directions, output/order reproducibility, decoding without RNG, association cases, failed likelihood support, re-anchoring without double growth, chronological split checks, hashes and optical ineligibility. Tests are evidence for those exercised cases, not proof of scientific accuracy or every possible input combination.

## Claude review priorities

1. **Compare code with the intended contract.** Identify implementation discrepancies independently of the delivery checklist. Separate software bugs from scientific model changes. Give file/function, concrete failing case, expected behavior and acceptance test.
2. **Review applicability and event semantics.** Assess distinguishable-leaf appearance versus initiation, unknown apical state, stopping, provided-axis scope and the explicit no-loss assumption. Do not infer growth habit solely from a dwarf label.
3. **Review the joint dynamics.** Assess lognormal/transformed waiting variables, shared effects/AR dependence, spatial conditioning, fixed stem directions, anchored saturation and rotation. A current snapshot cannot identify temporal rates or covariance.
4. **Specify parameter evidence and calibration.** For each adopted coefficient/distribution, state units, primary evidence, cultivar/environment limits, local measurement requirements and identifiability. Other-cultivar literature values are not validated local defaults.
5. **Review update limitations.** Assess the observation likelihood, association marginalization, finite support/ESS, width-profile re-anchoring limits and requirements for a fresh 30-day forecast after new measurements. Do not treat non-detection as death.
6. **Define useful independent validation.** Specify observation/visibility intervals, persistent identities, comparable area bases, plant-level chronological splits, proper scores plus coverage/sharpness and operational acceptance criteria at actual 7/14/21/30-day targets. Leave unsupported thresholds inactive.

Expected review output: one English handoff with a decision per reviewed component (`retain`, `revise`, or `unresolved`), evidence and transfer limits, then a prioritized Codex change list with exact fields/functions/units and tests. Do not write a replacement implementation in the review. Record unresolved scientific choices explicitly instead of filling plausible coefficients.

## Resume commands and scope

```powershell
python -X utf8 -m tools.compound_growth probabilistic --help
python -X utf8 -m tools.compound_growth probabilistic templates --out build/growth_review_inputs_new
python -X utf8 -m pytest tools/tests/test_probabilistic_compound_growth.py tools/tests/test_compound_growth.py tools/tests/test_monthly_growth.py -q
```

Use fresh build paths; inspect saved results before rerunning. Cultivar/dates, longitudinal records and future environmental settings were not supplied. Do not repeat searches for those already-confirmed absent inputs. Flow Matching, automatic fitting, physiology/carbon allocation, yield, canopy feedback and native light execution were not part of this delivery. Any separately authored calibration or FSP prompt is a separate scope, not evidence those features were implemented here. This handoff itself does not launch code, train models or send messages to another chat.
