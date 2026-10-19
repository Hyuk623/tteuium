# Product MVP implementation brief

Request: preserve tomato3d as the Research/Analysis Engine and add an independently runnable product boundary: device JSON -> SQLite -> API -> dashboard -> advisory rules -> action log, plus research-result ingestion.

Inspected baseline: d1f89a4cca56994c0abe2b97f4f6f37603a8391a. Read AGENTS.md, CONVENTIONS.md, README, state/package.py, state/schema.py, light/budget.py, light/pipeline.py and cli/run_light.py. Research includes working state/light pipelines and explicit reconstruction/diagnosis stubs. Root README is not a complete inventory of current capabilities.

Scope: add product/ (including its own docs/tests/dependencies) under the user's explicit authorization. SQLite storage is a product requirement, not a change to research CSV conventions. No edits to tomato3d/, tests/, tools/, config/, docs/, data/ or synced project sources. No training, inference, hardware actuation, LLM or remote publication. Generated runtime files go under build/.

Design and sequence: first product/docs/architecture.md and roadmap.md; then schema, storage, advisory services, file adapter, HTTP API and static dashboard; finally mock HTTP end-to-end and failure-path tests. The API runs independently of OpenCV and the research dependency graph. Unknown thresholds remain inactive; demo thresholds are explicitly synthetic.

Validation: isolated product tests exercise contract rejection, atomic ingestion, duplicate/conflicting retries, rules, actions, SQLite persistence and research unavailable/provenance semantics. Real hardware and biological validity cannot be claimed from mock data. Actual results will be appended below.

## Outcome
Implemented the planned local slice. 19 product tests pass, including real HTTP mock and adapter CLIs. Browser action saving and research/missing-value display verified. See product/docs/delivery.md for exact file inventory and limitations. Existing research files remain unchanged. No physical or biological validation claimed.
