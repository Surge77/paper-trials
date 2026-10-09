import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PredictionBand } from "../src/components/prediction-band";
import { makeBand } from "./factories";

describe("PredictionBand", () => {
  it("describes the range for screen readers", () => {
    render(<PredictionBand band={makeBand()} />);
    expect(screen.getByRole("figure")).toHaveAccessibleName("Predicted 12.0 m to 16.0 m, most likely 14.0 m");
  });

  it("marks a flight inside the range", () => {
    render(<PredictionBand band={makeBand()} actual={13.5} />);
    expect(screen.getByText("Flew 13.5 m · inside the range")).toBeInTheDocument();
  });

  it("marks a flight outside the range", () => {
    render(<PredictionBand band={makeBand()} actual={17.2} />);
    expect(screen.getByText("Flew 17.2 m · outside the range")).toBeInTheDocument();
  });

  it("names the reference line before flying", () => {
    render(<PredictionBand band={makeBand()} reference={{ value: 15.1, label: "your best" }} />);
    expect(screen.getByText("Dashed line: your best, 15.1 m")).toBeInTheDocument();
  });
});
