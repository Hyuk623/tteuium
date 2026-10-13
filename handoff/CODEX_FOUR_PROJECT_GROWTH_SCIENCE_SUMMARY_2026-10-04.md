# Four project growth Science delivery summary

Date: 2026-10-04. Author: Codex coordination review.

## Review brief

Read the four requested P1 readiness and P2/P3/P4 execution handoffs, consolidate completed work and outstanding dependencies, and inspect their saved verification evidence. Check current source hashes against delivery/snapshot records where available. This review does not rerun models or tests, alter implementation, select the undecided physiology policy, or start integration. Append the verified outcome below; preserve the source deliveries.

## Overall finding

All four bounded Science follow-up tasks are delivered: P1 completed its observation audit; P2 completed provenance clarification through the explicitly unsupported-reference-channel branch; P3 implemented the accepted growth fixes; P4 implemented diagnostic accounting safeguards. This does not establish completion of every original project goal, an integrated system, or accurate real-plant forecasts.

The decisive remaining inputs are accepted real P1 physical area and persistent organ identity, a supported reference-position DLI channel for P3, target-supported model parameters, and the unresolved P4 physiological policy/source conventions. P3 owns realized growth; P4 remains read-only. Integration remains deferred under the existing decisions.

## Source deliveries

- [P1 observation readiness](CODEX_P1_GROWTH_SCIENCE_READINESS_2026-10-04.md).
- [P2 light clarification](CODEX_P2_GROWTH_SCIENCE_EXECUTION_2026-10-04.md).
- [P3 growth fixes](CODEX_P3_GROWTH_SCIENCE_EXECUTION_2026-10-04.md).
- [P4 diagnostic fixes](CODEX_P4_GROWTH_SCIENCE_EXECUTION_2026-10-04.md).

Use their final-outcome sections. Initial brief headings such as audit in progress or implementation started are historical within the same files, not their current delivery status.

## Project status

| Project | Completed in this delivery | Saved verification inspected here | Remaining boundary |
|---|---|---|---|
| P1 | 25-field inventory covering identity, area, geometry, time, uncertainty, event records and canopy splits | 58 inspected-source hashes; saved completion audit; two exact synthetic canopy splits | Accepted real tissue area and longitudinal physical-organ identity are unavailable |
| P2 | Explicit unsupported reference-DLI metadata, false-claim rejection, corrected directional capability description, tissue/reference and nonlinear-use guidance | 84 core + 97 tools tests, all passing; three package manifest hashes; recorded unchanged numerical tables | No reference-position sampler/importer or daily reference-DLI output exists in this package |
| P3 | Accepted decisions 1/3 and F2/F3/F7/F8/F9/F11: input domains, per-curve DLI identities, trait unavailability, semantic guards and ordered ESS reporting | 174 passing tests; saved baseline equality and three synthetic CLI runs; source/export hashes | Real observations and applicable coefficients remain missing; no direct light-driven orientation response or optical future mesh |
| P4 | F1/F4/F5/F6/F10: versioned registry, interval reuse validation, plant RGR5 evidence, primary inverse and originating-ledger association | 105 passing tests; saved 12 CLI executions, 10 synthetic cases and 256 delivery checks; hashes and registry function references | Question 2 and source conventions unresolved; no dynamic reserve state, growth feedback or whole-system validation |

Test counts belong to the listed saved suites. They are not new runs by this coordination review and must not be added to older overlapping delivery counts as unique tests.

## What changed in practical terms

### P1 distinguishes measurable observations from candidate geometry

The current T1 evidence includes 435 annotation rows over 18 photographs: 433 computed dimensionless ratios and two explicit exclusions. These are per-photo annotations, not 435 physical leaves. Projected area calculations remain diagnostic; projected mask area is not tissue surface area. Real supported surface area and total tissue area remain null.

Twelve current candidate regions do not establish persistent compound-leaf identity. Old names must not be transferred from the earlier five-region partition without reviewed associations bound to the new partition hash. Whole rachis measurements, real organ frames, supported area and dated organ correspondence are not ready for real P3 input.

The configured observation tables are empty and real capture clock/photoperiod phase is unavailable in the inspected artifacts. P1 quality measures are not calibrated measurement covariance. Repeated matched-organ observations, repeatability captures and reviewed physical scale/surface evidence remain necessary inputs to any later calibration plan.

Synthetic canopy splitting works as representation: source/instance IDs and full canopy shading context are retained. It does not validate real plant identity or reconstruct lost organ detail from aggregated means. Later GPU/mapping results supersede older pending-execution statements but do not establish physical area or optical eligibility.

### P2 prevents tissue DLI from being presented as reference DLI

P2 still computes supported-tissue light, daily doses and actual directional moments. Its new metadata explicitly states `reference_position_channel_not_implemented`, with null reference value/basis/applicability fields. The independent consumer rejects invented reference values, including fabricated zero.

Accepted question 1 requires incident PPFD over a complete local day at one declared reference position and sensor plane. Existing tissue DLI cannot be renamed to meet that requirement. A future separately scoped channel must preserve position, normal, frame, clock/coverage, incident basis, evidence and plant association. P3 owns the numerical applicability domain and curve coefficients. One reference used for several plants needs an explicit association; whole-plant model scope does not mean a leaf-area-weighted average.

The physical two-face light output remains unchanged. Future P4 use must resolve question 2 rather than silently interpret two-face receipt as adaxial-only. Sum simultaneous fixtures at the same patch/time before nonlinear photosynthesis, and do not add `fixture_id=all` to the individual fixture rows.

The three REF-30-40 fixtures still have confirmed 16 h/day at full output. PPF, actual clock windows and other unresolved optical inputs remain missing; neither lumens nor a nominal photoperiod fills those gaps.

### P3 handles accepted domains and unavailable predictions explicitly

The calculator now validates reference DLI metadata, complete local-day coverage, an inclusive declared applicability range and distinct coefficient bindings for exponential and beta curves. Two independently supported coefficients may have equal numerical values; shared semantic binding is what is rejected.

An explicitly supplied sub-base zero knot can pause development without allowing extrapolation. Low-DLI target failures preserve trajectory IDs and weights while marking affected traits unavailable. Quantiles remain conditional on available curves and now expose coverage of the original ensemble; they are not full-ensemble certainty statements.

Width targets are labelled at reference DLI, with realized asymptote `w0 + f_DLI*(target-w0)`. Narrowing evidence follows the adopted threshold only. Existing organs still reject beta. Calibration checks retain clock/meaning compatibility and reject light moments as growth-direction parameters.

Observation updates expose prior, after-geometry and after-events ESS. The stage changes depend on conditioning order and are not a causal decomposition. Shared cross-organ measurement correlation remains explicitly unmodeled. Beta observation reanchoring retains its original remaining increment, so endpoint displacement is preserved; the optional new weighting rule was not adopted.

### P4 audits carbon accounting without changing P3 growth

P4 now labels single-interval independence and lack of reserve propagation. Its explicit table validator detects the specified identical-reserve reuse across supplied contiguous rows. A single-row call cannot inspect unseen history, and differing reserve values do not prove a conserved dynamic stock model.

RGR5 activity now requires separate, complete plant-level structural-mass history; organ history is not silently substituted. Zero activity is flagged, and saturation at 1 is unavailable under the declared domain. No basal-maintenance floor was introduced.

Multiple mass-form inverses require a declared primary while retaining consistency checks. Carbon conservation audit verifies the originating demand result and pack association rather than trusting an echoed pack ID.

The new registry covers 28 equations: 11 implemented, 8 partial and 9 deferred. These are the registry's detailed equations, not the 18 groups in the earlier review pack; the counts are not contradictory. Implementation status is separate from biological acceptance, which remains false for the target domain.

## Current user decisions and source findings

| Item | Current status | Consequence |
|---|---|---|
| Question 1 | Accepted and enforced by P3 | Reference-position incident complete-day DLI; P2 producer remains absent |
| Question 3 | Accepted and implemented by P3 | Separate growth-family coefficient identities and applicability, with explicit unavailable handling |
| Question 2 | Still undecided | No adopted before_mito/net_leaf, incident/absorbed or botanical face-policy combination for real use |
| Optional reanchor weight, transient posture, truss observable | Unadopted | Existing behavior retained; no silent visible_bud or posture choice |

P4's saved primary-source inspection reports:

1. **NRH fit convention unresolved.** Source model algebra uses the curve before maintenance, but this does not establish whether empirical measurements were corrected from net to before-mito exchange before fitting. Original preprocessing/raw data or author clarification remains needed.
2. **Maintenance units conflicting.** The paper/thesis indicate CH2O equivalents while the pinned parameter CSV labels matching numerical rates as CO2. At equal numeric rates, the corresponding carbon conversions differ by about 1.466. This is a convention conflict, not authorization to multiply/divide current coefficients.
3. **Measurement conditions located, parameter basis still limited.** The source reports three plants, a mature rank-3 leaf, approximately 23 C cuvette conditions, 798 microbar CO2 partial pressure, 50:50 red:blue and 0-2000 applied PPFD. Applied-light setpoints do not settle an equation's absorbed-light coefficient basis or target-cultivar applicability.

These statements summarize [P4 source-check evidence](../build/p4_growth_science_20261004_01/source_checks.json); this coordination review did not independently reread the original papers or resolve their conflict.

## Cross-project gaps and follow-up order

| Priority | Gap / next concrete result | Owner and scope |
|---|---|---|
| 1 | Associate P4 registry status with the final P3 completion report | Coordination/P4: append or create a new version recording final report hash; preserve the historical snapshot. Code mappings already match current P3, so no algorithm repair is indicated |
| 2 | Define and separately authorize a supported reference-DLI channel or reviewed measured-data route | P2 producer plus human/Claude reference evidence; P3 keeps its strict input contract. Do not substitute tissue DLI |
| 3 | Establish accepted real geometry/area, persistent organ IDs, timestamp/scale/frame evidence | P1 and human acquisition under a reviewed protocol; distinguish observed support from predicted/generated geometry |
| 4 | Resolve physiological source conventions and question 2, then document target applicability | Claude scientific review/user policy; P4 keeps unavailable/hypothetical results where evidence is absent |
| 5 | Obtain repeated growth, event, mass and light data for applicable parameter packs | Reviewed acquisition/calibration plan; no coefficients inferred from software tests |
| 6 | Reassess integration prerequisites after original project goals and input contracts are ready | Keep D3 deferred linking; first synthetic pass still permits P4 unavailable under D6. No automatic integration authorization follows from these four deliveries |

Items 2-5 can progress independently within their authorized scopes. This is a dependency list, not authorization for experiments, new adapters, remote runs or biological choices.

For a future integration, unit spellings (`mol/m2/day` versus `mol/m2/d`), field names, frame/identity associations and reference provenance need explicit mapping. P3's stricter DLI input rejects older underspecified configurations. P4's stricter export requires regenerated results rather than editing historical archives. Existing schema IDs alone do not establish compatibility across these revisions; preserve revision and source hashes.

The intended information flow remains observed P1 structure plus P2 light -> P3 growth predictions -> P4 read-only carbon diagnostic. P2-to-P3 reference light and P2-to-P4 tissue light are different channels. A repeated loop using future P3 optical geometry or propagated P4 reserve is not implemented.

## Independent review evidence

Saved [review_evidence.json](../build/four_project_growth_science_review_20261004_01/review_evidence.json) records the checks performed here.

- Recomputed 206 recorded hash comparisons; 205 match. These are comparisons, not 206 unique files.
- The sole difference is P4's frozen P3 execution brief versus the final P3 report. The frozen text is an exact prefix of the final text; the completion sections were appended. It is a normal documented status change, not source-code drift or a damaged archive.
- All 31 equation-registry code references match the current source hashes, function names and starting lines. P4's `P3_in_progress_pending_final_refresh` label is therefore stale completion metadata, not evidence that its inspected P3 code differs from the delivered code.
- Read saved JUnit XML: P2 84+97, P3 174, P4 105; zero failures, errors or skips in those reports.
- P1/P2/P3/P4 saved audits support the scoped outcomes above. This review rehashed selected recorded source/artifact evidence and inspected saved results; it did not rerun all original 256 P4 delivery checks or any test/model suite.

Completion: four source reports reviewed, shared status and gaps summarized, evidence saved. No production code, coefficients, observations, user decisions or source delivery artifacts were modified.
