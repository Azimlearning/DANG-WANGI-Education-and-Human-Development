"use client";

// The loading skeleton (D-23): once the plan has passed its checks the server streams a draft, and this card is drawn at once from it so the first
// useful paint does not wait for verification. It is a DRAFT. It never renders the plan's HTML (there is none yet) and it is replaced by the
// verified Environment when that arrives, or removed with a plain note when the turn degrades.
import type { PlanDraft } from "@synapse/schema";

export function PeekSkeleton({ draft }: { draft: PlanDraft }) {
  return (
    <article aria-label={`${draft.title} (draft)`} aria-busy="true" className="grid gap-3 rounded-2xl p-3" style={{ border: "1px dashed var(--border)" }}>
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold">{draft.title}</h2>
        <span className="rounded-full px-2 py-1 text-xs" style={{ background: "var(--card)", color: "var(--muted)" }}>
          Draft, not yet checked
        </span>
      </header>
      <p className="text-sm" style={{ color: "var(--muted)" }}>
        {draft.note}
      </p>
      <div role="status" className="grid gap-2 rounded-xl p-3 text-sm" style={{ background: "var(--card)", color: "var(--muted)", minHeight: 160 }}>
        <span>Checking this Environment in a real browser…</span>
        {draft.controls.length > 0 ? <span>Sliders: {draft.controls.map((c) => `${c.label} (${c.unit})`).join(", ")}</span> : null}
        {draft.readouts.length > 0 ? <span>Shows: {draft.readouts.map((r) => `${r.label} (${r.unit})`).join(", ")}</span> : null}
        {draft.hasGraph ? <span>A graph</span> : null}
        {draft.hasTable ? <span>A results table</span> : null}
      </div>
    </article>
  );
}
