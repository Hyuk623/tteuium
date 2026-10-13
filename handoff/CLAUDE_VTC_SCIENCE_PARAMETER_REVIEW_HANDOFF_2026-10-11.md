# Scientific review handoff: VTC equations, parameters and coefficients

Date: 2026-10-11
Recipient: Claude scientific reviewer and the V3 implementation owner
Purpose: determine which model forms and numbers can support conditional Micro-Tom development, which need correction or measurement, and which must remain unavailable. This inventory does not approve coefficients or authorize changes to human measurements.

## 1. Evidence boundary and current work

This handoff is based on inspected local source and contracts, not a new validation against full research papers. Publisher retrieval for diaf022 and Chen2014 was unsuccessful during this review; independently verify original equations, preprocessing and units before scientific acceptance.

The verified executable baseline is `phase1_leaflet_subset_v1`. It uses native GroIMP light, a borrowed Thornley response and conditional carbon allocation, with constant-SLA rectangular blade expansion. It is not a complete tomato developmental model. Temperature and CO2 are recorded but do not modify its response.

A separate owner has claimed V3 implementation files. Do not edit those files concurrently. Treat the V3 parameters below as required review targets, not proof of implemented or tested behavior. Reconcile this inventory with the actual new code when that owner delivers.

Authoritative local sources:

- `tools/vtc_growth_fork.py`: executed native template and imported NRH function.
- `tools/vtc_growth_bridge.py::demo_inputs`: example coefficients and provenance; these are demo inputs, not global biological defaults.
- `tools/vtc_growth_io.py`: units, validation and independent arithmetic checks.
- `handoff/PHASE1_VTC_PYTHON_SCIENCE_AND_IO_CONTRACT_2026-10-11.md`.
- `handoff/PHASE1_GROIMP_PYTHON_EXECUTION_2026-10-11.md` and its acceptance artifacts.
- `handoff/CLAUDE_PHASE1_VTC_WHOLE_PLANT_DEVELOPMENT_PROMPT_V3_2026-10-11.md`.
- `handoff/MTG_CONVENTION_2026-10-10.md`, sections 11–13.
- Original reference under `C:/Users/sho36/Downloads/vtc-main/vtc-main/tomatoFSPM_basic_isP/`, especially `photosynthesis.rgg`, `parametersMerlice.rgg`, `modules_organs.rgg`, `modules_base.rgg`, `updates.rgg` and `rewrites.rgg`.

Use these status distinctions throughout: active conditional model; reference-only; proposed for V3; measured; borrowed other-cultivar; synthetic assumption; physically defined conversion. A passing software test is not biological acceptance.

## 2. Immediate high-priority issues

1. **Photosynthesis unit conflict:** `parametersMerlice.rgg` comments label AMAX as `mmol m-2 s-1`, whereas `photosynthesis.rgg` describes the NRH output as `umol CO2 m-2 s-1` and the current bridge uses that micromole interpretation. Resolve from the original source/fitting data. Do not silently multiply by 1000 or assume the comment is correct.
2. **Gross/net and respiration:** the bounded NRH is interpreted as gross; confirm whether the borrowed fit was estimated from gross or net exchange and from incident or absorbed PPFD. A wrong interpretation can double-subtract respiration or distort alpha.
3. **Area versus photosynthetically active area:** the user selected `full_outline`, including browned/necrotic margins. That measurement rule does not establish equal photosynthetic activity across the outline. Preserve full-outline area and review a separate green/active-tissue fraction or spatial classification. Never silently replace the main area column with green-only area or grant dead tissue full assimilation.
4. **Unrealistic demonstration rates:** initial leaflet DM 0.02 g and potential increment 0.08 gDM/day in the baseline demo are software fixtures. They are not Micro-Tom rates or safe starting priors for fitting.
5. **Birth and non-leaf carbon:** V3 must charge initial organ mass, root/stem/reproductive growth and maintenance. A leaf-only balance cannot certify whole-plant conservation.

## 3. Active bounded-mode equations and parameters

Notation: Q = absorbed photon flux per represented one-sided blade area; S = that area; M = structural dry mass; B = available carbon; C_r = reserve carbon; d = potential dry-matter increment; C_a = allocated carbon. Numerical values below describe inspected demo settings only. A particular run's frozen input package remains authoritative.

### A1. Light to leaflet PPFD

`Q = Phi_abs / S`

| Item | Units/current status | Review required |
| --- | --- | --- |
| Phi_abs | umol photons/s; native ray-traced absorption | Confirm photon-power interpretation of GroIMP source/material settings and any spectral integration. |
| S | m2, one-sided represented area | Full-outline measurement, represented mesh area and active photosynthetic area must remain distinguishable. |
| Lamp power/position/direction/shape | Scenario inputs; current fixture uses assumed point LED | Measure absolute output/distribution or clearly declare assumptions; do not replace three real bars with a validated point source by naming alone. |
| Reflectance, transmittance, absorptance | Current baseline uses black flat blades | Review measured or sourced spectra and face treatment; alpha + rho + tau must obey the selected energy/photon convention. |
| Front/back response | Same response in bounded scenario | Review anatomical face and whether two-sided incident flux is compatible with the response fit. |

No canopy extinction coefficient k or fixed projection coefficient G is required by the current explicit ray geometry. Introducing either as a correction on top of ray tracing requires a separate justification to avoid double-counting shading.

### A2. Thornley non-rectangular hyperbola

`A_g(Q) = [alpha*Q + Amax - sqrt((alpha*Q + Amax)^2 - 4*theta*alpha*Q*Amax)] / (2*theta)`

| Parameter | Inspected demo value | Units and interpretation | Review/measurement |
| --- | --- | --- | --- |
| Amax | 13.57 | umol CO2/m2/s in the bridge; maximum response | Merlice upper-layer borrowing; resolve unit conflict, fit basis, age/position, temperature/CO2 and Micro-Tom domain. |
| alpha | 0.048 | mol CO2/mol photons; initial slope | Incident versus absorbed photons, spectrum, active area and gross/net preprocessing. |
| theta | 0.92 | Dimensionless curvature | Fit identifiability with Amax and alpha; uncertainty and admissible domain. Not a leaf angle. |

Numerical handling at zero curvature or invalid discriminants is an implementation issue; do not change biological coefficients just to avoid a numerical failure. Leaf-level gas-exchange light-response measurements are the direct calibration target. Photos alone do not identify all three parameters.

### A3. Daily assimilation and leaf respiration

`C_gross = A_g * S * illuminated_seconds * 12.011e-6`

`C_leaf_resp = R_leaf * S * 86400 * 12.011e-6`

`C_net = C_gross - C_leaf_resp`

| Item | Current setting/status | Review required |
| --- | --- | --- |
| R_leaf | 0 in base demos, 1 umol CO2/m2/s in the named deficit fixture; other runs may differ | Zero is an explicit test setting, not living-leaf physiology. Review dark/day respiration, mass versus area basis, temperature dependence and daily duration. |
| Illuminated duration | 14 h in the inspected fixture | Not the user's measured schedule. For changing PPFD use time integration, not a single unqualified mean through a nonlinear response. |
| 86400 | Seconds/day | Fixed conversion for a daily interval, not an agronomic coefficient. |
| 12.011e-6 | gC per umol CO2 | Chemical conversion, not a fitted growth parameter. Keep CO2, CH2O, gC and gDM distinct. |
| Additional maintenance | Explicitly absent in this leaf-subset path | Do not carry this exclusion into whole-plant V3 as zero stem/root/truss maintenance. |

Potential temperature candidate, not active here: `R(T)=R_ref*Q10^((T-T_ref)/10)`.
Review R_ref units, reference temperature, Q10, acclimation, organ basis and whether leaf exchange already includes that respiration. Do not install a generic Q10 without provenance.

### A4. Potential demand, allocation and reserves

For each organ i in the current supported subset:

`D_i = d_i * f_C / eta`

`B = C_r,start + sum(C_net,i)`

`F = min(max(B, 0), sum(D_i))`

`C_a,i = F * D_i / sum(D_i)` when total demand is positive; otherwise zero.

`Delta M_i = C_a,i * eta / f_C`

`C_growth_resp,i = C_a,i * (1-eta)`

`C_r,end = max(0, B - sum(C_a,i))`

If B < 0 the engine reports an unmet deficit; the collector must reject successful conservation/publication. The max operation is not a biological starvation model.

| Parameter/rule | Demo value/status | Units | Review required |
| --- | --- | --- | --- |
| d_i (`potential_dm_g_day`) | 0.08 per leaflet in the basic fixture | gDM/day, interpreted over one daily step | Replace fixture demand with a reviewed age/stage-dependent potential demand in V3. |
| f_C (`carbon_fraction_gC_gDM`) | 0.45, synthetic assumed | gC/gDM | Organ composition; tissue age; measurement or justified literature uncertainty. |
| eta (`growth_efficiency`) | 0.75, synthetic assumed | Structural gC/allocated gC | Conversion costs and organ differences; not automatically interchangeable with VTC F_CO2 or a growth-respiration fraction. |
| Demand-proportional allocation | Active conditional rule | Dimensionless shares | Organ priority, sink competition, saturation, roots/reproduction and carbon transport scope. |
| Reserve pool | Explicit input, often zero in fixtures | gC | Seed/endosperm versus mobile carbohydrate, accessibility, capacity, mobilization limits and surplus handling. |
| Starvation | Fail closed when obligations cannot be funded | gC deficit | Choose whether to halt, mobilize structure or model senescence; do not infer mortality from a software failure. |

A reviewed whole-plant balance must include every structural organ, new-organ mass, reserves, respiration and exports/losses. Conservation alone does not validate allocation priorities.

### A5. Mass to planar leaf dimensions

`scale = (M_new/M_initial)^(1/2)`

`L_new = L_initial*scale; W_new = W_initial*scale`

Therefore `S_new/S_initial = M_new/M_initial`, with constant aspect ratio and constant SLA.

| Item | Current assumption | Review required |
| --- | --- | --- |
| Exponent 1/2 | Active geometric scaling exponent | This follows from the chosen constant-SLA, two-dimension scaling, not a fitted tomato growth exponent. Test whether aspect ratio and SLA remain constant by age/light/treatment. |
| SLA = S/M | Implied by initial area/mass | State units explicitly, e.g. m2/gDM; measure dry mass and planar area of matched leaves. |
| Outline | Rectangle in bounded mode | V3 needs per-leaflet polygon shape and independent area validation. |
| Initial dimensions, mass and age | Supplied, often synthetic | Do not call hidden mass/age photo measurements; quantify sensitivity. |

The frozen-geometry control intentionally violates mass/area coupling to isolate light feedback. It is diagnostic-only and must not be fitted as a biological treatment.

## 4. Developmental equations, exponents and coefficients requiring V3 review

These are reference/candidate families. They are not all active in the verified bounded engine.

| Process | Model form / parameter family | Reference numbers or current status | Required scientific decision |
| --- | --- | --- | --- |
| Thermal age | Integrate f(T), often a base-temperature response; T_base, upper limits, day/night weighting | Earlier plan mentioned T_base 5.7 C and 18.63 degree-days/day as assumptions | Verify domain and use actual environmental records or explicit scenarios. Never make a setpoint-derived increment a measurement. |
| Germination/emergence | Delay in thermal time | Original Merlice DELAY 206.3 degree-days | Separate sowing, germination, initiation and visible emergence. Refit or retain conditional prior. |
| Phytomer appearance | Thermal-age thresholds / PHYLLOCHRON | Original Merlice 37.9 degree-days/phytomer | Micro-Tom and stage dependence; interval observations needed. Fruit delay 42.4 degree-days is not leaf phyllochron. |
| First reproductive transition | FINAL_VEG_PHYT_NUM, stage/topology rule | Merlice 8; Micro-Tom fork proposes a separately labelled prior 8 | Coincident values do not establish the same biological basis. Clarify cotyledon and true-leaf counting. |
| Truss cadence and termination | TRUSS_INTERVAL, SP_STOP_RULE, active/stopped apex state | Original indefinite every-fourth rule; fork proposes termination after two successive trusses | Verify determinacy/sympodial interpretation, affected axes, pruning and continued growth of existing organs. |
| Potential organ growth | Beta-type sink curves or derivative of a logistic; Wmax, growth duration te, peak tm, shape parameters | Original WMAX/TE/TM tables are Merlice-specific | Pin the exact equation, units and domain; determine organ-specific values and carbon-funded realization. |
| Logistic size envelope | X(a)=Xmax/[1+exp(-k*(a-tm))] | Merlice internode length Xmax=.072 m, k=.019, tm=222; leaf length .41 m, .014, 232 | Inspect implementation: some dimensions integrate the derivative rather than assigning X directly. k has inverse-age units; age may be thermal time. Potential envelopes must not overwrite allocated growth. |
| Area-length allometry | A_cm2=a_AL*(L_cm)^g_AL, or inverse | Original a_AL=.006, g_AL=3.08 | Unit-sensitive coefficient and fitted exponent; same definition of compound length/area and cultivar required. Not valid unchanged in mm or m. |
| Stem mass-to-size | Length, diameter, volume, dry density/taper relation | No accepted new coefficient in this handoff | Determine how allocated stem DM becomes length and thickness without creating volume or mass twice. |
| Root demand/maintenance | Root compartment mass, potential growth, allocation and respiration | Original root parameters are reference-only | Root/shoot allocation, rooting-volume constraint, initial root mass; photos cannot directly measure these. |
| Flower/truss growth | Birth cost, number, stage, sink strength, maintenance, abortion policy | Original FLOWER may combine flower/fruit roles | Separate organ types and stages. Fruit-set/yield predictions require additional validation beyond truss appearance. |
| Leaf insertion angle | theta_L=a_theta*(1-exp(-b_theta*L_cm)) | Original a_theta=81.5 deg, b_theta=.045 per cm | Chen-type reference; check stem/petiole angle definition, length basis, initial offset and side-view evidence. Not automatic phototropism. |
| Rachis bending | Per-node alpha_i, CURVE_RATIO, age dependence | Original curve60deg and uniform segment logic; fork ratio1:2:2 is a prior | Use current MTG A2 signs, count and geometry. Do not merge sum(alpha) with theta or blade curl. |
| Phyllotaxis | Cumulative azimuth y=a+b*true_leaf_index; handedness | Estimator planned; no measured Micro-Tom b established here | >=5 consecutive known true leaves, angle unwrapping, axis orientation, missing leaves and uncertainty. Do not impose 137.5deg or wild-species spread as a measured target. |
| Leaflet number and shape | Rank pair-count table, length/width ratio, middle-pair ramp, width-profile exponents | Original LW_RATIO_LF=2, MAX_WIDTH=.6, K1=2, K2=2.2; all reference-only | Confirm against target leaves and rank; outline basis and realistic variability; variable pair count. |
| Omitted small leaflets | AREA_CORRECTION | Earlier proposed1.0 is a declared no-correction assumption | Optical geometry, biomass and measured full-outline area must remain consistent; no fake absorbing area. |
| Organ birth | Seed mass, emergence cost, timing and resource gate | Unresolved beyond V3 contract | Zero-mass primordia versus funded tissue; no positive absorbing area without a declared mass/area rule. |
| Initial/spin-up state | Seed reserves, sowing date, 30-day environment | Thirty days is a scenario initialization choice | Verify a real spin-up, not an age label; uncertainty in roots, reserves and developmental stage. |

Original width profile uses power exponents K1 and K2 on normalized distance from the widest blade point. Confirm its equation and integration against actual outline area before using those exponents. These shape coefficients are not physiological rates.

If FvCB is adopted instead of fixed NRH, review Vcmax25, Jmax25, TPU25, Rd25, quantum/electron-transport efficiencies, stomatal/mesophyll/boundary conductance, CO2/O2 conventions, VPD, leaf versus air temperature, and Arrhenius/peaked-response activation/deactivation/entropy parameters. Do not tune both NRH and FvCB as if both independently govern the same leaf exchange. Original VTC gross-output selection needs an explicit audit.

## 5. Settled definitions versus deferred items

- `area_basis=full_outline` is a current user decision, not a tunable model coefficient. Green-only area can be an additional separately named quantity. Review physiological use of discoloured tissue without changing the measurement rule.
- MTG A2 fixes class-specific insertion angles, azimuth reference, downward-positive rachis bends and the two separate azimuth fields. Use it rather than redefining these quantities in a new model.
- Blade curl/rugosity and theta flat/bent thresholds are explicitly **on hold** under MTG section13. Do not invent thresholds. Continuous observed geometry may still be used within its evidence scope.
- A compound angle and an NRH curvature both called theta are unrelated; use qualified names in formulas and exports.
- Biological parameters above differ from numerical controls: ray count, random seed, bounce depth, daily step, mesh resolution and conservation tolerance. These need convergence/error analysis, not cultivar fitting.
- The current ray tests do not justify a universal error bound, even at4.8M rays. Normalized phone ratios do not calibrate absolute PPFD or carbon assimilation.
- Nutrient feedback is disabled in this stage. Future uptake kinetics, sorption, root ion capacity and deficiency response coefficients belong to a separate science contract, not hidden multipliers here.

## 6. Evidence needed and identification limits

| Evidence | Parameters it can help constrain | What it cannot establish alone |
| --- | --- | --- |
| Identified twice-daily images, capture phase and physical scale | Emergence times, dimensions, angles, visible topology, growth trajectories | Net carbon fixation, root mass, biochemical coefficients or hidden organ ages |
| Matched leaflet full-outline/green-only area and dry mass, repeated across ages | SLA, allometry, senescent fraction and structural growth | Independent Amax/alpha/theta or assimilation by brown tissue |
| Gas-exchange light-response curves with temperature, CO2 and leaf age | NRH parameters and respiration convention | Whole-plant allocation or target-cultivar universality from one leaf |
| Leaf/organ respiration and organ dry-mass series | Maintenance, conversion costs, sink timing and allocation | Unique identification of every storage/priority parameter without additional constraints |
| Calibrated PPFD/fixture measurements plus geometry/optics | Absolute photon supply, light distribution and transport checks | Carbon-use efficiency or developmental rules |
| Longitudinal node/truss/apex observations through termination | Phyllochron, transition, cadence, determinate scope | Fruit yield or seed-to-flowering extrapolation from a short series |
| Organ harvests including roots/stem/reproductive tissue | Partitioning, initial-state priors and whole-plant mass balance | Full root geometry or ion uptake from biomass alone |

Record uncertainty and replicate structure. Separate calibration plants/times from held-out evaluation.
Do not fit many compensating parameters to leaf area alone and call the fit mechanistically validated.
Report sensitivity before fitting weakly identifiable parameters, especially light power vs Amax/alpha,
SLA vs biomass allocation, and maintenance vs growth efficiency/reserve accessibility.

## 7. Requested Claude review output

Return an English reviewed registry and decision note, preferably:

- `handoff/VTC_SCIENCE_REVIEW_DECISIONS_2026-10-11.md`
- A versioned parameter/model registry JSON under a fresh `build/vtc_science_review_<date>_<id>/` directory.

Each entry must include: stable ID; active/reference/proposed mode; equation and code location; input/output
units; value/range/null; source DOI and exact equation/page/table; cultivar/organ/stage/environment;
evidence kind; uncertainty; dependencies; double-counting risks; calibration evidence; acceptance test;
and disposition (`retain_for_conditional_use`, `revise_contract`, `needs_measurement`, `defer`, or `reject`).

Prioritize decisions in this order:

1. Unit and gross/net/absorbed/incident/area conventions, including full-outline versus active tissue.
2. Whole-plant carbon closure, organ birth, respiration and storage ownership.
3. Potential demand, realized allocation, SLA/allometry and mass-to-geometry consistency.
4. Thermal clock, new organs, reproductive transition and determinate architecture.
5. Orientation/shape priors and uncertainty, respecting the user's deferred items.

Separate arithmetic/engineering acceptance from scientific model choice and from measured Micro-Tom
accuracy. Do not modify the running implementation owner's files during this review; provide precise
contract changes for coordinated implementation. The response must explicitly say which equations can
run only as conditional scenarios, which numerical values need replacement, and which remaining inputs
prevent biological validation.
