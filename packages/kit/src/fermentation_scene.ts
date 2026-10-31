// `fermentationScene(env, {fermented, energy, full})`: the yeast fermentation apparatus of the textbook's Activity 7.3. Two boiling tubes under paraffin oil, A with yeast and B without (the
// control), each with a delivery tube dipping into limewater, and a thermometer in each. It DRAWS and prints no number: the amount of glucose tube A has fermented (`fermented`, a control in
// mol, the one a `dial` makes) and the energy released (`energy`, the output of the respiration-energy model). As soon as glucose is fermented, bubbles pass along tube A's delivery tube, its
// limewater turns cloudy, its thermometer reads higher than tube B's and it smells of ethanol; tube B, the control, shows none of it. Its text is words only.
//
// What is drawn follows the numbers and nothing else: the audit keeps the exact attributes of every part and the elements inside the picture, and the verifier checks that the scene draws a
// control in mol and the respiration-energy model fed by that same control.

import { all, attr, effectiveOpacity, layoutAvailable, parentOf, rectOf, style } from "./dom";
import type { Environment } from "./environment";
import { kt } from "./i18n";
import type { Observable } from "./observable";
import { guard } from "./parts";
import { controls, markKitSvg, nodeOf, own, ownAttr, widgets } from "./provenance";

const NS = "http://www.w3.org/2000/svg";
const W = 260;
const H = 220;
const ENERGY_MODEL = "biology.respiration_energy";
/** The energy one mole of glucose gives by alcohol fermentation, in kJ (Table 7.1). What the scene draws is THIS pathway: ethanol, carbon dioxide, a little warmth. It is pinned, not an option:
 * lactic acid fermentation makes no carbon dioxide and aerobic respiration is not fermentation, so the same picture would be false for them. */
export const FERMENTATION_KJ_PER_MOL = 210;
const BUBBLES = 5;
const CLEAR = "var(--syn-card)";
const CLOUDY = "var(--syn-cloud)";

export interface FermentationSceneOptions {
  /** The glucose tube A has fermented: a control in mol (the one a `dial` makes). */
  fermented: Observable<number>;
  /** The energy released: the output of the respiration-energy model, fed by `fermented`. */
  energy: Observable<number>;
  /** The glucose, in the control's unit, at which the bubbling is drawn at its fullest: a drawing scale, never shown. At least the control's maximum. */
  full: number;
}

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

/** Words for how much gas bubbles through tube A's delivery tube. */
export function bubbleWords(count: number): string {
  return count <= 1 ? kt("bubblesFew") : count <= 3 ? kt("bubblesSteady") : kt("bubblesPlenty");
}

/** What the student would see in tube A and tube B, in words. */
export function observationWords(count: number): string {
  return count > 0 ? kt("fermentActive", bubbleWords(count)) : kt("fermentIdle");
}

export function fermentationScene(env: Environment, options: FermentationSceneOptions): HTMLDivElement {
  const fermented = options.fermented;
  const energy = options.energy;
  const full = options.full;
  const sourceNode = typeof fermented === "object" && fermented !== null ? nodeOf(fermented) : undefined;
  const record = sourceNode?.kind === "control" ? controls.find((c) => c.obs === fermented) : undefined;
  if (!record || record.unit !== "mol") throw new TypeError("fermentationScene: fermented must be a control in mol (the one a dial makes)");
  const energyNode = typeof energy === "object" && energy !== null ? nodeOf(energy) : undefined;
  if (!energyNode || energyNode.kind !== "model" || energyNode.id !== ENERGY_MODEL) throw new TypeError("fermentationScene: energy must be the output of the respiration-energy model (Synapse.respirationEnergy)");
  const fed = energyNode.inputs?.glucose;
  if (!fed || nodeOf(fed) !== sourceNode) throw new TypeError("fermentationScene: the energy must be fed by the same control the scene draws");
  if (energyNode.params?.energy_per_mole !== FERMENTATION_KJ_PER_MOL) throw new RangeError(`fermentationScene: the energy must be alcohol fermentation's (${FERMENTATION_KJ_PER_MOL} kJ per mole); this picture is false for any other pathway`);
  if (typeof full !== "number" || !Number.isFinite(full) || !(full > 0)) throw new RangeError("fermentationScene: full must be a positive number");
  if (full < record.max) throw new RangeError("fermentationScene: full must be at least the control's maximum");

  const wrap = document.createElement("div");
  wrap.className = "syn-ferment";
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "syn-scene syn-fermentation", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);

  const started = (): boolean => fermented.get() > 0;
  const warmer = (): boolean => energy.get() > 0;
  const bubbleCount = (): number => (started() ? Math.min(BUBBLES, Math.max(1, Math.ceil((fermented.get() / full) * BUBBLES))) : 0);
  const describe = (): string => kt("fermentScene", observationWords(bubbleCount()));

  // two tubes: a boiling tube, its liquid, an oil layer, a thermometer, a delivery tube into a limewater test tube
  const parts: { tube: SVGElement; cloud: SVGElement; mercury: SVGElement; bubbles: SVGElement[] }[] = [];
  const dynamic = new Map<Element, () => Record<string, string>>();
  const letters: [string, number][] = [
    ["A", 20],
    ["B", 140],
  ];
  letters.forEach(([letter, x0], index) => {
    const withYeast = index === 0;
    root.appendChild(svg("rect", { x: String(x0 + 4), y: "70", width: "44", height: "110", rx: "6", fill: "none", stroke: "var(--syn-line)", "stroke-width": "3" }));
    root.appendChild(svg("rect", { x: String(x0 + 6), y: "104", width: "40", height: "74", rx: "5", fill: withYeast ? "var(--syn-yeast)" : "var(--syn-liquid)" }));
    root.appendChild(svg("rect", { x: String(x0 + 6), y: "96", width: "40", height: "8", fill: "var(--syn-oil)" }));
    root.appendChild(svg("rect", { x: String(x0 + 38), y: "52", width: "5", height: "100", rx: "2", fill: "none", stroke: "var(--syn-muted)", "stroke-width": "1.5" }));
    const mercury = svg("rect", { x: String(x0 + 39), width: "3", fill: "var(--syn-indicator)" });
    root.appendChild(mercury);
    // the delivery tube: up out of the cork, across, down into the limewater
    root.appendChild(svg("polyline", { points: `${x0 + 26},70 ${x0 + 26},40 ${x0 + 72},40 ${x0 + 72},150`, fill: "none", stroke: "var(--syn-line)", "stroke-width": "3", "stroke-linejoin": "round" }));
    const tube = svg("rect", { x: String(x0 + 58), y: "110", width: "28", height: "72", rx: "5", fill: "none", stroke: "var(--syn-line)", "stroke-width": "3" });
    const cloud = svg("rect", { x: String(x0 + 60), y: "134", width: "24", height: "46", rx: "4" });
    root.append(cloud, tube);
    const bubbles: SVGElement[] = [];
    for (let i = 0; i < BUBBLES; i++) {
      // W19: each bubble bobs up through the limewater while it is drawn (a CSS animation on its transform; its size still follows the model, and reduced
      // motion stops it).
      const b = svg("circle", { cx: String(x0 + 72), cy: String(146 - i * 6 + (i % 2 === 0 ? 0 : 2)), class: `syn-a-bubble syn-d${(i % 3) + 1}` });
      bubbles.push(b);
      root.appendChild(b);
    }
    const label = own(svg("text", { x: String(x0 + 26), y: "205", "text-anchor": "middle", fill: "var(--syn-fg)", "font-weight": "800", "font-size": "16" }), () => letter);
    label.textContent = letter;
    root.appendChild(label);
    parts.push({ tube, cloud, mercury, bubbles });
    dynamic.set(mercury, () => ({ y: (withYeast && warmer() ? 76 : 100).toString(), height: (withYeast && warmer() ? 76 : 52).toString() }));
    dynamic.set(cloud, () => ({ fill: withYeast && started() ? CLOUDY : CLEAR }));
    bubbles.forEach((b, i) => dynamic.set(b, () => ({ r: withYeast && i < bubbleCount() ? "3" : "0", fill: "var(--syn-card)", stroke: "var(--syn-line)", "stroke-width": "1.5" })));
  });

  const note = own(document.createElement("p"), () => observationWords(bubbleCount()));
  note.className = "syn-text syn-ferment-note";
  note.setAttribute("data-synapse-observations", "");
  note.setAttribute("role", "status");
  note.setAttribute("aria-live", "polite");
  ownAttr(root, "aria-label", () => describe());

  const draw = (): void => {
    for (const [el, fn] of dynamic) for (const [k, v] of Object.entries(fn())) el.setAttribute(k, v);
    root.setAttribute("aria-label", describe());
    note.textContent = observationWords(bubbleCount());
  };
  fermented.subscribe(draw);
  energy.subscribe(draw);
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
    if (parentOf(root) !== wrap || parentOf(note) !== wrap || parentOf(wrap) === null) out.push("the fermentation picture was taken apart");
    if (style(wrap, "display") === "none" || style(wrap, "visibility") === "hidden" || style(root, "display") === "none" || style(root, "visibility") === "hidden") out.push("the fermentation picture is hidden");
    if (attr(root, "aria-label") !== describe()) out.push("the fermentation picture's description was changed by the page");
    return out;
  };
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return ["the fermentation picture is not drawn"];
    const out: string[] = [];
    if (effectiveOpacity(root) < 0.5 || effectiveOpacity(note) < 0.5) out.push("the fermentation picture is faded out");
    if (!(rectOf(note).height > 0)) out.push("the fermentation sentence is not drawn");
    for (const p of parts) {
      const t = rectOf(p.tube);
      if (!(t.width > 0 && t.height > 0)) out.push("a limewater tube is not drawn");
    }
    return out;
  };
  widgets.push({ kind: "scene", id: "fermentation", obs: energy, source: fermented, full, check, layout, exact: () => kept.problems() });
  return wrap;
}
