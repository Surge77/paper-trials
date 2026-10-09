from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from papertrials.fields import FIELDS_BY_NAME
from papertrials.models import DesignBase

MAX_DISTANCE_M = 100.0
MAX_TIME_S = 60.0
MAX_NOTE_CHARS = 500
MAX_FLIGHTS_PER_SUBMIT = 10


class DesignIn(DesignBase):
    @model_validator(mode="after")
    def check_ranges(self) -> "DesignIn":
        errors = []
        for name, value in self.model_dump().items():
            spec = FIELDS_BY_NAME.get(name)
            if spec is None or value is None:
                continue
            if spec.choices and value not in spec.choices:
                errors.append(f"{name} must be one of {list(spec.choices)}")
            elif not spec.choices and not spec.lo <= value <= spec.hi:
                errors.append(f"{name} must be between {spec.lo:g} and {spec.hi:g}")
        if errors:
            raise ValueError("; ".join(errors))
        return self


class ExperimentCreate(DesignIn):
    parent_id: int | None = None
    changed_field: str | None = None

    @model_validator(mode="after")
    def check_changed_field(self) -> "ExperimentCreate":
        if self.changed_field is not None and self.changed_field not in FIELDS_BY_NAME:
            raise ValueError(f"unknown field {self.changed_field}")
        if self.changed_field is not None and self.parent_id is None:
            raise ValueError("changed_field needs a parent_id")
        return self


class FlightIn(BaseModel):
    distance_m: float = Field(gt=0, le=MAX_DISTANCE_M)
    time_s: float | None = Field(default=None, gt=0, le=MAX_TIME_S)
    stability: int | None = Field(default=None, ge=1, le=5)
    wind: float | None = None
    note: str | None = Field(default=None, max_length=MAX_NOTE_CHARS)

    @model_validator(mode="after")
    def check_wind(self) -> "FlightIn":
        if self.wind is not None and self.wind not in FIELDS_BY_NAME["wind"].choices:
            raise ValueError("wind must be 0 (calm), 1 (light) or 2 (breezy)")
        return self


class FlightsIn(BaseModel):
    flights: list[FlightIn] = Field(min_length=1, max_length=MAX_FLIGHTS_PER_SUBMIT)


class FlightOut(BaseModel):
    id: int
    distance_m: float
    time_s: float | None
    stability: int | None
    wind: float | None
    note: str | None
    issues: list[str]
    issues_source: str | None


class BandOut(BaseModel):
    low: float
    median: float
    high: float
    confidence: str


class ExperimentOut(DesignBase):
    id: int
    number: int
    created_at: datetime
    status: str
    is_demo: bool
    parent_id: int | None
    changed_field: str | None
    changed_from: float | None
    changed_to: float | None
    prediction: BandOut | None
    pred_model: str | None
    pred_rows: int | None
    hypothesis: str | None
    lab_note: str | None
    photo_check: dict[str, Any] | None
    flights: list[FlightOut]
    median_m: float | None
    best_m: float | None
    median_time_s: float | None
    inside_prediction: bool | None


class CandidateOut(BaseModel):
    design: dict[str, float | None]
    changed_field: str | None
    changed_from: float | None
    changed_to: float | None
    prediction: BandOut | None
    score: float | None
    reason: str
    fixes_issue: str | None


class RecommendationOut(BaseModel):
    mode: str
    model: str | None
    base_experiment_id: int | None
    best_median: float | None
    recurring_issues: list[str]
    candidates: list[CandidateOut]


class StatusOut(BaseModel):
    gemma_available: bool
    gemma_model: str
    tabpfn_enabled: bool
    tabpfn_error: str | None
    model_in_use: str | None
    flown_experiments: int
    flights: int
    flights_needed_for_tabpfn: int
    experiments_needed_for_tabpfn: int
    has_demo_data: bool
