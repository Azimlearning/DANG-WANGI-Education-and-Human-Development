// `environment({title, note})` mounts the chrome every Environment shares: a title, a study-note card, a stage region, controls and
// readouts, using a small set of CSS variables. Touch targets are at least 44 px (hard constraint 10). Every element that carries
// text is registered as Kit-owned with the text it must have, so the L1 audit can tell a Kit-made number from a typed one.

import { installErrorHandlers } from "./bridge";
import { copy, isKitStyle, markKitStyle, own, ownAttr } from "./provenance";
import { STYLE } from "./style";

export interface Environment {
  root: HTMLElement;
  stage: HTMLElement;
  controls: HTMLElement;
  readouts: HTMLElement;
}

export interface EnvironmentOptions {
  title: string;
  note: string;
  /** A text equivalent of what the stage shows, announced for screen readers (hard constraint 10). */
  stageText?: string;
  /** Where to mount. Defaults to document.body. */
  into?: HTMLElement;
}


function div(className: string): HTMLDivElement {
  const el = document.createElement("div");
  el.className = className;
  return el;
}

// The host page tells the frame which theme it is in. A sandboxed frame has an opaque origin and cannot read the host's attribute, so the host posts one message
// and the frame sets `data-theme` on its own root, which the stylesheet reads. Exactly one message shape is accepted: `{type: "synapse_theme", theme}` with
// theme "light" or "dark". The sender check is hygiene, not a barrier: a page can build a MessageEvent with any `source`, and it can already set any
// attribute on its own root. What the listener guarantees is the SHAPE: nothing but one of two words is ever written, so the Kit adds no way to put
// text, a number or markup on the page.
const setAttribute = Element.prototype.setAttribute;
let themeListening = false;
function installThemeListener(): void {
  if (themeListening || typeof window === "undefined") return;
  themeListening = true;
  const parent = window.parent;
  window.addEventListener("message", (event: MessageEvent) => {
    if (event.source !== parent) return;
    const data = event.data as { type?: unknown; theme?: unknown } | null;
    if (data === null || typeof data !== "object" || data.type !== "synapse_theme") return;
    if (data.theme !== "light" && data.theme !== "dark") return;
    Reflect.apply(setAttribute, document.documentElement, ["data-theme", data.theme]);
  });
}

export function environment(opts: EnvironmentOptions): Environment {
  installErrorHandlers();
  installThemeListener();
  // Copy the strings now: a page that keeps the options object must not be able to change what the Kit later treats as expected.
  const options = { title: String(opts.title), note: String(opts.note), stageText: opts.stageText === undefined ? undefined : String(opts.stageText), into: opts.into };
  const host = options.into ?? document.body;
  // A stylesheet a page made (even one with the id `syn-style`) is not the Kit's: the Kit always adds its own, and the audit judges the other one on its text.
  if (!Array.from(document.head.querySelectorAll("style")).some(isKitStyle)) {
    const style = document.createElement("style");
    style.id = "syn-style";
    style.textContent = STYLE;
    document.head.appendChild(style);
    markKitStyle(style);
  }
  const root = document.createElement("main");
  root.className = "syn-env";
  const h1 = own(document.createElement("h1"), () => options.title);
  h1.textContent = options.title;
  const note = own(div("syn-note"), () => options.note);
  note.setAttribute("role", "note");
  note.textContent = options.note;
  copy.push(options.title, options.note);
  const stage = div("syn-stage");
  stage.setAttribute("role", "region");
  stage.setAttribute("aria-label", options.stageText ?? "Stage");
  ownAttr(stage, "aria-label", () => options.stageText ?? "Stage");
  if (options.stageText) copy.push(options.stageText);
  const controls = div("syn-controls");
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", "Controls");
  const readouts = div("syn-readouts");
  readouts.setAttribute("role", "group");
  readouts.setAttribute("aria-label", "Readouts");
  root.append(h1, note, stage, controls, readouts);
  host.appendChild(root);
  return { root, stage, controls, readouts };
}
