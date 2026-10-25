// Bridge to the host page. Message names are kept from Synapse v3 (generator prompt v8, Block C):
// synapse_ready, synapse_event, synapse_error. The sandboxed iframe has an opaque origin, so the parent cannot be named as a
// target origin; the host validates `event.source` instead.
//
// The transport and its flags live in one `state` object that is NOT reachable from window.Synapse (only the four public
// functions are exposed, frozen), so generated content cannot silence errors or re-send ready. Tests reach `state` directly.

/** What a Kit component tells the host about the student's lab work (W5b): the Amali card, the steps, and the table the student fills. Sent by the Kit's own modules
 * only and deliberately NOT in the public surface, so page code cannot call it. Strings are cut to a size the host re-checks. */
export type LabPart =
  | { part: "experiment"; fields: [string, string][] }
  | { part: "steps"; steps: string[] }
  | { part: "table"; caption: string; columns: { label: string; unit: string }[]; rows: string[][] };

export type BridgeMessage =
  | { type: "synapse_ready" }
  | ({ type: "synapse_lab" } & LabPart)
  | { type: "synapse_event"; control: string; value: number | string | boolean }
  | { type: "synapse_error"; message: string }
  | { type: "synapse_violation"; problems: string[] };

type Poster = (message: BridgeMessage) => void;

const defaultPoster: Poster = (message) => {
  if (typeof window !== "undefined" && window.parent && window.parent !== window) {
    window.parent.postMessage(message, "*");
  }
};

/** Module-private in the bundle; exported by name for tests only. */
export const state: { poster: Poster; readySent: boolean; handlersInstalled: boolean } = {
  poster: defaultPoster,
  readySent: false,
  handlersInstalled: false,
};

/** Post `synapse_ready` once, after the first paint (two animation frames). */
export function ready(): void {
  if (state.readySent) return;
  const fire = () => {
    if (state.readySent) return;
    state.readySent = true;
    state.poster({ type: "synapse_ready" });
  };
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(() => requestAnimationFrame(fire));
  } else {
    fire();
  }
}

export function event(control: string, value: number | string | boolean): void {
  state.poster({ type: "synapse_event", control, value });
}

export function error(message: string): void {
  state.poster({ type: "synapse_error", message: String(message).slice(0, 500) });
}

const cut = (v: string, n: number): string => String(v).slice(0, n);

/** Tell the host what the student is working on. Replaces, never appends: a table message carries every row. */
export function lab(message: LabPart): void {
  if (message.part === "experiment") {
    state.poster({ type: "synapse_lab", part: "experiment", fields: message.fields.slice(0, 8).map(([k, v]) => [cut(k, 80), cut(v, 400)]) });
  } else if (message.part === "steps") {
    state.poster({ type: "synapse_lab", part: "steps", steps: message.steps.slice(0, 8).map((x) => cut(x, 300)) });
  } else {
    state.poster({
      type: "synapse_lab",
      part: "table",
      caption: cut(message.caption, 120),
      columns: message.columns.slice(0, 6).map((c) => ({ label: cut(c.label, 60), unit: cut(c.unit, 16) })),
      rows: message.rows.slice(0, 30).map((r) => r.slice(0, 6).map((c) => cut(c, 40))),
    });
  }
}

/** The Kit's runtime self-check found the page showing something the Kit did not make. The host hides the Environment. */
export function violation(problems: string[]): void {
  state.poster({ type: "synapse_violation", problems: problems.slice(0, 5).map((p) => String(p).slice(0, 120)) });
}

/** Report uncaught errors and unhandled rejections to the host. Idempotent. */
export function installErrorHandlers(): void {
  if (typeof window === "undefined" || state.handlersInstalled) return;
  state.handlersInstalled = true;
  window.addEventListener("error", (e) => error(e.message || "error"));
  window.addEventListener("unhandledrejection", (e) => error(String((e as PromiseRejectionEvent).reason)));
}
