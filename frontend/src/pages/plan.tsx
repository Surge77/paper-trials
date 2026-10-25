import { useState } from "react";

import { api, errorMessage } from "../api";
import { DesignForm } from "../components/design-form";
import { Button, Card, CardHeader, Loading, Notice } from "../components/ui";
import { designFields, isInRange, pickDesign } from "../fields";
import { useFields } from "../fields-context";
import { navigate } from "../router";
import { type Design, type FieldSpec, toDesign } from "../types";
import { useResource } from "../use-resource";

interface Starting {
  design: Design;
  base: Design | null;
  parentId: number | null;
  parentNumber: number | null;
  reason: string | null;
}

async function loadStarting(fields: FieldSpec[], pick: number | null, copy: number | null): Promise<Starting> {
  if (copy !== null) {
    const exp = await api.experiment(copy);
    const design = pickDesign(fields, toDesign(exp));
    return { design, base: design, parentId: exp.id, parentNumber: exp.number, reason: null };
  }
  const recommendation = await api.recommendation();
  const candidate = recommendation.candidates[pick ?? 0];
  if (!candidate) throw new Error("That suggestion is gone. Go back to the notebook for fresh ones.");
  const parentId = recommendation.base_experiment_id;
  const parent = parentId === null ? null : await api.experiment(parentId);
  return {
    design: pickDesign(fields, candidate.design),
    base: parent ? pickDesign(fields, toDesign(parent)) : null,
    parentId,
    parentNumber: parent?.number ?? null,
    reason: candidate.reason,
  };
}

function changedFields(fields: FieldSpec[], design: Design, base: Design | null): FieldSpec[] {
  if (base === null) return [];
  return designFields(fields).filter((f) => (base[f.name] ?? null) !== (design[f.name] ?? null));
}

function outOfRange(fields: FieldSpec[], design: Design): FieldSpec[] {
  return designFields(fields).filter((f) => {
    const value = design[f.name];
    return value !== null && value !== undefined && !isInRange(f, value);
  });
}

export function PlanPage({ pick, copy, onDataChange }: { pick: number | null; copy: number | null; onDataChange: () => void }) {
  const fields = useFields();
  const [starting] = useResource(() => loadStarting(fields, pick, copy), [pick, copy]);
  if (starting.status === "loading") return <Loading />;
  if (starting.status === "error") return <Notice tone="error">{starting.message}</Notice>;
  // Keyed so editing the URL from one suggestion to another resets the form.
  return <PlanForm key={`${pick}-${copy}`} starting={starting.data} onDataChange={onDataChange} />;
}

function PlanForm({ starting, onDataChange }: { starting: Starting; onDataChange: () => void }) {
  const fields = useFields();
  const [design, setDesign] = useState<Design>(starting.design);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { base, parentId, parentNumber, reason } = starting;
  const changed = changedFields(fields, design, base);
  const invalid = outOfRange(fields, design);

  async function save() {
    setIsSaving(true);
    setError(null);
    try {
      const exp = await api.createExperiment({
        design,
        parent_id: parentId,
        changed_field: changed.length === 1 ? (changed[0]?.name ?? null) : null,
      });
      onDataChange();
      navigate(`#/experiments/${exp.id}`);
    } catch (e) {
      setError(errorMessage(e));
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Plan the next plane</h1>
        <p className="mt-1 text-sm text-muted">
          {parentNumber === null
            ? "This is your baseline. Fill in what you know; anything you leave out is just not recorded."
            : `Starting from plane #${parentNumber}. Change one thing so you'll know what made the difference.`}
        </p>
      </div>
      {reason && <Notice>{reason}</Notice>}
      <Card>
        <CardHeader title="Design" />
        <div className="px-4 py-4">
          <DesignForm fields={fields} design={design} base={base} onChange={setDesign} />
        </div>
      </Card>
      {changed.length > 1 && (
        <Notice>
          You've changed {changed.length} things ({changed.map((f) => f.label.toLowerCase()).join(", ")}). That's allowed,
          but if the distance moves you won't know which change did it.
        </Notice>
      )}
      {invalid.length > 0 && (
        <Notice tone="error">
          Out of range: {invalid.map((f) => `${f.label} (${f.lo}–${f.hi} ${f.unit})`).join(", ")}
        </Notice>
      )}
      {error && <Notice tone="error">{error}</Notice>}
      <div className="flex flex-wrap items-center gap-3">
        <Button kind="primary" onClick={save} disabled={isSaving || invalid.length > 0}>
          {isSaving ? "Saving prediction…" : "Save plan and predict"}
        </Button>
        <a href="#/" className="text-sm text-muted hover:text-ink">
          Cancel
        </a>
      </div>
      <p className="text-xs text-muted">
        The prediction is saved now and can't be edited later, so the comparison with your real flights stays honest.
      </p>
    </div>
  );
}
