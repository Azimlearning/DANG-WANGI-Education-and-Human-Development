// Scenes: pictures bound to observables. A scene DRAWS a quantity and never prints one: its text is words only, so there is nothing for the audit to ground and nothing a page
// could pass off as a computed number. Bound to a model's output (an observable the Kit made), it moves when the control moves; its text equivalent is a sentence with no digits.

import { all, attr, effectiveOpacity, layoutAvailable, parentOf, rectOf, style } from "./dom";
import { guard } from "./parts";
import type { Environment } from "./environment";
import { kt } from "./i18n";
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
const PAN_FILL = "var(--syn-line)";
const TOP = 16;
const MIN_LEN = 56;
const MAX_LEN = 176;
const COILS = 10;
const RULE_X = 130;

/** Words for how far the spring is stretched, with no number in them. */
export function stretchWords(fraction: number): string {
  if (fraction < 0.02) return kt("stretch0");
  if (fraction < 0.34) return kt("stretch1");
  if (fraction < 0.67) return kt("stretch2");
  return kt("stretch3");
}

export function springScene(env: Environment, options: SpringSceneOptions): SVGSVGElement {
  const x = options.extension;
  const full = options.full;
  const node = typeof x === "object" && x !== null ? nodeOf(x) : undefined;
  if (!node || node.kind !== "model" || node.id !== "mechanics.hookes") throw new TypeError("springScene: extension must be the output of the Hooke's law model (Synapse.hookes)");
  if (typeof full !== "number" || !Number.isFinite(full) || !(full > 0)) throw new RangeError("springScene: full must be a positive number (the extension drawn as fully stretched)");

  const root = svg("svg", { viewBox: "0 0 160 250", class: "syn-scene", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);
  // The retort stand (a rod, a base and the clamp arm the spring hangs from) and a metre rule beside the spring: the same bench V3 draws. Both are still, drawn in muted lines.
  const STAND = "var(--syn-muted)";
  root.append(
    svg("line", { x1: "14", y1: "8", x2: "14", y2: "236", stroke: STAND, "stroke-width": "6", "stroke-linecap": "round" }),
    svg("rect", { x: "2", y: "236", width: "46", height: "8", rx: "3", fill: STAND }),
    svg("line", { x1: "14", y1: String(TOP - 4), x2: "104", y2: String(TOP - 4), stroke: "var(--syn-fg)", "stroke-width": "6", "stroke-linecap": "round" }),
    svg("rect", { x: String(RULE_X), y: String(TOP + MIN_LEN - 6), width: "18", height: String(MAX_LEN - MIN_LEN + 12), rx: "3", fill: "var(--syn-card)", stroke: "var(--syn-border)", "stroke-width": "2" }),
  );
  for (let i = 0; i <= 12; i++) {
    const y = TOP + MIN_LEN + (i * (MAX_LEN - MIN_LEN)) / 12;
    root.appendChild(svg("line", { x1: String(RULE_X), y1: y.toFixed(1), x2: String(RULE_X + (i % 4 === 0 ? 12 : 7)), y2: y.toFixed(1), stroke: "var(--syn-muted)", "stroke-width": "1.5" }));
  }
  const coil = svg("polyline", { fill: "none", stroke: COIL_STROKE, "stroke-width": "4", "stroke-linejoin": "round", "stroke-linecap": "round" });
  const pan = svg("rect", { x: "52", width: "56", height: "8", rx: "3", fill: PAN_FILL });
  // The cord from the pan down to the hanger the student drops masses on (which sits under the picture), a guide line to the rule and its pointer.
  const cord = svg("line", { x1: "80", x2: "80", y2: "250", stroke: PAN_FILL, "stroke-width": "3", "stroke-linecap": "round" });
  const guide = svg("line", { x1: "108", x2: String(RULE_X), stroke: "var(--syn-indicator)", "stroke-width": "1.5", "stroke-dasharray": "3 3" });
  const pointer = svg("polygon", { fill: "var(--syn-indicator)" });
  root.append(cord, coil, pan, guide, pointer);

  const fraction = (): number => Math.min(1, Math.max(0, x.get() / full));
  const describe = (): string => kt("springHanging", stretchWords(fraction()));
  const geometry = (): { points: string; panY: string; cordY: string; guideY: string; pointerPoints: string } => {
    const length = MIN_LEN + fraction() * (MAX_LEN - MIN_LEN);
    const bottom = TOP + length;
    const pts: string[] = [`80,${TOP}`, `80,${TOP + 14}`];
    const span = length - 28;
    for (let i = 1; i <= COILS; i++) pts.push(`${i % 2 === 1 ? 62 : 98},${(TOP + 14 + (span * (i - 0.5)) / COILS).toFixed(1)}`);
    pts.push(`80,${(bottom - 14).toFixed(1)}`, `80,${bottom.toFixed(1)}`);
    const mid = bottom + 4;
    return {
      points: pts.join(" "),
      panY: bottom.toFixed(1),
      cordY: (bottom + 8).toFixed(1),
      guideY: mid.toFixed(1),
      pointerPoints: `${RULE_X - 8},${mid.toFixed(1)} ${RULE_X},${(mid - 5).toFixed(1)} ${RULE_X},${(mid + 5).toFixed(1)}`,
    };
  };

  const draw = (): void => {
    const g = geometry();
    coil.setAttribute("points", g.points);
    pan.setAttribute("y", g.panY);
    cord.setAttribute("y1", g.cordY);
    guide.setAttribute("y1", g.guideY);
    guide.setAttribute("y2", g.guideY);
    pointer.setAttribute("points", g.pointerPoints);
    root.setAttribute("aria-label", describe());
  };
  x.subscribe(draw);
  draw();
  // With a mass hanger on the stage the picture goes inside its bench, above the hanger, so the masses are dropped on what hangs from the spring (V3's bench).
  const bench = Array.from(env.stage.children).find((el) => el.classList.contains("syn-masses"));
  if (bench) bench.prepend(root);
  else env.stage.appendChild(root);

  // The picture is a claim about the model's number, so the audit holds it to that number: the spring is drawn where the extension says, described in the words the Kit
  // chose, still on the stage and still visible. A page that redraws or relabels it, or hides it, is reported.
  const parent = parentOf(root);
  const kept = guard();
  kept.tree(root);
  kept.part(root, () => ({ "aria-label": describe() }));
  kept.part(coil, () => ({ points: geometry().points }));
  kept.part(pan, () => ({ y: geometry().panY }));
  kept.part(cord, () => ({ y1: geometry().cordY }));
  kept.part(guide, () => ({ y1: geometry().guideY, y2: geometry().guideY }));
  kept.part(pointer, () => ({ points: geometry().pointerPoints }));
  for (const el of all(root, "*")) if (el !== coil && el !== pan && el !== cord && el !== guide && el !== pointer) kept.part(el);
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
