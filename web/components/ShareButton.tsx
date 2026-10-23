"use client";

import { useState } from "react";
import { shareUrl } from "../lib/library";

/** Copies this Environment's link. If the clipboard is unavailable the link is shown to copy by hand, so the action never silently fails. */
export function ShareButton({ id }: { id: string }) {
  const [state, setState] = useState<"idle" | "copied" | "manual">("idle");
  const url = shareUrl(typeof window === "undefined" ? "" : window.location.origin, id);
  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setState("copied");
    } catch {
      setState("manual");
    }
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <button type="button" onClick={copy} className="btn btn-ghost px-4 text-sm">
        Copy link
      </button>
      <span role="status" className="text-sm font-semibold text-verify-ink">
        {state === "copied" ? "Link copied." : null}
      </span>
      {state === "manual" ? (
        <input
          readOnly
          aria-label="Link to this Environment"
          value={url}
          onFocus={(e) => e.currentTarget.select()}
          className="min-h-11 rounded-ctl border-2 border-line-2 bg-card px-3 text-sm text-ink"
        />
      ) : null}
    </span>
  );
}
