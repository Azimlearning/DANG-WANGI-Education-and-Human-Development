import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ProbeEvent } from "@synapse/schema";
import { afterEach, describe, expect, it } from "vitest";
import { ProbeCard } from "./ProbeCard";
import { parseStreamEvent } from "../lib/stream";
import { turnReducer } from "../lib/turns";

afterEach(cleanup);

const probe: ProbeEvent = {
  type: "probe",
  id: "newton-force-needed-to-keep-moving",
  question: "A puck slides on very smooth ice. What does it do?",
  options: ["It slows down at once.", "It keeps moving at almost the same speed.", "It speeds up."],
  correct: 1,
  explanation: "With no resultant force an object keeps its velocity.",
  basis: "This correction is the assistant's own wording and no teacher has reviewed it yet.",
};

describe("ProbeCard", () => {
  it("shows the question and its options but hides the answer until one is chosen", () => {
    render(<ProbeCard probe={probe} />);
    expect(screen.getByText(probe.question)).toBeTruthy();
    expect(screen.getAllByRole("button").filter((b) => b.getAttribute("aria-pressed") !== null)).toHaveLength(3);
    expect(screen.queryByText(/resultant force/)).toBeNull();
    expect(screen.queryByText(/What this rests on/)).toBeNull();
  });

  it("says in words that a right answer is right, and shows the correction and what it rests on", () => {
    render(<ProbeCard probe={probe} />);
    fireEvent.click(screen.getByText("It keeps moving at almost the same speed."));
    expect(screen.getByRole("status").textContent).toContain("Yes, that is right.");
    expect(screen.getByRole("status").textContent).toContain(probe.explanation);
    expect(screen.getByRole("status").textContent).toContain("no teacher has reviewed it");
  });

  it("says a wrong answer is not quite right, marks the correct option in words, and keeps only the first answer", () => {
    render(<ProbeCard probe={probe} />);
    fireEvent.click(screen.getByText("It speeds up."));
    expect(screen.getByRole("status").textContent).toContain("Not quite");
    expect(screen.getByText(/\(correct answer\)/)).toBeTruthy();
    fireEvent.click(screen.getByText(/It keeps moving at almost/));
    expect(screen.getByRole("status").textContent).toContain("Not quite");
    for (const b of screen.getAllByRole("button").filter((x) => x.getAttribute("aria-pressed") !== null)) expect((b as HTMLButtonElement).disabled).toBe(true);
  });

  it("can be hidden, and every control is a button of at least the 44 px class", () => {
    render(<ProbeCard probe={probe} />);
    for (const b of screen.getAllByRole("button")) expect(b.className).toContain("btn");
    fireEvent.click(screen.getByLabelText("Hide this quick check"));
    expect(screen.queryByTestId("probe")).toBeNull();
  });

  it("renders text as text, never as markup", () => {
    render(<ProbeCard probe={{ ...probe, question: "<img src=x onerror=alert(1)> what happens?" }} />);
    expect(document.querySelector("img")).toBeNull();
  });
});

describe("the probe on the wire and in a turn", () => {
  it("is parsed when well formed and dropped when its answer index is not one of its options", () => {
    expect(parseStreamEvent(probe)).toEqual(probe);
    expect(parseStreamEvent({ ...probe, correct: 3 })).toBeNull();
    expect(parseStreamEvent({ ...probe, correct: 1.5 })).toBeNull();
    expect(parseStreamEvent({ ...probe, options: ["only one"] })).toBeNull();
    expect(parseStreamEvent({ ...probe, basis: 4 })).toBeNull();
  });

  it("lands on the current turn and nowhere else", () => {
    let turns = turnReducer([], { type: "ask", question: "q1" });
    turns = turnReducer(turns, { type: "event", event: probe });
    turns = turnReducer(turns, { type: "ask", question: "q2" });
    expect(turns[0]?.probe).toEqual(probe);
    expect(turns[1]?.probe).toBeNull();
  });
});
