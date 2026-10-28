// The honest badges. V3's "Science checked" badge was shown for anything that passed its LLM verifier; V4's label is the Environment's real trust label, so the
// green check appears only for `kit-verified` (a textbook citation re-proved by the corpus, D-25). A `model-checked` Environment gets a plain, neutral badge, and a
// Free-lane Environment says outright that a model wrote it whole (hard constraint 3). The words on the badge never claim more than `Provenance` below it says.
import type { EnvironmentBlock } from "@synapse/schema";
import { useT, type StringKey } from "../lib/i18n";

const LABEL_BADGE: Record<EnvironmentBlock["label"], { text: StringKey; tone: "verified" | "checked" }> = {
  "kit-verified": { text: "badgeKitVerified", tone: "verified" },
  "model-checked": { text: "badgeCheckedByCode", tone: "checked" },
  reviewed: { text: "badgeReviewed", tone: "verified" },
  canonical: { text: "badgeCanonical", tone: "verified" },
};

const LANE_BADGE: Record<EnvironmentBlock["lane"], StringKey> = {
  instantiate: "laneLibrary",
  compose: "laneCompose",
  free: "laneFree",
};

const Check = () => (
  <svg width="13" height="13" viewBox="0 0 12 12" fill="none" aria-hidden>
    <path d="M2.5 6.2l2.2 2.2L9.5 3.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export function LabelBadge({ label }: { label: EnvironmentBlock["label"] }) {
  const t = useT();
  const { text, tone } = LABEL_BADGE[label];
  return (
    <span className={`study-badge ${tone === "verified" ? "study-badge-verified pop" : "study-badge-checked"}`}>
      {tone === "verified" ? <Check /> : null}
      {t(text)}
    </span>
  );
}

export function LaneBadge({ lane }: { lane: EnvironmentBlock["lane"] }) {
  const t = useT();
  return <span className={`study-badge ${lane === "free" ? "study-badge-free" : ""}`}>{t(LANE_BADGE[lane])}</span>;
}
