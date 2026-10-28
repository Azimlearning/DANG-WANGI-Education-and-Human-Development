// The lab report (W5b): what the Kit's experiment card, steps and table told the host, plus what the student writes. A view of what the Kit showed, never text the
// host composes itself. The student's own writing stays in this browser and is not sent anywhere. Plain text out, so the file is its own text equivalent.
import type { LabPart } from "./sandbox";

export interface LabReportData {
  experiment: [string, string][] | null;
  steps: string[] | null;
  table: { caption: string; columns: { label: string; unit: string }[]; rows: string[][] } | null;
}

export const EMPTY_REPORT: LabReportData = { experiment: null, steps: null, table: null };

/** Each part replaces the last of its kind (the table is sent whole every time). */
export function applyLabPart(data: LabReportData, part: LabPart): LabReportData {
  switch (part.part) {
    case "experiment":
      return { ...data, experiment: part.fields };
    case "steps":
      return { ...data, steps: part.steps };
    case "table":
      return { ...data, table: { caption: part.caption, columns: part.columns, rows: part.rows } };
  }
}

/** A report is worth showing once the Environment has told the host anything about a practical. */
export function hasReport(data: LabReportData): boolean {
  return data.experiment !== null || data.steps !== null || (data.table !== null && data.table.columns.length > 0);
}

import { english, type T } from "./i18n";

export interface Writing {
  observations: string;
  discussion: string;
  conclusion: string;
}

export const NO_WRITING: Writing = { observations: "", discussion: "", conclusion: "" };

/** The report as plain text. This is exactly what the panel shows, so a screen reader and a printout see the same thing. */
export function reportText(title: string, data: LabReportData, writing: Writing, t: T = english): string {
  const blank = t("notWritten");
  const out: string[] = [t("labReportHeading", { title }), ""];
  for (const [name, value] of data.experiment ?? []) out.push(`${name}: ${value}`);
  if (data.steps?.length) {
    out.push("", t("procedure"));
    data.steps.forEach((s, i) => out.push(`${i + 1}. ${s}`));
  }
  if (data.table) {
    out.push("", t("resultsCaption", { caption: data.table.caption }));
    const header = data.table.columns.map((c) => `${c.label} (${c.unit})`);
    out.push(header.join(" | "));
    if (data.table.rows.length === 0) out.push(t("noRowsText"));
    for (const row of data.table.rows) out.push(row.join(" | "));
  }
  out.push("", t("observations"), writing.observations.trim() || blank);
  out.push("", t("discussion"), writing.discussion.trim() || blank);
  out.push("", t("conclusion"), writing.conclusion.trim() || blank);
  out.push("", t("reportTextNote"));
  return out.join("\n");
}

export function reportFileName(title: string): string {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);
  return `lab-report-${slug || "environment"}.txt`;
}
