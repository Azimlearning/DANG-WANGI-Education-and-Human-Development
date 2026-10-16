// The Kit manifest: one entry per micro-component, generated into dist/<semver>/manifest.json. It is the second seam
// (Kit to API). Every entry needs a written precondition and a one-line doc sized for a prompt (hard constraint 6).

export type KitKind = "ui" | "scene" | "interaction" | "science" | "pedagogy" | "core";

export interface ManifestEntry {
  /** The property name on window.Synapse. */
  id: string;
  kind: KitKind;
  signature: string;
  /** When the component may be used. A science micro-model's precondition names its domain and units. */
  precondition: string;
  doc: string;
  /** Science micro-models only. */
  citation?: string;
}

export const KIT_VERSION = "0.0.1";

export const manifestEntries: ManifestEntry[] = [
  {
    id: "observable",
    kind: "core",
    signature: "observable<T>(initial: T): Observable<T>",
    precondition: "Any value that changes over time and is shown or used by another component.",
    doc: "A value you can get, set, subscribe to and map. Readouts only accept observables.",
  },
  {
    id: "environment",
    kind: "ui",
    signature: "environment({title: string, note: string}): Environment",
    precondition: "Called once, before any other component, in a page with a body.",
    doc: "Mounts the title, a study-note card, a stage, controls and readouts. Returns the env passed to slider and readout.",
  },
  {
    id: "slider",
    kind: "interaction",
    signature: "slider(env, {id, label, unit, min, max, value, step?}): Observable<number>",
    precondition: "min is below max; id is unique in the page. The returned observable clamps to [min, max].",
    doc: "A labelled range control. Reports each change to the host.",
  },
  {
    id: "readout",
    kind: "ui",
    signature: "readout(env, {label, unit, value: Observable<number>, digits?}): HTMLOutputElement",
    precondition: "value is an observable. A plain number throws.",
    doc: "Shows an observable's current value with its unit, announced politely to screen readers.",
  },
  {
    id: "hookes",
    kind: "science",
    signature: "hookes({k: number, load: Observable<number>}): Observable<number>",
    precondition: "Domain: k above 0 N/m, load 0 N or more, within the elastic limit. Units: load N, k N/m, extension m.",
    doc: "Hooke's law: extension = load / k. Returns a read-only observable that follows the load.",
    citation: "UNVERIFIED (corpus not loaded until P2)",
  },
  {
    id: "bridge",
    kind: "core",
    signature: "bridge.ready() | bridge.event(control, value) | bridge.error(message) | bridge.installErrorHandlers()",
    precondition: "Call bridge.ready() once after the components are mounted.",
    doc: "Messages to the host: synapse_ready after first paint, synapse_event on control change, synapse_error on a caught error.",
  },
];
