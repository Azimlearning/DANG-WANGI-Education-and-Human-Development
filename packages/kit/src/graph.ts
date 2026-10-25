// `graph(env, {title, x, y, yLabel, yUnit})`: y plotted against a control x over the control's whole range. The Kit samples y by moving
// x across its range in code (then puts it back), so the curve is exactly what the model gives, drawn at once, and is redrawn when any
// other control changes. Every number on the graph is in a Kit-owned element, the curve's points are reported to the verifier (which
// re-derives each from the independent reference), and a visually hidden table is the text equivalent (hard constraint 10).

import type { Environment } from "./environment";
import type { Observable } from "./observable";
import { controls, copy, isObservable, markKitSvg, nodeOf, own, ownAttr, series } from "./provenance";

const NS = "http://www.w3.org/2000/svg";
const W = 320;
const H = 200;
const L = 48;
const R = 12;
const T = 12;
const B = 40;
const MAX_POINTS = 40;
const TABLE_ROWS = 11;

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

  let points: [number, number][] = [];
  let sampling = false;
  let lo = 0;
  let hi = 1;

  const root = svg("svg", { class: "syn-graph", viewBox: `0 0 ${W} ${H}`, role: "img" });
  markKitSvg(root);
  const label = `Graph of ${yLabel} against ${xc.label}. ${title}`;
  root.setAttribute("aria-label", label);
  ownAttr(root, "aria-label", () => label);
  copy.push(title, yLabel, yUnit);
  const frame = svg("path", { d: `M${L} ${T}V${H - B}H${W - R}`, fill: "none", stroke: "currentColor", "stroke-width": "1" });
  const curve = svg("polyline", { fill: "none", stroke: "var(--syn-accent)", "stroke-width": "2" });
  const marker = svg("circle", { r: "5", fill: "var(--syn-accent)" });
  const text = (xp: number, yp: number, anchor: string, get: () => string): SVGTextElement => {
    const t = own(svg("text", { x: String(xp), y: String(yp), "text-anchor": anchor, "font-size": "11", fill: "currentColor" }), get);
    t.textContent = get();
    return t;
  };
  const xMin = text(L, H - B + 14, "start", () => fmt(xc.min));
  const xMax = text(W - R, H - B + 14, "end", () => fmt(xc.max));
  const xTitle = text((L + W - R) / 2, H - 6, "middle", () => `${xc.label} (${xc.unit})`);
  const yMin = text(L - 4, H - B, "end", () => (points.length ? fmt(lo) : ""));
  const yMax = text(L - 4, T + 10, "end", () => (points.length ? fmt(hi) : ""));
  const yTitle = text(L, T - 2, "start", () => `${yLabel} (${yUnit})`);
  root.append(frame, curve, marker, xMin, xMax, xTitle, yMin, yMax, yTitle);
  copy.push(xc.label, xc.unit);

  // The text equivalent: a table of evenly spaced samples, hidden visually but read by screen readers.
  const wrap = document.createElement("div");
  const tbl = document.createElement("table");
  const hidden = document.createElement("div");
  hidden.className = "syn-sr";
  const cap = own(document.createElement("caption"), () => `${yLabel} against ${xc.label}`);
  cap.textContent = `${yLabel} against ${xc.label}`;
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const text of [`${xc.label} (${xc.unit})`, `${yLabel} (${yUnit})`]) {
    const th = own(document.createElement("th"), () => text);
    th.scope = "col";
    th.textContent = text;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  const tbody = document.createElement("tbody");
  const cells: [HTMLTableCellElement, HTMLTableCellElement][] = [];
  const rowAt = (i: number): [number, number] | undefined => {
    if (!points.length) return undefined;
    const idx = Math.round((i * (points.length - 1)) / (TABLE_ROWS - 1));
    return points[idx];
  };
  for (let i = 0; i < TABLE_ROWS; i += 1) {
    const tr = document.createElement("tr");
    const a = own(document.createElement("td"), () => (rowAt(i) ? fmt(rowAt(i)![0]) : ""));
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
    lo = Math.min(...ys);
    hi = Math.max(...ys);
    if (hi === lo) hi = lo + 1;
    const px = (v: number) => L + ((v - xc.min) / (xc.max - xc.min)) * (W - L - R);
    const py = (v: number) => H - B - ((v - lo) / (hi - lo)) * (H - B - T - 14);
    curve.setAttribute("points", points.map(([a, b]) => `${px(a).toFixed(1)},${py(b).toFixed(1)}`).join(" "));
    marker.setAttribute("cx", px(x.get()).toFixed(1));
    marker.setAttribute("cy", py(y.get()).toFixed(1));
    yMin.textContent = fmt(lo);
    yMax.textContent = fmt(hi);
    cells.forEach(([a, b], i) => {
      const r = rowAt(i);
      a.textContent = r ? fmt(r[0]) : "";
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
  env.stage.appendChild(wrap);
  return root;
}
