// `hintLadder(env, {hints})`: help that is given one step at a time. A button reveals the next hint; hints that are not yet shown are hidden but already
// in the page as Kit-owned text, so the audit sees every number in them whether or not they are visible.

import type { Environment } from "./environment";
import { kt } from "./i18n";
import { copy, own, registerAction } from "./provenance";

const MAX_HINTS = 5;

export function hintLadder(env: Environment, options: { hints: string[] }): HTMLElement {
  const hints = (options.hints ?? []).map(String);
  if (hints.length < 1 || hints.length > MAX_HINTS) throw new RangeError(`hintLadder: 1 to ${MAX_HINTS} hints`);
  const wrap = document.createElement("div");
  wrap.className = "syn-card";
  const list = document.createElement("div");
  list.setAttribute("aria-live", "polite");
  const items = hints.map((text) => {
    const p = own(document.createElement("p"), () => text);
    p.textContent = text;
    p.hidden = true;
    copy.push(text);
    list.appendChild(p);
    return p;
  });
  const label = kt("showHint");
  const button = own(document.createElement("button"), () => label);
  button.type = "button";
  button.className = "syn-btn";
  button.textContent = label;
  button.setAttribute("data-synapse-action", "hint");
  registerAction(button, "hint", label);
  let shown = 0;
  button.addEventListener("click", () => {
    if (shown < items.length) items[shown]!.hidden = false;
    shown += 1;
    if (shown >= items.length) button.disabled = true;
  });
  wrap.append(list, button);
  env.extras.appendChild(wrap);
  return wrap;
}
