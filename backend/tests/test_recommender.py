from papertrials.fields import DESIGN_FIELDS
from papertrials.ml.dataset import design_of
from papertrials.ml.recommender import recommend, recurring_issues
from tests.factories import make_experiment


def _changed_fields(before: dict, after: dict) -> list[str]:
    return [f.name for f in DESIGN_FIELDS if before.get(f.name) != after.get(f.name)]


def test_empty_notebook_suggests_a_starter_plane() -> None:
    rec = recommend([])
    assert rec.mode == "first"
    assert len(rec.candidates) == 1
    assert rec.candidates[0].changed_field is None


def test_planned_but_unflown_experiments_do_not_count_as_data() -> None:
    assert recommend([make_experiment()]).mode == "first"


def test_cold_start_sweeps_wing_span_first() -> None:
    rec = recommend([make_experiment([10, 11, 12])])
    assert rec.mode == "sweep"
    assert {c.changed_field for c in rec.candidates} == {"wing_span_cm"}


def test_cold_start_moves_on_after_a_field_was_varied() -> None:
    base = make_experiment([10, 11, 12])
    varied = make_experiment([9, 10, 11], changed_field="wing_span_cm", wing_span_cm=19)
    rec = recommend([base, varied])
    assert {c.changed_field for c in rec.candidates} == {"nose_angle_deg"}


def test_every_candidate_changes_exactly_one_field_of_the_best_plane() -> None:
    weak = make_experiment([8, 9, 9], wing_span_cm=16)
    best = make_experiment([14, 15, 15], wing_span_cm=20)
    rec = recommend([weak, best, make_experiment([10, 10, 11], wing_span_cm=17), make_experiment([11, 12, 12], wing_span_cm=18)])
    assert rec.mode == "model"
    assert rec.base_experiment_id == best.id
    for c in rec.candidates:
        assert _changed_fields(design_of(best), c.design) == [c.changed_field]


def test_never_suggests_a_plane_already_built() -> None:
    base = make_experiment([10, 11, 12], wing_span_cm=18)
    tried_up = make_experiment([9, 9, 9], wing_span_cm=19)
    tried_down = make_experiment(wing_span_cm=17)  # planned, not flown yet, still counts as built
    rec = recommend([base, tried_up, tried_down])
    built = {tuple(design_of(e).values()) for e in (base, tried_up, tried_down)}
    assert all(tuple(c.design[k] for k in design_of(base)) not in built for c in rec.candidates)


def test_untunable_fields_are_never_changed() -> None:
    exps = [make_experiment([10 + i, 11 + i, 12 + i], wing_span_cm=16 + i) for i in range(4)]
    rec = recommend(exps)
    assert all(c.changed_field not in {"fold_style", "paper_gsm", "launch_angle", "launch_force"} for c in rec.candidates)


def test_candidates_are_ranked_by_score() -> None:
    exps = [make_experiment([10 + i, 11 + i, 12 + i], wing_span_cm=16 + i) for i in range(4)]
    scores = [c.score for c in recommend(exps).candidates if c.score is not None]
    assert scores
    assert scores == sorted(scores, reverse=True)


def test_recurring_issue_needs_half_the_flights() -> None:
    exp = make_experiment([10, 10, 10, 10], issues=[["stall"], ["stall"], [], ["spiral"]])
    assert recurring_issues(exp) == ["stall"]


def test_recurring_stall_boosts_adding_a_paper_clip() -> None:
    stalls = [["stall"], ["stall"], ["stall"]]
    exps = [make_experiment([10, 10, 10], issues=stalls, wing_span_cm=16 + i) for i in range(3)]
    exps.append(make_experiment([12, 12, 12], issues=stalls, wing_span_cm=20))
    rec = recommend(exps)
    assert rec.recurring_issues == ["stall"]
    clip = next(c for c in rec.candidates if c.changed_field == "added_clips")
    assert clip.fixes_issue == "stall"
    assert "stalls" in clip.reason
