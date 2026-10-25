// `orbitScene(env, {speed, circular, escape, full})`: Newton's cannonball. A cannon on a very tall mountain fires sideways; the picture shows where it goes. It DRAWS and prints no number: the launch speed
// (`speed`, a control in km/s, the one a plain slider makes), the circular speed (`circular`, the output of the circular-speed model) and the escape speed (`escape`, the output of the escape-speed
// model), both for Earth at the cannon's distance from Earth's centre. Below the circular speed the cannonball falls back to Earth; at the circular speed (within 2 percent) it circles Earth;
// between the two it goes round in an oval; at the escape speed or more it leaves for good. Its text is words only, and says the picture is a schematic.
//
// What is drawn follows the numbers and nothing else: the audit keeps the exact attributes of every part and the elements inside the picture, and the verifier checks that the scene draws a
// control in km/s and the two models fed by one declared radius, with Earth's mass.

import { all, attr, effectiveOpacity, layoutAvailable, parentOf, rectOf, style } from "./dom";
import type { Environment } from "./environment";
import type { Observable } from "./observable";
import { guard } from "./parts";
import { constants, controls, markKitSvg, nodeOf, own, ownAttr, widgets } from "./provenance";

const NS = "http://www.w3.org/2000/svg";
const W = 260;
const H = 240;
const CIRCULAR_MODEL = "physics.circular_speed";
const ESCAPE_MODEL = "physics.escape_speed";
/** Earth's mass, in kg, as the textbooks give it. The words and the picture are about Earth, so the scene is pinned to it, not to any central mass. */
export const EARTH_MASSES: readonly number[] = [5.97e24, 5.972e24];
/** The radius, in km, a cannon on Earth's surface is from Earth's centre (the textbooks use 6371 or 6378 km). */
export const EARTH_RADIUS_KM: readonly [number, number] = [6371, 6378.2];
/** How close to the circular speed counts as a circle: this fraction of it. */
export const CIRCLE_BAND = 0.02;

const CX = 130;
const CY = 100;
const EARTH_R = 26;
const LAUNCH_R = 36;
const LAUNCH_Y = CY - LAUNCH_R;

export type Outcome = "falls" | "circle" | "oval" | "escapes";

export interface OrbitSceneOptions {
  /** The launch speed: a control in km/s. */
  speed: Observable<number>;
  /** The circular speed: the output of the circular-speed model. */
  circular: Observable<number>;
  /** The escape speed: the output of the escape-speed model, fed by the same radius as `circular`. */
  escape: Observable<number>;
  /** The launch speed, in the control's unit, at which the launch arrow is drawn at its longest: a drawing scale, never shown. At least the control's maximum. */
  full: number;
}

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

/** Which of the four things the cannonball does. The one rule everything (the picture, the sentence, the verifier) uses. */
export function outcomeOf(speed: number, circular: number, escape: number): Outcome {
  if (speed >= escape) return "escapes";
  if (Math.abs(speed - circular) <= CIRCLE_BAND * circular) return "circle";
  return speed < circular ? "falls" : "oval";
}

const WORDS: Record<Outcome, string> = {
  falls: "The cannonball is too slow: it curves down and lands on Earth.",
  circle: "The cannonball goes round Earth in a circle: it keeps falling but keeps missing the ground.",
  oval: "The cannonball goes round Earth in an oval, moving away from Earth and then back towards it.",
  escapes: "The cannonball is fast enough to leave Earth and never comes back.",
};
const SCHEMATIC = "The picture is a sketch, not to scale, and the mountain is drawn far taller than a real one.";

export function outcomeWords(o: Outcome): string {
  return WORDS[o];
}

const f = (n: number): string => n.toFixed(1);

/** The path of the cannonball, as a schematic that follows the speed ratio. */
export function pathFor(o: Outcome, ratio: number): string {
  if (o === "circle") return `M ${f(CX)} ${f(LAUNCH_Y)} A ${f(LAUNCH_R)} ${f(LAUNCH_R)} 0 1 1 ${f(CX)} ${f(CY + LAUNCH_R)} A ${f(LAUNCH_R)} ${f(LAUNCH_R)} 0 1 1 ${f(CX)} ${f(LAUNCH_Y)}`;
  if (o === "oval") {
    const e = 0.1 + 0.4 * Math.min(1, Math.max(0, (ratio - 1) / (Math.SQRT2 - 1)));
    const a = LAUNCH_R / (1 - e);
    const b = a * Math.sqrt(1 - e * e);
    const cy = CY + a * e;
    return `M ${f(CX)} ${f(cy - a)} A ${f(b)} ${f(a)} 0 0 1 ${f(CX)} ${f(cy + a)} A ${f(b)} ${f(a)} 0 0 1 ${f(CX)} ${f(cy - a)}`;
  }
  if (o === "escapes") return `M ${f(CX)} ${f(LAUNCH_Y)} C ${f(CX + 40)} ${f(LAUNCH_Y - 4)} ${f(CX + 80)} ${f(LAUNCH_Y - 18)} ${f(W - 8)} 8`;
  const x = Math.min(1, Math.max(0, ratio));
  const theta = ((20 + 50 * x) * Math.PI) / 180;
  const lx = CX + EARTH_R * Math.sin(theta);
  const ly = CY - EARTH_R * Math.cos(theta);
  return `M ${f(CX)} ${f(LAUNCH_Y)} Q ${f(CX + 30 + 40 * x)} ${f(LAUNCH_Y - 2)} ${f(lx)} ${f(ly)}`;
}

export function orbitScene(env: Environment, options: OrbitSceneOptions): HTMLDivElement {
  const { speed, circular, escape, full } = options;
  const sourceNode = typeof speed === "object" && speed !== null ? nodeOf(speed) : undefined;
  const record = sourceNode?.kind === "control" ? controls.find((c) => c.obs === speed) : undefined;
  if (!record || record.unit !== "km/s") throw new TypeError("orbitScene: speed must be a control in km/s (a slider)");
  const circNode = typeof circular === "object" && circular !== null ? nodeOf(circular) : undefined;
  if (!circNode || circNode.kind !== "model" || circNode.id !== CIRCULAR_MODEL) throw new TypeError("orbitScene: circular must be the output of the circular-speed model (Synapse.circularSpeed)");
  const escNode = typeof escape === "object" && escape !== null ? nodeOf(escape) : undefined;
  if (!escNode || escNode.kind !== "model" || escNode.id !== ESCAPE_MODEL) throw new TypeError("orbitScene: escape must be the output of the escape-speed model (Synapse.escapeSpeed)");
  const circRadius = circNode.inputs?.radius;
  const escRadius = escNode.inputs?.radius;
  const radiusNode = circRadius ? nodeOf(circRadius) : undefined;
  if (!circRadius || !escRadius || !radiusNode || radiusNode !== nodeOf(escRadius) || radiusNode.kind !== "constant") throw new TypeError("orbitScene: both models must be fed by the same declared radius (a constant)");
  const radiusUnit = constants.find((c) => c.label === radiusNode.id)?.unit;
  const radiusKm = (circRadius as Observable<number>).get();
  if (radiusUnit !== "km" || !(radiusKm >= EARTH_RADIUS_KM[0] && radiusKm <= EARTH_RADIUS_KM[1])) throw new RangeError("orbitScene: the radius must be Earth's radius in km; this picture is about a cannon on Earth");
  const mass = circNode.params?.central_mass;
  if (mass === undefined || !EARTH_MASSES.includes(mass) || escNode.params?.central_mass !== mass) throw new RangeError("orbitScene: both models must use Earth's mass; this picture is about Earth");
  if (typeof full !== "number" || !Number.isFinite(full) || !(full > 0)) throw new RangeError("orbitScene: full must be a positive number");
  if (full < record.max) throw new RangeError("orbitScene: full must be at least the control's maximum");

  const wrap = document.createElement("div");
  wrap.className = "syn-orbit";
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "syn-scene syn-orbit-scene", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);

  const outcome = (): Outcome => outcomeOf(speed.get(), circular.get(), escape.get());
  const ratio = (): number => speed.get() / circular.get();
  const arrow = (): number => 8 + 52 * Math.min(1, Math.max(0, speed.get() / full));
  const describe = (): string => `A cannon on a tall mountain fires sideways over Earth. ${WORDS[outcome()]} ${SCHEMATIC}`;

  const earth = svg("circle", { cx: f(CX), cy: f(CY), r: f(EARTH_R), fill: "var(--syn-liquid)", stroke: "var(--syn-edge)", "stroke-width": "2" });
  const mountain = svg("polygon", { points: `${f(CX - 14)},${f(CY - EARTH_R + 3)} ${f(CX)},${f(LAUNCH_Y)} ${f(CX + 14)},${f(CY - EARTH_R + 3)}`, fill: "var(--syn-muted)", stroke: "var(--syn-edge)", "stroke-width": "2", "stroke-linejoin": "round" });
  const path = svg("path", { fill: "none", "stroke-width": "3", "stroke-linecap": "round" });
  const shaft = svg("line", { x1: f(CX), y1: f(LAUNCH_Y - 8), y2: f(LAUNCH_Y - 8), stroke: "var(--syn-edge)", "stroke-width": "3", "stroke-linecap": "round" });
  const head = svg("polygon", { fill: "var(--syn-edge)" });
  const label = own(svg("text", { x: f(CX), y: f(CY + 4), "text-anchor": "middle", fill: "var(--syn-fg)", "font-weight": "800", "font-size": "13" }), () => "Earth");
  label.textContent = "Earth";
  root.append(earth, path, mountain, shaft, head, label);

  const dynamic = new Map<Element, () => Record<string, string>>();
  dynamic.set(path, () => ({ d: pathFor(outcome(), ratio()), stroke: outcome() === "falls" ? "var(--syn-indicator)" : "var(--syn-accent)", "stroke-dasharray": outcome() === "escapes" ? "6 5" : "none" }));
  dynamic.set(shaft, () => ({ x2: f(CX + arrow()) }));
  dynamic.set(head, () => ({ points: `${f(CX + arrow() + 7)},${f(LAUNCH_Y - 8)} ${f(CX + arrow() - 2)},${f(LAUNCH_Y - 14)} ${f(CX + arrow() - 2)},${f(LAUNCH_Y - 2)}` }));

  const note = own(document.createElement("p"), () => `${WORDS[outcome()]} ${SCHEMATIC}`);
  note.className = "syn-text syn-orbit-note";
  note.setAttribute("data-synapse-observations", "");
  note.setAttribute("role", "status");
  note.setAttribute("aria-live", "polite");
  ownAttr(root, "aria-label", () => describe());

  const draw = (): void => {
    for (const [el, fn] of dynamic) for (const [k, v] of Object.entries(fn())) el.setAttribute(k, v);
    root.setAttribute("aria-label", describe());
    note.textContent = `${WORDS[outcome()]} ${SCHEMATIC}`;
  };
  speed.subscribe(draw);
  circular.subscribe(draw);
  escape.subscribe(draw);
  draw();
  wrap.append(root, note);
  env.stage.appendChild(wrap);

  const kept = guard();
  for (const [el, fn] of dynamic) kept.part(el, fn);
  kept.part(root, () => ({ "aria-label": describe() }));
  for (const el of [wrap, note, ...all(root, "*")]) if (!dynamic.has(el)) kept.part(el);
  kept.tree(wrap);

  const check = (): string[] => {
    const out: string[] = [];
    if (parentOf(root) !== wrap || parentOf(note) !== wrap || parentOf(wrap) === null) out.push("the orbit picture was taken apart");
    if (style(wrap, "display") === "none" || style(wrap, "visibility") === "hidden" || style(root, "display") === "none" || style(root, "visibility") === "hidden") out.push("the orbit picture is hidden");
    if (attr(root, "aria-label") !== describe()) out.push("the orbit picture's description was changed by the page");
    return out;
  };
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return ["the orbit picture is not drawn"];
    const out: string[] = [];
    if (effectiveOpacity(root) < 0.5 || effectiveOpacity(note) < 0.5) out.push("the orbit picture is faded out");
    if (!(rectOf(note).height > 0)) out.push("the orbit sentence is not drawn");
    if (!(rectOf(path).width > 0 && rectOf(path).height > 0)) out.push("the cannonball's path is not drawn");
    return out;
  };
  widgets.push({ kind: "scene", id: "orbit", obs: circular, second: escape, source: speed, full, check, layout, exact: () => kept.problems() });
  return wrap;
}
