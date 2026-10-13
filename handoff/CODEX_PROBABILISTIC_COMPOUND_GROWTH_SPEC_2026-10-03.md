# Probabilistic CompoundLeaf architecture specification

Status: proposed scientific and implementation contract, prepared by Codex on 2026-10-03 in response to the user-selected design prompt. This is not a claim of Claude review, fitted parameters, implemented software or validated growth. The existing role split remains explicit: scientific choices below require scientific review before being adopted as biological claims; the contract distinguishes implementable mathematics from unsupported biological values.

## Task boundary and inspected baseline

The requested deliverable is this English specification for a measured-state-conditioned forecast over 30 calendar days. The work consists of source inspection, primary-source assessment, mathematical/interface definition and a requirement audit. It does not authorize production edits, model training, inference, simulation campaigns or messages to another chat. Generated future blocks must not replace existing measured leaves or become optical tissue.

The current source was inspected for the observation schemas and extraction/validation functions in `tools.compound_growth`, the explicit scenario assumptions in `tools.monthly_growth`, and the existing tissue/light separation. The following sections define the minimum additional responsibility, reuse boundaries, scientific assumptions, data contracts and validation. No numerical biological coefficient or uncertainty scale is adopted from a test fixture or another cultivar.

## 1. Decision and evidence limits

Implement an event-driven, context-sensitive stochastic graph grammar in Python with a small joint parameter sampler and analytic continuous transitions. Its graph semantics must be compatible with existing RGG vocabulary; a second XL execution engine is not required to establish the probability model. Use the existing GroIMP exporters unchanged only if a later authorized task requires graph transport. Keep a conditional Flow Matching interface, disabled for current real-data use. Flow Matching will replace the continuous conditional sampler, not measured geometry, organ identity, event semantics or optical eligibility.

This choice handles variable numbers of future compounds without requiring a neural model. A plant-level parameter draw shared across leaves and a sequential joint residual model encode dependencies; a deterministic decoder produces coherent trajectories. The initial distribution is explicitly conditional on supplied parameters and a specified environment scenario. It is not calibrated uncertainty until evaluated against independent trajectories.

Use the following explicit statuses:

| Status | Meaning |
| --- | --- |
| `unavailable` | A required measured anchor, biological parameter or probability definition is missing. Return named reasons and any independently eligible component. |
| `assumption_conditioned` | User-supplied or externally informed distributions enable calculation, without local calibration. |
| `evaluated_unaccepted` / `accepted_for_domain` | Independent evaluation exists; the latter additionally requires an explicit prospective acceptance record. Implementation or a source citation cannot set this status. |

Current facts do not support fitting appearance rates, growth curves, response coefficients, parameter covariance or observation noise. This specification therefore completes the algorithm and field definitions while leaving their numerical values unset. An unavailable numerical parameter is not an unfinished software design. An execution claiming calibrated real forecasts with those parameters absent would be incorrect.

### 1.1 Primary evidence and its permitted use

The following are the literature-derived statements used here; subsequent equations explicitly labelled proposed are design choices rather than extracted plant laws.

| Source and inspected material | Supported statement | Applicability and transfer limit |
| --- | --- | --- |
| [Loi and Cournede, stochastic L-systems](https://dmtcs.episciences.org/articles/3574), publisher abstract | Stochastic plant grammars can describe organ-count distributions through branching/differentiation processes. | Mathematical/GreenLab context, not a target-tomato waiting-time or angle distribution. Full article download failed; no detailed formula is adopted. |
| [Prusinkiewicz, crop architecture with L-systems](https://library.wur.nl/ojs/index.php/frontis/article/view/1369), indexed publisher abstract | Structured parameters and information transfer support context-dependent architectural models. | Formalism precedent only. Direct publisher retrieval failed; no crop coefficient or equation adopted. |
| [Butturini et al., dwarf tomato FSP](https://academic.oup.com/insilicoplants/article/8/1/diaf024/8402035), accessible abstract, introduction, model overview and parameter table | MTG/RGG architecture is implemented in GroIMP for controlled-environment dwarf tomatoes. The reported model has explicit architecture and determinate-growth parameters. | Relevant architectural precedent. Full methods/cultivar details were not recovered in this run; repository PDF timed out. No numerical value is transferred. It does not validate this proposed block-distribution model. |
| [Smolenova et al., tomato digital twin](https://edepot.wur.nl/706749), full 20-page author-institution PDF, sections 2.1, 2.2, 2.3, 2.5 and discussion | Phytomer appearance uses rewriting rules; leaf area and internode dimensions use fitted expansion relationships. Image-based updating is demonstrated for plant height. | Baseline parameterization uses Merlice; experiments also include other greenhouse cultivars. Single-stem greenhouse management differs from the target dwarf plant. Their thermal clock, coefficients and height-update results are not transferred as local block-forecast evidence. |
| [Lipman et al., Flow Matching](https://arxiv.org/html/2210.02747v2), sections 2-4 | Conditional probability paths provide a vector-field regression objective and ODE-based sampling. | General generative mathematics, not plant-growth evidence. The conditional model and decoder below are proposed applications. |
| [Flow Matching Guide and Code](https://arxiv.org/abs/2412.06264), author abstract | General reference covering FM foundations and extensions. | Full PDF exceeded retrieval size and HTML retrieval failed; no additional method depends on it. |

Local evidence archive: `build/probabilistic_compound_design_20261003/sources.json` records download outcomes. The retrieved digital-twin PDF and extracted text are archived there, with the PDF SHA256. Only short supported conclusions are used; missing supplementary parameters remain missing.

### 1.2 Biological rule register

| Rule | Selected mathematical representation | Evidence and unresolved values |
| --- | --- | --- |
| Successive compound appearance | Positive residual/inter-event times plus an optional absorbing stop event, section 4 | Sequential organogenesis is supported by the grammar/tomato sources. Lognormal waiting times and the stop model are proposed statistical approximations. Waiting-time means, dispersion and stop probabilities require scenario assumptions or local appearance intervals. |
| Relative placement | Stem-attached local frame and conditional joint relative traits, sections 2 and 4 | Tomato sources motivate organ order and architecture, not this regression/covariance. Current confirmed positions supply anchors/features; temporal records and applicable priors supply coefficients. |
| Dimension expansion | Anchored saturating remaining-growth function, section 5 | Fitted bounded expansion in the digital-twin study motivates testing saturation. The exact exponential remaining-growth function here is a smaller proposed surrogate, not that study's fitted logistic model. Rates and remaining expansion are unset. |
| Direction and spread change | Smooth local rotation and signed changes toward nonnegative width targets, section 5 | No retrieved source establishes a target-cultivar directional law. This is a kinematic conditional model to compare with persistence/recent-change. No causal phototropism claim. |
| Stem and attachment movement | Measured segment directions with uncertain segment elongation, section 5 | Internode elongation is supported as a state variable. Fixed segment direction is a simplifying assumption requiring validation. Measured stem bending is preserved at initialization. |
| Environment dependence | Explicit scenario clock and optional fitted/assumed coefficients, section 3 | Temperature-dependent development in other cultivars does not supply the target base temperature or response. Calendar time is the first supported clock; physiology is not inferred. |

## 2. Observation and relational state

### 2.1 Immutable evidence and eligible state

Reuse `tools.compound_growth.load_history` and `extract_compound_state` for existing `compound-observations-1` inputs. Preserve source hashes, geometry references and original tables without modification. A forecast copy always has `eligible_state=false`, `validated_growth=false` and `suitable_for_ppfd=false`. Do not feed it back through an observed-data loader.

The existing adapter requires timezone-aware observation times, confirmed identity and stable board-frame evidence, and supported full-axis data. It does not establish those facts from labels. Do not weaken it to obtain more forecasts. Date-only source records remain date-only; the model may produce a separately declared relative-day assumption scenario, but cannot add midnight as a fabricated observation time. Unknown acquisition times cannot enter chronological fitting as exact times.

The existing T1/T2/T3 run copies describe different plants captured on 2026-10-02, not successive dates of one plant. They cannot identify temporal growth rates. Any additional candidate history needs its own plant/session/time provenance check before fitting.

Some measurements may be valid although the full compound state is ineligible. Return such values as evidence with field-level availability. Do not use a partial petiole as a full axis. Proposed relationships remain proposals. Raw measurement records and any latent/noise-adjusted state are separate objects.

Minimum additional parent-axis evidence consists of a directed measured stem polyline, attachment-to-segment correspondence, and a measured apex if future attachment coordinates are requested. Projecting an attachment onto that polyline is a derived operation: retain the residual distance, correspondence review and explicit geometric tolerance. An unsupported projection or uncertain stem direction makes its relational quantities unavailable; it is not repaired automatically.

| State field | Meaning and units |
| --- | --- |
| `plant_id`, `parent_stem_id`, `compound_leaf_id`, `session_id` | Existing observed identifiers and their provenance; never assigned from visual rank alone. |
| `observed_at`, `frame_id`, `coordinate_frame` | Exact source time and coordinate identity; existing measurements use `board_mm`. |
| `axis_stations`, `rachis_points_mm` | Existing measured station correspondence and supported axis shape. Do not resample differently across dates and call that growth. |
| `attachment_xyz_mm`, `direction_unit_xyz`, `rachis_arc_length_mm` | Derived by existing `axis_traits`; signed elevation and wrap-safe azimuth are display summaries. |
| `extent_stations`, `left_extent_mm`, `right_extent_mm`, `transverse_unit_xyz` | Measured envelope descriptors with explicit transverse reference; not tissue. |
| `supported_area_cm2`, `area_basis_id`, `estimated_total_area_cm2` | Existing separate area semantics; a changing support basis invalidates a growth comparison. |
| `material_node_id`, `predecessor_id`, `order_status`, `adjacency_status` | Derived/reviewed stem attachment and ordering evidence. Consecutive visible blocks need not be consecutive biological nodes. |
| `development_state`, `age_interval_days` | Stage or age evidence; unknown remains null. Neither size nor rank supplies an exact age. |
| `state_source`, `shape_ref`, `shape_hash` | `observed`, `estimated_latent`, `inferred_preexisting` or `predicted_future`, with immutable shape linkage. |

Existing measured shape is retained at the forecast origin even if a simplified descriptor is needed for probability calculations. The probability model does not replace it with a generic leaf.

### 2.2 Local frames and relational features

At each directed stem segment, let `e3` be its measured tangent. Project an explicitly recorded board-reference vector into its normal plane and normalize it to `e1`; let `e2=e3 cross e1`. The reference vector and numerical degeneracy tolerance are configuration fields, not guessed from the current leaf arrangement. Transport the reference along the measured polyline using the minimum rotation between adjacent tangents. Antiparallel tangents or a degenerate reference require explicit reviewed frame evidence; do not choose an arbitrary axis.

`Q=[e1,e2,e3]` maps stem-local vectors to board coordinates. This is a representation of measured geometry, not cross-session registration. Identity/frame checks must reject plant movement relative to the board or unresolved T3 capture-group motion. Sheet-to-board or board-to-grow conversion remains in existing helpers and is not duplicated.

Use this fixed candidate feature dictionary; include a feature only when its evidence is present and its coefficient is explicitly supplied:

- Parent axis and observed growth-stage category.
- Local order index, only where node order and missing-node status are resolved. It is not an age estimate.
- Latest confirmed adjacent attachment distance, normalized by a supplied length scale.
- Previous compound direction in the stem-local frame; `sin` and `cos` of relative azimuth where defined.
- Previous measured axis length and left/right extents, and ratios for confirmed comparable neighbors.
- Present/missing feature indicators and declared environment-scenario fields.

Numerical standardization is fitted only on training plants, or supplied as an explicit scenario setting. Missing continuous features enter the design matrix as zero only after centering, together with their missingness indicator; this is a regression encoding, never a zero-valued measurement or exported imputation. Corresponding missingness coefficients must be specified. With no supported adjacent pair, use a separately supplied intercept-only prior; do not pretend a gap is an internode length. Raw mean angles are prohibited; relational directions are calculated as vectors or circular differences.

## 3. Time and the probability target

Let `t` denote biological elapsed calendar days from the explicit forecast origin, `s` denote FM interpolation time in `[0,1]`, `O` the observations available at the origin, `E` a declared environment scenario, `A` associations/topology hypotheses, `Theta` parameters and shared plant effects, `B` future appearance events, and `Y(t)` continuous block/stem state. The target is:

```text
p(A, Theta, B, Y[0:30] | O, E, model_version).
```

Use nested sampling: draw a model/parameter particle and any supported observation-state hypothesis; draw events and jointly related block variables; decode the entire trajectory at requested times. Retain `parameter_particle_id`, `trajectory_id`, weights and model/scenario labels. Alternative environment scenarios are reported separately unless the user supplies probabilities over them. Unweighted alternative hypotheses are sensitivity scenarios, not a probability mixture.

First implementation uses calendar days. An optional explicitly assumed piecewise-constant development multiplier `m(t)>=0` defines `a(t)=integral_0^t m(u)du` in development days. `m(t)=1` is the identity of the calendar clock, not a crop response coefficient. Different future environment values do not change this clock unless a declared response specification maps them to `m`. Do not automatically reuse the monthly scenario's multiplicative response as physiology. Reject use outside supplied response domains and missing values required by an enabled response.

Events are sampled on the selected clock, then inverted through `a(t)`. A zero-clock interval produces no development events; it is skipped during inversion. Store both elapsed calendar time and elapsed development. Sample events and trajectory parameters once per trajectory. Output frequency must not trigger new random draws.

## 4. Stochastic graph grammar

### 4.1 Symbols and event semantics

Use only `Plant`, `Axis`, `Apex` and `CompoundLeaf`; an `Axis` contains material nodes/segments, so a separate full internode object hierarchy is unnecessary. Existing observed lateral axes are supported independently with shared plant effects. The first version does not predict the initiation of entirely unobserved lateral axes. Declare `topology_scope=provided_axes`; whole-plant completeness is unavailable if additional axes may emerge. This is a stated applicability limit, not an assertion that branching will not occur.

The event is **appearance of a distinguishable compound leaf at its parent apex under the specified multiview observation protocol**, not microscopic primordium initiation. Event records contain a last confirmed not-yet-appeared time and first confirmed appeared time where available. Occlusion or failed detection is not negative evidence. A block detected without a valid earlier absence observation is left-censored or origin-ambiguous, not assigned a birth at detection. This operational endpoint requires a versioned review protocol but no invented size threshold.

Each apex has `active`, `stopped` or `unknown` status. Unknown growth habit remains a model uncertainty/scenario choice; a dwarf label does not establish a node cap. A known stopped apex cannot produce another event without a new explicit state observation.

### 4.2 Event and joint-trait sampler

The following is a proposed statistical family, not a calibrated tomato law. A parameter particle contains all means, feature coefficients, covariance matrices and any mixture weights, each with an evidence status. No unspecified variance becomes zero and no unspecified categorical distribution becomes uniform.

At each active apex, first sample a stop decision with probability `logistic(c_stop dot phi)`. A stop yields an absorbing event at infinity. A confirmed active/apical state may condition this decision according to the reviewed protocol; it must not be used to assert that future stopping is impossible.

Conditional on continuation, sample a joint latent vector:

```text
z_k = mu + B phi_k + b_plant + r_k
b_plant ~ Normal(0, Sigma_plant)
r_k = rho * r_(k-1) + eta_k
eta_k ~ Normal(0, Q),  abs(rho) < 1
```

`rho` is one scalar for the minimum model; the residual vectors and covariances are joint across enabled traits. Initialize `r_0` from an explicitly supplied distribution. A stationary initialization may use `Q/(1-rho^2)` only when stationarity is an accepted assumption. Mixture components may be supplied as parameter particles rather than introducing another model family. The shared plant effect and sequential residuals induce cross-block dependence; deterministic trajectories induce cross-time dependence. Fit or supply those dependencies, rather than claiming them from randomization alone.

The event-time coordinate gives `Delta a_k = exp(z_wait_k)` in development days after applying its declared dimensional reference. Other coordinates represent positive birth dimensions, remaining expansions/rates, local angular offsets and next terminal-segment growth. The exact enabled coordinate list and transformations are in section 9. Direction/size and waiting time may be correlated; if a two-stage sampler is used, sample waiting time first and use the conditional Gaussian for the remaining coordinates, not the unconditional marginal.

For a partition `(z_wait,z_geom)` with nonsingular wait variance, use conditional mean `mu_geom + Sigma_geom,wait / Sigma_wait,wait * (z_wait-mu_wait)` and conditional covariance `Sigma_geom,geom - Sigma_geom,wait Sigma_wait,geom / Sigma_wait,wait`. A specified point-mass wait uses its explicitly defined conditional geometry model; do not divide by zero or insert jitter. Validate covariance symmetry/positive semidefiniteness and reject materially invalid inputs.

At the forecast origin the previous event's exact time is usually unknown. Use a separately specified **residual-to-next-event** distribution. Do not use a full inter-event distribution as if a leaf appeared at the origin. If previous event age is known, use the inter-event law conditioned on survival to that age. A supplied residual prior may depend on current apex/leaf-stage evidence; missing residual parameters make appearance timing unavailable. For lognormal waiting law `F`, survival over `h` after known age `a0` is `(1-F(a0+h))/(1-F(a0))`, conditional on the active branch. The stop mixture adds its point mass at infinity.

### 4.3 Rewrite and scheduling contract

| Rule | Predecessor and context | Successor and side effect |
| --- | --- | --- |
| R0 initialize | Measured `Plant/Axis/CompoundLeaf` graph and supported apex evidence | Copy immutable measured state references; initialize per-trajectory latent parameters without changing day-zero geometry. |
| R1 schedule | Active apex, context, residual/inter-event prior | One pending appearance time or an absorbing stop. A time beyond the horizon is retained as censored future, not a failed event. |
| R2 appear | Pending event reached on the selected clock | Promote the current terminal endpoint to a material node; attach one predicted CompoundLeaf with a scenario-local ID; retain the previous segment's growth state; start a new zero-length terminal segment at the same point and schedule the next event. |
| R3 advance | Existing segments/blocks over an interval | Evaluate section 5 at elapsed development; no rewriting of measurements and no per-output-time random sampling. |
| R4 stop | Stop event | Retain the apex and existing blocks; disable future R2 events on that apex. This is not simulated death or leaf loss. |
| R5 observe | New evidence and association decision | Perform section 7; preserve the prior forecast and start a versioned updated origin. |

Process event times chronologically, including multiple events within one output day. Break equal-time events on different axes by stable axis ID; they share the pre-event plant context so arbitrary processing order does not change the law. A new block's growth starts at its actual sampled event, not the start of the day. Positive waiting times prevent simultaneous events on the same axis; detect numerical underflow and resource exhaustion rather than silently truncating a trajectory.

Before birth, a future ID has `existence=not_yet_appeared`; its geometry is null, not a zero-sized observed leaf. Its label is stable within the trajectory. The kth future block is a rank-conditioned prediction, not proof of the same physical identity across all samples.

## 5. Continuous state and preservation of measured shape

These transitions are proposed low-parameter surrogates for testing. They are deliberately not presented as the cited papers' physiology. All parameters are sampled jointly at initialization/birth and held consistent along the trajectory.

Define `H(k,a)=1-exp(-k*a)`, with nonnegative rate `k` in inverse development days and elapsed development `a>=0`. Compute with `-expm1(-k*a)` for numerical stability. A supplied zero rate explicitly represents no change. Do not replace unknown rates with zero.

### 5.1 Stem elongation and attachments

Represent the measured stem by material segments split at confirmed attachments, retaining every supported polyline bend. Each segment j has measured start length `l_j0`, measured direction `e_j` and sampled remaining elongation `D_j>=0`, rate `k_j>=0`:

```text
l_j(a) = l_j0 + D_j H(k_j,a)
P_j(a) = P_base + sum_(h<=j) e_h l_h(a).
```

Splitting a measured segment by a derived attachment projection does not create a new independent measurement. The basal reference is fixed to its confirmed frame. Existing attachment points move with accumulated lower segment extension. This replaces the monthly demo's fixed existing attachments. Segment directions remain fixed in this minimum model; their observed initial bending is preserved. Parent rotational growth and new bending remain unavailable, not attributed to leaf motion.

Only the root-axis basal reference is fixed in the board frame. An observed lateral axis uses its confirmed attachment on the parent axis as `P_base(t)` and inherits that translation; reject cycles or unsupported parent attachments. Preserve each measured leaf attachment's offset from its reviewed stem projection: `A(t)=P_projection(t)+Q*offset_local`, with the offset computed from the original measured `A0`. Thus accepting a small projection residual does not move the observed attachment at the origin. Store the offset and its evidence explicitly.

At an appearance event, the growing terminal segment becomes a retained material segment. It keeps its original growth clock and remaining-capacity law; it does not restart or instantly stop. The newly appended terminal segment starts at length zero and follows `D_new H(k_new,a_since_birth)` along the supplied terminal tangent. This prevents a discontinuous apex jump. Future block attachment follows its material node as lower segments continue expanding.

If the measured apex or supporting stem polyline is unavailable, counts/event times may still be eligible under supplied event parameters, but new attachment coordinates are unavailable. No artificial stem is inferred from leaf count. Full spatial forecast status must reflect this failure.

### 5.2 Existing compounds

Let measured attachment be `A0`, measured axis points `P_j0`, measured arc length `L0>0`, local frame `Q`, and modelled parent attachment `A(t)`. Define a leaf-local smooth rotation `R_leaf(a)=Exp([omega]_x H(k_rot,a))`, where `omega` is a rotation vector in radians and `[ ]_x` is its skew matrix. The existing parent's rotation is identity in this model; do not estimate it implicitly from leaf rotation.

```text
L(a) = L0 + D_L H(k_L,a)
P_j(a) = A(t) + Q R_leaf(a) Q^T (P_j0-A0) * L(a)/L0.
```

Thus every measured axis point is recovered exactly at `a=0`, and its current normalized shape is preserved. This is a predicted similarity deformation, not a measured future shape; changing curvature is outside this minimal decoder. Keep measured tissue-mesh files untouched. A transformed display mesh, if ever requested separately, would require predicted provenance and would not inherit optical approval.

Implement the origin query as a direct copy of measured arrays, avoiding floating-point roundoff from an otherwise identity matrix calculation. Predicted displacement is evaluated only for positive elapsed time.

For each supported extent station and side, use `w(a)=w0+(w_target-w0) H(k_w,a)`, with both endpoints nonnegative. This allows spreading or folding rather than forcing monotone envelope width. Transport the measured transverse axis with the same rotation. Use the measured extent station/profile definition; do not fill gaps between leaflets.

Comparable supported tissue area may use `A_tissue(a)=A0+D_A H(k_A,a)` only for an explicitly declared active-expansion/no-loss scenario and an unchanged coverage basis. Total area requires its own evidence. With missing or changing area basis, area-growth output is unavailable even when axis prediction succeeds. Neither axis length nor spread automatically produces tissue area.

No senescence, abscission or damage model is introduced. The applicability field is `leaf_retention_assumption=no_loss_over_horizon`, with evidence/assumption provenance; it must not be silently asserted for an unknown biological stage. If that condition cannot be supplied, retained-leaf projections are conditional scenarios, not complete leaf-count forecasts.

### 5.3 Newly appeared compounds

At birth, sample positive initial axis length and nonnegative side extents, a local direction and growth parameters conditional on the parent and supported predecessor context. A straight axis from attachment to sampled tip is an **envelope descriptor only**, never an observed rachis or leaflet skeleton. Use side-width profiles only where an explicit profile definition is supplied; otherwise export scalar maximal extents rather than fabricating station shapes.

Use local azimuth `alpha=wrap(alpha_reference + delta_alpha)` and elevation `beta` relative to the parent frame, then `d=Q[cos(beta)cos(alpha), cos(beta)sin(alpha), sin(beta)]`. A confirmed predecessor provides `alpha_reference`; otherwise an absolute local-direction prior is required. A vertical predecessor has no azimuth and cannot supply one. The angular transforms and provenance are part of the prior contract, not a fixed phyllotactic angle.

Use the same continuous expansion/rotation laws from the sampled birth state. Birth geometry must represent the chosen appearance endpoint, so zero full-axis length is not silently substituted for a distinguishable leaf. Area is optional and separate. Do not generate leaflets or assign their count.

### 5.4 Parameter transforms and support

Each enabled latent coordinate has a declared name, physical unit, transform and dimensional reference. For a strictly positive quantity use `x=x_ref*exp(z)` with `x_ref>0` in the same unit; invert with `log(x/x_ref)`. For a bounded quantity use explicitly supplied endpoints and a logistic transform. Zero remaining growth or a zero rate is an explicit inactive component, not an approximation to missing data. A mixture with exact zeros requires supplied component probabilities. A deterministic assumption is allowed but must be declared as such.

Use an unwrapped azimuth increment in radians, wrapping only the decoded angle; elevation may use `beta=(pi/2)*tanh(z_beta)`. This elevation map excludes the exact poles: an observed vertical leaf is retained exactly, while a proposed distribution needing probability mass at a pole needs a separate declared component. Rotation vectors have radian units. Do not regress raw wrapped angles through their discontinuity. Publish the coordinate order and transform version alongside every covariance matrix.

The joint latent vector covers only enabled responses: waiting time, birth axis/extent descriptors, direction, remaining axis/extent/segment expansion, their rates and any leaf rotation. Area is included only with independent area evidence. Existing-leaf remaining-growth parameters use a separately specified conditional block of the same joint family, conditioned on their measured states. Do not reuse a newborn-leaf prior for mature measured leaves. Shared plant effects may couple these draws; unsupported cross-covariances remain unidentified. Event count and size dependencies arise from their joint draw, not independent daily noise.

## 6. Bounded Flow Matching extension

**Current decision: disabled.** No longitudinal training set or identifiable growth-parameter targets have been supplied. A flexible sampler is useful only if independent observations show that the smaller grammar-conditioned joint distribution misses relevant dependencies and a trained replacement improves held-out probabilistic forecasts.

Keep the event mechanism in section 4. For this extension, sample one next event and its stop decision using that mechanism, then condition a continuous sampler on the sampled waiting time, current context and shared plant latent. Its output replaces the conditional Gaussian draw of continuous traits for that event. It must not resample the event, invent additional nodes or overwrite observed geometry. Repeated calls are sequentially conditioned on the sampled prior block and a shared plant latent; their decoded trajectories remain coherent. Existing-block transitions need their own observed-state conditioning flag and eligible training targets. This sequential interface avoids a padded maximum plant size and silent truncation of leaf counts.

### 6.1 Learning and sampling contract

Let `c` contain only information available at the forecast origin plus the current simulated history: measured-state features and masks, local-frame geometry, explicit environment scenario, forecast horizon and remaining horizon, sampled event wait, block role, shared plant latent and previous sampled state. Use a small multilayer perceptron for the conditional vector field; concatenate fixed-size context, latent coordinates and a scalar-time embedding. No graph transformer, image encoder or model search framework is required. Network width/depth, embedding definition, optimizer, learning rate, batch size and stopping rule are training settings selected on training/validation groups and recorded explicitly, not biological constants.

The target `y1` is a standardized vector of identifiable continuous decoder parameters in the transformed coordinates of section 5.4. Repeated observations must support those parameter estimates. Record estimation uncertainty and identifiability failures; do not manufacture target rates and asymptotes from a single snapshot. A future alternative trajectory-target decoder would be a separate version, not an undocumented change of target.

For the minimal independent linear conditional path, draw `y0 ~ Normal(0,I)` and `s ~ Uniform(0,1)` independently of a training pair `(y1,c)`:

```text
y_s = (1-s)y0 + s*y1
L(theta) = E[ ||v_theta(y_s,s,c) - (y1-y0)||^2 ].
```

This is the selected conditional vector-field regression construction based on [Flow Matching](https://arxiv.org/html/2210.02747v2). It is not a claim of globally optimal transport coupling. At inference, integrate `dy/ds=v_theta(y,s,c)` from `s=0` to `1`, inverse-standardize and transform, then decode biological trajectories using section 5. Biological elapsed time `t` is never replaced by ODE interpolation time `s`. Sample one parameter vector per block transition, not an unrelated shape at each day.

The future adapter uses a named ODE solver with recorded tolerances, software version and maximum evaluations; solver failure returns an invalid sample and reason. Training and sampling masks must agree. Positive/bounded transforms and the grammar enforce their respective constraints by construction. Rejecting or projecting additional geometric constraints changes the output distribution: report the rule and rejection fraction, and evaluate the resulting distribution. Do not hide an empirical correction behind the original FM density. No hard overlap rejection is included: real compound envelopes can overlap.

### 6.2 Activation gate

Activation requires time-corresponded repeated observations, supported event intervals, frame/identity continuity, identifiable targets, declared environment coverage and independent plants for evaluation. There is no asserted sufficient number of plants. Demonstrate learning curves, fit stability and out-of-domain detection; select complexity from evidence. Compare the same grammar with and without FM using the same origins, scenarios and evaluation protocol in section 10. Improvement must include proper scores with acceptable coverage, failures and runtime, not only visual diversity or training loss.

Synthetic grammar data may test interfaces or a separately labelled surrogate experiment. They do not validate tomato growth or correct generator bias. Neither synthetic pretraining nor a training run is part of this assignment. No checkpoint means `sampler=flow_matching` returns `unavailable`, without silently using random neural weights.

## 7. Uncertainty and observation updates

### 7.1 What an ensemble represents

| Component | Representation and limitation |
| --- | --- |
| Current measurement/identity | Raw measured state is immutable. Supported latent-state or association hypotheses require explicit likelihoods/weights. Without them, condition on the measured state and report measurement uncertainty as unquantified. |
| Future biological variation | Event and joint-trait draws conditional on one parameter particle. This is assumed variation until validated. |
| Parameter uncertainty | Weighted parameter particles from an identified posterior, supplied prior, or explicitly declared scenario ensemble. Fixed coefficients do not represent parameter uncertainty. |
| Model-form uncertainty | Report the fixed model's limitations. Alternative models are separate sensitivity runs unless their probabilities are justified. No automatic uniform mixture. |
| Future environment | Separate scenario-conditioned results; aggregate only with supplied scenario probabilities. Unsupported response coefficients do not acquire meaning because controls are adjustable. |

Report which components were included. Nominal quantiles from assumed distributions are assumption-conditioned intervals, not calibrated coverage. More samples reduce Monte Carlo error, not structural bias. Distinguish `unquantified` uncertainty from a justified zero variance.

### 7.2 One initial update method: finite-bank Bayesian reweighting

Retain a weighted bank of parameter/trajectory/association particles. Given a new observation batch `D`, update compatible particles by:

```text
log w_i_new = log w_i_old + log p(D | particle_i, observation_model)
w_i_new = exp(log w_i_new - logsumexp(log w_new))
ESS = 1 / sum_i(w_i_new^2).
```

Use this single method initially; no automatic neural retraining, particle rejuvenation or second filter is required. Report effective sample size, support loss and Monte Carlo limits. The finite bank cannot recover hypotheses absent from its support. If all likelihoods are zero or nonfinite, return `update_incompatible`; never normalize to uniform. Regenerating a subsequent forecast from the reweighted parameter particles is a new forecast run, not retroactive repair of the old run.

The observation model is explicit and optional. For matched continuous traits, a multivariate normal residual may be used only with a supplied/estimated covariance, units, supported trait subset and validated frame. Angles use wrap-safe tangent-plane directional residuals in radians; this small-error likelihood is unavailable near its antipodal singularity. The covariance must describe measurement plus any explicitly modelled residual discrepancy without counting process variation twice. A normal likelihood is a selected approximation, not an assumed noise scale. Covariance must be positive definite on the scored coordinates; exact constraints are handled separately, never by adding arbitrary jitter.

For an interval-confirmed event `(l,r]`, use its interval likelihood; for an explicitly confirmed absence through `c`, use survival through `c`. At particle level these are indicators of the stored event time, or an analytically integrated conditional likelihood when available. Occlusion alone contributes no absence likelihood. Probabilistic detection/false-positive terms are enabled only with their own measured probabilities and protocol. No such model means an uncertain non-detection is uninformative.

Association handling is fixed as follows:

| New evidence | Required behavior |
| --- | --- |
| Confirmed match | Score comparable fields, retain the prediction-to-observation association, and anchor the next forecast at the new measured geometry/time. Preserve the earlier forecast and its errors. |
| Ambiguous match | Keep candidate associations. Marginalize likelihood over supplied association probabilities, retaining posterior alternatives. If those probabilities are unavailable, return separate unresolved hypotheses without a claimed combined probability. Never force nearest-neighbor identity. |
| Missed or occluded block | Retain its latent/predicted status and record visibility. Do not infer death, zero area or a stopped apex. Use negative evidence only where absence was actually established. |
| Observed block with no prior match | Add its measured identity/state after normal extraction checks; record `unmatched_observation`. Its appearance interval is unknown unless established independently. If outside the old ensemble support, flag model mismatch; do not relabel it as a successful prediction. |

After reweighting, create a new origin-state version from the new measured observations plus explicitly unresolved latent components. Refresh graph order only where confirmed. Continue known latent ages/event histories conditionally; unknown ages remain intervals or unknown. Growth parameters governing remaining expansion must be recomputed for the new anchor so that previously accumulated expansion is not added again. For the exponential decoder after development increment `da`, the remaining increment becomes `D_new=D_old*exp(-k*da)` and the local age resets to zero; a new measured dimension replaces the predicted anchor. Apply the analogous residual-to-target update to widths/rotations, using the recorded local frame, without moving the measurement to fit the old prediction.

For widths, carry the remaining signed increment `(w_target-w_old_anchor)*exp(-k*da)` and add it to the newly measured anchor to define the new conditional target; if that produces a negative target, flag the particle as incompatible rather than clipping. For rotation along the same fixed local rotation vector, use `omega_new=omega_old*exp(-k_rot*da)` after consistent frame transport. Changed/unsupported frames require new reviewed correspondence. Retained event particles are shifted to the new origin and conditioned on observed history; do not reset every apex to a full inter-event wait merely because an update occurred.

Only declared uncertain parameter particles are reweighted. Environment scenario weights change only when scenario probabilities and an appropriate likelihood exist; otherwise scenarios stay separate. With new observations but no justified likelihood, allow deterministic re-anchoring and discrepancy export, explicitly `parameter_update=unavailable`; do not call unchanged assumed weights a posterior. With no new observations, preserve the prior forecast, model and weights. Any elapsed-time query is a view of that run, not a new calibration.

## 8. Optical boundary and reuse

Envelopes, swept regions and spatial probability summaries are not leaf tissue. Set `surface_role=compound_envelope`, `optical_eligible=false` and `suitable_for_ppfd=false` on every future block output. Do not derive opacity, transmittance or occupied tissue fraction from spatial occurrence probability. No envelope triangle is exported to light transport.

Measured leaflet/tissue surfaces retain their separate IDs, gaps, supported-area basis and optical review records. Compound-level forecasting does not merge those surfaces. Future light eligibility would require a separate reviewed tissue-allocation model, surface geometry and optical assumptions; this task defines only a nullable `future_tissue_ref` and unavailable eligibility reason. No tissue generator or renderer is included.

| Existing code | Reuse boundary |
| --- | --- |
| `tools.compound_growth.load_history`, `extract_compound_state`, `axis_traits` | Read and validate existing observations/traits. Validate histories per confirmed compound, not as one mixed-identity history. Preserve original source hashes. |
| `tools.compound_growth.forecast`, `evaluate_compound_forecasts` | Reuse eligible persistence/recent-change comparisons for existing compounds. They do not supply a future-organ event model. |
| `tools.leaf_light.common` | Reuse CSV/JSON IO, numeric checks, hashes and output-directory conventions where compatible. |
| `tools.monthly_growth` | Inspect scenario provenance and controls for compatibility; do not silently adopt its response coefficients or fixed-attachment assumptions. No viewer changes. |
| `tools.growth_simulator` | Procedural examples only; no display anatomy, test value or environment coefficient enters biological priors. |
| `tools.compound_surface`, `tools.plant_light_bridge` | Preserve surface audits and light eligibility gates. The new model does not bypass them. |
| `tools.groimp_structure_export` | Reuse graph vocabulary/IDs if export is later requested. Do not duplicate the renderer or require native GroIMP for this sampler. |
| `tools.groimp_static_verify`, `tools.groimp_bridge` | Existing frozen transport/verification helpers remain unchanged. They do not validate forecast biology. |
| `tools.plant_traits`, `tools.plant_structure` | Read outputs only through their documented provenance. A photo-area proxy is not direct tissue area; unsigned structural elevation is not the signed direction contract here. |

## 9. Minimal implementation contract

Add one proposed module, `tools/probabilistic_compound_growth.py`, and targeted tests under the existing tools-test convention. Keep types as validated dictionaries/tables initially; no plugin registry, database, service or generic simulation framework. A future FM adapter can be a separate module only when authorized and data-ready. All functions below are proposed, not currently implemented.

### 9.1 Functions

| Function | Input -> output / failures |
| --- | --- |
| `prepare_origin(history_dir, structure_path, origin_config)` | Existing observed bundle plus reviewed parent geometry -> origin state, supported relations, hashes and field-level eligibility. Unknown IDs/times/frames are reported; contradictory evidence fails validation. |
| `validate_model_config(config, origin)` | Versioned config -> enabled operations, missing requirements and validated parameter/transform order. Invalid probabilities, units, covariance or domains fail; missing inputs yield unavailable components. |
| `sample_forecast(origin, config)` | Eligible origin and explicit distributions -> joint event/trajectory bank plus status/provenance. No fitting or observation-table mutation. |
| `decode_trajectory(trajectory, elapsed_days)` | Stored events/parameters -> analytic states at sorted requested times in `[0,30]`, including event existence. Queries do not draw randomness. |
| `summarize_forecast(bank, summary_config)` | Bank -> weighted occurrence/count distribution and conditional scalar/directional summaries with effective sample counts. Preserve samples/modes rather than constructing a mean plant. |
| `update_forecast(previous_run, observation_dir, associations, observation_model)` | New observed evidence -> immutable update record, posterior weights or explicit update limitation, and next origin. It does not overwrite the old run. |
| `evaluate_forecasts(run_paths, target_dir, evaluation_plan)` | Frozen forecasts and independent observations -> scores, coverage, failures and provenance. Missing targets remain missing; no parameter fitting. |
| `export_run(result, output_path)` | Validated result -> new CSV/JSON run directory and manifest. Existing run paths are not overwritten. |

Public failures use existing `StudyError` conventions for malformed inputs. Scientific unavailability is a structured result with `component`, `reason_code` and source references; never NaN disguised as a valid prediction. Separate invalid input, unavailable science and failed numerical computation.

### 9.2 Files and required fields

Reuse the existing observation CSV bundle without adding forecasts to it. The following are additional minimal contracts. JSON null and empty CSV cells mean unavailable; numeric zero means measured/modelled zero. Infinity is represented as an event state and a null time, never invalid JSON `Infinity`.

| File | Required content |
| --- | --- |
| `origin.json` | `schema_version`, `origin_id`, `plant_id`, `session_id`, `observed_at`, `frame_id`, `coordinate_frame`, input hashes, observed block references, applicability and availability. |
| `parent_axis_points.csv` | `parent_stem_id,point_id,order,x_mm,y_mm,z_mm,source_ref,review_status`; ordered directed polylines with reviewed apex identity in structure JSON. |
| `attachments.csv` | `compound_leaf_id,parent_stem_id,segment_start_id,segment_end_id,fraction,material_node_id,predecessor_id,adjacency_status,projection_residual_mm,review_ref`; fraction in `[0,1]`. |
| `model.json` | Model/transform versions, evidence-linked parameter particles, environment scenario and clock, declared scope, observation model reference and computational settings. |
| `trajectories.csv` | `run_id,trajectory_id,parameter_particle_id,scenario_id,weight,valid,status_reason,random_stream_id`; weights normalized only within an explicitly defined scenario/model distribution. |
| `events.csv` | `trajectory_id,parent_stem_id,predicted_block_id,event_index,event_state,appearance_elapsed_days,appearance_development_days,material_node_id`; `event_state` distinguishes appeared, beyond horizon and stopped. |
| `block_states.csv` | `trajectory_id,block_id,source_compound_leaf_id,parent_stem_id,elapsed_days,target_at,existence,state_source,frame_id,attachment_x_mm,attachment_y_mm,attachment_z_mm,direction_x,direction_y,direction_z,axis_length_mm,left_extent_mm,right_extent_mm,supported_area_cm2,area_basis_id,optical_eligible`; unavailable values empty, prebirth geometry empty. |
| `trajectory_parameters.json` | Per-trajectory events and decoder parameters sufficient for exact re-query, measured shape/hash references, material-segment graph, transforms and shared effects. |
| `summary.csv` | `scenario_id,horizon_days,target_kind,target_id,quantity,conditioning,statistic,value,unit,nominal_probability,available_weight,reason`; occurrence is unconditional, geometry explicitly conditioned on existence. |
| `update.json` and `associations.csv` | Prior/new run and origin IDs, immutable hashes, observation-model version, weight update/ESS/status; candidate/confirmed associations, probabilities if supplied, evidence and reviewer. |
| `evaluation.csv` and `manifest.json` | Scores and denominators by split/horizon/target; missingness/failures. Manifest records all files/hashes, source/code/config versions, commands, timestamp, status, seeds and environment. |

For measured blocks, `block_id` is their confirmed identity. For new blocks it is scoped by trajectory, axis and event index; it is not a cross-trajectory physical ID. `source_compound_leaf_id` stays empty until a separately recorded observation association exists. Queries before birth may include explicit `not_yet_appeared` rows; a stopped apex has no fabricated future block. A within-horizon block that later remains unobserved does not disappear from the forecast table.

The internal bank can be ragged. Export existing measured axis stations through source references and decoded arrays in `trajectory_parameters.json`; do not compress their shape into one straight line. `block_states.csv` contains summaries, not a substitute for measured shape. Material segment IDs remain stable within a trajectory so attachment movement can be reconstructed.

Minimal unavailable configuration example, intentionally not executable as a real forecast:

```json
{
  "schema_version": "probabilistic-compound-1",
  "model_version": "stochastic-grammar-proposal-1",
  "origin_id": null,
  "horizon_days": 30,
  "sampler": "joint_gaussian",
  "topology_scope": "provided_axes",
  "leaf_retention_assumption": null,
  "clock": {"kind": "calendar"},
  "environment_scenario": {"id": null, "values": null, "response_ref": null},
  "parameter_particles": null,
  "observation_model_ref": null,
  "future_tissue_ref": null,
  "computation": {
    "seed": null,
    "sample_count": null,
    "output_days": [0, 7, 14, 21, 30],
    "numeric_tolerances": null
  }
}
```

Every biological parameter entry follows this evidence contract; the nulls are deliberate:

```json
{
  "name": "appearance_wait_location",
  "value": null,
  "unit": "log(development_day/reference_day)",
  "reference_value": null,
  "source_kind": "unidentified",
  "source_ref": null,
  "applicability": {"cultivar": null, "environment_domain": null},
  "fitting_split_id": null,
  "adjustable": true
}
```

Allowed source kinds are `measured`, `user_assumed`, `literature_informed`, `fitted` and `unidentified`. User adjustment produces a new config hash and retains previous evidence; it does not turn an assumed value into a fitted one. Parameters for unsupported responses remain absent/disabled, not multiplied into growth with a neutral value presented as biology.

### 9.3 Reproducibility and summaries

Record a root seed and named deterministic substreams derived from stable keys `(run model version, trajectory index, axis ID, event index, draw role)` using an explicit stable hashing/seed algorithm. Do not use Python's randomized object hash. Save the random generator algorithm and library versions. Separate parameter, process, observation-hypothesis and future FM-noise streams. Reordering table rows, changing export frequency or parallel worker count must not change a keyed trajectory. Bitwise reproduction is promised only within the recorded numerical environment; cross-platform comparison uses declared numerical tolerances.

Use normalized weights for occurrence probabilities and count histograms. Report geometry quantiles conditional on block existence with the conditioning mass. For direction, retain unit-vector samples and circular summaries with undefined-result status when concentration vanishes. Do not average multimodal positions into a supposedly likely leaf. Selected representative complete trajectories may be exported using an explicit selection rule, but no new visualization is required. A spatial occupancy grid is excluded from the minimum implementation; the samples already retain the distribution without adding grid-resolution assumptions.

## 10. Verification and scientific acceptance

### 10.1 Software invariants

These are future implementation checks, not tests claimed to have passed in this document task:

1. At the origin, measured positions, shape references, axis stations, extents and identities are exactly preserved; source-file hashes remain unchanged after export/update.
2. Unit and frame mismatches fail; directed frames are orthonormal/right-handed; signed elevation and wrapped azimuth round-trip, including vertical/degenerate cases without fabricated angles.
3. Birth times are ordered, waits positive, stopped apices absorbing, parents valid and material-node IDs stable. Zero, one and multiple births within a day all work. Before birth, geometry is null.
4. Old stem segments continue growth after an event; creating a new zero-length terminal does not move the existing apex discontinuously. Existing attachments move consistently with lower-segment extension.
5. Analytic decoding and identical keyed draws give the same state at the same biological time for daily, hourly and irregular output schedules. Test clock inversion across zero-development intervals and events exactly at query boundaries.
6. Missing identity, area basis, apex, noise covariance, response input or parameter yields its documented unavailable component, not a guessed value. Unknown extent is not zero tissue area.
7. Samples retain cross-time/organ dependence; deterministic cases and small synthetic distributions with known probabilities verify bookkeeping. Synthetic fixtures are clearly labelled and cannot enter observed-state fitting.
8. Updates cover confirmed/ambiguous/missed/unmatched observations, all-zero likelihood, weak support and no-observation behavior. Prior forecasts and raw evidence remain immutable; new origins do not reapply already accrued growth.
9. No envelope gains tissue/PPFD eligibility. Existing distinct optical identities are preserved.
10. Reproducibility holds under changed row order and output schedules; numerical failures/rejections appear in denominators. A requested sample count is a computational control, not an evidence claim.

Use exact equality for copied identifiers, hashes and origin arrays; use declared machine/scale-aware tolerances for computed rotations, inversions and ODE integration. Those numerical tolerances are not agronomic accuracy thresholds. No biological acceptance limit is invented here.

### 10.2 Independent evaluation

Freeze configuration before examining held-out outcomes. Use chronological origins and independent plant groups: all records of one plant belong to one generalization split. Past observations of a test plant may initialize its forecast; its future observations only evaluate it. Parameter selection, normalization, observation-noise estimation and FM target preparation follow the same split discipline. Keep separate records for interpolation, synthetic checks and prospective forecasts.

Evaluate 7, 14, 21 and 30 calendar days only where independent targets exist. Report the actual observation interval and visibility; do not relabel a nearby or shorter target as an exact 30-day observation. Match at a documented temporal tolerance only if the evaluation plan justifies it; otherwise evaluate at the actual elapsed time. Report applicability to the provided axes/no-loss scenario, not whole-plant completeness.

Use persistence and eligible recent-change forecasts for existing blocks. For new blocks, use a context-free appearance/placement prior fitted on training plants or explicitly supplied as an assumption baseline; without event evidence it is unavailable. Compare the relational stochastic grammar against that baseline before testing the same grammar with FM. A no-new-leaf comparator may be included as a clearly degenerate baseline, not presented as a defensible biological forecast without evidence.

| Target | Compact metric contract |
| --- | --- |
| Appearance/count | Brier loss for confirmed occurrence by horizon; CRPS for new-block count where axis coverage permits a count. Include stopped/beyond-horizon mass. |
| Event timing | Interval log loss `-log P(l<T<=r)`; confirmed right censoring uses `-log P(T>c)`. Visibility-conditioned observation protocol must be fixed; occluded intervals are not right censoring by absence. Zero assigned probability gives infinite loss and a reported failure, not an undocumented probability floor. |
| Matched geometry | Attachment Euclidean error in mm; direction geodesic error `acos(clamp(d_pred dot d_obs,-1,1))` in radians (degrees for display); axis/extent absolute error in mm; comparable area error in cm2. Use predefined sample summaries and confirmed correspondences. |
| Distribution quality | Weighted CRPS for scalar traits; energy loss for fixed, pre-scaled multivariate geometry with direction encoded as a unit vector. Evaluate geometry conditional on existence and report occurrence separately, so false absences are not hidden. |
| Calibration/sharpness | Empirical coverage and width of declared scalar intervals, angular coverage/radius where defined, and paired proper scores. Nominal levels are fixed in the evaluation plan. Report uncertainty by independent plant, with effective sample size. |
| Coverage/failures | Eligible/total targets, confirmed/ambiguous/unmatched identities, missing visibility, unavailable outputs, numerical failures, rejected samples and effective weights, by horizon and trait. |

For normalized weights, use the lower-is-better convention:

```text
CRPS = sum_i w_i |x_i-y| - 0.5 sum_ij w_i w_j |x_i-x_j|.
Energy loss = the same expression with Euclidean vector distances.
```

The underlying proper-score definitions and the need to assess calibration with sharpness follow [Gneiting and Raftery (2007)](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf). Fixed dimensionless scaling must be determined from training data or an explicit evaluation utility, not tuned on test errors. Finite-ensemble estimates have sampling error. An interval-observation loss is comparable across models only under the same observation/censoring protocol; it does not establish fine event-time calibration within an unobserved interval.

No scored identity alignment may use a model-specific best-case matching to discard difficult leaves. Use reviewed correspondences or an explicitly frozen association protocol; report unresolved pairs. Do not compute aggregate geometry error only on successful matches without its denominator and separate occurrence score.

### 10.3 Acceptance and missing inputs

`accepted_for_domain` requires an explicit evaluation record stating the target cultivar/stage/environment domain, forecast horizons, practical tolerances, proper-score comparison, coverage/sharpness criteria and failure limits. Numeric thresholds require operational requirements and independent evidence; they remain inactive now. In their absence, successful software checks and retrospective scores can support `evaluated_unaccepted`, not a claim of reliable real 30-day prediction. FM needs measured improvement over the grammar-only model under that same record and must not worsen required failure/coverage limits.

Only these unresolved inputs are needed to progress:

- **Measured anchor:** eligible timestamped compound states, stable frame/identities, parent-axis direction/material attachment correspondence, and apex evidence for future XYZ placement.
- **Scenario parameters:** appearance/residual-wait and stopping distributions; enabled conditional trait coefficients/covariances, expansion targets/rates and local frame references. Unknown cultivar, age and environment remain unknown or user-assumed with explicit scope.
- **Longitudinal calibration:** block-level repeated measurements, appearance intervals, visibility, extent/area correspondence and independent plants. No mandatory detailed annotation of every leaflet is introduced.
- **Updates:** association evidence and supported observation/discrepancy likelihoods; otherwise only re-anchoring and discrepancy reporting are available.
- **Acceptance:** practical forecast-use tolerances and independent targets through the claimed horizons. These are separate from the computing sample count and numerical tolerances.

### 10.4 Implementation order and exclusions

Codex can implement the validated state adapter, parameter/evidence contract, event grammar, joint sampler, analytic decoder, CSV/JSON export and software invariants from this specification, using explicit assumption configurations. Next add summaries, finite-bank updates and the specified evaluation functions. Real parameter fitting, calibrated uncertainty and FM activation await the observation evidence above. Scientific review determines whether the proposed statistical families are acceptable for the intended plant domain; this document does not represent completed Claude review.

Do not add a dashboard, new viewer, animation system, reconstruction pipeline, leaflet generator, neural model zoo, cloud service, deployment, scheduler or training campaign. Carbon allocation, nutrient uptake, flowering, fruit, yield and economics are outside this block-architecture scope. Environmental inputs are optional justified conditioning, not a full physiology project.

## 11. Design completion audit

This audit concerns the requested specification, not implementation or biological validation.

| Requested result | Location and concrete completion evidence |
| --- | --- |
| Preserve measured leaves and provenance | Sections 2, 5.2, 8 and 9 define immutable shapes, exact origin recovery, forecast flags and separate output tables. |
| Future CompoundLeaf distribution from grammar and relations | Sections 2.2-5 define supported relations, event endpoint, stop/wait law, shared/sequential latent dependence, material attachments and anchored growth equations. |
| Sources without transferred crop defaults | Sections 1.1-1.2 identify retrieved material, access limits, cultivar/domain limits and proposed rather than literature-derived equations. No numerical biological coefficient is filled. |
| Precise bounded FM decision | Section 6 gives a disabled-current decision, sequential topology interface, transformed parameter target, conditional path/objective, sampling procedure and evidence gate. |
| Uncertainty and observation correction | Section 7 separates uncertainty components and defines one update equation, likelihood requirements, all four association cases, no-observation behavior and new-origin preservation. |
| Optical separation | Section 8 makes envelopes ineligible and preserves separate measured optical identities; no tissue reconstruction is included. |
| Reuse and concrete implementation | Sections 8-9 identify existing functions, one new module, exact operations, file fields, units, null semantics and reproducible random streams. |
| Meaningful validation and missing data | Section 10 separates software invariants from independent chronological/plant-group evaluation, gives score formulas/horizon rules and leaves unsupported acceptance thresholds inactive. |
| Minimal authorized deliverable | One English specification, local handoff log/TODO updates and read-only verification only. No production edits, model execution, training or cross-chat messages. |

The numerical forecast remains unavailable until its required inputs are supplied. That limitation is explicit in the contract and is not a claim that the real plant's next month has been predicted.
