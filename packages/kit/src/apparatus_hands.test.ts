import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { apparatus, gripPoint, gripValue } from "./apparatus";
import { APPARATUS } from "./apparatus_catalogue";
import { environment } from "./environment";
import { KIT_VERSION } from "./index";
import { resetForTests, widgets } from "./provenance";
import { ph } from "./science/ph";
import { slider } from "./slider";

// The hands-on bench (W17, D-69, D-70): grips on the drawing and items dropped onto a part.

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

const point = (type: string, x: number, y: number) => new MouseEvent(type, { clientX: x, clientY: y, button: 0, bubbles: true });
const box = (el: Element, r: { left: number; top: number; width: number; height: number }) => {
  (el as HTMLElement).getBoundingClientRect = () => ({ ...r, x: r.left, y: r.top, right: r.left + r.width, bottom: r.top + r.height, toJSON: () => ({}) }) as DOMRect;
};
const grip = (id: string) => document.querySelector(`[data-synapse-handle='${id}']`) as SVGCircleElement;
const input = (id: string) => document.querySelector(`[data-synapse-control='${id}']`) as HTMLInputElement;

function beakerBench(value = 50) {
  const env = environment({ title: "Bench", note: "Apparatus." });
  const water = slider(env, { id: "water", label: "Water", unit: "cm3", min: 0, max: 100, value, grid: 10 });
  const svg = apparatus(env, { kind: "beaker", label: "Water", channels: { level: { value: water, full: 100 } } });
  box(svg, { left: 0, top: 0, width: 120, height: 140 }); // one pixel per drawing unit
  return { env, water, svg };
}

describe("grips", () => {
  it("a channel bound to a slider gets a grip where the catalogue says, hidden from assistive technology; one bound to a model's output gets none", () => {
    const env = environment({ title: "Bench", note: "Apparatus." });
    const water = slider(env, { id: "water", label: "Water", unit: "cm3", min: 0, max: 100, value: 50, grid: 10 });
    const h = slider(env, { id: "h_conc", label: "Hydrogen ions", unit: "mol/dm3", min: 0.001, max: 1, value: 0.1, grid: 10 });
    const acid = ph({ h_conc: h });
    apparatus(env, { kind: "beaker", label: "Water", channels: { level: { value: water, full: 100 } } });
    apparatus(env, { kind: "syringe", label: "Gas", channels: { volume: { value: acid, full: 14 } } });
    const grips = document.querySelectorAll("[data-synapse-handle]");
    expect(grips.length).toBe(1);
    expect(grips[0]?.getAttribute("data-synapse-handle")).toBe("beaker-0.level");
    expect(grips[0]?.getAttribute("aria-hidden")).toBe("true");
    const w = widgets.find((x) => x.kind === "handle");
    expect(w?.control).toBe("water");
    expect(w?.grab).toEqual(APPARATUS.beaker?.grabs?.level);
    expect(document.querySelectorAll(".syn-app-hint").length).toBe(1);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
    const record = audit(KIT_VERSION).widgets.find((x) => x.kind === "handle") as Record<string, unknown>;
    expect(record.control).toBe("water");
    expect(record.grab).toEqual({ from: [60, 130], to: [60, 38] });
  });

  it("dragging the grip moves the slider to the step nearest the pointer, both ways, and only while held", () => {
    const { water } = beakerBench(50);
    const g = grip("beaker-0.level");
    expect([g.getAttribute("cx"), g.getAttribute("cy")]).toEqual(["60.0", "84.0"]);
    g.dispatchEvent(point("pointerdown", 60, 84));
    expect(water.get()).toBe(50); // a press alone moves nothing
    g.dispatchEvent(point("pointermove", 60, 38));
    expect(water.get()).toBe(100);
    g.dispatchEvent(point("pointermove", 60, 200));
    expect(water.get()).toBe(0);
    g.dispatchEvent(point("pointermove", 60, 130 - 0.37 * 92));
    expect(water.get()).toBe(40);
    g.dispatchEvent(point("pointerup", 60, 130 - 0.37 * 92));
    expect(input("water").value).toBe("40");
    expect(g.getAttribute("cy")).toBe((130 - 0.4 * 92).toFixed(1));
    g.dispatchEvent(point("pointermove", 60, 38));
    expect(water.get()).toBe(40);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });

  it("the ramp's grip turns about its pivot, in degrees", () => {
    const env = environment({ title: "Bench", note: "Apparatus." });
    const tilt = slider(env, { id: "tilt", label: "Angle", unit: "deg", min: 0, max: 60, value: 0, grid: 12 });
    const svg = apparatus(env, { kind: "ramp", label: "Slope", channels: { angle: { value: tilt } } });
    box(svg, { left: 0, top: 0, width: 120, height: 140 });
    const g = grip("ramp-0.angle");
    g.dispatchEvent(point("pointerdown", 65, 126));
    const [x, y] = gripPoint({ pivot: [10, 126], radius: 55 }, 31);
    g.dispatchEvent(point("pointermove", x, y));
    expect(tilt.get()).toBe(30);
    g.dispatchEvent(point("pointerup", x, y));
  });

  it("every grab in the catalogue maps back to the value it was drawn at", () => {
    for (const [kind, info] of Object.entries(APPARATUS)) {
      for (const [channel, g] of Object.entries(info.grabs ?? {})) {
        expect(info.channels[channel], `${kind}.${channel}`).toBeDefined();
        const values = "pivot" in g ? [0, 15, 30, 60] : [0, 0.25, 0.5, 1];
        for (const v of values) {
          const [x, y] = gripPoint(g, v);
          expect(gripValue(g, x, y)).toBeCloseTo(v, 9);
        }
      }
    }
  });

  it("a grip a page switches off, hides or moves is reported", () => {
    beakerBench(50);
    const g = grip("beaker-0.level");
    g.setAttribute("style", "pointer-events:none");
    expect(violations(audit(KIT_VERSION)).length).toBeGreaterThan(0);
    g.removeAttribute("style");
    g.setAttribute("cy", "10");
    expect(audit(KIT_VERSION).widgets.find((w) => w.kind === "apparatus")?.exact.length).toBeGreaterThan(0);
  });
});

function cupsBench(value = 1) {
  const env = environment({ title: "Bench", note: "Apparatus." });
  const cups = slider(env, { id: "cups", label: "Water", unit: "kg", min: 0, max: 2, value, grid: 4, snap: true });
  apparatus(env, { kind: "beaker", label: "Water", channels: { level: { value: cups, full: 2 } }, drop: { value: cups, item: "Cup of water" } });
  return { env, cups };
}
const zone = () => document.querySelector("[data-synapse-dropzone='cups']") as HTMLDivElement;
const tray = () => document.querySelector("[data-synapse-tray='cups']") as HTMLDivElement;
const items = (state: string) => Array.from(document.querySelectorAll(`[data-synapse-drag='cups'][data-state='${state}']`)) as HTMLButtonElement[];

describe("drops", () => {
  it("items dropped onto the part are steps of its slider, by pointer, by press and from the slider", () => {
    const { cups } = cupsBench(0.5);
    expect(items("hung").length).toBe(1);
    expect(items("tray").length).toBe(3);
    expect(zone().contains(document.querySelector("svg"))).toBe(true);
    items("tray")[0]?.click();
    expect(cups.get()).toBe(1);
    box(zone(), { left: 0, top: 0, width: 150, height: 200 });
    const t = items("tray")[0] as HTMLButtonElement;
    t.dispatchEvent(point("pointerdown", 400, 400));
    t.dispatchEvent(point("pointermove", 60, 60));
    expect(zone().classList.contains("syn-over")).toBe(true);
    t.dispatchEvent(point("pointerup", 60, 60));
    expect(cups.get()).toBe(1.5);
    expect(items("hung").length).toBe(3);
    const back = items("hung")[0] as HTMLButtonElement;
    back.dispatchEvent(point("pointerdown", 60, 60));
    back.dispatchEvent(point("pointermove", 400, 400));
    back.dispatchEvent(point("pointerup", 400, 400));
    expect(cups.get()).toBe(1);
    input("cups").value = "0";
    input("cups").dispatchEvent(new Event("input", { bubbles: true }));
    expect(items("hung").length).toBe(0);
    expect(tray().querySelectorAll("button").length).toBe(4);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
    expect(audit(KIT_VERSION).widgets.find((w) => w.kind === "masses")).toMatchObject({ id: "cups", masses: 4 });
  });

  it("the item's name is the Plan's, the words around it are the Kit's, in both languages", () => {
    cupsBench(0.5);
    expect(tray().textContent).toContain("Cup of water");
    expect(items("tray")[0]?.getAttribute("aria-label")).toBe("Cup of water B, in the tray. Press Enter to move it.");
    expect(zone().getAttribute("aria-label")).toBe("Water, one added. Drop items here.");
    resetForTests();
    document.body.innerHTML = "";
    const env = environment({ title: "Meja", note: "Radas.", lang: "ms" });
    const cups = slider(env, { id: "cups", label: "Air", unit: "kg", min: 0, max: 2, value: 0, grid: 4, snap: true });
    apparatus(env, { kind: "beaker", label: "Air", channels: { level: { value: cups, full: 2 } }, drop: { value: cups, item: "Secawan air" } });
    expect(zone().getAttribute("aria-label")).toBe("Air, tiada yang ditambah. Letakkan item di sini.");
  });

  it("refuses a drop that is not a slider of 2 to 8 steps starting on a step, or has no item, or a second drop for one slider", () => {
    const env = environment({ title: "Bench", note: "Apparatus." });
    const many = slider(env, { id: "many", label: "Many", unit: "g", min: 0, max: 9, value: 0, grid: 9 });
    const odd = slider(env, { id: "odd", label: "Odd", unit: "g", min: 0, max: 4, value: 1.5, grid: 4 });
    const ok = slider(env, { id: "ok", label: "Ok", unit: "g", min: 0, max: 4, value: 1, grid: 4, snap: true });
    const h = slider(env, { id: "h_conc", label: "H", unit: "mol/dm3", min: 0.001, max: 1, value: 0.1, grid: 10 });
    const acid = ph({ h_conc: h });
    const part = (drop: { value: unknown; item: string }) => () =>
      apparatus(env, { kind: "beaker", label: "B", channels: { level: { value: ok, full: 4 } }, drop: drop as { value: typeof ok; item: string } });
    expect(part({ value: many, item: "Scoop" })).toThrow(/2 to 8 steps/);
    expect(part({ value: odd, item: "Scoop" })).toThrow(/start on a step/);
    expect(part({ value: acid, item: "Scoop" })).toThrow(/bound to a slider/);
    expect(part({ value: ok, item: " " })).toThrow(/item of 1 to 40/);
    part({ value: ok, item: "Scoop" })();
    expect(part({ value: ok, item: "Scoop" })).toThrow(/already has items/);
  });

  it("an item a page moves out of its place, or a drop place it takes apart, is reported", () => {
    cupsBench(0.5);
    const t = items("tray")[0] as HTMLButtonElement;
    zone().appendChild(t);
    expect(violations(audit(KIT_VERSION)).length).toBeGreaterThan(0);
  });
});
