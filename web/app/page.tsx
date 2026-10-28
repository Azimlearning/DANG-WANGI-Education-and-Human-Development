"use client";

// The page. Layout adapted from Synapse v3: frontend/app/page.tsx (Genui monorepo, commit 835a2cefda28): a top bar, a study rail, the conversation, and a lab bench
// column that appears once a question is asked. Rewritten for V4's events, with one frame mounted at a time, and nothing here ever holds an unverified page.
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { Composer } from "../components/Composer";
import { LabBench } from "../components/LabBench";
import { Mascot } from "../components/Mascot";
import { MessageList } from "../components/MessageList";
import { QuickStarts, SideRail } from "../components/SideRail";
import { TopBar } from "../components/TopBar";
import { useT } from "../lib/i18n";
import { addRecent, loadRecent, removeRecent, type RecentItem } from "../lib/recent";
import { useMediaQuery, WIDE_QUERY } from "../lib/media";
import { AskError, streamAsk } from "../lib/stream";
import { turnReducer } from "../lib/turns";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const t = useT();
  const [turns, dispatch] = useReducer(turnReducer, []);
  const [stagedId, setStagedId] = useState<string | null>(null);
  const [presentFirst, setPresentFirst] = useState(false);
  const [recent, setRecent] = useState<RecentItem[]>([]);
  const abort = useRef<AbortController | null>(null);
  const wide = useMediaQuery(WIDE_QUERY);

  useEffect(() => setRecent(loadRecent()), []);

  const last = turns[turns.length - 1] ?? null;
  const busy = last?.open ?? false;
  const started = turns.length > 0;

  const ask = useCallback(async (question: string) => {
    abort.current?.abort();
    abort.current = new AbortController();
    setStagedId(null);
    setPresentFirst(false);
    dispatch({ type: "ask", question });
    try {
      for await (const event of streamAsk(question, { baseUrl: API_BASE, signal: abort.current.signal })) {
        dispatch({ type: "event", event });
        if (event.type === "environment") setRecent(addRecent({ id: event.block.id, title: event.block.title }));
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") dispatch({ type: "fail", error: err instanceof AskError ? (err.envelope ?? err.message) : t("serverUnreachable") });
    } finally {
      dispatch({ type: "close" });
    }
  }, [t]);

  const send = useCallback(
    (question: string) => {
      if (busy) return;
      void ask(question);
    },
    [ask, busy],
  );

  const open = useCallback((id: string, present = false) => {
    setPresentFirst(present);
    setStagedId(id);
  }, []);
  const back = useCallback(() => {
    setStagedId(null);
    setPresentFirst(false);
  }, []);
  // The lab takeover (V3's page.tsx and the demo video): once a question is asked on a wide screen the rail folds away, the conversation narrows to a fifth and
  // the lab bench takes the rest.
  const takeover = started && wide;

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <TopBar />
      <main className={`grid min-h-0 flex-1 overflow-x-hidden ${takeover ? "xl:grid-cols-[0px_minmax(300px,1fr)_4fr]" : "xl:grid-cols-[272px_1fr]"}`}>
        <div className="hidden min-h-0 overflow-y-auto xl:block">
          {takeover ? null : <SideRail onPrompt={send} disabled={busy} recent={recent} onForget={(id) => setRecent(removeRecent(id))} />}
        </div>

        <section className="flex min-h-0 min-w-0 flex-col px-4 sm:px-6">
          {started ? (
            <MessageList turns={turns} wide={wide} stagedId={stagedId} onOpen={open} onBack={back} onRetry={send} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-6 overflow-y-auto py-8">
              <div className="max-w-md text-center">
                <Mascot mood="happy" size={72} className="mx-auto" />
                <p className="study-kicker mt-4">{t("openNotebook")}</p>
                <h2 className="mt-3 font-display text-3xl font-semibold leading-tight">{t("whatUnderstand")}</h2>
                <p className="mt-3 leading-relaxed text-ink-dim">{t("emptyIntro")}</p>
              </div>
              <div className="w-full max-w-md xl:hidden">
                <p className="study-kicker mb-2">{t("quickStarts")}</p>
                <QuickStarts onPrompt={send} disabled={busy} />
              </div>
            </div>
          )}
          <div className="grid min-w-0 gap-2 border-t-2 border-line pb-3 pt-2">
            <Composer onSend={send} disabled={busy} variant={started ? "bar" : "hero"} />
          </div>
        </section>

        {takeover ? <LabBench turn={last} stagedId={stagedId} presentFirst={presentFirst} onOpen={open} onBack={back} /> : null}
      </main>
    </div>
  );
}
