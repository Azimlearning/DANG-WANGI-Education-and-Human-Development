// `graph(env, {title, x, y, yLabel, yUnit})`: y plotted against a control x over the control's whole range. The Kit samples y by moving
// x across its range in code (then puts it back), so the curve is exactly what the model gives, drawn at once, and is redrawn when any
// other control changes. Every number on the graph is in a Kit-owned element, the curve's points are reported to the verifier (which
// re-derives each from the independent reference), and a visually hidden table is the text equivalent (hard constraint 10).

import { contains, effectiveOpacity, hitAt, layoutAvailable, parentOf, rectOf, style } from "./dom";
import type { Environment } from "./environment";
import { dragAlong, quiet } from "./handles";
import { kt } from "./i18n";
import type { Observable } from "./observable";
import { controls, copy, isObservable, markKitSvg, nodeOf, own, ownAttr, series, widgets } from "./provenance";

const NS = "http://www.w3.org/2000/svg";
const W = 320;
const H = 200;
const L = 48;
const R = 12;
const T = 12;
const B = 40;
const MAX_POINTS = 40;
const TABLE_ROWS = 11;
/** The handle on the graph's point (W18): a pointer area about 44 px across where the graph is drawn about 340 px wide. */
const HANDLE_RADIUS = 24;

let graphCounter = 0;
const fmt = (v: number): string => String(Number(v.toPrecision(4)));

function svg<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

export interface GraphOptions {
  title: string;
  x: Observable<number>;
  y: Observable<number>;
  yLabel: string;
  yUnit: string;
  digits?: number;
}

export function graph(env: Environment, options: GraphOptions): SVGSVGElement {
  const { x, y } = options;
  const title = String(options.title);
  const yLabel = String(options.yLabel);
  const yUnit = String(options.yUnit);
  const digits = options.digits ?? 2;
  if (!isObservable(x) || !isObservable(y)) throw new TypeError("graph: x and y must be Kit observables");
  const xNode = nodeOf(x);
  if (xNode?.kind !== "control") throw new TypeError("graph: x must be a slider (a control)");
  const xc = controls.find((c) => c.obs === x);
  if (!xc) throw new TypeError("graph: x must be a slider made by this Kit");
  if (!Number.isInteger(digits) || digits < 0 || digits > 8) throw new RangeError("graph: digits must be 0 to 8");

  // A choice control (planets) is drawn as labelled bars, one per choice; anything else as a curve.
  const words = xc.words;
  const slots = words ? xc.grid + 1 : 0;
  const plotW = W - L - R;
  const px = (v: number): number =>
    words ? L + ((((v - xc.min) / (xc.max - xc.min)) * (slots - 1) + 0.5) / slots) * plotW : L + ((v - xc.min) / (xc.max - xc.min)) * plotW;
  let points: [number, number][] = [];
  let sampling = false;
  let lo = 0;
  let hi = 1;

  const root = svg("svg", { class: "syn-graph", viewBox: `0 0 ${W} ${H}`, role: "img" });
  markKitSvg(root);
  const label = kt("graphOf", yLabel, xc.label, title);
  root.setAttribute("aria-label", label);
  ownAttr(root, "aria-label", () => label);
  copy.push(title, yLabel, yUnit);
  const frame = svg("path", { d: `M${L} ${T}V${H - B}H${W - R}`, fill: "none", stroke: "currentColor", "stroke-width": "1" });
  const curve = svg("polyline", { fill: "none", stroke: "var(--syn-accent)", "stroke-width": "2" });
  const bars = words ? words.map(() => svg("rect", { fill: "var(--syn-accent)", "fill-opacity": "0.45", rx: "2" })) : [];
  const marker = svg("circle", { r: "6", fill: "var(--syn-accent)", stroke: "var(--syn-bg)", "stroke-width": "2" });
  // The point is a handle (W18): drag it along the graph to set x, unless something on the page already drags this control (the masses, a grip, a dial, a valve, another graph),
  // or the control's range would put the line's start off the drawing's scale. The handle is drawn last, so it is on top.
  const driven = widgets.some((w) => w.id === xc.id || w.control === xc.id);
  const hit = !driven && xc.max > 0 ? svg("circle", { r: String(HANDLE_RADIUS), fill: "#000", "fill-opacity": "0", class: "syn-app-grip", "aria-hidden": "true", "data-synapse-handle": `graph.${xc.id}` }) : null;
  const ring = hit ? svg("circle", { r: "11", fill: "none", stroke: "var(--syn-accent)", "stroke-width": "2", class: "syn-a-pulse" }) : null;
  const text = (xp: number, yp: number, anchor: string, get: () => string): SVGTextElement => {
    const t = own(svg("text", { x: String(xp), y: String(yp), "text-anchor": anchor, "font-size": "11", fill: "currentColor" }), get);
    t.textContent = get();
    return t;
  };
  const xMin = text(L, H - B + 14, "start", () => (words ? "" : fmt(xc.min)));
  const xMax = text(W - R, H - B + 14, "end", () => (words ? "" : fmt(xc.max)));
  const xTitle = text((L + W - R) / 2, H - 6, "middle", () => (words ? xc.label : `${xc.label} (${xc.unit})`));
  // One word under each bar, slanted so eight names fit.
  const names = (words ?? []).map((w, i) => {
    const cx = px(xc.min + ((xc.max - xc.min) * i) / Math.max(1, slots - 1));
    const t = own(svg("text", { x: cx.toFixed(1), y: String(H - B + 12), "text-anchor": "end", "font-size": "9", fill: "currentColor", transform: `rotate(-35 ${cx.toFixed(1)} ${H - B + 12})` }), () => w);
    t.textContent = w;
    return t;
  });
  const yMin = text(L - 4, H - B, "end", () => (points.length ? fmt(lo) : ""));
  const yMax = text(L - 4, T + 10, "end", () => (points.length ? fmt(hi) : ""));
  const yTitle = text(L, T - 2, "start", () => `${yLabel} (${yUnit})`);
  root.append(frame, ...(words ? [] : [curve]), ...bars, ...(ring ? [ring] : []), marker, xMin, xMax, xTitle, ...names, yMin, yMax, yTitle, ...(hit ? [hit] : []));
  copy.push(xc.label, xc.unit);

  // The text equivalent: a table of evenly spaced samples, hidden visually but read by screen readers.
  const wrap = document.createElement("div");
  const tbl = document.createElement("table");
  const hidden = document.createElement("div");
  hidden.className = "syn-sr";
  const cap = own(document.createElement("caption"), () => kt("against", yLabel, xc.label));
  cap.textContent = kt("against", yLabel, xc.label);
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const text of [words ? xc.label : `${xc.label} (${xc.unit})`, `${yLabel} (${yUnit})`]) {
    const th = own(document.createElement("th"), () => text);
    th.scope = "col";
    th.textContent = text;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  const tbody = document.createElement("tbody");
  const cells: [HTMLTableCellElement, HTMLTableCellElement][] = [];
  const rows = words ? slots : TABLE_ROWS;
  const rowAt = (i: number): [number, number] | undefined => {
    if (!points.length) return undefined;
    const idx = words ? i : Math.round((i * (points.length - 1)) / (TABLE_ROWS - 1));
    return points[idx];
  };
  const xText = (v: number): string => (words ? (words[Math.round(((v - xc.min) / (xc.max - xc.min)) * (slots - 1))] ?? fmt(v)) : fmt(v));
  for (let i = 0; i < rows; i += 1) {
    const tr = document.createElement("tr");
    const a = own(document.createElement("td"), () => (rowAt(i) ? xText(rowAt(i)![0]) : ""));
    const b = own(document.createElement("td"), () => (rowAt(i) ? rowAt(i)![1].toFixed(digits) : ""));
    tr.append(a, b);
    tbody.appendChild(tr);
    cells.push([a, b]);
  }
  tbl.id = `syn-graph-table-${graphCounter++}`;
  root.setAttribute("aria-describedby", tbl.id);
  tbl.append(cap, thead, tbody);
  hidden.appendChild(tbl);
  wrap.append(root, hidden);

  const draw = () => {
    if (!points.length) return;
    const ys = points.map((p) => p[1]);
    lo = words ? Math.min(0, ...ys) : Math.min(...ys);
    hi = Math.max(...ys);
    if (hi === lo) hi = lo + 1;
    const py = (v: number) => H - B - ((v - lo) / (hi - lo)) * (H - B - T - 14);
    curve.setAttribute("points", points.map(([a, b]) => `${px(a).toFixed(1)},${py(b).toFixed(1)}`).join(" "));
    const barW = (plotW / Math.max(1, slots)) * 0.62;
    bars.forEach((bar, i) => {
      const p = points[i];
      if (!p) return;
      bar.setAttribute("x", (px(p[0]) - barW / 2).toFixed(1));
      bar.setAttribute("y", Math.min(py(p[1]), py(0)).toFixed(1));
      bar.setAttribute("width", barW.toFixed(1));
      bar.setAttribute("height", Math.max(0.5, Math.abs(py(p[1]) - py(0))).toFixed(1));
      bar.setAttribute("fill-opacity", Math.abs(p[0] - x.get()) < 1e-9 ? "1" : "0.45");
    });
    const mx = px(x.get()).toFixed(1);
    const my = py(y.get()).toFixed(1);
    for (const el of [marker, ring, hit]) {
      if (!el) continue;
      el.setAttribute("cx", mx);
      el.setAttribute("cy", my);
    }
    yMin.textContent = fmt(lo);
    yMax.textContent = fmt(hi);
    cells.forEach(([a, b], i) => {
      const r = rowAt(i);
      a.textContent = r ? xText(r[0]) : "";
      b.textContent = r ? r[1].toFixed(digits) : "";
    });
  };

  const resample = () => {
    if (sampling) return;
    sampling = true;
    const keep = x.get();
    const n = Math.min(xc.grid, MAX_POINTS);
    const next: [number, number][] = [];
    for (let i = 0; i <= n; i += 1) {
      x.set(xc.min + ((xc.max - xc.min) * i) / n);
      next.push([x.get(), y.get()]);
    }
    x.set(keep);
    points = next;
    sampling = false;
    draw();
  };
  resample();
  for (const c of controls) {
    if (c.obs !== x) (c.obs as Observable<number>).subscribe(resample);
  }
  x.subscribe(() => {
    if (!sampling) draw();
  });
  y.subscribe(() => {
    if (!sampling) draw();
  });

  series.push({ kind: "graph", title, label: yLabel, unit: yUnit, digits, obs: y, xControl: xc.id, points: () => points.map(([a, b]) => [a, b] as [number, number]) });
  if (hit) {
    dragAlong(root, hit, [W, H], px(xc.min), px(xc.max), xc);
    quiet(xc);
    widgets.push({
      kind: "handle",
      id: `graph.${xc.id}`,
      control: xc.id,
      host: "graph",
      box: [W, H],
      origin: xc.min,
      full: xc.max,
      grab: { from: [px(xc.min), H - B], to: [px(xc.max), H - B] },
      obs: x,
      check: () => {
        const out: string[] = [];
        if (parentOf(hit) !== root) out.push(`the handle on the graph of ${xc.label} was taken off`);
        if (style(hit, "display") === "none" || style(hit, "visibility") === "hidden" || style(hit, "pointer-events") === "none") out.push(`the handle on the graph of ${xc.label} cannot be grabbed`);
        return out;
      },
      layout: () => {
        if (!layoutAvailable()) return [];
        const out: string[] = [];
        const r = rectOf(hit);
        if (r.width < 40 || r.height < 40) out.push(`the handle on the graph of ${xc.label} is too small to grab`);
        if (effectiveOpacity(root) < 0.5) out.push(`the graph of ${xc.label} is faded out`);
        const over = hitAt(r.left + r.width / 2, r.top + r.height / 2);
        if (over && over !== hit && !contains(hit, over)) out.push(`the handle on the graph of ${xc.label} is covered by something else`);
        return out;
      },
    });
  }
  // A graph sits on the bench when it is the only picture, and beside it, in the right column under the readouts and the table, when the bench already holds a scene or
  // the masses: the apparatus stays together on the left and the empty right column is used (W14).
  (env.stage.childElementCount > 0 ? env.panel : env.stage).appendChild(wrap);
  return root;
}
