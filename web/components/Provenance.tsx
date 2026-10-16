// Provenance is always visible (hard constraint 11): the lane, the trust label in words, the source, what was checked and the limits.
import type { EnvironmentBlock } from "@synapse/schema";

const LANE_TEXT: Record<EnvironmentBlock["lane"], string> = {
  instantiate: "Instantiate: a stored Environment, not written for this question",
  compose: "Compose: assembled from audited Kit components",
  free: "Free: written whole by a model, not built on the Kit",
};

const LABEL_TEXT: Record<EnvironmentBlock["label"], { name: string; limits: string }> = {
  "dev-fixture": {
    name: "Development fixture",
    limits:
      "A hand-written example used to test the system. It was checked only for forbidden code and for working controls. Its physics was NOT checked against the textbook.",
  },
  "kit-verified": { name: "Kit verified", limits: "Built on audited Kit components with a textbook citation." },
  "model-checked": { name: "Model checked", limits: "Checked by a model, with no textbook source. It may be wrong." },
  reviewed: { name: "Reviewed", limits: "Reviewed by a person." },
  canonical: { name: "Canonical", limits: "Reviewed by a person and approved." },
};

export function Provenance({ block }: { block: EnvironmentBlock }) {
  const label = LABEL_TEXT[block.label];
  return (
    <section aria-label="Where this Environment comes from" className="grid gap-2 rounded-xl p-4 text-sm" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <p>
        <strong>{label.name}.</strong> {LANE_TEXT[block.lane]}.
      </p>
      <p>{block.planSummary}</p>
      <p style={{ color: "var(--muted)" }}>
        <strong>Source:</strong>{" "}
        {block.citations.length === 0
          ? "none stated"
          : block.citations.map((c) => `${c.source}${c.page !== null ? `, page ${c.page}` : ""}${c.verified ? "" : " (not verified)"}`).join("; ")}
      </p>
      <p style={{ color: "var(--muted)" }}>
        <strong>Limits:</strong> {label.limits}
      </p>
    </section>
  );
}
