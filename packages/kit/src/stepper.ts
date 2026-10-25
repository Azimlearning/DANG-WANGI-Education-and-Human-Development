// `stepper(env, {steps})`: the procedure of an experiment as an ordered list. Every step is Kit-owned text, so the numbers in it are checked
// like any other sentence (a step may state a slider value, a model setting or a declared constant, and nothing else).

import { lab } from "./bridge";
import type { Environment } from "./environment";
import { copy, own } from "./provenance";

const MAX_STEPS = 8;

export function stepper(env: Environment, options: { steps: string[] }): HTMLOListElement {
  const steps = (options.steps ?? []).map((s) => String(s));
  if (steps.length < 1 || steps.length > MAX_STEPS) throw new RangeError(`stepper: 1 to ${MAX_STEPS} steps`);
  const list = document.createElement("ol");
  list.className = "syn-steps";
  list.setAttribute("aria-label", "Steps");
  for (const step of steps) {
    const item = own(document.createElement("li"), () => step);
    item.textContent = step;
    copy.push(step);
    list.appendChild(item);
  }
  env.stage.appendChild(list);
  lab({ part: "steps", steps });
  return list;
}
