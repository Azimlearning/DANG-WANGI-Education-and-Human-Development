// chemistry.cell_voltage: the standard cell voltage of a voltaic cell, E0 cell = E0 (cathode) - E0 (anode) (Electrochemistry: the chemical cell). The cathode is the positive
// terminal (the more positive electrode potential), the anode the negative terminal. Potentials are standard electrode potentials in volts, from -3.1 V to +3.0 V.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.cell_voltage",
  exportName: "cellVoltage",
  inputs: { cathode_potential: { unit: "V", min: -3.1, max: 3 } },
  params: { anode_potential: { unit: "V", min: -3.1, max: 3 } },
  output: { unit: "V" },
  fn: ({ cathode_potential, anode_potential }) => (cathode_potential as number) - (anode_potential as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from E0 cell = E0 (cathode) - E0 (anode). The first case is the textbook's Daniell cell (copper +0.34 V, zinc -0.76 V gives +1.10 V).
  reference: [
    { args: { cathode_potential: 0.34, anode_potential: -0.76 }, expected: 1.1, tolerance: 1e-9, derivation: "(+0.34) - (-0.76) = +1.10 V (Daniell cell)" },
    { args: { cathode_potential: 0.8, anode_potential: 0.34 }, expected: 0.46, tolerance: 1e-9, derivation: "0.80 - 0.34 = 0.46 V" },
    { args: { cathode_potential: 0.34, anode_potential: 0.34 }, expected: 0, tolerance: 1e-12, derivation: "the same electrode potential on both sides gives no voltage" },
    { args: { cathode_potential: -0.76, anode_potential: 0.34 }, expected: -1.1, tolerance: 1e-9, derivation: "a positive terminal that is less positive gives a negative voltage" },
    { args: { cathode_potential: 0.8, anode_potential: -0.76 }, expected: 1.56, tolerance: 1e-9, derivation: "0.80 - (-0.76) = 1.56 V" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "increasing", arg: "cathode_potential" },
    { kind: "decreasing", arg: "anode_potential" },
  ],
  grid: { cathode_potential: [-0.76, -0.13, 0.34, 0.8], anode_potential: [-0.76, 0.34, 0.8] },
};

export function cellVoltage(options: { cathode_potential: Observable<number>; anode_potential: number }): Observable<number> {
  return model(spec, { anode_potential: options.anode_potential }, { cathode_potential: options.cathode_potential });
}
