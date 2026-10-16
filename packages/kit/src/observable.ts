// Kit v0 core: a tiny observable. The Kit API is ASSUMED (A-2): `readout` accepts only observables, so a number can never
// be typed by hand into a readout (the generator cannot fake a result; L1 in P1 makes that check structural).

export interface Observable<T> {
  readonly __observable: true;
  get(): T;
  set(value: T): void;
  subscribe(listener: (value: T) => void): () => void;
  map<U>(fn: (value: T) => U): Observable<U>;
}

export interface ObservableOptions<T> {
  /** Applied to every value written, including the initial one (a slider clamps here). */
  transform?: (value: T) => T;
}

export function observable<T>(initial: T, options: ObservableOptions<T> = {}): Observable<T> {
  const transform = options.transform ?? ((v: T) => v);
  let current = transform(initial);
  const listeners = new Set<(value: T) => void>();
  const self: Observable<T> = {
    __observable: true,
    get: () => current,
    set(value: T) {
      const next = transform(value);
      if (Object.is(next, current)) return;
      current = next;
      for (const listener of [...listeners]) listener(current);
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    map<U>(fn: (value: T) => U): Observable<U> {
      const derived = observable<U>(fn(current));
      // Derived values are recomputed from the source and cannot be written directly.
      const write = derived.set;
      self.subscribe((value) => write(fn(value)));
      return {
        ...derived,
        set() {
          throw new TypeError("a derived observable is read-only");
        },
      };
    },
  };
  return self;
}

export function isObservable(value: unknown): value is Observable<unknown> {
  return typeof value === "object" && value !== null && (value as { __observable?: unknown }).__observable === true;
}
