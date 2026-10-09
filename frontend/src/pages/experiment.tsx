import { useState } from "react";

import { api, errorMessage } from "../api";
import { DesignTable } from "../components/design-table";
import { PhotoCheck } from "../components/photo-check";
import { PredictionBand } from "../components/prediction-band";
import { RecordFlights } from "../components/record-flights";
import { Results } from "../components/results";
import { Button, Card, CardHeader, Loading, Notice, SampleBadge } from "../components/ui";
import { fieldByName, formatValue } from "../fields";
import { useFields } from "../fields-context";
import { navigate } from "../router";
import { type Experiment, type FlightInput, toDesign } from "../types";
import { useResource } from "../use-resource";

function OutsideSteps({ experiment }: { experiment: Experiment }) {
  const spec = fieldByName(useFields(), experiment.changed_field);
  const build = spec
    ? `Build plane #${experiment.number}. Change only the ${spec.label.toLowerCase()}, to ${formatValue(spec, experiment.changed_to)}.`
    : `Build plane #${experiment.number} from the spec below.`;
  const steps = [
    build,
    "Close this tab and go outside. Pick a spot you can come back to.",
    "Throw it three times, the same way each time.",
    "Measure each landing with a tape, or count your steps.",
    "Come back and log the flights below.",
  ];
  return (
    <ol className="space-y-2 px-4 py-4">
      {steps.map((step, i) => (
        <li key={step} className="flex gap-3 text-sm">
          <span className="num flex size-6 shrink-0 items-center justify-center rounded-full bg-grass-soft text-xs font-semibold text-grass">
            {i + 1}
          </span>
          <span className="pt-0.5">{step}</span>
        </li>
      ))}
    </ol>
  );
}

function TestMode({ experiment, onUpdated, onDeleted }: {
  experiment: Experiment;
  onUpdated: (e: Experiment) => void;
  onDeleted: () => void;
}) {
  const [error, setError] = useState<string | null>(null);

  async function record(flights: FlightInput[]) {
    onUpdated(await api.addFlights(experiment.id, flights));
  }

  async function remove() {
    try {
      await api.deleteExperiment(experiment.id);
      onDeleted();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium text-grass">Ready to fly</p>
        <h1 className="text-2xl font-semibold">Plane #{experiment.number}: time to go outside</h1>
        {experiment.hypothesis && <p className="mt-2 max-w-3xl text-sm">{experiment.hypothesis}</p>}
      </div>
      <Card>
        <CardHeader title="Before you come back" />
        <OutsideSteps experiment={experiment} />
      </Card>
      <Card>
        <CardHeader title="Prediction, saved before flying" />
        <div className="px-4 py-4">
          {experiment.prediction ? (
            <PredictionBand band={experiment.prediction} />
          ) : (
            <p className="text-sm text-muted">No prediction for your first plane. Its flights become the baseline.</p>
          )}
          {experiment.pred_model === "baseline" && (
            <p className="mt-2 text-xs text-muted">
              A rough guess from your most similar planes. TabPFN takes over once there's more data.
            </p>
          )}
        </div>
      </Card>
      <Card>
        <CardHeader title="The plane" />
        <DesignTable design={toDesign(experiment)} changedField={experiment.changed_field} changedFrom={experiment.changed_from} />
      </Card>
      <Card>
        <CardHeader title="Optional: photo check" />
        <PhotoCheck experiment={experiment} onChecked={onUpdated} />
      </Card>
      <Card className="border-grass">
        <CardHeader title="Log your flights" />
        <RecordFlights onSubmit={record} />
      </Card>
      {error && <Notice tone="error">{error}</Notice>}
      <Button kind="danger" onClick={remove}>
        Delete this plan
      </Button>
    </div>
  );
}

export function ExperimentPage({ id, onDataChange }: { id: number; onDataChange: () => void }) {
  const [loaded] = useResource(() => api.experiment(id), [id]);
  const [updated, setUpdated] = useState<Experiment | null>(null);

  if (loaded.status === "loading") return <Loading />;
  if (loaded.status === "error") return <Notice tone="error">{loaded.message}</Notice>;
  const experiment = updated ?? loaded.data;

  const onUpdated = (e: Experiment) => {
    setUpdated(e);
    onDataChange();
    window.scrollTo(0, 0);
  };
  const onDeleted = () => {
    onDataChange();
    navigate("#/");
  };

  return (
    <div className="space-y-4">
      {experiment.is_demo && (
        <p className="text-sm text-muted">
          <SampleBadge /> Simulated flights from the sample notebook.
        </p>
      )}
      {experiment.status === "planned" ? (
        <TestMode experiment={experiment} onUpdated={onUpdated} onDeleted={onDeleted} />
      ) : (
        <Results experiment={experiment} />
      )}
    </div>
  );
}
