"""Send deterministic mock values over HTTP; never writes directly to the DB."""
import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def post(base: str, path: str, payload: dict) -> dict:
    request = Request(base.rstrip("/") + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def register(base: str, path: str, payload: dict) -> None:
    try:
        post(base, path, payload)
    except HTTPError as error:
        if error.code != 409:
            raise
        with urlopen(base.rstrip("/") + path, timeout=10) as response:
            rows = json.load(response)
        if payload not in [{key: row[key] for key in payload} for row in rows]:
            raise ValueError("existing registration does not match mock device/plant") from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--interval", type=float, default=1)
    args = parser.parse_args()
    if args.count < 1 or args.interval < 0:
        parser.error("count must be positive and interval nonnegative")
    register(args.url, "/api/plants", {"id": "demo-plant", "name": "Demo tomato"})
    register(args.url, "/api/devices", {"id": "demo-device", "name": "Mock sensor", "plant_id": "demo-plant"})
    for index in range(args.count):
        event = {"schema_version": "1.0", "event_id": str(uuid.uuid4()), "device_id": "demo-device", "observed_at": datetime.now(timezone.utc).isoformat(), "source": "mock", "sensors": {"temperature_c": 24 + index % 10, "humidity_pct": 55, "water_level_pct": 10 if index % 4 == 0 else 65, "light_lux": 1200 + index * 10}}
        print(post(args.url, "/api/readings", event))
        if index + 1 < args.count:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
