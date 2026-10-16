import { beforeEach, describe, expect, it } from "vitest";
import * as bridge from "./bridge";
import { components, KIT_VERSION, manifestEntries } from "./index";
import { environment } from "./environment";
import { isObservable, observable } from "./observable";
import { readout } from "./readout";
import { hookes, hookesExtension } from "./science_hookes";
import { slider } from "./slider";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
});

describe("observable", () => {
  it("propagates changes to subscribers and to mapped values", () => {
    const a = observable(2);
    const doubled = a.map((v) => v * 2);
    const seen: number[] = [];
    doubled.subscribe((v) => seen.push(v));
    a.set(5);
    expect(doubled.get()).toBe(10);
    expect(seen).toEqual([10]);
  });
  it("does not notify when the value is unchanged, and unsubscribe works", () => {
    const a = observable(1);
    let calls = 0;
    const off = a.subscribe(() => calls++);
    a.set(1);
    a.set(2);
    off();
    a.set(3);
    expect(calls).toBe(1);
  });
  it("a mapped observable is read-only", () => {
    expect(() => observable(1).map((v) => v + 1).set(0)).toThrow(TypeError);
  });
  it("isObservable is false for plain values", () => {
    expect(isObservable(3)).toBe(false);
    expect(isObservable(null)).toBe(false);
    expect(isObservable(observable(3))).toBe(true);
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
  it("rejects min >= max", () => {
    const env = environment({ title: "t", note: "n" });
    expect(() => slider(env, { id: "x", label: "X", unit: "u", min: 1, max: 1, value: 1 })).toThrow(RangeError);
  });
});

describe("readout", () => {
  it("rejects a plain number", () => {
    const env = environment({ title: "t", note: "n" });
    // @ts-expect-error a plain number is not an Observable
    expect(() => readout(env, { label: "Extension", unit: "m", value: 3.2 })).toThrow(TypeError);
  });
  it("follows its observable", () => {
    const env = environment({ title: "t", note: "n" });
    const v = observable(1);
    const out = readout(env, { label: "Value", unit: "m", value: v, digits: 1 });
    expect(out.textContent).toBe("1.0 m");
    v.set(2.25);
    expect(out.textContent).toBe("2.3 m");
    expect(out.getAttribute("aria-live")).toBe("polite");
  });
});

describe("hookes", () => {
  it("is extension = load / k and follows the load", () => {
    expect(hookesExtension(10, 50)).toBeCloseTo(0.2);
    const load = observable(4);
    const ext = hookes({ k: 20, load });
    expect(ext.get()).toBeCloseTo(0.2);
    load.set(10);
    expect(ext.get()).toBeCloseTo(0.5);
  });
  it("refuses a non-positive k and a negative load", () => {
    expect(() => hookes({ k: 0, load: observable(1) })).toThrow(RangeError);
    expect(() => hookesExtension(-1, 10)).toThrow(RangeError);
  });
});

describe("bridge", () => {
  it("posts the three message types", async () => {
    const sent: unknown[] = [];
    bridge.setPoster((m) => sent.push(m));
    bridge.resetForTests();
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
    bridge.setPoster((m) => sent.push(m));
    bridge.resetForTests();
    bridge.ready();
    bridge.ready();
    await new Promise((r) => setTimeout(r, 60));
    expect(sent).toHaveLength(1);
  });
});

describe("manifest", () => {
  it("lists every exported micro-component id, and nothing else", () => {
    const exported = Object.keys(components).sort();
    const listed = manifestEntries.map((e) => e.id).sort();
    expect(listed).toEqual(exported);
  });
  it("gives every entry a precondition and a doc, and every science entry a citation", () => {
    for (const e of manifestEntries) {
      expect(e.precondition.length, e.id).toBeGreaterThan(10);
      expect(e.doc.length, e.id).toBeGreaterThan(10);
      if (e.kind === "science") expect(e.citation, e.id).toBeTruthy();
    }
    expect(KIT_VERSION).toBe("0.0.1");
  });
  it("marks the P0 science citation as unverified", () => {
    expect(manifestEntries.find((e) => e.id === "hookes")?.citation).toMatch(/^UNVERIFIED/);
  });
});
