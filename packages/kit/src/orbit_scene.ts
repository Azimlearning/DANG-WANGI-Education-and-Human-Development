// `orbitScene(env, {speed, circular, escape, full})`: Newton's cannonball. A cannon on a very tall mountain fires sideways; the picture shows where it goes. It DRAWS and prints no number: the launch speed
// (`speed`, a control in km/s, the one a plain slider makes), the circular speed (`circular`, the output of the circular-speed model) and the escape speed (`escape`, the output of the escape-speed
// model), both for Earth at the cannon's distance from Earth's centre. Below the circular speed the cannonball falls back to Earth; at the circular speed (within 2 percent) it circles Earth;
// between the two it goes round in an oval; at the escape speed or more it leaves for good. Its text is words only, and says the picture is a schematic.
//
// What is drawn follows the numbers and nothing else: the audit keeps the exact attributes of every part and the elements inside the picture, and the verifier checks that the scene draws a
// control in km/s and the two models fed by one declared radius, with Earth's mass.

import { event } from "./bridge";
import { all, attr, contains, effectiveOpacity, hitAt, layoutAvailable, parentOf, rectOf, style } from "./dom";
import type { Environment } from "./environment";
import { dragAlong, quiet } from "./handles";
import { kt } from "./i18n";
import type { Observable } from "./observable";
import { guard } from "./parts";
import { constants, controls, markKitSvg, nodeOf, own, ownAttr, registerAction, widgets } from "./provenance";

const NS = "http://www.w3.org/2000/svg";
const W = 260;
const H = 240;
const CIRCULAR_MODEL = "physics.circular_speed";
const ESCAPE_MODEL = "physics.escape_speed";
/** Earth's mass, in kg, as the textbooks give it. The words and the picture are about Earth, so the scene is pinned to it, not to any central mass. */
export const EARTH_MASSES: readonly number[] = [5.97e24, 5.972e24];
/** The radius, in km, a cannon on Earth's surface is from Earth's centre (the textbooks use 6371 or 6378 km). */
export const EARTH_RADIUS_KM: readonly [number, number] = [6371, 6378.2];
/** How close to the circular speed counts as a circle: this fraction of it. */
export const CIRCLE_BAND = 0.02;

const CX = 130;
const CY = 118;
const EARTH_R = 26;
/** The cannon's distance from Earth's centre, in Earth radii. Chosen so that the 2 percent band below the circular speed is exactly where the worked-out path stops missing the ground. */
const R0 = 1.083;
const LAUNCH_R = EARTH_R * R0;
const LAUNCH_Y = CY - LAUNCH_R;
/** A path leaves the picture beyond this many Earth radii. */
const VIEW_R = 4.5;
/** The sky is dark in either theme, as in V3; the path is coloured by what the cannonball does. */
const SKY = "#0b1020";
const FALL_COLOUR = "#e2795f";
const ORBIT_COLOUR = "#3fb6a2";
const ESCAPE_COLOUR = "#e6b93f";

export type Outcome = "falls" | "circle" | "oval" | "escapes";

export interface OrbitSceneOptions {
  /** The launch speed: a control in km/s. */
  speed: Observable<number>;
  /** The circular speed: the output of the circular-speed model. */
  circular: Observable<number>;
  /** The escape speed: the output of the escape-speed model, fed by the same radius as `circular`. */
  escape: Observable<number>;
  /** The launch speed, in the control's unit, at which the launch arrow is drawn at its longest: a drawing scale, never shown. At least the control's maximum. */
  full: number;
}

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

/** Which of the four things the cannonball does. The one rule everything (the picture, the sentence, the verifier) uses. */
export function outcomeOf(speed: number, circular: number, escape: number): Outcome {
  if (speed >= escape) return "escapes";
  if (Math.abs(speed - circular) <= CIRCLE_BAND * circular) return "circle";
  return speed < circular ? "falls" : "oval";
}

const WORD_KEYS = { falls: "orbitFalls", circle: "orbitCircle", oval: "orbitOval", escapes: "orbitEscapes" } as const;
const words = (o: Outcome): string => kt(WORD_KEYS[o]);
const schematic = (): string => kt("orbitSketch");

export function outcomeWords(o: Outcome): string {
  return words(o);
}

const f = (n: number): string => n.toFixed(1);

/** A worked-out flight: the path to draw, and where the ball is at any fraction of the time it takes (the ball is quick near Earth and slow far from it, as in life). */
export interface Flight {
  d: string;
  /** Where the flight ends: on the ground, back where it began (a lap), or away out of the picture. */
  ends: "ground" | "lap" | "away";
  at(fraction: number): { x: number; y: number };
}

const flights = new Map<string, Flight>();

/**
 * Newton's cannonball, worked out. Units: Earth's radius 1 and GM = 1, so the circular speed at the cannon is sqrt(1 / R0) and the escape speed is sqrt(2) times that. The launch
 * speed is the control's speed divided by the circular speed the MODEL gave, times that: so the picture follows the model's two speeds, and the circle and the escape fall exactly
 * where the model says they do. Integrated with RK4 and a step that shrinks near Earth.
 */
export function flightFor(o: Outcome, ratio: number): Flight {
  const key = `${o}:${ratio.toFixed(4)}`;
  const hit = flights.get(key);
  if (hit) return hit;
  const k = Math.max(0.0001, ratio) ** 2;
  const speed = Math.sqrt(k / R0);
  const apo = k < 2 ? (R0 * k) / (2 - k) : Infinity;
  const closed = (o === "circle" || o === "oval") && apo <= VIEW_R;
  let x = 0;
  let y = -R0;
  let vx = speed;
  let vy = 0;
  let t = 0;
  const period = closed ? 2 * Math.PI * ((R0 + apo) / 2) ** 1.5 : Infinity;
  const xs = [x];
  const ys = [y];
  const ts = [0];
  const acc = (px: number, py: number): [number, number] => {
    const r2 = px * px + py * py;
    const c = -1 / (r2 * Math.sqrt(r2));
    return [px * c, py * c];
  };
  let ends: Flight["ends"] = closed ? "lap" : "away";
  for (let n = 0; n < 30000; n++) {
    const r = Math.hypot(x, y);
    let dt = 0.012 * r ** 1.5;
    if (closed && t + dt > period) dt = period - t;
    // Runge-Kutta-Nystrom: the acceleration depends only on where the ball is, so the second and third slopes coincide.
    const [a1x, a1y] = acc(x, y);
    const [a2x, a2y] = acc(x + 0.5 * dt * vx + (dt * dt * a1x) / 8, y + 0.5 * dt * vy + (dt * dt * a1y) / 8);
    const [a4x, a4y] = acc(x + dt * vx + 0.5 * dt * dt * a2x, y + dt * vy + 0.5 * dt * dt * a2y);
    const nx = x + dt * vx + (dt * dt * (a1x + 2 * a2x)) / 6;
    const ny = y + dt * vy + (dt * dt * (a1y + 2 * a2y)) / 6;
    vx += (dt * (a1x + 4 * a2x + a4x)) / 6;
    vy += (dt * (a1y + 4 * a2y + a4y)) / 6;
    x = nx;
    y = ny;
    t += dt;
    const rr = Math.hypot(x, y);
    if (rr <= 1) {
      // Scale the last step back onto the ground so the path ends on Earth's edge.
      x /= rr;
      y /= rr;
      xs.push(x);
      ys.push(y);
      ts.push(t);
      ends = "ground";
      break;
    }
    xs.push(x);
    ys.push(y);
    ts.push(t);
    if (closed ? t >= period : rr > VIEW_R) break;
  }
  const px = (v: number): number => CX + v * EARTH_R;
  const py = (v: number): number => CY + v * EARTH_R;
  // The path, thinned to a point about every pixel and a quarter.
  let d = `M ${f(px(xs[0] as number))} ${f(py(ys[0] as number))}`;
  let lx = px(xs[0] as number);
  let ly = py(ys[0] as number);
  for (let i = 1; i < xs.length; i++) {
    const qx = px(xs[i] as number);
    const qy = py(ys[i] as number);
    if (i === xs.length - 1 || Math.hypot(qx - lx, qy - ly) >= 1.25) {
      d += ` L ${f(qx)} ${f(qy)}`;
      lx = qx;
      ly = qy;
    }
  }
  // The ball: the same flight sampled at equal times, so it moves at the speed the physics gives.
  const total = ts[ts.length - 1] as number;
  const SAMPLES = 300;
  const line: { x: number; y: number }[] = [];
  let at = 0;
  for (let s = 0; s <= SAMPLES; s++) {
    const want = (total * s) / SAMPLES;
    while (at < ts.length - 2 && (ts[at + 1] as number) < want) at++;
    const t0 = ts[at] as number;
    const t1 = ts[at + 1] ?? t0;
    const w = t1 > t0 ? Math.min(1, Math.max(0, (want - t0) / (t1 - t0))) : 0;
    const ax = xs[at] as number;
    const ay = ys[at] as number;
    const bx = xs[at + 1] ?? ax;
    const by = ys[at + 1] ?? ay;
    line.push({ x: Math.round(px(ax + (bx - ax) * w) * 10) / 10, y: Math.round(py(ay + (by - ay) * w) * 10) / 10 });
  }
  const made: Flight = {
    d,
    ends,
    at: (fraction) => line[Math.round(Math.min(1, Math.max(0, fraction)) * SAMPLES)] as { x: number; y: number },
  };
  if (flights.size > 400) flights.clear();
  flights.set(key, made);
  return made;
}

/** The path of the cannonball for this outcome and speed ratio: the worked-out flight, drawn. */
export function pathFor(o: Outcome, ratio: number): string {
  return flightFor(o, ratio).d;
}

export function orbitScene(env: Environment, options: OrbitSceneOptions): HTMLDivElement {
  const { speed, circular, escape, full } = options;
  const sourceNode = typeof speed === "object" && speed !== null ? nodeOf(speed) : undefined;
  const record = sourceNode?.kind === "control" ? controls.find((c) => c.obs === speed) : undefined;
  if (!record || record.unit !== "km/s") throw new TypeError("orbitScene: speed must be a control in km/s (a slider)");
  const circNode = typeof circular === "object" && circular !== null ? nodeOf(circular) : undefined;
  if (!circNode || circNode.kind !== "model" || circNode.id !== CIRCULAR_MODEL) throw new TypeError("orbitScene: circular must be the output of the circular-speed model (Synapse.circularSpeed)");
  const escNode = typeof escape === "object" && escape !== null ? nodeOf(escape) : undefined;
  if (!escNode || escNode.kind !== "model" || escNode.id !== ESCAPE_MODEL) throw new TypeError("orbitScene: escape must be the output of the escape-speed model (Synapse.escapeSpeed)");
  const circRadius = circNode.inputs?.radius;
  const escRadius = escNode.inputs?.radius;
  const radiusNode = circRadius ? nodeOf(circRadius) : undefined;
  if (!circRadius || !escRadius || !radiusNode || radiusNode !== nodeOf(escRadius) || radiusNode.kind !== "constant") throw new TypeError("orbitScene: both models must be fed by the same declared radius (a constant)");
  const radiusUnit = constants.find((c) => c.label === radiusNode.id)?.unit;
  const radiusKm = (circRadius as Observable<number>).get();
  if (radiusUnit !== "km" || !(radiusKm >= EARTH_RADIUS_KM[0] && radiusKm <= EARTH_RADIUS_KM[1])) throw new RangeError("orbitScene: the radius must be Earth's radius in km; this picture is about a cannon on Earth");
  const mass = circNode.params?.central_mass;
  if (mass === undefined || !EARTH_MASSES.includes(mass) || escNode.params?.central_mass !== mass) throw new RangeError("orbitScene: both models must use Earth's mass; this picture is about Earth");
  if (typeof full !== "number" || !Number.isFinite(full) || !(full > 0)) throw new RangeError("orbitScene: full must be a positive number");
  if (full < record.max) throw new RangeError("orbitScene: full must be at least the control's maximum");

  const wrap = document.createElement("div");
  wrap.className = "syn-orbit";
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "syn-scene syn-orbit-scene", role: "img", preserveAspectRatio: "xMidYMid meet" });
  markKitSvg(root);

  const outcome = (): Outcome => outcomeOf(speed.get(), circular.get(), escape.get());
  const ratio = (): number => speed.get() / circular.get();
  // The launch arrow grows with the launch speed, and its tip is a handle (W18): drag it to set the speed, then press Launch.
  const ARROW_SPAN = 92;
  const arrow = (): number => 8 + ARROW_SPAN * Math.min(1, Math.max(0, speed.get() / full));
  const tipAt = (v: number): number => CX + 12 + ARROW_SPAN * Math.min(1, Math.max(0, v / full));
  const describe = (): string => kt("orbitScene", words(outcome()), schematic());
  const colourOf = (o: Outcome): string => (o === "falls" ? FALL_COLOUR : o === "escapes" ? ESCAPE_COLOUR : ORBIT_COLOUR);

  // Space, as V3 draws it: a dark sky with stars (always dark, in either theme), Earth, the mountain with its cannon, the path the launch speed gives, a faint copy of the last
  // three launches, and the cannonball itself, which the Launch button sends along the path.
  const sky = svg("rect", { x: "0", y: "0", width: String(W), height: String(H), rx: "12", fill: SKY });
  root.appendChild(sky);
  let seed = 7;
  for (let i = 0; i < 30; i++) {
    seed = (seed * 48271) % 2147483647;
    const sx = (seed % 2600) / 10;
    seed = (seed * 48271) % 2147483647;
    const sy = (seed % 2400) / 10;
    root.appendChild(svg("circle", { cx: sx.toFixed(1), cy: sy.toFixed(1), r: i % 5 === 0 ? "1.3" : "0.8", fill: "#cfe4f5", "fill-opacity": i % 3 === 0 ? "0.9" : "0.5" }));
  }
  const earth = svg("circle", { cx: f(CX), cy: f(CY), r: f(EARTH_R), fill: "#2f8fd6", stroke: "#8fd6a0", "stroke-width": "2" });
  const shine = svg("circle", { cx: f(CX - 9), cy: f(CY - 10), r: "9", fill: "#7fd0ff", "fill-opacity": "0.45" });
  const trails: { d: string; colour: string }[] = [];
  const trailEls = [0, 1, 2].map(() => svg("path", { fill: "none", "stroke-width": "2", "stroke-linecap": "round" }));
  const mountain = svg("polygon", { points: `${f(CX - 7)},${f(LAUNCH_Y + 3)} ${f(CX)},${f(LAUNCH_Y - 6)} ${f(CX + 7)},${f(LAUNCH_Y + 3)}`, fill: "#8a949c", stroke: "#cfd8de", "stroke-width": "2", "stroke-linejoin": "round" });
  const path = svg("path", { fill: "none", "stroke-width": "3", "stroke-linecap": "round" });
  const shaft = svg("line", { x1: f(CX), y1: f(LAUNCH_Y - 10), y2: f(LAUNCH_Y - 10), stroke: ESCAPE_COLOUR, "stroke-width": "3", "stroke-linecap": "round" });
  const head = svg("polygon", { fill: ESCAPE_COLOUR });
  const ball = svg("circle", { r: "4.5", fill: "#ffffff" });
  const label = own(svg("text", { x: f(CX), y: f(CY + 4), "text-anchor": "middle", fill: "#ffffff", "font-weight": "800", "font-size": "13" }), () => kt("earth"));
  label.textContent = kt("earth");
  const grip = svg("circle", { r: "24", fill: "#000", "fill-opacity": "0", class: "syn-app-grip", "aria-hidden": "true", "data-synapse-handle": `orbit.${record.id}` });
  root.append(earth, shine, ...trailEls, path, mountain, shaft, head, label, ball, grip);

  // The flight: a launch sends the ball once along the path (a fall or an escape) or twice round it (a circle or an oval), then it rests. The ball's place is a function of
  // `phase` alone, set together with the attributes, so the audit can always say where it should be. Reduced motion skips the flight and shows where it ends.
  let phase = -1; // below 0: not launched, the ball is not drawn
  let laps = 1;
  let frame = 0;
  const ballAt = (): { x: number; y: number } => {
    if (phase < 0) return { x: CX, y: LAUNCH_Y };
    const flight = flightFor(outcome(), ratio());
    const rest = flight.ends === "lap" ? 0 : 1; // a lap ends where it began; a fall or an escape ends at the end of its path
    return flight.at(phase >= laps ? rest : phase % 1);
  };
  const stop = (): void => {
    if (frame) {
      if (typeof cancelAnimationFrame === "function") cancelAnimationFrame(frame);
      else clearTimeout(frame);
    }
    frame = 0;
    phase = -1;
  };

  const dynamic = new Map<Element, () => Record<string, string>>();
  dynamic.set(path, () => ({ d: pathFor(outcome(), ratio()), stroke: colourOf(outcome()), "stroke-dasharray": outcome() === "escapes" ? "6 5" : "none" }));
  dynamic.set(shaft, () => ({ x2: f(CX + arrow()) }));
  dynamic.set(grip, () => ({ cx: f(tipAt(speed.get())), cy: f(LAUNCH_Y - 10) }));
  dynamic.set(head, () => ({ points: `${f(CX + arrow() + 7)},${f(LAUNCH_Y - 10)} ${f(CX + arrow() - 2)},${f(LAUNCH_Y - 16)} ${f(CX + arrow() - 2)},${f(LAUNCH_Y - 4)}` }));
  dynamic.set(ball, () => {
    const b = ballAt();
    return { cx: f(b.x), cy: f(b.y), "fill-opacity": phase < 0 ? "0" : "1" };
  });
  trailEls.forEach((el, i) => dynamic.set(el, () => ({ d: trails[i]?.d ?? "M 0 0", stroke: trails[i]?.colour ?? ORBIT_COLOUR, "stroke-opacity": trails[i] ? "0.4" : "0" })));

  const note = own(document.createElement("p"), () => `${words(outcome())} ${schematic()}`);
  note.className = "syn-text syn-orbit-note";
  note.setAttribute("data-synapse-observations", "");
  note.setAttribute("role", "status");
  note.setAttribute("aria-live", "polite");
  ownAttr(root, "aria-label", () => describe());

  const launchWord = kt("launch");
  const launchButton = own(document.createElement("button"), () => launchWord);
  launchButton.type = "button";
  launchButton.className = "syn-btn";
  launchButton.textContent = launchWord;
  launchButton.setAttribute("data-synapse-action", "launch");
  registerAction(launchButton, "launch", launchWord);

  const draw = (): void => {
    for (const [el, fn] of dynamic) for (const [k, v] of Object.entries(fn())) el.setAttribute(k, v);
    root.setAttribute("aria-label", describe());
    note.textContent = `${words(outcome())} ${schematic()}`;
  };
  // A new speed ends the flight in the air: the path is a different one now.
  const redraw = (): void => {
    stop();
    draw();
  };
  speed.subscribe(redraw);
  circular.subscribe(redraw);
  escape.subscribe(redraw);

  const finish = (): void => {
    trails.push({ d: pathFor(outcome(), ratio()), colour: colourOf(outcome()) });
    while (trails.length > trailEls.length) trails.shift();
    draw();
  };
  const reduced = (): boolean => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const next = (tick: () => void): number => (typeof requestAnimationFrame === "function" ? requestAnimationFrame(tick) : (setTimeout(tick, 16) as unknown as number));
  const clock = (): number => (typeof performance !== "undefined" ? performance.now() : Date.now());
  launchButton.addEventListener("click", () => {
    stop();
    draw();
    const o = outcome();
    const ends = flightFor(o, ratio()).ends;
    laps = ends === "lap" ? 2 : 1;
    const seconds = (ends === "ground" ? 1.8 : ends === "away" ? 2.8 : o === "circle" ? 3.2 : 4) * laps;
    event("launch", Number(speed.get().toFixed(3)));
    if (reduced()) {
      phase = laps;
      finish();
      return;
    }
    phase = 0;
    const began = clock();
    const tick = (): void => {
      const t = (clock() - began) / (seconds * 1000);
      if (t >= 1) {
        phase = laps;
        frame = 0;
        finish();
        return;
      }
      phase = t * laps;
      draw();
      frame = next(tick);
    };
    draw();
    frame = next(tick);
  });
  draw();
  wrap.append(root, note, launchButton);
  env.stage.appendChild(wrap);

  const kept = guard();
  for (const [el, fn] of dynamic) kept.part(el, fn);
  kept.part(root, () => ({ "aria-label": describe() }));
  for (const el of [wrap, note, launchButton, ...all(root, "*")]) if (!dynamic.has(el)) kept.part(el);
  kept.tree(wrap);

  const check = (): string[] => {
    const out: string[] = [];
    if (parentOf(root) !== wrap || parentOf(note) !== wrap || parentOf(launchButton) !== wrap || parentOf(wrap) === null) out.push("the orbit picture was taken apart");
    if (style(wrap, "display") === "none" || style(wrap, "visibility") === "hidden" || style(root, "display") === "none" || style(root, "visibility") === "hidden") out.push("the orbit picture is hidden");
    if (attr(root, "aria-label") !== describe()) out.push("the orbit picture's description was changed by the page");
    return out;
  };
  const layout = (): string[] => {
    if (!layoutAvailable()) return [];
    const box = rectOf(root);
    if (!(box.width > 0 && box.height > 0)) return ["the orbit picture is not drawn"];
    const out: string[] = [];
    if (effectiveOpacity(root) < 0.5 || effectiveOpacity(note) < 0.5) out.push("the orbit picture is faded out");
    if (!(rectOf(note).height > 0)) out.push("the orbit sentence is not drawn");
    if (!(rectOf(path).width > 0 && rectOf(path).height > 0)) out.push("the cannonball's path is not drawn");
    return out;
  };
  widgets.push({ kind: "scene", id: "orbit", obs: circular, second: escape, source: speed, full, check, layout, exact: () => kept.problems() });
  dragAlong(root, grip, [W, H], tipAt(record.min), tipAt(record.max), record);
  quiet(record);
  widgets.push({
    kind: "handle",
    id: `orbit.${record.id}`,
    control: record.id,
    host: "orbit",
    box: [W, H],
    origin: record.min,
    full: record.max,
    grab: { from: [tipAt(record.min), LAUNCH_Y - 10], to: [tipAt(record.max), LAUNCH_Y - 10] },
    obs: speed,
    check: () => {
      const out: string[] = [];
      if (parentOf(grip) !== root) out.push("the launch arrow's handle was taken off");
      if (style(grip, "display") === "none" || style(grip, "visibility") === "hidden" || style(grip, "pointer-events") === "none") out.push("the launch arrow cannot be grabbed");
      return out;
    },
    layout: () => {
      if (!layoutAvailable()) return [];
      const out: string[] = [];
      const r = rectOf(grip);
      if (r.width < 40 || r.height < 40) out.push("the launch arrow's handle is too small to grab");
      const over = hitAt(r.left + r.width / 2, r.top + r.height / 2);
      if (over && over !== grip && !contains(grip, over)) out.push("the launch arrow's handle is covered by something else");
      return out;
    },
  });
  return wrap;
}
