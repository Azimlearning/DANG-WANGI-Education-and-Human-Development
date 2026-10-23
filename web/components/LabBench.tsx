"use client";

// Adapted from Synapse v3: frontend/components/study/LabPane.tsx (Genui monorepo, commit 835a2cefda28). The lab bench column beside the conversation on a wide
// screen: the Environment (or its draft, or the progress of making it) for the latest question, or Axi waiting. Changed from V3: the header badges are the
// Environment's real label and lane (the schema has no domain or type, D-38), and V3's mobile overlay is not needed (below this width the same card is inline).
import type { Turn } from "../lib/turns";
import { Mascot } from "./Mascot";
import { Peek } from "./Peek";
import { PeekSkeleton } from "./PeekSkeleton";
import { ProgressStages } from "./ProgressStages";
import { Stage } from "./Stage";

export function LabBench({ turn, stagedId, onOpen, onBack }: { turn: Turn | null; stagedId: string | null; onOpen: (id: string) => void; onBack: () => void }) {
  return (
    <aside aria-label="Lab bench" className="flex min-h-0 flex-col border-l-2 border-line bg-band">
      <header className="border-b-2 border-line px-5 py-4">
        <p className="study-kicker">Interactive workspace</p>
        <h2 className="mt-1 font-display text-xl font-semibold">Your lab bench</h2>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {turn?.block ? (
          stagedId === turn.block.id ? (
            <Stage block={turn.block} onBack={onBack} />
          ) : (
            <Peek block={turn.block} onOpen={() => onOpen(turn.block!.id)} frameHeight={520} />
          )
        ) : turn?.draft ? (
          <PeekSkeleton draft={turn.draft} />
        ) : turn?.open ? (
          <ProgressStages step={turn.step} />
        ) : (
          <div className="lab-empty flex min-h-[360px] flex-col justify-center p-6">
            <Mascot mood="thinking" size={56} />
            <p className="study-kicker mt-4">Ready when you are</p>
            <h3 className="mt-3 font-display text-3xl font-semibold leading-tight">
              Ask a question.
              <br />
              Make it tangible.
            </h3>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-ink-dim">Interactive models open here, with the source and what was checked beside them.</p>
          </div>
        )}
      </div>
    </aside>
  );
}
