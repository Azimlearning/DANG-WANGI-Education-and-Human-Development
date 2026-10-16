// A tiny closed-form science micro-model: Hooke's law, extension = load / k. This is P0's one science component.
// Its citation is explicitly UNVERIFIED: the corpus is not loaded until P2, so nothing built on it can be `kit-verified`
// (hard constraint 4).

import type { Observable } from "./observable";

export interface HookesOptions {
  /** Spring constant in N/m. Must be above 0. */
  k: number;
  /** Load in newtons, 0 or more. */
  load: Observable<number>;
}

/** Extension in metres for a load in newtons, within the elastic limit. */
export function hookesExtension(load: number, k: number): number {
  if (!(k > 0)) throw new RangeError("hookes: k must be above 0 N/m");
  if (!(load >= 0)) throw new RangeError("hookes: load must be 0 N or more");
  return load / k;
}

export function hookes(options: HookesOptions): Observable<number> {
  const { k, load } = options;
  if (!(k > 0)) throw new RangeError("hookes: k must be above 0 N/m");
  // A derived, read-only observable: the extension always follows the load.
  return load.map((n) => hookesExtension(Math.max(n, 0), k));
}
