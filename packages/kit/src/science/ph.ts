// chemistry.ph_from_h: pH = -log10 of the hydrogen ion concentration in mol/dm3 (Acids, Bases and Salts). UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.ph_from_h",
  exportName: "ph",
  inputs: { h_conc: { unit: "mol/dm3", min: 0, exclusive: true } },
  params: {},
  output: { unit: "pH" },
  // `0 -` keeps the pH of a 1 mol/dm3 solution as 0, not -0.
  fn: ({ h_conc }) => 0 - Math.log10(h_conc as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Hand-computed: a power of ten has a whole-number pH.
  reference: [
    { args: { h_conc: 0.1 }, expected: 1, tolerance: 1e-9, derivation: "0.1 = 10^-1, so pH 1" },
    { args: { h_conc: 0.001 }, expected: 3, tolerance: 1e-9, derivation: "0.001 = 10^-3, so pH 3" },
    { args: { h_conc: 1e-7 }, expected: 7, tolerance: 1e-9, derivation: "10^-7, so pH 7 (pure water)" },
    { args: { h_conc: 1 }, expected: 0, tolerance: 1e-9, derivation: "1 = 10^0, so pH 0" },
    { args: { h_conc: 0.01 }, expected: 2, tolerance: 1e-9, derivation: "0.01 = 10^-2, so pH 2" },
    { args: { h_conc: 0.002 }, expected: 2.69897, tolerance: 1e-5, derivation: "2 x 10^-3: pH = 3 - log10(2) = 3 - 0.30103 = 2.69897" },
    { args: { h_conc: 3e-8 }, expected: 7.52288, tolerance: 1e-5, derivation: "3 x 10^-8: pH = 8 - log10(3) = 8 - 0.47712 = 7.52288 (above 7, a weak alkali side)" },
  ],
  properties: [{ kind: "finite" }, { kind: "decreasing", arg: "h_conc" }],
  grid: { h_conc: [1e-9, 1e-7, 1e-4, 1e-3, 1e-2, 0.1, 1] },
};

export function ph(options: { h_conc: Observable<number> }): Observable<number> {
  return model(spec, {}, { h_conc: options.h_conc });
}
