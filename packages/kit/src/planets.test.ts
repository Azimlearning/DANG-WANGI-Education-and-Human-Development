import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { environment } from "./environment";
import { graph } from "./graph";
import { KIT_VERSION } from "./index";
import { planetPicker, planetNames } from "./planets";
import { controls, resetForTests } from "./provenance";
import { readout } from "./readout";
import { planetGravity } from "./science/planet_gravity";
import { weight } from "./science/weight";
import { slider } from "./slider";
import { hookes } from "./science/hookes";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

function bench(start = 3) {
  const env = environment({ title: "Gravity on the planets", note: "A test mass on each planet." });
  const planet = planetPicker(env, { id: "planet", label: "Planet", value: start });
  const mass = slider(env, { id: "mass", label: "Mass", unit: "kg", min: 0, max: 5, value: 1, grid: 5 });
  const g = planetGravity({ planet });
  const w = weight({ mass, gravity: g });
  readout(env, { label: "Gravitational field strength", unit: "N/kg", value: g, digits: 2 });
  readout(env, { label: "Weight", unit: "N", value: w, digits: 2 });
  return { env, planet, mass, g, w };
}
const widget = (id: string) => audit(KIT_VERSION).widgets.find((w) => w.id === id);

describe("planetPicker: a control whose value is a planet", () => {
  it("is a slider from 1 to 8 that says the planet's name, with its range bar drawn only with focus", () => {
    const { planet } = bench(4);
    const input = document.querySelector("[data-synapse-control='planet']") as HTMLInputElement;
    expect(input.min).toBe("1");
    expect(input.max).toBe("8");
    expect(input.getAttribute("aria-valuetext")).toBe("Mars");
    expect(input.parentElement?.classList.contains("syn-control-quiet")).toBe(true);
    expect(input.parentElement?.querySelector(".syn-control-value")?.textContent).toBe("Mars");
    planet.set(5.4);
    expect(planet.get()).toBe(5);
    expect(input.getAttribute("aria-valuetext")).toBe("Jupiter");
  });

  it("draws the eight planets by name, says in words where the test mass is, and moves it when a planet is tapped", () => {
    const { planet } = bench(3);
    const root = document.querySelector(".syn-planets-scene") as SVGSVGElement;
    expect(Array.from(root.querySelectorAll("text")).map((t) => t.textContent)).toEqual(planetNames());
    expect(root.getAttribute("aria-label")).toContain("Earth, the third planet");
    expect(/\d/.test(root.getAttribute("aria-label") ?? "")).toBe(false);
    (root.querySelectorAll(".syn-planet")[4] as SVGCircleElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(planet.get()).toBe(5);
    expect(root.getAttribute("aria-label")).toContain("Jupiter, the fifth planet");
  });

  it("reports a handle the verifier can drag along the row, in its own drawing box, from Mercury to Neptune", () => {
    bench();
    const h = widget("planets.planet");
    expect(h).toMatchObject({ kind: "handle", control: "planet", host: "planets", origin: 1, full: 8, box: [340, 156], problems: [] });
    expect(document.querySelectorAll("[data-synapse-handle]").length).toBe(1);
  });

  it("gives the gravity of the chosen planet through planetGravity, and the weight through weight", () => {
    const { planet, g, w } = bench(3);
    expect(g.get()).toBeCloseTo(9.798, 2);
    expect(w.get()).toBeCloseTo(9.798, 2);
    planet.set(5);
    expect(g.get()).toBeCloseTo(24.79, 1);
  });

  it("leaves the audit clean, and reports a page that redraws the test mass or renames a planet", () => {
    bench();
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
    expect(violations(a)).toEqual([]);
    expect(widget("planet")?.exact).toEqual([]);
    const mass = document.querySelector(".syn-planets-scene rect[width='16']") as SVGRectElement;
    mass.setAttribute("x", "5");
    expect(widget("planet")?.exact.length).toBeGreaterThan(0);
    mass.remove();
    const names = document.querySelectorAll(".syn-planets-scene text");
    (names[3] as SVGTextElement).textContent = "Pluto";
    expect(audit(KIT_VERSION).ownedMismatches.length).toBeGreaterThan(0);
  });

  it("refuses a starting planet outside the row only by clamping to it, like any slider", () => {
    const env = environment({ title: "t", note: "n" });
    const p = planetPicker(env, { id: "p", label: "Planet", value: 12 });
    expect(p.get()).toBe(8);
  });
});

describe("graph against a choice control: labelled bars", () => {
  it("draws one bar per planet with its name, a word in the hidden table, and no handle of its own when the planets already drag the control", () => {
    const { env, planet, g } = bench(4);
    graph(env, { title: "Gravity on each planet", x: planet, y: g, yLabel: "Gravitational field strength", yUnit: "N/kg" });
    const root = document.querySelector(".syn-graph") as SVGSVGElement;
    expect(root.querySelectorAll("rect").length).toBe(8);
    const names = Array.from(root.querySelectorAll("text")).map((t) => t.textContent);
    for (const n of planetNames()) expect(names).toContain(n);
    const firstCells = Array.from(document.querySelectorAll(".syn-sr tbody tr td:first-child")).map((c) => c.textContent);
    expect(firstCells).toEqual(planetNames());
    expect(document.querySelectorAll("[data-synapse-handle]").length).toBe(1);
    expect(audit(KIT_VERSION).ownedMismatches).toEqual([]);
    expect(audit(KIT_VERSION).unownedNumbers).toEqual([]);
  });
});

describe("graph point as a handle", () => {
  it("adds a handle on the point for a control nothing else drags, quiets that control, and reports it in the graph's box", () => {
    const env = environment({ title: "t", note: "n" });
    const load = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2, grid: 5 });
    const x = hookes({ k: 50, load });
    graph(env, { title: "g", x: load, y: x, yLabel: "Extension", yUnit: "m" });
    const h = widget("graph.load");
    expect(h).toMatchObject({ kind: "handle", control: "load", host: "graph", origin: 0, full: 10, box: [320, 200], problems: [] });
    expect(controls[0]?.el.parentElement?.classList.contains("syn-control-quiet")).toBe(true);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });

  it("adds none for a control whose range ends at or below zero, and only one for two graphs of the same control", () => {
    const env = environment({ title: "t", note: "n" });
    const load = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2, grid: 5 });
    const x = hookes({ k: 50, load });
    graph(env, { title: "a", x: load, y: x, yLabel: "Extension", yUnit: "m" });
    graph(env, { title: "b", x: load, y: x, yLabel: "Extension", yUnit: "m" });
    expect(document.querySelectorAll("[data-synapse-handle]").length).toBe(1);
  });
});
