// `table(env, {caption, columns})`: results the student records. Each column shows a Kit observable; the Record button appends one row
// holding the current values, formatted by the Kit. Cells are Kit-owned with the text they were given, so editing one is detected.
// Each column is reported to the verifier as a series, so its chain must be grounded in controls and models like a readout's.

import { lab } from "./bridge";
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
  const caption = String(options.caption);
  // Snapshot the columns now: Record must read what was verified, not whatever the caller later puts in the array it kept.
  const columns: Required<TableColumn>[] = (options.columns ?? []).map((c) => ({ label: String(c.label), unit: String(c.unit), value: c.value, digits: c.digits ?? 2 }));
  if (columns.length < 1 || columns.length > 6) throw new RangeError("table: 1 to 6 columns");
  for (const c of columns) {
    if (!isObservable(c.value)) throw new TypeError(`table column "${c.label}": value must be a Kit observable`);
    const digits = c.digits;
    if (!Number.isInteger(digits) || digits < 0 || digits > 8) throw new RangeError(`table column "${c.label}": digits must be 0 to 8`);
  }
  const wrap = document.createElement("div");
  const scroller = document.createElement("div");
  scroller.className = "syn-table-wrap";
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
    series.push({ kind: "table", title: caption, label: c.label, unit: c.unit, digits: c.digits, obs: c.value });
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
  // What the student has recorded, as the cells show it. The host builds the lab report from this (W5b); it is sent whole each time so a lost message cannot corrupt it.
  const recorded: string[][] = [];
  const tell = () => lab({ part: "table", caption, columns: columns.map((c) => ({ label: c.label, unit: c.unit })), rows: recorded });
  record.addEventListener("click", () => {
    if (body.rows.length >= MAX_ROWS) return;
    const tr = document.createElement("tr");
    const cells: string[] = [];
    for (const c of columns) {
      const text = c.value.get().toFixed(c.digits);
      const td = own(document.createElement("td"), () => text);
      td.textContent = text;
      tr.appendChild(td);
      cells.push(text);
    }
    body.appendChild(tr);
    recorded.push(cells);
    tell();
    announce("Row recorded");
  });
  clear.addEventListener("click", () => {
    for (const tr of Array.from(body.rows)) {
      // The owned-element registry holds the cells; they leave the page with the row and the audit only visits attached nodes.
      tr.remove();
    }
    recorded.length = 0;
    tell();
    announce("Table cleared");
  });
  // Rows are added silently otherwise; a polite status tells a screen-reader user what the button did.
  const status = own(document.createElement("p"), () => announced);
  status.className = "syn-sr";
  status.setAttribute("role", "status");
  let announced = "";
  const announce = (message: string) => {
    announced = message;
    status.textContent = message;
  };
  const buttons = document.createElement("div");
  buttons.append(record, clear);
  scroller.appendChild(el);
  wrap.append(scroller, buttons, status);
  env.stage.appendChild(wrap);
  tell();
  return el;
}
