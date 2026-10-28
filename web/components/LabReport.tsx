"use client";

// The lab report (W5b): the Amali card, the steps and the table the student recorded, as the Kit reported them, with three boxes for the student's own words.
// Everything is rendered as text. What the student writes stays in this browser (it is not sent anywhere), and the report can be copied, saved as a text file (which is
// also its text equivalent), or printed or saved as a PDF through the browser's own print dialog: a print stylesheet in globals.css shows only this panel.
import { useState } from "react";
import { useT, type StringKey } from "../lib/i18n";
import { type LabReportData, NO_WRITING, reportFileName, reportText, type Writing } from "../lib/labreport";

const BOXES: { key: keyof Writing; label: StringKey; hint: StringKey }[] = [
  { key: "observations", label: "observations", hint: "observationsHint" },
  { key: "discussion", label: "discussion", hint: "discussionHint" },
  { key: "conclusion", label: "conclusion", hint: "conclusionHint" },
];

export function LabReport({ title, data }: { title: string; data: LabReportData }) {
  const t = useT();
  const [writing, setWriting] = useState<Writing>(NO_WRITING);
  const [note, setNote] = useState("");
  const text = reportText(title, data, writing, t);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setNote(t("reportCopied"));
    } catch {
      setNote(t("reportCopyFailed"));
    }
  }

  function save() {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = reportFileName(title);
    a.click();
    URL.revokeObjectURL(url);
    setNote(t("reportSaved"));
  }

  function print() {
    window.print();
  }

  return (
    <section aria-label={t("labReportAria")} className="study-card grid gap-3 p-4 text-[15px]" data-testid="lab-report">
      <p className="study-kicker">{t("labReportKicker")}</p>
      <h3 className="font-display text-lg font-semibold">{title}</h3>

      {data.experiment ? (
        <dl className="grid gap-1">
          {data.experiment.map(([name, value]) => (
            <div key={name}>
              <dt className="font-semibold">{name}</dt>
              <dd className="text-ink-dim">{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {data.steps?.length ? (
        <div>
          <p className="font-semibold">{t("procedure")}</p>
          <ol className="list-decimal pl-5 text-ink-dim">
            {data.steps.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </div>
      ) : null}

      {data.table ? (
        <div>
          <p className="font-semibold">{t("resultsCaption", { caption: data.table.caption })}</p>
          {data.table.rows.length === 0 ? (
            <p className="text-ink-dim">{t("noRowsYet")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr>
                    {data.table.columns.map((c) => (
                      <th key={c.label} scope="col" className="border-b-2 border-line px-2 py-1">
                        {c.label} ({c.unit})
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.table.rows.map((row, i) => (
                    <tr key={i}>
                      {row.map((cell, j) => (
                        <td key={j} className="border-b border-line px-2 py-1">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}

      {BOXES.map(({ key, label, hint }) => (
        <div key={key} className="grid gap-1">
          <label className="grid gap-1">
            <span className="font-semibold">{t(label)}</span>
            <textarea
              value={writing[key]}
              maxLength={1500}
              rows={3}
              placeholder={t(hint)}
              onChange={(e) => setWriting((w) => ({ ...w, [key]: e.target.value }))}
              className="rounded-card border-2 border-line bg-card p-2 text-[15px] print:hidden"
            />
          </label>
          <p className="hidden whitespace-pre-wrap print:block" data-testid="print-writing">
            {writing[key].trim() || t("notWritten")}
          </p>
        </div>
      ))}

      <div className="flex flex-wrap gap-2 print:hidden">
        <button type="button" onClick={copy} className="btn btn-ghost px-4 text-sm">
          {t("copyReport")}
        </button>
        <button type="button" onClick={save} className="btn btn-ghost px-4 text-sm">
          {t("downloadReport")}
        </button>
        <button type="button" onClick={print} className="btn btn-ghost px-4 text-sm">
          {t("printReport")}
        </button>
      </div>
      <p role="status" aria-live="polite" className="text-sm text-ink-dim print:hidden">
        {note}
      </p>
      <p className="text-sm text-ink-dim">
        {t("reportNote")}
      </p>
    </section>
  );
}
