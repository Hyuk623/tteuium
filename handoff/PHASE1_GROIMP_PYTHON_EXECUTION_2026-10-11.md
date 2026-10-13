# Phase 1 VTC/Python execution brief

2026-10-11. Codex, executing the user's explicit one-task exception for the Claude-addressed V2 prompt. Scientific selections below are conditional software scenarios, not biological acceptance.

## Before implementation

Read parent rules, local AGENTS/CONVENTIONS, current handoffs, V2 and earlier fork/literature prompts, MTG convention and standalone A1 instructions, Stage-2/3 reconciliations, carbon/nutrient interfaces, VTC sources and existing GroIMP launchers. A2, phyllotaxis_fit and the Micro-Tom fork were absent. No other agent claimed the new bridge files.

Original VTC is not carbon-driven geometrically: Leaf.calcDimensions and Internode.calcDimensions integrate age curves independently of allocation. main.step computes light before renew advances climate and changes graph state. FvCB is selected but calcPhotosynthesis uses clipped output[2] (gross), not signed output[0]. PlantBase clips supply, resets reserves conditionally, and uses F_CO2=0.6 without an elemental-carbon state. These behaviors require explicit conditional corrections rather than endorsement.

Plan: create a versioned local fork and source/hash/diff manifest; a documented science/IO contract; strict frozen CSV/JSON packages; native GroIMP execution with run-specific completion; independent Python conservation/identity/geometry checks and atomic publication; actual multi-step synthetic scenarios and failure tests. Keep the original VTC sources and existing Python engines unchanged. Output only to fresh build folders. No training, remote compute, uploads or messages.

Licensing: the local archive and inspected upstream repository expose no model-code LICENSE. Keep attribution and report unresolved redistribution terms. No upload or redistribution is authorized or performed.

## Results

Pending implementation and execution. This brief is not completion evidence.

## Executed results (appended 2026-10-11)

**Overall V2 status: INCOMPLETE.** Implemented and executed a bounded existing-leaflet native mode, not the entire original-VTC Micro-Tom developmental engine. This is a material scope shortfall, not a request to redefine the original acceptance criteria. The full-V2 status remains incomplete in every results manifest.

### Delivered behavior

* tools/vtc_growth_bridge.py: audit/fork/prepare/run/collect/demo commands; safe argument-list subprocess; timeout/exit handling; native init acknowledgement and completion hashes; frozen ratio pointer; atomic verified publication.
* tools/vtc_growth_io.py: exact CSV/JSON validation, identity/frame/time/provenance constraints; independent carbon, allocation, growth/dimension, consumed-geometry and continuity checks. Unknown or invalid values are rejected, never filled with zero.
* tools/vtc_growth_fork.py: attributed local original-source copy plus native phase1 template, exact original VTC NRH function fragment, corrected per-plant allocation/reserves and graph-managed geometry updates. Python does not calculate or apply growth.
* tools/tests/test_vtc_growth_bridge.py and tools/VTC_GROWTH_BRIDGE.md; the new English science/IO contract; source manifest/diff and Korean local run guide in build/vtc_microtom_20261011/.
* Native and normalized ledgers, stable source/native identities, source/engine hashes, geometry sequence, pre-light native geometry snapshots, ratio comparisons and self-contained viewer in fresh final run folders.

The original source files are preserved byte-for-byte under upstream/. No original development file is advertised as modified or active. Only the separately named bounded entrypoint executes. No parametersMicroTom.rgg, determinate apex, rank-dependent rachis implementation or 30-day seed spin-up was delivered. A fixture biological age of 30 is not spin-up evidence.

### Actual local runtime evidence

GroIMP **2.2.1**, Temurin Java **21.0.12.1**, Python **3.13**. core.jar SHA256: `35c605d65d9b54fe64cdf93bf28ae44ae7a1b6ded03b461dedcb0156a5c22147`.

16 successful final scenarios, each with 3 committed daily intervals (**48 intervals total**), plus intentional native deficit and process-timeout failures. No mocked process is counted as an engine run. Exact command arrays, versions, working directories, native exit codes and log hashes are in each execution.json. All successful native processes returned zero and wrote their own run-specific completion record.

Final folders share prefix `build/vtc_python_phase1_20261011_final_`:

`sufficient`, `limited`, `dark`, `frozen`, `observation`, `feedback`, `feedback_frozen`, `feedback_repeat`, `feedback_highrays`, `feedback_seed`, `lower_alone`, `phone`, `feedback_4800k_5000`, `feedback_4800k_5100`, `respiration_funded`, `dark_reserve`.

Failures: `dark_deficit` (engine exits zero but independent conservation fails, outputs isolated in partial/) and `timeout` (actual Java process killed, no publication). Earlier run01/run02 exposed compile/command failures and also did not publish success. Earlier prototype folders with results receive SUPERSEDED.json; they do not serve as final acceptance evidence.

### Quantitative checks

* Same initial subset DM 0.060 g. At day 3: sufficient **0.7137906593 g**, limited **0.08223393835 g**, darkness **0.060 g**. Deliberately synthetic masses/rates; no biological growth-rate interpretation.
* Maximum normalized carbon residual across the original 12 final scenarios: **3.82e-17 gC**, below 1e-9 gC tolerance. Nonzero funded leaf respiration was run separately and charged once. A dark-reserve scenario consumes rather than resets the initial reserves; final reserve is zero for both plants.
* Two-plant causality scene: lower leaflet dimensions and demand are fixed; only the upper leaflet grows. At 300k rays, lower absorbed light is **1.536 → 0.456 → 0.452 umol/s**. Frozen-geometry control stays **1.536**, while the lower leaflet alone receives **4.228**. This establishes native geometry feedback and cross-plant shading within the declared synthetic scene; pools remain separate.
* Deterministic replay from the frozen initial state: maximum numeric delta **2.27e-13** across native geometry/organ/ledger/consumed-geometry/sensor tables. No dimension-only checkpoint resume exists.
* Sampling assessed at 300k, 1.2M and 4.8M rays, two seeds. 300k vs 1.2M lower-leaf differences reach **9.4%**; do not advertise 300k as converged. At 4.8M, two seeds' final lower light is **0.40275 / 0.402 umol/s** (0.19% spread), with approximately 4% day-0 spread. Strong shading effect persists. No universal convergence or physical-accuracy bound established.
* Native phone-grid comparison actually reads and freezes the human's light_ratio_map_20261010.csv. Normalized RMSE **0.16033** against a hypothetical grid. Height/spacing and lamp are assumed; this is neither physical calibration nor absolute PPFD validation. Slot pointer is also present in the local fork. No human record was edited.
* Hand check: 1000 umol CO2 = 0.012011 gC. Allocating 0.01 gC at efficiency .75 yields .0075 structural gC plus .0025 growth-respiration gC; at structural fraction .45, that is .0166667 gDM. No native biomass-equivalent reserve was silently reinterpreted as gC.

### Tests

Actual command:

```powershell
python -X utf8 -m pytest tools/tests/test_vtc_growth_bridge.py tools/tests/test_groimp_light_sanity.py tools/tests/test_fsp_carbon_diagnostic.py tools/tests/test_fsp_nutrients.py tools/tests/test_probabilistic_compound_growth.py -q
```

**234 passed in 36.32 s** (44 new bridge cases, 190 existing regression cases). New tests include rehashed corruption, stale completion identity/count/hash, reserve reset, altered respiration/allocation, wrong geometry ownership, stale consumed geometry, invalid units/frame, missing masses/parameters, malformed ratios, pointer freeze and non-promotion of observation-like fixtures. Native-evidence tests are clearly identified and skip if actual local evidence is absent; the actual engines were run separately as recorded above.

Machine-readable acceptance: build/vtc_python_phase1_20261011_acceptance/acceptance.json. Figure: feedback.png / feedback.svg. Interactive returned-state viewer: build/vtc_python_phase1_20261011_final_feedback/results/viewer.html. Source/download hashes were rechecked successfully. Original historical Python modules and protected config/docs/records were not edited.

### V2 acceptance disposition

| # | Status | Evidence / remaining gap |
|---|---|---|
| 1 Runtime | Bounded pass | Actual launch, 3 consecutive intervals and native completion; full original developmental project not run |
| 2 Initialization | Partial | Synthetic and observation-like CSV fixtures; no direct Stage-2 importer or original seed spin-up |
| 3 Mass/geometry | Bounded pass | Constant-SLA native managed dimensions, consumed-shape checks; rectangular blades only |
| 4 Carbon | Bounded pass | Per-plant subset balance, nonzero respiration and reserve consumption; roots/stem/fruit not represented |
| 5 Causality | Bounded pass | Sufficient/limited/dark and funded/unfunded respiration cases |
| 6 Feedback | Bounded pass | Growing upper/fixed lower vs frozen scene; original setter-cache bug found and corrected |
| 7 Canopy | Bounded pass | Two plants share light scene, separate identities and carbon ledgers |
| 8 Failure | Pass for implemented mode | Corruption/units/IDs/ratios/parameters/timeout/deficit fail closed |
| 9 Replay | Bounded pass | Full frozen-input replay; checkpoint resume unsupported |
| 10 Numerics | Assessed, not physically accepted | Daily only; ray/seed assessment and noise reported |
| 11 No duplication | Pass for implemented mode | Existing regressions pass; native engine imports no Python physiological updater |
| 12 Evidence | Pass for non-promotion | Conditional labels preserved; all real-data validation gaps remain |

### Unfinished work / scientific limits

Full V2 remains open: original VTC Micro-Tom determinate apex and truss cadence; internode cap with evidence; rank-dependent compound geometry, segment bending and middle-pair sizing; 30-day climate-driven seed spin-up; true Stage-2/P1 observation initialization; stem/root/fruit demands and mass/geometry consistency; original-model physiological/scientific reconciliation beyond the bounded extension. No A2 or phyllotaxis_fit implementation was added. Missing leaflet blade tilt/curl definitions were not declared solved.

Native optics are explicit black flat rectangular blades and an assumed point LED, with symmetric face response. NRH upper-layer Merlice coefficients are borrowed, not Micro-Tom coefficients; original empirical fit preprocessing remains unreviewed. Temperature and CO2 are stored and interval-bound but do not drive the selected fixed-coefficient response. Potential demand is an explicit fixture input, not a validated age-dependent sink law. Phone ratios cannot set absolute carbon supply. Source-code redistribution license remains unclear; no upload/distribution occurred.

The user-authorized exception allowed this execution and the new contract; it did not supply missing measurements or create independent scientific validation. Do not mark the entire V2 request completed from these artifacts.
