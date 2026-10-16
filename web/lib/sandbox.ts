// The artifact iframe is sandbox="allow-scripts" and NOTHING else, never allow-same-origin (hard constraint 2). The constant is
// pinned by a test; the iframe component takes its attribute only from here.
export const SANDBOX = "allow-scripts";

/** Messages the Kit's bridge posts to the host (names kept from Synapse v3). */
export type BridgeMessage =
  | { type: "synapse_ready" }
  | { type: "synapse_event"; control: string; value: number | string | boolean }
  | { type: "synapse_error"; message: string };

export function parseBridgeMessage(data: unknown): BridgeMessage | null {
  if (typeof data !== "object" || data === null) return null;
  const d = data as Record<string, unknown>;
  if (d.type === "synapse_ready") return { type: "synapse_ready" };
  if (d.type === "synapse_error" && typeof d.message === "string") return { type: "synapse_error", message: d.message.slice(0, 300) };
  if (
    d.type === "synapse_event" &&
    typeof d.control === "string" &&
    (typeof d.value === "number" || typeof d.value === "string" || typeof d.value === "boolean")
  ) {
    return { type: "synapse_event", control: d.control, value: d.value };
  }
  return null;
}
