// biology.population_density: the population density of a species from a quadrat sample, the total number of individuals in all the quadrats divided by (the number of
// quadrats x the area of one quadrat) (Ecosystem: estimation of population size). Individuals per square metre.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "biology.population_density",
  exportName: "populationDensity",
  inputs: { total_count: { unit: "individuals", min: 0 } },
  params: { quadrats: { unit: "quadrats", min: 0, exclusive: true }, quadrat_area: { unit: "m2", min: 0, exclusive: true } },
  output: { unit: "per m2" },
  fn: ({ total_count, quadrats, quadrat_area }) => (total_count as number) / ((quadrats as number) * (quadrat_area as number)),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from the textbook's density formula. Ten quadrats of one square metre each are the textbook's field study.
  reference: [
    { args: { total_count: 45, quadrats: 10, quadrat_area: 1 }, expected: 4.5, tolerance: 1e-9, derivation: "45 / (10 x 1) = 4.5 individuals per m2" },
    { args: { total_count: 20, quadrats: 5, quadrat_area: 0.25 }, expected: 16, tolerance: 1e-9, derivation: "20 / (5 x 0.25) = 16 individuals per m2" },
    { args: { total_count: 0, quadrats: 10, quadrat_area: 1 }, expected: 0, tolerance: 1e-12, derivation: "no individuals counted means a density of zero" },
    { args: { total_count: 120, quadrats: 10, quadrat_area: 4 }, expected: 3, tolerance: 1e-9, derivation: "120 / (10 x 4) = 3 individuals per m2" },
    { args: { total_count: 7, quadrats: 10, quadrat_area: 1 }, expected: 0.7, tolerance: 1e-9, derivation: "7 / (10 x 1) = 0.7 individuals per m2" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "total_count" },
    { kind: "decreasing", arg: "quadrats" },
    { kind: "decreasing", arg: "quadrat_area" },
    { kind: "homogeneous", arg: "total_count", degree: 1 },
    { kind: "homogeneous", arg: "quadrats", degree: -1 },
    { kind: "homogeneous", arg: "quadrat_area", degree: -1 },
  ],
  grid: { total_count: [5, 20, 45, 120], quadrats: [5, 10, 20], quadrat_area: [0.25, 1, 4] },
};

export function populationDensity(options: { total_count: Observable<number>; quadrats: number; quadrat_area: number }): Observable<number> {
  return model(spec, { quadrats: options.quadrats, quadrat_area: options.quadrat_area }, { total_count: options.total_count });
}
