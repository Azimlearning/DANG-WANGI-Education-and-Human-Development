"use client";

// Adapted from Synapse v3: frontend/components/artifact/ProgressStages.tsx (Genui monorepo, commit 835a2cefda28). Kept: the filling bar, the stages that check off
// teal into green, the "working / done / next" tags. Changed: the steps are V4's real pipeline layers (lib/turns.ts), and V3's "Watch the code being written" is NOT
// carried over: it streamed unverified HTML to the student, which hard constraint 1 forbids (D-38). What can be shown early is the plan's draft (PeekSkeleton).
import { STEPS, type StepKey } from "../lib/turns";

const Check = () => (
  <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden>
    <path d="M2.5 6.2l2.2 2.2L9.5 3.6" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export function ProgressStages({ step }: { step: StepKey }) {
  const active = STEPS.findIndex((s) => s.key === step);
  const percent = Math.round(((active + 1) / STEPS.length) * 100);
  const current = STEPS[active]?.label ?? "Getting started";
  return (
    <div className="w-full rounded-card border-2 border-line bg-canvas px-4 pb-3 pt-1" role="status" aria-live="polite" aria-label="Progress">
      <div className="flex items-center justify-between py-3">
        <span className="font-display text-sm font-semibold text-ink">{current}</span>
        <span className="rounded-full bg-primary-soft px-2.5 py-1 font-display text-[13px] font-semibold text-primary-ink">
          {active + 1} of {STEPS.length}
        </span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-line-2" aria-hidden>
        <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${percent}%` }} />
      </div>
      <ol className="mt-3 space-y-0.5">
        {STEPS.map((s, i) => {
          const state = i < active ? "done" : i === active ? "active" : "pending";
          return (
            <li key={s.key} className="grid grid-cols-[24px_1fr_auto] items-center gap-3 py-1.5">
              <span
                aria-hidden
                className={`grid h-[22px] w-[22px] place-items-center rounded-full ${
                  state === "done" ? "bg-verify shadow-[0_2px_0_var(--verify-edge)]" : state === "active" ? "border-[3px] border-primary bg-card" : "border-[3px] border-line-2 bg-card"
                }`}
              >
                {state === "done" ? <Check /> : state === "active" ? <span className="node-pulse h-[7px] w-[7px] rounded-full bg-primary" /> : null}
              </span>
              <span className={`text-[14.5px] font-semibold ${state === "done" ? "text-ink-dim" : state === "active" ? "text-ink" : "text-ink-faint"}`}>{s.label}</span>
              <span className={`font-mono text-[10px] uppercase tracking-[0.06em] ${state === "done" ? "text-verify-ink" : state === "active" ? "text-primary-ink" : "text-ink-faint"}`}>
                {state === "done" ? "done" : state === "active" ? "working" : "next"}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
