import { describe, expect, it } from "vitest";
import { parseBridgeMessage, SANDBOX } from "./sandbox";

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
    expect(parseBridgeMessage({ type: "other" })).toBeNull();
    expect(parseBridgeMessage("synapse_ready")).toBeNull();
    expect(parseBridgeMessage(null)).toBeNull();
  });
});
