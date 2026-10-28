import { describe, expect, it } from "vitest";
import { parseBridgeMessage, parseLabPart, SANDBOX } from "./sandbox";

describe("sandbox", () => {
  it("is exactly allow-scripts and nothing else", () => {
    expect(SANDBOX).toBe("allow-scripts");
    expect(SANDBOX.split(/\s+/)).toEqual(["allow-scripts"]);
    expect(SANDBOX).not.toContain("allow-same-origin");
  });
  it("parses the three bridge messages and ignores anything else", () => {
    expect(parseBridgeMessage({ type: "synapse_ready" })).toEqual({ type: "synapse_ready" });
    expect(parseBridgeMessage({ type: "synapse_event", control: "load", value: 3 })).toEqual({ type: "synapse_event", control: "load", value: 3 });
    expect(parseBridgeMessage({ type: "synapse_error", message: "x".repeat(900) })).toMatchObject({ type: "synapse_error" });
    expect((parseBridgeMessage({ type: "synapse_error", message: "x".repeat(900) }) as { message: string }).message).toHaveLength(300);
    expect(parseBridgeMessage({ type: "synapse_event", control: "load", value: { a: 1 } })).toBeNull();
    expect(parseBridgeMessage({ type: "synapse_violation", problems: ["a", 3, "b"] })).toEqual({ type: "synapse_violation", problems: ["a", "b"] });
    expect(parseBridgeMessage({ type: "other" })).toBeNull();
    expect(parseBridgeMessage("synapse_ready")).toBeNull();
    expect(parseBridgeMessage(null)).toBeNull();
  });
});


describe("parseLabPart: holes", () => {
  it("refuses a sparse array of steps or a sparse row, as the offline shell does (structured clone keeps holes)", () => {
    const steps = new Array(3);
    steps[0] = "only the first";
    expect(parseLabPart({ part: "steps", steps })).toBeNull();
    const row = new Array(2);
    row[0] = "1";
    expect(parseLabPart({ part: "table", caption: "c", columns: [{ label: "a", unit: "u" }, { label: "b", unit: "u" }], rows: [row] })).toBeNull();
  });
  it("accepts a step of exactly 300 characters and refuses 301, eight steps and refuses nine", () => {
    expect(parseLabPart({ part: "steps", steps: ["y".repeat(300)] })).not.toBeNull();
    expect(parseLabPart({ part: "steps", steps: ["z".repeat(301)] })).toBeNull();
    expect(parseLabPart({ part: "steps", steps: Array.from({ length: 8 }, () => "s") })).not.toBeNull();
    expect(parseLabPart({ part: "steps", steps: Array.from({ length: 9 }, () => "s") })).toBeNull();
  });
});
