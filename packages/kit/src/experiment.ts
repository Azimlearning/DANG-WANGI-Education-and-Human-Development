// `experiment(env, {aim, hypothesis, independent, dependent, controlled, apparatus})`: the Amali card, the scaffold of a practical
// (SPM practical test): what is being investigated, what is changed, what is measured, what is kept the same and what is used. Every word is
// Kit-owned text, so a number in it must be a slider value, a model setting or a declared constant.

import { lab } from "./bridge";
import type { Environment } from "./environment";
import { kt } from "./i18n";
import { copy, own } from "./provenance";

export interface ExperimentOptions {
  aim: string;
  hypothesis: string;
  /** The quantity the student changes. */
  independent: string;
  /** The quantity the student measures. */
  dependent: string;
  /** Quantities kept the same. */
  controlled: string[];
  apparatus: string[];
}

export function experiment(env: Environment, options: ExperimentOptions): HTMLElement {
  const fields: [string, string][] = [
    [kt("aim"), String(options.aim)],
    [kt("hypothesis"), String(options.hypothesis)],
    [kt("changed"), String(options.independent)],
    [kt("measured"), String(options.dependent)],
    [kt("kept"), (options.controlled ?? []).map(String).join("; ")],
    [kt("apparatus"), (options.apparatus ?? []).map(String).join("; ")],
  ];
  if (fields.some(([, v]) => v.trim() === "")) throw new RangeError("experiment: every field needs text");
  if ((options.controlled ?? []).length > 6 || (options.apparatus ?? []).length > 8) throw new RangeError("experiment: too many items");
  const card = document.createElement("section");
  card.className = "syn-card";
  card.setAttribute("aria-label", kt("experimentTitle"));
  const list = document.createElement("dl");
  for (const [name, value] of fields) {
    const dt = own(document.createElement("dt"), () => name);
    dt.textContent = name;
    const dd = own(document.createElement("dd"), () => value);
    dd.textContent = value;
    copy.push(value);
    list.append(dt, dd);
  }
  card.appendChild(list);
  env.extras.appendChild(card);
  lab({ part: "experiment", fields });
  return card;
}
