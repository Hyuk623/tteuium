"""Versioned product boundary models; units are part of field names."""
from datetime import date, datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,96}$")]
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Plant(Model):
    id: Identifier
    name: str = Field(min_length=1, max_length=120)


class Device(Plant):
    plant_id: Identifier


class Sensors(Model):
    temperature_c: Annotated[Number, Field(ge=-273.15)] | None = None
    humidity_pct: Annotated[Number, Field(ge=0, le=100)] | None = None
    water_level_pct: Annotated[Number, Field(ge=0, le=100)] | None = None
    light_lux: Annotated[Number, Field(ge=0)] | None = None


class SensorEvent(Model):
    schema_version: Literal["1.0"]
    event_id: Identifier
    device_id: Identifier
    observed_at: AwareDatetime
    sensors: Sensors
    source: Literal["device", "mock"] = "device"

    @field_validator("observed_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class Action(Model):
    plant_id: Identifier
    action_date: date | None = None
    note: str = Field(min_length=1, max_length=2000)
    kind: Literal["inspection", "manual_care", "note", "water", "nutrients", "lighting", "pruning", "pollination", "relocation"] = "note"


class Image(Model):
    source: Literal["human", "device", "mock", "unknown"] = "unknown"
    plant_id: Identifier
    captured_at: AwareDatetime
    reference: str = Field(min_length=1, max_length=1000)


class Measurement(Model):
    metric: Literal["leaf_area", "plant_height", "canopy_area", "intercepted_full_output", "absorbed_full_output", "intercepted_daily", "absorbed_daily", "leaf_ppfd_cv"]
    value: Annotated[Number, Field(ge=0)] | None
    unit: str
    status: Literal["measured", "human", "derived", "model", "model_estimated", "unavailable"]

    @model_validator(mode="after")
    def semantics(self) -> "Measurement":
        units = {"leaf_area": "mm2", "plant_height": "mm", "canopy_area": "mm2", "intercepted_full_output": "umol/s", "absorbed_full_output": "umol/s", "intercepted_daily": "mol/day", "absorbed_daily": "mol/day", "leaf_ppfd_cv": "1"}
        if self.unit != units[self.metric]:
            raise ValueError("metric unit mismatch")
        if (self.value is None) != (self.status == "unavailable"):
            raise ValueError("null values must have unavailable status and vice versa")
        return self


class ResearchImport(Model):
    import_id: Identifier
    plant_id: Identifier
    observed_at: AwareDatetime
    source_ref: str = Field(min_length=1, max_length=1000)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scenario_id: str = Field(min_length=1, max_length=96)
    geometry_variant_id: str = Field(min_length=1, max_length=96)
    evidence: Literal["research_model", "synthetic_fixture"]
    measurements: list[Measurement] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_metrics(self) -> "ResearchImport":
        if len({m.metric for m in self.measurements}) != len(self.measurements):
            raise ValueError("duplicate metric")
        if any(m.status not in ("model", "model_estimated", "unavailable") for m in self.measurements):
            raise ValueError("research light exports are model estimates, not sensor measurements")
        return self


class ObservationBatch(Model):
    """Manual or mock growth observations; never accepted as research output."""
    import_id: Identifier
    plant_id: Identifier
    observed_at: AwareDatetime
    source_ref: str = Field(min_length=1, max_length=1000)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scenario_id: Literal["observation"] = "observation"
    geometry_variant_id: Literal["manual", "demo"]
    evidence: Literal["human", "mock"]
    measurements: list[Measurement] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def observations_only(self) -> "ObservationBatch":
        if len({m.metric for m in self.measurements}) != len(self.measurements):
            raise ValueError("duplicate metric")
        if (self.evidence == "mock") != (self.geometry_variant_id == "demo"):
            raise ValueError("evidence and series must agree")
        for item in self.measurements:
            if item.metric not in ("plant_height", "leaf_area", "canopy_area"):
                raise ValueError("growth metrics only")
            expected = "model" if self.evidence == "mock" else "human"
            if item.status not in (expected, "unavailable"):
                raise ValueError("observation provenance mismatch")
        return self
