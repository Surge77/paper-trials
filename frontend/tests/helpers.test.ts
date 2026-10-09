import { describe, expect, it } from "vitest";

import { modelSummary } from "../src/components/status-bar";
import { describeChange, formatValue, isInRange } from "../src/fields";
import { parseRoute } from "../src/router";
import type { Status } from "../src/types";
import { FIELDS } from "./factories";

const [wingSpan, noseAngle, tailBend] = FIELDS as [(typeof FIELDS)[0], (typeof FIELDS)[0], (typeof FIELDS)[0]];

describe("formatValue", () => {
  it("uses choice labels, units and a tight degree sign", () => {
    expect(formatValue(tailBend, 2)).toBe("strong");
    expect(formatValue(wingSpan, 18.5)).toBe("18.5 cm");
    expect(formatValue(noseAngle, 30)).toBe("30°");
    expect(formatValue(wingSpan, null)).toBe("not recorded");
  });

  it("describes a one-field change", () => {
    const change = { changed_field: "wing_span_cm", changed_from: 18, changed_to: 19 };
    expect(describeChange(FIELDS, change)).toBe("Wing span: 18 cm → 19 cm");
    expect(describeChange(FIELDS, { ...change, changed_field: null })).toBeNull();
  });

  it("checks ranges and choices", () => {
    expect(isInRange(wingSpan, 31)).toBe(false);
    expect(isInRange(tailBend, 1)).toBe(true);
    expect(isInRange(tailBend, 1.5)).toBe(false);
  });
});

describe("parseRoute", () => {
  it.each([
    ["", { page: "notebook" }],
    ["#/lab", { page: "lab" }],
    ["#/experiments/12", { page: "experiment", id: 12 }],
    ["#/plan?pick=1", { page: "plan", pick: 1, copy: null }],
    ["#/plan?copy=abc", { page: "plan", pick: null, copy: null }],
    ["#/nowhere", { page: "notebook" }],
  ])("parses %s", (hash, route) => {
    expect(parseRoute(hash)).toEqual(route);
  });
});

describe("modelSummary", () => {
  const base: Status = {
    gemma_available: true,
    gemma_model: "gemma3:4b",
    tabpfn_enabled: true,
    tabpfn_error: null,
    model_in_use: "baseline",
    flown_experiments: 2,
    flights: 6,
    flights_needed_for_tabpfn: 8,
    experiments_needed_for_tabpfn: 4,
    has_demo_data: false,
  };

  it("says how much more data TabPFN needs", () => {
    expect(modelSummary(base).detail).toBe("TabPFN takes over after 2 more planes and 2 more flights");
  });

  it("explains when TabPFN failed to load", () => {
    expect(modelSummary({ ...base, flown_experiments: 5, flights: 15, tabpfn_error: "out of memory" }).detail).toBe(
      "TabPFN couldn't load: out of memory",
    );
  });

  it("reports TabPFN once it is in use", () => {
    expect(modelSummary({ ...base, model_in_use: "tabpfn", flights: 15 })).toEqual({
      label: "TabPFN",
      detail: "Learning from 15 flights",
      isOn: true,
    });
  });
});
