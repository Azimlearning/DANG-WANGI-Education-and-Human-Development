import { describe, expect, it } from "vitest";
import { nextShown } from "./pace";

describe("nextShown: the bar moves one stage at a time, forward only", () => {
  it("steps toward the real stage one stage per call", () => {
    expect(nextShown("reading", "ready")).toBe("explaining");
    expect(nextShown("explaining", "ready")).toBe("planning");
    expect(nextShown("planning", "ready")).toBe("checking");
    expect(nextShown("checking", "ready")).toBe("ready");
  });
  it("stays where it is once caught up, and never goes back", () => {
    expect(nextShown("planning", "planning")).toBe("planning");
    expect(nextShown("checking", "reading")).toBe("checking");
    expect(nextShown("ready", "ready")).toBe("ready");
  });
});
