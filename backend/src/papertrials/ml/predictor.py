"""Distance predictions with an honest range.

Two models share one interface:

* BaselinePredictor: used for the first few experiments. It looks at the most
  similar planes you've already flown and widens the range when the new plane
  is far from anything tested. It's a rough guess and the UI says so.
* TabPFNPredictor: once there are enough flights, TabPFN (a pretrained
  tabular foundation model) learns from every flight in one forward pass and
  returns the 10th, 50th and 90th percentile of the distance it expects.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from papertrials.config import get_settings
from papertrials.fields import CATEGORICAL_INDICES, FIELDS
from papertrials.ml.dataset import TrainingSet

log = logging.getLogger(__name__)

MIN_EXPERIMENTS_FOR_TABPFN = 4
MIN_FLIGHTS_FOR_TABPFN = 8
QUANTILES = [0.1, 0.5, 0.9]


@dataclass(frozen=True)
class Band:
    low: float
    median: float
    high: float

    @property
    def width(self) -> float:
        return self.high - self.low

    @property
    def confidence(self) -> str:
        """Plain-language label from how wide the range is compared to the middle."""
        relative = self.width / max(self.median, 0.5)
        if relative < 0.35:
            return "high"
        if relative < 0.75:
            return "medium"
        return "low"


class Predictor(Protocol):
    name: str

    def predict(self, X: np.ndarray) -> list[Band]: ...


def _feature_ranges() -> np.ndarray:
    spans = []
    for f in FIELDS:
        lo, hi = (min(f.choices), max(f.choices)) if f.choices else (f.lo, f.hi)
        spans.append(max(hi - lo, 1e-6))
    return np.array(spans)


class BaselinePredictor:
    """Nearest-neighbour guess over the experiments you've already flown."""

    name = "baseline"

    def __init__(self, data: TrainingSet) -> None:
        self._groups: list[tuple[np.ndarray, np.ndarray]] = []
        for exp_id in dict.fromkeys(data.experiment_ids):
            mask = np.array([i == exp_id for i in data.experiment_ids])
            design = np.nanmean(data.X[mask], axis=0) if mask.sum() > 1 else data.X[mask][0]
            self._groups.append((design, data.y[mask]))
        self._spread = float(np.std(data.y)) if data.n_rows > 1 else 2.0
        self._ranges = _feature_ranges()

    def _distance(self, a: np.ndarray, b: np.ndarray) -> float:
        both = ~(np.isnan(a) | np.isnan(b))
        if not both.any():
            return 1.0
        diff = (a[both] - b[both]) / self._ranges[both]
        return float(np.sqrt(np.mean(diff**2)))

    def predict(self, X: np.ndarray) -> list[Band]:
        if not self._groups:
            raise ValueError("No flights yet, nothing to predict from.")
        return [self._predict_one(row) for row in X]

    def _predict_one(self, row: np.ndarray) -> Band:
        scored = sorted(((self._distance(row, d), y) for d, y in self._groups), key=lambda t: t[0])
        nearest = scored[:2]
        weights = np.array([1.0 / (dist + 0.05) for dist, _ in nearest])
        medians = np.array([float(np.median(y)) for _, y in nearest])
        median = float(np.average(medians, weights=weights))
        # Wider range the further the plane is from anything flown.
        half = self._spread * 1.3 + median * 0.6 * nearest[0][0]
        return Band(low=max(median - half, 0.0), median=median, high=median + half)


class TabPFNPredictor:
    name = "tabpfn"

    def __init__(self, data: TrainingSet) -> None:
        from tabpfn import TabPFNRegressor

        self._model = TabPFNRegressor(
            n_estimators=4,
            categorical_features_indices=list(CATEGORICAL_INDICES),
            random_state=0,
        )
        self._model.fit(data.X, data.y)

    def predict(self, X: np.ndarray) -> list[Band]:
        low, median, high = self._model.predict(X, output_type="quantiles", quantiles=QUANTILES)
        return [
            Band(low=max(float(lo), 0.0), median=float(md), high=float(hi))
            for lo, md, hi in zip(low, median, high, strict=True)
        ]


@dataclass
class ModelStatus:
    tabpfn_error: str | None = None


status = ModelStatus()
_cache: dict[str, Predictor] = {}
# Datasets TabPFN already failed on, so a missing licence doesn't retry on every request.
_failed: set[str] = set()


def _signature(data: TrainingSet, kind: str) -> str:
    digest = hashlib.sha256(np.nan_to_num(data.X, nan=-999).tobytes() + data.y.tobytes())
    return f"{kind}:{digest.hexdigest()}"


def has_enough_for_tabpfn(data: TrainingSet) -> bool:
    return data.n_experiments >= MIN_EXPERIMENTS_FOR_TABPFN and data.n_rows >= MIN_FLIGHTS_FOR_TABPFN


def get_predictor(data: TrainingSet) -> Predictor | None:
    """Pick the right model for how much data there is. None means no flights yet."""
    if data.n_rows == 0:
        return None
    if has_enough_for_tabpfn(data) and get_settings().use_tabpfn:
        key = _signature(data, "tabpfn")
        if key in _cache:
            return _cache[key]
        if key not in _failed:
            try:
                model = TabPFNPredictor(data)
            except Exception as exc:  # weights missing, license not accepted, out of memory...
                log.warning("TabPFN unavailable, using baseline: %s", exc)
                status.tabpfn_error = str(exc).strip().splitlines()[0][:300]
                _failed.add(key)
            else:
                _cache.clear()
                _cache[key] = model
                status.tabpfn_error = None
                return model
    return BaselinePredictor(data)
