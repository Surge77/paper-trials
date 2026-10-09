from itertools import count

from papertrials.ml.recommender import STARTER_DESIGN
from papertrials.models import Experiment, Flight

_ids = count(1)


def make_experiment(
    distances: list[float] | None = None,
    issues: list[list[str]] | None = None,
    status: str | None = None,
    changed_field: str | None = None,
    **design: float | None,
) -> Experiment:
    """An in-memory experiment with flights, for tests that don't need a database."""
    exp_id = next(_ids)
    exp = Experiment(id=exp_id, number=exp_id, changed_field=changed_field)
    for name, value in {**STARTER_DESIGN, **design}.items():
        setattr(exp, name, value)
    distances = distances or []
    issues = issues or [[] for _ in distances]
    exp.flights = [
        Flight(id=i, experiment_id=exp_id, distance_m=d, wind=0, issues=iss)
        for i, (d, iss) in enumerate(zip(distances, issues, strict=True))
    ]
    exp.status = status or ("flown" if distances else "planned")
    return exp
