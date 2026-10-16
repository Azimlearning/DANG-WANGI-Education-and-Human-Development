// `slider(env, {id,label,unit,min,max,value})` adds a labelled range input and returns a CONTROL observable that clamps to
// [min, max]. Its provenance node records the range and grid so the verifier can sweep it and knows which numbers are backed.
// Every change is reported to the host as `synapse_event` (control id and value).

import { event } from "./bridge";
import type { Environment } from "./environment";
import { create, type Observable } from "./observable";
import { controls, copy, own } from "./provenance";

export interface SliderOptions {
  id: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  value: number;
  /** Input step. Defaults to one grid interval. */
  step?: number;
  /** Number of equal intervals the verifier tests across [min, max] (so grid + 1 positions). Default 10. */
  grid?: number;
}

export function slider(env: Environment, options: SliderOptions): Observable<number> {
  const { id, label, unit, min, max } = options;
  if (!(min < max)) throw new RangeError(`slider ${id}: min must be below max`);
  if (controls.some((c) => c.id === id)) throw new RangeError(`slider ${id}: id already used`);
  const grid = options.grid ?? 10;
  if (!Number.isInteger(grid) || grid < 1 || grid > 200) throw new RangeError(`slider ${id}: grid must be an integer from 1 to 200`);
  const clamp = (v: number) => (Number.isFinite(v) ? Math.min(max, Math.max(min, v)) : min);
  const initial = clamp(options.value);
  const value = create(initial, { kind: "control", id, min, max, grid, default: initial }, { transform: clamp });

  const wrap = document.createElement("div");
  wrap.className = "syn-control";
  const lab = own(document.createElement("label"), () => `${label} (${unit})`);
  lab.htmlFor = `syn-${id}`;
  lab.textContent = `${label} (${unit})`;
  copy.push(label, unit);
  const input = document.createElement("input");
  input.type = "range";
  input.id = `syn-${id}`;
  input.min = String(min);
  input.max = String(max);
  input.step = String(options.step ?? (max - min) / grid);
  input.value = String(value.get());
  input.setAttribute("data-synapse-control", id);
  const describe = (v: number) => input.setAttribute("aria-valuetext", `${v} ${unit}`);
  describe(value.get());
  input.addEventListener("input", () => {
    value.set(Number(input.value));
    event(id, value.get());
  });
  value.subscribe((v) => {
    if (Number(input.value) !== v) input.value = String(v);
    describe(v);
  });
  wrap.append(lab, input);
  env.controls.appendChild(wrap);
  controls.push({ id, label, unit, min, max, grid, default: initial, obs: value, el: input });
  return value;
}
