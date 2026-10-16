// `readout(env, {label, unit, value})` shows a number that is always a Kit observable's current value, formatted by the Kit. It
// THROWS unless `value` is an observable this bundle created. The element is registered as owned with its expected text, so the L1
// audit detects any overwrite of it, and the audit reads the observable's provenance to decide whether the number is grounded.

import type { Environment } from "./environment";
import type { Observable } from "./observable";
import { copy, isObservable, own, readouts } from "./provenance";

export interface ReadoutOptions {
  label: string;
  unit: string;
  value: Observable<number>;
  digits?: number;
}

let labelCounter = 0;

export function readout(env: Environment, opts: ReadoutOptions): HTMLOutputElement {
  if (!isObservable(opts.value)) {
    throw new TypeError(`readout "${opts.label}": value must be a Kit observable, not ${typeof opts.value}`);
  }
  // Copy the strings now: the caller keeps its options object and could change it after the Kit has recorded what to expect.
  const options = { label: String(opts.label), unit: String(opts.unit), value: opts.value, digits: opts.digits };
  const digits = options.digits ?? 2;
  if (!Number.isInteger(digits) || digits < 0 || digits > 8) throw new RangeError(`readout "${options.label}": digits must be 0 to 8`);
  const obs = options.value;
  const format = () => `${obs.get().toFixed(digits)} ${options.unit}`;
  const wrap = document.createElement("div");
  wrap.className = "syn-readout";
  const lab = own(document.createElement("span"), () => options.label);
  lab.textContent = options.label;
  copy.push(options.label, options.unit);
  const out = own(document.createElement("output"), format);
  const labelId = `syn-readout-${labelCounter++}`;
  lab.id = labelId;
  out.setAttribute("aria-labelledby", labelId);
  out.setAttribute("data-synapse-readout", options.label);
  out.setAttribute("aria-live", "polite");
  out.textContent = format();
  obs.subscribe(() => {
    out.textContent = format();
  });
  wrap.append(lab, out);
  env.readouts.appendChild(wrap);
  readouts.push({ label: options.label, unit: options.unit, digits, obs, el: out });
  return out;
}
