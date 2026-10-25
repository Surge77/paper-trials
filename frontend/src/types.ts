// Mirrors backend/src/papertrials/schemas.py and fields.py.

export type FieldGroup = "design" | "launch" | "conditions";

export interface FieldSpec {
  name: string;
  label: string;
  group: FieldGroup;
  unit: string;
  help: string;
  choices: number[];
  choice_labels: string[];
  lo: number;
  hi: number;
  step: number;
  tunable: boolean;
  categorical: boolean;
}

/** Any subset of design and launch values, keyed by field name. */
export type Design = Record<string, number | null>;

// The design and launch columns every experiment carries (backend models.DesignBase).
export const DESIGN_KEYS = [
  "fold_style",
  "wing_span_cm",
  "body_length_cm",
  "nose_angle_deg",
  "winglet_mm",
  "elevator_bend",
  "added_clips",
  "paper_gsm",
  "launch_angle",
  "launch_force",
] as const;

export type DesignValues = Record<(typeof DESIGN_KEYS)[number], number | null>;

export function toDesign(values: DesignValues): Design {
  return Object.fromEntries(DESIGN_KEYS.map((key) => [key, values[key]]));
}

export type Confidence = "high" | "medium" | "low";

export interface Band {
  low: number;
  median: number;
  high: number;
  confidence: Confidence;
}

export interface Flight {
  id: number;
  distance_m: number;
  time_s: number | null;
  stability: number | null;
  wind: number | null;
  note: string | null;
  issues: string[];
  issues_source: "gemma" | "keywords" | null;
}

export interface PhotoCheck {
  symmetry: "even" | "uneven" | "unclear";
  nose: "sharp" | "blunt" | "unclear";
  winglets_visible: boolean;
  comment: string;
  confidence: number;
  estimate: true;
}

export type ModelName = "tabpfn" | "baseline";

export interface Experiment extends DesignValues {
  id: number;
  number: number;
  created_at: string;
  status: "planned" | "flown";
  is_demo: boolean;
  parent_id: number | null;
  changed_field: string | null;
  changed_from: number | null;
  changed_to: number | null;
  prediction: Band | null;
  pred_model: ModelName | null;
  pred_rows: number | null;
  hypothesis: string | null;
  lab_note: string | null;
  photo_check: PhotoCheck | null;
  flights: Flight[];
  median_m: number | null;
  best_m: number | null;
  median_time_s: number | null;
  inside_prediction: boolean | null;
}

export interface Candidate {
  design: Design;
  changed_field: string | null;
  changed_from: number | null;
  changed_to: number | null;
  prediction: Band | null;
  score: number | null;
  reason: string;
  fixes_issue: string | null;
}

export interface Recommendation {
  mode: "first" | "sweep" | "model";
  model: ModelName | null;
  base_experiment_id: number | null;
  best_median: number | null;
  recurring_issues: string[];
  candidates: Candidate[];
}

export interface Status {
  gemma_available: boolean;
  gemma_model: string;
  tabpfn_enabled: boolean;
  tabpfn_error: string | null;
  model_in_use: ModelName | null;
  flown_experiments: number;
  flights: number;
  flights_needed_for_tabpfn: number;
  experiments_needed_for_tabpfn: number;
  has_demo_data: boolean;
}

export interface ModelInsight {
  experiments: number;
  inside_range: number;
  mean_abs_error_m: number;
}

export type Insights = Partial<Record<ModelName, ModelInsight>>;

export interface FlightInput {
  distance_m: number;
  time_s: number | null;
  stability: number | null;
  wind: number | null;
  note: string | null;
}

export interface ExperimentInput {
  design: Design;
  parent_id: number | null;
  changed_field: string | null;
}
