"""Run from repository root: python -m product.backend.api."""
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from product.backend.db import connect, initialize
from product.backend.schemas import Plant, Device, SensorEvent, Action, Image, ResearchImport, ObservationBatch
from product.backend.services.ingestion import ingest, import_research
from product.backend.services.rules import RuleConfig
from product.backend.services.dashboard import dashboard_state
from product.backend.simulations import list_results

ROOT = Path(__file__).resolve().parents[1]


def create_app(db_path: Path, rules: RuleConfig | None = None) -> FastAPI:
    initialize(db_path)
    rules = rules or RuleConfig()
    app = FastAPI(title="Tomato Product MVP", version="0.1.0")

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse(status_code=409, content={"detail": "duplicate identifier or unknown related plant/device"})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": "local-single-user", "rules": rules.model_dump()}

    @app.post("/api/plants", status_code=201)
    def add_plant(plant: Plant):
        with connect(db_path) as db:
            db.execute("INSERT INTO plants VALUES(?,?)", (plant.id, plant.name))
        return plant

    @app.get("/api/plants")
    def plants():
        with connect(db_path) as db:
            return [dict(r) for r in db.execute("SELECT * FROM plants ORDER BY id")]

    @app.post("/api/devices", status_code=201)
    def add_device(device: Device):
        with connect(db_path) as db:
            db.execute("INSERT INTO devices VALUES(?,?,?)", (device.id, device.name, device.plant_id))
        return device

    @app.get("/api/devices")
    def devices():
        now = datetime.now(timezone.utc)
        with connect(db_path) as db:
            result = []
            for row in db.execute("SELECT * FROM devices ORDER BY id"):
                item = dict(row)
                latest = db.execute("SELECT payload FROM sensor_readings WHERE device_id=? ORDER BY observed_at DESC,received_at DESC LIMIT 1", (item["id"],)).fetchone()
                item["latest"] = json.loads(latest["payload"]) if latest else None
                item["status"] = "never_seen" if latest is None else ("stale" if (now - datetime.fromisoformat(item["latest"]["observed_at"])).total_seconds() > rules.stale_after_seconds else "online")
                result.append(item)
            return result

    @app.post("/api/readings", status_code=201)
    def readings_write(event: SensorEvent):
        return ingest(db_path, event, rules)

    @app.get("/api/readings")
    def readings(device_id: str, limit: int = Query(100, ge=1, le=1000)):
        with connect(db_path) as db:
            return [json.loads(r["payload"]) for r in db.execute("SELECT payload FROM sensor_readings WHERE device_id=? ORDER BY observed_at DESC,received_at DESC LIMIT ?", (device_id, limit))]

    @app.get("/api/recommendations")
    def recommendations(plant_id: str, limit: int = Query(100, ge=1, le=1000)):
        with connect(db_path) as db:
            return [dict(r) for r in db.execute("SELECT r.*,s.device_id,s.observed_at FROM recommendations r JOIN sensor_readings s USING(event_id) JOIN devices d ON d.id=s.device_id WHERE d.plant_id=? ORDER BY r.id DESC LIMIT ?", (plant_id, limit))]

    @app.post("/api/actions", status_code=201)
    def add_action(action: Action):
        with connect(db_path) as db:
            cursor = db.execute("INSERT INTO actions(plant_id,created_at,kind,note) VALUES(?,?,?,?)", (action.plant_id, datetime.now(timezone.utc).isoformat(), action.kind, action.note))
            return {"id": cursor.lastrowid, **action.model_dump()}

    @app.get("/api/actions")
    def actions(plant_id: str, limit: int = Query(100, ge=1, le=1000)):
        with connect(db_path) as db:
            return [dict(r) for r in db.execute("SELECT * FROM actions WHERE plant_id=? ORDER BY id DESC LIMIT ?", (plant_id, limit))]

    @app.post("/api/images", status_code=201)
    def add_image(image: Image):
        with connect(db_path) as db:
            cursor = db.execute("INSERT INTO images(plant_id,captured_at,reference) VALUES(?,?,?)", (image.plant_id, image.captured_at.astimezone(timezone.utc).isoformat(), image.reference))
            db.execute("INSERT INTO image_sources VALUES(?,?)", (cursor.lastrowid, image.source))
            return {"id": cursor.lastrowid}

    @app.get("/api/images")
    def images(plant_id: str, limit: int = Query(100, ge=1, le=1000)):
        with connect(db_path) as db:
            return [dict(r) for r in db.execute("SELECT * FROM images WHERE plant_id=? ORDER BY captured_at DESC LIMIT ?", (plant_id, limit))]

    @app.post("/api/research/import", status_code=201)
    def research(result: ResearchImport):
        return import_research(db_path, result)

    @app.get("/api/measurements")
    def measurements(plant_id: str, limit: int = Query(100, ge=1, le=1000)):
        with connect(db_path) as db:
            result = []
            for row in db.execute("SELECT m.*,r.payload FROM plant_measurements m JOIN research_imports r USING(import_id) WHERE plant_id=? ORDER BY observed_at DESC,m.id DESC LIMIT ?", (plant_id, limit)):
                item = dict(row)
                provenance = json.loads(item.pop("payload"))
                item["provenance"] = {k: v for k, v in provenance.items() if k != "measurements"}
                result.append(item)
            return result

    @app.post("/api/observations", status_code=201)
    def observations(result: ObservationBatch):
        if result.observed_at > datetime.now(timezone.utc):
            raise HTTPException(422, "future observation")
        return import_research(db_path, result)

    @app.get("/api/plants/{plant_id}/state")
    def state(plant_id: str, days: int = Query(14, ge=1, le=30)):
        return dashboard_state(db_path, plant_id, days, rules.stale_after_seconds)

    @app.get("/api/simulations")
    def simulations(plant_id: str):
        with connect(db_path) as db:
            if not db.execute("SELECT 1 FROM plants WHERE id=?", (plant_id,)).fetchone():
                raise HTTPException(404, "unknown plant")
        return list_results(db_path, plant_id)

    @app.get("/api/simulations/{result_id}/asset")
    def simulation_asset(result_id: str):
        with connect(db_path) as db:
            row = db.execute("SELECT * FROM simulation_results WHERE id=?", (result_id,)).fetchone()
        if not row:
            raise HTTPException(404, "unknown simulation")
        directory = (db_path.parent / "simulation-assets").resolve()
        asset = (directory / row["asset_name"]).resolve()
        if asset.parent != directory or not asset.is_file():
            raise HTTPException(404, "simulation asset unavailable")
        headers = {"X-Content-Type-Options": "nosniff"}
        if row["media_kind"] == "viewer":
            headers["Content-Security-Policy"] = "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; form-action 'none'"
        return FileResponse(asset, headers=headers)

    app.mount("/static", StaticFiles(directory=ROOT / "frontend" / "dashboard"), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(ROOT / "frontend" / "dashboard" / "index.html")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT.parent / "build" / "product" / "product.sqlite3")
    parser.add_argument("--rules", type=Path, default=ROOT / "rules.json")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    rules = RuleConfig.model_validate_json(args.rules.read_text(encoding="utf-8"))
    import uvicorn
    uvicorn.run(create_app(args.db, rules), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
