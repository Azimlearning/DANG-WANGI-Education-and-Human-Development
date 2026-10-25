"use client";

// The misconception probe (W5a): one optional question about an idea the student's question touched. It is plain text from the server, rendered as text (React
// escapes it), never a page, so it cannot hold an unverified Environment. The matcher that offered it is a topic detector, so the card asks about an idea and never
// says what the student thinks. Only the first answer counts; the correction and what it rests on appear after it. Every verdict is in words, not colour alone.
import { useState } from "react";
import type { ProbeEvent } from "@synapse/schema";

export function ProbeCard({ probe }: { probe: ProbeEvent }) {
  const [chosen, setChosen] = useState<number | null>(null);
  const [hidden, setHidden] = useState(false);
  if (hidden) return null;
  const answered = chosen !== null;
  const right = chosen === probe.correct;

  return (
    <section aria-label="Quick check" className="study-card grid gap-3 p-4" data-testid="probe">
      <div className="flex items-start justify-between gap-3">
        <p className="study-kicker">Quick check (optional)</p>
        <button type="button" onClick={() => setHidden(true)} className="btn btn-ghost px-3 text-sm" aria-label="Hide this quick check">
          Hide
        </button>
      </div>
      <p id={`probe-${probe.id}`} className="text-[15px] font-medium leading-relaxed">
        {probe.question}
      </p>
      <ul aria-labelledby={`probe-${probe.id}`} className="grid gap-2">
        {probe.options.map((option, i) => {
          const isChosen = chosen === i;
          const isCorrect = answered && i === probe.correct;
          return (
            <li key={option}>
              <button
                type="button"
                disabled={answered}
                aria-pressed={isChosen}
                onClick={() => setChosen((c) => c ?? i)}
                className={`btn btn-ghost w-full justify-start px-4 py-2 text-left text-[15px] font-normal ${isCorrect ? "border-2 border-verify" : isChosen ? "border-2 border-warn" : ""}`}
              >
                <span>
                  {option}
                  {answered && isChosen ? <span className="sr-only"> (your answer)</span> : null}
                  {isCorrect ? <span className="font-semibold"> (correct answer)</span> : null}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <div role="status" aria-live="polite" className="grid gap-2 text-[15px] leading-relaxed">
        {answered ? (
          <>
            <p className="font-semibold">{right ? "Yes, that is right." : "Not quite. Here is the idea."}</p>
            <p>{probe.explanation}</p>
            <p className="text-sm text-ink-dim">
              <strong>What this rests on:</strong> {probe.basis}
            </p>
          </>
        ) : null}
      </div>
    </section>
  );
}
