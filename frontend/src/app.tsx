import { lazy, Suspense, useCallback } from "react";

import { api } from "./api";
import { StatusBar } from "./components/status-bar";
import { Loading, Notice } from "./components/ui";
import { FieldsContext } from "./fields-context";
import { ExperimentPage } from "./pages/experiment";
import { NotebookPage } from "./pages/notebook";
import { PlanPage } from "./pages/plan";
import { type Route, useRoute } from "./router";
import { useResource } from "./use-resource";

// Charts are most of the bundle, so the lab loads them only when opened.
const LabPage = lazy(() => import("./pages/lab").then((m) => ({ default: m.LabPage })));

function NavLink({ href, isActive, children }: { href: string; isActive: boolean; children: string }) {
  return (
    <a
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={`border-b-2 px-1 py-3 text-sm font-medium ${isActive ? "border-grass text-ink" : "border-transparent text-muted hover:text-ink"}`}
    >
      {children}
    </a>
  );
}

function Page({ route, onDataChange }: { route: Route; onDataChange: () => void }) {
  switch (route.page) {
    case "lab":
      return (
        <Suspense fallback={<Loading />}>
          <LabPage onDataChange={onDataChange} />
        </Suspense>
      );
    case "plan":
      return <PlanPage pick={route.pick} copy={route.copy} onDataChange={onDataChange} />;
    case "experiment":
      return <ExperimentPage key={route.id} id={route.id} onDataChange={onDataChange} />;
    default:
      return <NotebookPage onDataChange={onDataChange} />;
  }
}

export function App() {
  const route = useRoute();
  const [fields] = useResource(api.fields, []);
  const [status, reloadStatus] = useResource(api.status, []);
  const onDataChange = useCallback(() => reloadStatus(), [reloadStatus]);

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 px-4">
          <a href="#/" className="flex items-center gap-2 py-3 font-semibold">
            <img src="/plane.svg" alt="" className="size-5" />
            Paper Trials
          </a>
          <nav className="flex gap-4" aria-label="Main">
            <NavLink href="#/" isActive={route.page === "notebook"}>
              Notebook
            </NavLink>
            <NavLink href="#/lab" isActive={route.page === "lab"}>
              Lab
            </NavLink>
          </nav>
          <div className="ml-auto py-2">{status.status === "ready" && <StatusBar status={status.data} />}</div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        {fields.status === "loading" && <Loading />}
        {fields.status === "error" && <Notice tone="error">{fields.message}</Notice>}
        {fields.status === "ready" && (
          <FieldsContext.Provider value={fields.data}>
            <Page route={route} onDataChange={onDataChange} />
          </FieldsContext.Provider>
        )}
      </main>
    </div>
  );
}
