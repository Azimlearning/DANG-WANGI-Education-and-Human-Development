// DOM primitives captured when the bundle loads. The Kit is the first script on the page, so these are the browser's own functions.
// Everything the audit and the runtime self-check read goes through here, never through `node.textContent` or `document.body`, because
// a script can shadow an instance property (`Object.defineProperty(document, "body", ...)`) even when the prototypes are frozen. The
// functions are called with an explicit receiver, so a shadowed property on the instance is never consulted.

const apply = Reflect.apply;
const getter = (proto: object | undefined, name: string): ((this: never) => unknown) | undefined =>
  proto ? (Object.getOwnPropertyDescriptor(proto, name)?.get as ((this: never) => unknown) | undefined) : undefined;
const method = <F extends (...a: never[]) => unknown>(proto: object | undefined, name: string): F | undefined =>
  proto ? ((proto as Record<string, unknown>)[name] as F | undefined) : undefined;

const nodeText = getter(Node.prototype, "textContent");
const nodeParent = getter(Node.prototype, "parentElement");
const elTag = getter(Element.prototype, "tagName");
const elId = getter(Element.prototype, "id");
const elShadow = getter(Element.prototype, "shadowRoot");
const elGet = Element.prototype.getAttribute;
const elNames = Element.prototype.getAttributeNames;
const elHas = Element.prototype.hasAttribute;
const elQsa = Element.prototype.querySelectorAll;
const docBody = getter(Document.prototype, "body");
const docHead = getter(Document.prototype, "head");
const docFonts = getter(Document.prototype, "fonts");
const fontsSize = getter(typeof FontFaceSet === "undefined" ? undefined : FontFaceSet.prototype, "size");
const makeWalker = Document.prototype.createTreeWalker;
const walkNext = TreeWalker.prototype.nextNode;
const listLength = getter(NodeList.prototype, "length");
const listItem = NodeList.prototype.item;
const inputValue = getter(typeof HTMLInputElement === "undefined" ? undefined : HTMLInputElement.prototype, "value");
const computed = typeof window.getComputedStyle === "function" ? window.getComputedStyle.bind(window) : undefined;
const styleGet = method<(this: CSSStyleDeclaration, name: string) => string>(
  typeof CSSStyleDeclaration === "undefined" ? undefined : CSSStyleDeclaration.prototype,
  "getPropertyValue",
);
const elRect = Element.prototype.getBoundingClientRect;
const nodeContains = Node.prototype.contains;
const docAt = typeof Document.prototype.elementFromPoint === "function" ? Document.prototype.elementFromPoint : undefined;
const doc = document;
// jsdom (the unit-test DOM) cannot compute pseudo-element styles and logs an error for each try; real browsers can.
const PSEUDO_STYLES = !/jsdom/i.test(navigator.userAgent);

export const textOf = (n: Node): string => (nodeText ? String(apply(nodeText, n, [])) : "");
export const parentOf = (n: Node): Element | null => (nodeParent ? ((apply(nodeParent, n, []) as Element | null) ?? null) : null);
export const tagOf = (e: Element): string => String(apply(elTag!, e, [])).toLowerCase();
export const idOf = (e: Element): string => String(apply(elId!, e, []));
export const hasShadow = (e: Element): boolean => (elShadow ? !!apply(elShadow, e, []) : false);
export const attr = (e: Element, name: string): string => String(apply(elGet, e, [name]) ?? "");
export const attrNames = (e: Element): string[] => apply(elNames, e, []) as string[];
export const hasAttribute = (e: Element, name: string): boolean => !!apply(elHas, e, [name]);
export const bodyEl = (): HTMLElement => apply(docBody!, doc, []) as HTMLElement;
export const headEl = (): HTMLElement => apply(docHead!, doc, []) as HTMLElement;
export const fontCount = (): number => {
  const set = docFonts ? apply(docFonts, doc, []) : undefined;
  return set && fontsSize ? Number(apply(fontsSize, set, [])) : 0;
};
export const value = (e: Element): string => (inputValue ? String(apply(inputValue, e, [])) : "");

export function all(root: Element | Document, selector: string): Element[] {
  const list = (root === doc ? apply(Document.prototype.querySelectorAll, doc, [selector]) : apply(elQsa, root, [selector])) as NodeList;
  const n = Number(apply(listLength!, list, []));
  const out: Element[] = [];
  for (let i = 0; i < n; i += 1) out.push(apply(listItem, list, [i]) as Element);
  return out;
}

export function textNodes(root: Node): Node[] {
  const walker = apply(makeWalker, doc, [root, NodeFilter.SHOW_TEXT]) as TreeWalker;
  const out: Node[] = [];
  for (let n = apply(walkNext, walker, []) as Node | null; n; n = apply(walkNext, walker, []) as Node | null) out.push(n);
  return out;
}

export const rectOf = (e: Element): DOMRect => apply(elRect, e, []) as DOMRect;
export const contains = (a: Node, b: Node): boolean => !!apply(nodeContains, a, [b]);
/** The element a pointer at (x, y) would hit, or null (off the viewport, covered by nothing, or an environment that cannot lay out). */
export const hitAt = (x: number, y: number): Element | null => (docAt ? ((apply(docAt, doc, [x, y]) as Element | null) ?? null) : null);

/** Layout can only be read when the document is drawn at all. A frame the host has hidden has no layout, and that is not the page's doing. */
export function layoutAvailable(): boolean {
  const r = rectOf(bodyEl());
  return r.width > 0 && r.height > 0;
}

/** How visible an element can be: the product of its opacity and every ancestor's. 1 where the environment cannot say. */
export function effectiveOpacity(el: Element): number {
  let out = 1;
  for (let n: Element | null = el; n; n = parentOf(n)) {
    const v = style(n, "opacity");
    if (v !== "" && Number.isFinite(Number(v))) out *= Number(v);
  }
  return out;
}

/** A computed style property, or "" where the environment cannot say. */
export function style(el: Element, property: string, pseudo?: string): string {
  try {
    if (!computed || !styleGet || (pseudo && !PSEUDO_STYLES)) return "";
    return String(apply(styleGet, (pseudo ? computed(el, pseudo) : computed(el)), [property]));
  } catch {
    return "";
  }
}
