"use client";

// Adapted from Synapse v3: frontend/components/study/StudyRail.tsx (Genui monorepo, commit 835a2cefda28). Kept: the heading, "Today's flow", "Quick starts", and
// the list of what you opened. Changed: the quick starts are real questions from the golden set (the library answers them with no model call); the copy says only
// what V4 does; and "saved labs" are pointers (id and title), reopened through the delivery gate, never stored HTML (D-38). Every target is at least 44 px.
import { useLang } from "../lib/i18n";
import type { RecentItem } from "../lib/recent";

export const STARTERS = [
  "Why does a spring stretch when I hang a weight on it?",
  "What happens to the current if I raise the resistance in a circuit?",
  "How does the pressure change as a diver goes deeper in water?",
  "How do I find the concentration of an acid by titration?",
  "Why does yeast make limewater go milky?",
  "What is Newton's cannonball, and how does a satellite stay in orbit?",
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
  const { t, lang } = useLang();
  return (
    <aside aria-label={t("studyGuide")} className="hidden border-r-2 border-line px-5 py-7 xl:block">
      <div className="sticky top-0">
        <h1 className="font-display text-[1.7rem] font-semibold leading-tight text-balance">{t("railTitle")}</h1>
        <p className="mt-3 text-sm leading-relaxed text-ink-dim">{t("railIntro")}</p>

        <section className="study-card mt-8 p-4" aria-label={t("todaysFlow")}>
          <p className="study-kicker">{t("todaysFlow")}</p>
          <ol className="mt-4 space-y-4 text-sm">
            <li className="flex gap-3">
              <span className="study-step">1</span>
              <span>
                <b>{t("flowAsk")}</b>
                <br />
                <em className="text-[0.8rem] not-italic text-ink-dim">{t("flowAskHint")}</em>
              </span>
            </li>
            <li className="flex gap-3">
              <span className="study-step">2</span>
              <span>
                <b>{t("flowSee")}</b>
                <br />
                <em className="text-[0.8rem] not-italic text-ink-dim">{t("flowSeeHint")}</em>
              </span>
            </li>
            <li className="flex gap-3">
              <span className="study-step">3</span>
              <span>
                <b>{t("flowTry")}</b>
                <br />
                <em className="text-[0.8rem] not-italic text-ink-dim">{t("flowTryHint")}</em>
              </span>
            </li>
          </ol>
        </section>

        <section className="mt-8" aria-label={t("quickStarts")}>
          <p className="study-kicker">{t("quickStarts")}</p>
          <div className="mt-3">
            <QuickStarts onPrompt={onPrompt} disabled={disabled} />
          </div>
          {lang === "ms" ? <p className="mt-2 text-xs text-ink-faint">{t("questionsEnglish")}</p> : null}
        </section>

        {recent.length > 0 ? (
          <section className="mt-8" aria-label={t("recentlyOpened")}>
            <p className="study-kicker">{t("recentlyOpened")}</p>
            <ul className="mt-3 space-y-2">
              {recent.map((item) => (
                <li key={item.id} className="study-starter gap-2 !py-0 !pr-1">
                  <a href={`/e/${encodeURIComponent(item.id)}`} className="min-w-0 flex-1 truncate py-3 font-semibold text-ink">
                    {item.title}
                  </a>
                  <button type="button" onClick={() => onForget(item.id)} aria-label={t("removeFromList", { title: item.title })} className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-lg leading-none text-ink-faint hover:text-ink">
                    ×
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-ink-faint">{t("keptHere")}</p>
          </section>
        ) : null}
      </div>
    </aside>
  );
}
