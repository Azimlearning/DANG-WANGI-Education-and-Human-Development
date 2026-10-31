import type { EnvironmentBlock, PlanDraft, StreamEvent } from "@synapse/schema";
import { describe, expect, it } from "vitest";
import { STEPS, turnReducer, type Turn } from "./turns";

const block = { type: "Environment", id: "hookes_amali-0123456789ab", title: "Hooke's law" } as unknown as EnvironmentBlock;
const stage = (layer: string, status: "start" | "done" | "degraded", note: string | null = null): StreamEvent => ({ type: "stage", layer, status, note });
const run = (events: StreamEvent[]) => events.reduce<Turn[]>((t, event) => turnReducer(t, { type: "event", event }), turnReducer([], { type: "ask", question: "Why?" }));
const last = (turns: Turn[]): Turn => turns[turns.length - 1] as Turn;
const draft: PlanDraft = { title: "d", goal: "g", pattern: "simulation", note: "n", controls: [], readouts: [], hasGraph: false, hasTable: false, steps: [], components: [] };

describe("turnReducer", () => {
  it("starts an open turn at the first step and numbers turns", () => {
    const two = turnReducer(turnReducer([], { type: "ask", question: "a" }), { type: "ask", question: "b" });
    expect(two.map((t) => t.id)).toEqual([1, 2]);
    expect(last(two)).toMatchObject({ open: true, step: "reading", text: "", block: null });
  });

  it("follows the real pipeline layers forward and never backwards", () => {
    expect(last(run([stage("route", "start"), stage("explain", "start"), stage("plan", "start"), stage("explain", "start"), stage("verify", "start")])).step).toBe("checking");
    expect(last(run([stage("verify", "start"), stage("route", "start")])).step).toBe("checking");
  });

  it("appends the written answer as it streams", () => {
    expect(last(run([{ type: "text_delta", text: "Springs " }, { type: "text_delta", text: "stretch." }])).text).toBe("Springs stretch.");
  });

  it("keeps a draft only until the verified Environment (or a degrade) replaces it", () => {
    expect(last(run([{ type: "plan", draft }])).draft).toEqual(draft);
    expect(last(run([{ type: "plan", draft }, { type: "environment", block }])).draft).toBeNull();
    expect(last(run([{ type: "plan", draft }, stage("verify", "degraded", "Written answer only.")]))).toMatchObject({ draft: null, note: "Written answer only." });
  });

  it("an Environment completes the steps and a library hit is marked as one", () => {
    const t = last(run([{ type: "text_delta", text: "x" }, stage("library", "done", "Found in the library."), { type: "environment", block }]));
    expect(t).toMatchObject({ step: "ready", fromLibrary: true });
    expect(t.block?.id).toBe("hookes_amali-0123456789ab");
    expect(t.note).toBeNull(); // an ordinary library hit adds no caveat
  });

  it("a lab that arrives after a degraded stage clears the no-lab note: the last step made one (D-80)", () => {
    const t = last(run([stage("verify", "degraded", "No lab this time."), stage("assemble", "start", "A simpler lab is being written."), { type: "environment", block }]));
    expect(t).toMatchObject({ step: "ready", note: null });
  });

  it("an error event and a transport failure both end up on the turn, and closing ends it", () => {
    expect(last(run([{ type: "error", error: { code: "internal", message: "no", issues: [], retryable: true } }])).error).toMatchObject({ message: "no" });
    const asked = turnReducer([], { type: "ask", question: "q" });
    expect(last(turnReducer(asked, { type: "fail", error: "Could not reach the server." }))).toMatchObject({ error: "Could not reach the server.", open: false });
    expect(last(turnReducer(asked, { type: "close" })).open).toBe(false);
  });

  it("an event only ever changes the last turn", () => {
    const first = last(run([{ type: "text_delta", text: "one" }]));
    const both = turnReducer([{ ...first, open: false }], { type: "ask", question: "second" });
    expect(turnReducer(both, { type: "event", event: { type: "text_delta", text: "two" } }).map((t) => t.text)).toEqual(["one", "two"]);
  });

  it("has the five steps a student is shown, ending in Ready", () => {
    expect(STEPS.map((s) => s.key)).toEqual(["reading", "explaining", "planning", "checking", "ready"]);
  });
});
