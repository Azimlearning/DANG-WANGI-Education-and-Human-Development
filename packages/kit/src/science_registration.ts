// The registration suite for science micro-models (hard constraint 6): an independent hand-written reference, properties over a
// grid, and domain refusals. A model joins the Kit only if `registrationFailures` is empty for the real implementation and
// NON-empty for every planted physics bug (see science_registration.test.ts). Test-only: not imported by the bundle.

export interface ReferenceCase {
  inputs: { k: number; load: number };
  expected: number;
  tolerance: number;
  /** How the value was obtained, so the independence of the reference can be audited. */
  derivation: string;
}

export type HookesFn = (load: number, k: number) => number;

/**
 * Hand-computed from F = k x rearranged as x = F / k, one line of arithmetic each. They were NOT derived by running the
 * implementation. They are still the author's own arithmetic, not a textbook worked example: the textbook citation is
 * UNVERIFIED until the corpus exists (P2), so these cases show internal consistency, not agreement with the syllabus.
 */
export const HOOKES_REFERENCE: ReferenceCase[] = [
  { inputs: { k: 50, load: 10 }, expected: 0.2, tolerance: 1e-12, derivation: "10 N over 50 N/m = 0.2 m" },
  { inputs: { k: 50, load: 2 }, expected: 0.04, tolerance: 1e-12, derivation: "2 N over 50 N/m = 0.04 m" },
  { inputs: { k: 20, load: 4 }, expected: 0.2, tolerance: 1e-12, derivation: "4 N over 20 N/m = 0.2 m" },
  { inputs: { k: 100, load: 0 }, expected: 0, tolerance: 1e-12, derivation: "no load, no extension" },
  { inputs: { k: 250, load: 5 }, expected: 0.02, tolerance: 1e-12, derivation: "5 N over 250 N/m = 0.02 m" },
  { inputs: { k: 0.5, load: 1 }, expected: 2, tolerance: 1e-12, derivation: "1 N over 0.5 N/m = 2 m (a very soft spring)" },
];

const KS = [1, 10, 50, 200];
const LOADS = Array.from({ length: 21 }, (_, i) => i * 0.5); // 0 to 10 N

export function registrationFailures(fn: HookesFn): string[] {
  const failures: string[] = [];

  for (const c of HOOKES_REFERENCE) {
    let got: number;
    try {
      got = fn(c.inputs.load, c.inputs.k);
    } catch (e) {
      failures.push(`reference ${c.derivation}: threw ${String(e)}`);
      continue;
    }
    if (!(Math.abs(got - c.expected) <= c.tolerance)) failures.push(`reference ${c.derivation}: got ${got}`);
  }

  for (const k of KS) {
    let previous = -Infinity;
    for (const load of LOADS) {
      let x: number;
      try {
        x = fn(load, k);
      } catch (e) {
        failures.push(`property finite: k=${k} load=${load} threw ${String(e)}`);
        continue;
      }
      if (!Number.isFinite(x)) failures.push(`property finite: k=${k} load=${load} gave ${x}`);
      if (x < 0) failures.push(`property non_negative: k=${k} load=${load} gave ${x}`);
      if (!(x > previous)) failures.push(`property strictly_increasing_in_load: k=${k} load=${load} gave ${x} after ${previous}`);
      previous = x;
      if (load > 0 && Math.abs(fn(2 * load, k) - 2 * x) > 1e-9 * (1 + Math.abs(x))) {
        failures.push(`property linear_in_load: k=${k} load=${load}`);
      }
    }
  }
  for (const load of [1, 5, 10]) {
    let previous = Infinity;
    for (const k of KS) {
      const x = fn(load, k);
      if (!(x < previous)) failures.push(`property decreasing_in_k: load=${load} k=${k} gave ${x} after ${previous}`);
      previous = x;
    }
  }

  for (const [load, k] of [[1, 0], [1, -5], [-1, 10], [Number.NaN, 10], [1, Number.NaN]] as const) {
    let threw = false;
    try {
      fn(load, k);
    } catch {
      threw = true;
    }
    if (!threw) failures.push(`domain: load=${load} k=${k} was not refused`);
  }
  return failures;
}
