# P3 growth calculator continuation prompt

Target chat: **생장방향**

Date: 2026-10-03. This is a paste-ready continuation prompt for the named project chat.

Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.
All paths below are relative to this root unless stated otherwise.

Read the parent `공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, the last five lines of `handoff/LOG.md`, and `handoff/TODO.md` first. Create an English work brief before implementation. Respect file ownership and active OneDrive edits: Codex owns `tools/` and `tools/tests/`; protected core changes belong to Claude Code. Do not edit human configuration, observations or `docs/`. Record specification conflicts for Claude rather than inventing a scientific decision.

Read [the integration decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), including D1-D10. The latest explicit decisions take precedence over older proposals; the Science review was not adopted in full. Inspect current source and execution records before repeating work.

Shared boundaries:
- P3 owns realized growth increments and future geometry. P4 is a read-only carbon diagnostic at runtime.
- Cross-project linking remains deferred under D3. Continue this project's own work; do not launch an end-to-end pipeline.
- An explicitly selected, frozen and hashed calibration pack may be applied before P3 runs under D5; never fit or apply it implicitly at runtime.
- The first later synthetic pass requires numerical P1-P2-P3 results. P4 may be unavailable with reasons under D6.
- Round-trip checks apply to reversible units, frames, IDs and representations. Light transport, aggregation, photosynthesis and forecasting require forward correctness checks, not inversion.
- Preserve source samples, complete shapes, identity, uncertainty, missingness and provenance. Follow each producer's actual missing-value contract rather than replacing unknown values with zero.

Continue work already authorized in this chat. A missing prerequisite should block only dependent work. Do not treat this prompt as permission for new private-data uploads, paid services, training or cross-chat messaging. Finish with an English handoff and a Korean explanation, distinguishing implemented software, synthetic evidence, scientific assumptions and remaining dependencies.

## Objective and source documents

Implement the adopted P3 internal changes D8-D10 within the existing calculator after completing the required source review. P3 remains the sole producer of realized size and direction trajectories.

Read:
- [Science equation review](CLAUDE_GROWTH_EQUATION_REVIEW_FOR_CODEX_2026-10-03.md).
- [D8-D10 implementation handoff](CODEX_P3_GROWTH_DECISIONS_IMPLEMENTATION_HANDOFF_2026-10-03.md).
- [Current calculator review handoff](CLAUDE_GROWTH_CALCULATOR_REVIEW_HANDOFF_2026-10-03.md).

Use the implementation handoff for exact fields and equations. First verify its nine reported code/document discrepancies. Work primarily in `tools/probabilistic_compound_growth.py`, the existing `tools/compound_growth.py` delegation, narrowly necessary `tools/growth_calibration.py` bindings and associated `tools/tests/`. Coordinate shared calibration-file edits with its active owner.

## D8 scope

- Keep existing organs on x0 + D*(1-exp(-k*a)). Retain sampled remaining increment D and existing covariance structures.
- Add opt-in `determinate_beta` for organs born within the horizon. Preserve birth geometry through x_birth + (x_max-x_birth)*beta_shape(alpha), with 0 < a_m < a_e.
- Reject invalid order, nonfinite parameters or x_max below x_birth; preserve the endpoint and monotonicity requirements.
- Do not adopt the Science proposal's log-x_inf reparameterization, rank-law/scalar-vigour replacement, covariance simplification or other unselected structural changes.
- Do not bind exponential fitted parameters to beta coordinates. Unsupported calibration bindings must fail explicitly.

## D9 scope

- Temperature enters the development clock only, through the declared piecewise-linear response normalized to 1 at T_ref. No undeclared T_base, m_max or extrapolation.
- DLI enters size targets only and is fixed over the horizon:
  - Existing organs: D_eff = D * exp(c_DLI*z(DLI)).
  - Newborn beta organs: x_max_eff = x_max * exp(c_DLI*z(DLI)).
- Require the declared DLI basis, scope, centre, scale, coefficient and provenance. Check validity after the response as well, including x_max_eff >= x_birth.
- DLI must not affect direction, the clock, event timing or stopping in the D9 profile. Temperature must not enter other coefficients. CO2, VPD, RH, EC and pH remain metadata rather than P3 drivers. Audit aliases and indirect feature paths.
- Add `p3_light_coupling` and `p3_environment_paths` as specified. Inspect the full frozen configuration, family features, stop features, clock, light response and calibrated-pack provenance. Derive legacy environment/light-used flags from that audit rather than the clock alone.
- Keep legacy behavior available as required by the handoff, but never label a nonconforming legacy configuration D9-compliant.

## D10 scope

- Draw one N_max per trajectory/main axis from a declared PMF. Remove probability mass below the observed node count and renormalize; no remaining mass means unavailable.
- Reject simultaneous node-budget and free stopping rules. Record the draw and use the existing finite-bank observation reweighting without resampling.
- Support `event_kind` leaf, truss and terminal. Truss and terminal have null geometry and never create optical surfaces. Truss placement requires its declared rule.
- At terminal, report `post_termination_scope=unavailable` with the specified reason. Preserve the supported main-axis count; do not report zero future whole-plant growth as a prediction.
- Retain the no-loss assumption. Add only the specified optional age-limit violation flag, not an unadopted senescence model.

## Contract checks before dependent edits

Record unresolved specification conflicts for Claude and continue unaffected work. In particular:
- Strict byte-identical legacy files conflict with requiring new fields in every output; obtain or reuse an explicit versioning/output policy rather than silently redefining compatibility.
- Clock normalization at one setpoint does not establish equivalence for arbitrary fluctuating calibration histories. Check the fitted pack's actual time/environment assumptions before accepting a clock conversion.
- The Science review's `asymptote_dli` proposal was superseded by `size_target_dli`; do not export both as interchangeable meanings.
- Preserve the explicit P3 angle and missingness contract; document boundary conversions where it differs from other projects.

## Validation and delivery

Run the implementation handoff's focused tests for legacy behavior, beta birth/endpoints, temperature normalization, forbidden environment paths, complete dependency audit, PMF truncation, null-geometry events, termination summaries and reweighting. Preserve measured day-zero geometry and future optical restrictions.

Use fresh `build/` outputs, JUnit results and hashes. Deliver or append the designated English execution report without overwriting another owner's work. List unresolved decisions and assumption-only parameters explicitly. Do not run cross-project integration, automatically fit real parameters, or claim that synthetic tests validate monthly biological forecasts.

