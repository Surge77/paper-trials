"""Sample data so the app has something to show on first run.

The sample flights are simulated, not real throws. They come from a made-up
formula plus random noise (see scripts/make_demo_data.py). The predictions
inside them are real though: the script replays the experiments in order
through the same pipeline the app uses, so each prediction was made before
its flights existed. Every sample row is flagged is_demo and shown with a
"sample" label, and one button removes them all.
"""

import json
from datetime import datetime
from importlib import resources
from typing import Any

from sqlmodel import Session, col, delete, select, update

from papertrials.models import Experiment, Flight

DEMO_FILE = "demo_data.json"


def demo_records() -> list[dict[str, Any]]:
    text = resources.files("papertrials").joinpath(DEMO_FILE).read_text(encoding="utf-8")
    return list(json.loads(text))


def has_demo(session: Session) -> bool:
    return session.exec(select(Experiment.id).where(col(Experiment.is_demo))).first() is not None


def load_demo(session: Session) -> int:
    if session.exec(select(Experiment.id)).first() is not None:
        raise ValueError("Sample data can only be loaded into an empty notebook.")
    id_map: dict[int, int] = {}
    records = demo_records()
    for record in records:
        flights = record.pop("flights")
        old_id = record.pop("id")
        parent = record.pop("parent_id")
        record["created_at"] = datetime.fromisoformat(record["created_at"])
        exp = Experiment(**record, is_demo=True, parent_id=id_map.get(parent) if parent else None)
        session.add(exp)
        session.flush()
        if exp.id is None:
            raise RuntimeError("database did not assign an id")
        id_map[old_id] = exp.id
        for flight in flights:
            flight.pop("id", None)
            flight.pop("experiment_id", None)
            flight["created_at"] = datetime.fromisoformat(flight["created_at"])
            session.add(Flight(experiment_id=exp.id, **flight))
    session.commit()
    return len(records)


def clear_demo(session: Session) -> int:
    demo_ids = list(session.exec(select(Experiment.id).where(col(Experiment.is_demo))).all())
    if not demo_ids:
        return 0
    # Your own experiments may have started from a sample plane; keep them, drop the link.
    session.exec(update(Experiment).where(col(Experiment.parent_id).in_(demo_ids)).values(parent_id=None))  # type: ignore[call-overload]
    session.exec(delete(Flight).where(col(Flight.experiment_id).in_(demo_ids)))  # type: ignore[call-overload]
    session.exec(delete(Experiment).where(col(Experiment.id).in_(demo_ids)))  # type: ignore[call-overload]
    session.commit()
    return len(demo_ids)
