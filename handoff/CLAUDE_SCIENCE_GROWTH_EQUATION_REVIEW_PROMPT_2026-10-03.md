# Review and improve the growth equations of a dwarf tomato CompoundLeaf growth model

I want to revise and strengthen the growth equations of an existing dwarf tomato growth calculator. This is a design and literature review discussion. Do not write code, and do not install literature coefficients as program defaults.

## 0. Context

Project path (readable only if you have access): `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`
If you can read it, check these first and report any difference from the summary below before anything else:
- `tools/PROBABILISTIC_COMPOUND_GROWTH.md` (implemented calculator, authoritative)
- `handoff/CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md` (design spec and evidence register)
- `tools/GROWTH_CALIBRATION.md` (implemented fitting families)
- `handoff/CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md` (integration decisions)
If you cannot read them, say so and work from this summary.

Four linked work streams share one codebase:
- P1 3D reconstruction: observed leaf area, supported triangle surfaces, compound-leaf structure from photos.
- P2 light simulator: received/absorbed photons per leaflet, compound leaf and plant in a canopy.
- P3 growth direction (this review): 30-day probabilistic trajectories of CompoundLeaf appearance, direction, length, width and area.
- P4 FSP: coefficient calibration now; future photosynthesis/respiration/carbon allocation.

Decisions already made by the user (treat as constraints):
- D1. P3 owns the realized growth increment, both direction and size. Only P3 changes organ geometry over time.
- D2. P4 (carbon physiology) is an auxiliary diagnostic index only, e.g. carbon supply/demand ratio for the P3-predicted increment. It does not add increments or multiply P3 rates.
- D3. First integration target is an end-to-end pass on synthetic data with exact unit/ID/angle/missing-value conversion between projects. Biological validation comes later.

## 1. Current growth equations (as implemented)

Engine: `probabilistic-compound-1`, an event-driven stochastic graph grammar with a joint parameter sampler and analytic continuous transitions. Measured geometry at day 0 is preserved exactly. Future compound leaves are optical-ineligible; all outputs carry `validated_growth=false`.

| Process | Current form | Parameters (units) |
|---|---|---|
| Continuous expansion (axis length, segment, area) | `x(a) = x0 + D * (1 - exp(-k * a))`, `a` = development age | `D_length_mm`, `k_length`; `D_segment_mm`, `k_segment`; `D_area_cm2`, `k_area`, `birth_area_cm2` (k in 1/development-day) |
| Width | Same saturating form toward nonnegative left/right targets; may decrease | `left_target_mm`, `right_target_mm`, `k_width` |
| Direction change | Smooth local rotation vector approaching target | `rotation_x/y/z_rad`, `k_rotation` |
| Initial direction of a new leaf | Parent-local azimuth/elevation drawn from conditional family | `azimuth_rad`, `elevation_rad` |
| Appearance timing | Residual wait to next event + inter-event waits; lognormal; plus stop probability or logistic stop rule | `wait_dev_days`, `stop_probability` or `stop_logit` |
| Dependencies | Transformed Gaussian coordinates, shared plant-level draw, cross-trait covariance, AR(1) residual between successive leaves | `plant_covariance`, `rho`, innovation covariance |
| Development clock | Calendar days; or piecewise-constant multipliers; or one piecewise-linear response table (e.g. temperature → clock multiplier). No product of responses, no extrapolation | knots `{value, multiplier}` |
| Light | Optional single scalar light feature, fixed over the horizon, incident vs absorbed kept distinct; no future shading recomputation | `light_feature_id` |
| Stem | Measured segment directions fixed; segment elongation uncertain | `D_segment_mm`, `k_segment` |

Calibration (`growth-calibration-1`) supports three fit families: `anchored_expansion` (Gaussian likelihood), `azimuth_rotation` (von Mises), `lognormal_wait` (interval/right-censored likelihood). Bounded L-BFGS-B, curvature/identifiability checks, bootstrap particles.

Evidence limits recorded by the spec: the exponential remaining-growth form is a proposed surrogate (the tomato digital twin of Smolenova et al. used fitted logistic-type expansion); lognormal waits and stop rule are statistical approximations; no source established a cultivar-specific direction law; dwarf tomato FSP (Butturini et al., in silico Plants, GroIMP, repo Micbut/FSP-model-dwarf-tomato commit 2d727a3) is an architectural precedent whose numbers were not transferred.

Current data (to be confirmed): plants dwt_01–04 and dwt_test T1–T3, 18 photos each, mostly a single time point; per-plant side leaf-area proxy ~10–17 cm², height 60–90 mm, stem diameter ~5.5–6.2 mm; partial manual records (leaf count, unfolding). Absent: repeated-time geometry of the same plant, destructive dry mass, independent leaf area, measured PPFD distribution.

## 2. What I want from you

For each process in section 1:
1. Judge whether the current form is adequate for a dwarf tomato under controlled light. Compare at least: the current exponential saturation, logistic, Gompertz, beta/Yin-type determinate growth, and thermal-time or development-rate driven forms. Do not assume more complex is better.
2. Propose corrections or supplements, each with:
   - equation and purpose
   - inputs, state variables, outputs, units
   - parameters, applicable range, and how they enter the existing parameter particles/covariance
   - literature support with exact equation/table/page location; mark sources you could not access and do not present their coefficients as verified
   - what the literature confirms vs. what is a proposed adaptation for this project
   - measurements needed, and which parameters are identifiable from current data vs. not
3. Keep the existing contract where possible: measured day-0 geometry preserved, explicit clock, no implicit environment multipliers, missing ≠ zero, radians in model parameters.

Specific questions:
- Size: Is `D` (remaining increment) better parameterized as a final size, a relative increment, or linked to leaf rank/position? How should leaf area relate to length × width (shape factor) and when should area be independent?
- Timing: Is a lognormal wait with a stop rule reasonable for leaf appearance (phyllochron) in a determinate dwarf tomato? Should a thermal-time or development-rate clock replace calendar days, and what base temperature evidence exists for dwarf/micro tomato cultivars?
- Stem: How should internode elongation and attachment-point movement be modeled, and is fixed segment direction acceptable over 30 days?
- Direction: How to separate (a) initial direction of a new leaf (phyllotaxis/divergence angle, insertion elevation), (b) persistent rotation/bending of existing leaves, (c) transient posture (diurnal leaf movement, water status). Propose observation protocols to tell transient from persistent change. Do not treat the brightest direction as the growth direction.
- Light and environment: Which variables (temperature, PPFD/DLI, photoperiod, CO₂, VPD, EC, pH) should enter which equation (clock, size, direction) and with what evidence? Since D1/D2 put all growth in P3, how should light enter P3 without later double counting against a P4 carbon index?
- Dependencies: Are the shared plant effect, cross-trait covariance and AR(1) between successive leaves sensible, and how can they be estimated or bounded with very few plants?
- Determinacy: How should truss/inflorescence appearance and growth stop in a determinate dwarf plant be represented relative to leaf appearance?

## 3. Coefficients and validation

For each parameter, classify the route: direct measurement on target cultivar / literature candidate / estimation from repeated observation / explicit assumption with sensitivity analysis / currently unidentifiable.
- Address fitting many parameters to few leaf-area observations, confounded environment variables, and counting leaves of one plant as independent replicates.
- Propose the minimal non-destructive repeated measurement plan (what, how often, how many plants) to identify the key parameters, with priorities.
- Propose an independent validation plan separating size, timing and direction, evaluated at 7, 14, 21, 30 days only where independent observations exist, and compared against persistence/recent-change baselines already in the code.

## 4. First response scope

Give only:
1. A table: process × current form × recommended form (keep/modify/replace) × reason × evidence status
2. Revised equation set for the minimal recommended model
3. What current data can and cannot support; the key missing measurements
4. At most 3 decisions I need to make first

Label every statement as **verified literature fact**, **design proposal**, or **open assumption**.
After we agree, summarize only the agreed equations as an implementation contract (English, CSV/JSON field definitions compatible with `probabilistic-compound-1` and `growth-calibration-1`).
