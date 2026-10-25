import { beforeEach, describe, expect, it } from "vitest";
import { audit, seal, violations } from "./audit";
import * as bridge from "./bridge";
import { state as bridgeState } from "./bridge";
import { constant } from "./constant";
import { conceptCheck } from "./concept_check";
import { convert } from "./convert";
import { environment } from "./environment";
import { experiment } from "./experiment";
import { graph } from "./graph";
import { hintLadder } from "./hints";
import { components, KIT_VERSION, manifestEntries, Synapse } from "./index";
import { observable } from "./observable";
import { predictCard } from "./predict_card";
import { isObservable, resetForTests } from "./provenance";
import { readout } from "./readout";
import { reset } from "./reset";
import { hookes } from "./science/hookes";
import { ohm } from "./science/ohm";
import { pressureDepth } from "./science/pressure_depth";
import { slider } from "./slider";
import { stepper } from "./stepper";
import { table } from "./table";
import { text } from "./text";
import { workedSolution } from "./worked_solution";
import { resetWatchForTests, startWatch } from "./watch";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

function spring() {
  const env = environment({ title: "Why does a spring stretch?", note: "Hang a load on a spring and it stretches.", stageText: "A spring with a load" });
  const load = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2 });
  const extension = hookes({ k: 50, load });
  const out = readout(env, { label: "Extension", unit: "m", value: extension, digits: 3 });
  return { env, load, extension, out };
}

describe("observable", () => {
  it("propagates changes to subscribers", () => {
    const a = observable(2);
    const seen: number[] = [];
    a.subscribe((v) => seen.push(v));
    a.set(5);
    a.set(5);
    expect(seen).toEqual([5]);
  });
  it("a mapped observable follows its source and is read-only", () => {
    const a = observable(2);
    const doubled = a.map((v) => v * 2);
    a.set(5);
    expect(doubled.get()).toBe(10);
    expect(() => doubled.set(0)).toThrow(TypeError);
  });
  it("is recognised by a private registry, not by shape", () => {
    expect(isObservable(observable(1))).toBe(true);
    const forged = { get: () => 1, set() {}, subscribe: () => () => {}, map() {}, __observable: true };
    expect(isObservable(forged)).toBe(false);
    expect(isObservable(3)).toBe(false);
    expect(isObservable(null)).toBe(false);
  });
});

describe("slider", () => {
  it("clamps the initial value and every write to [min, max]", () => {
    const env = environment({ title: "t", note: "n" });
    const s = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 50 });
    expect(s.get()).toBe(10);
    s.set(-4);
    expect(s.get()).toBe(0);
    s.set(Number.NaN);
    expect(s.get()).toBe(0);
  });
  it.each([
    [1.95, 20, 19],
    [6, 14, 3],
    [0, 1, 3],
    [0.001, 1, 10],
    [0, 7, 9],
  ])("has a step that reaches max exactly: min %s max %s grid %s", (min, max, grid) => {
    const env = environment({ title: "t", note: "n" });
    slider(env, { id: `s${min}${max}${grid}`, label: "L", unit: "u", min, max, grid, value: min });
    const input = document.querySelector<HTMLInputElement>(`input[data-synapse-control="s${min}${max}${grid}"]`)!;
    const step = Number(input.step);
    expect(Number.isFinite(step) && step > 0).toBe(true);
    // The last step position never lies above max (the browser could not reach max) and is within one part in 1e9 of it.
    expect(step * grid).toBeLessThanOrEqual((max - min) * (1 + 1e-13));
    expect(step * grid).toBeGreaterThan((max - min) * (1 - 1e-9));
  });
  it("is a labelled range input with a declared control id, and input events update the observable", () => {
    const env = environment({ title: "t", note: "n" });
    const s = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 1 });
    const input = document.querySelector<HTMLInputElement>('input[data-synapse-control="load"]')!;
    expect(input.type).toBe("range");
    expect(document.querySelector(`label[for="${input.id}"]`)?.textContent).toBe("Load (N)");
    input.value = "7";
    input.dispatchEvent(new Event("input"));
    expect(s.get()).toBe(7);
  });
  it("rejects min >= max, a duplicate id and a bad grid", () => {
    const env = environment({ title: "t", note: "n" });
    expect(() => slider(env, { id: "x", label: "X", unit: "u", min: 1, max: 1, value: 1 })).toThrow(RangeError);
    slider(env, { id: "a", label: "A", unit: "u", min: 0, max: 1, value: 0 });
    expect(() => slider(env, { id: "a", label: "A", unit: "u", min: 0, max: 1, value: 0 })).toThrow(/already used/);
    expect(() => slider(env, { id: "b", label: "B", unit: "u", min: 0, max: 1, value: 0, grid: 0 })).toThrow(RangeError);
  });
});

describe("readout", () => {
  it("rejects a plain number and an object that only looks like an observable", () => {
    const env = environment({ title: "t", note: "n" });
    // @ts-expect-error a plain number is not an Observable
    expect(() => readout(env, { label: "Extension", unit: "m", value: 3.2 })).toThrow(TypeError);
    const forged = { get: () => 3.2, set() {}, subscribe: () => () => {}, map() {} };
    // @ts-expect-error a look-alike is not a Kit observable
    expect(() => readout(env, { label: "Extension", unit: "m", value: forged })).toThrow(TypeError);
  });
  it("follows its observable", () => {
    const { load, out } = spring();
    expect(out.textContent).toBe("0.040 m");
    load.set(10);
    expect(out.textContent).toBe("0.200 m");
    expect(out.getAttribute("aria-live")).toBe("polite");
  });
});

describe("models", () => {
  it("hookes, ohm and pressureDepth compute their laws and follow their inputs", () => {
    const load = observable(4);
    expect(hookes({ k: 20, load }).get()).toBeCloseTo(0.2, 12);
    const v = observable(12);
    const r = constant(4, { label: "Resistance", unit: "ohm" });
    const i = ohm({ voltage: v, resistance: r });
    expect(i.get()).toBe(3);
    v.set(6);
    expect(i.get()).toBe(1.5);
    const depth = observable(2);
    const p = pressureDepth({ depth, density: 1000, g: 10 });
    expect(p.get()).toBe(20000);
    depth.set(5);
    expect(p.get()).toBe(50000);
  });
  it("refuses out-of-domain parameters and inputs, wrong input names and non-observable inputs", () => {
    expect(() => hookes({ k: 0, load: observable(1) })).toThrow(RangeError);
    expect(() => hookes({ k: 10, load: observable(-1) })).toThrow(RangeError);
    // @ts-expect-error not an observable
    expect(() => hookes({ k: 10, load: 3 })).toThrow(TypeError);
    // @ts-expect-error missing input
    expect(() => ohm({ voltage: observable(1) })).toThrow(TypeError);
    expect(() => pressureDepth({ depth: observable(1), density: -1, g: 10 })).toThrow(RangeError);
  });
  it("a model output is read-only", () => {
    expect(() => hookes({ k: 10, load: observable(1) }).set(5)).toThrow(TypeError);
  });
});

describe("provenance audit", () => {
  it("reports a grounded readout: control -> model, with its parameters", () => {
    spring();
    const a = audit(KIT_VERSION);
    expect(a.controls).toEqual([{ id: "load", label: "Load", unit: "N", min: 0, max: 10, grid: 10, default: 2, step: 1, value: 2, inputValue: "2" }]);
    expect(a.readouts).toHaveLength(1);
    const r = a.readouts[0]!;
    expect(r.displayed).toBe("0.040 m");
    expect(r.displayed).toBe(r.expected);
    expect(r.chain.kind).toBe("model");
    expect(r.chain.id).toBe("mechanics.hookes");
    expect(r.chain.params).toEqual({ k: 50 });
    expect(r.chain.inputs?.load?.kind).toBe("control");
    expect(r.chain.inputs?.load?.id).toBe("load");
    expect(a.ownedMismatches).toEqual([]);
    expect(a.unownedNumbers).toEqual([]);
  });

  it("detects a readout whose text was overwritten by hand", () => {
    const { out } = spring();
    out.textContent = "0.123 m";
    const a = audit(KIT_VERSION);
    expect(a.readouts[0]!.displayed).not.toBe(a.readouts[0]!.expected);
    expect(a.ownedMismatches.map((m) => m.tag)).toContain("output");
  });

  it("detects an edited study note and an edited slider label", () => {
    spring();
    document.querySelector(".syn-note")!.textContent = "The extension is 0.9 m";
    document.querySelector("label")!.textContent = "Load (kN)";
    const a = audit(KIT_VERSION);
    expect(a.ownedMismatches.map((m) => m.expected)).toEqual(expect.arrayContaining(["Hang a load on a spring and it stretches.", "Load (N)"]));
  });

  it("detects a number typed straight into the page, and ignores digits inside identifiers only if the element is Kit-owned", () => {
    const { env } = spring();
    const p = document.createElement("p");
    p.textContent = "Extension: 0.04 m";
    env.stage.appendChild(p);
    expect(audit(KIT_VERSION).unownedNumbers.map((u) => u.text)).toContain("Extension: 0.04 m");
    // The same text through the sanctioned path is owned, and recorded as copy.
    document.body.innerHTML = "";
    resetForTests();
    const { env: env2 } = spring();
    text(env2, "Try a load of 5 N.");
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.copy.find((c) => c.text === "Try a load of 5 N.")?.numbers).toEqual(["5"]);
  });

  it("detects a number in a spoken or tooltip attribute the Kit did not set, and accepts the ones it did", () => {
    const { env } = spring();
    expect(audit(KIT_VERSION).unownedAttributeNumbers).toEqual([]);
    const p = document.createElement("p");
    p.setAttribute("aria-label", "The extension is 0.04 m");
    env.stage.appendChild(p);
    const found = audit(KIT_VERSION).unownedAttributeNumbers;
    expect(found.map((a) => a.attribute)).toContain("aria-label");
  });

  it("reports a shadow root, whose content it cannot audit", () => {
    const { env } = spring();
    expect(audit(KIT_VERSION).shadowRoots).toBe(0);
    const host = document.createElement("div");
    env.stage.appendChild(host);
    host.attachShadow({ mode: "open" }).innerHTML = "<p>0.04 m</p>";
    expect(audit(KIT_VERSION).shadowRoots).toBe(1);
  });

  it("a script cannot mark its own element as Kit-owned", () => {
    const { env } = spring();
    const p = document.createElement("p");
    p.textContent = "0.04 m";
    p.setAttribute("data-synapse-owned", "");
    p.setAttribute("data-synapse-readout", "Extension");
    env.stage.appendChild(p);
    expect(audit(KIT_VERSION).unownedNumbers.map((u) => u.text)).toContain("0.04 m");
  });

  it("records a free observable and user arithmetic in the chain so the verifier can refuse them", () => {
    const env = environment({ title: "t", note: "n" });
    readout(env, { label: "Typed", unit: "m", value: observable(0.04) });
    const load = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2 });
    readout(env, { label: "Mapped", unit: "m", value: hookes({ k: 50, load }).map((x) => x * 2) });
    const [typed, mapped] = audit(KIT_VERSION).readouts;
    expect(typed!.chain.kind).toBe("free");
    expect(mapped!.chain.kind).toBe("derived");
    expect(mapped!.chain.user).toBe(true);
    expect(mapped!.chain.inputs?.x?.kind).toBe("model");
  });

  it("allows a unit conversion by a known factor and records it", () => {
    const env = environment({ title: "t", note: "n" });
    const load = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2 });
    const mm = convert(hookes({ k: 50, load }), "m", "mm");
    expect(mm.get()).toBeCloseTo(40, 9);
    readout(env, { label: "Extension", unit: "mm", value: mm, digits: 1 });
    const r = audit(KIT_VERSION).readouts[0]!;
    expect(r.displayed).toBe("40.0 mm");
    expect(r.chain).toMatchObject({ kind: "convert", from: "m", to: "mm", factor: 1000 });
    expect(() => convert(mm, "m", "kg")).toThrow(RangeError);
    expect(() => convert(mm, "m", "lightyear")).toThrow(RangeError);
    // @ts-expect-error not an observable
    expect(() => convert(5, "m", "cm")).toThrow(TypeError);
  });

  it("records declared constants", () => {
    constant(50, { label: "Spring constant", unit: "N/m" });
    expect(audit(KIT_VERSION).constants).toEqual([{ label: "Spring constant", unit: "N/m", value: 50 }]);
    expect(() => constant(Number.NaN, { label: "x", unit: "u" })).toThrow(RangeError);
  });

  it("does not count digits inside identifiers as numbers in copy", () => {
    const env = environment({ title: "Water, H2O and CO2", note: "Resistor R1 and R2." });
    void env;
    const a = audit(KIT_VERSION);
    expect(a.copy.flatMap((c) => c.numbers)).toEqual([]);
  });

  it("reports window.Synapse as not intact when it is not the sealed, locked property", () => {
    seal(Synapse);
    expect(audit(KIT_VERSION).intact).toBe(false); // the unit-test window has no locked Synapse; the bundle test checks the real thing
  });
});

describe("bridge", () => {
  it("posts the three message types", async () => {
    const sent: unknown[] = [];
    bridgeState.poster = (m) => sent.push(m);
    bridgeState.readySent = false;
    bridge.event("load", 3);
    bridge.error("boom");
    bridge.ready();
    await new Promise((r) => setTimeout(r, 60));
    expect(sent).toEqual([
      { type: "synapse_event", control: "load", value: 3 },
      { type: "synapse_error", message: "boom" },
      { type: "synapse_ready" },
    ]);
  });
  it("posts ready only once", async () => {
    const sent: unknown[] = [];
    bridgeState.poster = (m) => sent.push(m);
    bridgeState.readySent = false;
    bridge.ready();
    bridge.ready();
    await new Promise((r) => setTimeout(r, 60));
    expect(sent).toHaveLength(1);
  });
});

describe("accessibility fence", () => {
  it("names every readout and gives every slider a spoken value with its unit", () => {
    const { load, out } = spring();
    const labelId = out.getAttribute("aria-labelledby")!;
    expect(document.getElementById(labelId)?.textContent).toBe("Extension");
    const input = document.querySelector<HTMLInputElement>("[data-synapse-control]")!;
    expect(input.getAttribute("aria-valuetext")).toBe("2 N");
    load.set(7);
    expect(input.getAttribute("aria-valuetext")).toBe("7 N");
    expect(document.querySelector('[role="region"]')?.getAttribute("aria-label")).toBe("A spring with a load");
  });
});

describe("the public surface", () => {
  it("is frozen, so generated content cannot replace a component", () => {
    expect(Object.isFrozen(Synapse)).toBe(true);
    expect(Object.isFrozen(Synapse.bridge)).toBe(true);
    expect(Object.keys(Synapse.bridge).sort()).toEqual(["error", "event", "installErrorHandlers", "ready"]);
    expect(() => {
      "use strict";
      (Synapse as unknown as Record<string, unknown>).hookes = () => 0;
    }).toThrow(TypeError);
  });
  it("exposes no way to create an observable that the registry would accept except through the Kit", () => {
    expect(Object.keys(Synapse).sort()).toEqual(
      ["audit", "averageRate", "cardiacOutput", "gasVolume", "newtonSecond", "percentChangeMass", "ph", "waveSpeed", "bridge", "conceptCheck", "constant", "convert", "dilution", "environment", "experiment", "graph", "heatEnergy", "hintLadder", "hookes", "magnification", "massHanger", "moles", "netPhotosynthesis", "observable", "ohm", "predictCard", "pressureDepth", "readout", "reset", "slider", "springScene", "stepper", "surfaceAreaToVolume", "table", "text", "titration", "titrationEndpoint", "titrationScene", "valve", "dial", "fermentationScene", "respirationEnergy", "circularSpeed", "escapeSpeed", "centripetalAcceleration", "orbitScene", "version", "workedSolution"].sort(),
    );
  });
});

describe("manifest", () => {
  it("lists every exported micro-component id, and nothing else", () => {
    expect(manifestEntries.map((e) => e.id).sort()).toEqual(Object.keys(components).sort());
  });
  it("gives every entry a precondition and a doc, and every science entry a model id, units and an unverified citation", () => {
    for (const e of manifestEntries) {
      expect(e.precondition.length, e.id).toBeGreaterThan(10);
      expect(e.doc.length, e.id).toBeGreaterThan(10);
      if (e.kind === "science") {
        expect(e.modelId, e.id).toMatch(/^[a-z]+\.[a-z_]+$/);
        expect(e.citation, e.id).toMatch(/^UNVERIFIED/);
        expect(Object.keys(e.units ?? {}).length, e.id).toBeGreaterThanOrEqual(2);
      }
    }
    expect(KIT_VERSION).toBe("0.1.0");
  });
  it("gives every entry a one-sentence useWhen and every science entry its domain, generated from the spec", () => {
    for (const e of manifestEntries) {
      expect(e.useWhen, e.id).toMatch(/^Use .+\.$/);
      expect(e.useWhen!.length, e.id).toBeLessThan(200);
      if (e.kind === "science") {
        expect(Object.keys(e.inputs ?? {}).length, e.id).toBeGreaterThanOrEqual(1);
        expect(e.output?.unit, e.id).toBeTruthy();
        const names = [...Object.keys(e.inputs!), ...Object.keys(e.params!)].sort();
        expect(names, e.id).toEqual(Object.keys(e.units!).filter((k) => k !== "output").sort());
      }
    }
  });
});

describe("reset, table and graph", () => {
  it("reset puts every control back to its starting value and the readout follows", () => {
    const { env, load, extension } = spring();
    reset(env);
    load.set(8);
    expect(extension.get()).toBeCloseTo(0.16, 12);
    document.querySelector<HTMLButtonElement>("[data-synapse-action=reset]")!.click();
    expect(load.get()).toBe(2);
    expect(extension.get()).toBeCloseTo(0.04, 12);
  });

  it("table records the current values as Kit-owned cells and Clear removes them", () => {
    const { env, load, extension } = spring();
    table(env, { caption: "Results", columns: [{ label: "Load", unit: "N", value: load, digits: 1 }, { label: "Extension", unit: "m", value: extension, digits: 3 }] });
    const record = document.querySelector<HTMLButtonElement>("[data-synapse-action=record]")!;
    record.click();
    load.set(5);
    record.click();
    const cells = Array.from(document.querySelectorAll("tbody td")).map((c) => c.textContent);
    expect(cells).toEqual(["2.0", "0.040", "5.0", "0.100"]);
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
    expect(a.series.map((x) => [x.kind, x.label, x.unit])).toEqual([["table", "Load", "N"], ["table", "Extension", "m"]]);
    document.querySelector<HTMLTableCellElement>("tbody td")!.textContent = "9.9";
    expect(audit(KIT_VERSION).ownedMismatches.map((m) => m.actual)).toContain("9.9");
    document.querySelector<HTMLButtonElement>("[data-synapse-action=clear]")!.click();
    expect(document.querySelectorAll("tbody tr")).toHaveLength(0);
  });

  it("table refuses a value that is not a Kit observable and a bad column count", () => {
    const { env } = spring();
    expect(() => table(env, { caption: "x", columns: [{ label: "A", unit: "m", value: { get: () => 1 } as never }] })).toThrow(TypeError);
    expect(() => table(env, { caption: "x", columns: [] })).toThrow(RangeError);
  });

  it("graph samples the whole range, restores x, and keeps every number in an owned element", () => {
    const { env, load, extension } = spring();
    graph(env, { title: "Extension grows with load.", x: load, y: extension, yLabel: "Extension", yUnit: "m", digits: 3 });
    expect(load.get()).toBe(2);
    const a = audit(KIT_VERSION);
    const g = a.series.find((x) => x.kind === "graph")!;
    expect(g.xControl).toBe("load");
    expect(g.points![0]).toEqual([0, 0]);
    expect(g.points![g.points!.length - 1]![0]).toBe(10);
    expect(g.points![g.points!.length - 1]![1]).toBeCloseTo(0.2, 12);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    const rows = document.querySelectorAll(".syn-sr table tbody tr");
    expect(rows).toHaveLength(11);
    expect(rows[10]!.textContent).toBe("100.200");
  });

  it("graph redraws when another control changes", () => {
    const env = environment({ title: "Ohm", note: "Current depends on voltage and resistance." });
    const voltage = slider(env, { id: "voltage", label: "Voltage", unit: "V", min: 0, max: 12, value: 6 });
    const resistance = slider(env, { id: "resistance", label: "Resistance", unit: "ohm", min: 1, max: 20, value: 4 });
    const current = ohm({ voltage, resistance });
    graph(env, { title: "Current against voltage.", x: voltage, y: current, yLabel: "Current", yUnit: "A", digits: 3 });
    const before = audit(KIT_VERSION).series[0]!.points!.at(-1)![1];
    resistance.set(2);
    const after = audit(KIT_VERSION).series[0]!.points!.at(-1)![1];
    expect(before).toBeCloseTo(3, 12);
    expect(after).toBeCloseTo(6, 12);
    expect(voltage.get()).toBe(6);
  });

  it("graph refuses an x that is not a slider and a y that is not a Kit observable", () => {
    const { env, extension } = spring();
    expect(() => graph(env, { title: "t", x: extension, y: extension, yLabel: "E", yUnit: "m" })).toThrow(TypeError);
    const { load } = { load: slider(env, { id: "other", label: "Other", unit: "N", min: 0, max: 1, value: 0 }) };
    expect(() => graph(env, { title: "t", x: load, y: { get: () => 1 } as never, yLabel: "E", yUnit: "m" })).toThrow(TypeError);
  });

  it("the audit counts a look-alike action button a script made", () => {
    const { env } = spring();
    reset(env);
    expect(audit(KIT_VERSION).forgedActions).toBe(0);
    const b = document.createElement("button");
    b.setAttribute("data-synapse-action", "reset");
    env.controls.appendChild(b);
    expect(audit(KIT_VERSION).forgedActions).toBe(1);
    expect(audit(KIT_VERSION).actions).toEqual([{ kind: "reset", label: "Reset" }]);
  });
});

describe("what the audit refuses to leave unseen", () => {
  const forbiddenWhat = () => audit(KIT_VERSION).forbidden.map((f) => f.what);

  it("flags canvas, media, meter, progress, list counters and look-alike widgets", () => {
    const { env } = spring();
    expect(forbiddenWhat()).toEqual([]);
    for (const tag of ["canvas", "meter", "progress", "img", "video"]) env.stage.appendChild(document.createElement(tag));
    const ol = document.createElement("ol");
    ol.setAttribute("start", "42");
    env.stage.appendChild(ol);
    const li = document.createElement("li");
    li.setAttribute("value", "42");
    env.stage.appendChild(li);
    env.stage.appendChild(document.createElement("input"));
    const found = forbiddenWhat().join("|");
    for (const expected of ["<canvas> element", "<meter> element", "<progress> element", "<img> element", "<video> element", "list counter start", "list item value", "a widget no Kit component made"]) {
      expect(found).toContain(expected);
    }
  });

  it("flags a stylesheet that draws an image, a font or generated content, and a link element", () => {
    spring();
    const style = document.createElement("style");
    style.textContent = "p::before { content: 'x' }";
    document.body.appendChild(style);
    const link = document.createElement("link");
    link.rel = "stylesheet";
    document.head.appendChild(link);
    expect(forbiddenWhat().join("|")).toContain("stylesheet with an image");
    expect(forbiddenWhat().join("|")).toContain("<link> element");
  });

  it("refuses CSS that can put a list marker's number on screen without a text node, in a stylesheet or inline", () => {
    spring();
    expect(forbiddenWhat()).toEqual([]);
    for (const css of [
      "li { counter-set: list-item 41 }",
      "p { counter-reset: list-item 41 }",
      "div { counter-increment: list-item 5 }",
      "div { display: list-item; list-style-type: decimal }",
      'li { list-style-type: "42" }',
      "li::marker { color: red }",
      "p::before { content: counter(x) }",
    ]) {
      const sheet = document.createElement("style");
      sheet.textContent = css;
      document.body.appendChild(sheet);
      expect(forbiddenWhat().join("|"), css).toContain("stylesheet with an image");
      sheet.remove();
    }
    expect(forbiddenWhat()).toEqual([]);
    for (const inline of ["counter-set: list-item 41", "display:list-item", 'list-style-type:"7"', "list-style: '7'"]) {
      const div = document.createElement("div");
      div.setAttribute("style", inline);
      document.body.appendChild(div);
      expect(forbiddenWhat().join("|"), inline).toContain("inline style that can draw a number");
      div.remove();
    }
    expect(forbiddenWhat()).toEqual([]);
  });

  it("refuses an inline style on the body or on a head element that could draw a number", () => {
    spring();
    document.body.setAttribute("style", "counter-set: list-item 41");
    expect(forbiddenWhat().join("|")).toContain("inline style that can draw a number");
    document.body.removeAttribute("style");
    const meta = document.createElement("meta");
    meta.setAttribute("style", 'list-style-type:"9"');
    document.head.appendChild(meta);
    expect(forbiddenWhat().join("|")).toContain("inline style that can draw a number");
    meta.remove();
    expect(forbiddenWhat()).toEqual([]);
  });

  it("refuses a non-visual element (script, style, title, a head element) that CSS has made visible", () => {
    spring();
    expect(forbiddenWhat()).toEqual([]);
    const script = document.createElement("script");
    script.setAttribute("type", "text/plain");
    script.setAttribute("style", "display:block");
    script.textContent = "the answer is 42";
    document.body.appendChild(script);
    expect(forbiddenWhat().join("|")).toContain("<script> made visible");
    script.remove();
    const title = document.createElement("title");
    title.textContent = "42";
    title.setAttribute("style", "display:block");
    document.head.appendChild(title);
    expect(forbiddenWhat().join("|")).toContain("<title> made visible");
    title.remove();
    expect(forbiddenWhat()).toEqual([]);
  });

  it("leaves ordinary hidden non-visual elements alone, and refuses an inline style the Kit did not set", () => {
    const { env } = spring();
    const script = document.createElement("script");
    script.textContent = "var x = 1;";
    document.body.appendChild(script);
    const hidden = document.createElement("title");
    hidden.textContent = "A title";
    document.head.appendChild(hidden);
    expect(forbiddenWhat()).toEqual([]);
    const p = document.createElement("p");
    p.setAttribute("style", "color: red; margin: 0");
    env.stage.appendChild(p);
    // Not a finding the student's own browser acts on (an extension adds styles to pages), but one the verifier refuses.
    expect(forbiddenWhat()).toEqual([]);
    expect(audit(KIT_VERSION).foreign.map((f) => f.what)).toContain("an inline style the Kit did not set");
    p.removeAttribute("style");
    const q = document.createElement("div");
    q.setAttribute("popover", "");
    env.stage.appendChild(q);
    expect(audit(KIT_VERSION).foreign.map((f) => f.what)).toContain("a popover (it draws in the top layer)");
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });

  it("counts non-ASCII digits as digits in text and in attributes", () => {
    const { env } = spring();
    const p = document.createElement("p");
    p.textContent = "Answer: ４２ m";
    env.stage.appendChild(p);
    expect(audit(KIT_VERSION).unownedNumbers.map((u) => u.text)).toContain("Answer: ４２ m");
    const q = document.createElement("p");
    q.setAttribute("aria-valuenow", "42");
    env.stage.appendChild(q);
    expect(audit(KIT_VERSION).unownedAttributeNumbers.map((a) => a.attribute)).toContain("aria-valuenow");
  });

  it("reads the body through the captured getter even if a script shadows document.body", () => {
    const { env } = spring();
    const p = document.createElement("p");
    p.textContent = "Answer: 42 m";
    env.stage.appendChild(p);
    Object.defineProperty(document, "body", { configurable: true, get: () => document.createElement("body") });
    try {
      expect(audit(KIT_VERSION).unownedNumbers.map((u) => u.text)).toContain("Answer: 42 m");
    } finally {
      delete (document as unknown as Record<string, unknown>).body;
    }
  });

  it("counts readout elements the Kit did not make", () => {
    const { env } = spring();
    const o = document.createElement("output");
    o.setAttribute("data-synapse-readout", "Fake");
    env.readouts.appendChild(o);
    const a = audit(KIT_VERSION);
    expect(a.readoutElements).toBe(2);
    expect(a.readouts).toHaveLength(1);
    expect(violations(a).join("|")).toContain("a readout element the Kit did not make");
  });

  it("a control whose input disagrees with the observable is reported", () => {
    const { load } = spring();
    document.querySelector("input")!.value = "9";
    expect(violations(audit(KIT_VERSION)).join("|")).toContain('control "load" disagrees');
    load.set(9);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });
});

describe("kit-owned strings cannot be changed through the options object", () => {
  it("environment, readout and table copy what they were given", () => {
    const opts = { title: "T", note: "N" };
    const env = environment(opts);
    opts.note = "At 10 N the extension is 42 m.";
    expect(audit(KIT_VERSION).ownedMismatches).toEqual([]);
    document.querySelector(".syn-note")!.textContent = opts.note;
    expect(audit(KIT_VERSION).ownedMismatches.map((m) => m.expected)).toContain("N");
    const load = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2 });
    const ext = hookes({ k: 50, load });
    const ro = { label: "Extension", unit: "m", value: ext, digits: 3 };
    const out = readout(env, ro);
    ro.label = "Extension (at 10 N it is 42 m)";
    (out.previousSibling as HTMLElement).textContent = ro.label;
    expect(audit(KIT_VERSION).ownedMismatches.map((m) => m.expected)).toContain("Extension");
    const cols = [{ label: "Load", unit: "N", value: load }, { label: "Extension", unit: "m", value: ext, digits: 3 }];
    table(env, { caption: "R", columns: cols });
    cols[1]!.value = { get: () => 42 } as never;
    document.querySelector<HTMLButtonElement>("[data-synapse-action=record]")!.click();
    expect(Array.from(document.querySelectorAll("tbody td")).map((c) => c.textContent)).toEqual(["2.00", "0.040"]);
  });

  it("an observable cannot have its methods replaced", () => {
    const { load } = spring();
    expect(Object.isFrozen(load)).toBe(true);
    expect(() => {
      "use strict";
      (load as unknown as Record<string, unknown>).get = () => 99;
    }).toThrow(TypeError);
  });
});

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

describe("the runtime self-check", () => {
  it("reports a tampered readout and empties the page", async () => {
    resetWatchForTests();
    const sent: unknown[] = [];
    bridgeState.poster = (m) => sent.push(m);
    spring();
    startWatch();
    expect(sent).toEqual([]);
    document.querySelector("output")!.textContent = "42.000 m";
    await wait(200);
    expect(sent).toHaveLength(1);
    expect(sent[0]).toMatchObject({ type: "synapse_violation" });
    expect(document.body.textContent).toBe("");
  });

  it("stays quiet while the Kit itself moves the controls and redraws", async () => {
    resetWatchForTests();
    const sent: unknown[] = [];
    bridgeState.poster = (m) => sent.push(m);
    const { env, load, extension } = spring();
    graph(env, { title: "g", x: load, y: extension, yLabel: "Extension", yUnit: "m" });
    table(env, { caption: "r", columns: [{ label: "Load", unit: "N", value: load }] });
    reset(env);
    startWatch();
    for (const v of [0, 5, 10, 3]) {
      load.set(v);
      document.querySelector<HTMLButtonElement>("[data-synapse-action=record]")!.click();
      await wait(120);
    }
    document.querySelector<HTMLButtonElement>("[data-synapse-action=reset]")!.click();
    await wait(1300);
    expect(sent.filter((m) => (m as { type: string }).type === "synapse_violation")).toEqual([]);
  });
});

describe("stepper and experiment", () => {
  it("stepper lists owned steps and refuses 0 or too many", () => {
    const { env } = spring();
    stepper(env, { steps: ["Set the load to 2 N.", "Read the extension.", "Move the load to 10 N."] });
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.copy.map((c) => c.text)).toContain("Set the load to 2 N.");
    expect(() => stepper(env, { steps: [] })).toThrow(RangeError);
    expect(() => stepper(env, { steps: Array(9).fill("x") })).toThrow(RangeError);
  });
  it("experiment shows the card, every word owned, and refuses an empty field", () => {
    const { env } = spring();
    experiment(env, { aim: "To find how the extension depends on the load", hypothesis: "The extension is proportional to the load", independent: "Load (N)", dependent: "Extension (m)", controlled: ["The spring"], apparatus: ["Spring", "Weights"] });
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
    expect(document.querySelector("section dd")!.textContent).toContain("depends on the load");
    expect(() => experiment(env, { aim: " ", hypothesis: "h", independent: "i", dependent: "d", controlled: ["c"], apparatus: ["a"] })).toThrow(RangeError);
  });
  it("a step that states an unbacked number is visible to the verifier as copy", () => {
    const { env } = spring();
    stepper(env, { steps: ["The extension is 42 m."] });
    expect(audit(KIT_VERSION).copy.some((c) => c.numbers.includes("42"))).toBe(true);
  });
});

describe("pedagogy components", () => {
  it("hintLadder reveals one hint per press and keeps hidden hints owned and audited", () => {
    const { env } = spring();
    hintLadder(env, { hints: ["Think about what the load does.", "Compare 2 N with 4 N.", "Try a load of 10 N."] });
    const p = Array.from(document.querySelectorAll<HTMLElement>("p")).filter((e) => /load/.test(e.textContent ?? ""));
    expect(p.filter((e) => !e.hidden)).toHaveLength(0);
    const button = document.querySelector<HTMLButtonElement>("[data-synapse-action=hint]")!;
    button.click();
    expect(p.filter((e) => !e.hidden)).toHaveLength(1);
    button.click();
    button.click();
    expect(p.every((e) => !e.hidden)).toBe(true);
    expect(button.disabled).toBe(true);
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.copy.map((c) => c.text)).toContain("Compare 2 N with 4 N.");
    expect(() => hintLadder(env, { hints: [] })).toThrow(RangeError);
  });

  it("conceptCheck tells the host how the FIRST answer went, once", () => {
    const sent: unknown[] = [];
    const before = bridgeState.poster;
    bridgeState.poster = (m) => sent.push(m);
    try {
      const { env } = spring();
      conceptCheck(env, { question: "Which is it?", options: ["a", "b", "c"], correct: 2, explanation: "because" });
      const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-synapse-action=choose]"));
      buttons[0]!.click();
      buttons[2]!.click();
      buttons[1]!.click();
      expect(sent).toEqual([{ type: "synapse_event", control: "concept_check", value: "incorrect" }]);
    } finally {
      bridgeState.poster = before;
    }
  });

  it("conceptCheck gives feedback only after a choice and says correct or not quite", () => {
    const { env } = spring();
    conceptCheck(env, { question: "What happens to the extension when the load doubles?", options: ["It halves", "It doubles", "It stays the same"], correct: 1, explanation: "Within the elastic limit the extension is proportional to the load." });
    const status = document.querySelector("[role=status]")!;
    expect(status.textContent).toBe("");
    const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-synapse-action=choose]"));
    buttons[0]!.click();
    expect(status.textContent).toBe("Not quite.");
    buttons[1]!.click();
    expect(status.textContent).toBe("Correct.");
    expect(document.body.textContent).toContain("proportional to the load");
    expect(audit(KIT_VERSION).ownedMismatches).toEqual([]);
    expect(() => conceptCheck(env, { question: "q", options: ["a"], correct: 0, explanation: "e" })).toThrow(RangeError);
    expect(() => conceptCheck(env, { question: "q", options: ["a", "b"], correct: 2, explanation: "e" })).toThrow(RangeError);
  });

  it("predictCard shows its reveal only after the student commits", () => {
    const { env } = spring();
    predictCard(env, { prompt: "What will happen to the extension if you double the load?", choices: ["Less", "More", "The same"], reveal: "Watch the extension as you move the slider." });
    expect(document.body.textContent).not.toContain("Watch the extension");
    document.querySelector<HTMLButtonElement>("[data-synapse-action=predict]")!.click();
    expect(document.body.textContent).toContain("Watch the extension");
    expect(audit(KIT_VERSION).forbidden).toEqual([]);
  });

  it("workedSolution opens its steps on request, and a typed result in a step is visible as copy", () => {
    const { env } = spring();
    workedSolution(env, { steps: ["Write down F = k x.", "Divide the load by the spring constant.", "The answer is 0.99 m."] });
    const list = document.querySelector<HTMLElement>("ol")!;
    expect(list.hidden).toBe(true);
    document.querySelector<HTMLButtonElement>("[data-synapse-action=solution]")!.click();
    expect(list.hidden).toBe(false);
    expect(audit(KIT_VERSION).copy.some((c) => c.numbers.includes("0.99"))).toBe(true);
  });

  it("none of the new action buttons counts as a forged action or an unregistered widget", () => {
    const { env } = spring();
    hintLadder(env, { hints: ["a hint"] });
    conceptCheck(env, { question: "q?", options: ["a", "b"], correct: 0, explanation: "because" });
    predictCard(env, { prompt: "p?", choices: ["a", "b"], reveal: "look" });
    workedSolution(env, { steps: ["one"] });
    const a = audit(KIT_VERSION);
    expect(a.forgedActions).toBe(0);
    expect(a.forbidden).toEqual([]);
    expect(violations(a)).toEqual([]);
  });
});

describe("lab messages for the host's report (W5b)", () => {
  function capture() {
    const sent: any[] = [];
    const before = bridgeState.poster;
    bridgeState.poster = (m) => sent.push(m);
    return { sent, restore: () => (bridgeState.poster = before) };
  }

  it("tells the host the table whole at creation, after each Record and after Clear", () => {
    const c = capture();
    try {
      const { env, load, extension } = spring();
      table(env, {
        caption: "Load and extension",
        columns: [
          { label: "Load", unit: "N", value: load, digits: 1 },
          { label: "Extension", unit: "m", value: extension, digits: 3 },
        ],
      });
      const labs = () => c.sent.filter((m) => m.type === "synapse_lab" && m.part === "table");
      expect(labs()).toHaveLength(1);
      expect(labs()[0]).toEqual({
        type: "synapse_lab",
        part: "table",
        caption: "Load and extension",
        columns: [
          { label: "Load", unit: "N" },
          { label: "Extension", unit: "m" },
        ],
        rows: [],
      });
      const [record, clear] = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-synapse-action]"));
      record!.click();
      load.set(4);
      record!.click();
      expect(labs().at(-1).rows).toEqual([
        ["2.0", "0.040"],
        ["4.0", "0.080"],
      ]);
      clear!.click();
      expect(labs().at(-1).rows).toEqual([]);
    } finally {
      c.restore();
    }
  });

  it("sends the Amali card and the steps once each, as the text the Kit showed", () => {
    const c = capture();
    try {
      const { env } = spring();
      experiment(env, { aim: "To find how the extension depends on the load.", hypothesis: "The extension is proportional to the load.", independent: "The load", dependent: "The extension", controlled: ["The spring"], apparatus: ["Spring", "Ruler"] });
      stepper(env, { steps: ["Hang a load.", "Read the extension."] });
      const labs = c.sent.filter((m) => m.type === "synapse_lab");
      expect(labs.map((m) => m.part)).toEqual(["experiment", "steps"]);
      expect(labs[0].fields[0]).toEqual(["Aim", "To find how the extension depends on the load."]);
      expect(labs[0].fields).toHaveLength(6);
      expect(labs[1].steps).toEqual(["Hang a load.", "Read the extension."]);
    } finally {
      c.restore();
    }
  });

  it("cuts what it sends to the sizes the host accepts", () => {
    const c = capture();
    try {
      bridge.lab({ part: "steps", steps: Array.from({ length: 12 }, () => "x".repeat(900)) });
      bridge.lab({ part: "table", caption: "c".repeat(500), columns: Array.from({ length: 9 }, () => ({ label: "l".repeat(200), unit: "u".repeat(99) })), rows: Array.from({ length: 50 }, () => Array.from({ length: 9 }, () => "9".repeat(99))) });
      const [steps, tbl] = c.sent;
      expect(steps.steps).toHaveLength(8);
      expect(steps.steps[0]).toHaveLength(300);
      expect(tbl.caption).toHaveLength(120);
      expect(tbl.columns).toHaveLength(6);
      expect(tbl.rows).toHaveLength(30);
      expect(tbl.rows[0]).toHaveLength(6);
      expect(tbl.rows[0][0]).toHaveLength(40);
    } finally {
      c.restore();
    }
  });

  it("is not reachable from page code: the public bridge is still exactly four functions", () => {
    expect(Object.keys(Synapse.bridge).sort()).toEqual(["error", "event", "installErrorHandlers", "ready"]);
    expect(Object.keys(Synapse)).not.toContain("lab");
  });
});
