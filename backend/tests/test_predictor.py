import numpy as np
import pytest

from papertrials.config import get_settings
from papertrials.ml import predictor
from papertrials.ml.dataset import build_training_set, design_of, feature_row
from papertrials.ml.predictor import Band, BaselinePredictor, get_predictor
from tests.factories import make_experiment


def _four_experiments() -> list:
    return [
        make_experiment([10, 11, 12], wing_span_cm=16),
        make_experiment([12, 13, 14], wing_span_cm=18),
        make_experiment([14, 15, 16], wing_span_cm=20),
        make_experiment([15, 16, 17], wing_span_cm=22),
    ]


def test_training_set_has_one_row_per_flight() -> None:
    data = build_training_set(_four_experiments())
    assert data.n_rows == 12
    assert data.n_experiments == 4
    assert data.X.shape[0] == 12


def test_unrecorded_fields_become_nan() -> None:
    row = feature_row({"wing_span_cm": 18, "nose_angle_deg": None}, wind=None)
    assert np.isnan(row).sum() >= 2


def test_baseline_predicts_near_the_closest_flown_plane() -> None:
    exps = _four_experiments()
    model = BaselinePredictor(build_training_set(exps))
    band = model.predict(np.array([feature_row(design_of(exps[1]), 0)]))[0]
    assert 12 <= band.median <= 15
    assert band.low < band.median < band.high


def test_baseline_range_grows_for_unfamiliar_planes() -> None:
    exps = _four_experiments()
    model = BaselinePredictor(build_training_set(exps))
    near = model.predict(np.array([feature_row(design_of(exps[0]), 0)]))[0]
    far = model.predict(np.array([feature_row({**design_of(exps[0]), "nose_angle_deg": 70, "added_clips": 3}, 0)]))[0]
    assert far.width > near.width


def test_no_flights_means_no_predictor() -> None:
    assert get_predictor(build_training_set([])) is None


def test_baseline_is_used_before_enough_data() -> None:
    model = get_predictor(build_training_set(_four_experiments()[:2]))
    assert model is not None and model.name == "baseline"


def test_tabpfn_is_used_once_there_is_enough_data(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeTabPFN:
        name = "tabpfn"

        def __init__(self, data: object) -> None: ...

        def predict(self, X: np.ndarray) -> list[Band]:
            return [Band(1, 2, 3) for _ in X]

    monkeypatch.setattr(get_settings(), "use_tabpfn", True)
    monkeypatch.setattr(predictor, "TabPFNPredictor", FakeTabPFN)
    model = get_predictor(build_training_set(_four_experiments()))
    assert model is not None and model.name == "tabpfn"


def test_falls_back_to_baseline_and_reports_why_when_tabpfn_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(data: object) -> None:
        raise RuntimeError("license not accepted\nmore detail")

    monkeypatch.setattr(get_settings(), "use_tabpfn", True)
    monkeypatch.setattr(predictor, "TabPFNPredictor", broken)
    model = get_predictor(build_training_set(_four_experiments()))
    assert model is not None and model.name == "baseline"
    assert predictor.status.tabpfn_error == "license not accepted"


@pytest.mark.parametrize(("band", "label"), [(Band(9, 10, 11), "high"), (Band(8, 10, 13), "medium"), (Band(2, 10, 20), "low")])
def test_confidence_label_follows_range_width(band: Band, label: str) -> None:
    assert band.confidence == label


@pytest.mark.slow
def test_real_tabpfn_returns_ordered_quantiles() -> None:
    data = build_training_set(_four_experiments())
    bands = predictor.TabPFNPredictor(data).predict(data.X[:2])
    assert all(b.low <= b.median <= b.high for b in bands)
