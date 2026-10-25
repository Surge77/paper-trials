import type { Design, FieldSpec } from "./types";

export function formatValue(spec: FieldSpec, value: number | null | undefined): string {
  if (value === null || value === undefined) return "not recorded";
  const index = spec.choices.indexOf(value);
  if (spec.choice_labels.length > 0 && index >= 0) return spec.choice_labels[index] ?? String(value);
  const number = Number(value.toFixed(2));
  if (spec.unit === "°") return `${number}°`;
  return `${number} ${spec.unit}`.trim();
}

export function fieldByName(fields: FieldSpec[], name: string | null): FieldSpec | undefined {
  return name === null ? undefined : fields.find((f) => f.name === name);
}

/** "Wing span: 18 cm → 19 cm" for an experiment or candidate that changed one thing. */
export function describeChange(
  fields: FieldSpec[],
  change: { changed_field: string | null; changed_from: number | null; changed_to: number | null },
): string | null {
  const spec = fieldByName(fields, change.changed_field);
  if (!spec) return null;
  return `${spec.label}: ${formatValue(spec, change.changed_from)} → ${formatValue(spec, change.changed_to)}`;
}

export function designFields(fields: FieldSpec[]): FieldSpec[] {
  return fields.filter((f) => f.group !== "conditions");
}

export function pickDesign(fields: FieldSpec[], source: Design): Design {
  return Object.fromEntries(designFields(fields).map((f) => [f.name, source[f.name] ?? null]));
}

export function isInRange(spec: FieldSpec, value: number): boolean {
  if (spec.choices.length > 0) return spec.choices.includes(value);
  return value >= spec.lo && value <= spec.hi;
}

export function issueLabel(issue: string): string {
  return issue.replace(/_/g, " ");
}

export function metres(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(digits)} m`;
}
