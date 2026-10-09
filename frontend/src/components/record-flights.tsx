import { useState } from "react";

import type { FlightInput } from "../types";
import { Button } from "./ui";

export const DEFAULT_FLIGHTS = 3;
export const MAX_FLIGHTS = 10;
export const MAX_DISTANCE_M = 100;
export const STEP_LENGTH_M = 0.75;

const WIND = ["calm", "light", "breezy"] as const;

interface Row {
  distance: string;
  time: string;
  stability: string;
  wind: string;
  note: string;
}

const EMPTY_ROW: Row = { distance: "", time: "", stability: "", wind: "0", note: "" };
const INPUT = "w-full rounded-md border border-line bg-white px-2 py-2 text-sm focus:border-grass focus:outline-none";

function optionalNumber(text: string): number | null {
  return text.trim() === "" ? null : Number(text);
}

/** Turns the typed rows into flights, or returns the first problem found. */
export function toFlights(rows: Row[], unit: "m" | "steps"): FlightInput[] | string {
  const flights: FlightInput[] = [];
  for (const [i, row] of rows.entries()) {
    if (row.distance.trim() === "") continue;
    const raw = Number(row.distance);
    const distance = unit === "steps" ? raw * STEP_LENGTH_M : raw;
    if (!Number.isFinite(distance) || distance <= 0 || distance > MAX_DISTANCE_M) {
      return `Flight ${i + 1}: distance must be more than 0 and at most ${MAX_DISTANCE_M} m.`;
    }
    const time = optionalNumber(row.time);
    if (time !== null && (!Number.isFinite(time) || time <= 0 || time > 60)) {
      return `Flight ${i + 1}: time must be between 0 and 60 seconds.`;
    }
    flights.push({
      distance_m: Math.round(distance * 10) / 10,
      time_s: time,
      stability: optionalNumber(row.stability),
      wind: optionalNumber(row.wind),
      note: row.note.trim() || null,
    });
  }
  return flights.length > 0 ? flights : "Enter the distance of at least one flight.";
}

export function RecordFlights({ onSubmit }: { onSubmit: (flights: FlightInput[]) => Promise<void> }) {
  const [rows, setRows] = useState<Row[]>(() => Array.from({ length: DEFAULT_FLIGHTS }, () => EMPTY_ROW));
  const [unit, setUnit] = useState<"m" | "steps">("m");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const update = (index: number, patch: Partial<Row>) =>
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));

  async function submit() {
    const result = toFlights(rows, unit);
    if (typeof result === "string") {
      setError(result);
      return;
    }
    setError(null);
    setIsSaving(true);
    try {
      await onSubmit(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save the flights");
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-3 px-4 py-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted">Distance in</span>
        {(["m", "steps"] as const).map((u) => (
          <button
            key={u}
            type="button"
            aria-pressed={unit === u}
            onClick={() => setUnit(u)}
            className={`rounded-md border px-3 py-1 ${unit === u ? "border-grass bg-grass-soft font-medium" : "border-line bg-white"}`}
          >
            {u === "m" ? "metres" : `steps (≈${STEP_LENGTH_M} m each)`}
          </button>
        ))}
      </div>
      <ol className="space-y-3">
        {rows.map((row, i) => (
          <li key={i} className="grid grid-cols-2 gap-2 rounded-md border border-line p-3 sm:grid-cols-[3rem_1fr_1fr_1fr_1fr]">
            <span className="col-span-2 self-center text-sm font-medium sm:col-span-1">#{i + 1}</span>
            <label className="text-xs text-muted">
              Distance ({unit === "m" ? "m" : "steps"})
              <input aria-label={`Flight ${i + 1} distance`} className={`${INPUT} num mt-1`} type="number" inputMode="decimal" min="0" step="0.1" value={row.distance} onChange={(e) => update(i, { distance: e.target.value })} />
            </label>
            <label className="text-xs text-muted">
              Time in air (s)
              <input aria-label={`Flight ${i + 1} time`} className={`${INPUT} num mt-1`} type="number" inputMode="decimal" min="0" step="0.1" value={row.time} onChange={(e) => update(i, { time: e.target.value })} />
            </label>
            <label className="text-xs text-muted">
              Steadiness
              <select className={`${INPUT} mt-1`} value={row.stability} onChange={(e) => update(i, { stability: e.target.value })}>
                <option value="">—</option>
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n} {n === 1 ? "wobbly" : n === 5 ? "steady" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-muted">
              Wind
              <select className={`${INPUT} mt-1`} value={row.wind} onChange={(e) => update(i, { wind: e.target.value })}>
                {WIND.map((w, n) => (
                  <option key={w} value={n}>
                    {w}
                  </option>
                ))}
              </select>
            </label>
            <label className="col-span-2 text-xs text-muted sm:col-span-4 sm:col-start-2">
              What did it do? (optional)
              <input aria-label={`Flight ${i + 1} note`} className={`${INPUT} mt-1`} maxLength={500} placeholder="e.g. climbed, stalled, then veered left" value={row.note} onChange={(e) => update(i, { note: e.target.value })} />
            </label>
          </li>
        ))}
      </ol>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <Button kind="primary" onClick={submit} disabled={isSaving}>
          {isSaving ? "Saving and writing the lab note…" : "Save flights"}
        </Button>
        {rows.length < MAX_FLIGHTS && (
          <Button onClick={() => setRows((r) => [...r, EMPTY_ROW])} disabled={isSaving}>
            Add another flight
          </Button>
        )}
      </div>
    </div>
  );
}
