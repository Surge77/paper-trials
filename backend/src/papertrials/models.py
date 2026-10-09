from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DesignBase(SQLModel):
    """One plane plus how it was thrown. Mirrors the design and launch entries in fields.py."""

    fold_style: float | None = None
    wing_span_cm: float | None = None
    body_length_cm: float | None = None
    nose_angle_deg: float | None = None
    winglet_mm: float | None = None
    elevator_bend: float | None = None
    added_clips: float | None = None
    paper_gsm: float | None = None
    launch_angle: float | None = None
    launch_force: float | None = None


class Experiment(DesignBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    number: int = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    status: str = "planned"  # planned -> flown
    is_demo: bool = False

    # Which experiment this one was derived from, and the single thing that changed.
    parent_id: int | None = Field(default=None, foreign_key="experiment.id")
    changed_field: str | None = None
    changed_from: float | None = None
    changed_to: float | None = None

    # Prediction saved when the experiment is planned, before any flight.
    # Kept untouched afterwards so prediction-vs-actual is an honest comparison.
    pred_low: float | None = None
    pred_median: float | None = None
    pred_high: float | None = None
    pred_model: str | None = None
    pred_rows: int | None = None

    hypothesis: str | None = None
    lab_note: str | None = None
    photo_check: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    flights: list["Flight"] = Relationship(
        back_populates="experiment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Flight(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    distance_m: float
    time_s: float | None = None
    stability: int | None = None  # 1 (wobbly) to 5 (rock steady)
    wind: float | None = None
    note: str | None = None
    issues: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    issues_source: str | None = None  # "gemma" or "keywords"

    experiment: Experiment | None = Relationship(back_populates="flights")
