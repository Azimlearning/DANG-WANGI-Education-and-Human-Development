// `readout(env, {label, unit, value})` shows a number that is always an observable's current value. It THROWS unless `value` is an
// observable. This stops accidents only: a constant can be wrapped in an observable, and provenance is checked by L1 in P1 (A-2).

import type { Environment } from "./environment";
import { isObservable, type Observable } from "./observable";

export interface ReadoutOptions {
  label: string;
  unit: string;
  value: Observable<number>;
  digits?: number;
}

let labelCounter = 0;

export function readout(env: Environment, options: ReadoutOptions): HTMLOutputElement {
  if (!isObservable(options.value)) {
    throw new TypeError(`readout "${options.label}": value must be an observable, not a plain ${typeof options.value}`);
  }
  const digits = options.digits ?? 2;
  const wrap = document.createElement("div");
  wrap.className = "syn-readout";
  const lab = document.createElement("span");
  lab.textContent = options.label;
  const out = document.createElement("output");
  const labelId = `syn-readout-${labelCounter++}`;
  lab.id = labelId;
  out.setAttribute("aria-labelledby", labelId);
  out.setAttribute("data-synapse-readout", options.label);
  out.setAttribute("aria-live", "polite");
  const render = (v: number) => {
    out.textContent = `${v.toFixed(digits)} ${options.unit}`;
  };
  render(options.value.get());
  options.value.subscribe(render);
  wrap.append(lab, out);
  env.readouts.appendChild(wrap);
  return out;
}
