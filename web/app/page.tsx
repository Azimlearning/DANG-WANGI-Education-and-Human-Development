"use client";

import type { EnvironmentBlock, ErrorEnvelope } from "@synapse/schema";
import { useCallback, useRef, useState } from "react";
import { Peek } from "../components/Peek";
import { Stage } from "../components/Stage";
import { AskError, streamAsk } from "../lib/stream";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [text, setText] = useState("");
  const [block, setBlock] = useState<EnvironmentBlock | null>(null);
  const [error, setError] = useState<ErrorEnvelope | string | null>(null);
  const [busy, setBusy] = useState(false);
  const [staged, setStaged] = useState(false);
  const abort = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const q = question.trim();
      if (!q || busy) return;
      abort.current?.abort();
      abort.current = new AbortController();
      setBusy(true);
      setText("");
      setBlock(null);
      setError(null);
      setStaged(false);
      try {
        for await (const event of streamAsk(q, { baseUrl: API_BASE, signal: abort.current.signal })) {
          if (event.type === "text_delta") setText((t) => t + event.text);
          else if (event.type === "environment") setBlock(event.block);
          else if (event.type === "error") setError(event.error);
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") setError(err instanceof AskError ? (err.envelope ?? err.message) : "Could not reach the server.");
      } finally {
        setBusy(false);
      }
    },
    [question, busy],
  );

  return (
    <main className="mx-auto grid max-w-2xl gap-4 p-4">
      <h1 className="text-xl font-semibold">Synapse</h1>
      <form onSubmit={ask} className="grid gap-2">
        <label htmlFor="q" className="font-semibold">
          Ask a science question
        </label>
        <input
          id="q"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={500}
          autoComplete="off"
          className="min-h-11 rounded-xl px-3"
          style={{ border: "1px solid var(--border)", background: "var(--bg)", color: "var(--fg)" }}
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="min-h-11 rounded-xl px-4 font-semibold disabled:opacity-50"
          style={{ background: "var(--accent)", color: "var(--bg)" }}
        >
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>

      <div aria-live="polite" data-testid="answer">
        {text ? <p>{text}</p> : null}
      </div>

      {error ? (
        <p role="alert" className="rounded-xl p-4 text-sm" style={{ background: "var(--warn-bg)", color: "var(--warn-fg)" }}>
          {typeof error === "string" ? error : error.message}
          {typeof error !== "string" && error.issues.length > 0 ? ` (${error.issues.map((i) => `${i.path}: ${i.message}`).join("; ")})` : ""}
        </p>
      ) : null}

      {block && !staged ? <Peek block={block} onOpen={() => setStaged(true)} /> : null}
      {block && staged ? <Stage block={block} onBack={() => setStaged(false)} /> : null}
    </main>
  );
}
