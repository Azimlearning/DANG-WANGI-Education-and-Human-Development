// HTTP and stream shapes that cross the wire. Anything that crosses the wire belongs here (hard constraint 7).
// Adapted from the stream conventions of Azimlearning/Arcana-v2, packages/schema/src/api.ts @ 21c6dcf5.

import type { Block } from "./blocks";
import type { ErrorEnvelope } from "./errors";

/** POST /ask body. Single operator (D-11), so there is no user id. The endpoint enforces length bounds. */
export interface AskRequest {
  question: string;
}

// ── SSE stream (POST /ask) ──────────────────────────────────────────────────
// Each SSE message carries exactly one StreamEvent as JSON in `data:`.
// Order on success: meta, stage events, text_delta (one or more), plan, more stage events, environment, probe (optional), exam (optional), done. A turn that cannot make an
// Environment ends with a text answer and a degraded stage event instead of an environment.

/** First event. The lane and label are NOT here: they are decided by what verification the Environment survives, so they arrive on the block. */
export interface MetaEvent {
  type: "meta";
  requestId: string;
  kitVersion: string;
}

/** A pipeline layer started, finished, or degraded (D-23). `note` is plain language for the student, or null. */
export interface StageEvent {
  type: "stage";
  layer: string;
  status: "start" | "done" | "degraded";
  note: string | null;
}

/** What the plan says, streamed once the plan checks pass so the client can draw the loading skeleton. It is a draft, not verified. */
export interface PlanDraft {
  title: string;
  goal: string;
  pattern: string;
  note: string;
  controls: PlanPart[];
  readouts: PlanPart[];
  hasGraph: boolean;
  hasTable: boolean;
  steps: string[];
}

export interface PlanPart {
  label: string;
  unit: string;
}

export interface PlanEvent {
  type: "plan";
  draft: PlanDraft;
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

/** An optional follow-up question about an idea the student's question touched (W5a). Host text, not an Environment: it is never HTML and is not verified by the
 * verifier. `basis` says in plain words what the correction rests on. A match is a topic detector, so the card asks a question and never says what the student thinks. */
export interface ProbeEvent {
  type: "probe";
  id: string;
  question: string;
  options: string[];
  /** @int Zero-based index of the correct option. */
  correct: number;
  explanation: string;
  basis: string;
}

/** One marking point of an exam-mirror question (W5c): the sentence shown after marking, and the wordings that earn it. A wording is a list of word stems that must ALL
 * appear in the answer; a point is earned when any one wording matches. A stem made only of digits must match a whole number; any other stem matches a word that starts with it. */
export interface ExamPoint {
  text: string;
  wordings: string[][];
}

/** An optional practice question in the style of a structured exam question, marked in the browser by matching key words (W5c). It is host text, not an Environment, and the
 * answer a student types never leaves the browser. */
export interface ExamEvent {
  type: "exam";
  id: string;
  stem: string;
  /** @int One mark for each point. */
  marks: number;
  points: ExamPoint[];
  sample: string;
}

export interface DoneEvent {
  type: "done";
}

export type StreamEvent = MetaEvent | StageEvent | PlanEvent | TextDeltaEvent | EnvironmentEvent | ProbeEvent | ExamEvent | StreamErrorEvent | DoneEvent;
