import { beforeEach, describe, expect, it } from "vitest";
import { audit, seal } from "./audit";
import * as bridge from "./bridge";
import { state as bridgeState } from "./bridge";
import { constant } from "./constant";
import { convert } from "./convert";
import { environment } from "./environment";
import { components, KIT_VERSION, manifestEntries, Synapse } from "./index";
import { observable } from "./observable";
import { isObservable, resetForTests } from "./provenance";
import { readout } from "./readout";
import { hookes } from "./science/hookes";
import { ohm } from "./science/ohm";
import { pressureDepth } from "./science/pressure_depth";
import { slider } from "./slider";
import { text } from "./text";

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
    expect(a.controls).toEqual([{ id: "load", label: "Load", unit: "N", min: 0, max: 10, grid: 10, default: 2, value: 2 }]);
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
      ["audit", "bridge", "constant", "convert", "environment", "hookes", "observable", "ohm", "pressureDepth", "readout", "slider", "text", "version"].sort(),
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
});
