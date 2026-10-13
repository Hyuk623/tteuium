# V3 decisions and settings requiring review

Implemented under the user's explicit V3 exception. These are conditional selections, not scientific approval. All exact values/units/provenance are in each run's parameter_registry.json. Do not silently promote any to measurement.

| Decision/input | Implemented conditional choice | Required follow-up |
|---|---|---|
| Exchange light/CO2 basis | VTC fixed NRH, absorbed photons, Amax 13.57 umol CO2/m2/s, alpha .048, theta .92 | Resolve upstream mmol comment versus equation units and incident/absorbed fit basis; assess Micro-Tom applicability |
| Thermal clock | base 5.7 C, germination 206.3 DD, phyllochron 37.9 DD | Germination/leaf-emergence series and actual climate; borrowed Merlice timing is not fitted |
| Determinate development | first 9 leaves; successor cadence 2,1,0; stop at two successive trusses | Confirm affected axes and natural Micro-Tom developmental sequence |
| Seed/hidden state | .06 gC per plant; root starts massless; no cotyledon/hypocotyl geometry | Seed reserves, roots, organ age/mass and reserve initialization for real observations |
| Tissue demand | normalized logistic targets by organ; demand-proportional allocation | Organ/stage maximum mass, rate, midpoint and allocation evidence |
| Respiration/carbon | .45 carbon fraction, .75 construction efficiency, .0005 gC/gDM/day maintenance on each tissue | Organ-specific values, gross/net fit convention and starvation policy; current deficit rejects the run |
| Leaf shape and area | full_outline, constant SLA .025 m2/gDM, diamond L/W=2 | Real outlines, SLA and green/active tissue fraction; browned margins remain in main area but are not proven active |
| Stem/rachis/flowers | 12 mm internode cap; cube-root funded dimensions; fixed structural limits | Mass-volume/length relationships, floral stages and geometry; proxies are not complete anatomy |
| Leaflet pattern | 1,1,2 pairs by true order, middle ramp .35; terminal separate | Rank-pattern measurements; no universal 13-leaflet template |
| Angles | fixed insertion 80 deg, divergence 137.5 deg, total bend 20 deg, basal leaflet angle 35 deg | Developmental orientation data; no phototropism implied; curl and flat/bent thresholds remain on hold |
| Lamps/optics | assumed point lamp; black two-sided full-outline polygons, 14 h scenarios | Measured source emission/position, optics, absorption and absolute PPFD; phone ratios stay relative |
| Time discretization | daily frozen geometry, next-interval light for new tissue | Subdaily response/validation contract; no timestep-convergence claim |
| Observation producer | exact-column Stage-2 fixture and hidden-state supplement | Actual Claude P1 delivery, scale/pose/time/identity, located surfaces and explicit physiology assumptions |
| Nutrients | disabled growth feedback; existing prescribed ledger unchanged | Executable uptake/demand/joint-allocation contract; EC/pH cannot supply it |
| Model scope/license | main plus declared sympodial axes, root compartment, explicit flowers | No fruit/yield/lateral-shoot accuracy claim; resolve VTC redistribution license |

Review priority: light/CO2 basis and active area; real initialization; carbon/respiration; thermal/apex rules; geometry coefficients. Supplying one measurement does not validate all other parameters.

## Staged integration update (2026-10-11)

P1 delivery is now present: `build/p1_state_20261011_01` is a fixture package and `_02` is a real-photo audit. The connected native run consumes the fixture's explicitly separate truth route. Its observation reconstruction is not certified by that execution. Real audit: 117 captures lack a solved metric scale and aware timestamps; 13 plants lack optical surfaces. Inspect the producer's `audit_gaps.csv` for detector, identity, pose and environmental gaps as well. Add actual timezone information through the producer rather than silently attaching an offset in the consumer.

Additional settings requiring a decision before interpreting real forecasts:

| Setting | Executed assumption | Needed decision/evidence |
|---|---|---|
| Imported P1 leaf growth | Preserve initial triangles/posture; scale dimensions with sqrt(mass / initial mass) | Measured outline development, specific leaf area, active area and angle changes |
| Imported structures | Cube-root dimension change and parent-tip offsets; explicit root/stem/apex hidden compartments | Initial tissue mass, reserve, age, actual developmental rank, root state and attachment reconstruction |
| Instance placement | P1 rigid matrix applied once; shelf pitches remain producer-labelled assumptions | Measured pot/row/tray positions and orientation; resolve missing neighbors, pot and shelf shading objects |
| Absolute illumination | 1200 umol/s hypothetical point lamp, 14 h daily | Lamp emission, absolute PPFD, schedule and tissue optical properties; phone ratios cannot supply these |
| Numerical interval | Daily default; 12 h fixture refinement with 7 h light + 5 h dark per interval | Same-horizon mass differs about 0.22% in one test; this does not establish convergence across cases or represent an actual half-day climate schedule |
| Optics and sampling | Black tissue, 4.8 million rays, two seeds in controls | Transmission/scattering and whole-scene energy accounting remain unsupported; quantify uncertainty for the intended scene |
| Required nutrient ledger | Prescribed independent water/element replay; enabled required-ledger failure prevents publication | Reviewed joint nutrient/carbon demand and actual allocation contract before growth feedback can be enabled |
| Forecast wrapper | Native pipeline is the single state-advance authority | Claude Code owns the separate Micro-Tom/Stage-3 forecast layer under S2; wrappers must not advance an already-produced checkpoint again |

The fixture also includes `fx_sp0` with a separate source morphology; a shared conditional parameter set in a software test is not cultivar-specific validation. Fruit, yield, natural branching, phototropism and nutrient-driven direction remain outside the delivered contract. See `CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md` for executed stages and failure evidence.

## Declared side-shoot conditional selections (2026-10-12)
User-authorized contract: P4_SIDESHOOT_SCIENCE_AND_IO_CONTRACT_2026-10-12.md section 2, version fsp-axes-1. Shared plant carbon pool selected; capped demand-proportional allocation with SUBSTEM_SINK_SCALE=1.0 (user_assumed, no dominance), independent declared-axis apices and same conditional determinate program when explicitly enabled, common age-target tissue curves, once-only imported mass and no new side-axis emergence. Nutrient bookkeeping remains plant-level with feedback disabled. Axis absorbed-light/gross attribution is diagnostic, not local carbon retention. Main sympodial continuations remain M, not side shoots.
Pending human/scientific decisions: actual Micro-Tom substem truss behavior; axis-specific developmental timing and allocation/dominance evidence; observed two-visible/two-expanded leaf registration evidence; actual hidden mass/age/clock/attachment state. APPLY_DETERMINATE_STOP=false means no new initiation on that declared axis, not an adopted indeterminate law. Topology is provided_axes and completeness unavailable. No fitted cultivar branching claim.

## Extension delivery and current readiness (2026-10-12)

This addendum updates the historical statuses above without replacing their evidence. Canonical declared-axis contract: `P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md` section 2; executed evidence: `P4_SIDESHOOT_EXECUTION_2026-10-12.md`. The default unity side sink multiplier remains `user_assumed`, source: explicit user assignment / contract section 2. Nonunity fixture values demonstrate software allocation only. No dominance coefficient has been fitted or adopted from another cultivar.

| Decision/input | Current implementation/evidence | Still required |
|---|---|---|
| Real P1 time and geometry | New producer package `build/p1_state_20261011_03` carries user-confirmed Asia/Seoul camera timezone; consumer audit `build/fsp_extensions_20261012_real_intake_02` has 130 producer gaps, comprising 117 scale and 13 optical-surface gaps, and no timestamp gap | Metric scale, located surfaces, hidden physiological state and absolute illumination; no real initialized forecast yet |
| Side-axis producer | Explicit `fsp-axes-1` fixture consumed; producer `axis`/`axis_state` aliases tested; P1 owner has agreed to exchange columns in LOG | A4 and actual P1 exporter reconciliation after parallel delivery; no inferred missing axis, stage promotion, mass or age |
| Optical materials | Conditional grey reflection/transmission and static scene objects execute natively; fixture wavelength 550 nm is `user_assumed`, source: extension acceptance scenario | Spectrum/material observations and NRH absorbed-versus-incident fit basis; nonblack growth is blocked pending this decision |
| Photon accounting | First-hit received/absorbed/reflected/transmitted and emitted power exported; terminal escape/cutoff/residual remain unavailable | Backend terminal-path instrumentation and validation; do not infer escape by subtraction or claim complete photon closure |
| Time discretization | Aware, source-specific piecewise schedules and elapsed-time thermal/maintenance integration implemented; tested coarse/refined short fixture agrees | Target-scene timestep and ray convergence; temperature/CO2 physiological response is not added |
| Geometry hooks | Exact-count bend weights, explicitly supplied flat/bent templates and reporting-only full-outline area correction executed | Human bend classification thresholds/curl remain on hold; no template is a measured Micro-Tom default |
| Imported deformation | Initial geometry preserved and existing funded scaling retained; anchored rigid-rotation utility tested | Reviewed developmental deformation law, reference frame, age response and mass/area relationship; runtime deformation remains disabled |
| Nutrient coupling | Transaction protocol tested only as a labelled fixture; prescribed ledger stays plant-level with growth feedback disabled | Reviewed uptake/demand/joint-allocation science contract and actual native proposal/finalize handshake; no axis-specific uptake rule |

Counts in this addendum are execution/audit results (`source_kind=execution_result`), with source refs to the named build artifacts and execution reports. They are not biological parameters. Final focused regression comprises 193 unique passing cases; nine declared-axis native runs cover 29 intervals at 4.8M rays, including independent stop, weighted allocation, shading and replay controls.

A4 follow-up: Amendment A4 section 15 was published and read during final delivery. Canonical resource contract section 6 now records its CompoundLeaf axil representation. Its numbering basis and two-leaf rank tie remain proposals; the consumer preserves explicit IDs/ranks. Actual P1 side-exporter execution and later P3 forwarding remain separate prerequisites.

A4 verification update: the consumer accepts the explicit CompoundLeaf axil representation and passed native two-interval fixture execution plus missing-parent rejection. The latest unique focused count is 195; declared-axis evidence now covers 10 native runs / 31 intervals. Source refs: P4_SIDESHOOT_EXECUTION_2026-10-12.md final addendum and build/fsp_axes_20261012_a4_01. Actual producer side-export testing and P3 axis forwarding are still separate pending work; no additional biological parameter was selected.

## Selected substem truss applicability (2026-10-12)
Supersedes the earlier pending applicability item only. The user observed that Micro-Tom side shoots bear trusses (`source_kind=user_stated`, source_ref=user decision 2026-10-12 / docs definition mirror section 1-1). Select the existing conditional determinate program for M and declared substems, default APPLY_DETERMINATE_STOP=true (`source_kind=user_assumed`, source_ref=P4 resource contract section 7); explicit per-axis false stays available. Timing/cadence are not fitted. User additionally authorized existing conditional new-truss generation in this task; outputs remain model_generated. Missing segment/history gives unavailable rule status, never segment 1. Axis-specific timing, dominance evidence, attachment and hidden physiology remain pending.

## Substem truss delivery and A5 reconciliation (2026-10-12)
The selected applicability/default above is implemented and verified; earlier pending substem applicability and actual P1 fixture interoperability entries are superseded by P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md. Source_kind=execution_result, source_ref=build/fsp_truss_20261012_delivery_01/acceptance.json: 219 unique focused tests pass; seven native runs/fifteen intervals at 4.8M rays preserve carbon closure and independent stops. Actual P1 build/p1_state_20261012_05 uses explicitly declared fixture_truth/c2 and separate hidden physiology/geometry; no real-data accuracy is established. Missing segments/history remain unavailable and withhold initiation while existing tissue can grow. Still pending: axis-specific timing (engine CADENCE remains shared), dominance evidence, actual registration/attachment, hidden mass/age/clock and truss position. P3 owner must reconcile its earlier no-new-truss clause with the user's explicit authorization recorded in resource contract section 7. No nutrient feedback or side-axis emergence law is selected.

## Accepted P2 empirical-field consequence (2026-10-13)
The user selected the empirical light field in CODEX_CLI_PROMPT_P2_EMPIRICAL_LIGHT_FIELD_2026-10-13.md and authorized implementation with no plants above the 150 mm observation plane. Moving lamps, changing the board/tray geometry or changing the enclosure requires new measurements; lamp-movement counterfactual prediction is intentionally unavailable. This is an accepted consequence, not an open fitting task. No wall-covering experiment or lamp/reflectance fitting is requested. Direction splits 0.5/0.6/0.7 remain user_assumed sensitivity scenarios, not measured reflected fractions. The approximate 60% narrative and sparse synthetic recovery failure do not establish a measured reflection fraction or structural non-identifiability. Reference: P2_EMPIRICAL_LIGHT_FIELD_EXECUTION_2026-10-13.md; build/p2_empirical_light_field_20261013_01/verification.json.

## Tray solution implementation addendum, 2026-10-13

The latest continuation and user decision authorize bookkeeping without inventing missing science. tools/nutrient_reservoir.py, nutrient_reservoir_records.py and nutrient_reservoir_transaction.py now implement separate standing/medium solution and stored pools, explicit two-way transfers, status-aware human record intake, conservative declared uncertainty bounds, blank-adjusted signed residuals and modelled plant split. Old plant element ledgers remain unchanged. None of this identifies elemental uptake or enables native feedback.

Resolved engineering fields: quantities/units, tray membership, record lineage, finite-stock water/EC-equivalent arithmetic, missing-evidence refusal, later registry/callable insertion boundary and fixture-only joint candidate publication. Still unresolved: response equations/parameters and EC semantics, measured medium/stored initial conditions, predictive exchange/saturation law, valid blank scaling and uncertainty, and actual native causal proposal/finalize. Existing E7 or nutrient rows above remain open for science/native coupling. A scalar EC limitation does not imply N/P/K co-limitation. A typical 0.4 L tray quantity is user-stated approximate metadata, not a replacement for missing observations. Details and sign correction: P4_NUTRIENT_RESERVOIR_CONTRACT_2026-10-12.md.
