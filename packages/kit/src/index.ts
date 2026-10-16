// The public surface of Kit v0, exposed as window.Synapse by the IIFE bundle. A behaviour change bumps KIT_VERSION
// (and the dist folder), which marks stored environments stale (hard constraint 6).

import * as bridge from "./bridge";
import { environment } from "./environment";
import { observable, isObservable } from "./observable";
import { readout } from "./readout";
import { hookes } from "./science_hookes";
import { slider } from "./slider";
import { KIT_VERSION } from "./manifest";

export const components = { observable, environment, slider, readout, hookes, bridge };

export const Synapse = { version: KIT_VERSION, isObservable, ...components };

export type { Observable } from "./observable";
export type { Environment } from "./environment";
export { KIT_VERSION, manifestEntries } from "./manifest";
