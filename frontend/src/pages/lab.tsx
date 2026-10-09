import { useState } from "react";

import { api, errorMessage } from "../api";
import { DesignExplorer, PredictionChart } from "../components/lab-charts";
import { Button, Card, CardHeader, Loading, Notice, SampleBadge } from "../components/ui";
import { describeChange, metres } from "../fields";
import { useFields } from "../fields-context";
import type { Experiment, Insights } from "../types";
import { useResource } from "../use-resource";

const MODEL_LABELS = { tabpfn: "TabPFN", baseline: "Baseline guess" } as const;

function Verdict({ experiment }: { experiment: Experiment }) {
  if (experiment.status === "planned") return <span className="text-grass">not flown yet</span>;
  if (experiment.inside_prediction === null) return <span className="text-muted">no prediction</span>;
  return experiment.inside_prediction ? <span>inside</span> : <span className="font-medium text-miss">outside</span>;
}

function History({ experiments }: { experiments: Experiment[] }) {
  const fields = useFields();
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-muted">
          <tr>
            <th className="px-4 py-2 font-normal">Plane</th>
            <th className="px-2 py-2 font-normal">What changed</th>
            <th className="px-2 py-2 font-normal">Predicted</th>
            <th className="px-2 py-2 font-normal">Median</th>
            <th className="px-4 py-2 font-normal">Range</th>
          </tr>
        </thead>
        <tbody>
          {[...experiments].reverse().map((e) => (
            <tr key={e.id} className="border-t border-line hover:bg-gray-50">
              <td className="px-4 py-2">
                <a href={`#/experiments/${e.id}`} className="font-medium underline-offset-2 hover:underline">
                  #{e.number}
                </a>{" "}
                {e.is_demo && <SampleBadge />}
              </td>
              <td className="px-2 py-2">{describeChange(fields, e) ?? <span className="text-muted">starting plane</span>}</td>
              <td className="num px-2 py-2 text-muted">
                {e.prediction ? `${e.prediction.low.toFixed(1)}–${e.prediction.high.toFixed(1)} m` : "—"}
              </td>
              <td className="num px-2 py-2 font-medium">{metres(e.median_m)}</td>
              <td className="px-4 py-2">
                <Verdict experiment={e} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ModelScores({ insights }: { insights: Insights }) {
  const entries = (["baseline", "tabpfn"] as const).flatMap((m) => {
    const s = insights[m];
    return s ? [[m, s] as const] : [];
  });
  if (entries.length === 0) return <p className="px-4 py-4 text-sm text-muted">No flown predictions yet.</p>;
  return (
    <dl className="grid divide-line sm:grid-cols-2 sm:divide-x">
      {entries.map(([model, s]) => (
        <div key={model} className="px-4 py-3">
          <dt className="text-xs text-muted">{MODEL_LABELS[model]}</dt>
          <dd className="num mt-0.5 text-sm">
            <strong className="text-lg">
              {s.inside_range}/{s.experiments}
            </strong>{" "}
            inside the range · off by {s.mean_abs_error_m.toFixed(1)} m on average
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function LabPage({ onDataChange }: { onDataChange: () => void }) {
  const [data, reload] = useResource(() => Promise.all([api.experiments(), api.insights()]), []);
  const [error, setError] = useState<string | null>(null);

  if (data.status === "loading") return <Loading />;
  if (data.status === "error") return <Notice tone="error">{data.message}</Notice>;
  const [experiments, insights] = data.data;
  const hasDemo = experiments.some((e) => e.is_demo);

  async function clearDemo() {
    try {
      await api.clearDemo();
      reload();
      onDataChange();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  if (experiments.length === 0) {
    return <Notice>Nothing here yet. Plan your first plane from the notebook.</Notice>;
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Lab</h1>
      <Card>
        <CardHeader title="Prediction vs real median, plane by plane" />
        <div className="px-2 pt-4">
          <PredictionChart experiments={experiments} />
        </div>
        <p className="px-4 pb-3 text-xs text-muted">
          Shaded: the range predicted before flying. Dots: what the plane really did. Orange dots landed outside.
        </p>
      </Card>
      <Card>
        <CardHeader title="How good the predictions were" />
        <ModelScores insights={insights} />
      </Card>
      <Card>
        <CardHeader title="Design explorer" />
        <DesignExplorer experiments={experiments} />
      </Card>
      <Card>
        <CardHeader title="Every plane" />
        <History experiments={experiments} />
      </Card>
      {error && <Notice tone="error">{error}</Notice>}
      {hasDemo && (
        <Button kind="danger" onClick={clearDemo}>
          Remove sample data
        </Button>
      )}
    </div>
  );
}
