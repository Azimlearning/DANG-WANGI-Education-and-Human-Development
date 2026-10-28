// `refractionScene(env, {incidence, refraction})`: a ray of light entering a denser medium from air, drawn at the angles the lab computes (W15). It DRAWS and prints no number: the angle of
// incidence (`incidence`, a control in degrees, the one a plain slider makes) and the angle of refraction (`refraction`, the output of the refraction model, fed by that same control). The
// incident ray comes down to the boundary at the angle of incidence from the normal, and the refracted ray leaves it at the angle of refraction. Its text is words only: along the normal the
// ray goes straight on, with no change of medium it does not bend, and otherwise it bends towards the normal.
//
// What is drawn follows the numbers and nothing else: the audit keeps the exact attributes of every part and the elements inside the picture, and the verifier checks that the scene draws
// the refraction model fed by the very control it draws.

import { all, attr, effectiveOpacity, layoutAvailable, parentOf, rectOf, style } from "./dom";
import type { Environment } from "./environment";
import { kt } from "./i18n";
import type { Observable } from "./observable";
import { guard } from "./parts";
import { controls, markKitSvg, nodeOf, own, widgets } from "./provenance";

const NS = "http://www.w3.org/2000/svg";
const W = 240;
const H = 200;
const BOUNDARY = 96;
const PX = 120;
const RAY = 82;
const REFRACTION_MODEL = "physics.refraction_angle";
/** The angle, in degrees, the scene is drawn to: the whole range of an angle of incidence. Also the scale the verifier expects. */
export const REFRACTION_FULL = 90;
/** How much smaller the angle of refraction must be, in degrees, before the words say the ray bends. */
const BEND_EPS = 0.05;

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

const f = (v: number): string => v.toFixed(2);

export type Bending = "straight" | "same" | "bends";

/** What the ray does, from the two angles: the one rule the words, the picture and the verifier share. */
export function bendingOf(incidence: number, refraction: number): Bending {
  if (incidence < BEND_EPS) return "straight";
  return refraction < incidence - BEND_EPS ? "bends" : "same";
}

export function refractionWords(b: Bending): string {
  return kt(b === "straight" ? "refrStraight" : b === "same" ? "refrSame" : "refrBends");
}

export interface RefractionSceneOptions {
  /** The angle of incidence: a control in degrees (a slider). */
  incidence: Observable<number>;
  /** The angle of refraction: the output of the refraction model (`Synapse.refractionAngle`), fed by `incidence`. */
  refraction: Observable<number>;
}

export function refractionScene(env: Environment, options: RefractionSceneOptions): HTMLDivElement {
  const { incidence, refraction } = options;
  const sourceNode = typeof incidence === "object" && incidence !== null ? nodeOf(incidence) : undefined;
  const record = sourceNode?.kind === "control" ? controls.find((c) => c.obs === incidence) : undefined;
  if (!record || record.unit !== "deg") throw new TypeError("refractionScene: incidence must be a control in deg (a slider)");
  if (!(record.min >= 0 && record.max <= REFRACTION_FULL)) throw new RangeError("refractionScene: the angle of incidence must stay within 0 to 90 degrees");
  const modelNode = typeof refraction === "object" && refraction !== null ? nodeOf(refraction) : undefined;
  if (!modelNode || modelNode.kind !== "model" || modelNode.id !== REFRACTION_MODEL) throw new TypeError("refractionScene: refraction must be the output of the refraction model (Synapse.refractionAngle)");
  const fed = modelNode.inputs?.incidence_angle;
  if (!fed || nodeOf(fed) !== sourceNode) throw new TypeError("refractionScene: the angle of refraction must be fed by the same control the scene draws");

  const rad = (deg: number): number => (Math.max(0, Math.min(89.9, deg)) * Math.PI) / 180;
  const geometry = (): { inc: Record<string, string>; ref: Record<string, string>; head: string } => {
    const i = rad(incidence.get());
    const r = rad(refraction.get());
    const sx = PX - RAY * Math.sin(i);
    const sy = BOUNDARY - RAY * Math.cos(i);
    const ex = PX + RAY * Math.sin(r);
    const ey = BOUNDARY + RAY * Math.cos(r);
    // An arrowhead halfway along the incident ray, pointing the way the light travels.
    const mx = (sx + PX) / 2;
    const my = (sy + BOUNDARY) / 2;
    const ux = Math.sin(i);
    const uy = Math.cos(i);
    const head = `${f(mx + 7 * ux)},${f(my + 7 * uy)} ${f(mx - 5 * uy - 3 * ux)},${f(my + 5 * ux - 3 * uy)} ${f(mx + 5 * uy - 3 * ux)},${f(my - 5 * ux - 3 * uy)}`;
    return { inc: { x1: f(sx), y1: f(sy), x2: f(PX), y2: f(BOUNDARY) }, ref: { x1: f(PX), y1: f(BOUNDARY), x2: f(ex), y2: f(ey) }, head };
  };
  const bending = (): Bending => bendingOf(incidence.get(), refraction.get());
  const describe = (): string => kt("refrScene", refractionWords(bending()));

  const wrap = document.createElement("div");
  wrap.className = "syn-refr";
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "syn-scene syn-refr-scene", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);
  const medium = svg("rect", { x: "12", y: String(BOUNDARY), width: String(W - 24), height: String(H - BOUNDARY - 8), rx: "6", fill: "var(--syn-liquid)", "fill-opacity": "0.35", stroke: "var(--syn-line)", "stroke-width": "2" });
  const normal = svg("line", { x1: String(PX), y1: "10", x2: String(PX), y2: String(H - 12), stroke: "var(--syn-muted)", "stroke-width": "1.5", "stroke-dasharray": "5 4" });
  const inc = svg("line", { stroke: "var(--syn-indicator)", "stroke-width": "3", "stroke-linecap": "round" });
  const ref = svg("line", { stroke: "var(--syn-indicator)", "stroke-width": "3", "stroke-linecap": "round" });
  const head = svg("polygon", { fill: "var(--syn-indicator)" });
  const label = (x: number, y: number, key: "refrAir" | "refrMedium" | "refrNormal", anchor = "start"): SVGTextElement => {
    const t = own(svg("text", { x: String(x), y: String(y), "text-anchor": anchor, fill: "var(--syn-fg)", "font-size": "12", "font-weight": "700" }), () => kt(key));
    t.textContent = kt(key);
    return t;
  };
  root.append(medium, normal, inc, ref, head, label(18, 24, "refrAir"), label(18, BOUNDARY + 20, "refrMedium"), label(PX + 6, 22, "refrNormal"));
  wrap.appendChild(root);
  const note = own(document.createElement("p"), () => refractionWords(bending()));
  note.className = "syn-text syn-refr-note";
  note.setAttribute("data-synapse-observations", "");
  note.setAttribute("role", "status");
  note.setAttribute("aria-live", "polite");
  wrap.appendChild(note);

  const draw = (): void => {
    const g = geometry();
    for (const [k, v] of Object.entries(g.inc)) inc.setAttribute(k, v);
    for (const [k, v] of Object.entries(g.ref)) ref.setAttribute(k, v);
    head.setAttribute("points", g.head);
    root.setAttribute("aria-label", describe());
    note.textContent = refractionWords(bending());
  };
  incidence.subscribe(draw);
  refraction.subscribe(draw);
  draw();
  env.stage.appendChild(wrap);

  // The picture is a claim about the two angles, so the audit holds it to them: each ray where the angles put it, described in the Kit's words, still on the stage and visible.
  const kept = guard();
  kept.part(inc, () => geometry().inc);
  kept.part(ref, () => geometry().ref);
  kept.part(head, () => ({ points: geometry().head }));
  kept.part(root, () => ({ "aria-label": describe() }));
  for (const el of [wrap, note, ...all(root, "*")]) if (el !== inc && el !== ref && el !== head) kept.part(el);
  kept.tree(wrap);
  const check = (): string[] => {
    const out: string[] = [];
    if (parentOf(root) !== wrap || parentOf(note) !== wrap || parentOf(wrap) === null) out.push("the refraction picture was taken apart");
    if (style(wrap, "display") === "none" || style(wrap, "visibility") === "hidden" || style(root, "display") === "none" || style(root, "visibility") === "hidden") out.push("the refraction picture is hidden");
    if (attr(root, "aria-label") !== describe()) out.push("the refraction picture's description was changed by the page");
    return out;
  };
  // The layout half, read only by the verifier: the picture takes up room, both rays are drawn, and the refracted ray leaves the boundary on the far side of the normal.
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return ["the refraction picture is not drawn"];
    const out: string[] = [];
    if (effectiveOpacity(root) < 0.5 || effectiveOpacity(note) < 0.5) out.push("the refraction picture is faded out");
    if (!(rectOf(note).height > 0)) out.push("the refraction sentence is not drawn");
    for (const [name, line] of [["incident", inc], ["refracted", ref]] as const) {
      if (style(line, "stroke") === "none" || style(line, "stroke-width") === "0px" || style(line, "display") === "none" || style(line, "visibility") === "hidden") out.push(`the ${name} ray is not drawn`);
    }
    return out;
  };
  widgets.push({ kind: "scene", id: "refraction", obs: refraction, source: incidence, full: REFRACTION_FULL, check, layout, exact: () => kept.problems() });
  return wrap;
}
