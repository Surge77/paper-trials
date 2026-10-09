"""Builds the sample notebook in src/papertrials/demo_data.json.

The flights are SIMULATED. A made-up formula decides how far each design
"wants" to fly, then random noise and wind are added. Nothing here was
thrown by a person.

What is real: every experiment is planned by the app's own recommender, and
its prediction is made by the app's own model using only the flights that
came before it. So the prediction-vs-actual chart in the sample notebook is
an honest replay, not something drawn after the fact.

Run from the backend folder:
    uv run python scripts/make_demo_data.py            # notes parsed by keywords, template lab notes
    uv run python scripts/make_demo_data.py --gemma    # use local Gemma for notes and lab notes
"""

import argparse
import asyncio
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from sqlmodel import Session

from papertrials import db, lab
from papertrials.config import get_settings
from papertrials.ml.recommender import recommend
from papertrials.models import Experiment
from papertrials.schemas import ExperimentCreate, FlightIn

EXPERIMENTS = 12
FLIGHTS_PER_EXPERIMENT = 3
SEED = 7
OUTPUT = Path(__file__).resolve().parents[1] / "src" / "papertrials" / "demo_data.json"
START = datetime(2026, 10, 6, 15, 30, tzinfo=timezone.utc)


def true_distance(e: Experiment) -> float:
    """The pretend physics. Unknown to the app; it only ever sees the noisy results."""
    span = e.wing_span_cm or 18
    distance = 13.0
    distance -= 0.10 * (span - 23) ** 2
    distance -= 0.003 * ((e.nose_angle_deg or 35) - 30) ** 2
    distance -= 0.08 * ((e.body_length_cm or 21) - 21) ** 2
    distance += {0: 0.0, 1: 2.2, 2: 0.4}[int(e.elevator_bend or 0)]
    distance += {0: 0.0, 1: 1.5, 2: 0.8, 3: -1.0}[int(e.added_clips or 0)]
    winglet = e.winglet_mm or 0
    distance += 0.12 * winglet - 0.006 * winglet**2
    return distance


def simulated_note(e: Experiment, rng: np.random.Generator) -> str | None:
    clips, bend = int(e.added_clips or 0), int(e.elevator_bend or 0)
    if clips == 0 and bend == 0 and rng.random() < 0.7:
        return str(rng.choice(["climbed then stalled", "went up, stalled and dropped", "stalled halfway"]))
    if clips >= 2 and bend == 0 and rng.random() < 0.6:
        return "nose dived into the grass"
    if bend == 2 and rng.random() < 0.5:
        return "swooped up and stalled"
    if rng.random() < 0.15:
        return str(rng.choice(["drifted left a bit", "pulled right at the end"]))
    if rng.random() < 0.3:
        return str(rng.choice(["smooth glide", "nice and flat", "good one"]))
    return None


def simulated_flights(e: Experiment, rng: np.random.Generator) -> list[FlightIn]:
    flights = []
    for _ in range(FLIGHTS_PER_EXPERIMENT):
        wind = float(rng.choice([0, 1, 2], p=[0.6, 0.3, 0.1]))
        distance = true_distance(e) + rng.normal(0, 0.9) - wind * rng.uniform(0, 1.2)
        distance = round(max(distance, 1.5), 1)
        flights.append(FlightIn(
            distance_m=distance,
            time_s=round(distance / rng.uniform(5.0, 6.5), 1),
            stability=int(np.clip(round(3 + rng.normal(0, 1) - wind * 0.5), 1, 5)),
            wind=wind,
            note=simulated_note(e, rng),
        ))
    return flights


async def build(session: Session, rng: np.random.Generator) -> None:
    for i in range(EXPERIMENTS):
        rec = recommend(lab.list_experiments(session))
        top = rec.candidates[0]
        payload = ExperimentCreate(
            **{k: v for k, v in top.design.items()},
            parent_id=rec.base_experiment_id,
            changed_field=top.changed_field,
        )
        exp = lab.create_experiment(session, payload)
        exp.created_at = START + timedelta(hours=i // 6 * 20, minutes=(i % 6) * 14)
        await lab.record_flights(session, exp, simulated_flights(exp, rng))
        for n, flight in enumerate(exp.flights):
            flight.created_at = exp.created_at + timedelta(minutes=4 + n * 2)
        session.commit()
        print(f"#{exp.number} {exp.changed_field or 'start'}: median {np.median([f.distance_m for f in exp.flights]):.1f} m, "
              f"predicted {exp.pred_median and round(exp.pred_median, 1)} by {exp.pred_model}")


def dump(session: Session) -> list[dict]:
    records = []
    for exp in lab.list_experiments(session):
        record = exp.model_dump(mode="json", exclude={"is_demo"})
        record["flights"] = [f.model_dump(mode="json", exclude={"experiment_id"}) for f in exp.flights]
        records.append(record)
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gemma", action="store_true", help="use local Gemma via Ollama for notes")
    args = parser.parse_args()

    settings = get_settings()
    if not args.gemma:
        settings.ollama_url = "http://127.0.0.1:9"
    with tempfile.TemporaryDirectory() as tmp:
        settings.db_path = Path(tmp) / "demo.db"
        engine = db.get_engine()
        with Session(engine) as session:
            asyncio.run(build(session, np.random.default_rng(SEED)))
            OUTPUT.write_text(json.dumps(dump(session), indent=1, ensure_ascii=False), encoding="utf-8")
        engine.dispose()
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
