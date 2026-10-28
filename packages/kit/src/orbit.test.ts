import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { constant } from "./constant";
import { environment } from "./environment";
import { KIT_VERSION } from "./index";
import { observable } from "./observable";
import { CIRCLE_BAND, flightFor, outcomeOf, orbitScene, outcomeWords, pathFor } from "./orbit_scene";
import { resetForTests } from "./provenance";
import { readout } from "./readout";
import { circularSpeed } from "./science/circular_speed";
import { escapeSpeed } from "./science/escape_speed";
import { slider } from "./slider";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

const EARTH = 5.972e24;

function bench(value = 7.9) {
  const env = environment({ title: "Orbit", note: "A cannonball fired sideways from a tall mountain." });
  const launch = slider(env, { id: "launch", label: "Launch speed", unit: "km/s", min: 1, max: 15, value });
  const radius = constant(6371, { label: "Distance from Earth's centre", unit: "km" });
  const circular = circularSpeed({ radius, central_mass: EARTH });
  const escape = escapeSpeed({ radius, central_mass: EARTH });
  readout(env, { label: "Circular speed", unit: "km/s", value: circular, digits: 2 });
  readout(env, { label: "Escape speed", unit: "km/s", value: escape, digits: 2 });
  return { env, launch, radius, circular, escape };
}
const widgetOf = (id: string) => {
  const w = audit(KIT_VERSION).widgets.find((x) => x.id === id);
  return w && { ...w, problems: [...w.problems, ...w.exact] };
};

describe("outcomeOf: the one rule", () => {
  const c = 7.91;
  const e = c * Math.SQRT2;
  it("falls below the circular speed, circles within the band, goes oval between, and escapes at the escape speed or more", () => {
    expect(outcomeOf(3, c, e)).toBe("falls");
    expect(outcomeOf(c * (1 - CIRCLE_BAND) - 0.001, c, e)).toBe("falls");
    expect(outcomeOf(c * (1 - CIRCLE_BAND) + 0.001, c, e)).toBe("circle");
    expect(outcomeOf(c, c, e)).toBe("circle");
    expect(outcomeOf(c * (1 + CIRCLE_BAND) - 0.001, c, e)).toBe("circle");
    expect(outcomeOf(c * (1 + CIRCLE_BAND) + 0.001, c, e)).toBe("oval");
    expect(outcomeOf(e - 0.001, c, e)).toBe("oval");
    expect(outcomeOf(e, c, e)).toBe("escapes");
    expect(outcomeOf(14, c, e)).toBe("escapes");
  });
  it("gives every outcome words with no digit in them", () => {
    for (const o of ["falls", "circle", "oval", "escapes"] as const) expect(/\d/.test(outcomeWords(o))).toBe(false);
  });
});

describe("pathFor: a drawing that follows the speed ratio and stays on the canvas", () => {
  it("makes a different path for each outcome and keeps every number inside the picture", () => {
    const paths = [pathFor("falls", 0.5), pathFor("circle", 1), pathFor("oval", 1.2), pathFor("escapes", 1.5)];
    expect(new Set(paths).size).toBe(4);
    for (const p of paths) for (const n of p.match(/-?\d+(\.\d+)?/g) ?? []) expect(Math.abs(Number(n))).toBeLessThanOrEqual(260);
  });
  it("draws a longer oval for a higher speed", () => {
    expect(pathFor("oval", 1.05)).not.toBe(pathFor("oval", 1.35));
  });
});

describe("orbitScene: what it refuses", () => {
  it("draws only a km/s control and the two speed models fed by one radius constant, with Earth's radius and mass, at a scale that holds the control's range", () => {
    const { env, launch, radius, circular, escape } = bench();
    expect(() => orbitScene(env, { speed: observable(7) as never, circular, escape, full: 15 })).toThrow(TypeError);
    expect(() => orbitScene(env, { speed: launch, circular: observable(1) as never, escape, full: 15 })).toThrow(TypeError);
    expect(() => orbitScene(env, { speed: launch, circular, escape: circular, full: 15 })).toThrow(TypeError); // the same model twice
    expect(() => orbitScene(env, { speed: launch, circular: escape, escape: circular, full: 15 })).toThrow(TypeError); // swapped
    expect(() => orbitScene(env, { speed: circular, circular, escape, full: 15 })).toThrow(TypeError); // a model is not a control
    // two different radius constants
    const other = constant(6371, { label: "A second radius", unit: "km" });
    expect(() => orbitScene(env, { speed: launch, circular, escape: escapeSpeed({ radius: other, central_mass: EARTH }), full: 15 })).toThrow(TypeError);
    // a radius that is a control, not a constant
    const wild = slider(env, { id: "wild", label: "Wild radius", unit: "km", min: 6371, max: 7000, value: 6371 });
    expect(() => orbitScene(env, { speed: launch, circular: circularSpeed({ radius: wild, central_mass: EARTH }), escape: escapeSpeed({ radius: wild, central_mass: EARTH }), full: 15 })).toThrow(TypeError);
    // not Earth's mass, not Earth's radius, not km
    expect(() => orbitScene(env, { speed: launch, circular: circularSpeed({ radius, central_mass: 6.4e23 }), escape: escapeSpeed({ radius, central_mass: 6.4e23 }), full: 15 })).toThrow(RangeError);
    expect(() => orbitScene(env, { speed: launch, circular, escape: escapeSpeed({ radius, central_mass: 5.97e24 }), full: 15 })).toThrow(RangeError); // two different masses
    const moon = constant(1737, { label: "Moon radius", unit: "km" });
    expect(() => orbitScene(env, { speed: launch, circular: circularSpeed({ radius: moon, central_mass: EARTH }), escape: escapeSpeed({ radius: moon, central_mass: EARTH }), full: 15 })).toThrow(RangeError);
    const metres = constant(6371000, { label: "Radius in metres", unit: "m" });
    expect(() => orbitScene(env, { speed: launch, circular: circularSpeed({ radius: metres, central_mass: EARTH }), escape: escapeSpeed({ radius: metres, central_mass: EARTH }), full: 15 })).toThrow(RangeError);
    for (const full of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, "15" as unknown as number]) expect(() => orbitScene(env, { speed: launch, circular, escape, full })).toThrow(RangeError);
    expect(() => orbitScene(env, { speed: launch, circular, escape, full: 14 })).toThrow(RangeError);
    orbitScene(env, { speed: launch, circular, escape, full: 15 });
  });
});

describe("orbitScene: the picture follows the numbers, in words", () => {
  it("shows each of the four outcomes as the slider moves, with words only and a sketch caveat", () => {
    const { env, launch, circular, escape } = bench(3);
    orbitScene(env, { speed: launch, circular, escape, full: 15 });
    const root = document.querySelector(".syn-orbit-scene") as SVGSVGElement;
    const note = () => document.querySelector("[data-synapse-observations]")?.textContent ?? "";
    const path = () => root.querySelector("path[stroke-width='3']")?.getAttribute("d");
    expect(note()).toContain(outcomeWords("falls"));
    const seen = new Set<string | null | undefined>([path()]);
    launch.set(7.9);
    expect(note()).toContain(outcomeWords("circle"));
    seen.add(path());
    launch.set(9.5);
    expect(note()).toContain(outcomeWords("oval"));
    seen.add(path());
    launch.set(12);
    expect(note()).toContain(outcomeWords("escapes"));
    seen.add(path());
    expect(seen.size).toBe(4);
    expect(note()).toContain("not to scale");
    expect(/\d/.test(note())).toBe(false);
    expect(/\d/.test(root.getAttribute("aria-label") ?? "")).toBe(false);
    const a = audit(KIT_VERSION);
    expect(a.unownedNumbers).toEqual([]);
    expect(a.unownedAttributeNumbers).toEqual([]);
    expect(a.ownedMismatches).toEqual([]);
  });

  it("makes the launch arrow longer for a higher speed and never longer than its box", () => {
    const { env, launch, circular, escape } = bench(1);
    orbitScene(env, { speed: launch, circular, escape, full: 15 });
    const x2 = () => Number(document.querySelector(".syn-orbit-scene line")?.getAttribute("x2"));
    const slow = x2();
    launch.set(15);
    expect(x2()).toBeGreaterThan(slow);
    expect(x2()).toBeLessThanOrEqual(260);
  });
});

describe("orbitScene: the audit", () => {
  it("reports a clean scene with its three chains, and every way a page can falsify it", () => {
    const { env, launch, circular, escape } = bench(9.5);
    orbitScene(env, { speed: launch, circular, escape, full: 15 });
    const w = widgetOf("orbit");
    expect(w).toMatchObject({
      kind: "scene",
      id: "orbit",
      full: 15,
      problems: [],
      chain: { kind: "model", id: "physics.circular_speed" },
      secondChain: { kind: "model", id: "physics.escape_speed" },
      sourceChain: { kind: "control", id: "launch" },
    });
    const root = document.querySelector(".syn-orbit-scene") as SVGSVGElement;
    const problems = () => widgetOf("orbit")?.problems ?? [];
    root.querySelector("path[stroke-width='3']")?.setAttribute("d", "M 0 0 L 1 1");
    expect(problems().length).toBeGreaterThan(0);
    launch.set(9);
    launch.set(9.5);
    expect(problems()).toEqual([]);
    root.querySelector("circle[r='26.0']")?.setAttribute("fill-opacity", "0");
    expect(problems().length).toBeGreaterThan(0);
    root.querySelector("circle[r='26.0']")?.removeAttribute("fill-opacity");
    root.querySelector("path[stroke-width='3']")?.setAttribute("stroke", "var(--syn-bg)");
    expect(problems().length).toBeGreaterThan(0);
    launch.set(9);
    launch.set(9.5);
    const extra = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    root.appendChild(extra);
    expect(problems().length).toBeGreaterThan(0);
    root.removeChild(extra);
    const loose = document.createElementNS("http://www.w3.org/2000/svg", "text");
    loose.textContent = "Mars";
    root.querySelector("text")!.after(loose);
    expect(problems().length).toBeGreaterThan(0);
    loose.remove();
    expect(problems()).toEqual([]);
    root.querySelector("text")!.textContent = "Moon";
    expect(audit(KIT_VERSION).ownedMismatches.length).toBeGreaterThan(0);
  });

  it("notices a page hiding the picture and rewriting its description", () => {
    const { env, launch, circular, escape } = bench(9.5);
    orbitScene(env, { speed: launch, circular, escape, full: 15 });
    const root = document.querySelector(".syn-orbit-scene") as SVGSVGElement;
    root.setAttribute("aria-label", "The cannonball lands on Earth.");
    expect(widgetOf("orbit")?.problems.length).toBeGreaterThan(0);
  });

  it("the layout half is empty without a layout engine, and the student's self-check acts on structure only", () => {
    const { env, launch, circular, escape } = bench(9.5);
    orbitScene(env, { speed: launch, circular, escape, full: 15 });
    for (const w of audit(KIT_VERSION).widgets) expect(w.layout).toEqual([]);
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });
});

describe("orbitScene: the launch", () => {
  const ballOf = (root: Element) => root.querySelector("circle[r='4.5']") as SVGCircleElement;
  it("has a Launch button the Kit registered, a ball that is hidden until it is pressed, and a trail kept for each finished launch", async () => {
    const { env, launch, circular, escape } = bench(5);
    orbitScene(env, { speed: launch, circular, escape, full: 15 });
    const root = document.querySelector(".syn-orbit-scene") as SVGSVGElement;
    const button = document.querySelector("[data-synapse-action='launch']") as HTMLButtonElement;
    expect(button.textContent).toBe("Launch");
    expect(audit(KIT_VERSION).actions.some((a) => a.kind === "launch")).toBe(true);
    expect(ballOf(root).getAttribute("fill-opacity")).toBe("0");
    // jsdom has no matchMedia: the flight runs on timers, so a launch ends within the fall's 1.6 s plus a frame.
    button.click();
    expect(ballOf(root).getAttribute("fill-opacity")).toBe("1");
    expect(widgetOf("orbit")?.problems).toEqual([]);
    await new Promise((r) => setTimeout(r, 1800));
    const trails = Array.from(root.querySelectorAll("path[stroke-width='2']"));
    expect(trails[0]?.getAttribute("stroke-opacity")).toBe("0.4");
    expect(trails[1]?.getAttribute("stroke-opacity")).toBe("0");
    expect(widgetOf("orbit")?.problems).toEqual([]);
  });
  it("hides the ball again when the speed changes, and a page that moves the ball is reported", () => {
    const { env, launch, circular, escape } = bench(5);
    orbitScene(env, { speed: launch, circular, escape, full: 15 });
    const root = document.querySelector(".syn-orbit-scene") as SVGSVGElement;
    (document.querySelector("[data-synapse-action='launch']") as HTMLButtonElement).click();
    launch.set(9);
    expect(ballOf(root).getAttribute("fill-opacity")).toBe("0");
    ballOf(root).setAttribute("cx", "5");
    expect(widgetOf("orbit")?.problems.length).toBeGreaterThan(0);
  });
});

describe("flightFor: the worked-out path agrees with the Kit's one rule", () => {
  const e = Math.SQRT2;
  it("ends on the ground below the circular speed's band, and not above it", () => {
    expect(flightFor("falls", 0.5).ends).toBe("ground");
    expect(flightFor("falls", 1 - CIRCLE_BAND - 0.002).ends).toBe("ground");
    expect(flightFor("circle", 1 - CIRCLE_BAND + 0.002).ends).not.toBe("ground");
  });
  it("goes round a circle at a steady distance and comes back to where it began", () => {
    const flight = flightFor("circle", 1);
    expect(flight.ends).toBe("lap");
    const start = flight.at(0);
    const end = flight.at(1);
    expect(Math.hypot(start.x - end.x, start.y - end.y)).toBeLessThan(3);
    for (const f of [0.1, 0.3, 0.5, 0.7, 0.9]) {
      const p = flight.at(f);
      expect(Math.abs(Math.hypot(p.x - 130, p.y - 118) - 28.2)).toBeLessThan(1.5);
    }
  });
  it("goes further from Earth on an oval than on a circle, and leaves the picture at the escape speed", () => {
    const far = (r: number) => Math.max(...[0, 0.25, 0.5, 0.75].map((f) => Math.hypot(flightFor("oval", r).at(f).x - 130, flightFor("oval", r).at(f).y - 118)));
    expect(far(1.25)).toBeGreaterThan(far(1.05));
    expect(flightFor("escapes", e).ends).toBe("away");
    expect(flightFor("escapes", 1.8).ends).toBe("away");
  });
  it("is quick near Earth and slow far from it", () => {
    const flight = flightFor("oval", 1.25);
    const dist = (a: number, b: number) => Math.hypot(flight.at(a).x - flight.at(b).x, flight.at(a).y - flight.at(b).y);
    expect(dist(0, 0.02)).toBeGreaterThan(dist(0.49, 0.51));
  });
});
