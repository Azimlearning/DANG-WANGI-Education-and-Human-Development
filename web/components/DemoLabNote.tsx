"use client";

// While the server runs on the offline fake model, a lab that was not taken from the library was "planned" by a script that ignores the question: it is a canned lab, not one
// made for what the student asked. Its label is true to how it was checked, so the page adds this plain note beside it. Gone once the server is live.
import { useServerMode } from "../lib/mode";
import { useT } from "../lib/i18n";

export function DemoLabNote({ lane }: { lane: string }) {
  const t = useT();
  const mode = useServerMode();
  if (mode !== "fake" || lane === "instantiate") return null;
  return (
    <p role="status" data-testid="demo-lab-note" className="border-b-2 border-line bg-band px-3 py-2 text-sm text-ink-dim">
      {t("demoLabNote")}
    </p>
  );
}
