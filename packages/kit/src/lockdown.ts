// `lockdown()`: freeze the JavaScript and DOM intrinsics the audit and the self-check depend on, so a page script that runs after the
// Kit cannot patch `RegExp.prototype.test`, `Array.prototype.flatMap`, `Map.prototype.get`, `Element.prototype.querySelectorAll` and the like
// to blind them (kit-guardian P1 B1). It runs once, at the end of the bundle, before any generated script. It is NOT run when the Kit is
// imported by the unit tests (freezing the test runner's own prototypes would break it); the bundle footer calls it, and the end-to-end
// tests prove a page cannot patch afterwards. Honest limit: this is the standard "freeze the primordials" defence, not a full realm
// isolation; the runtime self-check and the verifier's other layers remain.

const NAMES = [
  "Object", "Function", "Array", "String", "Number", "Boolean", "Symbol", "BigInt", "RegExp", "Map", "Set", "WeakMap", "WeakSet", "WeakRef",
  "Promise", "Date", "Error", "TypeError", "RangeError", "SyntaxError", "ReferenceError", "EvalError", "URIError", "ArrayBuffer",
  "DataView", "Uint8Array", "Float64Array", "Int32Array", "Uint32Array", "Intl",
  "Node", "Element", "HTMLElement", "Document", "Text", "CharacterData", "Attr", "NamedNodeMap", "NodeList", "HTMLCollection", "EventTarget",
  "TreeWalker", "MutationObserver", "CSSStyleDeclaration", "ShadowRoot", "DocumentFragment", "SVGElement", "FontFaceSet", "Event",
  "MessageEvent", "DOMTokenList", "CSSStyleSheet", "HTMLInputElement", "HTMLOutputElement", "HTMLButtonElement", "HTMLStyleElement",
  "HTMLCanvasElement", "HTMLTableElement", "HTMLTableCellElement", "HTMLLabelElement",
];
const SINGLETONS = ["Reflect", "JSON", "Math", "Atomics"];

function freezeDeep(target: unknown): void {
  if (target === null || (typeof target !== "object" && typeof target !== "function")) return;
  try {
    Object.freeze(target);
  } catch {
    /* an exotic object that cannot be frozen */
  }
}

export function lockdown(): void {
  const g = globalThis as unknown as Record<string, unknown>;
  for (const name of NAMES) {
    const ctor = g[name] as { prototype?: unknown } | undefined;
    if (!ctor) continue;
    freezeDeep(ctor.prototype);
    freezeDeep(ctor);
  }
  for (const name of SINGLETONS) freezeDeep(g[name]);
  // Typed-array and generator prototypes reached through the language.
  for (const proto of [
    Object.getPrototypeOf(Int8Array),
    Object.getPrototypeOf(function* () {}),
    Object.getPrototypeOf(async function () {}),
    Object.getPrototypeOf([][Symbol.iterator]()),
    Object.getPrototypeOf(new Map()[Symbol.iterator]()),
    Object.getPrototypeOf(new Set()[Symbol.iterator]()),
    Object.getPrototypeOf(""[Symbol.iterator]()),
  ]) {
    freezeDeep(proto);
  }
  for (const key of Object.getOwnPropertyNames(g)) {
    if (/^(HTML|SVG)\w*Element$/.test(key)) freezeDeep((g[key] as { prototype?: unknown }).prototype);
  }
}
