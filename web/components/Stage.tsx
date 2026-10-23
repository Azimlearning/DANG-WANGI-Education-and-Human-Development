"use client";

// Stage: the Environment at full viewport, with a back affordance. Escape also closes it. Focus moves to Back on open. It sits above the top bar (z-40).
import type { EnvironmentBlock } from "@synapse/schema";
import { useEffect, useRef } from "react";
import { LabelBadge, LaneBadge } from "./Badges";
import { EnvironmentFrame } from "./EnvironmentFrame";
import { Provenance } from "./Provenance";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function Stage({ block, onBack }: { block: EnvironmentBlock; onBack: () => void }) {
  const back = useRef<HTMLButtonElement>(null);
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
          Back
        </button>
        <h2 className="font-display text-lg font-semibold">{block.title}</h2>
        <span className="flex flex-wrap gap-2">
          <LabelBadge label={block.label} />
          <LaneBadge lane={block.lane} />
        </span>
        <a href={`${API_BASE.replace(/\/$/, "")}/library/${encodeURIComponent(block.id)}/export`} download className="btn btn-ghost ml-auto px-4 text-sm">
          Save a copy to use offline
        </a>
      </header>
      <div className="mx-auto grid w-full max-w-4xl content-start gap-3 p-3">
        <EnvironmentFrame block={block} height="70vh" />
        <Provenance block={block} />
      </div>
    </div>
  );
}
