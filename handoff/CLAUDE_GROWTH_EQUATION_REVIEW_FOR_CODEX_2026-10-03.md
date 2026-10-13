# P3 growth equation review (Claude Science) — handoff for Codex

Date: 2026-10-03, Asia/Seoul. Source: Claude Science response to `handoff/CLAUDE_SCIENCE_GROWTH_EQUATION_REVIEW_PROMPT_2026-10-03.md`. Consolidated by Claude for Codex.
Status: **proposal under review.** Three user decisions (section 6) are still open. Do not implement until they are recorded. This document authorizes code inspection and review only.

Tags: **[LIT]** verified from an accessed source; **[DP]** design proposal; **[OA]** open assumption.
Constraints in force: D1 (P3 owns realized increments), D2 (P4 diagnostic only), D5 (frozen calibration pack applied before P3), D6 (P4 numeric optional in first pass), D7 (reversible conversions round-trip; computations correctness-checked). See `CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md`.

## 1 Discrepancies between the prompt summary and the code/docs

Codex: confirm each against current source and correct if wrong.

| # | Prompt summary | Files say (per Claude Science) | Consequence |
|---|---|---|---|
| 1 | k in 1/development-day | Engine yes; calibration `anchored_expansion` k is 1/calendar_day; calibrated forecast must use calendar clock | Anything fitted now is calendar-only. Thermal clock is blocked at the fitter/engine boundary. |
| 2 | Direction = local rotation vector | Engine has `rotation_x/y/z_rad`; fitter only `azimuth_rotation` (scalar, von Mises) | Initial direction and 3D bending are assumption-only. |
| 3 | Width = left/right targets | "A scalar width increment must not be bound directly to an absolute target width" | Width cannot receive a fitted value without a new conversion. |
| 4 | Plant covariance, rho, innovation covariance | `lognormal_wait` binding rejects unfitted conditional/shared/serial/cross-trait dependence | These are declared assumptions only. |
| 5 | `D_segment_mm`, `k_segment` | `segment_families` keyed by material segment ID | ~2 free parameters per segment (~20 for 10 nodes). |
| 6 | — | `topology_scope = provided_axes`; no initiation of unobserved lateral axes | Sympodial continuation after apex termination cannot be produced. |
| 7 | — | `leaf_retention_assumption = no_loss_over_horizon` | No senescence/abscission. |
| 8 | — | Grammar symbols only Plant, Axis, Apex, CompoundLeaf; area optional and independent | No truss symbol; no length×width→area link. |
| 9 | Butturini full text not recovered | `tools/growth_calibration_evidence.json` supersedes the spec: PDF recovered, cultivar Heartbreakers F1 Twiggy Red, equations located | Spec evidence register is stale; evidence file is authoritative. |

## 2 Verified literature facts used [LIT]

Butturini et al. 2026, in silico Plants 8(1):diaf024, cv. Heartbreakers F1 Twiggy Red, vertical farm (cached PDF):
- Eq 1 p.3: `N_phytomers = floor(z1*t^2 + z2*t - z3)` for `t <= -z2/(2*z1)`, else `N_max`; t in °Cd. z1–z3 in uninspected supplement — **not verified, do not adopt**.
- Eq 3 p.3: `SLA = r1*rho + r2` (rho = plants/m2). r1, r2 not verified.
- Eq 4 p.5: `D = lambda * w_str^gamma`; internode allometry fitted separately below/above rank 5. lambda, gamma not verified.
- Eq 12 (ref. p.10): beta growth function for potential growth of all organs.
- Table 1 p.5: T_base 5.7 °C; phyllotaxis 137°; beta_leaf 70°; beta_branch 30°; N_phytomers_max 10; N_side_max 4; internode t_m 228, t_e 513 °Cd; leaf rank>=2 t_m 271, t_e 464 °Cd, L:W 2; leaf rank 1 L:W 1; potential mass 111 mg (rank 1) vs 547 mg (rank>=2); truss t_e 400 °Cd; fruit delay 42.4 °Cd.
- p.11 assumptions: phyllotaxis 137° (golden angle); internode inclination random ±15° then fixed; leaves fall at PAR <= 2 umol/m2/s and age > 400 °Cd; equal leaflets per leaf; flat leaflets.
- p.9 conditions: 22/19 °C, 16 h, 230 umol/m2/s, 800 ppm CO2, EC 2, pH 5.5–6.5, LED 12/9/79/2 % B/G/R/FR.
- p.3: photoreceptor-driven morphology excluded.

Zeist et al. 2018, Pesq. Agropec. Bras. 53(3):307–315 (abstract only): node-emission T_base 4.5–14.8 °C across tomato germplasm. No per-genotype value accessed.

[DP] scale check: Butturini conditions give ~15.3 °Cd/day (confirmed by their DAT-42 cross-check ~15.4). So leaf t_e 464 °Cd ≈ 30 d, internode t_e ≈ 34 d, phyllochron ≈ 4–6 d. A 30-day horizon ≈ one full leaf expansion, 5–7 new leaves, and routinely crosses apex termination.

## 3 Process recommendations

| Process | Current | Recommendation | Status |
|---|---|---|---|
| Expansion, existing (age-unknown) organs | `x0 + D(1-exp(-k*a))` | KEEP (self-anchoring; logistic/Gompertz/beta need absolute age) | [DP] |
| Expansion, newborn organs | same exponential | ADD declared alternative `determinate_beta`; exponential stays default | [LIT] beta used by Butturini; [DP] application |
| Logistic/Gompertz | — | REJECT | [DP] |
| Thermal time | — | Clock reparameterization, not a curve family; decide separately | [DP] |
| D parameterization | remaining increment | MODIFY: sample `log x_inf`, derive `D = x_inf - x0`; reject particle if `x_inf < x0` (no clipping) | [DP] |
| Rank | none | ADD rank feature on `log x_inf` + juvenile-rank intercept (uses existing `order_index`) | [LIT] existence; [DP] form |
| Width | independent L/R targets | MODIFY: sum S and asymmetry A; `log S_inf` follows rank law; A small declared variance, no plant effect | [DP] |
| Area | independent | KEEP default; ADD optional `area_link=loglinear` | [LIT] no L×W precedent; [DP] link |
| Initial direction | conditional Gaussian az/el | MODIFY: circular prior on fitted divergence angle; 137.5° only as declared start with sensitivity band | [LIT] values are assumptions; [DP] |
| Persistent bending | 3-vector + k (4 dof/leaf) | MODIFY: two angles (elevation drift, azimuth drift); optional elevation coupled to `log L_inf` | [DP] |
| Transient posture | absent | ADD to **observation model only** (phase offset), never to state | [LIT] phase-specific angles; [DP] |
| Appearance wait | lognormal | KEEP; ADD rank term in location (gamma_w >= 0) | [LIT] deceleration Eq 1; [DP] |
| Stop rule | free stop prob/logit | REPLACE: node budget `N_max` drawn once per trajectory from declared pmf; stop at rank = N_max (expressible via steep rank `stop_logit`) | [LIT] hard cap; [DP] |
| Truss | none | ADD `event_kind ∈ {leaf, truss, terminal}`, null geometry | [LIT] positions; [DP] |
| Post-termination | silent | ADD `post_termination_scope = unavailable` | [DP] |
| Clock | calendar / piecewise | KEEP calendar for fitting; temperature as piecewise-linear response normalized to 1 at setpoint | [DP]; [LIT] T_base range forbids default |
| Light | one scalar feature | MODIFY: DLI only, on `log x_inf` only; never on clock or direction | [DP]; [LIT] exclusion precedent |
| CO2, VPD, EC, pH | declarable | EXCLUDE from P3 (belong to P4) | [LIT]+[DP] |
| Stem segments | per-segment (D,k) | REPLACE: rank law with break, single shared `k_s` | [LIT] rank break; [DP] |
| Fixed segment direction | assumed | KEEP; make falsifiable (along-axis vs perpendicular attachment error at 14/30 d) | [LIT] precedent; [DP] |
| Senescence | no loss | KEEP; flag violation when predicted leaf age exceeds declared limit | [LIT] rule; [DP] |
| Plant effect | full covariance | REPLACE: scalar vigour `v_plant ~ N(0, sigma_v^2)`, loading 1 on log-size, 0 on angles/rates | [DP] |
| Cross-trait covariance | full | REPLACE: one common factor + diagonal | [DP] |
| AR(1) rho | free | KEEP structure; bound rho ∈ [0, 0.6], default 0.3, sensitivity axis | [DP]; [OA] bound |

Net effect: fewer parameters (~30 population-level total instead of ~20 per stem + ~9 per leaf + full covariance).

## 4 Proposed minimal equation set [DP]

Notation: t calendar days from origin; `a(t) = ∫ m(T(u)) du` development days; `alpha = a - a_birth`; r rank; z(·) standardization with declared centre/scale; angles rad.

- **E1 Clock:** `m(T) = clip((T - T_base)/(T_ref - T_base), 0, m_max)`, T_ref = calibration-period mean so m ≡ 1 at setpoint. Implemented through existing `clock.piecewise_linear_response`. T_base declared and swept 4.5–14.8 °C; upper knot declared, no extrapolation.
- **E2 Existing organs:** `x(alpha) = x0 + (x_inf - x0)(1 - exp(-k_x*alpha))`; sampled `log(x_inf/x_ref)`, `log(k_x/k_ref)`; reject `x_inf < x0`. Applies to axis length mm, width sum mm, segment length mm, area cm2.
- **E3 Newborn organs (`determinate_beta`):** `x = x_max*(1 + (a_e - alpha)/(a_e - a_m))*(alpha/a_e)^(a_e/(a_e - a_m))` for `0<=alpha<=a_e`, else x_max; `0 < a_m < a_e`. Butturini a_m/a_e = 0.584 (leaf), 0.444 (internode) as prior candidates only.
- **E4 Size with rank and vigour:** `log x_inf(r) = mu_x + c1*z(r) + c2*1[r <= r_low] + v_plant + u_r`; `u_r = rho*u_{r-1} + eta_r`, `eta_r ~ N(0,Q)`. r_low, r_break declared.
- **E5 Width:** `S = w_L + w_R` (mm), `A = (w_L - w_R)/S`, |A| <= 1; `log S_inf` per E4; `A_inf ~ N(0, sigma_A^2)`; S follows E2. Persistent narrowing is a separate declared component, default off.
- **E6 Area (optional link):** `log A_inf = log f(r) + p*log L_inf + q*log S_inf + eps_A`; default p=q=1; f in cm2/mm2, rank-indexed. Disabled when area_basis_id differs between anchor and target or when area is an occlusion-unmeasured projected proxy.
- **E7a Initial direction:** `az_k = wrap(az_{k-1} + dphi + eps)`, eps wrapped-normal(0, 1/kappa_phi); `el_k = el_bar(r) + eps_el` via existing elevation transform.
- **E7b Persistent bending:** `el(alpha) = el_birth + d_el_inf*(1-exp(-k_rot*alpha))`; same for azimuth; optional `d_el_inf = b0 + b1*log L_inf` (default b1 = 0). Free 3-vector retired.
- **E7c Transient posture (observation model only):** `theta_obs = theta_state + delta(phase) + eps_obs`, `delta(reference phase) = 0`. Uses existing calibration capture-phase field.
- **E8 Stem:** `l_j(alpha) = l_j0 + (l_j_inf - l_j0)(1-exp(-k_s*alpha))`, single k_s; `log l_j_inf = s0 + s1*z(r_j) + s2*1[r_j > r_break] + v_plant + u_rj`; `P_j(a) = P_base + Σ_{h<=j} e_h*l_h(a)`, directions fixed.
- **E9 Appearance/determinacy:** `Δa_k ~ LogNormal(mu_w + gamma_w*z(r_k) + v_plant_w, sigma_w^2)`, gamma_w >= 0; `N_max` from declared pmf per trajectory; stop at rank = N_max; `event_kind ∈ {leaf, truss, terminal}`; on terminal emit `post_termination_scope = unavailable`.
- **E10 Light (if enabled):** `log x_inf += c_DLI*z(DLI)`, DLI mol/m2/d fixed over horizon. Not in clock or direction. Manifest field `p3_light_coupling ∈ {none, asymptote_dli}`; P4 must read it and exclude that effect. This field is the anti-double-counting contract.

## 5 Data support

Identifiable now (single time point, 4+3 plants): day-0 anchoring; divergence angle and kappa (needs resolved node order); insertion elevation trend by rank (level confounded with posture); rank→size shape (c1, s1, r_break); shape factor f(r) at one age (occlusion-biased); sigma_v crude (~±70 % relative SE, declare with sensitivity).

Not identifiable: all rates (k_*); any asymptote separate from current size (D and k jointly unidentified); phyllochron, wait distribution, N_max (unless manual records hold ≥2 dated counts per plant — **check this**); rho, plant covariance, cross-trait covariance; persistent vs transient direction; measurement-error covariance (blocks `update_forecast`); every environment response including T_base (one chamber = one independent unit).

Recommended non-destructive plan (priority): (1) repeat 18-photo protocol every 3–4 d for 30 d, same time of day, ≥6 plants; (2) diurnal capture pair on 3 sessions; (3) back-to-back repeatability pair on 1 session; (4) dated first-visible log per leaf and truss; (5) 3 sacrificial plants at day 30, flatbed leaf area by rank; (6) continuous T/RH/PPFD logging at ≥3 positions; (7) second-chamber contrast only if available; reserve 3 plants for 7/14/21/30-day validation (CRPS for size, interval log loss for timing, geodesic error for direction) against existing persistence/recent-change baselines.

## 6 Open user decisions (block implementation)

1. **Size parameterization and decoder:** `log x_inf` sampled with D derived, rank law carrying plant effect, exponential for existing organs + `determinate_beta` for newborns. Breaking change to `trajectory_parameters.json`.
2. **Environment entry and P4 exclusion:** temperature → clock only (normalized to 1 at setpoint); DLI → `log x_inf` only; nothing else in P3; `p3_light_coupling` in manifest. Alternative: no light in P3 at all.
3. **Determinacy and topology:** node budget replaces free stop probability; `event_kind` with null geometry; `post_termination_scope = unavailable` after apex termination.

## 7 Requested Codex review (no implementation yet)

1. Verify discrepancies 1–9 in section 1 against current `tools/probabilistic_compound_growth.py`, `tools/growth_calibration.py`, `tools/growth_calibration_evidence.json` and docs. Cite file/function/line.
2. For each row in section 3, classify the change: config-only (existing schema), additive schema field, or breaking change. Name affected functions, schemas, CSV/JSON fields and tests.
3. Check that E1 (normalized clock) works with the current calibrated-forecast requirement of a calendar clock, and whether `stop_logit` can express the N_max budget without a new event type.
4. Check whether manual growth records (leaf count, unfolding) contain ≥2 dated counts per plant usable as interval-censored appearance data.
5. Confirm the `sample_forecast` `environment_used`/`light_used` flags issue (clock-only) and how `p3_light_coupling` would replace or extend them.
6. Return findings in a new Codex handoff. Do not edit active-owner files. Unverified literature values (z1–z3, r1, r2, lambda, gamma) must not be installed anywhere.

Not verified by Claude Science: the plant/photo inventory (directory listing timed out) and Butturini supplementary tables.
