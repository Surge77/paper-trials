from papertrials.fields import DESIGN_FIELDS, FIELDS_BY_NAME
from papertrials.models import DesignBase


def test_design_columns_match_field_list() -> None:
    assert set(DesignBase.model_fields) == {f.name for f in DESIGN_FIELDS}


def test_numeric_neighbours_take_one_step_each_way() -> None:
    assert FIELDS_BY_NAME["wing_span_cm"].neighbours(18) == [17, 19]


def test_numeric_neighbours_stay_inside_range() -> None:
    assert FIELDS_BY_NAME["wing_span_cm"].neighbours(30) == [29]
    assert FIELDS_BY_NAME["winglet_mm"].neighbours(0) == [5]


def test_choice_neighbours_move_to_adjacent_choice() -> None:
    assert FIELDS_BY_NAME["added_clips"].neighbours(0) == [1]
    assert FIELDS_BY_NAME["elevator_bend"].neighbours(1) == [0, 2]


def test_choice_neighbours_of_unknown_value_are_empty() -> None:
    assert FIELDS_BY_NAME["added_clips"].neighbours(7) == []


def test_format_uses_choice_labels_and_units() -> None:
    assert FIELDS_BY_NAME["elevator_bend"].format(2) == "strong"
    assert FIELDS_BY_NAME["wing_span_cm"].format(18.5) == "18.5 cm"
    assert FIELDS_BY_NAME["wing_span_cm"].format(None) == "not recorded"


def test_degrees_sit_right_after_the_number() -> None:
    assert FIELDS_BY_NAME["nose_angle_deg"].format(30) == "30°"
