# P2/P4 flow refresh

User explicitly requests updating the Codex part of flow using P2_EMPIRICAL_GROWTH_BOUNDARY_EXECUTION_2026-10-13.md and P4_NUTRIENT_RESERVOIR_EXECUTION_2026-10-12.md. This supersedes the earlier no-flow-edit instruction for this bounded documentation task.

Scope: merge the previously supplied empirical-field rows, add actual boundary/reservoir modules and evidence paths, reconcile related DLI and prompt status, update README P2/P4 and the Codex hook summary, regenerate FLOW_STATUS with the unchanged checker. Preserve unrelated P1/P3 and human rows. No source, native engine, records or model changes. Before writing, snapshot the existing files and reject concurrent byte changes.

Evidence limits: P2 has 86 focused passing tests and three native light-only runs / 135 leaf-interval comparisons; it does not verify empirical growth/NRH, complex original geometry, repeated incidence or terminal photon closure. P4 has 84 final focused tests and 24 checks / six CLIs; transaction is fixture-only and actual feedback remains disabled. Its original existing-model result includes one failure, and its targeted recheck was interrupted; do not claim all regressions passed. Final evidence directories, not superseded intermediate snapshots, are linked.

Validation: unchanged unrelated row equality, added-path existence, valid status vocabulary, stable row keys, checker exit and exact generated-render equality. No numerical simulations or software regression rerun is required for this metadata update.

Outcome: 19 rows added and 4 existing related rows updated (159 -> 178). Unrelated rows preserved exactly as parsed; all referenced concrete paths exist. Unchanged checker main(['--md']) returned 0 and FLOW_STATUS matches its render. README P2/P4 and Codex hook/remaining-boundary summaries updated; P1/P3 historical wording retained and dated explicitly. Snapshot and verification: build/flow_refresh_p2_p4_20261013_01/. No numerical implementation or tests re-executed.
