"use client";

// The loading skeleton (D-23): once the plan has passed its checks the server streams a draft, and this card is drawn at once from it so the first
// useful paint does not wait for verification. It is a DRAFT. It never renders the plan's HTML (there is none yet) and it is replaced by the
// verified Environment when that arrives, or removed with a plain note when the turn degrades. (This is the only "draft" V4 shows; V3's view of an
// unverified page is not carried over, D-38.)
import type { PlanDraft } from "@synapse/schema";

export function PeekSkeleton({ draft }: { draft: PlanDraft }) {
  return (
    <article aria-label={`${draft.title} (draft)`} aria-busy="true" className="grid gap-3 rounded-frame border-2 border-dashed border-line-2 bg-card p-3">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-lg font-semibold leading-tight">{draft.title}</h2>
        <span className="study-badge">Draft, not yet checked</span>
      </header>
      <p className="text-sm text-ink-dim">{draft.note}</p>
      <div role="status" className="grid min-h-40 gap-2 rounded-card bg-band p-4 text-sm text-ink-dim">
        <span className="font-semibold text-ink">Checking this Environment in a real browser…</span>
        {draft.controls.length > 0 ? <span>Sliders: {draft.controls.map((c) => `${c.label} (${c.unit})`).join(", ")}</span> : null}
        {draft.readouts.length > 0 ? <span>Shows: {draft.readouts.map((r) => `${r.label} (${r.unit})`).join(", ")}</span> : null}
        {draft.hasGraph ? <span>A graph</span> : null}
        {draft.hasTable ? <span>A results table</span> : null}
      </div>
    </article>
  );
}
