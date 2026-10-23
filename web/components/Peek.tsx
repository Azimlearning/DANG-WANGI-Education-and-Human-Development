"use client";

// Peek: a compact card in the conversation, shown as V3's "lab bench" card. At most TWO actions (Open, and Copy link). The live Environment is shown at a small
// height so a student can try the control without leaving the chat; on a wide screen the same card sits in the lab bench column at a taller height.
import type { EnvironmentBlock } from "@synapse/schema";
import { LabelBadge, LaneBadge } from "./Badges";
import { EnvironmentFrame } from "./EnvironmentFrame";
import { Provenance } from "./Provenance";
import { ShareButton } from "./ShareButton";

export const MAX_PEEK_ACTIONS = 2;

export function Peek({ block, onOpen, frameHeight = 360 }: { block: EnvironmentBlock; onOpen: () => void; frameHeight?: number }) {
  return (
    <article aria-label={block.title} className="grid gap-3 rounded-frame border-2 border-line bg-card p-3 shadow-frame">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-lg font-semibold leading-tight">{block.title}</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            <LabelBadge label={block.label} />
            <LaneBadge lane={block.lane} />
          </div>
        </div>
        <button type="button" onClick={onOpen} className="btn btn-primary px-5 text-sm">
          Open
        </button>
      </header>
      <ShareButton id={block.id} />
      <EnvironmentFrame block={block} height={frameHeight} />
      <Provenance block={block} />
    </article>
  );
}
