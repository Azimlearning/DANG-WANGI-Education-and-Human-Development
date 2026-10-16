"use client";

// Renders one Environment in a sandboxed iframe, but only after the browser has re-hashed its HTML against the hash the server
// verified (hard constraint 1). The sandbox attribute comes from the pinned constant and nothing else; the document carries its own
// CSP (injected server-side). A SECOND load of the frame means it navigated away from its srcdoc, so it is torn down at once.
import type { EnvironmentBlock } from "@synapse/schema";
import { useEffect, useRef, useState } from "react";
import { checkBlockHash } from "../lib/hash";
import { load, record, save } from "../lib/progress";
import { parseBridgeMessage, SANDBOX } from "../lib/sandbox";

type Phase = { kind: "checking" } | { kind: "ok" } | { kind: "refused"; reason: string };

export function EnvironmentFrame({
  block,
  height,
  onRefused,
}: {
  block: EnvironmentBlock;
  height: number | string;
  onRefused?: (reason: string) => void;
}) {
  const [phase, setPhase] = useState<Phase>({ kind: "checking" });
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const loads = useRef(0);

  useEffect(() => {
    let live = true;
    setPhase({ kind: "checking" });
    loads.current = 0;
    checkBlockHash(block).then((result) => {
      if (!live) return;
      if (result.ok) setPhase({ kind: "ok" });
      else {
        setPhase({ kind: "refused", reason: result.reason });
        onRefused?.(result.reason);
      }
    });
    return () => {
      live = false;
    };
  }, [block, onRefused]);

  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (!iframeRef.current || e.source !== iframeRef.current.contentWindow) return; // only our own frame
      const message = parseBridgeMessage(e.data);
      if (message?.type === "synapse_error") setRuntimeError(message.message);
      if (message?.type === "synapse_event" && message.control === "concept_check" && (message.value === "correct" || message.value === "incorrect")) {
        // The first answer to a concept check, kept on this device only (P6). A failure to store is silent: progress is a convenience.
        save(record(load(), { id: block.id, title: block.title }, message.value));
        window.dispatchEvent(new Event("synapse-progress"));
      }
      if (message?.type === "synapse_violation") {
        // The Kit watched itself and found the page showing something it did not make. Nothing it shows can be trusted: close it.
        const reason = "This Environment changed what it was showing in a way the checker does not allow, so it was closed.";
        setPhase({ kind: "refused", reason });
        onRefused?.(reason);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [onRefused, block.id, block.title]);

  if (phase.kind === "checking") {
    return (
      <p role="status" className="p-4 text-sm" style={{ color: "var(--muted)" }}>
        Checking the Environment&apos;s hash…
      </p>
    );
  }
  if (phase.kind === "refused") {
    return (
      <p role="alert" className="rounded-xl p-4 text-sm" style={{ background: "var(--warn-bg)", color: "var(--warn-fg)" }}>
        {phase.reason}
      </p>
    );
  }
  return (
    <>
      <iframe
        ref={iframeRef}
        title={block.title}
        sandbox={SANDBOX}
        srcDoc={block.html}
        referrerPolicy="no-referrer"
        style={{ width: "100%", height, border: 0, borderRadius: 12, background: "var(--card)" }}
        onLoad={() => {
          loads.current += 1;
          if (loads.current > 1) {
            // The frame left its srcdoc. Nothing it shows now was verified.
            const reason = "The Environment tried to navigate away, so it was closed.";
            setPhase({ kind: "refused", reason });
            onRefused?.(reason);
          }
        }}
      />
      {runtimeError ? (
        <p role="alert" className="mt-2 text-sm" style={{ color: "var(--warn-fg)" }}>
          This Environment reported an error: {runtimeError}
        </p>
      ) : null}
    </>
  );
}
