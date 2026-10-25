import { designFields, formatValue } from "../fields";
import { useFields } from "../fields-context";
import type { Design } from "../types";

interface DesignTableProps {
  design: Design;
  changedField?: string | null;
  changedFrom?: number | null;
}

/** The full spec of a plane, with the one changed value highlighted. */
export function DesignTable({ design, changedField = null, changedFrom = null }: DesignTableProps) {
  const fields = designFields(useFields());
  return (
    <dl className="grid grid-cols-1 text-sm sm:grid-cols-2">
      {fields.map((spec) => {
        const isChanged = spec.name === changedField;
        return (
          <div
            key={spec.name}
            className={`flex items-baseline justify-between gap-3 border-b border-line px-4 py-2 ${isChanged ? "bg-grass-soft" : ""}`}
          >
            <dt className={isChanged ? "font-medium text-grass" : "text-muted"}>{spec.label}</dt>
            <dd className="num text-right">
              {isChanged && (
                <span className="mr-2 text-xs text-muted line-through">{formatValue(spec, changedFrom)}</span>
              )}
              <span className={isChanged ? "font-semibold" : ""}>{formatValue(spec, design[spec.name])}</span>
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
