# Tray solution continuation execution — 2026-10-13

Executed PROMPT_CODEX_NUTRIENT_RESERVOIR_CONTINUATION_2026-10-13.md and the implementable portions of the amended 2026-10-12 source prompt. Later user direction: implement without missing science values and prepare their future insertion. The contract and missing-decisions table were written before code. The user clarified that the tray usually contains about 400 mL; this is recorded as approximate user-stated context, not an observed endpoint, irrigation dose, capacity or medium water.

## Delivered and deliberately gated

| Layer | Result | Interpretation |
|---|---|---|
| Records | Read-only ingest of existing template and October 13 observation dialect; status/unit normalization, raw rows and source hashes, geometry/membership/time diagnostics | Actual readings retained; no fabricated tray mapping or exact timestamps |
| Records -> calculation | Explicit source-hash-bound supplement, CSV endpoint/event coverage, normalized uncertainty bounds and separately supplied medium states | Working synthetic CSV-to-estimate CLI; current real records remain insufficient |
| Finite stocks | Separate standing solution, medium-held solution and stored EC-equivalent; supply/removal, well-mixed transfer, pure-water loss, prescribed adsorption/release/uptake | Conditional scalar bookkeeping, not elemental uptake or kinetics |
| Blank correction | Signed water/EC-equivalent residuals, explicit medium-volume scaling and separate evaporation scaling, discrepancy/error bounds | Missing evidence withholds uptake; negative residuals are preserved rather than clipped |
| Plant split | Complete interval/plant demand weights, proportional split, modelled_split labels | Never a measured per-plant nutrient claim or another carbon allocation |
| Later response insertion | Required versioned registry plus callable evaluator ID/version/EC semantics; complete-parameter fixture exercises low/high input; separate none/moderate/strong diagnostics | No built-in biological coefficients; none is disabled reference; no pooled prediction interval |
| Transactions | Proposal/interval/state/config/membership binding, expiry, stale/conflict refusal, single atomic joint fixture bundle, identical interrupted/retried finalize | Fixture persistence only; no live resource debit, native rollback or global predecessor service |
| Native causality | Feedback remains false; enabling through this module refuses | No claim of native gross-assimilation limitation or nutrient-constrained growth |
| Biological validation | Not established | No response fitting, salt kinetics, elemental stoichiometry, pH, root or directional response |

Code: tools/nutrient_reservoir.py, tools/nutrient_reservoir_records.py, tools/nutrient_reservoir_transaction.py. Guide: tools/NUTRIENT_RESERVOIR.md. Tests: tools/tests/test_nutrient_reservoir.py. The original nutrient_balance.py, nutrient_fsp_bridge.py and fsp_nutrient_transaction.py remain unchanged. Native/controller templates are owned by the concurrent native continuation; no edits were made to them, flow, docs, config, human records or the old plant-level ledgers.

The native owner was contacted under the explicit coordination instruction. That owner retains the actual proposal/pause/finalize and once-only gross-assimilation application boundary. Current retrospective proposals are not used to constrain finished growth. The selected scalar EC concept cannot be represented as joint N/P/K limitation.

## Arithmetic findings

For solution EC-equivalent D and stored pool S, delta D=I-O-A+R-U and delta S=A-R. Therefore U=I-O-deltaD-A+R. At fixed observed deltaD, omitting positive release R underestimates U. This conflicts with the original source's unqualified overestimation wording; the discrepancy is recorded for Claude in the contract/TODO, without modifying the source science document. Overestimating planted evaporation with the blank gives a downward bias in inferred plant water uptake. Both directions have explicit fixtures.

In the prescribed fixture, stored stock is 0.5+0.3-0.2=0.6 EC-equivalent units; water and scalar accounting close within 1e-14. The independent blank-adjusted fixture gives 0.3 uptake; changing the blank to net release while holding the planted observation fixed gives 0.75. These are invented software cases, not estimates for the actual tomatoes. Declining prescribed adsorption is demonstrated, but a kinetic saturation law has not been invented or validated. The blank's no-plant uptake constraint is zero by declaration; this is not an independent fit/recovery of exchange kinetics.

## Evidence

Final artifact directory: build/reservoir_continuation_20261013_delivery_01/. Development and first regression evidence remains under build/reservoir_continuation_20261013_01/.

- **83 focused tests passed** after final source changes: reservoir_tests_sealed.xml. Covers bidirectional transfers, conservation/no mutation, missing initial pools, negative/nonfinite/overdraw/identity/time failures, uncertainty propagation and signs, modelled split, declared injected response/science refusals, disabled bypass, stale/expired/conflicting/interrupted transaction, real read-only audit, actual CSV-to-calculation binding, supply/removal units and interval endpoint semantics, and actual CLI output protection.
- **24 independent delivery checks passed**, including six fresh CLI executions: prescribed replay, blank-adjusted estimate, missing-blank refusal, actual observations audit, unchanged human-template audit, and synthetic CSV-to-estimate. Verification manifest binds all new sources and preserved human/legacy inputs. No enabled nutrient hook exists, so no native nutrient-causality evidence is claimed.
- Initial combined regression: **254 passed, 1 failed** (76 then-current reservoir cases and 179 legacy/V3/integration/forecast cases). The single failure was the concurrently changing native intake rejecting the historical frame_transforms header in test_b1_pipeline_route_reads_committed_checkpoints_only. It was sent to the native owner, who recorded a version-aware compatibility correction without rewriting the old fixture. Final targeted recheck is reported below; the original failed XML remains preserved.
- Existing exact disabled-P4 nutrient bridge parity is included in the 67 legacy nutrient tests. No new nutrient integration branch was inserted into the native path; this delivery does not claim a separate new bitwise native on/off benchmark.

Commands are recorded in tools/NUTRIENT_RESERVOIR.md. Response insertion files are response_registry_template.json and response_scenarios_unavailable.json in the final build. Both moderate/strong factors remain null; the code rejects their activation. Synthetic records and supplement show exact linkage without changing the human form. user_stated_typical_tray_water.json holds the approximate 0.4 L statement separately.

## What a real EC series can establish

With confirmed tray membership, internal geometry/depth or measured volume, timed supplies/removals, an independent comparable blank, medium-held water/EC evidence and declared error bounds, a record series can constrain interval water and net EC-equivalent residuals under the chosen mixing/scaling assumptions. It cannot by itself identify elemental uptake, distinguish adsorption from release, reconstruct initial stored ions, fit exchange rates, identify a photosynthetic-versus-expansion mechanism or validate crop growth. Seven supply events including the blank are a stated minimum collection target, not sufficient evidence of identifiability. The current October 13 readings lack tray identities, exact times, volumes and blank evidence; they remain observations, with uptake unavailable.

The source's interpretation of a rapid EC rise as medium release is retained as a hypothesis. Missing initial pools and biological response values were not replaced by zeros or chosen to produce desired scenario differences. Complete science values can be inserted through the registry/evaluator API later; actual feedback additionally requires the native owner's causal joint-commit implementation and evidence.

## Final delivery addendum (supersedes the earlier 83-case snapshot)

Final source includes an additional output-boundary guard: both new and existing transaction directories must remain below project build/, so an existing proposal cannot bypass the output restriction. Final focused result: **84 passed**, zero failures, including its regression test. Final independent delivery again passed **24 checks / six actual CLI executions** using those exact sources in **build/reservoir_continuation_20261013_delivery_02/**. Earlier delivery_01 and development artifacts remain unchanged historical evidence.

The existing-model regression result remains **178 passed and one failed** from the first combined run, separately from the new module's 84 passing cases. The native owner recorded a compatibility correction for the historical frame header. Our targeted B1 recheck then did not finish after more than nine minutes and was interrupted (process exit 1, no completed test result). No successful B1/native-parity result is inferred from that interruption, and no other chat's process or source was changed. Its original failure and the owner handoff remain visible; the entire legacy suite is not claimed green. This limitation is separate from the tested tray bookkeeping and the deliberately disabled nutrient feedback.
