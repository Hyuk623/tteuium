# P1–P4 integration: scientific equation and parameter review register

Date: 2026-10-11
Recipient: Claude scientific reviewer and the P1–P4 integration/development implementers
Scope: the complete workflow requested in `CLAUDE_P1_P2_P3_P4_END_TO_END_INTEGRATION_PROMPT_2026-10-11.md`.

This register expands the earlier VTC-only science handoff to include photo geometry, tracking, canopy light, physiology, development, substrate nutrients and feedback. It is a review inventory, not approval of all listed equations or coefficients. Preserve existing user decisions and contracts; do not install new biological defaults from this document.

## 1. Status, architecture and evidence

Target sequence: **P1 current structure -> canopy placement -> P2 light -> P4 resources/allocation -> P3 development/geometry -> next P2 step -> comparison with new P1 observations.**

Python manages observations, identifiers, adapters, execution and verification. GroIMP/VTC owns authoritative within-run light/carbon/development. Python's existing ray tracer and carbon diagnostic are separate comparison paths. Substrate water/element bookkeeping is a separate Python authority; biological nutrient feedback remains science-gated. Do not apply two engines' results to one state.

Status codes in this register:

- **A:** implemented in the inspected bounded model or established diagnostic; conditional, not biologically validated.
- **R:** reference-only code/equation; not automatically active in the integrated run.
- **P:** proposed or required contract; adoption/implementation must be confirmed.
- **D:** user-defined measurement/convention rule; preserve it.

The last verified native mode was `phase1_leaflet_subset_v1`. V3 development files are under another owner's active implementation claim. Recheck its final contract/report before changing the status of a P/R item to A. Test-file existence or a directory name is not execution evidence.

Sources inspected locally include `tomato3d/light/{scene,raytrace}.py`, `tools/vtc_growth_{bridge,fork,io}.py`, `tools/nutrient_{contract,composition,balance}.py`, current MTG sections 11–13, and the original VTC source. Supporting project documents:

- `CLAUDE_VTC_SCIENCE_PARAMETER_REVIEW_HANDOFF_2026-10-11.md` for detailed bounded-mode and VTC coefficient provenance.
- `PHASE1_GROIMP_PYTHON_EXECUTION_2026-10-11.md` and its acceptance artifacts.
- Stage-2/Stage-3 contracts and their appended reconciliations.
- The literature P1–P4 prompt, VTC Micro-Tom fork prompt and V3 development prompt.
- `CLAUDE_FSP_NUTRIENT_SCIENCE_CONTRACT_REQUEST_2026-10-06.md`.

These are local implementation references, not a new independent verification of their cited research. Claude must confirm original paper equations, units, cultivar and experimental conditions. Parameter values below are explicitly identified as fixtures or reference values, never recommendations for actual plants.

## 2. Common units and uncertainty rules

| Quantity | Required convention | Main risk |
| --- | --- | --- |
| Position/length | Frame ID plus mm at Python boundary; explicit conversion to GroIMP m | A 1000-fold length conversion becomes a million-fold area error. |
| Angle | Degrees/radians explicit; MTG reference axis, sign and handedness | Same number can represent different botanical quantities. |
| Area | Visible projected / completed estimate / one-sided surface, each separately identified | A projection or envelope is not optical tissue area. |
| Photon flux | umol/s versus PPFD umol/m2/s versus DLI mol/m2/day | Dividing by area twice or using DLI as PPFD. |
| Carbon/mass | gC, gCO2, gCH2O, gDM kept distinct | Treating a biomass conversion factor as elemental carbon fraction. |
| Nutrients | mg element, mmol element/L; species/form labels retained | NO3-N mass is not NO3 ion mass; oxide label is not elemental content. |
| Time | Aware timestamps, interval duration, chronological and developmental ages | Light, environment and geometry one step out of sync. |
| Missing input | Unavailable/null with reason | Missing measurements silently interpreted as zero. |

Every fitted or borrowed coefficient requires source, organ, cultivar, stage, domain, uncertainty and dependencies. Preserve correlations between parameters; independent random draws are not automatically appropriate. Numerical tolerance is not measurement uncertainty. No biological acceptance from arithmetic closure alone.

## 3. P1 — photo geometry, area and temporal identity

### G1. Projection, camera calibration and scale

Ideal pinhole relation, before distortion:

`z_c * [u,v,1]^T = K * (R*X + t)`

K contains fx, fy, principal point and any declared skew. Distortion parameters depend on the selected calibration model. This relation is a geometry identity, not authorization to choose a reconstruction algorithm.

| ID | Parameter/equation | Status | Units | Scientific/metrological review and evidence |
| --- | --- | --- | --- | --- |
| G1 | fx, fy, cx, cy; k1,k2,k3,p1,p2 where used | A/R by route | px / model-specific | Calibration resolution, lens mode, distortion convention, per-view residuals and independent scale/pose error. A low reprojection residual alone does not certify correct physical size. |
| G2 | Extrinsic R,t, reference object size, camera/plant motion | A/P by route | Rotation, mm | Recorded camera geometry; board-free estimator validation; reject ambiguous poses and unreviewed board-to-plant transforms. |
| G3 | Scale s and area scaling A=s^2*A_px | P/conditional | mm/px, mm2 | Valid only for the appropriate plane/depth mapping. Pot rim scale cannot be applied universally to leaves at other heights under perspective. Measure pot inner diameter; include depth/pose uncertainty. |
| G4 | Mask score, acceptance/occlusion thresholds, boundary error | A/P | Dimensionless, px | Detection confidence is not area uncertainty. Validate against held-out manually delineated masks; report visible support and scale-sensitive edge error. |
| G5 | Mesh area = sum(0.5*norm((v2-v1) cross (v3-v1))) | A geometry formula | mm2/m2 | Triangle coverage, one-sided convention, overlap/duplicate triangles, generated hidden surface and contour uncertainty. |

### G2. Projected area versus true surface area

For a single planar, fully visible surface under orthographic viewing:

`A_projected = A_surface * abs(n dot v)`

An inverse using this equation becomes ill-conditioned for edge-on leaves. It does not solve occlusion, curved blades, depth or shape. n and -n give the same projected area: photographs of area alone cannot establish botanical front/back identity.

| ID | Review target | Status | Required decision/evidence |
| --- | --- | --- | --- |
| G6 | Projection factor G, area multiplier k, ring-average inversion | P, unadopted | Do not freeze G=.5 or one empirical multiplier as exact. Quantify leaf-angle distribution, view geometry and changing occlusion; independent scan/planar reference needed. |
| G7 | Planar sweep model A*abs(sin(theta_L)*sin(theta_v)*cos(phi-phi_L)+cos(theta_L)*cos(theta_v)) | P | Requires stable leaflet correspondence and planar/view assumptions; does not recover centroid/depth/outline. Quantile tau=.9 is a proposed estimator choice, not validated biology. |
| G8 | Occlusion correction, visible fraction, completion priors | P | Specify observability and uncertainty; unknown coverage can prevent a finite area estimate. No silent generated-to-measured promotion. |
| G9 | Curvature factor, surface-area correction, hidden leaflet assumptions | P/on hold where applicable | Leaf blade curl is not rachis bending. No numeric curl correction while its definition is deferred. |
| G10 | Main area basis = full_outline | D | Include original outline/browned margins. Green-only area is a separately named optional field, not a replacement. |

### G3. Tracking and canopy identity

| ID | Parameter | Status | Review and validation |
| --- | --- | --- | --- |
| G11 | Matching cost weights, spatial/appearance/angle gates, best-vs-second margin | P | No universal defaults. Validate identity switches, false merges, occlusion, new organs and removals against independently labelled same-plant time series. |
| G12 | Growth/posture process noise, measurement covariance | P | Separate twice-daily photoperiod posture from growth; collect capture times relative to lights-on and repeated measurements. |
| G13 | Plant-local to canopy transform X_canopy=R_p*X_local+t_p | A/P adapter | Transform positions and normals correctly; preserve scale and unique instance IDs. Verify inverse mapping and real pot placement. |

No blanket independence assumption for many views of the same leaf or plants sharing one lighting measurement. Confidence and uncertainty must be attached to the estimated quantity, not inferred from a detector score alone.

## 4. P2 — emission, transport and light aggregation

### L1. Existing Python comparison-engine formulas

These describe the inspected Python direct-light path, **not an assertion that GroIMP uses the same emission law**:

`I(theta)=I0*cos(theta)^m` inside a declared cutoff cone.

`m=log(0.5)/log(cos(theta_half))`

`I0=PPF*(m+1)/[2*pi*(1-cos(theta_cut)^(m+1))]`

`Q_receiver=sum_e I_e(theta_e)*c_receiver,e/d_e^2 * T_path,e`

The source is sampled over its emitting surface. c_receiver is the applicable one- or two-sided incidence factor. Distances and area conversion must be consistent. In the current Python direct path `T_path=tau^n` for n distinct leaf crossings, and opaque blockers stop the ray. This is straight-through attenuation, not diffuse scattering.

| ID | Parameter | Status | Units | Review/evidence |
| --- | --- | --- | --- | --- |
| L1 | PPF, source spectrum, dimming response | A inputs; measurement pending | umol/s | Actual fixture measurement/specification. Watts, lumens and CCT alone do not identify PPF. |
| L2 | Emitting aperture, centre, aim, fixture count | A inputs | mm/m, deg | Measure installed bar positions/heights/orientation; housing dimensions may differ from emitting area. |
| L3 | Cosine-power exponent m, half-angle, cutoff | A Python / backend-dependent | Dimensionless, rad/deg | Beam distribution evidence, cutoff normalization, near-field extended-source sampling. Not a crop coefficient. |
| L4 | Leaf absorptance a_opt, reflectance rho, transmittance tau | A/P by engine | Fractions | Source wavelength and upper/lower face dependence; check a_opt+rho+tau=1 under the selected band convention. Black demo blades are not measured leaf optics. |
| L5 | Angle-dependent optics and scattering phase/BRDF | R/P | Model-specific | State what the selected backend supports. Do not claim Python's scalar tau captures angle-dependent transmission/reflection. |
| L6 | Sensor position, orientation, cosine response, calibration and spectral mismatch | A/P | Frame, mm/m, dimensionless | Independent PPFD reference and spatial samples; phone readings require a declared relative-only scope. |
| L7 | Photoperiod, actual on/off timing, time-varying output | A inputs | s/h, timestamps | Dated schedule/log rather than duration alone; synchronize with observation phases. |

### L2. Time and area aggregation

`DLI=1e-6*integral(PPFD(t) dt)` with seconds as the integration variable.

For constant illumination only: `DLI=PPFD*hours*3600*1e-6`.

`leaf_absorbed_flux = absorbed_PPFD * one_sided_area` only under the matched area/face definition.

Distinguish physical absorption from interception counts. A photon transmitted through multiple leaves may contribute to several interception events, but total physically absorbed photons must not exceed supplied photons in a closed accounting definition.

Reference ratios (`reading_i / reference_reading`) do not determine absolute photons or carbon fixation. Keep reference height, normalization population and measurement repetitions. Multiplying a ratio into an already calibrated light field again is double correction.

Numerical settings: source sampling, ray count, random seed, bounce depth, mesh resolution and timestep. Require convergence/seed studies; none is a biological coefficient. A 4.8M-ray run is evidence for a tested case, not a universal physical accuracy guarantee.

## 5. P4 — photosynthesis, respiration, allocation and mass

### C1. Active bounded NRH and daily carbon exchange

`A_g(Q)=[alpha*Q+Amax-sqrt((alpha*Q+Amax)^2-4*theta_NRH*alpha*Q*Amax)]/(2*theta_NRH)`

`C_gross=1e-6*M_C*integral(A_g(Q(t))*S(t) dt)`

`C_leaf_resp=1e-6*M_C*integral(R_leaf(t)*S(t) dt)`

`C_net=C_gross-C_leaf_resp`

M_C=12.011 g/mol is a conversion constant, not a fitted parameter. In the bounded daily implementation, S and coefficients are fixed within the day and light duration is explicit. No temperature/CO2 response follows merely from storing those columns.

| ID | Parameter | Inspected bounded demo value | Units/status | Review required |
| --- | --- | --- | --- | --- |
| C1 | Amax | 13.57 | umol CO2/m2/s; borrowed Merlice upper layer | Original parameter-file comment says mmol, function/bridge says umol. Resolve original fit and units; do not silently rescale. |
| C2 | alpha | .048 | mol CO2/mol photons; borrowed | Incident/absorbed basis, spectrum, fit preprocessing, active area, cultivar and age. |
| C3 | theta_NRH | .92 | Dimensionless curvature; borrowed | Joint identifiability with alpha/Amax; not leaf angle. |
| C4 | R_leaf | 0 in base fixture; 1 in named deficit fixture | umol CO2/m2/s; synthetic | Dark/day respiration, temperature, age, gross/net fit convention. Zero is not a physiological default. |
| C5 | Temperature/CO2/VPD response | Inactive in verified fixed-NRH baseline | P | Select a supported response/model and calibrate it; avoid unsupported multipliers. |
| C6 | Green/active tissue fraction or spatial classification | Unresolved | P | Full-outline area includes brown tissue; equal activity is not implied. Do not multiply correction twice if fit area already excludes it. |

Candidate organ maintenance: `R_m,i=r_ref,i*M_i*Q10_i^((T-Tref_i)/10)` with explicit rate/time/carbon units. Review r_ref, Q10, Tref, organ composition and overlap with leaf respiration. No automatic second subtraction after net leaf exchange.

If using FvCB, review Vcmax25, Jmax25, TPU25, Rd25, conductances, electron-transport curvature/efficiency, CO2/O2 conventions, VPD, leaf temperature and Arrhenius/peaked-response parameters. Select one exchange authority per leaf and document its gross/net output. Original VTC gross-output selection is not proof of a correct respiratory contract.

### C2. Bounded allocation and reserves

For daily potential structural increment d_i:

`D_i=d_i*f_C/eta`

`B=C_reserve,start+sum(C_net,i)-maintenance_not_already_included`

`F=min(max(B,0),sum(D_i)); C_alloc,i=F*D_i/sum(D_i)` for positive total demand.

`Delta M_i=C_alloc,i*eta/f_C; R_growth,i=C_alloc,i*(1-eta)`

| ID | Parameter/rule | Current example | Review required |
| --- | --- | --- | --- |
| C7 | f_C carbon fraction | .45 gC/gDM, synthetic | Organ/stage-specific composition and uncertainty; not F_CO2. |
| C8 | eta growth efficiency | .75 structural gC/allocated gC, synthetic | Organ construction costs and respiration; do not confuse efficiency with respiration fraction. |
| C9 | Potential d_i | .08 gDM/day per fixture leaflet | Deliberately synthetic, not observed growth. V3 requires stage/age-dependent sink demand. |
| C10 | Demand-proportional allocation | Active conditional subset rule | Root/shoot/reproductive competition, priority, saturation and limits. |
| C11 | Initial reserve, accessibility, capacity, mobilization | Supplied assumption | Seed storage versus mobile carbohydrate; no resets or replenishment without a transaction. |
| C12 | Birth cost, turnover, senescence, starvation | P whole-plant | No free initial organ mass; deficit must be visible. Halting a run is not a fitted plant-death response. |

Balance per plant and interval:

`initial reserve + signed exchange = final reserve + structural carbon increment + respiration not already included + explicit exports/losses`.

Include all tissue classes exactly once. A compound total and its leaflet components cannot both be counted as separate carbon stocks. In the bounded engine negative B produces an explicit unmet deficit and must not publish success.

## 6. P3 — development, geometry, angles and exponents

| ID | Model/form and parameters | Status/reference numbers | Review evidence and limitations |
| --- | --- | --- | --- |
| D1 | Thermal age: integrate f(T); T_base, upper thresholds, response shape | P/R; earlier 5.7 C and 18.63 degree-days/day were assumptions | Actual environment, crop stage and base-temperature definition. Setpoints are not measured thermal history. |
| D2 | Phyllochron and germination delay | R Merlice 37.9 and 206.3 degree-days | Define initiation vs emergence and true phytomer count. Fruit appearance delay 42.4 is not phyllochron. |
| D3 | First floral transition, truss interval, SP_STOP_RULE | P; original indefinite every-fourth rule must not silently remain | Longitudinal Micro-Tom observations; affected meristem, sympodial continuation and pruning scope. |
| D4 | Potential mass-growth curve: Wmax, tm, te and shape exponents | P/R | Select exact beta/logistic formulation, age units, organ class and domain; demand is not realized growth. |
| D5 | Logistic envelope X=Xmax/(1+exp(-k*(a-tm))) | R; internode length .072m/.019/222; leaf length .41m/.014/232 in Merlice | k has inverse-age units. Some original dimensions integrate a derivative. Do not overwrite funded dimensions with an age-only curve. |
| D6 | Leaf allometry A_cm2=a_AL*(L_cm)^g_AL | R: a_AL=.006, exponent g_AL=3.08 | Units embedded in coefficient; compound versus leaflet length/area and cultivar must match. |
| D7 | Constant-SLA scaling L,W proportional to (M/M0)^(1/2) | A bounded | Exponent 1/2 follows the geometry/SLA assumption, not a fitted tomato law. Measure matched area and dry mass by age/light. |
| D8 | Stem volume/dry density/taper; axial vs radial growth split | P | Fund both length and thickness; matched internode dry mass, diameter and length. |
| D9 | theta_insert=a_theta*(1-exp(-b_theta*L_cm)) | R: 81.5 deg and .045/cm in Merlice | Exact Chen-type equation, stem–petiole reference and initial offset; not phototropism. |
| D10 | Rachis bends alpha_i, CURVE_RATIO, age response | P/R; 1:2:2 is a prior | MTG A2 node count/signs; theta excludes a different terminal segment under stated coplanarity. Blade curl is distinct and on hold. |
| D11 | Phyllotaxis y=a+b*true_leaf_index; handedness, variance | P | >=5 consecutive known true leaves; unwrapping, axis orientation and uncertainty. No universal 137.5 deg or adopted wild-species spread. |
| D12 | Leaflet count by rank, aspect ratio, outline exponents K1/K2, widest-point fraction | R: aspect 2, K1=2,K2=2.2, fraction.6 | Target morphology and rank; middle-pair ramp; validate mesh area/shape. Fixed 13 leaflets is not adopted. |
| D13 | Intercalary/secondary area correction | P | No photons on nonexistent tissue; separate measured full-outline totals from supported optical geometry. |
| D14 | Inflorescence birth, flowers, reproductive sink and abortion | P | Truss appearance is not fruit set/yield. Separate flower/fruit stages and their resource costs. |
| D15 | Root compartment mass/demand/maintenance | P | Root/shoot partition, constrained substrate volume, initial hidden state. Not recoverable from shoot photos alone. |
| D16 | Seed reserves, initial organ ages, 30-day spin-up | P | Execute and check actual spin-up; setting age 30 is not a trajectory. Preserve uncertainty and original observations. |

Direction can change through reviewed developmental geometry without a light-seeking response. If future phototropism/gravitropism is proposed, independently define the sensed directional signal, target organ, lag/time constant, amplitude limits and interaction with mechanical posture. Do not add it implicitly to this integration.

## 7. P4 extension — fertilizer, two-layer water/ion balance and stress

### N1. Implemented composition and bookkeeping

For a mass-fraction w_j of element j in product mass m:

`element_mg = product_g * w_j * 1000`.

If label percentage p_j is supplied instead: `element_mg = product_g * p_j * 10`.

`P = P2O5 * [2*M_P/(2*M_P+5*M_O)]`.

`K = K2O * [2*M_K/(2*M_K+M_O)]`.

`concentration_mg_L=element_mg/solution_L; concentration_mmol_element_L=concentration_mg_L/atomic_mass_g_mol`.

These are stoichiometric/unit conversions, not fitted growth responses. Validate product label basis, liquid density where needed, final dilution volume, water ions, total-N versus nitrate/ammonium sums and unlisted composition status. Keep unknown species unknown.

Layer water balance: `W_new=W_old+inflow-outflow-evaporation-transpiration`.

Layer dissolved element balance: `M_new=M_old+inflow-outflow-uptake-sorption+desorption+explicit_other_terms`.

Account for retained ions and plant pools separately so transfers cancel in the system total. Evaporation removes water, not nutrient mass. In a well-mixed compartment, outflow carries concentration times volume; that is a declared mixing assumption, not measured transport physics.

| ID | Parameter/process | Status | Scientific review |
| --- | --- | --- | --- |
| N1 | Upper vermiculite/lower perlite geometry | A user scenario | 6x6 cm and 5/1 cm layers imply 180/36 mL only if internal filled dimensions. Geometric volume is not retained water. |
| N2 | Initial water, water capacity, drainage/inter-layer transport | A prescribed / P predictive | Water-retention curves, hydraulic conductance, layer interface, pot packing, irrigation location and drainage reuse. |
| N3 | Sorption/desorption, exchange capacity, initial release | A prescribed / P predictive | Ion-specific medium chemistry, pH and competing ions; no arbitrary zero terms. |
| N4 | Root uptake concentration response | P, not adopted | Possible saturating candidate U=Vmax*C/(Km+C)*root_basis*f(T,W,pH); define units/root basis, uptake caps, evidence and ion-specific coefficients before use. |
| N5 | Root amount/distribution/activity | P | Dry mass vs length vs surface area and layer occupancy; do not infer measured roots from canopy photos. |
| N6 | Tissue demand, critical concentrations, storage/remobilization | P | Organ/stage-specific nutritional requirement versus deficiency response; Mg/P/K/N cannot be treated as interchangeable. |
| N7 | Deficiency effects on photosynthesis, expansion and partitioning | P | Select response law and causal location; do not penalize the same deficiency twice without mechanism. |
| N8 | Salinity, ammonium toxicity, nutrient antagonism, pH responses | P | EC is not elemental composition. Require domain-specific response evidence, not a universal fertilizer-ratio multiplier. |
| N9 | Actual growth constrained jointly by carbon and nutrients | P | One final allocation/commit; actual consumption follows realized growth. Do not debit potential demand before limitation. |

The current nutrient module is a prescribed-flux ledger, not a predictive uptake model. Respect `nutrient_feedback_enabled=false` until the biological contract is adopted. Water/ion conservation can pass while a physiological response remains unvalidated.

## 8. Cross-project feedback and observation assimilation

| ID | Parameter/rule | Review required |
| --- | --- | --- |
| X1 | Time step, light quadrature, within-step geometry, birth ordering | Same interval across engines; no premature assimilation by unborn leaves or stale light after climate advances. |
| X2 | Existing P3 DLI response plus new carbon limitation | Explicitly choose their relationship; no automatic double light penalty. |
| X3 | State-update weight / observation covariance / process covariance | These are statistical model choices. Independent measurement error and bias evidence needed; do not default to trusting either forecast or image completely. |
| X4 | Area correction -> implied mass/reserve correction | A new observed area cannot silently create carbon. Track assimilation/reinitialization separately from physical process ledger. |
| X5 | Uncertainty propagation between scale, area, light and carbon | Correlations and common errors matter. Uniformly enlarging a leaf and independently drawing its mass may violate selected allometry. |
| X6 | Calibration split, fitting scope, forecast horizon, observation matching | Independent plants/times, no future-data leakage or refitting on evaluation outputs. Preserve untouched forecasts before later observation correction. |

A lower light level does not prove a particular new leaf direction. A good visual match does not identify physiological coefficients. A correct carbon ledger does not validate biological allocation, and a source-backed equation does not validate its transferred coefficient.

## 9. Priorities, measurements and requested reviewer deliverable

Review priority:

1. **Input meaning and units:** metric scale, full-outline vs active area, absolute light, photon/CO2 units, gross/net exchange.
2. **Resource closure:** respiration ownership, organ birth, reserves, all tissue pools and realized allocation.
3. **Morphology/development:** mass-area/length relations, thermal age, phyllochron, new organs and apex termination.
4. **Uncertainty and calibration:** parameter identifiability, shared measurement errors, held-out validation and numerical convergence.
5. **Future nutrient response:** complete ion/water science before claiming fertilizer-driven growth.

Minimum evidence families:

- Calibrated camera/scale and independent area/angle references for P1; same-organ labels and capture phase for tracking.
- Calibrated absolute PPFD and spatial light/fixture/optics measurements for P2; ratios remain useful but insufficient alone.
- Gas-exchange light/temperature/CO2 response and respiration where feasible; otherwise explicitly bounded literature priors.
- Matched organ dry mass, full-outline and optional green area, dimensions and repeated stage observations.
- Truss/apex follow-up through termination, not just an early short growth window.
- Water inputs/drainage/pot mass and, for ion validation, solution/tissue chemistry. Existing EC/pH/photos cannot validate each uptake flux.

Return `handoff/FOUR_PROJECT_SCIENCE_REVIEW_DECISIONS_2026-10-11.md` and a versioned JSON registry under a fresh `build/four_project_science_review_<date>_<id>/` directory. For each G/L/C/D/N/X ID record:

`model_id, equation, parameters, units, input_basis, output_basis, current_mode, value_or_null, source, exact_page_equation_table, cultivar, organ, stage, environmental_domain, evidence_kind, uncertainty, dependencies, double_counting_risk, calibration_data, verification_test, review_disposition`.

Dispositions: retain for conditional use, revise contract, needs measurement, defer, reject. Separate definition approval, software correctness and independent Micro-Tom validation. List the highest-impact changes and exact implementer-facing contracts, without editing another owner's active code or human records.

Do not assign substitute values simply to make the full chain run. A real-input run can remain unavailable while a labelled synthetic case verifies engineering. Keep those conclusions separate in every report.
