"""The variables you can record about a plane and how you throw it.

Everything else (the database columns, the model features, the form in the
browser and the steps the recommender is allowed to take) is derived from
this one list, so adding a variable means adding one entry here.
"""

from dataclasses import dataclass
from typing import Literal

Group = Literal["design", "launch", "conditions"]


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    group: Group
    unit: str = ""
    help: str = ""
    # Discrete choices, stored as numbers. `choice_labels` names each one.
    choices: tuple[float, ...] = ()
    choice_labels: tuple[str, ...] = ()
    # Continuous range and the size of one "small change" for the recommender.
    lo: float = 0.0
    hi: float = 0.0
    step: float = 0.0
    # Whether the recommender may suggest changing this field.
    tunable: bool = True
    categorical: bool = False

    def neighbours(self, value: float) -> list[float]:
        """Values one small step away from `value`, staying inside the allowed range."""
        if self.choices:
            if value not in self.choices:
                return []
            i = self.choices.index(value)
            return [self.choices[j] for j in (i - 1, i + 1) if 0 <= j < len(self.choices)]
        return [round(v, 2) for v in (value - self.step, value + self.step) if self.lo <= v <= self.hi]

    def format(self, value: float | None) -> str:
        if value is None:
            return "not recorded"
        if self.choice_labels and value in self.choices:
            return self.choice_labels[self.choices.index(value)]
        number = f"{value:g}"
        if self.unit == "°":
            return f"{number}°"
        return f"{number} {self.unit}".strip()


FOLD_STYLES = ("dart", "glider", "delta", "other")

FIELDS: tuple[Field, ...] = (
    Field(
        "fold_style", "Fold style", "design",
        help="The basic design you started from.",
        choices=(0, 1, 2, 3), choice_labels=FOLD_STYLES, tunable=False, categorical=True,
    ),
    Field(
        "wing_span_cm", "Wing span", "design", "cm",
        help="Tip to tip, measured flat.", lo=8, hi=30, step=1,
    ),
    Field(
        "body_length_cm", "Body length", "design", "cm",
        help="Nose to tail.", lo=12, hi=30, step=1,
    ),
    Field(
        "nose_angle_deg", "Nose angle", "design", "°",
        help="Rough angle of the nose point. A sharp dart is about 30°.", lo=15, hi=70, step=5,
    ),
    Field(
        "winglet_mm", "Winglets", "design", "mm",
        help="Height of the folded-up wing tips. 0 if flat.", lo=0, hi=30, step=5,
    ),
    Field(
        "elevator_bend", "Tail bend", "design",
        help="Upward bend on the back edge of the wings.",
        choices=(0, 1, 2), choice_labels=("none", "slight", "strong"),
    ),
    Field(
        "added_clips", "Paper clips", "design",
        help="Paper clips on the nose.", choices=(0, 1, 2, 3), choice_labels=("0", "1", "2", "3"),
    ),
    Field(
        "paper_gsm", "Paper weight", "design", "gsm",
        help="Printer paper is usually 80 gsm.",
        choices=(70, 80, 90, 100, 120), choice_labels=("70 gsm", "80 gsm", "90 gsm", "100 gsm", "120 gsm"),
        tunable=False,
    ),
    Field(
        "launch_angle", "Launch angle", "launch",
        choices=(-1, 0, 1), choice_labels=("aimed down", "level", "aimed up"), tunable=False,
    ),
    Field(
        "launch_force", "Throw strength", "launch",
        choices=(1, 2, 3), choice_labels=("gentle", "medium", "hard"), tunable=False,
    ),
    Field(
        "wind", "Wind", "conditions",
        help="Per flight. Wind is noise you can't control, so it's recorded, not tuned.",
        choices=(0, 1, 2), choice_labels=("calm", "light", "breezy"), tunable=False,
    ),
)

FIELDS_BY_NAME = {f.name: f for f in FIELDS}
DESIGN_FIELDS = tuple(f for f in FIELDS if f.group in ("design", "launch"))
FEATURE_NAMES = tuple(f.name for f in FIELDS)
CATEGORICAL_INDICES = tuple(i for i, f in enumerate(FIELDS) if f.categorical)

# Field order for the first few experiments, before there is enough data to model.
COLD_START_SWEEP = ("wing_span_cm", "nose_angle_deg", "elevator_bend", "added_clips")
