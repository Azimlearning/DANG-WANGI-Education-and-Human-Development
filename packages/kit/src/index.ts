// The public surface of Kit 0.1.0, exposed as window.Synapse by the IIFE bundle (build.mjs defines it non-writable and non-configurable).
// The object and its bridge are frozen so generated content cannot replace a component. A behaviour change bumps KIT_VERSION (and the
// dist folder), which marks stored environments stale; the build refuses to change a locked version's bytes (kit-lock.json), D-16.

import { audit, seal } from "./audit";
import { error, event, installErrorHandlers, ready } from "./bridge";
import { constant } from "./constant";
import { convert } from "./convert";
import { environment } from "./environment";
import { graph } from "./graph";
import { KIT_VERSION } from "./manifest";
import { observable } from "./observable";
import { readout } from "./readout";
import { reset } from "./reset";
import { hookes } from "./science/hookes";
import { ohm } from "./science/ohm";
import { pressureDepth } from "./science/pressure_depth";
import { slider } from "./slider";
import { table } from "./table";
import { text } from "./text";

const bridge = Object.freeze({ ready, event, error, installErrorHandlers });

export const components = { observable, environment, slider, readout, reset, graph, table, text, constant, convert, hookes, ohm, pressureDepth, bridge };

export const Synapse = Object.freeze({ version: KIT_VERSION, ...components, audit: () => audit(KIT_VERSION) });
seal(Synapse);

export type { Observable } from "./observable";
export type { Environment } from "./environment";
export { KIT_VERSION, manifestEntries } from "./manifest";
