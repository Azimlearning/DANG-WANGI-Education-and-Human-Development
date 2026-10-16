// Runtime self-check, in the student's browser. The verifier can only look at the moments its harness visits; a page can be written to
// misbehave only on a phone, after a minute, or for a real finger (kit-guardian P1 B2). So the Kit keeps auditing itself: a
// MutationObserver (captured at load) and a timer re-run the structural audit, and the first violation is sent to the host, which hides the
// Environment, and is also acted on here by emptying the document. The numeric truth of values is the verifier's job; this catches tampering
// with what the Kit drew, and any number put on screen by other means, while the page runs.

import { audit, violations } from "./audit";
import { violation } from "./bridge";
import { bodyEl } from "./dom";
import { KIT_VERSION } from "./manifest";

const Observer = MutationObserver;
const later = setTimeout;
const every = setInterval;
const observe = MutationObserver.prototype.observe;
// Read ONCE, when the bundle loads (the Kit is the first script, so only the verification harness's own init script can have set it).
// In verification the page is left standing after a violation so the verifier can name every problem; for a student it is emptied.
const VERIFY_MODE = (window as unknown as Record<string, unknown>).__SYNAPSE_VERIFY__ === true;
const INTERVAL_MS = 1000;
const DEBOUNCE_MS = 50;

let started = false;
let tripped = false;
let pending = false;

function check(): void {
  pending = false;
  if (tripped) return;
  let problems: string[] = [];
  try {
    problems = violations(audit(KIT_VERSION));
  } catch (e) {
    problems = ["the self-check could not run: " + String((e as Error)?.message ?? e)];
  }
  if (problems.length === 0) return;
  tripped = true;
  violation(problems);
  if (VERIFY_MODE) return;
  try {
    bodyEl().textContent = "";
    document.documentElement.style.display = "none";
  } catch {
    /* the host hides the frame regardless */
  }
}

export function startWatch(): void {
  if (started) return;
  started = true;
  const schedule = () => {
    if (pending || tripped) return;
    pending = true;
    later(check, DEBOUNCE_MS);
  };
  const observer = new Observer(schedule);
  Reflect.apply(observe, observer, [document, { subtree: true, childList: true, characterData: true, attributes: true }]);
  every(check, INTERVAL_MS);
  check();
}

/** Tests only. */
export function resetWatchForTests(): void {
  started = false;
  tripped = false;
  pending = false;
}
