"use client";

// Peek: a compact card in the conversation. At most TWO actions (Open, and nothing else yet). The live Environment is shown at a
// small height so a student can try the control without leaving the chat.
import type { EnvironmentBlock } from "@synapse/schema";
import { EnvironmentFrame } from "./EnvironmentFrame";
import { Provenance } from "./Provenance";

export const MAX_PEEK_ACTIONS = 2;

export function Peek({ block, onOpen }: { block: EnvironmentBlock; onOpen: () => void }) {
  return (
    <article aria-label={block.title} className="grid gap-3 rounded-2xl p-3" style={{ border: "1px solid var(--border)" }}>
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold">{block.title}</h2>
        <button
          type="button"
          onClick={onOpen}
          className="min-h-11 min-w-11 rounded-xl px-4 text-sm font-semibold"
          style={{ background: "var(--accent)", color: "var(--bg)" }}
        >
          Open
        </button>
      </header>
      <EnvironmentFrame block={block} height={360} />
      <Provenance block={block} />
    </article>
  );
}
