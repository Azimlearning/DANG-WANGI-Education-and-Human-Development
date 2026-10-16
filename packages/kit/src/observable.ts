// Kit core: a tiny observable. The Kit API is ASSUMED (A-2).
//
// `readout` accepts only observables the Kit created. That check is by private registry (see provenance.ts), not by shape, so it is a
// real boundary for "this value came from the Kit". It says nothing about where the value came from: that is the provenance node,
// which the L1 audit reads. A public `observable(x)` is kind `free` and a `map` written by generated code is kind `derived` with
// `user: true`; the verifier refuses a readout that depends on either.

import { isObservable, nodeOf, track, type ProvNode } from "./provenance";

export interface Observable<T> {
  get(): T;
  set(value: T): void;
  subscribe(listener: (value: T) => void): () => void;
  map<U>(fn: (value: T) => U): Observable<U>;
}

export interface ObservableOptions<T> {
  /** Applied to every value written, including the initial one (a slider clamps here). */
  transform?: (value: T) => T;
  /** Computed observables cannot be written. */
  readOnly?: boolean;
}

/** Internal: an observable with an explicit provenance node. Not exposed on `Synapse`. */
export function create<T>(initial: T, node: ProvNode, options: ObservableOptions<T> = {}): Observable<T> {
  const transform = options.transform ?? ((v: T) => v);
  let current = transform(initial);
  const listeners = new Set<(value: T) => void>();
  const write = (value: T) => {
    const next = transform(value);
    if (Object.is(next, current)) return;
    current = next;
    for (const listener of [...listeners]) listener(current);
  };
  const self: Observable<T> = {
    get: () => current,
    set(value: T) {
      if (options.readOnly) throw new TypeError("this observable is computed and read-only");
      write(value);
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    map<U>(fn: (value: T) => U): Observable<U> {
      const derived = create<U>(fn(current), { kind: "derived", inputs: { x: self }, user: true }, { readOnly: true });
      self.subscribe((value) => feed(derived, fn(value)));
      return derived;
    },
  };
  writers.set(self, write);
  // Frozen: a page cannot replace `get`, `set` or `subscribe` on an observable it was handed (kit-guardian P1 B8).
  return track(Object.freeze(self), node);
}

// Computed observables are updated by whoever computed them, through a private writer.
const writers = new WeakMap<object, (value: never) => void>();
export function feed<T>(obs: Observable<T>, value: T): void {
  const write = writers.get(obs) as ((value: T) => void) | undefined;
  if (!write) throw new TypeError("not a Kit observable");
  write(value);
}

/** Public: a free observable. Fine for UI state; the verifier refuses a readout that depends on one. */
export function observable<T>(initial: T, options: Omit<ObservableOptions<T>, "readOnly"> = {}): Observable<T> {
  return create(initial, { kind: "free" }, options);
}

export { isObservable, nodeOf };
