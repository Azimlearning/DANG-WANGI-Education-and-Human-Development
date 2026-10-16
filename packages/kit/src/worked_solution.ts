// `workedSolution(env, {steps})`: a worked answer the student opens when ready. Every step is Kit-owned text, so the numbers in it are checked like any
// sentence: a step may use only slider values, grid positions, declared constants and model settings, never a computed result typed in.

import type { Environment } from "./environment";
import { copy, own, registerAction } from "./provenance";

export function workedSolution(env: Environment, options: { steps: string[] }): HTMLElement {
  const steps = (options.steps ?? []).map(String);
  if (steps.length < 1 || steps.length > 6) throw new RangeError("workedSolution: 1 to 6 steps");
  const wrap = document.createElement("section");
  wrap.className = "syn-card";
  wrap.setAttribute("aria-label", "Worked solution");
  const list = document.createElement("ol");
  list.className = "syn-steps";
  list.hidden = true;
  for (const text of steps) {
    const li = own(document.createElement("li"), () => text);
    li.textContent = text;
    copy.push(text);
    list.appendChild(li);
  }
  const label = "Show the worked solution";
  const button = own(document.createElement("button"), () => label);
  button.type = "button";
  button.className = "syn-btn";
  button.textContent = label;
  button.setAttribute("data-synapse-action", "solution");
  registerAction(button, "solution", label);
  button.addEventListener("click", () => {
    list.hidden = false;
    button.disabled = true;
  });
  wrap.append(button, list);
  env.stage.appendChild(wrap);
  return wrap;
}
