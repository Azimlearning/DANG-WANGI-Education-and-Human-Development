// HTTP and stream shapes that cross the wire. Anything that crosses the wire belongs here (hard constraint 7).
// Adapted from the stream conventions of Azimlearning/Arcana-v2, packages/schema/src/api.ts @ 21c6dcf5.

import type { Block, Lane, TrustLabel } from "./blocks";
import type { ErrorEnvelope } from "./errors";

/** POST /ask body. Single operator (D-11), so there is no user id. The endpoint enforces length bounds. */
export interface AskRequest {
  question: string;
}

// ── SSE stream (POST /ask) ──────────────────────────────────────────────────
// Each SSE message carries exactly one StreamEvent as JSON in `data:`.
// Order on success: meta, text_delta (one or more), environment, done.

export interface MetaEvent {
  type: "meta";
  requestId: string;
  lane: Lane;
  label: TrustLabel;
  kitVersion: string;
}

export interface TextDeltaEvent {
  type: "text_delta";
  text: string;
}

export interface EnvironmentEvent {
  type: "environment";
  block: Block;
}

/** A failure of the whole turn (as opposed to one block, which carries meta.error). */
export interface StreamErrorEvent {
  type: "error";
  error: ErrorEnvelope;
}

export interface DoneEvent {
  type: "done";
}

export type StreamEvent = MetaEvent | TextDeltaEvent | EnvironmentEvent | StreamErrorEvent | DoneEvent;
