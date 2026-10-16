// `slider(env, {id,label,unit,min,max,value})` adds a labelled range input and returns an observable that clamps to
// [min, max]. Every change is reported to the host as `synapse_event` (control id and value).

import { event } from "./bridge";
import type { Environment } from "./environment";
import { observable, type Observable } from "./observable";

export interface SliderOptions {
  id: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  value: number;
  step?: number;
}

export function slider(env: Environment, options: SliderOptions): Observable<number> {
  const { id, label, unit, min, max } = options;
  if (!(min < max)) throw new RangeError(`slider ${id}: min must be below max`);
  const clamp = (v: number) => (Number.isFinite(v) ? Math.min(max, Math.max(min, v)) : min);
  const value = observable(options.value, { transform: clamp });

  const wrap = document.createElement("div");
  wrap.className = "syn-control";
  const lab = document.createElement("label");
  lab.htmlFor = `syn-${id}`;
  lab.textContent = `${label} (${unit})`;
  const input = document.createElement("input");
  input.type = "range";
  input.id = `syn-${id}`;
  input.min = String(min);
  input.max = String(max);
  input.step = String(options.step ?? (max - min) / 100);
  input.value = String(value.get());
  input.setAttribute("data-synapse-control", id);
  input.addEventListener("input", () => {
    value.set(Number(input.value));
    event(id, value.get());
  });
  value.subscribe((v) => {
    if (Number(input.value) !== v) input.value = String(v);
  });
  wrap.append(lab, input);
  env.controls.appendChild(wrap);
  return value;
}
