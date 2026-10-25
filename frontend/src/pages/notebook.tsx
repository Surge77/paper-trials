import { useState } from "react";

import { api, errorMessage } from "../api";
import { NextExperiment } from "../components/next-experiment";
import { Button, Card, CardHeader, LinkButton, Loading, Notice, SampleBadge, Stat } from "../components/ui";
import { describeChange, metres } from "../fields";
import { useFields } from "../fields-context";
import type { Experiment } from "../types";
import { useResource } from "../use-resource";

const LOOP_STEPS = [
  ["Plan", "Pick one thing to change. The app saves its prediction before you fly."],
  ["Fly", "Build the plane, go outside, throw it three times the same way."],
  ["Log", "Come back and enter how far each throw went."],
  ["Learn", "TabPFN learns from every flight and suggests the next change."],
] as const;

function Welcome({ onLoadSample, isBusy }: { onLoadSample: () => void; isBusy: boolean }) {
  return (
    <Card>
      <div className="px-5 py-6">
        <h1 className="text-xl font-semibold">A lab notebook for paper airplanes</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Change one thing at a time, fly it outside, and write down what happened. Most of the work happens away from
          this screen.
        </p>
        <ol className="mt-5 grid gap-3 sm:grid-cols-4">
          {LOOP_STEPS.map(([title, text], i) => (
            <li key={title} className="rounded-md border border-line p-3">
              <div className="text-xs text-muted">Step {i + 1}</div>
              <div className="font-medium">{title}</div>
              <p className="mt-1 text-xs text-muted">{text}</p>
            </li>
          ))}
        </ol>
        <div className="mt-6 flex flex-wrap gap-3">
          <LinkButton href="#/plan?pick=0" kind="primary">
            Start with a plain dart
          </LinkButton>
          <Button onClick={onLoadSample} disabled={isBusy}>
            Look around with sample data
          </Button>
        </div>
      </div>
    </Card>
  );
}

function WaitingToFly({ planned }: { planned: Experiment[] }) {
  const fields = useFields();
  return (
    <Card className="border-grass">
      <CardHeader title="Waiting to be flown" />
      <ul>
        {planned.map((exp) => (
          <li key={exp.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3 last:border-0">
            <div>
              <span className="font-medium">Plane #{exp.number}</span>{" "}
              <span className="text-sm text-muted">{describeChange(fields, exp) ?? "starting plane"}</span>
            </div>
            <LinkButton href={`#/experiments/${exp.id}`} kind="primary">
              Take it outside
            </LinkButton>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Summary({ experiments }: { experiments: Experiment[] }) {
  const flown = experiments.filter((e) => e.median_m !== null);
  const best = flown.reduce<Experiment | null>((a, e) => (a === null || (e.median_m ?? 0) > (a.median_m ?? 0) ? e : a), null);
  const predicted = flown.filter((e) => e.inside_prediction !== null);
  const inside = predicted.filter((e) => e.inside_prediction).length;
  return (
    <Card className="grid grid-cols-2 divide-line sm:grid-cols-4 sm:divide-x">
      <Stat label="Best plane" value={metres(best?.median_m)} hint={best ? `#${best.number}, median of its flights` : undefined} />
      <Stat label="Planes flown" value={flown.length} />
      <Stat label="Flights logged" value={flown.reduce((n, e) => n + e.flights.length, 0)} />
      <Stat
        label="Predictions that held"
        value={predicted.length ? `${inside}/${predicted.length}` : "—"}
        hint="real median inside the predicted range"
      />
    </Card>
  );
}

export function NotebookPage({ onDataChange }: { onDataChange: () => void }) {
  const [data, reload] = useResource(() => Promise.all([api.experiments(), api.recommendation(), api.status()]), []);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setIsBusy(true);
    setError(null);
    try {
      await action();
      reload();
      onDataChange();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setIsBusy(false);
    }
  }

  if (data.status === "loading") return <Loading />;
  if (data.status === "error") return <Notice tone="error">{data.message}</Notice>;
  const [experiments, recommendation, status] = data.data;
  const planned = experiments.filter((e) => e.status === "planned");

  return (
    <div className="space-y-5">
      {error && <Notice tone="error">{error}</Notice>}
      {status.has_demo_data && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-amber-200 bg-miss-soft px-4 py-2 text-sm">
          <span>
            <SampleBadge /> The sample flights are simulated, not real throws. The predictions in them are real model
            output.
          </span>
          <Button onClick={() => run(api.clearDemo)} disabled={isBusy}>
            Remove sample data
          </Button>
        </div>
      )}
      {experiments.length === 0 ? (
        <Welcome onLoadSample={() => run(api.loadDemo)} isBusy={isBusy} />
      ) : (
        <>
          {planned.length > 0 && <WaitingToFly planned={planned} />}
          <Summary experiments={experiments} />
          <NextExperiment recommendation={recommendation} />
        </>
      )}
    </div>
  );
}
