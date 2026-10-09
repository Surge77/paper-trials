"""Picks the next experiment.

Rules, in order:

1. Start from your best plane so far.
2. Only ever change one thing, by one small step, so a result can be traced to its cause.
3. Never suggest a plane you've already built.
4. Score each option by its predicted median distance, plus a bonus for how
   uncertain the model is. Uncertain options are worth testing because the
   result teaches the model the most.
5. If your notes keep mentioning the same problem (stalls, nose dives...),
   options known to address that problem get a bonus too.

Before there is enough data for TabPFN, it walks through a fixed list of
fields one at a time so the first flights cover the basics.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from papertrials.fields import COLD_START_SWEEP, DESIGN_FIELDS, FIELDS_BY_NAME
from papertrials.ml.dataset import build_training_set, design_of, feature_row
from papertrials.ml.predictor import Band, get_predictor, has_enough_for_tabpfn
from papertrials.models import Experiment

EXPLORATION_WEIGHT = 0.25
ISSUE_BONUS_M = 1.0
MAX_CANDIDATES = 3
CALM = 0.0

# Which single change tends to help with each recurring problem, and in which direction.
ISSUE_FIXES: dict[str, tuple[tuple[str, int], ...]] = {
    "stall": (("added_clips", 1), ("elevator_bend", -1)),
    "nose_dive": (("elevator_bend", 1), ("added_clips", -1)),
    "spiral": (("winglet_mm", 1),),
    "flutter": (("wing_span_cm", -1),),
    "tumble": (("added_clips", 1),),
}

STARTER_DESIGN: dict[str, float | None] = {
    "fold_style": 0, "wing_span_cm": 18, "body_length_cm": 21, "nose_angle_deg": 35,
    "winglet_mm": 0, "elevator_bend": 0, "added_clips": 0, "paper_gsm": 80,
    "launch_angle": 0, "launch_force": 2,
}

Mode = Literal["first", "sweep", "model"]


@dataclass(frozen=True)
class Candidate:
    design: dict[str, float | None]
    changed_field: str | None
    changed_from: float | None
    changed_to: float | None
    band: Band | None
    score: float | None
    reason: str
    fixes_issue: str | None = None


@dataclass(frozen=True)
class Recommendation:
    mode: Mode
    model: str | None
    base_experiment_id: int | None
    best_median: float | None
    recurring_issues: list[str]
    candidates: list[Candidate] = field(default_factory=list)


def median_distance(exp: Experiment) -> float:
    return float(np.median([f.distance_m for f in exp.flights]))


def recurring_issues(exp: Experiment) -> list[str]:
    """Issues mentioned in at least half of an experiment's flights (needs 2+ flights)."""
    if len(exp.flights) < 2:
        return []
    counts = Counter(issue for f in exp.flights for issue in set(f.issues or []))
    return [issue for issue, n in counts.most_common() if n * 2 >= len(exp.flights)]


def _design_key(design: dict[str, float | None]) -> tuple[float | None, ...]:
    return tuple(design.get(f.name) for f in DESIGN_FIELDS)


def _issue_fixed_by(field_name: str, direction: int, issues: Sequence[str]) -> str | None:
    for issue in issues:
        if (field_name, direction) in ISSUE_FIXES.get(issue, ()):
            return issue
    return None


def _one_step_options(
    base: dict[str, float | None], fields: Sequence[str], tested: set[tuple[float | None, ...]]
) -> list[tuple[dict[str, float | None], str, float, float]]:
    options = []
    for name in fields:
        spec = FIELDS_BY_NAME[name]
        current = base.get(name)
        if current is None or not spec.tunable:
            continue
        for value in spec.neighbours(current):
            design = {**base, name: value}
            if _design_key(design) not in tested:
                options.append((design, name, current, value))
    return options


def _reason(name: str, old: float, new: float, band: Band | None, best: float, issue: str | None) -> str:
    spec = FIELDS_BY_NAME[name]
    text = f"Change only {spec.label.lower()}: {spec.format(old)} → {spec.format(new)}."
    if band is not None:
        text += (
            f" Expected around {band.median:.1f} m (likely {band.low:.1f}–{band.high:.1f} m)"
            f" vs your best of {best:.1f} m."
        )
    if issue is not None:
        text += f" Also aimed at the {issue.replace('_', ' ')}s in your notes."
    return text


def recommend(experiments: Sequence[Experiment]) -> Recommendation:
    flown = [e for e in experiments if e.status == "flown" and e.flights]
    if not flown:
        return Recommendation(
            mode="first", model=None, base_experiment_id=None, best_median=None, recurring_issues=[],
            candidates=[Candidate(
                design=dict(STARTER_DESIGN), changed_field=None, changed_from=None, changed_to=None,
                band=None, score=None,
                reason="Start with a plain dart from one sheet of printer paper. Measure it, fly it three times, and that becomes your baseline.",
            )],
        )

    base_exp = max(flown, key=lambda e: (median_distance(e), e.number))
    base = design_of(base_exp)
    best = median_distance(base_exp)
    issues = recurring_issues(base_exp)
    tested = {_design_key(design_of(e)) for e in experiments}

    data = build_training_set(flown)
    mode: Mode = "model" if has_enough_for_tabpfn(data) else "sweep"
    all_fields = [f.name for f in DESIGN_FIELDS]
    options = []
    if mode == "sweep":
        varied = {e.changed_field for e in experiments if e.changed_field}
        for name in (n for n in COLD_START_SWEEP if n not in varied):
            options = _one_step_options(base, [name], tested)
            if options:
                break
    if not options:
        options = _one_step_options(base, all_fields, tested)
    predictor = get_predictor(data)
    bands: list[Band | None] = [None] * len(options)
    if predictor is not None and options:
        X = np.array([feature_row(design, CALM) for design, *_ in options])
        bands = list(predictor.predict(X))

    candidates = []
    for (design, name, old, new), band in zip(options, bands, strict=True):
        direction = 1 if new > old else -1
        issue = _issue_fixed_by(name, direction, issues)
        score = None
        if band is not None:
            score = band.median + EXPLORATION_WEIGHT * band.width + (ISSUE_BONUS_M if issue else 0.0)
        candidates.append(Candidate(
            design=design, changed_field=name, changed_from=old, changed_to=new, band=band,
            score=score, reason=_reason(name, old, new, band, best, issue), fixes_issue=issue,
        ))
    candidates.sort(key=lambda c: c.score if c.score is not None else float("-inf"), reverse=True)

    return Recommendation(
        mode=mode, model=getattr(predictor, "name", None), base_experiment_id=base_exp.id,
        best_median=best, recurring_issues=issues, candidates=candidates[:MAX_CANDIDATES],
    )
