// Scenes: pictures bound to observables. A scene DRAWS a quantity and never prints one: its text is words only, so there is nothing for the audit to ground and nothing a page
// could pass off as a computed number. Bound to a model's output (an observable the Kit made), it moves when the control moves; its text equivalent is a sentence with no digits.

import { all, attr, effectiveOpacity, layoutAvailable, parentOf, rectOf, style } from "./dom";
import { guard } from "./parts";
import type { Environment } from "./environment";
import type { Observable } from "./observable";
import { markKitSvg, nodeOf, ownAttr, widgets } from "./provenance";

const NS = "http://www.w3.org/2000/svg";

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

export interface SpringSceneOptions {
  /** The spring's extension: the output of the Hooke's law model (`mechanics.hookes`), and nothing else. */
  extension: Observable<number>;
  /** The extension at which the spring is drawn fully stretched. A drawing scale; it is never shown. */
  full: number;
}

const COIL_STROKE = "var(--syn-accent)";
const PAN_FILL = "var(--syn-edge)";
const TOP = 16;
const MIN_LEN = 56;
const MAX_LEN = 176;
const COILS = 10;

/** Words for how far the spring is stretched, with no number in them. */
export function stretchWords(fraction: number): string {
  if (fraction < 0.02) return "not stretched";
  if (fraction < 0.34) return "stretched a little";
  if (fraction < 0.67) return "stretched a fair amount";
  return "stretched a lot";
}

export function springScene(env: Environment, options: SpringSceneOptions): SVGSVGElement {
  const x = options.extension;
  const full = options.full;
  const node = typeof x === "object" && x !== null ? nodeOf(x) : undefined;
  if (!node || node.kind !== "model" || node.id !== "mechanics.hookes") throw new TypeError("springScene: extension must be the output of the Hooke's law model (Synapse.hookes)");
  if (typeof full !== "number" || !Number.isFinite(full) || !(full > 0)) throw new RangeError("springScene: full must be a positive number (the extension drawn as fully stretched)");

  const root = svg("svg", { viewBox: "0 0 160 250", class: "syn-scene", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);
  root.appendChild(svg("line", { x1: "36", y1: String(TOP - 4), x2: "124", y2: String(TOP - 4), stroke: "var(--syn-fg)", "stroke-width": "6", "stroke-linecap": "round" }));
  const coil = svg("polyline", { fill: "none", stroke: COIL_STROKE, "stroke-width": "4", "stroke-linejoin": "round", "stroke-linecap": "round" });
  const pan = svg("rect", { x: "52", width: "56", height: "8", rx: "3", fill: PAN_FILL });
  root.append(coil, pan);

  const fraction = (): number => Math.min(1, Math.max(0, x.get() / full));
  const describe = (): string => `A spring hanging from a bracket, ${stretchWords(fraction())}.`;
  const geometry = (): { points: string; panY: string } => {
    const length = MIN_LEN + fraction() * (MAX_LEN - MIN_LEN);
    const bottom = TOP + length;
    const pts: string[] = [`80,${TOP}`, `80,${TOP + 14}`];
    const span = length - 28;
    for (let i = 1; i <= COILS; i++) pts.push(`${i % 2 === 1 ? 62 : 98},${(TOP + 14 + (span * (i - 0.5)) / COILS).toFixed(1)}`);
    pts.push(`80,${(bottom - 14).toFixed(1)}`, `80,${bottom.toFixed(1)}`);
    return { points: pts.join(" "), panY: bottom.toFixed(1) };
  };

  const draw = (): void => {
    const g = geometry();
    coil.setAttribute("points", g.points);
    pan.setAttribute("y", g.panY);
    root.setAttribute("aria-label", describe());
  };
  x.subscribe(draw);
  draw();
  env.stage.appendChild(root);

  // The picture is a claim about the model's number, so the audit holds it to that number: the spring is drawn where the extension says, described in the words the Kit
  // chose, still on the stage and still visible. A page that redraws or relabels it, or hides it, is reported.
  const parent = parentOf(root);
  const kept = guard();
  kept.tree(root);
  kept.part(root, () => ({ "aria-label": describe() }));
  kept.part(coil, () => ({ points: geometry().points }));
  kept.part(pan, () => ({ y: geometry().panY }));
  for (const el of all(root, "*")) if (el !== coil && el !== pan) kept.part(el);
  const check = (): string[] => {
    const out: string[] = [];
    const g = geometry();
    if (attr(coil, "points") !== g.points || attr(pan, "y") !== g.panY) out.push("the spring picture was redrawn by the page");
    if (attr(root, "aria-label") !== describe()) out.push("the spring picture's description was changed by the page");
    if (parentOf(root) !== parent || parent === null) out.push("the spring picture was moved off the stage");
    if (style(root, "display") === "none" || style(root, "visibility") === "hidden" || style(root, "opacity") === "0") out.push("the spring picture is hidden");
    if (attr(coil, "stroke") !== COIL_STROKE || attr(coil, "stroke-width") !== "4" || attr(coil, "fill") !== "none" || attr(pan, "fill") !== PAN_FILL) out.push("the spring picture was restyled by the page");
    return out;
  };
  // The layout half, read only by the verifier: the picture takes up room, shows, strokes its coil, and the pan sits where the extension puts it (a style rule that squashes,
  // shifts or hides the drawing leaves every attribute above untouched).
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const out: string[] = [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return ["the spring picture is not drawn"];
    if (effectiveOpacity(root) < 0.5) out.push("the spring picture is faded out");
    if (style(coil, "stroke") === "none" || style(coil, "stroke-width") === "0px") out.push("the spring's coil is not drawn");
    const s = Math.min(box.width / 160, box.height / 250);
    const expected = box.top + (box.height - 250 * s) / 2 + Number(geometry().panY) * s;
    if (Math.abs(rectOf(pan).top - expected) > 3 * s + 2) out.push("the spring picture is drawn at a different length than the extension says");
    return out;
  };
  widgets.push({ kind: "scene", id: "spring", obs: x, full, check, layout, exact: () => kept.problems() });
  return root;
}
