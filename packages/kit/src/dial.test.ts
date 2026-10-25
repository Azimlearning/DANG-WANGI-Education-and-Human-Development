import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { constant } from "./constant";
import { dial } from "./dial";
import { environment } from "./environment";
import { fermentationScene, observationWords } from "./fermentation_scene";
import { KIT_VERSION } from "./index";
import { observable } from "./observable";
import { resetForTests } from "./provenance";
import { readout } from "./readout";
import { respirationEnergy } from "./science/respiration_energy";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

const press = (type: string, init: Record<string, unknown> = {}) => new MouseEvent(type, { bubbles: true, button: 0, ...init });

function bench(value = 0) {
  const env = environment({ title: "Fermentation", note: "Yeast breaks glucose down without oxygen." });
  const glucose = dial(env, { id: "glucose", label: "Glucose fermented", unit: "mol", min: 0, max: 0.004, value, grid: 8 });
  const ferment = respirationEnergy({ glucose, energy_per_mole: 210 });
  const aerobic = respirationEnergy({ glucose, energy_per_mole: 2898 });
  readout(env, { label: "Energy from fermentation", unit: "kJ", value: ferment, digits: 3 });
  readout(env, { label: "Energy if aerobic", unit: "kJ", value: aerobic, digits: 3 });
  return { env, glucose, ferment, aerobic };
}
const knob = () => document.querySelector<HTMLElement>("[data-synapse-dial='glucose']") as HTMLElement;
const input = () => document.querySelector<HTMLInputElement>("input[data-synapse-control='glucose']") as HTMLInputElement;
const widgetOf = (id: string) => {
  const w = audit(KIT_VERSION).widgets.find((x) => x.id === id);
  return w && { ...w, problems: [...w.problems, ...w.exact] }; // the structural half and the exact-attributes half, together
};
/** Put the knob at (100, 100) with a radius of 48, so a pointer at angle a (clockwise from straight up) is at (100 + 40 sin a, 100 - 40 cos a). */
function place() {
  knob().getBoundingClientRect = () => ({ left: 52, top: 52, right: 148, bottom: 148, width: 96, height: 96, x: 52, y: 52, toJSON: () => ({}) }) as DOMRect;
}
const at = (deg: number) => ({ clientX: 100 + 40 * Math.sin((deg * Math.PI) / 180), clientY: 100 - 40 * Math.cos((deg * Math.PI) / 180) });

describe("dial: what it refuses", () => {
  it("needs 2 to 40 steps, a start on a step, a unique id and a real range", () => {
    const env = environment({ title: "t", note: "n" });
    const base = { id: "a", label: "Amount", unit: "mol", min: 0, max: 0.004, value: 0 };
    for (const grid of [1, 41, 2.5, 0, -3, Number.NaN]) expect(() => dial(env, { ...base, id: `g${grid}`, grid })).toThrow(RangeError);
    for (const value of [0.0003, 0.0015, 0.0035]) expect(() => dial(env, { ...base, id: `v${value}`, grid: 4, value })).toThrow(RangeError);
    dial(env, { ...base, grid: 8 });
    expect(() => dial(env, { ...base, grid: 8 })).toThrow(RangeError);
    expect(() => dial(env, { ...base, id: "b", min: 1, max: 1, grid: 8 })).toThrow(RangeError);
  });
});

describe("dial: it is a control exactly as a slider is, turned like a knob", () => {
  it("keeps the range input declared and named, snaps what a script sets, and hides the knob from assistive technology", () => {
    const { glucose } = bench();
    expect(input().getAttribute("data-synapse-control")).toBe("glucose");
    expect(input().getAttribute("aria-valuetext")).toBe("0 mol");
    glucose.set(0.0013);
    expect(glucose.get()).toBe(0.0015);
    glucose.set(99);
    expect(glucose.get()).toBe(0.004);
    expect(knob().getAttribute("aria-hidden")).toBe("true");
    expect(knob().tabIndex).toBe(-1);
  });

  it("follows the pointer's angle: the first mark at the lower left, the last at the lower right, and the gap goes to the nearer end", () => {
    const { glucose } = bench(0.002);
    place();
    knob().dispatchEvent(press("pointerdown", at(-135)));
    expect(glucose.get()).toBe(0);
    knob().dispatchEvent(press("pointermove", at(0)));
    expect(glucose.get()).toBe(0.002);
    knob().dispatchEvent(press("pointermove", at(67.5)));
    expect(glucose.get()).toBe(0.003);
    knob().dispatchEvent(press("pointermove", at(135)));
    expect(glucose.get()).toBe(0.004);
    knob().dispatchEvent(press("pointermove", at(170))); // the gap at the bottom, nearer the last mark
    expect(glucose.get()).toBe(0.004);
    knob().dispatchEvent(press("pointermove", at(-170)));
    expect(glucose.get()).toBe(0);
    knob().dispatchEvent(press("pointerup", at(-170)));
    knob().dispatchEvent(press("pointermove", at(0)));
    expect(glucose.get()).toBe(0); // not turning any more
    expect(input().value).toBe("0");
  });

  it("the mark points where the value says, and the range input moves it back", () => {
    const { glucose } = bench(0);
    const mark = knob().querySelector(".syn-dial-mark") as HTMLElement;
    expect(mark.getAttribute("style")).toBe("transform:rotate(-135.00deg)");
    glucose.set(0.004);
    expect(mark.getAttribute("style")).toBe("transform:rotate(135.00deg)");
    input().value = "0.002";
    input().dispatchEvent(new Event("input", { bubbles: true }));
    expect(mark.getAttribute("style")).toBe("transform:rotate(0.00deg)");
  });
});

describe("dial: the audit", () => {
  it("is reported with no problems, and a knob a page moved, hid, restyled or marked is reported", () => {
    bench();
    expect(widgetOf("glucose")).toMatchObject({ kind: "dial", problems: [], layout: [] });
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    expect(a.forbidden).toEqual([]);
    (knob().querySelector(".syn-dial-mark") as HTMLElement).setAttribute("style", "transform:rotate(90deg)");
    expect(widgetOf("glucose")?.problems.length).toBeGreaterThan(0);
    (knob().querySelector(".syn-dial-mark") as HTMLElement).setAttribute("style", "transform:rotate(-135.00deg)");
    expect(widgetOf("glucose")?.problems).toEqual([]);
    knob().setAttribute("class", "syn-dial other");
    expect(widgetOf("glucose")?.problems.length).toBeGreaterThan(0);
    knob().setAttribute("class", "syn-dial");
    knob().style.opacity = "0.1";
    expect(audit(KIT_VERSION).foreign.some((f) => f.what.includes("inline style"))).toBe(true);
    expect(violations(audit(KIT_VERSION))).toEqual([]); // verifier only: the student's own browser does not blank the page for it
  });
});

describe("fermentationScene: what it refuses", () => {
  it("draws only a mol control and the respiration-energy model fed by that same control, at a scale that holds the control's range", () => {
    const { env, glucose, ferment } = bench();
    expect(() => fermentationScene(env, { fermented: observable(0.001) as never, energy: ferment, full: 0.004 })).toThrow(TypeError);
    expect(() => fermentationScene(env, { fermented: glucose, energy: observable(1) as never, full: 0.004 })).toThrow(TypeError);
    expect(() => fermentationScene(env, { fermented: glucose, energy: glucose, full: 0.004 })).toThrow(TypeError);
    expect(() => fermentationScene(env, { fermented: ferment, energy: ferment, full: 0.004 })).toThrow(TypeError);
    // an energy model fed by another amount than the one drawn
    const other = constant(0.003, { label: "Another amount", unit: "mol" });
    expect(() => fermentationScene(env, { fermented: glucose, energy: respirationEnergy({ glucose: other, energy_per_mole: 210 }), full: 0.004 })).toThrow(TypeError);
    for (const full of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, "0.004" as unknown as number]) expect(() => fermentationScene(env, { fermented: glucose, energy: ferment, full })).toThrow(RangeError);
    expect(() => fermentationScene(env, { fermented: glucose, energy: ferment, full: 0.003 })).toThrow(RangeError);
    fermentationScene(env, { fermented: glucose, energy: ferment, full: 0.004 });
  });
});

describe("fermentationScene: the picture follows the numbers, in words", () => {
  it("shows nothing until glucose is fermented, then bubbles, a cloudy limewater A, a warmer tube A, and leaves tube B alone", () => {
    const { env, glucose, ferment } = bench(0);
    fermentationScene(env, { fermented: glucose, energy: ferment, full: 0.004 });
    const root = document.querySelector(".syn-fermentation") as SVGSVGElement;
    const clouds = () => Array.from(root.querySelectorAll("rect")).filter((r) => r.getAttribute("fill") === "var(--syn-card)" || r.getAttribute("fill") === "var(--syn-cloud)");
    const fills = () => clouds().map((r) => r.getAttribute("fill"));
    const radii = () => Array.from(root.querySelectorAll("circle")).map((c) => c.getAttribute("r"));
    expect(radii().every((r) => r === "0")).toBe(true);
    expect(fills()).toEqual(["var(--syn-card)", "var(--syn-card)"]);
    expect(document.querySelector("[data-synapse-observations]")?.textContent).toBe(observationWords(0));
    glucose.set(0.0005);
    expect(fills()).toEqual(["var(--syn-cloud)", "var(--syn-card)"]);
    expect(radii().slice(0, 5).filter((r) => r === "3")).toHaveLength(1);
    expect(radii().slice(5).every((r) => r === "0")).toBe(true); // tube B never bubbles
    glucose.set(0.004);
    expect(radii().slice(0, 5).every((r) => r === "3")).toBe(true);
    expect(root.getAttribute("aria-label")).toContain("limewater has turned cloudy");
    expect(/\d/.test(root.getAttribute("aria-label") ?? "")).toBe(false);
    expect(document.querySelector("[data-synapse-observations]")?.textContent).toBe(observationWords(5));
    expect(observationWords(5)).toContain("plenty of bubbles");
    expect(observationWords(1)).toContain("a few bubbles");
    expect(observationWords(3)).toContain("steady bubbling");
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
  });

  it("describes the observations in words only", () => {
    expect(/\d/.test(observationWords(2))).toBe(false);
    expect(observationWords(2)).toContain("smells of ethanol");
    expect(observationWords(0)).toContain("Nothing has happened");
  });
});

describe("fermentationScene: the audit", () => {
  it("reports a clean scene with its chains, and every way a page can falsify it", () => {
    const { env, glucose, ferment } = bench(0.002);
    fermentationScene(env, { fermented: glucose, energy: ferment, full: 0.004 });
    const w = widgetOf("fermentation");
    expect(w).toMatchObject({ kind: "scene", id: "fermentation", full: 0.004, problems: [], chain: { kind: "model", id: "biology.respiration_energy" }, sourceChain: { kind: "control", id: "glucose" } });
    const root = document.querySelector(".syn-fermentation") as SVGSVGElement;
    const problems = () => widgetOf("fermentation")?.problems ?? [];
    const cloud = Array.from(root.querySelectorAll("rect")).find((r) => r.getAttribute("fill") === "var(--syn-cloud)") as SVGElement;
    cloud.setAttribute("fill", "var(--syn-card)");
    expect(problems().length).toBeGreaterThan(0);
    glucose.set(0.001);
    glucose.set(0.002);
    expect(problems()).toEqual([]);
    root.querySelector("circle")?.setAttribute("r", "0");
    expect(problems().length).toBeGreaterThan(0);
    glucose.set(0.001);
    glucose.set(0.002);
    root.querySelector("rect")?.setAttribute("fill-opacity", "0");
    expect(problems().length).toBeGreaterThan(0);
    root.querySelector("rect")?.removeAttribute("fill-opacity");
    const extra = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    root.appendChild(extra);
    expect(problems().length).toBeGreaterThan(0);
    root.removeChild(extra);
    expect(problems()).toEqual([]);
    root.querySelector("text")!.textContent = "B";
    expect(audit(KIT_VERSION).ownedMismatches.length).toBeGreaterThan(0);
  });

  it("the layout half is empty without a layout engine, and the student's self-check acts on structure only", () => {
    const { env, glucose, ferment } = bench(0.002);
    fermentationScene(env, { fermented: glucose, energy: ferment, full: 0.004 });
    for (const w of audit(KIT_VERSION).widgets) expect(w.layout).toEqual([]);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });
});
