"use client";

// Stage: the Environment at full viewport, with a back affordance. Escape also closes it. Focus moves to Back on open. It sits above the top bar (z-40).
import type { EnvironmentBlock } from "@synapse/schema";
import { useCallback, useEffect, useRef, useState } from "react";
import { citationText } from "../lib/citation";
import { LangSwitch, useT } from "../lib/i18n";
import { LabLanguageNote, useTranslatedBlock } from "../lib/translation";
import { LabelBadge, LaneBadge } from "./Badges";
import { EnvironmentFrame } from "./EnvironmentFrame";
import { applyLabPart, EMPTY_REPORT, hasReport, type LabReportData } from "../lib/labreport";
import type { LabPart } from "../lib/sandbox";
import { LabReport } from "./LabReport";
import { Provenance } from "./Provenance";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function Stage({ block: original, onBack, startPresenting = false }: { block: EnvironmentBlock; onBack: () => void; startPresenting?: boolean }) {
  const t = useT();
  const { block, state, draft } = useTranslatedBlock(original);
  const back = useRef<HTMLButtonElement>(null);
  const [report, setReport] = useState<LabReportData>(EMPTY_REPORT);
  const onLab = useCallback((part: LabPart) => setReport((r) => applyLabPart(r, part)), []);
  useEffect(() => setReport(EMPTY_REPORT), [block.id]);
  // Present mode (D-39, ASSUMED behaviour): the Environment as large as the screen allows, for projecting to a class. Nothing about the student or a class is kept.
  // The label, the lane and the source stay on screen (hard constraint 11); only the long provenance panel and the lab report are folded away.
  const [presenting, setPresenting] = useState(startPresenting);
  useEffect(() => setPresenting(startPresenting), [block.id, startPresenting]);
  useEffect(() => {
    back.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onBack();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onBack]);
  return (
    <div role="dialog" aria-modal="true" aria-label={block.title} className="fixed inset-0 z-40 grid grid-rows-[auto_1fr] overflow-auto bg-canvas">
      <header className="flex flex-wrap items-center gap-3 border-b-2 border-line bg-canvas p-3">
        <button ref={back} type="button" onClick={onBack} className="btn btn-ghost px-4 text-sm">
          {t("back")}
        </button>
        <h2 className="sr-only">{block.title}</h2>
        <span className="flex flex-wrap gap-2">
          <LabelBadge label={block.label} />
          <LaneBadge lane={block.lane} />
          {presenting ? (
            <span className="study-badge study-badge-checked" role="status">
              {t("presenting")}
            </span>
          ) : null}
        </span>
        <button type="button" onClick={() => setPresenting((p) => !p)} aria-pressed={presenting} className="btn btn-ghost ml-auto px-4 text-sm">
          {presenting ? t("stopPresenting") : t("present")}
        </button>
        <a href={`${API_BASE.replace(/\/$/, "")}/library/${encodeURIComponent(block.id)}/export`} download className="btn btn-ghost px-4 text-sm">
          {t("saveCopy")}
        </a>
        <LangSwitch compact />
      </header>
      <LabLanguageNote state={state} draft={draft} />
      <div className={`mx-auto grid w-full content-start gap-3 p-3 ${presenting ? "max-w-none" : "max-w-4xl"}`}>
        <EnvironmentFrame block={block} height={presenting ? "calc(100dvh - 9rem)" : "70vh"} onLab={onLab} />
        {presenting ? (
          <p className="text-sm text-ink-dim" data-testid="present-source">
            <strong>{t("sourceLabel")}</strong> {block.citations.length === 0 ? t("noneStated") : block.citations.map((c) => citationText(c)).join("; ")}
          </p>
        ) : null}
        {/* Folded away, not unmounted, so what a student has typed in the lab report survives a stop and a start of Present mode. */}
        <div className={presenting ? "hidden" : "grid gap-3"}>
          {hasReport(report) ? <LabReport key={block.id} title={block.title} data={report} /> : null}
          <Provenance block={block} />
        </div>
      </div>
    </div>
  );
}
