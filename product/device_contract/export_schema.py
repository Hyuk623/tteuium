"""Export the API model as the single-source device JSON Schema."""
import json
from pathlib import Path
from product.backend.schemas import SensorEvent


if __name__ == "__main__":
    schema = SensorEvent.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    Path(__file__).with_name("sensor-event.schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
