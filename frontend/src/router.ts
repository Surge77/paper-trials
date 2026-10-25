import { useEffect, useState } from "react";

export type Route =
  | { page: "notebook" }
  | { page: "lab" }
  | { page: "plan"; pick: number | null; copy: number | null }
  | { page: "experiment"; id: number };

function toInt(value: string | null): number | null {
  if (value === null || !/^\d+$/.test(value)) return null;
  return Number(value);
}

export function parseRoute(hash: string): Route {
  const [path = "", query = ""] = hash.replace(/^#/, "").split("?");
  const params = new URLSearchParams(query);
  const experiment = /^\/experiments\/(\d+)$/.exec(path);
  if (experiment?.[1]) return { page: "experiment", id: Number(experiment[1]) };
  if (path === "/lab") return { page: "lab" };
  if (path === "/plan") return { page: "plan", pick: toInt(params.get("pick")), copy: toInt(params.get("copy")) };
  return { page: "notebook" };
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => {
      setRoute(parseRoute(window.location.hash));
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function navigate(hash: string): void {
  window.location.hash = hash;
}
