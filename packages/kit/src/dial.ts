// `dial(env, {id, label, unit, min, max, value, grid})`: a CONTROL, like `slider`, turned like a knob. The student drags round the knob (mouse, pen or a finger) and the control's value
// follows the angle of the pointer, from the first mark at the lower left to the last at the lower right. It is built ON `slider` (with snapping), so the labelled range input is still on
// the page, still `data-synapse-control`, and every sweep, provenance and reference check is a slider's. That range input is also the keyboard and screen-reader path (arrow keys, Home
// and End, announced with its value), so the knob itself is a pointer surface and is hidden from assistive technology rather than being a second, redundant control. The render harness
// really turns the knob by mouse and by finger, and really presses the arrow keys on the range input, and refuses a dial that does not follow (`dial_dead`).

import { event } from "./bridge";
import { contains, hitAt, layoutAvailable, parentOf, rectOf, style } from "./dom";
import type { Environment } from "./environment";
import type { Observable } from "./observable";
import { guard } from "./parts";
import { controls, markOwnStyle, widgets } from "./provenance";
import { slider } from "./slider";

export interface DialOptions {
  id: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  value: number;
  /** The number of equal steps from min to max (the control has grid + 1 positions). */
  grid: number;
}

export const MAX_DIAL_STEPS = 40;
/** The knob turns this far either side of straight up, so the whole sweep is 270 degrees and the gap is at the bottom. */
export const SWEEP = 135;

export function dial(env: Environment, options: DialOptions): Observable<number> {
  const id = String(options.id);
  const grid = options.grid;
  if (!Number.isInteger(grid) || grid < 2 || grid > MAX_DIAL_STEPS) throw new RangeError(`dial ${id}: grid is the number of steps, an integer from 2 to ${MAX_DIAL_STEPS}`);
  const { min, max } = options;
  const step = (max - min) / grid;
  const atStart = (options.value - min) / step;
  if (!(Math.abs(atStart - Math.round(atStart)) < 1e-9)) throw new RangeError(`dial ${id}: the starting value must sit on a step (steps of ${step} from ${min})`);
  const value = slider(env, { id, label: options.label, unit: options.unit, min, max, value: options.value, grid, snap: true });
  const record = controls.find((c) => c.id === id);
  if (!record) throw new Error(`dial ${id}: its control was not registered`);

  const fraction = (): number => Math.min(1, Math.max(0, (value.get() - min) / (max - min)));
  const angle = (): number => -SWEEP + fraction() * 2 * SWEEP;
  const turn = (): string => `transform:rotate(${angle().toFixed(2)}deg)`;

  const surface = document.createElement("div");
  surface.className = "syn-dials";
  const knob = document.createElement("div");
  knob.className = "syn-dial";
  knob.setAttribute("data-synapse-dial", id);
  knob.setAttribute("aria-hidden", "true"); // the range input is the accessible control; this is the pointer surface for it
  const mark = document.createElement("div");
  mark.className = "syn-dial-mark";
  knob.appendChild(mark);
  surface.appendChild(knob);
  markOwnStyle(mark);
  const draw = (): void => mark.setAttribute("style", turn());
  value.subscribe(draw);
  draw();

  let turning = false;
  const toFraction = (clientX: number, clientY: number): number => {
    const r = knob.getBoundingClientRect(); // the student's own pointer, so the element's own method; the audit's reads go through the captured one
    const dx = clientX - (r.left + r.width / 2);
    const dy = clientY - (r.top + r.height / 2);
    if (dx === 0 && dy === 0) return fraction();
    const degrees = (Math.atan2(dx, -dy) * 180) / Math.PI; // clockwise from straight up, in (-180, 180]
    if (Math.abs(degrees) > SWEEP) return degrees < 0 ? 0 : 1; // the gap at the bottom belongs to whichever end the pointer is nearer
    return (degrees + SWEEP) / (2 * SWEEP);
  };
  const follow = (e: PointerEvent): void => {
    const f = toFraction(e.clientX, e.clientY);
    if (!Number.isFinite(f)) return;
    value.set(min + f * (max - min));
    event(id, value.get());
  };
  knob.addEventListener("pointerdown", (e: PointerEvent) => {
    if (e.button !== undefined && e.button !== 0) return;
    turning = true;
    try {
      knob.setPointerCapture?.(e.pointerId);
    } catch {
      /* a pointer that cannot be captured still turns by its move events */
    }
    follow(e);
  });
  knob.addEventListener("pointermove", (e: PointerEvent) => {
    if (turning) follow(e);
  });
  const release = (e: PointerEvent): void => {
    if (!turning) return;
    turning = false;
    try {
      knob.releasePointerCapture?.(e.pointerId);
    } catch {
      /* nothing was captured */
    }
  };
  knob.addEventListener("pointerup", release);
  knob.addEventListener("pointercancel", release);

  const g = guard();
  g.part(surface);
  g.part(knob);
  g.part(mark, () => ({ style: turn() }));
  g.tree(surface);
  const check = (): string[] => {
    const out: string[] = [];
    if (parentOf(knob) !== surface || parentOf(surface) === null) out.push(`the dial for "${id}" was taken apart`);
    if (style(knob, "display") === "none" || style(knob, "visibility") === "hidden") out.push(`the dial for "${id}" is hidden`);
    return out;
  };
  // The layout half (the verifier only): the knob is big enough for a finger, drawn, not covered, and its mark points where the value says.
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const r = rectOf(knob);
    const out: string[] = [];
    if (r.width < 44 || r.height < 44) out.push(`the dial for "${id}" is too small to turn`);
    if (Number(style(knob, "opacity") || "1") < 0.5) out.push(`the dial for "${id}" is faded out`);
    const hit = hitAt(r.left + r.width / 2, r.top + r.height / 2);
    if (hit && hit !== knob && !contains(knob, hit)) out.push(`the dial for "${id}" is covered by something else`);
    return out;
  };
  widgets.push({ kind: "dial", id, check, layout, exact: () => g.problems() });

  const wrap = record.el.closest(".syn-control");
  if (wrap?.parentElement) wrap.parentElement.insertBefore(surface, wrap);
  else env.controls.appendChild(surface);
  return value;
}
