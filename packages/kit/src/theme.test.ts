import { beforeEach, describe, expect, it } from "vitest";
import { audit } from "./audit";
import { environment } from "./environment";
import { KIT_VERSION } from "./index";
import { hookes } from "./science/hookes";
import { readout } from "./readout";
import { resetForTests } from "./provenance";
import { slider } from "./slider";

// The host tells the frame which theme it is in (W3, D-38). A sandboxed frame cannot read the host's attribute, so the host posts one message and the Kit sets
// `data-theme` on its own root, which its stylesheet reads. Exactly one message shape is accepted, from the embedding page only.
const send = (data: unknown, source: MessageEventSource | null = window.parent) => window.dispatchEvent(new MessageEvent("message", { data, source }));
const theme = () => document.documentElement.getAttribute("data-theme");

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
  document.documentElement.removeAttribute("data-theme");
  environment({ title: "t", note: "n" }); // installs the listener (once per page)
});

describe("theme", () => {
  it("sets data-theme from exactly one message shape sent by the embedding page", () => {
    send({ type: "synapse_theme", theme: "dark" });
    expect(theme()).toBe("dark");
    send({ type: "synapse_theme", theme: "light" });
    expect(theme()).toBe("light");
  });

  it("ignores any other type, value, shape or sender", () => {
    const bad: unknown[] = [{ type: "synapse_theme", theme: "neon" }, { type: "synapse_theme" }, { type: "other", theme: "dark" }, { theme: "dark" }, "dark", null, 7, { type: "synapse_theme", theme: ["dark"] }];
    for (const data of bad) {
      send(data);
      expect(theme()).toBeNull();
    }
    send({ type: "synapse_theme", theme: "dark" }, new MessageChannel().port1);
    expect(theme()).toBeNull();
    send({ type: "synapse_theme", theme: "dark" }, null);
    expect(theme()).toBeNull();
  });

  it("changes nothing the audit looks at: a page still audits clean after a theme change", () => {
    const env = environment({ title: "Why does a spring stretch?", note: "Hang a load on a spring and it stretches." });
    const load = slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2 });
    readout(env, { label: "Extension", unit: "m", value: hookes({ k: 50, load }), digits: 3 });
    send({ type: "synapse_theme", theme: "dark" });
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
  });

  it("styles both themes: a dark set for the system preference and for the forced choice, and a forced light choice beats a dark system", () => {
    const css = document.getElementById("syn-style")?.textContent ?? "";
    expect(css).toContain('@media (prefers-color-scheme: dark){:root:not([data-theme="light"])');
    expect(css).toContain(':root[data-theme="dark"]');
  });
});
