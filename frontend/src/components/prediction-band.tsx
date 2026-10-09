import { metres } from "../fields";
import type { Band } from "../types";

const MIN_SCALE_M = 5;

interface PredictionBandProps {
  band: Band;
  actual?: number | null;
  /** Right edge of the track in metres, so several bands on one page share a scale. */
  scaleMax?: number;
  /** A distance to compare against, such as your best plane so far. */
  reference?: { value: number; label: string } | null;
}

function percent(value: number, max: number): string {
  return `${Math.min(Math.max(value / max, 0), 1) * 100}%`;
}

/** The predicted range as a bar, with the real median dropped onto it once flown. */
export function PredictionBand({ band, actual = null, scaleMax, reference = null }: PredictionBandProps) {
  const max = Math.max(scaleMax ?? 0, band.high * 1.15, (actual ?? 0) * 1.1, (reference?.value ?? 0) * 1.1, MIN_SCALE_M);
  const isInside = actual !== null && actual >= band.low && actual <= band.high;
  const summary =
    `Predicted ${metres(band.low)} to ${metres(band.high)}, most likely ${metres(band.median)}` +
    (actual === null ? "" : `. Flew ${metres(actual)}, ${isInside ? "inside" : "outside"} the range.`);

  return (
    <figure aria-label={summary} className="m-0">
      <div className="relative h-6" aria-hidden="true">
        <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
        <div
          className="absolute top-1 bottom-1 rounded-sm bg-band"
          style={{ left: percent(band.low, max), width: `calc(${percent(band.high, max)} - ${percent(band.low, max)})` }}
        />
        <div className="absolute top-0.5 bottom-0.5 w-0.5 bg-band-ink" style={{ left: percent(band.median, max) }} />
        {reference && (
          <div
            className="absolute -top-0.5 -bottom-0.5 border-l border-dashed border-grass"
            style={{ left: percent(reference.value, max) }}
          />
        )}
        {actual !== null && (
          <div
            className={`absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white ${isInside ? "bg-ink" : "bg-miss"}`}
            style={{ left: percent(actual, max) }}
          />
        )}
      </div>
      <figcaption className="num mt-1 flex flex-wrap justify-between gap-x-3 text-xs text-muted">
        <span>
          Predicted {band.low.toFixed(1)}–{band.high.toFixed(1)} m · {band.confidence} confidence
        </span>
        {reference && actual === null && (
          <span className="text-grass">
            Dashed line: {reference.label}, {metres(reference.value)}
          </span>
        )}
        {actual !== null && (
          <span className={isInside ? "text-ink" : "font-medium text-miss"}>
            Flew {metres(actual)} · {isInside ? "inside" : "outside"} the range
          </span>
        )}
      </figcaption>
    </figure>
  );
}
