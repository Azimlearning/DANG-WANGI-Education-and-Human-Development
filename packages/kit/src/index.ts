// The public surface of Kit 0.1.0, exposed as window.Synapse by the IIFE bundle (build.mjs defines it non-writable and non-configurable).
// The object and its bridge are frozen so generated content cannot replace a component. A behaviour change bumps KIT_VERSION (and the
// dist folder), which marks stored environments stale; the build refuses to change a locked version's bytes (kit-lock.json), D-16.

import { audit, seal } from "./audit";
import { lockdown } from "./lockdown";
import { startWatch } from "./watch";
import { error, event, installErrorHandlers, ready } from "./bridge";
import { constant } from "./constant";
import { conceptCheck } from "./concept_check";
import { convert } from "./convert";
import { environment } from "./environment";
import { experiment } from "./experiment";
import { graph } from "./graph";
import { hintLadder } from "./hints";
import { massHanger } from "./mass_hanger";
import { KIT_VERSION } from "./manifest";
import { observable } from "./observable";
import { predictCard } from "./predict_card";
import { readout } from "./readout";
import { reset } from "./reset";
import { springScene } from "./scene";
import { hookes } from "./science/hookes";
import { magnification } from "./science/magnification";
import { surfaceAreaToVolume } from "./science/sa_to_v";
import { netPhotosynthesis } from "./science/photosynthesis";
import { moles } from "./science/moles";
import { waveSpeed } from "./science/wave_speed";
import { newtonSecond } from "./science/newton_second";
import { cardiacOutput } from "./science/cardiac_output";
import { percentChangeMass } from "./science/mass_change";
import { ph } from "./science/ph";
import { gasVolume } from "./science/gas_volume";
import { titration } from "./science/titration";
import { dilution } from "./science/dilution";
import { heatEnergy } from "./science/heat_energy";
import { averageRate } from "./science/average_rate";

import { ohm } from "./science/ohm";
import { pressureDepth } from "./science/pressure_depth";
import { titrationEndpoint } from "./science/titration_endpoint";
import { titrationScene } from "./titration_scene";
import { valve } from "./valve";
import { slider } from "./slider";
import { stepper } from "./stepper";
import { table } from "./table";
import { text } from "./text";
import { workedSolution } from "./worked_solution";

// Reporting ready also starts the runtime self-check, so every Environment that reaches the student is being watched.
const readyAndWatch = (): void => {
  ready();
  startWatch();
};
const bridge = Object.freeze({ ready: readyAndWatch, event, error, installErrorHandlers });

export const components = { observable, environment, slider, massHanger, springScene, valve, titrationScene, titrationEndpoint, readout, reset, graph, table, stepper, experiment, hintLadder, conceptCheck, predictCard, workedSolution, text, constant, convert, hookes, ohm, pressureDepth, magnification, surfaceAreaToVolume, netPhotosynthesis, moles, titration, dilution, heatEnergy, averageRate, waveSpeed, newtonSecond, cardiacOutput, percentChangeMass, ph, gasVolume, bridge };

export const Synapse = Object.freeze({ version: KIT_VERSION, ...components, audit: () => audit(KIT_VERSION) });
seal(Synapse);

export { lockdown };
export type { Observable } from "./observable";
export type { Environment } from "./environment";
export { KIT_VERSION, manifestEntries } from "./manifest";
