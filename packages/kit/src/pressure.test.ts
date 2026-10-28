import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { environment } from "./environment";
import { KIT_VERSION } from "./index";
import { observable } from "./observable";
import { pressureScene, pressureWords } from "./pressure_scene";
import { resetForTests } from "./provenance";
import { readout } from "./readout";
import { hookes } from "./science/hookes";
import { pressureDepth } from "./science/pressure_depth";
import { slider } from "./slider";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

function bench(d = 5) {
  const env = environment({ title: "Pressure", note: "Pressure in a liquid increases with depth." });
  const depth = slider(env, { id: "depth", label: "Depth", unit: "m", min: 0, max: 20, value: d });
  const pressure = pressureDepth({ depth, density: 1000, g: 9.81 });
  readout(env, { label: "Pressure", unit: "Pa", value: pressure, digits: 0 });
  return { env, depth, pressure };
}
const FULL = 200000;
const widgetOf = (id: string) => {
  const w = audit(KIT_VERSION).widgets.find((x) => x.id === id);
  return w && { ...w, problems: [...w.problems, ...w.exact] };
};
const probeY = () => Number(document.querySelector(".syn-pressure-scene circle")?.getAttribute("cy"));
const arrowLength = () => {
  const d = document.querySelector(".syn-pressure-scene path[stroke='var(--syn-indicator)']")?.getAttribute("d") ?? "";
  const n = (d.match(/-?\d+(\.\d+)?/g) ?? []).map(Number);
  return Math.abs((n[2] ?? 0) - (n[0] ?? 0));
};

describe("pressureScene: what it refuses", () => {
  it("draws only the pressure model's output, at a positive scale", () => {
    const { env, depth, pressure } = bench();
    expect(() => pressureScene(env, { pressure: observable(5) as never, full: FULL })).toThrow(TypeError);
    expect(() => pressureScene(env, { pressure: depth, full: FULL })).toThrow(TypeError); // a control, not the model
    expect(() => pressureScene(env, { pressure: hookes({ k: 50, load: depth }) as never, full: FULL })).toThrow(TypeError); // another model
    for (const full of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, "2e5" as unknown as number]) expect(() => pressureScene(env, { pressure, full })).toThrow(RangeError);
    pressureScene(env, { pressure, full: FULL });
  });
});

describe("pressureScene: the picture follows the number, in words", () => {
  it("puts the probe deeper and makes the arrows longer as the pressure rises, and says so in words", () => {
    const { env, depth, pressure } = bench(0);
    pressureScene(env, { pressure, full: FULL });
    const note = () => document.querySelector(".syn-pressure-note")?.textContent ?? "";
    expect(note()).toBe(pressureWords(0));
    const top = { y: probeY(), len: arrowLength() };
    depth.set(10);
    expect(probeY()).toBeGreaterThan(top.y);
    expect(arrowLength()).toBeGreaterThan(top.len);
    expect(note()).toBe(pressureWords(pressure.get() / FULL));
    depth.set(20);
    expect(probeY()).toBeLessThanOrEqual(240);
    expect(note()).toBe(pressureWords(1));
    for (const fr of [0, 0.2, 0.5, 0.9]) expect(/\d/.test(pressureWords(fr))).toBe(false);
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
  });
});

describe("pressureScene: the audit", () => {
  it("reports a clean scene with its chain, and every way a page can falsify it", () => {
    const { env, depth, pressure } = bench(10);
    pressureScene(env, { pressure, full: FULL });
    expect(widgetOf("pressure")).toMatchObject({ kind: "scene", id: "pressure", full: FULL, problems: [], chain: { kind: "model", id: "fluids.pressure_depth" } });
    const problems = () => widgetOf("pressure")?.problems ?? [];
    const probe = document.querySelector(".syn-pressure-scene circle") as SVGCircleElement;
    probe.setAttribute("cy", "45"); // the probe moved up to the surface
    expect(problems().length).toBeGreaterThan(0);
    depth.set(11);
    depth.set(10);
    expect(problems()).toEqual([]);
    const arrow = document.querySelector(".syn-pressure-scene path[stroke='var(--syn-indicator)']") as SVGPathElement;
    arrow.setAttribute("stroke", "var(--syn-bg)");
    expect(problems().length).toBeGreaterThan(0);
    arrow.setAttribute("stroke", "var(--syn-indicator)");
    expect(problems()).toEqual([]);
    const root = document.querySelector(".syn-pressure-scene") as SVGSVGElement;
    root.setAttribute("aria-label", "The probe is at the surface.");
    expect(problems().length).toBeGreaterThan(0);
  });

  it("the layout half is empty without a layout engine, and the self-check is clean", () => {
    const { env, pressure } = bench(10);
    pressureScene(env, { pressure, full: FULL });
    for (const w of audit(KIT_VERSION).widgets) expect(w.layout).toEqual([]);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });
});
