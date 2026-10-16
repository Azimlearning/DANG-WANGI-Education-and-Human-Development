// The registration framework for science micro-models (hard constraint 6). A model joins the Kit only if `registrationFailures` is
// empty for its real implementation and NON-empty for every planted physics bug in its test file. A spec states, as data: units and
// domain for every input and parameter, a textbook citation (UNVERIFIED until the corpus exists, P2), reference cases computed by hand,
// and properties checked over a grid. Test-only support code: the bundle imports `model.ts`, not this file.

export interface Quantity {
  unit: string;
  /** Smallest allowed value. */
  min: number;
  /** When true the value must be strictly above `min`. */
  exclusive?: boolean;
}

export interface ReferenceCase {
  args: Record<string, number>;
  expected: number;
  tolerance: number;
  /** How the value was obtained, so the independence of the reference can be audited. */
  derivation: string;
}

export type Property =
  | { kind: "finite" }
  | { kind: "non_negative" }
  | { kind: "increasing"; arg: string }
  | { kind: "decreasing"; arg: string }
  | { kind: "homogeneous"; arg: string; degree: number };

export interface ScienceSpec {
  /** Model id, `<domain>.<name>`. The same id keys the independent Python reference. */
  id: string;
  /** The name it has on `window.Synapse`. */
  exportName: string;
  /** Observable inputs (controls, constants or other models) and numeric parameters, by name. */
  inputs: Record<string, Quantity>;
  params: Record<string, Quantity>;
  output: { unit: string };
  /** The pure function of all inputs and parameters. */
  fn: (args: Record<string, number>) => number;
  /** Where the law comes from. `UNVERIFIED (corpus not loaded until P2)` until a quote is verified. */
  citation: string;
  reference: ReferenceCase[];
  properties: Property[];
  /** Values to sweep for every argument when checking properties. Each list is ascending. */
  grid: Record<string, number[]>;
}

export function domainErrors(spec: ScienceSpec, args: Record<string, number>): string[] {
  const out: string[] = [];
  const all = { ...spec.inputs, ...spec.params };
  for (const [name, q] of Object.entries(all)) {
    const v = args[name];
    if (typeof v !== "number" || Number.isNaN(v) || !Number.isFinite(v)) out.push(`${name} must be a finite number`);
    else if (q.exclusive ? !(v > q.min) : !(v >= q.min)) out.push(`${name} must be ${q.exclusive ? "above" : "at least"} ${q.min} ${q.unit}`);
  }
  return out;
}

/** The spec's function with its domain enforced: this is what the Kit ships. Throws RangeError outside the domain. */
export function guarded(spec: ScienceSpec): (args: Record<string, number>) => number {
  return (args) => {
    const errors = domainErrors(spec, args);
    if (errors.length > 0) throw new RangeError(`${spec.id}: ${errors.join("; ")}`);
    return spec.fn(args);
  };
}

function combos(spec: ScienceSpec): Record<string, number>[] {
  const names = Object.keys({ ...spec.inputs, ...spec.params });
  let acc: Record<string, number>[] = [{}];
  for (const n of names) {
    const values = spec.grid[n];
    if (!values || values.length === 0) throw new Error(`${spec.id}: grid is missing '${n}'`);
    acc = acc.flatMap((a) => values.map((v) => ({ ...a, [n]: v })));
  }
  return acc;
}

export type Impl = (args: Record<string, number>) => number;

export function registrationFailures(spec: ScienceSpec, impl: Impl): string[] {
  const failures: string[] = [];
  const call = (args: Record<string, number>): number | Error => {
    try {
      return impl(args);
    } catch (e) {
      return e instanceof Error ? e : new Error(String(e));
    }
  };

  for (const c of spec.reference) {
    const got = call(c.args);
    if (got instanceof Error) failures.push(`reference (${c.derivation}): threw ${got.message}`);
    else if (!(Math.abs(got - c.expected) <= c.tolerance)) failures.push(`reference (${c.derivation}): got ${got}, expected ${c.expected}`);
  }

  const all = combos(spec);
  for (const p of spec.properties) {
    if (p.kind === "finite" || p.kind === "non_negative") {
      for (const args of all) {
        const v = call(args);
        if (v instanceof Error) failures.push(`property ${p.kind}: ${JSON.stringify(args)} threw ${v.message}`);
        else if (!Number.isFinite(v)) failures.push(`property finite: ${JSON.stringify(args)} gave ${v}`);
        else if (p.kind === "non_negative" && v < 0) failures.push(`property non_negative: ${JSON.stringify(args)} gave ${v}`);
      }
    } else if (p.kind === "increasing" || p.kind === "decreasing") {
      const values = spec.grid[p.arg] ?? [];
      const others = Object.keys({ ...spec.inputs, ...spec.params }).filter((n) => n !== p.arg);
      for (const rest of combos({ ...spec, inputs: Object.fromEntries(Object.entries(spec.inputs).filter(([n]) => n !== p.arg)), params: Object.fromEntries(Object.entries(spec.params).filter(([n]) => n !== p.arg)) })) {
        if (others.some((n) => !(n in rest))) continue;
        let previous: number | null = null;
        for (const v of values) {
          const got = call({ ...rest, [p.arg]: v });
          if (got instanceof Error) {
            failures.push(`property ${p.kind} in ${p.arg}: ${JSON.stringify({ ...rest, [p.arg]: v })} threw ${got.message}`);
            continue;
          }
          const ok = previous === null || (p.kind === "increasing" ? got > previous : got < previous);
          if (!ok) failures.push(`property ${p.kind} in ${p.arg}: ${JSON.stringify({ ...rest, [p.arg]: v })} gave ${got} after ${previous}`);
          previous = got;
        }
      }
    } else if (p.kind === "homogeneous") {
      for (const args of all) {
        const base = call(args);
        const doubled = call({ ...args, [p.arg]: (args[p.arg] as number) * 2 });
        if (base instanceof Error || doubled instanceof Error) continue;
        const want = base * 2 ** p.degree;
        if (!(Math.abs(doubled - want) <= 1e-9 * (1 + Math.abs(want)))) failures.push(`property homogeneous(${p.degree}) in ${p.arg}: ${JSON.stringify(args)}`);
      }
    }
  }

  // Domain refusals: every argument just outside its domain, and NaN, must be refused.
  const base = Object.fromEntries(Object.keys({ ...spec.inputs, ...spec.params }).map((n) => [n, (spec.grid[n] as number[])[Math.floor((spec.grid[n] as number[]).length / 2)] as number]));
  for (const [name, q] of Object.entries({ ...spec.inputs, ...spec.params })) {
    for (const bad of [q.exclusive ? q.min : q.min - 1, Number.NaN]) {
      const got = call({ ...base, [name]: bad });
      if (!(got instanceof Error)) failures.push(`domain: ${name}=${bad} was not refused`);
    }
  }
  return failures;
}
