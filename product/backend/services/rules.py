"""Human-inspection advice only; thresholds are explicitly configured."""
from datetime import datetime
from pydantic import Field
from product.backend.schemas import Model, Number, SensorEvent


class RuleConfig(Model):
    temperature_high_c: Number | None = None
    water_low_pct: Number | None = Field(default=None, ge=0, le=100)
    stale_after_seconds: int = Field(default=300, gt=0)
    future_tolerance_seconds: int = Field(default=60, ge=0)
    demo_only: bool = False


def evaluate(event: SensorEvent, config: RuleConfig, now: datetime) -> list[tuple[str, str]]:
    if (now - event.observed_at).total_seconds() > config.stale_after_seconds:
        return [("stale_reading", "Reading is stale. Check connectivity and device clock; do not act on old data.")]
    prefix = "DEMO ONLY: " if config.demo_only or event.source == "mock" else ""
    advice = []
    if all(v is None for v in event.sensors.model_dump().values()):
        advice.append(("missing_data", prefix + "No valid sensor values. Inspect the sensor connection."))
    if config.temperature_high_c is not None and event.sensors.temperature_c is not None and event.sensors.temperature_c > config.temperature_high_c:
        advice.append(("temperature_high", prefix + f"Temperature exceeds configured {config.temperature_high_c} C. Verify the sensor and inspect conditions manually."))
    if config.water_low_pct is not None and event.sensors.water_level_pct is not None and event.sensors.water_level_pct < config.water_low_pct:
        advice.append(("water_low", prefix + f"Water level is below configured {config.water_low_pct}%. Inspect reservoir and sensor manually."))
    return advice
