// The artifact iframe is sandbox="allow-scripts" and NOTHING else, never allow-same-origin (hard constraint 2). The constant is
// pinned by a test; the iframe component takes its attribute only from here.
export const SANDBOX = "allow-scripts";

/** Messages the Kit's bridge posts to the host (names kept from Synapse v3). */
/** The parts of a lab report the Kit reports (W5b). Text only; the host re-checks every size because it cannot trust what crosses the frame boundary. */
export type LabPart =
  | { part: "experiment"; fields: [string, string][] }
  | { part: "steps"; steps: string[] }
  | { part: "table"; caption: string; columns: { label: string; unit: string }[]; rows: string[][] };

export type BridgeMessage =
  | { type: "synapse_ready" }
  | ({ type: "synapse_lab" } & LabPart)
  | { type: "synapse_event"; control: string; value: number | string | boolean }
  | { type: "synapse_error"; message: string }
  | { type: "synapse_violation"; problems: string[] };

const isStr = (v: unknown, max: number): v is string => typeof v === "string" && v.length <= max;
const strings = (v: unknown, count: number, max: number): string[] | null => {
  if (!Array.isArray(v) || v.length > count) return null;
  // A plain loop, not `every`: `every` skips the holes of a sparse array, which survive structured cloning.
  for (let i = 0; i < v.length; i++) if (!isStr(v[i], max)) return null;
  return v as string[];
};

export function parseLabPart(d: Record<string, unknown>): LabPart | null {
  if (d.part === "experiment") {
    if (!Array.isArray(d.fields) || d.fields.length > 8) return null;
    const fields: [string, string][] = [];
    for (const f of d.fields) {
      if (!Array.isArray(f) || f.length !== 2 || !isStr(f[0], 80) || !isStr(f[1], 400)) return null;
      fields.push([f[0], f[1]]);
    }
    return { part: "experiment", fields };
  }
  if (d.part === "steps") {
    const steps = strings(d.steps, 8, 300);
    return steps ? { part: "steps", steps } : null;
  }
  if (d.part === "table") {
    if (!isStr(d.caption, 120) || !Array.isArray(d.columns) || d.columns.length < 1 || d.columns.length > 6 || !Array.isArray(d.rows) || d.rows.length > 30) return null;
    const columns: { label: string; unit: string }[] = [];
    for (const c of d.columns) {
      if (typeof c !== "object" || c === null) return null;
      const { label, unit } = c as Record<string, unknown>;
      if (!isStr(label, 60) || !isStr(unit, 16)) return null;
      columns.push({ label, unit });
    }
    const rows: string[][] = [];
    for (const r of d.rows) {
      const cells = strings(r, columns.length, 40);
      if (!cells || cells.length !== columns.length) return null;
      rows.push(cells);
    }
    return { part: "table", caption: d.caption, columns, rows };
  }
  return null;
}

export function parseBridgeMessage(data: unknown): BridgeMessage | null {
  if (typeof data !== "object" || data === null) return null;
  const d = data as Record<string, unknown>;
  if (d.type === "synapse_lab") {
    const part = parseLabPart(d);
    return part ? { type: "synapse_lab", ...part } : null;
  }
  if (d.type === "synapse_ready") return { type: "synapse_ready" };
  if (d.type === "synapse_error" && typeof d.message === "string") return { type: "synapse_error", message: d.message.slice(0, 300) };
  if (d.type === "synapse_violation") {
    const problems = Array.isArray(d.problems) ? d.problems.filter((p): p is string => typeof p === "string").slice(0, 5) : [];
    return { type: "synapse_violation", problems };
  }
  if (
    d.type === "synapse_event" &&
    typeof d.control === "string" &&
    (typeof d.value === "number" || typeof d.value === "string" || typeof d.value === "boolean")
  ) {
    return { type: "synapse_event", control: d.control, value: d.value };
  }
  return null;
}
