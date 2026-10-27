"""Atomic, replay-safe ingestion. No background work or research imports."""
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException
from product.backend.db import connect
from product.backend.schemas import SensorEvent, ResearchImport, ObservationBatch
from product.backend.services.rules import RuleConfig, evaluate


def canonical(model: SensorEvent | ResearchImport | ObservationBatch) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def ingest(path: Path, event: SensorEvent, rules: RuleConfig) -> dict:
    now = datetime.now(timezone.utc)
    if (event.observed_at - now).total_seconds() > rules.future_tolerance_seconds:
        raise HTTPException(422, "observation timestamp is too far in the future")
    payload = canonical(event)
    with connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT payload FROM sensor_readings WHERE event_id=?", (event.event_id,)).fetchone()
        if old:
            if old["payload"] != payload:
                raise HTTPException(409, "event_id already used with different data")
            return {"event_id": event.event_id, "duplicate": True}
        if not db.execute("SELECT 1 FROM devices WHERE id=?", (event.device_id,)).fetchone():
            raise HTTPException(404, "register device and plant first")
        db.execute("INSERT INTO sensor_readings VALUES(?,?,?,?,?)", (event.event_id, event.device_id, event.observed_at.isoformat(), now.isoformat(), payload))
        for rule_id, message in evaluate(event, rules, now):
            db.execute("INSERT INTO recommendations(event_id,created_at,rule_id,message) VALUES(?,?,?,?)", (event.event_id, now.isoformat(), rule_id, message))
    return {"event_id": event.event_id, "duplicate": False}


def import_research(path: Path, result: ResearchImport | ObservationBatch) -> dict:
    payload = canonical(result)
    with connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT payload FROM research_imports WHERE import_id=?", (result.import_id,)).fetchone()
        if old:
            if old["payload"] != payload:
                raise HTTPException(409, "import_id already used with different data")
            return {"import_id": result.import_id, "duplicate": True}
        if not db.execute("SELECT 1 FROM plants WHERE id=?", (result.plant_id,)).fetchone():
            raise HTTPException(404, "unknown plant")
        db.execute("INSERT INTO research_imports VALUES(?,?)", (result.import_id, payload))
        for item in result.measurements:
            db.execute("INSERT INTO plant_measurements(import_id,plant_id,observed_at,metric,value,unit,status) VALUES(?,?,?,?,?,?,?)", (result.import_id, result.plant_id, result.observed_at.astimezone(timezone.utc).isoformat(), item.metric, item.value, item.unit, item.status))
    return {"import_id": result.import_id, "duplicate": False}
