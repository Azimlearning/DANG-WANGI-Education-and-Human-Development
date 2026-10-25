// `Synapse.audit()`: the Kit's report to the verifier (layer L1). It states facts; the verifier (api/verify) decides. It returns plain,
// serialisable data. Every read of the page goes through the primitives captured in dom.ts when the bundle loaded, and lockdown.ts
// freezes the intrinsics before any generated script runs, so a page cannot blind the audit by patching built-ins or shadowing a
// property on `document`. The same facts feed the runtime self-check (watch.ts), which runs in the student's browser.

import { adoptedCount, all, attr, attrNames, bodyEl, fontCount, hasAttribute, hasShadow, headEl, idOf, parentOf, sheetText, style, tagOf, textNodes, textOf, value } from "./dom";
import { actions, constants, controls, copy, describe, isAction, isOwned, ownedAttr, ownedEntries, readouts, series, type ChainNode, isKitStyle, isKitSvg, isOwnStyle, kitSheetRules, widgets } from "./provenance";
import { STYLE } from "./style";

let sealed: object | null = null;
/** Called once by the entry module with the frozen public object. */
export function seal(synapse: object): void {
  sealed = synapse;
}

// Attributes whose value is spoken, shown as a tooltip, used as a placeholder, or drawn as a marker.
const WORDS_ATTRS = [
  "aria-label", "aria-valuetext", "aria-description", "aria-roledescription", "title", "alt", "placeholder", "aria-valuenow", "aria-valuemin",
  "aria-valuemax", "aria-posinset", "aria-setsize", "aria-level", "aria-rowcount", "aria-colcount", "aria-rowindex", "aria-colindex", "content",
];
const HAS_NUMBER = /\p{N}/u;
// A number in copy: digits (any script, after NFKC) not glued to a letter, so R1, H2O and CO2 are identifiers, not quantities.
const COPY_NUMBER = /(?<![A-Za-z0-9_.])-?\d+(?:\.\d+)?/g;
const FORBIDDEN_TAGS = ["canvas", "meter", "progress", "video", "audio", "img", "picture", "object", "embed", "iframe", "frame", "source", "track", "map", "area", "dialog"];
const INTERACTIVE = "input, select, textarea, button, output, details, summary, [contenteditable], a[href], [role=slider], [role=button], [role=spinbutton]";
const CSS_IMAGE_PROPS = ["background-image", "list-style-image", "border-image-source", "mask-image", "-webkit-mask-image", "shape-outside"];
const STYLE_FORBIDDEN = /@font-face|@import|url\s*\(|image-set\s*\(|\bcontent\s*:/i;
// The ways a list marker can show a number with no text node: a counter set or stepped by CSS, the ::marker pseudo-element, a quoted marker string,
// and any element made a list item. Looked for in stylesheet text AND in inline style attributes (refused whole: nothing the Kit makes needs them).
const MARKER_FORBIDDEN = /@counter-style\b|\bcounter-(?:reset|set|increment)\b|\bcounters?\s*\(|::?marker\b|\blist-style(?:-type)?\s*:[^;}]*["']|\bdisplay\s*:\s*(?:list-item|inline list-item|block list-item)/i;
// Elements that are never drawn. If CSS makes one visible, its text (a title, a script's source) is shown to the student with no component owning it.
const NON_VISUAL = ["script", "style", "noscript", "template", "title", "meta", "link", "base", "head"];

export interface AuditRecord {
  kitVersion: string;
  /** True only when `window.Synapse` is the sealed object and cannot be replaced. */
  intact: boolean;
  controls: { id: string; label: string; unit: string; min: number; max: number; grid: number; default: number; step: number; value: number; inputValue: string }[];
  readouts: { label: string; unit: string; digits: number; value: number; displayed: string; expected: string; chain: ChainNode }[];
  /** How many `[data-synapse-readout]` elements the page really has (must equal `readouts.length`). */
  readoutElements: number;
  constants: { label: string; unit: string; value: number }[];
  /** Values shown by tables and graphs, with their chains; a graph also lists the (x, y) points it drew. */
  series: { kind: string; title: string; label: string; unit: string; digits: number; value: number; chain: ChainNode; xControl?: string; points?: [number, number][] }[];
  /** Buttons the Kit made. */
  actions: { kind: string; label: string }[];
  /** Elements carrying data-synapse-action that no Kit component made. */
  forgedActions: number;
  /** Static copy, with the numbers found in it. The verifier checks each number is backed. */
  copy: { text: string; numbers: string[] }[];
  /** Kit-owned elements whose live text differs from the text the Kit gave them. */
  ownedMismatches: { tag: string; expected: string; actual: string }[];
  /** Text nodes containing a digit whose parent element no Kit component made. */
  unownedNumbers: { text: string; parent: string }[];
  /** Spoken or tooltip attributes holding a digit that the Kit did not set (or whose value was changed). */
  unownedAttributeNumbers: { attribute: string; value: string; element: string }[];
  /** Elements and styles that can put a number on screen without a text node: canvas, media, list counters, CSS images, fonts, look-alike widgets. */
  forbidden: { what: string; element: string }[];
  /** CSS or markup a Kit page may not carry at all: a stylesheet or inline style the Kit did not make, a changed Kit stylesheet, a constructed stylesheet, a popover. The verifier refuses
   * every one; the student's runtime self-check does NOT act on them, because a browser extension (a dark-mode or translation tool, a screenshot tool) adds styles to pages it did not write. */
  foreign: { what: string; element: string }[];
  /** Elements with a shadow root: their content cannot be audited, so the verifier refuses them. */
  shadowRoots: number;
  /** Composite widgets (mass hangers, scenes): what each is, how many masses the Kit made, the chain a scene draws, and any way the page changed it. */
  widgets: { kind: string; id: string; masses?: number; full?: number; eye?: boolean; chain?: ChainNode; sourceChain?: ChainNode; secondChain?: ChainNode; problems: string[]; exact: string[]; layout: string[] }[];
}

/** True for an element inside a drawing the Kit made (a nested `svg` the Kit's own picture holds is the Kit's). */
function kitInside(el: Element): boolean {
  for (let n: Element | null = parentOf(el); n; n = parentOf(n)) if (isKitSvg(n)) return true;
  return false;
}

const label = (el: Element): string => `${tagOf(el)}${idOf(el) ? "#" + idOf(el) : ""}`;

function kitWidget(el: Element): boolean {
  return isAction(el) || controls.some((c) => c.el === el) || readouts.some((r) => r.el === el);
}

export function audit(version: string): AuditRecord {
  const descriptor = Object.getOwnPropertyDescriptor(window, "Synapse");
  const intact = !!descriptor && descriptor.value === sealed && descriptor.writable === false && descriptor.configurable === false;
  const body = bodyEl();

  const unowned: { text: string; parent: string }[] = [];
  for (const node of textNodes(body)) {
    const text = textOf(node).trim();
    const parent = parentOf(node);
    if (!text || !HAS_NUMBER.test(text) || !parent) continue;
    const tag = tagOf(parent);
    if (tag === "script" || tag === "style" || tag === "noscript") continue;
    if (!isOwned(parent)) unowned.push({ text: text.slice(0, 80), parent: label(parent) });
  }

  const attrs: { attribute: string; value: string; element: string }[] = [];
  const forbidden: { what: string; element: string }[] = [];
  const foreign: { what: string; element: string }[] = [];
  let shadowRoots = 0;
  let forgedActions = 0;
  const elements = all(body, "*");
  for (const el of elements) {
    const tag = tagOf(el);
    if (hasShadow(el)) shadowRoots += 1;
    if (hasAttribute(el, "data-synapse-action") && !isAction(el)) forgedActions += 1;
    for (const name of attrNames(el)) {
      const lower = name.toLowerCase();
      if (!WORDS_ATTRS.includes(lower)) continue;
      const v = attr(el, name);
      if (!HAS_NUMBER.test(v)) continue;
      const expected = ownedAttr(el, lower);
      if (!expected || expected() !== v) attrs.push({ attribute: lower, value: v.slice(0, 80), element: label(el) });
    }
    if (FORBIDDEN_TAGS.includes(tag)) forbidden.push({ what: `<${tag}> element`, element: label(el) });
    if (tag === "ol" && hasAttribute(el, "start")) forbidden.push({ what: "list counter start", element: label(el) });
    if (tag === "li" && hasAttribute(el, "value")) forbidden.push({ what: "list item value", element: label(el) });
    // A marker can be given content or a counter on ANY element made a list item, not only ol, ul and li.
    const marker = style(el, "content", "::marker");
    if (marker && marker !== "normal" && marker !== "none") forbidden.push({ what: "list marker content", element: label(el) });
    const markerString = style(el, "list-style-type");
    if (markerString && /^["']/.test(markerString)) forbidden.push({ what: "list marker string", element: label(el) });
    if (tag !== "li" && style(el, "display") === "list-item") forbidden.push({ what: "list item display on a non-list element", element: label(el) });
    const inline = attr(el, "style");
    if (inline && (MARKER_FORBIDDEN.test(inline) || STYLE_FORBIDDEN.test(inline))) {
      forbidden.push({ what: "inline style that can draw a number", element: label(el) });
    }
    // A Kit page has no CSS but the Kit's: the only inline styles are the ones the Kit sets itself, and nothing a page can style is outside the Kit's own rules.
    if (inline !== "" && !isOwnStyle(el)) foreign.push({ what: "an inline style the Kit did not set", element: label(el) });
    if (tag === "svg" && !isKitSvg(el) && !kitInside(el)) foreign.push({ what: "a drawing the Kit did not make", element: label(el) });
    if (hasAttribute(el, "popover")) foreign.push({ what: "a popover (it draws in the top layer)", element: label(el) });
    if (NON_VISUAL.includes(tag)) {
      const shown = style(el, "display");
      if (shown && shown !== "none") forbidden.push({ what: `<${tag}> made visible`, element: label(el) });
    }
    for (const prop of CSS_IMAGE_PROPS) {
      const v = style(el, prop);
      if (v && v !== "none") forbidden.push({ what: `CSS ${prop}`, element: label(el) });
    }
    for (const pseudo of ["::before", "::after"]) {
      const c = style(el, "content", pseudo);
      if (c && c !== "none" && c !== "normal" && c !== '""') forbidden.push({ what: `CSS ${pseudo} content`, element: label(el) });
    }
  }
  for (const el of all(body, INTERACTIVE)) {
    if (!kitWidget(el)) forbidden.push({ what: "a widget no Kit component made", element: label(el) });
  }
  for (const s of all(headEl(), "style, link")) {
    const tag = tagOf(s);
    if (tag === "link") forbidden.push({ what: "<link> element", element: label(s) });
    else if (!(isKitStyle(s) && textOf(s) === STYLE)) {
      foreign.push({ what: "a stylesheet the Kit did not make", element: label(s) });
      if (STYLE_FORBIDDEN.test(textOf(s)) || MARKER_FORBIDDEN.test(textOf(s))) {
        forbidden.push({ what: "stylesheet with an image, font, import or generated content", element: label(s) });
      }
    } else if (sheetText(s) !== (kitSheetRules(s) ?? null)) {
      foreign.push({ what: "the Kit's stylesheet was changed", element: label(s) });
    }
  }
  for (const s of all(body, "style")) {
    foreign.push({ what: "a stylesheet the Kit did not make", element: label(s) });
    if (STYLE_FORBIDDEN.test(textOf(s)) || MARKER_FORBIDDEN.test(textOf(s))) {
      forbidden.push({ what: "stylesheet with an image, font, import or generated content", element: label(s) });
    }
  }
  if (adoptedCount() > 0) foreign.push({ what: "a constructed stylesheet", element: "document" });
  // The head's own non-visual elements are not in the body walk above: check that none was made visible, and that none carries a style that draws.
  for (const el of all(headEl(), "*")) {
    const tag = tagOf(el);
    if (NON_VISUAL.includes(tag)) {
      const shown = style(el, "display");
      if (shown && shown !== "none") forbidden.push({ what: `<${tag}> made visible`, element: label(el) });
    }
    const inline = attr(el, "style");
    if (inline && (MARKER_FORBIDDEN.test(inline) || STYLE_FORBIDDEN.test(inline))) {
      forbidden.push({ what: "inline style that can draw a number", element: label(el) });
    }
    if (inline !== "") foreign.push({ what: "an inline style the Kit did not set", element: label(el) });
  }
  // The body itself is in neither walk (the first covers its descendants, the second the head).
  if (style(body, "display") === "list-item") forbidden.push({ what: "list item display on a non-list element", element: "body" });
  const bodyInline = attr(body, "style");
  if (bodyInline && (MARKER_FORBIDDEN.test(bodyInline) || STYLE_FORBIDDEN.test(bodyInline))) {
    forbidden.push({ what: "inline style that can draw a number", element: "body" });
  }
  if (bodyInline !== "" && !isOwnStyle(body)) foreign.push({ what: "an inline style the Kit did not set", element: "body" });
  for (const rootEl of all(document, ":root")) {
    if (attr(rootEl, "style") !== "" && !isOwnStyle(rootEl)) foreign.push({ what: "an inline style the Kit did not set", element: "html" });
  }
  if (fontCount() > 0) forbidden.push({ what: "a font loaded by script", element: "document" });

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
      step: c.step,
      value: (c.obs as { get(): number }).get(),
      inputValue: value(c.el),
    })),
    readouts: readouts.map((r) => {
      const v = r.obs.get();
      return {
        label: r.label,
        unit: r.unit,
        digits: r.digits,
        value: v,
        displayed: textOf(r.el),
        expected: `${v.toFixed(r.digits)} ${r.unit}`,
        chain: describe(r.obs),
      };
    }),
    readoutElements: all(body, "[data-synapse-readout]").length,
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
    copy: copy.map((text) => ({ text, numbers: text.normalize("NFKC").match(COPY_NUMBER) ?? [] })),
    ownedMismatches: ownedEntries().flatMap(([el, expected]) => {
      const actual = textOf(el);
      const want = expected();
      return actual === want ? [] : [{ tag: tagOf(el), expected: want, actual: actual.slice(0, 80) }];
    }),
    unownedNumbers: unowned,
    unownedAttributeNumbers: attrs,
    forbidden,
    foreign,
    shadowRoots,
    widgets: widgets.map((w) => ({
      kind: w.kind,
      id: w.id,
      ...(w.masses !== undefined ? { masses: w.masses } : {}),
      ...(w.full !== undefined ? { full: w.full } : {}),
      ...(w.eye ? { eye: true } : {}),
      ...(w.obs ? { chain: describe(w.obs) } : {}),
      ...(w.source ? { sourceChain: describe(w.source) } : {}),
      ...(w.second ? { secondChain: describe(w.second) } : {}),
      problems: w.check(),
      exact: w.exact ? w.exact() : [],
      layout: w.layout ? w.layout() : [],
    })),
  };
}

/** The structural problems a record shows, for the runtime self-check. Numeric truth is the verifier's job; this catches tampering live. */
export function violations(a: AuditRecord): string[] {
  const out: string[] = [];
  for (const r of a.readouts) if (r.displayed !== r.expected) out.push(`readout "${r.label}" shows ${r.displayed}`);
  if (a.readoutElements !== a.readouts.length) out.push("a readout element the Kit did not make");
  for (const m of a.ownedMismatches) out.push(`a ${m.tag} the Kit made was edited`);
  for (const u of a.unownedNumbers) out.push(`a number outside the Kit's elements: ${u.text}`);
  for (const u of a.unownedAttributeNumbers) out.push(`${u.attribute} holds a number the Kit did not set`);
  for (const f of a.forbidden) out.push(f.what);
  if (a.shadowRoots) out.push("a shadow root");
  if (a.forgedActions) out.push("a forged action button");
  for (const w of a.widgets) for (const p of w.problems) out.push(p);
  for (const c of a.controls) if (!(Math.abs(Number(c.inputValue) - c.value) <= c.step / 2 + 1e-9)) out.push(`control "${c.id}" disagrees with its input`);
  return out;
}
