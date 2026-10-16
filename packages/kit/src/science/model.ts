// `model(spec, params, inputs)`: the one way a science micro-model becomes an observable. The result carries a `model` provenance
// node (id, parameters, inputs) and is read-only. Inputs must be Kit observables. Parameters are checked against the spec's domain.

import { create, feed, type Observable } from "../observable";
import { isObservable } from "../provenance";
import { domainErrors, guarded, type ScienceSpec } from "./spec";

export function model(
  spec: ScienceSpec,
  params: Record<string, number>,
  inputs: Record<string, Observable<number>>,
): Observable<number> {
  const wantedInputs = Object.keys(spec.inputs).sort().join(",");
  if (Object.keys(inputs).sort().join(",") !== wantedInputs) throw new TypeError(`${spec.id}: inputs must be exactly {${wantedInputs}}`);
  const wantedParams = Object.keys(spec.params).sort().join(",");
  if (Object.keys(params).sort().join(",") !== wantedParams) throw new TypeError(`${spec.id}: params must be exactly {${wantedParams}}`);
  for (const [name, obs] of Object.entries(inputs)) {
    if (!isObservable(obs)) throw new TypeError(`${spec.id}: input '${name}' must be a Kit observable`);
  }
  const paramErrors = domainErrors({ ...spec, inputs: {} }, params);
  if (paramErrors.length > 0) throw new RangeError(`${spec.id}: ${paramErrors.join("; ")}`);

  const run = guarded(spec);
  const read = () => run({ ...params, ...Object.fromEntries(Object.entries(inputs).map(([n, o]) => [n, o.get()])) });
  const out = create(read(), { kind: "model", id: spec.id, params: { ...params }, inputs }, { readOnly: true });
  for (const obs of Object.values(inputs)) obs.subscribe(() => feed(out, read()));
  return out;
}
