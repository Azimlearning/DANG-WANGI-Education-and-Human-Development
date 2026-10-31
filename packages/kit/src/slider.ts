// `slider(env, {id,label,unit,min,max,value})` adds a labelled range input and returns a CONTROL observable that clamps to
// [min, max]. Its provenance node records the range and grid so the verifier can sweep it and knows which numbers are backed.
// Every change is reported to the host as `synapse_event` (control id and value).

import { event } from "./bridge";
import type { Environment } from "./environment";
import { create, type Observable } from "./observable";
import { controls, copy, own, ownAttr } from "./provenance";

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
  /** Snap every value the control takes (typed, set by a script, or dragged) to the nearest step from `min`. For a control that only has whole positions, such as a count of masses. */
  snap?: boolean;
  /** A choice control (W18): one word per whole step from `min` (grid + 1 words), said and shown instead of the number and unit. Implies snap. */
  words?: readonly string[];
}

export function slider(env: Environment, options: SliderOptions): Observable<number> {
  const id = String(options.id);
  const label = String(options.label);
  const unit = String(options.unit);
  const { min, max } = options;
  if (!(min < max)) throw new RangeError(`slider ${id}: min must be below max`);
  if (controls.some((c) => c.id === id)) throw new RangeError(`slider ${id}: id already used`);
  const grid = options.grid ?? 10;
  if (!Number.isInteger(grid) || grid < 1 || grid > 200) throw new RangeError(`slider ${id}: grid must be an integer from 1 to 200`);
  // (max - min) / grid is often a binary-float smear (0.9500000000000001) or a repeating decimal (2.6666...), and min + grid x step must not lie above
  // max or the browser's range input cannot reach max. Twelve significant digits, rounded DOWN one unit in the last place if it would overshoot.
  const words = options.words ? options.words.map(String) : undefined;
  if (words && words.length !== grid + 1) throw new RangeError(`slider ${id}: words needs one word per step (${grid + 1})`);
  const raw = (max - min) / grid;
  let tidy = Number(raw.toPrecision(12));
  if (tidy * grid > (max - min) * (1 + 1e-13)) tidy = Number((tidy - 10 ** (Math.floor(Math.log10(tidy)) - 11)).toPrecision(12));
  const stepSize = options.step ?? tidy;
  const clamp = (v: number) => (Number.isFinite(v) ? Math.min(max, Math.max(min, v)) : min);
  const fit = options.snap || words ? (v: number) => clamp(Number((min + Math.round((clamp(v) - min) / stepSize) * stepSize).toPrecision(12))) : clamp;
  const initial = fit(options.value);
  const value = create(initial, { kind: "control", id, min, max, grid, default: initial }, { transform: fit });

  const wrap = document.createElement("div");
  wrap.className = "syn-control";
  const heading = words ? label : `${label} (${unit})`;
  const lab = own(document.createElement("label"), () => heading);
  lab.htmlFor = `syn-${id}`;
  lab.textContent = heading;
  copy.push(label, unit, ...(words ?? []));
  const input = document.createElement("input");
  input.type = "range";
  input.id = `syn-${id}`;
  input.min = String(min);
  input.max = String(max);
  input.step = String(stepSize);
  input.value = String(value.get());
  input.setAttribute("data-synapse-control", id);
  const spoken = (v: number): string => (words ? (words[Math.round((v - min) / stepSize)] ?? `${v} ${unit}`) : `${v} ${unit}`);
  const describe = (v: number) => input.setAttribute("aria-valuetext", spoken(v));
  describe(value.get());
  ownAttr(input, "aria-valuetext", () => spoken(value.get()));
  input.addEventListener("input", () => {
    value.set(Number(input.value));
    event(id, value.get());
  });
  // The value in words beside the name (W18): when the drawing is what the student drags and the bar is drawn only with focus, the card still says where the control is.
  const shown = (v: number): string => (words ? spoken(v) : `${v} ${unit}`);
  const valueText = own(document.createElement("span"), () => shown(value.get()));
  valueText.className = "syn-control-value";
  valueText.setAttribute("aria-hidden", "true");
  valueText.textContent = shown(value.get());
  value.subscribe((v) => {
    if (Number(input.value) !== v) input.value = String(v);
    describe(v);
    valueText.textContent = shown(v);
  });
  const head = document.createElement("div");
  head.className = "syn-control-head";
  head.append(lab, valueText);
  wrap.append(head, input);
  env.controls.appendChild(wrap);
  controls.push({ id, label, unit, min, max, grid, default: initial, step: Number(input.step), obs: value, el: input, ...(words ? { words } : {}) });
  return value;
}
