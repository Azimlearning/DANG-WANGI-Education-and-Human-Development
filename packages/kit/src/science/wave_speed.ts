// physics.wave_speed: wave speed v = f x lambda (Waves). Frequency in hertz, wavelength in metres. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.wave_speed",
  exportName: "waveSpeed",
  inputs: { frequency: { unit: "Hz", min: 0, exclusive: true }, wavelength: { unit: "m", min: 0, exclusive: true } },
  params: {},
  output: { unit: "m/s" },
  fn: ({ frequency, wavelength }) => (frequency as number) * (wavelength as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed from v = f lambda.
  reference: [
    { args: { frequency: 50, wavelength: 0.4 }, expected: 20, tolerance: 1e-9, derivation: "50 Hz x 0.4 m = 20 m/s" },
    { args: { frequency: 2, wavelength: 3 }, expected: 6, tolerance: 1e-9, derivation: "2 x 3 = 6 m/s" },
    { args: { frequency: 100, wavelength: 3.4 }, expected: 340, tolerance: 1e-9, derivation: "100 x 3.4 = 340 m/s (about the speed of sound in air)" },
    { args: { frequency: 0.5, wavelength: 4 }, expected: 2, tolerance: 1e-9, derivation: "0.5 x 4 = 2 m/s" },
    { args: { frequency: 10, wavelength: 0.15 }, expected: 1.5, tolerance: 1e-9, derivation: "10 x 0.15 = 1.5 m/s" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "frequency" },
    { kind: "increasing", arg: "wavelength" },
    { kind: "homogeneous", arg: "frequency", degree: 1 },
    { kind: "homogeneous", arg: "wavelength", degree: 1 },
  ],
  grid: { frequency: [0.5, 2, 10, 50, 100], wavelength: [0.15, 0.4, 3, 3.4] },
};

export function waveSpeed(options: { frequency: Observable<number>; wavelength: Observable<number> }): Observable<number> {
  return model(spec, {}, { frequency: options.frequency, wavelength: options.wavelength });
}
