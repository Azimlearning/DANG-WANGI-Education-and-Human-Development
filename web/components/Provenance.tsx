// Provenance is always visible (hard constraint 11): the lane, the trust label in words, the source, WHAT WAS CHECKED and the limits.
// "What was checked" is rendered from the verifier's own stored record, not from a generic badge (enhancement N10).
import type { CheckedSummary, EnvironmentBlock } from "@synapse/schema";

const LANE_TEXT: Record<EnvironmentBlock["lane"], string> = {
  instantiate: "Instantiate: a stored Environment reused as it was",
  compose: "Compose: planned for your question and assembled from audited Kit components",
  free: "Free: written whole by a model, not built on the Kit",
};

const LABEL_NAME: Record<EnvironmentBlock["label"], string> = {
  "kit-verified": "Kit verified",
  "model-checked": "Checked by code, no verified textbook source",
  reviewed: "Reviewed by a person",
  canonical: "Canonical",
};

const LAYER_TEXT: Record<string, string> = {
  postprocess: "the page structure and its security policy",
  scan: "no forbidden code",
  render: "it runs in a real browser and its controls work",
  provenance: "the values it computes come from a science model, and the numbers in its sentences match its settings",
  grid: "controls were moved across their range, including the extremes",
  reference: "values were compared with an independent calculation",
  wording: "its words were read by a second model for false or misleading statements (a model's reading, not a proof)",
};

export function checkedLines(checked: CheckedSummary): string[] {
  const lines: string[] = [];
  const layers = checked.layers.map((l) => LAYER_TEXT[l] ?? l);
  if (layers.length > 0) lines.push(`Checked: ${layers.join("; ")}.`);
  const counts: string[] = [];
  if (checked.controlsExercised > 0) counts.push(`${checked.controlsExercised} control${checked.controlsExercised === 1 ? "" : "s"} tried`);
  if (checked.gridPoints > 0) counts.push(`${checked.gridPoints} control positions`);
  if (checked.referenceCases > 0) counts.push(`${checked.referenceCases} values compared with the reference`);
  if (checked.readouts > 0) counts.push(`${checked.readouts} readout${checked.readouts === 1 ? "" : "s"}`);
  if (counts.length > 0) lines.push(`${counts.join(", ")}.`);
  for (const m of checked.models) {
    const params = Object.entries(m.params).map(([k, v]) => `${k} = ${v}`);
    lines.push(`Science model: ${m.id}${params.length ? ` (${params.join(", ")})` : ""}.`);
  }
  return lines;
}

export function Provenance({ block }: { block: EnvironmentBlock }) {
  return (
    <section aria-label="Where this Environment comes from" className="grid gap-2 rounded-xl p-4 text-sm" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <p>
        <strong>{LABEL_NAME[block.label]}.</strong> {LANE_TEXT[block.lane]}.
      </p>
      <p>{block.planSummary}</p>
      <p style={{ color: "var(--muted)" }}>
        <strong>Source:</strong>{" "}
        {block.citations.length === 0
          ? "none stated"
          : block.citations.map((c) => `${c.source}${c.page !== null ? `, page ${c.page}` : ""}${c.verified ? "" : " (not verified)"}`).join("; ")}
      </p>
      <div style={{ color: "var(--muted)" }}>
        <p>
          <strong>What was checked:</strong>
        </p>
        <ul className="list-disc pl-5">
          {checkedLines(block.checked).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
      <p style={{ color: "var(--muted)" }}>
        <strong>Limits:</strong> {block.checked.limits}
      </p>
    </section>
  );
}
