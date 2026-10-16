// `table(env, {caption, columns})`: results the student records. Each column shows a Kit observable; the Record button appends one row
// holding the current values, formatted by the Kit. Cells are Kit-owned with the text they were given, so editing one is detected.
// Each column is reported to the verifier as a series, so its chain must be grounded in controls and models like a readout's.

import type { Environment } from "./environment";
import type { Observable } from "./observable";
import { isObservable } from "./provenance";
import { copy, own, registerAction, series } from "./provenance";

export interface TableColumn {
  label: string;
  unit: string;
  value: Observable<number>;
  digits?: number;
}

const MAX_ROWS = 30;

export function table(env: Environment, options: { caption: string; columns: TableColumn[] }): HTMLTableElement {
  const { caption, columns } = options;
  if (columns.length < 1 || columns.length > 6) throw new RangeError("table: 1 to 6 columns");
  for (const c of columns) {
    if (!isObservable(c.value)) throw new TypeError(`table column "${c.label}": value must be a Kit observable`);
    const digits = c.digits ?? 2;
    if (!Number.isInteger(digits) || digits < 0 || digits > 8) throw new RangeError(`table column "${c.label}": digits must be 0 to 8`);
  }
  const wrap = document.createElement("div");
  const el = document.createElement("table");
  el.className = "syn-table";
  const cap = own(document.createElement("caption"), () => caption);
  cap.textContent = caption;
  copy.push(caption);
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const c of columns) {
    const text = `${c.label} (${c.unit})`;
    const th = own(document.createElement("th"), () => text);
    th.scope = "col";
    th.textContent = text;
    copy.push(c.label, c.unit);
    headRow.appendChild(th);
    series.push({ kind: "table", title: caption, label: c.label, unit: c.unit, digits: c.digits ?? 2, obs: c.value });
  }
  head.appendChild(headRow);
  const body = document.createElement("tbody");
  el.append(cap, head, body);

  const record = document.createElement("button");
  const clear = document.createElement("button");
  for (const [b, kind, label] of [[record, "record", "Record"], [clear, "clear", "Clear"]] as const) {
    own(b, () => label);
    b.type = "button";
    b.className = "syn-btn";
    b.textContent = label;
    b.setAttribute("data-synapse-action", kind);
    registerAction(b, kind, label);
  }
  record.addEventListener("click", () => {
    if (body.rows.length >= MAX_ROWS) return;
    const tr = document.createElement("tr");
    for (const c of columns) {
      const text = c.value.get().toFixed(c.digits ?? 2);
      const td = own(document.createElement("td"), () => text);
      td.textContent = text;
      tr.appendChild(td);
    }
    body.appendChild(tr);
  });
  clear.addEventListener("click", () => {
    for (const tr of Array.from(body.rows)) {
      // The owned-element registry holds the cells; they leave the page with the row and the audit only visits attached nodes.
      tr.remove();
    }
  });
  const buttons = document.createElement("div");
  buttons.append(record, clear);
  wrap.append(el, buttons);
  env.stage.appendChild(wrap);
  return el;
}
