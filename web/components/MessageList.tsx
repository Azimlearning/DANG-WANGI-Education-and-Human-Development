"use client";

// Adapted from Synapse v3: frontend/components/chat/MessageList.tsx and StreamRenderer.tsx (Genui monorepo, commit 835a2cefda28). Kept: the question bubble, the
// teal-ruled response, the streaming caret. Changed: a turn is V4's (lib/turns.ts), the Environment is a Peek card shown inline (or a lab bench column on a wide
// screen, see LabBench), and the progress card shows the real pipeline layers.
import { useEffect, useRef } from "react";
import type { Turn } from "../lib/turns";
import { DegradedCard } from "./DegradedCard";
import { Peek } from "./Peek";
import { PeekSkeleton } from "./PeekSkeleton";
import { ProgressStages } from "./ProgressStages";
import { Stage } from "./Stage";

export function MessageList({
  turns,
  wide,
  stagedId,
  onOpen,
  onBack,
  onRetry,
}: {
  turns: Turn[];
  /** On a wide screen the Environment, the draft and the progress live in the lab bench column, so they are not repeated here. */
  wide: boolean;
  stagedId: string | null;
  onOpen: (id: string) => void;
  onBack: () => void;
  onRetry: (question: string) => void;
}) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: "end" });
  }, [turns]);

  return (
    <div className="flex-1 space-y-6 overflow-y-auto py-6">
      {turns.map((turn) => (
        <div key={turn.id} className="space-y-4">
          <div className="flex justify-end">
            <div className="max-w-[85%] rounded-card border-2 border-line bg-card px-4 py-2.5 text-[15px] font-medium text-ink shadow-[0_3px_0_var(--line-2)]">{turn.question}</div>
          </div>
          <div className="study-response grid gap-3">
            {!wide && turn.open && !turn.block ? <ProgressStages step={turn.step} /> : null}
            <p className="study-kicker">{turn.fromLibrary ? "From the library" : "Quick study note"}</p>
            <div data-testid="answer" aria-live="polite" className={`text-[15px] leading-7 whitespace-pre-wrap ${turn.open && !turn.block ? "caret" : ""}`}>
              {turn.text}
            </div>
            {turn.note ? <DegradedCard kind="note" message={turn.note} /> : null}
            {turn.error ? (
              <DegradedCard
                kind="error"
                message={
                  typeof turn.error === "string"
                    ? turn.error
                    : `${turn.error.message}${turn.error.issues.length > 0 ? ` (${turn.error.issues.map((i) => `${i.path}: ${i.message}`).join("; ")})` : ""}`
                }
                onRetry={typeof turn.error === "string" || turn.error.retryable ? () => onRetry(turn.question) : undefined}
              />
            ) : null}
            {!wide && turn.draft && !turn.block ? <PeekSkeleton draft={turn.draft} /> : null}
            {!wide && turn.block ? (
              stagedId === turn.block.id ? <Stage block={turn.block} onBack={onBack} /> : <Peek block={turn.block} onOpen={() => onOpen(turn.block!.id)} />
            ) : null}
          </div>
        </div>
      ))}
      <div ref={bottom} />
    </div>
  );
}
