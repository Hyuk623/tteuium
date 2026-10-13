# P4 implemented carbon diagnostic handoff

Date: 2026-10-04, Asia/Seoul. Author: Codex.

The user explicitly requested code and model changes after the specification-only
delivery. The isolated P4 diagnostic is now implemented and exercised. It connects
declared metric light samples to conditional photosynthesis, maintenance, organ
structural demand and carbon sufficiency. P3 remains the sole realized-growth
owner; no P3 geometry, rate, event, seed or trajectory-weight changes occur.

## Delivered files and behavior

- [Model and CLI](../tools/fsp_carbon_diagnostic.py): all eight contracted functions, templates/audit/diagnose commands, component-scoped availability, immutable input provenance and CSV/JSON export.
- [Exact runtime input guide](../tools/FSP_CARBON_DIAGNOSTIC.md) and [schema](../tools/fsp_carbon_diagnostic_schema.json): nested fields, units, hash envelopes, statuses and semantic checks.
- [Hypothetical fixture generator](../tools/fsp_carbon_diagnostic_demo.py): invented numbers only, separate from production parameter defaults.
- [Tests](../tools/tests/test_fsp_carbon_diagnostic.py) and [tool dependency](../tools/fsp_carbon_diagnostic_requirements.txt).

Implemented numerics include stable NRH before or after explicitly assigned leaf
respiration, signed night exchange, Q10 maintenance with declared activity/history,
direct or independently supported inverse mass demand, growth-cost accounting,
reserve-protected sufficiency and a separate funded hypothetical balance audit.
Area is one-sided m2, exchange duration is elapsed seconds and maintenance's
source-day conversion is explicit. Fixture irradiance is combined before the
nonlinear response; alternative replicates remain separate.

The implementation does not install the source paper's coefficients. A compatible
pack must be explicitly hypothetical or carry a recorded review and per-parameter
evidence. Undefined light basis can block supply while preserving supported
maintenance/demand. Missing roots, reproductive scope, reserves, subset boundaries
or exposure remain explicit unavailable dependencies. Negative mass changes are
not remobilization credits; new organs cannot receive free initial material.

## Current producer and integration boundary

P3 has since completed its D8-D10 software delivery (142 tests recorded by its
owner). P4's read-only audit successfully consumed that saved run's original
manifest and frozen model, including full environment paths and size-target DLI.
This inspected existing metadata only; it did not execute P3 or link P2 to P3/P4.
Frozen fitted-pack effects and calendar/normalized-clock provenance remain
explicit. Unknown aliases or stale hashes cannot masquerade as independence.

D5 is still an explicit pre-P3 `apply_parameter_set` route, never a P4 runtime call.
P4 retains photosynthesis even when P3 uses DLI. P3 output is never clipped/scaled
or reweighted. D6 permits unavailable P4 in the later first synthetic pass; D3
continues to defer cross-project adapters and the end-to-end run.

The isolated request uses canonical hashes of complete endpoint state arrays.
Native P2 mesh/file hashes are distinct and must remain preserved in producer
metadata. A later reviewed geometry association/adapter must connect these
representations; the implementation does not silently rename a native mesh hash.
Light integration currently uses an explicitly declared fixed supported-tissue
snapshot and arbitrary supplied time-varying forcing. It does not create optical
tissue for new P3 envelopes or run a dynamic geometry/light feedback loop.

## Executed verification

The authoritative package is `build/p4_implementation_20261004_01/`, with current
CLI outputs under `final_04/`. Earlier sibling runs are preserved intermediate
evidence; use `final_04` for current production-code hashes.

| Evidence | Actual result |
|---|---|
| `tests_delivery.xml` | **79 tests passed**; independent analytic NRH/maintenance/demand expectations, negative inputs, scope, provenance, immutability and export checks |
| `final_04/commands.json` | **11 CLI commands succeeded**, including blank templates and unavailable audit |
| `final_04/cli_cases.csv` | **9 hypothetical scenarios**: sufficient, zero demand, growth deficit, maintenance deficit, missing reserve, missing subset boundary, signed net night exchange, existing P3 DLI, and hashed CSV input |
| `final_04/balance.json` | Funded hypothetical carbon ledger balanced within supplied tolerance |
| Refinement test | Midpoint temperature-forcing h/h2/h4 errors decrease at the expected second-order rate; unchanged forcing gives partition-invariant totals |
| `final_04/existing_producer_audit.json` | Existing P3 audit/config hashes verified; coupling complete and D9 compatible for that stored example |
| `verification.json` | **196 delivery checks passed**; all **24 software requirement groups** mapped to executed test evidence |
| `manifest.json` | Current code/schema/test/document hashes, fresh final-output/source hashes and preserved earlier evidence |

Reproduce the tests from project root:

```powershell
python -X utf8 -m pytest tools/tests/test_fsp_carbon_diagnostic.py -q
python -X utf8 build/p4_implementation_20261004_01/run_delivery.py --out build/my_fresh_p4_delivery
python -X utf8 build/p4_implementation_20261004_01/verify_delivery.py
```

The verifier checks the saved `final_04` delivery. The CLI reproduction creates
another fresh package. Original physiology source artifacts and inspected P3 /
calibration / common IO files retain their hashes. No protected pipeline/config/
human observations were edited. No remote execution, fitting or training occurred.

## Model evidence and remaining review

The passing cases are software and synthetic arithmetic evidence. They do not
establish target-cultivar parameters, absolute biomass accuracy or improved growth
prediction. Every exported diagnostic keeps `accepted_for_domain=false`.

Claude's existing review queue remains: incident versus absorbed NRH, net versus
before-mito respiration, ASR and CH2O/CO2/source mass conflicts, root/fruit ordering,
independent organ allometry, initial masses/reserves, carbon fractions and valid
temperature/activity domains. No scientific verdict was inferred from a green test.

Practical serialization decisions are documented in the runtime guide: external
hash envelopes, disjoint patch/fixture inventories, per-organ temperature basis,
typed reproductive scope, explicit new-organ material and independent interval
stocks. Hypothetical mode exercises them without making up real observations.

The prior specification verifier checks absence of production modules as a
historical specification-only invariant. That invariant is intentionally superseded
by this authorized implementation; use this delivery's verifier for current code.
Prior evidence and scientific decisions were not rewritten.


## Superseding safety revision, 2026-10-04

Current code, schema and tests are now covered by [P4 growth Science execution](CODEX_P4_GROWTH_SCIENCE_EXECUTION_2026-10-04.md): 105 tests, 12 CLI commands and 256 delivery checks. Use build/p4_growth_science_20261004_01 for current hashes. The implementation delivery above remains historical evidence; its pinned verifier is not the current-code verifier. Q2 remains undecided.
