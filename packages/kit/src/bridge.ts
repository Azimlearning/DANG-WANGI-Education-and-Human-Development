// Bridge to the host page. Message names are kept from Synapse v3 (generator prompt v8, Block C):
// synapse_ready, synapse_event, synapse_error. The sandboxed iframe has an opaque origin, so the parent cannot be named as a
// target origin; the host validates `event.source` instead.

export type BridgeMessage =
  | { type: "synapse_ready" }
  | { type: "synapse_event"; control: string; value: number | string | boolean }
  | { type: "synapse_error"; message: string };

type Poster = (message: BridgeMessage) => void;

let poster: Poster = (message) => {
  if (typeof window !== "undefined" && window.parent && window.parent !== window) {
    window.parent.postMessage(message, "*");
  }
};

/** For tests: replace the transport. */
export function setPoster(next: Poster): void {
  poster = next;
}

let readySent = false;

/** Post `synapse_ready` once, after the first paint (two animation frames). */
export function ready(): void {
  if (readySent) return;
  const fire = () => {
    if (readySent) return;
    readySent = true;
    poster({ type: "synapse_ready" });
  };
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(() => requestAnimationFrame(fire));
  } else {
    fire();
  }
}

export function event(control: string, value: number | string | boolean): void {
  poster({ type: "synapse_event", control, value });
}

export function error(message: string): void {
  poster({ type: "synapse_error", message: String(message).slice(0, 500) });
}

/** Report uncaught errors and unhandled rejections to the host. */
let handlersInstalled = false;

export function installErrorHandlers(): void {
  if (typeof window === "undefined" || handlersInstalled) return;
  handlersInstalled = true;
  window.addEventListener("error", (e) => error(e.message || "error"));
  window.addEventListener("unhandledrejection", (e) => error(String((e as PromiseRejectionEvent).reason)));
}

/** For tests. */
export function resetForTests(): void {
  readySent = false;
  handlersInstalled = false;
}
