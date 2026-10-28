"use client";

// The lab in the lab pane, built to V3's lab frame and the demo video: ONE bordered frame (soft green and chunky when the label is Kit verified), one header row
// with the label and lane badges and a compact tool group (Present, Share, Save offline, Full screen), then the Environment filling the pane, then the provenance.
// The title is not repeated here: the Environment page shows it once (the Kit's own heading), and this frame is named for screen readers instead.
// Peek stays the inline card for a narrow screen and keeps its two-action limit; this is the wide-screen frame.
import type { EnvironmentBlock } from "@synapse/schema";
import { useT } from "../lib/i18n";
import { LabLanguageNote, useTranslatedBlock } from "../lib/translation";
import { LabelBadge, LaneBadge } from "./Badges";
import { EnvironmentFrame } from "./EnvironmentFrame";
import { DemoLabNote } from "./DemoLabNote";
import { Provenance } from "./Provenance";
import { ShareButton } from "./ShareButton";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function LabFrame({ block: original, onOpen }: { block: EnvironmentBlock; onOpen: (present: boolean) => void }) {
  const t = useT();
  const { block, state, draft } = useTranslatedBlock(original);
  const verified = block.label === "kit-verified" || block.label === "reviewed" || block.label === "canonical";
  return (
    <article
      aria-label={block.title}
      className={`overflow-hidden rounded-frame border-2 bg-card ${verified ? "border-verify shadow-[0_5px_0_var(--verify-edge)]" : "border-line-2 shadow-[0_5px_0_var(--line-2)]"}`}
    >
      <header className="flex flex-wrap items-center gap-2 border-b-2 border-line px-3 py-1.5">
        <h2 className="sr-only">{block.title}</h2>
        <LabelBadge label={block.label} />
        <LaneBadge lane={block.lane} />
        <span className="ml-auto flex flex-wrap items-center gap-2" role="group" aria-label={t("labTools")}>
          <button type="button" onClick={() => onOpen(true)} className="btn btn-ghost px-3 text-sm">
            {t("present")}
          </button>
          <ShareButton id={block.id} label={t("share")} />
          <a href={`${API_BASE.replace(/\/$/, "")}/library/${encodeURIComponent(block.id)}/export`} download className="btn btn-ghost px-3 text-sm">
            {t("saveOffline")}
          </a>
          <button type="button" onClick={() => onOpen(false)} className="btn btn-ghost px-3 text-sm">
            {t("fullScreen")}
          </button>
        </span>
      </header>
      <DemoLabNote lane={block.lane} />
      <LabLanguageNote state={state} draft={draft} />
      <EnvironmentFrame block={block} height="max(560px, calc(100dvh - 11rem))" />
      <Provenance block={block} plain />
    </article>
  );
}
