// `valve(env, {id, label, unit, min, max, value, grid})`: a CONTROL, like `slider`, operated by a stopcock. The student holds the stopcock to run a liquid in (the control's value
// rises one step every moment it is held), or taps it to let out one measure, or presses it from the keyboard. It is built ON `slider` (with snapping), so the labelled range input
// is still on the page, still `data-synapse-control`, and every sweep, provenance and reference check is a slider's. The stopcock is a Kit action button: a real button, at least
// 44 px, with a words-only name; it works by mouse, pen, a finger or the keyboard. The render harness really taps it, holds it, presses it and holds it with a finger, and checks that
// letting go stops the flow. A valve that does nothing is refused (`valve_dead`).

import { event } from "./bridge";
import { contains, hasAttribute, hitAt, layoutAvailable, parentOf, rectOf, style, tagOf } from "./dom";
import { guard } from "./parts";
import type { Environment } from "./environment";
import { quiet } from "./handles";
import { kt } from "./i18n";
import type { Observable } from "./observable";
import { controls, own, ownAttr, registerAction, widgets } from "./provenance";
import { slider } from "./slider";

export interface ValveOptions {
  id: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  value: number;
  /** The number of equal steps from min to max (the control has grid + 1 positions). */
  grid: number;
}

export const MAX_VALVE_STEPS = 40;
const HOLD_MS = 250;
const RUN_MS = 140;
// Taken when the bundle loads, so a page cannot slow, speed or stop the flow by replacing the timers afterwards.
const later = setTimeout;
const every = setInterval;
const stopEvery = clearInterval;
const stopLater = clearTimeout;

export function valve(env: Environment, options: ValveOptions): Observable<number> {
  const id = String(options.id);
  const grid = options.grid;
  if (!Number.isInteger(grid) || grid < 2 || grid > MAX_VALVE_STEPS) throw new RangeError(`valve ${id}: grid is the number of steps, an integer from 2 to ${MAX_VALVE_STEPS}`);
  const { min, max } = options;
  const step = (max - min) / grid;
  const atStart = (options.value - min) / step;
  if (!(Math.abs(atStart - Math.round(atStart)) < 1e-9)) throw new RangeError(`valve ${id}: the starting value must sit on a step (steps of ${step} from ${min})`);
  const value = slider(env, { id, label: options.label, unit: options.unit, min, max, value: options.value, grid, snap: true });
  const record = controls.find((c) => c.id === id);
  if (!record) throw new Error(`valve ${id}: its control was not registered`);
  quiet(record); // the stopcock or the knob is what the student operates; the bar is drawn only with focus (W19)

  const wordsNow = (): string => (running ? kt("stopcockOpen") : value.get() >= max ? kt("stopcockLimit") : kt("stopcockClosed"));
  let running = false;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "syn-valve";
  button.textContent = kt("stopcock");
  button.setAttribute("data-synapse-action", "valve");
  button.setAttribute("data-synapse-valve", id);
  const name = kt("stopcockName");
  button.setAttribute("aria-label", name);
  ownAttr(button, "aria-label", () => name);
  own(button, () => kt("stopcock"));
  registerAction(button, "valve", kt("stopcock"));

  const status = own(document.createElement("span"), () => wordsNow());
  status.className = "syn-sr";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.textContent = wordsNow();

  const surface = document.createElement("div");
  surface.className = "syn-valves";
  surface.append(button, status);

  const say = (): void => {
    status.textContent = wordsNow();
  };
  const bump = (): boolean => {
    const now = value.get();
    if (now >= max - step / 2) return false;
    value.set(Number((now + step).toPrecision(12)));
    event(id, value.get());
    return true;
  };

  value.subscribe(() => say());
  let holdTimer: ReturnType<typeof later> | undefined;
  let runTimer: ReturnType<typeof every> | undefined;
  let held = false;
  let suppressClick = false;
  const halt = (): void => {
    if (holdTimer !== undefined) stopLater(holdTimer);
    if (runTimer !== undefined) stopEvery(runTimer);
    holdTimer = undefined;
    runTimer = undefined;
    running = false;
    button.classList.remove("syn-open");
    say();
  };
  button.addEventListener("pointerdown", (e: PointerEvent) => {
    if (e.button !== undefined && e.button !== 0) return;
    held = false;
    try {
      button.setPointerCapture?.(e.pointerId);
    } catch {
      /* a pointer that cannot be captured still holds by its own events */
    }
    holdTimer = later(() => {
      held = true;
      running = true;
      button.classList.add("syn-open");
      say();
      if (!bump()) halt();
      runTimer = every(() => {
        if (!bump()) halt();
      }, RUN_MS);
    }, HOLD_MS);
  });
  const release = (e: PointerEvent): void => {
    try {
      button.releasePointerCapture?.(e.pointerId);
    } catch {
      /* nothing was captured */
    }
    const wasHeld = held;
    held = false;
    halt();
    if (wasHeld) {
      suppressClick = true; // the click some browsers send after a long press must not add a measure on top of the flow
      later(() => {
        suppressClick = false;
      }, 50);
    }
  };
  button.addEventListener("pointerup", release);
  button.addEventListener("pointercancel", release);
  button.addEventListener("click", (e: MouseEvent) => {
    if (suppressClick) {
      e.preventDefault();
      return;
    }
    bump();
  });
  // Leaving the page's focus while the stopcock is held must not leave the liquid running.
  button.addEventListener("blur", () => {
    if (running) halt();
  });

  // The structural half (also acted on in the student's browser): the stopcock is still the Kit's button, where the Kit put it, not hidden or restyled by attribute.
  const g = guard();
  g.tree(surface);
  g.part(surface);
  g.part(status);
  g.part(button, () => ({ class: running ? "syn-valve syn-open" : "syn-valve" }));
  const check = (): string[] => {
    const out: string[] = [];
    if (parentOf(button) !== surface || parentOf(surface) === null) out.push(`the stopcock for "${id}" was taken apart`);
    if (tagOf(button) !== "button" || hasAttribute(button, "hidden")) out.push(`the stopcock for "${id}" was moved or hidden`);
    if (style(button, "display") === "none" || style(button, "visibility") === "hidden") out.push(`the stopcock for "${id}" is hidden`);
    return out;
  };
  // The layout half (the verifier only): it has a size a finger can press, is drawn, and nothing else lies over it.
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const r = rectOf(button);
    const out: string[] = [];
    if (r.width < 44 || r.height < 44) out.push(`the stopcock for "${id}" is too small to press`);
    if (Number(style(button, "opacity") || "1") < 0.5) out.push(`the stopcock for "${id}" is faded out`);
    const hit = hitAt(r.left + r.width / 2, r.top + r.height / 2);
    if (hit && hit !== button && !contains(button, hit)) out.push(`the stopcock for "${id}" is covered by something else`);
    return out;
  };
  widgets.push({ kind: "valve", id, check, layout, exact: () => g.problems() });

  const wrap = record.el.closest(".syn-control");
  if (wrap?.parentElement) wrap.parentElement.insertBefore(surface, wrap);
  else env.controls.appendChild(surface);
  return value;
}
