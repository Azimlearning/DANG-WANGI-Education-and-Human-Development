import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { apparatus, band, phBand, phColour, speedStep } from "./apparatus";
import { APPARATUS, MAX_APPARATUS_PARTS } from "./apparatus_catalogue";
import { constant } from "./constant";
import { environment } from "./environment";
import { KIT_VERSION, manifestEntries } from "./index";
import { observable } from "./observable";
import { resetForTests } from "./provenance";
import { ph } from "./science/ph";
import { slider } from "./slider";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

/** A page with one slider per channel, each in the unit its channel accepts, and the part bound to them. */
function onePart(kind: string, lang: "en" | "ms" = "en") {
  const env = environment({ title: "Bench", note: "Apparatus.", lang });
  const sliders: Record<string, ReturnType<typeof slider>> = {};
  const channels: Record<string, { value: ReturnType<typeof slider>; full?: number }> = {};
  for (const [name, ch] of Object.entries(APPARATUS[kind]!.channels)) {
    const unit = ch.units?.[0] ?? "cm3";
    const max = ch.type === "angle" ? 60 : ch.type === "ph" ? 14 : 100;
    const s = slider(env, { id: name, label: name, unit, min: 0, max, value: max / 2 });
    sliders[name] = s;
    channels[name] = ch.type === "fraction" ? { value: s, full: 100 } : { value: s };
  }
  const svg = apparatus(env, { kind, label: "Sample", channels });
  return { env, sliders, svg };
}
const dynamicSnapshot = (svg: SVGSVGElement): string =>
  Array.from(svg.querySelectorAll("*"))
    .map((e) => Array.from(e.attributes).map((a) => `${a.name}=${a.value}`).join(","))
    .join("|");

describe("the catalogue", () => {
  it("every part draws, in both languages, with words and no digit in them, and the audit is clean", () => {
    for (const kind of Object.keys(APPARATUS)) {
      for (const lang of ["en", "ms"] as const) {
        document.body.innerHTML = "";
        resetForTests();
        const { svg } = onePart(kind, lang);
        const words = svg.getAttribute("aria-label") ?? "";
        expect(words.length, kind).toBeGreaterThan(5);
        expect(/\d/.test(words), `${kind} ${lang}: ${words}`).toBe(false);
        expect(svg.querySelectorAll("*").length, kind).toBeGreaterThan(1);
        const a = audit(KIT_VERSION);
        expect(a.unownedNumbers, kind).toEqual([]);
        expect(a.unownedAttributeNumbers, kind).toEqual([]);
        expect(a.ownedMismatches, kind).toEqual([]);
        expect(violations(a), kind).toEqual([]);
      }
    }
  }, 30_000); // 26 parts in two languages with a full audit each: about 5 s on this machine, more under load

  it("every channel moves the drawing, and the drawing goes back when the value does", () => {
    for (const kind of Object.keys(APPARATUS)) {
      document.body.innerHTML = "";
      resetForTests();
      const { sliders, svg } = onePart(kind);
      for (const [name, s] of Object.entries(sliders)) {
        const before = dynamicSnapshot(svg);
        const start = s.get();
        s.set(APPARATUS[kind]!.channels[name]!.type === "angle" ? 55 : APPARATUS[kind]!.channels[name]!.type === "ph" ? 1 : 98);
        expect(dynamicSnapshot(svg), `${kind}.${name} changed nothing`).not.toBe(before);
        s.set(start);
        expect(dynamicSnapshot(svg), `${kind}.${name} did not come back`).toBe(before);
      }
    }
  });

  it("a label with a number in it is the Plan's copy, and the spoken sentence around it is owned by the Kit", () => {
    const env = environment({ title: "Bench", note: "Apparatus." });
    const share = slider(env, { id: "share", label: "Share", unit: "%", min: 0, max: 100, value: 75 });
    const svg = apparatus(env, { kind: "gauge", label: "Share of chlorine-35", channels: { value: { value: share, full: 100 } } });
    expect(svg.getAttribute("aria-label")).toContain("chlorine-35");
    expect(violations(audit(KIT_VERSION))).toEqual([]);
    svg.setAttribute("aria-label", "Gauge, Share of chlorine-37: reading high.");
    expect(violations(audit(KIT_VERSION)).length).toBeGreaterThan(0);
  });

  it("is in the built manifest as one component and its parts have no number in their names", () => {
    expect(manifestEntries.some((e) => e.id === "apparatus")).toBe(true);
    for (const [kind, info] of Object.entries(APPARATUS)) {
      expect(/^[a-z_]+$/.test(kind)).toBe(true);
      expect(Object.keys(info.channels).length).toBeGreaterThan(0);
      expect(Object.values(info.channels).some((c) => !c.optional), kind).toBe(true);
    }
  });

  it("the word bands, the motion steps and the indicator colours", () => {
    expect([0, 0.1, 0.5, 0.8, 1].map(band)).toEqual([0, 1, 2, 3, 4]);
    expect([0, 0.1, 0.5, 0.8, 1].map(speedStep)).toEqual([0, 1, 3, 4, 4]);
    expect([1, 5, 7, 9, 13].map(phBand)).toEqual([0, 1, 2, 3, 4]);
    expect(phColour(1)).not.toBe(phColour(13));
    expect(phColour(-3)).toBe(phColour(0));
  });
});

describe("apparatus: what it refuses", () => {
  it("an unknown part or channel, a missing channel, a constant, a loose number, a bad scale, an empty label", () => {
    const env = environment({ title: "t", note: "n" });
    const v = slider(env, { id: "v", label: "Volume", unit: "cm3", min: 0, max: 100, value: 50 });
    expect(() => apparatus(env, { kind: "teapot", label: "Tea", channels: {} })).toThrow(TypeError);
    expect(() => apparatus(env, { kind: "beaker", label: "Water", channels: { level: { value: v, full: 100 }, colour: { value: v, full: 1 } } })).toThrow(TypeError);
    expect(() => apparatus(env, { kind: "beaker", label: "Water", channels: {} })).toThrow(TypeError);
    expect(() => apparatus(env, { kind: "beaker", label: "Water", channels: { level: { value: constant(50, { label: "Fixed", unit: "cm3" }) as never, full: 100 } } })).toThrow(TypeError);
    expect(() => apparatus(env, { kind: "beaker", label: "Water", channels: { level: { value: observable(5) as never, full: 100 } } })).toThrow(TypeError);
    for (const full of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, undefined]) expect(() => apparatus(env, { kind: "beaker", label: "Water", channels: { level: { value: v, full } } })).toThrow(RangeError);
    expect(() => apparatus(env, { kind: "beaker", label: " ", channels: { level: { value: v, full: 100 } } })).toThrow(RangeError);
    apparatus(env, { kind: "beaker", label: "Water", channels: { level: { value: v, full: 100 } } });
  });

  it("at most four parts on one bench", () => {
    const env = environment({ title: "t", note: "n" });
    const v = slider(env, { id: "v", label: "Volume", unit: "cm3", min: 0, max: 100, value: 50 });
    for (let i = 0; i < MAX_APPARATUS_PARTS; i++) apparatus(env, { kind: "beaker", label: `Beaker ${"ABCD"[i]}`, channels: { level: { value: v, full: 100 } } });
    expect(() => apparatus(env, { kind: "beaker", label: "One too many", channels: { level: { value: v, full: 100 } } })).toThrow(RangeError);
    expect(document.querySelectorAll(".syn-app-bench").length).toBe(1);
    expect(document.querySelectorAll(".syn-app").length).toBe(MAX_APPARATUS_PARTS);
  });
});

describe("apparatus: the audit", () => {
  it("reports one widget per channel with its part, type, units, source and scale", () => {
    const env = environment({ title: "t", note: "n" });
    const conc = slider(env, { id: "conc", label: "Concentration", unit: "mol/dm3", min: 0.0001, max: 1, value: 0.01 });
    const acid = ph({ h_conc: conc });
    const heat = slider(env, { id: "heat", label: "Heat", unit: "W", min: 0, max: 500, value: 100 });
    apparatus(env, { kind: "indicator", label: "Acid", channels: { ph: { value: acid } } });
    apparatus(env, { kind: "burner", label: "Burner", channels: { heat: { value: heat, full: 500 } } });
    const ws = audit(KIT_VERSION).widgets.filter((w) => w.kind === "apparatus");
    expect(ws.map((w) => w.id)).toEqual(["indicator-0.ph", "burner-1.heat"]);
    expect(ws[0]).toMatchObject({ part: "indicator", channel: "ph", channelType: "ph", units: ["pH"], chain: { kind: "model", id: "chemistry.ph_from_h" }, problems: [] });
    expect(ws[1]).toMatchObject({ part: "burner", channel: "heat", channelType: "fraction", full: 500, chain: { kind: "control", id: "heat" }, problems: [] });
  });

  it("every way a page can falsify a part is reported, and the part recovers when the Kit redraws", () => {
    const { sliders, svg } = onePart("beaker");
    const problems = () => audit(KIT_VERSION).widgets.filter((w) => w.kind === "apparatus").flatMap((w) => [...w.problems, ...w.exact]);
    expect(problems()).toEqual([]);
    const liquid = svg.querySelector("rect") as SVGRectElement;
    liquid.setAttribute("y", "20"); // the beaker drawn full
    expect(problems().length).toBeGreaterThan(0);
    sliders.level!.set(51);
    sliders.level!.set(50);
    expect(problems()).toEqual([]);
    liquid.setAttribute("fill-opacity", "0"); // the liquid made invisible
    expect(problems().length).toBeGreaterThan(0);
    liquid.setAttribute("fill-opacity", "0.55");
    expect(problems()).toEqual([]);
    const extra = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    svg.appendChild(extra);
    expect(problems().length).toBeGreaterThan(0);
    svg.removeChild(extra);
    expect(problems()).toEqual([]);
    svg.setAttribute("aria-label", "An empty beaker.");
    expect(problems().length).toBeGreaterThan(0);
    sliders.level!.set(51);
    const caption = document.querySelector(".syn-app-label") as HTMLElement;
    caption.textContent = "Mercury";
    expect(audit(KIT_VERSION).ownedMismatches.length).toBeGreaterThan(0);
  });

  it("motion is by class only, so a number never changes while a part moves", () => {
    const { sliders, svg } = onePart("circuit");
    const flow = svg.querySelector(".syn-a-flow") as SVGElement;
    sliders.current!.set(0);
    expect(flow.getAttribute("class")).toContain("syn-sp0");
    sliders.current!.set(100);
    expect(flow.getAttribute("class")).toContain("syn-sp4");
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });
});
