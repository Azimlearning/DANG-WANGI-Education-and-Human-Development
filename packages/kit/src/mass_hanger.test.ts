import { beforeEach, describe, expect, it } from "vitest";
import { audit } from "./audit";
import { environment } from "./environment";
import { KIT_VERSION, Synapse } from "./index";
import { massHanger } from "./mass_hanger";
import { observable } from "./observable";
import { ohm } from "./science/ohm";
import { actions, controls, isAction, resetForTests } from "./provenance";
import { readout } from "./readout";
import { reset } from "./reset";
import { springScene, stretchWords } from "./scene";
import { hookes } from "./science/hookes";
import { STYLE } from "./style";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

function bench(value = 2) {
  const env = environment({ title: "Hooke", note: "Hang masses on a spring." });
  const load = massHanger(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value, grid: 5 });
  const extension = hookes({ k: 50, load });
  readout(env, { label: "Extension", unit: "m", value: extension, digits: 3 });
  return { env, load, extension };
}

// In letter order, whichever side of the bench each mass is on.
const tokens = () => Array.from(document.querySelectorAll<HTMLButtonElement>("[data-synapse-drag='load']")).sort((a, b) => (a.textContent ?? "").localeCompare(b.textContent ?? ""));
const hung = () => tokens().filter((t) => t.dataset.state === "hung").length;
const input = () => document.querySelector<HTMLInputElement>("input[data-synapse-control='load']") as HTMLInputElement;
const hanger = () => document.querySelector<HTMLElement>("[data-synapse-dropzone='load']") as HTMLElement;
const point = (type: string, x: number, y: number) => new MouseEvent(type, { clientX: x, clientY: y, button: 0, bubbles: true });
const rect = (r: { left: number; right: number; top: number; bottom: number }) => {
  hanger().getBoundingClientRect = () => ({ ...r, x: r.left, y: r.top, width: r.right - r.left, height: r.bottom - r.top, toJSON: () => ({}) }) as DOMRect;
};

describe("massHanger: what it refuses", () => {
  it("needs an integer number of masses from 2 to 8, a unique id and a real range", () => {
    const env = environment({ title: "t", note: "n" });
    const base = { id: "a", label: "Load", unit: "N", min: 0, max: 10, value: 2 };
    for (const grid of [1, 9, 2.5, 0, -3, Number.NaN]) expect(() => massHanger(env, { ...base, id: `g${grid}`, grid })).toThrow(RangeError);
    massHanger(env, { ...base, grid: 5 });
    expect(() => massHanger(env, { ...base, grid: 5 })).toThrow(RangeError);
    expect(() => massHanger(env, { ...base, id: "b", min: 5, max: 5, grid: 5 })).toThrow(RangeError);
  });

  it("refuses a starting value that is not a whole number of masses, and snaps what a script sets to one", () => {
    const env = environment({ title: "t", note: "n" });
    const base = { id: "a", label: "Load", unit: "N", min: 0, max: 10, grid: 5 };
    for (const value of [3, 1, 9.9, 0.5]) expect(() => massHanger(env, { ...base, id: `v${value}`, value })).toThrow(RangeError);
    const load = massHanger(env, { ...base, value: 2 });
    load.set(2.9);
    expect(load.get()).toBe(2);
    load.set(3.1);
    expect(load.get()).toBe(4);
    load.set(99);
    expect(load.get()).toBe(10);
    expect(hung()).toBe(0);
  });
});

describe("massHanger: it is a control exactly as a slider is", () => {
  it("registers the same control record, keeps the range input declared and named, and returns a control observable", () => {
    const { load } = bench();
    expect(controls.map((c) => c.id)).toEqual(["load"]);
    expect(controls[0]).toMatchObject({ min: 0, max: 10, grid: 5, default: 2 });
    expect(input().getAttribute("data-synapse-control")).toBe("load");
    expect(input().getAttribute("aria-valuetext")).toBe("2 N");
    expect(document.querySelector("label[for='syn-load']")?.textContent).toBe("Load (N)");
    expect(load.get()).toBe(2);
    expect(() => (load as unknown as { map: unknown }).map).not.toThrow();
  });

  it("starts with the masses its starting value means and says so in words", () => {
    bench(4);
    expect(hung()).toBe(2);
    expect(hanger().getAttribute("aria-label")).toBe("Hanger, holding two masses");
    expect(tokens().map((t) => t.getAttribute("aria-label"))).toEqual([
      "Mass A, on the hanger. Press Enter to move it.",
      "Mass B, on the hanger. Press Enter to move it.",
      "Mass C, in the tray. Press Enter to move it.",
      "Mass D, in the tray. Press Enter to move it.",
      "Mass E, in the tray. Press Enter to move it.",
    ]);
  });
});

describe("massHanger: the keyboard and tap path", () => {
  it("pressing a mass moves it and the control, in both directions, and keeps focus on it", () => {
    const { load } = bench(2);
    const [a, , , , e] = tokens() as [HTMLButtonElement, HTMLButtonElement, HTMLButtonElement, HTMLButtonElement, HTMLButtonElement];
    e.focus();
    e.click();
    expect(load.get()).toBe(4);
    expect(hung()).toBe(2);
    expect(e.dataset.state).toBe("hung");
    expect(document.activeElement).toBe(e);
    a.click();
    expect(load.get()).toBe(2);
    expect(a.dataset.state).toBe("tray");
    expect(input().value).toBe("2");
  });

  it("can fill and empty the hanger and never leaves the control's range", () => {
    const { load } = bench(0);
    for (const t of tokens()) t.click();
    expect(load.get()).toBe(10);
    expect(hung()).toBe(5);
    for (const t of tokens()) t.click();
    expect(load.get()).toBe(0);
    expect(hung()).toBe(0);
  });
});

describe("massHanger: the masses follow the control", () => {
  it("moving the range input moves the masses, as does Reset", () => {
    const { env } = bench(2);
    reset(env);
    input().value = "8";
    input().dispatchEvent(new Event("input", { bubbles: true }));
    expect(hung()).toBe(4);
    (document.querySelector("[data-synapse-action='reset']") as HTMLButtonElement).click();
    expect(hung()).toBe(1);
    expect(hanger().getAttribute("aria-label")).toBe("Hanger, holding one mass");
  });
});

describe("massHanger: the pointer path", () => {
  beforeEach(() => bench(2));

  it("dragging a mass from the tray onto the hanger hangs it", () => {
    const { load } = { load: input() };
    rect({ left: 100, right: 200, top: 100, bottom: 160 });
    const t = tokens().find((x) => x.dataset.state === "tray") as HTMLButtonElement;
    t.dispatchEvent(point("pointerdown", 10, 10));
    t.dispatchEvent(point("pointermove", 150, 130));
    expect(t.classList.contains("syn-dragging")).toBe(true);
    expect(hanger().classList.contains("syn-over")).toBe(true);
    expect(t.style.transform).toContain("translate");
    t.dispatchEvent(point("pointerup", 150, 130));
    expect(Number(load.value)).toBe(4);
    expect(t.dataset.state).toBe("hung");
    expect(t.classList.contains("syn-dragging")).toBe(false);
    expect(t.style.transform).toBe("");
  });

  it("dropping it anywhere else snaps it back and changes nothing", () => {
    rect({ left: 100, right: 200, top: 100, bottom: 160 });
    const t = tokens().find((x) => x.dataset.state === "tray") as HTMLButtonElement;
    t.dispatchEvent(point("pointerdown", 10, 10));
    t.dispatchEvent(point("pointermove", 40, 40));
    t.dispatchEvent(point("pointerup", 40, 40));
    expect(Number(input().value)).toBe(2);
    expect(t.dataset.state).toBe("tray");
  });

  it("dragging a hung mass out of the hanger takes it off", () => {
    rect({ left: 100, right: 200, top: 100, bottom: 160 });
    const t = tokens().find((x) => x.dataset.state === "hung") as HTMLButtonElement;
    t.dispatchEvent(point("pointerdown", 150, 130));
    t.dispatchEvent(point("pointermove", 20, 20));
    t.dispatchEvent(point("pointerup", 20, 20));
    expect(Number(input().value)).toBe(0);
    expect(hung()).toBe(0);
  });

  it("a click straight after a drag does not toggle a second time, and a plain tap does toggle", async () => {
    rect({ left: 100, right: 200, top: 100, bottom: 160 });
    const t = tokens().find((x) => x.dataset.state === "tray") as HTMLButtonElement;
    t.dispatchEvent(point("pointerdown", 10, 10));
    t.dispatchEvent(point("pointermove", 150, 130));
    t.dispatchEvent(point("pointerup", 150, 130));
    t.click();
    expect(Number(input().value)).toBe(4);
    await new Promise((resolve) => setTimeout(resolve, 80));
    const u = tokens().find((x) => x.dataset.state === "tray") as HTMLButtonElement;
    u.dispatchEvent(point("pointerdown", 10, 10));
    u.dispatchEvent(point("pointerup", 10, 10));
    u.click();
    expect(Number(input().value)).toBe(6);
  });

  it("a cancelled drag (the pointer was taken away) changes nothing", () => {
    rect({ left: 100, right: 200, top: 100, bottom: 160 });
    const t = tokens().find((x) => x.dataset.state === "tray") as HTMLButtonElement;
    t.dispatchEvent(point("pointerdown", 10, 10));
    t.dispatchEvent(point("pointermove", 150, 130));
    t.dispatchEvent(point("pointercancel", 150, 130));
    expect(Number(input().value)).toBe(2);
    expect(t.style.transform).toBe("");
  });
});

describe("massHanger: the audit and the accessibility fence", () => {
  it("every mass is a registered Kit action and a real, named, 44 px button; nothing on the page is an unowned number", () => {
    bench(4);
    expect(tokens()).toHaveLength(5);
    for (const t of tokens()) {
      expect(t.tagName).toBe("BUTTON");
      expect(isAction(t)).toBe(true);
      expect(t.getAttribute("aria-label")).toMatch(/^Mass [A-E], /);
    }
    expect(actions.filter((a) => a.kind === "drag")).toHaveLength(5);
    expect(STYLE).toMatch(/\.syn-mass\{min-width:44px;min-height:44px/);
    expect(STYLE).toContain("touch-action:none");
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    expect(a.forgedActions).toBe(0);
    expect(a.forbidden).toEqual([]);
    expect(a.controls.map((c) => c.id)).toEqual(["load"]);
  });

  it("a mass a page made itself is reported as a forged action", () => {
    bench();
    const fake = document.createElement("button");
    fake.setAttribute("data-synapse-action", "drag");
    fake.setAttribute("data-synapse-drag", "load");
    fake.textContent = "Mass Z";
    document.body.appendChild(fake);
    expect(isAction(fake)).toBe(false);
    expect(audit(KIT_VERSION).forgedActions).toBe(1);
  });

  it("the text of a mass cannot be turned into a number without the audit noticing", () => {
    bench();
    (tokens()[0] as HTMLButtonElement).setAttribute("aria-label", "Mass A is 9.81 N");
    expect(audit(KIT_VERSION).unownedAttributeNumbers.length).toBeGreaterThan(0);
  });
});

describe("springScene", () => {
  it("draws only the Hooke's law model's output, and needs a positive drawing scale", () => {
    const env = environment({ title: "t", note: "n" });
    expect(() => springScene(env, { extension: observable(0.1) as never, full: 0.25 })).toThrow(TypeError);
    expect(() => springScene(env, { extension: {} as never, full: 0.25 })).toThrow(TypeError);
    const current = massHanger(env, { id: "i", label: "Current", unit: "A", min: 0, max: 10, value: 2, grid: 5 });
    expect(() => springScene(env, { extension: current, full: 0.25 })).toThrow(TypeError);
    expect(() => springScene(env, { extension: current.map((v: number) => v * 2) as never, full: 0.25 })).toThrow(TypeError);
    const other = ohm({ voltage: current, resistance: current });
    expect(() => springScene(env, { extension: other, full: 0.25 })).toThrow(TypeError);
    const load = massHanger(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2, grid: 5 });
    const x = hookes({ k: 50, load });
    for (const full of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, "0.25" as unknown as number]) expect(() => springScene(env, { extension: x, full })).toThrow(RangeError);
  });

  it("stretches as the extension grows, describes itself in words only, and never prints a number", () => {
    const env = environment({ title: "t", note: "n" });
    const load = massHanger(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 0, grid: 5 });
    const x = hookes({ k: 50, load });
    const scene = springScene(env, { extension: x, full: 0.25 });
    const bottom = () => Number(scene.querySelector("rect")?.getAttribute("y"));
    const label = () => scene.getAttribute("aria-label") ?? "";
    const short = bottom();
    expect(label()).toBe("A spring hanging from a bracket, not stretched.");
    (document.querySelector("[data-synapse-drag='load']") as HTMLButtonElement).click();
    expect(bottom()).toBeGreaterThan(short);
    expect(label()).toBe("A spring hanging from a bracket, stretched a little.");
    for (const t of tokens()) if (t.dataset.state === "tray") t.click();
    expect(label()).toBe("A spring hanging from a bracket, stretched a lot.");
    expect(bottom()).toBeGreaterThan(short);
    expect(scene.textContent).toBe("");
    expect(/\d/.test(label())).toBe(false);
    expect(audit(KIT_VERSION).unownedAttributeNumbers).toEqual([]);
    expect(audit(KIT_VERSION).unownedNumbers).toEqual([]);
  });

  it("describes any fraction in words and clamps what it draws", () => {
    expect(["not stretched", "stretched a little", "stretched a fair amount", "stretched a lot"]).toEqual([0, 0.2, 0.5, 5].map(stretchWords));
  });
});

describe("the audit holds the bench and the scene to what the Kit built", () => {
  const widgetOf = (kind: string) => audit(KIT_VERSION).widgets.find((w) => w.kind === kind);

  it("reports a mass bench and a scene with no problems when nobody touched them, and the masses the Kit made", () => {
    const { env, extension } = bench(4);
    springScene(env, { extension, full: 0.25 });
    expect(widgetOf("masses")).toMatchObject({ id: "load", masses: 5, problems: [] });
    expect(widgetOf("scene")).toMatchObject({ id: "spring", problems: [], chain: { kind: "model", id: "mechanics.hookes" } });
  });

  it("reports a mass a page hid, moved, took out of the layout or put somewhere the control does not say", () => {
    bench(4);
    const [a, b, c] = tokens() as [HTMLButtonElement, HTMLButtonElement, HTMLButtonElement];
    a.style.display = "none";
    expect(widgetOf("masses")?.problems.some((p) => p.includes("mass A"))).toBe(true);
    a.removeAttribute("style");
    expect(widgetOf("masses")?.problems).toEqual([]);
    b.style.transform = "translate(900px, 0)";
    expect(widgetOf("masses")?.problems.some((p) => p.includes("mass B"))).toBe(true);
    b.removeAttribute("style");
    c.setAttribute("hidden", "");
    expect(widgetOf("masses")?.problems.some((p) => p.includes("mass C"))).toBe(true);
    c.removeAttribute("hidden");
    hanger().appendChild(c); // shown on the hanger while the control says it is in the tray
    expect(widgetOf("masses")?.problems.some((p) => p.includes("mass C"))).toBe(true);
  });

  it("reports a bench taken apart or hidden, and violations() carries every problem to the runtime self-check", async () => {
    bench(2);
    (document.querySelector(".syn-masses") as HTMLElement).style.visibility = "hidden";
    const { violations } = await import("./audit");
    expect(violations(audit(KIT_VERSION)).some((v) => v.includes("hidden"))).toBe(true);
  });

  it("reports a scene a page redrew, relabelled, moved or hid", () => {
    const { env, extension } = bench(4);
    const scene = springScene(env, { extension, full: 0.25 });
    scene.querySelector("polyline")?.setAttribute("points", "0,0 1,1");
    expect(widgetOf("scene")?.problems.some((p) => p.includes("redrawn"))).toBe(true);
    extension.get();
    (document.querySelector("[data-synapse-drag='load'][data-state='tray']") as HTMLButtonElement).click(); // the Kit redraws it
    expect(widgetOf("scene")?.problems).toEqual([]);
    scene.setAttribute("aria-label", "A spring that is not stretched");
    expect(widgetOf("scene")?.problems.some((p) => p.includes("description"))).toBe(true);
    scene.remove();
    expect(widgetOf("scene")?.problems.some((p) => p.includes("moved"))).toBe(true);
  });

  it("announces the hanger in a polite live region made of words", () => {
    bench(4);
    const live = document.querySelector(".syn-masses [role='status']") as HTMLElement;
    expect(live.getAttribute("aria-live")).toBe("polite");
    expect(live.textContent).toBe("Hanger, holding two masses");
    (document.querySelector("[data-synapse-drag='load'][data-state='tray']") as HTMLButtonElement).click();
    expect(live.textContent).toBe("Hanger, holding three masses");
    expect(audit(KIT_VERSION).ownedMismatches).toEqual([]);
  });
});

describe("the second review: captions, the scene's style and the layout half", () => {
  it("the Tray and Hanger captions are Kit-owned text: swapping them is reported", () => {
    bench(4);
    const caps = document.querySelectorAll(".syn-cap");
    const first = caps[0] as HTMLElement;
    first.textContent = "Hanger";
    expect(audit(KIT_VERSION).ownedMismatches.length).toBeGreaterThan(0);
  });

  it("a scene whose coil was restyled by an attribute is reported, and records the scale it was given", () => {
    const { env, extension } = bench(4);
    const scene = springScene(env, { extension, full: 0.25 });
    expect(audit(KIT_VERSION).widgets.find((w) => w.kind === "scene")?.full).toBe(0.25);
    scene.querySelector("polyline")?.setAttribute("stroke", "none");
    expect(audit(KIT_VERSION).widgets.find((w) => w.kind === "scene")?.problems.some((p) => p.includes("restyled"))).toBe(true);
  });

  it("without a layout engine the layout half reports nothing, and the student's self-check never acts on it", async () => {
    const { env, extension } = bench(4);
    springScene(env, { extension, full: 0.25 });
    for (const w of audit(KIT_VERSION).widgets) expect(w.layout).toEqual([]);
    const { violations } = await import("./audit");
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });
});
