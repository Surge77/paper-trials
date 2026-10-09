import { createContext, useContext } from "react";

import type { FieldSpec } from "./types";

export const FieldsContext = createContext<FieldSpec[]>([]);

export function useFields(): FieldSpec[] {
  return useContext(FieldsContext);
}
