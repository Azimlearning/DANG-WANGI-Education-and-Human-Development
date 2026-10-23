// The conversation as a list of turns (V3's chat reducer, rewritten for V4's events). One turn is a question, the written answer that streams in, the draft the
// plan produced, the verified Environment when it arrives, and where the pipeline is. Nothing here ever holds unverified HTML: a `draft` is data about a plan, and
// only the server's `environment` event carries a page (D-38: no "watch the code being written").
import type { EnvironmentBlock, ErrorEnvelope, PlanDraft, StreamEvent } from "@synapse/schema";

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

export interface Turn {
  id: number;
  question: string;
  text: string;
  block: EnvironmentBlock | null;
  draft: PlanDraft | null;
  note: string | null;
  error: ErrorEnvelope | string | null;
  step: StepKey;
  fromLibrary: boolean;
  /** True until the stream closes. */
  open: boolean;
}

export type TurnAction =
  | { type: "ask"; question: string }
  | { type: "event"; event: StreamEvent }
  | { type: "fail"; error: ErrorEnvelope | string }
  | { type: "close" };

const index = (k: StepKey) => STEPS.findIndex((s) => s.key === k);

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
      const turn: Turn = { id, question: action.question, text: "", block: null, draft: null, note: null, error: null, step: "reading", fromLibrary: false, open: true };
      return [...turns, turn];
    }
    case "fail":
      return updateLast(turns, (t) => ({ ...t, error: action.error, draft: null, open: false }));
    case "close":
      return updateLast(turns, (t) => ({ ...t, draft: null, open: false }));
    case "event": {
      const e = action.event;
      return updateLast(turns, (t) => {
        switch (e.type) {
          case "text_delta":
            return { ...t, text: t.text + e.text };
          case "plan":
            return { ...t, draft: e.draft };
          case "stage":
            if (e.status === "degraded") return { ...t, note: e.note, draft: null };
            if (e.layer === "library" && e.status === "done") return { ...t, step: "ready", fromLibrary: true };
            if (e.status === "start") return { ...t, step: advance(t.step, LAYER_STEP[e.layer] ?? t.step) };
            return t;
          case "environment":
            return { ...t, block: e.block, draft: null, step: "ready" };
          case "error":
            return { ...t, error: e.error, draft: null };
          default:
            return t; // meta, done
        }
      });
    }
  }
}
