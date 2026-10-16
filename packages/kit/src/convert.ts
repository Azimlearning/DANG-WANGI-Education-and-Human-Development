// `convert(obs, from, to)`: the one kind of arithmetic generated code may do on a model's output, a unit change by a known factor.
// Any other arithmetic (`obs.map(fn)`) is recorded as user-written and refused by the verifier.

import { create, feed, type Observable } from "./observable";
import { isObservable } from "./provenance";

const UNITS: Record<string, { dim: string; toSI: number }> = {
  m: { dim: "length", toSI: 1 },
  cm: { dim: "length", toSI: 0.01 },
  mm: { dim: "length", toSI: 0.001 },
  km: { dim: "length", toSI: 1000 },
  kg: { dim: "mass", toSI: 1 },
  g: { dim: "mass", toSI: 0.001 },
  s: { dim: "time", toSI: 1 },
  ms: { dim: "time", toSI: 0.001 },
  min: { dim: "time", toSI: 60 },
  Pa: { dim: "pressure", toSI: 1 },
  kPa: { dim: "pressure", toSI: 1000 },
  A: { dim: "current", toSI: 1 },
  mA: { dim: "current", toSI: 0.001 },
  J: { dim: "energy", toSI: 1 },
  kJ: { dim: "energy", toSI: 1000 },
  N: { dim: "force", toSI: 1 },
  V: { dim: "voltage", toSI: 1 },
  mV: { dim: "voltage", toSI: 0.001 },
  W: { dim: "power", toSI: 1 },
};

export function convert(source: Observable<number>, from: string, to: string): Observable<number> {
  if (!isObservable(source)) throw new TypeError("convert: source must be a Kit observable");
  const a = UNITS[from];
  const b = UNITS[to];
  if (!a || !b) throw new RangeError(`convert: unknown unit ${!a ? from : to}`);
  if (a.dim !== b.dim) throw new RangeError(`convert: ${from} (${a.dim}) cannot become ${to} (${b.dim})`);
  const factor = a.toSI / b.toSI;
  const out = create(source.get() * factor, { kind: "convert", from, to, factor, inputs: { x: source } }, { readOnly: true });
  source.subscribe((v) => feed(out, v * factor));
  return out;
}
