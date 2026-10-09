import type { ReactNode } from "react";

import type { Status } from "../types";

function Pill({ isOn, children, title }: { isOn: boolean; children: ReactNode; title: string }) {
  return (
    <span title={title} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-2.5 py-1 text-xs">
      <span className={`size-1.5 rounded-full ${isOn ? "bg-grass" : "bg-gray-300"}`} aria-hidden="true" />
      {children}
    </span>
  );
}

export function modelSummary(status: Status): { label: string; detail: string; isOn: boolean } {
  if (status.model_in_use === "tabpfn") {
    return { label: "TabPFN", detail: `Learning from ${status.flights} flights`, isOn: true };
  }
  if (!status.tabpfn_enabled) {
    return { label: "Baseline", detail: "TabPFN is switched off in settings", isOn: false };
  }
  if (status.tabpfn_error) {
    return { label: "Baseline", detail: `TabPFN couldn't load: ${status.tabpfn_error}`, isOn: false };
  }
  const flightsLeft = Math.max(status.flights_needed_for_tabpfn - status.flights, 0);
  const experimentsLeft = Math.max(status.experiments_needed_for_tabpfn - status.flown_experiments, 0);
  const parts = [
    experimentsLeft > 0 ? `${experimentsLeft} more plane${experimentsLeft === 1 ? "" : "s"}` : null,
    flightsLeft > 0 ? `${flightsLeft} more flight${flightsLeft === 1 ? "" : "s"}` : null,
  ].filter(Boolean);
  return { label: "Baseline", detail: `TabPFN takes over after ${parts.join(" and ")}`, isOn: false };
}

export function StatusBar({ status }: { status: Status }) {
  const model = modelSummary(status);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Pill isOn={model.isOn} title={model.detail}>
        Predictions: {model.label}
      </Pill>
      <Pill
        isOn={status.gemma_available}
        title={status.gemma_available ? `${status.gemma_model} via Ollama` : "Ollama isn't running, using plain fallbacks"}
      >
        Gemma {status.gemma_available ? "on" : "off"}
      </Pill>
    </div>
  );
}
