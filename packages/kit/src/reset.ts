// `reset(env)`: one button that puts every control back to its starting value; the readouts follow because they are derived.
// The button is registered as a Kit action, so the render harness knows it is not an undeclared control and the audit refuses a
// look-alike a script made (`data-synapse-action` on an element the Kit did not create).

import { event } from "./bridge";
import type { Environment } from "./environment";
import { controls, own, registerAction } from "./provenance";

export function reset(env: Environment, options: { label?: string } = {}): HTMLButtonElement {
  const label = String(options.label ?? "Reset");
  const button = own(document.createElement("button"), () => label);
  button.type = "button";
  button.className = "syn-btn";
  button.textContent = label;
  button.setAttribute("data-synapse-action", "reset");
  button.addEventListener("click", () => {
    for (const c of controls) {
      (c.obs as { set(v: number): void }).set(c.default);
      event(c.id, c.default);
    }
  });
  registerAction(button, "reset", label);
  env.controls.appendChild(button);
  return button;
}
