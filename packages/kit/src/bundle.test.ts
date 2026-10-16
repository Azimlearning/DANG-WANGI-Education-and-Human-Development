// Tests the BUILT bundle (dist/<semver>/core.js), loaded the way a page loads it: as a classic script. `npm test` builds first.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { KIT_VERSION } from "./manifest";

const code = () => readFileSync(resolve(__dirname, "..", "dist", KIT_VERSION, "core.js"), "utf-8");

function load(): void {
  // eslint-disable-next-line no-eval
  (0, eval)(code());
}

describe("the built bundle", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("defines window.Synapse as frozen, non-writable and non-configurable", () => {
    load();
    const d = Object.getOwnPropertyDescriptor(window, "Synapse")!;
    expect(d.writable).toBe(false);
    expect(d.configurable).toBe(false);
    expect(Object.isFrozen(d.value)).toBe(true);
    expect(d.value.version).toBe(KIT_VERSION);
  });

  it("cannot be replaced, redefined or loaded twice", () => {
    expect(() => {
      "use strict";
      (window as unknown as Record<string, unknown>).Synapse = { audit: () => ({}) };
    }).toThrow(TypeError);
    expect(() => Object.defineProperty(window, "Synapse", { value: {}, configurable: true })).toThrow(TypeError);
    expect(() => load()).toThrow(TypeError);
  });

  it("reports itself intact through the audit", () => {
    const S = (window as unknown as { Synapse: { audit(): { intact: boolean; kitVersion: string } } }).Synapse;
    const a = S.audit();
    expect(a.intact).toBe(true);
    expect(a.kitVersion).toBe(KIT_VERSION);
  });

  it("builds a grounded spring from the public surface alone", () => {
    const S = (window as unknown as { Synapse: Record<string, (...a: unknown[]) => unknown> & { audit(): { readouts: { displayed: string; chain: { kind: string } }[] } } }).Synapse;
    const env = S.environment({ title: "t", note: "n" });
    const load = S.slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2 });
    S.readout(env, { label: "Extension", unit: "m", value: S.hookes({ k: 50, load }), digits: 3 });
    const r = S.audit().readouts[0]!;
    expect(r.displayed).toBe("0.040 m");
    expect(r.chain.kind).toBe("model");
  });
});
