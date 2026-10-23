// The honest badges. V3's "Science checked" badge was shown for anything that passed its LLM verifier; V4's label is the Environment's real trust label, so the
// green check appears only for `kit-verified` (a textbook citation re-proved by the corpus, D-25). A `model-checked` Environment gets a plain, neutral badge, and a
// Free-lane Environment says outright that a model wrote it whole (hard constraint 3). The words on the badge never claim more than `Provenance` below it says.
import type { EnvironmentBlock } from "@synapse/schema";

const LABEL_BADGE: Record<EnvironmentBlock["label"], { text: string; tone: "verified" | "checked" }> = {
  "kit-verified": { text: "Kit verified", tone: "verified" },
  "model-checked": { text: "Checked by code", tone: "checked" },
  reviewed: { text: "Reviewed by a person", tone: "verified" },
  canonical: { text: "Canonical", tone: "verified" },
};

const LANE_BADGE: Record<EnvironmentBlock["lane"], string> = {
  instantiate: "From the library",
  compose: "Built for your question",
  free: "Written whole by a model",
};

const Check = () => (
  <svg width="13" height="13" viewBox="0 0 12 12" fill="none" aria-hidden>
    <path d="M2.5 6.2l2.2 2.2L9.5 3.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export function LabelBadge({ label }: { label: EnvironmentBlock["label"] }) {
  const { text, tone } = LABEL_BADGE[label];
  return (
    <span className={`study-badge ${tone === "verified" ? "study-badge-verified pop" : "study-badge-checked"}`}>
      {tone === "verified" ? <Check /> : null}
      {text}
    </span>
  );
}

export function LaneBadge({ lane }: { lane: EnvironmentBlock["lane"] }) {
  return <span className={`study-badge ${lane === "free" ? "study-badge-free" : ""}`}>{LANE_BADGE[lane]}</span>;
}
