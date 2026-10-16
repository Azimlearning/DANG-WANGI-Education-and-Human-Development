// `text(env, string)` is the sanctioned way for generated code to write copy. The string is owned (it cannot be edited afterwards)
// and recorded; the verifier refuses any number in it that is not backed by a model parameter, a control range or a declared constant.

import type { Environment } from "./environment";
import { copy, own } from "./provenance";

export function text(env: Environment, content: string): HTMLParagraphElement {
  const p = own(document.createElement("p"), () => content);
  p.className = "syn-text";
  p.textContent = content;
  copy.push(content);
  env.stage.appendChild(p);
  return p;
}
