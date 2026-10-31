// Drag handles on Kit drawings that are not apparatus parts (W18): a point on a graph, a test mass carried between planets. The pattern is the apparatus grip's (D-69): the handle is
// a pointer surface hidden from assistive technology, dragging it sets its control (snapped to the control's steps, so the control stays the one source of every number), and the
// control's range input stays on the page as the keyboard and screen-reader path. A control that has a handle is "quiet": its card keeps its name and value, and the bar itself is
// drawn only while it has focus, so the drawing is what a student operates.

import { event } from "./bridge";
import type { Observable } from "./observable";
import type { ControlRecord } from "./provenance";

/** Draw the control's range bar only while it has focus (the stylesheet's `syn-control-quiet`). Its label and value stay. */
export function quiet(rec: ControlRecord): void {
  rec.el?.parentElement?.classList.add("syn-control-quiet");
}

/** `v` moved onto the control's steps and into its range, as the verifier expects a drag to land. */
export function onSteps(rec: ControlRecord, v: number): number {
  const c = Math.min(rec.max, Math.max(rec.min, v));
  return Math.min(rec.max, Number((rec.min + Math.round((c - rec.min) / rec.step) * rec.step).toPrecision(12)));
}

/**
 * Let `hit` (an element of the drawing `root`, whose viewBox is `box`) drag `rec` along the horizontal line from `x0` (the control's minimum) to `x1` (its maximum), in drawing
 * units. The drawing is assumed centred in its box and scaled to fit (SVG's default `xMidYMid meet`), as the verifier assumes when it drags.
 */
export function dragAlong(root: SVGSVGElement, hit: SVGElement, box: [number, number], x0: number, x1: number, rec: ControlRecord): void {
  const obs = rec.obs as Observable<number>;
  const [W, H] = box;
  const toDrawingX = (clientX: number, clientY: number): number | null => {
    const r = root.getBoundingClientRect(); // the student's own pointer, so the element's own method
    const k = Math.min(r.width / W, r.height / H);
    if (!(k > 0)) return null;
    void clientY;
    return (clientX - (r.left + (r.width - W * k) / 2)) / k;
  };
  let held = false;
  const follow = (e: PointerEvent): void => {
    const x = toDrawingX(e.clientX, e.clientY);
    if (x === null || x1 === x0) return;
    obs.set(onSteps(rec, rec.min + ((x - x0) / (x1 - x0)) * (rec.max - rec.min)));
    event(rec.id, obs.get());
  };
  hit.addEventListener("pointerdown", (e: PointerEvent) => {
    if (e.button !== undefined && e.button !== 0) return;
    held = true;
    try {
      hit.setPointerCapture?.(e.pointerId);
    } catch {
      /* a pointer that cannot be captured still drags by its move events */
    }
    e.preventDefault();
  });
  hit.addEventListener("pointermove", (e: PointerEvent) => {
    if (held) follow(e);
  });
  hit.addEventListener("pointerup", (e: PointerEvent) => {
    if (!held) return;
    held = false;
    follow(e);
    try {
      hit.releasePointerCapture?.(e.pointerId);
    } catch {
      /* nothing was captured */
    }
  });
  hit.addEventListener("pointercancel", () => {
    held = false;
  });
  // `touch-action` is not honoured on an SVG shape: only a touch that starts on the handle is kept from scrolling the page.
  const still = (e: TouchEvent): void => e.preventDefault();
  hit.addEventListener("touchstart", still, { passive: false });
  hit.addEventListener("touchmove", still, { passive: false });
}
