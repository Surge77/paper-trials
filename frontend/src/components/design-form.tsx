import { formatValue } from "../fields";
import type { Design, FieldSpec } from "../types";

interface DesignFormProps {
  fields: FieldSpec[];
  design: Design;
  base: Design | null;
  onChange: (design: Design) => void;
}

const INPUT = "w-full rounded-md border border-line bg-white px-3 py-2 text-sm focus:border-grass focus:outline-none";

function FieldInput({ spec, value, onChange }: { spec: FieldSpec; value: number | null; onChange: (v: number | null) => void }) {
  if (spec.choices.length > 0) {
    return (
      <select
        id={spec.name}
        className={INPUT}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      >
        <option value="">not recorded</option>
        {spec.choices.map((choice) => (
          <option key={choice} value={choice}>
            {formatValue(spec, choice)}
          </option>
        ))}
      </select>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <input
        id={spec.name}
        type="number"
        inputMode="decimal"
        className={`${INPUT} num`}
        min={spec.lo}
        max={spec.hi}
        step={spec.step || "any"}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      />
      <span className="w-8 text-sm text-muted">{spec.unit}</span>
    </div>
  );
}

const GROUP_TITLES: Record<string, string> = { design: "The plane", launch: "How you'll throw it" };

/** Inputs for every design and launch field. Values that differ from `base` are marked. */
export function DesignForm({ fields, design, base, onChange }: DesignFormProps) {
  const groups = (["design", "launch"] as const).map((group) => ({
    group,
    specs: fields.filter((f) => f.group === group),
  }));
  return (
    <div className="space-y-6">
      {groups.map(({ group, specs }) => (
        <fieldset key={group}>
          <legend className="mb-3 text-sm font-semibold">{GROUP_TITLES[group]}</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            {specs.map((spec) => {
              const value = design[spec.name] ?? null;
              const isChanged = base !== null && (base[spec.name] ?? null) !== value;
              return (
                <div key={spec.name}>
                  <label htmlFor={spec.name} className="mb-1 flex items-baseline justify-between gap-2 text-sm">
                    <span className={isChanged ? "font-medium text-grass" : ""}>{spec.label}</span>
                    {isChanged && base && (
                      <span className="text-xs text-muted">was {formatValue(spec, base[spec.name])}</span>
                    )}
                  </label>
                  <FieldInput spec={spec} value={value} onChange={(v) => onChange({ ...design, [spec.name]: v })} />
                  {spec.help && <p className="mt-1 text-xs text-muted">{spec.help}</p>}
                </div>
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
