// Provenance: where every number on the page came from. This is the Kit half of verification layer L1 (the harness reads it through
// `Synapse.audit()` and decides). Everything here is module-private state in the bundle: generated code receives only the frozen
// `Synapse` object, so it cannot register an observable, mark an element as Kit-owned, or edit a provenance node.
//
// An observable is recognised by membership in a private WeakSet, never by its shape. An object that merely looks like an
// observable is therefore refused (kit-guardian S4: the old shape check could be satisfied by any object literal).

export type NodeKind = "control" | "model" | "constant" | "convert" | "derived" | "free";

export interface ProvNode {
  kind: NodeKind;
  /** Model id (`mechanics.hookes`), control id, or constant label. */
  id?: string;
  params?: Record<string, number>;
  inputs?: Record<string, object>;
  /** A control's range and defaults, so the verifier can sweep it and know which numbers are backed. */
  min?: number;
  max?: number;
  grid?: number;
  default?: number;
  /** `convert` only. */
  from?: string;
  to?: string;
  factor?: number;
  /** `derived` only: arithmetic written by generated code, which the verifier refuses. */
  user?: boolean;
}

export interface ChainNode {
  kind: NodeKind;
  id?: string;
  params?: Record<string, number>;
  inputs?: Record<string, ChainNode>;
  min?: number;
  max?: number;
  grid?: number;
  default?: number;
  from?: string;
  to?: string;
  factor?: number;
  user?: boolean;
}

const registry = new WeakSet<object>();
const nodes = new WeakMap<object, ProvNode>();

export function track<T extends object>(obs: T, node: ProvNode): T {
  registry.add(obs);
  nodes.set(obs, node);
  return obs;
}

/** True only for observables this bundle created. */
export function isObservable(value: unknown): boolean {
  return typeof value === "object" && value !== null && registry.has(value);
}

export function nodeOf(obs: object): ProvNode | undefined {
  return nodes.get(obs);
}

/** A serialisable copy of the provenance tree under `obs`. Depth-limited so a cycle cannot hang the audit. */
export function describe(obs: object, depth = 0): ChainNode {
  const node = nodes.get(obs);
  if (!node || depth > 12) return { kind: "free" };
  const out: ChainNode = { kind: node.kind };
  for (const key of ["id", "min", "max", "grid", "default", "from", "to", "factor", "user"] as const) {
    if (node[key] !== undefined) (out as unknown as Record<string, unknown>)[key] = node[key];
  }
  if (node.params) out.params = { ...node.params };
  if (node.inputs) {
    out.inputs = {};
    for (const [name, input] of Object.entries(node.inputs)) out.inputs[name] = describe(input, depth + 1);
  }
  return out;
}

// ── owned elements ──────────────────────────────────────────────────────────────────────────────────────────────────
// Every element that carries text and was made by a Kit component is registered here with a function giving the text it must have.
// The audit compares the live DOM with it, so overwriting a readout, a label or the study note is detected, and any text node
// whose parent is NOT in this map is "unowned" (a number typed straight into the page).

const ownedElements = new Map<Element, () => string>();

export function own<E extends Element>(el: E, expected: () => string): E {
  ownedElements.set(el, expected);
  return el;
}

export function ownedEntries(): [Element, () => string][] {
  return [...ownedElements.entries()];
}

// ── owned attributes ────────────────────────────────────────────────────────────────────────────────────────────────────
// Attributes a person or a screen reader receives as words (`aria-label`, `aria-valuetext`, `title`, `alt`, `placeholder`...) can carry a
// number just as well as a text node can. The Kit registers the ones it sets, with the value each must have; any such attribute that holds
// a digit and is not registered is reported by the audit.

const ownedAttributes = new Map<Element, Map<string, () => string>>();

export function ownAttr<E extends Element>(el: E, name: string, expected: () => string): E {
  let attrs = ownedAttributes.get(el);
  if (!attrs) ownedAttributes.set(el, (attrs = new Map()));
  attrs.set(name, expected);
  return el;
}

export function ownedAttr(el: Element, name: string): (() => string) | undefined {
  return ownedAttributes.get(el)?.get(name);
}

export function isOwned(el: Element | null): boolean {
  return el !== null && ownedElements.has(el);
}

// ── page-level registries (what the audit reports) ──────────────────────────────────────────────────────────────────

export interface ControlRecord {
  id: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  grid: number;
  default: number;
  /** The input's step: the most the input's own value can differ from the observable's after rounding to a step. */
  step: number;
  obs: object;
  el: HTMLInputElement;
}

export interface ReadoutRecord {
  label: string;
  unit: string;
  digits: number;
  obs: { get(): number };
  el: HTMLElement;
}

export interface ConstantRecord {
  label: string;
  unit: string;
  value: number;
}

/** A value a table column or a graph shows. The verifier treats it like a readout: its chain must be grounded and its unit right. */
export interface SeriesRecord {
  kind: "graph" | "table";
  title: string;
  label: string;
  unit: string;
  digits: number;
  obs: { get(): number };
  /** Graph only: the control that is the x axis and the sampled (x, y) points currently drawn. */
  xControl?: string;
  points?: () => [number, number][];
}

/** Buttons the Kit made (reset, record, clear). Held privately so the audit can tell them from a button a script made. */
const actionElements = new WeakSet<Element>();
export interface ActionRecord {
  kind: string;
  label: string;
}

export const controls: ControlRecord[] = [];
export const series: SeriesRecord[] = [];
export const actions: ActionRecord[] = [];

export function registerAction(el: Element, kind: string, label: string): void {
  actionElements.add(el);
  actions.push({ kind, label });
  copy.push(label);
}

export function isAction(el: Element): boolean {
  return actionElements.has(el);
}
export const readouts: ReadoutRecord[] = [];
export const constants: ConstantRecord[] = [];
/** Sanctioned static copy: titles, notes, labels and `text()` calls. Numbers inside are checked against backed values. */
export const copy: string[] = [];

/** Tests only. */
export function resetForTests(): void {
  ownedElements.clear();
  ownedAttributes.clear();
  controls.length = 0;
  readouts.length = 0;
  series.length = 0;
  actions.length = 0;
  constants.length = 0;
  copy.length = 0;
}
