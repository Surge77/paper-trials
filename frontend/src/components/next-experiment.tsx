import { describeChange, issueLabel, metres } from "../fields";
import { useFields } from "../fields-context";
import type { Candidate, Recommendation } from "../types";
import { PredictionBand } from "./prediction-band";
import { Card, CardHeader, LinkButton } from "./ui";

const MODE_NOTES: Record<Recommendation["mode"], string> = {
  first: "No flights yet. Every notebook starts with one plain plane as the baseline.",
  sweep: "Still learning the basics, so this tests one setting at a time from your best plane.",
  model: "Ranked by TabPFN: expected distance, plus a bonus where it's unsure and a flight would teach it the most.",
};

interface CandidateRowProps {
  candidate: Candidate;
  index: number;
  scaleMax: number;
  best: number | null;
}

function CandidateRow({ candidate, index, scaleMax, best }: CandidateRowProps) {
  const fields = useFields();
  const change = describeChange(fields, candidate);
  const isTop = index === 0;
  return (
    <li className={`px-4 py-4 ${isTop ? "" : "border-t border-line"}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className={isTop ? "text-base font-semibold" : "text-sm font-medium"}>
            {change ? `Change only ${change.toLowerCase()}` : "Build a plain dart"}
          </p>
          {candidate.fixes_issue && (
            <p className="mt-1 text-xs text-grass">Aimed at the {issueLabel(candidate.fixes_issue)}s in your notes</p>
          )}
        </div>
        <LinkButton href={`#/plan?pick=${index}`} kind={isTop ? "primary" : "secondary"}>
          Plan this
        </LinkButton>
      </div>
      {candidate.prediction && (
        <div className="mt-3">
          <PredictionBand
            band={candidate.prediction}
            scaleMax={scaleMax}
            reference={best === null ? null : { value: best, label: "your best" }}
          />
        </div>
      )}
      {isTop && !candidate.prediction && <p className="mt-2 text-sm text-muted">{candidate.reason}</p>}
    </li>
  );
}

export function NextExperiment({ recommendation }: { recommendation: Recommendation }) {
  const scaleMax = Math.max(recommendation.best_median ?? 0, ...recommendation.candidates.map((c) => c.prediction?.high ?? 0));
  return (
    <Card>
      <CardHeader
        title="Next experiment"
        aside={
          recommendation.best_median !== null && (
            <span className="num text-xs text-muted">Your best: {metres(recommendation.best_median)}</span>
          )
        }
      />
      <p className="px-4 pt-3 text-xs text-muted">{MODE_NOTES[recommendation.mode]}</p>
      <ol>
        {recommendation.candidates.map((candidate, index) => (
          <CandidateRow
            key={index}
            candidate={candidate}
            index={index}
            scaleMax={scaleMax}
            best={recommendation.best_median}
          />
        ))}
      </ol>
      {recommendation.candidates.length === 0 && (
        <p className="px-4 py-4 text-sm text-muted">
          Every one-step change from your best plane has been tried. Plan your own variation from the Lab.
        </p>
      )}
    </Card>
  );
}
