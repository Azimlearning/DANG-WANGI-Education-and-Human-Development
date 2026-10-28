// `conceptCheck(env, {question, options, correct, explanation})`: one multiple-choice question with immediate feedback. The options are Kit buttons;
// the feedback and the explanation are Kit-owned text, hidden until a choice is made. The author states which option is correct: the Kit cannot check
// that (it is prose), and the page says nothing more than "correct" or "not quite" plus the author's explanation.

import type { Environment } from "./environment";
import { event as hostEvent } from "./bridge";
import { kt } from "./i18n";
import { copy, own, registerAction } from "./provenance";

export interface ConceptCheckOptions {
  question: string;
  options: string[];
  /** Zero-based index of the correct option. */
  correct: number;
  explanation: string;
}

export function conceptCheck(env: Environment, options: ConceptCheckOptions): HTMLElement {
  const question = String(options.question);
  const choices = (options.options ?? []).map(String);
  const explanation = String(options.explanation);
  if (choices.length < 2 || choices.length > 4) throw new RangeError("conceptCheck: 2 to 4 options");
  if (!Number.isInteger(options.correct) || options.correct < 0 || options.correct >= choices.length) throw new RangeError("conceptCheck: correct must index an option");
  if (question.trim() === "" || explanation.trim() === "") throw new RangeError("conceptCheck: needs a question and an explanation");
  const correct = options.correct;
  const wrap = document.createElement("section");
  wrap.className = "syn-card";
  wrap.setAttribute("aria-label", kt("checkTitle"));
  const q = own(document.createElement("p"), () => question);
  q.textContent = question;
  copy.push(question, ...choices, explanation);
  const group = document.createElement("div");
  group.setAttribute("role", "group");
  group.setAttribute("aria-label", kt("options"));
  let feedback = "";
  let answered = false;
  const result = own(document.createElement("p"), () => feedback);
  result.setAttribute("role", "status");
  const why = own(document.createElement("p"), () => (feedback ? explanation : ""));
  choices.forEach((text, i) => {
    const b = own(document.createElement("button"), () => text);
    b.type = "button";
    b.className = "syn-btn";
    b.textContent = text;
    b.setAttribute("data-synapse-action", "choose");
    registerAction(b, "choose", text);
    b.addEventListener("click", () => {
      // The host keeps a device-local record of how the FIRST answer went (P6). Later clicks only show the feedback again.
      if (!answered) {
        answered = true;
        hostEvent("concept_check", i === correct ? "correct" : "incorrect");
      }
      feedback = i === correct ? kt("correct") : kt("notQuite");
      result.textContent = feedback;
      why.textContent = explanation;
    });
    group.appendChild(b);
  });
  wrap.append(q, group, result, why);
  env.extras.appendChild(wrap);
  return wrap;
}
