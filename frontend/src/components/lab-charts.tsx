import { useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { designFields, formatValue } from "../fields";
import { useFields } from "../fields-context";
import { type Experiment, toDesign } from "../types";

const INK = "#111827";
const GRID = "#e5e7eb";
const BAND = "#c7d2fe";
const BAND_INK = "#3730a3";
const MISS = "#b45309";
const CHART_HEIGHT = 260;
const DEFAULT_EXPLORER_FIELD = "wing_span_cm";

export function PredictionChart({ experiments }: { experiments: Experiment[] }) {
  const rows = experiments
    .filter((e) => e.median_m !== null)
    .map((e) => ({
      number: e.number,
      band: e.prediction ? [e.prediction.low, e.prediction.high] : null,
      predicted: e.prediction?.median ?? null,
      actual: e.median_m,
      isInside: e.inside_prediction,
    }));
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <ComposedChart data={rows} margin={{ top: 10, right: 16, bottom: 4, left: -8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="number" tickFormatter={(n: number) => `#${n}`} tick={{ fontSize: 12 }} />
        <YAxis unit=" m" tick={{ fontSize: 12 }} width={56} />
        <Tooltip
          labelFormatter={(n) => `Plane #${String(n)}`}
          formatter={(value, name) =>
            Array.isArray(value)
              ? [`${Number(value[0]).toFixed(1)}–${Number(value[1]).toFixed(1)} m`, "Predicted range"]
              : [`${Number(value).toFixed(1)} m`, name === "actual" ? "Real median" : "Predicted median"]
          }
        />
        <Area dataKey="band" stroke="none" fill={BAND} fillOpacity={0.8} connectNulls={false} isAnimationActive={false} />
        <Line dataKey="predicted" stroke={BAND_INK} strokeDasharray="4 3" dot={false} connectNulls={false} isAnimationActive={false} />
        <Line
          dataKey="actual"
          stroke={INK}
          strokeWidth={1.5}
          isAnimationActive={false}
          dot={(props: { cx?: number; cy?: number; index?: number }) => {
            const isMiss = rows[props.index ?? 0]?.isInside === false;
            return <circle key={props.index} cx={props.cx} cy={props.cy} r={4} fill={isMiss ? MISS : INK} stroke="white" strokeWidth={1.5} />;
          }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/** Every flight plotted against one design setting, so you can eyeball what matters. */
export function DesignExplorer({ experiments }: { experiments: Experiment[] }) {
  const fields = designFields(useFields()).filter((f) => !f.categorical);
  const [fieldName, setFieldName] = useState(DEFAULT_EXPLORER_FIELD);
  const spec = fields.find((f) => f.name === fieldName);
  const points = experiments.flatMap((e) =>
    e.flights.map((f) => ({ x: toDesign(e)[fieldName] ?? null, y: f.distance_m, number: e.number })),
  ).filter((p) => p.x !== null);

  return (
    <div className="px-4 py-4">
      <label className="flex flex-wrap items-center gap-2 text-sm">
        Distance against
        <select
          className="rounded-md border border-line bg-white px-2 py-1"
          value={fieldName}
          onChange={(e) => setFieldName(e.target.value)}
        >
          {fields.map((f) => (
            <option key={f.name} value={f.name}>
              {f.label.toLowerCase()}
            </option>
          ))}
        </select>
      </label>
      {points.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted">No flights with this setting recorded yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <ScatterChart margin={{ top: 16, right: 16, bottom: 4, left: -8 }}>
            <CartesianGrid stroke={GRID} />
            <XAxis
              type="number"
              dataKey="x"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v: number) => (spec ? formatValue(spec, v) : String(v))}
              tick={{ fontSize: 12 }}
            />
            <YAxis type="number" dataKey="y" unit=" m" tick={{ fontSize: 12 }} width={56} />
            <Tooltip
              formatter={(value, name) =>
                name === "y" ? [`${Number(value).toFixed(1)} m`, "Distance"] : [spec ? formatValue(spec, Number(value)) : value, spec?.label ?? ""]
              }
            />
            <Scatter data={points} fill={INK} fillOpacity={0.6} isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>
      )}
      <p className="mt-2 text-xs text-muted">
        Each dot is one throw. Wind and how you throw add noise, so look for a trend, not a line.
      </p>
    </div>
  );
}
