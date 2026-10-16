// The /ask stream client. Each SSE message carries exactly one StreamEvent as JSON in `data:`. The web app has only TypeScript
// types from @synapse/schema (no runtime validator), so every event is checked structurally here before it is used. An event
// whose type this client does not know, and a block whose type is not "Environment", are IGNORED, never a crash (a newer server
// may send more than this client understands).
import type { EnvironmentBlock, ErrorEnvelope, StreamEvent } from "@synapse/schema";

const LANES = ["instantiate", "compose", "free"] as const;
const LABELS = ["dev-fixture", "kit-verified", "model-checked", "reviewed", "canonical"] as const;
const STATUSES = ["empty", "loading", "partial", "ready", "error"] as const;
const CODES = [
  "validation_failed",
  "bad_request",
  "not_found",
  "spend_cap_exceeded",
  "provider_unavailable",
  "verification_refused",
  "internal",
] as const;

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => typeof v === "object" && v !== null && !Array.isArray(v);
const isStr = (v: unknown): v is string => typeof v === "string";
const oneOf = <T extends string>(set: readonly T[], v: unknown): v is T => isStr(v) && (set as readonly string[]).includes(v);

export function parseErrorEnvelope(v: unknown): ErrorEnvelope | null {
  if (!isRec(v) || !oneOf(CODES, v.code) || !isStr(v.message) || typeof v.retryable !== "boolean" || !Array.isArray(v.issues)) return null;
  const issues = [];
  for (const i of v.issues) {
    if (!isRec(i) || !isStr(i.path) || !isStr(i.message)) return null;
    issues.push({ path: i.path, message: i.message });
  }
  return { code: v.code, message: v.message, issues, retryable: v.retryable };
}

export function parseEnvironmentBlock(v: unknown): EnvironmentBlock | null {
  if (!isRec(v) || v.type !== "Environment") return null; // an unknown block type is ignored
  if (!isStr(v.id) || !v.id || !isStr(v.title) || !isStr(v.kitVersion) || !isStr(v.htmlSha256) || !isStr(v.html) || !isStr(v.planSummary)) return null;
  if (!oneOf(LANES, v.lane) || !oneOf(LABELS, v.label)) return null;
  if (!isRec(v.meta) || !oneOf(STATUSES, v.meta.status)) return null;
  const error = v.meta.error === null ? null : parseErrorEnvelope(v.meta.error);
  if (v.meta.error !== null && error === null) return null;
  if (!Array.isArray(v.citations)) return null;
  const citations = [];
  for (const c of v.citations) {
    if (!isRec(c) || !isStr(c.source) || typeof c.verified !== "boolean") return null;
    if (!(c.page === null || Number.isInteger(c.page)) || !(c.quote === null || isStr(c.quote))) return null;
    citations.push({ source: c.source, page: c.page as number | null, quote: c.quote as string | null, verified: c.verified });
  }
  return {
    type: "Environment",
    id: v.id,
    meta: { status: v.meta.status, error },
    title: v.title,
    lane: v.lane,
    label: v.label,
    kitVersion: v.kitVersion,
    htmlSha256: v.htmlSha256,
    html: v.html,
    citations,
    planSummary: v.planSummary,
  };
}

/** One decoded JSON value to a StreamEvent, or null for anything this client does not understand. */
export function parseStreamEvent(v: unknown): StreamEvent | null {
  if (!isRec(v)) return null;
  switch (v.type) {
    case "meta":
      if (isStr(v.requestId) && oneOf(LANES, v.lane) && oneOf(LABELS, v.label) && isStr(v.kitVersion)) {
        return { type: "meta", requestId: v.requestId, lane: v.lane, label: v.label, kitVersion: v.kitVersion };
      }
      return null;
    case "text_delta":
      return isStr(v.text) ? { type: "text_delta", text: v.text } : null;
    case "environment": {
      const block = parseEnvironmentBlock(v.block);
      return block ? { type: "environment", block } : null;
    }
    case "error": {
      const error = parseErrorEnvelope(v.error);
      return error ? { type: "error", error } : null;
    }
    case "done":
      return { type: "done" };
    default:
      return null;
  }
}

/** Split an SSE byte stream into `data:` payloads. Handles chunk boundaries anywhere, CRLF, comments and multi-line data. */
export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const flush = function* (final: boolean): Generator<string> {
    buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    let cut: number;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const message = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const data = message
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).replace(/^ /, ""));
      if (data.length > 0) yield data.join("\n");
    }
    if (final && buffer.trim()) {
      const data = buffer.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).replace(/^ /, ""));
      buffer = "";
      if (data.length > 0) yield data.join("\n");
    }
  };
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      yield* flush(false);
    }
    buffer += decoder.decode();
    yield* flush(true);
  } finally {
    reader.releaseLock();
  }
}

export class AskError extends Error {
  constructor(
    message: string,
    readonly envelope: ErrorEnvelope | null,
  ) {
    super(message);
  }
}

export interface AskOptions {
  baseUrl: string;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
}

/** POST the question and yield each validated event. A non-200 answer carries an ErrorEnvelope and throws AskError. */
export async function* streamAsk(question: string, options: AskOptions): AsyncGenerator<StreamEvent> {
  const doFetch = options.fetchImpl ?? fetch;
  const response = await doFetch(`${options.baseUrl.replace(/\/$/, "")}/ask`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream" },
    body: JSON.stringify({ question }),
    signal: options.signal,
  });
  if (!response.ok || !response.body) {
    let envelope: ErrorEnvelope | null = null;
    try {
      envelope = parseErrorEnvelope(await response.json());
    } catch {
      envelope = null;
    }
    throw new AskError(envelope?.message ?? `The server answered ${response.status}.`, envelope);
  }
  for await (const payload of readSse(response.body)) {
    let decoded: unknown;
    try {
      decoded = JSON.parse(payload);
    } catch {
      continue; // not JSON: ignore
    }
    const event = parseStreamEvent(decoded);
    if (event) yield event;
  }
}
