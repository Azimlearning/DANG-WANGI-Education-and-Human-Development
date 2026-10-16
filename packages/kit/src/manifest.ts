// The Kit manifest: one entry per micro-component, generated into dist/<semver>/manifest.json. It is the second seam (Kit to API). Every
// entry needs a written precondition and a one-line doc sized for a prompt (hard constraint 6). Science models also carry units, domain,
// the id that keys their independent Python reference, and the citation status.

import type { Quantity, ScienceSpec } from "./science/spec";
import { spec as hookesSpec } from "./science/hookes";
import { spec as ohmSpec } from "./science/ohm";
import { spec as pressureSpec } from "./science/pressure_depth";

export type KitKind = "ui" | "scene" | "interaction" | "science" | "pedagogy" | "core";

export interface ManifestEntry {
  /** The property name on window.Synapse. */
  id: string;
  kind: KitKind;
  signature: string;
  /** When the component may be used. A science micro-model's precondition names its domain and units. */
  precondition: string;
  doc: string;
  /** One sentence for retrieval: when to reach for this component (D-23). */
  useWhen?: string;
  /** Science micro-models only. */
  modelId?: string;
  /** Science micro-models only: names, units and domain of the inputs and parameters, and the output unit, generated from the spec. */
  inputs?: Record<string, Quantity>;
  params?: Record<string, Quantity>;
  output?: { unit: string };
  citation?: string;
  units?: Record<string, string>;
}

/** The fields of a manifest entry that come from the science spec, so the plan checks read the domain from the built manifest. */
const fromSpec = (spec: ScienceSpec) => ({ inputs: spec.inputs, params: spec.params, output: spec.output });

export const KIT_VERSION = "0.1.0";

export const manifestEntries: ManifestEntry[] = [
  {
    id: "observable",
    kind: "core",
    signature: "observable<T>(initial: T, {transform?: (v: T) => T}?): Observable<T>",
    precondition: "UI state only. A readout cannot show a value that depends on a free observable, or on arithmetic you wrote with map.",
    doc: "A value you can get, set and subscribe to. Not a source of science: the verifier refuses a readout that depends on one.",
    useWhen: "Use for UI-only state the student toggles; never for a quantity that a readout shows.",
  },
  {
    id: "environment",
    kind: "ui",
    signature: "environment({title: string, note: string, stageText?: string, into?: HTMLElement}): Environment",
    precondition: "Called once, before any other component, in a page whose first script is the Kit.",
    doc: "Mounts the title, a study-note card, a stage, controls and readouts. stageText is the screen-reader text for the stage. Returns the env passed to the other components.",
    useWhen: "Use first, once, on every page: it mounts the title, study note, stage, controls and readouts.",
  },
  {
    id: "slider",
    kind: "interaction",
    signature: "slider(env, {id, label, unit, min, max, value, step?, grid?}): Observable<number>",
    precondition: "min is below max; id is unique in the page; grid is an integer from 1 to 200 (default 10). The returned observable clamps to [min, max].",
    doc: "A labelled range control. The verifier tries every grid position and both extremes. Reports each change to the host.",
    useWhen: "Use for any quantity the student varies continuously: a load, a voltage, a depth, a temperature.",
  },
  {
    id: "readout",
    kind: "ui",
    signature: "readout(env, {label, unit, value: Observable<number>, digits?}): HTMLOutputElement",
    precondition: "value derives from a control through a science model (a unit change with convert is allowed). A declared constant alone, a free observable and arithmetic written in the page are refused.",
    doc: "Shows an observable's current value with its unit, announced politely to screen readers. Do not edit the element.",
    useWhen: "Use to show a computed or measured quantity that a science model produced, with its unit.",
  },
  {
    id: "reset",
    kind: "interaction",
    signature: "reset(env, {label?: string}?): HTMLButtonElement",
    precondition: "Create it on any page with at least one slider; it restores every control to its starting value when pressed.",
    doc: "A button that returns every control to its starting value. The readouts follow.",
    useWhen: "Use whenever a page has sliders and the student may want to start again.",
  },
  {
    id: "table",
    kind: "ui",
    signature: "table(env, {caption: string, columns: {label, unit, value: Observable<number>, digits?}[]}): HTMLTableElement",
    precondition: "1 to 6 columns, each a Kit observable that derives from a control through a science model. At most 30 rows.",
    doc: "A results table with Record and Clear buttons. Record appends one row of the columns' current values.",
    useWhen: "Use when the student should record readings across several settings to see a pattern, as in an experiment.",
  },
  {
    id: "graph",
    kind: "ui",
    signature: "graph(env, {title: string, x: Observable<number>, y: Observable<number>, yLabel: string, yUnit: string, digits?: number}): SVGSVGElement",
    precondition: "x is a slider created before the graph; y derives from controls through a science model. Create it after every slider so it redraws when they change.",
    doc: "Plots y against the whole range of x, with a marker at the current value and a hidden table as the text equivalent.",
    useWhen: "Use to show how one quantity depends on another over the whole range of a slider, with a marker at the current value.",
  },
  {
    id: "stepper",
    kind: "pedagogy",
    signature: "stepper(env, {steps: string[]}): HTMLOListElement",
    precondition: "1 to 8 steps. Any number in a step must be a slider value, a model setting or a declared constant.",
    doc: "The procedure of an experiment as an ordered list.",
    useWhen: "Use to give the student the procedure of an experiment as short ordered steps.",
  },
  {
    id: "experiment",
    kind: "pedagogy",
    signature: "experiment(env, {aim, hypothesis, independent, dependent, controlled: string[], apparatus: string[]}): HTMLElement",
    precondition: "Every field has text; at most 6 controlled variables and 8 apparatus items. Numbers in it must be backed like any sentence.",
    doc: "The practical-work card: aim, hypothesis, what is changed, what is measured, what is kept the same, what is used.",
    useWhen: "Use for a virtual experiment (Amali) so the student sees the aim, the variables and the apparatus before experimenting.",
  },
  {
    id: "text",
    kind: "ui",
    signature: "text(env, content: string): HTMLParagraphElement",
    precondition: "Any number in content must be a model parameter, a control range or grid value, a declared constant, or a step marker such as 'Step 2'.",
    doc: "The sanctioned way to write a sentence on the stage. The element cannot be edited afterwards.",
    useWhen: "Use for a short explanatory sentence on the stage; any number in it must be a slider value, a constant or a model setting.",
  },
  {
    id: "constant",
    kind: "core",
    signature: "constant(value: number, {label: string, unit: string}): Observable<number>",
    precondition: "A fixed quantity of the experiment (a spring's constant). value is finite.",
    doc: "Declares a fixed quantity so it can feed a model or a readout and be treated as backed.",
    useWhen: "Use to give a model a fixed given value (a spring constant, a resistor, a liquid density) that the page also states.",
  },
  {
    id: "convert",
    kind: "core",
    signature: "convert(source: Observable<number>, from: string, to: string): Observable<number>",
    precondition: "from and to are known units of the same dimension (m, cm, mm, km, kg, g, s, ms, min, Pa, kPa, A, mA, J, kJ, N, V, mV, W).",
    doc: "A unit change by a known factor, the only arithmetic allowed on a model's output.",
    useWhen: "Use to show a model's output in a different unit of the same kind (Pa to kPa, m to cm).",
  },
  {
    id: "hookes",
    kind: "science",
    signature: "hookes({k: number, load: Observable<number>}): Observable<number>",
    precondition: "Within the elastic limit. Domain: k above 0 N/m, load 0 N or more. Units: load N, k N/m, extension m.",
    doc: "Hooke's law: extension = load / k. A read-only observable that follows the load.",
    useWhen: "Use for a spring or elastic material stretching under a load, within the elastic limit (Force and Elasticity).",
    modelId: "mechanics.hookes",
    citation: "UNVERIFIED (corpus not loaded until P2)",
    units: { load: "N", k: "N/m", output: "m" },
    ...fromSpec(hookesSpec),
  },
  {
    id: "ohm",
    kind: "science",
    signature: "ohm({voltage: Observable<number>, resistance: Observable<number>}): Observable<number>",
    precondition: "An ohmic conductor at steady state. Domain: voltage 0 V or more, resistance above 0 ohm. Units: voltage V, resistance ohm, current A.",
    doc: "Ohm's law: current = voltage / resistance. A read-only observable that follows both inputs.",
    useWhen: "Use for the current through a resistor given the voltage and resistance (Electricity).",
    modelId: "electricity.ohm",
    citation: "UNVERIFIED (corpus not loaded until P2)",
    units: { voltage: "V", resistance: "ohm", output: "A" },
    ...fromSpec(ohmSpec),
  },
  {
    id: "pressureDepth",
    kind: "science",
    signature: "pressureDepth({depth: Observable<number>, density: number, g: number}): Observable<number>",
    precondition: "A liquid of uniform density at rest. Domain: depth 0 m or more, density and g above 0. Units: depth m, density kg/m3, g m/s2, pressure Pa (gauge).",
    doc: "Liquid pressure: P = depth x density x g. g is recorded so the student sees whether 9.81 or 10 was used.",
    useWhen: "Use for the pressure of a liquid at a depth (Forces and Pressure).",
    modelId: "fluids.pressure_depth",
    citation: "UNVERIFIED (corpus not loaded until P2)",
    units: { depth: "m", density: "kg/m3", g: "m/s2", output: "Pa" },
    ...fromSpec(pressureSpec),
  },
  {
    id: "bridge",
    kind: "core",
    signature: "bridge.ready() | bridge.event(control, value) | bridge.error(message) | bridge.installErrorHandlers()",
    precondition: "Call bridge.ready() once after the components are mounted.",
    doc: "Messages to the host: synapse_ready after first paint, synapse_event on control change, synapse_error on a caught error.",
    useWhen: "Use once at the end of the page to tell the host the Environment is ready.",
  },
];
