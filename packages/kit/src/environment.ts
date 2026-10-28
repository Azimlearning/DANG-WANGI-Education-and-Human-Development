// `environment({title, note})` mounts the chrome every Environment shares: a title, a study-note card, a stage region, controls and
// readouts, using a small set of CSS variables. Touch targets are at least 44 px (hard constraint 10). Every element that carries
// text is registered as Kit-owned with the text it must have, so the L1 audit can tell a Kit-made number from a typed one.

import { installErrorHandlers } from "./bridge";
import { sheetText } from "./dom";
import { kt, setLanguage, type Lang } from "./i18n";
import { copy, isKitStyle, markKitStyle, own, ownAttr, recordKitSheet } from "./provenance";
import { STYLE } from "./style";

export interface Environment {
  root: HTMLElement;
  /** The header: the kicker, the title, the "Try this" line, the key idea, the step cards and the predict card. */
  head: HTMLElement;
  /** The illustrated bench (the left column of the two-column area): scenes and graphs. */
  stage: HTMLElement;
  /** The right column: the controls and the readout cards, the results table, and the graphs when the bench already holds a scene. */
  panel: HTMLElement;
  controls: HTMLElement;
  readouts: HTMLElement;
  /** Below the bench: the Amali card, the study sentences, the hints, the concept check and the worked solution. */
  extras: HTMLElement;
}

export interface EnvironmentOptions {
  title: string;
  note: string;
  /** A small line above the title, such as "Interactive physics lab". */
  kicker?: string;
  /** One line telling the student what to do first. Shown after the label "Try this:". */
  tryThis?: string;
  /** A text equivalent of what the stage shows, announced for screen readers (hard constraint 10). */
  stageText?: string;
  /** The language of the Kit's own words on this page ("en" by default). A Malay page is built from a Malay Plan, so the words around the numbers match. */
  lang?: Lang;
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
  setLanguage(opts.lang ?? "en");
  installErrorHandlers();
  installThemeListener();
  // Copy the strings now: a page that keeps the options object must not be able to change what the Kit later treats as expected.
  const options = {
    title: String(opts.title),
    note: String(opts.note),
    kicker: opts.kicker === undefined ? undefined : String(opts.kicker),
    tryThis: opts.tryThis === undefined ? undefined : String(opts.tryThis),
    stageText: opts.stageText === undefined ? undefined : String(opts.stageText),
    into: opts.into,
  };
  const host = options.into ?? document.body;
  // A stylesheet a page made (even one with the id `syn-style`) is not the Kit's: the Kit always adds its own, and the audit judges the other one on its text.
  if (!Array.from(document.head.querySelectorAll("style")).some(isKitStyle)) {
    const style = document.createElement("style");
    style.id = "syn-style";
    style.textContent = STYLE;
    document.head.appendChild(style);
    markKitStyle(style);
    recordKitSheet(style, sheetText(style));
  }
  const root = document.createElement("main");
  root.className = "syn-env";
  const head = document.createElement("header");
  head.className = "syn-head";
  const h1 = own(document.createElement("h1"), () => options.title);
  h1.textContent = options.title;
  if (options.kicker) {
    const kickerText = options.kicker;
    const kicker = own(div("syn-kicker"), () => kickerText);
    kicker.textContent = kickerText;
    copy.push(kickerText);
    head.appendChild(kicker);
  }
  head.appendChild(h1);
  if (options.tryThis) {
    const tryText = options.tryThis;
    const line = div("syn-try");
    const lead = own(document.createElement("strong"), () => kt("tryThis"));
    lead.textContent = kt("tryThis");
    const rest = own(document.createElement("span"), () => ` ${tryText}`);
    rest.textContent = ` ${tryText}`;
    copy.push(kt("tryThis"), tryText);
    line.append(lead, rest);
    head.appendChild(line);
  }
  const keyIdea = div("syn-keyidea");
  const keyLead = own(document.createElement("strong"), () => kt("keyIdea"));
  keyLead.textContent = kt("keyIdea");
  const note = own(div("syn-note"), () => options.note);
  note.setAttribute("role", "note");
  note.textContent = options.note;
  keyIdea.append(keyLead, note);
  head.appendChild(keyIdea);
  copy.push(options.title, kt("keyIdea"), options.note);
  const main = div("syn-main");
  const stage = div("syn-stage");
  stage.setAttribute("role", "region");
  stage.setAttribute("aria-label", options.stageText ?? kt("stage"));
  ownAttr(stage, "aria-label", () => options.stageText ?? kt("stage"));
  if (options.stageText) copy.push(options.stageText);
  const controls = div("syn-controls");
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", kt("controls"));
  const readouts = div("syn-readouts");
  readouts.setAttribute("role", "group");
  readouts.setAttribute("aria-label", kt("readouts"));
  const panel = div("syn-panel");
  panel.append(controls, readouts);
  main.append(stage, panel);
  const extras = div("syn-extras");
  root.append(head, main, extras);
  host.appendChild(root);
  return { root, head, stage, panel, controls, readouts, extras };
}
