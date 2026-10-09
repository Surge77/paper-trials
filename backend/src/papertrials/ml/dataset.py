"""Turns the experiment log into a table the models can learn from.

One row per flight. Each row carries the plane's design, how it was thrown,
and the wind for that flight. The target is the distance flown. Fields that
weren't recorded become NaN; TabPFN handles missing values natively.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from papertrials.fields import FEATURE_NAMES
from papertrials.models import Experiment

Design = Mapping[str, float | None]


@dataclass(frozen=True)
class TrainingSet:
    X: np.ndarray
    y: np.ndarray
    experiment_ids: tuple[int, ...]

    @property
    def n_rows(self) -> int:
        return len(self.y)

    @property
    def n_experiments(self) -> int:
        return len(set(self.experiment_ids))


def feature_row(design: Design, wind: float | None = None) -> list[float]:
    values: dict[str, float | None] = {**design, "wind": wind}
    row: list[float] = []
    for name in FEATURE_NAMES:
        value = values.get(name)
        row.append(np.nan if value is None else float(value))
    return row


def design_of(experiment: Experiment) -> dict[str, float | None]:
    return {name: getattr(experiment, name) for name in FEATURE_NAMES if name != "wind"}


def build_training_set(experiments: Sequence[Experiment]) -> TrainingSet:
    rows: list[list[float]] = []
    targets: list[float] = []
    ids: list[int] = []
    for exp in experiments:
        if exp.id is None:
            continue
        design = design_of(exp)
        for flight in exp.flights:
            rows.append(feature_row(design, flight.wind))
            targets.append(flight.distance_m)
            ids.append(exp.id)
    X = np.array(rows, dtype=float).reshape(len(rows), len(FEATURE_NAMES))
    return TrainingSet(X=X, y=np.array(targets, dtype=float), experiment_ids=tuple(ids))
