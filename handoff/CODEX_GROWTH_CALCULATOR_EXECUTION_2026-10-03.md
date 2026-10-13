# Growth calculator execution brief

Request: implement CODEX_GROWTH_CALCULATOR_HANDOFF_2026-10-03.md as an extension of existing tools. Read the detailed proposed mathematics and IO contract; coefficients remain explicit assumptions, not scientifically reviewed defaults.

Inspected: tools/compound_growth.py provides strict observation loading, traits, baselines and CLI; tools/monthly_growth.py provides a separate manual scenario; tools/leaf_light/common.py provides hashes, strict build directories and IO. No probabilistic calculator exists. This workspace has no Git repository. Other ongoing work and protected files remain untouched.

Plan: add tools/probabilistic_compound_growth.py for the eight public functions, with a lazy entry point from the existing compound_growth CLI. Preserve current commands/viewers. Reuse observation checks and baseline functions. Implement concrete versioned parameter bindings for the specified latent Gaussian/AR family, analytic growth, material attachments, event scheduling, optional explicit developmental clock, summaries, updates, evaluation and immutable exports. Blank templates contain no biological defaults; synthetic fixtures are explicitly synthetic.

Requirement map: origin/availability -> measured adapter; distributions/events -> joint sampler; geometry -> analytic decoder; new observations -> finite-bank update; quality -> chronological evaluation with existing baselines; delivery -> CSV/JSON, CLI, documentation and focused tests. Flow Matching remains explicitly unavailable. External light/environment are metadata unless an explicit supported response contract is present. Do not execute image, light, native or training pipelines.

Validation: exact measured origin, moving attachments and continuity, residual waits/stops/multiple births, covariance and probabilities, missing fields and area basis, wrapped orientation, deterministic keys/output-independent decoding, update support failures/history/re-anchoring, chronological split gates, export optical ineligibility. Run focused existing/new tests and one bounded synthetic CLI demonstration under a fresh build directory; preserve known absent real inputs rather than search again.

Results will be appended after implementation. This brief authorizes no changes outside tools/, tools/tests/, generated build output and shared handoff logs.

## Delivered implementation and verification

Implemented the eight requested public functions in `tools/probabilistic_compound_growth.py` and a lazy `probabilistic` subcommand in the existing `tools/compound_growth.py`. Existing commands and viewers retain their behavior. Documentation: `tools/PROBABILISTIC_COMPOUND_GROWTH.md`. Focused new tests: `tools/tests/test_probabilistic_compound_growth.py`.

Run from the project root:

```powershell
python -X utf8 -m tools.compound_growth probabilistic --help
python -X utf8 -m tools.compound_growth probabilistic templates --out build/growth_inputs_next
python -X utf8 -m tools.compound_growth probabilistic demo --out build/growth_demo_next
python -X utf8 -m pytest tools/tests/test_probabilistic_compound_growth.py tools/tests/test_compound_growth.py tools/tests/test_monthly_growth.py -q
```

Use the documentation's `audit`, `forecast`, `decode`, `summarize`, `update` and `evaluate` commands with explicit paths and fresh output folders. Blank templates leave biological parameters and tolerances null. The synthetic demo is a software example, not a dwarf-tomato coefficient recommendation.

Final test result: **92 passed**. Evidence: `build/growth_calculator_20261003_02/tests_final.xml`. The final-code demonstration and command verification are in `build/growth_calculator_20261003_03/`: 16 valid synthetic trajectories, six successful CLI operations, 41 output hashes checked, and current source hashes matching the run manifest. The demo and blank-template commands also completed. `verification.json` records exact commands and explicitly identifies synthetic targets derived from a sample, so they are not independent validation.

### Requirement completion audit

| Requirement | Implemented behavior and inspected evidence |
| --- | --- |
| Add to the existing program | Existing `compound_growth` CLI delegates to one new calculation module; legacy/new combined suite passes. No second observation extractor or UI. |
| Eight public functions | All named signatures are implemented; adapter, sampling, query, summaries, update, evaluation and export have direct tests and CLI exercises. |
| Origin and input integrity | Existing hash/frame/identity checks reused; exact day-zero curved axes/extents preserved; projection offsets retained. Tests cover frame/hash errors and unavailable projection tolerance. |
| Explicit parameter evidence | Versioned schemas, unit/coordinate order, positive-semidefinite covariance, weights, transforms and evidence checks; blank parameters and disabled FM produce unavailable results. |
| Stochastic events and joint samples | Distinct residual/inter-event families, stop probability/conditional logit, plant-shared effects and AR residuals; covariance/conditioning, multiple within-day births and resource exhaustion tested. |
| Existing/future growth and parent motion | Anchored saturation, smooth rotation, material-segment elongation, continued old terminal growth and newly appended terminal. Exact origin, moving attachments and event continuity tested. |
| Independent component availability | Event forecasts continue without measured spatial geometry; unavailable axes/area/rates stay null with reasons. No fabricated stem or length-times-width tissue area. |
| Environment/light | Explicit calendar, piecewise development schedule or one declared piecewise-linear response. Units/domains checked; external fixed-light feature provenance required. No default response product, optics or light execution. |
| Reproducibility | Stable SHA256/PCG64 streams, shared draws, analytic decoder; reordered axes, independently ordered trajectory generation and output schedules tested. Decoder succeeds with RNG disabled. |
| Outputs | Required CSV/JSON tables plus source shapes/parameters, occurrence/count/geometry summaries and manifest. Missing CSV cells are empty; stopped event time is null. Hashes and optical-ineligible outputs checked. |
| Observation updates | Confirmed, ambiguous, missed/occluded and unmatched cases; likelihood marginalization, finite-bank weights/ESS, zero-support failure, immutable prior and remaining-growth re-anchoring tested. |
| Evaluation | Chronological plant-group gates, count/occurrence/event/scalar/vector metrics, missingness and existing persistence/recent-change baselines. Explicit target times only; real accuracy remains unvalidated. |
| CLI/templates/documentation | Help, blank templates and all calculation subcommands verified. Detailed schema/parameter/response/update/evaluation usage is documented. |
| Real supplied data | Re-audited the exact known T1 snapshot without searching for absent records. Five candidates remain partial observations, none eligible for a real growth forecast. Source hashes preserved. |
| Scope | No protected core/config/measurement changes, new image analysis, canopy integration, light run, UI or training. Scientific coefficients were not fitted or imported from unrelated cultivars. |

### Explicit limitations and decisions

- The module implements the proposed mathematical contract as assumption-conditioned software. Claude scientific review, fitted response coefficients and independent 7/14/21/30-day validation remain separate evidence dependencies.
- `numeric_tolerances.absolute` implements the detailed schema's tolerance object; scalar `numeric_tolerance` is a documented compatibility alias. Conflicting values fail. Structural/table details and family bindings that were only schematic in the design are made explicit in the module documentation, without introducing biological coefficients.
- An update returns the remaining original-horizon trajectory bank and a new measured block origin. It does not fabricate another 30 days of unsupported events or treat an old/predicted stem as newly measured. A new full-horizon forecast needs explicit new-origin parameters and parent evidence; continuation-only configurations cannot silently restart it.
- Fixed-light response is a declared scenario. There is no recalculated future shading or implicit photosynthesis. Without a response contract, coupling remains unavailable.
- Future envelopes remain optical-ineligible and generated predictions cannot become observed training truth. Failed samples and unsupported target/association fields remain visible in weights, reasons and evaluation denominators.

Software delivery is complete for the named handoff. The current real plant's next month has not been validated or claimed as predicted.
