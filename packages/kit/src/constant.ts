// `constant(value, {label, unit})` declares a fixed quantity (for example a spring's constant). It is recorded with its value so the
// verifier can treat it as backed. A readout fed only by a constant is allowed; a readout fed by an undeclared observable is not.

import { create, type Observable } from "./observable";
import { constants } from "./provenance";

export function constant(value: number, opts: { label: string; unit: string }): Observable<number> {
  const options = { label: String(opts.label), unit: String(opts.unit) };
  if (!Number.isFinite(value)) throw new RangeError(`constant "${options.label}": value must be finite`);
  constants.push({ label: options.label, unit: options.unit, value });
  return create(value, { kind: "constant", id: options.label }, { readOnly: true });
}
