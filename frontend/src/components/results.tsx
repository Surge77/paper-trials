import { describeChange, issueLabel, metres } from "../fields";
import { useFields } from "../fields-context";
import { type Experiment, type Flight, toDesign } from "../types";
import { DesignTable } from "./design-table";
import { PredictionBand } from "./prediction-band";
import { Card, CardHeader, LinkButton, Stat } from "./ui";

const WIND = ["calm", "light", "breezy"];

function FlightRow({ flight, index }: { flight: Flight; index: number }) {
  return (
    <tr className="border-t border-line align-top">
      <td className="num px-4 py-2 text-muted">{index + 1}</td>
      <td className="num px-2 py-2 font-medium">{metres(flight.distance_m)}</td>
      <td className="num px-2 py-2">{flight.time_s === null ? "—" : `${flight.time_s} s`}</td>
      <td className="num px-2 py-2">{flight.stability ?? "—"}</td>
      <td className="px-2 py-2">{flight.wind === null ? "—" : WIND[flight.wind]}</td>
      <td className="px-4 py-2">
        {flight.note && <div>{flight.note}</div>}
        {flight.issues.length > 0 && (
          <div className="mt-1 flex flex-wrap items-center gap-1">
            {flight.issues.map((issue) => (
              <span key={issue} className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
                {issueLabel(issue)}
              </span>
            ))}
            <span className="text-[11px] text-muted">
              tagged by {flight.issues_source === "gemma" ? "Gemma" : "keywords"}
            </span>
          </div>
        )}
      </td>
    </tr>
  );
}

export function Results({ experiment }: { experiment: Experiment }) {
  const fields = useFields();
  const change = describeChange(fields, experiment);
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Plane #{experiment.number}</h1>
        <p className="mt-1 text-sm text-muted">{change ?? "Starting plane"}</p>
      </div>
      <Card className="grid grid-cols-3 sm:divide-x sm:divide-line">
        <Stat label="Median distance" value={metres(experiment.median_m)} />
        <Stat label="Best throw" value={metres(experiment.best_m)} />
        <Stat label="Median time" value={experiment.median_time_s === null ? "—" : `${experiment.median_time_s.toFixed(1)} s`} />
      </Card>
      {experiment.lab_note && (
        <Card>
          <CardHeader title="Lab note" />
          <p className="px-4 py-3 text-sm">{experiment.lab_note}</p>
        </Card>
      )}
      {experiment.prediction && (
        <Card>
          <CardHeader title="Prediction vs what happened" aside={<span className="text-xs text-muted">by {experiment.pred_model === "tabpfn" ? "TabPFN" : "baseline guess"}</span>} />
          <div className="px-4 py-4">
            <PredictionBand band={experiment.prediction} actual={experiment.median_m} />
            {experiment.hypothesis && <p className="mt-3 text-xs text-muted">Hypothesis: {experiment.hypothesis}</p>}
          </div>
        </Card>
      )}
      <Card>
        <CardHeader title={`Flights (${experiment.flights.length})`} />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted">
              <tr>
                <th className="px-4 py-2 font-normal">#</th>
                <th className="px-2 py-2 font-normal">Distance</th>
                <th className="px-2 py-2 font-normal">Time</th>
                <th className="px-2 py-2 font-normal">Steady</th>
                <th className="px-2 py-2 font-normal">Wind</th>
                <th className="px-4 py-2 font-normal">Notes</th>
              </tr>
            </thead>
            <tbody>
              {experiment.flights.map((flight, i) => (
                <FlightRow key={flight.id} flight={flight} index={i} />
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card>
        <CardHeader title="The plane" />
        <DesignTable design={toDesign(experiment)} changedField={experiment.changed_field} changedFrom={experiment.changed_from} />
      </Card>
      <div className="flex flex-wrap gap-3">
        <LinkButton href="#/" kind="primary">
          See the next suggestion
        </LinkButton>
        <LinkButton href={`#/plan?copy=${experiment.id}`}>Plan your own change from this plane</LinkButton>
      </div>
    </div>
  );
}
