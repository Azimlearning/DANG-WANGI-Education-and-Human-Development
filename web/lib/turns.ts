// The conversation as a list of turns (V3's chat reducer, rewritten for V4's events). One turn is a question, the written answer that streams in, the draft the
// plan produced, the verified Environment when it arrives, and where the pipeline is. Nothing here ever holds unverified HTML: a `draft` is data about a plan, and
// only the server's `environment` event carries a page (D-38: no "watch the code being written").
import type { EnvironmentBlock, ErrorEnvelope, ExamEvent, PlanDraft, ProbeEvent, StreamEvent } from "@synapse/schema";

export type StepKey = "reading" | "explaining" | "planning" | "checking" | "ready";

/** What a student sees while a question is worked on, in the order it happens. Each is true to a real pipeline layer; none is a fake spinner. */
export const STEPS: { key: StepKey; label: string }[] = [
  { key: "reading", label: "Reading your question" },
  { key: "explaining", label: "Writing the explanation" },
  { key: "planning", label: "Designing the experiment" },
  { key: "checking", label: "Checking the science" },
  { key: "ready", label: "Ready" },
];

const LAYER_STEP: Record<string, StepKey> = {
  intake: "reading",
  route: "reading",
  lookup: "reading",
  explain: "explaining",
  plan: "planning",
  assemble: "planning",
  verify: "checking",
  deliver: "checking",
  library: "ready",
};

/** One line of the build log (W18, D-77): a stage the server reported, the plan's arrival, or the verified page's arrival. Words from the pipeline, never code. */
export interface LogEntry {
  kind: "stage" | "plan" | "environment" | "code";
  layer: string;
  status: "start" | "done" | "degraded";
  note: string | null;
}

/** The page's code as the build log shows it (D-79): text, never run. */
export interface CodeView {
  lane: "compose" | "free";
  status: "writing" | "unchecked" | "passed" | "refused";
  text: string;
  note: string | null;
}

/** The most code the log keeps: a Free page is capped well under this; anything longer is cut, never run either way. */
const MAX_CODE_CHARS = 120_000;

export interface Turn {
  id: number;
  question: string;
  text: string;
  block: EnvironmentBlock | null;
  draft: PlanDraft | null;
  /** The optional follow-up question about an idea this question touched (W5a). Plain text; never a page. */
  probe: ProbeEvent | null;
  /** The optional practice question for the topic (W5c), marked in the browser. */
  exam: ExamEvent | null;
  note: string | null;
  error: ErrorEnvelope | string | null;
  step: StepKey;
  fromLibrary: boolean;
  /** True until the stream closes. */
  open: boolean;
  /** What the pipeline did, in order (the "See how it's built" log). */
  log: LogEntry[];
  /** The page's code as it was written and checked, or null before any. */
  code: CodeView | null;
}

export type TurnAction =
  | { type: "ask"; question: string }
  | { type: "event"; event: StreamEvent }
  | { type: "fail"; error: ErrorEnvelope | string }
  | { type: "close" };

const index = (k: StepKey) => STEPS.findIndex((s) => s.key === k);

const MAX_LOG = 40;

/** The log with this event's line added, when it has one. */
function logged(log: LogEntry[], e: StreamEvent): LogEntry[] {
  let line: LogEntry | null = null;
  if (e.type === "stage") line = { kind: "stage", layer: e.layer, status: e.status, note: e.note };
  else if (e.type === "plan") line = { kind: "plan", layer: "plan", status: "done", note: e.draft.title };
  else if (e.type === "environment") line = { kind: "environment", layer: "deliver", status: "done", note: e.block.title };
  else if (e.type === "code" && e.note) line = { kind: "code", layer: "code", status: e.status === "passed" ? "done" : e.status === "refused" ? "degraded" : "start", note: e.note };
  return line ? [...log, line].slice(-MAX_LOG) : log;
}

/** Progress only moves forward: a late event for an earlier layer must not send the card backwards. */
function advance(current: StepKey, next: StepKey): StepKey {
  return index(next) > index(current) ? next : current;
}

function updateLast(turns: Turn[], change: (t: Turn) => Turn): Turn[] {
  const last = turns[turns.length - 1];
  if (!last) return turns;
  return [...turns.slice(0, -1), change(last)];
}

export function turnReducer(turns: Turn[], action: TurnAction): Turn[] {
  switch (action.type) {
    case "ask": {
      const id = (turns[turns.length - 1]?.id ?? 0) + 1;
      const turn: Turn = { id, question: action.question, text: "", block: null, draft: null, probe: null, exam: null, note: null, error: null, step: "reading", fromLibrary: false, open: true, log: [], code: null };
      return [...turns, turn];
    }
    case "fail":
      return updateLast(turns, (t) => ({ ...t, error: action.error, draft: null, open: false }));
    case "close":
      return updateLast(turns, (t) => ({ ...t, draft: null, open: false }));
    case "event": {
      const e = action.event;
      return updateLast(turns, (raw) => {
        const t = { ...raw, log: logged(raw.log, e) };
        switch (e.type) {
          case "text_delta":
            return { ...t, text: t.text + e.text };
          case "code": {
            const before = e.reset || !t.code ? "" : t.code.text;
            return { ...t, code: { lane: e.lane, status: e.status, text: (before + e.delta).slice(0, MAX_CODE_CHARS), note: e.note ?? (e.reset ? null : t.code?.note ?? null) } };
          }
          case "plan":
            return { ...t, draft: e.draft };
          case "stage":
            if (e.status === "degraded") return { ...t, note: e.note, draft: null };
            if (e.layer === "library" && e.status === "done") return { ...t, step: "ready", fromLibrary: true };
            // A stage that starts after a degraded one means the pipeline is still trying for a lab (the last step, D-80): the "no lab" note no longer holds.
            if (e.status === "start") return { ...t, note: null, step: advance(t.step, LAYER_STEP[e.layer] ?? t.step) };
            return t;
          case "environment":
            // A lab that arrives after a degraded stage (the simple lab, D-80) replaces the "no lab" note: the student has a lab.
            return { ...t, block: e.block, draft: null, step: "ready", note: null };
          case "probe":
            return { ...t, probe: e };
          case "exam":
            return { ...t, exam: e };
          case "error":
            return { ...t, error: e.error, draft: null };
          default:
            return t; // meta, done
        }
      });
    }
  }
}
