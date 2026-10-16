// `readout(env, {label, unit, value})` shows a number that is always an observable's current value. It THROWS unless
// `value` is an observable, so a result cannot be typed in by hand (A-2; the structural check for hand-written numbers
// arrives with L1 in P1).

import type { Environment } from "./environment";
import { isObservable, type Observable } from "./observable";

export interface ReadoutOptions {
  label: string;
  unit: string;
  value: Observable<number>;
  digits?: number;
}

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
