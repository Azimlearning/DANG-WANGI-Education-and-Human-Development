"use client";

// Stage: the Environment at full viewport, with a back affordance. Escape also closes it. Focus moves to Back on open.
import type { EnvironmentBlock } from "@synapse/schema";
import { useEffect, useRef } from "react";
import { EnvironmentFrame } from "./EnvironmentFrame";
import { Provenance } from "./Provenance";

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
    <div role="dialog" aria-modal="true" aria-label={block.title} className="fixed inset-0 z-10 grid grid-rows-[auto_1fr] overflow-auto" style={{ background: "var(--bg)" }}>
      <header className="flex items-center gap-3 p-3">
        <button
          ref={back}
          type="button"
          onClick={onBack}
          className="min-h-11 min-w-11 rounded-xl px-4 text-sm font-semibold"
          style={{ border: "1px solid var(--border)" }}
        >
          Back
        </button>
        <h2 className="text-base font-semibold">{block.title}</h2>
      </header>
      <div className="grid content-start gap-3 p-3">
        <EnvironmentFrame block={block} height="70vh" />
        <Provenance block={block} />
      </div>
    </div>
  );
}
