# V3 whole-plant development execution

2026-10-11. Work in progress; not an acceptance report yet.

The user explicitly extended the exception to V3: implement conditional rules and separately identify decisions still needed. Codex may select and implement those conditional rules for this task. No independent scientific review is implied.

Inspected: parent rules, project AGENTS/CONVENTIONS, current LOG/TODO, V2 execution/contract/bridge, V3 prompt, earlier Micro-Tom fork and literature contracts, current MTG A1/A2, Stage-2/3 owner reconciliations, original VTC apex/rewrite/sink/dimension code. A2 exists. New MTG section 13 keeps blade curl and flat/bent thresholds on hold and selects full outline including browned margins; the synthetic polygon is not a measured outline.

Implement a separately versioned native development mode, with dynamic graph identity and native polygon surfaces, whole-system carbon accounting, real 30-day integration and continued development. Python freezes inputs, launches the local runtime, independently verifies returned states and collects them. Original files, protected data/config/docs, historical subset results and nutrient tools remain untouched. No upload, training or cross-chat dispatch.

Validation will include actual native runs, birth/stop events, carbon-dependent growth, dark/reserve cases, mesh and graph checks, deterministic replay, observation-contract fixtures and existing regression tests. Quantitative optics uses at least 4.8M rays and multiple seeds. Synthetic timing checks do not establish cultivar accuracy.

## Executed result (supersedes the opening work-in-progress status)

Software scope: implemented and exercised for the explicitly conditional main/sympodial architecture. Conditional simulation: ledger/graph/causality checks passed. Independent Micro-Tom accuracy: not established. Real P1 reconstruction: unavailable in this V3 delivery; the separate queued staged adapter work follows.

Actual GroIMP 2.2.1 / Java 21 execution: `tools.vtc_development` prepares and collects, `tools.vtc_growth_bridge.run` launches `working/Model.rgg::simulate`. The engine inlines the hash-bound annotated `parametersMicroTom.rgg`; the original VTC NRH routine is active, while apex, sink and geometry routines are documented conditional replacements. Original source hashes are retained in prepared.json. Source and returned-mesh viewer snapshot: `build/vtc_microtom_development_v3_20261011/`. This local snapshot is not a redistribution license.

Primary evidence: `build/vtc_dev_v3_acceptance_01/acceptance.json` (11 verified native scenarios and one intentionally rejected deficit), plus `build/vtc_dev_v3_delivery_sufficient/` (65 daily intervals, 4.8M rays). The acceptance suite uses 300k-ray development scenarios and 4.8M-ray controlled optical comparisons. Each scenario retains inputs, parameter registry, actual command, native log, exit, completion SHA256s and independently checked results.

Commands executed:

```text
python -X utf8 -m tools.vtc_development_acceptance --out build/vtc_dev_v3_acceptance_01
python -X utf8 -m tools.vtc_development_acceptance --out build/vtc_dev_v3_acceptance_01 --summarize-existing
python -X utf8 -m pytest tools/tests/test_vtc_development.py tools/tests/test_vtc_growth_bridge.py tools/tests/test_groimp_light_sanity.py tools/tests/test_fsp_carbon_diagnostic.py tools/tests/test_fsp_nutrients.py tools/tests/test_probabilistic_compound_growth.py -q
python -X utf8 -m pytest tools/tests/test_vtc_development.py -q
```

The first suite command completed all native scenarios but initially rejected exact string equality of replay carbon values (2.2324016613073894e-5 versus 2.2324016613073898e-5). Event IDs/dates/rules were identical. The corrected summarizer independently revalidated existing native outputs and passed with explicit 1e-10 numerical tolerance (observed maximum state difference 1.3877787807814457e-17). No failed native run was relabelled successful. The regression command had 263 passes and one error-type failure in deliberate orphan corruption; missing ancestor now raises ContractError. All 30 V3 tests then passed; the other 234 passed unchanged in that regression run.

## Acceptance mapping to actual evidence

| Item | Evidence and result |
|---|---|
| 1 engine | Native completion mode vtc_development_v3, real command/log/exit0 in successful execution.json files; no fallback |
| 2 new leaves | sufficient/events.csv: p1/C0001 initiated day14 under p1/N1; dynamic count grows from 8 to 312 across two plants; 304 new organs |
| 3 stem | states and edges contain p1/I1..I12; funded dimensions, native parent edges and metric stem-length/top-leaf-height tables are independently checked |
| 4 trusses | p1/Truss1 initiated day32 under p1/I9; first funded birth day33 = 5.9910573312139246e-6 structural gC in the high-ray trajectory; four explicit Flower children per truss |
| 5 stop | p1/A3/apex and p2/A3/apex each stop exactly once day44; 312 organs remain, but total mass rises from 2.836543364446236 to 4.063741114656535 gDM by day65 |
| 6 causality | sufficient final total 4.063741114656535 versus limited .21013473718131634 gDM; zero-reserve darkness produces zero mass/area; funded darkness grows from reserves; insufficient-reserve darkness rejected |
| 7 conservation | independent checker recomputes normalized logistic demands, per-tissue maintenance, NRH gross, allocation, structural carbon and reserve balances; max sufficient residual 2.22e-16 gC; funded_birth rows bound to first-positive transaction |
| 8 dynamic optics | actual pre-light consumed triangle coordinates match preceding committed meshes; fixed receiver p2 falls .44625 to .37100 umol/s (16.86%) as p1 grows; frozen control constant .44625; effect .07525 exceeds max two-seed difference .01350 umol/s at 4.8M rays |
| 9 structure | default PAIRS 1,1,2 plus three_pairs 1,1,3 scenario; variable rachis count, terminal T and PnL/PnR identities, A2 derived angle fields and actual two-triangle diamond blades |
| 10 spin-up | all boundaries day0..65 returned; day30 has 194 organs and .5958481148665472 gDM in high-ray run; same native state continues beyond30; full-sequence replay matches IDs/events and numeric tolerance |
| 11 observations | Stage-2 exact-column fixture from native day30, explicit hidden-state supplement, 8 actual further daily intervals, 72 new organs; initial IDs/coords/masses round-trip; real producer not claimed |
| 12 robustness | deliberate rehashed orphan, negative/nonfinite state, over-allocation, reserve, stale consumed geometry and duplicate event corruptions rejected; wrong mode/schema rejected; actual .01s timeout in build/vtc_dev_v3_timeout_01 recorded failed without results |
| 13 regression | 30 V3 tests pass after orphan fix; 234 bounded/P2/P3/P4/nutrient tests passed; replay above |
| 14 evidence | all coefficient origins retained; fixed-NRH temperature/CO2 response inactive, nutrient feedback false, geometry hypothetical and biological validation not_established |

The optical comparison uses two seeds and is evidence for this controlled scene, not a universal error bound or a full convergence study. Daily-only integration is supported; subdaily convergence is not established. Frozen geometry and fixed-receiver cases intentionally decouple later mass from fixed optical geometry and are diagnostic controls only.

## Outputs, limits and remaining decisions

The viewer under the versioned snapshot draws the actual exported triangle coordinates, highlights initial versus future-organ provenance, and shows persistent apex-stop labels. `native_geometry.png` shows returned day30/44/65 meshes and was visually inspected. Historical collected viewers remain immutable; the newer separate presentation fixes their old horizontal-width rendering approximation.

See `tools/VTC_DEVELOPMENT.md` for CLI/schema/API, and `handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md` for the requested separate review/settings list. Planar diamond leaflets and slender diamond structural/flower proxies are explicit; root geometry, cotyledon/hypocotyl morphology, unrestricted lateral shoots, fruit/yield, curl and nutrient stress are excluded. A full_outline blade is not evidence that browned tissue has equal photosynthetic activity.

Remaining V2 mapping: native internodes/compound leaves/trusses/apex termination, root maintenance, carbon-funded geometry and real 30-day spin-up now have V3 evidence; Stage-2 fixture import exists. Actual Claude P1 optical producer compatibility belongs to the queued staged integration. Fruit pools remain outside V3 scope. No historical V2 incomplete manifest was rewritten.
