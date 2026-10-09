from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select

from papertrials import demo, gemma, lab
from papertrials.config import get_settings
from papertrials.db import get_session
from papertrials.fields import FIELDS
from papertrials.ml.dataset import build_training_set
from papertrials.ml.predictor import (
    MIN_EXPERIMENTS_FOR_TABPFN,
    MIN_FLIGHTS_FOR_TABPFN,
    has_enough_for_tabpfn,
    status as model_status,
)
from papertrials.ml.recommender import recommend
from papertrials.models import Experiment
from papertrials.schemas import (
    ExperimentCreate,
    ExperimentOut,
    FlightsIn,
    RecommendationOut,
    StatusOut,
)

MAX_PHOTO_BYTES = 8 * 1024 * 1024

router = APIRouter(prefix="/api")
SessionDep = Annotated[Session, Depends(get_session)]


def _get_experiment(session: Session, experiment_id: int) -> Experiment:
    exp = session.get(Experiment, experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.get("/fields")
async def list_fields() -> list[dict[str, Any]]:
    return [asdict(f) for f in FIELDS]


@router.get("/status")
async def get_status(session: SessionDep) -> StatusOut:
    settings = get_settings()
    flown = lab.flown_only(lab.list_experiments(session))
    data = build_training_set(flown)
    model_in_use = None
    if data.n_rows:
        use_tabpfn = has_enough_for_tabpfn(data) and settings.use_tabpfn and model_status.tabpfn_error is None
        model_in_use = "tabpfn" if use_tabpfn else "baseline"
    return StatusOut(
        gemma_available=await gemma.is_available(),
        gemma_model=settings.gemma_model,
        tabpfn_enabled=settings.use_tabpfn,
        tabpfn_error=model_status.tabpfn_error,
        model_in_use=model_in_use,
        flown_experiments=data.n_experiments,
        flights=data.n_rows,
        flights_needed_for_tabpfn=MIN_FLIGHTS_FOR_TABPFN,
        experiments_needed_for_tabpfn=MIN_EXPERIMENTS_FOR_TABPFN,
        has_demo_data=demo.has_demo(session),
    )


@router.get("/experiments")
async def list_experiments(session: SessionDep) -> list[ExperimentOut]:
    return [lab.experiment_out(e) for e in lab.list_experiments(session)]


@router.post("/experiments", status_code=201)
async def create_experiment(payload: ExperimentCreate, session: SessionDep) -> ExperimentOut:
    try:
        exp = await run_in_threadpool(lab.create_experiment, session, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return lab.experiment_out(exp)


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: int, session: SessionDep) -> ExperimentOut:
    return lab.experiment_out(_get_experiment(session, experiment_id))


@router.delete("/experiments/{experiment_id}", status_code=204)
async def delete_experiment(experiment_id: int, session: SessionDep) -> None:
    exp = _get_experiment(session, experiment_id)
    children = session.exec(select(Experiment).where(Experiment.parent_id == exp.id)).all()
    for child in children:
        child.parent_id = None
        session.add(child)
    session.delete(exp)
    session.commit()


@router.post("/experiments/{experiment_id}/flights")
async def add_flights(experiment_id: int, payload: FlightsIn, session: SessionDep) -> ExperimentOut:
    exp = _get_experiment(session, experiment_id)
    exp = await lab.record_flights(session, exp, payload.flights)
    return lab.experiment_out(exp)


@router.post("/experiments/{experiment_id}/photo")
async def check_photo(experiment_id: int, photo: UploadFile, session: SessionDep) -> ExperimentOut:
    exp = _get_experiment(session, experiment_id)
    if not (photo.content_type or "").startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload an image")
    image = await photo.read(MAX_PHOTO_BYTES + 1)
    if len(image) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 8 MB")
    try:
        result = await gemma.check_photo(image)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Gemma couldn't check the photo. Is Ollama running?") from exc
    # Only the estimate is kept. The photo itself is never written to disk.
    exp.photo_check = result
    session.add(exp)
    session.commit()
    session.refresh(exp)
    return lab.experiment_out(exp)


@router.get("/recommendation")
async def get_recommendation(session: SessionDep) -> RecommendationOut:
    experiments = lab.list_experiments(session)
    result = await run_in_threadpool(recommend, experiments)
    return lab.recommendation_out(result)


@router.get("/insights")
async def get_insights(session: SessionDep) -> dict[str, Any]:
    """How good the frozen predictions turned out to be, split by which model made them."""
    by_model: dict[str, dict[str, float]] = {}
    for exp in lab.flown_only(lab.list_experiments(session)):
        out = lab.experiment_out(exp)
        if out.prediction is None or out.median_m is None or exp.pred_model is None:
            continue
        stats = by_model.setdefault(exp.pred_model, {"count": 0, "inside": 0, "abs_error_sum": 0.0})
        stats["count"] += 1
        stats["inside"] += 1 if out.inside_prediction else 0
        stats["abs_error_sum"] += abs(out.median_m - out.prediction.median)
    return {
        model: {
            "experiments": int(s["count"]),
            "inside_range": int(s["inside"]),
            "mean_abs_error_m": round(s["abs_error_sum"] / s["count"], 2),
        }
        for model, s in by_model.items()
    }


@router.post("/demo", status_code=201)
async def load_demo(session: SessionDep) -> dict[str, int]:
    try:
        return {"loaded": demo.load_demo(session)}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/demo")
async def clear_demo(session: SessionDep) -> dict[str, int]:
    return {"removed": demo.clear_demo(session)}
