"use client";

// "See how it's built" (W18, D-77; W19, D-79): while a question is worked on, the log lists each real step the pipeline reported (the plan, the Kit parts it names, the lane,
// the checks), in the pipeline's own words, and the page's code as it is built: a model's page token by token as it is written, a Kit page whole as the assembler makes it. The
// code here is TEXT in a <pre>: it is never rendered and never run (the owner's call in D-79; only the verified block runs, in the sandboxed frame). Its status says where it
// stands: being written, being checked, passed or refused. Under the finished lab, "View the page code" shows the verified block's exact HTML and its SHA-256.
import type { EnvironmentBlock, PlanDraft } from "@synapse/schema";
import { useEffect, useRef } from "react";
import { useT, type StringKey } from "../lib/i18n";
import type { CodeView, LogEntry } from "../lib/turns";

const LAYER: Record<string, StringKey> = {
  intake: "layerIntake",
  route: "layerRoute",
  library: "layerLibrary",
  lookup: "layerLookup",
  explain: "layerExplain",
  plan: "layerPlan",
  assemble: "layerAssemble",
  verify: "layerVerify",
  deliver: "layerDeliver",
  code: "layerCode",
};
const CODE_STATUS: Record<CodeView["status"], StringKey> = { writing: "codeWriting", unchecked: "codeUnchecked", passed: "codePassed", refused: "codeRefused" };
const STATUS: Record<LogEntry["status"], StringKey> = { start: "statusStart", done: "statusDone", degraded: "statusDegraded" };
const MARK: Record<LogEntry["status"], string> = { start: "…", done: "✓", degraded: "!" };

function Line({ entry }: { entry: LogEntry }) {
  const t = useT();
  const layer = LAYER[entry.layer] ? t(LAYER[entry.layer] as StringKey) : entry.layer;
  const head =
    entry.kind === "plan"
      ? t("logPlanReady", { title: entry.note ?? "" })
      : entry.kind === "environment"
        ? t("logDelivered", { title: entry.note ?? "" })
        : entry.kind === "code"
          ? `${layer}: ${entry.note ?? ""}`
          : `${layer}: ${t(STATUS[entry.status])}`;
  return (
    <li className="grid grid-cols-[1.25rem_1fr] gap-2">
      <span aria-hidden className={entry.status === "degraded" ? "text-warn" : entry.status === "done" ? "text-verify-ink" : "text-primary-ink"}>
        {MARK[entry.status]}
      </span>
      <span>
        <span className="font-semibold text-ink">{head}</span>
        {entry.kind === "stage" && entry.note ? <span className="block text-ink-dim">{entry.note}</span> : null}
      </span>
    </li>
  );
}

/** The page's code as it is built: text that follows the newest line while it is written, with where it stands. */
function LiveCode({ code }: { code: CodeView }) {
  const t = useT();
  const box = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (code.status === "writing" && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [code.text, code.status]);
  const tone = code.status === "passed" ? "text-verify-ink" : code.status === "refused" ? "text-warn" : "text-primary-ink";
  return (
    <div className="grid gap-1.5 pb-2" data-testid="live-code">
      <p className="flex flex-wrap items-baseline gap-x-2 text-[13px]">
        <span className="font-display font-semibold text-ink">{t("liveCode")}</span>
        <span className="study-badge">{t(code.lane === "free" ? "codeLaneFree" : "codeLaneCompose")}</span>
        <span className={`font-semibold ${tone}`} role="status">
          {t(CODE_STATUS[code.status])}
        </span>
      </p>
      <pre ref={box} className="max-h-[360px] overflow-auto rounded-card border-2 border-line bg-band p-3 font-mono text-[11.5px] leading-snug text-ink" tabIndex={0} aria-label={t("liveCode")}>
        <code>{code.text}</code>
        {code.status === "writing" ? <span className="caret" aria-hidden /> : null}
      </pre>
    </div>
  );
}

/** The log of a question being worked on, folded away until opened. */
export function BuildLog({ log, draft, code = null, open = false }: { log: LogEntry[]; draft: PlanDraft | null; code?: CodeView | null; open?: boolean }) {
  const t = useT();
  if (log.length === 0) return null;
  return (
    <details className="study-card px-4 py-2" open={open} data-testid="build-log">
      <summary className="min-h-11 cursor-pointer py-2 font-display text-sm font-semibold">{t("seeHowBuilt")}</summary>
      <ol className="grid gap-1.5 pb-2 font-mono text-[12.5px] leading-snug" aria-live="polite">
        {log.map((entry, i) => (
          <Line key={i} entry={entry} />
        ))}
      </ol>
      {draft && draft.components.length > 0 ? <p className="pb-2 font-mono text-[12px] text-ink-dim">{t("kitParts", { list: draft.components.join(", ") })}</p> : null}
      {code && code.text ? <LiveCode code={code} /> : null}
    </details>
  );
}

/** The verified page's code and the log that made it, under the lab. The code is the block's own HTML, the one the frame runs after re-hashing it. */
export function BuildDetails({ block, log }: { block: EnvironmentBlock | null; log: LogEntry[] }) {
  const t = useT();
  return (
    <div className="grid gap-2">
      <BuildLog log={log} draft={null} />
      <details className="study-card px-4 py-2" data-testid="code-view">
        <summary className="min-h-11 cursor-pointer py-2 font-display text-sm font-semibold">{t("viewCode")}</summary>
        {block ? (
          <>
            <p className="pb-2 text-[13px] text-ink-dim">{t("codeMeta", { chars: block.html.length.toLocaleString("en"), sha: block.htmlSha256.slice(0, 12) })}</p>
            <pre className="max-h-[420px] overflow-auto rounded-card border-2 border-line bg-band p-3 font-mono text-[11.5px] leading-snug text-ink" tabIndex={0}>
              <code>{block.html}</code>
            </pre>
          </>
        ) : (
          <p className="pb-2 text-[13px] text-ink-dim">{t("codeAfterChecks")}</p>
        )}
      </details>
    </div>
  );
}
