"use client";

// Adapted from Synapse v3: frontend/components/artifact/DegradedCard.tsx (Genui monorepo, commit 835a2cefda28). The honest failure state: the written answer stays,
// the interactive admits it was not made, in plain words, with a warn (not danger) left border and no reward. Axi looks sheepish. V4 uses it for a degrade note
// (role=status) and for an error (role=alert), so a screen reader hears each as what it is.
import { Mascot } from "./Mascot";

export function DegradedCard({ message, kind, onRetry }: { message: string; kind: "note" | "error"; onRetry?: () => void }) {
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      data-testid={kind === "note" ? "degraded-note" : undefined}
      className="mt-4 flex gap-3 rounded-card border-2 border-l-[5px] border-line border-l-warn bg-card px-4 py-4"
    >
      <Mascot mood="oops" size={48} bob={false} className="mt-0.5" />
      <div className="min-w-0">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-warn">{kind === "error" ? "Something went wrong" : "Explanation only"}</p>
        <p className="mt-2 text-[15px] leading-relaxed text-ink-dim">{message}</p>
        {onRetry ? (
          <button type="button" onClick={onRetry} className="btn btn-ghost mt-3 px-4 text-sm">
            Try again
          </button>
        ) : null}
      </div>
    </div>
  );
}
