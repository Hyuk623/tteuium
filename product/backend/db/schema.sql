PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS plants (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS devices (id TEXT PRIMARY KEY, name TEXT NOT NULL, plant_id TEXT NOT NULL REFERENCES plants(id));
CREATE TABLE IF NOT EXISTS sensor_readings (
 event_id TEXT PRIMARY KEY, device_id TEXT NOT NULL REFERENCES devices(id),
 observed_at TEXT NOT NULL, received_at TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sensor_history ON sensor_readings(device_id, observed_at DESC);
CREATE TABLE IF NOT EXISTS images (
 id INTEGER PRIMARY KEY, plant_id TEXT NOT NULL REFERENCES plants(id), captured_at TEXT NOT NULL, reference TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_imports (import_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plant_measurements (
 id INTEGER PRIMARY KEY, import_id TEXT NOT NULL REFERENCES research_imports(import_id),
 plant_id TEXT NOT NULL REFERENCES plants(id), observed_at TEXT NOT NULL,
 metric TEXT NOT NULL, value REAL, unit TEXT NOT NULL, status TEXT NOT NULL,
 UNIQUE(import_id, metric)
);
CREATE TABLE IF NOT EXISTS actions (
 id INTEGER PRIMARY KEY, plant_id TEXT NOT NULL REFERENCES plants(id),
 created_at TEXT NOT NULL, kind TEXT NOT NULL, note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendations (
 id INTEGER PRIMARY KEY, event_id TEXT NOT NULL REFERENCES sensor_readings(event_id),
 created_at TEXT NOT NULL, rule_id TEXT NOT NULL, message TEXT NOT NULL,
 UNIQUE(event_id, rule_id)
);
PRAGMA user_version=1;

CREATE TABLE IF NOT EXISTS image_sources (image_id INTEGER PRIMARY KEY REFERENCES images(id), source TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS simulation_results (
 id TEXT PRIMARY KEY, plant_id TEXT NOT NULL REFERENCES plants(id),
 title TEXT NOT NULL, run_id TEXT NOT NULL, scenario_id TEXT NOT NULL,
 generated_at TEXT NOT NULL, input_kind TEXT NOT NULL,
 source_name TEXT NOT NULL, sha256 TEXT NOT NULL, asset_name TEXT NOT NULL,
 media_kind TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(plant_id,run_id,scenario_id,sha256)
);
