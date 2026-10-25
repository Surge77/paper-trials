import type { Band, Experiment, FieldSpec, Flight } from "../src/types";

export function makeField(overrides: Partial<FieldSpec> = {}): FieldSpec {
  return {
    name: "wing_span_cm",
    label: "Wing span",
    group: "design",
    unit: "cm",
    help: "",
    choices: [],
    choice_labels: [],
    lo: 8,
    hi: 30,
    step: 1,
    tunable: true,
    categorical: false,
    ...overrides,
  };
}

export const FIELDS: FieldSpec[] = [
  makeField(),
  makeField({ name: "nose_angle_deg", label: "Nose angle", unit: "°", lo: 15, hi: 70, step: 5 }),
  makeField({
    name: "elevator_bend",
    label: "Tail bend",
    unit: "",
    choices: [0, 1, 2],
    choice_labels: ["none", "slight", "strong"],
  }),
  makeField({ name: "wind", label: "Wind", group: "conditions", unit: "", choices: [0, 1, 2], choice_labels: ["calm", "light", "breezy"] }),
];

export function makeBand(overrides: Partial<Band> = {}): Band {
  return { low: 12, median: 14, high: 16, confidence: "medium", ...overrides };
}

export function makeFlight(overrides: Partial<Flight> = {}): Flight {
  return {
    id: 1,
    distance_m: 14.2,
    time_s: 2.4,
    stability: 4,
    wind: 0,
    note: null,
    issues: [],
    issues_source: null,
    ...overrides,
  };
}

export function makeExperiment(overrides: Partial<Experiment> = {}): Experiment {
  return {
    id: 7,
    number: 7,
    created_at: "2026-10-06T15:30:00",
    status: "flown",
    is_demo: false,
    parent_id: 6,
    changed_field: "wing_span_cm",
    changed_from: 19,
    changed_to: 20,
    prediction: makeBand(),
    pred_model: "tabpfn",
    pred_rows: 18,
    hypothesis: null,
    lab_note: "Median rose from 13.6 m to 14.2 m.",
    photo_check: null,
    flights: [makeFlight({ id: 1 }), makeFlight({ id: 2, distance_m: 13.1 }), makeFlight({ id: 3, distance_m: 15 })],
    median_m: 14.2,
    best_m: 15,
    median_time_s: 2.4,
    inside_prediction: true,
    fold_style: 0,
    wing_span_cm: 20,
    body_length_cm: 21,
    nose_angle_deg: 30,
    winglet_mm: 0,
    elevator_bend: 1,
    added_clips: 0,
    paper_gsm: 80,
    launch_angle: 0,
    launch_force: 2,
    ...overrides,
  };
}
