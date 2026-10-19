# Observation dashboard MVP — implementation brief (2026-10-18)

Request: extend fish-444/tomato with four household-oriented observation screens and a revised six-week plan. Preserve the Analysis Engine; no diagnosis, automatic control, training or inference.

Inspected baseline: local origin is fish-444/tomato, HEAD d1f89a4. Existing uncommitted product/ work provides FastAPI, SQLite, sensor ingestion, CSV adapter and one technical dashboard. Preserve and extend it. Git network verification is unavailable in the shell; do not claim this is the latest remote revision.

Plan: add explicit Plant State serialization and provenance, period-filtered histories, manual growth input, safe evidence-based checks, reproducible 14-day mock history, four responsive screens, image comparison, documented contracts and roadmap. Existing research CSV lacks height/canopy; keep them unavailable. Model scenarios must never be joined into one growth trend. Default agronomic thresholds remain disabled.

Validation: existing API/CLI tests plus new period, provenance, isolation, manual measurement, safety and persistence cases; browser interaction if available. Work only in product/ and append-only handoff/. Generated data stays in build/. No external deployment or repository push is needed for the requested local DB/API deliverable.

## Outcome (2026-10-18)

Implemented four observation screens, six-domain Plant State, period/device/source isolation, human growth input, mock history and image provenance, and evidence-based checks. Reused the CSV adapter without changing the engine. Remote HEAD verified equal to local d1f89a4cca56994c0abe2b97f4f6f37603a8391a. API/HTTP suite: 21 passed, one third-party deprecation warning. Browser verified Home/Growth/Environment/Action navigation, seven-day filter, action save/list, 390px home layout and no console errors. Fixed a mock generator date-cycle discontinuity found during browser QA. PostgreSQL runtime, real hardware, diagnoses and image uploads remain deferred; roadmap documents weekly acceptance and three domain decisions. No push or PR created.
