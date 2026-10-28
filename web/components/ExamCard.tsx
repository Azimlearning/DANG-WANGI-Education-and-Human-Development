"use client";

// The exam mirror (W5c): a structured question with one mark per point, answered in a text box and marked IN THIS BROWSER by matching key words (lib/exam.ts). The answer
// is never sent anywhere. The card says what keyword marking is, shows each point as earned or missed in words, and then the sample answer. A practice aid, not a grade.
import { useState } from "react";
import type { ExamEvent } from "@synapse/schema";
import { mark } from "../lib/exam";
import { useT } from "../lib/i18n";

export function ExamCard({ item }: { item: ExamEvent }) {
  const t = useT();
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<{ score: number; got: boolean[] } | null>(null);
  const [hidden, setHidden] = useState(false);
  if (hidden) return null;

  return (
    <section aria-label={t("examAria")} className="study-card grid gap-3 p-4" data-testid="exam">
      <div className="flex items-start justify-between gap-3">
        <p className="study-kicker">{t("examKicker", { marks: item.marks })}</p>
        <button type="button" onClick={() => setHidden(true)} className="btn btn-ghost px-3 text-sm" aria-label={t("hideExam")}>
          {t("hide")}
        </button>
      </div>
      <p id={`exam-${item.id}`} className="text-[15px] font-medium leading-relaxed">
        {item.stem}
      </p>
      <label className="grid gap-1">
        <span className="text-sm font-semibold">{t("yourAnswer")}</span>
        <textarea
          aria-describedby={`exam-${item.id}`}
          value={answer}
          maxLength={1200}
          rows={4}
          readOnly={result !== null}
          onChange={(e) => setAnswer(e.target.value)}
          className="rounded-card border-2 border-line bg-card p-2 text-[15px]"
        />
      </label>
      {result === null ? (
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => setResult(mark(item, answer))} disabled={answer.trim() === ""} className="btn btn-primary px-5 text-sm">
            {t("markAnswer")}
          </button>
          <span className="text-sm text-ink-dim">{t("staysHere")}</span>
        </div>
      ) : (
        <div role="status" aria-live="polite" className="grid gap-2 text-[15px] leading-relaxed">
          <p className="font-semibold" data-testid="exam-score">
            {t("marksOf", { score: result.score, marks: item.marks })}
          </p>
          <ul className="grid gap-1">
            {item.points.map((p, i) => (
              <li key={p.text}>
                <strong>{result.got[i] ? t("earned") : t("missed")}:</strong> {p.text}
              </li>
            ))}
          </ul>
          <p>
            <strong>{t("fullMarkAnswer")}</strong> {item.sample}
          </p>
        </div>
      )}
      <p className="text-sm text-ink-dim">
        {t("examNote")}
      </p>
    </section>
  );
}
