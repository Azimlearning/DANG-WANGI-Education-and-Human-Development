// `Synapse.audit()`: the Kit's report to the verifier (layer L1). It states facts; the verifier (api/verify) decides. It returns plain,
// serialisable data and reads the page through DOM functions captured when the bundle loaded, so a script that runs later cannot patch
// `Node.prototype.textContent` to hide a mismatch. (The verifier also requires the Kit to be the first script in the document.)

import { actions, constants, controls, copy, describe, isAction, isOwned, ownedAttr, ownedEntries, readouts, series, type ChainNode } from "./provenance";

const textGet = Object.getOwnPropertyDescriptor(Node.prototype, "textContent")?.get;
const makeWalker = Document.prototype.createTreeWalker;
const getAttr = Element.prototype.getAttribute;
const getAttrNames = Element.prototype.getAttributeNames;
const hasAttr = Element.prototype.hasAttribute;
const shadowRootOf = Object.getOwnPropertyDescriptor(Element.prototype, "shadowRoot")?.get;
// Attributes whose value is spoken, shown as a tooltip or used as a placeholder or alternative.
const WORDS_ATTRS = ["aria-label", "aria-valuetext", "aria-description", "aria-roledescription", "title", "alt", "placeholder"];
const textOf = (node: Node): string => (textGet ? String(Reflect.apply(textGet, node, [])) : "");

let sealed: object | null = null;
/** Called once by the entry module with the frozen public object. */
export function seal(synapse: object): void {
  sealed = synapse;
}

// A number in copy: digits not glued to a letter, so R1, H2O and CO2 are identifiers, not quantities.
const COPY_NUMBER = /(?<![A-Za-z0-9_.])-?\d+(?:\.\d+)?/g;

export interface AuditRecord {
  kitVersion: string;
  /** True only when `window.Synapse` is the sealed object and cannot be replaced. */
  intact: boolean;
  controls: { id: string; label: string; unit: string; min: number; max: number; grid: number; default: number; value: number }[];
  readouts: { label: string; unit: string; digits: number; value: number; displayed: string; expected: string; chain: ChainNode }[];
  constants: { label: string; unit: string; value: number }[];
  /** Static copy, with the numbers found in it. The verifier checks each number is backed. */
  copy: { text: string; numbers: string[] }[];
  /** Kit-owned elements whose live text differs from the text the Kit gave them. */
  ownedMismatches: { tag: string; expected: string; actual: string }[];
  /** Text nodes containing a digit whose parent element no Kit component made. */
  unownedNumbers: { text: string; parent: string }[];
  /** Spoken or tooltip attributes holding a digit that the Kit did not set (or whose value was changed). */
  unownedAttributeNumbers: { attribute: string; value: string; element: string }[];
  /** Values shown by tables and graphs, with their chains; a graph also lists the (x, y) points it drew. */
  series: { kind: string; title: string; label: string; unit: string; digits: number; value: number; chain: ChainNode; xControl?: string; points?: [number, number][] }[];
  /** Buttons the Kit made. */
  actions: { kind: string; label: string }[];
  /** Elements carrying data-synapse-action that no Kit component made. */
  forgedActions: number;
  /** Elements with a shadow root: their content cannot be audited, so the verifier refuses them. */
  shadowRoots: number;
}

export function audit(version: string): AuditRecord {
  const descriptor = Object.getOwnPropertyDescriptor(window, "Synapse");
  const intact = !!descriptor && descriptor.value === sealed && descriptor.writable === false && descriptor.configurable === false;

  const unowned: { text: string; parent: string }[] = [];
  const walker = Reflect.apply(makeWalker, document, [document.body, NodeFilter.SHOW_TEXT]) as TreeWalker;
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = textOf(node).trim();
    const parent = node.parentElement;
    if (!text || !/\d/.test(text) || !parent) continue;
    const tag = parent.tagName;
    if (tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT") continue;
    if (!isOwned(parent)) unowned.push({ text: text.slice(0, 80), parent: `${tag.toLowerCase()}${parent.id ? "#" + parent.id : ""}` });
  }

  const attrs: { attribute: string; value: string; element: string }[] = [];
  let shadowRoots = 0;
  let forgedActions = 0;
  const all = document.body.querySelectorAll("*");
  for (const el of Array.from(all)) {
    if (shadowRootOf && Reflect.apply(shadowRootOf, el, [])) shadowRoots += 1;
    if (Reflect.apply(hasAttr, el, ["data-synapse-action"]) && !isAction(el)) forgedActions += 1;
    for (const name of Reflect.apply(getAttrNames, el, []) as string[]) {
      const lower = name.toLowerCase();
      if (!WORDS_ATTRS.includes(lower)) continue;
      const value = String(Reflect.apply(getAttr, el, [name]) ?? "");
      if (!/\d/.test(value)) continue;
      const expected = ownedAttr(el, lower);
      if (!expected || expected() !== value) {
        attrs.push({ attribute: lower, value: value.slice(0, 80), element: `${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""}` });
      }
    }
  }

  return {
    kitVersion: version,
    intact,
    controls: controls.map((c) => ({
      id: c.id,
      label: c.label,
      unit: c.unit,
      min: c.min,
      max: c.max,
      grid: c.grid,
      default: c.default,
      value: (c.obs as { get(): number }).get(),
    })),
    readouts: readouts.map((r) => {
      const value = r.obs.get();
      return {
        label: r.label,
        unit: r.unit,
        digits: r.digits,
        value,
        displayed: textOf(r.el),
        expected: `${value.toFixed(r.digits)} ${r.unit}`,
        chain: describe(r.obs),
      };
    }),
    constants: constants.map((c) => ({ ...c })),
    series: series.map((r) => ({
      kind: r.kind,
      title: r.title,
      label: r.label,
      unit: r.unit,
      digits: r.digits,
      value: r.obs.get(),
      chain: describe(r.obs),
      ...(r.xControl !== undefined ? { xControl: r.xControl } : {}),
      ...(r.points ? { points: r.points() } : {}),
    })),
    actions: actions.map((a) => ({ ...a })),
    forgedActions,
    copy: copy.map((text) => ({ text, numbers: text.match(COPY_NUMBER) ?? [] })),
    ownedMismatches: ownedEntries().flatMap(([el, expected]) => {
      const actual = textOf(el);
      const want = expected();
      return actual === want ? [] : [{ tag: el.tagName.toLowerCase(), expected: want, actual: actual.slice(0, 80) }];
    }),
    unownedNumbers: unowned,
    unownedAttributeNumbers: attrs,
    shadowRoots,
  };
}
