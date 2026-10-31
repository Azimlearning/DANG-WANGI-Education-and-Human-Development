// `titrationScene(env, {added, endpoint, full})`: a burette over a flask, and an eye the student places to read the burette. It DRAWS two quantities and prints neither: the liquid
// left in the burette (the volume run in is `added`, a control the student works with the stopcock) and the colour of the flask (colourless until `added` reaches the end point,
// the output of the end-point model, then pink). Its text is words only. The eye is a Kit button the student drags up and down the burette (or moves with the arrow keys); a sentence
// says, in words, whether the eye is level with the meniscus or above or below it and what that does to a reading. No number is printed and none is read from the eye.
//
// The picture is held to the numbers: the Kit's audit checks the liquid, the colour, the words and the eye against `added` and `endpoint`, and the verifier checks that the
// scene draws a control in cm3 and the end-point model, and that the burette's scale fits the control's range.

import { all, attr, contains, effectiveOpacity, hitAt, layoutAvailable, parentOf, rectOf, style, tagOf } from "./dom";
import { guard } from "./parts";
import type { Environment } from "./environment";
import { kt } from "./i18n";
import type { Observable } from "./observable";
import { controls, markKitSvg, markOwnStyle, nodeOf, own, ownAttr, registerAction, widgets } from "./provenance";

const NS = "http://www.w3.org/2000/svg";
const W = 220;
const H = 280;
const TOP = 20;
const BURETTE_H = 130;
const BASE = TOP + BURETTE_H;
const LEVEL_TOLERANCE = 0.05;
const EYE_STEP = 0.05;
const ENDPOINT_MODEL = "chemistry.titration_endpoint_volume";
const CLEAR = "var(--syn-card)";
const PINK = "var(--syn-indicator)";
const LIQUID = "var(--syn-liquid)";

export interface TitrationSceneOptions {
  /** The volume of liquid run in from the burette: a control, in cm3 (the one a `valve` makes). */
  added: Observable<number>;
  /** The volume at which the indicator changes colour: the output of the end-point model. */
  endpoint: Observable<number>;
  /** The burette's capacity in the same unit: a drawing scale, never shown. */
  full: number;
}

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

/** Words for how much liquid is left in the burette. */
export function buretteWords(used: number): string {
  if (used < 0.02) return kt("buretteFull");
  if (used < 0.34) return kt("buretteNearlyFull");
  if (used < 0.67) return kt("buretteHalf");
  return kt("buretteNearlyEmpty");
}

/** Words for what the student's eye position does to a reading. */
export function eyeWords(eye: number, meniscus: number): string {
  if (Math.abs(eye - meniscus) <= LEVEL_TOLERANCE) return kt("eyeLevel");
  // The textbook tells the student to keep the eye level with the meniscus when reading a burette; it says nothing about which way a wrong position misreads, so neither does this.
  return eye < meniscus
    ? kt("eyeAbove")
    : kt("eyeBelow");
}

export function titrationScene(env: Environment, options: TitrationSceneOptions): HTMLDivElement {
  const added = options.added;
  const endpoint = options.endpoint;
  const full = options.full;
  const addedNode = typeof added === "object" && added !== null ? nodeOf(added) : undefined;
  const record = addedNode?.kind === "control" ? controls.find((c) => c.obs === added) : undefined;
  if (!record || record.unit !== "cm3") throw new TypeError("titrationScene: added must be a control in cm3 (the one a valve makes)");
  const endNode = typeof endpoint === "object" && endpoint !== null ? nodeOf(endpoint) : undefined;
  if (!endNode || endNode.kind !== "model" || endNode.id !== ENDPOINT_MODEL) throw new TypeError("titrationScene: endpoint must be the output of the end-point model (Synapse.titrationEndpoint)");
  if (typeof full !== "number" || !Number.isFinite(full) || !(full > 0)) throw new RangeError("titrationScene: full must be a positive number (the burette's capacity)");
  if (full < record.max) throw new RangeError("titrationScene: full must be at least the control's maximum, so the burette can hold what the control can run in");

  const wrap = document.createElement("div");
  wrap.className = "syn-titr";
  const frame = document.createElement("div");
  frame.className = "syn-titr-frame";

  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "syn-scene syn-titration", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);
  // stand, burette (outline, graduations), liquid, meniscus line, tip, flask and its liquid, the eye's line of sight
  root.appendChild(svg("rect", { x: "8", y: "8", width: "6", height: String(H - 24), rx: "3", fill: "var(--syn-line)" }));
  root.appendChild(svg("rect", { x: "8", y: String(H - 18), width: "70", height: "6", rx: "3", fill: "var(--syn-line)" }));
  const liquid = svg("rect", { x: "42", width: "26", fill: LIQUID });
  root.appendChild(liquid);
  root.appendChild(svg("rect", { x: "40", y: String(TOP), width: "30", height: String(BURETTE_H), rx: "4", fill: "none", stroke: "var(--syn-line)", "stroke-width": "3" }));
  for (let i = 1; i < 10; i++) root.appendChild(svg("line", { x1: "40", x2: i % 5 === 0 ? "54" : "48", y1: String(TOP + (BURETTE_H * i) / 10), y2: String(TOP + (BURETTE_H * i) / 10), stroke: "var(--syn-line)", "stroke-width": "1.5" }));
  const meniscus = svg("line", { x1: "36", x2: "74", "stroke-dasharray": "4 3", stroke: "var(--syn-accent)", "stroke-width": "2" });
  meniscus.setAttribute("data-synapse-meniscus", "");
  root.appendChild(meniscus);
  root.appendChild(svg("line", { x1: "55", x2: "55", y1: String(BASE), y2: String(BASE + 28), stroke: "var(--syn-line)", "stroke-width": "4" }));
  // W19: a drop falls from the tip while the stopcock is held open (shown by the stylesheet from the stopcock's own open state; hidden otherwise and under
  // reduced motion). It is decoration: nothing in it follows a number, and its attributes never change.
  root.appendChild(svg("circle", { cx: "55", cy: String(BASE + 34), r: "3.5", fill: LIQUID, class: "syn-titr-drop" }));
  const flaskFill = svg("path", { d: "M45 200 L45 228 L22 262 L88 262 L65 228 L65 200 Z", stroke: "var(--syn-line)", "stroke-width": "3", "stroke-linejoin": "round", fill: CLEAR });
  // W20: the student picks the flask up and swirls it, as in V3 and at a real bench. Motion only: it follows the pointer through the Web Animations API, which
  // changes no attribute (the guard below still holds every one exactly) and no number, and it is off under reduced motion.
  const flask = svg("g", { class: "syn-titr-flask" });
  flask.appendChild(flaskFill);
  root.appendChild(flask);
  const sight = svg("line", { x1: "72", x2: "122", "stroke-dasharray": "5 4", stroke: "var(--syn-muted)", "stroke-width": "2" });
  root.appendChild(sight);

  const eye = document.createElement("button");
  eye.type = "button";
  eye.className = "syn-eye";
  eye.textContent = kt("eye");
  eye.setAttribute("data-synapse-eye", "");
  eye.setAttribute("data-synapse-action", "eye");
  const eyeName = kt("eyeName");
  eye.setAttribute("aria-label", eyeName);
  ownAttr(eye, "aria-label", () => eyeName);
  own(eye, () => kt("eye"));
  registerAction(eye, "eye", kt("eye"));
  markOwnStyle(eye);

  let eyeAt = 0; // 0 is the top of the burette, 1 the bottom
  const usedFraction = (): number => Math.min(1, Math.max(0, added.get() / full));
  const flaskIsPink = (): boolean => added.get() >= endpoint.get();
  const meniscusY = (): number => TOP + usedFraction() * BURETTE_H;
  const eyeY = (): number => TOP + eyeAt * BURETTE_H;
  const eyeSentence = (): string => eyeWords(eyeAt, usedFraction());
  const describe = (): string => kt("buretteScene", buretteWords(usedFraction()), flaskIsPink());
  const eyeStyle = (): string => `top:${((eyeY() / H) * 100).toFixed(2)}%`;

  const note = own(document.createElement("p"), () => eyeSentence());
  note.className = "syn-text syn-eye-note";
  note.setAttribute("data-synapse-eye-status", "");
  note.setAttribute("role", "status");
  note.setAttribute("aria-live", "polite");
  ownAttr(root, "aria-label", () => describe());

  const draw = (): void => {
    const y = meniscusY();
    liquid.setAttribute("y", y.toFixed(2));
    liquid.setAttribute("height", Math.max(0, BASE - y).toFixed(2));
    meniscus.setAttribute("y1", y.toFixed(2));
    meniscus.setAttribute("y2", y.toFixed(2));
    flaskFill.setAttribute("fill", flaskIsPink() ? PINK : CLEAR);
    sight.setAttribute("y1", eyeY().toFixed(2));
    sight.setAttribute("y2", eyeY().toFixed(2));
    eye.setAttribute("style", eyeStyle());
    root.setAttribute("aria-label", describe());
    note.textContent = eyeSentence();
  };
  added.subscribe(draw);
  endpoint.subscribe(draw);
  draw();

  const moveEye = (to: number): void => {
    if (!Number.isFinite(to)) return;
    eyeAt = Math.min(1, Math.max(0, to));
    draw();
  };
  let dragging = false;
  const fromPointer = (clientY: number): number => {
    const box = root.getBoundingClientRect(); // the student's own pointer, so the element's own method; the audit's reads go through the captured one
    const s = Math.min(box.width / W, box.height / H);
    const ySvg = (clientY - box.top - (box.height - H * s) / 2) / s;
    return (ySvg - TOP) / BURETTE_H;
  };
  eye.addEventListener("pointerdown", (e: PointerEvent) => {
    if (e.button !== undefined && e.button !== 0) return;
    dragging = true;
    try {
      eye.setPointerCapture?.(e.pointerId);
    } catch {
      /* a pointer that cannot be captured still drags by its move events */
    }
    moveEye(fromPointer(e.clientY));
  });
  eye.addEventListener("pointermove", (e: PointerEvent) => {
    if (dragging) moveEye(fromPointer(e.clientY));
  });
  const stop = (e: PointerEvent): void => {
    if (!dragging) return;
    dragging = false;
    try {
      eye.releasePointerCapture?.(e.pointerId);
    } catch {
      /* nothing was captured */
    }
  };
  eye.addEventListener("pointerup", stop);
  eye.addEventListener("pointercancel", stop);

  // The swirl: tilt and lift with the pointer's sideways movement while held, then settle back.
  const still = (): boolean => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  let swirl: { x: number; anim: Animation | null } | null = null;
  const pose = (dx: number): Keyframe => {
    const tilt = Math.max(-14, Math.min(14, dx * 0.35));
    return { transform: `translate(${(tilt * 0.4).toFixed(1)}px, -6px) rotate(${tilt.toFixed(1)}deg)` };
  };
  const hold = (frame0: Keyframe): void => {
    if (!swirl || typeof flask.animate !== "function") return;
    swirl.anim?.cancel();
    swirl.anim = flask.animate([frame0], { duration: 0, fill: "forwards" });
  };
  flask.addEventListener("pointerdown", (e: PointerEvent) => {
    if (still() || (e.button !== undefined && e.button !== 0)) return;
    swirl = { x: e.clientX, anim: null };
    try {
      flask.setPointerCapture?.(e.pointerId);
    } catch {
      /* moves still arrive without capture */
    }
    hold(pose(0));
  });
  flask.addEventListener("pointermove", (e: PointerEvent) => {
    if (swirl) hold(pose(e.clientX - swirl.x));
  });
  const settle = (): void => {
    if (!swirl) return;
    const last = swirl.anim;
    swirl = null;
    if (typeof flask.animate !== "function") return;
    const back = flask.animate([{ transform: "translate(0px, 0px) rotate(0deg)" }], { duration: 450, easing: "cubic-bezier(.3,1.6,.5,1)" });
    back.onfinish = () => last?.cancel();
    last?.cancel();
  };
  flask.addEventListener("pointerup", settle);
  flask.addEventListener("pointercancel", settle);
  eye.addEventListener("keydown", (e: KeyboardEvent) => {
    const keys: Record<string, () => number> = {
      ArrowUp: () => eyeAt - EYE_STEP,
      ArrowDown: () => eyeAt + EYE_STEP,
      Home: () => 0,
      End: () => 1,
    };
    const to = keys[e.key];
    if (!to) return;
    e.preventDefault();
    moveEye(to());
  });

  // W19: the stopcock goes on the burette, by its tip, as on a real burette and in V3, instead of above the readouts. It stays the valve's own button and group (the
  // valve checks only that it is intact and uncovered); the stylesheet places it. A page that built the scene without a valve keeps the picture as it was.
  const stopcock = record.el.closest(".syn-control")?.previousElementSibling;
  if (stopcock?.classList.contains("syn-valves")) frame.append(root, eye, stopcock);
  else frame.append(root, eye);
  wrap.append(frame, note);
  env.stage.appendChild(wrap);

  // What the page may not change: every part's attributes (the ones that follow a number are given as functions) and the elements inside the picture.
  const g = guard();
  g.part(liquid, () => ({ y: meniscusY().toFixed(2), height: Math.max(0, BASE - meniscusY()).toFixed(2) }));
  g.part(meniscus, () => ({ y1: meniscusY().toFixed(2), y2: meniscusY().toFixed(2) }));
  g.part(flaskFill, () => ({ fill: flaskIsPink() ? PINK : CLEAR }));
  g.part(sight, () => ({ y1: eyeY().toFixed(2), y2: eyeY().toFixed(2) }));
  g.part(root, () => ({ "aria-label": describe() }));
  g.part(eye, () => ({ style: eyeStyle() }));
  const dynamicParts: Element[] = [liquid, meniscus, flaskFill, sight, root, eye];
  for (const el of [wrap, frame, note, ...all(root, "*")]) if (!dynamicParts.includes(el)) g.part(el);
  g.tree(wrap);

  // The structural half (also acted on in the student's browser): what the Kit drew is still there and still says what the numbers say.
  const check = (): string[] => {
    const out: string[] = [];
    const y = meniscusY();
    if (attr(liquid, "y") !== y.toFixed(2) || attr(liquid, "height") !== Math.max(0, BASE - y).toFixed(2)) out.push("the burette's liquid was redrawn by the page");
    if (attr(meniscus, "y1") !== y.toFixed(2) || attr(meniscus, "y2") !== y.toFixed(2)) out.push("the meniscus line was moved by the page");
    if (attr(flaskFill, "fill") !== (flaskIsPink() ? PINK : CLEAR)) out.push("the flask's colour does not follow the end point");
    if (parentOf(flaskFill) !== flask || parentOf(flask) !== root) out.push("the flask was taken out of the picture");
    if (attr(root, "aria-label") !== describe()) out.push("the burette picture's description was changed by the page");
    if (attr(eye, "style") !== eyeStyle()) out.push("the eye was moved by the page");
    if (parentOf(root) !== frame || parentOf(eye) !== frame || parentOf(frame) !== wrap || parentOf(note) !== wrap || parentOf(wrap) === null) out.push("the burette picture was taken apart");
    if (tagOf(eye) !== "button") out.push("the eye is not a button");
    if (style(wrap, "display") === "none" || style(wrap, "visibility") === "hidden" || style(root, "display") === "none" || style(root, "visibility") === "hidden") out.push("the burette picture is hidden");
    for (const [name, el, want] of [
      ["liquid", liquid, LIQUID],
      ["flask outline", flaskFill, "var(--syn-line)"],
    ] as const) {
      const have = name === "liquid" ? attr(el, "fill") : attr(el, "stroke");
      if (have !== want) out.push(`the burette picture's ${name} was restyled by the page`);
    }
    return out;
  };
  // The layout half (the verifier only): drawn at a real size, nothing covers it, the meniscus and the eye are where the numbers put them.
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const out: string[] = [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return ["the burette picture is not drawn"];
    if (effectiveOpacity(root) < 0.5 || effectiveOpacity(eye) < 0.5 || effectiveOpacity(note) < 0.5) out.push("the burette picture is faded out");
    const s = Math.min(box.width / W, box.height / H);
    const oy = (box.height - H * s) / 2;
    const at = (ySvg: number): number => box.top + oy + ySvg * s;
    const tol = 3 * s + 2;
    const m = rectOf(meniscus);
    if (Math.abs(m.top + m.height / 2 - at(meniscusY())) > tol) out.push("the meniscus is drawn where the volume run in does not put it");
    const er = rectOf(eye);
    if (er.width < 44 || er.height < 44) out.push("the eye is too small to press");
    if (Math.abs(er.top + er.height / 2 - at(eyeY())) > tol) out.push("the eye is drawn away from where the Kit put it");
    const hit = hitAt(er.left + er.width / 2, er.top + er.height / 2);
    if (hit && hit !== eye && !contains(eye, hit)) out.push("the eye is covered by something else");
    return out;
  };
  widgets.push({ kind: "scene", id: "titration", obs: endpoint, source: added, full, eye: true, check, layout, exact: () => g.problems() });
  return wrap;
}
