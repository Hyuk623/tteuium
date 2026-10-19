"""Import one plant/scenario/variant from the real plant_light.csv contract."""
import argparse
import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from product.backend.schemas import Measurement, ResearchImport

MAPPING = {
    "leaf_area_mm2": ("leaf_area", "mm2"),
    "intercepted_full_output_umol_s": ("intercepted_full_output", "umol/s"),
    "absorbed_full_output_umol_s": ("absorbed_full_output", "umol/s"),
    "intercepted_mol_day": ("intercepted_daily", "mol/day"),
    "absorbed_mol_day": ("absorbed_daily", "mol/day"),
    "leaf_ppfd_cv": ("leaf_ppfd_cv", "1"),
}


def adapt(path: Path, *, plant_id: str, scenario_id: str, geometry_variant_id: str,
          observed_at: datetime, evidence: str, import_id: str) -> ResearchImport:
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    required = {"plant_id", "scenario_id", "geometry_variant_id", *MAPPING}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("plant_light.csv missing required columns")
    rows = [r for r in reader if (r["plant_id"], r["scenario_id"], r["geometry_variant_id"]) == (plant_id, scenario_id, geometry_variant_id)]
    if len(rows) != 1:
        raise ValueError("expected exactly one plant/scenario/variant row")
    measurements = []
    for column, (metric, unit) in MAPPING.items():
        value = rows[0][column]
        missing = value == "unavailable"
        measurements.append(Measurement(metric=metric, unit=unit, value=None if missing else float(value), status="unavailable" if missing else "model_estimated"))
    # Neither plant height nor projected canopy footprint is exported by plant_light.csv.
    for metric, unit in (("plant_height", "mm"), ("canopy_area", "mm2")):
        measurements.append(Measurement(metric=metric, unit=unit, value=None, status="unavailable"))
    return ResearchImport(import_id=import_id, plant_id=plant_id, observed_at=observed_at,
        source_ref=path.name, source_sha256=hashlib.sha256(raw).hexdigest(), scenario_id=scenario_id,
        geometry_variant_id=geometry_variant_id, evidence=evidence, measurements=measurements)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    for name in ("plant-id", "scenario-id", "geometry-variant-id", "observed-at", "import-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--evidence", choices=["research_model", "synthetic_fixture"], required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    result = adapt(args.csv, plant_id=args.plant_id, scenario_id=args.scenario_id,
        geometry_variant_id=args.geometry_variant_id, observed_at=datetime.fromisoformat(args.observed_at),
        evidence=args.evidence, import_id=args.import_id)
    request = Request(args.url.rstrip("/") + "/api/research/import", data=result.model_dump_json().encode(), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        print(response.read().decode())


if __name__ == "__main__":
    main()
