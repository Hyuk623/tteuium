# Architecture map and disposition

Baseline: `d1f89a4cca56994c0abe2b97f4f6f37603a8391a` (inspected 2026-10-14).

```text
RESEARCH (unchanged, offline)
capture + config -> calib (ChArUco/PnP) -> mask + quality
observations -> state + track -> P1 state CSV/JSON package
leaf surfaces + scene -> light -> plant_light.csv + run_summary.json
tools/, phynotype2/, flow/ -> research tooling, experiments, workflow inventory
                           |
                    explicit file adapter
                           v
PRODUCT (independent process and dependencies)
mock / device -> versioned JSON -> FastAPI -> SQLite
                                   |          |
                               dashboard <- query API
                                   |          |
                               actions    advisory rules
```

| Existing area | Decision | Evidence / boundary |
|---|---|---|
| `tomato3d/calib`, `mask`, `io`, stage1 CLI | Reuse unchanged | Capturing, pose/QC and unavailable semantics; not imported by server |
| `tomato3d/state`, `track` | Reuse output contracts | `state/package.py` publishes snapshots, `schema.py` distinguishes area types/status/evidence; old track entrypoint still has a stub |
| `tomato3d/light` | Reuse output | `budget.plant_rows` and `cli/run_light.py`: plant-level area, intercepted/absorbed photons, CV; simulated values remain model estimates |
| `tools`, `phynotype2`, `flow` | Preserve / defer integration | Existing research and native-engine orchestration; no execution or coupling in product request path |
| `recon`, `fuse3d`, `organ`, `graph`, `pheno`, `twoview`, `rules` legacy entrypoints | Defer | Numerous explicit NotImplementedError stubs; not an MVP dependency |
| Existing source deletion | None | No evidence justifies removing research assets |
| Direct research-to-UI coupling, guessed crop thresholds, automatic actuation | Reject for MVP | Breaks boundaries or implies unsupported agronomic knowledge |

## Product structure

`backend/api.py`: HTTP and static dashboard; `schemas.py`: strict contract models;
`db/`: schema and connection factory; `services/`: atomic ingestion and advisory rules;
`adapters/`: read-only research CSV mapping and upload CLI;
`frontend/dashboard/`: no-build HTML/CSS/JS; `device_contract/`: exported JSON schema and mock;
`tests/`: isolated product tests; `docs/`: architecture, adapter mapping and delivery plan.

## Storage and scope

devices 1:N sensor_readings; plants 1:N devices, images, plant_measurements, actions;
sensor_readings 1:N recommendations. Foreign keys are enforced. Each sensor event has a unique event_id,
device, UTC observation time, receipt time and original normalized payload. Replays are idempotent;
conflicting event reuse is HTTP 409. Writes and generated recommendations share one transaction.
Readings retain history; latest is ordered by observation time, not arrival time.

The single-user local MVP has no account/auth system. Bind to loopback only. Remote deployment requires
authentication, TLS, authorization, rate limiting, backups and database migrations first.
Images are metadata references, not an upload or image inference service. No remote URL is fetched.
