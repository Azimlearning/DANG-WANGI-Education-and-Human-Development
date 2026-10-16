// `Synapse.audit()`: the Kit's report to the verifier (layer L1). It states facts; the verifier (api/verify) decides. It returns plain,
// serialisable data and reads the page through DOM functions captured when the bundle loaded, so a script that runs later cannot patch
// `Node.prototype.textContent` to hide a mismatch. (The verifier also requires the Kit to be the first script in the document.)

import { constants, controls, copy, describe, isOwned, ownedEntries, readouts, type ChainNode } from "./provenance";

const textGet = Object.getOwnPropertyDescriptor(Node.prototype, "textContent")?.get;
const makeWalker = Document.prototype.createTreeWalker;
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
    copy: copy.map((text) => ({ text, numbers: text.match(COPY_NUMBER) ?? [] })),
    ownedMismatches: ownedEntries().flatMap(([el, expected]) => {
      const actual = textOf(el);
      const want = expected();
      return actual === want ? [] : [{ tag: el.tagName.toLowerCase(), expected: want, actual: actual.slice(0, 80) }];
    }),
    unownedNumbers: unowned,
  };
}
