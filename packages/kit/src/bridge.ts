// Bridge to the host page. Message names are kept from Synapse v3 (generator prompt v8, Block C):
// synapse_ready, synapse_event, synapse_error. The sandboxed iframe has an opaque origin, so the parent cannot be named as a
// target origin; the host validates `event.source` instead.
//
// The transport and its flags live in one `state` object that is NOT reachable from window.Synapse (only the four public
// functions are exposed, frozen), so generated content cannot silence errors or re-send ready. Tests reach `state` directly.

export type BridgeMessage =
  | { type: "synapse_ready" }
  | { type: "synapse_event"; control: string; value: number | string | boolean }
  | { type: "synapse_error"; message: string };

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

/** Report uncaught errors and unhandled rejections to the host. Idempotent. */
export function installErrorHandlers(): void {
  if (typeof window === "undefined" || state.handlersInstalled) return;
  state.handlersInstalled = true;
  window.addEventListener("error", (e) => error(e.message || "error"));
  window.addEventListener("unhandledrejection", (e) => error(String((e as PromiseRejectionEvent).reason)));
}
