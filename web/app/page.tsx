"use client";

// The page. Layout adapted from Synapse v3: frontend/app/page.tsx (Genui monorepo, commit 835a2cefda28): a top bar, a study rail, the conversation, and a lab bench
// column that appears once a question is asked. Rewritten for V4's events, with one frame mounted at a time, and nothing here ever holds an unverified page.
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { Composer } from "../components/Composer";
import { LabBench } from "../components/LabBench";
import { Mascot } from "../components/Mascot";
import { MessageList } from "../components/MessageList";
import { ProgressPanel } from "../components/ProgressPanel";
import { QuickStarts, SideRail } from "../components/SideRail";
import { TopBar } from "../components/TopBar";
import { addRecent, loadRecent, removeRecent, type RecentItem } from "../lib/recent";
import { useMediaQuery, WIDE_QUERY } from "../lib/media";
import { AskError, streamAsk } from "../lib/stream";
import { turnReducer } from "../lib/turns";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [turns, dispatch] = useReducer(turnReducer, []);
  const [stagedId, setStagedId] = useState<string | null>(null);
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
    dispatch({ type: "ask", question });
    try {
      for await (const event of streamAsk(question, { baseUrl: API_BASE, signal: abort.current.signal })) {
        dispatch({ type: "event", event });
        if (event.type === "environment") setRecent(addRecent({ id: event.block.id, title: event.block.title }));
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") dispatch({ type: "fail", error: err instanceof AskError ? (err.envelope ?? err.message) : "Could not reach the server." });
    } finally {
      dispatch({ type: "close" });
    }
  }, []);

  const send = useCallback(
    (question: string) => {
      if (busy) return;
      void ask(question);
    },
    [ask, busy],
  );

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <TopBar />
      <main className={`grid min-h-0 flex-1 overflow-x-hidden ${started ? "xl:grid-cols-[272px_minmax(420px,0.9fr)_minmax(460px,1.1fr)]" : "xl:grid-cols-[272px_1fr]"}`}>
        <div className="hidden min-h-0 overflow-y-auto xl:block">
          <SideRail onPrompt={send} disabled={busy} recent={recent} onForget={(id) => setRecent(removeRecent(id))} />
        </div>

        <section className="flex min-h-0 min-w-0 flex-col px-4 sm:px-6">
          {started ? (
            <MessageList turns={turns} wide={wide} stagedId={stagedId} onOpen={setStagedId} onBack={() => setStagedId(null)} onRetry={send} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-6 overflow-y-auto py-8">
              <div className="max-w-md text-center">
                <Mascot mood="happy" size={72} className="mx-auto" />
                <p className="study-kicker mt-4">Open notebook</p>
                <h2 className="mt-3 font-display text-3xl font-semibold leading-tight">What are you trying to understand?</h2>
                <p className="mt-3 leading-relaxed text-ink-dim">Ask one clear science question. You get a short note and, when there is one, an interactive model with its source and what was checked.</p>
              </div>
              <div className="w-full max-w-md xl:hidden">
                <p className="study-kicker mb-2">Quick starts</p>
                <QuickStarts onPrompt={send} disabled={busy} />
              </div>
            </div>
          )}
          <div className="grid gap-2 border-t-2 border-line pb-3 pt-2">
            <Composer onSend={send} disabled={busy} variant={started ? "bar" : "hero"} />
            <ProgressPanel />
          </div>
        </section>

        {started && wide ? <LabBench turn={last} stagedId={stagedId} onOpen={setStagedId} onBack={() => setStagedId(null)} /> : null}
      </main>
    </div>
  );
}
