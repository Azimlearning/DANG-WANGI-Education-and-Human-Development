// `pressureScene(env, {pressure, full})`: a tank of liquid with a small probe in it and arrows pressing on the probe from every side (W15). It DRAWS the pressure and prints no number: the
// probe sits as far down the tank as the pressure is of `full`, and the arrows grow with it. Bound to the output of the pressure model (`fluids.pressure_depth`), whose pressure is the depth
// times the density and g, the probe's place is the depth the student set. Its text is words only.
//
// What is drawn follows the number and nothing else: the audit keeps the exact attributes of every part, and the verifier checks the scale against the model's reach.

import { all, attr, effectiveOpacity, layoutAvailable, parentOf, rectOf, style } from "./dom";
import type { Environment } from "./environment";
import { kt } from "./i18n";
import type { Observable } from "./observable";
import { guard } from "./parts";
import { markKitSvg, nodeOf, own, widgets } from "./provenance";

const NS = "http://www.w3.org/2000/svg";
const W = 200;
const H = 240;
const SURFACE = 40;
const BOTTOM = 222;
const CX = 100;
const PRESSURE_MODEL = "fluids.pressure_depth";

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

const f = (v: number): string => v.toFixed(2);

/** Words for how hard the liquid presses, with no number in them. */
export function pressureWords(fraction: number): string {
  if (fraction < 0.02) return kt("pressureSurface");
  if (fraction < 0.34) return kt("pressureLow");
  if (fraction < 0.67) return kt("pressureMid");
  return kt("pressureHigh");
}

export interface PressureSceneOptions {
  /** The pressure: the output of the pressure model (`Synapse.pressureDepth`), and nothing else. */
  pressure: Observable<number>;
  /** The pressure, in the model's unit, at which the probe is drawn at the bottom of the tank. A drawing scale; it is never shown. */
  full: number;
}

export function pressureScene(env: Environment, options: PressureSceneOptions): HTMLDivElement {
  const { pressure, full } = options;
  const node = typeof pressure === "object" && pressure !== null ? nodeOf(pressure) : undefined;
  if (!node || node.kind !== "model" || node.id !== PRESSURE_MODEL) throw new TypeError("pressureScene: pressure must be the output of the pressure model (Synapse.pressureDepth)");
  if (typeof full !== "number" || !Number.isFinite(full) || !(full > 0)) throw new RangeError("pressureScene: full must be a positive number (the pressure drawn at the bottom of the tank)");

  const fraction = (): number => Math.min(1, Math.max(0, pressure.get() / full));
  const geometry = (): { cy: string; arrows: string[] } => {
    const y = SURFACE + 14 + fraction() * (BOTTOM - SURFACE - 28);
    const len = 6 + 24 * fraction();
    const gap = 12;
    // Four arrows pointing in at the probe: from the left, the right, above and below. The liquid presses on it from every side.
    // Each arrow is one path: the shaft, then a head of two short strokes at the end that touches the probe.
    const h = 5;
    const arrows = [
      `M ${f(CX - gap - len)} ${f(y)} L ${f(CX - gap)} ${f(y)} M ${f(CX - gap - h)} ${f(y - h)} L ${f(CX - gap)} ${f(y)} L ${f(CX - gap - h)} ${f(y + h)}`,
      `M ${f(CX + gap + len)} ${f(y)} L ${f(CX + gap)} ${f(y)} M ${f(CX + gap + h)} ${f(y - h)} L ${f(CX + gap)} ${f(y)} L ${f(CX + gap + h)} ${f(y + h)}`,
      `M ${f(CX)} ${f(y - gap - len)} L ${f(CX)} ${f(y - gap)} M ${f(CX - h)} ${f(y - gap - h)} L ${f(CX)} ${f(y - gap)} L ${f(CX + h)} ${f(y - gap - h)}`,
      `M ${f(CX)} ${f(y + gap + len)} L ${f(CX)} ${f(y + gap)} M ${f(CX - h)} ${f(y + gap + h)} L ${f(CX)} ${f(y + gap)} L ${f(CX + h)} ${f(y + gap + h)}`,
    ];
    return { cy: f(y), arrows };
  };
  const describe = (): string => kt("pressureScene", pressureWords(fraction()));

  const wrap = document.createElement("div");
  wrap.className = "syn-pressure";
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "syn-scene syn-pressure-scene", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);
  const tank = svg("rect", { x: "24", y: "20", width: String(W - 48), height: String(BOTTOM - 20 + 6), rx: "8", fill: "none", stroke: "var(--syn-line)", "stroke-width": "3" });
  const water = svg("rect", { x: "27", y: String(SURFACE), width: String(W - 54), height: String(BOTTOM - SURFACE + 3), rx: "5", fill: "var(--syn-liquid)", "fill-opacity": "0.45" });
  const surface = svg("line", { x1: "27", y1: String(SURFACE), x2: String(W - 27), y2: String(SURFACE), stroke: "var(--syn-line)", "stroke-width": "2", "stroke-dasharray": "6 4" });
  const label = own(svg("text", { x: "32", y: String(SURFACE - 6), fill: "var(--syn-fg)", "font-size": "11", "font-weight": "700" }), () => kt("pressureSurfaceLabel"));
  label.textContent = kt("pressureSurfaceLabel");
  const probe = svg("circle", { cx: String(CX), r: "7", fill: "var(--syn-card)", stroke: "var(--syn-line)", "stroke-width": "2.5" });
  const arrows = [0, 1, 2, 3].map(() => svg("path", { fill: "none", stroke: "var(--syn-indicator)", "stroke-width": "3", "stroke-linecap": "round", "stroke-linejoin": "round" }));
  root.append(water, tank, surface, label, ...arrows, probe);
  wrap.appendChild(root);
  const note = own(document.createElement("p"), () => pressureWords(fraction()));
  note.className = "syn-text syn-pressure-note";
  note.setAttribute("data-synapse-observations", "");
  note.setAttribute("role", "status");
  note.setAttribute("aria-live", "polite");
  wrap.appendChild(note);

  const draw = (): void => {
    const g = geometry();
    probe.setAttribute("cy", g.cy);
    arrows.forEach((a, i) => a.setAttribute("d", g.arrows[i] as string));
    root.setAttribute("aria-label", describe());
    note.textContent = pressureWords(fraction());
  };
  pressure.subscribe(draw);
  draw();
  env.stage.appendChild(wrap);

  // The picture is a claim about the model's number, so the audit holds it to that number: the probe as deep and the arrows as long as the pressure says, in the Kit's words, visible.
  const kept = guard();
  kept.part(probe, () => ({ cy: geometry().cy }));
  arrows.forEach((a, i) => kept.part(a, () => ({ d: geometry().arrows[i] as string })));
  kept.part(root, () => ({ "aria-label": describe() }));
  for (const el of [wrap, note, ...all(root, "*")]) if (el !== probe && !arrows.includes(el as SVGPathElement)) kept.part(el);
  kept.tree(wrap);
  const check = (): string[] => {
    const out: string[] = [];
    if (parentOf(root) !== wrap || parentOf(note) !== wrap || parentOf(wrap) === null) out.push("the pressure picture was taken apart");
    if (style(wrap, "display") === "none" || style(wrap, "visibility") === "hidden" || style(root, "display") === "none" || style(root, "visibility") === "hidden") out.push("the pressure picture is hidden");
    if (attr(root, "aria-label") !== describe()) out.push("the pressure picture's description was changed by the page");
    return out;
  };
  // The layout half, read only by the verifier: the picture takes up room, the probe and its arrows are drawn, and the probe sits where the pressure puts it.
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return ["the pressure picture is not drawn"];
    const out: string[] = [];
    if (effectiveOpacity(root) < 0.5 || effectiveOpacity(note) < 0.5) out.push("the pressure picture is faded out");
    if (!(rectOf(note).height > 0)) out.push("the pressure sentence is not drawn");
    if (arrows.some((a) => style(a, "stroke") === "none" || style(a, "display") === "none" || style(a, "visibility") === "hidden")) out.push("the pressure arrows are not drawn");
    const s = Math.min(box.width / W, box.height / H);
    const expected = box.top + (box.height - H * s) / 2 + Number(geometry().cy) * s;
    const pb = rectOf(probe);
    if (Math.abs(pb.top + pb.height / 2 - expected) > 3 * s + 2) out.push("the probe is drawn at a different depth than the pressure says");
    return out;
  };
  widgets.push({ kind: "scene", id: "pressure", obs: pressure, full, check, layout, exact: () => kept.problems() });
  return wrap;
}
