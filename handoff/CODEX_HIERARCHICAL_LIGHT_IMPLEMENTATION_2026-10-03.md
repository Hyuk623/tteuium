# Hierarchical light implementation brief

The user invoked CODEX_HIERARCHICAL_LIGHT_INTERACTION_PROMPT_2026-10-03.md as the active goal. Implement its complete direct-light counterfactual calculation, identity/provenance audits, source-removal matrices, output tables/viewer, bounded native preparation/execution interface, and focused verification under tools/ and tools/tests/.

Inspected current behavior: the shared direct solver counts distinct physical surfaces, samples triangles at equal area, and uses original occluder indices for receiver exclusion. It supplies per-fixture received PPFD but no hierarchical attribution. Existing canopy and native adapters provide materialization, surface gates and job machinery. Reuse them without editing owner-protected files. A compound membership mapping is a separate required input; organ labels alone are insufficient.

Preserve target tissue and fixed background in all eight A/B/C subset scenes. Remap receiver indices after filtering; namespace optical identities by instance/session. Export raw subsets, signed Shapley allocations and overlap terms separately from nonadditive source-removal effects. Audit unavailable identity separately from unavailable transport. Preserve supported partial surface coverage and diagnostic-only validity.

Execution scope: deterministic synthetic direct-light calculations and focused tests are authorized. Native preparation does not execute jobs; a bounded explicit --execute path will be implemented, but native runs are not required or implicitly launched in this session. No training, source data edits, configuration changes or live service changes.

Verification: analytic layered shading, redundant shadows, surface crossing identities, receiver remapping, missing/stale/conflicting inputs, weighted aggregation, source-removal behavior, native preparation contracts and viewer interactions. Produce a fresh synthetic build and a current real-input blocker audit. Record actual results and command lines in a completion supplement after testing.

## Delivered and verified

Implemented tools/hierarchical_light.py, hierarchical_light_native.py, hierarchical_light_demo.py, hierarchical_light.html, HIERARCHICAL_LIGHT.md and tools/tests/test_hierarchical_light.py. Direct transport, eight-subset accounting, signed allocation/overlap, weighted summaries, directed matrices, input audits, source/target filters, provenance/stale checks, native preparation/opt-in/collection and the standalone viewer are executable.

Integration command: python -X utf8 -m pytest tools/tests/test_hierarchical_light.py tools/tests/test_plant_light_bridge.py tools/tests/test_canopy_light.py tools/tests/test_groimp_density.py tools/tests/test_ppfd_validation.py -q: 113 passed in 35.63 seconds. Final focused command after output/readiness and filtered-view corrections: python -X utf8 -m pytest tools/tests/test_hierarchical_light.py -q: 41 passed in 15.96 seconds.

Final delivery: build/hierarchical_light_20261003_04/. Reproduce with python -X utf8 -m tools.hierarchical_light demo --out build/<fresh_directory>. See REPRODUCTION.md and verification.json for requirement evidence and executed commands. Browser controls, source-level selection, signed/received/absorbed quantities and filtered receiver area were checked; no console errors observed. Final outputs and both prepared backends are fresh by source/code/artifact hashes. The earlier _01/_02/_03 runs are superseded.

Native: 30 prepared hashed jobs, two seeds, 100000 rays/job, depth 8. The execute CLI without --execute reports 3000000 planned rays and creates no execution folder. No native optical jobs ran. Native collector tests use artificial logs, explicitly distinct from native reflection/conservation validation. Direct-only results and native transport are not interchangeable. All physical validity flags remain false.

Real inputs: build/hierarchical_light_real_audit_20261003_01/ re-audits four explicitly known snapshots. All lack light_scene, leaf_surfaces and selected plant case; dwt_t3 also lacks registered geometry provenance. Sources and media remained unchanged. A reviewed compound membership input is required for real hierarchy attribution. No leaves, lamp coefficients or identity reviews were invented. This is not a claim that no newer files exist elsewhere.

Optional DLI is left unavailable; no schedule inference or physiological/growth prediction was added. Partial supported area is not extrapolated. No owner-protected source file was edited; reusable source hashes were checked against the first synthetic run. Test browser/server are temporary and can be closed after viewing; the saved viewer is standalone.
