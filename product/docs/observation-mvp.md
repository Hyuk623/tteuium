# Observation MVP contract and architecture

## Boundary

`tomato3d` (unchanged Analysis Engine) → exported `plant_light.csv` → adapter → validated research import → SQLite `plant_measurements` → Plant State API → Home / Growth / Environment / Action dashboard.

Device JSON or mock generator → ingestion validation → `sensor_readings` → Environment and data-quality checks. Manual height input → observation validation → `plant_measurements`. Manual care → `actions`. Image references → `images` + `image_sources`. Research jobs are never launched by an HTTP request.

Reuse: existing device contract, replay-safe ingestion, SQLite connection boundary, research CSV adapter. Extend: four screens, evidence-aware read model, 14-day fixture, human observation entry. Defer: fruit/condition/diagnosis, automatic care, PPFD/DLI/distribution imports, production hosting.

## State and provenance

`GET /api/plants/{id}/state?days=7|14|30` (any integer 1–30 accepted) returns six sections. Growth/Environment/Light have supported capability; missing data is unavailable. Fruit/Condition are planned/unavailable (diagnosis unavailable). Action is manual. Capability support never implies a currently available observation or validated diagnosis.

Measurement status accepts measured/human/derived/model/model_estimated/unavailable. Legacy model_estimated is preserved. A value must be null exactly when unavailable. Research import accepts only model/model_estimated/unavailable; manual API accepts human/unavailable; mock observations accept model/unavailable with evidence=mock. No arbitrary API caller can label a research import measured. Input routes currently do not produce derived/measured growth values; these are future contract options. Sensor source=device represents an asserted device observation, not proof of calibration; mock remains separately identified.

A measurement preserves import ID, observation time, units, source reference/hash, evidence, scenario and geometry variant. The graph groups by metric + source + scenario + geometry variant + status; unlike origins are never joined. Manual entry has no source file: source_sha256 is the documented all-zero sentinel, not a claimed checksum. Research adapter hashes the actual CSV bytes.

Image source is explicit human/device/mock/unknown. Existing records default to unknown. The new image_sources table is additive and preserves previous DB contents. Only references are stored; files are not uploaded. Browser renders HTTP(S) references, shows errors for missing assets, and labels mock drawings. Human action entries are manually recorded, including actions recorded against the demo plant.

## Tables

| Table | Key / relationship | Purpose |
|---|---|---|
| plants | id | Plant identity/name |
| devices | id; plant_id → plants | Device assignment |
| sensor_readings | event_id; device_id → devices | UTC observed/received times and immutable JSON payload |
| research_imports | import_id | Immutable provenance payload; both research and validated human/mock observation batches |
| plant_measurements | id; import_id; plant_id; unique(import_id, metric) | Value, unit, status and observation time |
| images | id; plant_id | Capture time and reference |
| image_sources | image_id → images | Explicit image origin; additive compatibility table |
| actions | id; plant_id | Manual care type, note and server-recorded time |
| recommendations | id; event_id; unique(event_id,rule_id) | Existing ingestion check history |

New dashboard checks are computed read-time observations (not persisted notifications); their evidence includes the exact sample interval and endpoints or sensor IDs. Existing threshold recommendation history remains available at /api/recommendations, but is not the current-status source. Default thresholds remain null; no general agronomic thresholds were invented. Five-day check fires only for comparable non-increasing samples spanning at least 5 days in the last 6 days, with last sample within 24 hours. It asks for measurement-method/lighting/temperature/watering review, never prescribes treatment. Sparse endpoints are not evidence of a disease or a continuously flat trajectory.

## API additions

- `GET /api/plants/{plant_id}/state?days=14`: bounded chronological observations, separate devices and origins, checks, images and latest 100 actions. Unknown plant 404. Over 10,000 sensor samples per device/window returns 422; shorten period (no silent truncation).
- `POST /api/observations`: immutable manual/mock growth batch. Same replay/conflict contract as research import. Future timestamps rejected. See OpenAPI for units/fields.
- `POST /api/actions`: water/nutrients/lighting/pruning/pollination/relocation plus existing inspection/manual_care/note.
- `POST /api/images`: optional source enum; existing callers remain compatible.

30-second dashboard refresh. Latest environment value is the selected device's most recent observation within the selected window; stale label after 300 seconds by default. No observation in window is unavailable. Images and measurements are filtered by observation time; action history is latest 100 independently of period. Nulls and >2-day graph gaps are not connected. Model graphs are descriptive, not biological validation.

## PostgreSQL readiness and deployment limits

SQLite is the implemented development database, with transactions, foreign keys and a small connection boundary. PostgreSQL is **not yet implemented or tested**. Migration requires replacing sqlite3/positional placeholders, identity columns and PRAGMAs; introducing explicit migrations; moving JSON text to JSONB and timestamp strings to timestamptz; and rerunning replay/isolation/persistence tests. No claim of a working PostgreSQL switch is made.

The local single-user service binds to 127.0.0.1 only. Authentication, uploads, remote hosting, rate limits, device calibration and backup automation remain future work. No changes to tomato3d/config/data/records were made.
