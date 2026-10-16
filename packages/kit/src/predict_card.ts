// `predictCard(env, {prompt, choices, reveal})`: predict, then observe, then explain. The student commits to a prediction BEFORE using the sliders; the
// Kit then shows the author's note about what to look for. It stores nothing and grades nothing: a prediction is the student's own.

import type { Environment } from "./environment";
import { copy, own, registerAction } from "./provenance";

export function predictCard(env: Environment, options: { prompt: string; choices: string[]; reveal: string }): HTMLElement {
  const prompt = String(options.prompt);
  const choices = (options.choices ?? []).map(String);
  const reveal = String(options.reveal);
  if (choices.length < 2 || choices.length > 4) throw new RangeError("predictCard: 2 to 4 choices");
  if (prompt.trim() === "" || reveal.trim() === "") throw new RangeError("predictCard: needs a prompt and a reveal");
  const wrap = document.createElement("section");
  wrap.className = "syn-card";
  wrap.setAttribute("aria-label", "Make a prediction");
  const p = own(document.createElement("p"), () => prompt);
  p.textContent = prompt;
  copy.push(prompt, ...choices, reveal);
  const group = document.createElement("div");
  group.setAttribute("role", "group");
  group.setAttribute("aria-label", "Your prediction");
  let chosen = false;
  const note = own(document.createElement("p"), () => (chosen ? reveal : ""));
  note.setAttribute("role", "status");
  for (const text of choices) {
    const b = own(document.createElement("button"), () => text);
    b.type = "button";
    b.className = "syn-btn";
    b.textContent = text;
    b.setAttribute("data-synapse-action", "predict");
    registerAction(b, "predict", text);
    b.addEventListener("click", () => {
      chosen = true;
      note.textContent = reveal;
    });
    group.appendChild(b);
  }
  wrap.append(p, group, note);
  env.stage.appendChild(wrap);
  return wrap;
}
