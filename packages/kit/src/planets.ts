// `planetPicker(env, {id, label, value})`: a CONTROL, like `massHanger`, with a different surface (W18). It is which planet a test mass on a spring balance stands on: 1 Mercury,
// 2 Venus, 3 Earth, 4 Mars, 5 Jupiter, 6 Saturn, 7 Uranus, 8 Neptune. The eight planets are drawn in a row in space, in order from the Sun and bigger or smaller by size (not to
// scale); the student drags the test mass from planet to planet, or taps a planet. It is built ON `slider` with one word per step, so its provenance node, the sweep and every L1
// and L3 check are a slider's; the range input stays on the page for the keyboard and screen readers, and is drawn only while it has focus.
//
// It draws and prints no number: the planet names are words, the drawing follows the control, and the gravity on each planet comes from `physics.planet_gravity` wherever a
// Plan shows it. The verifier drags the test mass along the row like any grip and refuses a page whose test mass does not move the control (`handle_dead`).

import { all, contains, effectiveOpacity, hitAt, layoutAvailable, parentOf, rectOf, style } from "./dom";
import type { Environment } from "./environment";
import { dragAlong, quiet } from "./handles";
import { kt } from "./i18n";
import type { Observable } from "./observable";
import { guard } from "./parts";
import { controls, markKitSvg, own, ownAttr, widgets } from "./provenance";
import { slider } from "./slider";
import { event } from "./bridge";

export interface PlanetPickerOptions {
  id: string;
  label: string;
  /** The planet the test mass starts on: 1 (Mercury) to 8 (Neptune). */
  value: number;
}

export const PLANET_COUNT = 8;
const NS = "http://www.w3.org/2000/svg";
const W = 340;
const H = 156;
const X0 = 30;
const GAP = 40.6;
const CY = 98;
/** Drawn radii, in order from the Sun: bigger planets are drawn bigger, but nothing here is to scale. */
const SIZES = [8, 11, 11.5, 9, 19, 17, 14, 14];
const COLOURS = ["#a7a7a7", "#e3bb76", "#3d8fd6", "#c8603a", "#d9a86c", "#e8cf8c", "#82d4dc", "#4f74e3"];
const SKY = "#0b1020";
const HIT_RADIUS = 27;

const at = (planet: number): number => X0 + (planet - 1) * GAP;
const f = (n: number): string => n.toFixed(1);

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

const NAME_KEYS = ["planet1", "planet2", "planet3", "planet4", "planet5", "planet6", "planet7", "planet8"] as const;
const ORDINAL_KEYS = ["ordinal1", "ordinal2", "ordinal3", "ordinal4", "ordinal5", "ordinal6", "ordinal7", "ordinal8"] as const;

/** The planets' names in the page's language, in order from the Sun. */
export function planetNames(): string[] {
  return NAME_KEYS.map((k) => kt(k));
}

export function planetPicker(env: Environment, options: PlanetPickerOptions): Observable<number> {
  const id = String(options.id);
  const names = planetNames();
  const value = slider(env, { id, label: String(options.label), unit: "planet", min: 1, max: PLANET_COUNT, value: options.value, grid: PLANET_COUNT - 1, words: names });
  const rec = controls.find((c) => c.id === id);
  if (!rec) throw new Error(`planetPicker ${id}: its control was not registered`);
  quiet(rec);
  const index = (): number => Math.min(PLANET_COUNT, Math.max(1, Math.round(value.get())));

  const wrap = document.createElement("div");
  wrap.className = "syn-planets";
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "syn-scene syn-planets-scene", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);
  const describe = (): string => kt("planetsScene", names[index() - 1] as string, kt(ORDINAL_KEYS[index() - 1] as (typeof ORDINAL_KEYS)[number]));

  // Space, the edge of the Sun on the left, a few fixed stars.
  root.append(svg("rect", { x: "0", y: "0", width: String(W), height: String(H), rx: "12", fill: SKY }), svg("circle", { cx: "-46", cy: f(CY), r: "58", fill: "#f6c344" }));
  let seed = 11;
  for (let i = 0; i < 24; i++) {
    seed = (seed * 48271) % 2147483647;
    const sx = (seed % 3400) / 10;
    seed = (seed * 48271) % 2147483647;
    const sy = (seed % 1500) / 10;
    root.appendChild(svg("circle", { cx: f(sx), cy: f(sy), r: i % 4 === 0 ? "1.2" : "0.7", fill: "#cfe4f5", "fill-opacity": "0.6" }));
  }
  const glow = svg("circle", { fill: "none", stroke: "#3fb6a2", "stroke-width": "3" });
  root.appendChild(glow);
  const bodies = SIZES.map((r, i) => {
    const cx = f(at(i + 1));
    if (i === 5) root.appendChild(svg("ellipse", { cx, cy: f(CY), rx: f(r + 9), ry: "4.5", fill: "none", stroke: "#e8cf8c", "stroke-width": "2" }));
    const body = svg("circle", { cx, cy: f(CY), r: f(r), fill: COLOURS[i] as string, stroke: "#e9eef4", "stroke-width": "1", class: "syn-planet" });
    root.appendChild(body);
    return body;
  });
  const labels = names.map((name, i) => {
    const t = own(svg("text", { x: f(at(i + 1)), y: f(H - 10), "text-anchor": "middle", "font-size": "10", "font-weight": "700", fill: "#e9eef4" }), () => name);
    t.textContent = name;
    root.appendChild(t);
    return t;
  });

  // The test mass on its spring balance, hanging over the chosen planet.
  const top = (): number => CY - (SIZES[index() - 1] as number) - 40;
  const cord = svg("line", { stroke: "#e9eef4", "stroke-width": "2" });
  const coil = svg("polyline", { fill: "none", stroke: "#e9eef4", "stroke-width": "2", "stroke-linejoin": "round" });
  const mass = svg("rect", { width: "16", height: "12", rx: "2", fill: "#e6b93f", stroke: "#0b1020", "stroke-width": "1" });
  const hit = svg("circle", { r: String(HIT_RADIUS), fill: "#000", "fill-opacity": "0", class: "syn-app-grip", "aria-hidden": "true", "data-synapse-handle": `planets.${id}` });
  root.append(cord, coil, mass, hit);

  const dynamic = new Map<Element, () => Record<string, string>>();
  dynamic.set(glow, () => ({ cx: f(at(index())), cy: f(CY), r: f((SIZES[index() - 1] as number) + 5) }));
  dynamic.set(cord, () => ({ x1: f(at(index())), y1: f(top()), x2: f(at(index())), y2: f(top() + 8) }));
  dynamic.set(coil, () => {
    const x = at(index());
    const y = top() + 8;
    return { points: [0, 1, 2, 3, 4, 5].map((k) => `${f(x + (k % 2 === 0 ? -4 : 4))},${f(y + k * 3)}`).join(" ") };
  });
  dynamic.set(mass, () => ({ x: f(at(index()) - 8), y: f(top() + 24) }));
  dynamic.set(hit, () => ({ cx: f(at(index())), cy: f(top() + 22) }));

  const draw = (): void => {
    for (const [el, fn] of dynamic) for (const [k, v] of Object.entries(fn())) el.setAttribute(k, v);
    root.setAttribute("aria-label", describe());
  };
  ownAttr(root, "aria-label", describe);
  value.subscribe(draw);
  draw();

  // A tap on a planet takes the test mass there.
  bodies.forEach((body, i) =>
    body.addEventListener("click", () => {
      value.set(i + 1);
      event(id, value.get());
    }),
  );
  dragAlong(root, hit, [W, H], at(1), at(PLANET_COUNT), rec);

  const hint = own(document.createElement("p"), () => kt("planetsHint"));
  hint.className = "syn-text syn-planets-hint";
  hint.textContent = kt("planetsHint");
  wrap.append(root, hint);
  env.stage.appendChild(wrap);

  const kept = guard();
  for (const [el, fn] of dynamic) kept.part(el, fn);
  kept.part(root, () => ({ "aria-label": describe() }));
  for (const el of [wrap, hint, ...all(root, "*")]) if (!dynamic.has(el)) kept.part(el);
  kept.tree(wrap);

  const check = (): string[] => {
    const out: string[] = [];
    if (parentOf(root) !== wrap || parentOf(hint) !== wrap || parentOf(wrap) === null) out.push("the planets picture was taken apart");
    if (style(wrap, "display") === "none" || style(wrap, "visibility") === "hidden" || style(root, "display") === "none" || style(root, "visibility") === "hidden") out.push("the planets picture is hidden");
    if (labels.some((t, i) => t.textContent !== names[i])) out.push("a planet's name was changed by the page");
    return out;
  };
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return ["the planets picture is not drawn"];
    return effectiveOpacity(root) < 0.5 ? ["the planets picture is faded out"] : [];
  };
  widgets.push({ kind: "planets", id, control: id, check, layout, exact: () => kept.problems() });
  widgets.push({
    kind: "handle",
    id: `planets.${id}`,
    control: id,
    host: "planets",
    box: [W, H],
    origin: 1,
    full: PLANET_COUNT,
    grab: { from: [at(1), CY], to: [at(PLANET_COUNT), CY] },
    obs: value,
    check: () => {
      const out: string[] = [];
      if (parentOf(hit) !== root) out.push("the test mass was taken off the planets picture");
      if (style(hit, "display") === "none" || style(hit, "visibility") === "hidden" || style(hit, "pointer-events") === "none") out.push("the test mass cannot be grabbed");
      return out;
    },
    layout: () => {
      if (!layoutAvailable()) return [];
      const out: string[] = [];
      const r = rectOf(hit);
      if (r.width < 40 || r.height < 40) out.push("the test mass is too small to grab");
      const over = hitAt(r.left + r.width / 2, r.top + r.height / 2);
      if (over && over !== hit && !contains(hit, over)) out.push("the test mass is covered by something else");
      return out;
    },
  });
  return value;
}
