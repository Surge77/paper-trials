import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RecordFlights, STEP_LENGTH_M, toFlights } from "../src/components/record-flights";

const row = (distance: string, note = "") => ({ distance, time: "", stability: "", wind: "", note });

describe("toFlights", () => {
  it("skips empty rows and keeps the rest", () => {
    expect(toFlights([row("12.4"), row(""), row("13", " stalled ")], "m")).toEqual([
      { distance_m: 12.4, time_s: null, stability: null, wind: null, note: null },
      { distance_m: 13, time_s: null, stability: null, wind: null, note: "stalled" },
    ]);
  });

  it("converts steps to metres", () => {
    const flights = toFlights([row("20")], "steps");
    expect(flights).toEqual([expect.objectContaining({ distance_m: Math.round(20 * STEP_LENGTH_M * 10) / 10 })]);
  });

  it("rejects impossible distances with the flight number", () => {
    expect(toFlights([row("10"), row("-3")], "m")).toBe("Flight 2: distance must be more than 0 and at most 100 m.");
  });

  it("asks for at least one distance", () => {
    expect(toFlights([row(""), row("")], "m")).toBe("Enter the distance of at least one flight.");
  });
});

describe("RecordFlights", () => {
  it("leaves wind unrecorded unless you pick one", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RecordFlights onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText("Flight 1 distance"), "9");
    await userEvent.selectOptions(screen.getByLabelText("Flight 2 wind"), "breezy");
    await userEvent.type(screen.getByLabelText("Flight 2 distance"), "8");
    await userEvent.click(screen.getByRole("button", { name: "Save flights" }));
    expect(onSubmit).toHaveBeenCalledWith([
      expect.objectContaining({ distance_m: 9, wind: null }),
      expect.objectContaining({ distance_m: 8, wind: 2 }),
    ]);
  });

  it("submits typed flights", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RecordFlights onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText("Flight 1 distance"), "14.8");
    await userEvent.type(screen.getByLabelText("Flight 1 note"), "veered left");
    await userEvent.click(screen.getByRole("button", { name: "Save flights" }));
    expect(onSubmit).toHaveBeenCalledWith([
      { distance_m: 14.8, time_s: null, stability: null, wind: null, note: "veered left" },
    ]);
  });

  it("shows the problem instead of submitting an empty form", async () => {
    const onSubmit = vi.fn();
    render(<RecordFlights onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole("button", { name: "Save flights" }));
    expect(screen.getByRole("alert")).toHaveTextContent("at least one flight");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
