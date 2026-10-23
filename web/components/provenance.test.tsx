import { describe, expect, it } from "vitest";
import type { CheckedSummary } from "@synapse/schema";
import { checkedLines } from "./Provenance";

const base: CheckedSummary = {
  layers: ["postprocess", "scan", "render"],
  controlsExercised: 1,
  gridPoints: 0,
  referenceCases: 0,
  readouts: 1,
  models: [],
  limits: "x",
};

describe("checkedLines", () => {
  it("says in plain words that the wording layer was a second model's reading and not a proof", () => {
    const line = checkedLines({ ...base, layers: [...base.layers, "wording"] })[0];
    expect(line).toContain("read by a second model");
    expect(line).toContain("not a proof");
  });

  it("does not mention a second reader when the layer was not claimed", () => {
    expect(checkedLines(base)[0]).not.toContain("second model");
  });

  it("shows a layer name it has no words for as it is, rather than hiding it", () => {
    expect(checkedLines({ ...base, layers: ["scan", "brand_new_layer"] })[0]).toContain("brand_new_layer");
  });
});
