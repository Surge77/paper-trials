import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Results } from "../src/components/results";
import { FieldsContext } from "../src/fields-context";
import { FIELDS, makeExperiment, makeFlight } from "./factories";

function renderResults(overrides = {}) {
  return render(
    <FieldsContext.Provider value={FIELDS}>
      <Results experiment={makeExperiment(overrides)} />
    </FieldsContext.Provider>,
  );
}

describe("Results", () => {
  it("shows the median, the change and the lab note", () => {
    renderResults();
    expect(screen.getByRole("heading", { name: "Plane #7" })).toBeInTheDocument();
    expect(screen.getByText("Wing span: 19 cm → 20 cm")).toBeInTheDocument();
    expect(screen.getByText("Median rose from 13.6 m to 14.2 m.")).toBeInTheDocument();
  });

  it("says when the real median landed outside the prediction", () => {
    renderResults({ median_m: 18, inside_prediction: false });
    expect(screen.getByText(/outside the range/)).toBeInTheDocument();
  });

  it("labels issue tags with where they came from", () => {
    renderResults({ flights: [makeFlight({ note: "stalled", issues: ["nose_dive"], issues_source: "gemma" })] });
    expect(screen.getByText("nose dive")).toBeInTheDocument();
    expect(screen.getByText("tagged by Gemma")).toBeInTheDocument();
  });
});
