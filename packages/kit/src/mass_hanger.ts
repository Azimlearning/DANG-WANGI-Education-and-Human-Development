// `massHanger(env, {id, label, unit, min, max, value, grid})`: a CONTROL, like `slider`, with a different surface. The student drags masses from a tray onto a hanger
// (or presses a mass to move it: Enter, Space or a tap), and the control's value is min plus one step per hung mass. It is built ON `slider`: the same labelled range input
// is still on the page, still declared `data-synapse-control`, still announced with its value, so the control's provenance node, its sweep to the grid and extremes, and
// every L1 and L3 check are exactly those of a slider. The masses are a skin that keeps in step with that control in both directions: moving the range input moves the
// masses, moving a mass moves the range input.
//
// The masses are Kit action buttons (registered, so the audit proves the Kit made them and the harness knows they are not undeclared controls). They are real buttons, so the
// keyboard and screen-reader path needs no pointer, and each is at least 44 px. A drag is pointer events with the pointer captured, so mouse, pen and touch all work. The render
// harness really drags a mass onto the hanger and off it, and presses one from the keyboard, and refuses a page whose masses do nothing (`drag_dead`).
//
// A mass is named by a letter, never a number, so the labels hold nothing for the audit to ground.

import { event } from "./bridge";
import { attr, contains, effectiveOpacity, hasAttribute, hitAt, layoutAvailable, parentOf, rectOf, style, tagOf } from "./dom";
import type { Environment } from "./environment";
import type { Observable } from "./observable";
import { controls, markOwnStyle, own, ownAttr, registerAction, widgets } from "./provenance";
import { slider } from "./slider";

export interface MassHangerOptions {
  id: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  value: number;
  /** The number of masses: the control has this many equal steps between min and max. */
  grid: number;
}

export const MAX_MASSES = 8;
const LETTERS = "ABCDEFGH";
const WORDS = ["no masses", "one mass", "two masses", "three masses", "four masses", "five masses", "six masses", "seven masses", "eight masses"];
const DRAG_THRESHOLD = 6;

function div(className: string): HTMLDivElement {
  const el = document.createElement("div");
  el.className = className;
  return el;
}

function caption(text: string): HTMLSpanElement {
  const el = own(document.createElement("span"), () => text);
  el.className = "syn-cap";
  el.textContent = text;
  return el;
}

export function massHanger(env: Environment, options: MassHangerOptions): Observable<number> {
  const id = String(options.id);
  const grid = options.grid;
  if (!Number.isInteger(grid) || grid < 2 || grid > MAX_MASSES) throw new RangeError(`massHanger ${id}: grid is the number of masses, an integer from 2 to ${MAX_MASSES}`);
  const { min, max } = options;
  const step = (max - min) / grid;
  const atStart = (options.value - min) / step;
  if (!(Math.abs(atStart - Math.round(atStart)) < 1e-9)) throw new RangeError(`massHanger ${id}: the starting value must be a whole number of masses (steps of ${step} from ${min})`);
  // snap: a value a script sets is moved to the nearest whole number of masses, so the masses and the control can never disagree about a half mass.
  const value = slider(env, { id, label: options.label, unit: options.unit, min, max, value: options.value, grid, snap: true });
  const record = controls.find((c) => c.id === id);
  if (!record) throw new Error(`massHanger ${id}: its control was not registered`);
  const countOf = (v: number) => Math.max(0, Math.min(grid, Math.round((v - min) / step)));

  // Which masses are on the hanger. The control's value is derived from how many.
  const hung = new Set<number>();
  for (let i = 0; i < countOf(value.get()); i++) hung.add(i);

  const surface = div("syn-masses");
  surface.setAttribute("role", "group");
  const groupLabel = `${String(options.label)}: masses to hang`;
  surface.setAttribute("aria-label", groupLabel);
  ownAttr(surface, "aria-label", () => groupLabel);
  const tray = div("syn-tray");
  tray.setAttribute("role", "group");
  tray.setAttribute("aria-label", "Masses in the tray");
  tray.setAttribute("data-synapse-tray", id);
  const hanger = div("syn-hanger");
  hanger.setAttribute("role", "group");
  hanger.setAttribute("data-synapse-dropzone", id);
  const hangerName = () => `Hanger, holding ${WORDS[hung.size]}`;
  ownAttr(hanger, "aria-label", hangerName);
  // A screen reader hears the hanger's contents change here, since a label that changes on a button is not announced.
  const status = own(document.createElement("span"), () => hangerName());
  status.className = "syn-sr";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.textContent = hangerName();
  const trayCap = caption("Tray");
  const hangerCap = caption("Hanger");

  const tokens: HTMLButtonElement[] = [];
  const nameOf = (i: number) => `Mass ${LETTERS[i]}, ${hung.has(i) ? "on the hanger" : "in the tray"}. Press Enter to move it.`;
  for (let i = 0; i < grid; i++) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "syn-mass";
    b.textContent = LETTERS[i] as string;
    b.setAttribute("data-synapse-action", "drag");
    b.setAttribute("data-synapse-drag", id);
    ownAttr(b, "aria-label", () => nameOf(i));
    registerAction(b, "drag", `Mass ${LETTERS[i]}`);
    markOwnStyle(b);
    tokens.push(b);
  }

  const render = (focus?: HTMLElement | null): void => {
    tray.replaceChildren(trayCap, ...tokens.filter((_, i) => !hung.has(i)));
    hanger.replaceChildren(hangerCap, ...tokens.filter((_, i) => hung.has(i)));
    tokens.forEach((b, i) => {
      b.setAttribute("aria-label", nameOf(i));
      b.dataset.state = hung.has(i) ? "hung" : "tray";
    });
    hanger.setAttribute("aria-label", hangerName());
    status.textContent = hangerName();
    focus?.focus();
  };

  const commit = (): void => {
    value.set(Number((min + hung.size * step).toPrecision(12)));
    event(id, value.get());
  };
  const toggle = (i: number): void => {
    if (hung.has(i)) hung.delete(i);
    else hung.add(i);
    commit();
    render(tokens[i]);
  };
  const adjustTo = (n: number): void => {
    while (hung.size < n) hung.add(tokens.findIndex((_, k) => !hung.has(k)));
    while (hung.size > n) hung.delete(Math.max(...hung));
  };
  const inside = (x: number, y: number): boolean => {
    const r = hanger.getBoundingClientRect();
    return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
  };

  let dragsInFlight = 0;
  tokens.forEach((b, i) => {
    let start: { x: number; y: number } | null = null;
    let dragging = false;
    let suppressClick = false;
    b.addEventListener("pointerdown", (e: PointerEvent) => {
      if (e.button !== undefined && e.button !== 0) return;
      start = { x: e.clientX, y: e.clientY };
      dragging = false;
      try {
        b.setPointerCapture?.(e.pointerId);
      } catch {
        /* a pointer that cannot be captured still drags by its move events */
      }
    });
    b.addEventListener("pointermove", (e: PointerEvent) => {
      if (!start) return;
      const dx = e.clientX - start.x;
      const dy = e.clientY - start.y;
      if (!dragging && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
      if (!dragging) dragsInFlight += 1;
      dragging = true;
      b.classList.add("syn-dragging");
      b.style.transform = `translate(${dx}px, ${dy}px)`;
      hanger.classList.toggle("syn-over", inside(e.clientX, e.clientY));
    });
    const finish = (e: PointerEvent, cancelled: boolean): void => {
      if (!start) return;
      const wasDragging = dragging;
      if (wasDragging) dragsInFlight -= 1;
      start = null;
      dragging = false;
      try {
        b.releasePointerCapture?.(e.pointerId);
      } catch {
        /* nothing was captured */
      }
      b.classList.remove("syn-dragging");
      b.style.removeProperty("transform");
      hanger.classList.remove("syn-over");
      if (!wasDragging) return; // a tap: the click that follows does the work
      suppressClick = true; // the click some browsers send after a drag must not toggle a second time
      setTimeout(() => {
        suppressClick = false;
      }, 50);
      if (!cancelled && inside(e.clientX, e.clientY) !== hung.has(i)) toggle(i);
    };
    b.addEventListener("pointerup", (e: PointerEvent) => finish(e, false));
    b.addEventListener("pointercancel", (e: PointerEvent) => finish(e, true));
    b.addEventListener("click", (e: MouseEvent) => {
      if (suppressClick) {
        e.preventDefault();
        return;
      }
      toggle(i);
    });
  });

  // The other direction: the range input (or a sweep, or Reset) moved the control, so the masses follow it.
  value.subscribe((v) => {
    const n = countOf(v);
    if (n === hung.size) return;
    adjustTo(n);
    render();
  });

  // What the audit and the runtime self-check ask of the masses: they are where the control says they are, each in the part of the bench it belongs to, drawn
  // where they are laid out (not moved, hidden or taken out of flow), and as many as the control's value means. A page cannot make the picture say one thing and the control another.
  const hidden = (el: Element): boolean => style(el, "display") === "none" || style(el, "visibility") === "hidden" || style(el, "opacity") === "0";
  const check = (): string[] => {
    const out: string[] = [];
    if (hung.size !== countOf(value.get())) out.push(`the masses for "${id}" disagree with the control`);
    if (parentOf(surface) === null || parentOf(tray) !== surface || parentOf(hanger) !== surface) out.push(`the mass bench for "${id}" was taken apart`);
    for (const part of [surface, tray, hanger]) if (hidden(part)) out.push(`the mass bench for "${id}" is hidden`);
    tokens.forEach((b, i) => {
      const name = `mass ${LETTERS[i]}`;
      if (parentOf(b) !== (hung.has(i) ? hanger : tray)) out.push(`${name} of "${id}" is not where the control says`);
      if (hidden(b) || tagOf(b) !== "button") out.push(`${name} of "${id}" is hidden`);
      const position = style(b, "position");
      if (position === "absolute" || position === "fixed") out.push(`${name} of "${id}" was taken out of the layout`);
      if (hasAttribute(b, "hidden") || (dragsInFlight === 0 && attr(b, "style") !== "")) out.push(`${name} of "${id}" was moved or hidden`);
    });
    return out;
  };
  // The layout half, read only by the verifier: the bench and its parts have a size a student can use, each mass sits inside the part it belongs to, is visible, and nothing
  // is drawn over it that would take a press. (A pointer-transparent overlay cannot be seen this way; it is a recorded limit.)
  const layout = (): string[] => {
    if (!layoutAvailable() || dragsInFlight > 0) return [];
    const out: string[] = [];
    const bench = rectOf(surface);
    if (!(bench.width > 0 && bench.height > 0)) out.push(`the mass bench for "${id}" is not drawn`);
    if (effectiveOpacity(surface) < 0.5) out.push(`the mass bench for "${id}" is faded out`);
    for (const [name, part] of [["tray", tray], ["hanger", hanger]] as const) {
      const r = rectOf(part);
      if (r.width < 44 || r.height < 44) out.push(`the ${name} for "${id}" is too small to put a mass on`);
    }
    tokens.forEach((b, i) => {
      const name = `mass ${LETTERS[i]}`;
      const r = rectOf(b);
      const home = parentOf(b);
      if (r.width < 40 || r.height < 40) out.push(`${name} of "${id}" is too small to press`);
      if (home) {
        const c = rectOf(home);
        if (r.left < c.left - 2 || r.right > c.right + 2 || r.top < c.top - 2 || r.bottom > c.bottom + 2) out.push(`${name} of "${id}" is outside the ${hung.has(i) ? "hanger" : "tray"}`);
      }
      if (effectiveOpacity(b) < 0.5) out.push(`${name} of "${id}" is faded out`);
      const hit = hitAt(r.left + r.width / 2, r.top + r.height / 2);
      if (hit && hit !== b && !contains(b, hit)) out.push(`${name} of "${id}" is covered by something else`);
    });
    return out;
  };
  widgets.push({ kind: "masses", id, masses: grid, check, layout });

  surface.append(tray, hanger, status);
  render();
  const wrap = record.el.closest(".syn-control");
  if (wrap?.parentElement) wrap.parentElement.insertBefore(surface, wrap);
  else env.controls.appendChild(surface);
  return value;
}
