"use client";

// Which model the server runs on, from its /health answer. "fake" is the offline deterministic model: it can reply only to the questions the stored library holds, so the page says
// so instead of letting a student think a lab failed. Unknown (the server is down, or an older server that does not say) is treated as live: nothing is claimed that is not known.
import { useEffect, useState } from "react";

export type ServerMode = "fake" | "live" | "unknown";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function parseMode(body: unknown): ServerMode {
  if (typeof body !== "object" || body === null) return "unknown";
  const mode = (body as Record<string, unknown>).llm_mode;
  return mode === "fake" || mode === "live" ? mode : "unknown";
}

export function useServerMode(): ServerMode {
  const [mode, setMode] = useState<ServerMode>("unknown");
  useEffect(() => {
    let alive = true;
    fetch(`${API_BASE}/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((body) => {
        if (alive) setMode(parseMode(body));
      })
      .catch(() => {
        /* the server is down: the ask itself says so */
      });
    return () => {
      alive = false;
    };
  }, []);
  return mode;
}
