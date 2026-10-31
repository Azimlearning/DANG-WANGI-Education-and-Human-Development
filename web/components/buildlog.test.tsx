import { cleanup, render, screen } from "@testing-library/react";
import type { EnvironmentBlock, PlanDraft, StreamEvent } from "@synapse/schema";
import { afterEach, describe, expect, it } from "vitest";
import { turnReducer, type Turn } from "../lib/turns";
import { BuildDetails, BuildLog } from "./BuildLog";

afterEach(cleanup);

const draft: PlanDraft = { title: "Gravity on the planets", goal: "g", pattern: "simulation", note: "n", controls: [], readouts: [], hasGraph: true, hasTable: false, steps: [], components: ["planetPicker", "planetGravity", "graph"] };
const block = { type: "Environment", id: "e1", title: "Gravity on the planets", lane: "compose", label: "kit-verified", html: "<!doctype html><html><body><p>planets</p></body></html>", htmlSha256: "a".repeat(64) } as unknown as EnvironmentBlock;

function play(events: StreamEvent[]): Turn {
  let turns = turnReducer([], { type: "ask", question: "gravity on each planet" });
  for (const event of events) turns = turnReducer(turns, { type: "event", event });
  return turns[0] as Turn;
}

describe("the build log (W18, D-77)", () => {
  it("records every stage, the plan's arrival and the checked page, in order, in the pipeline's words", () => {
    const turn = play([
      { type: "stage", layer: "route", status: "start", note: null },
      { type: "plan", draft },
      { type: "stage", layer: "plan", status: "done", note: "Planned with the Kit: 3 audited parts, 2 science models." },
      { type: "stage", layer: "verify", status: "done", note: "Passed." },
      { type: "environment", block },
    ]);
    expect(turn.log.map((l) => `${l.kind}:${l.layer}:${l.status}`)).toEqual(["stage:route:start", "plan:plan:done", "stage:plan:done", "stage:verify:done", "environment:deliver:done"]);
  });

  it("shows the steps and the Kit parts, folded under 'See how it's built'", () => {
    const turn = play([{ type: "plan", draft }, { type: "stage", layer: "assemble", status: "done", note: "Assembled the page from the Kit's parts." }]);
    render(<BuildLog log={turn.log} draft={draft} open />);
    expect(screen.getByText("See how it's built")).toBeTruthy();
    expect(screen.getByText("Plan ready: Gravity on the planets")).toBeTruthy();
    expect(screen.getByText("Assembled the page from the Kit's parts.")).toBeTruthy();
    expect(screen.getByText("Kit parts: planetPicker, planetGravity, graph")).toBeTruthy();
  });

  it("shows no code before a checked page exists, and then exactly the checked page's HTML", () => {
    const { unmount } = render(<BuildDetails block={null} log={[]} />);
    expect(screen.queryByText(/<!doctype html>/)).toBeNull();
    expect(screen.getByText(/Nothing unchecked is shown or run/)).toBeTruthy();
    unmount();
    render(<BuildDetails block={block} log={[]} />);
    expect(screen.getByText(block.html)).toBeTruthy();
    expect(screen.getByText(/SHA-256 aaaaaaaaaaaa/)).toBeTruthy();
  });
});

describe("the code as it is built (W19, D-79)", () => {
  it("appends the written pieces, starts again on a reset, and keeps the latest status and note", () => {
    const turn = play([
      { type: "code", lane: "free", status: "writing", reset: true, delta: "", note: null },
      { type: "code", lane: "free", status: "writing", reset: false, delta: "<!doctype html>", note: null },
      { type: "code", lane: "free", status: "writing", reset: false, delta: "<p>hi</p>", note: null },
      { type: "code", lane: "free", status: "refused", reset: false, delta: "", note: "Refused by the checker: absolute URL" },
      { type: "code", lane: "free", status: "writing", reset: true, delta: "<!doctype html><p>again", note: "Written once more" },
    ]);
    expect(turn.code).toEqual({ lane: "free", status: "writing", text: "<!doctype html><p>again", note: "Written once more" });
    expect(turn.log.filter((l) => l.kind === "code").map((l) => l.status)).toEqual(["degraded", "start"]);
  });

  it("shows the code as text with where it stands, and never as a page", () => {
    const turn = play([
      { type: "stage", layer: "assemble", status: "start", note: null },
      { type: "code", lane: "compose", status: "unchecked", reset: true, delta: "<!doctype html><script>run()</script>", note: "Assembled" },
    ]);
    const { container } = render(<BuildLog log={turn.log} draft={null} code={turn.code} open />);
    expect(screen.getByText("<!doctype html><script>run()</script>")).toBeTruthy();
    expect(screen.getByText("Assembled from the Kit")).toBeTruthy();
    expect(screen.getByText(/Written, now being checked/)).toBeTruthy();
    expect(container.querySelector("iframe")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
  });
});
