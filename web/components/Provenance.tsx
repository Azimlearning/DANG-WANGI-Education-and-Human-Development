// Provenance is always visible (hard constraint 11): the lane, the trust label in words, the source, WHAT WAS CHECKED and the limits.
// "What was checked" is rendered from the verifier's own stored record, not from a generic badge (enhancement N10).
import type { CheckedSummary, EnvironmentBlock } from "@synapse/schema";
import { citationText } from "../lib/citation";
import { english, useT, type StringKey, type T } from "../lib/i18n";

const LANE_TEXT: Record<EnvironmentBlock["lane"], StringKey> = {
  instantiate: "laneTextInstantiate",
  compose: "laneTextCompose",
  free: "laneTextFree",
};

const LABEL_NAME: Record<EnvironmentBlock["label"], StringKey> = {
  "kit-verified": "labelNameKit",
  "model-checked": "labelNameChecked",
  reviewed: "labelNameReviewed",
  canonical: "labelNameCanonical",
};

const LAYER_TEXT: Record<string, StringKey> = {
  postprocess: "layerPostprocess",
  scan: "layerScan",
  render: "layerRender",
  provenance: "layerProvenance",
  grid: "layerGrid",
  reference: "layerReference",
  wording: "layerWording",
};

export function checkedLines(checked: CheckedSummary, t: T = english): string[] {
  const lines: string[] = [];
  const layers = checked.layers.map((l) => (LAYER_TEXT[l] ? t(LAYER_TEXT[l]) : l));
  if (layers.length > 0) lines.push(t("checkedPrefix", { layers: layers.join("; ") }));
  const counts: string[] = [];
  if (checked.controlsExercised > 0) counts.push(t(checked.controlsExercised === 1 ? "countControlOne" : "countControlMany", { n: checked.controlsExercised }));
  if (checked.gridPoints > 0) counts.push(t("countPositions", { n: checked.gridPoints }));
  if (checked.referenceCases > 0) counts.push(t("countReference", { n: checked.referenceCases }));
  if (checked.readouts > 0) counts.push(t(checked.readouts === 1 ? "countReadoutOne" : "countReadoutMany", { n: checked.readouts }));
  if (counts.length > 0) lines.push(`${counts.join(", ")}.`);
  for (const m of checked.models) {
    const params = Object.entries(m.params).map(([k, v]) => `${k} = ${v}`);
    lines.push(t("scienceModelLine", { id: m.id, params: params.length ? ` (${params.join(", ")})` : "" }));
  }
  return lines;
}

/** `plain` drops the card border: inside the lab frame the one border is the frame's own. */
export function Provenance({ block, plain = false }: { block: EnvironmentBlock; plain?: boolean }) {
  const t = useT();
  return (
    <section aria-label={t("provenanceAria")} className={plain ? "grid gap-2 border-t-2 border-line px-4 py-3 text-sm" : "study-card grid gap-2 p-4 text-sm"}>
      <p>
        <strong>{t(LABEL_NAME[block.label])}.</strong> {t(LANE_TEXT[block.lane])}.
      </p>
      <p>{block.planSummary}</p>
      <p className="text-ink-dim">
        <strong>{t("sourceLabel")}</strong>{" "}
        {block.citations.length === 0
          ? t("noneStated")
          : block.citations.map((c) => citationText(c)).join("; ")}
      </p>
      <div className="text-ink-dim">
        <p>
          <strong>{t("whatWasChecked")}</strong>
        </p>
        <ul className="list-disc pl-5">
          {checkedLines(block.checked, t).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
      <p className="text-ink-dim">
        <strong>{t("limitsLabel")}</strong> {block.checked.limits}
      </p>
    </section>
  );
}
