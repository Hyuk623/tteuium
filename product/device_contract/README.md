# Device contract v1

Transport: `POST /api/readings`, `Content-Type: application/json`. Register the plant and device
through `/api/plants` and `/api/devices` first. The machine-readable contract is
`sensor-event.schema.json`, generated from `backend/schemas.py::SensorEvent`.

```json
{
  "schema_version": "1.0",
  "event_id": "device-01:boot-03:sample-42",
  "device_id": "device-01",
  "observed_at": "2026-10-14T09:00:00+09:00",
  "source": "device",
  "sensors": {
    "temperature_c": 25.3,
    "humidity_pct": 61.2,
    "water_level_pct": null,
    "light_lux": 1200
  }
}
```

Use a globally unique event ID and retain the same ID, timestamp and data on retry. HTTP 201
returns `duplicate: false` for new data and `duplicate: true` for exact normalized replay.
HTTP 409 indicates conflicting ID reuse; 404 unknown device; 422 invalid payload/timestamp.
Never retry a conflict with changed data under the same ID. Use bounded backoff for connection failures.

Timezone is mandatory, stored in UTC. Observation and server receipt times are separate. Default
future tolerance is 60 seconds; older events remain history and produce only stale-data advice
after 300 seconds. Latest state uses observation time, so delayed packets cannot replace newer data.
These timings are operational defaults pending hardware cadence, not crop thresholds.

Fields may be omitted or null when unavailable. Zero is a real value. An all-null event is stored
and produces a missing-data inspection recommendation. Extra fields, numeric strings, non-finite
numbers and values outside declared physical bounds are rejected. Humidity/water percentage are
0..100; lux >=0; temperature >=-273.15 C. These are contract bounds, not calibrated sensor ranges.
Lux does not mean PPFD. Add a versioned field/contract when the actual device exposes another unit.

No device secrets, auto-enrollment, firmware, MQTT bridge or actuator commands are supplied.
`mock_sensor.py` registers a labelled mock device and sends real HTTP requests; it never edits SQLite.
