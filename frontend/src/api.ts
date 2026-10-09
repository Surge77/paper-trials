import type {
  Experiment,
  ExperimentInput,
  FieldSpec,
  FlightInput,
  Insights,
  Recommendation,
  Status,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

// FastAPI returns {"detail": "..."} for HTTPException and a list of issues for validation errors.
function detailMessage(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null || !("detail" in body)) return fallback;
  const { detail } = body as { detail: unknown };
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "object" && d !== null && "msg" in d ? String(d.msg) : String(d)))
      .join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(detailMessage(body, `Request failed (${response.status})`), response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function sendJson<T>(method: string, path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  fields: () => request<FieldSpec[]>("/fields"),
  status: () => request<Status>("/status"),
  experiments: () => request<Experiment[]>("/experiments"),
  experiment: (id: number) => request<Experiment>(`/experiments/${id}`),
  recommendation: () => request<Recommendation>("/recommendation"),
  insights: () => request<Insights>("/insights"),
  createExperiment: ({ design, parent_id, changed_field }: ExperimentInput) =>
    sendJson<Experiment>("POST", "/experiments", { ...design, parent_id, changed_field }),
  deleteExperiment: (id: number) => request<void>(`/experiments/${id}`, { method: "DELETE" }),
  addFlights: (id: number, flights: FlightInput[]) =>
    sendJson<Experiment>("POST", `/experiments/${id}/flights`, { flights }),
  checkPhoto: (id: number, photo: File) => {
    const form = new FormData();
    form.append("photo", photo);
    return request<Experiment>(`/experiments/${id}/photo`, { method: "POST", body: form });
  },
  loadDemo: () => request<{ loaded: number }>("/demo", { method: "POST" }),
  clearDemo: () => request<{ removed: number }>("/demo", { method: "DELETE" }),
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "Can't reach the Paper Trials server. Is it running?";
  return error instanceof Error ? error.message : "Something went wrong";
}
