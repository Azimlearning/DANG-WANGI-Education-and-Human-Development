// The public surface of Kit v0, exposed as window.Synapse by the IIFE bundle. The object and its bridge are frozen so generated
// content cannot replace a component. A behaviour change bumps KIT_VERSION (and the dist folder), which marks stored environments
// stale; the build refuses to change a locked version's bytes (kit-lock.json), see build.mjs (hard constraint 6).

import { error, event, installErrorHandlers, ready } from "./bridge";
import { environment } from "./environment";
import { observable } from "./observable";
import { readout } from "./readout";
import { hookes } from "./science_hookes";
import { slider } from "./slider";
import { KIT_VERSION } from "./manifest";

const bridge = Object.freeze({ ready, event, error, installErrorHandlers });

export const components = { observable, environment, slider, readout, hookes, bridge };

export const Synapse = Object.freeze({ version: KIT_VERSION, ...components });

export type { Observable } from "./observable";
export type { Environment } from "./environment";
export { KIT_VERSION, manifestEntries } from "./manifest";
