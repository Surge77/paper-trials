import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "./api";

export type Resource<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

/** Loads `load()` on mount and whenever `reload` is called. Ignores results after unmount. */
export function useResource<T>(load: () => Promise<T>, deps: unknown[]): [Resource<T>, () => void] {
  const [state, setState] = useState<Resource<T>>({ status: "loading" });
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let isActive = true;
    load().then(
      (data) => isActive && setState({ status: "ready", data }),
      (error: unknown) => isActive && setState({ status: "error", message: errorMessage(error) }),
    );
    return () => {
      isActive = false;
    };
    // `load` is a fresh closure every render; callers list what it really depends on in `deps`.
  }, [...deps, version]);

  return [state, reload];
}
