"use client";

// Adapted from Synapse v3: frontend/components/study/StudyRail.tsx (Genui monorepo, commit 835a2cefda28). Kept: the heading, "Today's flow", "Quick starts", and
// the list of what you opened. Changed: the quick starts are real questions from the golden set (the library answers them with no model call); the copy says only
// what V4 does; and "saved labs" are pointers (id and title), reopened through the delivery gate, never stored HTML (D-38). Every target is at least 44 px.
import type { RecentItem } from "../lib/recent";

export const STARTERS = [
  "Why does a spring stretch when I hang a weight on it?",
  "What happens to the current if I raise the resistance in a circuit?",
  "How does the pressure change as a diver goes deeper in water?",
];

export function QuickStarts({ onPrompt, disabled }: { onPrompt: (prompt: string) => void; disabled: boolean }) {
  return (
    <div className="space-y-2">
      {STARTERS.map((prompt) => (
        <button key={prompt} type="button" disabled={disabled} onClick={() => onPrompt(prompt)} className="study-starter w-full text-left disabled:opacity-50">
          {prompt}
        </button>
      ))}
    </div>
  );
}

export function SideRail({
  onPrompt,
  disabled,
  recent,
  onForget,
}: {
  onPrompt: (prompt: string) => void;
  disabled: boolean;
  recent: RecentItem[];
  onForget: (id: string) => void;
}) {
  return (
    <aside aria-label="Study guide" className="hidden border-r-2 border-line px-5 py-7 xl:block">
      <div className="sticky top-0">
        <h1 className="font-display text-[1.7rem] font-semibold leading-tight text-balance">Ask. See it. Try it.</h1>
        <p className="mt-3 text-sm leading-relaxed text-ink-dim">Verified, interactive science for KSSM Form 4 and 5, with its source beside it.</p>

        <section className="study-card mt-8 p-4" aria-label="Today's flow">
          <p className="study-kicker">Today&apos;s flow</p>
          <ol className="mt-4 space-y-4 text-sm">
            <li className="flex gap-3">
              <span className="study-step">1</span>
              <span>
                <b>Ask</b>
                <br />
                <em className="text-[0.8rem] not-italic text-ink-dim">Start with the thing that feels fuzzy.</em>
              </span>
            </li>
            <li className="flex gap-3">
              <span className="study-step">2</span>
              <span>
                <b>See the idea</b>
                <br />
                <em className="text-[0.8rem] not-italic text-ink-dim">A short note, with its textbook source when there is one.</em>
              </span>
            </li>
            <li className="flex gap-3">
              <span className="study-step">3</span>
              <span>
                <b>Try it</b>
                <br />
                <em className="text-[0.8rem] not-italic text-ink-dim">Move a slider and watch the numbers respond.</em>
              </span>
            </li>
          </ol>
        </section>

        <section className="mt-8" aria-label="Quick starts">
          <p className="study-kicker">Quick starts</p>
          <div className="mt-3">
            <QuickStarts onPrompt={onPrompt} disabled={disabled} />
          </div>
        </section>

        {recent.length > 0 ? (
          <section className="mt-8" aria-label="Recently opened">
            <p className="study-kicker">Recently opened</p>
            <ul className="mt-3 space-y-2">
              {recent.map((item) => (
                <li key={item.id} className="study-starter gap-2 !py-0 !pr-1">
                  <a href={`/e/${encodeURIComponent(item.id)}`} className="min-w-0 flex-1 truncate py-3 font-semibold text-ink">
                    {item.title}
                  </a>
                  <button type="button" onClick={() => onForget(item.id)} aria-label={`Remove from this list: ${item.title}`} className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-lg leading-none text-ink-faint hover:text-ink">
                    ×
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-ink-faint">Kept in this browser only.</p>
          </section>
        ) : null}
      </div>
    </aside>
  );
}
