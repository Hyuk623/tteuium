# P4 carbon diagnostic implementation execution

Date: 2026-10-04. The user explicitly requested code/model changes against
CLAUDE_FSP_CURRENT_HANDOFF_2026-10-03.md after the specification delivery.
This authorizes the isolated diagnostic implementation described there. It does
not change D1-D10 or adopt unresolved biological coefficients.

## Inspected state and implementation scope

No tools/fsp_carbon_diagnostic module exists. The earlier specification/evidence
pack is complete. P3 has now delivered D8-D10 with 142 recorded passing tests;
consume its frozen audit representation without editing or invoking its engine.
No prior interrupted implementation or running command was found in this turn.

Implement the eight contracted diagnostic functions, explicit templates/audit/
diagnose CLI, result schema and English usage guide under tools/, with focused
tests under tools/tests/. Model equations: evidence-gated NRH/signed leaf exchange,
maintenance with explicit activity, supported mass-demand inversion, carbon-budget
statuses and a separate funded hypothetical conservation ledger. P3 inputs remain
immutable. No runtime fitting, light solving, allocation/form updates or integration.

Use explicit hypothetical parameter packs to exercise numerics while scientific
review remains unresolved. Reviewed inputs require recorded review/provenance;
no literature defaults or automatic domain acceptance. Unknown data block only
dependent components. Outputs distinguish component fluxes, scope, status, reasons,
P3 coupling and source hashes. Initial/root/reproductive/boundary assumptions must
be supplied rather than guessed.

## Serialization refinements for implementation

Preserve the exact public function names/signature and nine core output fields.
The parameter pack and optional producer references use external SHA256 envelopes
of canonical JSON payloads, avoiding a self-referential pack hash. The CLI may load
explicit file references with byte hashes; pure arithmetic accepts materialized
objects and does not load/execute producers. Document exact nested record fields
in tools/FSP_CARBON_DIAGNOSTIC.md and the schema.

Light quadrature uses explicit patch/fixture inventories, one-sided area weights,
backend/replicate and complete half-open time intervals. Different fixture/time
partitions are aligned at their union of boundaries; sum simultaneous fixtures
before the nonlinear response. Replicates are diagnosed separately. Explicit
piecewise-constant forcing is an input approximation, not inferred observations.
Maintenance uses explicitly declared interval mass/activity histories or an
explicit start-state approximation. Unknown scope, source or exposure is unavailable.

These are serialization/numerical choices implementing the existing contract,
not new physiological assumptions. Missing required evidence remains unavailable.

## Verification plan

Run focused numerical/negative/immutability tests: units, light basis, nonlinear
patches, fixtures versus replicates, day/night and respiration overlap, Q10/activity,
mass inversions, growth-cost accounting, root/subset/new-organ/terminal scope,
zero demand and deficits, tolerances, provenance/hash/identity/gap rejection,
full P3 audit and export consistency. Use independent analytical expectations and
refinement/reporting-grid checks. Exercise blank audit and synthetic CLI runs in
fresh build/p4_implementation_20261004_01 directories. Preserve original source
and prior evidence hashes. Report software results separately from biology.

## Outcome

Implementation and checks in progress.

## Completed implementation outcome

Implemented tools/fsp_carbon_diagnostic.py, fsp_carbon_diagnostic_schema.json,
FSP_CARBON_DIAGNOSTIC.md and dependency declaration, plus the explicitly invented
fixture generator and focused tests. All eight public functions and three CLI
operations are present. No P3/P2/core/config/observation edits or integration.

Refined runtime records for typed reproductive scope, per-organ temperature basis,
hashed file references, endpoint-state hashes distinct from native producer mesh
hashes, complete light inventories, new-organ material and component-only missing
science. Missing photosynthesis inputs no longer block independently supported
mass demand/maintenance. CSV/JSON references are read and hashed from the same
bytes, and exports reject inconsistent provenance/identity/accounting.

Final tests: 78 passed, stored in build/p4_implementation_20261004_01/tests_delivery.xml.
Final CLI runs: 11 successful commands, 9 hypothetical scenarios under final_03.
Conservation and existing P3 metadata inspection passed. The separate completion
audit has 196 passing checks and 24 software requirement groups. Initial runs are
retained as historical evidence; final_03 matches current code hashes.

Authoritative handoff: CODEX_P4_IMPLEMENTATION_HANDOFF_2026-10-04.md. Earlier
scientific review dependencies remain open; no coefficients were adopted as
target defaults, no biological accuracy claim is made, and D3 linking is deferred.

Final completion refinement: explicitly enforce parameter-pack scope before
mass/budget use, preserving independent light exchange when scopes differ. The
added regression brings the final suite to 79 passing tests. Current CLI/code
evidence is final_04 (11 successful commands/nine cases); final_03 and earlier runs
are historical. The 196-check delivery audit still covers 24 requirement groups.
