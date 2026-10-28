"use client";

// Peek: a compact card in the conversation, shown as V3's "lab bench" card. At most TWO actions (Open, and Copy link). The live Environment is shown at a small
// height so a student can try the control without leaving the chat; on a wide screen the same card sits in the lab bench column at a taller height.
import type { EnvironmentBlock } from "@synapse/schema";
import { useT } from "../lib/i18n";
import { LabLanguageNote, useTranslatedBlock } from "../lib/translation";
import { LabelBadge, LaneBadge } from "./Badges";
import { EnvironmentFrame } from "./EnvironmentFrame";
import { DemoLabNote } from "./DemoLabNote";
import { Provenance } from "./Provenance";
import { ShareButton } from "./ShareButton";

export const MAX_PEEK_ACTIONS = 2;

// On a phone the lab's header (title, key idea, the prediction, the steps) is long, so the frame takes most of the screen height: a 360 px frame showed the header and none
// of the bench.
export function Peek({ block: original, onOpen, frameHeight = "min(75dvh, 640px)" }: { block: EnvironmentBlock; onOpen: () => void; frameHeight?: number | string }) {
  const t = useT();
  const { block, state, draft } = useTranslatedBlock(original);
  return (
    <article aria-label={block.title} className="grid gap-3 rounded-frame border-2 border-line bg-card p-3 shadow-frame">
      <header className="flex flex-wrap items-center gap-2">
        <h2 className="sr-only">{block.title}</h2>
        <LabelBadge label={block.label} />
        <LaneBadge lane={block.lane} />
        <span className="ml-auto flex flex-wrap items-center gap-2">
          <ShareButton id={block.id} />
          <button type="button" onClick={onOpen} className="btn btn-primary px-5 text-sm">
            {t("open")}
          </button>
        </span>
      </header>
      <DemoLabNote lane={block.lane} />
      <LabLanguageNote state={state} draft={draft} />
      <EnvironmentFrame block={block} height={frameHeight} />
      <Provenance block={block} />
    </article>
  );
}
