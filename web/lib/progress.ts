// Device-local progress (P6). Nothing here leaves the browser: no account, no server, no analytics. The state is one small object kept in
// localStorage, and "an export code" is that object plus a checksum so a student can move it to another device by copying text.
// The checksum catches a mistyped or half-pasted code; it is not a security feature (a student can edit their own progress, and nothing depends on it).

export interface Entry {
  id: string;
  title: string;
  tries: number;
  correct: number;
  last: string;
}

export interface Progress {
  v: 1;
  items: Record<string, Entry>;
}

export type Outcome = "correct" | "incorrect";
export type Mastery = "Just started" | "Getting there" | "Secure";

export const STORAGE_KEY = "synapse.progress.v1";
export const MAX_ITEMS = 200;
const MAX_TEXT = 120;
const MAX_COUNT = 10000;

export const empty = (): Progress => ({ v: 1, items: {} });

const clip = (s: string) => s.slice(0, MAX_TEXT);

export function record(state: Progress, env: { id: string; title: string }, outcome: Outcome, now: Date = new Date()): Progress {
  const id = clip(env.id);
  const old = state.items[id];
  const items = { ...state.items };
  if (!old && Object.keys(items).length >= MAX_ITEMS) {
    const oldest = Object.values(items).sort((a, b) => a.last.localeCompare(b.last))[0];
    if (oldest) delete items[oldest.id];
  }
  items[id] = {
    id,
    title: clip(env.title),
    tries: Math.min((old?.tries ?? 0) + 1, MAX_COUNT),
    correct: Math.min((old?.correct ?? 0) + (outcome === "correct" ? 1 : 0), MAX_COUNT),
    last: now.toISOString(),
  };
  return { v: 1, items };
}

/** In words, because a bare percentage from two or three answers would claim more than it knows. */
export function mastery(e: Entry): Mastery {
  if (e.tries < 2) return "Just started";
  return e.correct >= 2 && e.correct / e.tries >= 0.7 ? "Secure" : "Getting there";
}

export function list(state: Progress): Entry[] {
  return Object.values(state.items).sort((a, b) => b.last.localeCompare(a.last));
}

// ── storage (every access is guarded: it can be blocked, full or corrupt) ─────────────────────────────────────────────────────────────────────

export function load(storage: Pick<Storage, "getItem"> | null = safeStorage()): Progress {
  try {
    const raw = storage ? storage.getItem(STORAGE_KEY) : null;
    return (raw ? validate(JSON.parse(raw)) : null) ?? empty();
  } catch {
    return empty();
  }
}

export function save(state: Progress, storage: Pick<Storage, "setItem"> | null = safeStorage()): boolean {
  try {
    if (!storage) return false;
    storage.setItem(STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

function safeStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

// ── validation and the export code ────────────────────────────────────────────────────────────────────────────────────────────────────────────

const isInt = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v) && v >= 0 && v <= MAX_COUNT;

export function validate(v: unknown): Progress | null {
  if (typeof v !== "object" || v === null || (v as { v?: unknown }).v !== 1) return null;
  const items = (v as { items?: unknown }).items;
  if (typeof items !== "object" || items === null || Array.isArray(items)) return null;
  const out: Record<string, Entry> = {};
  const entries = Object.entries(items as Record<string, unknown>);
  if (entries.length > MAX_ITEMS) return null;
  for (const [key, e] of entries) {
    if (typeof e !== "object" || e === null) return null;
    const { id, title, tries, correct, last } = e as Record<string, unknown>;
    if (typeof id !== "string" || id !== key || id.length === 0 || id.length > MAX_TEXT) return null;
    if (typeof title !== "string" || title.length > MAX_TEXT) return null;
    if (!isInt(tries) || !isInt(correct) || correct > tries) return null;
    if (typeof last !== "string" || last.length > 40 || Number.isNaN(Date.parse(last))) return null;
    out[id] = { id, title, tries, correct, last };
  }
  return { v: 1, items: out };
}

/** FNV-1a, 32 bit: enough to notice a typo. */
function checksum(text: string): string {
  let h = 0x811c9dc5;
  for (const byte of new TextEncoder().encode(text)) {
    h ^= byte;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

const b64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const unb64 = (s: string) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));

export function encode(state: Progress): string {
  const json = JSON.stringify(state);
  return `SYN1.${b64(new TextEncoder().encode(json))}.${checksum(json)}`;
}

/** The state in a code, or null for anything that is not exactly what `encode` makes. */
export function decode(code: string): Progress | null {
  try {
    const parts = code.trim().split(".");
    if (parts.length !== 3 || parts[0] !== "SYN1" || parts[1]!.length > 60000) return null;
    const json = new TextDecoder("utf-8", { fatal: true }).decode(unb64(parts[1]!));
    if (checksum(json) !== parts[2]) return null;
    return validate(JSON.parse(json));
  } catch {
    return null;
  }
}
