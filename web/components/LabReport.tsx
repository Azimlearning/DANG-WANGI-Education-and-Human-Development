"use client";

// The lab report (W5b): the Amali card, the steps and the table the student recorded, as the Kit reported them, with three boxes for the student's own words.
// Everything is rendered as text. What the student writes stays in this browser (it is not sent anywhere), and the report can be copied or saved as a text file,
// which is also its text equivalent.
import { useState } from "react";
import { type LabReportData, NO_WRITING, reportFileName, reportText, type Writing } from "../lib/labreport";

const BOXES: { key: keyof Writing; label: string; hint: string }[] = [
  { key: "observations", label: "Observations", hint: "What did you see happen as you changed it?" },
  { key: "discussion", label: "Discussion", hint: "Why do you think it happened? Did the results match the hypothesis?" },
  { key: "conclusion", label: "Conclusion", hint: "State what the experiment shows, in one or two sentences." },
];

export function LabReport({ title, data }: { title: string; data: LabReportData }) {
  const [writing, setWriting] = useState<Writing>(NO_WRITING);
  const [note, setNote] = useState("");
  const text = reportText(title, data, writing);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setNote("Report copied.");
    } catch {
      setNote("Could not copy. Use Save as a text file instead.");
    }
  }

  function save() {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = reportFileName(title);
    a.click();
    URL.revokeObjectURL(url);
    setNote("Report saved.");
  }

  return (
    <section aria-label="Lab report" className="study-card grid gap-3 p-4 text-[15px]" data-testid="lab-report">
      <p className="study-kicker">Lab report</p>
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
          <p className="font-semibold">Procedure</p>
          <ol className="list-decimal pl-5 text-ink-dim">
            {data.steps.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </div>
      ) : null}

      {data.table ? (
        <div>
          <p className="font-semibold">Results: {data.table.caption}</p>
          {data.table.rows.length === 0 ? (
            <p className="text-ink-dim">No rows yet. Press Record in the model to add a row of your results.</p>
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
        <label key={key} className="grid gap-1">
          <span className="font-semibold">{label}</span>
          <textarea
            value={writing[key]}
            maxLength={1500}
            rows={3}
            placeholder={hint}
            onChange={(e) => setWriting((w) => ({ ...w, [key]: e.target.value }))}
            className="rounded-card border-2 border-line bg-card p-2 text-[15px]"
          />
        </label>
      ))}

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={copy} className="btn btn-ghost px-4 text-sm">
          Copy report
        </button>
        <button type="button" onClick={save} className="btn btn-ghost px-4 text-sm">
          Save as a text file
        </button>
      </div>
      <p role="status" aria-live="polite" className="text-sm text-ink-dim">
        {note}
      </p>
      <p className="text-sm text-ink-dim">
        The experiment, procedure and results come from the model you used. The observations, discussion and conclusion are your own words: they stay in this browser and are not checked.
      </p>
    </section>
  );
}
