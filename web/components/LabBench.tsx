"use client";

// Adapted from Synapse v3: frontend/components/study/LabPane.tsx (Genui monorepo, commit 835a2cefda28). The lab bench column beside the conversation on a wide
// screen: the Environment (or its draft, or the progress of making it) for the latest question, or Axi waiting. Changed from V3: the header badges are the
// Environment's real label and lane (the schema has no domain or type, D-38), and V3's mobile overlay is not needed (below this width the same card is inline).
// The progress bar stays on screen for the whole of a question (above the draft, until the lab is shown), and a question that ends without a lab says so here
// instead of going back to "ready when you are" (W18).
import { useT } from "../lib/i18n";
import { useServerMode } from "../lib/mode";
import { usePacedStep } from "../lib/pace";
import type { Turn } from "../lib/turns";
import { BuildDetails, BuildLog } from "./BuildLog";
import { DegradedCard } from "./DegradedCard";
import { Mascot } from "./Mascot";
import { LabFrame } from "./LabFrame";
import { PeekSkeleton } from "./PeekSkeleton";
import { ProgressStages } from "./ProgressStages";
import { Stage } from "./Stage";

export function LabBench({
  turn,
  stagedId,
  presentFirst = false,
  onOpen,
  onBack,
}: {
  turn: Turn | null;
  stagedId: string | null;
  presentFirst?: boolean;
  onOpen: (id: string, present?: boolean) => void;
  onBack: () => void;
}) {
  const t = useT();
  const mode = useServerMode();
  const shown = usePacedStep(turn?.step ?? "reading", turn?.id ?? 0);
  // The bar is up while the question is open, and for the few stages a stored lab would otherwise skip past; the lab replaces it when the bar reaches "ready".
  const working = !!turn && (turn.open || (turn.block !== null && shown !== "ready"));
  const lab = turn?.block && !working ? turn.block : null;
  const noLab = !!turn && !turn.open && !turn.block;
  return (
    <aside aria-label={t("labBenchAria")} className="flex min-h-0 flex-col border-l-2 border-line bg-band">
      {/* The bench's own heading only while nothing is on it: once a lab is open, its frame says what it is and the height goes to the lab. */}
      {lab ? (
        <h2 className="sr-only">{t("yourLabBench")}</h2>
      ) : (
        <header className="border-b-2 border-line px-5 py-2">
          <p className="study-kicker">{t("interactiveWorkspace")}</p>
          <h2 className="font-display text-xl font-semibold leading-tight">{t("yourLabBench")}</h2>
        </header>
      )}
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {lab && turn ? (
          stagedId === lab.id ? (
            <Stage block={lab} onBack={onBack} startPresenting={presentFirst} />
          ) : (
            <div className="grid gap-3">
              <LabFrame block={lab} onOpen={(present) => onOpen(lab.id, present)} />
              <BuildDetails block={lab} log={turn.log} />
            </div>
          )
        ) : working && turn ? (
          <div className="grid gap-3">
            <ProgressStages step={shown} />
            <BuildLog log={turn.log} draft={turn.draft} code={turn.code} />
            {turn.draft ? <PeekSkeleton draft={turn.draft} /> : null}
          </div>
        ) : noLab ? (
          <DegradedCard kind="note" title={t("noLabTitle")} message={mode === "fake" ? t("noLabDemo") : (turn?.note ?? t("noLabGeneric"))} />
        ) : (
          <div className="lab-empty flex min-h-[360px] flex-col justify-center p-6">
            <Mascot mood="thinking" size={56} />
            <p className="study-kicker mt-4">{t("readyWhen")}</p>
            <h3 className="mt-3 font-display text-3xl font-semibold leading-tight">
              {t("askAQuestion")}
              <br />
              {t("makeTangible")}
            </h3>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-ink-dim">{t("benchIntro")}</p>
          </div>
        )}
      </div>
    </aside>
  );
}
