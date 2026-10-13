# Growth and development equations: Claude review pack

Date: 2026-10-04. Prepared by Codex at the user's request.

## Work brief and scope

Request: collect the equations related to tomato growth and development in a separate, reviewable document for Claude. Describe current implementation, units, assumptions, evidence gaps and specific decisions needed.

This is a review artifact, not a new biological specification. No model, coefficient, configuration, observation or design document is changed by this work. No fitting, simulation, remote execution or cross-project integration is authorized by this document. Validation consists of comparison with current source and checking referenced local files/functions; it does not establish biological accuracy.

## Instructions to Claude

Review this pack against the current implementation and original literature. For each equation group, return **retain / revise / unresolved**, with the exact proposed equation, units, domain, parameter evidence and validation data. Distinguish a faithful transcription from an appropriate model for the target dwarf tomato cultivar. Do not infer biological acceptance from passing synthetic software tests.

Preserve the current decisions unless the user explicitly changes them:

- P1 supplies observed structure and measurement support. Per-photo projected ratios and generated RGB views are not accepted physical leaf area or optical surfaces.
- P2 supplies light quantities and their spatial, temporal and directional provenance.
- P3 is the sole owner of realized growth, developmental events and predicted geometry.
- P4 is a read-only carbon diagnostic. It must not scale growth, move organs, reject trajectories or alter P3 probabilities.
- Frozen, hashed calibration packs are applied explicitly before a P3 run. No implicit runtime fitting.
- P3 temperature affects the development clock; fixed whole-plant DLI affects permitted size targets. No direct light-driven orientation law is implemented.
- Integration remains deferred. Future optical geometry and interval-to-interval reserve propagation are not delivered capabilities.

Primary implementation references:

- [P3 calculator](../tools/probabilistic_compound_growth.py), especially `beta_shape`, `normalized_temperature_clock`, `_size_response`, `_draw`, `_decode_block`, `_trajectory`, `_remaining`, `update_forecast`.
- [P3 guide](../tools/PROBABILISTIC_COMPOUND_GROWTH.md).
- [Calibration](../tools/growth_calibration.py), especially `_prediction`, `_event_log_probability`, `_loss`, `apply_parameter_set`.
- [P4 calculator](../tools/fsp_carbon_diagnostic.py), especially `compute_leaf_exchange`, `compute_respiration`, `infer_structural_demand`, `_budget`, `compute_carbon_sufficiency`, `audit_carbon_balance`.
- [P4 guide](../tools/FSP_CARBON_DIAGNOSTIC.md).
- [P2 interface](../tools/LIGHT_GROWTH_BRIDGE.md) and [directional contract](../tools/DIRECT_ANGULAR_CONTRACT.md).
- [Four-project review](CODEX_FOUR_PROJECT_DELIVERY_REVIEW_2026-10-04.md).

## 1. Units and meanings to preserve

| Symbol | Meaning | Unit / basis |
|---|---|---|
| t | Elapsed calendar time | day; 86,400 seconds per day |
| a(t), u | Accumulated development time, organ elapsed development age | development day; not degree-day |
| x, L, w | Organ length, rachis arc length, side extent | mm |
| A | Supported leaf area | P3: cm2; P4: m2; multiply by 1e-4 |
| phi, beta, omega | Azimuth, elevation, rotation vector | radians in equations; honor each serialized field's declared unit |
| I | PPFD at a tissue patch | umol photon m-2 s-1; incident or absorbed must be explicit |
| DLI | Daily light integral | mol photon m-2 day-1; explicit support and basis |
| H, Rd | Leaf CO2 exchange rate density | umol CO2 m-2 s-1, one-sided tissue-area basis |
| W | Structural dry mass | g structural DM; excludes nonstructural reserve |
| S, R, D, V | Carbon supply, respiration, demand, available carbon over one interval | g C per interval, not g CO2 or g carbohydrate |
| chi | Carbon fraction of carbohydrate equivalent | 12.011 / 30.026 g C per g CH2O |
| k | Growth/rotation rate parameter | development day-1 in P3; calendar day-1 in calendar calibration |

The implemented physiology uses a **carbon budget**, not an ATP or joule budget. A conversion to energy would need a separately specified model. Do not rename carbon as energy or interchange g C, g CO2, g CH2O and g DM.

## 2. Light inputs supporting growth review

### L01 — Daily light integral

Implemented supporting light reduction:

`DLI = 1e-6 * sum_j(I_j * delta_t_j_seconds)`

Daily outputs require complete declared local-day coverage. Missing intervals are not darkness. A fixed 16-hour photoperiod alone does not supply PPFD, actual clock windows or absorbed light.

**Review:** P2 tissue/region DLI and P3 fixed whole-plant DLI need an explicit spatial reduction, horizon rule and matching `basis_id`. Incident and absorbed calibration coefficients are not interchangeable. A daily mean alone does not reproduce nonlinear, time-resolved photosynthesis.

### L02 — Directional light moments

For weighted light contributions q, with one-sided area A_q, PPFD contribution I_q and unit direction v_q:

`F = sum_q(A_q I_q)`

`M = sum_q(A_q I_q v_q)`

`B = sum_q(A_q I_q v_q v_q^T)`

F, M components and B components have units umol photon s-1. The exported convention points **receiver to emitter**, opposite photon travel. Opposing light can produce M near zero even when F is positive; a dominant direction can therefore be unavailable.

**Review:** These are exposure descriptors, not a phototropism equation. Do not set the future leaf direction equal to M/|M| without a separately justified response law, response time, organ-age dependence and validation.

## 3. P3 size, shape and developmental equations

### G01 — Development clock

Implemented calendar clock: `a(t) = t`.

For contiguous constant-multiplier intervals:

`a(t) = sum_j m_j * max(0, min(t, end_j) - start_j)`

The normalized temperature helper builds piecewise-linear knots corresponding to:

`m(T) = clip((T - T_base) / (T_ref - T_base), 0, m_max)`

Require `T_base < T_ref <= upper_knot`, `m_max >= 1`, and `m(T_ref)=1`. The helper's supported temperature interval begins at T_base; temperatures outside declared knots are rejected rather than extrapolated. Thus the algebraic zero below T_base is **not** an implemented permission to run below that knot. There is no descending high-temperature stress branch.

**Review:** assess the normalization, temperature domain and plateau. Calendar-fit parameters cannot be relabelled as development-time parameters. Current non-calendar use needs explicit evidence-bearing fixed-setpoint/calendar-day calibration reference; a fluctuating-temperature mean is insufficient. Temperature also changes the timing of rotations and events through this clock.

### G02 — Existing-organ remaining expansion

`h(k,u) = 1 - exp(-k * max(0,u))`

`x(u) = x_0 + D_eff * h(k,u)`

Used for supported length, area and segment growth coordinates. x_0 is the observed origin, D_eff the remaining increment in the same unit, and k a reciprocal development-day rate. Existing organs with unknown biological age are anchored at elapsed origin time; this is not an estimate of their true age.

For side s and width station j:

`w_sj(u) = w_sj,0 + (w_s,target - w_sj,0) * f_DLI * h(k_width,u)`

The side target is an **absolute extent**, not an increment. A target below the starting station permits narrowing if the effective result remains valid. Missing supported parameters remain unavailable.

**Review:** can remaining increment and rate be identified from the available observation span? Are narrowing and common side targets biologically and geometrically appropriate? Leaf area is a separate coordinate; it is not automatically constrained by length, width or future envelope area.

### G03 — Optional beta expansion for newborn organs

For `0 < a_m < a_e`, define:

`g(u) = 0`, at u=0;

`g(u) = [1 + (a_e-u)/(a_e-a_m)] * (u/a_e)^[a_e/(a_e-a_m)]`, for 0<u<a_e;

`g(u) = 1`, for u>=a_e.

`x(u) = x_birth + (x_max,eff - x_birth) * g(u)`

a_m and a_e are development days; x_max,eff and x_birth use the trait's mm or cm2 unit. Require x_max,eff >= x_birth. Each coordinate supplies a_m or a_m/a_e explicitly. This is opt-in for newborns; existing age-unknown organs keep the remaining-expansion model. The default newborn model remains exponential unless beta is selected.

After an observation reanchor at age u_a:

`x_new(v) = x_observed + (x_max,eff - x_original_birth) * [g(u_a+v)-g(u_a)]`

The original developmental age persists. **Review:** the observation correction shifts the endpoint relative to the original absolute asymptote. Decide whether this is the intended residual-growth interpretation; do not silently restart the beta curve or force a new target. Current calibration does not fit a beta family.

### G04 — Fixed DLI size response

`z_DLI = (DLI - center) / scale`, with scale>0 in the same DLI unit.

`f_DLI = exp(c_DLI * z_DLI)`

Current `_size_response` multiplies `D_*` increments and `*_x_max_*` absolute beta targets by f_DLI. Exponential width targets use the residual-target formula in G02. c_DLI is dimensionless.

DLI is fixed for the forecast horizon with whole-plant scope and declared basis. It does not directly modify k, orientation coefficients, waiting times or the node budget. CO2, RH, VPD, EC and pH have no P3 response coefficients under the current decision.

**Review:** establish the DLI definition, calibration domain and uncertainty. The exponential response is unbounded; low-DLI beta targets may fall below birth size and be rejected. Multiplying an absolute beta maximum differs from multiplying remaining expansion. Review that distinction explicitly rather than describing all paths as one size multiplier.

### G05 — Shared plant variation and serial organ dependence

For a selected frozen parameter particle:

`b ~ Normal(0, Sigma_plant)`

`epsilon_0 ~ Normal(0, Q_0)`

`epsilon_r = rho * epsilon_(r-1) + eta_r`, where `eta_r ~ Normal(0,Q_innovation)` and |rho|<1.

`z_r = mu_family + B_family * f_standardized + b + epsilon_r`

Declared coordinate transforms include identity, `x=x_ref*exp(z)`, bounded logistic `x=l+(u-l)/(1+exp(-z))`, and elevation `(pi/2)*tanh(z)`. Latent scales and all covariance matrices belong to the parameter definition; explicit zero covariance is a deterministic assumption.

**Review:** identify data support for each conditional effect, covariance and serial dependence. Preserve full covariance and explicit missing-feature behavior. This is a distribution over trajectories, not fresh independent daily noise. Do not introduce a scalar vigour surrogate or unsupported environmental features.

### G06 — Birth direction, rotation and shape transport

Birth direction in a local frame Q:

`d_local = (cos(beta)cos(phi), cos(beta)sin(phi), sin(beta))`

`d_board = Q * d_local`

Azimuth is absolute or predecessor-relative according to the declared model; no universal phyllotactic angle is supplied.

For subsequent motion:

`r(u) = omega_infinity * h(k_rotation,u)`

`R_board(u) = Q * Exp([r(u)]_cross) * Q^T`

`d(u) = R_board(u) * d_0`

`p_j(u) = attachment(u) + [L(u)/L_0] * R_board(u) * (p_j,0 - p_0,0)`

Exp is the rotation-matrix exponential represented in code by a rotation vector. Stem nodes accumulate fixed segment directions e_h and variable lengths: `P_j(u)=P_base+sum_(h<=j) e_h*l_h(u)`. Attachments follow declared material/node locations. Newly extended terminal segments inherit the last segment direction.

**Review:** distinguish persistent growth rotation from reversible posture changes. This is whole-rachis scaling/rotation, not differential bending, mechanical equilibrium, gravitropism or light-seeking behavior. Predicted compound envelopes remain ineligible for optical PPFD calculations.

### G07 — Appearance times, node budget and determinacy

Positive waiting-time coordinate:

`delta_a = w_ref * exp(z_wait)`

Event development times accumulate waits and are converted back through the clock. The first residual wait and later inter-event waits use distinct families.

Given declared PMF pi_n and observed cumulative main-axis leaf count n_obs:

`Pr(N_max=n | n>=n_obs) = pi_n / sum_(m>=n_obs) pi_m`, for n>=n_obs.

Draw N_max once per trajectory/main axis. Zero admissible probability is unavailable. Observed cumulative rank is not the number of visible leaves.

With first truss rank r_0 and declared leaf interval q, a truss event occurs at a new leaf rank r satisfying `r>=r_0` and `(r-r_0) mod q=0`. The terminal event coincides with the final allowed leaf; if the budget is already reached at origin, terminal time is zero. Truss/terminal geometry is null.

**Review:** identify what the observed truss event means: emergence, visible bud, anthesis and fruit set are different observations. Current events supply no reproductive mass. No sympodial continuation is modeled; post-terminal whole-plant coverage is unavailable under current scope rules. A known-age retention-limit flag is not a senescence or abscission model.

### G08 — Observation conditioning and continuation

For Gaussian measurement residual e with declared covariance Sigma:

`log L = -0.5 * [n log(2*pi) + log(det(Sigma)) + e^T Sigma^-1 e]`

Ambiguous association uses `L=sum_c pi_c L_c`. Confirmed event evidence imposes admissibility on the existing trajectory bank.

`weight_i,new = weight_i,old * L_i / sum_j(weight_j,old * L_j)`

`ESS = 1 / sum_i(weight_i,new^2)`

All-zero support is incompatible; it is not replaced with uniform weights. Unsupported observation likelihoods do not constitute parameter learning. Continuation preserves the remaining original forecast horizon.

For exponential reanchoring: `D_remaining = D_old * exp(-k*u_anchor)`. Rotation amplitude uses the analogous remaining factor. Width reanchoring preserves station-specific remaining residuals; incompatible scalar target representation is unavailable, not averaged. Beta reanchoring is G03.

**Review:** repeated observations require a defensible measurement-error and dependence model. Track identity ambiguity and correlated measurement errors; assess whether finite-bank ESS is adequate before interpreting narrowed intervals as increased biological certainty.

## 4. P4 carbon diagnostic equations

### C01 — Nonrectangular-hyperbola leaf exchange

First sum simultaneous fixtures at the same patch and time: `I=sum_fixture I_fixture`.

The implemented stable form is:

`H(I) = 2*alpha*I*Pmax / [alpha*I + Pmax + sqrt((alpha*I-Pmax)^2 + 4*(1-theta)*alpha*I*Pmax)]`

At I=0, H=0. Require alpha>0, Pmax>0 and 0<theta<=1. alpha has units umol CO2 per umol photon; Pmax and H have units umol CO2 m-2 s-1; theta is dimensionless.

`S = 12.011e-6 * sum_patch,time [(H(I)-Rd_owned) * A_patch_m2 * delta_t_seconds]`

In `before_mito` mode Rd_owned=0 and maintenance is charged downstream. In `net_leaf` mode use explicit day/night Rd and assign the corresponding leaf maintenance to leaf exchange so it is not deducted again. Preserve signed nighttime exchange. Do not use a curve that already includes growth respiration while also charging full ASR demand.

**Review:** resolve whether the source curve represents exchange before mitochondrial respiration or net leaf exchange, how photorespiration is represented, incident/absorbed PPFD, and one-sided area with illumination from both faces. The internal variable name `gross` does not resolve these physiological meanings. Current alpha/Pmax/theta are pack constants; environment domain checking is not a temperature/CO2/VPD response function. Current light support is fixed observed tissue, not future P3 optical tissue.

### C02 — Maintenance respiration

For organ o and covered intervals j:

`R_maint,o = chi * sum_j [m_o * W_o,j * Q10_o^((T_o,j-Tref_o)/10) * activity_o,j * delta_t_j_seconds/86400]`

m_o: g CH2O per g structural DM per calendar day at Tref. W: g structural DM. T and Tref: deg C. Q10 and activity: dimensionless. R: g C. Charge only compartments not already owned by leaf exchange.

Use supported mass history or an explicit starting-mass approximation. Use the declared organ temperature; substituting air for leaf temperature must be labelled.

Optional implemented activity:

`RGR5 = log(W_now/W_5days_ago) / 5`, in calendar day-1;

`activity = 1 - exp(-f_days * RGR5)`.

Requires positive masses and complete supported five-calendar-day history. Negative RGR is unsupported. Otherwise use an explicitly declared constant activity in [0,1].

**Review:** RGR5=0 gives zero activity and therefore zero modeled maintenance. Assess that implication and the physiological meaning of this factor before acceptance. Do not quietly impose a basal floor. Check carbohydrate-versus-CO2 source units and organ mass basis.

### C03 — Recover structural mass change from supported form

Supported direct endpoint masses are usable with explicit evidence. Otherwise current anchored inverses use known initial structural mass W_0.

Area path, blade compartment only:

`A_1-A_0 = SLA_1*W_1 - SLA_0*W_0`

`W_1 = (A_1-A_0 + SLA_0*W_0) / SLA_1`

A in m2; SLA in m2 per g structural blade DM. Convert supported P3 cm2 first. This is an anchored increment mapping; it does not establish that the absolute origin satisfies A_0=SLA_0 W_0.

Dimension path:

`h(W) = lambda * (1000*W)^gamma`

`W_1 = [(x_1-x_0+h(W_0))/lambda]^(1/gamma) / 1000`

x is mm, W is g structural DM, lambda is mm per mg^gamma, gamma>0. Multiple independently supplied inverses must agree within declared tolerance; disagreement is unavailable, not averaged.

**Review:** obtain organ/compartment-specific initial masses and mappings. Do not apply blade SLA to whole compound-leaf mass or whole-plant mass. Confirm scalar dimension extraction from P3 arrays before any adapter. Negative mass change is not a remobilization credit. New organs require zero initial mass plus accounted birth material; pre-existing bud transfer needs a separate stock ledger.

### C04 — Structural carbon, growth demand and growth respiration

`delta_W_o = W_o,1-W_o,0 >= 0`

`C_struct,o = c_o * delta_W_o`

`D_o = chi * ASR_o * delta_W_o`

`R_growth,required,o = D_o - C_struct,o`

ASR: g CH2O required per g structural DM produced. c: g C per g structural DM. Require `0<c_o<=min(1,chi*ASR_o)`. Total D is the sum over the declared organ scope.

**Review:** verify source convention and organ mapping. Here growth respiration is already contained in D: subtracting R_growth again from available carbon before comparing with D would double-charge it. Required demand is a diagnostic of P3 growth, not funded realized growth or an allocation rule. Whole-plant claims need root and reproductive compartments; event labels alone do not supply them.

### C05 — Available carbon and sufficiency

`U = reserve_start + S + import - export - R_maint,charged`

If U<0: `maintenance_deficit=max(-U,0)`; available growth carbon V and sufficiency ratio are null.

Otherwise: `V=max(U-minimum_reserve,0)`.

For D>0: `ratio=V/D`, `growth_deficit=max(D-V,0)`.

For D=0: ratio is null with `no_growth_demand`.

The implemented sufficiency comparison allows an explicitly declared numerical tolerance:

`V + abs_tol + rel_tol*max(abs(V),abs(D)) >= D`.

The raw ratio remains reported. Missing required components make the combined diagnostic unavailable, even when individual components are available.

**Review:** a supported-leaf subset needs an explicit reserve/transfer boundary policy. Initial reserve is a stock and cannot be independently spent again in every interval to claim a conserved simulation. There is currently no propagated reserve state. Retain P4 photosynthesis even when P3 has a DLI response; double-counting is avoided by forbidding diagnostic feedback, not by deleting diagnostic supply.

### C06 — Hypothetical funded conservation audit

`delta_reserve + C_struct = S - R_maint,charged - R_growth + import - export`

The audit requires an explicitly hypothetical, funded ledger with nonnegative end reserve and a declared tolerance. It does not create a next state or fund unfunded P3 growth.

**Review:** check scope, interval boundaries and whether all transfers belong in the ledger. This is a conservation identity, not evidence that the model predicts a real plant accurately.

## 5. Calibration equations and binding risks

### K01 — Currently supported fit families

Anchored expansion uses `x(t)=x_initial+D*(1-exp(-k*t))` on **calendar days**. Azimuth rotation uses the analogous angular increment and wrapped residual `atan2(sin(delta),cos(delta))` with von Mises likelihood.

For a lognormal wait, `scale=w_ref*exp(mu)`, sigma is dimensionless. With stop probability p_stop:

`Pr(l<T<=u)=(1-p_stop)*[F_lognormal(u)-F_lognormal(l)]`

`Pr(T>l)=p_stop+(1-p_stop)*[1-F_lognormal(l)]`.

The stop mixture belongs to that fit family; it cannot silently replace the current N_max budget decision. No beta fitter is currently supplied.

**Review:** match likelihood to interval-censored appearance events and distinguish observed absence from no observation. Validate fitted time units, trait identity, initial anchors and physical meanings before applying a pack.

### K02 — Same units do not imply equivalent parameters

The generic `apply_parameter_set` adapter checks declared units, but those alone do not distinguish a fitted width increment D_mm from an absolute side target in mm. A valid conversion would additionally require the correct anchor, station representation, light-response handling and an approved mapping.

**Requested decision:** require semantic role compatibility or reject the binding unless a reviewed explicit conversion exists. This document records the gap; it does not implement a conversion or claim an invalid delivered forecast was reproduced.

## 6. Parameter and observation checklist for review

For every adopted parameter, require an ID, equation/semantic role, value or distribution, unit, organ/compartment, cultivar, stage, environment domain, exact source locator, evidence kind, uncertainty and calibration/evaluation separation. Unknown values remain unavailable or explicitly hypothetical; do not insert literature defaults.

| Group | Parameters needing evidence | Measurements useful for review/fitting |
|---|---|---|
| Clock | T_base, T_ref, m_max, supported temperature domain | Time-stamped temperature and dated developmental events across conditions |
| Expansion | D, k; beta x_max, a_m, a_e; side targets | Repeated same-organ length, side extents, supported area, appearance dates and measurement uncertainty |
| DLI | center, scale, c_DLI, basis and reduction | Comparable plants under measured DLI treatments with temperature and initial size controlled/recorded |
| Direction | Birth-angle distributions, rotation vectors/rates, covariance | Same-frame repeated organ directions and posture context; directional-light treatment data for any later response law |
| Determinacy | N_max PMF, first truss rank, spacing, wait distributions | Cumulative leaf/node ranks, truss definitions, terminal dates; censored observations preserved |
| Leaf exchange | alpha, Pmax, theta, Rd_day, Rd_night | Light-response and dark-exchange observations with leaf temperature, CO2 and area/light basis |
| Maintenance | m, Q10, Tref, activity/f_days, ownership | Organ-resolved structural mass, temperature and respiration evidence; five-day history for RGR5 |
| Mass/form | SLA, lambda, gamma, initial W | Matched geometry and destructive dry-mass samples by organ; structural/nonstructural distinction |
| Demand/stock | ASR, c, reserves, boundary transfers | Source-supported construction costs and carbon fractions; reserve measurements or labelled scenarios |

These are review inputs, not an approved experimental protocol. Claude should identify which coefficients are identifiable together, which need independent measurement, and which claims the available observations cannot support.

## 7. Evidence register and unresolved source reconciliation

Use the existing evidence records as locators, not as automatic adoption:

- [Growth calibration evidence](../tools/growth_calibration_evidence.json).
- [Earlier Science equation review](CLAUDE_GROWTH_EQUATION_REVIEW_FOR_CODEX_2026-10-03.md): includes proposals not adopted by later decisions.
- [Physiology source registry](../build/fsp_physiology_spec_20261003_01/source_registry.json).
- [Physiology equation registry](../build/fsp_physiology_spec_20261003_01/equation_registry.json).
- [Parameter candidates](../build/fsp_physiology_spec_20261003_01/parameter_candidates.json): candidates are not accepted target coefficients.
- [Current P4 handoff](CLAUDE_FSP_CURRENT_HANDOFF_2026-10-03.md) and [implementation delivery](CODEX_P4_IMPLEMENTATION_HANDOFF_2026-10-04.md).

The recorded dwarf-tomato paper locator is DOI `10.1093/insilicoplants/diaf024`; its cited model repository is `Micbut/FSP-model-dwarf-tomato`. Consult the registry's preserved source/version/page evidence before citing or adopting it. The source cultivar and growth conditions require applicability review for this project. This compilation did not independently re-verify the external literature.

Previously recorded reconciliation issues remain scientific review items: ASR multiply/divide conventions between paper and source implementation; maintenance units expressed as carbohydrate versus CO2; root/fruit coefficient ordering; and structural versus total dry-mass basis. Source equations, source-code versions and corrected interpretations must be recorded separately. The anchored inverses in C03 are implementation adaptations and must not be presented as independently validated merely because the underlying allometry appears in a paper.

## 8. Priority decisions and explicitly missing models

1. Resolve light/area/carbon/respiration semantics first: L01, C01-C04. These determine whether quantities can be combined at all.
2. Resolve clock compatibility and coefficient binding: G01, G04, K02. Keep absolute target and remaining increment distinct.
3. Review consistency of independent area, dimensions and mass: G02-G03, C03. Define the supported compartment and uncertainty before linking.
4. Review developmental scope and observation definitions: G07-G08. A truss event is not reproductive growth and terminal main-axis prediction is not continued whole-plant prediction.
5. Decide whether later extensions are justified by measurements. Currently missing: direct phototropism/light-driven reorientation, mechanistic bending, FvCB/CO2-stomatal coupling, water/nutrient stress, senescence/remobilization, reproductive/root allocation, future optical meshes and dynamic reserve propagation. Do not describe these as implemented or add equations by analogy without evidence.

## 9. Required Claude response

Return an English handoff suitable for a later Codex implementation request, with a Korean explanation for the user. Review only; do not silently change code or coefficients.

Use one row per equation group:

| ID | Retain / revise / unresolved | Exact equation and unit changes | Source equation/page/version | Required parameter evidence and domain | Required observations | Affected function and acceptance check |
|---|---|---|---|---|---|---|

Then provide:

1. A respiratory-accounting table assigning leaf exchange, leaf/stem/root/reproductive maintenance and growth respiration exactly once.
2. A parameter ledger distinguishing measured, fitted, literature candidate, explicit assumption and unavailable entries.
3. The smallest defensible set of equations for current data, and a separate list of extensions needing a new user decision.
4. Proposed software checks for units, boundary values, mass/carbon conservation and unavailable behavior; separate those from biological evaluation with held-out plants, times and treatments.
5. Specific implementation instructions only for decisions that are resolved, with file/function/input/output/unit references. Preserve unresolved items rather than inventing numbers.

## Completion record

Prepared a documentation-only equation inventory from the current source and local evidence records. Model code, model parameters, configurations and observations were not edited. Source/function and local-link verification is recorded in `build/growth_equation_review_20261004_01/verification.json`. No model tests, biological experiments, fitting or simulations were run for this compilation.
