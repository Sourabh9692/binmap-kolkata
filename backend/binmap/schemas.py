from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Timed(StrictModel):
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def valid_time(cls, value):
        if value.tzinfo is None:
            raise ValueError("An explicit time zone is required")
        if value > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Observation cannot be in the future")
        return value


class SessionIn(StrictModel):
    id: UUID
    surveyor: str = Field(min_length=2, max_length=60)
    started_at: datetime
    consent: Literal[True]

    @field_validator("started_at")
    @classmethod
    def valid_time(cls, value):
        return Timed.valid_time(value)


class InspectionIn(Timed):
    id: UUID
    session_id: UUID
    segment_id: str = Field(min_length=1, max_length=80)
    sides: Literal["both", "left", "right", "neither"]
    visibility: Literal["clear", "partial", "obstructed"]
    coverage: float = Field(ge=0, le=1)
    result: Literal["no_bin_observed", "bins_observed", "unable_to_inspect"]
    notes: str = Field(default="", max_length=2000)


class ObservationIn(Timed):
    id: UUID
    session_id: UUID
    segment_id: str = Field(min_length=1, max_length=80)
    latitude: float = Field(ge=22, le=23)
    longitude: float = Field(ge=88, le=89)
    accuracy_m: float = Field(gt=0, le=1000)
    category: Literal[
        "public_litter_bin", "community_container", "recycling", "private_bin"
    ]
    condition: Literal["usable", "overflowing", "damaged", "blocked", "missing"]
    public_access: bool
    evidence_id: UUID
    notes: str = Field(default="", max_length=2000)


class ReviewIn(StrictModel):
    target_type: Literal["observation", "inspection"]
    target_id: UUID
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=5, max_length=2000)
