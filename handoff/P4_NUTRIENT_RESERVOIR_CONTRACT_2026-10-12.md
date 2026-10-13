# Tray reservoir executable contract — 2026-10-13 continuation

Written before implementation. Implements the 2026-10-12 source prompt and 2026-10-13 continuation; latest user instruction: implement without missing science values and prepare explicit insertion points. No approval is inferred for a missing law. Read current rules, human template/actual observations, existing nutrient balance/transaction, V3/side-axis resource contracts, eight-capability report and active native boundary contract. Keep flow, native/controller, legacy ledgers and human records unchanged.

## Implementable scope and units

Schema `tray-reservoir-1`. Every result carries scenario_id, element_resolved=false, quantity_basis=EC_equivalent, biological_validation=not_established. EC-equivalent is an additive bookkeeping assumption, not a conserved elemental species or nitrogen measurement. Unit: mS/cm*L. Water: L. Explicit separate compartments: reservoir solution (depth-derived volume), medium-held solution (independently supplied volume/EC), and stored EC-equivalent pool (unobserved unless independently supplied). No pool/medium volume lumping and no hidden initial zero. Within each solution, withdrawals use an explicitly declared well-mixed assumption. No equilibrium or kinetic adsorption model is chosen.

Stocks and ordered events are finite/nonnegative; geometry is positive, tray and plant IDs unique, blank has no plants. Water transfers move a well-mixed aliquot between solution compartments. `adsorb` moves nonnegative EC-equivalent medium solution -> stored pool; `release` reverses it. Both must be prescribed with provenance. Supply/removal, evaporation, plant water uptake and EC-equivalent uptake are distinct. Zero flux is allowed only when explicitly supplied; omitting a process schedule is not permission to infer it from observations. Replay is immutable and rejects the entire interval on overdraw. Prescribed accounting is not inferred uptake or a native growth update.

## Signed interval residuals and uncertainty

Let D=EC_pool*V_pool + EC_medium*V_medium; S=stored stock. I/O are supplied/removed EC-equivalent; A/R nonnegative adsorption/release; U is plant uptake. Equations: delta D=I-O-A+R-U; delta S=A-R; therefore U=I-O-delta D-A+R. Water closure: delta(V_pool+V_medium)=I_water-O_water-E-T. Accounting residual is initial + inputs - outputs - final (including stored pool).

Blank residual B=I_b-O_b-delta D_b estimates **net** adsorption A_b-R_b only under the declared same-medium/supply/interval comparability contract. It does not separate adsorption from release or identify S_initial. Planted residual U=I_p-O_p-delta D_p-k*B; k is the explicit medium-volume scale, with an evidence declaration that volume scaling is appropriate. Negative residuals remain signed diagnostics; they are never clipped into uptake or silently interpreted as plant exudation. Missing blank/identity/volume/EC/medium state/comparability/uncertainty => uptake unavailable, not zero.

For water, E_b=I_b-O_b-delta V_b, T_lower=I_p-O_p-delta V_p-kE*E_b. kE is a separately declared evaporation scaling factor, not medium-volume scaling. If blank evaporation bounds planted evaporation from above, this subtraction biases inferred plant water uptake **downward**. This is a conditional lower estimate, not measured transpiration.

Inputs may declare conservative absolute error bounds with source_kind/ref and explicit `uncertainty_mode=absolute_bounds`. Interval arithmetic propagates bounds without invented normal distributions or independent-error assumptions. Missing bounds withhold inferred uptake; deterministic prescribed ledger closure remains available. EC and depth meter bounds alone cannot account for unknown medium storage or blank mismatch. Scenario spread is never a confidence/prediction interval.

Source correction requested: at fixed observed delta D, omitting positive R from U=I-O-delta D-A+R **underestimates** U, not overestimates it. Other fitted parameter responses can change that comparison. The original sink-only overestimation sentence is not implemented as algebra. Likewise a 20-minute EC rise is consistent with release but cannot identify it without volumes, mixing/measurement information and prior solution composition. Preserve that interpretation as a hypothesis.

## Modelled plant split

Nonnegative available tray uptake is distributed U_i=U*d_i/sum(d), for complete same-interval plant demand weights with a common declared unit and provenance. It is labelled modelled_split, never observed and never a stoichiometric demand conversion. Positive U with zero summed demand is unavailable. Blank gets no plant split. No additional organ/carbon allocation or reserve update occurs here.

## Required registry and future native connection

Registry schema `tray-nutrient-response-registry-1`: EC input definition/unit/time support, exact equation ID/version/branches, breakpoint definitions, complete none/moderate/strong parameter records (value/unit/source_kind/source_ref/uncertainty), reviewer/source reference, exchange law and initial-pool evidence. No built-in numerical biological response is supplied. A versioned injected evaluator must match the registry law ID; it receives the full immutable registry and explicit EC evidence and returns a finite [0,1] factor. Evaluator use is diagnostic only. Default feedback=false bypasses it exactly. `none` is the disabled reference; moderate/strong remain separate outputs. No native feedback enablement is allowed by this module, even if a registry exists, until actual hook acceptance is separately delivered.

Native owner handoff: proposal ID, run/scenario/tray and exact plant membership, interval, predecessor/model/parameters/geometry/config/state hashes; reservoir input state hash; bounded expires_at; source-bound factor/evaluator identity. Native must apply f_nut once to **gross assimilation before allocation**, verify native/reservoir candidate states and atomically publish both in one commit. No retrospective proposals.csv coupling. Engineering transaction adapter will stage one immutable joint candidate bundle, require exact proposal/response binding and idempotent finalize, reject stale/expired/conflicting retries, and recover identical interrupted publication. This tests persistence mechanics only; native_causality=false until independently validated by the native owner. Scalar EC never implies joint N/P/K limitation.

## Missing decisions for Claude scientific owner

| Field | Required decision/evidence | Current executable behavior |
|---|---|---|
| EC input | reservoir or medium, instant/mean/end, temperature convention | required registry field; no inferred choice |
| Response law | exact deficiency/high-EC equations, continuity/domain/breakpoints, full parameter triples per scenario | injected versioned evaluator only; no built-in physiology |
| Initial pools | per-tray medium water/EC and stored stock plus uncertainty | unavailable unless explicitly supplied |
| Exchange | adsorption/release kinetics/capacities, scaling, identifiability | prescribed bidirectional transfers only |
| Blank correction | same supply/medium/time evidence, medium-volume scale applicability, separate evaporation scale | strict explicit comparability contract |
| Uncertainty | EC/depth/volume error bounds, scale/medium/blank discrepancy and calibration evidence | conservative declared bounds; no fabricated precision |
| Bias sign | reconcile source sink-only wording with signed residual equation above | use explicit conservation algebra |
| Inference/calibration | seven supply events incl blank necessary but not sufficient; growth observations absent | no parameter fitting or biological validation |
| Native hooks | accepted response semantics, rollback/joint commit, actual causal evidence | interface fixture only; native owner controls engine |

## Validation and deliverables

Fresh build evidence: blank and bidirectional fixtures, independent closure arithmetic, missing evidence/negative stores, membership/split, registry injection/refusal/disabled parity, stale/timeout/idempotent/interrupted transaction tests, real record read-only audit and legacy/native-consumer regressions. No high-EC biological scenario without a complete accepted law. Record exact passed tests and unresolved gates separately in execution report. Claim LOG before code, release after results.

## User clarification during implementation (2026-10-13)

The user states that the tray usually holds about 400 mL. Register nominal_reservoir_water_L=0.4, unit=L, source_kind=user_stated, source_ref=this chat 2026-10-13, status=approximate, uncertainty=unavailable. This is a typical standing-solution quantity, not maximum capacity, a measured endpoint, supplied volume per event, or medium-held water. Do not substitute it into missing measurements or assign it to unidentified pool_1/pool_2/pool_3 samples. Use “tray solution” in user-facing descriptions.
