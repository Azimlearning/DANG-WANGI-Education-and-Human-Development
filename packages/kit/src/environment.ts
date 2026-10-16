// `environment({title, note})` mounts the chrome every Environment shares: a title, a study-note card, a stage region, controls and
// readouts, using a small set of CSS variables. Touch targets are at least 44 px (hard constraint 10). Every element that carries
// text is registered as Kit-owned with the text it must have, so the L1 audit can tell a Kit-made number from a typed one.

import { installErrorHandlers } from "./bridge";
import { copy, own, ownAttr } from "./provenance";

export interface Environment {
  root: HTMLElement;
  stage: HTMLElement;
  controls: HTMLElement;
  readouts: HTMLElement;
}

export interface EnvironmentOptions {
  title: string;
  note: string;
  /** A text equivalent of what the stage shows, announced for screen readers (hard constraint 10). */
  stageText?: string;
  /** Where to mount. Defaults to document.body. */
  into?: HTMLElement;
}

const STYLE = `
:root{--syn-bg:#ffffff;--syn-fg:#14213d;--syn-muted:#4a5568;--syn-accent:#0b5fff;--syn-card:#f3f6fb;--syn-border:#c9d3e3;--syn-radius:12px}
@media (prefers-color-scheme: dark){:root{--syn-bg:#10151f;--syn-fg:#eef2fa;--syn-muted:#aab6cc;--syn-accent:#7aa7ff;--syn-card:#1a2232;--syn-border:#33415c}}
*{box-sizing:border-box}
body{margin:0;background:var(--syn-bg);color:var(--syn-fg);font:16px/1.5 system-ui,sans-serif}
.syn-env{max-width:720px;margin:0 auto;padding:16px;display:grid;gap:16px}
.syn-env h1{font-size:1.4rem;margin:0}
.syn-note{background:var(--syn-card);border:1px solid var(--syn-border);border-radius:var(--syn-radius);padding:12px 16px;color:var(--syn-muted)}
.syn-stage{min-height:120px;border:1px solid var(--syn-border);border-radius:var(--syn-radius);padding:12px;display:grid;gap:8px}
.syn-controls,.syn-readouts{display:grid;gap:12px}
.syn-control{display:grid;gap:4px}
.syn-control label{font-weight:600}
.syn-control input[type=range]{width:100%;min-height:44px;accent-color:var(--syn-accent)}
.syn-readout{display:flex;justify-content:space-between;align-items:center;min-height:44px;background:var(--syn-card);border:1px solid var(--syn-border);border-radius:var(--syn-radius);padding:8px 16px}
.syn-readout output{font-weight:700;font-variant-numeric:tabular-nums}
.syn-btn{min-height:44px;min-width:44px;padding:0 16px;border-radius:var(--syn-radius);border:1px solid var(--syn-border);background:var(--syn-card);color:var(--syn-fg);font:inherit;font-weight:600}
.syn-text{margin:0;color:var(--syn-muted)}
.syn-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.syn-graph{width:100%;height:auto;max-height:260px}
.syn-table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
.syn-table th,.syn-table td{border:1px solid var(--syn-border);padding:6px 8px;text-align:right}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
`;

function div(className: string): HTMLDivElement {
  const el = document.createElement("div");
  el.className = className;
  return el;
}

export function environment(options: EnvironmentOptions): Environment {
  installErrorHandlers();
  const host = options.into ?? document.body;
  if (!document.getElementById("syn-style")) {
    const style = document.createElement("style");
    style.id = "syn-style";
    style.textContent = STYLE;
    document.head.appendChild(style);
  }
  const root = document.createElement("main");
  root.className = "syn-env";
  const h1 = own(document.createElement("h1"), () => options.title);
  h1.textContent = options.title;
  const note = own(div("syn-note"), () => options.note);
  note.setAttribute("role", "note");
  note.textContent = options.note;
  copy.push(options.title, options.note);
  const stage = div("syn-stage");
  stage.setAttribute("role", "region");
  stage.setAttribute("aria-label", options.stageText ?? "Stage");
  ownAttr(stage, "aria-label", () => options.stageText ?? "Stage");
  if (options.stageText) copy.push(options.stageText);
  const controls = div("syn-controls");
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", "Controls");
  const readouts = div("syn-readouts");
  readouts.setAttribute("role", "group");
  readouts.setAttribute("aria-label", "Readouts");
  root.append(h1, note, stage, controls, readouts);
  host.appendChild(root);
  return { root, stage, controls, readouts };
}
