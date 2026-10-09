"""The experiment lifecycle: plan -> predict (frozen) -> fly -> log -> lab note."""

import statistics
from collections.abc import Sequence
from typing import Any

import numpy as np
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, func, select

from papertrials import gemma
from papertrials.fields import FIELDS_BY_NAME
from papertrials.ml.dataset import build_training_set, design_of, feature_row
from papertrials.ml.predictor import Band, get_predictor
from papertrials.ml.recommender import Candidate, Recommendation, median_distance
from papertrials.models import Experiment, Flight
from papertrials.schemas import (
    BandOut,
    CandidateOut,
    ExperimentCreate,
    ExperimentOut,
    FlightIn,
    FlightOut,
    RecommendationOut,
)

CALM = 0.0


def list_experiments(session: Session) -> list[Experiment]:
    query = select(Experiment).options(selectinload(Experiment.flights)).order_by(col(Experiment.number))  # type: ignore[arg-type]
    return list(session.exec(query).all())


def flown_only(experiments: Sequence[Experiment]) -> list[Experiment]:
    return [e for e in experiments if e.status == "flown" and e.flights]


def predict_design(experiments: Sequence[Experiment], design: dict[str, float | None]) -> tuple[Band | None, str | None, int]:
    data = build_training_set(flown_only(experiments))
    predictor = get_predictor(data)
    if predictor is None:
        return None, None, 0
    band = predictor.predict(np.array([feature_row(design, CALM)]))[0]
    return band, predictor.name, data.n_rows


def _hypothesis(exp: Experiment, parent: Experiment | None, band: Band | None) -> str | None:
    if band is None:
        return None
    expected = f"about {band.median:.1f} m (likely {band.low:.1f}–{band.high:.1f} m)"
    if parent is None or exp.changed_field is None or not parent.flights:
        return f"Expected distance: {expected}."
    spec = FIELDS_BY_NAME[exp.changed_field]
    return (
        f"Changing {spec.label.lower()} from {spec.format(exp.changed_from)} to {spec.format(exp.changed_to)} "
        f"should move the median distance from {median_distance(parent):.1f} m to {expected}."
    )


def create_experiment(session: Session, payload: ExperimentCreate) -> Experiment:
    experiments = list_experiments(session)
    parent = session.get(Experiment, payload.parent_id) if payload.parent_id is not None else None
    if payload.parent_id is not None and parent is None:
        raise LookupError(f"experiment {payload.parent_id} not found")

    number = (session.exec(select(func.max(Experiment.number))).one() or 0) + 1
    exp = Experiment(number=number, **payload.model_dump(exclude={"parent_id", "changed_field"}))
    if parent is not None:
        exp.parent_id = parent.id
    if parent is not None and payload.changed_field is not None:
        exp.changed_field = payload.changed_field
        exp.changed_from = getattr(parent, payload.changed_field)
        exp.changed_to = getattr(exp, payload.changed_field)

    band, model_name, n_rows = predict_design(experiments, design_of(exp))
    if band is not None:
        exp.pred_low, exp.pred_median, exp.pred_high = band.low, band.median, band.high
        exp.pred_model, exp.pred_rows = model_name, n_rows
    exp.hypothesis = _hypothesis(exp, parent, band)

    session.add(exp)
    session.commit()
    session.refresh(exp)
    return exp


def lab_note_facts(exp: Experiment, parent: Experiment | None) -> dict[str, Any]:
    distances = [f.distance_m for f in exp.flights]
    median = round(statistics.median(distances), 1)
    issues = sorted({i for f in exp.flights for i in (f.issues or [])})
    facts: dict[str, Any] = {
        "number": exp.number,
        "flights": len(distances),
        "median_m": median,
        "best_m": round(max(distances), 1),
        "issues": [i.replace("_", " ") for i in issues],
    }
    if exp.changed_field:
        spec = FIELDS_BY_NAME[exp.changed_field]
        facts["changed"] = f"{spec.label.lower()} from {spec.format(exp.changed_from)} to {spec.format(exp.changed_to)}"
    if parent is not None and parent.flights:
        facts["parent_median_m"] = round(median_distance(parent), 1)
    if exp.pred_low is not None and exp.pred_high is not None:
        facts["predicted_low"] = round(exp.pred_low, 1)
        facts["predicted_high"] = round(exp.pred_high, 1)
        facts["inside_prediction"] = exp.pred_low <= median <= exp.pred_high
    return facts


async def record_flights(session: Session, exp: Experiment, flights: Sequence[FlightIn]) -> Experiment:
    if exp.id is None:
        raise ValueError("experiment must be saved before logging flights")
    for flight_in in flights:
        issues, source = await gemma.parse_note(flight_in.note)
        session.add(Flight(experiment_id=exp.id, issues=issues, issues_source=source, **flight_in.model_dump()))
    exp.status = "flown"
    session.commit()
    session.refresh(exp)

    parent = session.get(Experiment, exp.parent_id) if exp.parent_id is not None else None
    exp.lab_note, _ = await gemma.write_lab_note(lab_note_facts(exp, parent))
    session.add(exp)
    session.commit()
    session.refresh(exp)
    return exp


def band_out(band: Band | None) -> BandOut | None:
    if band is None:
        return None
    return BandOut(low=round(band.low, 2), median=round(band.median, 2), high=round(band.high, 2), confidence=band.confidence)


def experiment_out(exp: Experiment) -> ExperimentOut:
    distances = [f.distance_m for f in exp.flights]
    times = [f.time_s for f in exp.flights if f.time_s is not None]
    band = None
    if exp.pred_low is not None and exp.pred_median is not None and exp.pred_high is not None:
        band = Band(exp.pred_low, exp.pred_median, exp.pred_high)
    median = statistics.median(distances) if distances else None
    inside = None if band is None or median is None else band.low <= median <= band.high
    return ExperimentOut(
        **exp.model_dump(exclude={"flights", "pred_low", "pred_median", "pred_high"}),
        prediction=band_out(band),
        flights=[FlightOut.model_validate(f.model_dump()) for f in exp.flights],
        median_m=median,
        best_m=max(distances) if distances else None,
        median_time_s=statistics.median(times) if times else None,
        inside_prediction=inside,
    )


def candidate_out(c: Candidate) -> CandidateOut:
    return CandidateOut(
        design=c.design, changed_field=c.changed_field, changed_from=c.changed_from, changed_to=c.changed_to,
        prediction=band_out(c.band), score=c.score, reason=c.reason, fixes_issue=c.fixes_issue,
    )


def recommendation_out(r: Recommendation) -> RecommendationOut:
    return RecommendationOut(
        mode=r.mode, model=r.model, base_experiment_id=r.base_experiment_id, best_median=r.best_median,
        recurring_issues=r.recurring_issues, candidates=[candidate_out(c) for c in r.candidates],
    )
