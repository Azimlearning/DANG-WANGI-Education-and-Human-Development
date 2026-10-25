import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { constant } from "./constant";
import { environment } from "./environment";
import { KIT_VERSION } from "./index";
import { observable } from "./observable";
import { actions, isAction, resetForTests } from "./provenance";
import { readout } from "./readout";
import { titrationEndpoint } from "./science/titration_endpoint";
import { titration } from "./science/titration";
import { buretteWords, eyeWords, titrationScene } from "./titration_scene";
import { valve } from "./valve";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const press = (type: string, init: Record<string, unknown> = {}) => new MouseEvent(type, { bubbles: true, button: 0, ...init });

function bench(value = 5) {
  const env = environment({ title: "Titration", note: "Run alkali into the acid." });
  const added = valve(env, { id: "vb", label: "Alkali run in", unit: "cm3", min: 5, max: 40, value, grid: 7 });
  const va = constant(25, { label: "Volume of acid", unit: "cm3" });
  const mb = constant(0.125, { label: "True concentration of the alkali", unit: "mol/dm3" });
  const end = titrationEndpoint({ va, mb, ma: 0.1, acid_coeff: 1, base_coeff: 1 });
  const conc = titration({ va, vb: added, ma: 0.1, acid_coeff: 1, base_coeff: 1 });
  readout(env, { label: "Concentration of the alkali", unit: "mol/dm3", value: conc, digits: 3 });
  return { env, added, end };
}
const stopcock = () => document.querySelector<HTMLButtonElement>("[data-synapse-valve='vb']") as HTMLButtonElement;
const input = () => document.querySelector<HTMLInputElement>("input[data-synapse-control='vb']") as HTMLInputElement;
const widgetOf = (id: string) => audit(KIT_VERSION).widgets.find((w) => w.id === id);

describe("valve: what it refuses", () => {
  it("needs 2 to 40 steps, a start on a step, a unique id and a real range", () => {
    const env = environment({ title: "t", note: "n" });
    const base = { id: "a", label: "Run in", unit: "cm3", min: 5, max: 40, value: 5 };
    for (const grid of [1, 41, 2.5, 0, -3, Number.NaN]) expect(() => valve(env, { ...base, id: `g${grid}`, grid })).toThrow(RangeError);
    for (const value of [6, 7.5, 39]) expect(() => valve(env, { ...base, id: `v${value}`, grid: 7, value })).toThrow(RangeError);
    valve(env, { ...base, grid: 7 });
    expect(() => valve(env, { ...base, grid: 7 })).toThrow(RangeError);
    expect(() => valve(env, { ...base, id: "b", min: 5, max: 5, grid: 7 })).toThrow(RangeError);
  });
});

describe("valve: it is a control exactly as a slider is", () => {
  it("keeps the range input declared and named, snaps what a script sets, and registers the stopcock as a Kit action", () => {
    const { added } = bench();
    expect(input().getAttribute("data-synapse-control")).toBe("vb");
    expect(input().getAttribute("aria-valuetext")).toBe("5 cm3");
    added.set(11.3);
    expect(added.get()).toBe(10);
    added.set(99);
    expect(added.get()).toBe(40);
    expect(isAction(stopcock())).toBe(true);
    expect(actions.filter((a) => a.kind === "valve")).toHaveLength(1);
    expect(stopcock().getAttribute("aria-label")).toMatch(/^Stopcock\./);
    expect(/\d/.test(stopcock().getAttribute("aria-label") ?? "")).toBe(false);
  });
});

describe("valve: the tap, the keyboard and the hold", () => {
  it("a press (a click, which is also what Enter and Space send) lets out one step and stops at the limit", () => {
    const { added } = bench(5);
    stopcock().click();
    expect(added.get()).toBe(10);
    expect(input().value).toBe("10");
    for (let i = 0; i < 20; i++) stopcock().click();
    expect(added.get()).toBe(40);
  });

  it("holding runs the liquid, letting go stops it, and the click after a hold adds nothing", async () => {
    const { added } = bench(5);
    stopcock().dispatchEvent(press("pointerdown"));
    await wait(750);
    const running = added.get();
    expect(running).toBeGreaterThanOrEqual(15);
    expect(stopcock().classList.contains("syn-open")).toBe(true);
    stopcock().dispatchEvent(press("pointerup"));
    stopcock().click(); // some browsers send a click after a long press
    const stopped = added.get();
    expect(stopped).toBeGreaterThanOrEqual(running);
    await wait(400);
    expect(added.get()).toBe(stopped);
    expect(stopcock().classList.contains("syn-open")).toBe(false);
  });

  it("a quick press and release is a tap: it adds nothing by itself and the click adds one step", async () => {
    const { added } = bench(5);
    stopcock().dispatchEvent(press("pointerdown"));
    stopcock().dispatchEvent(press("pointerup"));
    await wait(400);
    expect(added.get()).toBe(5);
    stopcock().click();
    expect(added.get()).toBe(10);
  });

  it("a held stopcock that loses focus or is cancelled stops, and the flow stops by itself at the limit", async () => {
    const { added } = bench(35);
    stopcock().dispatchEvent(press("pointerdown"));
    await wait(700);
    expect(added.get()).toBe(40);
    expect(stopcock().classList.contains("syn-open")).toBe(false);
    const { added: again } = (() => {
      resetForTests();
      document.body.innerHTML = "";
      return bench(5);
    })();
    stopcock().dispatchEvent(press("pointerdown"));
    await wait(450);
    stopcock().dispatchEvent(new Event("blur"));
    const at = again.get();
    await wait(400);
    expect(again.get()).toBe(at);
  });
});

describe("valve: the audit", () => {
  it("is reported with no problems, names no number, and a stopcock a page moved or hid is reported", () => {
    bench();
    expect(widgetOf("vb")).toMatchObject({ kind: "valve", problems: [], layout: [] });
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    expect(a.forgedActions).toBe(0);
    stopcock().style.display = "none";
    expect(widgetOf("vb")?.problems.length).toBeGreaterThan(0);
    stopcock().removeAttribute("style");
    expect(widgetOf("vb")?.problems).toEqual([]);
    stopcock().setAttribute("hidden", "");
    expect(violations(audit(KIT_VERSION)).some((v) => v.includes("stopcock"))).toBe(true);
  });

  it("a stopcock whose label was rewritten with a number is reported", () => {
    bench();
    stopcock().setAttribute("aria-label", "Stopcock, 25 cm3 run in");
    expect(audit(KIT_VERSION).unownedAttributeNumbers.length).toBeGreaterThan(0);
  });
});

describe("titrationScene: what it refuses", () => {
  it("draws only a cm3 control and the end-point model, at a scale that holds the control's range", () => {
    const { env, added, end } = bench();
    expect(() => titrationScene(env, { added: observable(10) as never, endpoint: end, full: 50 })).toThrow(TypeError);
    expect(() => titrationScene(env, { added, endpoint: observable(20) as never, full: 50 })).toThrow(TypeError);
    expect(() => titrationScene(env, { added, endpoint: added, full: 50 })).toThrow(TypeError);
    expect(() => titrationScene(env, { added: end, endpoint: end, full: 50 })).toThrow(TypeError);
    for (const full of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, "50" as unknown as number]) expect(() => titrationScene(env, { added, endpoint: end, full })).toThrow(RangeError);
    expect(() => titrationScene(env, { added, endpoint: end, full: 30 })).toThrow(RangeError); // the control can run in 40
    titrationScene(env, { added, endpoint: end, full: 50 });
  });
});

describe("titrationScene: the picture follows the numbers, in words", () => {
  it("empties the burette, turns the flask pink at the end point, and prints no number", () => {
    const { env, added, end } = bench(5);
    titrationScene(env, { added, endpoint: end, full: 50 });
    const root = document.querySelector(".syn-titration") as SVGSVGElement;
    const liquidTop = () => Number(root.querySelector("rect[fill='var(--syn-liquid)']")?.getAttribute("y"));
    const flask = () => root.querySelector("path")?.getAttribute("fill");
    const first = liquidTop();
    expect(flask()).toBe("var(--syn-card)");
    expect(root.getAttribute("aria-label")).toBe("A burette above a flask: the burette is nearly full, and the liquid in the flask is still colourless.");
    added.set(15);
    expect(liquidTop()).toBeGreaterThan(first);
    expect(flask()).toBe("var(--syn-card)");
    added.set(20); // the end point of 25 cm3 of 0.1 mol/dm3 acid and 0.125 mol/dm3 alkali is 20 cm3
    expect(flask()).toBe("var(--syn-indicator)");
    expect(root.getAttribute("aria-label")).toContain("has turned pink");
    added.set(40);
    expect(root.getAttribute("aria-label")).toContain("nearly empty");
    expect(/\d/.test(root.getAttribute("aria-label") ?? "")).toBe(false);
    expect(root.textContent).toBe("");
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
  });

  it("the eye moves with the arrow keys and a drag, and says in words whether it reads level, too high or too low", () => {
    const { env, added, end } = bench(5);
    titrationScene(env, { added, endpoint: end, full: 50 });
    added.set(20);
    const eye = document.querySelector("[data-synapse-eye]") as HTMLButtonElement;
    const note = document.querySelector("[data-synapse-eye-status]") as HTMLElement;
    const key = (k: string) => eye.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
    key("Home");
    expect(note.textContent).toBe("Your eye is above the meniscus. Bring it level with the meniscus before you read.");
    key("End");
    expect(note.textContent).toBe("Your eye is below the meniscus. Bring it level with the meniscus before you read.");
    // the meniscus sits at 20/50 of the burette: 0.4
    key("Home");
    for (let i = 0; i < 8; i++) key("ArrowDown");
    expect(note.textContent).toBe("Your eye is level with the meniscus, so this is a fair reading.");
    key("ArrowDown");
    key("ArrowDown");
    expect(note.textContent).toContain("below");
    // a drag: the picture is 220 by 280 units drawn 220 by 280 px at the origin, the burette runs from 20 to 150
    const root = document.querySelector(".syn-titration") as SVGSVGElement;
    root.getBoundingClientRect = () => ({ left: 0, top: 0, right: 220, bottom: 280, width: 220, height: 280, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
    eye.dispatchEvent(press("pointerdown", { clientY: 20 + 0.4 * 130, clientX: 120 }));
    expect(note.textContent).toBe("Your eye is level with the meniscus, so this is a fair reading.");
    eye.dispatchEvent(press("pointermove", { clientY: 10, clientX: 120 }));
    expect(note.textContent).toContain("above");
    eye.dispatchEvent(press("pointerup", { clientY: 10, clientX: 120 }));
    eye.dispatchEvent(press("pointermove", { clientY: 150, clientX: 120 })); // not dragging any more
    expect(note.textContent).toContain("above");
  });

  it("describes any fraction in words", () => {
    expect([0, 0.2, 0.5, 0.9].map(buretteWords)).toEqual(["full", "nearly full", "about half empty", "nearly empty"]);
    expect(eyeWords(0.4, 0.4)).toContain("level");
    expect(eyeWords(0.1, 0.4)).toContain("above");
    expect(eyeWords(0.9, 0.4)).toContain("below");
  });
});

describe("titrationScene: the audit", () => {
  it("reports a clean scene with its chains and an eye, and every way a page can falsify it", () => {
    const { env, added, end } = bench(5);
    titrationScene(env, { added, endpoint: end, full: 50 });
    added.set(20);
    const w = widgetOf("titration");
    expect(w).toMatchObject({ kind: "scene", id: "titration", full: 50, eye: true, problems: [], chain: { kind: "model", id: "chemistry.titration_endpoint_volume" }, sourceChain: { kind: "control", id: "vb" } });
    const root = document.querySelector(".syn-titration") as SVGSVGElement;
    const eye = document.querySelector("[data-synapse-eye]") as HTMLElement;
    const problems = () => widgetOf("titration")?.problems ?? [];

    root.querySelector("rect[fill='var(--syn-liquid)']")?.setAttribute("y", "40");
    expect(problems().some((p) => p.includes("liquid"))).toBe(true);
    added.set(25);
    added.set(20);
    expect(problems()).toEqual([]);

    root.querySelector("path")?.setAttribute("fill", "var(--syn-card)"); // the flask should be pink at the end point
    expect(problems().some((p) => p.includes("colour"))).toBe(true);
    added.set(25);
    added.set(20);
    expect(problems()).toEqual([]);

    eye.style.top = "5%";
    expect(problems().some((p) => p.includes("eye"))).toBe(true);
    eye.setAttribute("style", `top:${(((20 + 0 * 130) / 280) * 100).toFixed(2)}%`);
    expect(problems()).toEqual([]);

    root.setAttribute("aria-label", "A full burette above a pink flask.");
    expect(problems().some((p) => p.includes("description"))).toBe(true);
    added.set(25);
    added.set(20);

    (document.querySelector("[data-synapse-eye-status]") as HTMLElement).textContent = "Your eye is level with the meniscus, so this is a fair reading.";
    document.querySelector("[data-synapse-eye-status]")!.textContent = "A different sentence.";
    expect(audit(KIT_VERSION).ownedMismatches.length).toBeGreaterThan(0);
  });

  it("the layout half is empty without a layout engine, and the student's self-check acts on structure only", () => {
    const { env, added, end } = bench(5);
    titrationScene(env, { added, endpoint: end, full: 50 });
    for (const w of audit(KIT_VERSION).widgets) expect(w.layout).toEqual([]);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });
});
