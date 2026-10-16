// The Kit manifest: one entry per micro-component, generated into dist/<semver>/manifest.json. It is the second seam (Kit to API). Every
// entry needs a written precondition and a one-line doc sized for a prompt (hard constraint 6). Science models also carry units, domain,
// the id that keys their independent Python reference, and the citation status.

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
  modelId?: string;
  citation?: string;
  units?: Record<string, string>;
}

export const KIT_VERSION = "0.1.0";

export const manifestEntries: ManifestEntry[] = [
  {
    id: "observable",
    kind: "core",
    signature: "observable<T>(initial: T, {transform?: (v: T) => T}?): Observable<T>",
    precondition: "UI state only. A readout cannot show a value that depends on a free observable, or on arithmetic you wrote with map.",
    doc: "A value you can get, set and subscribe to. Not a source of science: the verifier refuses a readout that depends on one.",
  },
  {
    id: "environment",
    kind: "ui",
    signature: "environment({title: string, note: string, stageText?: string, into?: HTMLElement}): Environment",
    precondition: "Called once, before any other component, in a page whose first script is the Kit.",
    doc: "Mounts the title, a study-note card, a stage, controls and readouts. stageText is the screen-reader text for the stage. Returns the env passed to the other components.",
  },
  {
    id: "slider",
    kind: "interaction",
    signature: "slider(env, {id, label, unit, min, max, value, step?, grid?}): Observable<number>",
    precondition: "min is below max; id is unique in the page; grid is an integer from 1 to 200 (default 10). The returned observable clamps to [min, max].",
    doc: "A labelled range control. The verifier tries every grid position and both extremes. Reports each change to the host.",
  },
  {
    id: "readout",
    kind: "ui",
    signature: "readout(env, {label, unit, value: Observable<number>, digits?}): HTMLOutputElement",
    precondition: "value derives from a control through a science model (a unit change with convert is allowed). A declared constant alone, a free observable and arithmetic written in the page are refused.",
    doc: "Shows an observable's current value with its unit, announced politely to screen readers. Do not edit the element.",
  },
  {
    id: "reset",
    kind: "interaction",
    signature: "reset(env, {label?: string}?): HTMLButtonElement",
    precondition: "Create it on any page with at least one slider; it restores every control to its starting value when pressed.",
    doc: "A button that returns every control to its starting value. The readouts follow.",
  },
  {
    id: "table",
    kind: "ui",
    signature: "table(env, {caption: string, columns: {label, unit, value: Observable<number>, digits?}[]}): HTMLTableElement",
    precondition: "1 to 6 columns, each a Kit observable that derives from a control through a science model. At most 30 rows.",
    doc: "A results table with Record and Clear buttons. Record appends one row of the columns' current values.",
  },
  {
    id: "graph",
    kind: "ui",
    signature: "graph(env, {title: string, x: Observable<number>, y: Observable<number>, yLabel: string, yUnit: string, digits?: number}): SVGSVGElement",
    precondition: "x is a slider created before the graph; y derives from controls through a science model. Create it after every slider so it redraws when they change.",
    doc: "Plots y against the whole range of x, with a marker at the current value and a hidden table as the text equivalent.",
  },
  {
    id: "text",
    kind: "ui",
    signature: "text(env, content: string): HTMLParagraphElement",
    precondition: "Any number in content must be a model parameter, a control range or grid value, a declared constant, or a step marker such as 'Step 2'.",
    doc: "The sanctioned way to write a sentence on the stage. The element cannot be edited afterwards.",
  },
  {
    id: "constant",
    kind: "core",
    signature: "constant(value: number, {label: string, unit: string}): Observable<number>",
    precondition: "A fixed quantity of the experiment (a spring's constant). value is finite.",
    doc: "Declares a fixed quantity so it can feed a model or a readout and be treated as backed.",
  },
  {
    id: "convert",
    kind: "core",
    signature: "convert(source: Observable<number>, from: string, to: string): Observable<number>",
    precondition: "from and to are known units of the same dimension (m, cm, mm, km, kg, g, s, ms, min, Pa, kPa, A, mA, J, kJ, N, V, mV, W).",
    doc: "A unit change by a known factor, the only arithmetic allowed on a model's output.",
  },
  {
    id: "hookes",
    kind: "science",
    signature: "hookes({k: number, load: Observable<number>}): Observable<number>",
    precondition: "Within the elastic limit. Domain: k above 0 N/m, load 0 N or more. Units: load N, k N/m, extension m.",
    doc: "Hooke's law: extension = load / k. A read-only observable that follows the load.",
    modelId: "mechanics.hookes",
    citation: "UNVERIFIED (corpus not loaded until P2)",
    units: { load: "N", k: "N/m", output: "m" },
  },
  {
    id: "ohm",
    kind: "science",
    signature: "ohm({voltage: Observable<number>, resistance: Observable<number>}): Observable<number>",
    precondition: "An ohmic conductor at steady state. Domain: voltage 0 V or more, resistance above 0 ohm. Units: voltage V, resistance ohm, current A.",
    doc: "Ohm's law: current = voltage / resistance. A read-only observable that follows both inputs.",
    modelId: "electricity.ohm",
    citation: "UNVERIFIED (corpus not loaded until P2)",
    units: { voltage: "V", resistance: "ohm", output: "A" },
  },
  {
    id: "pressureDepth",
    kind: "science",
    signature: "pressureDepth({depth: Observable<number>, density: number, g: number}): Observable<number>",
    precondition: "A liquid of uniform density at rest. Domain: depth 0 m or more, density and g above 0. Units: depth m, density kg/m3, g m/s2, pressure Pa (gauge).",
    doc: "Liquid pressure: P = depth x density x g. g is recorded so the student sees whether 9.81 or 10 was used.",
    modelId: "fluids.pressure_depth",
    citation: "UNVERIFIED (corpus not loaded until P2)",
    units: { depth: "m", density: "kg/m3", g: "m/s2", output: "Pa" },
  },
  {
    id: "bridge",
    kind: "core",
    signature: "bridge.ready() | bridge.event(control, value) | bridge.error(message) | bridge.installErrorHandlers()",
    precondition: "Call bridge.ready() once after the components are mounted.",
    doc: "Messages to the host: synapse_ready after first paint, synapse_event on control change, synapse_error on a caught error.",
  },
];
