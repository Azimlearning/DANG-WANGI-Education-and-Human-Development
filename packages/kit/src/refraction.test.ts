import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { environment } from "./environment";
import { KIT_VERSION } from "./index";
import { observable } from "./observable";
import { resetForTests } from "./provenance";
import { readout } from "./readout";
import { bendingOf, REFRACTION_FULL, refractionScene, refractionWords } from "./refraction_scene";
import { criticalAngle } from "./science/critical_angle";
import { refractionAngle } from "./science/refraction_angle";
import { slider } from "./slider";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

function bench(i = 30, n = 1.5) {
  const env = environment({ title: "Refraction", note: "A ray of light bends when it enters glass." });
  const incidence = slider(env, { id: "incidence", label: "Angle of incidence", unit: "deg", min: 0, max: 80, value: i });
  const index = slider(env, { id: "index", label: "Refractive index", unit: "ratio", min: 1, max: 2.5, value: n });
  const refraction = refractionAngle({ incidence_angle: incidence, refractive_index: index });
  readout(env, { label: "Angle of refraction", unit: "deg", value: refraction, digits: 1 });
  return { env, incidence, index, refraction };
}
const widgetOf = (id: string) => {
  const w = audit(KIT_VERSION).widgets.find((x) => x.id === id);
  return w && { ...w, problems: [...w.problems, ...w.exact] };
};
const lines = () => Array.from(document.querySelectorAll(".syn-refr-scene line")).filter((l) => l.getAttribute("stroke") === "var(--syn-indicator)");
const angleFromNormal = (l: Element): number => {
  const dx = Math.abs(Number(l.getAttribute("x2")) - Number(l.getAttribute("x1")));
  const dy = Math.abs(Number(l.getAttribute("y2")) - Number(l.getAttribute("y1")));
  return (Math.atan2(dx, dy) * 180) / Math.PI;
};

describe("bendingOf: the one rule", () => {
  it("goes straight along the normal, does not bend with no change of medium, and bends towards the normal otherwise", () => {
    expect(bendingOf(0, 0)).toBe("straight");
    expect(bendingOf(30, 30)).toBe("same");
    expect(bendingOf(30, 19.47)).toBe("bends");
  });
  it("gives every case words with no digit in them", () => {
    for (const b of ["straight", "same", "bends"] as const) expect(/\d/.test(refractionWords(b))).toBe(false);
  });
});

describe("refractionScene: what it refuses", () => {
  it("draws only a degree control and the refraction model fed by that same control", () => {
    const { env, incidence, index, refraction } = bench();
    expect(() => refractionScene(env, { incidence: observable(30) as never, refraction })).toThrow(TypeError);
    expect(() => refractionScene(env, { incidence: index, refraction })).toThrow(TypeError); // a control, but not in degrees
    expect(() => refractionScene(env, { incidence, refraction: observable(20) as never })).toThrow(TypeError);
    expect(() => refractionScene(env, { incidence, refraction: criticalAngle({ refractive_index: index }) as never })).toThrow(TypeError); // another model
    // the right model, fed by a different degree control
    const other = slider(env, { id: "other", label: "Another angle", unit: "deg", min: 0, max: 60, value: 10 });
    expect(() => refractionScene(env, { incidence, refraction: refractionAngle({ incidence_angle: other, refractive_index: index }) })).toThrow(TypeError);
    // a degree control that can go past 90
    const wide = slider(env, { id: "wide", label: "Wide angle", unit: "deg", min: 0, max: 120, value: 10 });
    expect(() => refractionScene(env, { incidence: wide, refraction: refractionAngle({ incidence_angle: wide, refractive_index: index }) })).toThrow(RangeError);
    refractionScene(env, { incidence, refraction });
  });
});

describe("refractionScene: the picture follows the numbers, in words", () => {
  it("draws the incident ray at the angle of incidence and the refracted ray at the angle of refraction, both from the normal", () => {
    const { env, incidence, refraction } = bench(30, 1.5);
    refractionScene(env, { incidence, refraction });
    const [inc, ref] = lines() as [Element, Element];
    expect(angleFromNormal(inc)).toBeCloseTo(30, 0);
    expect(angleFromNormal(ref)).toBeCloseTo(refraction.get(), 0);
    expect(refraction.get()).toBeCloseTo(19.47, 1);
    incidence.set(60);
    expect(angleFromNormal(lines()[0]!)).toBeCloseTo(60, 0);
    expect(angleFromNormal(lines()[1]!)).toBeCloseTo(refraction.get(), 0);
  });

  it("says in words what the ray does, never with a number", () => {
    const { env, incidence, index, refraction } = bench(0, 1.5);
    refractionScene(env, { incidence, refraction });
    const note = () => document.querySelector(".syn-refr-note")?.textContent ?? "";
    expect(note()).toBe(refractionWords("straight"));
    incidence.set(40);
    expect(note()).toBe(refractionWords("bends"));
    index.set(1);
    expect(note()).toBe(refractionWords("same"));
    const root = document.querySelector(".syn-refr-scene") as SVGSVGElement;
    expect(/\d/.test(root.getAttribute("aria-label") ?? "")).toBe(false);
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
  });

  it("speaks Malay on a Malay page", () => {
    document.body.innerHTML = "";
    resetForTests();
    const env = environment({ title: "Pembiasan", note: "Sinar membengkok.", lang: "ms" });
    const incidence = slider(env, { id: "incidence", label: "Sudut tuju", unit: "deg", min: 0, max: 80, value: 30 });
    const index = slider(env, { id: "index", label: "Indeks biasan", unit: "ratio", min: 1, max: 2.5, value: 1.5 });
    refractionScene(env, { incidence, refraction: refractionAngle({ incidence_angle: incidence, refractive_index: index }) });
    expect(document.querySelector(".syn-refr-note")?.textContent).toContain("Sinar membengkok ke arah garis normal");
    expect(document.querySelector(".syn-refr-scene")?.textContent).toContain("Udara");
  });
});

describe("refractionScene: the audit", () => {
  it("reports a clean scene with its chains, and every way a page can falsify it", () => {
    const { env, incidence, refraction } = bench(40, 1.5);
    refractionScene(env, { incidence, refraction });
    expect(widgetOf("refraction")).toMatchObject({
      kind: "scene",
      id: "refraction",
      full: REFRACTION_FULL,
      problems: [],
      chain: { kind: "model", id: "physics.refraction_angle" },
      sourceChain: { kind: "control", id: "incidence" },
    });
    const problems = () => widgetOf("refraction")?.problems ?? [];
    const [inc, ref] = lines() as [Element, Element];
    ref.setAttribute("x2", "200"); // the refracted ray bent the wrong way
    expect(problems().length).toBeGreaterThan(0);
    incidence.set(41);
    incidence.set(40);
    expect(problems()).toEqual([]);
    inc.setAttribute("stroke", "var(--syn-bg)"); // the incident ray painted out
    expect(problems().length).toBeGreaterThan(0);
    inc.setAttribute("stroke", "var(--syn-indicator)");
    expect(problems()).toEqual([]);
    const root = document.querySelector(".syn-refr-scene") as SVGSVGElement;
    const extra = document.createElementNS("http://www.w3.org/2000/svg", "line");
    root.appendChild(extra);
    expect(problems().length).toBeGreaterThan(0);
    root.removeChild(extra);
    expect(problems()).toEqual([]);
    root.setAttribute("aria-label", "The ray goes straight on.");
    expect(problems().length).toBeGreaterThan(0);
  });

  it("the layout half is empty without a layout engine, and the self-check is clean", () => {
    const { env, incidence, refraction } = bench(40, 1.5);
    refractionScene(env, { incidence, refraction });
    for (const w of audit(KIT_VERSION).widgets) expect(w.layout).toEqual([]);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });
});
